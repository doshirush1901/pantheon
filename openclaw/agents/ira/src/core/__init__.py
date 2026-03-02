"""
Core components for IRA agent.

This module contains fundamental components used across all IRA modules:
- Brain state management classes
- Unified caching solution
"""

from .brain_state import (
    ProcessingPhase,
    BrainState,
    AttentionManager,
    FeedbackLearner,
)

from .redis_cache import (
    RedisCache,
    get_cache,
    get_connected_cache,
)

__all__ = [
    # Brain State
    "ProcessingPhase",
    "BrainState",
    "AttentionManager",
    "FeedbackLearner",
    # Caching
    "RedisCache",
    "get_cache",
    "get_connected_cache",
]
