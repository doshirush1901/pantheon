"""
Brain Orchestrator - Ties together all brain modules.

This was the missing piece that connects:
- Machine Recommender
- Knowledge Retriever
- Generate Answer
- BrainState coordination
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

try:
    from .brain_state import BrainState, ProcessingPhase, AttentionManager
except ImportError:
    from brain_state import BrainState, ProcessingPhase, AttentionManager

_logger = logging.getLogger("ira.brain_orchestrator")


# Try to import brain modules
MODULES_AVAILABLE = {}

try:
    from machine_recommender import recommend_from_query, recommend_machines
    MODULES_AVAILABLE["machine_recommender"] = True
except ImportError:
    try:
        from ..brain.machine_recommender import recommend_from_query, recommend_machines
        MODULES_AVAILABLE["machine_recommender"] = True
    except ImportError as e:
        _logger.warning(f"Machine recommender not available: {e}")
        MODULES_AVAILABLE["machine_recommender"] = False

try:
    from generate_answer import generate_answer, generate_email_response
    MODULES_AVAILABLE["generate_answer"] = True
except ImportError:
    try:
        from ..brain.generate_answer import generate_answer, generate_email_response
        MODULES_AVAILABLE["generate_answer"] = True
    except ImportError as e:
        _logger.warning(f"Generate answer not available: {e}")
        MODULES_AVAILABLE["generate_answer"] = False

try:
    from unified_retriever import UnifiedRetriever
    MODULES_AVAILABLE["unified_retriever"] = True
except ImportError:
    try:
        from ..brain.unified_retriever import UnifiedRetriever
        MODULES_AVAILABLE["unified_retriever"] = True
    except ImportError as e:
        _logger.warning(f"Unified retriever not available: {e}")
        MODULES_AVAILABLE["unified_retriever"] = False

try:
    from hybrid_search import hybrid_search, get_hybrid_searcher
    MODULES_AVAILABLE["hybrid_search"] = True
except ImportError:
    try:
        from ..brain.hybrid_search import hybrid_search, get_hybrid_searcher
        MODULES_AVAILABLE["hybrid_search"] = True
    except ImportError as e:
        _logger.warning(f"Hybrid search not available: {e}")
        MODULES_AVAILABLE["hybrid_search"] = False


@dataclass
class BrainOrchestrator:
    """
    Coordinates all brain modules for intelligent processing.
    
    This orchestrator provides:
    1. Machine recommendations from natural language queries
    2. Knowledge retrieval and hybrid search
    3. Response generation with full context
    4. Working memory management (attention filtering)
    """
    
    attention_manager: AttentionManager = field(default_factory=AttentionManager)
    
    @property
    def modules(self) -> Dict[str, bool]:
        """Return status of all available modules."""
        return MODULES_AVAILABLE.copy()
    
    @property
    def available(self) -> bool:
        """Check if core modules are available."""
        return any(MODULES_AVAILABLE.values())
    
    def process(
        self,
        message: str,
        identity_id: Optional[str] = None,
        channel: str = "telegram",
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> BrainState:
        """
        Process a message through the brain pipeline.
        
        Pipeline:
        1. Create BrainState
        2. Check for machine recommendation intent
        3. Retrieve relevant knowledge
        4. Apply attention filtering
        5. Return enriched state
        """
        # Create brain state
        state = BrainState(
            message=message,
            identity_id=identity_id,
            channel=channel,
            context=context or {},
            **{k: v for k, v in kwargs.items() if hasattr(BrainState, k)}
        )
        
        state.phase = ProcessingPhase.QUERY_ANALYSIS
        
        # Detect machine recommendation intent
        machine_keywords = [
            "machine", "recommend", "price", "cost", "forming",
            "thickness", "material", "budget", "specification",
            "PF1", "PF2", "AM", "ATF", "IMG", "UNO", "DUO"
        ]
        
        is_machine_query = any(kw.lower() in message.lower() for kw in machine_keywords)
        
        if is_machine_query and MODULES_AVAILABLE.get("machine_recommender"):
            state.phase = ProcessingPhase.PROCEDURAL
            try:
                rec_result = recommend_from_query(message)
                if rec_result and rec_result.recommendations:
                    state.procedure_guidance = self._format_recommendations(rec_result)
                    state.matched_procedure = rec_result
                    _logger.info(f"Machine recommendations: {len(rec_result.recommendations)} matches")
            except Exception as e:
                state.add_error("machine_recommender", str(e))
                _logger.error(f"Machine recommender error: {e}")
        
        # Run knowledge retrieval
        if MODULES_AVAILABLE.get("unified_retriever"):
            state.phase = ProcessingPhase.RETRIEVAL
            try:
                retriever = UnifiedRetriever()
                # This will be filled in by RAG later
            except Exception as e:
                state.add_error("retrieval", str(e))
        
        # Apply attention filtering
        state.phase = ProcessingPhase.ATTENTION
        context_pack = state.to_context_pack()
        filtered, num_filtered = self.attention_manager.prioritize(context_pack)
        state.final_context = filtered
        state.items_filtered = num_filtered
        
        state.phase = ProcessingPhase.COMPLETE
        return state
    
    def _format_recommendations(self, result) -> str:
        """Format machine recommendations into guidance text."""
        lines = ["MACHINE RECOMMENDATIONS:"]
        
        for i, rec in enumerate(result.recommendations[:3], 1):
            lines.append(f"\n{i}. {rec.machine.model}")
            lines.append(f"   Forming: {rec.machine.forming_area_mm}")
            lines.append(f"   Price: ₹{rec.machine.price_inr:,}")
            if rec.machine.price_usd:
                lines.append(f"   (~${rec.machine.price_usd:,} USD)")
            lines.append(f"   Match Score: {rec.overall_score:.0%}")
            if rec.size_match_pct:
                lines.append(f"   Size Match: {rec.size_match_pct:.0%}")
            if rec.budget_within:
                lines.append(f"   ✓ Within Budget")
        
        if result.constraints_parsed:
            lines.append(f"\nParsed Requirements:")
            c = result.constraints_parsed
            if c.get("forming_area"):
                lines.append(f"   - Forming: {c['forming_area']}mm")
            if c.get("max_thickness"):
                lines.append(f"   - Thickness: up to {c['max_thickness']}mm")
            if c.get("budget_inr"):
                lines.append(f"   - Budget: ₹{c['budget_inr']:,}")
        
        return "\n".join(lines)
    
    def recommend_machine(self, query: str) -> Optional[str]:
        """Convenience method for direct machine recommendations."""
        if not MODULES_AVAILABLE.get("machine_recommender"):
            return None
        
        try:
            result = recommend_from_query(query)
            if result and result.recommendations:
                return self._format_recommendations(result)
        except Exception as e:
            _logger.error(f"Recommendation error: {e}")
        
        return None


# Singleton instance
_brain_instance: Optional[BrainOrchestrator] = None


def get_brain() -> BrainOrchestrator:
    """Get or create the brain orchestrator singleton."""
    global _brain_instance
    if _brain_instance is None:
        _brain_instance = BrainOrchestrator()
        _logger.info(f"Brain orchestrator initialized with modules: {_brain_instance.modules}")
    return _brain_instance
