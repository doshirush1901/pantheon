#!/usr/bin/env python3
"""
Ingest PF1 1015 All Options Quotation

Comprehensive quotation showing all available options for PF1 machines.
Useful for understanding what customers can configure and typical choices.

Key data:
- Base machine: ₹60 Lakhs
- All options detailed with individual pricing
- Technical explanations for each option
- Time savings quantified
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "PF1 1015 all options format Machinecraft INR.docx.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the PF1 1015 all options quotation."""
    items = []

    # 1. Machine Overview & Base Specs
    items.append(KnowledgeItem(
        text="""PF1-1015 Base Machine Overview

MODEL: PF1-1015 (PF1 Series)
FORMING AREA: 1500 x 1000 mm (X × Y)
MAX TOOL HEIGHT: 400 mm (Z)

BASE MACHINE SPECIFICATIONS:
- Forming Area Adjustment: Fixed Window Frames
- Tool Loading: Using Forklift
- Tool Clamping: Using Bolts
- Sheet Loading: Manual
- Part Unloading: Manual
- Heater Elements: Infrared Ceramic (Long-Wave)
- Heater Control: SSR (Solid State Relay)
- IR Probe for Heating: Yes (included)
- Cooling System: Centrifugal Fans
- IR Probe for Cooling: Yes (included)
- Vacuum Pump: Oil Rotary Vane Type

POWER & VACUUM:
- Total Heater Load: 50 KW
- Total Connected Power: 60 KW
- Vacuum Pump Capacity: 100 m³/hr
- Vacuum Tank: 1000 liters

BASE MACHINE MOVEMENTS (Default - Pneumatic):
- Sheet Clamping: Pneumatic (air cylinders)
- Heater Ovens: Pneumatic (air cylinders)
- Lower Table: Pneumatic (air cylinders)
- Upper Table: Pneumatic (air cylinders)

BASE PRICE: ₹60 Lakhs (~$72,000 USD)

SAFETY INCLUDED:
- Light Guard
- Front Door Safety Switch
- Interlocks
- Emergency switches at operator area
- Overload protection for motors
- Fuse/MCB for heaters, MCCB
- Overtravel protection""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-1015",
        summary="PF1-1015 base: 1500x1000mm, 400mm Z, 60KW, ₹60L; pneumatic movements, manual ops",
        metadata={
            "topic": "base_machine",
            "model": "PF1-1015",
            "forming_area_mm": "1500x1000",
            "base_price_inr": 6000000,
            "power_kw": 60
        }
    ))

    # 2. Forming Area Adjustment Options
    items.append(KnowledgeItem(
        text="""PF1 Option: Forming Area Adjustment Systems

OPTION 1: FIXED WINDOW FRAMES (Standard - Included in Base)
- Material: Steel or aluminum
- Operation: Unbolt frame, remove with forklift
- Upper frame: Adjust cross members with bolting
- Changeover Time: 60 to 120 minutes
- Cost: Included in base price
- Best for: Single product runs, infrequent changes

OPTION 2: UNIVERSAL MOTORISED WINDOW PLATES
- Operation: Motorized adjustment in both X and Y axes
- Control: Settings on touchscreen HMI
- Range: Min 1000 x 700 mm to Max 2000 x 1200 mm
- Feature: Prepared for temperature control
- Changeover Time: Less than 5 minutes
- Cost: ₹40 Lakhs additional
- Additional Power: 2.4 KW

COMPARISON:
| Feature | Fixed Frames | Universal Motorised |
|---------|--------------|---------------------|
| Change Time | 60-120 min | <5 min |
| Labor | Forklift + operator | Button press |
| Flexibility | Low | High |
| Cost | Included | +₹40L |

RECOMMENDATION LOGIC:
- Choose FIXED if: Single product, rare changes, budget priority
- Choose UNIVERSAL if: Multiple products, frequent changeovers, high-volume
- ROI: If changing >2x per week, Universal pays back in labor savings""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Options",
        summary="Forming area: Fixed frames (included, 60-120min) vs Universal motorized (+₹40L, <5min)",
        metadata={
            "topic": "forming_area_option",
            "options": ["Fixed Window Frames", "Universal Motorised"],
            "price_upgrade_inr": 4000000
        }
    ))

    # 3. Tool Loading & Clamping Options
    items.append(KnowledgeItem(
        text="""PF1 Options: Tool Loading & Clamping Systems

TOOL LOADING OPTIONS:

OPTION A: FORKLIFT LOADING (Standard - Included)
- Method: Operator uses forklift to place tool
- Positioning: Manual adjustment to center
- Time: 30 to 60 minutes
- Cost: Included in base price
- Skill Required: Forklift operation, alignment skill

OPTION B: QUICK LOADING BY SLIDING
- Method: Ball transfer units on bottom table
- Operation: Slide tool on, transfers retract
- Feature: Tool slides easily, auto-centers
- Time: Less than 10 minutes
- Cost: ₹8 Lakhs additional
- Skill Required: Minimal

TOOL CLAMPING OPTIONS:

OPTION A: BOLT CLAMPING (Standard - Included)
- Method: 4-sided bolt clamping by operator
- Time: 60 minutes
- Cost: Included in base price

OPTION B: PNEUMATIC QUICK CLAMPING
- Method: Air cylinder clamping from bottom
- Feature: Auto-centering, instant clamp
- Time: Less than 5 minutes
- Cost: ₹8 Lakhs additional

FRONT DOOR LOCKING OPTION:
- Standard: Manual hand wrench
- Upgrade: Air cylinder locking
- Cost: ₹2 Lakhs additional

COMBINED QUICK CHANGEOVER PACKAGE:
- Quick Sliding: ₹8L
- Pneumatic Clamp: ₹8L
- Air Door Lock: ₹2L
- TOTAL: ₹18L for full quick-change capability

TIME SAVINGS SUMMARY:
| Operation | Standard | Quick | Savings |
|-----------|----------|-------|---------|
| Tool Load | 30-60 min | <10 min | 50+ min |
| Clamping | 60 min | <5 min | 55+ min |
| TOTAL | 90-120 min | <15 min | 75-105 min |""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Options",
        summary="Quick tool load (+₹8L), pneumatic clamp (+₹8L), air door (+₹2L) = 75min faster changeover",
        metadata={
            "topic": "tool_loading_options",
            "quick_load_inr": 800000,
            "quick_clamp_inr": 800000,
            "air_door_inr": 200000
        }
    ))

    # 4. Sheet Loading & Automation Options
    items.append(KnowledgeItem(
        text="""PF1 Options: Sheet Loading & Automation

OPTION 1: MANUAL LOADING & UNLOADING (Standard - Included)
- Sheet Load: Operator(s) manually load sheet, press cycle start
- Part Unload: Clamp frame rises, operator removes formed part
- Cycle Time Impact: 120 to 240 seconds for load/unload
- Labor: 1-2 operators required
- Cost: Included in base price

OPTION 2: AUTOMATIC SHEET LOADER & UNLOADER ROBOT
- Cost: ₹60 Lakhs additional

AUTOLOADER FEATURES:
1. SHEET LOADING:
   - Operator loads stack of sheets on pallet
   - Pallet size must be smaller than sheet size
   - Vacuum suction cups pick top sheet
   - Pneumatic sheet separation (air blow) ensures single sheet
   - Sheet transported to forming station

2. PART UNLOADING:
   - Simultaneous with next sheet loading
   - Top auto frame unloads formed part
   - Pneumatic pusher moves part to tilted table
   - Easy operator pickup from front

AUTOMATION BENEFITS:
- Cycle Time: 30 to 60 seconds (vs 120-240s manual)
- Labor: Reduced to monitoring only
- Consistency: No operator variation
- Safety: Operator away from moving parts

AUTOMATION ROI CALCULATION:
- Cycle time savings: ~2 minutes per cycle
- At 15 cycles/hour: 30 minutes saved/hour
- At 8 hours/day: 4 hours labor saved
- Operator cost ~₹500/hr: ₹2000/day savings
- Annual savings: ~₹5-6 Lakhs
- Payback: ~10-12 years (but also enables higher volume)

RECOMMENDATION:
- Choose MANUAL if: Low volume, simple parts, budget priority
- Choose AUTO if: High volume, consistent production, labor costs high
- Often combined with Universal Window Plates for max flexibility""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Options",
        summary="Autoloader robot (+₹60L): 30-60s vs 120-240s manual; auto load + simultaneous unload",
        metadata={
            "topic": "automation_options",
            "autoloader_price_inr": 6000000,
            "time_savings": "60-180 seconds per cycle"
        }
    ))

    # 5. Heating System Options
    items.append(KnowledgeItem(
        text="""PF1 Options: Heating System Configurations

PF1 uses SANDWICH HEATING (Upper + Lower heaters)

HEATER ELEMENT OPTIONS:

1. IR CERAMIC (Long-Wave) - Standard Included
   - Wattage: Top 500W each, Bottom 350W each
   - Wavelength: Long-wave infrared
   - Advantage: Rugged, wide material acceptance
   - Materials: All thermoplastics
   - Cost: Included in base price
   - Energy: Baseline

2. IR QUARTZ (Medium-Wave)
   - Wattage: Top 500W each, Bottom 300W each
   - Wavelength: Medium-wave infrared
   - Advantage: Up to 25% energy savings
   - Materials: All thermoplastics
   - Cost: ₹4 Lakhs additional
   - Note: Savings depend on cooling time

3. IR HALOGEN FLASH TYPE (Short-Wave)
   - Wattage: Top 1500W each, Bottom 750W each
   - Wavelength: Short-wave infrared
   - Advantage: Up to 50% energy savings
   - Materials: All EXCEPT PMMA, PC, PET
   - Cost: ₹8 Lakhs additional
   - Heater Load: Changes to 160 KW (vs 50KW)
   - REQUIREMENT: Must use Heatronik controller

WAVELENGTH SELECTION GUIDE:
"Every thermoplastic has characteristic IR permeability"

| Material | Ceramic | Quartz | Halogen |
|----------|---------|--------|---------|
| ABS | ✓ | ✓ | ✓ |
| HIPS | ✓ | ✓ | ✓ |
| PP | ✓ | ✓ | ✓ |
| PE | ✓ | ✓ | ✓ |
| PMMA | ✓ | ✓ | ✗ |
| PC | ✓ | ✓ | ✗ |
| PET | ✓ | ✓ | ✗ |

HEATER CONTROL OPTIONS:

1. SSR (Solid State Relay) - Standard
   - Advantage: Easy to replace, readily available
   - Control: Zone-based temperature setting
   - Cost: Included

2. THYRISTOR HEATRONIK CONTROLLER
   - Advantage: Faulty heater detection on HMI
   - Feature: Soft start, faster firing
   - MANDATORY for Halogen heaters
   - Benefit: Smaller panel size
   - Cost: ₹12 Lakhs additional

IR PYROMETER OPTION:
- Location: Center of top heater oven
- Purpose: Sheet temperature monitoring
- Included in base configuration""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Options",
        summary="Heaters: Ceramic (std), Quartz (+₹4L, 25% saving), Halogen (+₹8L, 50% but not for PC/PMMA)",
        metadata={
            "topic": "heating_options",
            "quartz_price_inr": 400000,
            "halogen_price_inr": 800000,
            "heatronik_price_inr": 1200000
        }
    ))

    # 6. Machine Movement Options (Servo Upgrades)
    items.append(KnowledgeItem(
        text="""PF1 Options: Machine Movement Systems (Pneumatic vs Servo)

BASE: ALL PNEUMATIC (Included)
- Sheet Clamping: Pneumatic
- Heater Ovens: Pneumatic
- Lower Table: Pneumatic
- Upper Table: Pneumatic
- Advantage: Simple, low cost, proven
- Limitation: Fixed speed, less precision

SERVO UPGRADE OPTIONS:

1. HEATER OVENS - SERVO DRIVEN
   - Function: Moves heating ovens in/out
   - Benefit: Precise positioning, programmable speed
   - Energy: Reduced air consumption
   - Cost: ₹6 Lakhs additional

2. BOTTOM PLATEN (Lower Table) - SERVO DRIVEN
   - Function: Main forming movement (tool rises to sheet)
   - Benefit: Programmable forming profile
   - Features:
     * Variable speed during forming
     * Precise stop positions
     * Repeatability
     * Lower maintenance
   - Cost: ₹18 Lakhs additional
   - Note: Most impactful servo upgrade

3. UPPER PLATEN - SERVO DRIVEN
   - Function: Plug assist movement
   - Benefit: Programmable plug timing and depth
   - Features:
     * Multi-step plug movement
     * Precise depth control
     * Optimized wall thickness
   - Cost: ₹12 Lakhs additional

SERVO PACKAGE PRICING:
| Servo Upgrade | Price | Priority |
|---------------|-------|----------|
| Heater Ovens | ₹6L | Nice-to-have |
| Bottom Platen | ₹18L | High impact |
| Upper Platen | ₹12L | For plug assist |
| ALL THREE | ₹36L | Full servo |

WHY CHOOSE SERVO:
1. Energy efficiency (no continuous air consumption)
2. Precise, repeatable movements
3. Programmable profiles for different products
4. Quieter operation
5. Lower long-term maintenance
6. Better part quality consistency

RECOMMENDATION:
- Budget priority: Stay pneumatic (included)
- Quality priority: Bottom platen servo (₹18L)
- Full automation: All three servos (₹36L)
- Often paired with Universal Window Plates + Autoloader""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Options",
        summary="Servo upgrades: Heaters (+₹6L), Bottom platen (+₹18L), Upper platen (+₹12L) = ₹36L total",
        metadata={
            "topic": "servo_options",
            "servo_heaters_inr": 600000,
            "servo_bottom_inr": 1800000,
            "servo_upper_inr": 1200000,
            "servo_all_inr": 3600000
        }
    ))

    # 7. Cooling System Options
    items.append(KnowledgeItem(
        text="""PF1 Options: Cooling System Configurations

OPTION 1: CENTRIFUGAL FANS (Standard - Included)
- Method: Multiple blowers blow air to cool part
- Location: Around forming area
- Effectiveness: Standard cooling
- Cost: Included in base price
- Maintenance: Simple fan maintenance

OPTION 2: CENTRAL DUCTED COOLING
- Method: Centrally connected blower pulls air from bottom
- Features:
  * Increased airflow
  * More uniform cooling
  * Reduced cooling time
  * Better temperature distribution
- Cost: ₹8 Lakhs additional
- Benefit: Faster cycles, better part quality

IR PYROMETER FOR COOLING (Optional):
- Can be fitted to monitor part temperature during cooling
- Enables automatic cycle end when target temp reached
- Included in base for heating cycle

COOLING TIME IMPACT:
- Cooling is often the longest part of cycle
- Central ducted can reduce cooling time 20-30%
- Faster cooling = more cycles per hour

RECOMMENDATION:
- Standard fans: Adequate for most applications
- Ducted cooling: For thick parts, faster cycles, premium quality""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Options",
        summary="Cooling: Centrifugal fans (std) vs Central ducted (+₹8L, 20-30% faster cooling)",
        metadata={
            "topic": "cooling_options",
            "ducted_cooling_inr": 800000
        }
    ))

    # 8. Complete Options Pricing Summary
    items.append(KnowledgeItem(
        text="""PF1-1015 Complete Options Pricing Summary (INR)

BASE MACHINE: ₹60 Lakhs

AVAILABLE OPTIONS:

| # | Option | Price (₹) |
|---|--------|-----------|
| 1 | Universal Motorised Window Plates | 40,00,000 |
| 2 | Quick Tool Loading (Sliding) | 8,00,000 |
| 3 | Quick Tool Clamping (Pneumatic) | 8,00,000 |
| 4 | Front Door Air Cylinders | 2,00,000 |
| 5 | Autoloader Robot | 60,00,000 |
| 6a | IR Quartz Heaters | 4,00,000 |
| 6b | IR Halogen Flash Heaters | 8,00,000 |
| 7 | Heatronik Controller (Thyristor) | 12,00,000 |
| 8 | Central Ducted Cooling | 8,00,000 |
| 9a | Servo Heater Ovens | 6,00,000 |
| 9b | Servo Bottom Platen | 18,00,000 |
| 9c | Servo Upper Platen | 12,00,000 |

CONFIGURATION EXAMPLES:

BASIC MACHINE (Manual, Pneumatic):
- Base price: ₹60 Lakhs
- No options added
- Good for: Single product, budget priority

QUICK CHANGEOVER PACKAGE:
- Base: ₹60L
- Quick Load: ₹8L
- Quick Clamp: ₹8L
- Air Door: ₹2L
- TOTAL: ₹78 Lakhs
- Good for: Multiple products, frequent changes

SEMI-AUTOMATED:
- Base: ₹60L
- Universal Windows: ₹40L
- Quick Load/Clamp: ₹16L
- Quartz Heaters: ₹4L
- TOTAL: ₹120 Lakhs (~$144K)
- Good for: Mid-volume, product variety

FULLY LOADED MACHINE:
- Base: ₹60L
- Universal Windows: ₹40L
- Quick Load/Clamp/Door: ₹18L
- Autoloader: ₹60L
- Halogen + Heatronik: ₹20L
- All Servos: ₹36L
- Ducted Cooling: ₹8L
- TOTAL: ₹242 Lakhs (~$290K)
- Good for: High volume, premium production

COMMERCIAL TERMS:
- Lead Time: 6-9 months from PO + advance
- Incoterms: EXW
- Payment: 50% advance, 50% before dispatch
- Warranty: 12 months from installation
- Quote Validity: 2 weeks""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="PF1-1015",
        summary="PF1-1015: Base ₹60L, options up to ₹182L more; full config ₹242L (~$290K)",
        metadata={
            "topic": "pricing_summary",
            "base_price_inr": 6000000,
            "max_options_inr": 18200000,
            "fully_loaded_inr": 24200000
        }
    ))

    # 9. Component Brands
    items.append(KnowledgeItem(
        text="""PF1 Series Component Brands

CONTROL & AUTOMATION:
- PLC, HMI & Servos: Mitsubishi (Japan)

PNEUMATICS:
- Cylinders & Valves: Festo / SMC

SENSORS & SAFETY:
- Light Guard & Sensors: Sick / Pepperl+Fuchs / Omron
- Safety Components: Euchner / Phoenix / Sick

VACUUM:
- Vacuum Pump: Busch / Becker (Germany)

ELECTRICAL:
- Control Panel Enclosures: Hoffman / Rittal
- Switch Gears: Eaton / Schneider
- Bus-Bar System: Rittal / Wohner
- Heater Control: Crydom / Unison (SSR) or Heatronik (Thyristor)

HEATING:
- Heater Elements: Ceramicx / TQS

MECHANICAL:
- Gearbox: Bonfiglioli / SEW
- Linear Rails: Hiwin / THK
- Cooling Fans: EBM Papst / Nicotra Gebhart

BRAND POLICY:
"In case any item is not available due to abnormal lead time,
item of similar quality/brand will be used - client will be
informed prior"

CONTROL SYSTEM FEATURES:
- Touchscreen HMI for all parameters
- Software developed with operators over 25 years
- Heater bank visualization
- I/O status and alarms
- Recipe storage on SD card
- Internet connectivity for remote monitoring
- Operator & manager access levels with passcode""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1 Components",
        summary="PF1 components: Mitsubishi control, Festo/SMC pneumatics, Busch vacuum, Sick safety",
        metadata={
            "topic": "component_brands",
            "plc": "Mitsubishi",
            "pneumatics": ["Festo", "SMC"],
            "vacuum": ["Busch", "Becker"]
        }
    ))

    # 10. Why Choose Machinecraft (Sales Points)
    items.append(KnowledgeItem(
        text="""Why Choose Machinecraft PF1 - Sales Talking Points

ENGINEERING QUALITY:
- Strong machine design with thick profiles
- Heavy-duty racks, shafts, gearboxes
- Robust mechanical components
- Designed for industrial production

SAFETY DESIGN:
- Upper tables locked with 2-level safety
- Appropriate interlocks with sensors
- Special electrical safety elements
- Light guards, door switches
- Emergency stops

AUTOMATION OPTIONS:
- Automatic sheet loader available
- Universal sheet size frames
- Servo motor upgrades
- Energy-efficient heater options

ENERGY EFFICIENCY:
- Servo motor options reduce air consumption
- Quartz heaters: 25% energy savings
- Halogen heaters: 50% energy savings
- Heatronik controller for optimal firing

SERVICEABILITY:
- Easy to maintain design
- Standard international components
- Components available in customer's region
- Global brand names (Mitsubishi, Festo, Busch)

CUSTOMIZATION:
- All machines tailor-made per customer
- Flexible options to match requirements
- Quote format helps select right configuration
- No one-size-fits-all approach

SOFTWARE:
- 25 years of operator feedback
- Recipe management
- Remote monitoring capability
- Intuitive HMI interface

DOCUMENTATION:
- English manuals
- Operation instructions
- Spare part lists
- System layouts
- Maintenance instructions
- Wiring diagrams
- Available on USB or paper""",
        knowledge_type="sales",
        source_file=SOURCE_FILE,
        entity="Machinecraft PF1",
        summary="PF1 selling points: robust design, safety, automation options, energy efficiency, customizable",
        metadata={
            "topic": "sales_points",
            "key_messages": ["quality", "safety", "automation", "efficiency", "customization"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("PF1-1015 All Options Quotation Ingestion")
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
