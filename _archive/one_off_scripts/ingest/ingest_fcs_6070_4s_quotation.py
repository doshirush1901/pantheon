#!/usr/bin/env python3
"""
Ingest FCS 6070-4S Form-Cut-Stack Machine Quotation

Comprehensive quote with full technical details for high-volume
inline thermoforming production (Form + Cut + Hole + Stack).

Key specs:
- 4 stations: Forming, Cutting, Holing, Stacking
- Tool size: 600 x 700 mm
- 150mm forming depth
- 30 cycles/min dry, 25 wet
- Mitsubishi PLC/Servo, Elstein heaters, Festo pneumatics
- Price: ₹1.75 CR (~$210K USD)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Quotation_ Machinecraft FCS 6070-4S.docx.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the FCS 6070-4S quotation."""
    items = []

    # 1. Machine Overview
    items.append(KnowledgeItem(
        text="""FCS 6070-4S - Form-Cut-Stack Thermoforming Machine Overview

MACHINE TYPE:
- 4-Station Inline Thermoformer (Forming → Cutting → Holing → Stacking)
- Fully automatic roll-fed production system
- High-volume plastic packaging applications
- Converts roll sheet to finished containers without manual handling

PRODUCTION CONCEPT:
Station 1: HEATING - Multi-zone IR oven heats sheet
Station 2: FORMING - Servo press with pressure forming (4 bar)
Station 3: CUTTING - Servo cutting press with steel rule die
Station 4: HOLING - Servo-driven holing press for additional features
Station 5: STACKING - Servo + pneumatic hybrid automatic stacker

KEY ADVANTAGES:
- Single continuous process from roll to stacked parts
- No manual handling between operations
- High throughput: up to 30 cycles/min dry, 25 cycles/min production
- Pressure forming capability for fine detail
- CE compliant, European safety standards
- Quick mold change (15-30 minutes)

TARGET APPLICATIONS:
- Food packaging containers
- Disposable cups, lids, trays
- Blister packs
- Clamshells
- Any high-volume thin-gauge thermoformed packaging

BUILT BY:
- Engineered and manufactured in-house by Machinecraft India
- CE certified for European markets
- Single-source responsibility""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="FCS6070-4S",
        summary="FCS 6070-4S: 4-station inline thermoformer (form-cut-hole-stack), roll-fed, 30 cpm",
        metadata={
            "topic": "machine_overview",
            "model": "FCS6070-4S",
            "stations": 4,
            "type": "inline_thermoformer"
        }
    ))

    # 2. Technical Specifications
    items.append(KnowledgeItem(
        text="""FCS 6070-4S Technical Specifications

FORMING AREA:
- Max Tool Size: 600 × 700 mm (net usable area)
- Max Forming Depth: 150 mm
- Max Sheet Width: 870 mm
- Sheet Thickness Range: 0.3 to 1.4 mm

FORMING CAPABILITY:
- Forming Air Pressure: Up to 4 bar
- Vacuum assisted forming
- Pressure + vacuum combined capability
- Suitable for fine detail and fast cycle

SPEED & PERFORMANCE:
- Max Dry Cycle: 30 cycles per minute (without sheet)
- Typical Wet Production: 25 cycles per minute average
- Note: Actual speed depends on material heating time and part design

POWER REQUIREMENTS:
- Heating Oven Load: ~60 kW (IR heaters)
- Total Connected Power: ~85 kW
- Power Supply: 400 VAC ±10%, 50 Hz, 3-Phase (European)

UTILITIES:
- Compressed Air: 6 bar supply, ~4 bar usage
- Customer must provide air compressor
- Chilled water required for mold cooling

MACHINE SIZE:
- Dimensions: Approx. 8.5 m × 2.2 m × 2.5 m (L × W × H)
- Weight: Approx. 8–10 Tons

DRIVE SYSTEMS:
- Forming Press: Servo motor driven (toggle press)
- Cutting Press: Servo motor driven (steel-rule die)
- Holing Press: Servo motor driven
- Stacking: Servo + Pneumatic hybrid
- Sheet Transport: Servo-controlled chain indexing""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="FCS6070-4S",
        summary="FCS 6070: 600x700mm tool, 150mm depth, 4 bar pressure, 85kW, 8.5m long, 8-10 tons",
        metadata={
            "topic": "specifications",
            "tool_size_mm": "600x700",
            "forming_depth_mm": 150,
            "sheet_width_mm": 870,
            "thickness_mm": "0.3-1.4",
            "pressure_bar": 4,
            "power_kw": 85,
            "cycles_per_min_dry": 30,
            "cycles_per_min_wet": 25
        }
    ))

    # 3. Key Components & Brands
    items.append(KnowledgeItem(
        text="""FCS 6070-4S Key Components and Brands

CONTROL & MOTION (Mitsubishi Electric - Japan):
- PLC: Mitsubishi high-performance programmable controller
- HMI: 15" color touchscreen (recipe storage, parameters)
- Servo Motors: All major axes (forming, cutting, indexing, stacking)
- Servo Drives: Precise control, repeatable positioning, fast cycles

HEATING SYSTEM (Elstein - Germany):
- IR Ceramic Heaters
- Multi-zone configuration for uniform heating
- Efficient and consistent heat distribution
- Energy efficient

PNEUMATICS (Festo - Germany):
- Cylinders, valves, air preparation units
- Sheet clamping, part ejectors, stacking mechanisms
- Reliable, fast operation
- Global spare parts availability

VACUUM SYSTEM (Busch/Becker - Germany):
- Heavy-duty vacuum pump
- Vacuum reservoir integrated
- For forming process and de-molding

SENSORS (Pepperl+Fuchs - Germany):
- Photoelectric sensors
- Precise sheet positioning
- Quality detection

SAFETY (Omron/Schneider - Japan/France):
- Safety interlocks and switches
- Light curtains on operator areas
- Emergency stops
- CE compliant safety systems

ELECTRICAL (Siemens/Schneider - Germany/France):
- Contactors, relays, motor protectors
- IEC and CE standard components

MECHANICAL (Global Sources):
- Gearboxes: Bonfiglioli (Italy) / SEW (Germany)
- Bearings: SKF (Sweden)
- Linear Guides: HIWIN (Taiwan)
- Frame: Machinecraft fabricated steel

WHY PREMIUM COMPONENTS:
- 24/7 industrial production reliability
- Global availability of spares
- Easy serviceability
- Long operational life
- Single-source Machinecraft responsibility""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="FCS6070-4S",
        summary="Components: Mitsubishi PLC/servo, Elstein IR heaters, Festo pneumatics, Busch vacuum",
        metadata={
            "topic": "components",
            "plc": "Mitsubishi",
            "servo": "Mitsubishi",
            "heaters": "Elstein",
            "pneumatics": "Festo",
            "vacuum": "Busch"
        }
    ))

    # 4. Scope of Supply & Features
    items.append(KnowledgeItem(
        text="""FCS 6070-4S Scope of Supply

INCLUDED IN DELIVERY:

1. MAIN MACHINE:
   - 4-station thermoformer (Forming + Cutting + Holing + Stacking)
   - Integrated on single base frame
   - All drives and mechanisms

2. HEATING OVEN:
   - Roll-fed sheet heating
   - Multi-zone IR heaters (Elstein Germany)
   - Adjustable heating zones
   - Precise temperature control

3. FORMING STATION:
   - Servo-driven forming press
   - Net forming area: 600 × 700 mm
   - Pressure forming up to 4 bar
   - Clamping frames and guide rods
   - 870mm sheet width capacity

4. CUTTING STATION:
   - Servo-driven cutting press
   - Steel rule die trimming
   - X-Y adjustment mechanism (motor driven)
   - Precise alignment capability

5. HOLING STATION:
   - Servo-driven holing press
   - For additional holes/features
   - 4th station capability

6. STACKING STATION:
   - Automatic stacking unit
   - Servo + pneumatic hybrid motion
   - Configurable: up-stacking or down-stacking
   - Adjustable for different product heights
   - Stack count programmable

7. SHEET FEEDING SYSTEM:
   - Chain-rail sheet transport
   - Servo-controlled indexing
   - Automatic roll unwind stand
   - Edge trim removal system (trim winder)
   - Programmable index length

8. CONTROL SYSTEM:
   - Free-standing control panel
   - Operator console
   - Mitsubishi PLC
   - 15" touchscreen HMI
   - Recipe storage and recall
   - Alarm diagnostics

9. VACUUM SYSTEM:
   - Busch vacuum pump integrated
   - Vacuum reservoir

10. PNEUMATIC SYSTEM:
    - All valves, cylinders, tubing
    - Air preparation unit (FRL)

11. SAFETY FEATURES:
    - CE compliant guarding
    - Safety doors with interlocks
    - Emergency stops
    - Light curtains on operator areas

12. DOCUMENTATION:
    - Operation manual (English)
    - Maintenance manual
    - Electrical schematics
    - Pneumatic diagrams
    - Parts list (illustrated)

13. TRAINING & FAT:
    - Factory Acceptance Test at Machinecraft
    - Customer inspection before dispatch
    - Personnel training during FAT

NOT INCLUDED (Customer Provides):
- Production molds/tooling
- Raw material (plastic roll)
- Compressed air supply (6 bar, dry, oil-free)
- Chilled water for mold cooling""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="FCS6070-4S",
        summary="FCS scope: 4 stations, heating, feeding, control, vacuum, safety, CE docs, FAT training",
        metadata={
            "topic": "scope_of_supply",
            "stations": ["forming", "cutting", "holing", "stacking"],
            "includes_fat": True,
            "ce_compliant": True
        }
    ))

    # 5. Quick Mold Change Procedure
    items.append(KnowledgeItem(
        text="""FCS 6070-4S Quick Mold Change Procedure

CHANGEOVER TIME: 15 to 30 minutes typical

STEP-BY-STEP PROCESS:

STEP 1: PREPARATION & SAFETY
- Stop machine completely
- Power off heating elements and drives
- Activate safety doors/interlocks
- Engage safety interlock system

STEP 2: RELEASE TOOLING
- Unlock pneumatic mold clamps via control panel
- Quick-release system activation
- Disconnect utility couplings:
  * Air quick-connect fittings
  * Water quick-connect fittings
- Easy-disconnect couplers provided

STEP 3: REMOVE EXISTING MOLD
- Use integrated mold lifting provisions OR
- Use mold handling trolley
- Slide mold from forming/cutting station guides
- Smooth withdrawal onto trolley

STEP 4: INSERT NEW MOLD
- Position new mold onto tooling guides
- Precision alignment pins ensure accurate positioning
- Slide until fully aligned against stops
- X and Y axis alignment automatic

STEP 5: LOCK & RECONNECT
- Activate pneumatic quick-lock from HMI
- Mold clamped securely within seconds
- Reconnect air lines (quick-connect)
- Reconnect water lines (quick-connect)
- Verify proper seating and sealing

STEP 6: ALIGNMENT & ADJUSTMENT
- X-Y position adjustment via motorized controls
- Electronic fine-tuning from control panel
- Mold height adjustment via motorized vertical
- Stroke parameters via HMI
- Match mold specifications precisely

STEP 7: CONFIRMATION & RESTART
- Visual alignment confirmation
- Digital readout verification on HMI
- Re-enable safety interlocks
- Power systems on
- Select/confirm mold-specific recipe
- Initiate production run

DESIGN FEATURES FOR QUICK CHANGE:
- Fast mold clamps (pneumatic)
- Quick-connect utility couplings
- Precision alignment pins
- Motorized adjustment axes
- Recipe storage for instant recall
- Intuitive, safe, rapid procedure""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="FCS6070-4S",
        summary="FCS mold change: 15-30 min, pneumatic clamps, quick-connect, motorized X-Y-Z adjust",
        metadata={
            "topic": "mold_change",
            "changeover_minutes": "15-30",
            "features": ["pneumatic_clamps", "quick_connect", "motorized_adjustment"]
        }
    ))

    # 6. Commercial Terms & Pricing
    items.append(KnowledgeItem(
        text="""FCS 6070-4S Commercial Terms and Pricing (Nov 2025)

PRICING:
- Base Price: INR 1.75 Crore (₹1,75,00,000)
- Equivalent: ~$210,000 USD
- Basis: Ex-Works India (Mumbai)
- Includes seaworthy export packing

NOT INCLUDED:
- Taxes (GST/VAT/duties)
- Shipping costs
- Insurance
- Import clearance at destination
- Production molds/tooling

DELIVERY:
- Lead Time: 20-24 weeks from order + advance
- Includes: Design finalization, assembly, testing, prep for shipment
- Terms: Ex-Works (EXW) Machinecraft Factory, India
- Buyer arranges freight pickup
- Machinecraft assists with loading

PAYMENT TERMS:
- 40% advance with Purchase Order
- 60% upon completion of manufacturing and FAT
- Balance due before dispatch
- Alternative terms negotiable

QUOTATION VALIDITY:
- Valid for 60 days from issue
- After 60 days: Subject to revision (material costs, exchange rates)

INSTALLATION & COMMISSIONING:
- Included: Up to 5 working days on-site supervision
- 2 Machinecraft technicians deputed
- Travel/visa/lodging: Charged at actual to buyer
- Buyer provides: Power, air, water, molds

DOCUMENTATION:
- Technical drawings
- Manuals
- CE compliance declaration
- CE marking nameplate on machine

CERTIFICATION:
- CE marking included
- Other certifications (UL etc.): Quoted separately if needed

COMPARISON CONTEXT:
- FCS 6070-4S is high-volume inline machine
- Compare to PF1 (cut-sheet) or smaller FCS models
- Best for packaging applications needing >20 cycles/min
- ROI advantage over multiple standalone machines""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="FCS6070-4S",
        summary="FCS 6070-4S: ₹1.75 Cr (~$210K) EXW, 20-24 weeks, 40/60 payment, 5 days commissioning",
        metadata={
            "topic": "pricing",
            "price_inr": 17500000,
            "price_usd": 210000,
            "lead_weeks": "20-24",
            "payment_advance": 40,
            "payment_balance": 60,
            "commissioning_days": 5
        }
    ))

    # 7. Warranty & After-Sales
    items.append(KnowledgeItem(
        text="""FCS 6070-4S Warranty and After-Sales Support

WARRANTY:
- Duration: 12 months standard
- Start: From dispatch date (Ex-Works) or factory acceptance
- Coverage: Manufacturing defects
- Includes: Replacement or repair of defective parts (free)

NOT COVERED:
- Wear-and-tear parts (heaters, belts, seals, cutting knives)
- Consumables
- Damage from improper use
- Lack of maintenance
- User modifications

WARRANTY CONDITIONS:
- Operate per provided instructions
- Regular maintenance required
- Lubrication, cleaning, inspection per manual
- Prompt warranty claims attended to
- Parts shipped or service engineers dispatched

AFTER-SALES SUPPORT:

1. SPARE PARTS:
   - Full range available for 10+ years
   - Common parts stocked for quick dispatch
   - Spare part kits available
   - Can purchase with machine or as needed

2. TECHNICAL SUPPORT:
   - Email and phone support
   - Remote troubleshooting assistance
   - On-site visits available (service rates apply)

3. SERVICE NETWORK:
   - For Europe: Local service partner coordination
   - Indian engineers available for maintenance visits
   - Preventive maintenance contracts available post-warranty

4. TRAINING & UPGRADES:
   - Additional training sessions available
   - New operator training
   - Advanced maintenance training
   - Software upgrades provided when developed
   - Control system enhancements available

MACHINECRAFT COMMITMENT:
- Support through installation, ramp-up, and production
- Goal: Maximum production uptime
- Single-source solution (branding, docs, software)
- Long-term partnership approach""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="FCS6070-4S",
        summary="FCS warranty: 12 months, spares 10+ years, remote support, service network",
        metadata={
            "topic": "warranty_support",
            "warranty_months": 12,
            "spare_parts_years": 10,
            "support": ["remote", "on-site", "training"]
        }
    ))

    # 8. FCS vs Other Machinecraft Machines Comparison
    items.append(KnowledgeItem(
        text="""FCS 6070-4S vs Other Machinecraft Machines - Selection Guide

FCS 6070-4S IS IDEAL FOR:
- High-volume thin-gauge packaging
- Roll-fed material (continuous operation)
- 0.3-1.4mm sheet thickness
- Products needing inline stacking
- Cycles >20/min required
- Food packaging, cups, trays, lids, clamshells

PF1 SERIES IS BETTER FOR:
- Heavy gauge thermoforming (2-12mm)
- Cut-sheet operation
- Large single parts (automotive, industrial)
- Flexible production runs
- Technical parts requiring precision
- Lower cycle rates acceptable

AM SERIES IS BETTER FOR:
- Entry-level production
- Smaller forming areas
- Budget-conscious operations
- Pressure forming capability (AM-P)
- Learning/training environments

FCS 6070-4S SPECIFICATIONS COMPARISON:

| Feature | FCS 6070-4S | PF1-X | AM-P |
|---------|-------------|-------|------|
| Sheet Type | Roll | Cut-sheet | Cut-sheet |
| Thickness | 0.3-1.4mm | 2-12mm | 2-10mm |
| Tool Size | 600x700mm | Varies | 500x600mm |
| Depth | 150mm | Up to 800mm | 60mm |
| Cycles/min | 25-30 | 1-4 | 2-6 |
| Inline Stack | Yes | No | No |
| Price Range | ₹1.75Cr | ₹45L-1Cr | ₹35-65L |

WHEN TO RECOMMEND FCS 6070-4S:
- Customer makes packaging products
- Volume exceeds 500,000 parts/month
- Material is thin gauge (<1.5mm)
- Inline production required
- Wants complete forming-to-stacking automation
- Has roll material supply chain

BUNDLE OPPORTUNITIES:
- FCS + MC-4A for parts needing CNC trimming
- Multiple FCS lines for very high volume
- FCS for packaging + PF1 for industrial parts""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="FCS6070-4S",
        summary="FCS 6070 for high-volume thin gauge; PF1 for heavy gauge cut-sheet; AM for entry-level",
        metadata={
            "topic": "machine_selection",
            "best_for": "thin_gauge_packaging",
            "vs": ["PF1", "AM"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("FCS 6070-4S Form-Cut-Stack Machine Quotation Ingestion")
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
