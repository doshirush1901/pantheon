"""
IRA Agents Module (OpenClaw Native)

This module provides the Pantheon of skills as service functions that can be
invoked by the LLM through OpenClaw's native tool system.

The Pantheon:
- Athena (Chief of Staff) - Orchestration and planning
- Clio (Researcher) - Knowledge retrieval
- Calliope (Writer) - Content creation
- Vera (Fact Checker) - Verification
- Sophia (Reflector) - Learning

Usage:
    from openclaw.agents.ira.src.agents import research, write, verify, reflect
    
    # In an async context:
    research_output = await research("What are the specs for PF1-C-2015?")
    draft = await write("Query", {"research_output": research_output})
    verified = await verify(draft, "Original query")
"""

# Core service functions (OpenClaw native style)
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

from .chief_of_staff.agent import (
    analyze_intent,
    get_recommended_skills,
    create_plan,
    synthesize_response,
    get_intent,
)

# Data structures
from .researcher.agent import ResearchResult
from .fact_checker.agent import VerificationReport
from .reflector.agent import ReflectionResult, QualityScore
from .chief_of_staff.agent import Plan, OrchestrationResult

__all__ = [
    # Core functions
    "research",
    "write", 
    "verify",
    "reflect",
    
    # Intent helpers
    "analyze_intent",
    "get_recommended_skills",
    "create_plan",
    "synthesize_response",
    "get_intent",
    
    # Research utilities
    "get_machine_specs",
    "list_machines",
    "check_thickness_compatibility",
    
    # Writing utilities
    "format_for_channel",
    "add_brand_voice",
    
    # Verification utilities
    "generate_verification_report",
    
    # Reflection utilities
    "get_recent_errors",
    "get_recent_lessons",
    "get_quality_trends",
    
    # Data structures
    "ResearchResult",
    "VerificationReport",
    "ReflectionResult",
    "QualityScore",
    "Plan",
    "OrchestrationResult",
]
