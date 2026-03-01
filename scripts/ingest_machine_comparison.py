#!/usr/bin/env python3
"""
Ingest Vacuum Forming Machine Comparison knowledge.

Source: data/imports/Vacuum Forming Machine Comparison[34383].docx.pdf
This document explains why Machinecraft's closed chamber zero-sag design is 
superior to traditional North American rotary/open style machines.

Critical sales knowledge for positioning against North American competitors.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "skills" / "brain"))

from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Vacuum Forming Machine Comparison[34383].docx.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Extract structured knowledge from machine comparison document."""
    items = []
    
    # Overview - the core problem with North American machines
    items.append(KnowledgeItem(
        text="""Vacuum Forming Machine Technology Comparison Overview:

THE PROBLEM WITH NORTH AMERICAN MACHINES:
Companies throughout North America are still using OLD thermoforming technologies
that result in inefficiency, material waste, and quality issues.

Based on 50 years of hands-on experience, this comparison demonstrates why 
Machinecraft's CLOSED CHAMBER ZERO-SAG technology produces superior results.

COMPARISON BASIS:
- Material: 0.125" (3.2mm) ABS sheet
- Sheet size: 72" x 48" (1830mm x 1220mm)
- Mold: Well-rounded mold, 20" (500mm) deep

CORE TECHNOLOGY DIFFERENCE:

NORTH AMERICAN (Old Technology):
- OPEN CHAMBER design
- Sheet SAGS during heating (no support)
- Bottom heater far from sheet (to avoid sagging contact)
- Center of mold contacts sagging sheet first
- Material pushed upward creating THIN WALLS
- Manual operations, operator-dependent

MACHINECRAFT (Advanced Technology):
- CLOSED CHAMBER design
- Sheet SUPPORTED FLAT with compressed air during heating
- Bottom heater close to sheet (efficient heating)
- PRE-BLOW BUBBLE formed before mold enters
- EVEN WALL THICKNESS throughout part
- Fully automatic operation""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machine Comparison",
        summary="North American open-chamber vs Machinecraft closed-chamber: sagging sheet vs supported flat = thin walls vs even thickness",
        metadata={"topic": "technology_comparison", "market": "north_america"}
    ))
    
    # Technical comparison - feature by feature
    items.append(KnowledgeItem(
        text="""Machinecraft vs North American Machines - Feature Comparison:

1. MOLD REQUIREMENTS:
   North American: Requires vacuum box, hoses, connections - EXTRA labor and materials
   Machinecraft: Mold simply mounted on plate - NO vacuum box required

2. MOLD MOUNTING:
   North American: Manually secured to platen - TIME CONSUMING
   Machinecraft: Locked in place with quick-locking feature - FAST

3. VACUUM BOX:
   North American: Chances of vacuum leaks if not made right
   Machinecraft: NO vacuum box = NO LEAKS possible

4. CLAMP FRAME:
   North American: Manually adjusted, requires sectional clamps, many hoses and 
   cylinders - MAY REQUIRE TWO OPERATORS
   Machinecraft: Select size on computer screen - frame AND mold opening SET AUTOMATICALLY

5. HEATERS:
   North American: Select zones, mostly CERAMIC heating elements
   Machinecraft: Select zones, modern HALOGEN heating elements (faster, more efficient)

6. SHEET LOADING:
   North American: Manually loaded - MAY REQUIRE TWO OPERATORS for large sheets
   Machinecraft: FULLY AUTOMATIC loading - NO OPERATORS required

7. HEATER POSITION:
   North American: Bottom heater far from sheet (because sheet sags) - NOT EFFECTIVE
   Machinecraft: Bottom heater CLOSE to sheet (sheet supported flat) - EFFICIENT

8. PART REMOVAL:
   North American: Manually removed by 1-2 operators depending on size
   Machinecraft: Auto loader picks formed part and delivers to unload area""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Feature Comparison",
        summary="8 key feature differences: Machinecraft eliminates vacuum box, manual adjustment, and multi-operator requirements",
        metadata={"topic": "feature_comparison", "advantages_count": 8}
    ))
    
    # The critical heating and forming difference
    items.append(KnowledgeItem(
        text="""THE CRITICAL DIFFERENCE: Heating and Forming Process

WHY NORTH AMERICAN MACHINES PRODUCE INFERIOR PARTS:

HEATING PHASE - North American (Open Chamber):
- Sheet sags during heating due to gravity
- Creates THIN-OUT in CENTER of sheet
- Results in UNEVEN heating
- Difficult to control desired sheet temperature
- Bottom heater must be far away to avoid sheet touching it

HEATING PHASE - Machinecraft (Closed Chamber):
- Sheet FULLY SUPPORTED FLAT with compressed air
- Provides CONTROLLED, UNIFORM sheet temperature
- Bottom heater can be positioned CLOSE to sheet
- More efficient, more consistent heating

FORMING PHASE - North American:
- Center of mold contacts the SAGGING sheet first
- Sheet material PUSHED UPWARD by mold
- Creates THIN OUT in VERTICAL WALLS
- Uneven wall thickness = weaker parts or must use thicker material

FORMING PHASE - Machinecraft (PRE-BLOW BUBBLE):
1. Controlled heated sheet is PRE-BLOWN into a programmed BUBBLE
2. Bubble rises BEFORE mold enters
3. Mold enters the pre-formed bubble
4. Material already pre-stretched uniformly
5. Results in EVEN WALL THICKNESS throughout part

THIS IS THE FUNDAMENTAL ADVANTAGE:
Pre-blow bubble technology ensures material is evenly distributed BEFORE 
mold contact, eliminating the thin spots caused by mold pushing into sagging sheet.""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="Heating/Forming Difference",
        summary="Critical difference: sagging sheet creates thin walls vs pre-blow bubble creates even wall thickness",
        metadata={"topic": "process_comparison", "key_feature": "preblow_bubble"}
    ))
    
    # Ejection and temperature control
    items.append(KnowledgeItem(
        text="""Part Ejection - Temperature Control Advantage:

NORTH AMERICAN (Time-Based Ejection):
- Part ejects at end of cooling cycle
- Based on TIME only
- If not cooled right → DISTORTION
- Operator must guess cooling time
- Risk of warped parts or wasted time

MACHINECRAFT (Temperature-Based Ejection):
- Part ejects upon reaching SET TEMPERATURE
- Works regardless of material THICKNESS VARIATION
- NO DISTORTION because guaranteed cooled properly
- More consistent cycle times
- No guessing required

WHY TEMPERATURE-BASED IS SUPERIOR:
- Material thickness varies slightly sheet to sheet
- Environmental temperature affects cooling
- Time-based ejection doesn't account for these variables
- Temperature-based ensures part is actually ready
- Eliminates reject parts from premature ejection""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="Ejection System",
        summary="North American: time-based ejection (may distort) vs Machinecraft: temperature-based (no distortion)",
        metadata={"topic": "ejection_comparison"}
    ))
    
    # Setup time comparison
    items.append(KnowledgeItem(
        text="""Setup Time Comparison - DRAMATIC DIFFERENCE:

NORTH AMERICAN MACHINE (Previously Run Job):
- Remove mold
- Set up clamp frame for new mold (manual adjustment)
- Secure mold to platen (manual)
- Connect vacuum hoses
- Adjust frame with many hoses and cylinders
- Average setup time: 1 to 1.5 HOURS
- May require TWO OPERATORS

MACHINECRAFT MACHINE (Previously Run Job):
- Remove mold
- Secure new mold (quick-lock)
- RECALL previously run program from computer
- Machine SETS ITSELF UP automatically:
  * Clamp frame adjusts
  * Mold opening adjusts
  * Oven parameters set
- Change over time: 15 MINUTES
- ONE OPERATOR sufficient

SETUP TIME SAVINGS:
- North American: 1.5 hours = $180 at $120/hour
- Machinecraft: 0.25 hours = $30 at $120/hour
- SAVINGS PER SETUP: $150

For shops doing multiple changeovers per day, this adds up to THOUSANDS in savings.""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Setup Time",
        summary="Setup time: North American 1-1.5 hours vs Machinecraft 15 minutes - $150 savings per changeover",
        metadata={"topic": "setup_time", "na_time": "1.5_hours", "mc_time": "15_min", "savings": "$150"}
    ))
    
    # Cycle time comparison
    items.append(KnowledgeItem(
        text="""Cycle Time Comparison - DOUBLE THE OUTPUT:

NORTH AMERICAN MACHINE:
- Cycle time: 4 to 5 MINUTES per cycle
- Output: 12 to 15 parts per hour
- Totally OPERATOR DEPENDENT
- May require 2 operators to load/unload
- Machine warm-up time: 20-30 minutes

MACHINECRAFT MACHINE:
- Cycle time: 2 to 2.5 MINUTES per cycle
- Output: 24 to 30 parts per hour (NORMAL operation)
- Under optimal conditions: UP TO 40 CYCLES PER HOUR
- FULLY AUTOMATIC - no operators for loading/unloading
- Machine warm-up time: 10 minutes

PRODUCTIVITY COMPARISON:
- North American: 15 parts/hour × 8 hours = 120 parts/day
- Machinecraft: 30 parts/hour × 8 hours = 240 parts/day
- DOUBLE THE OUTPUT with same (or less) labor

LABOR COMPARISON:
- North American: 1-2 operators required
- Machinecraft: 0 operators during cycle (automated)
- One operator can supervise multiple Machinecraft machines""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Cycle Time",
        summary="Cycle time: NA 4-5 min (15/hr) vs Machinecraft 2-2.5 min (30/hr) - DOUBLE output with less labor",
        metadata={"topic": "cycle_time", "na_output": "15/hr", "mc_output": "30/hr"}
    ))
    
    # Material savings - critical cost advantage
    items.append(KnowledgeItem(
        text="""Material Savings - The HIDDEN Cost Advantage:

THE MATERIAL THICKNESS DIFFERENCE:

NORTH AMERICAN MACHINE:
- Due to sheet thin-out and stretching during forming
- MUST use 0.125" (3.2mm) ABS to produce acceptable parts
- Thinner material would result in weak spots

MACHINECRAFT MACHINE:
- Due to pre-blow bubble and accurately controlled heating
- Can use 0.115" (2.9mm) ABS to produce SAME QUALITY parts
- 8% THINNER material achieves same wall thickness

MATERIAL REQUIREMENT FOR 1200 PARTS:
- North American: 20,740 lbs material required
- Machinecraft: 19,080 lbs material required
- SAVINGS: 1,660 lbs per 1200 parts (8% reduction)

COST SAVINGS AT $2.80/lb:
- North American: $58,072 material cost ($48.40/sheet)
- Machinecraft: $53,424 material cost ($44.52/sheet)
- SAVINGS: $4,648 per 1200 parts

WHY THIS MATTERS:
Material is often the LARGEST cost in thermoforming.
8% material savings goes directly to bottom line profit.
Over a year of production, this represents MASSIVE savings.""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Material Savings",
        summary="Material savings: Can use 8% thinner sheet (0.115\" vs 0.125\") = $4,648 savings per 1200 parts",
        metadata={"topic": "material_savings", "thickness_reduction": "8%", "savings_1200_parts": "$4648"}
    ))
    
    # Total cost comparison
    items.append(KnowledgeItem(
        text="""Total Manufacturing Cost Comparison - ROI Analysis:

EQUIPMENT COST:
- North American machine: $255,000 US
- Machinecraft machine: $260,000 US
- Difference: Only $5,000 more for Machinecraft

PER-PART THERMOFORMING COST (at $120/hour):
- North American: $120/hour ÷ 15 cycles = $8.00 per part
- Machinecraft: $120/hour ÷ 30 cycles = $4.00 per part
- SAVINGS: $4.00 per part (50% reduction)

TOTAL PIECE PRICE (Setup + Cycle + Material):
- North American: $56.55 per piece
- Machinecraft: $48.52 per piece
- SAVINGS: $8.03 per piece (14% reduction)

TOTAL MANUFACTURING COST FOR 1200 CYCLES:
- North American: $67,860.00
- Machinecraft: $58,224.00
- SAVINGS: $9,636.00

ROI CALCULATION:
- Extra machine cost: $5,000
- Savings per 1200 parts: $9,636
- PAYBACK: Less than 1200 parts (typically 1-2 months)
- ANNUAL SAVINGS: $50,000+ depending on volume

CONCLUSION:
For only $5,000 more in equipment cost, Machinecraft machines generate 
$9,636 ADDITIONAL PROFIT per 1200 cycles through:
- Faster setup times
- Faster cycle times
- Material savings from thinner sheets
- Reduced labor requirements""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Cost Analysis",
        summary="ROI: $5K more machine cost generates $9,636 additional profit per 1200 parts - payback in 1-2 months",
        metadata={
            "topic": "cost_comparison",
            "na_piece_price": "$56.55",
            "mc_piece_price": "$48.52",
            "savings_per_1200": "$9636"
        }
    ))
    
    # Sales talking points summary
    items.append(KnowledgeItem(
        text="""Sales Talking Points - Machinecraft vs North American Competitors:

KEY DIFFERENTIATORS TO EMPHASIZE:

1. CLOSED CHAMBER vs OPEN CHAMBER:
   "Our closed chamber design keeps the sheet flat during heating, eliminating 
   the thin spots that plague open-chamber machines."

2. PRE-BLOW BUBBLE TECHNOLOGY:
   "The pre-blow bubble pre-stretches the material uniformly BEFORE mold contact,
   resulting in consistent wall thickness throughout the part."

3. MATERIAL SAVINGS (8%):
   "You can use thinner material and still achieve the same wall thickness,
   saving 8% on material costs - your biggest expense."

4. SETUP TIME (15 min vs 1.5 hours):
   "Recipe recall means setup takes 15 minutes, not 1.5 hours. That's $150 
   savings every changeover."

5. CYCLE TIME (2x FASTER):
   "We produce 30 parts/hour vs 15 parts/hour - double your output with 
   the same floor space."

6. AUTOMATION:
   "Fully automatic loading and unloading means no operators required during
   the cycle. One person can supervise multiple machines."

7. NO VACUUM BOX:
   "Our design eliminates the vacuum box entirely - no extra fabrication,
   no leak risks, simpler mold design."

8. TEMPERATURE-BASED EJECTION:
   "Parts eject when they reach the right temperature, not on a timer -
   no distortion, no guesswork."

COMPETITOR RESPONSE:
When competing against Brown, Belovac, or other North American brands,
emphasize the CLOSED CHAMBER and PRE-BLOW BUBBLE advantages - these are
the technical features they cannot match.""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Sales Talking Points",
        summary="8 key sales points: closed chamber, pre-blow, material savings, setup time, cycle time, automation, no vacuum box, temp ejection",
        metadata={"topic": "sales_arguments", "competitors": ["Brown", "Belovac", "North_American"]}
    ))
    
    return items


def main():
    print("=" * 70)
    print("Ingesting Machine Comparison - Closed Chamber vs Open Chamber")
    print("=" * 70)
    print(f"\nSource: {SOURCE_FILE}")
    print("Critical competitive analysis for North American market.\n")
    
    items = create_knowledge_items()
    print(f"Extracted {len(items)} knowledge items:\n")
    
    for i, item in enumerate(items, 1):
        print(f"  {i:2}. [{item.knowledge_type:12}] {item.entity}: {item.summary[:50]}...")
    
    print("\n" + "-" * 70)
    print("Starting ingestion to all storage systems...")
    
    ingestor = KnowledgeIngestor(verbose=True)
    result = ingestor.ingest_batch(items)
    
    print("\n" + "=" * 70)
    print(f"RESULT: {result}")
    print("=" * 70)
    
    if result.success:
        print("\n✓ Competitive knowledge ingested successfully!")
        print(f"  - Items ingested: {result.items_ingested}")
        print(f"  - Qdrant main: {result.qdrant_main}")
        print(f"  - Qdrant discovered: {result.qdrant_discovered}")
        print(f"  - Mem0: {result.mem0}")
        print(f"  - JSON backup: {result.json_backup}")
    else:
        print("\n✗ Ingestion failed")
        if result.errors:
            print(f"  Errors: {result.errors}")
    
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
