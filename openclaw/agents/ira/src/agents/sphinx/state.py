"""
Sphinx pending state — in-memory store for clarification Q&A across messages.

Keyed by user_id. When the user replies after Sphinx asked questions,
the orchestrator checks this store, merges the brief, and clears it.
"""

from typing import Any, Dict, List, Optional

# In-memory: user_id -> { "original": str, "questions": list[str], "channel": str }
_SPHINX_PENDING: Dict[str, Dict[str, Any]] = {}


def get_sphinx_pending(user_id: str) -> Optional[Dict[str, Any]]:
    """Return pending Sphinx state for this user, or None."""
    return _SPHINX_PENDING.get(user_id)


def store_sphinx_pending(user_id: str, original_message: str, questions: List[str], channel: str = "api") -> None:
    """Store that we are waiting for this user to answer Sphinx questions."""
    _SPHINX_PENDING[user_id] = {
        "original": original_message,
        "questions": questions,
        "channel": channel,
    }


def clear_sphinx_pending(user_id: str) -> None:
    """Clear pending state after merging the brief or on skip."""
    _SPHINX_PENDING.pop(user_id, None)
