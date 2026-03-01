#!/usr/bin/env python3
"""
Ingest PF1-R-0707-X Roll Feeder Machine Quotation

This document is a quotation for the PF1-R-0707-X model - a roll-fed 
thermoforming machine designed for large parts using roll format raw material.
Key differentiator: spike chain material transport system.

Key specifications:
- Roll feeder for continuous material from rolls
- Servo-driven spike chain transport to forming station
- 700x700mm forming area
- Closed chamber zero-sag system
- IR ceramic sandwich heating (~260 kW)
- Price: 120,000 GBP ex-works
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "PF1-R-0707-X _ Machinecraft PF1 Quotation.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the PF1-R-0707-X quotation."""
    items = []

    # 1. PF1-R Series Overview
    items.append(KnowledgeItem(
        text="""PF1-R Series Roll Feeder Thermoforming Machine Overview:

The Machinecraft PF1-R Series is a heavy-gauge, single-station ROLL-SHEET 
thermoforming machine line designed for versatility and high performance.

KEY DIFFERENTIATOR FROM STANDARD PF1:
- Uses ROLL FORMAT raw material instead of cut sheets
- Ideal for LARGE SIZED PARTS with continuous material feed
- Spike chain material transport system (servo-driven)
- Pneumatic shot cutter/shear cuts material at start of cycle

MACHINE CONCEPT:
- Closed chamber design (area below forming is completely sealed/airtight)
- Zero-sag control using pulsated air blown in chamber below sheet
- Preblow capability for even wall thickness on male moulds
- Dual photocell system:
  * Preblow photocell: ABOVE the sheet
  * Sag photocell: BELOW the sheet (prevents sheet touching bottom heater)

ROLL FEEDER BENEFITS:
- Continuous production capability
- Reduced material handling (no individual sheet loading)
- Better material utilization (no cut sheet waste)
- Suitable for high-volume production runs
- Ideal for large parts that would be difficult to handle as cut sheets""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-R",
        summary="PF1-R series roll feeder machine overview with spike chain transport for large parts",
        metadata={
            "topic": "machine_overview",
            "series": "PF1-R",
            "material_type": "roll_format"
        }
    ))

    # 2. Technical Specifications
    items.append(KnowledgeItem(
        text="""PF1-R-0707-X Technical Specifications:

MACHINE MODEL: PF1-R-0707-X
(R = Roll feeder, 0707 = 700x700mm forming area, X = extended features)

FORMING CAPABILITIES:
- Forming Area (Max): 700 x 700 mm (Length × Depth)
- Max Stroke Z Direction: 400 mm
- Sheet Thickness Range: Typically 2 - 10 mm (material-dependent)

MATERIALS SUITED:
- PS (Polystyrene)
- ABS
- ASA
- ABS PMMA
- PC (Polycarbonate)
- PP (Polypropylene)
- PE-HD (High Density Polyethylene)
- TPO (Thermoplastic Olefin)
- And other thermoformable plastics

FRAME SYSTEM:
- Fixed Welded Frames (need to be changed when sheet size changes)
- Machine supplied with 1 frame at max aperture window size
- Additional frames can be ordered at extra cost

POWER REQUIREMENTS:
- Total Machine Connected Load: ~30 KW (excluding heaters)
- Heater Power: ~260 KW
- Compressed Air: ~6 bar (100 psi)

VACUUM SYSTEM:
- Vacuum Pump Capacity: ~40 m³/hr""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-R-0707-X",
        summary="PF1-R-0707-X specifications: 700x700mm forming area, 2-10mm thickness, 260kW heating",
        metadata={
            "topic": "specifications",
            "model": "PF1-R-0707-X",
            "forming_area_mm": "700x700",
            "stroke_mm": 400,
            "heater_power_kw": 260
        }
    ))

    # 3. Roll Feeder & Material Transport System
    items.append(KnowledgeItem(
        text="""PF1-R Roll Feeder and Spike Chain Material Transport System:

ROLL FEEDER SYSTEM:
- Accepts raw material in ROLL FORMAT
- Eliminates need for pre-cut sheet handling
- Continuous material feed for high-volume production
- Suitable for large parts that are difficult to handle as sheets

SPIKE CHAIN TRANSPORT SYSTEM:
- Material transport method: Chain Driven using Servo motors
- Spike chains grip the material edges
- Transports material from roll unwinder to forming station
- Servo drive allows precise control over:
  * Feed rate
  * Positioning accuracy
  * Start/stop timing
  * Material tension

ROLL CUTTING MECHANISM:
- Pneumatic Shot Cutter / Shear
- Located at START of cycle (before sheet clamp)
- Cuts material to length after forming
- Clean cut for finished part separation

MATERIAL FLOW SEQUENCE:
1. Material unwound from roll
2. Spike chains grip material edges
3. Servo-driven chains advance material to heating position
4. After heating: material advanced to forming station
5. Forming cycle completes
6. Pneumatic cutter shears formed part from roll
7. Finished part ejected/removed
8. Cycle repeats with continuous material feed

ADVANTAGES OF SPIKE CHAIN SYSTEM:
- Positive grip on material (no slippage)
- Works with various material thicknesses
- Maintains material tension during transport
- Servo control enables programmable indexing""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-R",
        summary="Roll feeder with servo-driven spike chain transport and pneumatic shot cutter",
        metadata={
            "topic": "material_transport",
            "transport_type": "spike_chain",
            "drive": "servo",
            "cutter": "pneumatic_shear"
        }
    ))

    # 4. Heating System
    items.append(KnowledgeItem(
        text="""PF1-R-0707-X Heating System Configuration:

OVEN CONFIGURATION:
- Sandwich Style: Top AND Bottom ovens (standard)
- Both ovens heat material simultaneously
- Reduces heating time compared to single-sided heating
- More uniform through-thickness temperature

HEATER TYPE:
- IR Ceramic Type heaters
- Long wave infrared for efficient plastic heating
- Durable construction for industrial use

HEATING ZONES & CONTROL:
- Individual Heater Control: 1 heating element connected to 1 SSR
- Plus Zone Control for grouping elements
- SSR (Solid State Relay) control
- Digital PID control via HMI
- Total Heater Power: Approximately 260 kW

HEATER OVEN MOVEMENT:
- Pneumatic Driven
- Special high-temperature cylinders
- Upper & Lower heater retraction
- 2-level safety system

SAG & PREBLOW CONTROL (During Heating):
- Closed chamber below sheet line (airtight)
- Pulsated air maintains sheet level
- Pneumatic cylinder system for air control
- Controllable via HMI by PLC
- Dual photocell system:
  * Sag photocell (below sheet): Prevents sheet touching bottom heater
  * Preblow photocell (above sheet): Controls bubble formation

PREBLOW PURPOSE:
- Critical for MALE MOULDS
- Creates even wall thickness in final part
- Pre-stretches material before mould contact""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-R-0707-X",
        summary="Sandwich IR ceramic heating 260kW with dual photocell sag/preblow control",
        metadata={
            "topic": "heating_system",
            "config": "sandwich",
            "heater_type": "IR_ceramic",
            "power_kw": 260,
            "control": "individual_SSR_PID"
        }
    ))

    # 5. Motion Systems & Drives
    items.append(KnowledgeItem(
        text="""PF1-R-0707-X Motion Systems and Drives:

SERVO-DRIVEN SYSTEMS (Precision):

1. Forming Platen Drive:
   - Servo Motor Driven
   - Allows control over acceleration/deceleration profiles
   - Programmable stroke, speed, and force
   - Soft-touch forming capability
   - Prevents tool/part damage

2. Plug Assist Drive:
   - Servo Motor Driven
   - Control over acceleration/deceleration profiles
   - Programmable depth and timing
   - Precise material pre-stretch control

3. Material Transport (Spike Chain):
   - Servo Motor Driven
   - Precise material indexing
   - Programmable feed lengths

PNEUMATIC-DRIVEN SYSTEMS (Robust):

1. Clamp Frame Drive:
   - Pneumatic using 2 cylinders
   - Rack & pinion mechanism
   - Reliable clamping action

2. Heater Oven Drive:
   - Pneumatic with special high-temp cylinders
   - Retracts heaters for forming access

3. Front Door:
   - Air cylinder operated
   - Opens for part removal/access

4. Roll Cutter:
   - Pneumatic shot cutter/shear
   - Fast, clean cuts

COOLING SYSTEM:
- Centrifugal Fans
- Capacity: 26 m³/hr each
- Quantity: 2 pieces
- Total cooling: 52 m³/hr airflow""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-R-0707-X",
        summary="Servo drives for platen, plug assist, transport; pneumatic for clamps, heaters, cutter",
        metadata={
            "topic": "motion_systems",
            "servo_systems": ["forming_platen", "plug_assist", "material_transport"],
            "pneumatic_systems": ["clamp_frame", "heater_oven", "front_door", "roll_cutter"]
        }
    ))

    # 6. Control System & Electrical
    items.append(KnowledgeItem(
        text="""PF1-R-0707-X Control System and Electrical Configuration:

HMI & PLC:
- PLC Controller: Mitsubishi Japan
- HMI: 10" color touchscreen
- Software developed alongside machine operators over 25 years
- User-friendly interface features:
  * Recipe storage and management
  * Heater zone control visualization
  * Timing parameters
  * Diagnostics and alarms
  * I/O status display

RECIPE MANAGEMENT:
- Ability to store recipes on SD card
- Recipe and program management
- Operator and Manager access levels with passcodes

CONNECTIVITY:
- Internet connectivity for remote monitoring
- VPN/Internet remote support capability (IoT module)
- Remote diagnostics and troubleshooting

SAFETY SYSTEMS:
- Emergency switches at operator area and control panel
- Appropriate interlocks for all motion systems
- Upper & Lower heater retraction: 2-level safety
- Light guards: Sick / PnF / Omron brands

ELECTRICAL PROTECTION:
- Overload protection for motors
- Fuse/MCB for heaters
- MCCB protection
- Overtravel protection on motion axes

PNEUMATIC SYSTEM:
- FRL (Filter-Regulator-Lubricator) unit
- Max feed pressure: 10 bar
- Operating pressure: 6 bar (controlled reduction)
- Working pressure monitoring""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-R-0707-X",
        summary="Mitsubishi PLC/10\" HMI with remote monitoring, recipe storage, multi-level safety",
        metadata={
            "topic": "control_system",
            "plc": "Mitsubishi",
            "hmi_size": "10_inch",
            "features": ["recipe_storage", "remote_monitoring", "diagnostics"]
        }
    ))

    # 7. Component Brands & Quality
    items.append(KnowledgeItem(
        text="""PF1-R-0707-X Component Brands (Premium Quality):

CONTROL & AUTOMATION:
- PLC, HMI & Servos: Mitsubishi Japan
- Pneumatics: Festo / SMC / Janatics
- Light Guard & Sensors: Sick / PnF / Omron

VACUUM & AIR HANDLING:
- Vacuum Pump: Busch / Becker (German quality)
- Cooling Fans: EBM Papst / Nicotra Gebhart

ELECTRICAL:
- Control Panel: Hoffman / Rittal
- Switch Gears: Eaton / Schneider
- Bus-Bar System: Rittal / Wohner

HEATING:
- Heater Elements: Ceramicx / Elstein / Stella
  (Premium IR ceramic heater manufacturers)

SAFETY:
- Safety Components: Euchner / Phoenix / Sick

MECHANICAL:
- Gearbox: Bonfiglioli / SEW
- Linear Rails: Hiwin / THK

QUALITY ASSURANCE:
- All components are premium international brands
- If any item unavailable due to lead time:
  * Similar quality/brand substituted
  * Client informed prior to substitution

This component selection ensures:
- Long machine life
- Reliable performance
- Global spare parts availability
- Professional service support""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-R-0707-X",
        summary="Premium component brands: Mitsubishi, Festo, Sick, Busch, Eaton, Hiwin",
        metadata={
            "topic": "component_brands",
            "plc": "Mitsubishi",
            "pneumatics": ["Festo", "SMC", "Janatics"],
            "vacuum": ["Busch", "Becker"],
            "rails": ["Hiwin", "THK"]
        }
    ))

    # 8. Commercial Terms
    items.append(KnowledgeItem(
        text="""PF1-R-0707-X Commercial Terms and Pricing:

PRICING:
- Machine Price: 120,000 GBP
- Price Basis: Ex-works Umargam, Gujarat, India
- Not Included: Packing, freight, insurance, on-site installation
  (Can be arranged at additional cost)

LEAD TIME:
- 6 to 7 months from date of advance
- Unless stated otherwise

PAYMENT TERMS:
- 50% advance with purchase order
- 50% balance against Factory Acceptance Test (FAT) approval
- Balance due prior to dispatch
- Payment method: Wire transfer per pro-forma invoice
- Ownership transfers upon full payment

WARRANTY:
- 1-year limited warranty from date of commissioning
- Covers manufacturing defects in mechanical and control components
- Exclusions: Consumables (heating elements, seals), wear-and-tear parts
- Extended warranty/service contracts available on request

QUOTATION VALIDITY:
- Valid for 8 days from date of issue
- Prices subject to change thereafter
- Configuration changes may result in revised quote

INSTALLATION & TRAINING:
- On-site commissioning provided
- Basic operator training included
- Travel and lodging for Machinecraft technician: Extra cost
- Client responsibility: Utilities (electricity, air) and test material

AFTER-SALES SUPPORT:
- Remote support via VPN/Internet (if IoT module included)
- On-site support visits available if remote resolution not possible
- Recommendation: Maintain stock of critical spare parts""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="PF1-R-0707-X",
        summary="PF1-R-0707-X priced at 120,000 GBP, 6-7 month lead time, 1-year warranty",
        metadata={
            "topic": "commercial_terms",
            "price_gbp": 120000,
            "lead_time_months": "6-7",
            "warranty_years": 1,
            "payment_advance": "50%"
        }
    ))

    # 9. Application Use Cases for Roll Feeder
    items.append(KnowledgeItem(
        text="""PF1-R Roll Feeder Machine - Ideal Applications:

WHEN TO CHOOSE ROLL FEEDER (PF1-R) OVER CUT SHEET (PF1-C):

1. LARGE PART PRODUCTION:
   - Parts too large or heavy to handle as cut sheets
   - Reduces manual material handling
   - Safer operation with heavy-gauge materials

2. HIGH VOLUME PRODUCTION:
   - Continuous material feed increases throughput
   - Reduced downtime for sheet loading
   - More efficient for long production runs

3. ROLL MATERIAL AVAILABILITY:
   - When raw material is supplied/preferred in roll format
   - Cost savings on pre-cut sheet purchasing
   - Direct from extrusion line integration possible

4. SPECIFIC MATERIAL TYPES:
   - Heavy gauge materials (2-10mm range)
   - Materials that are easier to handle in roll form
   - Flexible or semi-rigid materials

TYPICAL PART EXAMPLES:
- Large automotive interior panels
- Commercial vehicle trim panels
- Agricultural equipment covers
- Industrial equipment housings
- Large packaging components

SPIKE CHAIN ADVANTAGE:
- Positive grip prevents material slip
- Handles thicker materials reliably
- Consistent positioning every cycle
- Works with textured/embossed materials

QUOTATION CONTEXT:
- This quote was prepared for:
  * Prof. Massimiliano Barletta
  * Università degli Studi Roma Tre
  * Department of Industrial, Electronic and Mechanical Engineering
- Indicates: Research/academic application or industrial R&D""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="PF1-R",
        summary="Roll feeder ideal for large parts, high volume, heavy gauge materials with spike chain",
        metadata={
            "topic": "applications",
            "use_cases": ["large_parts", "high_volume", "heavy_gauge"],
            "materials": "2-10mm"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("PF1-R-0707-X Roll Feeder Quotation Knowledge Ingestion")
    print("Source: " + SOURCE_FILE)
    print("=" * 60)

    items = create_knowledge_items()

    print(f"\nCreated {len(items)} knowledge items:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.summary[:60]}...")

    ingestor = KnowledgeIngestor()
    results = ingestor.ingest_batch(items)

    print("\n" + "=" * 60)
    print("INGESTION RESULTS")
    print("=" * 60)

    print(f"  Total items processed: {results.total_processed}")
    print(f"  Items stored: {results.stored}")
    print(f"  Duplicates skipped: {results.duplicates}")
    print(f"  Qdrant main: {'✓' if results.qdrant_main else '✗'}")
    print(f"  Qdrant discovered: {'✓' if results.qdrant_discovered else '✗'}")
    print(f"  Mem0: {'✓' if results.mem0 else '✗'}")
    print(f"  JSON backup: {'✓' if results.json_backup else '✗'}")

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
