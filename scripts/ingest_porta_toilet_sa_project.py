#!/usr/bin/env python3
"""
Ingest Porta Toilet Project SA Tyrone Offer (July 2022)

Comprehensive turnkey project quote for porta-toilet production.
Critical reference for tooling costs, project structure, and quoting.

Client: Moreki Solutions ZA (Tyrone Palmer)
Total Project: ~$1,057,300 (machines + tooling)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Porta Toilet Project SA Tyrone Offer from Machinecraft Thermoforming July 2022 01.docx.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the Porta Toilet project quote."""
    items = []

    # 1. Project Overview
    items.append(KnowledgeItem(
        text="""Porta Toilet Thermoforming Project Overview

QUOTE: 2022070401 (July 4, 2022)
CLIENT: Tyrone Palmer, Moreki Solutions ZA
LOCATION: South Africa
APPLICATION: Porta-Toilet housing production

PROJECT SCOPE:
1. Vacuum Forming Machine (PF1-1224) x 2
2. CNC Trimming Router Machine (RT-4A-1224) x 2
3. US (Ultrasonic) Welding System x 4 guns
4. Moulds for Vacuum Forming (Proto + Serial)
5. Fixtures for CNC Trimming
6. Fixtures for US Welding

PORTA-TOILET PARTS TO PRODUCE:
- Wall left (WL)
- Wall right (WR)
- Wall back (WB)
- Roof (RF)
- Door A-Surface & B-Surface (2-sheet thermoformed)
- Door Frame A-Surface & B-Surface (2-sheet thermoformed)

PROCESS NOTES:
- Walls: Single-sheet vacuum forming (standard)
- Door & Door Frame: 2-sheet thermoformed (higher strength needed)
- Material: HDPE

TOTAL PROJECT VALUE:
- Machines: $845,000
- Tooling: $212,300
- TOTAL: $1,057,300 USD (FOB India)""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Porta Toilet Project SA",
        summary="Porta Toilet SA: $1.05M turnkey (2x PF1 + 2x CNC + tooling), HDPE parts, Moreki Solutions ZA",
        metadata={
            "topic": "project_overview",
            "quote_number": "2022070401",
            "client": "Moreki Solutions ZA",
            "total_value_usd": 1057300
        }
    ))

    # 2. Machine Pricing
    items.append(KnowledgeItem(
        text="""Porta Toilet Project: Machine Pricing Breakdown

MACHINE A: THERMOFORMING MACHINE PF1-1224
- Unit Price: $350,000 USD
- Quantity: 2
- Subtotal: $700,000 USD
- Features: Automatic Sheet Loading/Unloading Robot System

PF1-1224 SPECIFICATIONS:
- Max Forming Area: 1200 x 2400 mm
- Max Stroke Z: 500 mm
- Heater Load: 102 kW
- Servo Load: 38 kW
- Total Connected Load: 140 kW
- Vacuum Pump: 300 m³/hr
- Heater Type: IR Quartz (energy saving)
- Heater Size: 245 x 63 mm
- Heater Grid: 10 x 12
- Control: Mitsubishi PLC/HMI/Servos
- Tool Weight Capacity: 1000 kg (bottom), 350 kg (top)

MACHINE B: 4-AXIS CNC ROUTER RT-4A-1224
- Unit Price: $50,000 USD
- Quantity: 2
- Subtotal: $100,000 USD

RT-4A-1224 SPECIFICATIONS:
- Working Area: 1300 x 2400 mm
- 5-Axis Mode: 1200 x 1400 mm
- Connected Load: 30 kW
- Vacuum Pump: 100 m³/hr
- Spindle: 9 kW HSD/Hiteco (18,000 rpm)
- ATC: 6-position automatic
- Controller: Syntec Taiwan
- Servos: Yaskawa Japan

MACHINE C: US WELDING HAND-GUN FH 413
- Unit Price: $15,000 USD
- Quantity: 4
- Subtotal: $45,000 USD (note: should be $60,000 at 4x but quote shows $45,000)

MACHINES TOTAL: $845,000 USD""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Project Machine Pricing",
        summary="Machines: PF1-1224 $350K x2, RT-4A-1224 $50K x2, US Gun $15K x4 = $845K total",
        metadata={
            "topic": "machine_pricing",
            "pf1_1224_price": 350000,
            "cnc_router_price": 50000,
            "us_gun_price": 15000
        }
    ))

    # 3. Tooling Types Explained
    items.append(KnowledgeItem(
        text="""Porta Toilet Project: Tooling Types & Philosophy

THREE TYPES OF TOOLING REQUIRED:

1. VACUUM FORMING TOOLS (VFT)
   Two sub-types:
   
   a) Proto MDF Tool (P):
      - Made from artificial wood (MDF)
      - Low cost
      - Can run up to 10 samples
      - Purpose: Prototyping only
   
   b) Serial Aluminum Tool (S):
      - Made from special cast material (ALWA Germany)
      - Casting compound poured into proto pattern
      - Note: Slight shrinkage occurs
      - Option: Make proto slightly bigger to compensate
      - Purpose: Production runs

2. CNC TRIMMING FIXTURES (CTF)
   - Made from artificial wood
   - Vacuum pads to hold plastic part
   - Purpose: Hold part during CNC trimming

3. US WELDING FIXTURES (UWF)
   - Made from artificial wood
   - Toggle clamps to hold 2 plastic parts together
   - Purpose: Hold parts during ultrasonic welding

TOOL NAMING CONVENTION:
- VFT = Vacuum Forming Tool
- CTF = CNC Trimming Fixture
- UWF = US Welding Fixture
- _P = Proto (MDF)
- _S = Serial (Aluminum)
- WL/WR/WB = Wall Left/Right/Back
- RF = Roof
- D = Door
- DF = Door Frame""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Tooling Types",
        summary="Tool types: VFT (Proto MDF vs Serial Aluminum), CTF (trimming), UWF (welding fixtures)",
        metadata={
            "topic": "tooling_types",
            "vft_proto_material": "MDF",
            "vft_serial_material": "ALWA Aluminum cast"
        }
    ))

    # 4. Proto Tooling Costs
    items.append(KnowledgeItem(
        text="""Porta Toilet Project: Proto Tooling Costs (MDF)

PROTO VACUUM FORMING TOOLS (VFT_P):
Purpose: Up to 10 samples for prototyping

| Tool Code | Part          | Unit Price (USD) | Qty | Total    |
|-----------|---------------|------------------|-----|----------|
| VFT_WL_P  | Wall Left     | $1,900          | 1   | $1,900   |
| VFT_WR_P  | Wall Right    | $1,900          | 1   | $1,900   |
| VFT_WB_P  | Wall Back     | $1,900          | 1   | $1,900   |
| VFT_RF_P  | Roof          | $3,600          | 1   | $3,600   |
| VFT_D_P   | Door          | $4,000          | 1   | $4,000   |
| VFT_DF_P  | Door Frame    | $1,400          | 1   | $1,400   |

PROTO TOOLING SUBTOTAL: $14,700 USD

PRICING LOGIC:
- Simple walls (WL, WR, WB): ~$1,900 each
- Roof (larger/complex): $3,600 (89% premium)
- Door (2-sheet, complex): $4,000 (111% premium)
- Door Frame (smaller): $1,400 (26% discount)

PROTO TOOL CHARACTERISTICS:
- Material: MDF (artificial wood)
- Lifespan: ~10 samples
- Lead time: Faster than aluminum
- Purpose: Design validation before serial investment""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Proto Tooling Costs",
        summary="Proto tools (MDF): walls $1.9K, roof $3.6K, door $4K, frame $1.4K = $14.7K total for prototyping",
        metadata={
            "topic": "proto_tooling_costs",
            "wall_cost": 1900,
            "roof_cost": 3600,
            "door_cost": 4000,
            "frame_cost": 1400,
            "total": 14700
        }
    ))

    # 5. Serial Tooling Costs
    items.append(KnowledgeItem(
        text="""Porta Toilet Project: Serial Tooling Costs (Aluminum)

SERIAL VACUUM FORMING TOOLS (VFT_S):
Purpose: Production runs (ALWA Germany aluminum cast)

| Tool Code | Part          | Unit Price (USD) | Qty | Total     |
|-----------|---------------|------------------|-----|-----------|
| VFT_WL_S  | Wall Left     | $8,500          | 2   | $17,000   |
| VFT_WR_S  | Wall Right    | $8,500          | 2   | $17,000   |
| VFT_WB_S  | Wall Back     | $8,500          | 2   | $17,000   |
| VFT_RF_S  | Roof          | $19,000         | 2   | $38,000   |
| VFT_D_S   | Door          | $11,000         | 2   | $22,000   |
| VFT_DF_S  | Door Frame    | $4,200          | 2   | $8,400    |

SERIAL TOOLING SUBTOTAL: $119,400 USD

SERIAL vs PROTO PRICE MULTIPLIERS:
- Wall tools: $8,500 / $1,900 = 4.5x proto price
- Roof: $19,000 / $3,600 = 5.3x proto price
- Door: $11,000 / $4,000 = 2.75x proto price
- Door Frame: $4,200 / $1,400 = 3.0x proto price
- Average multiplier: ~3.5-5x from proto to serial

WHY 2 SETS OF SERIAL TOOLS?
- 2 thermoforming machines in project
- Each machine needs its own tool set
- Enables parallel production""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Serial Tooling Costs",
        summary="Serial tools (Aluminum): walls $8.5K, roof $19K, door $11K = $119.4K (3.5-5x proto prices)",
        metadata={
            "topic": "serial_tooling_costs",
            "wall_cost": 8500,
            "roof_cost": 19000,
            "door_cost": 11000,
            "frame_cost": 4200,
            "total": 119400,
            "multiplier_from_proto": "3.5-5x"
        }
    ))

    # 6. CNC Trimming Fixture Costs
    items.append(KnowledgeItem(
        text="""Porta Toilet Project: CNC Trimming Fixture Costs

CNC TRIMMING FIXTURES (CTF):
Purpose: Hold thermoformed parts for CNC trimming
Material: Artificial wood + vacuum pads

| Tool Code | Part          | Unit Price (USD) | Qty | Total     |
|-----------|---------------|------------------|-----|-----------|
| CTF_WL    | Wall Left     | $3,700          | 2   | $7,400    |
| CTF_WR    | Wall Right    | $3,700          | 2   | $7,400    |
| CTF_WB    | Wall Back     | $3,700          | 2   | $7,400    |
| CTF_RF    | Roof          | $9,500          | 2   | $19,000   |
| CTF_D     | Door          | $7,200          | 2   | $14,400   |
| CTF_DF    | Door Frame    | $2,700          | 2   | $5,400    |

CNC FIXTURES SUBTOTAL: $61,000 USD

PRICING LOGIC:
- Simple walls: $3,700 each (base price)
- Roof (larger): $9,500 (157% premium - 2.57x wall)
- Door (complex): $7,200 (95% premium - 1.95x wall)
- Door Frame (smaller): $2,700 (27% discount)

CTF vs VFT SERIAL RATIO:
- Wall: $3,700 / $8,500 = 44% of VFT cost
- Roof: $9,500 / $19,000 = 50% of VFT cost
- Door: $7,200 / $11,000 = 65% of VFT cost
- Average: CTF ~50% of serial VFT cost""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="CNC Fixture Costs",
        summary="CNC trimming fixtures: walls $3.7K, roof $9.5K, door $7.2K = $61K (~50% of VFT serial cost)",
        metadata={
            "topic": "cnc_fixture_costs",
            "wall_cost": 3700,
            "roof_cost": 9500,
            "door_cost": 7200,
            "total": 61000,
            "ratio_to_vft": "50%"
        }
    ))

    # 7. US Welding Fixture Costs
    items.append(KnowledgeItem(
        text="""Porta Toilet Project: Ultrasonic Welding Fixture Costs

US WELDING FIXTURES (UWF):
Purpose: Hold 2 plastic parts together for ultrasonic welding
Material: Artificial wood + toggle clamps
Only needed for: Door and Door Frame (2-sheet thermoformed parts)

| Tool Code | Part          | Unit Price (USD) | Qty | Total     |
|-----------|---------------|------------------|-----|-----------|
| UWF_D     | Door          | $6,500          | 2   | $13,000   |
| UWF_DF    | Door Frame    | $2,100          | 2   | $4,200    |

US WELDING FIXTURES SUBTOTAL: $17,200 USD

WHY ONLY DOOR & DOOR FRAME?
- Walls and roof are single-sheet thermoformed
- Door/Door Frame need 2-sheet process for strength
- US welding fuses 2 sheets together at weld points

UWF PRICING LOGIC:
- Door fixture: $6,500 (complex, larger)
- Door Frame fixture: $2,100 (simpler, smaller)
- Ratio: Door is 3.1x Door Frame cost

COMPLETE TOOLING SUMMARY:
- Proto VFT: $14,700
- Serial VFT: $119,400
- CTF: $61,000
- UWF: $17,200
- TOTAL TOOLING: $212,300 USD""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="US Welding Fixture Costs",
        summary="US welding fixtures: door $6.5K, frame $2.1K = $17.2K (only for 2-sheet parts)",
        metadata={
            "topic": "us_welding_fixture_costs",
            "door_cost": 6500,
            "frame_cost": 2100,
            "total": 17200
        }
    ))

    # 8. Commercial Terms & Shipping
    items.append(KnowledgeItem(
        text="""Porta Toilet Project: Commercial Terms

INCOTERMS: FOB India (Nhava Sheva port)

NOT INCLUDED IN PRICE:
- Shipping India to South Africa
- Local customs clearance
- Local VAT payment
- Local transport (port to site)
- Packaging cost

INCLUDED IN PRICE:
- Commissioning by 2 Machinecraft engineers
- Client assistance required for commissioning

SHIPPING CONTAINER ESTIMATE:
- Thermoforming Machines: 2 x 40ft HQ containers
- CNC Routers: 1 x 40ft container
- US Welding + All Tools: 1 x 40ft container
- TOTAL: 4 x 40ft containers
- Note: Final count confirmed ~30% into project

PAYMENT TERMS:
- 30% Advance
- 25% After 30 days (on progress)
- 25% After 60 days (on progress)
- 15% After final trial (before dispatch)
- 5% After installation (within 2 weeks)

LEAD TIME: ~24 weeks after technical/commercial clarification
- May vary due to: chip crisis, COVID, war, supply chain issues

WARRANTY: 12 months from pre-acceptance date

QUOTE VALIDITY: 2 weeks""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Project Commercial Terms",
        summary="FOB India, 4x 40ft containers, 30/25/25/15/5 payment, 24 weeks lead, 12 mo warranty",
        metadata={
            "topic": "commercial_terms",
            "incoterms": "FOB",
            "containers": 4,
            "lead_time_weeks": 24,
            "warranty_months": 12
        }
    ))

    # 9. Machine Technical Features
    items.append(KnowledgeItem(
        text="""PF1-1224 Technical Features (Porta Toilet Project)

HEATER SYSTEM:
- Type: IR Quartz (energy saving)
- Configuration: Sandwich (top & bottom)
- Top heaters: 500W each
- Bottom heaters: 300W each
- Grid layout: 10 x 12 elements
- Control: SSR controlled by PLC (2:1 ratio)
- Temp sensing: 1x Raytek pyrometer (center)
- Max sheet thickness: 10mm

MACHINE TYPE: Open-Type (American concept)
- Suited for HDPE forming
- Open chamber design

SHEET HANDLING:
- MS welded fixed frames (per sheet size)
- Frames provided for: walls, door frame, door, roof
- Bottom frame: C-clamp bolted by operator
- Top frame: Adjustable cross-members (manual)
- Automatic sheet loader with separator
- Servo-driven up/down & in/out mechanism
- Pneumatic pusher for part ejection

MOULD TABLE:
- Bottom movement: Electric servo (0 to max stroke)
- Soft touch & soft release capability
- Tool weight: up to 1000 kg
- Tool clamping: Pneumatic (quick)
- Base plate: Aluminum chequered
- Thermoregulation provision for heating/cooling

PLUG ASSIST:
- Movement: Pneumatic with DC motor height adjust
- Weight capacity: 350 kg
- Clamping: Bolts on upper platen

COOLING:
- Type: Centrifugal fans (ducted, centrally connected)
- Capacity: 26 m³/hr each
- Quantity: 6 fans
- Temp sensing: Raytek pyrometer for cooled part

VACUUM SYSTEM:
- Pump: 300 m³/hr (Busch/Becker Germany)
- Type: Oil-lubricated rotary vane
- Features: Auto air-ejection, Festo proportional servo valve""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="PF1-1224 Features",
        summary="PF1-1224: 1200x2400mm, IR quartz sandwich heaters, auto loader, servo table, for HDPE",
        metadata={
            "topic": "pf1_1224_features",
            "forming_area": "1200x2400mm",
            "heater_type": "IR Quartz",
            "tool_capacity_kg": 1000
        }
    ))

    # 10. Component Brands
    items.append(KnowledgeItem(
        text="""Porta Toilet Project: Component Brands Specified

PF1-1224 THERMOFORMER COMPONENTS:
- PLC, HMI & Servos: Mitsubishi Japan
- Pneumatics: FESTO / SMC
- Cooling Blowers: EBM Papst
- Light Guard & Sensors: Sick / P+F / Autonics / Omron
- Vacuum Pump: Busch/Becker Germany
- Control Panel: Rittal / Hoffman
- Heater Elements: TQS / Ceramicx
- Switchgears: Eaton / Siemens
- Gearbox: SEW Germany / Bonfiglioli

RT-4A-1224 CNC ROUTER COMPONENTS:
- Controller: Syntec Taiwan
- Spindle: HSD/Hiteco Italy
- Pneumatics: SMC Japan
- Sensors: Omron / P+F / Sick
- Vacuum Pump: Becker Germany
- Servo Motors: Yaskawa Japan
- Gearbox: Shimpo Japan

NOTE ON SUBSTITUTIONS:
"In-case any item is not available due to abnormal lead time then 
the item of similar quality / brand will be used"

This quote demonstrates Machinecraft's premium component sourcing:
- Japanese controls (Mitsubishi, Yaskawa)
- German vacuum (Busch/Becker)
- Italian spindles (HSD/Hiteco)
- European pneumatics (Festo, SMC)""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="Component Brands",
        summary="Premium brands: Mitsubishi controls, Busch vacuum, HSD spindle, Festo pneumatics",
        metadata={
            "topic": "component_brands"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Porta Toilet Project SA Ingestion")
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
