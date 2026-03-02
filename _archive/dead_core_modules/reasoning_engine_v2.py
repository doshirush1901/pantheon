#!/usr/bin/env python3
"""
REASONING ENGINE V2 - World-Class AI Reasoning for Ira
=======================================================

Implements state-of-the-art patterns from AI research:

1. ReAct Pattern (Google/Princeton)
   - Thought → Action → Observation loop
   - Explicit reasoning traces
   - Self-correction on failures

2. Self-Consistency (Google Research)
   - Sample multiple reasoning paths
   - Vote on most consistent answer
   - +17% accuracy on complex tasks

3. Reflection Loop (LangGraph)
   - Generate → Critique → Refine
   - Self-improvement before responding

4. Query Decomposition
   - Break complex queries into sub-questions
   - Multi-hop reasoning

5. Working Memory (Scratchpad)
   - Track what we've learned
   - Accumulate evidence

6. Parallel Tool Execution
   - Run multiple searches simultaneously
   - asyncio-based concurrency

7. Tool Success Learning
   - Track which tools work for which queries
   - Adaptive tool selection

8. Semantic Caching
   - Cache similar queries via embeddings
   - Fast retrieval for near-duplicates

9. Streaming Responses
   - Stream tokens for long answers
   - Better UX for users

10. Multi-Agent Debate
    - Two agents argue for best answer
    - Devil's advocate pattern

References:
- ReAct: https://arxiv.org/abs/2210.03629
- Self-Consistency: https://arxiv.org/abs/2203.11171
- DSPy: https://github.com/stanfordnlp/dspy
- Reflexion: https://arxiv.org/abs/2303.11366
- Debate: https://arxiv.org/abs/1805.00899

Usage:
    from reasoning_engine_v2 import ReActReasoner, reason_with_react
    
    reasoner = ReActReasoner()
    result = reasoner.reason("What are the hot leads in Germany we can follow up?")
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable, Generator, Iterator

logger = logging.getLogger(__name__)

BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))
sys.path.insert(0, str(SKILLS_DIR / "memory"))

try:
    from config import PROJECT_ROOT, get_openai_client, FAST_LLM_MODEL
except ImportError:
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
    get_openai_client = None
    FAST_LLM_MODEL = "gpt-4o-mini"


# =============================================================================
# CORE DATA STRUCTURES
# =============================================================================

class ActionType(str, Enum):
    """Actions the reasoner can take."""
    SEARCH_MEMORY = "search_memory"
    SEARCH_CRM = "search_crm"
    SEARCH_DOCUMENTS = "search_documents"
    SEARCH_PRICING = "search_pricing"
    ASK_CLARIFICATION = "ask_clarification"
    CALCULATE = "calculate"
    FINISH = "finish"


@dataclass
class Thought:
    """A reasoning step - what the agent is thinking."""
    step: int
    content: str
    confidence: float = 0.0


@dataclass
class Action:
    """An action to take."""
    action_type: ActionType
    query: str
    reasoning: str = ""


@dataclass
class Observation:
    """Result of an action."""
    action: Action
    result: str
    success: bool
    source: str = ""


@dataclass
class ReasoningTrace:
    """Complete trace of the reasoning process."""
    query: str
    thoughts: List[Thought] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    observations: List[Observation] = field(default_factory=list)
    
    # Working memory - accumulated knowledge
    scratchpad: Dict[str, Any] = field(default_factory=dict)
    
    # Final result
    final_answer: Optional[str] = None
    confidence: float = 0.0
    needs_clarification: bool = False
    clarifying_question: Optional[str] = None
    
    # Metadata
    iterations: int = 0
    total_time_ms: float = 0.0
    
    def add_thought(self, content: str, confidence: float = 0.0):
        self.thoughts.append(Thought(
            step=len(self.thoughts) + 1,
            content=content,
            confidence=confidence,
        ))
    
    def add_to_scratchpad(self, key: str, value: Any):
        """Add to working memory."""
        if key not in self.scratchpad:
            self.scratchpad[key] = []
        self.scratchpad[key].append(value)
    
    def get_context(self) -> str:
        """Get accumulated context from scratchpad."""
        parts = []
        for key, values in self.scratchpad.items():
            if values:
                parts.append(f"[{key.upper()}]")
                for v in values[:5]:  # Limit per category
                    parts.append(f"  • {str(v)[:200]}")
        return "\n".join(parts)
    
    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "thoughts": [{"step": t.step, "content": t.content} for t in self.thoughts],
            "actions": [{"type": a.action_type.value, "query": a.query} for a in self.actions],
            "observations": len(self.observations),
            "final_answer": self.final_answer[:200] if self.final_answer else None,
            "confidence": self.confidence,
            "iterations": self.iterations,
            "time_ms": self.total_time_ms,
        }


# =============================================================================
# TOOLS REGISTRY - What actions Ira can take
# =============================================================================

class ToolRegistry:
    """Registry of tools the reasoner can use."""
    
    def __init__(self):
        self.tools: Dict[ActionType, Callable] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register built-in tools."""
        self.tools[ActionType.SEARCH_MEMORY] = self._search_memory
        self.tools[ActionType.SEARCH_CRM] = self._search_crm
        self.tools[ActionType.SEARCH_DOCUMENTS] = self._search_documents
        self.tools[ActionType.SEARCH_PRICING] = self._search_pricing
    
    def execute(self, action: Action) -> Observation:
        """Execute an action and return observation."""
        tool = self.tools.get(action.action_type)
        if not tool:
            return Observation(
                action=action,
                result=f"Unknown action: {action.action_type}",
                success=False,
            )
        
        try:
            result, source = tool(action.query)
            return Observation(
                action=action,
                result=result,
                success=bool(result),
                source=source,
            )
        except Exception as e:
            logger.error("Tool execution error: %s", e)
            return Observation(
                action=action,
                result=f"Error: {str(e)}",
                success=False,
            )
    
    def _search_memory(self, query: str) -> Tuple[str, str]:
        """Search Mem0 memory."""
        try:
            from mem0 import MemoryClient
            api_key = os.environ.get("MEM0_API_KEY")
            if not api_key:
                return "", "memory"
            
            client = MemoryClient(api_key=api_key)
            # Mem0 v2 API requires filters - use user_id filter
            results = client.search(
                query=query,
                version="v2",
                top_k=10,
                filters={"user_id": "system_ira"}  # Required filter
            )
            
            memories = results.get("memories", results.get("results", []))
            if not memories:
                return "", "memory"
            
            lines = []
            for m in memories[:5]:
                if m.get("score", 0) > 0.5:
                    lines.append(f"• {m.get('memory', '')}")
            
            return "\n".join(lines), "memory"
        except Exception as e:
            logger.error("Memory search error: %s", e)
            return "", "memory"
    
    def _search_crm(self, query: str) -> Tuple[str, str]:
        """Search CRM/Leads database."""
        try:
            from leads_database import get_leads_db
            db = get_leads_db()
            
            query_lower = query.lower()
            region = "Europe" if "europe" in query_lower else None
            country = None
            for c in ["germany", "france", "austria", "uk", "italy"]:
                if c in query_lower:
                    country = c.title()
                    break
            
            hot_only = "hot" in query_lower or "active" in query_lower
            
            leads = db.query(region=region, country=country, hot_only=hot_only, limit=10)
            
            if not leads:
                return "", "crm"
            
            lines = []
            for lead in leads:
                info = f"• {lead.full_name} - {lead.company} ({lead.country})"
                if lead.email:
                    info += f" [{lead.email}]"
                if lead.comments:
                    info += f"\n  Notes: {lead.comments[:100]}"
                lines.append(info)
            
            return "\n".join(lines), "crm"
        except Exception as e:
            logger.error("CRM search error: %s", e)
            return "", "crm"
    
    def _search_documents(self, query: str) -> Tuple[str, str]:
        """Search Qdrant vector database."""
        try:
            from knowledge_retriever import KnowledgeRetriever
            retriever = KnowledgeRetriever()
            result = retriever.retrieve(query, max_results=5)
            return result.get_context(max_tokens=1500), "documents"
        except Exception as e:
            logger.error("Document search error: %s", e)
            return "", "documents"
    
    def _search_pricing(self, query: str) -> Tuple[str, str]:
        """Search pricing data."""
        try:
            from pricing_learner import get_pricing_learner
            learner = get_pricing_learner()
            
            # Extract model from query
            models = re.findall(r'pf1[-\s]?([a-z])[-\s]?(\d{4})', query.lower())
            if models:
                variant, size = models[0]
                model_name = f"PF1-{variant.upper()}-{size}"
                estimate = learner.estimate_price(model_name)
                if estimate:
                    return f"Price for {model_name}: {estimate}", "pricing"
            
            # General pricing info
            return "Check quotes database for specific pricing.", "pricing"
        except Exception as e:
            logger.error("Pricing search error: %s", e)
            return "", "pricing"


# =============================================================================
# FEATURE 1: PARALLEL TOOL EXECUTION
# =============================================================================

class ParallelToolExecutor:
    """Execute multiple tools simultaneously using ThreadPoolExecutor."""
    
    def __init__(self, tool_registry: ToolRegistry, max_workers: int = 4):
        self.tools = tool_registry
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def execute_parallel(self, actions: List[Action]) -> List[Observation]:
        """Execute multiple actions in parallel and return all observations."""
        if not actions:
            return []
        
        start = time.time()
        results = []
        
        futures = {
            self.executor.submit(self.tools.execute, action): action
            for action in actions
        }
        
        for future in as_completed(futures):
            action = futures[future]
            try:
                observation = future.result(timeout=10)
                results.append(observation)
            except Exception as e:
                logger.error("Parallel execution error for %s: %s", action.action_type.value, e)
                results.append(Observation(
                    action=action,
                    result=f"Error: {str(e)}",
                    success=False,
                ))
        
        elapsed = (time.time() - start) * 1000
        logger.info("[Parallel] Executed %d tools in %.0fms", len(actions), elapsed)
        return results
    
    def execute_all_searches(self, query: str) -> List[Observation]:
        """Execute all search tools in parallel for a query."""
        search_actions = [
            Action(ActionType.SEARCH_MEMORY, query, "Parallel search"),
            Action(ActionType.SEARCH_CRM, query, "Parallel search"),
            Action(ActionType.SEARCH_DOCUMENTS, query, "Parallel search"),
        ]
        return self.execute_parallel(search_actions)
    
    def shutdown(self):
        """Shutdown the executor."""
        self.executor.shutdown(wait=False)


# =============================================================================
# FEATURE 2: TOOL SUCCESS LEARNING
# =============================================================================

@dataclass
class ToolStats:
    """Statistics for a tool's performance."""
    total_calls: int = 0
    successful_calls: int = 0
    total_latency_ms: float = 0.0
    query_patterns: Dict[str, int] = field(default_factory=dict)  # pattern -> success count
    
    @property
    def success_rate(self) -> float:
        return self.successful_calls / max(self.total_calls, 1)
    
    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(self.total_calls, 1)


class ToolSuccessLearner:
    """
    Learns which tools work best for which query types.
    
    Tracks:
    - Success rate per tool
    - Query patterns that work with each tool
    - Latency stats for optimization
    """
    
    STATS_FILE = Path(__file__).parent / "tool_learning_stats.json"
    
    def __init__(self):
        self.stats: Dict[str, ToolStats] = {}
        self._load_stats()
        self._lock = threading.Lock()
    
    def _load_stats(self):
        """Load stats from disk."""
        try:
            if self.STATS_FILE.exists():
                with open(self.STATS_FILE) as f:
                    data = json.load(f)
                for tool_name, stats_dict in data.items():
                    self.stats[tool_name] = ToolStats(
                        total_calls=stats_dict.get("total_calls", 0),
                        successful_calls=stats_dict.get("successful_calls", 0),
                        total_latency_ms=stats_dict.get("total_latency_ms", 0),
                        query_patterns=stats_dict.get("query_patterns", {}),
                    )
                logger.info("[ToolLearner] Loaded stats for %d tools", len(self.stats))
        except Exception as e:
            logger.warning("Failed to load tool stats: %s", e)
    
    def _save_stats(self):
        """Save stats to disk."""
        try:
            data = {}
            for tool_name, stats in self.stats.items():
                data[tool_name] = {
                    "total_calls": stats.total_calls,
                    "successful_calls": stats.successful_calls,
                    "total_latency_ms": stats.total_latency_ms,
                    "query_patterns": dict(list(stats.query_patterns.items())[:100]),  # Limit
                }
            with open(self.STATS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save tool stats: %s", e)
    
    def _extract_pattern(self, query: str) -> str:
        """Extract a pattern from a query for learning."""
        query_lower = query.lower()
        patterns = []
        
        if any(w in query_lower for w in ["lead", "contact", "customer", "prospect"]):
            patterns.append("leads")
        if any(w in query_lower for w in ["price", "cost", "quote", "pricing"]):
            patterns.append("pricing")
        if any(w in query_lower for w in ["europe", "germany", "france", "austria"]):
            patterns.append("region")
        if any(w in query_lower for w in ["hot", "warm", "cold", "follow"]):
            patterns.append("status")
        if any(w in query_lower for w in ["pf1", "machine", "model", "thermoform"]):
            patterns.append("product")
        if any(w in query_lower for w in ["remember", "told", "said", "mentioned"]):
            patterns.append("memory")
        
        return "_".join(sorted(patterns)) if patterns else "general"
    
    def record_result(
        self,
        action_type: ActionType,
        query: str,
        success: bool,
        latency_ms: float,
    ):
        """Record the result of a tool execution."""
        tool_name = action_type.value
        pattern = self._extract_pattern(query)
        
        with self._lock:
            if tool_name not in self.stats:
                self.stats[tool_name] = ToolStats()
            
            stats = self.stats[tool_name]
            stats.total_calls += 1
            if success:
                stats.successful_calls += 1
                stats.query_patterns[pattern] = stats.query_patterns.get(pattern, 0) + 1
            stats.total_latency_ms += latency_ms
            
            # Save periodically (every 10 calls)
            if stats.total_calls % 10 == 0:
                self._save_stats()
    
    def recommend_tools(self, query: str, top_k: int = 3) -> List[ActionType]:
        """Recommend tools based on query pattern and past success."""
        pattern = self._extract_pattern(query)
        
        # Score each tool
        scores: List[Tuple[ActionType, float]] = []
        
        for action_type in [ActionType.SEARCH_MEMORY, ActionType.SEARCH_CRM,
                           ActionType.SEARCH_DOCUMENTS, ActionType.SEARCH_PRICING]:
            tool_name = action_type.value
            stats = self.stats.get(tool_name)
            
            if not stats or stats.total_calls < 5:
                # New tool, give it a chance
                scores.append((action_type, 0.5))
                continue
            
            # Base score on success rate
            score = stats.success_rate
            
            # Boost if this pattern worked before
            if pattern in stats.query_patterns:
                pattern_success = stats.query_patterns[pattern]
                score += min(pattern_success * 0.1, 0.3)
            
            scores.append((action_type, score))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scores[:top_k]]
    
    def get_stats_summary(self) -> Dict:
        """Get a summary of tool performance."""
        return {
            tool_name: {
                "success_rate": f"{stats.success_rate:.1%}",
                "total_calls": stats.total_calls,
                "avg_latency_ms": f"{stats.avg_latency_ms:.0f}ms",
                "top_patterns": list(stats.query_patterns.keys())[:5],
            }
            for tool_name, stats in self.stats.items()
        }


# =============================================================================
# FEATURE 3: SEMANTIC CACHING
# =============================================================================

class SemanticCache:
    """
    Cache queries by semantic similarity, not just exact match.
    
    Uses embeddings to find similar past queries and return cached results.
    Much more effective than exact-match caching.
    """
    
    CACHE_FILE = Path(__file__).parent / "semantic_cache.json"
    SIMILARITY_THRESHOLD = 0.85
    MAX_CACHE_SIZE = 200
    
    def __init__(self):
        self.cache: Dict[str, Dict] = {}  # query_hash -> {embedding, result, timestamp}
        self.embeddings_cache: Dict[str, List[float]] = {}  # query_hash -> embedding
        self._voyageai_client = None
        self._openai_client = None
        self._load_cache()
        self._init_embedding_client()
    
    def _init_embedding_client(self):
        """Initialize embedding client (Voyage AI or OpenAI)."""
        try:
            voyage_key = os.environ.get("VOYAGE_API_KEY")
            if voyage_key:
                import voyageai
                self._voyageai_client = voyageai.Client(api_key=voyage_key)
                logger.info("[SemanticCache] Using Voyage AI for embeddings")
            else:
                if get_openai_client:
                    self._openai_client = get_openai_client()
                else:
                    from openai import OpenAI
                    self._openai_client = OpenAI()
                logger.info("[SemanticCache] Using OpenAI for embeddings")
        except Exception as e:
            logger.warning("Failed to init embedding client: %s", e)
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text."""
        try:
            if self._voyageai_client:
                result = self._voyageai_client.embed(
                    [text],
                    model="voyage-2",
                    input_type="query"
                )
                return result.embeddings[0]
            elif self._openai_client:
                response = self._openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text,
                )
                return response.data[0].embedding
        except Exception as e:
            logger.warning("Embedding error: %s", e)
        return None
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
    
    def _query_hash(self, query: str) -> str:
        """Generate a hash for a query."""
        normalized = " ".join(query.lower().strip().split())
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def _load_cache(self):
        """Load cache from disk."""
        try:
            if self.CACHE_FILE.exists():
                with open(self.CACHE_FILE) as f:
                    data = json.load(f)
                self.cache = data.get("cache", {})
                self.embeddings_cache = data.get("embeddings", {})
                logger.info("[SemanticCache] Loaded %d cached queries", len(self.cache))
        except Exception as e:
            logger.warning("Failed to load semantic cache: %s", e)
    
    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.CACHE_FILE, "w") as f:
                json.dump({
                    "cache": self.cache,
                    "embeddings": self.embeddings_cache,
                }, f)
        except Exception as e:
            logger.warning("Failed to save semantic cache: %s", e)
    
    def get(self, query: str) -> Optional[ReasoningTrace]:
        """
        Get cached result for a semantically similar query.
        
        Returns None if no similar query is found.
        """
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            return None
        
        best_match = None
        best_score = 0.0
        
        for query_hash, cached_embedding in self.embeddings_cache.items():
            similarity = self._cosine_similarity(query_embedding, cached_embedding)
            if similarity > best_score and similarity >= self.SIMILARITY_THRESHOLD:
                best_score = similarity
                best_match = query_hash
        
        if best_match and best_match in self.cache:
            cached = self.cache[best_match]
            logger.info("[SemanticCache] Hit! Similarity=%.2f", best_score)
            
            # Reconstruct ReasoningTrace
            trace = ReasoningTrace(query=query)
            trace.final_answer = cached.get("answer")
            trace.confidence = cached.get("confidence", 0.7)
            trace.total_time_ms = 0  # Cached, no time spent
            return trace
        
        return None
    
    def put(self, query: str, trace: ReasoningTrace):
        """Cache a query result."""
        if not trace.final_answer or trace.confidence < 0.5:
            return
        
        query_hash = self._query_hash(query)
        embedding = self._get_embedding(query)
        
        if not embedding:
            return
        
        # Evict oldest if cache is full
        if len(self.cache) >= self.MAX_CACHE_SIZE:
            # Remove oldest by timestamp
            oldest_hash = min(
                self.cache.keys(),
                key=lambda h: self.cache[h].get("timestamp", 0)
            )
            del self.cache[oldest_hash]
            if oldest_hash in self.embeddings_cache:
                del self.embeddings_cache[oldest_hash]
        
        self.cache[query_hash] = {
            "query": query,
            "answer": trace.final_answer,
            "confidence": trace.confidence,
            "timestamp": time.time(),
        }
        self.embeddings_cache[query_hash] = embedding
        
        # Save periodically
        if len(self.cache) % 10 == 0:
            self._save_cache()
        
        logger.debug("[SemanticCache] Cached result for: %s", query[:40])
    
    def clear(self):
        """Clear the cache."""
        self.cache = {}
        self.embeddings_cache = {}
        self._save_cache()


# =============================================================================
# FEATURE 4: STREAMING RESPONSES
# =============================================================================

class StreamingResponseGenerator:
    """
    Generate responses token-by-token for better UX.
    
    Instead of waiting for the full response, stream tokens as they're generated.
    """
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize OpenAI client."""
        try:
            if get_openai_client:
                self.client = get_openai_client()
            else:
                from openai import OpenAI
                self.client = OpenAI()
        except Exception as e:
            logger.error("Failed to init OpenAI client for streaming: %s", e)
    
    def stream_response(
        self,
        query: str,
        context: str,
        system_prompt: str = None,
    ) -> Generator[str, None, None]:
        """
        Stream a response token by token.
        
        Yields individual tokens as they're generated.
        """
        if not self.client:
            yield f"Based on my search:\n\n{context}"
            return
        
        if not system_prompt:
            system_prompt = """You are Ira, Machinecraft's AI assistant.
Generate a helpful, accurate response based on the retrieved information.
Be specific and cite data when available. Be concise but complete."""
        
        try:
            stream = self.client.chat.completions.create(
                model=FAST_LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"""Query: {query}

Retrieved information:
{context}

Generate a response:"""}
                ],
                temperature=0.7,
                max_tokens=800,
                stream=True,  # Enable streaming
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error("Streaming error: %s", e)
            yield f"Based on my search:\n\n{context}"
    
    def stream_to_string(
        self,
        query: str,
        context: str,
        callback: Callable[[str], None] = None,
    ) -> str:
        """
        Stream response and optionally call callback for each token.
        
        Returns the full response string.
        """
        full_response = []
        for token in self.stream_response(query, context):
            full_response.append(token)
            if callback:
                callback(token)
        return "".join(full_response)


# =============================================================================
# FEATURE 5: MULTI-AGENT DEBATE
# =============================================================================

@dataclass
class DebateArgument:
    """An argument in the debate."""
    agent_id: str
    position: str  # "for" or "against"
    argument: str
    evidence: str
    confidence: float


class MultiAgentDebater:
    """
    Two agents debate to find the best answer.
    
    Based on "AI Safety via Debate" (Irving et al., 2018)
    https://arxiv.org/abs/1805.00899
    
    One agent proposes an answer, another critiques it,
    and they iterate to find the best response.
    """
    
    MAX_ROUNDS = 3
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize OpenAI client."""
        try:
            if get_openai_client:
                self.client = get_openai_client()
            else:
                from openai import OpenAI
                self.client = OpenAI()
        except Exception as e:
            logger.error("Failed to init OpenAI client for debate: %s", e)
    
    def debate(
        self,
        query: str,
        context: str,
        user_id: str = "system",
    ) -> Tuple[str, float, List[DebateArgument]]:
        """
        Run a multi-agent debate to find the best answer.
        
        Returns: (best_answer, confidence, debate_history)
        """
        if not self.client:
            return context, 0.5, []
        
        debate_history: List[DebateArgument] = []
        
        # Round 1: Proposer generates initial answer
        proposer_answer = self._generate_proposal(query, context)
        debate_history.append(DebateArgument(
            agent_id="proposer",
            position="for",
            argument=proposer_answer,
            evidence=context[:500],
            confidence=0.7,
        ))
        
        # Round 2: Critic challenges the answer
        critique = self._generate_critique(query, proposer_answer, context)
        debate_history.append(DebateArgument(
            agent_id="critic",
            position="against",
            argument=critique,
            evidence="",
            confidence=0.6,
        ))
        
        # Round 3: Proposer defends/refines based on critique
        refined_answer = self._refine_with_critique(query, proposer_answer, critique, context)
        debate_history.append(DebateArgument(
            agent_id="proposer",
            position="for",
            argument=refined_answer,
            evidence="",
            confidence=0.8,
        ))
        
        # Judge decides final confidence
        final_confidence = self._judge_debate(query, refined_answer, debate_history)
        
        logger.info("[Debate] Completed with confidence=%.2f", final_confidence)
        return refined_answer, final_confidence, debate_history
    
    def _generate_proposal(self, query: str, context: str) -> str:
        """Proposer agent generates initial answer."""
        try:
            response = self.client.chat.completions.create(
                model=FAST_LLM_MODEL,
                messages=[
                    {"role": "system", "content": """You are Agent A, the Proposer.
Your job is to provide the best possible answer based on the given information.
Be thorough, cite evidence, and be confident in your response."""},
                    {"role": "user", "content": f"""Query: {query}

Available information:
{context}

Provide your best answer:"""}
                ],
                temperature=0.7,
                max_tokens=600,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("Proposal error: %s", e)
            return context
    
    def _generate_critique(self, query: str, proposal: str, context: str) -> str:
        """Critic agent challenges the proposal."""
        try:
            response = self.client.chat.completions.create(
                model=FAST_LLM_MODEL,
                messages=[
                    {"role": "system", "content": """You are Agent B, the Critic (Devil's Advocate).
Your job is to find weaknesses, gaps, or inaccuracies in the proposed answer.
Be constructive but thorough. Point out:
1. Missing information
2. Potential inaccuracies
3. Unclear statements
4. Better ways to phrase things"""},
                    {"role": "user", "content": f"""Query: {query}

Proposed answer:
{proposal}

Original context:
{context[:800]}

What are the weaknesses or gaps in this answer?"""}
                ],
                temperature=0.8,
                max_tokens=400,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("Critique error: %s", e)
            return "No significant issues found."
    
    def _refine_with_critique(
        self,
        query: str,
        proposal: str,
        critique: str,
        context: str,
    ) -> str:
        """Proposer refines answer based on critique."""
        try:
            response = self.client.chat.completions.create(
                model=FAST_LLM_MODEL,
                messages=[
                    {"role": "system", "content": """You are Agent A, the Proposer.
You've received critique on your initial answer. 
Refine your answer to address valid points while maintaining accuracy.
Don't be defensive - if the critique is valid, improve your answer."""},
                    {"role": "user", "content": f"""Query: {query}

Your original answer:
{proposal}

Critique received:
{critique}

Original context:
{context[:600]}

Provide your refined answer:"""}
                ],
                temperature=0.6,
                max_tokens=600,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("Refinement error: %s", e)
            return proposal
    
    def _judge_debate(
        self,
        query: str,
        final_answer: str,
        history: List[DebateArgument],
    ) -> float:
        """Judge the quality of the final answer."""
        try:
            debate_summary = "\n".join([
                f"[{arg.agent_id}] {arg.argument[:200]}..."
                for arg in history
            ])
            
            response = self.client.chat.completions.create(
                model=FAST_LLM_MODEL,
                messages=[
                    {"role": "system", "content": """You are a Judge evaluating a debate.
Rate the final answer's quality from 0.0 to 1.0 based on:
- Accuracy and relevance to the query
- How well critique was addressed
- Clarity and completeness

Respond with ONLY a number between 0.0 and 1.0."""},
                    {"role": "user", "content": f"""Query: {query}

Debate history:
{debate_summary}

Final answer:
{final_answer}

Confidence score (0.0-1.0):"""}
                ],
                temperature=0.2,
                max_tokens=10,
            )
            
            score_text = response.choices[0].message.content.strip()
            # Extract number from response
            match = re.search(r'(\d+\.?\d*)', score_text)
            if match:
                return min(float(match.group(1)), 1.0)
            return 0.7
        except Exception as e:
            logger.error("Judge error: %s", e)
            return 0.7


# =============================================================================
# ReAct REASONER - Thought → Action → Observation Loop
# =============================================================================

class ReActReasoner:
    """
    ReAct-style reasoning agent with advanced features.
    
    Implements the Thought → Action → Observation loop from:
    "ReAct: Synergizing Reasoning and Acting in Language Models"
    https://arxiv.org/abs/2210.03629
    
    Key improvements over simple retrieval:
    1. Explicit reasoning traces (debuggable)
    2. Multi-step reasoning (can chain actions)
    3. Self-correction (can retry on failure)
    4. Working memory (accumulates knowledge)
    5. Early stopping when confident (saves time)
    6. Semantic caching (finds similar queries)
    7. Parallel tool execution (faster searches)
    8. Tool success learning (adaptive selection)
    9. Streaming responses (better UX)
    10. Multi-agent debate (higher quality)
    """
    
    MAX_ITERATIONS = 5
    EARLY_STOP_CONFIDENCE = 0.85
    
    # Shared instances (singletons)
    _semantic_cache: Optional[SemanticCache] = None
    _tool_learner: Optional[ToolSuccessLearner] = None
    _debater: Optional[MultiAgentDebater] = None
    _streamer: Optional[StreamingResponseGenerator] = None
    
    def __init__(
        self,
        use_semantic_cache: bool = True,
        use_tool_learning: bool = True,
        use_parallel_execution: bool = True,
        use_debate: bool = False,  # Off by default (slower but higher quality)
        use_streaming: bool = False,  # Off by default for compatibility
    ):
        self.tools = ToolRegistry()
        self.client = None
        self._init_client()
        
        # Feature flags
        self.use_semantic_cache = use_semantic_cache
        self.use_tool_learning = use_tool_learning
        self.use_parallel_execution = use_parallel_execution
        self.use_debate = use_debate
        self.use_streaming = use_streaming
        
        # Initialize advanced components (lazy singletons)
        if use_parallel_execution:
            self.parallel_executor = ParallelToolExecutor(self.tools)
        else:
            self.parallel_executor = None
        
        # Use shared instances for efficiency
        if use_semantic_cache and ReActReasoner._semantic_cache is None:
            ReActReasoner._semantic_cache = SemanticCache()
        if use_tool_learning and ReActReasoner._tool_learner is None:
            ReActReasoner._tool_learner = ToolSuccessLearner()
        if use_debate and ReActReasoner._debater is None:
            ReActReasoner._debater = MultiAgentDebater()
        if use_streaming and ReActReasoner._streamer is None:
            ReActReasoner._streamer = StreamingResponseGenerator()
    
    def _init_client(self):
        """Initialize OpenAI client."""
        try:
            if get_openai_client:
                self.client = get_openai_client()
            else:
                from openai import OpenAI
                self.client = OpenAI()
        except Exception as e:
            logger.error("Failed to init OpenAI client: %s", e)
    
    def reason(
        self,
        query: str,
        user_id: str = "system_ira",
        context: Dict[str, Any] = None,
        mode: str = "balanced",  # fast, balanced, thorough
    ) -> ReasoningTrace:
        """
        Main reasoning loop using ReAct pattern with advanced features.
        
        Modes:
        - fast: Skip debate, minimal iterations
        - balanced: Standard processing with caching
        - thorough: Enable debate, full iterations
        
        Flow:
        1. Check semantic cache for similar query
        2. Parallel search if enabled (first iteration)
        3. Think → Act → Observe loop
        4. Tool learning feedback
        5. Multi-agent debate (if enabled)
        6. Cache result
        """
        start_time = time.time()
        context = context or {}
        
        # FEATURE 3: Semantic cache check
        if self.use_semantic_cache and self._semantic_cache:
            cached = self._semantic_cache.get(query)
            if cached:
                logger.info("[ReAct] Semantic cache hit!")
                return cached
        
        trace = ReasoningTrace(query=query)
        logger.info("[ReAct] Starting reasoning for: '%s...' (mode=%s)", query[:50], mode)
        
        # FEATURE 1: Parallel execution for first iteration
        if self.use_parallel_execution and self.parallel_executor:
            logger.info("[ReAct] Running parallel initial search...")
            parallel_start = time.time()
            observations = self.parallel_executor.execute_all_searches(query)
            
            for obs in observations:
                if obs.success and obs.result:
                    trace.add_to_scratchpad(obs.source, obs.result)
                    trace.observations.append(obs)
                    trace.actions.append(obs.action)
                    
                    # FEATURE 2: Record tool success for learning
                    if self.use_tool_learning and self._tool_learner:
                        self._tool_learner.record_result(
                            obs.action.action_type,
                            query,
                            obs.success,
                            (time.time() - parallel_start) * 1000,
                        )
            
            # Check if parallel search gave us enough
            if len(trace.scratchpad) >= 2:
                evidence_quality = self._assess_evidence_quality(trace)
                if evidence_quality >= self.EARLY_STOP_CONFIDENCE:
                    logger.info("[ReAct] Parallel search sufficient (quality=%.2f)", evidence_quality)
                    trace.final_answer = self._generate_final_answer(query, trace)
                    trace.confidence = evidence_quality
                    trace.iterations = 1
                    self._finalize_trace(trace, start_time, query)
                    return trace
        
        # Adjust max iterations based on mode
        max_iter = 2 if mode == "fast" else (self.MAX_ITERATIONS if mode == "balanced" else 7)
        
        for i in range(max_iter):
            trace.iterations = i + 1
            
            # FEATURE 2: Use learned tool recommendations
            recommended_tools = None
            if self.use_tool_learning and self._tool_learner:
                recommended_tools = self._tool_learner.recommend_tools(query)
            
            # STEP 1: Think - What should I do?
            thought, action = self._think_and_plan(query, trace, context, recommended_tools)
            trace.add_thought(thought.content, thought.confidence)
            
            logger.info("[ReAct] Iteration %d - Thought: %s", i+1, thought.content[:80])
            
            # STEP 2: Check if we should finish
            if action.action_type == ActionType.FINISH:
                logger.info("[ReAct] Finishing with answer")
                trace.final_answer = self._generate_final_answer(query, trace)
                trace.confidence = thought.confidence
                break
            
            # STEP 3: Check if we need clarification
            if action.action_type == ActionType.ASK_CLARIFICATION:
                logger.info("[ReAct] Needs clarification")
                trace.needs_clarification = True
                trace.clarifying_question = action.query
                break
            
            # STEP 4: Execute the action
            action_start = time.time()
            trace.actions.append(action)
            observation = self.tools.execute(action)
            trace.observations.append(observation)
            action_latency = (time.time() - action_start) * 1000
            
            logger.info("[ReAct] Action: %s → Success: %s (%.0fms)",
                       action.action_type.value, observation.success, action_latency)
            
            # FEATURE 2: Record tool result for learning
            if self.use_tool_learning and self._tool_learner:
                self._tool_learner.record_result(
                    action.action_type,
                    query,
                    observation.success,
                    action_latency,
                )
            
            # STEP 5: Update working memory
            if observation.success and observation.result:
                trace.add_to_scratchpad(observation.source, observation.result)
            
            # Early stopping if we have strong evidence
            if observation.success and len(trace.scratchpad) >= 2:
                evidence_quality = self._assess_evidence_quality(trace)
                if evidence_quality >= self.EARLY_STOP_CONFIDENCE:
                    logger.info("[ReAct] Early stopping - high evidence quality (%.2f)", evidence_quality)
                    trace.final_answer = self._generate_final_answer(query, trace)
                    trace.confidence = evidence_quality
                    break
        
        # If we hit max iterations, generate best-effort answer
        if not trace.final_answer and not trace.needs_clarification:
            trace.final_answer = self._generate_final_answer(query, trace)
            trace.confidence = 0.5
        
        # FEATURE 5: Multi-agent debate for thorough mode or low confidence
        if (self.use_debate and self._debater and trace.final_answer 
            and (mode == "thorough" or trace.confidence < 0.6)):
            logger.info("[ReAct] Engaging multi-agent debate for quality...")
            context_str = trace.get_context()
            debated_answer, debated_confidence, _ = self._debater.debate(
                query, context_str, user_id
            )
            if debated_confidence > trace.confidence:
                trace.final_answer = debated_answer
                trace.confidence = debated_confidence
                trace.add_thought(f"Debate improved answer (confidence {debated_confidence:.2f})")
        
        # Finalize and cache
        self._finalize_trace(trace, start_time, query)
        return trace
    
    def _finalize_trace(self, trace: ReasoningTrace, start_time: float, query: str):
        """Finalize the trace with timing and caching."""
        trace.total_time_ms = (time.time() - start_time) * 1000
        logger.info("[ReAct] Completed in %.0fms, confidence=%.2f",
                   trace.total_time_ms, trace.confidence)
        
        # FEATURE 3: Semantic cache storage
        if self.use_semantic_cache and self._semantic_cache:
            self._semantic_cache.put(query, trace)
    
    def _assess_evidence_quality(self, trace: ReasoningTrace) -> float:
        """Assess the quality of accumulated evidence."""
        score = 0.5
        
        # More sources = better
        unique_sources = set(trace.scratchpad.keys())
        score += min(len(unique_sources) * 0.1, 0.2)
        
        # More content = better (up to a point)
        total_content = sum(len(v) for v in trace.scratchpad.values())
        if total_content > 200:
            score += 0.1
        if total_content > 500:
            score += 0.1
        
        # Successful observations = better
        success_rate = sum(1 for o in trace.observations if o.success) / max(len(trace.observations), 1)
        score += success_rate * 0.1
        
        return min(score, 1.0)
    
    def _think_and_plan(
        self,
        query: str,
        trace: ReasoningTrace,
        context: Dict,
        recommended_tools: List[ActionType] = None,
    ) -> Tuple[Thought, Action]:
        """
        Generate a thought and plan the next action.
        
        Uses LLM to reason about:
        1. What do I need to answer this?
        2. What do I already have (in scratchpad)?
        3. What action should I take next?
        
        Args:
            recommended_tools: Tools recommended by the learning system
        """
        if not self.client:
            # Fallback to rule-based
            return self._rule_based_planning(query, trace, recommended_tools)
        
        # Build prompt with current state
        scratchpad_context = trace.get_context()
        previous_actions = [
            f"- {a.action_type.value}: {a.query[:50]}" 
            for a in trace.actions[-3:]
        ]
        
        # Add tool recommendations to prompt
        tool_hint = ""
        if recommended_tools:
            tool_names = [t.value for t in recommended_tools[:3]]
            tool_hint = f"\n\nRecommended tools (based on past success): {', '.join(tool_names)}"
        
        system_prompt = f"""You are a reasoning engine. Given a query and current context, 
decide the best next action to find the answer.

Available actions:
- search_memory: Search Ira's memory for facts
- search_crm: Search CRM database for leads/contacts
- search_documents: Search documents (PDFs, specs) for technical info
- search_pricing: Search pricing database
- ask_clarification: Ask user for more info (only if truly needed)
- finish: You have enough info to answer{tool_hint}

Respond in JSON:
{{
  "thought": "What I'm thinking...",
  "confidence": 0.0-1.0,
  "action": "action_name",
  "action_query": "specific query for the action"
}}"""

        user_prompt = f"""Query: {query}

What I know so far:
{scratchpad_context if scratchpad_context else "(nothing yet)"}

Previous actions: {previous_actions if previous_actions else "(none)"}

What should I do next?"""

        try:
            response = self.client.chat.completions.create(
                model=FAST_LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=300,
            )
            
            result = json.loads(response.choices[0].message.content)
            
            thought = Thought(
                step=len(trace.thoughts) + 1,
                content=result.get("thought", ""),
                confidence=result.get("confidence", 0.5),
            )
            
            action_str = result.get("action", "finish")
            action_type = ActionType.FINISH
            for at in ActionType:
                if at.value == action_str:
                    action_type = at
                    break
            
            action = Action(
                action_type=action_type,
                query=result.get("action_query", query),
                reasoning=result.get("thought", ""),
            )
            
            return thought, action
            
        except Exception as e:
            logger.error("[ReAct] Planning error: %s", e)
            return self._rule_based_planning(query, trace)
    
    def _rule_based_planning(
        self,
        query: str,
        trace: ReasoningTrace,
        recommended_tools: List[ActionType] = None,
    ) -> Tuple[Thought, Action]:
        """Fallback rule-based planning with learning integration."""
        query_lower = query.lower()
        
        # If we already have data, finish
        if trace.scratchpad:
            return (
                Thought(step=len(trace.thoughts)+1, content="Have enough info", confidence=0.7),
                Action(action_type=ActionType.FINISH, query=query)
            )
        
        # FEATURE 2: Prefer recommended tools from learning system
        if recommended_tools:
            best_tool = recommended_tools[0]
            return (
                Thought(step=len(trace.thoughts)+1, 
                       content=f"Using learned recommendation: {best_tool.value}", 
                       confidence=0.65),
                Action(action_type=best_tool, query=query)
            )
        
        # Route based on keywords
        if any(kw in query_lower for kw in ["lead", "contact", "prospect", "customer"]):
            return (
                Thought(step=len(trace.thoughts)+1, content="Need CRM data", confidence=0.6),
                Action(action_type=ActionType.SEARCH_CRM, query=query)
            )
        
        if any(kw in query_lower for kw in ["price", "cost", "quote"]):
            return (
                Thought(step=len(trace.thoughts)+1, content="Need pricing", confidence=0.6),
                Action(action_type=ActionType.SEARCH_PRICING, query=query)
            )
        
        # Default: search memory first
        return (
            Thought(step=len(trace.thoughts)+1, content="Check memory first", confidence=0.5),
            Action(action_type=ActionType.SEARCH_MEMORY, query=query)
        )
    
    def _generate_final_answer(self, query: str, trace: ReasoningTrace) -> str:
        """Generate the final answer using accumulated knowledge."""
        context = trace.get_context()
        
        if not context:
            return "I couldn't find specific information for your query. Could you provide more details?"
        
        if not self.client:
            return f"Based on my search:\n\n{context}"
        
        try:
            # Generate answer
            response = self.client.chat.completions.create(
                model=FAST_LLM_MODEL,
                messages=[
                    {"role": "system", "content": """You are Ira, Machinecraft's AI assistant.
Generate a helpful, accurate response based on the retrieved information.
Be specific and cite data when available. Be concise but complete.
If the data doesn't fully answer the query, say what you found and what's missing."""},
                    {"role": "user", "content": f"""Query: {query}

Retrieved information:
{context}

Generate a response:"""}
                ],
                temperature=0.7,
                max_tokens=800,
            )
            answer = response.choices[0].message.content
            
            # IMPROVEMENT: Quick answer verification
            if len(answer) > 50:
                is_valid = self._verify_answer_relevance(query, answer)
                if not is_valid:
                    logger.warning("[ReAct] Answer verification failed, appending disclaimer")
                    answer += "\n\n(Note: I've shared what I found, but it may not fully address your question.)"
            
            return answer
        except Exception as e:
            logger.error("Answer generation error: %s", e)
            return f"Based on my search:\n\n{context}"
    
    def _verify_answer_relevance(self, query: str, answer: str) -> bool:
        """Quick check that answer addresses the query."""
        query_lower = query.lower()
        answer_lower = answer.lower()
        
        # Extract key terms from query (simple heuristic)
        key_terms = []
        for word in query_lower.split():
            if len(word) > 4 and word not in {"about", "would", "could", "should", "where", "which", "there"}:
                key_terms.append(word)
        
        # Check if at least half the key terms appear in answer
        if not key_terms:
            return True
        matches = sum(1 for term in key_terms if term in answer_lower)
        coverage = matches / len(key_terms)
        
        return coverage >= 0.4


# =============================================================================
# SELF-CONSISTENCY - Multiple reasoning paths, vote on answer
# =============================================================================

class SelfConsistencyReasoner:
    """
    Self-Consistency Reasoning.
    
    Samples multiple reasoning paths and votes on the most consistent answer.
    From: "Self-Consistency Improves Chain of Thought Reasoning"
    https://arxiv.org/abs/2203.11171
    
    Accuracy improvement: +17% on complex reasoning tasks
    """
    
    def __init__(self, num_samples: int = 3):
        self.num_samples = num_samples
        self.base_reasoner = ReActReasoner()
    
    def reason_with_consistency(
        self,
        query: str,
        user_id: str = "system_ira",
    ) -> ReasoningTrace:
        """
        Sample multiple reasoning paths and select most consistent.
        """
        logger.info("[SelfConsistency] Sampling %d reasoning paths", self.num_samples)
        
        traces = []
        for i in range(self.num_samples):
            trace = self.base_reasoner.reason(query, user_id)
            traces.append(trace)
            logger.debug("[SelfConsistency] Path %d confidence: %.2f", i+1, trace.confidence)
        
        # Select highest confidence trace
        best_trace = max(traces, key=lambda t: t.confidence)
        
        # Boost confidence if multiple paths agree
        agreements = sum(
            1 for t in traces 
            if t.final_answer and best_trace.final_answer 
            and self._answers_agree(t.final_answer, best_trace.final_answer)
        )
        
        if agreements > 1:
            best_trace.confidence = min(1.0, best_trace.confidence + 0.1 * agreements)
            logger.info("[SelfConsistency] %d/%d paths agree, boosted confidence to %.2f",
                       agreements, self.num_samples, best_trace.confidence)
        
        return best_trace
    
    def _answers_agree(self, a1: str, a2: str) -> bool:
        """Check if two answers roughly agree."""
        # Simple overlap check
        words1 = set(a1.lower().split())
        words2 = set(a2.lower().split())
        overlap = len(words1 & words2) / max(len(words1), len(words2), 1)
        return overlap > 0.5


# =============================================================================
# REFLECTION - Generate → Critique → Refine
# =============================================================================

class ReflectionReasoner:
    """
    Reflection-based reasoning.
    
    Implements the Generate → Critique → Refine loop.
    From LangGraph reflection pattern.
    
    Trade-off: Slower but higher quality answers.
    """
    
    def __init__(self, max_reflections: int = 2):
        self.max_reflections = max_reflections
        self.base_reasoner = ReActReasoner()
        self.client = None
        self._init_client()
    
    def _init_client(self):
        try:
            if get_openai_client:
                self.client = get_openai_client()
            else:
                from openai import OpenAI
                self.client = OpenAI()
        except Exception:
            pass
    
    def reason_with_reflection(
        self,
        query: str,
        user_id: str = "system_ira",
    ) -> ReasoningTrace:
        """
        Generate answer, critique it, then refine.
        """
        # Step 1: Initial reasoning
        trace = self.base_reasoner.reason(query, user_id)
        
        if not trace.final_answer or not self.client:
            return trace
        
        logger.info("[Reflection] Starting reflection loop")
        
        for i in range(self.max_reflections):
            # Step 2: Critique
            critique = self._critique_answer(query, trace.final_answer)
            
            if not critique.get("needs_improvement"):
                logger.info("[Reflection] Answer is good, no refinement needed")
                break
            
            logger.info("[Reflection] Critique: %s", critique.get("issues", "")[:80])
            
            # Step 3: Refine
            refined = self._refine_answer(query, trace.final_answer, critique)
            trace.final_answer = refined
            trace.add_thought(f"Refined based on critique: {critique.get('issues', '')[:50]}")
        
        return trace
    
    def _critique_answer(self, query: str, answer: str) -> Dict:
        """Critique an answer for issues."""
        try:
            response = self.client.chat.completions.create(
                model=FAST_LLM_MODEL,
                messages=[
                    {"role": "system", "content": """You are a critical reviewer.
Analyze this answer for:
1. Accuracy - Is it factually correct?
2. Completeness - Does it fully address the query?
3. Clarity - Is it clear and well-structured?

Respond in JSON:
{
  "needs_improvement": true/false,
  "issues": "description of issues",
  "suggestions": "how to improve"
}"""},
                    {"role": "user", "content": f"Query: {query}\n\nAnswer: {answer}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=200,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error("Critique error: %s", e)
            return {"needs_improvement": False}
    
    def _refine_answer(self, query: str, answer: str, critique: Dict) -> str:
        """Refine answer based on critique."""
        try:
            response = self.client.chat.completions.create(
                model=FAST_LLM_MODEL,
                messages=[
                    {"role": "system", "content": "Refine the answer based on the critique. Keep what's good, fix what's wrong."},
                    {"role": "user", "content": f"""Query: {query}

Original answer: {answer}

Critique: {critique.get('issues', '')}
Suggestions: {critique.get('suggestions', '')}

Provide a refined answer:"""}
                ],
                temperature=0.5,
                max_tokens=800,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("Refine error: %s", e)
            return answer


# =============================================================================
# QUERY DECOMPOSITION - Break complex queries into sub-questions
# =============================================================================

class QueryDecomposer:
    """
    Decompose complex queries into simpler sub-questions.
    
    For multi-hop reasoning where the answer requires combining
    information from multiple sources.
    """
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        try:
            if get_openai_client:
                self.client = get_openai_client()
            else:
                from openai import OpenAI
                self.client = OpenAI()
        except Exception:
            pass
    
    def decompose(self, query: str) -> List[str]:
        """Break a complex query into sub-questions."""
        if not self.client:
            return [query]
        
        try:
            response = self.client.chat.completions.create(
                model=FAST_LLM_MODEL,
                messages=[
                    {"role": "system", "content": """Break this query into simpler sub-questions
that can be answered independently. Return JSON array of questions.
If the query is already simple, return just that one question.

Example:
"What's the price of PF1 machines for the hot leads in Germany?"
→ ["What are the hot leads in Germany?", "What are the prices for PF1 machines?"]"""},
                    {"role": "user", "content": query}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=200,
            )
            result = json.loads(response.choices[0].message.content)
            questions = result.get("questions", result.get("sub_questions", [query]))
            return questions if questions else [query]
        except Exception as e:
            logger.error("Decomposition error: %s", e)
            return [query]


# =============================================================================
# UNIFIED REASONER - Combines all patterns
# =============================================================================

class UnifiedReasoner:
    """
    Unified reasoning engine combining:
    - ReAct for action planning
    - Self-Consistency for accuracy
    - Reflection for quality
    - Decomposition for complex queries
    
    This is the main entry point for world-class reasoning.
    """
    
    def __init__(
        self,
        use_self_consistency: bool = False,  # Slower but more accurate
        use_reflection: bool = True,          # Quality check
        use_decomposition: bool = True,       # Complex queries
    ):
        self.use_self_consistency = use_self_consistency
        self.use_reflection = use_reflection
        self.use_decomposition = use_decomposition
        
        self.base_reasoner = ReActReasoner()
        self.consistency_reasoner = SelfConsistencyReasoner() if use_self_consistency else None
        self.reflection_reasoner = ReflectionReasoner() if use_reflection else None
        self.decomposer = QueryDecomposer() if use_decomposition else None
    
    def reason(
        self,
        query: str,
        user_id: str = "system_ira",
        mode: str = "balanced",  # "fast", "balanced", "thorough"
    ) -> ReasoningTrace:
        """
        Unified reasoning with configurable depth.
        
        Modes:
        - fast: ReAct only (quickest)
        - balanced: ReAct + Reflection (default)
        - thorough: Decomposition + Self-Consistency + Reflection (most accurate)
        """
        logger.info("[Unified] Reasoning in '%s' mode for: '%s...'", mode, query[:50])
        
        if mode == "fast":
            return self.base_reasoner.reason(query, user_id)
        
        if mode == "thorough" and self.decomposer:
            # Decompose complex queries
            sub_questions = self.decomposer.decompose(query)
            
            if len(sub_questions) > 1:
                logger.info("[Unified] Decomposed into %d sub-questions", len(sub_questions))
                
                # Answer each sub-question
                combined_trace = ReasoningTrace(query=query)
                for sq in sub_questions:
                    sub_trace = self.base_reasoner.reason(sq, user_id)
                    combined_trace.scratchpad[sq] = sub_trace.final_answer
                    combined_trace.thoughts.extend(sub_trace.thoughts)
                
                # Generate combined answer
                combined_trace.final_answer = self._combine_answers(query, combined_trace.scratchpad)
                return combined_trace
        
        # Balanced mode: ReAct + optional Reflection
        if self.use_self_consistency and self.consistency_reasoner:
            trace = self.consistency_reasoner.reason_with_consistency(query, user_id)
        else:
            trace = self.base_reasoner.reason(query, user_id)
        
        # Apply reflection if enabled
        if self.use_reflection and self.reflection_reasoner and trace.final_answer:
            trace = self.reflection_reasoner.reason_with_reflection(query, user_id)
        
        return trace
    
    def _combine_answers(self, original_query: str, sub_answers: Dict) -> str:
        """Combine answers from sub-questions."""
        parts = []
        for q, a in sub_answers.items():
            if a:
                parts.append(f"**{q}**\n{a}")
        
        return "\n\n".join(parts) if parts else "Could not find information."


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_unified_reasoner: Optional[UnifiedReasoner] = None


def get_reasoner(mode: str = "balanced") -> ReActReasoner:
    """
    Get a configured reasoner based on mode.
    
    Modes:
    - fast: No debate, minimal features, fastest
    - balanced: Semantic cache + tool learning + parallel exec
    - thorough: All features including debate
    """
    if mode == "fast":
        return ReActReasoner(
            use_semantic_cache=True,
            use_tool_learning=False,
            use_parallel_execution=False,
            use_debate=False,
            use_streaming=False,
        )
    elif mode == "thorough":
        return ReActReasoner(
            use_semantic_cache=True,
            use_tool_learning=True,
            use_parallel_execution=True,
            use_debate=True,
            use_streaming=False,
        )
    else:  # balanced
        return ReActReasoner(
            use_semantic_cache=True,
            use_tool_learning=True,
            use_parallel_execution=True,
            use_debate=False,
            use_streaming=False,
        )


# Singleton for repeated use
_default_reasoner: Optional[ReActReasoner] = None


def get_default_reasoner() -> ReActReasoner:
    """Get the default singleton reasoner."""
    global _default_reasoner
    if _default_reasoner is None:
        _default_reasoner = ReActReasoner(
            use_semantic_cache=True,
            use_tool_learning=True,
            use_parallel_execution=True,
            use_debate=False,
        )
    return _default_reasoner


def reason_with_react(
    query: str,
    user_id: str = "system_ira",
    mode: str = "balanced",
) -> ReasoningTrace:
    """
    Quick reasoning function.
    
    Args:
        query: The question to answer
        user_id: User identifier for personalization
        mode: fast | balanced | thorough
    
    Returns:
        ReasoningTrace with the answer
    """
    reasoner = get_default_reasoner()
    return reasoner.reason(query, user_id, mode=mode)


def stream_response(
    query: str,
    context: str = "",
    callback: Callable[[str], None] = None,
) -> str:
    """
    Stream a response token-by-token.
    
    Args:
        query: The question
        context: Retrieved context to use
        callback: Called with each token (for real-time display)
    
    Returns:
        The complete response string
    """
    streamer = StreamingResponseGenerator()
    return streamer.stream_to_string(query, context, callback)


def get_tool_stats() -> Dict:
    """Get current tool learning statistics."""
    learner = ToolSuccessLearner()
    return learner.get_stats_summary()


def clear_semantic_cache():
    """Clear the semantic cache."""
    cache = SemanticCache()
    cache.clear()
    logger.info("Semantic cache cleared")


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("=" * 70)
    print("REASONING ENGINE V2 - Advanced AI Reasoning for Ira")
    print("=" * 70)
    print("\nFeatures enabled:")
    print("  ✓ Parallel tool execution")
    print("  ✓ Tool success learning")
    print("  ✓ Semantic caching")
    print("  ✓ Streaming responses")
    print("  ✓ Multi-agent debate")
    print()
    
    # Test modes
    test_queries = [
        ("What are the hot leads in Germany?", "fast"),
        ("Give me the pricing for PF1-C-2020", "balanced"),
    ]
    
    for query, mode in test_queries:
        print(f"\n{'='*70}")
        print(f"Query: {query}")
        print(f"Mode: {mode}")
        print("-" * 70)
        
        trace = reason_with_react(query, mode=mode)
        
        print(f"\nThoughts ({len(trace.thoughts)}):")
        for t in trace.thoughts[:3]:
            print(f"  {t.step}. {t.content[:80]}")
        
        print(f"\nActions taken: {len(trace.actions)}")
        for a in trace.actions[:5]:
            print(f"  - {a.action_type.value}: {a.query[:50]}")
        
        print(f"\nConfidence: {trace.confidence:.2f}")
        print(f"Time: {trace.total_time_ms:.0f}ms")
        
        if trace.final_answer:
            print(f"\nAnswer preview: {trace.final_answer[:300]}...")
        elif trace.clarifying_question:
            print(f"\nClarifying Q: {trace.clarifying_question}")
    
    # Test semantic cache
    print(f"\n{'='*70}")
    print("SEMANTIC CACHE TEST")
    print("-" * 70)
    print("Running same query twice to test cache...")
    
    q = "What leads are available?"
    trace1 = reason_with_react(q, mode="balanced")
    print(f"First run: {trace1.total_time_ms:.0f}ms")
    
    trace2 = reason_with_react(q, mode="balanced")
    print(f"Second run (cached): {trace2.total_time_ms:.0f}ms")
    
    # Show tool stats
    print(f"\n{'='*70}")
    print("TOOL LEARNING STATS")
    print("-" * 70)
    stats = get_tool_stats()
    for tool, data in stats.items():
        print(f"  {tool}: {data}")
