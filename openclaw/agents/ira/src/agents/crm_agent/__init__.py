"""
Mnemosyne — The Keeper of Relationships (CRM Agent)
"""

from .agent import (
    lookup_contact,
    get_lead_brief,
    get_drip_candidates,
    get_pipeline_overview,
    suggest_next_action,
    LeadBrief,
)

__all__ = [
    "lookup_contact",
    "get_lead_brief",
    "get_drip_candidates",
    "get_pipeline_overview",
    "suggest_next_action",
    "LeadBrief",
]
