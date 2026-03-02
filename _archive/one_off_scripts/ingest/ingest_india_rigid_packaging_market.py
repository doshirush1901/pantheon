#!/usr/bin/env python3
"""
Ingest India Rigid Packaging Market Opportunity

Market intelligence for PET thermoforming in India.
Directly relevant for AM-V, AM-P, and FCS machine sales.

Key data:
- Market: $1.07B (2021) → $1.78B (2028), 7-8% CAGR
- Segments: Food (largest), Pharma (blisters), Electronics (ESD trays)
- Key players and target customers identified
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Rigid Packaging Market Opportunity India.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the India rigid packaging market report."""
    items = []

    # 1. Market Overview & Size
    items.append(KnowledgeItem(
        text="""India PET Thermoforming Market Overview

MARKET SIZE:
- 2021: USD 1.07 billion
- 2028 (projected): USD 1.78 billion
- Growth: 7-8% CAGR
- Outpacing global averages

MATERIAL LEADERSHIP:
- PET is the leading material for thermoformed packaging in India
- Largest revenue-generating segment as of 2021
- Preferred for clarity, food-safe, recyclability

GROWTH DRIVERS:
1. Rising packaged food consumption
2. Pharmaceutical production expansion
3. Electronics manufacturing boom (Make in India)
4. Urbanization and busy lifestyles
5. Ready-to-eat and convenience foods
6. Healthcare/blister pack demand
7. Post-COVID hygiene awareness
8. Tamper-proof packaging requirements

TRENDS:
- Sustainability initiatives (rPET adoption)
- FSSAI now allowing recycled PET in food packaging
- PVC-to-PET shift in pharma blisters
- Technology improvements in forming
- Mono-material designs for recyclability
- Thinner PET with same strength (50% reduction possible)

MACHINECRAFT OPPORTUNITY:
- AM-V, AM-P, FCS machines serve this market
- Growing demand = growing machine sales
- Key segments: food trays, blisters, ESD trays
- Both domestic and export-focused customers""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="India Thermoforming Market",
        summary="India PET thermoforming: $1.07B→$1.78B (2021-28), 7-8% CAGR, PET leads",
        metadata={
            "topic": "market_size",
            "market_2021_usd": 1070000000,
            "market_2028_usd": 1780000000,
            "cagr_percent": "7-8",
            "region": "India"
        }
    ))

    # 2. Key Players - Target Customers
    items.append(KnowledgeItem(
        text="""India PET Thermoforming Key Players - Potential Machinecraft Customers

MAJOR INDIAN THERMOFORMERS:

1. ORACLE GROUP (Oracle Polyplast):
   - Founded: 2000
   - Positioning: Leading one-stop food packaging provider
   - Strength: 300+ channel partners nationwide
   - Products: PET containers, trays for food service & FMCG
   - Markets: India + exports (USA, UK, Middle East)
   - POTENTIAL: Large buyer, may need multiple FCS lines

2. AVI GLOBAL PLAST:
   - Type: PET rigid packaging AND film producer
   - Segments: 10+ (food, medical devices, custom sheets)
   - Role: Backbone supplier of PET material to other thermoformers
   - Customers: Packaging converters, consumer goods companies
   - POTENTIAL: Equipment upgrades, may recommend Machinecraft to customers

3. JOLLY PLASTICS / J.V. PACKS:
   - Reputation: Innovation and service
   - Products: Consumer blisters to industrial trays
   - Strength: Custom design, quick turnaround
   - POTENTIAL: Growing company, may need AM-P or FCS

4. THERM O PACK (Thermopack):
   - Specialty: High-end and technical thermoformed solutions
   - Products: ESD-safe trays, vacuum formed handling trays, automotive trays
   - Markets: Electronics OEMs, automotive suppliers
   - POTENTIAL: Premium customer for specialized equipment

5. USK BALAJI PLAST:
   - Focus: Medical and pharmaceutical packaging
   - Products: Medical device trays, surgical kit trays, pharma blisters
   - Compliance: Healthcare standards, cleanroom production
   - Customers: Pharma companies, hospitals, medtech
   - POTENTIAL: May need precision equipment

GLOBAL PLAYERS IN INDIA:
- Amcor (acquired Bemis): Blister packaging materials
- Huhtamaki: PET packaging for food/consumer goods
- Berry Global: Via acquisitions
- Ecobliss India: Dutch-Indian JV, cold-seal blister packs

OTHER DOMESTIC FIRMS:
- Hello Polymer
- Shri Sai Thermopack
- Protech Industries
- Regional players serving local markets

INDUSTRY DYNAMICS:
- Active capacity expansion
- Investment in new thermoforming lines
- Consolidation and acquisitions ongoing
- Partnerships to broaden customer base
- Innovation in recyclable materials""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="India Thermoforming Companies",
        summary="Key targets: Oracle Group, AVI Global, Therm O Pack, USK Balaji - all potential customers",
        metadata={
            "topic": "key_players",
            "companies": ["Oracle Group", "AVI Global Plast", "Jolly Plastics", "Therm O Pack", "USK Balaji Plast"],
            "global_players": ["Amcor", "Huhtamaki", "Berry Global"]
        }
    ))

    # 3. Food Packaging Segment
    items.append(KnowledgeItem(
        text="""India Food Packaging - Largest PET Thermoforming Segment

MARKET POSITION:
- Food & beverage is LARGEST consumer of thermoformed products
- Significant portion of India's thermoform packaging for food items

PRODUCT CATEGORIES:
- Clear trays and containers
- Bakery goods packaging
- Confectionery trays
- Frozen meal containers
- Salad boxes
- Pre-cut fruit clamshells
- Multi-compartment snack trays
- Hinged-lid lunch boxes
- Traditional sweets packaging
- Dessert trays
- Chocolate blisters

WHY PET FOR FOOD:
- Lightweight
- Durable
- Food-safe (non-toxic)
- Transparent (consumer can see product)
- Rigid (protects delicate items)
- Recyclable (increasingly important)
- Can be heat-sealed with lidding film

REGULATORY UPDATE (Important!):
- FSSAI historically prohibited recycled plastics in food contact
- 2022: FSSAI proposed amendments allowing food-grade rPET
- Condition: Must meet stringent safety and quality criteria
- Impact: Spurring interest in rPET thermoformed containers

CONSUMER TRENDS:
- COVID increased hygiene awareness
- Sealed thermoformed containers preferred
- Ready-to-eat and takeaway growth
- Convenience packaging demand
- Organized retail expansion
- E-commerce grocery boom
- Attractive packaging for retail

SUSTAINABILITY PUSH:
- Global QSR chains demand international standards
- Mono-material PET designs preferred
- Thinner PET (up to 50% reduction achieved)
- rPET percentage in trays appealing to eco-brands

MACHINECRAFT MACHINE FIT:
- FCS series: High-volume food trays, containers
- AM-P: Food trays with detail
- AM-V: Basic food trays (budget)
- All machines handle PET well""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="India Food Packaging",
        summary="Food packaging: largest segment, PET preferred, rPET now allowed, FCS/AM machines ideal",
        metadata={
            "topic": "food_packaging",
            "segment_rank": 1,
            "materials": ["PET", "rPET"],
            "machines": ["FCS", "AM-P", "AM-V"]
        }
    ))

    # 4. Pharmaceutical Packaging Segment
    items.append(KnowledgeItem(
        text="""India Pharmaceutical Packaging - Major PET Thermoforming Application

MARKET SIGNIFICANCE:
- India is leading generic drug producer and exporter
- Enormous volumes of tablets/capsules need blister packaging
- Blister packaging = 35-40% of ALL thermoform packaging by volume

TRADITIONAL VS EMERGING:
Traditional: PVC thermoformed cavity + aluminum foil seal
Emerging: PET-based blister films (shift happening)

WHY PET SHIFT IN PHARMA:
1. Recyclability (PVC recycling difficult)
2. EU regulations considering PVC restrictions
3. Environmental concerns (no chlorine)
4. Superior clarity
5. Lighter weight (Bayer achieved 18% lighter)
6. Lower CO₂ emissions (Bayer achieved 38% reduction)
7. Indian pharma exports to EU/US need compliance

CASE STUDY - BAYER:
- Launched fully PET blister pack (eliminating PVC)
- 18% lighter weight
- 38% lower CO₂ emissions
- Industry benchmark for sustainability

MEDICAL DEVICE TRAYS:
- Custom thermoformed trays for:
  * Syringes
  * Catheters
  * Implants
  * Diagnostic kits
  * Surgical instruments
- Requirements:
  * Cleanroom production
  * Sterilizable
  * Custom cavities
  * Sterile barrier system
  * ISO 11607 compliance

REGULATORY REQUIREMENTS:
- USP (United States Pharmacopeia) compliance
- ISO 11607 for sterile device packaging
- Pharmaceutical grade materials
- Stability testing for material changes
- Drug Master File updates (for FDA if exporting)

KEY PHARMA CUSTOMERS IN INDIA:
- Sun Pharma
- Dr. Reddy's
- Cipla
- Lupin
- Many piloting PVC-free blister packs

MACHINECRAFT MACHINE FIT:
- FCS series: High-volume blister production
- AM-P: Precision medical trays (with pressure forming)
- Sheet thickness typically 0.3-0.8mm for blisters""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="India Pharma Packaging",
        summary="Pharma blisters: 35-40% of thermoforming, PVC→PET shift, FCS for high-volume blisters",
        metadata={
            "topic": "pharmaceutical_packaging",
            "volume_share_percent": "35-40",
            "trend": "PVC_to_PET",
            "machines": ["FCS", "AM-P"]
        }
    ))

    # 5. Electronics/ESD Packaging Segment
    items.append(KnowledgeItem(
        text="""India Electronics Packaging - Fast-Growing PET Thermoforming Segment

MARKET STATUS:
- Fast-emerging segment
- Rapidly expanding due to Make in India
- Double-digit growth expected

ESD (ELECTROSTATIC DISCHARGE) TRAYS:
- Material: PET with anti-static/conductive additives
- Appearance: Typically black plastic
- Function: Dissipate static charge
- Protects: Microchips, circuit boards, semiconductors

TYPICAL PRODUCTS:
- ESD-safe component trays
- PCB handling trays
- Semiconductor carriers
- Camera module holders
- SIM card kit trays
- Retail phone box inserts
- Automotive electronics trays

GROWTH DRIVERS:
1. Make in India initiative
2. Production-Linked Incentive (PLI) schemes
3. Major electronics manufacturers setting up in India
4. Smartphone manufacturing boom
5. Automotive electronics growth
6. Defense/aerospace localization

KEY ESD TRAY MANUFACTURERS IN INDIA:
- Therm O Pack: 20+ years in ESD packaging
- Vibest International: ESD trays specialist
- Both export to global clients

NOTABLE CUSTOMERS:
- Foxconn (Apple manufacturer)
- Flex
- Samsung India operations
- Mobile phone makers
- EMS (Electronics Manufacturing Services) companies

COMPLIANCE REQUIREMENTS:
- ANSI/ESD standards
- Customer audits
- International ESD norms
- Often reusable trays (cost + sustainability)

INNOVATION:
- Conductive recycled PET exploration
- Robot-friendly tray designs
- Automation-compatible features
- High-speed manufacturing alignment

MACHINECRAFT MACHINE FIT:
- AM-P: ESD trays with custom cavities (pressure for detail)
- FCS: High-volume simple ESD trays
- PF1: Heavy-gauge electronics handling trays

Note: ESD trays often need custom cavities for each component.
This means frequent new tooling and machine flexibility matters.""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="India Electronics Packaging",
        summary="Electronics ESD trays: double-digit growth, Make in India driver, AM-P/FCS fit",
        metadata={
            "topic": "electronics_packaging",
            "growth": "double_digit",
            "drivers": ["Make in India", "PLI schemes", "smartphone boom"],
            "machines": ["AM-P", "FCS", "PF1"]
        }
    ))

    # 6. Machine Selection by Segment
    items.append(KnowledgeItem(
        text="""Machinecraft Machine Selection for India Rigid Packaging Market

SEGMENT → MACHINE MAPPING:

1. FOOD PACKAGING (Largest Segment):
   
   High Volume Production (>500k parts/month):
   - FCS 6070-4S: Best choice
   - 25-30 cycles/min
   - Roll-fed continuous
   - Inline stacking
   - ₹1.75 Cr investment
   
   Medium Volume / Startup:
   - AM-P-5060: Good balance
   - Pressure forming for detail
   - ₹35 Lakhs
   
   Budget / Basic Products:
   - AM-V-5060: Entry point
   - Vacuum only
   - ₹7.5 Lakhs
   - Simple trays, no fine detail

2. PHARMACEUTICAL BLISTERS:

   High Volume Blisters:
   - FCS series: Primary choice
   - Thin gauge (0.3-0.8mm)
   - High speed critical
   - Inline cutting essential
   
   Medical Device Trays:
   - AM-P: Pressure forming for precision
   - Custom cavities
   - May need cleanroom specs

3. ELECTRONICS ESD TRAYS:

   Component Trays (moderate volume):
   - AM-P-5060: Good fit
   - Pressure forming for custom cavities
   - ESD material handling
   
   High Volume Simple Trays:
   - FCS: If volume justifies
   
   Heavy-Gauge Handling Trays:
   - PF1: Cut-sheet, thicker materials

PRICING REFERENCE (India Market):
| Machine | Price | Best For |
|---------|-------|----------|
| AM-V-5060 | ₹7.5L | Basic food trays |
| AM-P-5060 | ₹35L | Food/pharma with detail |
| AM-P-6050 DP | ₹62L | PC/PP deep draw |
| FCS 6070-4S | ₹1.75Cr | High-volume packaging |

SALES APPROACH:
1. Understand customer's product mix
2. Ask about volume requirements
3. Check material types (PET vs PC vs PP)
4. Assess detail/precision needs
5. Recommend appropriate machine tier
6. Offer upgrade path story""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Machine Selection India",
        summary="Food→FCS/AM; Pharma→FCS; Electronics→AM-P; budget→AM-V; see pricing tiers",
        metadata={
            "topic": "machine_selection",
            "segments": ["food", "pharma", "electronics"],
            "machines": ["FCS", "AM-P", "AM-V", "PF1"]
        }
    ))

    # 7. Sustainability Trends
    items.append(KnowledgeItem(
        text="""India Thermoforming Sustainability Trends - Sales Opportunity

REGULATORY CHANGES:

FSSAI rPET Approval (2022):
- Previously: Recycled plastics prohibited in food contact
- Now: Food-grade rPET allowed with stringent criteria
- Impact: Opens market for rPET thermoformed containers
- Customer demand: Eco-conscious brands want rPET content

PVC Phase-Out in Pharma:
- EU considering restrictions on PVC in pharma packaging
- Indian pharma exporters must comply
- Driving shift to PET-based blister films
- Opportunity: New machinery for PET blister capability

SUSTAINABILITY DRIVERS:
1. Global QSR chains demanding international standards
2. Export markets requiring compliance
3. Consumer preference for recyclable packaging
4. Corporate sustainability commitments
5. EPR (Extended Producer Responsibility) regulations

INNOVATION IN THERMOFORMING:
- Mono-material PET designs (easier recycling)
- Thinner PET with same strength (50% reduction achieved)
- rPET percentage in trays
- Conductive recycled PET for ESD trays
- Reduced material usage = lower cost + sustainability

SALES TALKING POINTS:

For Food Customers:
"Our FCS machines can process rPET just as efficiently as virgin PET.
As FSSAI now allows rPET in food packaging, you can differentiate
your brand with sustainable packaging without changing equipment."

For Pharma Customers:
"With EU moving away from PVC, PET blisters are the future.
Machinecraft FCS handles PET blister materials efficiently.
Bayer achieved 18% lighter, 38% less CO₂ with PET - you can too."

For Electronics Customers:
"Your global customers are asking about recycled content.
We're seeing conductive rPET development for ESD trays.
Machinecraft machines are ready for this transition."

MACHINECRAFT ADVANTAGE:
- All machines handle PET and rPET
- FCS optimized for thin-gauge (where rPET common)
- No equipment change needed for sustainability shift
- Future-proof investment""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Sustainability Trends India",
        summary="rPET now allowed (FSSAI), PVC phase-out in pharma, Machinecraft machines ready",
        metadata={
            "topic": "sustainability",
            "regulations": ["FSSAI rPET", "EU PVC restrictions"],
            "opportunities": ["rPET packaging", "PET blisters"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("India Rigid Packaging Market Opportunity Ingestion")
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
