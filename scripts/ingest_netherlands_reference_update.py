#!/usr/bin/env python3
"""
CRITICAL UPDATE: Ingest Netherlands Reference Site Changes

Batelaan is NO LONGER operational (sold and closed in 2026).
DutchTides and Dezet are now the active Netherlands reference sites.

This is HIGH PRIORITY knowledge that must override any previous references to Batelaan.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "netherlands_reference_sites_update.md"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create knowledge items for the Netherlands reference update."""
    items = []

    # 1. Critical status change about Batelaan
    items.append(KnowledgeItem(
        text="""CRITICAL UPDATE: BATELAAN IS NO LONGER A REFERENCE SITE (February 2026)

⚠️ IMPORTANT: Batelaan (Netherlands) is NO LONGER operational.
- Batelaan was sold to another company in 2026
- They have shut down operations
- DO NOT offer Batelaan as a factory visit destination
- DO NOT mention Batelaan as an active customer

Previous references to Batelaan should be updated to mention DutchTides instead.

When a European prospect asks to see a machine in the Netherlands, direct them to:
1. DutchTides (primary) - near Den Haag
2. Dezet - near Den Haag

Both locations are approximately 1 hour from Amsterdam Schiphol Airport.""",
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="Batelaan",
        summary="CRITICAL: Batelaan is CLOSED (2026) - use DutchTides/Dezet instead",
        metadata={
            "topic": "reference_site_closure",
            "priority": "critical",
            "customer": "Batelaan",
            "status": "closed",
            "alternative_references": ["DutchTides", "Dezet"]
        }
    ))

    # 2. DutchTides as primary reference
    items.append(KnowledgeItem(
        text="""DUTCHTIDES - PRIMARY NETHERLANDS REFERENCE SITE (2025)

Company: Dutch Tides
Location: Near Den Haag (The Hague), Netherlands
Industry: Hydroponics / Urban Farming
Contacts: Jurriaan van den Bos, Jaap Van Pooy

MACHINE DETAILS:
- Model: PF1-X-6520
- Forming Area: 6 x 2 meters (one of the largest in Europe)
- Application: Hydroponic Ebb Flow Trays
- Material: 4mm thick Polystyrene (PS) sheets
- Cycle Time: ~150 seconds per shot
- Value: €650,000
- Installed: 2025

WHY THIS IS A GREAT REFERENCE:
1. Massive scale - 6x2m forming area is impressive
2. Innovative application - hydroponics is growing sector
3. Recently installed - modern, well-maintained setup
4. Success story - startup achieving production goals
5. Full service - Machinecraft supplied machine + sheets + commissioning support
6. Accessible location - 1 hour from Schiphol Airport

LINKEDIN COVERAGE:
Post: "Revolutionizing Hydroponics with XL Thermoforming Innovation"
URL: https://www.linkedin.com/posts/rdd0101_hydroponics-thermoforming-machinecraft-activity-7427234843404701696-3V9k
Engagement: 122 likes, 8 comments including FRIMO CTO Rainer Janotta

HOW TO OFFER VISIT:
"We recently completed a successful installation of our PF1-X-6520 for Dutch Tides, an innovative hydroponics startup near Den Haag. This machine is producing one of the largest hydroponic trays on the market (6 x 2 meters) with remarkable precision. We would be delighted to arrange a visit for you to see this machine running in a live production environment." """,
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="DutchTides",
        summary="DutchTides (Netherlands): PF1-X-6520 6x2m €650K - PRIMARY reference site",
        metadata={
            "topic": "reference_site",
            "country": "Netherlands",
            "location": "Den Haag",
            "machine": "PF1-X-6520",
            "forming_area": "6x2m",
            "value": 650000,
            "application": "hydroponics",
            "status": "active_reference"
        }
    ))

    # 3. Dezet as secondary reference
    items.append(KnowledgeItem(
        text="""DEZET - SECONDARY NETHERLANDS REFERENCE SITE

Company: Dezet
Location: Near Den Haag, Netherlands

SIGNIFICANCE:
- Featured in LinkedIn article about replacing legacy machinery
- Story: Replaced a 1983 Illig thermoforming machine with modern Machinecraft PF1-X series
- Demonstrates Machinecraft's ability to modernize European factories

LINKEDIN COVERAGE:
Article: "From 1983 to 2025: A Story of Industrial Evolution"
URL: https://www.linkedin.com/posts/rdd0101_machinecraft-thermoforming-manufacturinginnovation-activity-7389891701663911936-7Vih
Theme: Helping European manufacturers replace aging equipment while cutting energy use

KEY MESSAGING:
- Not about changing how Europe manufactures
- About giving great teams better tools
- Modernizing legacy thermoforming lines
- Energy efficiency improvements

Can be combined with DutchTides visit for comprehensive Netherlands tour.""",
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="Dezet",
        summary="Dezet (Netherlands): Replaced 1983 Illig with PF1-X - secondary reference",
        metadata={
            "topic": "reference_site",
            "country": "Netherlands",
            "location": "Den Haag",
            "story": "legacy_replacement",
            "status": "active_reference"
        }
    ))

    # 4. Updated factory visit script
    items.append(KnowledgeItem(
        text="""FACTORY VISIT OFFERING - NETHERLANDS (Updated February 2026)

When European prospects ask to see a machine in Europe, offer Netherlands visit:

CORRECT RESPONSE:
"We would be delighted to arrange a visit for you and your team to see our machines in the Netherlands. 

Near Den Haag, we have two excellent reference sites:
1. Dutch Tides - producing large-scale hydroponic trays (6x2m) with our PF1-X-6520
2. Dezet - where we replaced a 1983 Illig machine with our modern PF1-X series

Both locations are about 1 hour from Amsterdam Schiphol Airport. I can arrange a one-day visit - I'll pick you up from the airport and we can see both machines running in live production environments."

DO NOT MENTION:
- Batelaan (closed in 2026)
- Any other Netherlands locations that may be outdated

LOGISTICS:
- Nearest airport: Amsterdam Schiphol (AMS)
- Travel time to Den Haag: ~1 hour
- Rushabh typically offers to pick up visitors personally
- Can combine both visits in one day""",
        knowledge_type="sales_knowledge",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Factory visit script for Netherlands: DutchTides + Dezet near Den Haag",
        metadata={
            "topic": "factory_visit_script",
            "country": "Netherlands",
            "locations": ["DutchTides", "Dezet"],
            "airport": "Amsterdam Schiphol",
            "travel_time": "1 hour"
        }
    ))

    return items


def main():
    print("=" * 60)
    print("CRITICAL UPDATE: Netherlands Reference Sites")
    print("=" * 60)
    print("\n⚠️  Batelaan is CLOSED - updating knowledge base\n")

    items = create_knowledge_items()

    print(f"Created {len(items)} knowledge items:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.summary[:55]}...")

    ingestor = KnowledgeIngestor()
    results = ingestor.ingest_batch(items)

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
