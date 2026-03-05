"""
Observers — post-turn hooks that extract learnings from conversations.

The RealTimeObserver runs after every conversation turn, extracting
short-term patterns (facts, corrections, preferences) into a
conversation-scoped hub. These are used immediately on the next turn
and consolidated into long-term memory during nightly nap.
"""

from openclaw.agents.ira.src.observers.realtime_observer import (
    RealTimeObserver,
    get_realtime_observer,
)
from openclaw.agents.ira.src.observers.realtime_hub import (
    RealTimeHub,
    LearnedPattern,
    PatternType,
    get_realtime_hub,
)

__all__ = [
    "RealTimeObserver",
    "get_realtime_observer",
    "RealTimeHub",
    "LearnedPattern",
    "PatternType",
    "get_realtime_hub",
]
