#!/usr/bin/env python3
"""
Ingest Anatomic SITT PF1-0810/S Quote

European market PF1 quote for vacuum lamination application.
Includes CE certification, Swedish language HMI, and exhibition display.

Source: MT2021112201 PF1 0810 S for Anatomic SITT_8e85a6c4.pdf
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

SOURCE_FILE = "MT2021112201 PF1 0810 S for Anatomic SITT_8e85a6c4.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from Anatomic SITT quote."""
    items = []

    # 1. Quote Overview
    items.append(KnowledgeItem(
        text="""Anatomic SITT PF1-0810/S Quote Overview

QUOTE DETAILS:
- Quote No: MT2021112201
- Date: 22 November 2021
- Contact: Rushabh Doshi
- Client: Mr Krister Eriksson, Anatomic SITT AB
- Location: Sweden (Europe)
- Email: krister@anatomicsitt.com

MACHINE MODEL: PF1-0810/S
- PF1 = Polymer Forming machine
- 0810 = 800 x 1000 mm forming area
- S = Servo driven movements

APPLICATION: Vacuum Lamination
- Laminating TPO/TPU blends to hard plastics (ABS/PP)
- Soft-feel surface applications
- Not just vacuum forming - also lamination capable

PRICING:
- Machine Price: EUR 65,000
- Includes: Shipping to Sweden, insurance, packaging, commissioning

PAYMENT TERMS:
- 30% Advance
- 50% Before dispatch (video proof of running machine)
- 20% After installation (max 15 days)

WARRANTY: 24 months (extended vs standard 12 months)

LEAD TIME: 16-20 weeks

SPECIAL: Machine displayed at Elmia Show before delivery

CE CERTIFICATION: Yes, CE label on control panel""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Anatomic SITT Quote Overview",
        summary="PF1-0810/S for Anatomic SITT Sweden: €65K; vacuum lamination; CE certified; 24-month warranty",
        metadata={
            "topic": "anatomic_sitt_overview",
            "quote_no": "MT2021112201",
            "price": "EUR 65,000",
            "market": "Sweden/Europe"
        }
    ))

    # 2. Technical Specifications
    items.append(KnowledgeItem(
        text="""PF1-0810/S Technical Specifications - Anatomic SITT

FORMING SPECIFICATIONS:
- Max Forming Area: 800 x 1000 mm
- Max Stroke: 400 mm
- Sheet Thickness: Up to 10 mm (sandwich heaters)

POWER REQUIREMENTS:
- Total Heating Load: 32 KW
- Servo Motor Load: 6.5 KW
- Total Connected Load: Approx. 41 KW

HEATER SYSTEM:
- Type: IR Quartz (Ceramicx Ireland)
- Configuration: Sandwich (top + bottom)
- Top Heater: 500 W each element
- Bottom Heater: 500 W each element (equal for lamination!)
- Element Size: 245 x 63 mm
- Elements per Zone: 2
- Control: SSR controlled by PLC
- Heater Oven Material: Non-corrosive stainless steel

HEATER MOVEMENT:
- Top Heater: Servo driven
- Bottom Heater: Pneumatic (for safety)

SPECIAL FEATURES FOR LAMINATION:
- Equal wattage top & bottom (critical for lamination)
- Bottom heater protection: Schott high-temperature glass
- IR Pyrometer in top heater center (measures actual sheet temp)

VACUUM SYSTEM:
- Pump Capacity: 100 m³/hr
- Pump Type: Oil-lubricated rotary vane (Busch/Becker Germany)
- Proportional vacuum: FESTO servo ball valve (settable on HMI)
- Auto air-ejection for demoulding""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-0810 Technical Specs",
        summary="PF1-0810: 800x1000mm, 400mm stroke, 32KW heaters (equal top/bottom for lamination), 100m³/hr vacuum",
        metadata={
            "topic": "pf1_0810_specs",
            "forming_area": "800 x 1000 mm",
            "total_load": "41 KW"
        }
    ))

    # 3. Vacuum Lamination Features
    items.append(KnowledgeItem(
        text="""PF1-0810/S Vacuum Lamination Capability

APPLICATION: Vacuum Lamination
- Laminating soft TPO/TPU films to rigid ABS/PP substrates
- Creates soft-feel/soft-touch surfaces
- Common in automotive interiors, furniture, etc.

KEY DESIGN FEATURES FOR LAMINATION:

1. EQUAL HEATER WATTAGE:
   - Top: 500W per element
   - Bottom: 500W per element
   - Why: Even heating from both sides critical for lamination
   - Standard forming often has stronger top vs bottom

2. SERVO TOP TABLE:
   - Speed: 1000 mm/s (faster than bottom)
   - Motor: 2 KW
   - Purpose: Precise control for lamination pressure/timing

3. SERVO BOTTOM TABLE:
   - Speed: 700 mm/s
   - Motor: 3.5 KW
   - Both tables can stop at any position (0 to max stroke)

4. PROPORTIONAL VACUUM:
   - FESTO servo ball valve between tank and table
   - Settable on HMI
   - Controlled vacuum draw for lamination (not just on/off)

5. BOTTOM HEATER PROTECTION:
   - Schott high-temperature glass
   - Protects elements during lamination process

6. CLOSED LOOP COOLING:
   - IR sensor (Raytec) monitors sheet temperature
   - Fans auto-shut when target temp reached
   - Critical for consistent lamination quality

PROCESS DIFFERENCE:
- Vacuum Forming: Pull sheet over tool
- Vacuum Lamination: Bond film to substrate using vacuum + heat

MACHINE VERSATILITY:
This machine handles BOTH vacuum forming AND vacuum lamination.""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="PF1-0810 Vacuum Lamination",
        summary="Vacuum lamination: Equal heaters, servo both tables, proportional vacuum, Schott glass protection",
        metadata={
            "topic": "vacuum_lamination_features",
            "application": "TPO/TPU lamination to ABS/PP",
            "key_feature": "Equal wattage heaters"
        }
    ))

    # 4. European Market Configuration
    items.append(KnowledgeItem(
        text="""PF1-0810/S European Market Configuration

CE CERTIFICATION:
- Machine designed per CE regulation
- CE label on control panel
- Mandatory for European market

SAFETY FEATURES (CE Compliant):
- Light guard in sheet loading area (Sick)
- Emergency switches at operator area & control panel
- Air reservoir for heater movement (power failure backup)
- Appropriate interlocks
- Manual locking pins for servo bottom table (maintenance)
- Pneumatic locking pins for top table

LANGUAGE CUSTOMIZATION:
- HMI programmed in Swedish AND English
- Documentation in English AND Swedish
- Operator-friendly for local workforce

EXHIBITION DISPLAY:
- Machine displayed at Elmia Show (Sweden trade fair)
- Then installed at customer site
- Marketing benefit: Live demonstration at show

DELIVERY SCOPE (Included in €65K):
- Transport from Machinecraft to Indian port
- Shipping from India to Sweden port
- Insurance
- Packaging
- Commissioning (2 Machinecraft personnel)
- Flights, car rental, hotel for commissioning team

CUSTOMER RESPONSIBILITY:
- Local transport: Port → Exhibition → Customer site
- Customs clearance in Sweden

DOCUMENTATION PROVIDED:
- Operation instructions (EN + SE)
- Spare part list
- System layout
- Maintenance instructions
- Wiring diagram
- Available on data medium or paper""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="PF1-0810 EU Configuration",
        summary="EU config: CE certified, Swedish+English HMI, Elmia show display, full delivery to Sweden port included",
        metadata={
            "topic": "pf1_eu_configuration",
            "certification": "CE",
            "languages": ["Swedish", "English"],
            "exhibition": "Elmia Show"
        }
    ))

    # 5. Motion & Frame Systems
    items.append(KnowledgeItem(
        text="""PF1-0810/S Motion & Frame Systems

BOTTOM TABLE:
- Drive: Electric Servo
- Speed: 700 mm/s
- Motor: 3.5 KW (Mitsubishi)
- Variable stop: Any position 0 to max stroke
- Tool clamping: Bolts

TOP TABLE (Plug Assist):
- Drive: Electric Servo (not pneumatic!)
- Speed: 1000 mm/s (faster than bottom)
- Motor: 2 KW (Mitsubishi)
- Variable stop: Any position 0 to max stroke
- Tool clamping: Bolts
- Locking: Pneumatic locking pins

SHEET SIZE SETTING:

Top Frame:
- Type: Servo motorized (2 x servo motors)
- Adjustment: Automatic via HMI setting
- Benefit: No manual adjustment needed

Bottom Frame:
- Type: CNC machined aluminum
- Mounting: Bolted with C-clamps
- Change: Operator swaps frame for different sizes

SHEET CLAMPING:
- Type: Pneumatic (2 x cylinders in sync)
- Not servo (unlike some larger PF1 models)

HEATER MOVEMENT:
- Top Heater: Servo driven
- Bottom Heater: Pneumatic (safety consideration)

MOTION SUMMARY - PF1-0810/S:
| Component | Drive | Speed/Feature |
|-----------|-------|---------------|
| Bottom Table | Servo | 700 mm/s, 3.5KW |
| Top Table | Servo | 1000 mm/s, 2KW |
| Top Frame | Servo | Auto adjust via HMI |
| Bottom Frame | Manual | CNC Aluminum |
| Sheet Clamp | Pneumatic | 2 cylinders |
| Top Heater | Servo | Moving |
| Bottom Heater | Pneumatic | Safety |

KEY DIFFERENCE vs Larger PF1:
Both top AND bottom tables are servo driven.
Ideal for vacuum lamination requiring precise control of both.""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-0810 Motion Systems",
        summary="PF1-0810 motion: Servo top table (1000mm/s) + bottom table (700mm/s); servo top frame adjust",
        metadata={
            "topic": "pf1_0810_motion",
            "top_table": "Servo 1000mm/s",
            "bottom_table": "Servo 700mm/s"
        }
    ))

    # 6. Commercial Terms Comparison
    items.append(KnowledgeItem(
        text="""PF1-0810/S Commercial Terms - European Export

PRICING:
- Price: EUR 65,000
- Equivalent: ~₹57 Lakhs (at 2021 rates)
- Includes: Full delivery to Sweden + commissioning

WHAT'S INCLUDED IN €65K:
✓ Machine (PF1-0810/S)
✓ Transport to Indian port
✓ Sea shipping to Sweden
✓ Insurance
✓ Packaging
✓ Commissioning (2 personnel)
✓ Team flights, car rental, hotel

CUSTOMER PAYS SEPARATELY:
- Local Sweden transport (port → show → site)
- Swedish customs clearance

PAYMENT TERMS (European):
- 30% Advance with PO
- 50% Before dispatch (video proof required)
- 20% After installation (max 15 days post-install)

Note: Video proof requirement protects customer -
they see machine running before major payment.

WARRANTY:
- 24 months (extended warranty for EU market)
- Standard Indian market: 12 months
- Starts from pre-acceptance notification

LEAD TIME: 16-20 weeks

QUOTE VALIDITY: 2 weeks

COMPARISON - India vs Europe Pricing:
| Model | India (INR) | Europe (EUR) |
|-------|-------------|--------------|
| PF1-1515/S/A | ₹1.17 CR | ~€130K equiv |
| PF1-0810/S | ~₹57L equiv | €65K |

European pricing includes more scope (shipping, 
commissioning, extended warranty) but competitive
vs local European machine makers.""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="PF1-0810 Commercial Terms",
        summary="PF1-0810 EU: €65K all-in (ship+commission); 30-50-20 payment; 24-month warranty; 16-20 weeks",
        metadata={
            "topic": "pf1_eu_commercial_terms",
            "price": "EUR 65,000",
            "payment": "30-50-20",
            "warranty": "24 months"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Anatomic SITT PF1-0810/S Quote Ingestion")
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
