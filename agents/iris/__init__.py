"""
IRIS - Lead Intelligence Agent
===============================

The swift messenger who gathers real-time intelligence about leads.

Usage:
    # Single lead
    from agents.iris import Iris
    
    iris = Iris()
    context = iris.enrich_lead("eu-012", "TSN Kunststoffverarbeitung", "Germany")
    print(context.news_hook)
    
    # Batch enrichment
    from agents.iris import enrich_top_25_hot_leads
    
    result = enrich_top_25_hot_leads()
    print(result.summary())
    print(result.to_report())
"""

from .agent import (
    Iris,
    IrisContext,
    IrisBatchProcessor,
    BatchEnrichmentResult,
    enrich_lead_for_email,
    enrich_lead_for_email_async,
    batch_enrich_european_leads,
    enrich_top_25_hot_leads,
)

__all__ = [
    "Iris",
    "IrisContext",
    "IrisBatchProcessor",
    "BatchEnrichmentResult",
    "enrich_lead_for_email",
    "enrich_lead_for_email_async",
    "batch_enrich_european_leads",
    "enrich_top_25_hot_leads",
]
