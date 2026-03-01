"""
Sales Skills Package
=====================

High-level sales automation skills for IRA:
- Quote generation with PDF output
- Proactive outreach
- Sales pipeline management
"""

from .quote_generator import (
    generate_quote,
    SalesQuoteGenerator,
    QuotePDF,
)
from .proactive_outreach import (
    ProactiveOutreachEngine,
    get_outreach_engine,
    identify_outreach_candidates,
    draft_follow_up_email,
)

__all__ = [
    "generate_quote",
    "SalesQuoteGenerator",
    "QuotePDF",
    "ProactiveOutreachEngine",
    "get_outreach_engine",
    "identify_outreach_candidates",
    "draft_follow_up_email",
]
