#!/usr/bin/env python3
"""
DOCUMENT INGESTOR - Unified Document → Memory Pipeline

╔════════════════════════════════════════════════════════════════════╗
║  Automatically scans documents and extracts knowledge into memory  ║
║  Supports: PDF, XLSX, DOCX, CSV, TXT, images                       ║
║  Detects conflicts and queues them for human clarification         ║
╚════════════════════════════════════════════════════════════════════╝

Usage:
    from document_ingestor import DocumentIngestor
    
    ingestor = DocumentIngestor()
    result = ingestor.ingest("/path/to/document.pdf")
    print(f"Stored {result.memories_stored} facts, {result.conflicts_found} conflicts")
"""

import json
import logging
import os
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Import from centralized config via brain_orchestrator
try:
    from config import OPENAI_API_KEY, PROJECT_ROOT
except ImportError:
    import os
    from pathlib import Path
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent

# Import shared document extractor
MEMORY_DIR = Path(__file__).parent
SKILLS_DIR = MEMORY_DIR.parent
BRAIN_DIR = SKILLS_DIR / "brain"
sys.path.insert(0, str(BRAIN_DIR))

try:
    from document_extractor import DocumentExtractor, ExtractionResult
    SHARED_EXTRACTOR_AVAILABLE = True
    _shared_extractor = DocumentExtractor()
except ImportError:
    SHARED_EXTRACTOR_AVAILABLE = False
    _shared_extractor = None
RUSHABH_IDENTITY_ID = "rushabh_doshi_founder"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ExtractedFact:
    """A single fact extracted from a document."""
    entity_type: str  # company, contact, product
    entity_name: str
    fact_text: str
    fact_type: str = "fact"  # fact, context, correction
    confidence: float = 0.9
    source_page: Optional[int] = None
    source_section: Optional[str] = None


@dataclass 
class ConflictItem:
    """A detected conflict between facts."""
    conflict_id: str
    entity_name: str
    existing_fact: str
    existing_fact_id: int
    new_fact: str
    conflict_type: str  # contradiction, outdated, ambiguous
    source_document: str
    created_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolution: Optional[str] = None  # keep_existing, use_new, merge


@dataclass
class IngestionResult:
    """Result of document ingestion."""
    document_path: str
    document_type: str
    pages_processed: int
    facts_extracted: int
    memories_stored: int
    conflicts_found: int
    conflicts: List[ConflictItem] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


# =============================================================================
# DOCUMENT EXTRACTORS
# =============================================================================

class PDFExtractor:
    """Extract text from PDF documents using shared DocumentExtractor."""
    
    @staticmethod
    def extract(path: Path) -> Tuple[str, int]:
        """Extract text and page count from PDF."""
        # Use shared extractor if available (has fallback chain)
        if SHARED_EXTRACTOR_AVAILABLE and _shared_extractor:
            result = _shared_extractor.extract(path)
            if result.success:
                return result.text, result.page_count
        
        # Fallback to direct pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(f"[PAGE {i+1}]\n{text}")
            return "\n\n".join(pages), len(reader.pages)
        except ImportError:
            return "", 0
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return "", 0


class ExcelExtractor:
    """Extract data from Excel files."""
    
    @staticmethod
    def extract(path: Path) -> Tuple[str, int]:
        """Extract text from Excel sheets."""
        try:
            import pandas as pd
            xlsx = pd.ExcelFile(path)
            sheets = []
            for sheet_name in xlsx.sheet_names:
                df = pd.read_excel(xlsx, sheet_name=sheet_name)
                if not df.empty:
                    sheets.append(f"[SHEET: {sheet_name}]\n{df.to_string()}")
            return "\n\n".join(sheets), len(xlsx.sheet_names)
        except ImportError:
            return "", 0
        except Exception as e:
            logger.error(f"Excel extraction error: {e}")
            return "", 0


class DocxExtractor:
    """Extract text from Word documents."""
    
    @staticmethod
    def extract(path: Path) -> Tuple[str, int]:
        """Extract text from DOCX."""
        try:
            from docx import Document
            doc = Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs), len(paragraphs)
        except ImportError:
            return "", 0
        except Exception as e:
            logger.error(f"DOCX extraction error: {e}")
            return "", 0


class TextExtractor:
    """Extract text from plain text files."""
    
    @staticmethod
    def extract(path: Path) -> Tuple[str, int]:
        """Extract text from TXT/CSV."""
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
            lines = len(content.splitlines())
            return content, lines
        except Exception as e:
            logger.error(f"Text extraction error: {e}")
            return "", 0


# =============================================================================
# FACT EXTRACTION (LLM-POWERED)
# =============================================================================

FACT_EXTRACTION_PROMPT = """You are a knowledge extraction expert for Machinecraft Technologies, a vacuum forming machine manufacturer.

Analyze this document and extract SPECIFIC, ACTIONABLE facts that should be remembered.

DOCUMENT: {filename}
---
{content}
---

Extract facts in these categories:

1. PRODUCT FACTS - Technical specs, features, pricing, models
   - Machine specifications (sizes, speeds, capabilities)
   - Pricing information (₹/$ amounts)
   - Configuration options
   
2. COMPANY FACTS - About Machinecraft or other companies
   - Financial data (revenue, orders, payments)
   - Milestones, achievements, history
   - Partnerships, relationships
   
3. CONTACT FACTS - About people/customers
   - Customer details (company, requirements, history)
   - Order information (what they ordered, when, status)
   - Payment status, pending amounts

4. MARKET FACTS - Industry intelligence
   - Competitor information
   - Market trends, applications
   - Customer preferences

Rules:
- Extract SPECIFIC facts with numbers/dates when available
- Each fact should be self-contained and understandable alone
- Include source context (e.g., "According to Q3 2024 data...")
- Maximum 50 facts per document
- Skip generic/obvious information

Output JSON:
{{
  "facts": [
    {{
      "entity_type": "product|company|contact|market",
      "entity_name": "Name of the entity this fact is about",
      "fact_text": "The specific fact (1-2 sentences max)",
      "fact_type": "fact|context|update",
      "confidence": 0.9
    }}
  ],
  "document_summary": "One-line summary of what this document contains"
}}

JSON:"""


class FactExtractor:
    """Extract facts from document text using LLM."""
    
    def __init__(self):
        self.client = None
        
    def _get_client(self):
        if not self.client:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=OPENAI_API_KEY)
            except Exception as e:
                logger.error(f"OpenAI client init failed: {e}")
        return self.client
    
    def extract_facts(self, content: str, filename: str) -> List[ExtractedFact]:
        """Extract facts from document content."""
        client = self._get_client()
        if not client:
            return []
        
        # Truncate content if too long (GPT-4 context limit)
        max_chars = 100000
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n[... TRUNCATED ...]"
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You extract structured facts from business documents. Output valid JSON only."},
                    {"role": "user", "content": FACT_EXTRACTION_PROMPT.format(
                        filename=filename,
                        content=content
                    )}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON (handle markdown code blocks)
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            data = json.loads(result_text)
            
            facts = []
            for item in data.get("facts", []):
                facts.append(ExtractedFact(
                    entity_type=item.get("entity_type", "company"),
                    entity_name=item.get("entity_name", "Unknown"),
                    fact_text=item.get("fact_text", ""),
                    fact_type=item.get("fact_type", "fact"),
                    confidence=item.get("confidence", 0.9)
                ))
            
            return facts
            
        except Exception as e:
            logger.error(f"Fact extraction failed: {e}")
            return []


# =============================================================================
# CONFLICT DETECTION
# =============================================================================

CONFLICT_DETECTION_PROMPT = """Compare these two facts about "{entity_name}" and determine if they conflict:

EXISTING FACT (in memory):
{existing_fact}

NEW FACT (from document):
{new_fact}

Analyze:
1. Do they contradict each other? (e.g., different prices, specs, dates)
2. Is the new fact an UPDATE to outdated info?
3. Are they about different aspects (no conflict)?

Output JSON:
{{
  "has_conflict": true/false,
  "conflict_type": "contradiction|outdated|none",
  "explanation": "Brief explanation of the conflict",
  "recommendation": "keep_existing|use_new|merge|no_action"
}}

JSON:"""


class ConflictDetector:
    """Detect conflicts between new facts and existing memory."""
    
    def __init__(self):
        self.client = None
        self._conflict_queue_path = PROJECT_ROOT / "openclaw/agents/ira/workspace/conflict_queue.json"
        
    def _get_client(self):
        if not self.client:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=OPENAI_API_KEY)
            except Exception:
                pass
        return self.client
    
    def find_similar_facts(self, entity_name: str, entity_type: str) -> List[Dict]:
        """Find existing facts about an entity."""
        try:
            try:
                from .persistent_memory import PersistentMemory
            except ImportError:
                from persistent_memory import PersistentMemory
            pm = PersistentMemory()
            # Get existing memories about this entity
            memories = pm.get_entity_memories(entity_name, limit=10)
            return [m.to_dict() for m in memories]
        except Exception as e:
            logger.error(f"Error searching existing facts: {e}")
            return []
    
    def check_conflict(self, new_fact: ExtractedFact, existing_fact: Dict) -> Optional[ConflictItem]:
        """Check if new fact conflicts with existing fact."""
        client = self._get_client()
        if not client:
            return None
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You detect factual conflicts. Output valid JSON only."},
                    {"role": "user", "content": CONFLICT_DETECTION_PROMPT.format(
                        entity_name=new_fact.entity_name,
                        existing_fact=existing_fact.get("memory_text", ""),
                        new_fact=new_fact.fact_text
                    )}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            data = json.loads(result_text)
            
            if data.get("has_conflict") and data.get("conflict_type") != "none":
                return ConflictItem(
                    conflict_id=str(uuid.uuid4())[:8],
                    entity_name=new_fact.entity_name,
                    existing_fact=existing_fact.get("memory_text", ""),
                    existing_fact_id=existing_fact.get("id", 0),
                    new_fact=new_fact.fact_text,
                    conflict_type=data.get("conflict_type", "ambiguous"),
                    source_document="document"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Conflict check failed: {e}")
            return None
    
    def queue_conflict(self, conflict: ConflictItem, source_doc: str):
        """Add conflict to the clarification queue."""
        conflict.source_document = source_doc
        
        # Load existing queue
        queue = []
        if self._conflict_queue_path.exists():
            try:
                queue = json.loads(self._conflict_queue_path.read_text())
            except (json.JSONDecodeError, IOError, OSError):
                queue = []
        
        # Add new conflict
        queue.append({
            "conflict_id": conflict.conflict_id,
            "entity_name": conflict.entity_name,
            "existing_fact": conflict.existing_fact,
            "existing_fact_id": conflict.existing_fact_id,
            "new_fact": conflict.new_fact,
            "conflict_type": conflict.conflict_type,
            "source_document": conflict.source_document,
            "created_at": conflict.created_at.isoformat(),
            "resolved": False
        })
        
        # Save queue
        self._conflict_queue_path.parent.mkdir(parents=True, exist_ok=True)
        self._conflict_queue_path.write_text(json.dumps(queue, indent=2))
        
        return True
    
    def get_pending_conflicts(self) -> List[Dict]:
        """Get all unresolved conflicts."""
        if not self._conflict_queue_path.exists():
            return []
        try:
            queue = json.loads(self._conflict_queue_path.read_text())
            return [c for c in queue if not c.get("resolved")]
        except (json.JSONDecodeError, IOError, OSError):
            return []
    
    def resolve_conflict(self, conflict_id: str, resolution: str, keep_fact: str = None):
        """Resolve a conflict and update memory."""
        if not self._conflict_queue_path.exists():
            return False
        
        try:
            queue = json.loads(self._conflict_queue_path.read_text())
            
            for conflict in queue:
                if conflict.get("conflict_id") == conflict_id:
                    conflict["resolved"] = True
                    conflict["resolution"] = resolution
                    conflict["resolved_at"] = datetime.now().isoformat()
                    
                    # Apply resolution to memory
                    if resolution == "use_new":
                        self._update_memory(
                            conflict["existing_fact_id"],
                            conflict["new_fact"]
                        )
                    elif resolution == "merge" and keep_fact:
                        self._update_memory(
                            conflict["existing_fact_id"],
                            keep_fact
                        )
                    # keep_existing = no action needed
                    
                    break
            
            self._conflict_queue_path.write_text(json.dumps(queue, indent=2))
            return True
            
        except Exception as e:
            logger.error(f"Error resolving conflict: {e}")
            return False
    
    def _update_memory(self, memory_id: int, new_text: str):
        """Update an existing memory with new text."""
        try:
            try:
                from .persistent_memory import PersistentMemory
            except ImportError:
                from persistent_memory import PersistentMemory
            pm = PersistentMemory()
            pm.update_entity_memory(memory_id, new_text)
        except Exception as e:
            logger.error(f"Error updating memory: {e}")


# =============================================================================
# MAIN INGESTOR CLASS
# =============================================================================

class DocumentIngestor:
    """
    Main document ingestion pipeline.
    
    Workflow:
    1. Extract text from document (PDF, XLSX, DOCX, etc.)
    2. Use LLM to extract structured facts
    3. Check each fact against existing memory for conflicts
    4. Store non-conflicting facts immediately
    5. Queue conflicts for human clarification via Telegram
    """
    
    EXTRACTORS = {
        ".pdf": PDFExtractor,
        ".xlsx": ExcelExtractor,
        ".xls": ExcelExtractor,
        ".docx": DocxExtractor,
        ".doc": DocxExtractor,
        ".txt": TextExtractor,
        ".csv": TextExtractor,
        ".md": TextExtractor,
    }
    
    def __init__(self, check_conflicts: bool = True):
        self.fact_extractor = FactExtractor()
        self.conflict_detector = ConflictDetector()
        self.check_conflicts = check_conflicts
        
    def ingest(self, document_path: str, source_identity: str = RUSHABH_IDENTITY_ID,
               context: str = None) -> IngestionResult:
        """
        Ingest a document into Ira's memory.
        
        Args:
            document_path: Path to the document
            source_identity: Who provided this document
            context: Optional human-written description of the document contents.
                     Prepended to extracted text so the LLM fact extractor knows
                     what to look for.
            
        Returns:
            IngestionResult with stats and any conflicts found
        """
        import time
        start_time = time.time()
        
        path = Path(document_path)
        result = IngestionResult(
            document_path=str(path),
            document_type=path.suffix.lower(),
            pages_processed=0,
            facts_extracted=0,
            memories_stored=0,
            conflicts_found=0
        )
        
        # 1. Check file exists
        if not path.exists():
            result.errors.append(f"File not found: {path}")
            return result
        
        # 2. Get appropriate extractor
        extractor_class = self.EXTRACTORS.get(path.suffix.lower())
        if not extractor_class:
            result.errors.append(f"Unsupported file type: {path.suffix}")
            return result
        
        # 3. Extract text
        logger.info(f"Extracting text from {path.name}")
        content, page_count = extractor_class.extract(path)
        result.pages_processed = page_count
        
        if not content.strip():
            result.errors.append("No text content extracted")
            return result

        if context:
            content = f"[UPLOADER CONTEXT: {context}]\n\n{content}"
        
        # 4. Extract facts using LLM
        logger.info(f"Extracting facts from {len(content):,} characters")
        facts = self.fact_extractor.extract_facts(content, path.name)
        result.facts_extracted = len(facts)
        
        if not facts:
            result.errors.append("No facts extracted")
            return result
        
        logger.info(f"Extracted {len(facts)} facts")
        
        # 5. Import memory system (unified: Mem0 primary, PostgreSQL fallback)
        try:
            try:
                from .unified_memory import get_unified_memory
            except ImportError:
                from unified_memory import get_unified_memory
            memory = get_unified_memory()
        except Exception as e:
            # Fall back to PostgreSQL directly
            try:
                try:
                    from .persistent_memory import PersistentMemory
                except ImportError:
                    from persistent_memory import PersistentMemory
                memory = PersistentMemory()
            except Exception as e2:
                result.errors.append(f"Memory system unavailable: {e}, {e2}")
                return result
        
        # 6. Process each fact
        for fact in facts:
            # Check for conflicts if enabled
            conflict = None
            if self.check_conflicts:
                existing = self.conflict_detector.find_similar_facts(
                    fact.entity_name, 
                    fact.entity_type
                )
                
                for existing_fact in existing:
                    # Check semantic similarity first (quick filter)
                    existing_text = existing_fact.get("memory_text", "").lower()
                    new_text = fact.fact_text.lower()
                    
                    # If they mention similar numbers/dates, check for conflict
                    if self._has_potential_conflict(existing_text, new_text):
                        conflict = self.conflict_detector.check_conflict(fact, existing_fact)
                        if conflict:
                            break
            
            if conflict:
                # Queue for clarification
                self.conflict_detector.queue_conflict(conflict, path.name)
                result.conflicts_found += 1
                result.conflicts.append(conflict)
                logger.warning(f"Conflict detected: {fact.entity_name}")
            else:
                # Store directly using unified memory (Mem0 + PostgreSQL)
                try:
                    # Check if using unified memory or fallback
                    if hasattr(memory, 'store_entity_memory'):
                        # Unified memory service or PersistentMemory
                        store_result = memory.store_entity_memory(
                            entity_type=fact.entity_type,
                            entity_name=fact.entity_name,
                            memory_text=fact.fact_text,
                            memory_type=fact.fact_type,
                            user_id=source_identity,
                            source_channel="document",
                            confidence=fact.confidence,
                        )
                        # Handle different return types
                        if hasattr(store_result, 'success'):
                            if store_result.success:
                                result.memories_stored += 1
                            else:
                                result.errors.append(f"Store failed: {store_result.error}")
                        elif store_result:  # PersistentMemory returns ID
                            result.memories_stored += 1
                    else:
                        result.errors.append("No store method available")
                except Exception as e:
                    result.errors.append(f"Store failed: {e}")
        
        result.duration_seconds = time.time() - start_time
        
        # Log summary
        logger.info(
            f"Ingestion complete: {path.name} - "
            f"Pages: {result.pages_processed}, Facts: {result.facts_extracted}, "
            f"Stored: {result.memories_stored}, Conflicts: {result.conflicts_found}, "
            f"Duration: {result.duration_seconds:.1f}s"
        )
        
        if result.conflicts_found > 0:
            logger.warning(f"{result.conflicts_found} conflicts queued for clarification")
        
        return result
    
    def _has_potential_conflict(self, text1: str, text2: str) -> bool:
        """Quick check if two texts might conflict (both have numbers/dates)."""
        # Look for numbers
        nums1 = set(re.findall(r'\d+(?:\.\d+)?', text1))
        nums2 = set(re.findall(r'\d+(?:\.\d+)?', text2))
        
        # If both have different numbers about same topic, might conflict
        if nums1 and nums2 and nums1 != nums2:
            return True
        
        return False
    
    def ingest_folder(self, folder_path: str, recursive: bool = False) -> List[IngestionResult]:
        """Ingest all supported documents in a folder."""
        path = Path(folder_path)
        results = []
        
        if not path.is_dir():
            return results
        
        pattern = "**/*" if recursive else "*"
        
        for file_path in path.glob(pattern):
            if file_path.suffix.lower() in self.EXTRACTORS:
                print(f"\n{'='*60}")
                print(f"Processing: {file_path.name}")
                result = self.ingest(str(file_path))
                results.append(result)
        
        return results


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    """Command-line interface for document ingestion."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python document_ingestor.py <document_path>")
        print("       python document_ingestor.py --folder <folder_path>")
        sys.exit(1)
    
    ingestor = DocumentIngestor()
    
    if sys.argv[1] == "--folder":
        if len(sys.argv) < 3:
            print("Error: folder path required")
            sys.exit(1)
        results = ingestor.ingest_folder(sys.argv[2])
        print(f"\n\n{'='*60}")
        print(f"BATCH COMPLETE: {len(results)} documents processed")
        total_facts = sum(r.facts_extracted for r in results)
        total_stored = sum(r.memories_stored for r in results)
        total_conflicts = sum(r.conflicts_found for r in results)
        print(f"Total Facts: {total_facts}")
        print(f"Total Stored: {total_stored}")
        print(f"Total Conflicts: {total_conflicts}")
    else:
        result = ingestor.ingest(sys.argv[1])
        if result.errors:
            print(f"\nErrors: {result.errors}")


if __name__ == "__main__":
    main()
