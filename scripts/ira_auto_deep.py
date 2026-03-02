#!/usr/bin/env python3
"""
IRA AUTO-DEEP - Continuous Auto-Reply with Deep Technical Research
===================================================================

This is the main email auto-reply loop that:
1. Monitors Rushabh's emails continuously
2. Takes TIME to research properly (no rushing)
3. Uses pre-built machine database for accurate specs
4. Generates LONG, TECHNICAL replies (400-600 words)
5. Ensures Ira ALWAYS replies last in a thread

Rules:
- Only reply if Rushabh sent the last message
- Never reply to our own messages
- Wait 60 seconds between checks (give time for full conversation)
- Take as long as needed for research (quality > speed)
"""

import os
import sys
import time
import base64
import re
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

PROJECT_ROOT = Path(__file__).parent.parent
for line in (PROJECT_ROOT / ".env").read_text().splitlines():
    if line.strip() and not line.startswith('#') and '=' in line:
        key, _, value = line.partition('=')
        os.environ[key.strip()] = value.strip().strip('"')

sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/src/brain"))

import openai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from qdrant_client import QdrantClient
import voyageai

from machine_database import (
    get_machine, get_machines_by_series, find_machines_by_size,
    format_spec_table, MachineSpec, MACHINE_SPECS
)
try:
    from src.agents.fact_checker import verify_reply, FactChecker
except ImportError:
    from fact_checker import verify_reply, FactChecker
from hallucination_guard import HallucinationGuard
from knowledge_discovery import KnowledgeDiscoverer, KnowledgeGap
from inquiry_qualifier import InquiryQualifier
from machine_features_kb import answer_feature_question, get_series_comparison
from detailed_specs_generator import generate_detailed_specs
from audit_logger import get_audit_logger

# Initialize audit logger
audit = get_audit_logger()

# Valid model patterns for validation
VALID_MODEL_PREFIXES = ["PF1-", "PF2-", "IMG-", "AM-", "UNO", "DUO", "PLAY", "FCS-"]


def verify_specs_in_reply(reply: str, machines: list) -> tuple:
    """
    Verify that any specs mentioned in reply match the database.
    Returns (is_valid, issues_found)
    """
    import re
    issues = []
    
    # Build lookup of correct specs
    correct_specs = {}
    for m in machines:
        correct_specs[m.model] = {
            "forming_area": m.forming_area_mm,
            "price_inr": m.price_inr,
            "price_usd": m.price_usd or (m.price_inr // 83 if m.price_inr else None),
        }
    
    # Check each model mentioned
    for model, specs in correct_specs.items():
        if model in reply or normalize_model_name(model) in reply:
            # Check if forming area is mentioned correctly
            if specs["forming_area"]:
                # Extract dimensions from correct spec
                dims = re.findall(r'(\d+)', specs["forming_area"])
                if len(dims) >= 2:
                    w, h = int(dims[0]), int(dims[1])
                    # Look for wrong dimensions near this model in reply
                    model_section = reply[max(0, reply.find(model)-200):reply.find(model)+500]
                    found_dims = re.findall(r'(\d{3,4})\s*[x×]\s*(\d{3,4})', model_section)
                    for fd in found_dims:
                        fw, fh = int(fd[0]), int(fd[1])
                        # Check if dimensions match (allowing for swapped order)
                        if not ((fw == w and fh == h) or (fw == h and fh == w)):
                            # Check if it's close (within 100mm) - might be typo
                            if abs(fw - w) > 100 or abs(fh - h) > 100:
                                issues.append(f"{model}: Found {fw}x{fh}mm but should be {w}x{h}mm")
    
    return len(issues) == 0, issues


def validate_models_in_reply(reply: str) -> tuple:
    """
    Check if reply contains any invalid/hallucinated model names.
    Returns (is_valid, invalid_models_found)
    """
    import re
    
    # Find all model-like patterns in reply
    # Matches things like PF1-X-1520, IMG-1350, PF1-1020, etc.
    model_pattern = r'\b(PF[12]-[A-Z]?-?\d{3,4}|IMG-\d{3,4}|AM-\d{4}|UNO[\s-]?\d{4}|DUO[\s-]?\d{4}|PLAY[\s-]?\d{4})\b'
    found_models = re.findall(model_pattern, reply, re.IGNORECASE)
    
    invalid_models = []
    for model in found_models:
        # Normalize model name
        normalized = model.upper().replace(" ", "-")
        
        # Check if it exists in database
        if normalized not in MACHINE_SPECS:
            # Try with common variations
            variations = [
                normalized,
                normalized.replace("PF1-", "PF1-X-"),
                normalized.replace("PF1-", "PF1-C-"),
                normalized.replace("PF1-", "PF1-A-"),
            ]
            found = False
            for var in variations:
                if var in MACHINE_SPECS:
                    found = True
                    break
            if not found:
                invalid_models.append(model)
    
    return len(invalid_models) == 0, list(set(invalid_models))


# Config
RUSHABH_EMAILS = ["rushabh@machinecraft.org", "rushabh@machinecraft.in"]
IRA_EMAIL = "ira@machinecraft.org"
CHECK_INTERVAL = 30  # seconds - faster response time

# Clients
voyage = voyageai.Client()
qdrant = QdrantClient(url="http://localhost:6333")
openai_client = openai.OpenAI()


def log(msg: str):
    """Timestamped logging."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_gmail_service():
    """Get Gmail API service."""
    creds = Credentials.from_authorized_user_file(str(PROJECT_ROOT / "token.json"))
    return build('gmail', 'v1', credentials=creds)


def get_body(payload) -> str:
    """Extract email body from payload."""
    if 'body' in payload and payload['body'].get('data'):
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
    return ''


def clean_query(body: str) -> str:
    """Clean email body to extract the actual query."""
    # Remove signature and quoted text
    text = body.split('With Best Regards')[0]
    text = text.split('Best Regards')[0]
    text = text.split('\nOn ')[0]
    text = text.split('\n>')[0]
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()


def parse_query(query: str) -> dict:
    """Parse query to understand what's being asked."""
    log("Parsing query...")
    
    # Machine patterns
    patterns = {
        "PF1": [r"PF1", r"PF-1", r"single station"],
        "PF2": [r"PF2", r"PF-2", r"open type"],
        "AM": [r"AM[-\s]?\d", r"roll.?fed", r"thin gauge"],
        "IMG": [r"IMG", r"in.?mold", r"lamination"],
        "FCS": [r"FCS", r"inline", r"form.?cut"],
    }
    
    series = None
    for name, pats in patterns.items():
        for pat in pats:
            if re.search(pat, query, re.IGNORECASE):
                series = name
                break
        if series:
            break
    
    # Find specific model
    model = None
    model_match = re.search(r"(PF1|PF2|AM|IMG|FCS|UNO|DUO)[-\s]?([A-Z])?[-\s]?(\d{4})", query, re.IGNORECASE)
    if model_match:
        model = model_match.group(0).upper().replace(" ", "-")
    
    # Find size requirements
    size_match = re.search(r"(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(mm|m)?", query)
    size = None
    if size_match:
        w, h, unit = size_match.groups()
        w, h = float(w), float(h)
        # Only convert to mm if explicitly in meters or very small numbers
        if unit == "m" and unit != "mm":  # Explicit meters
            w *= 1000
            h *= 1000
        elif w < 10 and h < 10 and not unit:  # Small numbers without unit = meters
            w *= 1000
            h *= 1000
        size = (int(w), int(h))
    
    # Detect query intent and complexity
    query_lower = query.lower()
    
    # Intent detection
    intent = "GENERAL"
    if any(w in query_lower for w in ["price", "cost", "how much", "quote"]):
        intent = "PRICE_INQUIRY"
    elif any(w in query_lower for w in ["compare", "vs", "versus", "difference", "both"]):
        intent = "COMPARISON"
    elif any(w in query_lower for w in ["spec", "technical", "kw", "pump", "detail", "complete", "full spec", "all spec", "feature"]):
        intent = "DETAILED_SPECS"
    elif any(w in query_lower for w in ["recommend", "suggest", "which", "best", "suitable", "should", "offer"]):
        intent = "RECOMMENDATION"
    
    # Explicit detailed specs triggers
    detailed_triggers = [
        "detailed tech", "technical spec", "full spec", "all spec",
        "complete spec", "detailed spec", "comprehensive spec",
        "tech sheet", "data sheet", "feature list", "all feature",
        "detailed feature", "machine spec", "full detail"
    ]
    if any(trigger in query_lower for trigger in detailed_triggers):
        intent = "DETAILED_SPECS"
    
    # Customer proposal = detailed specs + recommendation
    if "customer" in query_lower and "proposal" in query_lower:
        intent = "DETAILED_SPECS"
    
    # Complexity detection
    complexity = "MEDIUM"
    word_count = len(query.split())
    if word_count < 15 and intent == "PRICE_INQUIRY":
        complexity = "SIMPLE"
    elif any(w in query_lower for w in ["complete", "detailed", "full", "comprehensive", "all", "proposal", "customer"]):
        complexity = "COMPLEX"
    elif any(w in query_lower for w in ["table", "compare", "both"]):
        complexity = "COMPLEX"
    elif word_count > 40:  # Long queries are complex
        complexity = "COMPLEX"
    
    log(f"  Series: {series}, Model: {model}, Size: {size}")
    log(f"  Intent: {intent}, Complexity: {complexity}")
    
    return {
        "series": series, 
        "model": model, 
        "size": size, 
        "raw": query,
        "intent": intent,
        "complexity": complexity
    }


def get_reply_length(parsed: dict, num_machines: int) -> tuple:
    """
    Determine appropriate reply length based on query.
    
    Returns (min_words, max_words, max_tokens)
    """
    intent = parsed.get("intent", "GENERAL")
    complexity = parsed.get("complexity", "MEDIUM")
    
    # Simple price inquiry
    if intent == "PRICE_INQUIRY" and num_machines == 1 and complexity == "SIMPLE":
        return (150, 300, 800)
    
    # Simple single machine question
    if num_machines == 1 and complexity == "SIMPLE":
        return (200, 400, 1000)
    
    # Comparison of 2 machines
    if intent == "COMPARISON" or num_machines >= 2:
        return (500, 900, 2000)
    
    # Detailed specs request - allow much longer replies for comprehensive specs
    if intent == "DETAILED_SPECS":
        return (1000, 2000, 5000)
    
    # Complex queries
    if complexity == "COMPLEX":
        return (800, 1200, 3000)
    
    # Recommendation
    if intent == "RECOMMENDATION":
        return (400, 700, 1500)
    
    # Default: medium length
    return (400, 700, 1500)


def filter_conflicting_context(text: str) -> bool:
    """
    Filter out context that might conflict with our database.
    Returns True if content should be EXCLUDED.
    """
    import re
    text_lower = text.lower()
    
    # Exclude competitor mentions
    competitors = ["frimo", "illig", "kiefel", "geiss", "cms thermoforming", "maac"]
    if any(comp in text_lower for comp in competitors):
        return True
    
    # Exclude content with spec-like patterns that aren't Machinecraft
    # Pattern: dimensions like "1.100 x 2.000" (European format - not ours)
    if re.search(r'\d\.\d{3}\s*[x×]\s*\d\.\d{3}', text):
        return True
    
    # Exclude if it mentions non-Machinecraft model patterns
    non_mc_patterns = [
        r'\bKL-\d+',      # FRIMO KL series
        r'\bIC-\d+',      # ILLIG IC series
        r'\bKFM\d+',      # Kiefel KFM series
    ]
    for pattern in non_mc_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False


def search_qdrant(query: str, limit: int = 10) -> list:
    """Search ALL Qdrant collections for relevant context."""
    log("Searching knowledge base...")
    
    embedding = voyage.embed([query], model="voyage-3", input_type="query").embeddings[0]
    
    results = []
    
    # Knowledge collections (feature KB uses keyword lookup instead)
    collections = [
        ("ira_chunks_v4_voyage", "document"),       # Ingested PDFs/docs
        ("ira_dream_knowledge_v1", "dream"),        # Dream mode discoveries
    ]
    
    filtered_count = 0
    for collection, source_type in collections:
        try:
            r = qdrant.query_points(
                collection_name=collection,
                query=embedding,
                limit=limit * 2,  # Get extra to account for filtering
                with_payload=True
            )
            for p in r.points:
                text = p.payload.get("text", p.payload.get("raw_text", ""))
                if text:
                    # Filter out conflicting content
                    if filter_conflicting_context(text):
                        filtered_count += 1
                        continue
                    
                    results.append({
                        "text": text[:800], 
                        "score": p.score,
                        "source": source_type,
                        "feature_name": p.payload.get("feature_name", "")
                    })
        except Exception:
            pass
    
    results.sort(key=lambda x: x["score"], reverse=True)
    if filtered_count:
        log(f"  Filtered {filtered_count} conflicting chunks")
    log(f"  Found {len(results)} relevant chunks")
    return results[:10]


def check_and_discover_missing_data(query: str, machines: list, context: list) -> dict:
    """
    Check if any data is missing and trigger discovery.
    
    Returns discovered data that can be added to the reply.
    """
    log("Checking for missing data...")
    
    discovered_data = {}
    
    # Check each machine for missing critical specs
    critical_fields = ["vacuum_pump_capacity", "heater_power_kw", "heater_type"]
    
    for machine in machines:
        missing = []
        for field in critical_fields:
            value = getattr(machine, field, None)
            if not value or value == "—":
                missing.append(field)
        
        if missing:
            log(f"  {machine.model} missing: {', '.join(missing)}")
            
            # Trigger discovery for each missing field
            try:
                discoverer = KnowledgeDiscoverer()
                
                for field in missing[:2]:  # Limit to 2 fields per machine
                    field_name = field.replace("_", " ")
                    gap = KnowledgeGap(
                        query=f"What is the {field_name} for {machine.model}?",
                        missing_data=f"{field_name} for {machine.model}",
                        data_type="spec",
                        entity=machine.model,
                        confidence=0.8
                    )
                    
                    # Find and scan files
                    candidates = discoverer.find_candidate_files(gap, limit=3)
                    if candidates:
                        results = discoverer.deep_scan_files(candidates, gap)
                        if results:
                            best = max(results, key=lambda x: x.confidence)
                            discovered_data[f"{machine.model}_{field}"] = best.data_point
                            log(f"    ✓ Discovered {field}: {best.data_point}")
                            
                            # Store for future
                            discoverer.store_knowledge(best, gap)
                            
            except Exception as e:
                log(f"    Discovery error: {e}")
    
    # Also check if query asks for something specific not in context
    query_lower = query.lower()
    specific_asks = [
        ("hotmelt", "hot melt lamination process"),
        ("vacuum lamination", "vacuum lamination technology"),
        ("cycle time", "typical cycle times"),
        ("material", "material compatibility"),
    ]
    
    for keyword, topic in specific_asks:
        if keyword in query_lower:
            # Check if we have good context for this
            has_context = any(keyword in c.get("text", "").lower() for c in context)
            if not has_context:
                log(f"  Query asks about '{topic}' but no context found")
                try:
                    discoverer = KnowledgeDiscoverer()
                    gap = KnowledgeGap(
                        query=query,
                        missing_data=topic,
                        data_type="general",
                        confidence=0.7
                    )
                    candidates = discoverer.find_candidate_files(gap, limit=3)
                    if candidates:
                        results = discoverer.deep_scan_files(candidates, gap)
                        if results:
                            best = max(results, key=lambda x: x.confidence)
                            discovered_data[topic] = {
                                "data": best.data_point,
                                "context": best.context,
                                "source": best.source_file
                            }
                            log(f"    ✓ Discovered {topic}: {best.data_point[:50]}...")
                except Exception as e:
                    log(f"    Discovery error for {topic}: {e}")
    
    return discovered_data


def find_machines(parsed: dict) -> list:
    """Find relevant machines from database."""
    log("Looking up machines in database...")
    
    machines = []
    seen_models = set()  # Track by model name to avoid duplicates
    
    def add_machine(m):
        """Add machine if not already seen (by normalized name)."""
        normalized = normalize_model_name(m.model)
        if normalized not in seen_models:
            machines.append(m)
            seen_models.add(normalized)
            return True
        return False
    
    # Specific model lookup
    if parsed["model"]:
        spec = get_machine(parsed["model"])
        if spec:
            add_machine(spec)
            log(f"  Found exact model: {spec.model}")
    
    # Size-based search
    if parsed["size"]:
        w, h = parsed["size"]
        suitable = find_machines_by_size(w, h)
        if parsed["series"]:
            suitable = [m for m in suitable if m.series.upper() == parsed["series"].upper()]
        for m in suitable[:4]:
            add_machine(m)
        log(f"  Found {len(suitable)} machines for size {w}x{h}mm")
    
    # Series-based search
    if parsed["series"] and len(machines) < 3:
        series_machines = get_machines_by_series(parsed["series"])
        for m in series_machines[:5]:
            add_machine(m)
    
    return machines[:5]  # Max 5 machines


def normalize_model_name(model: str) -> str:
    """
    Normalize model names for external communication:
    - PF1-A-xxxx → PF1-C-xxxx (same machine, different naming)
    - PF1-S-xxxx → PF1-X-xxxx (same machine, different naming)
    """
    if model.startswith("PF1-A-"):
        return model.replace("PF1-A-", "PF1-C-")
    if model.startswith("PF1-S-"):
        return model.replace("PF1-S-", "PF1-X-")
    return model


def format_machine_specs(machines: list) -> str:
    """Format machines as bullet point specs for email (cleaner than tables)."""
    if not machines:
        return ""
    
    sections = []
    
    for m in machines:
        model = normalize_model_name(m.model)
        
        # Determine series description
        if "X" in model:
            series_desc = "All-Servo with Autoloader"
        elif "C" in model:
            series_desc = "Pneumatic (Cost-Effective)"
        else:
            series_desc = m.variant or "Standard"
        
        # Format price
        if m.price_usd:
            price = f"${m.price_usd:,} USD"
        elif m.price_inr:
            price = f"₹{m.price_inr:,} (~${m.price_inr // 83:,} USD)"
        else:
            price = "Price on request"
        
        section = f"""**{model}** ({series_desc})
• Forming Area: {m.forming_area_mm} mm
• Max Tool Height: {m.max_tool_height_mm or 'N/A'} mm
• Max Draw Depth: {m.max_draw_depth_mm or m.max_tool_height_mm or 'N/A'} mm
• Heater: {m.heater_power_kw or 'N/A'} kW ({m.heater_type or 'IR Ceramic/Quartz'})
• Vacuum: {m.vacuum_pump_capacity or 'N/A'}
• Price: {price}"""
        
        if m.features:
            section += f"\n• Key Features: {', '.join(m.features[:4])}"
        
        sections.append(section)
    
    return "\n\n".join(sections)


def generate_reply(parsed: dict, machines: list, context: list) -> str:
    """Generate technical reply with dynamic length."""
    
    # Determine reply length
    min_words, max_words, max_tokens = get_reply_length(parsed, len(machines))
    log(f"Generating reply ({min_words}-{max_words} words)...")
    
    intent = parsed.get("intent", "GENERAL")
    
    # For DETAILED_SPECS, use comprehensive spec generator
    if intent == "DETAILED_SPECS" and machines:
        detailed_specs = generate_detailed_specs(machines[0].model)
        table = detailed_specs
    else:
        # Build specs (bullet points, not table)
        table = format_machine_specs(machines)
    
    # Build machine details with normalized names
    machine_info = ""
    for m in machines:
        # Handle price formatting safely
        if m.price_inr:
            price_str = f"₹{m.price_inr:,} (${m.price_inr // 83:,} USD)"
        else:
            price_str = "Price on request"
        
        # Normalize model name for display
        display_model = normalize_model_name(m.model)
        
        # Normalize variant display
        variant = m.variant
        if "A (" in variant:
            variant = variant.replace("A (", "C (")
        if "S (" in variant:
            variant = variant.replace("S (", "X (")
        
        machine_info += f"""
{display_model} ({m.series} series, {variant}):
  - Forming Area: {m.forming_area_mm} mm
  - Max Tool Height: {m.max_tool_height_mm} mm
  - Heater Power: {m.heater_power_kw} kW ({m.heater_type or 'standard'})
  - Vacuum: {m.vacuum_pump_capacity or 'N/A'}, Tank: {m.vacuum_tank_size or 'N/A'}
  - Price: {price_str}
  - Features: {', '.join(m.features[:3]) if m.features else 'Standard'}
"""
    
    # Build context
    context_text = "\n".join(c["text"][:400] for c in context[:3])
    
    # Build length-appropriate prompt
    intent = parsed.get("intent", "GENERAL")
    
    if intent == "PRICE_INQUIRY" and len(machines) == 1:
        # Short, focused price response
        length_instruction = f"Write a CONCISE reply ({min_words}-{max_words} words) that directly answers the price question with brief context."
        structure = """
1. Brief greeting (1 sentence)
2. Direct price answer with the machine details
3. One sentence on key features
4. Offer to provide full quotation"""
    
    elif intent == "COMPARISON" or len(machines) >= 2:
        # Detailed comparison
        length_instruction = f"Write a DETAILED comparison ({min_words}-{max_words} words) analyzing both machines."
        structure = """
1. Brief greeting
2. Quick recommendation
3. SPECIFICATIONS TABLE (include exactly as shown)
4. Technical analysis comparing both machines
5. When to choose each
6. Closing with offer for quotation"""
    
    elif intent == "DETAILED_SPECS":
        # Full technical response with comprehensive specs
        length_instruction = f"Write a COMPREHENSIVE technical reply ({min_words}-{max_words} words) covering ALL specifications. The email can be long - include every section from the detailed specs below."
        structure = """
1. Brief professional greeting
2. Include the COMPLETE DETAILED SPECIFICATIONS provided below - use ALL sections:
   - Machine Overview (model, series, forming area, tool height, draw depth, sheet thickness)
   - Heating System (heater power, total power, heater type, zones, zone control, sag control)
   - Vacuum System (pump type, tank size, brands, features, optional proportional valve)
   - Motion System (drive type, clamp frame, lower platen, benefits)
   - Sheet Loading System (type, mechanism, sheet separation, safety, cycle time)
   - Frame & Clamping System (frame type, changeover time, construction)
   - Tool Change System (ball transfer units, lift cylinders, change time, clamping options)
   - Cooling System (standard fans, optional ducted cooling, water mist)
   - Control System (PLC brand, HMI, servo drives, features, remote monitoring)
   - Electrical Specifications (power supply, control cabinet, heater control)
   - Safety Features (perimeter guards, light curtains, 2-level safety, emergency stops, CE compliance)
   - Pricing (price, what's included, optional upgrades)
   - Applications (if applicable)
   - Key Features (if applicable)
3. Brief closing offer for quotation or demo

IMPORTANT: This is a DETAILED technical specification request. Include EVERY technical detail from the specs below. The email should be comprehensive - 1000+ words is expected."""
    
    else:
        # Standard response
        length_instruction = f"Write a HELPFUL reply ({min_words}-{max_words} words)."
        structure = """
1. Brief greeting
2. Answer their question directly
3. Include specs table if relevant
4. Technical context
5. Offer further help"""
    
    # Get list of all valid models for validation
    from machine_database import MACHINE_SPECS
    valid_models = sorted(MACHINE_SPECS.keys())
    valid_models_str = ", ".join(valid_models[:30]) + "..."  # First 30 for reference
    
    prompt = f"""You are Ira, Machinecraft's technical sales expert. Write in a professional, consultative tone similar to McKinsey or BCG communications - clear, structured, data-driven, and respectful.

RUSHABH'S QUERY:
{parsed['raw']}

═══════════════════════════════════════════════════════════════════════════════
MACHINES FROM DATABASE (ONLY SOURCE OF TRUTH - USE THESE EXACT SPECS):
═══════════════════════════════════════════════════════════════════════════════
{machine_info}

MACHINE SPECIFICATIONS (use bullet point format):
{table}

{length_instruction}

STRUCTURE TO FOLLOW:
{structure}

═══════════════════════════════════════════════════════════════════════════════
⚠️ ABSOLUTE RULES - VIOLATION WILL CAUSE REJECTION:
═══════════════════════════════════════════════════════════════════════════════
1. ONLY mention these EXACT machines from above - NO OTHERS
2. Use ONLY the specs listed above - DO NOT invent dimensions or prices
3. DO NOT mention any machine not in the database above
4. IGNORE any competitor machines (FRIMO, Illig, Kiefel) in context
5. If a requested size isn't available, say "we can customize" - don't invent models

VALID MACHINECRAFT MODELS: {valid_models_str}
Any model NOT in this list is INVALID and must NOT be mentioned.

TONE: Professional, consultative, MBB-style. No flowery language.
SIGN OFF: "Ira, Technical Sales, Machinecraft"
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"You are Ira, a professional technical sales consultant at Machinecraft. Write {min_words}-{max_words} word responses in a clear, consultative, MBB-style tone. Be data-driven and structured. CRITICAL: Only use machines from the database - never invent names."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens,
        temperature=0.3  # Lower temperature for more consistent professional tone
    )
    
    return response.choices[0].message.content


def send_reply(reply: str, thread_id: str, to: str, subject: str):
    """Send the reply."""
    service = get_gmail_service()
    
    msg = MIMEMultipart()
    msg['to'] = to
    msg['from'] = IRA_EMAIL
    msg['subject'] = f"Re: {subject}" if not subject.startswith("Re:") else subject
    msg.attach(MIMEText(reply, 'plain'))
    
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = service.users().messages().send(
        userId='me',
        body={'raw': raw, 'threadId': thread_id}
    ).execute()
    
    log(f"✅ Reply sent! ID: {sent['id']}")
    return sent


def check_and_reply():
    """Main check and reply cycle."""
    log("=" * 50)
    log("Checking for emails from Rushabh...")
    
    service = get_gmail_service()
    
    # Get threads from Rushabh
    results = service.users().threads().list(
        userId='me',
        q=f'from:({" OR ".join(RUSHABH_EMAILS)}) newer_than:4h',
        maxResults=5
    ).execute()
    
    threads = results.get('threads', [])
    if not threads:
        log("No recent threads from Rushabh")
        return
    
    log(f"Found {len(threads)} recent threads")
    
    for thread in threads:
        thread_data = service.users().threads().get(userId='me', id=thread['id']).execute()
        messages = thread_data.get('messages', [])
        
        if not messages:
            continue
        
        # Check last message
        last_msg = messages[-1]
        headers = {h['name']: h['value'] for h in last_msg['payload']['headers']}
        last_from = headers.get('From', '')
        
        # Only reply if Rushabh sent the last message
        is_from_rushabh = any(e in last_from.lower() for e in RUSHABH_EMAILS)
        is_from_ira = IRA_EMAIL in last_from.lower()
        
        if not is_from_rushabh or is_from_ira:
            log(f"  Thread {thread['id'][:8]}: Last message not from Rushabh, skipping")
            continue
        
        # Check if unread
        labels = last_msg.get('labelIds', [])
        if 'UNREAD' not in labels:
            log(f"  Thread {thread['id'][:8]}: Already read, skipping")
            continue
        
        # Get the query
        body = get_body(last_msg['payload'])
        if not body or len(body) < 10:
            continue
        
        query = clean_query(body)
        subject = headers.get('Subject', 'Technical Inquiry')
        
        log("=" * 50)
        log("PROCESSING EMAIL")
        log(f"Subject: {subject}")
        log(f"Query preview: {query[:100]}...")
        log("=" * 50)
        
        # Start audit logging
        audit.start_request(thread['id'], query)
        
        # CHECK FOR FEATURE QUESTIONS FIRST
        # If asking about autoloader, heaters, series comparison, etc.
        feature_answer = answer_feature_question(query)
        if feature_answer and len(query) < 200:  # Short query likely a direct question
            query_lower = query.lower()
            is_feature_question = any(kw in query_lower for kw in [
                "what is", "what does", "explain", "difference between",
                "autoloader", "heater", "ceramic", "quartz", "halogen",
                "c vs x", "c or x", "which series", "vacuum system"
            ])
            
            if is_feature_question:
                log("📚 Feature question detected - answering from knowledge base")
                
                # Format the reply
                reply = f"""Hello Rushabh,

{feature_answer}

If you have any other questions about machine features or specifications, feel free to ask!

Best regards,
Ira
Technical Sales
Machinecraft"""
                
                # Send directly
                send_reply(reply, thread['id'], headers.get('From', ''), subject)
                
                # Mark as read
                service.users().messages().modify(
                    userId='me', id=last_msg['id'],
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                log("Marked as read")
                continue
        
        # QUALIFICATION FLOW - Check if we need to ask questions first
        qualifier = InquiryQualifier()
        profile = qualifier.get_or_create_profile(thread['id'], headers.get('From', ''))
        profile = qualifier.extract_info_from_message(query, profile)
        
        log(f"Qualification stage: {profile.qualification_stage}")
        log(f"  Size: {profile.max_forming_area}, Depth: {profile.max_forming_depth}")
        log(f"  Loading: {profile.sheet_loading}, Materials: {profile.materials}")
        
        # If not ready for proposal, ask qualifying questions
        if not qualifier.is_ready_for_proposal(profile):
            log("❓ Need more info - sending qualification questions")
            qualification_msg = qualifier.generate_qualification_message(profile)
            
            if qualification_msg:
                # Send qualification questions
                send_reply(qualification_msg, thread['id'], headers.get('From', ''), subject)
                
                # Mark as read
                service.users().messages().modify(
                    userId='me', id=last_msg['id'],
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                log("Marked as read")
                continue  # Move to next thread
        
        log("✅ Ready for proposal - generating recommendation")
        log(f"  Recommended series: {qualifier.get_recommendation_type(profile)}")
        
        # Deep research
        parsed = parse_query(query)
        
        # Audit: Log parsed query
        audit.log_parsed(
            intent=parsed.get('intent', 'GENERAL'),
            series=parsed.get('series', ''),
            model=parsed.get('model', ''),
            size=str(parsed.get('size', ''))
        )
        
        # Use qualification to filter machines
        recommended_type = qualifier.get_recommendation_type(profile)
        machines = find_machines(parsed)
        
        # Filter based on qualification
        if recommended_type == "PF1-X":
            # Prioritize X series (with autoloader)
            x_machines = [m for m in machines if "-X-" in m.model or "-XL-" in m.model]
            if x_machines:
                machines = x_machines + [m for m in machines if m not in x_machines][:1]
        elif recommended_type == "PF1-C":
            # Prioritize C series (cost effective)
            c_machines = [m for m in machines if "-C-" in m.model or "-A-" in m.model]
            if c_machines:
                machines = c_machines + [m for m in machines if m not in c_machines][:1]
        
        context = search_qdrant(query)
        
        # Audit: Log machines and search results
        audit.log_machines(machines)
        audit.log_qdrant_search(query, context)
        
        if machines:
            for m in machines:
                log(f"  Machine: {m.model} - {m.forming_area_mm} - ₹{m.price_inr:,}" if m.price_inr else f"  Machine: {m.model}")
        
        # KNOWLEDGE DISCOVERY - Find missing data on-the-fly
        discovered_data = {}
        try:
            discovered_data = check_and_discover_missing_data(query, machines, context)
            if discovered_data:
                log(f"Discovered {len(discovered_data)} new data points")
                # Add discovered data to context for reply generation
                for key, value in discovered_data.items():
                    if isinstance(value, dict):
                        context.append({
                            "text": f"DISCOVERED: {key}: {value.get('data', '')}. {value.get('context', '')}",
                            "score": 0.95
                        })
                    else:
                        context.append({
                            "text": f"DISCOVERED: {key}: {value}",
                            "score": 0.95
                        })
        except Exception as e:
            log(f"Discovery error (continuing without): {e}")
        
        # Generate reply
        reply = generate_reply(parsed, machines, context)
        
        # MULTI-LAYER HALLUCINATION PROTECTION
        guard = HallucinationGuard()
        fact_checker = FactChecker()
        
        # Layer 0: Validate models exist in database
        is_valid, invalid_models = validate_models_in_reply(reply)
        retry_count = 0
        max_retries = 3
        
        # Audit: Log Layer 0 validation
        audit.log_validation("model_exists", is_valid, f"Invalid: {invalid_models}" if not is_valid else "All models valid")
        
        while not is_valid and retry_count < max_retries:
            log(f"🚨 INVALID MODELS DETECTED: {invalid_models}")
            log(f"Regenerating reply (attempt {retry_count + 1})...")
            audit.log_regeneration(retry_count + 1, f"Invalid models: {invalid_models}")
            parsed['force_strict'] = True
            reply = generate_reply(parsed, machines, context)
            is_valid, invalid_models = validate_models_in_reply(reply)
            retry_count += 1
        
        if not is_valid:
            log(f"🚨 STILL INVALID after {max_retries} retries: {invalid_models}")
            audit.log_validation("model_exists_final", False, f"Still invalid: {invalid_models}")
        
        # Layer 0.5: Verify specs match database
        specs_valid, spec_issues = verify_specs_in_reply(reply, machines)
        audit.log_validation("specs_match", specs_valid, f"Issues: {spec_issues}" if not specs_valid else "Specs verified")
        
        if not specs_valid:
            log(f"⚠️ SPEC MISMATCH DETECTED: {spec_issues}")
            audit.log_regeneration(retry_count + 1, f"Spec mismatch: {spec_issues}")
            # Regenerate with emphasis on using exact specs
            parsed['force_strict'] = True
            reply = generate_reply(parsed, machines, context)
            specs_valid, spec_issues = verify_specs_in_reply(reply, machines)
            if not specs_valid:
                log(f"⚠️ Still has spec issues after regeneration: {spec_issues}")
                audit.log_validation("specs_match_final", False, f"Still has issues: {spec_issues}")
        
        # Layer 1: Quick hallucination check (fake machine name patterns)
        has_hallucination, fake_names = fact_checker.has_hallucinated_machines(reply)
        audit.log_validation("no_fake_machines", not has_hallucination, f"Fake: {fake_names}" if has_hallucination else "No fake names")
        retry_count = 0
        
        while has_hallucination and retry_count < max_retries:
            log(f"🚨 BLOCKED (Layer 1): LLM hallucinated fake machines: {fake_names}")
            log(f"Regenerating reply (attempt {retry_count + 1})...")
            audit.log_regeneration(retry_count + 1, f"Fake machines: {fake_names}")
            
            # Add even more explicit instructions
            parsed['force_strict'] = True
            reply = generate_reply(parsed, machines, context)
            
            has_hallucination, fake_names = fact_checker.has_hallucinated_machines(reply)
            retry_count += 1
        
        if has_hallucination:
            log(f"🚨 STILL HALLUCINATING after {max_retries} retries")
            audit.log_validation("no_fake_machines_final", False, f"Still has: {fake_names}")
        
        # Layer 2: Full safety verification
        safety = guard.verify_all_claims(reply, machines)
        log(f"Safety check: risk={safety.hallucination_risk:.2f}, safe={safety.is_safe}")
        audit.log_validation("safety_check", safety.is_safe, f"Risk: {safety.hallucination_risk:.2f}")
        
        if safety.ungrounded_claims:
            log(f"  Ungrounded: {safety.ungrounded_claims}")
        if safety.warnings:
            log(f"  Warnings: {safety.warnings[:3]}")
        
        # Layer 3: Confidence scoring
        confidence = guard.score_response_confidence(reply, machines)
        log(f"Confidence score: {confidence:.2f}")
        audit.log_validation("confidence", confidence >= 0.5, f"Score: {confidence:.2f}")
        
        # Use fallback for: invalid models, fake names, or unresolvable hallucinations
        use_fallback = (not is_valid) or (has_hallucination and len(safety.ungrounded_claims) > 0)
        
        if use_fallback:
            log("🔒 Using safe fallback reply due to unresolvable hallucination")
            machine_list = ", ".join([m.model for m in machines[:5]]) if machines else "our PF1-C-2020, PF1-C-2520, PF2-P2020"
            
            # Generate a better fallback with actual specs
            if machines:
                table = format_spec_table(machines[:3])
                reply = f"""Hello Rushabh,

Thank you for your enquiry. Based on your requirements for a thermoforming machine, here are the recommended options from our range:

{table}

I recommend the {machines[0].model} for your application. Key specifications:
- Forming Area: {machines[0].forming_area_mm}
- Heater Power: {machines[0].heater_power_kw} kW
- Price: ₹{machines[0].price_inr:,} (${machines[0].price_inr // 83:,} USD)

Please let me know if you need additional details on any of these machines.

Best regards,
Ira
Technical Sales Expert
Machinecraft"""
            else:
                reply = f"""Hello Rushabh,

Thank you for your enquiry. For your requirements, I recommend exploring our PF1-C series machines which are ideal for thick sheet forming applications like truck bedliners.

Suitable models include: {machine_list}

I'll compile detailed specifications and pricing for these options and send them shortly.

Best regards,
Ira
Technical Sales Expert
Machinecraft"""
        
        # Layer 4: Fact-check specs and prices
        log("Fact-checking reply...")
        verified_reply, fact_report = verify_reply(reply, machines)
        log(fact_report)
        
        # Audit: Log final reply
        audit.log_reply(verified_reply, fallback=use_fallback)
        
        log("\n" + "=" * 50)
        log("VERIFIED REPLY:")
        log("=" * 50)
        print(verified_reply)
        log("=" * 50 + "\n")
        
        # Send the VERIFIED reply
        send_reply(verified_reply, thread['id'], headers.get('From', RUSHABH_EMAILS[0]), subject)
        
        # Mark as read
        service.users().messages().modify(
            userId='me',
            id=last_msg['id'],
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        log("Marked as read")
        
        # Audit: End request successfully
        audit.end_request(success=True)
        
        # Only process one email per cycle
        break


def main():
    """Main loop."""
    print("\n" + "=" * 60)
    print("IRA AUTO-DEEP REPLY SYSTEM")
    print("Deep technical research with accurate specs")
    print(f"Checking every {CHECK_INTERVAL} seconds")
    print(f"Audit logs: data/audit_logs/")
    print("=" * 60 + "\n")
    
    while True:
        try:
            check_and_reply()
        except Exception as e:
            log(f"Error: {e}")
            audit.log_error(str(e))
            audit.end_request(success=False)
            import traceback
            traceback.print_exc()
        
        log(f"\nWaiting {CHECK_INTERVAL} seconds...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
