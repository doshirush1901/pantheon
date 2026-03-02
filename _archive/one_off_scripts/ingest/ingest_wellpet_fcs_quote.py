#!/usr/bin/env python3
"""
Ingest WellPet FCS 5065 Quote (March 2021)

FCS (Form-Cut-Stack) multistation thermoforming machine quote.
Roll-fed, high-speed production for packaging applications.

Source: Machinecraft_FCS_2021_WellPet_March 2021.pdf
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

SOURCE_FILE = "Machinecraft_FCS_2021_WellPet_March 2021.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from WellPet FCS quote."""
    items = []

    # 1. Quote Overview
    items.append(KnowledgeItem(
        text="""WellPet FCS 5065 Quote Overview

QUOTE DETAILS:
- Quote No: MT2021030502
- Date: 05 March 2021
- Contact: Rushabh Doshi
- Client: Dilip Bhai (WellPet)
- Application: Hinge Box production

MACHINE MODEL: FCS 500x650/S/3ST
- FCS = Form-Cut-Stack
- 500x650 = 500 x 650 mm forming area
- S = Servo driven
- 3ST = 3 Station machine

FCS SERIES DESCRIPTION:
"FCS stands for Form-Cut-Stack machine type – multistation 
thermoforming machine – there are 3 stations – stations being 
heating, forming, punching and stacking. The machine is fully 
servo driven and runs at dry cycle speed of upto 30 cycles per minute."

PRICING BREAKDOWN:
| Item | Price (INR) |
|------|-------------|
| FCS 5065 Basic Machine | ₹90,00,000 |
| Servo Chain Adjustment | ₹7,50,000 |
| Servo Forming Station | ₹9,50,000 |
| Additional Servo Punching | ₹4,50,000 |
| Heating/Cooling Punching | ₹1,50,000 |
| Servo Punch Station Adjust | ₹1,50,000 |
| Pushout & Conveyor | ₹3,00,000 |
| Moveable HMI | ₹75,000 |
| Mould Set (2x2 Hinge Box) | ₹12,50,000 |
| **TOTAL** | **₹1,30,75,000** |

LEAD TIME: 24 weeks
PAYMENT: 25-25-40-10""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="WellPet FCS Quote Overview",
        summary="FCS 5065 for WellPet: ₹1.31CR total; 500x650mm, 30 cycles/min, hinge box mould included",
        metadata={
            "topic": "wellpet_fcs_overview",
            "quote_no": "MT2021030502",
            "total_price": "₹1,30,75,000"
        }
    ))

    # 2. Technical Specifications
    items.append(KnowledgeItem(
        text="""FCS 500x650/S/3ST Technical Specifications

FORMING SPECIFICATIONS:
- Max Forming Area: 500 x 650 mm
- Max Forming Depth: 140 mm
- Max Sheet Width: 700 mm
- Sheet Thickness Range: 0.2 mm to 1.4 mm

PERFORMANCE:
- Dry Cycle Speed: 30 cycles/minute
- Forming Air Pressure: 4 bar
- Pressure Forming: Yes

POWER:
- Total Power: 85 KW
- Heating Load: 40.8 KW (48 elements x 2 ovens)

PUNCHING:
- Press Force: 60 tonnes
- Press Type: Toggle design (servo driven)
- Temperature control for PET cutting
- Water cooling in press

SERVO DRIVES:
- Chain Adjustment: 4 servos
- Forming Press: 2 servos
- Punching Press: 2 servos
- Punching Station Adjustment: 1 servo
- Chain Indexing: 1 servo
- TOTAL: 10 servo motors

STACKING:
- Type: Pneumatic up-stacking
- Double layer capability
- Pushout with conveyor

CHAIN SYSTEM:
- Type: 1/2" duplex spiked chain
- Spike spacing: Every 1"
- Indexing accuracy: ±0.3 mm
- Width adjustment: Servo motorized (4 motors)""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="FCS 5065 Technical Specs",
        summary="FCS 5065: 500x650mm, 140mm depth, 30 cycles/min, 60-ton punch, 10 servo motors, ±0.3mm accuracy",
        metadata={
            "topic": "fcs_5065_specs",
            "forming_area": "500 x 650 mm",
            "cycle_speed": "30 cycles/min"
        }
    ))

    # 3. Station Details
    items.append(KnowledgeItem(
        text="""FCS 5065 Station-by-Station Description

ROLL UNWINDER:
- Max sheet roll width: 650 mm
- Max roll weight: 400 kg
- Loop sensing: Cat-whiskers limit switch
- Works with transparent materials
- Automatic unwinding

HEATING STATION:
- Configuration: Dual/Sandwich (top + bottom)
- Elements: 6 rows x 8 columns = 48 per oven
- Top Heater: 500W each element
- Bottom Heater: 350W each element
- Total Load: 40.8 KW
- Type: IR Elements (Elstein Germany)
- Control: Individual zone via HMI
- Sag sensor for safety
- Heaters moveable close to mould

STATION 1 - FORMING:
- Press type: Toggle (servo driven)
- Mould mounting: On forming platen
- Pressure box: Top/bottom, up to 4 bar
- Air release: Pneumatic (HMI controlled)
- Helping frame included

STATION 2 - PUNCHING:
- Press type: Toggle (servo driven)
- Press force: 60 tonnes
- Die type: Steel ruled cutting die
- Height adjustment: Chain mechanism
- Fine alignment: XY mechanism on linear guide
- XY setting: Motorized hand knobs
- Temperature controller for heated punching (PET)
- Water cooling in press
- Station distance: Servo adjustable (recipe storage)
- Lubrication: Automatic pump (PLC programmed)

STATION 3 - STACKING:
- Motion: Pneumatic up-stacking
- Double layer: Operator sets count, auto stack
- Output: Pneumatic pushout with conveyor

TRIM WINDING:
- Motor: 1/2 HP geared motor
- Winds leftover trim after punching""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="FCS Station Details",
        summary="FCS stations: Unwinder (400kg) → Heating (48 elements) → Forming (4 bar) → Punch (60T) → Stack",
        metadata={
            "topic": "fcs_station_details",
            "stations": ["Unwinder", "Heating", "Forming", "Punching", "Stacking", "Trim Winding"]
        }
    ))

    # 4. Mould Details
    items.append(KnowledgeItem(
        text="""FCS Mould Set - Hinge Box (MP-2/2-4-H)

MOULD DESCRIPTION:
- Model: MP-2/2-4-H
- Configuration: 2x2 = 4 cavity mould
- Product: Hinge Box
- Approximate size: 285 x 185 mm each

HEIGHT ADJUSTABLE FEATURE:
- 2 x height adjustable plates included
- Available heights: 40 mm, 50 mm, 70 mm
- Single tool makes 3 different depths

MOULD COMPONENTS:
1. Forming Mould
   - Material: HE30 Aluminium
   - Process: CNC Machined
   - No holing required

2. Punching Die
   - Material: Steel ruled cut die
   - Running length: Approx. 5 meters
   - Heated option for PET cutting

3. Stacking Fixture
   - Included with mould set

MOULD PRICE: ₹12,50,000

MOULD SET VALUE:
Complete tooling for production included -
customer can start production immediately
after commissioning.

TYPICAL FCS APPLICATIONS:
- Hinge boxes (like this quote)
- Food containers
- Blister packs
- Clamshells
- Lids and trays
- Disposable cups""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="FCS Hinge Box Mould",
        summary="FCS mould MP-2/2-4-H: 4-cavity hinge box; HE30 Al forming + steel rule die; ₹12.5L; 3 heights",
        metadata={
            "topic": "fcs_mould_details",
            "cavities": 4,
            "price": "₹12,50,000"
        }
    ))

    # 5. Options & Upgrades
    items.append(KnowledgeItem(
        text="""FCS 5065 Options & Upgrades Pricing

BASE MACHINE: ₹90,00,000
Includes: Forming (pneumatic), Punching (servo/pneumatic),
Stacking (pneumatic up), manual chain adjust, motor punch adjust

UPGRADE OPTIONS:

1. SERVO ADJUSTABLE CHAIN SYSTEM: ₹7,50,000
   - 4 servo motors for chain width
   - Automatic adjustment via HMI
   - Recipe storage for different sheet widths

2. SERVO FORMING STATION: ₹9,50,000
   - Replace pneumatic with servo
   - Precise control of forming motion
   - Better part quality

3. ADDITIONAL SERVO IN PUNCHING: ₹4,50,000
   - Servo in bottom of punching station
   - More precise die alignment

4. HEATING/COOLING FOR PUNCHING: ₹1,50,000
   - Temperature controller
   - Essential for PET cutting
   - Heated die prevents stringing

5. SERVO ADJUSTABLE PUNCH STATION: ₹1,50,000
   - Servo positioning of punch station
   - Recipe storage for different products

6. PUSHOUT & CONVEYOR: ₹3,00,000
   - Automatic part ejection
   - Conveyor for part transport
   - Reduces manual handling

7. MOVEABLE HMI: ₹75,000
   - HMI on linear rail guide
   - Operator can position for convenience

TOTAL OPTIONS: ₹28,25,000
OPTIONS AS % OF BASE: 31%

FULLY LOADED MACHINE:
₹90,00,000 + ₹28,25,000 = ₹1,18,25,000 (without mould)

WITH MOULD:
₹1,18,25,000 + ₹12,50,000 = ₹1,30,75,000""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="FCS Options Pricing",
        summary="FCS options: Base ₹90L; +servo chain ₹7.5L; +servo form ₹9.5L; +conveyor ₹3L; total ₹1.31CR",
        metadata={
            "topic": "fcs_options_pricing",
            "base_price": "₹90,00,000",
            "options_total": "₹28,25,000"
        }
    ))

    # 6. Component Brands & Control
    items.append(KnowledgeItem(
        text="""FCS 5065 Components & Control System

CONTROL SYSTEM:
- PLC: Mitsubishi (Japan)
- HMI: 10" color touchscreen Mitsubishi
- HMI features: Moveable on linear rail
- Recipe storage: SD card

SERVO MOTORS:
- Makes: Mitsubishi / Siemens / SEW
- Total: Up to 10 servo motors (fully loaded)
- Applications: Chain, forming, punching, adjustments

HEATERS:
- Make: Elstein (Germany)
- Type: IR heating elements

PNEUMATICS:
- Make: FESTO

SENSORS:
- Make: Pepperl+Fuchs
- Application: Loop sensing, limit switches

VACUUM:
- Make: Becker / Busch (Germany)

GEARBOX:
- Make: Bonfiglioli / SEW

HMI CAPABILITIES:
- Individual heater zone control
- Element percentage adjustment
- Recipe storage on SD card
- Servo position programming
- Cycle monitoring
- Alarm management

ELECTRICAL REQUIREMENTS:
- Supply: 400V + N + PE, 50Hz
- Network: TN-S or TN-C-S
- Total Load: 85 KW

AIR SUPPLY:
- Minimum: 6 bar
- Quality: Oil, water, pollution free""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="FCS Components & Control",
        summary="FCS control: Mitsubishi PLC + 10\" HMI; up to 10 servos; Elstein heaters; 85KW total load",
        metadata={
            "topic": "fcs_components",
            "plc": "Mitsubishi",
            "total_power": "85 KW"
        }
    ))

    # 7. Commercial Terms
    items.append(KnowledgeItem(
        text="""FCS 5065 Commercial Terms - WellPet Quote

PRICING:
- Total: ₹1,30,75,000 (₹1.31 Crore)
- Includes: Machine + all options + mould

TERMS OF DELIVERY:
- Basis: Ex-works (transportation extra)
- Installation: 2 men, 5 working days (included)
- Travel expenses: Customer pays actuals (flights, car, hotel)

PAYMENT TERMS:
- 25% Advance with signed PO
- 25% 30 days after PO
- 40% Upon machine completion
- 10% Before dispatch

LEAD TIME:
- 24 weeks after technical/commercial clarification
- Exact timing after written PO and advance

WARRANTY:
- 12 months from pre-acceptance notification
- Condition: Regular maintenance required
- Void if maintenance not performed

QUOTE VALIDITY: 2 weeks

SIGNATORIES:
- Deepak Doshi (Director)
- Rushabh Doshi (Technical Sales Manager)

FCS PRICING CONTEXT:
- Base machine: ₹90L (~$110K USD)
- Fully loaded + mould: ₹1.31 CR (~$160K USD)
- Competitive vs European FCS machines at €250K+
- 30 cycles/min = high volume capability
- ROI typically 1-2 years for packaging applications

FCS vs PF1 COMPARISON:
| Feature | FCS | PF1 |
|---------|-----|-----|
| Feed | Roll | Sheet |
| Stations | Multi (3+) | Single |
| Speed | 30 cycles/min | 2-5 cycles/min |
| Application | Packaging | Heavy gauge |
| Thickness | 0.2-1.4mm | 1-10mm |
| Output | High volume | Low-medium |""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="FCS Commercial Terms",
        summary="FCS terms: ₹1.31CR total; 25-25-40-10 payment; 24 weeks; 12-month warranty; install included",
        metadata={
            "topic": "fcs_commercial_terms",
            "total_price": "₹1,30,75,000",
            "payment": "25-25-40-10",
            "lead_time": "24 weeks"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("WellPet FCS 5065 Quote Ingestion")
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
