"""
Sphinx — The Gatekeeper of Clarity.

Pre-flight clarification agent: asks numbered questions for vague requests,
then merges answers into an enriched brief for Athena.
"""

from openclaw.agents.ira.src.agents.sphinx.agent import (
    detect_task_type,
    format_questions_for_user,
    merge_brief,
    generate_questions,
    should_clarify,
)
from openclaw.agents.ira.src.agents.sphinx.state import (
    clear_sphinx_pending,
    get_sphinx_pending,
    store_sphinx_pending,
)

__all__ = [
    "should_clarify",
    "generate_questions",
    "merge_brief",
    "detect_task_type",
    "format_questions_for_user",
    "get_sphinx_pending",
    "store_sphinx_pending",
    "clear_sphinx_pending",
]
