#!/usr/bin/env python3
"""
Ingest Car Mats Study - 3D Car Mats Manufacturers

Companies producing 3D car mats - target customers for ATF and PF1 machines.
This is a growing aftermarket segment for thermoforming.

Source: Car Mats Study.xlsx
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Car Mats Study.xlsx"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from car mats study."""
    items = []

    # 1. Car Mats Market Overview
    items.append(KnowledgeItem(
        text="""3D Car Mats Market Study - Overview

APPLICATION: 3D/Custom Car Floor Mats
MATERIAL: TPE, TPR, PVC, EVA (thermoformable)
MARKET: Automotive aftermarket, OEM accessories

MACHINECRAFT MACHINES FOR CAR MATS:
1. ATF (Auto Thermoforming) Series - Purpose-built for car mats
   - High volume production
   - Automated trim and stack
   - Multi-cavity tooling

2. PF1-C Series - Cut sheet thermoforming
   - Flexible production
   - Lower volume / custom sizes
   - Good for startup operations

3. AM-C Series - For smaller mat production
   - Entry-level option
   - Cost-effective for new entrants

PRODUCTION PROCESS:
1. Sheet material (TPE/TPR) fed to heating zone
2. Heated to forming temperature
3. Vacuum/pressure formed to 3D contour
4. Trimmed to final shape
5. Quality check and packaging

KEY SUCCESS FACTORS:
- Accurate vehicle-specific tooling
- Surface texture quality (anti-slip)
- Material durability and weather resistance
- Fast changeover between vehicle models""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Car Mats Application",
        summary="3D car mats: ATF/PF1-C/AM-C machines, TPE/TPR material, aftermarket segment",
        metadata={
            "topic": "car_mats_overview",
            "machines": ["ATF", "PF1-C", "AM-C"]
        }
    ))

    # 2. India Car Mats Companies
    items.append(KnowledgeItem(
        text="""3D Car Mats Study - India Market Leads

MAJOR INDIAN CAR MAT MANUFACTURERS:

1. SIPL Automotives
   - Contact: Ankur
   - Email: Ankur@siplautomotives.com
   - Alt: ryan.sankartt@gmail.com
   - Website: siplautomotives.com
   - Note: Established player, good prospect for ATF/PF1

2. Autoform India
   - Email: guptacarcraft@gmail.com
   - Website: autoformindia.com
   - Note: Major brand in aftermarket mats

3. Automat India
   - Contact: Parshv
   - Email: parshv@automat.in
   - Website: automat.in
   - Note: Growing brand

4. Premier Indoplast
   - Contact: Shyam
   - Email: shyam@premierindoplast.com
   - Alt: featherd3@gmail.com
   - Note: Already in PlastIndia leads - diversified player

5. Galio India (GFX Brand)
   - Email: 0757kp@gmail.com
   - Website: galioindia.com
   - Products: Life Long Car Floor Mats
   - Note: Strong online presence

6. QP India / Carorbis
   - Email: aevomauto@gmail.com
   - Website: qpoindia.com, carorbis.com
   - Note: E-commerce focused

7. Brotomotiv
   - Email: founders@brotomotiv.in
   - Note: Newer entrant, startup

8. Pratish Impex
   - Email: info@pratishimpex.com
   - Note: Trading/manufacturing

9. New Ashok
   - Email: newashokq@gmail.com
   - Note: Local manufacturer

INDIA MARKET OPPORTUNITY:
- 4M+ new cars sold annually in India
- Growing aftermarket accessories segment
- Shift from rubber to TPE/3D mats
- Premium segment growing faster""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="India Car Mat Leads",
        summary="India car mats: SIPL, Autoform, Automat, Premier, Galio - 9 leads, 4M car market",
        metadata={
            "topic": "india_car_mat_leads",
            "region": "India",
            "lead_count": 9
        }
    ))

    # 3. International Car Mats Companies
    items.append(KnowledgeItem(
        text="""3D Car Mats Study - International Market Leads

GLOBAL CAR MAT COMPANIES:

TURKEY:
1. Apesan
   - Location: Istanbul, Turkey
   - Website: www.apesan.com.tr
   - Note: Also in K2025 leads - cross reference
   - Machine Interest: Likely PF1 for car mats

EUROPE:
1. Frogum (Poland)
   - Website: www.frogum.com
   - Note: Major European car mat brand
   - Products: TPE floor mats, trunk mats

2. Car Shop (France)
   - Email: car-shop@hotmail.fr
   - Note: French distributor/manufacturer

USA:
1. WeatherTech (Reference/Benchmark)
   - Website: www.weathertech.com
   - Note: Market leader in premium car mats
   - Benchmark for quality and design
   - Uses advanced thermoforming

2. Racemark
   - Contact: Cilie
   - Email: cilie@racemark.com
   - Note: Performance/racing mats

LATIN AMERICA:
1. Convergent PT
   - Contact: Pablo Contreras
   - Email: pablocontreras@convergent-pt.com
   - Note: Potential distributor/manufacturer

2. Imapar (Colombia)
   - Email: gerencia@imapar.com.co
   - Note: Colombian market

3. Cooldtec
   - Email: oficina@cooldtec.com
   - Note: Latin American market

AFRICA:
1. Kenya Contact
   - Email: mwangi.kibuchi@gmail.com
   - Note: East African market opportunity

GLOBAL MARKET SIZE:
- $3B+ global car mat market
- Premium 3D mats fastest growing segment
- WeatherTech model: $500M+ revenue from car mats alone""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="International Car Mat Leads",
        summary="Global car mats: Apesan Turkey, Frogum Poland, WeatherTech benchmark, LATAM/Africa leads",
        metadata={
            "topic": "intl_car_mat_leads",
            "regions": ["Turkey", "Europe", "USA", "LATAM", "Africa"],
            "lead_count": 8
        }
    ))

    # 4. Machine Recommendations & Sales Strategy
    items.append(KnowledgeItem(
        text="""Car Mats - Machine Recommendations & Sales Strategy

MACHINE SELECTION BY PRODUCTION VOLUME:

HIGH VOLUME (>50,000 mats/month):
- Machine: ATF Series (Auto Thermoforming)
- Features: Automated feeding, forming, trimming, stacking
- Tooling: Multi-cavity molds
- Investment: Higher CAPEX, lower per-piece cost

MEDIUM VOLUME (10,000-50,000 mats/month):
- Machine: PF1-C Series (1015, 1507, 2016)
- Features: Cut-sheet feeding, versatile
- Tooling: Single/dual cavity
- Investment: Moderate CAPEX, flexible production

LOW VOLUME / STARTUP (<10,000 mats/month):
- Machine: AM-C Series (1507, 2016)
- Features: Manual/semi-auto operation
- Tooling: Basic vacuum forming
- Investment: Low CAPEX, quick ROI

SALES APPROACH:

For Established Players (SIPL, Autoform, Galio):
- Pitch ATF for capacity expansion
- Emphasize productivity gains
- ROI focus: labor savings, consistency

For Growing Companies (Automat, Brotomotiv):
- Pitch PF1-C for scaling up
- Flexibility for multiple vehicle models
- Growth path to ATF later

For New Entrants / Startups:
- Pitch AM-C as entry point
- Low investment to test market
- Upgrade path defined

COMPETITIVE ADVANTAGES:
- WeatherTech uses US-made machines (~$1M+)
- Machinecraft offers same quality at 50-70% cost
- Local service and tooling support in India
- Quick delivery vs import alternatives

TOOLING STRATEGY:
- Offer complete solution: machine + tooling
- Vehicle-specific molds as recurring business
- Partner with tooling houses for complex patterns""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Car Mats Sales Strategy",
        summary="Car mats strategy: ATF for high vol, PF1-C mid, AM-C entry; 50-70% cost vs US machines",
        metadata={
            "topic": "car_mats_strategy",
            "machines": ["ATF", "PF1-C", "AM-C"]
        }
    ))

    # 5. Contact List Summary
    items.append(KnowledgeItem(
        text="""Car Mats Study - Complete Contact List for CRM

HIGH PRIORITY (Established/Growing):
1. SIPL Automotives - Ankur@siplautomotives.com
2. Automat India - parshv@automat.in
3. Premier Indoplast - shyam@premierindoplast.com (existing contact)
4. Apesan Turkey - www.apesan.com.tr (K2025 cross-ref)
5. Autoform India - guptacarcraft@gmail.com

MEDIUM PRIORITY (Growing/New):
6. Galio India - 0757kp@gmail.com
7. QP India - aevomauto@gmail.com
8. Brotomotiv - founders@brotomotiv.in
9. Frogum Poland - www.frogum.com
10. Convergent PT - pablocontreras@convergent-pt.com

REFERENCE/RESEARCH:
11. WeatherTech USA - www.weathertech.com (benchmark study)
12. Racemark - cilie@racemark.com
13. Imapar Colombia - gerencia@imapar.com.co
14. Cooldtec - oficina@cooldtec.com
15. Car Shop France - car-shop@hotmail.fr

FOLLOW-UP ACTIONS:
- Research each company's current production capacity
- Identify which already have thermoforming equipment
- Prepare car mat specific presentation
- Develop ROI calculator for car mat production
- Cross-reference with PlastIndia and K2025 leads""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Car Mats Contact Summary",
        summary="Car mats CRM: 5 high priority, 5 medium priority, cross-ref PlastIndia/K2025",
        metadata={
            "topic": "car_mats_contacts",
            "total_leads": 15
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Car Mats Study Ingestion")
    print("Source: " + SOURCE_FILE)
    print("=" * 60)

    items = create_knowledge_items()

    print(f"\nCreated {len(items)} knowledge items:")
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
