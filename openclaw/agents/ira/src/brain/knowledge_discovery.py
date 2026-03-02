#!/usr/bin/env python3
"""
KNOWLEDGE DISCOVERY - Just-in-Time Learning
============================================

When Ira can't find data:
1. Detect the knowledge gap
2. Use nearest-neighbor to find relevant files
3. Deep scan those files to extract the specific data
4. Store new knowledge in Qdrant + Mem0
5. Return the discovered knowledge

This runs ON-THE-FLY for every query where data is missing.

Usage:
    from knowledge_discovery import KnowledgeDiscoverer
    discoverer = KnowledgeDiscoverer()
    result = discoverer.discover("What is the vacuum pump for IMG-1350?", gap="vacuum pump capacity")
"""

import os
import re
import json
import hashlib
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import uuid

# Setup paths and import from centralized config
BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent
sys.path.insert(0, str(AGENT_DIR))

# Import centralized config
try:
    from config import (
        QDRANT_URL, VOYAGE_API_KEY, OPENAI_API_KEY, MEM0_API_KEY,
        get_qdrant_client, get_voyage_client, get_openai_client
    )
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    # Fallback: Load environment
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    MEM0_API_KEY = os.environ.get("MEM0_API_KEY", "")

import openai
import voyageai
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

# Import shared document extractor
try:
    from document_extractor import extract_pdf, extract_document
    EXTRACTOR_AVAILABLE = True
except ImportError:
    EXTRACTOR_AVAILABLE = False

# Try to import Mem0
try:
    from mem0 import MemoryClient
    HAS_MEM0 = True
except ImportError:
    HAS_MEM0 = False

# Paths
IMPORTS_DIR = PROJECT_ROOT / "data" / "imports"
QDRANT_COLLECTION = "ira_discovered_knowledge"


@dataclass
class KnowledgeGap:
    """A detected gap in knowledge."""
    query: str
    missing_data: str  # e.g., "vacuum pump capacity for IMG-1350"
    data_type: str  # "spec", "price", "feature", "application", "general"
    entity: Optional[str] = None  # Machine model or topic
    confidence: float = 0.0


@dataclass
class DiscoveredKnowledge:
    """Knowledge extracted from a file."""
    data_point: str  # The actual data found
    source_file: str
    source_page: Optional[int] = None
    context: str = ""  # Surrounding text
    confidence: float = 0.0
    extraction_method: str = "llm"


@dataclass
class CandidateFile:
    """A file that might contain the missing data."""
    path: Path
    name: str
    relevance_score: float
    match_reasons: List[str] = field(default_factory=list)


class KnowledgeDiscoverer:
    """
    On-the-fly knowledge discovery system.
    
    When data is missing, finds and extracts it from source files.
    """
    
    def __init__(self):
        if CONFIG_AVAILABLE:
            self.openai = get_openai_client()
            self.voyage = get_voyage_client()
            self.qdrant = get_qdrant_client()
        else:
            self.openai = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else openai.OpenAI()
            self.voyage = voyageai.Client(api_key=VOYAGE_API_KEY) if VOYAGE_API_KEY else voyageai.Client()
            self.qdrant = QdrantClient(url=QDRANT_URL)
        
        self.mem0 = MemoryClient(api_key=MEM0_API_KEY) if HAS_MEM0 and MEM0_API_KEY else None
        
        # Ensure collection exists
        self._ensure_collection()
    
    def _log(self, msg: str):
        """Log with timestamp."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [DISCOVERY] {msg}")
    
    def _ensure_collection(self):
        """Ensure Qdrant collection exists."""
        try:
            self.qdrant.get_collection(QDRANT_COLLECTION)
        except Exception:
            self.qdrant.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
            )
            self._log(f"Created collection: {QDRANT_COLLECTION}")
    
    # =========================================================================
    # STEP 1: Detect Knowledge Gap
    # =========================================================================
    
    def detect_gap(self, query: str, search_results: List[Dict], 
                   machine_data: Optional[Dict] = None) -> Optional[KnowledgeGap]:
        """
        Detect if there's a knowledge gap that needs discovery.
        
        Returns KnowledgeGap if data is missing, None if we have enough.
        """
        self._log("Analyzing for knowledge gaps...")
        
        # Use LLM to analyze the gap
        prompt = f"""Analyze this query and search results to detect if there's missing data.

QUERY: {query}

SEARCH RESULTS SUMMARY:
{json.dumps([r.get('text', '')[:200] for r in search_results[:5]], indent=2)}

MACHINE DATA (if any):
{json.dumps(machine_data, indent=2) if machine_data else "None"}

Determine:
1. Is there a specific data point being asked for?
2. Is that data point present in the search results or machine data?
3. If missing, what exactly is missing?

Return JSON:
{{
    "has_gap": true/false,
    "missing_data": "description of what's missing",
    "data_type": "spec|price|feature|application|general",
    "entity": "machine model or topic if applicable",
    "confidence": 0.0-1.0
}}
"""

        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Analyze queries for missing data. Return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.2
            )
            
            text = response.choices[0].message.content
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            result = json.loads(text)
            
            if result.get("has_gap"):
                gap = KnowledgeGap(
                    query=query,
                    missing_data=result.get("missing_data", ""),
                    data_type=result.get("data_type", "general"),
                    entity=result.get("entity"),
                    confidence=result.get("confidence", 0.5)
                )
                self._log(f"Gap detected: {gap.missing_data}")
                return gap
            
            self._log("No knowledge gap detected")
            return None
            
        except Exception as e:
            self._log(f"Error detecting gap: {e}")
            return None
    
    # =========================================================================
    # STEP 2: Find Candidate Files (Nearest Neighbor)
    # =========================================================================
    
    def find_candidate_files(self, gap: KnowledgeGap, limit: int = 5) -> List[CandidateFile]:
        """
        Find files most likely to contain the missing data.
        
        Uses multiple signals:
        - Filename keywords
        - Entity mentions (model numbers)
        - File type preferences (catalogues > quotes > general)
        """
        self._log(f"Searching for files containing: {gap.missing_data}")
        
        candidates = []
        
        # Build search keywords
        keywords = self._extract_keywords(gap)
        self._log(f"Keywords: {keywords}")
        
        # Score all files in imports directory
        for file_path in IMPORTS_DIR.glob("**/*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in ['.pdf', '.xlsx', '.docx', '.txt', '.xls']:
                continue
            
            score, reasons = self._score_file(file_path, keywords, gap)
            
            if score > 0.1:  # Minimum threshold
                candidates.append(CandidateFile(
                    path=file_path,
                    name=file_path.name,
                    relevance_score=score,
                    match_reasons=reasons
                ))
        
        # Sort by score
        candidates.sort(key=lambda x: x.relevance_score, reverse=True)
        
        self._log(f"Found {len(candidates)} candidate files")
        for c in candidates[:3]:
            self._log(f"  {c.relevance_score:.2f}: {c.name} ({', '.join(c.match_reasons[:2])})")
        
        return candidates[:limit]
    
    def _extract_keywords(self, gap: KnowledgeGap) -> List[str]:
        """Extract search keywords from the gap."""
        keywords = []
        
        # Add entity
        if gap.entity:
            keywords.append(gap.entity.lower())
            # Also add variations
            keywords.append(gap.entity.replace("-", "").lower())
            keywords.append(gap.entity.replace("-", " ").lower())
        
        # Add data type keywords
        data_type_keywords = {
            "spec": ["specification", "spec", "technical", "catalogue", "catalog"],
            "price": ["price", "quotation", "quote", "cost"],
            "feature": ["feature", "catalogue", "brochure"],
            "application": ["application", "use case", "industry"],
        }
        keywords.extend(data_type_keywords.get(gap.data_type, []))
        
        # Extract keywords from missing_data
        words = re.findall(r'\b\w+\b', gap.missing_data.lower())
        keywords.extend([w for w in words if len(w) > 3])
        
        # Add technology-specific expansions
        technology_expansions = {
            "hotmelt": ["frimo", "thermoforming", "lamination", "technology"],
            "lamination": ["frimo", "hotmelt", "vacuum", "technology"],
            "vacuum": ["frimo", "lamination", "thermoforming"],
            "img": ["inmold", "grain", "thermoforming", "soft", "touch"],
            "soft": ["img", "inmold", "touch", "interior"],
        }
        
        for word in list(keywords):
            if word in technology_expansions:
                keywords.extend(technology_expansions[word])
        
        return list(set(keywords))
    
    def _score_file(self, file_path: Path, keywords: List[str], gap: KnowledgeGap) -> Tuple[float, List[str]]:
        """Score a file's relevance to the knowledge gap."""
        name_lower = file_path.name.lower()
        score = 0.0
        reasons = []
        
        # Keyword matching in filename
        for kw in keywords:
            if kw in name_lower:
                score += 0.3
                reasons.append(f"filename contains '{kw}'")
        
        # Entity match (highest weight)
        if gap.entity:
            entity_clean = gap.entity.replace("-", "").lower()
            if entity_clean in name_lower.replace("-", "").replace(" ", ""):
                score += 0.5
                reasons.append(f"exact entity match: {gap.entity}")
        
        # File type preferences
        if "catalogue" in name_lower or "catalog" in name_lower:
            score += 0.2
            reasons.append("catalogue file")
        elif "spec" in name_lower:
            score += 0.15
            reasons.append("spec file")
        elif "quotation" in name_lower or "quote" in name_lower:
            score += 0.1
            reasons.append("quotation file")
        
        # PDF preference for specs
        if gap.data_type == "spec" and file_path.suffix.lower() == ".pdf":
            score += 0.1
            reasons.append("PDF (good for specs)")
        
        # Excel preference for prices
        if gap.data_type == "price" and file_path.suffix.lower() in [".xlsx", ".xls"]:
            score += 0.1
            reasons.append("Excel (good for prices)")
        
        # Technology document matches (for process/technique questions)
        tech_docs = {
            "frimo": 0.4,  # FRIMO docs are key for thermoforming processes
            "technology": 0.3,
            "process": 0.2,
        }
        for tech_kw, tech_score in tech_docs.items():
            if tech_kw in name_lower:
                score += tech_score
                reasons.append(f"technology document: {tech_kw}")
        
        return min(score, 1.0), reasons
    
    # =========================================================================
    # STEP 3: Deep Scan Files
    # =========================================================================
    
    def deep_scan_files(self, candidates: List[CandidateFile], gap: KnowledgeGap) -> List[DiscoveredKnowledge]:
        """
        Deep scan candidate files to extract the missing data.
        """
        self._log("Deep scanning candidate files...")
        
        discovered = []
        
        for candidate in candidates[:3]:  # Scan top 3
            self._log(f"  Scanning: {candidate.name}")
            
            try:
                # Extract text based on file type
                if candidate.path.suffix.lower() == '.pdf':
                    knowledge = self._scan_pdf(candidate.path, gap)
                elif candidate.path.suffix.lower() in ['.xlsx', '.xls']:
                    knowledge = self._scan_excel(candidate.path, gap)
                else:
                    continue
                
                if knowledge:
                    discovered.extend(knowledge)
                    
            except Exception as e:
                self._log(f"  Error scanning {candidate.name}: {e}")
        
        self._log(f"Discovered {len(discovered)} data points")
        return discovered
    
    def _scan_pdf(self, pdf_path: Path, gap: KnowledgeGap) -> List[DiscoveredKnowledge]:
        """Deep scan a PDF for specific data using shared DocumentExtractor."""
        discovered = []
        
        # Use shared document extractor (has fallback chain: PyMuPDF → pdfplumber → pypdf)
        full_text = ""
        
        if EXTRACTOR_AVAILABLE:
            try:
                full_text = extract_pdf(pdf_path, max_pages=20)
            except Exception as e:
                self._log(f"Shared extractor failed: {e}, falling back to pdfplumber")
        
        # Fallback to direct pdfplumber if extractor failed or unavailable
        if not full_text:
            try:
                import pdfplumber
                with pdfplumber.open(str(pdf_path)) as pdf:
                    text_parts = []
                    for i, page in enumerate(pdf.pages[:20]):  # Limit to 20 pages
                        text = page.extract_text() or ""
                        if text.strip():
                            text_parts.append(f"--- Page {i+1} ---\n{text}")
                    full_text = "\n".join(text_parts)
            except Exception as e:
                self._log(f"PDF scan error: {e}")
                return discovered
        
        if full_text:
            # Use LLM to find specific data
            knowledge = self._extract_with_llm(full_text, gap, pdf_path.name)
            if knowledge:
                discovered.append(knowledge)
        
        return discovered
    
    def _scan_excel(self, excel_path: Path, gap: KnowledgeGap) -> List[DiscoveredKnowledge]:
        """Deep scan an Excel file for specific data."""
        discovered = []
        
        try:
            import pandas as pd
            
            # Read all sheets
            xl = pd.ExcelFile(str(excel_path))
            full_text = ""
            
            for sheet in xl.sheet_names[:5]:  # Limit to 5 sheets
                df = pd.read_excel(xl, sheet_name=sheet)
                full_text += f"\n--- Sheet: {sheet} ---\n"
                full_text += df.to_string()[:3000]
            
            knowledge = self._extract_with_llm(full_text, gap, excel_path.name)
            if knowledge:
                discovered.append(knowledge)
                
        except Exception as e:
            self._log(f"Excel scan error: {e}")
        
        return discovered
    
    def _extract_with_llm(self, text: str, gap: KnowledgeGap, source: str) -> Optional[DiscoveredKnowledge]:
        """Use LLM to extract specific data from text."""
        
        prompt = f"""Extract the specific data point from this document.

WHAT WE'RE LOOKING FOR:
{gap.missing_data}

ENTITY (if applicable): {gap.entity}
DATA TYPE: {gap.data_type}

DOCUMENT TEXT:
{text[:8000]}

Find the exact value/data we're looking for. Be precise.

Return JSON:
{{
    "found": true/false,
    "data_point": "the exact value found (e.g., '160 m³/hr' or '₹15,00,000')",
    "context": "surrounding text for verification (50-100 words)",
    "confidence": 0.0-1.0
}}

If the data is not in the document, return {{"found": false}}
"""

        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Extract specific data points from documents. Be precise and accurate."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            text = response.choices[0].message.content
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            result = json.loads(text)
            
            if result.get("found"):
                return DiscoveredKnowledge(
                    data_point=result.get("data_point", ""),
                    source_file=source,
                    context=result.get("context", ""),
                    confidence=result.get("confidence", 0.5)
                )
            
        except Exception as e:
            self._log(f"LLM extraction error: {e}")
        
        return None
    
    # =========================================================================
    # STEP 4: Store Knowledge
    # =========================================================================
    
    def store_knowledge(self, knowledge: DiscoveredKnowledge, gap: KnowledgeGap):
        """Store discovered knowledge in Qdrant and Mem0."""
        self._log(f"Storing discovered knowledge: {knowledge.data_point}")
        
        # Build knowledge text
        knowledge_text = f"""
DISCOVERED: {gap.missing_data}
VALUE: {knowledge.data_point}
SOURCE: {knowledge.source_file}
CONTEXT: {knowledge.context}
ENTITY: {gap.entity or 'General'}
DISCOVERED ON: {datetime.now().isoformat()}
"""
        
        # Store in Qdrant
        try:
            embedding = self.voyage.embed(
                [knowledge_text], 
                model="voyage-3", 
                input_type="document"
            ).embeddings[0]
            
            point_id = str(uuid.uuid4())
            self.qdrant.upsert(
                collection_name=QDRANT_COLLECTION,
                points=[PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": knowledge_text,
                        "data_point": knowledge.data_point,
                        "entity": gap.entity,
                        "data_type": gap.data_type,
                        "source_file": knowledge.source_file,
                        "confidence": knowledge.confidence,
                        "discovered_at": datetime.now().isoformat(),
                    }
                )]
            )
            self._log(f"  ✓ Stored in Qdrant: {QDRANT_COLLECTION}")
        except Exception as e:
            self._log(f"  ✗ Qdrant error: {e}")
        
        # Store in Mem0
        if self.mem0:
            try:
                self.mem0.add(
                    knowledge_text,
                    user_id="system_ira_discoveries",
                    metadata={
                        "type": "discovered_knowledge",
                        "entity": gap.entity or "",
                        "data_type": gap.data_type,
                    }
                )
                self._log(f"  ✓ Stored in Mem0")
            except Exception as e:
                self._log(f"  ✗ Mem0 error: {e}")
    
    # =========================================================================
    # MAIN DISCOVERY FLOW
    # =========================================================================
    
    def discover(self, query: str, search_results: List[Dict] = None, 
                 machine_data: Dict = None, force: bool = False) -> Optional[DiscoveredKnowledge]:
        """
        Main entry point: Attempt to discover missing knowledge.
        
        Args:
            query: The original question
            search_results: Results from existing search (to detect gaps)
            machine_data: Data from machine database (to detect gaps)
            force: Force discovery even if no gap detected
        
        Returns:
            DiscoveredKnowledge if found, None otherwise
        """
        self._log("=" * 50)
        self._log("STARTING KNOWLEDGE DISCOVERY")
        self._log(f"Query: {query[:80]}...")
        self._log("=" * 50)
        
        # Step 1: Detect gap
        gap = None
        if force:
            # Create gap from query
            gap = KnowledgeGap(
                query=query,
                missing_data=query,
                data_type="general",
                confidence=0.8
            )
        else:
            gap = self.detect_gap(query, search_results or [], machine_data)
        
        if not gap:
            self._log("No gap detected, skipping discovery")
            return None
        
        # Step 2: Find candidate files
        candidates = self.find_candidate_files(gap)
        
        if not candidates:
            self._log("No candidate files found")
            return None
        
        # Step 3: Deep scan
        discovered = self.deep_scan_files(candidates, gap)
        
        if not discovered:
            self._log("Could not extract data from files")
            return None
        
        # Get best result
        best = max(discovered, key=lambda x: x.confidence)
        
        # Step 4: Store knowledge
        self.store_knowledge(best, gap)
        
        self._log("=" * 50)
        self._log(f"DISCOVERY COMPLETE: {best.data_point}")
        self._log("=" * 50)
        
        return best


def discover_on_the_fly(query: str, context: Dict = None) -> Optional[str]:
    """
    Convenience function for on-the-fly discovery.
    
    Returns the discovered data point or None.
    """
    discoverer = KnowledgeDiscoverer()
    result = discoverer.discover(
        query, 
        search_results=context.get("search_results", []) if context else [],
        machine_data=context.get("machine_data") if context else None
    )
    return result.data_point if result else None


# =============================================================================
# CLI for OpenClaw skill
# =============================================================================

if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Knowledge Discovery Skill")
    parser.add_argument("--query", required=True, help="Query to discover knowledge for")
    parser.add_argument("--force", action="store_true", help="Force discovery even without gap detection")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    discoverer = KnowledgeDiscoverer()
    result = discoverer.discover(query=args.query, force=args.force)
    
    if result:
        if args.json:
            print(json.dumps({
                "discovered": True,
                "data_point": result.data_point,
                "source_file": result.source_file,
                "confidence": result.confidence,
                "data_type": result.data_type,
            }, indent=2))
        else:
            print(f"Discovered: {result.data_point}")
            print(f"Source: {result.source_file}")
            print(f"Confidence: {result.confidence:.0%}")
    else:
        if args.json:
            print(json.dumps({"discovered": False, "message": "No knowledge discovered"}, indent=2))
        else:
            print("No knowledge discovered for this query")
