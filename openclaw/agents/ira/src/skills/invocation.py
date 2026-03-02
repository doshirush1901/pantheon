"""
Unified Skill Invocation - Single source of truth for skill execution.

Per The Covenant: no duplication. All skill invocation logic lives here.
Used by UnifiedGateway, StreamingGateway, and any future BusOrchestrator.
"""

import logging
from typing import Any, AsyncGenerator, Dict, Optional

logger = logging.getLogger("ira.skills.invocation")

# Sentinel for unavailable skills
UNAVAILABLE = object()


def _load_research() -> Any:
    """Lazy-load research skill."""
    try:
        from openclaw.agents.ira.src.agents.researcher.agent import research
        return research
    except ImportError as e:
        logger.warning(f"Research skill unavailable: {e}")
        return UNAVAILABLE


def _load_write() -> Any:
    """Lazy-load write skill."""
    try:
        from openclaw.agents.ira.src.agents.writer.agent import write
        return write
    except ImportError as e:
        logger.warning(f"Write skill unavailable: {e}")
        return UNAVAILABLE


def _load_write_streaming() -> Any:
    """Lazy-load write_streaming skill."""
    try:
        from openclaw.agents.ira.src.agents.writer.agent import write_streaming
        return write_streaming
    except ImportError as e:
        logger.warning(f"Write streaming skill unavailable: {e}")
        return UNAVAILABLE


def _load_verify() -> Any:
    """Lazy-load verify skill."""
    try:
        from openclaw.agents.ira.src.agents.fact_checker.agent import verify
        return verify
    except ImportError as e:
        logger.warning(f"Verify skill unavailable: {e}")
        return UNAVAILABLE


def _load_iris_enrich() -> Any:
    """Lazy-load iris_enrich skill."""
    try:
        from openclaw.agents.ira.src.agents.iris_skill import iris_enrich
        return iris_enrich
    except ImportError as e:
        logger.warning(f"Iris enrich skill unavailable: {e}")
        return UNAVAILABLE


def _load_reflect() -> Any:
    """Lazy-load reflect skill."""
    try:
        from openclaw.agents.ira.src.agents.reflector.agent import reflect
        return reflect
    except ImportError as e:
        logger.warning(f"Reflect skill unavailable: {e}")
        return UNAVAILABLE


def _load_crm_lookup() -> Any:
    """Lazy-load Mnemosyne CRM lookup skill."""
    try:
        from openclaw.agents.ira.src.agents.crm_agent.agent import lookup_contact
        return lookup_contact
    except ImportError as e:
        logger.warning(f"CRM lookup skill unavailable: {e}")
        return UNAVAILABLE


def _load_crm_pipeline() -> Any:
    """Lazy-load Mnemosyne pipeline overview skill."""
    try:
        from openclaw.agents.ira.src.agents.crm_agent.agent import get_pipeline_overview
        return get_pipeline_overview
    except ImportError as e:
        logger.warning(f"CRM pipeline skill unavailable: {e}")
        return UNAVAILABLE


def _load_crm_drip() -> Any:
    """Lazy-load Mnemosyne drip candidates skill."""
    try:
        from openclaw.agents.ira.src.agents.crm_agent.agent import get_drip_candidates
        return get_drip_candidates
    except ImportError as e:
        logger.warning(f"CRM drip skill unavailable: {e}")
        return UNAVAILABLE


def _load_identity() -> Any:
    """Lazy-load identity service."""
    try:
        from openclaw.agents.ira.src.identity.unified_identity import UnifiedIdentityService
        return UnifiedIdentityService()
    except ImportError as e:
        logger.warning(f"Identity service unavailable: {e}")
        return UNAVAILABLE


async def invoke_research(message: str, context: Dict[str, Any]) -> str:
    """
    Invoke research skill. Returns research output string.
    """
    fn = _load_research()
    if fn is UNAVAILABLE:
        return ""
    return await fn(message, context)


async def invoke_write(message: str, context: Dict[str, Any]) -> str:
    """
    Invoke write skill. Returns draft string.
    """
    fn = _load_write()
    if fn is UNAVAILABLE:
        raise RuntimeError("Write skill unavailable")
    return await fn(message, context)


async def invoke_write_streaming(
    message: str, context: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    """
    Invoke write_streaming skill. Yields tokens.
    """
    fn = _load_write_streaming()
    if fn is UNAVAILABLE:
        yield "Error: Write streaming unavailable."
        return
    async for token in fn(message, context):
        yield token


async def invoke_verify(
    draft: str, original_query: str, context: Dict[str, Any]
) -> str:
    """
    Invoke verify skill. Returns verified draft.
    """
    fn = _load_verify()
    if fn is UNAVAILABLE:
        return draft
    return await fn(draft, original_query, context)


async def invoke_iris_enrich(context: Dict[str, Any]) -> Dict[str, str]:
    """
    Invoke iris_enrich skill. Returns email-ready dict.
    """
    fn = _load_iris_enrich()
    if fn is UNAVAILABLE:
        return {}
    return await fn(context)


async def invoke_reflect(interaction_data: Dict[str, Any]) -> None:
    """
    Invoke reflect skill. Fire-and-forget.
    """
    fn = _load_reflect()
    if fn is UNAVAILABLE:
        return
    await fn(interaction_data)


async def invoke_crm_lookup(query: str, context: Dict[str, Any] = None) -> str:
    """Invoke Mnemosyne CRM lookup. Returns contact/lead brief."""
    fn = _load_crm_lookup()
    if fn is UNAVAILABLE:
        return "CRM not available."
    return await fn(query, context)


async def invoke_crm_pipeline(context: Dict[str, Any] = None) -> str:
    """Invoke Mnemosyne pipeline overview."""
    fn = _load_crm_pipeline()
    if fn is UNAVAILABLE:
        return "CRM not available."
    return await fn(context)


async def invoke_crm_drip(context: Dict[str, Any] = None) -> str:
    """Invoke Mnemosyne drip candidates."""
    fn = _load_crm_drip()
    if fn is UNAVAILABLE:
        return "CRM not available."
    return await fn(context)


def invoke_identity_resolve(channel: str, identifier: str) -> Optional[str]:
    """
    Invoke identity service resolve. Sync.
    """
    svc = _load_identity()
    if svc is UNAVAILABLE or not hasattr(svc, "resolve"):
        return None
    return svc.resolve(channel, identifier)


def get_skill_availability() -> Dict[str, str]:
    """
    Report which skills are available. For health checks.
    """
    result: Dict[str, str] = {}
    for name, loader in [
        ("research", _load_research),
        ("write", _load_write),
        ("write_streaming", _load_write_streaming),
        ("verify", _load_verify),
        ("iris_enrich", _load_iris_enrich),
        ("reflect", _load_reflect),
        ("crm_lookup", _load_crm_lookup),
        ("crm_pipeline", _load_crm_pipeline),
        ("crm_drip", _load_crm_drip),
        ("identity", _load_identity),
    ]:
        try:
            val = loader()
            result[name] = "available" if val is not UNAVAILABLE else "unavailable"
        except Exception as e:
            result[name] = f"error: {e}"
    return result
