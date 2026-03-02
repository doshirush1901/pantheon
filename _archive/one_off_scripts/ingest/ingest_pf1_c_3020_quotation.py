#!/usr/bin/env python3
"""
Ingest PF1-C-3020 Quotation

Large format cut-sheet thermoforming machine quotation.
Key specs: 3000x2000mm forming area, 85 Lakhs INR (~$100K USD equivalent)
Configuration: Classic/base config with manual loading, fixed frames, pneumatic drives.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "PF1-C-3020 _ Machinecraft PF1 Quotation.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the PF1-C-3020 quotation."""
    items = []

    # 1. Machine Overview & Positioning
    items.append(KnowledgeItem(
        text="""PF1-C-3020 Machine Overview

MODEL: PF1-C-3020
- C = Cut-sheet (manual loading)
- 3020 = 3000mm x 2000mm forming area

SERIES POSITIONING:
The PF1 Series is a heavy-gauge, single-station cut-sheet thermoforming 
machine line designed for versatility and high performance.

KEY DESIGN FEATURES:
- Robust closed-chamber design
- Prevents sheet sag via pre-blow air pressure control
- Superior forming quality on thick materials
- Precision forming for thermoplastic sheets (2-12mm thick)

TARGET APPLICATIONS:
- Automotive parts
- Aerospace components
- Industrial applications
- Commercial products
- Applications demanding excellent detail and consistency

CONSTRUCTION:
- Heavy-duty steel frame
- Precision motion components
- Stability and durability focused
- Modern PLC control with intuitive HMI touchscreen

CLASSIC CONFIGURATION INCLUDES:
- Sandwich heating ovens (top & bottom)
- Ceramic infrared elements
- Solid-state temperature control
- Pneumatic-powered forming platen
- Manual sheet loading
- Fixed clamp frames
- Single-stage vacuum system
- Centrifugal cooling fans""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-C-3020",
        summary="PF1-C-3020: Large format 3000x2000mm cut-sheet thermoformer, classic config",
        metadata={
            "topic": "machine_overview",
            "model": "PF1-C-3020",
            "forming_area_mm": "3000x2000",
            "type": "cut_sheet"
        }
    ))

    # 2. Technical Specifications
    items.append(KnowledgeItem(
        text="""PF1-C-3020 Technical Specifications

FORMING CAPABILITIES:
- Machine Model: PF1-C-3020
- Forming Area (Max): 3000 x 2000 mm (Length × Depth)
- Max Stroke Z Direction: 800 mm
- Sheet Thickness Range: Typically 2 – 10 mm (material-dependent)

FRAME SYSTEM:
- Type: Fixed Welded Frames
- Supplied with: 1 frame at max aperture window size
- Frame change required when sheet size changes
- Additional frames: Available at extra cost
- Frame change time: 10-20 minutes (operator dependent)

SHEET HANDLING:
- Loading/Unloading: Manual

HEATING SYSTEM:
- Configuration: Sandwich (Top & Bottom ovens)
- Heater Type: IR Ceramic
- Zone Control: Individual heater control (2 elements to 1 SSR)
- Control Method: SSR and digital PID control via HMI
- Heater Power: Approximately 260 kW

VACUUM SYSTEM:
- Vacuum Pump Capacity: ~300 m³/hr
- Note: Large capacity for 3000x2000mm forming area

PNEUMATICS:
- Compressed Air Requirement: ~6 bar (100 psi)

MOTION SYSTEMS (ALL PNEUMATIC):
- Forming Platen Drive: 4 cylinders with rack & pinion
- Plug Assist Drive: 1 cylinder, manual height adjustment
- Clamp Frame Drive: 2 cylinders with rack & pinion
- Heater Oven Drive: Special high-temp cylinders

COOLING:
- System: Centrifugal Fans
- Capacity: 26 m³/hr each × 8 pieces = 208 m³/hr total

CONTROL:
- PLC Controller with 7" color touchscreen HMI
- Features: Recipe storage, heater zone control, timing, diagnostics

ELECTRICAL:
- Total Machine Connected Load: ~280 kW

DOOR:
- Front Door: Turnable locks for manual locking

SAG CONTROL:
- Preblow bubble for male tools
- Sheet flatness control during heating
- Light sensors monitor sheet level
- Closed chamber enables zero-sag operation""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-C-3020",
        summary="PF1-C-3020 specs: 800mm stroke, 300m³/hr vacuum, 260kW heaters, 280kW total load",
        metadata={
            "topic": "specifications",
            "forming_area_mm": "3000x2000",
            "stroke_mm": 800,
            "vacuum_m3hr": 300,
            "heater_power_kw": 260,
            "total_load_kw": 280,
            "cooling_fans": 8
        }
    ))

    # 3. Pricing
    items.append(KnowledgeItem(
        text="""PF1-C-3020 Pricing (February 2026)

MACHINE PRICE:
- Price: 85 Lakhs INR (₹85,00,000)
- Equivalent: ~$100,000 USD (approximate)
- Basis: Ex-works Umargam, Gujarat, India

LEAD TIME:
- Standard: 4 months from date of advance
- Note: Unless stated otherwise

WHAT'S INCLUDED IN PRICE:
- Complete PF1-C-3020 machine
- 1 fixed frame (max aperture size)
- PLC controller with 7" HMI
- Sandwich IR ceramic heating system
- Vacuum system (300 m³/hr)
- Pneumatic motion systems
- Cooling fans (8 units)
- Standard documentation

NOT INCLUDED (Extra Cost):
- Packing
- Freight
- Insurance
- On-site installation
- Additional frames for different sheet sizes
- Travel/lodging for Machinecraft technician

PRICE PER SQ METER FORMING AREA:
- Forming area: 3000 × 2000 = 6 sq meters
- Price per sq meter: ₹14.17 Lakhs (~$16,667 USD/sq.m)

COMPARISON CONTEXT:
The PF1-C-3020 is a LARGE format machine.
- 6 sq meter forming area
- Suitable for very large parts (automotive panels, aerospace components)
- Classic config keeps cost lower than X-series""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="PF1-C-3020",
        summary="PF1-C-3020 price: 85 Lakhs INR (~$100K USD), 4 month lead time, ex-works",
        metadata={
            "topic": "pricing",
            "price_inr": 8500000,
            "price_usd_approx": 100000,
            "lead_time_months": 4,
            "incoterms": "ex-works",
            "price_per_sqm_inr": 1417000
        }
    ))

    # 4. Commercial Terms
    items.append(KnowledgeItem(
        text="""PF1-C-3020 Commercial Terms & Conditions

PAYMENT TERMS:
- Advance: 50% with purchase order
- Balance: 50% against Factory Acceptance Test (FAT) approval
- Timing: Balance due prior to dispatch
- Method: Wire transfer per pro-forma invoice
- Ownership: Transfers upon full payment

DELIVERY:
- Incoterms: Ex-works (Umargam, Gujarat, India)
- Not included: Packing, freight, insurance, on-site installation
- Optional: Can be arranged at additional cost

INSTALLATION & TRAINING:
- Included: On-site commissioning
- Included: Basic operator training
- Extra cost: Travel and lodging for Machinecraft technician
- Client responsibility: Utilities (electricity, air) and test material

WARRANTY:
- Duration: 1 year limited warranty from commissioning date
- Covers: Manufacturing defects in mechanical and control components
- Excludes: Consumables (heating elements, seals), wear-and-tear parts
- Extended warranty: Available on request

QUOTATION VALIDITY:
- Valid: 8 days from date of issue
- After expiry: Prices subject to change
- Configuration changes: May result in revised quote

AFTER-SALES SUPPORT:
- Remote support: Via VPN/Internet (if IoT module included)
- Spare parts: Client recommended to maintain critical spares stock
- On-site support: Available if remote resolution not possible

FACTORY LOCATION:
- Production: Plot 92, Umbergaon Station-Dehri Rd, Valsad, Gujarat 396170, India
- Office: 505, Palm Springs, Link Road, Malad (W), Mumbai 400064, India""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="PF1-C-3020",
        summary="Terms: 50% advance, 50% FAT, 1-year warranty, 8-day quote validity",
        metadata={
            "topic": "commercial_terms",
            "payment_advance": "50%",
            "payment_balance": "50% at FAT",
            "warranty_years": 1,
            "quote_validity_days": 8
        }
    ))

    # 5. Configuration Comparison (Classic vs Upgrades)
    items.append(KnowledgeItem(
        text="""PF1-C-3020 Classic Configuration vs Available Upgrades

THIS QUOTE IS FOR CLASSIC (BASE) CONFIGURATION:

CLASSIC CONFIG (QUOTED):
- Sheet Loading: Manual
- Clamp Frames: Fixed welded (1 included)
- Platen Drive: Pneumatic (4 cylinders)
- Plug Assist: Pneumatic (1 cylinder, manual height)
- Heaters: IR Ceramic sandwich
- Heater Control: 2 elements per SSR
- Vacuum: Single-stage 300 m³/hr
- HMI: 7" touchscreen
- Front Door: Manual locks

POTENTIAL UPGRADES (Additional Cost):

Sheet Handling Upgrades:
- Automatic sheet loader (servo-driven)
- Automatic unloader

Frame System Upgrades:
- Universal clamping frame (servo-driven adjustment)
- Multiple frame sets for different sheet sizes

Drive System Upgrades:
- Servo-driven forming platen (precision, soft-touch)
- Servo-driven plug assist (programmable profiles)

Heating Upgrades:
- IR Quartz heaters (faster response)
- Halogen heaters (quickest response)
- 1:1 SSR control (individual element control)
- Pyrometer control (real-time temp monitoring)

Vacuum Upgrades:
- Multi-step vacuum control
- Larger vacuum capacity

Control Upgrades:
- Larger HMI (10" or 15")
- IoT connectivity module
- Remote monitoring capability

WHY CLASSIC CONFIG:
- Lower initial investment
- Suitable for consistent part sizes
- Manual operation acceptable
- Budget-conscious operations
- Entry point for thermoforming""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-C-3020",
        summary="Classic config: manual loading, fixed frames, pneumatic drives - upgrades available",
        metadata={
            "topic": "configuration",
            "config_type": "classic",
            "loading": "manual",
            "frames": "fixed",
            "drives": "pneumatic"
        }
    ))

    # 6. Frame Change Considerations
    items.append(KnowledgeItem(
        text="""PF1-C-3020 Fixed Frame System - Operational Considerations

STANDARD FIXED CLAMP FRAMES:

How They Work:
- Hold plastic sheet by edges during forming
- Fixed-size frames matched to sheet dimensions
- Frame change required when switching sheet sizes

FRAME CHANGE PROCESS:
1. Loosen frame segment fasteners
2. Slide segments to new positions
3. Re-tighten multiple segments on each side
4. Verify alignment

FRAME CHANGE TIME:
- Typical: 10-20 minutes
- Factors: Size change magnitude, operator experience

ADVANTAGES OF FIXED FRAMES:
- Robust construction
- Simple mechanism
- Lower cost than universal frames
- Reliable clamping

DISADVANTAGES:
- Manual adjustment = downtime
- Time needed when switching sheet sizes
- Less flexible for varied production

WHEN FIXED FRAMES WORK WELL:
- Consistent part sizes in production
- Limited sheet size variations
- Single product runs
- Budget-conscious operations

WHEN TO CONSIDER UNIVERSAL FRAMES:
- Frequent sheet size changes
- Multiple products on same machine
- High changeover frequency
- Time = money priority

ADDITIONAL FRAMES:
- Extra frames can be ordered at additional cost
- Specify sheet sizes when ordering
- Pre-set frames reduce changeover time""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="PF1-C-3020",
        summary="Fixed frames: 10-20min changeover, robust but manual, best for consistent sizes",
        metadata={
            "topic": "frame_system",
            "frame_type": "fixed_welded",
            "changeover_time_min": "10-20",
            "included_frames": 1
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("PF1-C-3020 Quotation Ingestion")
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
