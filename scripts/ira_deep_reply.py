#!/usr/bin/env python3
"""
IRA DEEP REPLY - Thorough Technical Research System
====================================================

Unlike quick replies, this system:
1. Takes TIME to research thoroughly (30-60 seconds is fine)
2. Uses PRE-EXTRACTED machine database for accurate specs
3. Searches MULTIPLE sources in sequence
4. Generates LONGER, more technical replies (400-600 words)
5. Formats tables properly for email (plain text aligned)

Research Flow:
1. Parse query to understand what's being asked
2. Look up machines in the pre-built database (instant, accurate)
3. Search Qdrant for additional context
4. Search specific PDFs for extra details
5. Generate comprehensive reply with full specs
6. Format properly and send
"""

import os
import sys
import re
import base64
import json
import pdfplumber
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

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

# Import our machine database
from machine_database import (
    get_machine, get_machines_by_series, find_machines_by_size,
    format_spec_table, MachineSpec, MACHINE_SPECS
)

# Paths
IMPORTS_DIR = PROJECT_ROOT / "data" / "imports"
PRICE_LIST_PDF = IMPORTS_DIR / "Machinecraft Price List for Plastindia (1).pdf"

# Machine series patterns (for query parsing)
MACHINE_PATTERNS = {
    "PF1": [r"PF1", r"PF-1", r"pressure form", r"single station"],
    "PF2": [r"PF2", r"PF-2", r"open type"],
    "AM": [r"AM[-\s]?\d", r"roll.?fed", r"thin gauge"],
    "IMG": [r"IMG", r"in.?mold.?grain", r"lamination"],
    "FCS": [r"FCS", r"inline", r"form.?cut.?stack"],
    "UNO": [r"UNO", r"uno"],
    "DUO": [r"DUO", r"duo", r"double station"],
}


class DeepResearcher:
    """
    Thorough technical research system.
    
    Uses pre-extracted machine database for accuracy.
    Takes time to find ALL relevant data.
    """
    
    def __init__(self):
        self.voyage = voyageai.Client()
        self.qdrant = QdrantClient(url="http://localhost:6333")
        self.openai = openai.OpenAI()
        self.pdf_cache: Dict[str, str] = {}
        
    def _log(self, msg: str):
        """Log with timestamp."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    
    # =========================================================================
    # DATABASE LOOKUPS (Fast & Accurate)
    # =========================================================================
    
    def lookup_machines_from_db(self, models: List[str]) -> List[MachineSpec]:
        """Look up machines from our pre-built database."""
        self._log(f"Looking up {len(models)} machines in database...")
        
        found = []
        for model in models:
            spec = get_machine(model)
            if spec:
                found.append(spec)
                self._log(f"  ✓ Found {spec.model}: {spec.forming_area_mm}, {spec.heater_power_kw}kW")
            else:
                self._log(f"  ✗ Not found: {model}")
        
        return found
    
    def find_suitable_machines(self, width_mm: int, height_mm: int, series: str = None) -> List[MachineSpec]:
        """Find machines that meet size requirements."""
        self._log(f"Finding machines >= {width_mm}x{height_mm}mm...")
        
        all_suitable = find_machines_by_size(width_mm, height_mm)
        
        if series:
            all_suitable = [m for m in all_suitable if m.series.upper() == series.upper()]
        
        self._log(f"  Found {len(all_suitable)} suitable machines")
        return all_suitable
    
    # =========================================================================
    # STEP 1: Parse Query
    # =========================================================================
    
    def parse_query(self, query: str) -> Dict:
        """Understand what's being asked."""
        self._log("Parsing query...")
        
        # Detect machine series
        series = None
        for name, patterns in MACHINE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    series = name
                    break
            if series:
                break
        
        # Detect specific model (multiple formats)
        model = None
        model_patterns = [
            r"(PF1|PF2|AM|IMG|FCS|UNO|DUO)[-\s]?([A-Z])?[-\s]?(\d{4})",  # PF1-C-2015
            r"(AM|IMG|UNO|DUO)[-\s]?(\d{4})",  # AM-5060
            r"(PF1|PF2)[-\s]?([A-Z])[-\s]?(\d{4})",  # PF1-A-1510
        ]
        for pattern in model_patterns:
            model_match = re.search(pattern, query, re.IGNORECASE)
            if model_match:
                model = model_match.group(0).upper().replace(" ", "-")
                break
        
        # Detect what's being asked
        wants_specs = any(w in query.lower() for w in ["spec", "technical", "kw", "pump", "power", "area", "dimension", "detail"])
        wants_price = any(w in query.lower() for w in ["price", "cost", "budget", "inr", "usd", "quote"])
        wants_comparison = any(w in query.lower() for w in ["compare", "both", "table", "vs", "difference"])
        
        # Extract dimensions if mentioned
        size_match = re.search(r"(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(m|mm|feet|ft)?", query)
        size = None
        if size_match:
            w, h, unit = size_match.groups()
            size = {"width": float(w), "height": float(h), "unit": unit or "mm"}
        
        result = {
            "series": series,
            "model": model,
            "wants_specs": wants_specs,
            "wants_price": wants_price,
            "wants_comparison": wants_comparison,
            "size_requirement": size,
            "raw_query": query
        }
        
        self._log(f"  Series: {series}, Model: {model}, Wants specs: {wants_specs}")
        return result
    
    # =========================================================================
    # STEP 2: Search Documents
    # =========================================================================
    
    def search_qdrant(self, query: str, collections: List[str], limit: int = 10) -> List[Dict]:
        """Search Qdrant for relevant chunks."""
        self._log(f"Searching Qdrant ({len(collections)} collections)...")
        
        embedding = self.voyage.embed([query], model="voyage-3", input_type="query").embeddings[0]
        
        all_results = []
        for collection in collections:
            try:
                results = self.qdrant.query_points(
                    collection_name=collection,
                    query=embedding,
                    limit=limit,
                    with_payload=True
                )
                for r in results.points:
                    text = r.payload.get("text", r.payload.get("raw_text", ""))
                    if text:
                        all_results.append({
                            "text": text,
                            "score": r.score,
                            "source": r.payload.get("filename", collection),
                            "collection": collection
                        })
            except Exception as e:
                self._log(f"  {collection}: error - {e}")
        
        # Sort by score
        all_results.sort(key=lambda x: x["score"], reverse=True)
        self._log(f"  Found {len(all_results)} results")
        return all_results
    
    def search_pdfs_for_machine(self, series: str, model: Optional[str] = None) -> List[Dict]:
        """Search PDFs specifically for machine specs."""
        self._log(f"Searching PDFs for {series} specs...")
        
        results = []
        
        # Keywords to look for based on series
        series_keywords = {
            "PF1": ["PF1", "Catalogue", "Quotation"],
            "PF2": ["PF2"],
            "AM": ["AM Machine", "AM-"],
            "IMG": ["IMG", "Catalogue"],
            "FCS": ["FCS", "Brochure"],
            "UNO": ["UNO"],
            "DUO": ["DUO"],
        }
        keywords = series_keywords.get(series, [series])
        
        # Find relevant PDFs
        relevant_pdfs = []
        for pdf_path in IMPORTS_DIR.glob("**/*.pdf"):
            name_lower = pdf_path.name.lower()
            if any(kw.lower() in name_lower for kw in keywords):
                relevant_pdfs.append(pdf_path)
        
        # Also check for specific model
        if model:
            model_clean = model.replace("-", "").replace(" ", "")
            for pdf_path in IMPORTS_DIR.glob("**/*.pdf"):
                if model_clean.lower() in pdf_path.name.lower().replace("-", "").replace(" ", ""):
                    if pdf_path not in relevant_pdfs:
                        relevant_pdfs.append(pdf_path)
        
        self._log(f"  Found {len(relevant_pdfs)} relevant PDFs")
        
        # Extract content from each
        for pdf_path in relevant_pdfs[:5]:  # Limit to top 5
            try:
                if str(pdf_path) not in self.pdf_cache:
                    with pdfplumber.open(str(pdf_path)) as pdf:
                        text = "\n".join(page.extract_text() or "" for page in pdf.pages[:20])
                        self.pdf_cache[str(pdf_path)] = text
                
                results.append({
                    "text": self.pdf_cache[str(pdf_path)],
                    "source": pdf_path.name,
                    "path": str(pdf_path)
                })
            except Exception as e:
                self._log(f"  Error reading {pdf_path.name}: {e}")
        
        return results
    
    # =========================================================================
    # STEP 3: Generate Comprehensive Reply
    # =========================================================================
    
    def format_specs_table_vertical(self, machines: List[MachineSpec]) -> str:
        """
        Format specs as a VERTICAL comparison table.
        Each row is a spec, each column is a machine.
        Uses plain text with proper alignment for email.
        """
        if not machines:
            return ""
        
        # Spec definitions: (label, getter function)
        specs_to_show = [
            ("Model", lambda m: m.model),
            ("Series", lambda m: f"{m.series}-{m.variant}" if m.variant else m.series),
            ("Forming Area", lambda m: m.forming_area_mm + " mm"),
            ("Max Tool Height", lambda m: f"{m.max_tool_height_mm} mm" if m.max_tool_height_mm else "—"),
            ("Max Draw Depth", lambda m: f"{m.max_draw_depth_mm} mm" if m.max_draw_depth_mm else "—"),
            ("Heater Power", lambda m: f"{m.heater_power_kw} kW" if m.heater_power_kw else "—"),
            ("Heater Type", lambda m: m.heater_type or "—"),
            ("Vacuum Pump", lambda m: m.vacuum_pump_capacity or "—"),
            ("Vacuum Tank", lambda m: m.vacuum_tank_size or "—"),
            ("Power Supply", lambda m: m.power_supply or "—"),
            ("Price (INR)", lambda m: f"₹{m.price_inr:,}" if m.price_inr else "On request"),
            ("Price (USD)", lambda m: f"${m.price_inr // 83:,}" if m.price_inr else "On request"),
        ]
        
        # Calculate column widths
        label_width = max(len(s[0]) for s in specs_to_show) + 2
        value_width = 22
        
        lines = []
        
        # Header row
        header = "Specification".ljust(label_width)
        for m in machines:
            header += m.model.ljust(value_width)
        lines.append(header)
        lines.append("=" * (label_width + value_width * len(machines)))
        
        # Data rows
        for label, getter in specs_to_show:
            row = label.ljust(label_width)
            for m in machines:
                value = str(getter(m) or "—")
                row += value[:value_width-1].ljust(value_width)
            lines.append(row)
        
        return "\n".join(lines)
    
    def generate_reply(self, parsed_query: Dict, machines: List[MachineSpec], context: str) -> str:
        """Generate comprehensive technical reply (400-600 words)."""
        self._log("Generating comprehensive technical reply...")
        
        # Build specs table
        specs_table = self.format_specs_table_vertical(machines) if machines else ""
        
        # Build detailed machine summary for context
        machine_details = ""
        for m in machines:
            machine_details += f"""
Machine: {m.model}
- Series: {m.series} ({m.variant})
- Forming Area: {m.forming_area_mm} mm
- Max Tool Height: {m.max_tool_height_mm} mm
- Heater Power: {m.heater_power_kw} kW
- Heater Type: {m.heater_type}
- Vacuum Pump: {m.vacuum_pump_capacity}
- Price: ₹{m.price_inr:,} (${m.price_inr // 83:,} USD)
- Description: {m.description}
- Features: {', '.join(m.features) if m.features else 'Standard configuration'}
"""
        
        prompt = f"""You are Ira, Machinecraft's highly knowledgeable technical sales assistant.

PERSONALITY:
- Dry British wit (subtle, not forced)
- Warm and genuinely helpful with the founder (your colleague/boss)
- DEEPLY technical - you understand thermoforming inside out
- You explain WHY specs matter, not just what they are
- You anticipate follow-up questions

QUERY FROM THE FOUNDER:
{parsed_query['raw_query']}

MACHINES I'VE FOUND (from our verified database):
{machine_details}

SPECIFICATIONS TABLE (include this EXACTLY in your reply):
{specs_table}

ADDITIONAL CONTEXT FROM DOCUMENTS:
{context[:1500]}

WRITE A COMPREHENSIVE REPLY (400-600 words) that:

1. OPENING: Brief warm greeting with subtle wit (1-2 sentences)

2. DIRECT ANSWER: Immediately state which machine(s) you recommend and why

3. SPECIFICATIONS TABLE: Include the full table above (copy it exactly, preserve formatting)

4. TECHNICAL EXPLANATION (this is important):
   - Explain what the heater power means for production (e.g., "125 kW allows rapid heating of thick sheets up to 8mm")
   - Explain why the forming area matters for the application
   - Explain vacuum system implications if relevant
   - Compare the options if multiple machines shown

5. APPLICATION CONTEXT: How these specs relate to what they're making (if mentioned)

6. RECOMMENDATIONS: Your professional opinion on which to choose and why

7. CLOSING: Offer to provide more details, quotation, or arrange a technical call

IMPORTANT:
- Be TECHNICAL and THOROUGH - this is a professional sales response
- Use actual numbers from the data above
- Don't invent specs - if something is marked "—" or missing, say so
- Keep the table formatted exactly as shown (it's designed for email)
- Sound knowledgeable and confident, not robotic
"""

        response = self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are Ira, a technical sales expert at Machinecraft. Generate detailed, professional responses that demonstrate deep knowledge of thermoforming equipment. Be thorough but personable."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.6
        )
        
        return response.choices[0].message.content
    
    # =========================================================================
    # MAIN RESEARCH FLOW
    # =========================================================================
    
    def research_and_reply(self, query: str) -> Tuple[str, Dict]:
        """
        Full research pipeline.
        
        Uses pre-built database for accurate specs.
        Takes time to be thorough - quality over speed.
        """
        self._log("=" * 60)
        self._log("STARTING DEEP RESEARCH")
        self._log("=" * 60)
        
        # Step 1: Parse query
        parsed = self.parse_query(query)
        
        # Step 2: Find machines from DATABASE (accurate, instant)
        machines = []
        
        # If specific model mentioned, look it up
        if parsed["model"]:
            spec = get_machine(parsed["model"])
            if spec:
                machines.append(spec)
        
        # If size requirement mentioned, find suitable machines
        if parsed["size_requirement"]:
            size = parsed["size_requirement"]
            w = int(size["width"])
            h = int(size["height"])
            # Convert if needed
            if size["unit"] in ("m", "meter"):
                w *= 1000
                h *= 1000
            suitable = self.find_suitable_machines(w, h, parsed["series"])
            for m in suitable[:3]:
                if m not in machines:
                    machines.append(m)
        
        # If series mentioned but no specific model, get series options
        if parsed["series"] and not machines:
            series_machines = get_machines_by_series(parsed["series"])
            machines = series_machines[:5]  # Top 5 from the series
        
        # Step 3: Search Qdrant for additional context
        qdrant_results = self.search_qdrant(
            query,
            collections=["ira_chunks_v4_voyage", "ira_dream_knowledge_v1"],
            limit=10
        )
        
        # Step 4: Extract any additional model mentions from results
        found_models = set(m.model for m in machines)
        for r in qdrant_results[:5]:
            # Look for model patterns
            model_matches = re.findall(
                r"(PF1[-\s]?[A-Z]?[-\s]?\d{4}|AM[-\s]?\d{4}|IMG[-\s]?\d{4}|FCS[-\s]?\d{4})",
                r["text"], re.IGNORECASE
            )
            for m in model_matches[:2]:
                clean = m.upper().replace(" ", "-")
                if clean not in found_models:
                    spec = get_machine(clean)
                    if spec:
                        machines.append(spec)
                        found_models.add(clean)
        
        # Step 5: Search specific PDFs for more context
        pdf_context = ""
        if parsed["series"]:
            pdf_results = self.search_pdfs_for_machine(parsed["series"], parsed["model"])
            for pdf in pdf_results[:2]:
                pdf_context += f"\n[From {pdf['source']}]:\n{pdf['text'][:1000]}\n"
        
        # Step 6: Build full context
        context = ""
        for r in qdrant_results[:5]:
            context += f"\n{r['text'][:500]}\n"
        context += pdf_context
        
        self._log(f"Found {len(machines)} machines from database")
        for m in machines:
            self._log(f"  • {m.model}: {m.forming_area_mm}, {m.heater_power_kw}kW, ₹{m.price_inr:,}" if m.price_inr else f"  • {m.model}: {m.forming_area_mm}")
        
        # Step 7: Generate comprehensive reply
        reply = self.generate_reply(parsed, machines, context)
        
        self._log("=" * 60)
        self._log("RESEARCH COMPLETE")
        self._log("=" * 60)
        
        return reply, {
            "parsed": parsed,
            "machines_found": len(machines),
            "machine_models": [m.model for m in machines],
            "docs_searched": len(qdrant_results)
        }


def send_reply(reply: str, thread_id: str, to_email: str, subject: str):
    """Send the reply email."""
    creds = Credentials.from_authorized_user_file(str(PROJECT_ROOT / "token.json"))
    service = build('gmail', 'v1', credentials=creds)
    
    message = MIMEMultipart()
    message['to'] = to_email
    message['from'] = 'ira@example-company.org'
    message['subject'] = f"Re: {subject}" if not subject.startswith("Re:") else subject
    message.attach(MIMEText(reply, 'plain'))
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service.users().messages().send(
        userId='me',
        body={'raw': raw, 'threadId': thread_id}
    ).execute()
    
    return sent


def main():
    """Process the most recent unread email from the founder."""
    print("\n" + "=" * 60)
    print("IRA DEEP REPLY SYSTEM")
    print("Taking time for thorough technical research...")
    print("=" * 60 + "\n")
    
    # Get latest email
    creds = Credentials.from_authorized_user_file(str(PROJECT_ROOT / "token.json"))
    service = build('gmail', 'v1', credentials=creds)
    
    results = service.users().messages().list(
        userId='me',
        q='from:founder@example-company.org newer_than:2h is:unread',
        maxResults=1
    ).execute()
    
    messages = results.get('messages', [])
    if not messages:
        print("No unread messages from the founder.")
        return
    
    # Get message details
    msg = service.users().messages().get(
        userId='me',
        id=messages[0]['id'],
        format='full'
    ).execute()
    
    headers = {h['name']: h['value'] for h in msg['payload']['headers']}
    thread_id = msg['threadId']
    
    # Extract body
    def get_body(payload):
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
        return ''
    
    body = get_body(msg['payload'])
    # Clean body
    clean_body = body.split('With Best Regards')[0].split('Best Regards')[0].strip()
    clean_body = clean_body.split('\nOn ')[0].strip()
    
    print(f"Query from the founder:")
    print(f"  {clean_body[:200]}...")
    print()
    
    # Do deep research
    researcher = DeepResearcher()
    reply, metadata = researcher.research_and_reply(clean_body)
    
    print("\n" + "=" * 60)
    print("GENERATED REPLY:")
    print("=" * 60)
    print(reply)
    print("=" * 60 + "\n")
    
    # Send
    sent = send_reply(
        reply,
        thread_id,
        headers.get('From', 'founder@example-company.org'),
        headers.get('Subject', 'Technical Inquiry')
    )
    
    # Mark as read
    service.users().messages().modify(
        userId='me',
        id=messages[0]['id'],
        body={'removeLabelIds': ['UNREAD']}
    ).execute()
    
    print(f"✅ Reply sent! Message ID: {sent['id']}")
    print(f"   Machines researched: {metadata['machines_found']}")
    print(f"   Documents searched: {metadata['docs_searched']}")


if __name__ == "__main__":
    main()
