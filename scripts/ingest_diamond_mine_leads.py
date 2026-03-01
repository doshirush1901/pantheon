#!/usr/bin/env python3
"""
Ingest Machinecraft Sales Diamond Mine - Prospect List by Material

72 prospects categorized by thermoforming materials they process.
Useful for targeted machine and material recommendations.

Source: Machinecraft Sales Diamond Mine.xlsx
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import directly from the module file
import importlib.util
spec = importlib.util.spec_from_file_location(
    "knowledge_ingestor",
    os.path.join(project_root, "openclaw/agents/ira/src/brain/knowledge_ingestor.py")
)
knowledge_ingestor_module = importlib.util.module_from_spec(spec)
sys.modules["knowledge_ingestor"] = knowledge_ingestor_module
spec.loader.exec_module(knowledge_ingestor_module)

KnowledgeIngestor = knowledge_ingestor_module.KnowledgeIngestor
KnowledgeItem = knowledge_ingestor_module.KnowledgeItem

SOURCE_FILE = "Machinecraft Sales Diamond Mine.xlsx"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from Diamond Mine prospects."""
    items = []

    # 1. Diamond Mine Overview
    items.append(KnowledgeItem(
        text="""Machinecraft Sales Diamond Mine - Prospect Overview

TOTAL PROSPECTS: 72 companies
MARKET: India (primarily)
DATA: Companies segmented by thermoforming materials processed

MATERIAL CATEGORIES:
1. ABS: 45 companies - Most common, automotive/industrial
2. ABS FR (Fire Retardant): 22 companies - Automotive/eBus interiors
3. ASA (UV resistant): 13 companies - Outdoor/exterior parts
4. HDPE: 16 companies - Heavy duty, industrial, outdoor
5. PP (Polypropylene): 6 companies - Low cost, flexible
6. PS (Polystyrene): 19 companies - Packaging, displays
7. TPE (Thermoplastic Elastomer): 4 companies - Car mats, soft-touch
8. PC (Polycarbonate): 10 companies - Lighting, transparent parts
9. ABS/PMMA: 2 companies - High gloss, automotive exterior

INDUSTRY SEGMENTS IDENTIFIED:
- Automotive OEMs & Tier-1: ~20 companies
- Lighting & Electrical: ~10 companies
- Consumer Products: ~15 companies
- Packaging: ~12 companies
- Industrial Products: ~15 companies

CROSS-REFERENCES:
Multiple companies appear in other lead lists (PlastIndia, K2025, LLM, European)
- Indicates high interest / multiple touchpoints""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Diamond Mine Overview",
        summary="Diamond Mine: 72 prospects by material, ABS (45), PS (19), HDPE (16), automotive dominant",
        metadata={
            "topic": "diamond_mine_overview",
            "total_leads": 72
        }
    ))

    # 2. Automotive & Transport Prospects
    items.append(KnowledgeItem(
        text="""Diamond Mine - Automotive & Transport Prospects

AUTOMOTIVE OEMs:
1. Tata Motors - ABS, ABS FR, HDPE, PP
   - Full range capability
   - Machines: PF1-X series

2. Ashok Leyland - ABS, ABS FR
   - CV manufacturer
   - Focus: Interior panels, dashboard

3. Sonalika Tractors - ABS
   - Already buying from Alphafoam
   - Tractor cabin interiors

4. Olectra - ABS, ABS FR
   - eBus manufacturer
   - FR critical for bus interiors
   - Cross-ref: CV Market contacts

AUTOMOTIVE TIER-1 SUPPLIERS:
5. Motherson - ABS
   - Global Tier-1
   - High potential
   - Cross-ref: PlastIndia leads

6. Maini Composites - ABS, ABS FR
   - Existing customer (PF1 + 5-axis)
   - Supplies Mahindra Treo

7. Pinnacle Industries - ABS, ABS FR, ASA
   - CV/Bus interiors specialist
   - Cross-ref: PlastIndia, CV Market

8. Mutual Automotive - ABS, ABS FR, ASA
   - Cross-ref: PlastIndia (4 contacts), LLM (Score 100)

9. Harita Fehrer Ltd - ABS
   - Seating/interior systems

10. Ather Energy - ABS FR
    - EV manufacturer
    - Cross-ref: PlastIndia

11. Sthenos Composites - ABS, ABS FR, ASA
    - Composite parts
    - Cross-ref: PlastIndia

12. Ukay Metal Industries - ABS, ABS FR, ASA, HDPE
    - Metal to plastic conversion opportunity

13. Durotuff - ABS, ABS FR, ASA
    - Industrial automotive parts
    - Cross-ref: PlastIndia

AUTOMOTIVE AFTERMARKET:
14. Automat - ABS, HDPE, TPE
    - Car mats, accessories
    - Cross-ref: Car Mats Study

15. AC Auto Connections - ABS, HDPE
    - Automotive accessories
    - Cross-ref: PlastIndia""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Diamond Mine Automotive",
        summary="Automotive: Tata, Ashok Leyland, Olectra OEMs; Motherson, Pinnacle, Mutual Tier-1; 15 prospects",
        metadata={
            "topic": "automotive_prospects",
            "segment": "Automotive",
            "lead_count": 15
        }
    ))

    # 3. Lighting & Electrical Prospects
    items.append(KnowledgeItem(
        text="""Diamond Mine - Lighting & Electrical Prospects

PC (POLYCARBONATE) PROCESSORS:
1. Raj Cooling Systems - ASA, PC
   - Cooling systems, enclosures
   - ASA for outdoor durability

2. VIP - PC
   - Luggage + lighting products

3. SVS - PC
   - Lighting components

4. Lighting Technologies - PC
   - Specialized lighting manufacturer

5. Daylight - PC
   - Daylighting systems
   - Skylights, roof lights

6. MK Daylighting - PC
   - Commercial daylighting
   - Large format panels

7. Jaquar - PC, ABS/PMMA
   - Bathroom fittings, lighting
   - High gloss surfaces

8. MG Polyplast - ABS, PC
   - Mixed plastics processor

9. Duraplast - ABS, PC
   - Industrial + lighting

10. NG Brothers - ABS, PC
    - Diverse plastics processing

MACHINE RECOMMENDATION FOR PC:
- PF1-X series with temperature control for PC
- AM-P series for pressure forming (better detail)
- Note: PC requires higher forming temperatures

APPLICATION TYPES:
- Light diffusers
- Skylights and roof panels
- Electrical enclosures
- Sign displays
- Protective covers""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Diamond Mine Lighting",
        summary="Lighting/Electrical: 10 PC processors - Raj, VIP, SVS, Daylight, MK, Jaquar, requires temp control",
        metadata={
            "topic": "lighting_electrical_prospects",
            "segment": "Lighting",
            "material": "PC",
            "lead_count": 10
        }
    ))

    # 4. Consumer Products & Packaging Prospects
    items.append(KnowledgeItem(
        text="""Diamond Mine - Consumer Products & Packaging Prospects

MAJOR CONSUMER BRANDS:
1. Nilkamal - ABS, ABS FR, HDPE
   - Furniture, storage, industrial
   - Large volume potential

2. Princeware - ABS
   - Household products
   - High volume thermoforming

3. Samsonite - ABS
   - Luggage manufacturing
   - Precision forming required

4. VIP - PC
   - Luggage + home products

5. Godrej - PS
   - Diversified products
   - Packaging focus

PACKAGING COMPANIES:
6. Transpack - PS
   - Industrial packaging

7. Sri Hari Pack - ABS, ABS FR, HDPE, PP
   - Multi-material capability
   - Diverse packaging

8. Propack - ABS, ABS FR
   - Protective packaging

9. Proform Packaging - ABS, HDPE
   - Custom packaging

10. Rajshree Polypack - ABS, PS
    - Packaging solutions

PS (POLYSTYRENE) SPECIALISTS:
11. Prakash Plastics - PS
12. Mirek - PP, PS
13. Southern Expanded PS - PS
14. Laser Shaving - PS
15. Indway Furniture - PS
16. Meridian Market Res - ABS, PS
17. Pallet Interation - PS
18. Formax - ABS, PS
19. Otter - PS

MACHINE RECOMMENDATION:
- FCS series for high-volume packaging
- AM series for medium volumes
- PF1 for custom/low volume""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Diamond Mine Consumer Packaging",
        summary="Consumer/Packaging: Nilkamal, Princeware, Samsonite, Godrej; 19 PS processors; FCS for volume",
        metadata={
            "topic": "consumer_packaging_prospects",
            "segment": ["Consumer", "Packaging"],
            "lead_count": 19
        }
    ))

    # 5. Industrial & Specialty Prospects
    items.append(KnowledgeItem(
        text="""Diamond Mine - Industrial & Specialty Prospects

MULTI-MATERIAL INDUSTRIAL:
1. Alphafoam - ABS, ABS FR, ASA, HDPE, PP
   - Existing customer (12 machines!)
   - Full capability
   - Supplies Sonalika

2. Arham Techplast - ABS, ABS FR, ASA, HDPE
   - Multi-material processor

3. Smartline - ABS, ABS FR, ASA
   - Technical plastics

4. Megafibre - ABS, ABS FR, ASA, HDPE, PP
   - Full range capability
   - Industrial applications

5. Pheonix - ABS, ABS FR, PC
   - Mixed industrial

6. Roots - ABS, ASA
   - Industrial products

HDPE SPECIALISTS:
7. ALP - HDPE
   - Heavy duty products
   - Large format potential

8. Dhaval Corporation - HDPE
   - Industrial HDPE
   - Cross-ref: PlastIndia

9. Suraj India - ABS, HDPE
   - Diverse products

10. Polymizer - ABS, HDPE
    - Technical plastics

TPE PROCESSORS (Car Mats):
11. Hyco - ABS, TPE
    - Car mats potential

12. Premier - ABS, TPE
    - Car mats + industrial
    - Cross-ref: PlastIndia, Car Mats

13. Automat - ABS, HDPE, TPE
    - Car mats specialist
    - Cross-ref: Car Mats Study

OTHER INDUSTRIAL:
14. Euro Industries - ASA
    - Outdoor industrial

15. Ess Ess - ABS/PMMA
    - High gloss products

16. Lakshmi Card Cops - ABS
    - Specialty applications

17. RV Chumble - ABS, ABS FR
    - Industrial products

18. Autoconnect - ABS, ASA
    - Automotive industrial""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Diamond Mine Industrial",
        summary="Industrial: Alphafoam (12 machines!), Arham, Megafibre multi-material; TPE: Hyco, Premier, Automat",
        metadata={
            "topic": "industrial_prospects",
            "segment": "Industrial",
            "lead_count": 18
        }
    ))

    # 6. Material-Based Sales Strategy
    items.append(KnowledgeItem(
        text="""Diamond Mine - Material-Based Sales Strategy

ABS PROCESSORS (45 companies) - Largest Segment:
- Machine: PF1-C or PF1-X series
- Applications: Automotive, consumer, industrial
- Temperature: 140-180°C forming
- Key Pitch: Versatility, surface quality

ABS FR PROCESSORS (22 companies):
- Machine: PF1-X with precise temp control
- Applications: eBus interiors, public transport
- Standards: UL94 V-0 certification
- Key Pitch: FR compliance, safety critical

ASA PROCESSORS (13 companies):
- Machine: PF1 series
- Applications: Outdoor, automotive exterior
- Key Pitch: UV resistance, color stability

HDPE PROCESSORS (16 companies):
- Machine: PF1-X for thick sheet (up to 15mm)
- Applications: Industrial, tanks, outdoor
- Key Pitch: Chemical resistance, durability

PP PROCESSORS (6 companies):
- Machine: AM or PF1-C series
- Applications: Interior panels, packaging
- Key Pitch: Low cost, lightweight

PS PROCESSORS (19 companies):
- Machine: FCS for packaging, AM for displays
- Applications: Food packaging, displays
- Key Pitch: High volume, low cost

PC PROCESSORS (10 companies):
- Machine: PF1-X or AM-P (pressure forming)
- Applications: Lighting, skylights, enclosures
- Key Pitch: Clarity, impact resistance

TPE PROCESSORS (4 companies):
- Machine: ATF or PF1-C for car mats
- Applications: Car mats, soft-touch parts
- Key Pitch: Flexibility, durability

CROSS-SELLING OPPORTUNITIES:
- ABS customers → Upgrade to ABS FR
- PC customers → Add ABS/PMMA for gloss
- HDPE customers → Consider ASA for outdoor
- PS packaging → Upgrade to PET (trading)""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Diamond Mine Strategy",
        summary="Sales by material: ABS (45), PS (19), HDPE (16); cross-sell FR/ASA upgrades; machine match",
        metadata={
            "topic": "material_strategy",
            "materials": ["ABS", "PS", "HDPE", "PC", "TPE", "PP", "ASA"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Diamond Mine Sales Leads Ingestion")
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
