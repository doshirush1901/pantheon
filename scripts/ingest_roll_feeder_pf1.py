#!/usr/bin/env python3
"""
Ingest Roll Feeder Machinecraft Machine Selections knowledge.

Source: data/imports/Roll Feeder Machinecraft Machine Selections to make Presentation Copy (2).pdf
Contains PF1 Roll Feeder machine technical specifications and configuration options.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "skills" / "brain"))

from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Roll Feeder Machinecraft Machine Selections to make Presentation Copy (2).pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Extract structured knowledge from Roll Feeder PF1 presentation."""
    items = []
    
    # Machine overview - closed chamber
    items.append(KnowledgeItem(
        text="""PF1 Roll Feeder Machine - Closed Chamber Design:

The Machinecraft PF1 Roll Feeder is a single station vacuum forming machine with automatic roll feeding.

KEY FEATURE - Closed Chamber Type:
- The box below the clamped sheet is air-tight sealed
- Allows blowing air to make a bubble BEFORE forming (for positive male tools)
- Allows blowing air to maintain zero-sag (for negative female tools)
- This is an IMPORTANT feature for achieving even part thickness

Benefits of closed chamber design:
- Better material distribution during forming
- More consistent part wall thickness
- Suitable for both positive and negative tooling
- Essential for deep-draw applications""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Roll Feeder",
        summary="PF1 Roll Feeder: closed chamber design for bubble forming and zero-sag, ensures even part thickness",
        metadata={"machine_type": "roll_feeder", "series": "PF1", "feature": "closed_chamber"}
    ))
    
    # Heater types
    items.append(KnowledgeItem(
        text="""PF1 Roll Feeder - Heater Options:

The machine uses Infrared (IR) heating elements for non-contact sheet heating.
Two heater ovens available - above AND below the sheet.
Note: If forming only up to 4mm thick material, top heater only is sufficient.

HEATER TYPE OPTIONS:

1. CERAMIC (Long-wave):
   - Rugged and durable
   - No energy savings
   - Best for: Production environments needing reliability

2. QUARTZ (Medium-wave):
   - Saves up to 30% energy vs ceramic
   - More fragile than ceramic
   - Best for: Balance of efficiency and durability

3. HALOGEN (Short-wave):
   - Saves up to 50% energy vs ceramic
   - Higher connected load requirement
   - Best for: Maximum energy efficiency, fast heating

All heater types feature:
- Zone control capability
- Individual element control
- Touch-screen HMI settings
- Top and bottom oven configuration""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Roll Feeder",
        summary="PF1 heaters: Ceramic (rugged), Quartz (30% energy saving), Halogen (50% energy saving) - zone controlled",
        metadata={
            "machine_type": "roll_feeder",
            "series": "PF1",
            "feature": "heaters",
            "options": ["ceramic", "quartz", "halogen"]
        }
    ))
    
    # Sheet frame types
    items.append(KnowledgeItem(
        text="""PF1 Roll Feeder - Sheet Frame Options:

When product changeover requires different sheet sizes, the clamping frames must be changed.

OPTION 1 - FIXED TYPE FRAMES:
- Steel welded construction
- Clamped using bolts on machine
- Changeover time: ~60 minutes
- Lower initial cost
- Best for: Single product or infrequent changeovers

OPTION 2 - UNIVERSAL FRAMES (Automated):
- CNC machined aluminium construction
- Moved using servo motors
- Settings via touchscreen HMI
- Changeover time: Less than 10 minutes
- Higher initial cost
- Best for: Multiple products, frequent changeovers

Cost-benefit: Universal frames cost more upfront but save significant time on changeovers.
For high-mix production, the 50-minute time savings per changeover adds up quickly.""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Roll Feeder",
        summary="PF1 frames: Fixed (60min change, lower cost) vs Universal servo (10min change, CNC aluminium)",
        metadata={
            "machine_type": "roll_feeder",
            "series": "PF1",
            "feature": "sheet_frames",
            "options": ["fixed", "universal"]
        }
    ))
    
    # Tool clamping system
    items.append(KnowledgeItem(
        text="""PF1 Roll Feeder - Tool Clamping & Centering Options:

During product changeover, tools must be changed on the bottom table.

OPTION 1 - BOLT CLAMPING SYSTEM:
- Operator loads tool via forklift into bottom area
- Manual centering using markings on table
- Bolt 4 sides to secure tool
- Changeover time: ~60 minutes
- Lower cost option

OPTION 2 - PNEUMATIC QUICK CLAMPING:
- Load tool via forklift onto pneumatic circuit
- Automatic locking and centering
- Tool always kept centered automatically
- Changeover time: Less than 20 minutes
- Higher cost but significant time savings

Recommendation: For production with frequent tool changes, pneumatic quick clamping
provides 40-minute savings per changeover.""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Roll Feeder",
        summary="PF1 tool clamping: Bolt system (60min) vs Pneumatic quick (20min) - auto centering available",
        metadata={
            "machine_type": "roll_feeder",
            "series": "PF1",
            "feature": "tool_clamping",
            "options": ["bolt", "pneumatic_quick"]
        }
    ))
    
    # Roll feeder system
    items.append(KnowledgeItem(
        text="""PF1 Roll Feeder - Automatic Sheet Loading System:

The roll feeder provides fully automatic sheet loading from rolls:

FEATURES:
- Handles rolls up to 600 kg capacity
- Integrated lifting device and roll shaft designed for heavy rolls
- Shear cutter cuts each shot before loading
- Servo motor driven spike chain transports cut sheet to forming station
- Automatic positioning in forming area

OPERATION SEQUENCE:
1. Roll material loaded onto roll shaft (up to 600kg)
2. Material fed to shear cutter
3. Sheet cut to required length
4. Spike chain grips and transports sheet
5. Sheet positioned in forming station
6. After forming, spike chain transfers to unloading area

Benefits:
- Continuous production from roll stock
- Reduced material handling labor
- Consistent sheet positioning
- Higher throughput than manual loading""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Roll Feeder",
        summary="PF1 roll feeder: up to 600kg rolls, shear cutter, servo spike chain, automatic sheet transport",
        metadata={
            "machine_type": "roll_feeder",
            "series": "PF1",
            "feature": "roll_feeder",
            "max_roll_weight": "600kg"
        }
    ))
    
    # Table movements
    items.append(KnowledgeItem(
        text="""PF1 Roll Feeder - Table Movement Options:

The machine has 2 tables:
- Lower table: Main vacuum forming tool
- Upper table: Plug assist

TABLE MOVEMENT OPTIONS:

OPTION 1 - PNEUMATIC:
- Economic option
- Standard speed and noise levels
- Adequate for most applications

OPTION 2 - SERVO MOTOR DRIVEN:
- Silent operation
- Faster cycle times
- Soft product release capability
- Can increase product quality in some cases
- Premium option

Quality benefit: Servo-driven tables allow controlled release speed,
reducing part distortion and improving surface quality on sensitive materials.""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Roll Feeder",
        summary="PF1 table movements: Pneumatic (economic) vs Servo (silent, faster, soft release for quality)",
        metadata={
            "machine_type": "roll_feeder",
            "series": "PF1",
            "feature": "table_movements",
            "options": ["pneumatic", "servo"]
        }
    ))
    
    # Vacuum system
    items.append(KnowledgeItem(
        text="""PF1 Roll Feeder - Vacuum System:

VACUUM SYSTEM FEATURES:
- Inbuilt vacuum tank + pump (integrated design)
- Servo motor driven vacuum valve
- Multi-step digital vacuum setting
- Settings controlled via touchscreen HMI

Advantages of servo-driven vacuum valve:
- Precise vacuum control during forming cycle
- Programmable vacuum profiles (multi-step)
- Repeatable vacuum settings for consistent parts
- Recipe storage for different products""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Roll Feeder",
        summary="PF1 vacuum: integrated tank+pump, servo-driven valve, multi-step digital control via HMI",
        metadata={
            "machine_type": "roll_feeder",
            "series": "PF1",
            "feature": "vacuum_system"
        }
    ))
    
    # Control system
    items.append(KnowledgeItem(
        text="""PF1 Roll Feeder - Control System:

CONTROL PANEL COMPONENTS:
- Heater control using SSR (Solid State Relays)
- PLC (Programmable Logic Controller)
- Servo motor drives
- Touchscreen HMI interface

UL-RATED ELECTRICAL CABINET:
- Built with recognized international brands
- Meets UL safety standards
- Suitable for export to North America and Europe

Control features:
- Recipe storage and recall
- Zone-by-zone heater control
- Servo positioning for all automated functions
- Diagnostic and alarm systems""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Roll Feeder",
        summary="PF1 control: PLC + SSR heater control + servo drives, UL-rated cabinet, touchscreen HMI",
        metadata={
            "machine_type": "roll_feeder",
            "series": "PF1",
            "feature": "control_system",
            "certification": "UL"
        }
    ))
    
    # Machine configurations
    items.append(KnowledgeItem(
        text="""PF1 Roll Feeder - Machine Configuration Options:

CONFIG A - STANDARD (Economic):
- Table Movements: Pneumatic
- Sheet Size Setting: Fixed Type frames
- Tool Clamping: Using Bolts
- Best for: Single product, budget-conscious, low changeover frequency

CONFIG B - PRO (Automated):
- Table Movements: Servo Motor Driven
- Sheet Size Setting: Universal frames
- Tool Clamping: Pneumatic Quick
- Best for: Multiple products, high changeover frequency, premium quality requirements

Changeover time comparison:
- Config A: ~120 minutes total (60 min frames + 60 min tool)
- Config B: ~30 minutes total (10 min frames + 20 min tool)

Config B saves ~90 minutes per changeover - critical for high-mix production.""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Roll Feeder",
        summary="PF1 configs: Standard (pneumatic, fixed, bolt) vs Pro (servo, universal, quick clamp) - 90min changeover difference",
        metadata={
            "machine_type": "roll_feeder",
            "series": "PF1",
            "feature": "configurations",
            "configs": ["standard", "pro"]
        }
    ))
    
    # Machine sizes
    items.append(KnowledgeItem(
        text="""PF1 Roll Feeder - Available Machine Sizes:

MAX FORMING AREA OPTIONS:
X-axis (width): 1000 | 1200 | 1500 | 2000 mm
Y-axis (depth): 800 | 1000 | 1200 | 1500 mm

MAX TOOL HEIGHT OPTIONS:
Z-axis: 400 | 500 | 650 mm

STANDARD COMMON SIZE:
1000 x 2000 x 500 mm (X x Y x Z)

Size combinations available:
- Small: 1000 x 800 mm forming, 400mm tool height
- Medium: 1200 x 1000 mm forming, 500mm tool height
- Large: 1500 x 1200 mm forming, 500mm tool height
- XL: 2000 x 1500 mm forming, 650mm tool height

Client selects size based on:
- Largest part to be formed
- Required tool/draw depth
- Production volume requirements""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Roll Feeder",
        summary="PF1 Roll Feeder sizes: 1000-2000mm x 800-1500mm forming area, 400-650mm tool height",
        metadata={
            "machine_type": "roll_feeder",
            "series": "PF1",
            "feature": "sizes",
            "max_x": "2000mm",
            "max_y": "1500mm",
            "max_z": "650mm",
            "standard_size": "1000x2000x500mm"
        }
    ))
    
    return items


def main():
    print("=" * 60)
    print("Ingesting PF1 Roll Feeder Machine Knowledge")
    print("=" * 60)
    print(f"\nSource: {SOURCE_FILE}")
    
    items = create_knowledge_items()
    print(f"Extracted {len(items)} knowledge items\n")
    
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.summary[:60]}...")
    
    print("\n" + "-" * 60)
    print("Starting ingestion...")
    
    ingestor = KnowledgeIngestor(verbose=True)
    result = ingestor.ingest_batch(items)
    
    print("\n" + "=" * 60)
    print(f"RESULT: {result}")
    print("=" * 60)
    
    if result.success:
        print("\n✓ Knowledge ingested successfully!")
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
