"""
Ira Tools - Callable capabilities for agent integrations

These tools provide a standard interface for invoking Ira's core
capabilities from external agents or automation frameworks.

Usage:
    from openclaw.agents.ira.tools import ira_email_draft, ira_email_send
"""

from .email import ira_email_draft, ira_email_send, IraEmailTool

__all__ = [
    "ira_email_draft",
    "ira_email_send",
    "IraEmailTool",
]
