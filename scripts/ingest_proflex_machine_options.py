#!/usr/bin/env python3
"""
Ingest Machine Options for Proflex Canada

Shows how Machinecraft presents PF1 machine configuration options to customers.
Example of pricing structure for large format machines with different stroke depths.

Source: Machine Options - for Proflex Canada.xlsx
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

SOURCE_FILE = "Machine Options - for Proflex Canada.xlsx"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from Proflex machine options."""
    items = []

    # 1. Machine Options Overview
    items.append(KnowledgeItem(
        text="""PF1 Machine Options Presentation - Proflex Canada Example

CUSTOMER: Proflex Canada
APPLICATION: Bathtubs / Spas (large format thermoforming)
MARKET: North America (CSA certification required)

OPTIONS PRESENTED:
6 configurations ranging from $350K to $425K USD

BASE MACHINE (Option 0):
- Forming Area: 2000 x 2500 mm
- Stroke: 750 mm
- Price: $350,000 USD

CONFIGURATION OPTIONS:
| Config | Forming Area | Stroke | Footprint | Price |
|--------|-------------|--------|-----------|-------|
| Base | 2000x2500mm | 750mm | 7x10.5x7m | $350K |
| Opt 1 | 2000x2500mm | 1250mm | 7x10.5x8.5m | $365K |
| Opt 2 | 2000x2500mm | 1500mm | 7x10.5x9.2m | $375K |
| Opt 3 | 2500x2500mm | 750mm | 8.25x10.5x7m | $390K |
| Opt 4 | 2500x2500mm | 1250mm | 8.25x10.5x8.5m | $415K |
| Opt 5 | 2500x2500mm | 1500mm | 8.25x10.5x9.2m | $425K |

PRICING INCREMENTS:
- Stroke upgrade 750→1250mm: +$15K
- Stroke upgrade 1250→1500mm: +$10K
- Size upgrade 2000→2500mm width: +$40K

KEY LEARNING:
This is how Machinecraft presents options - giving customer flexibility
to choose based on their application needs and budget.""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Proflex Machine Options Overview",
        summary="Proflex Canada: 6 PF1 configs $350K-$425K, 2000-2500mm, 750-1500mm stroke, CSA certified",
        metadata={
            "topic": "proflex_options_overview",
            "customer": "Proflex Canada",
            "price_range": "$350K-$425K USD"
        }
    ))

    # 2. Standard Features (All Configs)
    items.append(KnowledgeItem(
        text="""PF1 Machine Standard Features - All Configurations Include

MACHINE TYPE:
- Closed Chamber design
- For Preblow Bubble & Sheet Sag control
- Benefit: Sag control blows air from below sheet to maintain constant height
- Allows more uniform heating
- Preblow helps make positive tool parts
- Better border thickness

HEATER SYSTEM:
- IR Halogen Flash Type Heaters (energy efficient)
- Zone Control for precise heating
- Heatronik Type monitoring (detects malfunctioned elements)
- IR Probe for heating cycle monitoring

SHEET HANDLING:
- Universal Frames (Brass & Aluminium)
- Servo Motor Adjusted Automatic sizing
- Min. Forming Area: 1000 x 1500 mm
- Sheet Size Changeover Time: 10 mins
- Automatic Sheet Loading with Servo-driven Loader
- Automatic Part Unloading
- Sheet Load/Unload Time: 3 mins

SERVO DRIVES (All movements):
- Bottom Table: Servo Motor Driven
- Top Table: Servo Motor Driven
- Sheet Clamping: Servo Motor Driven
- Heater Movement: Servo Motor Driven
- Benefits: Acceleration/deceleration profiles, energy efficiency, soft delayed release

TOOL HANDLING:
- Pneumatic Locking with Ball Transfer Units
- Tool Setup Time: 15 mins
- Faster clamping with auto-alignment

COOLING:
- Central Ducted Cooling system
- IR Probe for cooling cycle monitoring
- Faster cooling time

CERTIFICATION:
- CSA certified (for North American market)""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Standard Features",
        summary="PF1 standard: Closed chamber, IR halogen heaters, servo drives, auto load/unload, 10min changeover",
        metadata={
            "topic": "pf1_standard_features",
            "features": ["Closed Chamber", "IR Halogen", "Servo Drive", "Auto Load", "CSA"]
        }
    ))

    # 3. Configuration Details
    items.append(KnowledgeItem(
        text="""PF1 Configuration Specifications - Proflex Options

ELECTRICAL REQUIREMENTS:

2000 x 2500 mm configurations:
- Heater Load: 420 KW
- Servo Load: 62.2 KW
- Max. Electrical Connection: 500 KW

2500 x 2500 mm configurations:
- Heater Load: 480 KW (+60 KW vs smaller)
- Servo Load: 70 KW (+7.8 KW vs smaller)
- Max. Electrical Connection: 550 KW (+50 KW vs smaller)

FOOTPRINT CHANGES BY STROKE:

2000 x 2500 mm forming area:
- 750mm stroke: 7 x 10.5 x 7 m (D x W x H)
- 1250mm stroke: 7 x 10.5 x 8.5 m (+1.5m height)
- 1500mm stroke: 7 x 10.5 x 9.2 m (+0.7m height)

2500 x 2500 mm forming area:
- 750mm stroke: 8.25 x 10.5 x 7 m (+1.25m depth)
- 1250mm stroke: 8.25 x 10.5 x 8.5 m
- 1500mm stroke: 8.25 x 10.5 x 9.2 m

STROKE SELECTION GUIDE:
- 750mm: Standard bathtubs, shallow spas
- 1250mm: Deep bathtubs, standard spas
- 1500mm: Very deep spas, specialty applications

SIZE SELECTION GUIDE:
- 2000 x 2500mm: Standard bathtub sizes
- 2500 x 2500mm: Large format spas, oversized tubs""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Configuration Specs",
        summary="PF1 configs: 2000/2500mm width, 750/1250/1500mm stroke, 420-480KW heater, 500-550KW connection",
        metadata={
            "topic": "pf1_configuration_specs",
            "forming_areas": ["2000x2500mm", "2500x2500mm"],
            "strokes": ["750mm", "1250mm", "1500mm"]
        }
    ))

    # 4. Pricing Strategy & Sales Approach
    items.append(KnowledgeItem(
        text="""PF1 Pricing Strategy - Options Presentation Method

PROFLEX CANADA PRICING (USD):
| Configuration | Price | Delta |
|--------------|-------|-------|
| Base 2020-750 | $350,000 | - |
| Opt 1 2020-1250 | $365,000 | +$15K |
| Opt 2 2020-1500 | $375,000 | +$10K |
| Opt 3 2525-750 | $390,000 | +$40K |
| Opt 4 2525-1250 | $415,000 | +$25K |
| Opt 5 2525-1500 | $425,000 | +$10K |

PRICING LOGIC:
1. Stroke Upgrade Cost:
   - 750mm → 1250mm: +$15,000 (additional structure + larger servo)
   - 1250mm → 1500mm: +$10,000 (incremental increase)

2. Size Upgrade Cost:
   - 2000mm → 2500mm width: +$40,000
   - Includes: larger frame, more heaters (+60KW), bigger servo (+7.8KW)

3. Combined Upgrades:
   - Full upgrade (2020-750 to 2525-1500): +$75,000 (21% premium)

SALES APPROACH:
- Present multiple options to give customer control
- Start with base price, show clear upgrade paths
- Let customer choose based on their application needs
- Include all features as standard (no hidden costs)
- Certification (CSA) included in price

COMPARISON VALUE:
- Similar Illig/CMS machines: $600K-$800K
- Machinecraft advantage: 40-50% cost savings
- All servo drives included (often extra with competitors)""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="PF1 Pricing Strategy",
        summary="PF1 pricing: Stroke +$10-15K, size +$40K; present options for customer choice; 40-50% vs Illig/CMS",
        metadata={
            "topic": "pf1_pricing_strategy",
            "base_price": "$350,000 USD",
            "max_price": "$425,000 USD"
        }
    ))

    # 5. Key Selling Points
    items.append(KnowledgeItem(
        text="""PF1 Key Selling Points - From Proflex Quote

AUTOMATIC OPERATION:
1. Sheet Loading: Fully automatic with servo-driven loader
   - Just load stack of sheets
   - Machine picks one by one automatically
   - Better cycle time than manual loading

2. Part Unloading: Automatic
   - Machinecraft concept allows automatic unloading
   - CMS concept requires manual removal every time
   - Manual removal can cause cracks in parts

3. Quick Changeover:
   - Sheet size change: 10 minutes (automatic)
   - Tool setup: 15 minutes
   - No manual adjustment required

SERVO ADVANTAGES:
- All movements servo motor driven
- Acceleration/Deceleration profiles programmable
- Energy efficient
- Soft delayed release (prevents part damage)
- Smaller tool heights possible

HEATER SYSTEM BENEFITS:
- IR Halogen flash type = energy efficient
- Zone control for precise heating
- Heatronik monitoring = detect faulty elements
- IR probe feedback for consistent heating

SAG CONTROL SYSTEM:
- Closed chamber design
- Air blown from below sheet
- Maintains constant sheet height
- More uniform heating
- Preblow helps positive tool parts
- Better border thickness

NORTH AMERICAN COMPLIANCE:
- CSA certification included
- Ready for Canadian/US installation
- No additional certification needed""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="PF1 Selling Points",
        summary="PF1 selling: Auto load/unload (vs CMS manual), 10min changeover, all servo, CSA certified",
        metadata={
            "topic": "pf1_selling_points",
            "key_differentiators": ["Auto unload", "All servo", "Quick changeover", "CSA"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Proflex Canada Machine Options Ingestion")
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
