#!/usr/bin/env python3
"""
Ingest MC-IMG-1350 Machine Specification Sheet

Turnkey IMG thermoforming machine delivered to IAC Manesar (Feb 2025).
Complete technical specifications for automotive interior applications.

Key specs:
- Tool size: 1300 x 550 mm
- Clamping force: ~10 tonnes
- 100 kW total connected load
- Full servo drive system
- Mitsubishi PLC/HMI/Servos
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "IMGS -1350_ Machinecraft IAC Project Summary (2).pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the IMG-1350 spec sheet."""
    items = []

    # 1. Machine Overview
    items.append(KnowledgeItem(
        text="""MC-IMG-1350 Machine Overview

MODEL: MC-IMG-1350
TYPE: IMG (In-Mold Graining) Thermoforming Machine
MANUFACTURER: Machinecraft Technologies

PROJECT DETAILS:
- Customer: IAC International Automotive India Pvt. Ltd.
- Location: IAC Manesar facility
- Delivery: February 2025
- Scope: Turnkey solution (design, manufacturing, supply, installation, commissioning)

APPLICATION:
- Automotive interior soft-touch components
- In-Mold Graining thermoforming
- Premium instrument panels, door trims, consoles

MACHINE CATEGORY:
- Heavy-duty thermoforming press
- Full servo-electric drives
- Integrated automatic sheet loading
- Quick tool change capability

SIGNIFICANCE:
- First production IMG machine by Machinecraft
- Follows successful YFG prototype project
- Establishes Machinecraft in automotive interiors market
- IAC is major Tier-1 supplier (Toyota, Maruti, etc.)""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="MC-IMG-1350",
        summary="MC-IMG-1350: Turnkey IMG machine for IAC Manesar, delivered Feb 2025, automotive interiors",
        metadata={
            "topic": "machine_overview",
            "model": "MC-IMG-1350",
            "customer": "IAC",
            "location": "Manesar",
            "delivery": "Feb 2025"
        }
    ))

    # 2. Complete Technical Specifications
    items.append(KnowledgeItem(
        text="""MC-IMG-1350 Complete Technical Specifications

PLATEN & TOOL DIMENSIONS:
- Max Platen Size (Top & Bottom): 1900 x 900 mm
- Max Tool Size: 1300 x 550 mm
- Tool Height: 800 mm (upper & lower)
- Working Area: 1800 x 800 mm

BLANK SHEET HANDLING:
- Maximum Blank Size: 1350 x 600 mm
- Minimum Blank Size: 800 x 400 mm
- Feed: Automatic sheet loading system

MACHINE TRAVEL & FORCE:
- Daylight Opening: 2200 mm
- Top Platen Travel: 1050 mm
- Bottom Platen Travel: 1050 mm
- Clamping Force: ~10 tonnes
- Load Capacity: 2000 kg (each platen)

VACUUM SYSTEM:
- Vacuum Tanks: 2 x 1000 liters (total 2000L)
- Vacuum Pumps: 2 x 100 m³/hr (total 200 m³/hr)
- Note: Dual redundancy for reliability

SPEED:
- Maximum Table Speed: 250 mm/s
- Minimum Table Speed: 30 mm/s
- Variable speed for process optimization

POWER:
- Heating Load: 70.2 kW
- Servo Motors Load: 21.8 kW
- Total Connected Load: ~100 kW

HEATING SYSTEM:
- Type: IR Quartz elements
- Wattage: 650 W each
- Configuration: Two grids (6 x 9 each) = 54 elements per grid
- Total elements: 108 elements (top + bottom)
- Max Heating Area: 1500 x 650 mm
- Sandwich heating (top & bottom)""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="MC-IMG-1350",
        summary="IMG-1350: 1300x550mm tool, 10T clamp, 2200mm daylight, 100kW, dual vacuum (2x100m³/hr)",
        metadata={
            "topic": "specifications",
            "tool_size_mm": "1300x550",
            "clamping_tonnes": 10,
            "power_kw": 100,
            "vacuum_m3hr": 200,
            "daylight_mm": 2200
        }
    ))

    # 3. Servo & Control System
    items.append(KnowledgeItem(
        text="""MC-IMG-1350 Servo & Control System

DRIVE SYSTEM: Full Electric Servo
All movements are servo motor driven:
- Top platen movement
- Bottom platen movement
- Sheet frame adjustments (X & Y)
- Autoloader movements

SERVO MOTORS: Mitsubishi Japan
- Total servo load: 21.8 kW
- Precise positioning
- Variable speed control
- Energy efficient

PLC & HMI:
- PLC: Mitsubishi FX5U Series
- HMI: 10-inch touchscreen
- Recipe storage and recall
- Process parameter control

GEARBOXES:
- SEW (Germany)
- Bonfiglioli (Italy)
- Heavy-duty industrial grade

ADJUSTABLE CLAMP FRAME:
- Servo motor driven
- Adjustable in X and Y axes
- Quick size changeover
- Programmable positions

SAFETY SYSTEM:
- Light sensors (presence detection)
- 3-color tower lamp (status indication)
- Harting type connectors (industrial grade)
- Safety interlocks throughout

PNEUMATICS:
- Brand: Festo (Germany)
- Certified tanks
- Precision valves
- Vacuum cups with adjustable arrangement""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="MC-IMG-1350",
        summary="IMG-1350 control: Mitsubishi FX5U PLC, 10\" HMI, full servo (21.8kW), Festo pneumatics",
        metadata={
            "topic": "control_system",
            "plc": "Mitsubishi FX5U",
            "servo": "Mitsubishi",
            "servo_load_kw": 21.8,
            "pneumatics": "Festo"
        }
    ))

    # 4. Auxiliary Systems
    items.append(KnowledgeItem(
        text="""MC-IMG-1350 Auxiliary Systems

COOLING SYSTEM:
- Type: Air blowers
- Quantity: 4 adjustable air blowers
- Brand: EBM Papst (Germany)
- Feature: Adjustable positioning and airflow
- Purpose: Rapid part cooling after forming

QUICK TOOL CHANGE SYSTEM:
- Ball transfer units on bottom platen
- Tool slides in easily
- Pneumatic cylinders for clamping
- Fast tool change for production flexibility

AUTOMATIC SHEET LOADING:
- Integrated autoloader
- Picks sheets from stack
- Servo-driven movements
- Automatic sheet positioning
- Reduces cycle time

VACUUM CUP ARRANGEMENT:
- Adjustable vacuum cups
- Configurable for different sheet sizes
- Quick reconfiguration
- Reliable sheet pickup

HEATING ELEMENTS:
- IR Quartz (not ceramic)
- 650W each element
- Grid arrangement: 6 rows x 9 columns per side
- Sandwich heating (top + bottom)
- Maximum heating area: 1500 x 650 mm""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="MC-IMG-1350",
        summary="IMG-1350 aux: EBM Papst cooling, quick tool change, autoloader, adjustable vacuum cups",
        metadata={
            "topic": "auxiliary_systems",
            "cooling": "EBM Papst",
            "quick_change": True,
            "autoloader": True
        }
    ))

    # 5. Process Flow
    items.append(KnowledgeItem(
        text="""MC-IMG-1350 Process Flow

MACHINE PROCESS SEQUENCE:

STEP 1: AUTOMATIC SHEET LOADING
- Sheet stack placed in loader
- Vacuum cups pick top sheet
- Sheet transported to forming area
- Automatic separation ensures single sheet

STEP 2: SHEET CLAMPING
- Sheet positioned in clamp frame
- Servo-adjustable clamp frame grips sheet
- Frame adjustable in X and Y
- Secure grip around perimeter

STEP 3: SHEET HEATING
- IR Quartz heaters activate
- Sandwich heating (top + bottom)
- 108 elements provide uniform heating
- PID temperature control
- Sheet reaches forming temperature

STEP 4: IMG PRESS FORMING
- Heated sheet positioned over tool
- Top and bottom platens move (servo-driven)
- 10-tonne clamping force applied
- Vacuum pulled through tool
- In-Mold Graining pattern transferred
- Grain from nickel shell tool to TPO skin

STEP 5: COOLING & RELEASE
- EBM Papst blowers activate
- Part cools in tool
- Vacuum released
- Platens open (2200mm daylight)
- Part removed (manual or automated)

CYCLE READY FOR NEXT PART:
- Autoloader brings next sheet
- Cycle repeats

TYPICAL CYCLE TIME:
- Varies with part complexity
- ~60-120 seconds typical for IMG parts
- Heating time is longest segment""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="MC-IMG-1350",
        summary="IMG process: Auto load → Clamp → Heat (IR Quartz) → Press form (10T) → Cool → Release",
        metadata={
            "topic": "process_flow",
            "steps": ["loading", "clamping", "heating", "forming", "cooling"]
        }
    ))

    # 6. Component Brands Summary
    items.append(KnowledgeItem(
        text="""MC-IMG-1350 Component Brands Summary

CONTROL & AUTOMATION:
- PLC: Mitsubishi FX5U Series (Japan)
- HMI: 10-inch touchscreen
- Servo Motors: Mitsubishi (Japan)
- Servo Drives: Mitsubishi (Japan)

MECHANICAL:
- Gearboxes: SEW (Germany) & Bonfiglioli (Italy)
- Ball Transfers: For quick tool change

PNEUMATICS:
- System: Festo (Germany)
- Tanks: Certified pressure vessels
- Valves: Festo precision
- Vacuum Cups: Adjustable arrangement

HEATING:
- Elements: IR Quartz, 650W each
- Configuration: 6x9 grid x 2 (top + bottom)
- Total: 108 elements

VACUUM:
- Pumps: 2 x 100 m³/hr
- Tanks: 2 x 1000 liters

COOLING:
- Blowers: EBM Papst (Germany)
- Quantity: 4 adjustable

SAFETY:
- Light Sensors: Presence detection
- Tower Lamp: 3-color status
- Connectors: Harting type (industrial)
- Interlocks: Throughout machine

QUALITY STANDARD:
- Premium international components
- Same brands as PF1 series
- Global availability of spares
- Industrial-grade reliability""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="MC-IMG-1350 Components",
        summary="IMG-1350 brands: Mitsubishi control/servo, Festo pneumatics, SEW/Bonfiglioli gearboxes, EBM Papst",
        metadata={
            "topic": "components",
            "plc": "Mitsubishi FX5U",
            "pneumatics": "Festo",
            "gearboxes": ["SEW", "Bonfiglioli"],
            "cooling": "EBM Papst"
        }
    ))

    # 7. Comparison to PF1 Series
    items.append(KnowledgeItem(
        text="""MC-IMG-1350 vs PF1 Series Comparison

IMG-1350 IS SPECIALIZED FOR AUTOMOTIVE INTERIORS:

| Feature | IMG-1350 | PF1 (Standard) |
|---------|----------|----------------|
| Primary Use | Automotive soft-touch | General thermoforming |
| Clamping Force | 10 tonnes | Lower (vacuum only) |
| Daylight | 2200mm | Varies by model |
| Heating | IR Quartz (108 elements) | Options available |
| Servo Drives | Full system | Optional |
| Autoloader | Included | Optional |
| Quick Tool Change | Included | Optional |
| Dual Vacuum | 2x100 m³/hr | Single pump typical |
| Target Material | TPO foil for IMG | Various sheet materials |

KEY DIFFERENCES:

1. CLAMPING FORCE:
   - IMG needs high force for press lamination
   - PF1 vacuum forming doesn't need high tonnage

2. DAYLIGHT OPENING:
   - IMG: 2200mm for complex automotive tools
   - PF1: Smaller, sufficient for simpler parts

3. AUTOMATION LEVEL:
   - IMG: Full servo, auto everything
   - PF1: Options from manual to full servo

4. VACUUM REDUNDANCY:
   - IMG: Dual pumps + dual tanks
   - PF1: Single system typical

5. PRICE POINT:
   - IMG: Premium (estimated ₹2+ Cr)
   - PF1: Range from ₹60L to ₹2.4Cr depending on options

WHEN TO RECOMMEND IMG VS PF1:
- IMG: Automotive interiors, soft-touch TPO, lamination
- PF1: Industrial parts, packaging, general thermoforming""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="IMG vs PF1",
        summary="IMG-1350: 10T force, automotive focus; PF1: general purpose; IMG is specialized premium",
        metadata={
            "topic": "comparison",
            "img_force_tonnes": 10,
            "img_use": "automotive_interiors"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("MC-IMG-1350 Specification Sheet Ingestion")
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
