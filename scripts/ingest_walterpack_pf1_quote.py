#!/usr/bin/env python3
"""
Ingest Walterpack PF1-1515/S/A Quote

Complete PF1 machine quotation with detailed technical specifications.
Reference quote for PF1 series pricing and features.

Source: MT2021102601 PF1 1515 S A Machinecraft for Walterpack.pdf
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

SOURCE_FILE = "MT2021102601 PF1 1515 S A Machinecraft for Walterpack.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from Walterpack PF1 quote."""
    items = []

    # 1. Quote Overview
    items.append(KnowledgeItem(
        text="""Walterpack PF1-1515/S/A Quote Overview

QUOTE DETAILS:
- Quote No: MT2021102601
- Date: 26 October 2021
- Contact: Rushabh Doshi
- Client: Mr Roy Matthew, Walterpack India

MACHINE MODEL: PF1-1515/S/A
- PF1 = Polymer Forming machine (Machinecraft's main series)
- 1515 = 1500 x 1500 mm forming area
- S = Servo driven movements
- A = Autoloader included

PF1 SERIES HISTORY:
- First displayed at K Show Dusseldorf in 1998
- Installed globally: India, Middle East, Europe, North America
- Each machine custom tailor-made per client requirements
- Customizable: Size, movements, automation options

PRICING:
- Machine Price: ₹1,17,00,000 (One Crore Seventeen Lakhs)
- Terms: Ex-works India
- Extras: Shipping, insurance, packing

PAYMENT TERMS:
- 50% advance
- 50% before dispatch

WARRANTY: 12 months from pre-acceptance notification

LEAD TIME: Approx. 20 weeks after technical/commercial clarification

VALIDITY: 2 weeks""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Walterpack PF1 Quote Overview",
        summary="PF1-1515/S/A for Walterpack: ₹1.17CR; 1500x1500mm, servo, autoloader; 50-50 payment; 20 weeks",
        metadata={
            "topic": "walterpack_pf1_overview",
            "quote_no": "MT2021102601",
            "price": "₹1,17,00,000"
        }
    ))

    # 2. Technical Specifications
    items.append(KnowledgeItem(
        text="""PF1-1515/S/A Technical Specifications

FORMING SPECIFICATIONS:
- Max Forming Area: 1500 x 1500 mm
- Max Tool Height (bottom): 500 mm
- Max Plug Assist Height: 500 mm below sheet level
- Sheet Thickness Capability: Up to 10 mm (sandwich heaters)

HEATER SYSTEM:
- Type: IR Quartz (Ceramicx Ireland)
- Configuration: Sandwich heaters (top + bottom ovens)
- Total Heating Load: 76.5 KW
- Top Heater: 500 W each element
- Bottom Heater: 350 W each element
- Element Size: 245 x 63 mm
- Elements per Zone: 2
- Control: SSR controlled by PLC
- Heater Movement: Electric Servo Driven
- Energy Saving: Up to 30% power saving vs ceramic

VACUUM SYSTEM:
- Pump Capacity: 1600 lpm
- Tank: Integrated, generously dimensioned
- Auto air-ejection for part demoulding
- FRL pneumatic system included

CLOSED CHAMBER DESIGN:
- European concept
- Area below forming area completely sealed (air-tight)
- Enables preblow with pulsated air
- Critical for even wall thickness on male moulds

PREBLOW & SAG CONTROL:
- Preblow: 1 x photocell above sheet, manually adjustable + timer
- Sag Control: 1 x photocell at center below sheet
- Protects bottom heater from sagging sheet""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-1515 Technical Specs",
        summary="PF1-1515: 1500x1500mm, 500mm stroke, 76.5KW quartz heaters, 1600lpm vacuum, closed chamber",
        metadata={
            "topic": "pf1_1515_specs",
            "forming_area": "1500 x 1500 mm",
            "heating_load": "76.5 KW"
        }
    ))

    # 3. Sheet Handling System
    items.append(KnowledgeItem(
        text="""PF1-1515/S/A Sheet Handling & Automation

SHEET SIZE SETTING SYSTEM:

Bottom Frame:
- Type: Fixed MS welded frame (sized per sheet)
- Mounting: Bolted with C-clamps by operator
- One full-size frame included with machine

Top Frame:
- Type: Manually adjustable
- Adjustment: Cross members

AUTOLOADER SYSTEM:

Features:
- Automated sheet loading (reduces operator work)
- Position: Right or left side (customer choice)
- Picks thermoplastic sheet and places on forming area
- Also unloads final formed part
- Pneumatic pusher ejects part for operator pickup

SHEET CLAMPING:
- Type: Electric Servo Driven
- Clamp frame tightly holds thermoplastic sheet

CYCLE FLOW:
1. Autoloader picks sheet from stack
2. Places sheet on forming area
3. Servo clamp engages
4. Heating cycle starts
5. After forming, clamp releases
6. Autoloader unloads formed part
7. Pneumatic pusher ejects part

AUTOMATION BENEFIT:
- Consistent loading position
- Faster cycle times
- Reduced operator fatigue
- Suitable for 24/7 production""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-1515 Sheet Handling",
        summary="PF1-1515 automation: Servo sheet clamp, autoloader robot (load + unload), pneumatic ejector",
        metadata={
            "topic": "pf1_sheet_handling",
            "automation": ["Autoloader", "Servo clamp", "Pneumatic ejector"]
        }
    ))

    # 4. Motion Systems
    items.append(KnowledgeItem(
        text="""PF1-1515/S/A Motion & Drive Systems

BOTTOM TABLE (Tool Table):
- Movement: Electric Servo Driven
- Speed: 700 mm/s (vs pneumatic 250 mm/s)
- Benefit: Avoids stretch marks on parts
- Variable Stop: Can stop at any distance (0 to max stroke)
- Use: For products with shorter height

TOOL CLAMPING:
- Type: Pneumatic cylinders at bottom of table
- Benefit: Faster clamping
- No need for operator to enter machine and bolt tool

TOP TABLE (Plug Assist):
- Movement: Pneumatic Driven
- Height Adjustment: DC Motor, settable on HMI
- Plug Material: Typically artificial wood or nylon

HEATER MOVEMENT:
- Type: Electric Servo Driven
- Independent top & bottom heater oven movement

SHEET CLAMPING:
- Type: Electric Servo Driven

SERVO ADVANTAGE:
- Precision control
- Repeatable positioning
- Energy efficient
- Programmable profiles
- Variable speed/position

MOTION SUMMARY:
| Component | Drive Type |
|-----------|------------|
| Bottom Table | Servo (700 mm/s) |
| Heater Ovens | Servo |
| Sheet Clamp | Servo |
| Top Table | Pneumatic + DC adjust |
| Tool Clamp | Pneumatic |""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-1515 Motion Systems",
        summary="PF1-1515 motion: Servo bottom table (700mm/s), servo heaters, servo clamp; pneumatic plug assist",
        metadata={
            "topic": "pf1_motion_systems",
            "servo_components": ["Bottom table", "Heaters", "Sheet clamp"],
            "speed": "700 mm/s"
        }
    ))

    # 5. Cooling & Control
    items.append(KnowledgeItem(
        text="""PF1-1515/S/A Cooling & Control Systems

COOLING SYSTEM:
- Type: Centrifugal Fans
- Capacity: 26 m³/hr each
- Quantity: 8 fans
- Purpose: Cool formed part before unloading

CONTROL PANEL:
- HMI: 10" touchscreen
- Software: Developed with operators over 25 years
- Recipe Storage: SD card
- PLC: Inside electrical cabinet

HMI FEATURES:
- Visualization of heater bank settings
- All process parameters displayed
- I/O status monitoring
- Alarm management
- Individual or total field heating adjustment

ELECTRICAL SAFETY:
- Overload protection for motors
- Fuse/MCB for heaters
- MCCB protection
- Overtravel protection
- Limit switches

SAFETY STANDARDS:
- Light guard in sheet loading area (Sick)
- Emergency switches at operator area & control panel
- Air reservoir for heater movement (power failure backup)
- Appropriate interlocks
- Manual locking pins for servo table (maintenance)

PNEUMATIC SYSTEM:
- FRL (Filter-Regulator-Lubricator) included
- Feed line: Max 10 bar
- Operating pressure: 6 bar
- Water separation included""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-1515 Cooling & Control",
        summary="PF1-1515 control: 10\" Mitsubishi HMI, 8x centrifugal fans, Sick light guards, air reservoir backup",
        metadata={
            "topic": "pf1_cooling_control",
            "fans": "8 x 26 m³/hr",
            "hmi": "10 inch touchscreen"
        }
    ))

    # 6. Component Brands
    items.append(KnowledgeItem(
        text="""PF1-1515/S/A Component Makes & Brands

CONTROL & AUTOMATION:
- PLC: Mitsubishi (Japan)
- HMI: Mitsubishi (Japan)
- Servo Motors: Mitsubishi (Japan)
- Gearbox: SEW

PNEUMATICS & VACUUM:
- Pneumatics: FESTO (Germany)
- Vacuum Pump: Becker/Busch (Germany)

HEATING & COOLING:
- Heater Elements: Elstein (Germany) [Note: Quote mentions Ceramicx Ireland for quartz]
- Cooling Blowers: EBM Papst

SAFETY & SENSORS:
- Light Guard: Sick
- Sensors: Pepperl+Fuchs (PnF)

ELECTRICAL:
- Control Panel: Rittal
- Wires: Lapp / Polycab
- Cable Tracks: Igus
- Switch Gears: Eaton

DOCUMENTATION PROVIDED:
- Operation instructions
- Spare part list
- System layout
- Maintenance instructions
- Wiring diagram
- Available on data medium or paper printing

BRAND POSITIONING:
All components are European/Japanese premium brands.
This justifies Machinecraft's quality positioning vs
Chinese machine alternatives.""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-1515 Component Brands",
        summary="PF1-1515 brands: Mitsubishi (PLC/servo), FESTO, Becker vacuum, Sick guards, Rittal panel",
        metadata={
            "topic": "pf1_component_brands",
            "key_brands": ["Mitsubishi", "FESTO", "Becker", "Sick", "Rittal", "SEW"]
        }
    ))

    # 7. Commercial Terms
    items.append(KnowledgeItem(
        text="""PF1-1515/S/A Commercial Terms - Walterpack Quote

PRICING STRUCTURE:
- Machine: ₹1,17,00,000 (₹1.17 Crore)
- Includes: All specs as quoted
- Basis: Ex-works factory India

EXTRAS (Customer bears):
- Shipping cost
- Insurance
- Packing

COMMISSIONING:
- Included in offer
- 2 x Machinecraft personnel
- Flight, car rental, hotel: Customer pays actuals
- Machinecraft invoices after installation

PAYMENT TERMS:
- 50% Advance with PO
- 50% Before dispatch

WARRANTY:
- Duration: 12 months
- Start: From pre-acceptance / ready notification

LEAD TIME:
- Approx. 20 weeks
- After technical and commercial clarification
- Exact timing after written PO and advance receipt

QUOTE VALIDITY: 2 weeks

SIGNATORIES:
- DB Doshi (Sales Director)
- Rushabh Doshi (Technical Sales Manager)

COMPARISON NOTE:
This 50-50 payment is simpler than SPM projects (25-25-40-10)
because standard PF1 machines have less customization risk.

PF1-1515 PRICING CONTEXT (Oct 2021):
- ₹1.17 CR for 1500mm with autoloader + servo
- Approximately $140,000-150,000 USD equivalent
- Competitive vs European machines at €250K+""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="PF1-1515 Commercial Terms",
        summary="PF1-1515 terms: ₹1.17CR ex-works; 50-50 payment; 20 weeks; 12-month warranty; commissioning included",
        metadata={
            "topic": "pf1_commercial_terms",
            "price": "₹1,17,00,000",
            "payment": "50-50",
            "lead_time": "20 weeks"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Walterpack PF1-1515/S/A Quote Ingestion")
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
