#!/usr/bin/env python3
"""
Ingest FRIMO Vacuum Lamination Technology & Machine Spec

Two sources:
1. FRIMO Thermoforming technology copy.pdf - What is vacuum lamination
2. Spec Single Station Thermoforming-machine_en.xls - FRIMO-Machinecraft spec mapping

Shows how Machinecraft machines fit FRIMO's European standards for vacuum lamination.

Sources:
- FRIMO Thermoforming technology copy.pdf
- Spec Single Station Thermoforming-machine_en.xls
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

SOURCE_FILE = "FRIMO Thermoforming technology + Spec Single Station Machine"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from FRIMO documents."""
    items = []

    # 1. Vacuum Forming vs Vacuum Laminating Definition
    items.append(KnowledgeItem(
        text="""Vacuum Forming vs Vacuum Laminating - FRIMO Definitions

VACUUM FORMING:
The process of heating a thermoplastic material (foils/sheets) and 
shaping it in a mould.

Process:
1. Material gets heated
2. Preformed (preblow)
3. Via vacuum positioned on a cooled positive tool
4. Following process: back pressed, back sprayed, or back foamed

Result: A FORMED foil/sheet

Materials: TPO, TEPEO2, ABS, PC, foam foil, compact foil

Applications:
- Interior automotive parts (doors, I-panels)
- Exterior automotive parts (bumpers)
- Technical parts (floor heating panels)

---

VACUUM LAMINATING:
Laminating means to HIDE the surface of a trimmed or functional part 
behind a surface with higher quality.

Process:
1. Material is heated
2. Preheated
3. Fixed with vacuum AND adhesive on a substrate
4. Result is a laminated part

Result: A LAMINATED part (substrate + decorative surface)

Materials: TPO, TEPEO2, PVC (mostly foam foils)

Applications:
- Interior automotive: Door panels, back panels, I-panels, armrests

KEY DIFFERENCE:
- Vacuum Forming = Creates a standalone formed part
- Vacuum Laminating = Covers an existing substrate with decorative surface""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Vacuum Forming vs Laminating",
        summary="Vacuum forming creates parts; vacuum laminating covers substrates with decorative film (TPO/PVC)",
        metadata={
            "topic": "vacuum_forming_vs_laminating",
            "source": "FRIMO Technology"
        }
    ))

    # 2. IMG Technology
    items.append(KnowledgeItem(
        text="""In-Mold Graining (IMG) Technology - FRIMO Explanation

DEFINITION:
During in-mold graining (IMG), the grain is first created on the foil 
during the deep drawing or vacuum laminating process.

PROCESS:
1. Ungrained and warmed foil is suctioned
2. Directly during forming/laminating process
3. Into a contoured, GRAINED SHELL
4. Grained surface of shell imprints on warmed foil

Result: Formed sheet or laminated component with impressive grain quality

FOIL MATERIALS:
- TPO foam sheet
- TPO compact sheet
- Note: PVC is NOT suitable for IMG

IMG TYPES:
1. IMG FORMING (IMGS) - Forms a grained part
2. IMG LAMINATING (IMGL) - Laminates with grain onto substrate

IMG SHELL MANUFACTURING METHODS:
1. Galvanic (Galvanoform, KTX, Standex) - Nickel shell, excellent quality
2. Gas Separating (Weber) - Chemical nickel, uniform thickness
3. Spraying (GS Engineering) - Liquid aluminum sprayed
4. Steel Shell (FRIMO) - Milled steel, etched grain

BENEFITS:
- No visible grain stretch
- Various grain areas, technical surfaces, logos possible
- Decorative embossing (airbag logo, stitching) without extra tools
- Shorter cycle times vs spray skins
- Plug assists can be used

LIMITATIONS:
- PVC not suitable
- Only small undercuts possible
- Tight radii difficult
- High/small areas challenging
- Higher tool costs""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="IMG Technology",
        summary="IMG: Grain created during forming via grained shell; TPO only (no PVC); IMGS=forming, IMGL=laminating",
        metadata={
            "topic": "img_technology",
            "types": ["IMGS", "IMGL"]
        }
    ))

    # 3. Machine Types Comparison
    items.append(KnowledgeItem(
        text="""Thermoforming Machine Types - FRIMO Classification

SINGLE STATION MACHINE:
- Heating and Forming: One after other in ONE station
- Transport of foil: Optional (possible)
- Cycle time: ~120 seconds
- Upper tables: 2 possible
- Tooling: 1 lower tool
- Example: FRIMO EcoForm

INLINE MACHINE (ECO):
- Heating and Forming: One after other in ONE station
- Transport of foil: Necessary (chain rail)
- Cycle time: ~70 seconds
- Upper tables: 2
- Tooling: 1 lower tool

INLINE MACHINE (FULL):
- Heating and Forming: One after other in TWO stations
- Transport of foil: Necessary (chain rail or clamps)
- Cycle time: ~45 seconds
- Upper tables: 4 possible
- Tooling: 2 lower tools
- Example: FRIMO VarioForm

MACHINECRAFT PF1 = SINGLE STATION MACHINE
- Matches FRIMO EcoForm concept
- Heating + forming in same station
- Manual or auto sheet loading
- 1 lower tool

FRIMO ECOFORM SIZES:
- FTE 86/240 (860 x 2400 mm)
- FTE 100/150 (1000 x 1500 mm)
- FTE 100/200 (1000 x 2000 mm)
- FTE 200/300 (2000 x 3000 mm)
- FTE 250/400 (2500 x 4000 mm)

MACHINECRAFT PF1 EQUIVALENT SIZES:
- PF1 100/150 (1000 x 1500 mm)
- PF1 150/200 (1500 x 2000 mm)
- PF1 150/250 (1500 x 2500 mm)""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Machine Types Comparison",
        summary="Single station ~120s cycle; Inline ~45-70s; PF1 = single station like FRIMO EcoForm",
        metadata={
            "topic": "machine_types",
            "pf1_equivalent": "FRIMO EcoForm"
        }
    ))

    # 4. FRIMO-Machinecraft Spec Mapping
    items.append(KnowledgeItem(
        text="""FRIMO-Machinecraft Machine Specification Mapping

This spec sheet shows how Machinecraft PF1 machines were mapped 
to FRIMO's European single-station thermoforming standards.

MACHINE SIZES MAPPED:
| FRIMO Code | MC Equivalent | Forming Area |
|------------|---------------|--------------|
| PF1 100/150 | PF1-1015 | 1000 x 1500 mm |
| PF1 150/200 | PF1-1520 | 1500 x 2000 mm |
| PF1 150/250 | PF1-1525 | 1500 x 2500 mm |

STANDARD CONFIGURATION (MACHINECRAFT):
- 1 worker operation, 1 start button
- 1 upper table, 1 lower tool
- Automatic + manual modes
- Sick light curtain
- Max part height: 500-650 mm

DRIVE OPTIONS:
Pneumatic (Standard):
- Lower table force: 25 kN
- Upper table force: 15 kN
- Clamp frame force: 12 kN (auto: 20 kN)

Electric/Servo (Optional):
- Same forces but more precise
- Electric lower table: +€20,000
- Electric upper table: +€15,000

HEATING OPTIONS:
1. Ceramic Elstein (Standard)
   - Upper: 375W (65x250mm) 72 pcs
   - Lower: 500W (65x250mm) 72 pcs
   - SSR 2:1 control (72 zones)

2. Quartz Ceramicx + Heatronix (Optional +€1,000)
   - Upper: 375W (65x125mm) 144 pcs
   - Lower: 500W (65x250mm) 72 pcs
   - 1:1 control (216 zones)

3. Halogen + Heatronix (Optional +€2,500)
   - Upper: 500W, 200 pcs
   - Lower: 500W, 200 pcs
   - 2:1 control (200 zones)

VACUUM:
- Standard: 100 m³/hr pump
- Optional: 300 m³/hr pump
- Proportional valve: Norgren 82880 (optional)""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="FRIMO-MC Spec Mapping",
        summary="FRIMO spec: PF1-1015/1520/1525; 25kN table force; Ceramic/Quartz/Halogen heater options",
        metadata={
            "topic": "frimo_mc_spec_mapping",
            "sizes": ["1000x1500", "1500x2000", "1500x2500"]
        }
    ))

    # 5. Tool Interface Standards
    items.append(KnowledgeItem(
        text="""Tool Interface Standards - FRIMO vs Machinecraft

TWO STANDARDS DEFINED:

1. "FRIMO STANDARD" TOOL INTERFACE:
   - Upper tool: Pneumatic interlocking
   - Lower tool: Vacuum interlocking OR pneumatic cylinders
   - Clamp frame: Manual interlocking
   - Media: Manual docking

2. "MACHINECRAFT STANDARD" TOOL INTERFACE:
   - Upper tool: Screwed (bolted)
   - Lower tool: Pneumatic locking
   - Upper clamp frame: Electric adjustable
   - Lower clamp frame: Bolted

PART DETECTION:
- Standard: 4 sensors per part
- Special detection: 2 additional sensors (optional)

EJECTORS & SUCTION:
- Ejector circles: 1 standard
- Suction cup circles: 1 standard
- Plug assist valves: 6 standard

TOOL WATER CIRCUITS:
- 1 circuit standard
- 2 x PT100 temperature sensors

COOLING:
- Standard: 4 radial fans
- Optional: Special duct cooling (FRIMO FACS)

QUICK MOULD CHANGE:
- Basic: Upper screwed, lower pneumatic (Machinecraft)
- Optional: FRIMO standard quick change system

This mapping allows Machinecraft machines to accept 
FRIMO-designed tools and vice versa.""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="Tool Interface Standards",
        summary="FRIMO vs MC standards: FRIMO=pneumatic/vacuum lock; MC=bolted/pneumatic; interchangeable tools",
        metadata={
            "topic": "tool_interface_standards",
            "frimo_interface": "Pneumatic/vacuum",
            "mc_interface": "Bolted/pneumatic"
        }
    ))

    # 6. Gluing Technologies
    items.append(KnowledgeItem(
        text="""Gluing Technologies for Vacuum Laminating - FRIMO

TWO MAIN ADHESIVE TYPES:

1. DISPERSION/SOLVENT ADHESIVE:
Benefits:
- Shorter cycle times (better initial bond)
- Lower costs
- ABS substrate + PVC foil possible
- Foil-free areas achievable (adhesive masks, kiss cut)
- Extensive FRIMO knowledge (10+ machines/year)

Drawbacks:
- Foil sticks everywhere (areas need masking)
- Higher tool costs for foil-free zones

2. HOTMELT ADHESIVE:
Benefits:
- Low investment
- Easy model changes
- Little space required
- Bonding of doubled foils during edge folding

Drawbacks:
- Longer cycle times
- ABS + PVC combination difficult
- Higher invest for equipment
- More effort for part changes

APPLICATION METHODS:
1. Spraying with drying
2. Slotted nozzle application
3. Roller application

FRIMO RECOMMENDATION:
- Dispersion for most vacuum laminating
- Hotmelt mainly for IMG with TPO foil
- Natural fiber laminations use hotmelt

MACHINECRAFT RELEVANCE:
Understanding glue types helps specify correct
machine features (heated clamp frames, etc.)""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Gluing Technologies",
        summary="Laminating glues: Dispersion (faster, ABS+PVC) vs Hotmelt (flexible, TPO/IMG); application methods",
        metadata={
            "topic": "gluing_technologies",
            "types": ["Dispersion", "Hotmelt"]
        }
    ))

    # 7. Heating Systems Comparison
    items.append(KnowledgeItem(
        text="""Thermoforming Heating Systems - FRIMO Technology

HALOGEN EMITTERS:
- Very powerful infrared heating
- Extremely quick heating gradients
- Energy efficient process
- Easy maintenance (plug-in emitters)
- No heating movements needed (inline machines)
- Best for: Fast cycle times, thin foils

QUARTZ EMITTERS (Ceramicx, TQS):
- Solid and proven heating
- Medium wave infrared heating
- Uniform heating
- Standard for Machinecraft
- Best for: General thermoforming

CERAMIC EMITTERS (Elstein):
- Long wave infrared
- Slower response
- More gradual heating
- Lower cost
- Best for: Thick sheets, budget machines

FRIMO TIME SHIFTED HEAT CONTROL (TSHC):
- Foil temperature calculations account for emitter layout
- Automatic calibration for foil thermal properties
- Absolute temperature values entered
- Heating picture changes per cycle
- Benefits: Energy savings, no warm-up, optimal efficiency

MACHINECRAFT HEATER MAPPING:
| FRIMO Option | MC Equivalent | Price Delta |
|--------------|---------------|-------------|
| Ceramic Elstein | Standard | Base |
| Quartz Ceramicx | Optional | +€1,000 |
| Halogen TQS | Optional | +€2,500 |

HEATRONIX CONTROL:
- 1:1 element-to-zone control
- Detects faulty elements
- +€9,500 for full system
- Required for Halogen/Quartz precision""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="Heating Systems Comparison",
        summary="Heaters: Halogen (fast), Quartz (standard), Ceramic (budget); TSHC for energy savings",
        metadata={
            "topic": "heating_systems",
            "types": ["Halogen", "Quartz", "Ceramic"]
        }
    ))

    # 8. Vacuum Laminating Applications
    items.append(KnowledgeItem(
        text="""Vacuum Laminating Applications - Automotive Focus

QUALITY HIERARCHY (FRIMO):
From highest to lowest quality/cost:
1. Leather - soft laminated (premium)
2. Press laminating (high)
3. PUR Spray skin (high)
4. PVC Slush skin (medium-high)
5. IMG compact foil (medium-high)
6. IMG foamed foil (medium)
7. TPO foamed foil - vacuum laminating (medium)
8. PVC foamed foil - vacuum laminating (medium-low)
9. Thin film injection mould (low)
10. Injection mould painted (low)
11. Injection mould blank (lowest)

VACUUM LAMINATING SWEET SPOT:
- TPO/PVC foamed foils
- Medium quality, cost-effective
- Soft-feel surface
- Automotive interiors

TYPICAL AUTOMOTIVE PARTS:
- Door panels (inner trim)
- Instrument panels
- Back panels
- Armrests
- Center consoles
- Pillar trims

PROCESS FLOW:
1. Substrate prepared (ABS, PP injection molded)
2. Foil heated in machine
3. Adhesive applied (or pre-applied hotmelt)
4. Vacuum draws foil onto substrate
5. Foil bonds to substrate surface
6. Edge folding (separate process or in-tool)

MACHINE REQUIREMENTS:
- Closed chamber for vacuum
- Substrate holding in lower tool
- Heating for foil
- Vacuum system (100-300 m³/hr)
- Optional: Heated clamp frame for hotmelt""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Vacuum Laminating Applications",
        summary="Vacuum laminating: TPO/PVC foils on ABS/PP substrates; door panels, I-panels, armrests; medium quality",
        metadata={
            "topic": "vacuum_laminating_applications",
            "parts": ["Door panels", "I-panels", "Armrests"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("FRIMO Vacuum Lamination Technology Ingestion")
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
