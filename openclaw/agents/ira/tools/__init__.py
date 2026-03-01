"""
Ira Tools - Callable capabilities for agent integrations

These tools provide a standard interface for invoking Ira's core
capabilities from external agents or automation frameworks.

Usage:
    from openclaw.agents.ira.tools import (
        ira_query,
        ira_email_draft,
        ira_market_research,
        ira_customer_lookup,
    )
    
    result = ira_query("What machines do we make?")
"""

from .query import ira_query, IraQueryTool
from .email import ira_email_draft, ira_email_send, IraEmailTool
from .research import ira_market_research, IraResearchTool
from .customer import ira_customer_lookup, IraCustomerTool

__all__ = [
    # Functions
    "ira_query",
    "ira_email_draft",
    "ira_email_send",
    "ira_market_research",
    "ira_customer_lookup",
    # Classes
    "IraQueryTool",
    "IraEmailTool",
    "IraResearchTool",
    "IraCustomerTool",
]
