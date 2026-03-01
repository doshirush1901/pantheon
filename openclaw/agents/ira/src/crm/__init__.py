"""
CRM Skills Package
==================

Customer relationship management features for Ira.

Modules:
- quote_lifecycle: Track quotes through their lifecycle
- customer_health: Engagement scoring and risk alerts
- follow_up_automation: Proactive follow-up suggestions
"""

from pathlib import Path

SKILL_DIR = Path(__file__).parent

try:
    from .quote_lifecycle import (
        QuoteTracker, 
        get_tracker,
        Quote,
        QuoteStatus,
        FollowUp,
        FollowUpType,
        PipelineStats,
    )
except ImportError:
    pass

try:
    from .follow_up_automation import (
        FollowUpEngine,
        get_engine as get_follow_up_engine,
        FollowUpSuggestion,
        FollowUpPriority,
        run_daily_follow_up_check,
    )
except ImportError:
    pass

try:
    from .customer_health import (
        HealthScorer,
        get_scorer as get_health_scorer,
        CustomerHealth,
        RiskLevel,
        EngagementTrend,
        run_health_check,
    )
except ImportError:
    pass
