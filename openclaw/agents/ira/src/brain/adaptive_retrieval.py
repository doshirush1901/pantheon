#!/usr/bin/env python3
"""
ADAPTIVE LEARNING RETRIEVAL - Self-Improving Knowledge System
==============================================================

When Ira doesn't know the answer:
1. PREDICT which document likely contains the answer
2. SEARCH that specific document
3. EXTRACT the answer using LLM
4. STORE in memory for future queries
5. RESPOND with the correct data

This creates a closed-loop learning system that gets smarter over time.
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    from .document_extractor import DocumentExtractor
except ImportError:
    from document_extractor import DocumentExtractor

IMPORTS_DIR = PROJECT_ROOT / "data" / "imports"

# Shared extractor instance
_doc_extractor = DocumentExtractor()

# =============================================================================
# QUERY CLASSIFICATION - What type of information is being requested?
# =============================================================================

QUERY_TYPES = {
    "financial": {
        "patterns": [
            r"turnover|revenue|sales|profit|margin|growth|financial",
            r"crores?|lakhs?|million|billion|rs\.?|₹|\$",
            r"last year|this year|FY\d{2}|20\d{2}",
            r"how much.*(?:make|earn|revenue|turnover)",
        ],
        "documents": [
            "Evolution and Performance",
            "Financial",
            "Annual Report",
            "Company Overview",
        ],
        "priority_fields": ["turnover", "revenue", "profit", "growth"],
    },
    "product_specs": {
        "patterns": [
            r"PF\d|AM[-\s]?\d|RE[-\s]?\d",
            r"specification|spec|dimension|size|capacity",
            r"forming area|platen|heater|tonnage",
            r"model|series|machine type",
        ],
        "documents": [
            "Catalogue",
            "PF1",
            "Quotation",
            "Specifications",
        ],
        "priority_fields": ["forming_area", "dimensions", "capacity", "price"],
    },
    "company_history": {
        "patterns": [
            r"history|founded|started|began|origin",
            r"1976|founder|BP Doshi|Deepak|Rajesh",
            r"how old|when did|milestone",
        ],
        "documents": [
            "Evolution and Performance",
            "History",
            "Company Story",
            "About",
        ],
        "priority_fields": ["founding_year", "founders", "milestones"],
    },
    "customer_info": {
        "patterns": [
            r"customer|client|buyer|who bought",
            r"use case|application|using our",
            r"reference|installation|delivered",
        ],
        "documents": [
            "Customer",
            "Reference",
            "Installation",
            "Case Study",
        ],
        "priority_fields": ["customer_name", "application", "machine_installed"],
    },
    "competitor": {
        "patterns": [
            r"competitor|competition|vs|versus|compare",
            r"formech|illig|kiefel|ridat",
            r"market share|industry position",
        ],
        "documents": [
            "Market Research",
            "Competition",
            "Industry Analysis",
        ],
        "priority_fields": ["competitor_name", "comparison", "advantage"],
    },
}


@dataclass
class QueryClassification:
    """Result of query classification."""
    query_type: str
    confidence: float
    predicted_documents: List[str]
    priority_fields: List[str]
    matched_patterns: List[str]


@dataclass
class ExtractionResult:
    """Result of extracting answer from document."""
    found: bool
    answer: str
    source_document: str
    extracted_facts: Dict[str, Any]
    confidence: float


@dataclass
class LearnedFact:
    """A fact learned from documents."""
    fact_id: str
    query_type: str
    question_pattern: str
    answer: str
    source_document: str
    extracted_at: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "fact_id": self.fact_id,
            "query_type": self.query_type,
            "question_pattern": self.question_pattern,
            "answer": self.answer,
            "source_document": self.source_document,
            "extracted_at": self.extracted_at,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


# =============================================================================
# ADAPTIVE RETRIEVAL ENGINE
# =============================================================================

class AdaptiveRetriever:
    """
    Self-improving retrieval system that learns from documents on-the-fly.
    """
    
    def __init__(self):
        self.learned_facts_file = BRAIN_DIR / "learned_facts.json"
        self.learned_facts: Dict[str, LearnedFact] = {}
        self._load_facts()
        self._pdf_cache: Dict[str, str] = {}
    
    def _load_facts(self):
        """Load previously learned facts."""
        if self.learned_facts_file.exists():
            try:
                data = json.loads(self.learned_facts_file.read_text())
                for f in data.get("facts", []):
                    fact = LearnedFact(**f)
                    self.learned_facts[fact.fact_id] = fact
            except Exception as e:
                print(f"[AdaptiveRetriever] Load error: {e}")
    
    def _save_facts(self):
        """Save learned facts."""
        try:
            data = {
                "facts": [f.to_dict() for f in self.learned_facts.values()],
                "last_updated": datetime.now().isoformat(),
            }
            self.learned_facts_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[AdaptiveRetriever] Save error: {e}")
    
    # =========================================================================
    # STEP 1: CLASSIFY QUERY
    # =========================================================================
    
    def classify_query(self, query: str) -> QueryClassification:
        """Classify what type of information the query is asking for."""
        query_lower = query.lower()
        
        best_type = "general"
        best_score = 0.0
        matched_patterns = []
        
        for qtype, config in QUERY_TYPES.items():
            score = 0.0
            matches = []
            
            for pattern in config["patterns"]:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    score += 1.0
                    matches.append(pattern)
            
            # Normalize by number of patterns
            normalized_score = score / len(config["patterns"]) if config["patterns"] else 0
            
            if normalized_score > best_score:
                best_score = normalized_score
                best_type = qtype
                matched_patterns = matches
        
        config = QUERY_TYPES.get(best_type, {"documents": [], "priority_fields": []})
        
        return QueryClassification(
            query_type=best_type,
            confidence=min(best_score * 1.5, 1.0),  # Scale up confidence
            predicted_documents=config.get("documents", []),
            priority_fields=config.get("priority_fields", []),
            matched_patterns=matched_patterns,
        )
    
    # =========================================================================
    # STEP 2: CHECK IF WE ALREADY KNOW THE ANSWER
    # =========================================================================
    
    def check_learned_facts(self, query: str, query_type: str) -> Optional[LearnedFact]:
        """Check if we've already learned the answer to this query."""
        query_lower = query.lower()
        
        # Check exact match first
        for fact in self.learned_facts.values():
            if fact.query_type == query_type:
                # Check if question pattern matches
                if re.search(fact.question_pattern, query_lower, re.IGNORECASE):
                    print(f"[AdaptiveRetriever] Found learned fact: {fact.fact_id}")
                    return fact
        
        return None
    
    # =========================================================================
    # STEP 3: PREDICT AND FIND DOCUMENT
    # =========================================================================
    
    def find_relevant_documents(self, predicted_docs: List[str]) -> List[Path]:
        """Find actual documents matching the predicted document types."""
        if not IMPORTS_DIR.exists():
            print(f"[AdaptiveRetriever] Imports directory not found: {IMPORTS_DIR}")
            return []
        
        found_docs = []
        _scannable = {".pdf", ".xlsx", ".xls", ".docx", ".doc", ".csv", ".txt", ".pptx", ".md", ".json"}

        for doc_path in IMPORTS_DIR.rglob("*"):
            if not doc_path.is_file() or doc_path.suffix.lower() not in _scannable:
                continue
            filename = doc_path.stem.lower()

            for pred in predicted_docs:
                if pred.lower() in filename:
                    found_docs.append(doc_path)
                    break
        
        # Sort by modification time (most recent first)
        found_docs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        return found_docs[:5]  # Top 5 most relevant
    
    # =========================================================================
    # STEP 4: EXTRACT CONTENT FROM PDF
    # =========================================================================
    
    def extract_pdf_content(self, pdf_path: Path) -> str:
        """Extract text content from PDF using shared DocumentExtractor."""
        # Check local cache first
        cache_key = str(pdf_path)
        if cache_key in self._pdf_cache:
            return self._pdf_cache[cache_key]
        
        # Use shared extractor (has its own cache + fallback chain)
        result = _doc_extractor.extract(pdf_path)
        if result.success:
            self._pdf_cache[cache_key] = result.text
            return result.text
        
        print(f"[AdaptiveRetriever] PDF extraction failed: {result.error}")
        return ""
    
    # =========================================================================
    # STEP 5: USE LLM TO EXTRACT ANSWER
    # =========================================================================
    
    def extract_answer_with_llm(
        self,
        query: str,
        document_content: str,
        query_type: str,
        priority_fields: List[str],
    ) -> ExtractionResult:
        """Use LLM to extract the specific answer from document content."""
        
        # Truncate content if too long
        max_content = 8000
        if len(document_content) > max_content:
            # Try to find relevant section first
            relevant_section = self._find_relevant_section(query, document_content)
            if relevant_section:
                document_content = relevant_section
            else:
                document_content = document_content[:max_content]
        
        prompt = f"""You are extracting specific facts from a document to answer a question.

QUESTION: {query}

DOCUMENT CONTENT:
{document_content}

INSTRUCTIONS:
1. Find the EXACT answer to the question in the document
2. Extract specific numbers, dates, names - not vague summaries
3. If the answer has numbers (revenue, turnover, etc.), include the EXACT figure
4. If not found, say "NOT_FOUND"

Respond in JSON format:
{{
    "found": true/false,
    "answer": "The exact answer with specific numbers/facts",
    "confidence": 0.0-1.0,
    "extracted_facts": {{
        "key1": "value1",
        "key2": "value2"
    }}
}}

IMPORTANT: Include exact numbers like "₹50 crores" or "$2 million" - don't round or estimate."""

        try:
            from openai import OpenAI
            
            client = OpenAI()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return ExtractionResult(
                found=result.get("found", False),
                answer=result.get("answer", ""),
                source_document="",  # Will be set by caller
                extracted_facts=result.get("extracted_facts", {}),
                confidence=result.get("confidence", 0.0),
            )
        except Exception as e:
            print(f"[AdaptiveRetriever] LLM extraction error: {e}")
            return ExtractionResult(
                found=False,
                answer="",
                source_document="",
                extracted_facts={},
                confidence=0.0,
            )
    
    def _find_relevant_section(self, query: str, content: str) -> str:
        """Find the section of content most relevant to the query."""
        query_lower = query.lower()
        
        # Extract key terms
        key_terms = []
        for word in query_lower.split():
            if len(word) > 3 and word not in ['what', 'when', 'where', 'which', 'how', 'much', 'many', 'does', 'did']:
                key_terms.append(word)
        
        if not key_terms:
            return ""
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        
        # Score each paragraph
        scored = []
        for para in paragraphs:
            para_lower = para.lower()
            score = sum(1 for term in key_terms if term in para_lower)
            if score > 0:
                scored.append((score, para))
        
        # Get top paragraphs
        scored.sort(key=lambda x: x[0], reverse=True)
        top_paras = [p for _, p in scored[:10]]
        
        return "\n\n".join(top_paras)
    
    # =========================================================================
    # STEP 6: STORE LEARNED FACT
    # =========================================================================
    
    def store_learned_fact(
        self,
        query: str,
        query_type: str,
        answer: str,
        source_document: str,
        extracted_facts: Dict[str, Any],
        confidence: float,
    ) -> LearnedFact:
        """Store a newly learned fact for future use."""
        
        # Generate a pattern that would match similar queries
        question_pattern = self._generate_question_pattern(query, query_type)
        
        fact_id = f"{query_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        fact = LearnedFact(
            fact_id=fact_id,
            query_type=query_type,
            question_pattern=question_pattern,
            answer=answer,
            source_document=source_document,
            extracted_at=datetime.now().isoformat(),
            confidence=confidence,
            metadata=extracted_facts,
        )
        
        self.learned_facts[fact_id] = fact
        self._save_facts()
        
        # Also store in Mem0 for cross-session persistence
        self._store_in_mem0(fact)
        
        print(f"[AdaptiveRetriever] Stored fact: {fact_id}")
        return fact
    
    def _generate_question_pattern(self, query: str, query_type: str) -> str:
        """Generate a regex pattern to match similar questions."""
        query_lower = query.lower()
        
        if query_type == "financial":
            if "turnover" in query_lower:
                return r"turnover|revenue|sales.*(?:last year|20\d{2}|annual)"
            if "profit" in query_lower:
                return r"profit|margin|earnings"
            if "growth" in query_lower:
                return r"growth|increase|grew"
        
        # Default: use key words from query
        words = [w for w in query_lower.split() if len(w) > 4]
        if words:
            return r"|".join(words[:3])
        
        return query_lower
    
    def _store_in_mem0(self, fact: LearnedFact):
        """Store fact in Mem0 for persistence."""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent / "memory"))
            from mem0_memory import get_mem0_service
            
            mem0 = get_mem0_service()
            mem0.add_memory(
                text=f"FACT: {fact.answer} (Source: {fact.source_document})",
                user_id="system_ira",
                metadata={
                    "type": "learned_fact",
                    "query_type": fact.query_type,
                    "source": fact.source_document,
                }
            )
        except Exception as e:
            print(f"[AdaptiveRetriever] Mem0 storage error: {e}")
    
    # =========================================================================
    # MAIN ENTRY POINT: ADAPTIVE RETRIEVAL
    # =========================================================================
    
    def retrieve(self, query: str, context: Dict = None) -> Tuple[str, Dict]:
        """
        Main entry point for adaptive retrieval.
        
        Returns:
            Tuple of (answer, metadata)
        """
        print(f"[AdaptiveRetriever] Query: {query}")
        
        # Step 1: Classify query
        classification = self.classify_query(query)
        print(f"[AdaptiveRetriever] Type: {classification.query_type} (conf: {classification.confidence:.2f})")
        
        if classification.confidence < 0.3:
            return "", {"status": "low_confidence_classification"}
        
        # Step 2: Check if we already know the answer
        existing_fact = self.check_learned_facts(query, classification.query_type)
        if existing_fact:
            return existing_fact.answer, {
                "status": "from_memory",
                "source": existing_fact.source_document,
                "confidence": existing_fact.confidence,
                "fact_id": existing_fact.fact_id,
            }
        
        # Step 3: Find relevant documents
        docs = self.find_relevant_documents(classification.predicted_documents)
        print(f"[AdaptiveRetriever] Found {len(docs)} potentially relevant documents")
        
        if not docs:
            return "", {"status": "no_documents_found"}
        
        # Step 4: Search through documents
        for doc_path in docs:
            print(f"[AdaptiveRetriever] Searching: {doc_path.name}")
            
            content = self.extract_pdf_content(doc_path)
            if not content:
                continue
            
            # Step 5: Extract answer with LLM
            result = self.extract_answer_with_llm(
                query=query,
                document_content=content,
                query_type=classification.query_type,
                priority_fields=classification.priority_fields,
            )
            
            if result.found and result.confidence > 0.5:
                result.source_document = doc_path.name
                
                # Step 6: Store for future use
                fact = self.store_learned_fact(
                    query=query,
                    query_type=classification.query_type,
                    answer=result.answer,
                    source_document=doc_path.name,
                    extracted_facts=result.extracted_facts,
                    confidence=result.confidence,
                )
                
                return result.answer, {
                    "status": "extracted_and_learned",
                    "source": doc_path.name,
                    "confidence": result.confidence,
                    "fact_id": fact.fact_id,
                    "extracted_facts": result.extracted_facts,
                }
        
        return "", {"status": "not_found_in_documents"}


# =============================================================================
# SINGLETON AND CONVENIENCE FUNCTIONS
# =============================================================================

_retriever: Optional[AdaptiveRetriever] = None


def get_adaptive_retriever() -> AdaptiveRetriever:
    """Get or create adaptive retriever singleton."""
    global _retriever
    if _retriever is None:
        _retriever = AdaptiveRetriever()
    return _retriever


def adaptive_retrieve(query: str, context: Dict = None) -> Tuple[str, Dict]:
    """Convenience function for adaptive retrieval."""
    return get_adaptive_retriever().retrieve(query, context)


# =============================================================================
# CLI FOR TESTING
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python adaptive_retrieval.py <query>")
        print("Example: python adaptive_retrieval.py 'What was our turnover last year?'")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    
    retriever = get_adaptive_retriever()
    answer, metadata = retriever.retrieve(query)
    
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    print(f"Answer: {answer}")
    print(f"Status: {metadata.get('status')}")
    print(f"Source: {metadata.get('source', 'N/A')}")
    print(f"Confidence: {metadata.get('confidence', 0):.2f}")
