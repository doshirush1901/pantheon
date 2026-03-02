"""
Iris Enrichment Skill - Adapter for the Iris Lead Intelligence Agent

Provides async iris_enrich() for the UnifiedGateway pipeline.
Uses native async Iris agent (aiohttp) - no run_in_executor.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger("ira.iris_skill")


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
