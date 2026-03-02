#!/usr/bin/env python3
"""
Ingest RT-5A-1515 5-Axis Router Quote

5-axis CNC router for trimming thermoformed parts.
Usually sold alongside PF1 machines for complete forming + trimming solution.

Source: MT2021091902 RT5A 1515 V01.pdf
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

SOURCE_FILE = "MT2021091902 RT5A 1515 V01.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from RT-5A router quote."""
    items = []

    # 1. Quote Overview
    items.append(KnowledgeItem(
        text="""RT-5A-1515 Five-Axis Router Quote Overview

QUOTE DETAILS:
- Quote No: MT2021091902
- Date: 19 September 2021
- Contact: Rushabh Doshi
- Client: Roy Matthew, Walterpack India

MACHINE MODEL: RT-5A-1515
- RT = Router (Machinecraft's router series)
- 5A = 5-Axis interpolating
- 1515 = 1500 x 1500 mm operating part (5-axis mode)

PRODUCT POSITIONING:
"RT Routers from Machinecraft are a range of latest generation 
5-axis interpolating machining centres for trimming thermoformed 
parts - created to perform at high speed on the most complex 3D 
shapes."

KEY VALUE PROPOSITION:
- Compact design with large machining volume
- High precision and reliability
- Ideal for thermoformed part trimming
- Highest quality available today

PRICING:
- Machine Price: ₹95,00,000 (Ninety Five Lakhs)
- Terms: Ex-works India
- Extras: Shipping, insurance, packing, commissioning

PAYMENT: 50% advance, 50% before dispatch
WARRANTY: 12 months
LEAD TIME: 16-20 weeks

TYPICAL USE:
Sold alongside PF1 thermoforming machines for complete
forming + trimming production cell.""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="RT-5A-1515 Quote Overview",
        summary="RT-5A-1515 router: ₹95L; 5-axis trimming for thermoformed parts; paired with PF1 machines",
        metadata={
            "topic": "rt5a_overview",
            "quote_no": "MT2021091902",
            "price": "₹95,00,000"
        }
    ))

    # 2. Technical Specifications
    items.append(KnowledgeItem(
        text="""RT-5A-1515 Technical Specifications

WORKING AREA:
- Max Working Area: 2500 x 2500 mm (table size)
- Max Operating Part (5-Axis Mode): 1500 x 1500 mm
- Max Operating Part (3-Axis Mode): 2500 x 2500 mm

Note: 5-axis mode has smaller envelope due to spindle rotation clearance.
For larger parts without complex angles, 3-axis mode gives full area.

POWER:
- Total Connected Load: 30 KW

ELECTRO-SPINDLE (HSD/Hiteco Italy):
- Power: 9 KW
- Max Speed: 18,000 rpm
- Nominal Speed: 12,000 rpm
- Cooling: Liquid/Air cooled
- Make: HSD or Hiteco (Italy)

AXIS SYSTEM:
- X, Y, Z axes: Ball-screw transmission
- B/C axes: Hollow shaft (rotation)
- Guides: Preloaded ball guides and slides
- Positioning: Yaskawa servo motors (Japan)

TOOL CHANGE:
- Type: Automatic Tool Change (ATC)
- Capacity: 6-position tool carousel

WORKING TABLE:
- Construction: Electro-welded steel monolithic structure
- Configuration: Smooth or with T-slots (configurable)

VACUUM SYSTEM:
- Pump Capacity: 100 m³/hr
- Pump Make: Becker (Germany)
- Purpose: Holding parts on fixture during cutting

CNC CONTROL:
- Controller: Syntec (Taiwan)
- Type: Full CNC unit""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="RT-5A-1515 Technical Specs",
        summary="RT-5A-1515: 2500x2500mm table, 1500x1500mm 5-axis, 9KW HSD spindle, 18K RPM, Yaskawa servos",
        metadata={
            "topic": "rt5a_specs",
            "working_area": "2500 x 2500 mm",
            "spindle": "9 KW, 18000 rpm"
        }
    ))

    # 3. Component Brands
    items.append(KnowledgeItem(
        text="""RT-5A-1515 Component Makes & Brands

CONTROL & AUTOMATION:
- Controller: Syntec (Taiwan)
- Servo Motors: Yaskawa (Japan)
- Gearbox: Shimpo (Japan)

SPINDLE:
- Make: HSD / Hiteco (Italy)
- Reputation: Leading European spindle manufacturers
- Used by: Major CNC router brands globally

PNEUMATICS:
- Make: SMC (Japan)

SENSORS:
- Makes: Omron / Pepperl+Fuchs / Sick
- Mix of Japanese and German sensors

VACUUM:
- Pump: Becker (Germany)
- Same brand used in PF1 thermoforming machines

BRAND POSITIONING:
All premium components:
- Italian spindle (HSD/Hiteco)
- Japanese servos (Yaskawa)
- Japanese gearbox (Shimpo)
- German vacuum (Becker)
- Japanese/German sensors

This justifies Machinecraft quality vs Chinese alternatives.

DOCUMENTATION:
- Operation instructions
- Spare part list
- System layout
- Maintenance instructions
- Wiring diagram
- Available on data medium or paper""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="RT-5A Component Brands",
        summary="RT-5A components: HSD/Hiteco spindle (Italy), Yaskawa servo (Japan), Syntec control, Becker vacuum",
        metadata={
            "topic": "rt5a_components",
            "spindle": "HSD/Hiteco Italy",
            "servo": "Yaskawa Japan"
        }
    ))

    # 4. 5-Axis vs 3-Axis Capability
    items.append(KnowledgeItem(
        text="""RT-5A-1515 Axis Modes & Capability

5-AXIS INTERPOLATING MODE:
- Part Size: Up to 1500 x 1500 mm
- Axes: X, Y, Z linear + B, C rotational
- Use: Complex 3D contours, undercuts, angled cuts
- Application: Thermoformed parts with complex edges

3-AXIS MODE:
- Part Size: Up to 2500 x 2500 mm (full table)
- Axes: X, Y, Z linear only
- Use: Flat trimming, simple edge cuts
- Application: Larger parts with simpler geometry

WHY 5-AXIS FOR THERMOFORMING:

Thermoformed parts have:
- Curved surfaces
- Draft angles
- Complex edge profiles
- Undercuts

5-axis allows:
- Spindle to stay perpendicular to surface
- Clean cuts on angled edges
- Access to undercut areas
- Single setup (no repositioning)

INTERPOLATING HEAD:
The B and C axes rotate the spindle continuously during cutting.
This means smooth curved cuts without stopping/repositioning.

COMPARISON - 3-Axis vs 5-Axis:
| Feature | 3-Axis | 5-Axis |
|---------|--------|--------|
| Part size | 2500mm | 1500mm |
| Curved edges | Limited | Full |
| Undercuts | No | Yes |
| Draft angles | Manual tilt | Auto |
| Setup time | Multiple | Single |
| Part complexity | Simple | Complex |

TYPICAL THERMOFORMED PARTS NEEDING 5-AXIS:
- Automotive interior panels (curved + holes)
- Bathtub/spa edges
- Equipment housings with angles
- Medical device parts with precision holes""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="RT-5A Axis Modes",
        summary="5-axis (1500mm) for complex 3D cuts; 3-axis (2500mm) for simple trimming; interpolating head",
        metadata={
            "topic": "rt5a_axis_modes",
            "5_axis_size": "1500 x 1500 mm",
            "3_axis_size": "2500 x 2500 mm"
        }
    ))

    # 5. Router + PF1 Pairing
    items.append(KnowledgeItem(
        text="""RT-5A Router - Pairing with PF1 Thermoforming Machines

TYPICAL PRODUCTION CELL:
1. PF1 Thermoforming Machine - Forms the part
2. RT-5A Router - Trims the formed part

WORKFLOW:
1. Sheet loaded into PF1
2. Heated and formed over tool
3. Formed part removed
4. Part placed on router fixture
5. Router trims edges, cuts holes, shapes
6. Finished part ready

SIZE MATCHING:

| PF1 Model | Forming Area | RT-5A Model | 5-Axis Part |
|-----------|--------------|-------------|-------------|
| PF1-1515 | 1500x1500 | RT-5A-1515 | 1500x1500 |
| PF1-2020 | 2000x2000 | RT-5A-2020 | 2000x2000 |
| PF1-2525 | 2500x2500 | RT-5A-2525 | 2500x2500 |

Router table should match or exceed PF1 forming area.

COMBINED PRICING EXAMPLE (Walterpack):
- PF1-1515/S/A: ₹1.17 CR
- RT-5A-1515: ₹0.95 CR
- COMBINED: ₹2.12 CR for complete cell

FIXTURE CONSIDERATION:
- Router uses vacuum fixtures to hold parts
- Fixtures designed per part geometry
- Fixture cost additional to machine
- Same fixture approach as SPM projects

WHY BUY TOGETHER:
- Single source for forming + trimming
- Matched capacity (no bottleneck)
- Integrated process support
- Simplified commissioning
- One supplier for service/support

ALTERNATIVE:
Some customers buy only PF1 and outsource trimming.
Or use manual trimming for low volume.
RT-5A justified at medium-high volumes.""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="RT-5A PF1 Pairing",
        summary="RT-5A pairs with PF1: Match sizes; combined cell ~₹2.12CR; single source forming + trimming",
        metadata={
            "topic": "rt5a_pf1_pairing",
            "combined_price": "~₹2.12 CR",
            "workflow": "Form → Trim"
        }
    ))

    # 6. Commercial Terms
    items.append(KnowledgeItem(
        text="""RT-5A-1515 Commercial Terms

PRICING:
- Machine: ₹95,00,000 (₹95 Lakhs)
- Basis: Ex-works factory India

EXTRAS (Customer bears):
- Shipping cost
- Insurance
- Packing
- Commissioning charges

PAYMENT TERMS:
- 50% Advance with PO
- 50% Before dispatch

WARRANTY:
- 12 months from pre-acceptance notification

LEAD TIME:
- 16-20 weeks after technical/commercial clarification
- Exact timing after written PO and advance receipt

QUOTE VALIDITY: 2 weeks

SIGNATORIES:
- DB Doshi (Sales Director)
- Rushabh Doshi (Technical Sales Manager)

PRICING CONTEXT:
- RT-5A-1515: ₹95 Lakhs (~$115K USD)
- Comparable to mid-range European 5-axis routers
- Premium components (Italian spindle, Japanese servo)
- Significantly less than Biesse/SCM brands

ROUTER vs SPM 5-AXIS:
| Feature | RT-5A (Standard) | SPM 5-Axis |
|---------|------------------|------------|
| Price | ₹95L | ₹52-65L |
| Bed Size | 2500x2500 | 600-1300mm |
| Part Size | 1500x1500 | 600x600 |
| Application | General | Specific |
| Spindle | 9KW/18K rpm | 9KW/24K rpm |

RT-5A is larger format for bigger thermoformed parts.
SPM router (like Motherson project) for smaller precision parts.""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="RT-5A Commercial Terms",
        summary="RT-5A: ₹95L ex-works; 50-50 payment; 12-month warranty; 16-20 weeks; commissioning extra",
        metadata={
            "topic": "rt5a_commercial",
            "price": "₹95,00,000",
            "payment": "50-50"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("RT-5A-1515 5-Axis Router Quote Ingestion")
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
