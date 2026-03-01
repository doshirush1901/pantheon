"""
Brain State - Core state management classes for IRA.

This module contains the fundamental state classes used across all IRA components:
- ProcessingPhase: Enum tracking processing stages
- BrainState: Shared state passed through all brain modules
- AttentionManager: Working memory limits implementation (Miller's 7±2)
- FeedbackLearner: Calibration learning from outcomes

These classes were extracted from the deprecated brain_orchestrator.py
to establish a clean, single source of truth for state management.

Usage:
    from src.core.brain_state import BrainState, ProcessingPhase, AttentionManager
    
    state = BrainState(message="Hello", identity_id="user123")
    state.phase = ProcessingPhase.RETRIEVAL
"""

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


# =============================================================================
# PATH SETUP
# =============================================================================

CORE_DIR = Path(__file__).parent
SRC_DIR = CORE_DIR.parent
AGENT_DIR = SRC_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent


# =============================================================================
# PROCESSING PHASE ENUM
# =============================================================================

class ProcessingPhase(Enum):
    """Tracks which phase of processing we're in."""
    INIT = "init"
    QUERY_ANALYSIS = "query_analysis"
    CUSTOMER_CONTEXT = "customer_context"
    TRIGGER = "trigger_evaluation"
    RETRIEVAL = "memory_retrieval"
    EPISODIC = "episodic_retrieval"
    PROCEDURAL = "procedural_matching"
    WEAVING = "memory_weaving"
    REASONING = "memory_reasoning"
    GOAL_REASONING = "goal_reasoning"
    COMPETITOR_INTELLIGENCE = "competitor_intelligence"
    METACOGNITION = "metacognition"
    ATTENTION = "attention_filtering"
    COMPLETE = "complete"
    FAILED = "failed"


# =============================================================================
# BRAIN STATE - Coordination Object
# =============================================================================

@dataclass
class BrainState:
    """
    Shared state passed through all brain modules.
    
    This is the coordination object that enables modules to communicate
    through shared state. Supports both Telegram and Email channels with
    channel-specific context.
    """
    # Input
    message: str = ""
    identity_id: Optional[str] = None
    channel: str = "telegram"
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Channel-specific context (for email integration)
    thread_id: Optional[str] = None
    subject: Optional[str] = None
    is_reply: bool = False
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    is_internal: bool = False
    thread_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Processing state
    phase: ProcessingPhase = ProcessingPhase.INIT
    errors: List[str] = field(default_factory=list)
    timings: Dict[str, float] = field(default_factory=dict)
    
    # Trigger decision
    should_retrieve: bool = True
    trigger_decision: Optional[Any] = None
    retrieval_config: Dict[str, Any] = field(default_factory=lambda: {
        "user_memory_limit": 5,
        "entity_memory_limit": 5,
        "min_relevance": 0.3
    })
    
    # Retrieved memories
    user_memories: List[Any] = field(default_factory=list)
    entity_memories: List[Any] = field(default_factory=list)
    
    # Episodic context
    episodic_context: str = ""
    episodes_retrieved: int = 0
    
    # Procedural guidance
    matched_procedure: Optional[Any] = None
    procedure_guidance: str = ""
    procedure_id: Optional[str] = None
    
    # Woven context
    woven_context: Optional[Any] = None
    memory_guidance: Dict[str, Any] = field(default_factory=dict)
    
    # Reasoning
    reasoning_trace: Optional[Any] = None
    reasoning_context: str = ""
    
    # Meta-cognition
    knowledge_assessment: Optional[Any] = None
    metacognitive_guidance: str = ""
    
    # Conflicts detected
    conflicts_detected: List[Dict] = field(default_factory=list)
    
    # Goal-directed reasoning
    active_goal_id: Optional[str] = None
    goal_status: Dict[str, Any] = field(default_factory=dict)
    goal_proactive_prompt: Optional[str] = None
    goal_context: Dict[str, Any] = field(default_factory=dict)
    goal_step_completed: bool = False
    
    # Competitor intelligence
    is_competitor_comparison: bool = False
    competitors_mentioned: List[str] = field(default_factory=list)
    competitor_context: str = ""
    competitor_data: Dict[str, Any] = field(default_factory=dict)
    
    # Query Analysis
    query_analysis: Optional[Any] = None
    query_intent: str = ""
    query_entities: Dict[str, Any] = field(default_factory=dict)
    query_constraints: List[Dict] = field(default_factory=list)
    suggested_response_length: str = "medium"
    
    # Customer Context
    customer_context: Optional[Any] = None
    customer_name: Optional[str] = None
    customer_company: Optional[str] = None
    customer_role: Optional[str] = None
    customer_style: str = "default"
    customer_relationship: str = "unknown"
    
    # Attention-filtered context
    final_context: Dict[str, Any] = field(default_factory=dict)
    items_filtered: int = 0
    

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dict. Skips complex objects."""
        return {
            "message": self.message,
            "identity_id": self.identity_id,
            "channel": self.channel,
            "context": self.context,
            "thread_id": self.thread_id,
            "subject": self.subject,
            "is_reply": self.is_reply,
            "from_email": self.from_email,
            "from_name": self.from_name,
            "is_internal": self.is_internal,
            "phase": self.phase.value if hasattr(self.phase, "value") else str(self.phase),
            "errors": self.errors,
            "timings": self.timings,
            "should_retrieve": self.should_retrieve,
            "retrieval_config": self.retrieval_config,
            "episodic_context": self.episodic_context,
            "episodes_retrieved": self.episodes_retrieved,
            "procedure_guidance": self.procedure_guidance,
            "memory_guidance": self.memory_guidance,
            "reasoning_context": self.reasoning_context,
            "metacognitive_guidance": self.metacognitive_guidance,
            "conflicts_detected": self.conflicts_detected,
            "is_competitor_comparison": self.is_competitor_comparison,
            "competitors_mentioned": self.competitors_mentioned,
            "competitor_context": self.competitor_context,
            "query_intent": self.query_intent,
            "query_entities": self.query_entities,
            "query_constraints": self.query_constraints,
            "suggested_response_length": self.suggested_response_length,
            "customer_name": self.customer_name,
            "customer_company": self.customer_company,
            "customer_role": self.customer_role,
            "customer_style": self.customer_style,
            "customer_relationship": self.customer_relationship,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BrainState":
        """Reconstruct from dict. Phase restored from string."""
        phase_val = d.get("phase", "init")
        try:
            phase = ProcessingPhase(phase_val)
        except ValueError:
            phase = ProcessingPhase.INIT
        state = cls()
        state.message = d.get("message", "")
        state.identity_id = d.get("identity_id")
        state.channel = d.get("channel", "telegram")
        state.context = d.get("context", {})
        state.thread_id = d.get("thread_id")
        state.subject = d.get("subject")
        state.is_reply = d.get("is_reply", False)
        state.from_email = d.get("from_email")
        state.from_name = d.get("from_name")
        state.is_internal = d.get("is_internal", False)
        state.phase = phase
        state.errors = d.get("errors", [])
        state.timings = d.get("timings", {})
        state.should_retrieve = d.get("should_retrieve", True)
        state.retrieval_config = d.get("retrieval_config", {})
        state.episodic_context = d.get("episodic_context", "")
        state.episodes_retrieved = d.get("episodes_retrieved", 0)
        state.procedure_guidance = d.get("procedure_guidance", "")
        state.memory_guidance = d.get("memory_guidance", {})
        state.reasoning_context = d.get("reasoning_context", "")
        state.metacognitive_guidance = d.get("metacognitive_guidance", "")
        state.conflicts_detected = d.get("conflicts_detected", [])
        state.is_competitor_comparison = d.get("is_competitor_comparison", False)
        state.competitors_mentioned = d.get("competitors_mentioned", [])
        state.competitor_context = d.get("competitor_context", "")
        state.query_intent = d.get("query_intent", "")
        state.query_entities = d.get("query_entities", {})
        state.query_constraints = d.get("query_constraints", [])
        state.suggested_response_length = d.get("suggested_response_length", "medium")
        state.customer_name = d.get("customer_name")
        state.customer_company = d.get("customer_company")
        state.customer_role = d.get("customer_role")
        state.customer_style = d.get("customer_style", "default")
        state.customer_relationship = d.get("customer_relationship", "unknown")
        return state

    def add_error(self, phase: str, error: str):
        """Record an error with context."""
        self.errors.append(f"[{phase}] {error}")
    
    def record_timing(self, phase: str, ms: float):
        """Record processing time for a phase."""
        self.timings[phase] = ms
    
    def to_context_pack(self) -> Dict[str, Any]:
        """Convert to the context_pack format expected by generate_answer."""
        pack = {
            "user_memories": self.user_memories,
            "entity_memories": self.entity_memories,
            "episodic_context": self.episodic_context,
            "procedure_guidance": self.procedure_guidance,
            "memory_guidance": self.memory_guidance,
            "reasoning_context": self.reasoning_context,
            "metacognitive_guidance": self.metacognitive_guidance,
            "conflicts": self.conflicts_detected,
            "goal_proactive_prompt": self.goal_proactive_prompt,
            "goal_status": self.goal_status,
            "goal_context": self.goal_context,
            "competitor_context": self.competitor_context,
            "is_competitor_comparison": self.is_competitor_comparison,
            "competitors_mentioned": self.competitors_mentioned,
            "query_intent": self.query_intent,
            "query_entities": self.query_entities,
            "query_constraints": self.query_constraints,
            "suggested_response_length": self.suggested_response_length,
            "customer_name": self.customer_name,
            "customer_company": self.customer_company,
            "customer_role": self.customer_role,
            "customer_style": self.customer_style,
            "customer_relationship": self.customer_relationship,
            **self.final_context
        }
        
        if self.query_analysis:
            pack["query_analysis_context"] = (
                self.query_analysis.to_prompt_context() 
                if hasattr(self.query_analysis, 'to_prompt_context') else ""
            )
        
        if self.customer_context:
            pack["customer_context_formatted"] = (
                self.customer_context.to_prompt_context() 
                if hasattr(self.customer_context, 'to_prompt_context') else ""
            )
            pack["customer_style_instructions"] = (
                self.customer_context.get_style_instructions() 
                if hasattr(self.customer_context, 'get_style_instructions') else ""
            )
        
        return pack


# =============================================================================
# ATTENTION MANAGER - Working Memory Limits
# =============================================================================

class AttentionManager:
    """
    Implements working memory limits (Miller's 7±2).
    
    Not everything can fit in the prompt. This prioritizes what matters.
    """
    
    MAX_ITEMS = 7
    
    PRIORITY_WEIGHTS = {
        "query_analysis_context": 0.96,
        "customer_context_formatted": 0.95,
        "customer_style_instructions": 0.94,
        "procedure_guidance": 0.93,
        "conflicts": 0.90,
        "competitor_context": 0.89,
        "goal_proactive_prompt": 0.88,
        "metacognitive_guidance": 0.85,
        "goal_context": 0.82,
        "reasoning_context": 0.80,
        "episodic_context": 0.75,
        "memory_guidance": 0.70,
        "user_memories": 0.65,
        "entity_memories": 0.60,
        "rag_chunks": 0.50,
        "recent_messages": 0.40,
    }
    
    def __init__(self, max_items: int = 7):
        self.max_items = max_items
    
    def prioritize(self, items: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """
        Filter items to fit within working memory capacity.
        
        Returns: (filtered_items, num_filtered_out)
        """
        if not items:
            return {}, 0
        
        scored = []
        for key, value in items.items():
            if value is None or value == "" or value == []:
                continue
            
            base_weight = self.PRIORITY_WEIGHTS.get(key, 0.3)
            relevance_boost = self._calculate_relevance(key, value)
            score = base_weight * (1 + relevance_boost)
            
            scored.append((key, value, score))
        
        scored.sort(key=lambda x: x[2], reverse=True)
        
        filtered = {}
        for key, value, score in scored[:self.max_items]:
            filtered[key] = value
        
        filtered_out = len(scored) - len(filtered)
        return filtered, filtered_out
    
    def _calculate_relevance(self, key: str, value: Any) -> float:
        """Calculate relevance boost based on content."""
        boost = 0.0
        
        if isinstance(value, str) and len(value) > 100:
            boost += 0.1
        elif isinstance(value, list) and len(value) > 2:
            boost += 0.1
        elif isinstance(value, dict) and len(value) > 2:
            boost += 0.1
        
        return boost


# =============================================================================
# FEEDBACK LEARNER - Calibration Learning
# =============================================================================

class FeedbackLearner:
    """
    Learns from assessment outcomes to improve calibration.
    
    When meta-cognition says "uncertain" but the response was correct,
    we should be more confident next time for similar queries.
    """
    
    def __init__(self):
        self._calibration_data = {}
        self._load_calibration()
    
    def _get_calibration_path(self) -> Path:
        return PROJECT_ROOT / "openclaw/agents/ira/workspace/calibration.json"
    
    def _load_calibration(self):
        path = self._get_calibration_path()
        if path.exists():
            try:
                self._calibration_data = json.loads(path.read_text())
            except (json.JSONDecodeError, IOError, OSError):
                self._calibration_data = {}
    
    def _save_calibration(self):
        path = self._get_calibration_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._calibration_data, indent=2))
    
    def record_outcome(self, query_type: str, predicted_confidence: float, 
                       actual_success: bool):
        """Record the outcome of a prediction for future calibration."""
        if query_type not in self._calibration_data:
            self._calibration_data[query_type] = {
                "predictions": [],
                "outcomes": []
            }
        
        self._calibration_data[query_type]["predictions"].append(predicted_confidence)
        self._calibration_data[query_type]["outcomes"].append(actual_success)
        
        # Keep only last 100 records per query type
        if len(self._calibration_data[query_type]["predictions"]) > 100:
            self._calibration_data[query_type]["predictions"] = \
                self._calibration_data[query_type]["predictions"][-100:]
            self._calibration_data[query_type]["outcomes"] = \
                self._calibration_data[query_type]["outcomes"][-100:]
        
        self._save_calibration()
    
    def get_calibration_adjustment(self, query_type: str) -> float:
        """
        Get calibration adjustment for a query type.
        
        Returns: adjustment factor (positive means be more confident,
                 negative means be less confident)
        """
        if query_type not in self._calibration_data:
            return 0.0
        
        data = self._calibration_data[query_type]
        if len(data["predictions"]) < 5:
            return 0.0
        
        avg_predicted = sum(data["predictions"]) / len(data["predictions"])
        actual_success_rate = sum(data["outcomes"]) / len(data["outcomes"])
        
        adjustment = actual_success_rate - avg_predicted
        return max(-0.2, min(0.2, adjustment))
