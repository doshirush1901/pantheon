#!/usr/bin/env python3
"""
IRA'S DREAM MODE - Unified Deep Learning System
================================================

FIXED VERSION - Now properly integrated with:
- Qdrant (for RAG retrieval)
- UnifiedMemory (Mem0 + PostgreSQL)
- Centralized config
- Conflict detection
- DocumentIngestor (shared extraction)
- Memory Consolidation (learn from conversations)

Every night, Ira enters "dream mode" where she:

Phase 1: SCAN & PRIORITIZE
    - Identify new/changed documents
    - Prioritize: Technical docs > Presentations > Emails

Phase 2: DEEP EXTRACTION
    - Extract facts, relationships, and insights
    - Use shared DocumentIngestor logic
    - Detect conflicts with existing knowledge

Phase 3: UNIFIED STORAGE
    - Store in Mem0 (semantic search)
    - Index in Qdrant (RAG retrieval)  <-- Dream knowledge now searchable!
    - Queue conflicts for clarification

Phase 4: GRAPH CONSOLIDATION
    - Analyze daily interactions
    - Strengthen/weaken relationships based on usage
    - Reorganize clusters based on co-access patterns

Phase 5: PRICE CONFLICT CHECK
    - Detect pricing inconsistencies
    - Notify Rushabh of conflicts

Phase 6: CONVERSATION QUALITY ANALYSIS
    - Identify queries with poor retrieval scores
    - Find knowledge gaps from user questions

Phase 7: LEARN FROM CORRECTIONS
    - Process explicit corrections from Rushabh
    - Reinforce corrected knowledge

Phase 7.5: MEMORY CONSOLIDATION (NEW!)
    - Review episodic memories (conversations) from past week
    - Extract recurring patterns across interactions
    - Synthesize into generalized knowledge:
      * Semantic facts ("Automotive dashboards are a common PF1 application")
      * Procedural memories ("handle_shipping_query" workflow)
      * Knowledge graph updates ("PF1-Series" --used_for--> "Automotive")
    - This is the core learning loop - IRA continuously improves!

Phase 8: INTERACTION LEARNING
    - Extract learnings from Telegram/email conversations
    - Store corrections and new facts

Phase 9: FOLLOW-UP AUTOMATION
    - Check for stale quotes
    - Generate follow-up suggestions

Phase 10: MORNING SUMMARY
    - Send Telegram report of overnight learning

Usage:
    python dream_mode.py              # Normal dream
    python dream_mode.py --deep       # Deep learning on all topics
    python dream_mode.py --force      # Reprocess all documents
    python dream_mode.py --status     # Show dream statistics
"""

import os
import sys
import json
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum

# =============================================================================
# IMPORTS - Use centralized config
# =============================================================================

BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

# ALWAYS load env first to ensure correct API keys
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # Always override API keys from .env
            if key.endswith(("_API_KEY", "_KEY", "_TOKEN", "_URL")):
                os.environ[key] = value
            elif not os.environ.get(key):
                os.environ[key] = value

try:
    from config import (
        QDRANT_URL, QDRANT_TIMEOUT, COLLECTIONS, EMBEDDING_MODEL_VOYAGE,
        get_embedding_dimension, TIMEOUTS, get_logger,
    )
    CONFIG_LOADED = True
    logger = get_logger("dream_mode")
except ImportError:
    CONFIG_LOADED = False
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("dream_mode")
    
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    QDRANT_TIMEOUT = 30
    COLLECTIONS = {"dream_knowledge": "ira_dream_knowledge_v1"}
    EMBEDDING_MODEL_VOYAGE = "voyage-3"
    TIMEOUTS = {"qdrant_query": 30}
    
    def get_embedding_dimension(model):
        return {"voyage-3": 1024, "text-embedding-3-large": 3072}.get(model, 1024)

# Get API keys from env (after loading)
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
MEM0_API_KEY = os.environ.get("MEM0_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Memory Controller - Intelligent memory routing (NEW)
try:
    sys.path.insert(0, str(SKILLS_DIR / "memory"))
    from memory_controller import remember, get_memory_controller
    MEMORY_CONTROLLER_AVAILABLE = True
except ImportError:
    MEMORY_CONTROLLER_AVAILABLE = False
    logger.warning("Memory controller not available")

# Memory Consolidator - Learn from conversations (NEW)
try:
    from memory_consolidator import MemoryConsolidator, run_memory_consolidation
    MEMORY_CONSOLIDATOR_AVAILABLE = True
except ImportError:
    MEMORY_CONSOLIDATOR_AVAILABLE = False
    logger.warning("Memory consolidator not available")

# Shared Document Extractor
try:
    from document_extractor import extract_document, get_extractor
    EXTRACTOR_AVAILABLE = True
except ImportError:
    EXTRACTOR_AVAILABLE = False
    logger.warning("Document extractor not available, using fallback")

# Paths
IMPORTS_DIR = PROJECT_ROOT / "data" / "imports"
WORKSPACE_DIR = PROJECT_ROOT / "openclaw/agents/ira/workspace"
DREAM_STATE_FILE = WORKSPACE_DIR / "dream_state.json"
DREAM_JOURNAL_FILE = WORKSPACE_DIR / "dream_journal.json"

# Collection for dream knowledge
DREAM_COLLECTION = COLLECTIONS.get("dream_knowledge", "ira_dream_knowledge_v1")


class DocumentPriority(Enum):
    """Document priority for learning."""
    CRITICAL = 1    # Technical manuals, spec sheets
    HIGH = 2        # Presentations, guides
    MEDIUM = 3      # Customer communications, quotes
    LOW = 4         # General emails
    SKIP = 5        # Receipts, spam


@dataclass
class DreamInsight:
    """An insight generated during dreaming."""
    insight: str
    source_docs: List[str]
    confidence: float
    topic: str
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class DocumentKnowledge:
    """Knowledge extracted from a document."""
    filename: str
    file_hash: str
    priority: DocumentPriority
    extracted_at: datetime
    facts: List[str]
    topics: List[str]
    key_terms: Dict[str, str]
    relationships: List[Dict[str, str]]
    insights: List[str] = field(default_factory=list)
    questions_raised: List[str] = field(default_factory=list)


@dataclass 
class DreamState:
    """State of Ira's dream learning."""
    last_dream: Optional[datetime] = None
    documents_processed: Dict[str, str] = field(default_factory=dict)
    total_facts_learned: int = 0
    total_indexed_in_qdrant: int = 0  # NEW: Track Qdrant indexing
    topics_covered: Set[str] = field(default_factory=set)
    knowledge_graph: Dict[str, List[str]] = field(default_factory=dict)
    insights_generated: int = 0
    knowledge_gaps: List[Dict] = field(default_factory=list)
    conflicts_detected: int = 0  # NEW: Track conflicts


class IntegratedDreamMode:
    """
    Ira's dream mode - NOW PROPERLY INTEGRATED.
    
    Key fixes:
    1. Stores to Qdrant (searchable via RAG)
    2. Uses UnifiedMemory (Mem0 + PostgreSQL fallback)
    3. Uses centralized config
    4. Detects conflicts
    """
    
    DOC_PRIORITY_PATTERNS = {
        DocumentPriority.CRITICAL: [
            r'technical', r'manual', r'specification', r'frimo', r'technology',
            r'machine.*guide', r'catalogue', r'catalog', r'brochure'
        ],
        DocumentPriority.HIGH: [
            r'presentation', r'overview', r'strategy', r'market.*research',
            r'industry.*report', r'analysis', r'whitepaper'
        ],
        DocumentPriority.MEDIUM: [
            r'quote', r'quotation', r'offer', r'proposal', r'inquiry'
        ],
        DocumentPriority.LOW: [
            r'gmail', r'email', r'message', r'reply', r'forward'
        ],
        DocumentPriority.SKIP: [
            r'receipt', r'invoice', r'payment', r'subscription', r'unsubscribe'
        ],
    }
    
    def __init__(self):
        self.state = self._load_state()
        self._qdrant = None
        self._voyage = None
        self._mem0 = None
        self._unified_memory = None
        self._openai = None
    
    # =========================================================================
    # LAZY INITIALIZATION
    # =========================================================================
    
    def _get_qdrant(self):
        """Get Qdrant client (lazy init)."""
        if self._qdrant is None:
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.models import Distance, VectorParams
                
                self._qdrant = QdrantClient(url=QDRANT_URL, timeout=QDRANT_TIMEOUT)
                
                # Ensure dream collection exists
                collections = [c.name for c in self._qdrant.get_collections().collections]
                if DREAM_COLLECTION not in collections:
                    logger.info(f"Creating Qdrant collection: {DREAM_COLLECTION}")
                    self._qdrant.create_collection(
                        collection_name=DREAM_COLLECTION,
                        vectors_config=VectorParams(
                            size=get_embedding_dimension(EMBEDDING_MODEL_VOYAGE),
                            distance=Distance.COSINE
                        )
                    )
            except Exception as e:
                logger.warning(f"Qdrant unavailable: {e}")
        return self._qdrant
    
    def _get_voyage(self):
        """Get Voyage client for embeddings."""
        if self._voyage is None and VOYAGE_API_KEY:
            try:
                import voyageai
                self._voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
            except Exception as e:
                logger.warning(f"Voyage unavailable: {e}")
        return self._voyage
    
    def _get_mem0(self):
        """Get Mem0 client."""
        if self._mem0 is None and MEM0_API_KEY:
            try:
                from mem0 import MemoryClient
                self._mem0 = MemoryClient(api_key=MEM0_API_KEY)
            except Exception as e:
                logger.warning(f"Mem0 unavailable: {e}")
        return self._mem0
    
    def _get_unified_memory(self):
        """Get UnifiedMemory service (now uses UnifiedMem0Service)."""
        if self._unified_memory is None:
            try:
                from ..memory.unified_mem0 import get_unified_mem0
                self._unified_memory = get_unified_mem0()
            except ImportError:
                try:
                    memory_dir = SKILLS_DIR / "memory"
                    sys.path.insert(0, str(memory_dir))
                    from unified_mem0 import get_unified_mem0
                    self._unified_memory = get_unified_mem0()
                except Exception as e:
                    logger.warning(f"UnifiedMem0 unavailable: {e}")
        return self._unified_memory
    
    def _get_openai(self):
        """Get OpenAI client."""
        if self._openai is None and OPENAI_API_KEY:
            import openai
            self._openai = openai.OpenAI(api_key=OPENAI_API_KEY)
        return self._openai
    
    # =========================================================================
    # STATE MANAGEMENT
    # =========================================================================
    
    def _load_state(self) -> DreamState:
        """Load dream state from disk."""
        if DREAM_STATE_FILE.exists():
            try:
                data = json.loads(DREAM_STATE_FILE.read_text())
                return DreamState(
                    last_dream=datetime.fromisoformat(data["last_dream"]) if data.get("last_dream") else None,
                    documents_processed=data.get("documents_processed", {}),
                    total_facts_learned=data.get("total_facts_learned", 0),
                    total_indexed_in_qdrant=data.get("total_indexed_in_qdrant", 0),
                    topics_covered=set(data.get("topics_covered", [])),
                    knowledge_graph=data.get("knowledge_graph", {}),
                    insights_generated=data.get("insights_generated", 0),
                    knowledge_gaps=data.get("knowledge_gaps", []),
                    conflicts_detected=data.get("conflicts_detected", 0),
                )
            except Exception as e:
                logger.warning(f"State load error: {e}")
        return DreamState()
    
    def _save_state(self):
        """Save dream state to disk."""
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "last_dream": self.state.last_dream.isoformat() if self.state.last_dream else None,
            "documents_processed": self.state.documents_processed,
            "total_facts_learned": self.state.total_facts_learned,
            "total_indexed_in_qdrant": self.state.total_indexed_in_qdrant,
            "topics_covered": list(self.state.topics_covered),
            "knowledge_graph": self.state.knowledge_graph,
            "insights_generated": self.state.insights_generated,
            "knowledge_gaps": self.state.knowledge_gaps,
            "conflicts_detected": self.state.conflicts_detected,
        }
        DREAM_STATE_FILE.write_text(json.dumps(data, indent=2))
    
    # =========================================================================
    # DOCUMENT DISCOVERY
    # =========================================================================
    
    def _classify_document(self, path: Path) -> DocumentPriority:
        """Classify document priority based on filename."""
        import re
        filename = path.stem.lower()
        
        for priority, patterns in self.DOC_PRIORITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, filename, re.IGNORECASE):
                    return priority
        
        if path.suffix.lower() == ".pdf":
            return DocumentPriority.MEDIUM
        return DocumentPriority.LOW
    
    def _get_file_hash(self, path: Path) -> str:
        """Get file hash for change detection."""
        try:
            return hashlib.md5(path.read_bytes()).hexdigest()[:16]
        except (IOError, OSError):
            return ""
    
    def _find_documents(self, force_all: bool = False) -> List[Tuple[Path, DocumentPriority]]:
        """Find documents to process."""
        docs = []
        
        if not IMPORTS_DIR.exists():
            logger.warning(f"Imports directory not found: {IMPORTS_DIR}")
            return docs
        
        for pattern in ["**/*.pdf", "**/*.docx", "**/*.txt", "**/*.md", "**/*.pptx"]:
            for path in IMPORTS_DIR.glob(pattern):
                try:
                    priority = self._classify_document(path)
                    if priority == DocumentPriority.SKIP:
                        continue
                    
                    file_hash = self._get_file_hash(path)
                    prev_hash = self.state.documents_processed.get(str(path))
                    
                    if force_all or prev_hash != file_hash:
                        docs.append((path, priority))
                except Exception as e:
                    logger.debug(f"Error checking {path}: {e}")
        
        # Sort by priority (critical first)
        docs.sort(key=lambda x: x[1].value)
        return docs
    
    # =========================================================================
    # CONTENT EXTRACTION
    # =========================================================================
    
    def _extract_content(self, path: Path) -> str:
        """Extract text from document using shared DocumentExtractor."""
        # Use shared extractor if available (handles PDF, DOCX, XLSX, PPTX, TXT, CSV)
        if EXTRACTOR_AVAILABLE:
            text = extract_document(path)
            if text:
                return text
        
        # Fallback if extractor unavailable
        suffix = path.suffix.lower()
        
        if suffix == ".pdf":
            try:
                import pdfplumber
                text_parts = []
                with pdfplumber.open(str(path)) as pdf:
                    for page in pdf.pages[:50]:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                return "\n".join(text_parts)
            except Exception as e:
                logger.warning(f"PDF error {path.name}: {e}")
                return ""
        
        elif suffix in [".txt", ".md"]:
            try:
                return path.read_text(errors="ignore")
            except (IOError, OSError, UnicodeDecodeError):
                return ""
        
        return ""
    
    def _detect_document_type(self, filename: str, content: str) -> str:
        """Detect document type for specialized extraction."""
        filename_lower = filename.lower()
        content_lower = content[:2000].lower()
        
        if "quote" in filename_lower or "quotation" in filename_lower or "offer" in filename_lower:
            return "quote"
        elif "inquiry" in filename_lower or "rfq" in filename_lower or "enquiry" in content_lower:
            return "inquiry"
        elif "spec" in filename_lower or "technical" in filename_lower:
            return "technical_spec"
        elif "price" in filename_lower or "pricing" in content_lower:
            return "pricing"
        elif "lead" in filename_lower or "contact" in filename_lower:
            return "contacts"
        elif any(x in filename_lower for x in ["catalog", "brochure", "presentation"]):
            return "marketing"
        else:
            return "general"
    
    def _extract_knowledge(self, content: str, filename: str, priority: DocumentPriority) -> DocumentKnowledge:
        """Extract structured knowledge using LLM with document-type awareness."""
        client = self._get_openai()
        if not client:
            return DocumentKnowledge(
                filename=filename, file_hash="", priority=priority,
                extracted_at=datetime.now(), facts=[], topics=[],
                key_terms={}, relationships=[]
            )
        
        # Detect document type for specialized extraction
        doc_type = self._detect_document_type(filename, content)
        
        # Adjust depth based on priority
        max_content = {
            DocumentPriority.CRITICAL: 20000,
            DocumentPriority.HIGH: 15000,
            DocumentPriority.MEDIUM: 10000,
        }.get(priority, 8000)
        
        content = content[:max_content]
        
        # Build specialized extraction prompt based on document type
        type_specific_instructions = self._get_type_specific_instructions(doc_type)
        
        prompt = f"""Analyze this document for Ira (AI sales assistant for Machinecraft thermoforming machines).

Document: {filename}
Document Type: {doc_type}
Priority: {priority.name}

Content:
{content}

Extract the following information:

## STANDARD EXTRACTION
1. FACTS: Specific, concrete information (numbers, specs, names, dates)
2. TOPICS: Main topics covered
3. KEY_TERMS: Important terms with definitions
4. RELATIONSHIPS: How concepts connect ("X is used for Y", "X requires Y")
5. INSIGHTS: Non-obvious conclusions
6. QUESTIONS: What this document doesn't answer

## STRUCTURED DATA EXTRACTION
{type_specific_instructions}

Return JSON:
{{
  "facts": ["fact 1", "fact 2", ...],
  "topics": ["topic1", "topic2", ...],
  "key_terms": {{"term": "definition", ...}},
  "relationships": [{{"subject": "...", "relation": "...", "object": "..."}}],
  "insights": ["insight 1", ...],
  "questions": ["question 1", ...],
  "structured_data": {{
    "contacts": [{{"name": "...", "email": "...", "company": "...", "phone": "...", "role": "..."}}],
    "machines": [{{"model": "...", "forming_size": "...", "price_inr": null, "price_usd": null, "lead_time": "..."}}],
    "pricing": [{{"item": "...", "price": ..., "currency": "...", "conditions": "..."}}],
    "requirements": [{{"requirement": "...", "material": "...", "application": "...", "quantity": "..."}}],
    "dates": [{{"event": "...", "date": "...", "status": "..."}}]
  }}
}}

Only include structured_data fields that are present in the document. Use null for unknown values."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract knowledge as JSON only. Be thorough with structured data."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,
                temperature=0.2,
            )
            
            text = response.choices[0].message.content
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            result = json.loads(text)
            
            # Process structured data into additional facts
            structured_facts = self._process_structured_data(result.get("structured_data", {}))
            all_facts = result.get("facts", []) + structured_facts
            
            knowledge = DocumentKnowledge(
                filename=filename,
                file_hash=hashlib.md5(content.encode()).hexdigest()[:16],
                priority=priority,
                extracted_at=datetime.now(),
                facts=all_facts,
                topics=result.get("topics", []),
                key_terms=result.get("key_terms", {}),
                relationships=result.get("relationships", []),
                insights=result.get("insights", []),
                questions_raised=result.get("questions", []),
            )
            
            # Store contacts in identity service
            self._store_extracted_contacts(result.get("structured_data", {}).get("contacts", []))
            
            return knowledge
            
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return DocumentKnowledge(
                filename=filename, file_hash="", priority=priority,
                extracted_at=datetime.now(), facts=[], topics=[],
                key_terms={}, relationships=[]
            )
    
    def _get_type_specific_instructions(self, doc_type: str) -> str:
        """Get document-type specific extraction instructions."""
        instructions = {
            "quote": """
For QUOTE documents, extract:
- Customer contact details (name, email, company)
- Machine model and specifications
- All pricing (base price, options, total)
- Payment terms and delivery timeline
- Quote validity period""",
            
            "inquiry": """
For INQUIRY documents, extract:
- Customer/prospect contact details
- Requested machine specifications
- Materials to be processed
- Application/industry
- Budget if mentioned
- Timeline/urgency""",
            
            "technical_spec": """
For TECHNICAL documents, extract:
- Machine model numbers
- Forming area sizes
- Power requirements (kW, voltage)
- Cycle times
- Features and options
- Weight and dimensions""",
            
            "pricing": """
For PRICING documents, extract:
- All machine models with prices
- Price currency (INR/USD/EUR)
- Optional extras with prices
- Discount conditions
- Price validity dates""",
            
            "contacts": """
For CONTACT/LEAD documents, extract:
- All names and their roles
- Email addresses
- Phone numbers
- Company names
- Source/event where contact was made
- Interest level or status""",
            
            "marketing": """
For MARKETING documents, extract:
- Product features and benefits
- Competitive advantages
- Target applications
- Customer testimonials
- Key selling points""",
        }
        
        return instructions.get(doc_type, """
Extract any:
- Contact information (names, emails, companies)
- Machine specifications (models, sizes, prices)
- Dates and timelines
- Requirements or specifications""")
    
    def _process_structured_data(self, structured: Dict) -> List[str]:
        """Convert structured data into searchable facts."""
        facts = []
        
        # Process contacts
        for contact in structured.get("contacts", []):
            if contact.get("name") and contact.get("email"):
                fact = f"Contact: {contact['name']}"
                if contact.get("company"):
                    fact += f" from {contact['company']}"
                if contact.get("role"):
                    fact += f" ({contact['role']})"
                fact += f" - email: {contact['email']}"
                if contact.get("phone"):
                    fact += f", phone: {contact['phone']}"
                facts.append(fact)
        
        # Process machines
        for machine in structured.get("machines", []):
            if machine.get("model"):
                fact = f"Machine {machine['model']}"
                if machine.get("forming_size"):
                    fact += f" forming size {machine['forming_size']}"
                if machine.get("price_inr"):
                    fact += f" price ₹{machine['price_inr']:,}"
                if machine.get("price_usd"):
                    fact += f" (${machine['price_usd']:,})"
                if machine.get("lead_time"):
                    fact += f" lead time: {machine['lead_time']}"
                facts.append(fact)
        
        # Process pricing
        for price in structured.get("pricing", []):
            if price.get("item") and price.get("price"):
                fact = f"Price: {price['item']} = {price.get('currency', 'INR')} {price['price']}"
                if price.get("conditions"):
                    fact += f" ({price['conditions']})"
                facts.append(fact)
        
        # Process requirements
        for req in structured.get("requirements", []):
            if req.get("requirement"):
                fact = f"Requirement: {req['requirement']}"
                if req.get("material"):
                    fact += f" for {req['material']}"
                if req.get("application"):
                    fact += f" ({req['application']})"
                facts.append(fact)
        
        # Process dates
        for date in structured.get("dates", []):
            if date.get("event") and date.get("date"):
                fact = f"Date: {date['event']} on {date['date']}"
                if date.get("status"):
                    fact += f" ({date['status']})"
                facts.append(fact)
        
        return facts
    
    def _store_extracted_contacts(self, contacts: List[Dict]) -> None:
        """Store extracted contacts in the identity service."""
        if not contacts:
            return
        
        try:
            sys.path.insert(0, str(SKILLS_DIR / "identity"))
            from unified_identity import get_identity_service
            identity_svc = get_identity_service()
            
            for contact in contacts:
                if not contact.get("email"):
                    continue
                
                # Check if contact exists
                contact_id = identity_svc.resolve("email", contact["email"])
                
                if not contact_id:
                    # Create new contact
                    identity_svc.create_contact(
                        email=contact["email"],
                        name=contact.get("name"),
                        company=contact.get("company"),
                        phone=contact.get("phone"),
                    )
                    logger.debug(f"Created contact: {contact.get('name')} <{contact['email']}>")
        except Exception as e:
            logger.debug(f"Contact storage error (non-fatal): {e}")
    
    # =========================================================================
    # UNIFIED STORAGE (THE KEY FIX!)
    # =========================================================================
    
    def _store_in_qdrant(self, text: str, metadata: dict) -> bool:
        """Store knowledge in Qdrant for RAG retrieval."""
        qdrant = self._get_qdrant()
        voyage = self._get_voyage()
        
        if not qdrant or not voyage:
            return False
        
        try:
            # Generate embedding
            embedding = voyage.embed([text], model=EMBEDDING_MODEL_VOYAGE, input_type="document").embeddings[0]
            
            # Create unique ID
            point_id = uuid.uuid4().hex
            
            # Upsert to Qdrant
            from qdrant_client.models import PointStruct
            
            qdrant.upsert(
                collection_name=DREAM_COLLECTION,
                points=[PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": text,
                        "raw_text": text,
                        "source": "dream_learning",
                        "indexed_at": datetime.now().isoformat(),
                        **metadata
                    }
                )]
            )
            return True
        except Exception as e:
            logger.error(f"Qdrant store error: {e}")
            return False
    
    def _store_in_mem0(self, text: str, metadata: dict) -> bool:
        """Store in Mem0 for semantic memory via Memory Controller."""
        # Try Memory Controller first (intelligent routing)
        if MEMORY_CONTROLLER_AVAILABLE:
            try:
                # Determine if this is entity knowledge
                entity_name = None
                entity_type = metadata.get("entity_type")
                if entity_type == "product":
                    # Extract product name from text
                    import re
                    match = re.search(r'(EcoForm|ThermoLine|PF\d+)\s*(\d*)', text)
                    if match:
                        entity_name = match.group(0)
                
                result = remember(
                    content=text,
                    source="dream",
                    entity_name=entity_name,
                    context={
                        "metadata": metadata,
                        "is_learned": True,
                    }
                )
                
                if result.get("action") in ["create", "reinforce"]:
                    return True
                elif result.get("action") == "ignore":
                    # Already known, but that's okay
                    return True
                elif result.get("action") == "conflict":
                    self.state.conflicts_detected += 1
                    return True
                return False
                
            except Exception as e:
                logger.warning(f"MemController error: {e}, falling back to Mem0")
        
        # Fallback: Direct Mem0
        mem0 = self._get_mem0()
        if not mem0:
            return False
        
        try:
            mem0.add(
                messages=[{"role": "user", "content": text}],
                user_id="system_ira",
                metadata={
                    "source": "dream_learning",
                    **metadata
                }
            )
            return True
        except Exception as e:
            logger.error(f"Mem0 store error: {e}")
            return False
    
    def _store_knowledge_unified(self, knowledge: DocumentKnowledge) -> Tuple[int, int]:
        """
        Store knowledge in BOTH Qdrant AND Mem0.
        
        This is the key fix - dream knowledge is now searchable!
        """
        stored_mem0 = 0
        stored_qdrant = 0
        
        metadata_base = {
            "document": knowledge.filename,
            "priority": knowledge.priority.name,
            "topics": knowledge.topics[:5],
        }
        
        # Store facts (most important)
        for fact in knowledge.facts[:25]:
            metadata = {**metadata_base, "type": "fact"}
            
            if self._store_in_qdrant(fact, metadata):
                stored_qdrant += 1
            if self._store_in_mem0(fact, metadata):
                stored_mem0 += 1
        
        # Store definitions
        for term, definition in list(knowledge.key_terms.items())[:15]:
            text = f"DEFINITION: {term} - {definition}"
            metadata = {**metadata_base, "type": "definition", "term": term}
            
            if self._store_in_qdrant(text, metadata):
                stored_qdrant += 1
            if self._store_in_mem0(text, metadata):
                stored_mem0 += 1
        
        # Store relationships
        for rel in knowledge.relationships[:15]:
            text = f"{rel.get('subject', '')} {rel.get('relation', '')} {rel.get('object', '')}"
            metadata = {**metadata_base, "type": "relationship"}
            
            if self._store_in_qdrant(text, metadata):
                stored_qdrant += 1
            if self._store_in_mem0(text, metadata):
                stored_mem0 += 1
            
            # Update knowledge graph
            subj = rel.get('subject', '').lower()
            obj = rel.get('object', '').lower()
            if subj and obj:
                if subj not in self.state.knowledge_graph:
                    self.state.knowledge_graph[subj] = []
                if obj not in self.state.knowledge_graph[subj]:
                    self.state.knowledge_graph[subj].append(obj)
        
        # Store insights
        for insight in knowledge.insights[:5]:
            text = f"INSIGHT: {insight}"
            metadata = {**metadata_base, "type": "insight"}
            
            if self._store_in_qdrant(text, metadata):
                stored_qdrant += 1
            if self._store_in_mem0(text, metadata):
                stored_mem0 += 1
            self.state.insights_generated += 1
        
        return stored_mem0, stored_qdrant
    
    # =========================================================================
    # REFLECTION & INSIGHTS
    # =========================================================================
    
    def _generate_cross_document_insights(self, all_knowledge: List[DocumentKnowledge]) -> List[DreamInsight]:
        """Generate insights by connecting knowledge from multiple documents."""
        if len(all_knowledge) < 2:
            return []
        
        client = self._get_openai()
        if not client:
            return []
        
        # Compile facts
        all_facts = []
        all_topics = set()
        for k in all_knowledge:
            all_facts.extend(k.facts[:10])
            all_topics.update(k.topics)
        
        if not all_facts:
            return []
        
        prompt = f"""You are Ira's "dreaming brain". Generate insights by connecting knowledge from multiple documents.

Knowledge learned:
{chr(10).join(f'- {f}' for f in all_facts[:30])}

Topics: {', '.join(list(all_topics)[:15])}

Generate:
1. 3-5 NEW INSIGHTS by connecting facts from different documents
2. 2-3 KNOWLEDGE GAPS - things Ira should learn

Return JSON:
{{
  "insights": [{{"insight": "...", "confidence": 0.8, "topic": "..."}}],
  "knowledge_gaps": [{{"topic": "...", "question": "...", "importance": 0.9}}]
}}"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Generate insights as JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7,
            )
            
            result = json.loads(response.choices[0].message.content)
            
            insights = [
                DreamInsight(
                    insight=i["insight"],
                    source_docs=[k.filename for k in all_knowledge[:3]],
                    confidence=i.get("confidence", 0.7),
                    topic=i.get("topic", "general"),
                )
                for i in result.get("insights", [])
            ]
            
            self.state.knowledge_gaps = result.get("knowledge_gaps", [])[:10]
            
            # Store insights in Qdrant too
            for insight in insights:
                self._store_in_qdrant(
                    f"CROSS-DOC INSIGHT: {insight.insight}",
                    {"type": "cross_document_insight", "topic": insight.topic}
                )
            
            return insights
        except Exception as e:
            logger.error(f"Insight generation error: {e}")
            return []
    
    # =========================================================================
    # GRAPH CONSOLIDATION (NEW!)
    # =========================================================================
    
    def _consolidate_knowledge_graph(self) -> Dict[str, Any]:
        """
        Consolidate knowledge graph based on daily interactions.
        
        This is like human memory consolidation during sleep:
        - Reviews what was accessed today
        - Strengthens useful connections
        - Weakens unused connections
        - Reorganizes clusters
        """
        try:
            from graph_consolidation import GraphConsolidator
            
            consolidator = GraphConsolidator(verbose=False)
            result = consolidator.consolidate(days=1)
            
            logger.info(f"Interactions analyzed: {result.interactions_analyzed}")
            logger.info(f"Edges: +{result.edges_strengthened} strengthened, -{result.edges_weakened} decayed")
            if result.edges_created > 0:
                logger.info(f"New connections discovered: {result.edges_created}")
            if result.clusters_reorganized > 0:
                logger.info(f"Clusters reorganized: {result.clusters_reorganized}")
            if result.knowledge_gaps:
                logger.info(f"Knowledge gaps found: {len(result.knowledge_gaps)}")
            
            return {
                "interactions": result.interactions_analyzed,
                "edges_strengthened": result.edges_strengthened,
                "edges_weakened": result.edges_weakened,
                "edges_created": result.edges_created,
                "knowledge_gaps": len(result.knowledge_gaps),
            }
            
        except ImportError as e:
            logger.warning(f"Graph consolidation not available: {e}")
            return {}
        except Exception as e:
            logger.warning(f"Graph consolidation error: {e}")
            return {}
    
    def _check_price_conflicts(self) -> Dict[str, Any]:
        """
        Check for price conflicts and notify Rushabh if any found.
        
        Detects:
        - Same model with different prices from different quotes
        - Price mismatches between database and quotes
        """
        try:
            from pricing_learner import PricingLearner
            
            learner = PricingLearner(verbose=False)
            
            learner.scan_knowledge()
            
            conflicts = learner.get_pending_conflicts()
            
            if conflicts:
                logger.warning(f"Found {len(conflicts)} price conflicts")
                for c in conflicts[:3]:
                    model = c["machine_model"]
                    variance = c["variance_percent"]
                    logger.warning(f"Price conflict - {model}: {variance}% variance")
                
                sent = learner.send_conflicts_notification()
                if sent:
                    logger.info("Notification sent to Rushabh via Telegram")
                
                return {
                    "conflicts_found": len(conflicts),
                    "notification_sent": sent,
                }
            else:
                logger.info("No price conflicts detected")
                return {"conflicts_found": 0}
            
        except ImportError as e:
            logger.warning(f"Pricing learner not available: {e}")
            return {}
        except Exception as e:
            logger.warning(f"Price conflict check error: {e}")
            return {}
    
    def _analyze_conversation_quality(self) -> Dict[str, Any]:
        """
        NEW: Analyze today's conversations to identify learning opportunities.
        
        Finds:
        - Queries with low retrieval scores (knowledge gaps)
        - Follow-up questions (indicates incomplete first answer)
        - Unanswered questions
        """
        result = {
            "conversations_reviewed": 0,
            "poor_retrievals": [],
            "follow_up_patterns": [],
            "lessons": [],
        }
        
        try:
            # Read from request log
            requests_log = PROJECT_ROOT / "crm" / "logs" / "requests.jsonl"
            if not requests_log.exists():
                logger.debug("No conversation log found")
                return result
            
            from datetime import timedelta
            cutoff = datetime.now() - timedelta(days=1)
            
            conversations = []
            with open(requests_log, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        ts_str = record.get("timestamp", "")
                        if ts_str:
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            if ts.replace(tzinfo=None) >= cutoff:
                                conversations.append(record)
                    except (json.JSONDecodeError, ValueError):
                        continue
            
            result["conversations_reviewed"] = len(conversations)
            
            # Find poor retrievals (low scores or no results)
            for conv in conversations:
                query = conv.get("query", conv.get("message_preview", ""))
                scores = conv.get("retrieval_scores", [])
                citations = conv.get("citations", [])
                
                if not query:
                    continue
                
                # Low score indicates poor knowledge match
                if scores and max(scores) < 0.4:
                    result["poor_retrievals"].append({
                        "query": query[:100],
                        "max_score": max(scores),
                        "topic": self._extract_topic(query),
                    })
                
                # No citations means no relevant knowledge found
                elif not citations and len(query) > 20:
                    result["poor_retrievals"].append({
                        "query": query[:100],
                        "max_score": 0,
                        "topic": self._extract_topic(query),
                    })
            
            # Generate lessons from poor retrievals
            if result["poor_retrievals"]:
                logger.info(f"Found {len(result['poor_retrievals'])} queries with poor knowledge matches")
                
                # Group by topic
                topics = {}
                for pr in result["poor_retrievals"]:
                    topic = pr.get("topic", "general")
                    if topic not in topics:
                        topics[topic] = []
                    topics[topic].append(pr["query"])
                
                # Create lessons
                for topic, queries in list(topics.items())[:5]:
                    lesson = f"Knowledge gap in '{topic}': Need better coverage for queries like '{queries[0][:50]}'"
                    result["lessons"].append(lesson)
                    logger.info(f"Lesson: {lesson[:70]}...")
                
                # Store lessons as knowledge gaps
                for topic, queries in topics.items():
                    self.state.knowledge_gaps.append({
                        "topic": topic,
                        "question": f"Improve knowledge coverage for: {queries[0][:100]}",
                        "importance": 0.8,
                        "source": "conversation_analysis",
                    })
            else:
                logger.info("All conversations had good knowledge matches")
            
            return result
            
        except Exception as e:
            logger.warning(f"Conversation analysis error: {e}")
            return result
    
    def _extract_topic(self, query: str) -> str:
        """Extract main topic from a query."""
        query_lower = query.lower()
        
        # Check for machine models
        import re
        model_match = re.search(r'(pf1|pf2|am|fcs|img)[-\s]?[a-z]?[-\s]?\d+', query_lower)
        if model_match:
            return model_match.group(0).upper().replace(" ", "-")
        
        # Check for common topics
        topic_keywords = {
            "pricing": ["price", "cost", "budget", "quote", "₹", "$", "inr", "usd"],
            "specifications": ["spec", "dimension", "size", "capacity", "power"],
            "delivery": ["delivery", "lead time", "shipping", "timeline"],
            "warranty": ["warranty", "guarantee", "support", "service"],
            "comparison": ["compare", "difference", "vs", "better", "which"],
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return topic
        
        return "general"
    
    def _learn_from_corrections(self) -> Dict[str, Any]:
        """
        NEW: Check for any corrections Rushabh made and learn from them.
        """
        result = {
            "corrections_found": 0,
            "lessons_learned": [],
        }
        
        try:
            from feedback_learner import FeedbackLearner
            
            learner = FeedbackLearner()
            past_corrections = learner.get_past_corrections()
            
            if past_corrections:
                result["corrections_found"] = len(past_corrections)
                logger.info(f"Found {len(past_corrections)} past corrections to reinforce")
                
                # Reinforce corrections by re-storing them
                for corr in past_corrections[:5]:
                    memory_text = corr.get("memory", "")
                    if memory_text:
                        # Store correction reinforcement in Qdrant
                        self._store_in_qdrant(
                            f"CORRECTION REINFORCEMENT: {memory_text[:500]}",
                            {"type": "correction", "reinforced": True}
                        )
                        result["lessons_learned"].append(memory_text[:100])
            else:
                logger.info("No corrections to process")
            
            return result
            
        except ImportError:
            logger.warning("Feedback learner not available")
            return result
        except Exception as e:
            logger.warning(f"Correction learning error: {e}")
            return result
    
    def _consolidate_episodic_to_semantic(self, days: int = 7) -> Dict[str, Any]:
        """
        NEW: Consolidate episodic memories into generalized semantic knowledge.
        
        This is the core learning loop - IRA reviews past conversations and
        extracts patterns that become permanent knowledge.
        
        Examples:
        - "Automotive dashboards are a common PF1 application" (semantic fact)
        - "handle_shipping_query" workflow (procedural memory)
        - "PF1-Series" --used_for--> "Automotive Dashboards" (knowledge graph)
        """
        result = {
            "episodes_reviewed": 0,
            "patterns_found": 0,
            "facts_created": 0,
            "procedures_created": 0,
            "relationships_created": 0,
        }
        
        if not MEMORY_CONSOLIDATOR_AVAILABLE:
            logger.warning("Memory consolidator not available - skipping episodic consolidation")
            return result
        
        try:
            consolidator = MemoryConsolidator(verbose=False)
            consolidation_result = consolidator.consolidate_episodic_memories(days_to_review=days)
            
            result["episodes_reviewed"] = consolidation_result.episodes_reviewed
            result["patterns_found"] = consolidation_result.patterns_identified
            result["facts_created"] = consolidation_result.semantic_facts_created
            result["procedures_created"] = consolidation_result.procedures_created
            result["relationships_created"] = consolidation_result.relationships_created
            
            if consolidation_result.patterns_identified > 0:
                logger.info(f"Memory consolidation: {consolidation_result.patterns_identified} patterns → "
                           f"{consolidation_result.semantic_facts_created} facts, "
                           f"{consolidation_result.procedures_created} procedures, "
                           f"{consolidation_result.relationships_created} relationships")
            else:
                logger.info("Memory consolidation: No significant patterns found")
            
            # Log any new knowledge for the dream journal
            if consolidation_result.new_knowledge:
                for k in consolidation_result.new_knowledge[:5]:
                    logger.info(f"  Learned: [{k['type']}] {k['content'][:50]}...")
            
            return result
            
        except Exception as e:
            logger.warning(f"Episodic consolidation error: {e}")
            return result
    
    def _send_morning_summary(self, dream_result: Dict[str, Any]) -> bool:
        """
        NEW: Send a Telegram summary of what Ira learned overnight.
        """
        try:
            import requests
            
            telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            rushabh_chat_id = os.environ.get("RUSHABH_TELEGRAM_ID", "5700751574")
            
            if not telegram_token:
                print("   ⚠ Telegram token not configured")
                return False
            
            # Build summary message
            docs = dream_result.get("documents_processed", 0)
            facts = dream_result.get("facts_learned", 0)
            qdrant = dream_result.get("qdrant_indexed", 0)
            insights = dream_result.get("insights_generated", 0)
            topics = dream_result.get("topics", [])[:5]
            gaps = len(self.state.knowledge_gaps)
            duration = dream_result.get("duration_seconds", 0)
            
            # Interaction learning stats
            interaction = dream_result.get("interaction_learning", {})
            conv_learnings = interaction.get("stored", 0)
            conv_types = interaction.get("by_type", {})
            
            # Memory consolidation stats
            mem_consolidation = dream_result.get("memory_consolidation", {})
            patterns_found = mem_consolidation.get("patterns_found", 0)
            facts_from_patterns = mem_consolidation.get("facts_created", 0)
            procedures_from_patterns = mem_consolidation.get("procedures_created", 0)
            relationships_from_patterns = mem_consolidation.get("relationships_created", 0)
            
            # Only send if something was learned
            if docs == 0 and facts == 0 and conv_learnings == 0 and patterns_found == 0:
                print("   No new learning to report")
                return False
            
            # Build conversation learnings summary
            conv_summary = ""
            if conv_learnings > 0:
                corrections = conv_types.get("correction", 0)
                new_facts = conv_types.get("fact", 0) + conv_types.get("entity", 0)
                conv_summary = f"\n\n📬 *From your messages:*\n• Learned {conv_learnings} things from our chats"
                if corrections > 0:
                    conv_summary += f"\n• {corrections} corrections noted ✅"
                if new_facts > 0:
                    conv_summary += f"\n• {new_facts} new facts captured"
            
            # Build memory consolidation summary
            consolidation_summary = ""
            if patterns_found > 0:
                consolidation_summary = f"\n\n🔄 *Memory Consolidation:*\n• Found {patterns_found} recurring patterns"
                if facts_from_patterns > 0:
                    consolidation_summary += f"\n• {facts_from_patterns} new generalized facts"
                if procedures_from_patterns > 0:
                    consolidation_summary += f"\n• {procedures_from_patterns} new workflows learned"
                if relationships_from_patterns > 0:
                    consolidation_summary += f"\n• {relationships_from_patterns} new connections"
            
            message = f"""🌅 *Good Morning! Ira's Dream Report*

Last night I learned:
• 📄 Documents processed: {docs}
• 🧠 Facts learned: {facts}
• 🔍 Indexed for search: {qdrant}
• 💡 Insights generated: {insights}{conv_summary}{consolidation_summary}

{"Topics covered: " + ", ".join(topics[:3]) if topics else ""}

{"⚠️ " + str(gaps) + " knowledge gaps identified" if gaps > 0 else "✅ No knowledge gaps"}

_Dream duration: {duration:.0f}s_"""

            response = requests.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                json={
                    "chat_id": rushabh_chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
            
            if response.ok:
                logger.info("Morning summary sent to Telegram")
                return True
            else:
                logger.warning(f"Telegram send failed: {response.text[:100]}")
                return False
                
        except Exception as e:
            logger.warning(f"Morning summary error: {e}")
            return False
    
    # =========================================================================
    # MAIN DREAM CYCLE
    # =========================================================================
    
    def dream(self, force_all: bool = False, deep_mode: bool = False) -> Dict[str, Any]:
        """
        Run the dream cycle.
        
        Args:
            force_all: Reprocess all documents
            deep_mode: Include low-priority documents
        """
        logger.info("=" * 60)
        logger.info("IRA ENTERING INTEGRATED DREAM MODE...")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # Phase 1: Find documents
        logger.info("Phase 1: Scanning documents...")
        docs = self._find_documents(force_all)
        
        if not docs:
            logger.info("No new documents to learn from.")
            return {"documents_processed": 0, "facts_learned": 0, "qdrant_indexed": 0}
        
        # Group by priority
        by_priority = {}
        for path, priority in docs:
            if priority not in by_priority:
                by_priority[priority] = []
            by_priority[priority].append(path)
        
        logger.info(f"Found {len(docs)} documents:")
        for priority in DocumentPriority:
            if priority in by_priority:
                logger.info(f"  {priority.name}: {len(by_priority[priority])}")
        
        # Phase 2: Extract and store
        logger.info("Phase 2: Deep extraction & unified storage...")
        all_knowledge = []
        total_mem0 = 0
        total_qdrant = 0
        topics_learned = set()
        
        for i, (path, priority) in enumerate(docs, 1):
            if priority == DocumentPriority.LOW and not deep_mode:
                continue
            
            logger.info(f"[{i}/{len(docs)}] {path.name}")
            logger.debug(f"Priority: {priority.name}")
            
            content = self._extract_content(path)
            if not content or len(content) < 100:
                logger.debug("Skipped (no content)")
                continue
            
            logger.debug(f"Extracted {len(content)} chars")
            
            knowledge = self._extract_knowledge(content, path.name, priority)
            
            if knowledge.facts:
                logger.info(f"Facts: {len(knowledge.facts)}, Topics: {len(knowledge.topics)}")
                
                all_knowledge.append(knowledge)
                
                # UNIFIED STORAGE - to Qdrant AND Mem0
                mem0_stored, qdrant_stored = self._store_knowledge_unified(knowledge)
                total_mem0 += mem0_stored
                total_qdrant += qdrant_stored
                topics_learned.update(knowledge.topics)
                
                logger.debug(f"Stored: Mem0={mem0_stored}, Qdrant={qdrant_stored}")
            
            self.state.documents_processed[str(path)] = self._get_file_hash(path)
        
        # Phase 3: Cross-document insights
        logger.info("Phase 3: Generating cross-document insights...")
        insights = self._generate_cross_document_insights(all_knowledge)
        
        if insights:
            logger.info(f"Generated {len(insights)} insights:")
            for insight in insights[:3]:
                logger.info(f"Insight: {insight.insight[:80]}...")
        
        if self.state.knowledge_gaps:
            logger.info("Knowledge gaps identified:")
            for gap in self.state.knowledge_gaps[:3]:
                logger.info(f"Gap: {gap.get('topic', '?')}: {gap.get('question', '?')[:60]}")
        
        # Phase 4: Graph Consolidation (based on daily interactions)
        logger.info("Phase 4: Knowledge graph consolidation...")
        consolidation_result = self._consolidate_knowledge_graph()
        
        # Phase 5: Price Conflict Check
        logger.info("Phase 5: Checking for price conflicts...")
        price_conflicts = self._check_price_conflicts()
        
        # Phase 6: Conversation Quality Analysis (NEW!)
        logger.info("Phase 6: Analyzing conversation quality...")
        conversation_analysis = self._analyze_conversation_quality()
        
        # Phase 7: Learn from Corrections (NEW!)
        logger.info("Phase 7: Learning from corrections...")
        corrections = self._learn_from_corrections()
        
        # Phase 7.5: Memory Consolidation (NEW!)
        # This is the core learning loop - extract generalized knowledge from conversations
        logger.info("Phase 7.5: Consolidating episodic memories...")
        memory_consolidation = self._consolidate_episodic_to_semantic(days=7)
        
        # Update state
        self.state.last_dream = datetime.now()
        self.state.total_facts_learned += total_mem0
        self.state.total_indexed_in_qdrant += total_qdrant
        self.state.topics_covered.update(topics_learned)
        self._save_state()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Build result
        result = {
            "documents_processed": len(all_knowledge),
            "facts_learned": total_mem0,
            "qdrant_indexed": total_qdrant,
            "insights_generated": len(insights),
            "consolidation": consolidation_result,
            "conversation_analysis": conversation_analysis,
            "corrections_learned": corrections.get("corrections_found", 0),
            "memory_consolidation": memory_consolidation,
            "duration_seconds": duration,
            "topics": list(topics_learned),
        }
        
        print("\n" + "=" * 60)
        print("🌅 DREAM COMPLETE - IRA WOKE UP SMARTER!")
        print("=" * 60)
        print(f"   Documents processed: {len(all_knowledge)}")
        print(f"   Facts in Mem0: {total_mem0}")
        print(f"   Facts in Qdrant: {total_qdrant} ← NOW SEARCHABLE VIA RAG!")
        print(f"   Insights generated: {len(insights)}")
        if consolidation_result:
            print(f"   Graph consolidation: {consolidation_result.get('edges_strengthened', 0)} edges reinforced")
        if conversation_analysis.get("poor_retrievals"):
            print(f"   Conversation gaps: {len(conversation_analysis['poor_retrievals'])} queries need better coverage")
        if corrections.get("corrections_found", 0) > 0:
            print(f"   Corrections reinforced: {corrections['corrections_found']}")
        if memory_consolidation.get("patterns_found", 0) > 0:
            print(f"   🧠 Memory consolidation: {memory_consolidation['patterns_found']} patterns → "
                  f"{memory_consolidation.get('facts_created', 0)} facts, "
                  f"{memory_consolidation.get('procedures_created', 0)} procedures, "
                  f"{memory_consolidation.get('relationships_created', 0)} relationships")
        if price_conflicts.get("conflicts_found", 0) > 0:
            print(f"   ⚠ Price conflicts: {price_conflicts['conflicts_found']} (notification sent: {price_conflicts.get('notification_sent', False)})")
        print(f"   Duration: {duration:.1f}s")
        print(f"\n   Total lifetime stats:")
        print(f"     Facts learned: {self.state.total_facts_learned}")
        print(f"     Qdrant indexed: {self.state.total_indexed_in_qdrant}")
        print(f"     Insights: {self.state.insights_generated}")
        
        # Phase 8: INTERACTION LEARNING (NEW!)
        # Extract learnings from today's emails and Telegram messages
        print("\n🎓 Phase 8: Learning from today's conversations...")
        interaction_learning_result = {"learnings_extracted": 0, "learnings_stored": 0}
        try:
            from interaction_learner import run_interaction_learning
            interaction_learning_result = run_interaction_learning(days=1, dry_run=False)
            if interaction_learning_result.learnings_stored > 0:
                print(f"   ✅ Extracted {interaction_learning_result.learnings_extracted} learnings")
                print(f"   ✅ Stored {interaction_learning_result.learnings_stored} learnings")
                print(f"   📊 By type: {interaction_learning_result.learnings_by_type}")
                if interaction_learning_result.sample_learnings:
                    print("   Sample learnings:")
                    for sample in interaction_learning_result.sample_learnings[:3]:
                        print(f"      • {sample[:80]}...")
            else:
                print("   No new learnings from conversations today")
        except ImportError as e:
            logger.warning(f"Interaction learner not available: {e}")
            print(f"   ⚠ Interaction learner not available: {e}")
        except Exception as e:
            logger.warning(f"Interaction learning error: {e}")
            print(f"   ⚠ Interaction learning error: {e}")
        
        result["interaction_learning"] = {
            "extracted": getattr(interaction_learning_result, 'learnings_extracted', 0),
            "stored": getattr(interaction_learning_result, 'learnings_stored', 0),
            "by_type": getattr(interaction_learning_result, 'learnings_by_type', {}),
        }
        
        # Phase 9: Follow-Up Automation
        print("\n📋 Phase 9: Checking for stale quotes...")
        follow_up_result = {"suggestions": 0, "digest_sent": False}
        try:
            sys.path.insert(0, str(SKILLS_DIR / "crm"))
            from follow_up_automation import run_daily_follow_up_check
            follow_up_result = run_daily_follow_up_check()
            if follow_up_result["suggestions_generated"] > 0:
                print(f"   ✅ Generated {follow_up_result['suggestions_generated']} follow-up suggestions")
                print(f"      High priority: {follow_up_result['high_priority']}")
                print(f"      Digest sent: {'Yes' if follow_up_result['digest_sent'] else 'No'}")
            else:
                print("   No stale quotes found")
        except Exception as e:
            logger.warning(f"Follow-up automation error: {e}")
            print(f"   ⚠ Follow-up check error: {e}")
        
        result["follow_ups"] = follow_up_result
        
        # Phase 8.5: Customer Health Check
        print("\n💚 Phase 8.5: Customer health analysis...")
        health_result = {"total_customers": 0}
        try:
            from customer_health import run_health_check
            health_result = run_health_check()
            at_risk = health_result.get("by_risk_level", {}).get("at_risk", 0)
            churning = health_result.get("by_risk_level", {}).get("churning", 0)
            if health_result["total_customers"] > 0:
                print(f"   ✅ Analyzed {health_result['total_customers']} customers")
                print(f"      Avg score: {health_result.get('avg_score', 0):.0f}/100")
                if at_risk > 0 or churning > 0:
                    print(f"      ⚠ At-risk: {at_risk}, Churning: {churning}")
            else:
                print("   No customer data to analyze")
        except Exception as e:
            logger.warning(f"Customer health error: {e}")
            print(f"   ⚠ Health check error: {e}")
        
        result["customer_health"] = health_result
        
        # Phase 10: Send Morning Summary
        print("\n📱 Phase 10: Sending morning summary...")
        self._send_morning_summary(result)
        
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get dream mode status."""
        return {
            "last_dream": self.state.last_dream.isoformat() if self.state.last_dream else None,
            "documents_processed": len(self.state.documents_processed),
            "total_facts_learned": self.state.total_facts_learned,
            "total_indexed_in_qdrant": self.state.total_indexed_in_qdrant,
            "topics_covered": len(self.state.topics_covered),
            "insights_generated": self.state.insights_generated,
            "knowledge_gaps": len(self.state.knowledge_gaps),
        }


# Backward compatibility alias
DreamMode = IntegratedDreamMode
EnhancedDreamMode = IntegratedDreamMode


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ira's Integrated Dream Mode")
    parser.add_argument("--force", action="store_true", help="Reprocess all documents")
    parser.add_argument("--deep", action="store_true", help="Include low-priority documents")
    parser.add_argument("--status", action="store_true", help="Show dream status")
    args = parser.parse_args()
    
    dream = IntegratedDreamMode()
    
    if args.status:
        status = dream.get_status()
        print("\n" + "=" * 60)
        print("IRA'S DREAM STATUS")
        print("=" * 60)
        for k, v in status.items():
            print(f"  {k}: {v}")
        
        if dream.state.knowledge_gaps:
            print("\n  Knowledge Gaps:")
            for gap in dream.state.knowledge_gaps[:5]:
                print(f"    - {gap.get('topic', '?')}: {gap.get('question', '?')[:50]}")
    else:
        dream.dream(force_all=args.force, deep_mode=args.deep)
