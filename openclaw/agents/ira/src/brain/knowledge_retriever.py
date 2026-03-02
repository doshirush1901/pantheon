#!/usr/bin/env python3
"""
KNOWLEDGE RETRIEVER - Ira's Brain Search System
================================================

When Ira encounters a topic, she:
1. First checks Mem0 memory for existing knowledge
2. If not found, searches through documents (PDFs, docs)
3. Uses semantic similarity to find relevant information
4. Returns knowledge to inform her response

This is the "thinking before speaking" module.

Usage:
    retriever = KnowledgeRetriever()
    knowledge = retriever.retrieve("hotmelt adhesive lamination")
    # Returns relevant facts from memory + documents
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import re

# Import from centralized config
BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

try:
    from config import PROJECT_ROOT
except ImportError:
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent

# Import shared document extractor
try:
    from .document_extractor import DocumentExtractor, extract_pdf
except ImportError:
    from document_extractor import DocumentExtractor, extract_pdf

# Document locations
IMPORTS_DIR = PROJECT_ROOT / "data" / "imports"

# Shared extractor instance
_doc_extractor = DocumentExtractor()


@dataclass
class KnowledgeChunk:
    """A piece of retrieved knowledge."""
    content: str
    source: str  # "memory" or document path
    relevance_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Result of knowledge retrieval."""
    query: str
    memory_hits: List[KnowledgeChunk]
    document_hits: List[KnowledgeChunk]
    total_hits: int
    
    def get_context(self, max_tokens: int = 2000) -> str:
        """Get combined context for LLM prompt."""
        context_parts = []
        
        # Memory knowledge first (most trusted)
        if self.memory_hits:
            context_parts.append("FROM IRA'S MEMORY:")
            for hit in self.memory_hits[:5]:
                context_parts.append(f"  • {hit.content}")
        
        # Document knowledge
        if self.document_hits:
            context_parts.append("\nFROM DOCUMENTS:")
            for hit in self.document_hits[:5]:
                source_name = Path(hit.source).stem if hit.source != "memory" else "memory"
                context_parts.append(f"  [{source_name}]: {hit.content[:500]}")
        
        return "\n".join(context_parts)[:max_tokens * 4]  # Rough char estimate
    
    def has_knowledge(self) -> bool:
        """Check if any knowledge was found."""
        return self.total_hits > 0


class KnowledgeRetriever:
    """
    Ira's knowledge retrieval system.
    
    Search flow:
    1. Query Mem0 for relevant memories
    2. Search document embeddings (if available)
    3. Fall back to keyword search in PDFs
    4. Rank and return top results
    """
    
    def __init__(self):
        self.mem0_client = None
        self.document_cache: Dict[str, str] = {}
        self._init_mem0()
    
    def _init_mem0(self):
        """Initialize Mem0 client."""
        try:
            from mem0 import MemoryClient
            api_key = os.environ.get("MEM0_API_KEY")
            if api_key:
                self.mem0_client = MemoryClient(api_key=api_key)
        except Exception as e:
            print(f"[knowledge_retriever] Mem0 not available: {e}")
    
    def retrieve(
        self,
        query: str,
        user_id: str = "system_ira",
        search_docs: bool = True,
        max_results: int = 10,
    ) -> RetrievalResult:
        """
        Retrieve knowledge relevant to a query.
        
        Args:
            query: What to search for (e.g., "hotmelt adhesive")
            user_id: Mem0 user ID to search
            search_docs: Whether to also search documents
            max_results: Max results to return
            
        Returns:
            RetrievalResult with memory and document hits
        """
        print(f"\n[knowledge_retriever] Searching for: '{query[:50]}...'")
        
        memory_hits = []
        document_hits = []
        
        # Step 1: Search Mem0 memory
        memory_hits = self._search_memory(query, user_id)
        
        # Filter memory hits to only those actually relevant (score > 0.5)
        relevant_memory_hits = [h for h in memory_hits if h.relevance_score > 0.5]
        print(f"  Memory hits: {len(memory_hits)} (relevant: {len(relevant_memory_hits)})")
        
        # Step 2: ALWAYS search documents for technical topics (hotmelt, adhesive, lamination, etc.)
        technical_terms = ['hotmelt', 'adhesive', 'lamination', 'vacuum', 'thermoform', 
                          'frimo', 'img', 'foil', 'substrate', 'heating', 'emitter']
        is_technical = any(term in query.lower() for term in technical_terms)
        
        if search_docs and (len(relevant_memory_hits) < 3 or is_technical):
            print(f"  Searching documents (technical query: {is_technical})...")
            document_hits = self._search_documents(query)
            print(f"  Document hits: {len(document_hits)}")
        
        # Combine and rank - use relevant memory hits only
        all_hits = relevant_memory_hits + document_hits
        all_hits.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return RetrievalResult(
            query=query,
            memory_hits=relevant_memory_hits[:max_results],
            document_hits=document_hits[:max_results],
            total_hits=len(all_hits),
        )
    
    def _search_memory(self, query: str, user_id: str) -> List[KnowledgeChunk]:
        """Search Mem0 memory."""
        if not self.mem0_client:
            return []
        
        try:
            # Search both user-specific and system memories
            results = self.mem0_client.search(
                query=query,
                version="v2",
                filters={"user_id": user_id},
                top_k=10,
            )
            
            hits = []
            memories = results.get("memories", results.get("results", []))
            
            for mem in memories:
                hits.append(KnowledgeChunk(
                    content=mem.get("memory", ""),
                    source="memory",
                    relevance_score=mem.get("score", 0.5),
                    metadata={"memory_id": mem.get("id")},
                ))
            
            # Also search system-wide knowledge
            system_results = self.mem0_client.search(
                query=query,
                version="v2",
                filters={"user_id": "system_ira"},
                top_k=10,
            )
            
            for mem in system_results.get("memories", system_results.get("results", [])):
                hits.append(KnowledgeChunk(
                    content=mem.get("memory", ""),
                    source="memory",
                    relevance_score=mem.get("score", 0.5),
                    metadata={"memory_id": mem.get("id"), "system": True},
                ))
            
            return hits
            
        except Exception as e:
            print(f"  Memory search error: {e}")
            return []
    
    def _search_documents(self, query: str) -> List[KnowledgeChunk]:
        """Search documents in the imports folder."""
        hits = []
        
        # Extract key terms from query
        key_terms = self._extract_key_terms(query)
        print(f"  Key terms: {key_terms}")
        
        # Search PDFs
        pdf_hits = self._search_pdfs(key_terms, query)
        hits.extend(pdf_hits)
        
        return hits
    
    def _extract_key_terms(self, query: str) -> List[str]:
        """Extract key search terms from query."""
        # Remove common words
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                     'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                     'through', 'during', 'before', 'after', 'above', 'below',
                     'between', 'under', 'again', 'further', 'then', 'once',
                     'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either',
                     'neither', 'not', 'only', 'own', 'same', 'than', 'too',
                     'very', 'just', 'about', 'this', 'that', 'these', 'those',
                     'what', 'which', 'who', 'whom', 'how', 'when', 'where', 'why'}
        
        words = re.findall(r'\b\w+\b', query.lower())
        key_terms = [w for w in words if w not in stopwords and len(w) > 2]
        
        return key_terms[:10]  # Top 10 terms
    
    def _search_pdfs(self, key_terms: List[str], full_query: str) -> List[KnowledgeChunk]:
        """Search PDFs for relevant content - searches CONTENT, not just filenames."""
        hits = []
        
        if not IMPORTS_DIR.exists():
            return hits
        
        # Find all PDFs
        pdf_files = list(IMPORTS_DIR.glob("**/*.pdf"))
        print(f"  Scanning {len(pdf_files)} PDFs for content...")
        
        # Priority PDFs - known technical documentation
        priority_keywords = ['frimo', 'thermoform', 'technical', 'technology', 'manual', 'guide']
        
        # Sort PDFs - priority ones first
        def pdf_priority(p):
            name_lower = p.stem.lower()
            for i, kw in enumerate(priority_keywords):
                if kw in name_lower:
                    return i
            return 100
        
        pdf_files.sort(key=pdf_priority)
        
        for pdf_path in pdf_files[:30]:  # Limit to top 30 for speed
            try:
                # Extract and search content
                content = self._extract_pdf_content(pdf_path)
                if not content:
                    continue
                
                # Score based on term frequency IN CONTENT
                score = self._score_content(content, key_terms)
                
                if score > 0.05:  # Lower threshold - search content not just filenames
                    print(f"    Found relevant: {pdf_path.name} (score: {score:.2f})")
                    
                    # Extract relevant sections
                    relevant_sections = self._extract_relevant_sections(content, key_terms)
                    for section in relevant_sections[:3]:
                        hits.append(KnowledgeChunk(
                            content=section,
                            source=str(pdf_path),
                            relevance_score=score,
                            metadata={"filename": pdf_path.name},
                        ))
                        
            except Exception as e:
                pass  # Skip problematic PDFs silently
        
        return hits
    
    def _extract_pdf_content(self, pdf_path: Path) -> str:
        """Extract text content from PDF using shared DocumentExtractor."""
        # Check local cache first
        cache_key = str(pdf_path)
        if cache_key in self.document_cache:
            return self.document_cache[cache_key]
        
        # Use shared extractor (has its own cache + fallback chain)
        result = _doc_extractor.extract(pdf_path)
        if result.success:
            self.document_cache[cache_key] = result.text
            return result.text
        return ""
    
    def _score_content(self, content: str, key_terms: List[str]) -> float:
        """Score content relevance based on term frequency."""
        content_lower = content.lower()
        
        matches = sum(1 for term in key_terms if term in content_lower)
        
        # Bonus for exact phrase matches
        phrase_bonus = 0
        for i in range(len(key_terms) - 1):
            phrase = f"{key_terms[i]} {key_terms[i+1]}"
            if phrase in content_lower:
                phrase_bonus += 0.2
        
        return min(1.0, (matches / max(len(key_terms), 1)) + phrase_bonus)
    
    def _extract_relevant_sections(self, content: str, key_terms: List[str], window: int = 500) -> List[str]:
        """Extract sections of content most relevant to key terms."""
        sections = []
        content_lower = content.lower()
        
        for term in key_terms:
            # Find all occurrences
            idx = 0
            while True:
                idx = content_lower.find(term, idx)
                if idx == -1:
                    break
                
                # Extract window around term
                start = max(0, idx - window // 2)
                end = min(len(content), idx + window // 2)
                
                section = content[start:end].strip()
                
                # Clean up section
                section = re.sub(r'\s+', ' ', section)
                
                if len(section) > 50 and section not in sections:
                    sections.append(section)
                
                idx += 1
                
                if len(sections) >= 5:
                    break
            
            if len(sections) >= 5:
                break
        
        return sections


# =============================================================================
# CRM/LEADS DATABASE SEARCH
# =============================================================================

class LeadsKnowledgeSource:
    """Search CRM/Leads data as a knowledge source."""
    
    def __init__(self):
        self.leads_db = None
        self._init_leads_db()
    
    def _init_leads_db(self):
        """Initialize leads database."""
        try:
            from leads_database import get_leads_db
            self.leads_db = get_leads_db()
        except Exception as e:
            print(f"[knowledge_retriever] Leads database not available: {e}")
    
    def search(self, query: str) -> List[KnowledgeChunk]:
        """Search leads database for relevant contacts."""
        if not self.leads_db:
            return []
        
        hits = []
        query_lower = query.lower()
        
        # Detect if this is a leads-related query
        leads_keywords = ['lead', 'leads', 'contact', 'contacts', 'prospect', 'customer', 'client']
        region_keywords = ['europe', 'european', 'germany', 'france', 'austria', 'uk', 'us', 'usa']
        
        is_leads_query = any(kw in query_lower for kw in leads_keywords)
        
        if not is_leads_query:
            return []
        
        print(f"  [leads] Searching CRM database...")
        
        # Determine filters from query
        region = None
        country = None
        hot_only = 'hot' in query_lower or 'active' in query_lower or 'warm' in query_lower
        
        if 'europe' in query_lower or 'european' in query_lower:
            region = "Europe"
        elif 'us' in query_lower or 'usa' in query_lower:
            region = "US"
        
        # Check for specific countries
        country_map = {
            'germany': 'Germany', 'france': 'France', 'austria': 'Austria',
            'italy': 'Italy', 'spain': 'Spain', 'uk': 'United Kingdom',
            'belgium': 'Belgium', 'netherlands': 'Netherlands', 'poland': 'Poland',
        }
        for kw, c in country_map.items():
            if kw in query_lower:
                country = c
                break
        
        # Query leads
        try:
            leads = self.leads_db.query(
                region=region,
                country=country,
                hot_only=hot_only,
                limit=15,
            )
            
            print(f"  [leads] Found {len(leads)} matching leads")
            
            for lead in leads:
                # Format lead info as knowledge chunk
                info_parts = [f"{lead.full_name} at {lead.company} ({lead.country})"]
                info_parts.append(f"Email: {lead.email}")
                if lead.meeting_info:
                    info_parts.append(f"Meeting: {lead.meeting_info}")
                if lead.quotes:
                    info_parts.append(f"Quote: {lead.quotes}")
                if lead.comments:
                    info_parts.append(f"Notes: {lead.comments}")
                
                hits.append(KnowledgeChunk(
                    content="\n".join(info_parts),
                    source="crm_leads",
                    relevance_score=0.9 if lead.is_hot else 0.7,
                    metadata={
                        "name": lead.full_name,
                        "company": lead.company,
                        "country": lead.country,
                        "email": lead.email,
                    },
                ))
        except Exception as e:
            print(f"  [leads] Search error: {e}")
        
        return hits


# Add leads to KnowledgeRetriever
KnowledgeRetriever._leads_source = None

def _get_leads_source(self) -> LeadsKnowledgeSource:
    """Get or create leads knowledge source."""
    if KnowledgeRetriever._leads_source is None:
        KnowledgeRetriever._leads_source = LeadsKnowledgeSource()
    return KnowledgeRetriever._leads_source

KnowledgeRetriever._get_leads_source = _get_leads_source

# Extend retrieve method to include leads
_original_retrieve = KnowledgeRetriever.retrieve

def _extended_retrieve(
    self,
    query: str,
    user_id: str = "system_ira",
    search_docs: bool = True,
    max_results: int = 10,
) -> RetrievalResult:
    """Extended retrieve that also searches CRM/leads data."""
    # Get original result
    result = _original_retrieve(self, query, user_id, search_docs, max_results)
    
    # Also search leads database
    leads_source = self._get_leads_source()
    leads_hits = leads_source.search(query)
    
    if leads_hits:
        print(f"  [retriever] Adding {len(leads_hits)} leads to results")
        # Add leads as document hits (they're structured data)
        result.document_hits = leads_hits + result.document_hits
        result.total_hits += len(leads_hits)
    
    return result

KnowledgeRetriever.retrieve = _extended_retrieve


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def retrieve_knowledge(query: str, user_id: str = "system_ira") -> RetrievalResult:
    """Quick knowledge retrieval."""
    retriever = KnowledgeRetriever()
    return retriever.retrieve(query, user_id)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("KNOWLEDGE RETRIEVER TEST")
    print("=" * 60)
    
    retriever = KnowledgeRetriever()
    
    # Test query
    result = retriever.retrieve("hotmelt adhesive lamination thermoforming")
    
    print(f"\nQuery: '{result.query}'")
    print(f"Total hits: {result.total_hits}")
    print(f"Memory hits: {len(result.memory_hits)}")
    print(f"Document hits: {len(result.document_hits)}")
    
    print("\n" + "=" * 60)
    print("CONTEXT FOR LLM:")
    print("=" * 60)
    print(result.get_context())
