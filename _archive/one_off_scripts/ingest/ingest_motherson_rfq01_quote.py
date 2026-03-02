#!/usr/bin/env python3
"""
Ingest Motherson Phillips SPM RFQ01 - Technical Spec & Quote

Detailed quote for Phillips dStream Torso Coil (MRI parts) project.
Complete machine specs, tooling breakdown, and pricing.

Source: 2021 Feb Motherson Phillips SPM RFQ01.pdf
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

SOURCE_FILE = "2021 Feb Motherson Phillips SPM RFQ01.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from Motherson RFQ01 quote."""
    items = []

    # 1. Quote Overview
    items.append(KnowledgeItem(
        text="""Motherson Phillips RFQ01 Quote Overview

OFFER DETAILS:
- Offer No: MT2021021003
- Date: 17 February 2021
- Contact: Rushabh Doshi
- Customer: Motherson India
- End Customer: Phillips Healthcare
- Application: dStream Torso Coil (MRI medical device)
- Location: Ranjangaon, Pune, India

SCOPE OF WORK:
- 16 parts for Medical Device
- Material: PC & Kydex (0.5, 1, 1.5, 4mm thicknesses)
- Process: Pressure Forming & Trimming
- Complete Turn-Key project solution

PRICING SUMMARY (INR):
| Item | Price |
|------|-------|
| Thermoforming Machine SPM/500x600/S | ₹64,00,000 |
| 5-Axis Cutting Router 5A/1300x1300x500 | ₹52,00,000 |
| Thermoforming Tools (11 tools) | ₹26,39,000 |
| Cutting Router Fixtures (16) | ₹28,73,000 |
| Checking Fixtures (16) | ₹20,35,000 |
| SUBTOTAL | ₹1,91,47,000 |
| 10% Discount on Tools | -₹7,54,700 |
| GRAND TOTAL | ₹1,83,92,300 |

TERMS: Turn-key including commissioning at customer site
and transportation to Ranjangaon, Pune.""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Motherson RFQ01 Quote Overview",
        summary="Motherson RFQ01: ₹1.84CR turn-key; SPM ₹64L + Router ₹52L + Tools ₹75L; Phillips MRI parts",
        metadata={
            "topic": "motherson_rfq01_overview",
            "offer_no": "MT2021021003",
            "total": "₹1,83,92,300"
        }
    ))

    # 2. SPM Machine Specifications
    items.append(KnowledgeItem(
        text="""SPM/500x600/S Pressure Thermoforming Machine - Technical Specs

MODEL: SPM/500x600/S (Special Purpose Machine)

FORMING SPECIFICATIONS:
- Max Forming Area: 600 x 500 mm (X x Y)
- Max Stroke: 180 mm in Z direction
- Press Force: 20 tons clamping (servo toggle mechanism)
- Material Thickness: 0.5 mm to 8 mm (sandwich heaters)
- Materials: ABS, PP, PC, PE, TPO, Kydex

CONSTRUCTION:
- Toggle mechanism: MS CNC machined, phosphor-bronze bushes
- CE safety compliant: Light curtains, sensors, guards
- Dual capability: Pressure forming AND vacuum forming

HEATING SYSTEM:
- Heaters: Sandwich (top + bottom)
- Top heater: Right side, 5x4 = 20 elements, 500W each
- Bottom heater: Left side, 5x4 = 20 elements, 300W each
- Element type: IR Ceramic (Elstein Germany)
- Element size: 125 x 125 mm square
- Total heating load: 16 KW
- Temperature range: up to 500°C
- Control: SSR with zone control via HMI

SENSORS & CONTROLS:
- Sag sensor: Adjustable, below sheet clamping area
- Pyrometer: IR temperature detector in top heater
- PLC: Mitsubishi Japan
- HMI: 10" touchscreen with SD card for recipes
- Electrical cabinet: Rittal (CE standards)

SERVO SYSTEM:
- Lower table: 3.5 KW servo (Mitsubishi Japan)
- Upper table: 3.5 KW servo (Mitsubishi Japan)
- Benefit: Precision control, additional Z stroke

PNEUMATIC MOVEMENTS:
- Top heater movement
- Bottom heater movement
- Sheet clamping (2 cylinders, hinge mechanism)
- Pneumatics: FESTO Germany

VACUUM SYSTEM:
- Pump capacity: 60 m³/hr
- Purpose: Enables vacuum forming for future applications

SHEET CLAMPING:
- Rubber seal: Silicone sponge (200°C rated)
- Frame: MS welded, changeable for different sheet sizes

TOOL CHANGE:
- Platform provided for mould loading from back
- Bolting: 4-6 holes evenly distributed

PRESSURE BOX:
- Different pressure box per tool
- Mounted on top table
- Internal deflector plates for even air distribution
- Digital pressure sensor with PLC feedback

POWER: Approx. 30 KW total
PRICE: ₹64,00,000""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="SPM/500x600/S Specifications",
        summary="SPM/500x600/S: 600x500mm, 20-ton servo toggle, sandwich heaters (Elstein), 0.5-8mm; ₹64L",
        metadata={
            "topic": "spm_500x600_specs",
            "forming_area": "600 x 500 mm",
            "price": "₹64,00,000"
        }
    ))

    # 3. 5-Axis Router Specifications
    items.append(KnowledgeItem(
        text="""5A/1300x1300x500 Five-Axis Cutting Router - Technical Specs

MODEL: 5A/1300x1300x500

TRAVEL & SIZE:
- XY Travel: 1300 mm each direction
- Z Travel: 500 mm
- Max Part Size: 600 x 600 mm (due to 90° spindle rotation)
- Frame: Steel profile, RAL 7035 spray paint

SERVO SYSTEM (YASKAWA Japan):
- X axis: 1.3 KW AC servo
- Y axis: 1.3 KW AC servo
- Z axis: 1.8 KW AC servo
- 5 total servo motors, all digital

AXES:
- 3 Linear axes: Tempered, ground linear guides (Hiwin)
- 2 Swiveling axes: Demas Italy

SPINDLE (Hyteco/HSD Italy):
- Power: 9 KW
- Max Speed: 24,000 rpm
- Tool Change: Automatic, up to 8 tools

CONTROLLER: Syntec (Taiwan)

ACCURACY:
- Path Accuracy (free): 0.1 mm
- Path Accuracy (cutting 8mm): 0.5 mm

VACUUM SYSTEM:
- Pump: Becker Germany, 60 m³/hr
- Fixture: Parts held by vacuum pads

CHIP CLEANING:
- Separate vacuum extractor (manual operation)
- Air gun provided

MATERIAL CAPABILITY:
- Thermoformed plastics: Yes
- Artificial wood: Yes
- Aluminum/Brass: Not recommended

SOFTWARE (not included):
- Recommended: SprutCAM, Siemens NX, MasterCAM
- Tool path generation by customer

POWER: Approx. 40 KW total
PRICE: ₹52,00,000""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="5A/1300x1300x500 Router Specs",
        summary="5-Axis Router: 1300x1300x500mm travel, 9KW HSD spindle, Yaskawa servos, 0.1mm accuracy; ₹52L",
        metadata={
            "topic": "5axis_router_specs",
            "travel": "1300 x 1300 x 500 mm",
            "price": "₹52,00,000"
        }
    ))

    # 4. Component Makes & Brands
    items.append(KnowledgeItem(
        text="""Machinecraft SPM Component Brands - Premium Specification

CONTROL SYSTEM:
- PLC: Mitsubishi (Japan)
- HMI: Mitsubishi (Japan)
- Servo Motors: Mitsubishi (Japan)
- Controller (Router): Syntec (Taiwan)

PNEUMATICS:
- Cylinders & Valves: FESTO (Germany)

HEATING:
- Heater Elements: Elstein (Germany)
- SSR Control: Crydom / Unison

COOLING:
- Blowers: EBM Papst

SENSORS:
- Light Sensors: Pepperl+Fuchs
- Sheet Temperature: Raytec (pyrometer)

VACUUM:
- Pump: Becker (Germany)

MOTION:
- Linear Guides: Hiwin
- Gearbox: Bonfiglioli / SEW
- 5-Axis Head: Demas (Italy)

SPINDLE:
- Make: Hyteco / HSD (Italy)

ELECTRICAL:
- Cabinet: Rittal (CE standards)

PAINT SPECIFICATION:
- System/devices: Light Grey RAL 7035 smooth
- Moveable parts: Siemens Grey RAL 7035 smooth
- Control cabinet: Light Grey RAL 7035 smooth
- Protective covers: Original supplier standard (yellow/black)
- Safety devices: Yellow orange RAL 2000 smooth

This component list demonstrates Machinecraft's commitment
to European/Japanese quality components in SPM machines.""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="SPM Component Brands",
        summary="SPM components: Mitsubishi PLC/servo, FESTO pneumatics, Elstein heaters, Becker vacuum, Hiwin guides",
        metadata={
            "topic": "spm_component_brands",
            "key_brands": ["Mitsubishi", "FESTO", "Elstein", "Becker", "Hiwin", "HSD"]
        }
    ))

    # 5. Tooling Details
    items.append(KnowledgeItem(
        text="""Motherson RFQ01 Tooling Breakdown - Phillips dStream Parts

FORMING TOOLS (11 tools, ₹26,39,000):

Tool construction:
- Material: Aluminum HE30 Grade
- Process: CNC machined
- Feature: Heating/Cooling mechanism

| Tool | Parts | Configuration | Cost |
|------|-------|---------------|------|
| Tool 1 | AC Hinge Front + Rear | 1+1 cavity | ₹3,40,000 |
| Tool 2 | AC Hinge Middle (2x) | 2 cavity | ₹3,44,000 |
| Tool 3 | Bottom Support Rear + Front | 1+1 cavity | ₹2,06,000 |
| Tool 4 | Bottom Support Middle (2x) | 2 cavity | ₹1,92,000 |
| Tool 5 | AC Middle PCB Support (2x) | 2 cavity | ₹2,02,000 |
| Tool 6 | AC Front + Rear PCB Support | 1+1 cavity | ₹2,18,000 |
| + 5 more tools | Various parts | Various | Balance |

CUTTING FIXTURES (16 fixtures, ₹28,73,000):

Construction:
- Material: Artificial wood + vacuum pads
- Some HE30 aluminum where required
- All individual fixtures

Range: ₹40,000 (small parts) to ₹4,20,000 (Catchment Plate)

CHECKING FIXTURES (16 fixtures, ₹20,35,000):

Construction:
- Material: Artificial wood
- Some HE30 aluminum
- Hand levers for part holding
- Master pins & jigs for hole verification
- Center-to-center distance checking

Range: ₹30,000 (small parts) to ₹2,90,000 (Catchment Plate)

TOOLING STRATEGY:
- Grouped forming tools where possible (2-cavity)
- Individual cutting/checking fixtures for precision
- HE30 aluminum for temperature-controlled forming
- Artificial wood for non-heated fixtures (cost effective)""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Motherson RFQ01 Tooling",
        summary="RFQ01 tooling: 11 forming (HE30 Al) ₹26L + 16 cutting ₹29L + 16 checking ₹20L = ₹75L total",
        metadata={
            "topic": "motherson_rfq01_tooling",
            "forming_tools": 11,
            "cutting_fixtures": 16,
            "checking_fixtures": 16
        }
    ))

    # 6. Ancillary Equipment Requirements
    items.append(KnowledgeItem(
        text="""Motherson RFQ01 Ancillary Equipment - Customer Site Requirements

EQUIPMENT CUSTOMER MUST PROVIDE:

1. AIR COMPRESSOR:
   - Type: Two-stage low pressure
   - Motor: 20 HP, 900 RPM
   - FAD: 59.8 CFM
   - Max Pressure: 175 PSIG (12.3 kg/cm²)
   - Required: Oil-free, water-free, clean air
   - Min 6 bar for both machines

2. MTC (Mould Temperature Controller):
   - Temperature range: Ambient to 150°C
   - Heating capacity: 9.0 KW (water heating)
   - Pump flow: 60 LPM max
   - Max pressure: 3.8 bar
   - Connected load: 9.5 KW
   - Tank volume: 15 liters
   - Cooling water: 50 LPM at 2-3 bar

3. WATER CHILLER:
   - Cooling capacity: 2 TR
   - Chilled water outlet: 10°C
   - Chilled water inlet: 30°C
   - Control range: 10-30°C
   - Refrigerant: R407 / R22
   - Connected load: 3.3 KW
   - Tank volume: 60 liters

4. AIR CIRCULATING OVEN (for PC annealing):
   - Chamber size: 1500 x 1000 x 1100 mm (WxDxH)
   - Sheet size capacity: 650 x 850 mm
   - Temperature range: up to 95°C
   - Heating: SS tubular with fins, 12 KW
   - Hot air circulation from top
   - Adjustable exhaust
   - Digital temperature controller with timer

5. SHEARING MACHINE:
   - Purpose: Cut sheets to frame sizes
   - Customer to source separately

FACILITY REQUIREMENTS:
- Electrical: 3 x 400/230V + N + PE, 50Hz
- N fully grounded and loadable
- Compressed air: Min 6 bar, oil/water free""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="RFQ01 Ancillary Equipment",
        summary="Customer needs: 20HP compressor, MTC (150°C), 2TR chiller, annealing oven (1500x1000mm), shear",
        metadata={
            "topic": "rfq01_ancillary_equipment",
            "customer_scope": ["Compressor", "MTC", "Chiller", "Oven", "Shear"]
        }
    ))

    # 7. Project Terms & Timeline
    items.append(KnowledgeItem(
        text="""Motherson RFQ01 Project Terms & Timeline

DELIVERY TIMELINE:
- Tools & Fixtures: 13 weeks from model data approval
- Machines: 13 weeks from PO and advance
- Commissioning at Machinecraft: 4 weeks (T1 trials)
- Commissioning at customer site: 1 week
- TOTAL: ~18 weeks from PO to production ready

COMMISSIONING SCOPE:
- Marriage of tools with forming and cutting machines
- T1 trial parts provided to client
- Customer provides material for testing
- Machinecraft sets process parameters
- Parts validated to customer expectations

PAYMENT TERMS:
- 25% Advance with signed PO
- 25% After 30 days of PO
- 40% After T1 trials at Machinecraft
- 10% Before final dispatch

WARRANTY:
- 12 months from commissioning date at customer site

QUOTE VALIDITY: 4 weeks

DELIVERY TERMS:
- Turn-key pricing
- Includes transport to Ranjangaon, Pune
- Includes commissioning at customer site

SOFTWARE NOTE:
- CAD/CAM software for router NOT included
- Customer to purchase SprutCAM, NX, or MasterCAM

KEY INSIGHT FOR SALES:
This quote structure (25-25-40-10) protects both parties:
- Customer pays 50% before work starts
- Customer pays 40% only after seeing T1 parts work
- 10% holdback ensures proper site commissioning""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="RFQ01 Terms & Timeline",
        summary="RFQ01 terms: 18 weeks total; 25-25-40-10 payment; 12-month warranty; turn-key to Pune",
        metadata={
            "topic": "rfq01_terms_timeline",
            "lead_time": "18 weeks",
            "payment": "25-25-40-10",
            "warranty": "12 months"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Motherson Phillips RFQ01 Quote Ingestion")
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
