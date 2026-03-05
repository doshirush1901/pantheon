"""
Iris Enrichment Skill - Adapter for the Iris Lead Intelligence Agent

Provides async iris_enrich() for the UnifiedGateway pipeline.
Uses native async Iris agent (aiohttp) - no run_in_executor.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger("ira.iris_skill")


def _extract_company_from_message(message: str) -> str:
    """
    Heuristic extraction of company name from message when identity doesn't have it.
    Patterns: "to Acme Corp", "at Company GmbH", "for Company X", "draft for Acme", "email to XYZ"
    """
    if not message or len(message) < 5:
        return ""
    import re
    # "to Company Name" / "at Company Name" / "for Company Name"
    for pat in [
        r"(?:to|for|at|about)\s+([A-Z][A-Za-z0-9\s&\.\-]{2,40}?)(?:\s|,|$|\.)",
        r"(?:company|lead|prospect)\s+([A-Z][A-Za-z0-9\s&\.\-]{2,40}?)(?:\s|,|$|\.)",
        r"([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:GmbH|Ltd|Inc|Ltd\.|LLC|AG|BV)",
    ]:
        m = re.search(pat, message, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            if len(name) > 2 and name.lower() not in ("the", "a", "an", "for", "to", "at"):
                return name
    return ""


async def iris_enrich(context: Dict[str, Any]) -> Dict[str, str]:
    """
    Enrich context with Iris intelligence (company news, industry trends, etc.).

    Args:
        context: Pipeline context with lead_id, company, and optionally
                 country, industries, website

    Returns:
        Dict of email-ready variables: news_hook, industry_hook, geo_context,
        timely_opener, value_prop_angle, etc. Empty dict if Iris unavailable.
    """
    lead_id = context.get("lead_id") or context.get("lead", "")
    company = context.get("company", "")
    if not company:
        # Max mode: extract from message when identity doesn't have company
        message = context.get("message", "")
        company = _extract_company_from_message(message or "")
    if not company:
        return {}

    country = context.get("country", "")
    industries = context.get("industries") or context.get("industry") or []
    if isinstance(industries, str):
        industries = [industries]
    website = context.get("website", "")

    try:
        from agents.iris.agent import enrich_lead_for_email_async
    except ImportError:
        try:
            import sys
            from pathlib import Path
            root = Path(__file__).resolve().parents[3]
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            from agents.iris.agent import enrich_lead_for_email_async
        except ImportError as e:
            logger.warning(f"Iris agent unavailable: {e}")
            return {}

    try:
        return await enrich_lead_for_email_async(
            lead_id=lead_id,
            company=company,
            country=country,
            industries=industries,
            website=website,
        )
    except Exception as e:
        logger.warning(f"Iris enrichment failed: {e}")
        return {}
