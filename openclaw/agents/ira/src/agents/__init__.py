"""
IRA Agents Module (OpenClaw Native)

This module provides the Pantheon base skills as service functions that can be
invoked by the LLM through OpenClaw's native tool system.

The 4 base agents:
- Clio (Researcher) - Knowledge retrieval
- Calliope (Writer) - Content creation
- Vera (Fact Checker) - Verification
- Sophia (Reflector) - Learning

Usage:
    from openclaw.agents.ira.src.agents import research, write, verify, reflect

    research_output = await research("What are the specs for PF1-C-2015?")
    draft = await write("Query", {"research_output": research_output})
    verified = await verify(draft, "Original query")
"""

from .researcher.agent import (
    research,
    get_machine_specs,
    list_machines,
    check_thickness_compatibility,
)

from .writer.agent import (
    write,
    format_for_channel,
    add_brand_voice,
)

from .fact_checker.agent import (
    verify,
    generate_verification_report,
)

from .reflector.agent import (
    reflect,
    get_recent_errors,
    get_recent_lessons,
    get_quality_trends,
)

# Data structures
from .researcher.agent import ResearchResult
from .fact_checker.agent import VerificationReport
from .reflector.agent import ReflectionResult, QualityScore

__all__ = [
    "research",
    "write",
    "verify",
    "reflect",
    "get_machine_specs",
    "list_machines",
    "check_thickness_compatibility",
    "format_for_channel",
    "add_brand_voice",
    "generate_verification_report",
    "get_recent_errors",
    "get_recent_lessons",
    "get_quality_trends",
    "ResearchResult",
    "VerificationReport",
    "ReflectionResult",
    "QualityScore",
]
