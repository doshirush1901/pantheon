#!/usr/bin/env python3
"""
Ingest MC-4A 4-Axis CNC Router Quotation

4-axis CNC machine for thermoforming part trimming application.
Usually sold alongside PF1 machines, mainly in Indian market.

Key specs:
- Working size: 3250 x 2250 x 750 mm
- 9KW spindle with auto tool change
- 8 tool magazine
- YASKAWA servos
- Price: ₹32 Lakhs (~$38K USD)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Maachinecraft 4 Axis Offer for MC-4A-15125.docx.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the 4-axis CNC router quotation."""
    items = []

    # 1. Machine Overview
    items.append(KnowledgeItem(
        text="""MC-4A Series - 4-Axis CNC Router for Thermoforming Part Trimming

PRODUCT CATEGORY:
- 4-Axis CNC Trimming/Routing Machine
- Post-process equipment for thermoformed parts
- Complementary product sold alongside PF1 machines

PRODUCT LAUNCH:
- Launched at K2022 Show, Düsseldorf, Germany (October 2022)
- Newly designed by Machinecraft

PRIMARY APPLICATION:
- Trimming thermoformed parts
- Cutting edges and openings
- Routing holes and features
- Finishing thermoformed components

WHY 4-AXIS FOR THERMOFORMING:
- Thermoformed parts have 3D contours
- 4th axis (±90° spindle rotation) follows part geometry
- Can trim angled edges and undercuts
- Better edge quality on formed shapes
- Single setup for complex parts

TYPICAL WORKFLOW:
1. Thermoform part on PF1 machine
2. Load part onto MC-4A CNC router
3. CNC trims flash, cuts holes, finishes edges
4. Finished part ready for assembly/shipping

TARGET MARKET:
- Primarily Indian market
- Sold as package with PF1 machines
- Also available standalone for existing thermoformers""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="MC-4A",
        summary="MC-4A: 4-axis CNC router for trimming thermoformed parts, sold with PF1 machines",
        metadata={
            "topic": "machine_overview",
            "series": "MC-4A",
            "application": "thermoform_trimming",
            "launch": "K2022"
        }
    ))

    # 2. Technical Specifications
    items.append(KnowledgeItem(
        text="""MC-4A-2515 Technical Specifications

MODEL: MC-4A-2515
Working Size: 3250 x 2250 x 750 mm (X × Y × Z)

SPINDLE:
- Power: 9KW air cooling
- Speed: 0-24,000 RPM
- Voltage: 220V or 380V, 400Hz
- Auto Tool Changing capability
- Tool Holder: ISO30 Taper (international standard)
- Collet: ER32, max 20mm diameter tools

4TH AXIS:
- Spindle rotation: ±90 degrees
- Allows angled cuts and contour following
- Essential for trimming 3D thermoformed parts

TOOL MAGAZINE:
- Capacity: 8 tools
- Location: Arranged at back of table
- High quality tool holders
- Automatic tool change

MOTION SYSTEM:
- Servo Motors: YASKAWA (Japanese)
- Y-axis: 750W servo
- Z-axis: 750W servo
- X-axis: 850W servo
- Reducers: Taiwan made

TRANSMISSION:
- Linear Guide Rails: 25mm width for X, Y, Z axes
- X & Y axes: 2M Helical gear and rack transmission
- Z-axis: TBI ballscrews (Taiwan)

LUBRICATION:
- Automatic centralized lubrication system
- Lubricates guide rails and ballscrews automatically

TABLE:
- T-slot table for fixture clamping
- Allows part alignment during cutting""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="MC-4A-2515",
        summary="MC-4A-2515: 3250x2250x750mm, 9KW spindle, 8 tools, YASKAWA servos, ±90° 4th axis",
        metadata={
            "topic": "specifications",
            "model": "MC-4A-2515",
            "working_size_mm": "3250x2250x750",
            "spindle_kw": 9,
            "tool_capacity": 8,
            "servo_brand": "YASKAWA"
        }
    ))

    # 3. Control System & Features
    items.append(KnowledgeItem(
        text="""MC-4A Control System & Features

CONTROL SYSTEM: Syntec
- Advanced open architecture CNC controller
- Built-in high-performance industrial computer
- 10.4-inch LCD screen
- Built-in PLC (Programmable Logic Controller)
- USB interface
- Compact Flash Card reading device

CAPABILITIES:
- Servo axis control
- Spindle control
- MPG axis control
- Program storage and recall

OPERATOR INTERFACE:
- Hand-held Pendant CNC MPG (Manual Pulse Generator)
- Also called Handwheel
- Functions:
  * Set working origin
  * Position fine-tuning
  * Manual or continuous jogging
  * Break-inserting actions

DUST COLLECTION SYSTEM:
- Integrated dust collector
- Blower Motor: 3KW
- Air Intake: 2,300 m³/hour
- Air Speed: 25 meters/second
- Components:
  * Dust hood on spindle
  * Dust hose
  * Dust bag collector

WHY DUST COLLECTION MATTERS:
- Thermoforming trimming generates plastic dust
- Clean working environment
- Longer machine lifespan
- Healthier workforce
- Dust brush on spindle vacuums debris immediately

SAFETY:
- Emergency stops
- Enclosed work area option
- Interlocks for tool change""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="MC-4A",
        summary="Syntec control, 10.4\" LCD, MPG pendant, 3KW dust collector 2300m³/hr",
        metadata={
            "topic": "control_features",
            "controller": "Syntec",
            "screen_size": "10.4 inch",
            "dust_collector_kw": 3,
            "air_intake_m3hr": 2300
        }
    ))

    # 4. Pricing
    items.append(KnowledgeItem(
        text="""MC-4A-2515 Pricing (June 2023)

BASE MACHINE PRICE:
- Price: ₹32,00,000 (Thirty Two Lakhs INR)
- Equivalent: ~$38,000 USD (approximate)
- Basis: Ex-works Mira Road, India

ADDITIONAL COSTS:
- Packing Charges: 1% extra
- Transportation: Extra (quote separately)
- GST: Extra (18%)

TOTAL ESTIMATED COST (India):
- Base: ₹32,00,000
- Packing (1%): ₹32,000
- GST (18%): ₹5,76,000
- Subtotal: ₹38,08,000 + transport
- Approximately ₹40 Lakhs delivered (~$48K USD)

COMMERCIAL TERMS:
- Delivery: 90 days from advance payment
- Payment: 50% advance with order
- Balance: 50% after demo at Machinecraft, before dispatch

DEMO REQUIREMENT:
- Machine demonstrated at Machinecraft facility
- Customer inspects before final payment
- Ensures satisfaction before shipping

COMPARISON CONTEXT:
- Entry-level industrial 4-axis CNC
- Competitive pricing for Indian market
- Suitable for thermoforming operations
- Often bundled with PF1 machines for complete solution

BUNDLE OPPORTUNITY:
When sold with PF1 machine:
- PF1 + MC-4A = Complete thermoforming cell
- Forming + Trimming in one package
- Attractive bundle pricing available""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="MC-4A-2515",
        summary="MC-4A-2515: ₹32L ex-works (~$38K), 90 days delivery, 50/50 payment with demo",
        metadata={
            "topic": "pricing",
            "base_price_inr": 3200000,
            "base_price_usd": 38000,
            "delivery_days": 90,
            "packing_percent": 1
        }
    ))

    # 5. Integration with PF1 Machines
    items.append(KnowledgeItem(
        text="""MC-4A Integration with PF1 Thermoforming Machines

COMPLETE THERMOFORMING CELL CONCEPT:

STEP 1: FORMING (PF1 Machine)
- Plastic sheet heated and formed
- Part has rough edges (flash)
- Holes and cutouts not yet made
- Part removed from mold

STEP 2: TRIMMING (MC-4A Router)
- Formed part loaded onto CNC
- Fixtured on T-slot table
- CNC program executes:
  * Trim flash from edges
  * Cut holes and openings
  * Route channels or features
  * Finish edges to spec

STEP 3: FINISHED PART
- Ready for assembly or shipping
- No manual trimming required
- Consistent quality

WHY BUNDLE PF1 + MC-4A:

1. COMPLETE SOLUTION:
   - Customer gets forming + finishing
   - Single supplier responsibility
   - Integrated workflow

2. WORKFLOW OPTIMIZATION:
   - Parts flow from PF1 to MC-4A
   - Minimal work-in-progress
   - Consistent cycle times

3. QUALITY CONSISTENCY:
   - CNC trimming is repeatable
   - No operator variation
   - Better edge finish than manual

4. COST EFFICIENCY:
   - Bundle pricing advantage
   - Reduced labor for trimming
   - Faster throughput

SIZING COMPATIBILITY:
- MC-4A-2515 working area: 3250 x 2250 mm
- Suitable for parts from PF1 machines up to ~3000 x 2000 mm
- Covers most PF1 Classic and PF1-X models

INDIAN MARKET FOCUS:
- Labor cost advantage still exists in India
- But CNC trimming provides:
  * Quality consistency
  * Faster production
  * Less skilled operator needed
  * Scalability""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="MC-4A",
        summary="PF1 + MC-4A bundle: complete thermoforming cell, forming + CNC trimming solution",
        metadata={
            "topic": "pf1_integration",
            "workflow": ["forming", "trimming", "finished"],
            "bundle_benefit": "complete_solution"
        }
    ))

    # 6. Key Components Summary
    items.append(KnowledgeItem(
        text="""MC-4A Key Components & Brands

MOTION COMPONENTS:
- Servo Motors: YASKAWA (Japan) - Premium industrial brand
- Reducers: Taiwan made
- Linear Rails: 25mm width (robust for routing forces)
- Ballscrews: TBI (Taiwan) - Z-axis
- Transmission: Helical gear and rack (X, Y axes)

SPINDLE:
- Power: 9KW (strong for plastic routing)
- Cooling: Air cooled (simpler maintenance)
- Speed: 0-24,000 RPM (wide range)
- Tool Interface: ISO30 taper (standard)
- Collet: ER32 (up to 20mm tools)

CONTROL:
- Controller: Syntec (Taiwan)
- Display: 10.4" LCD
- Interface: USB, CF card
- Pendant: MPG handwheel included

TOOL SYSTEM:
- Magazine: 8 position
- Change: Automatic
- Holder: ISO30 standard

DUST COLLECTION:
- Blower: 3KW motor
- Capacity: 2,300 m³/hr
- Speed: 25 m/s airflow

TABLE:
- Type: T-slot
- Purpose: Fixture mounting
- Material: Cast iron or aluminum

BUILD QUALITY:
- Frame: Heavy steel construction
- Suitable for: Industrial production
- Environment: Factory floor

ORIGIN:
- Designed by Machinecraft
- Manufactured in India
- Components sourced globally""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="MC-4A",
        summary="Components: YASKAWA servos, TBI ballscrews, Syntec control, 9KW spindle, ISO30",
        metadata={
            "topic": "components",
            "servo": "YASKAWA",
            "controller": "Syntec",
            "ballscrew": "TBI",
            "spindle_kw": 9
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("MC-4A 4-Axis CNC Router Quotation Ingestion")
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
