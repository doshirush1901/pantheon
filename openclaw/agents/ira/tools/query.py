"""
Ira Query Tool - RAG-based knowledge retrieval

Retrieves relevant information from Ira's knowledge base including:
- Product documentation (machines, specs, pricing)
- Email history
- Customer data
- Market research

Usage:
    from openclaw.agents.ira.tools import ira_query
    
    result = ira_query("What is the price of PF1?")
    print(result.answer)
    print(result.sources)
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOLS_DIR = Path(__file__).parent
AGENT_DIR = TOOLS_DIR.parent
SKILLS_DIR = AGENT_DIR / "skills"
BRAIN_DIR = SKILLS_DIR / "brain"

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))


@dataclass
class QueryResult:
    """Result from a query operation."""
    answer: str
    confidence: float = 0.0
    sources: List[Dict[str, Any]] = field(default_factory=list)
    raw_chunks: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0


class IraQueryTool:
    """
    Tool for querying Ira's knowledge base.
    
    Supports:
    - RAG retrieval with reranking
    - Product-specific lookups
    - Customer context awareness
    """
    
    def __init__(self, user_id: str = "tool_user"):
        self.user_id = user_id
        self._agent = None
    
    def _get_agent(self):
        if self._agent is None:
            try:
                from agent import get_agent
                self._agent = get_agent()
            except ImportError:
                self._agent = None
        return self._agent
    
    def query(
        self,
        question: str,
        context: Optional[str] = None,
        include_sources: bool = True,
    ) -> QueryResult:
        """
        Query Ira's knowledge base.
        
        Args:
            question: The question to answer
            context: Optional context to include
            include_sources: Whether to include source citations
            
        Returns:
            QueryResult with answer and sources
        """
        import time
        start = time.time()
        
        agent = self._get_agent()
        
        if agent:
            response = agent.process(
                message=question,
                channel="api",
                user_id=self.user_id,
            )
            
            return QueryResult(
                answer=response.message,
                confidence=response.confidence,
                sources=[{"text": c} for c in (response.rag_chunks_used or [])],
                processing_time_ms=(time.time() - start) * 1000,
            )
        
        # Fallback to direct RAG
        try:
            from qdrant_retriever import retrieve
            from generate_answer import generate_answer, ContextPack
            
            rag_result = retrieve(question, top_k=5)
            
            context_pack = ContextPack(
                current_message=question,
                recent_messages=[],
                key_entities={},
                rag_chunks=[c.text for c in rag_result.citations],
            )
            
            response = generate_answer(context_pack, channel="api")
            
            return QueryResult(
                answer=response.text,
                confidence=response.confidence,
                sources=[{"text": c.text, "file": c.filename} for c in rag_result.citations],
                raw_chunks=[c.text for c in rag_result.citations],
                processing_time_ms=(time.time() - start) * 1000,
            )
            
        except Exception as e:
            return QueryResult(
                answer=f"Query failed: {e}",
                confidence=0.0,
                processing_time_ms=(time.time() - start) * 1000,
            )


def ira_query(
    question: str,
    context: Optional[str] = None,
    user_id: str = "tool_user",
) -> QueryResult:
    """
    Query Ira's knowledge base.
    
    Args:
        question: The question to answer
        context: Optional context
        user_id: User identifier for memory
        
    Returns:
        QueryResult with answer and sources
    """
    tool = IraQueryTool(user_id=user_id)
    return tool.query(question, context=context)
