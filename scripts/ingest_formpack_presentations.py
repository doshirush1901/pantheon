#!/usr/bin/env python3
"""
Ingest Formpack Presentations (Oct 2021 & Mar 2023)

Formpack is Machinecraft's sister company - a subcontract thermoformer.
Shows vertically integrated manufacturing and reference projects.

Sources:
- Formpack PPT Oct 2021.pdf
- Formpack_Prensentation General_30Mar2023.pdf
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

SOURCE_FILE = "Formpack Presentations (Oct 2021 & Mar 2023)"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from Formpack presentations."""
    items = []

    # 1. Company Overview
    items.append(KnowledgeItem(
        text="""Formpack - Machinecraft's Sister Company Overview

RELATIONSHIP: Formpack is Machinecraft's sister company AND customer
- Uses Machinecraft machines for production
- Serves as reference site for potential customers
- Demonstrates vertical integration model

COMPANY DETAILS:
- Name: Formpack (+ Indu Thermoformers)
- Location: Near Mumbai, India
- Website: www.formpack.in
- Contact: +91 8291296791, info@formpack.in

GROUP OF COMPANIES:
1. FORMPACK - Vacuum formed plastic parts & mould making
2. INDU THERMOFORMERS - Plastic sheets, subcontracting
3. MACHINECRAFT TECHNOLOGIES - Machines (vacuum forming, cutting routers, extruders)
4. FRIMO (India Representative) - European machinery

VISION: "Innovations in Thermoforming with Cost-effectiveness"

VALUE PROPOSITION:
- One-stop solution for thermoforming products
- Build own tools, extrude own sheets
- Faster design and development
- Complete in-house solutions: Design → Prototype → Production
- 35+ years experience in plastic sheet extrusion and thermoforming""",
        knowledge_type="organization",
        source_file=SOURCE_FILE,
        entity="Formpack Company Overview",
        summary="Formpack: Machinecraft sister company; subcontract thermoformer; Mumbai; 35+ years experience",
        metadata={
            "topic": "formpack_overview",
            "relationship": "Sister company & customer",
            "location": "Mumbai, India"
        }
    ))

    # 2. Management Team
    items.append(KnowledgeItem(
        text="""Formpack/Machinecraft Group - Management Team

DOSHI FAMILY BUSINESS:

DEEPAK DOSHI
- Role: Managing Director (Formpack)
- Also: Chief of Finance

NIRMAL DOSHI
- Role: Technical Director (Subcontracting & Sheet Extrusion)
- Also: Chief of Technik

RAJESH DOSHI
- Role: Technical Director (Machinery & Moulds)

MANAN DOSHI
- Role: Head (Engineering & Design)

RUSHABH DOSHI
- Role: Head (Sales & Marketing)
- Focus: Machinecraft machine sales globally

AKASH DOSHI
- Role: Key Account Manager
- Focus: Formpack customer accounts

ALOK DOSHI
- Role: Key Account Manager
- Focus: Formpack customer accounts

ORGANIZATIONAL STRUCTURE:
- Family-owned business with clear role separation
- Technical leadership (Nirmal, Rajesh, Manan)
- Commercial leadership (Deepak, Rushabh, Akash, Alok)
- Cross-functional collaboration between Formpack & Machinecraft""",
        knowledge_type="organization",
        source_file=SOURCE_FILE,
        entity="Formpack Management Team",
        summary="Doshi family: Deepak (MD), Nirmal (Tech), Rajesh (Moulds), Rushabh (Sales), Akash/Alok (Accounts)",
        metadata={
            "topic": "formpack_management",
            "family": "Doshi",
            "key_people": ["Deepak", "Nirmal", "Rajesh", "Manan", "Rushabh", "Akash", "Alok"]
        }
    ))

    # 3. Manufacturing Capabilities
    items.append(KnowledgeItem(
        text="""Formpack Manufacturing Capabilities - Complete Process

1. SHEET EXTRUSION:
- Max Sheet Width: 2 meters
- Configuration: 3 Layer ABA
- Capacity: 400 kg/hr extruder
- In-house material blending
- Materials: ABS, ABS/ASA, PS, HIPS, PE, HDPE, PP
- Partnership with MP3 Italy for ABS/PMMA

2. THERMOFORMING:
- Size Range: 400 x 300 mm to 4250 x 2500 mm (L x W)
- Machines: Machinecraft (European Design)
- All closed chamber type with pre-blowing
- IR Heating (Quartz)
- Servo-Pneumatic drive
- Energy monitoring
- IoT controlled - Industry 4.0
- Materials: ABS, ASA, PMMA, PC, HIPS, HDPE, PP, PET, PETG, ABS FR
- Thickness range: 1 mm to 10 mm

3. CNC TRIMMING:
- 4-axis: Max 3000 x 1500 mm
- 3-axis: Max 4500 x 2200 mm
- Advanced CAD/CAM (Siemens NX)
- In-house fixture design & manufacturing

4. SECONDARY OPERATIONS:
- Ultrasonic welding (US technology)
- In-house paint booth
- Assembly
- Printing & labeling
- Packaging

5. TOOLING:
- In-house mould making
- Aluminium tooling
- Temperature controlled tools (thermoregulation)
- Quick turnaround""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Formpack Manufacturing Capabilities",
        summary="Formpack: Extrusion (2m, 400kg/hr) → Thermoform (4250x2500mm) → CNC (4-axis) → Assembly",
        metadata={
            "topic": "formpack_capabilities",
            "max_size": "4250 x 2500 mm",
            "processes": ["Extrusion", "Thermoforming", "CNC", "Welding", "Painting"]
        }
    ))

    # 4. Reference Projects - Automotive/CV
    items.append(KnowledgeItem(
        text="""Formpack Reference Projects - Automotive & Commercial Vehicles

CONSTRUCTION VEHICLES:
- Materials: ASA, ABS
- Parts: Exterior panels, covers
- Customers: Major construction equipment OEMs

BUS EXTERIOR PARTS:
- Materials: ASA, ABS
- Parts: Body panels, fairings
- Application: Public transport buses

COMMERCIAL VEHICLE PANELS:
- Materials: ABS
- Size: Large panels up to 4,000 x 2,000 mm
- Application: Truck/CV exterior panels

EV GOLF CARTS:
- Materials: ASA
- Parts: Body panels
- Application: Electric golf cart exteriors

EV SCOOTERS:
- Materials: ABS/PMMA
- Parts: Body panels with Class A finish
- Application: Electric scooter exteriors

RAILWAY PROJECTS:
- Materials: ABS FR (flame retardant), PC
- Application: Train interior panels
- Compliance: Fire safety standards

KEY LEARNING:
Formpack demonstrates that Machinecraft machines
can produce professional-grade automotive parts
for global OEMs. Strong reference for machine sales.""",
        knowledge_type="case_study",
        source_file=SOURCE_FILE,
        entity="Formpack Automotive Projects",
        summary="Formpack auto: Construction vehicles, buses, CV panels (4000x2000mm), EV, railway (ABS FR)",
        metadata={
            "topic": "formpack_automotive_projects",
            "segments": ["Construction", "Bus", "CV", "EV", "Railway"]
        }
    ))

    # 5. Reference Projects - Industrial
    items.append(KnowledgeItem(
        text="""Formpack Reference Projects - Industrial & Energy

WINDMILL PARTS - VESTAS:
- Material: ABS
- Size: XL - 4,200 x 2,200 mm (largest parts)
- Application: Nacelle covers, spinner components
- Customer: Vestas (global wind turbine leader)

WINDMILL PARTS - GE:
- Material: ABS
- Application: Wind turbine components
- Customer: GE Renewable Energy

MACHINE COVERS:
- Materials: ABS, ASA, ABS/PMMA
- Application: Industrial equipment housings
- Features: Various finishes and textures

MACHINE DUCTS:
- Materials: PETG, PC, ABS
- Application: Air handling, cable management
- Features: Transparent options (PETG, PC)

MATERIAL HANDLING TRAYS:
- Materials: HDPE, ABS
- Application: Industrial logistics
- Features: Durable, stackable

KEY INSIGHT:
Vestas and GE projects demonstrate:
- XL forming capability (4200mm+)
- Global OEM quality standards
- Renewable energy sector experience
- Strong reference for wind energy customers""",
        knowledge_type="case_study",
        source_file=SOURCE_FILE,
        entity="Formpack Industrial Projects",
        summary="Formpack industrial: Vestas/GE windmill XL parts (4200x2200mm), machine covers, ducts",
        metadata={
            "topic": "formpack_industrial_projects",
            "key_customers": ["Vestas", "GE"],
            "max_size": "4200 x 2200 mm"
        }
    ))

    # 6. Reference Projects - Consumer & Other
    items.append(KnowledgeItem(
        text="""Formpack Reference Projects - Consumer & Other Segments

APPLIANCES:
- Materials: HIPS, ABS
- Application: Refrigerator liners, appliance housings
- Features: Food-grade options

LUGGAGE:
- Materials: ABS+PC, ABS, PC
- Application: Hard-shell luggage
- Features: Impact resistant, lightweight

AGRICULTURAL TRAYS:
- Materials: HIPS, ABS, HDPE
- Application: Seed trays, nursery trays
- Features: UV resistant, durable

ADVERTISEMENT/SIGNAGE:
- Materials: HIPS, ABS, PETG
- Application: POP displays, signage
- Features: Backlit options (PETG)

MATERIALS SUMMARY:

| Material | Applications |
|----------|-------------|
| ABS | Universal, most applications |
| ASA | UV stable outdoor (CV, windmill) |
| ABS/PMMA | Class A automotive |
| ABS FR | Railway, flame retardant |
| PC | Clear, impact resistant |
| PETG | Clear, signage |
| HIPS | Low cost, appliances |
| HDPE | Chemical resistant, trays |
| PP | Flexible, low cost |
| PLA | Biopolymer option |

SHEET FEATURES:
- UV Resistant
- Fire Resistant
- Different textures/embossing
- Glossy or low gloss surface""",
        knowledge_type="case_study",
        source_file=SOURCE_FILE,
        entity="Formpack Consumer Projects",
        summary="Formpack consumer: Appliances, luggage (ABS+PC), agriculture, signage; 10+ material options",
        metadata={
            "topic": "formpack_consumer_projects",
            "segments": ["Appliances", "Luggage", "Agriculture", "Signage"]
        }
    ))

    # 7. Sales Value - Reference Site
    items.append(KnowledgeItem(
        text="""Formpack as Machinecraft Sales Tool

VALUE AS REFERENCE SITE:

1. PROOF OF CAPABILITY:
- Live production facility
- Can show machines in operation
- Real parts, real customers
- Quality evidence for prospects

2. MACHINE DEMONSTRATION:
- All Machinecraft machine types in use
- XL machines (4250x2500mm)
- Compact machines
- CNC routers (3-axis, 4-axis)
- Sheet extruders

3. VERTICAL INTEGRATION PROOF:
- Shows complete process capability
- Extrusion → Forming → Cutting → Assembly
- Customers can see entire workflow

4. GLOBAL OEM REFERENCES:
- Vestas, GE (Wind Energy)
- Major CV OEMs
- Railway customers
- EV manufacturers

5. TECHNOLOGY SHOWCASE:
- Closed chamber forming
- IR quartz heating
- Servo control
- Industry 4.0 / IoT
- Temperature controlled tooling
- Aluminium tools

SALES USE:
- Invite prospects to visit Formpack
- Show live production
- Demonstrate quality standards
- Prove Machinecraft machine capability
- Build confidence before purchase

LOCATION ADVANTAGE:
- Near Mumbai (easy access)
- International airport proximity
- Can combine with Machinecraft factory visit""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Formpack Sales Reference Value",
        summary="Formpack as sales tool: Live reference site, XL machines, global OEM parts, near Mumbai",
        metadata={
            "topic": "formpack_sales_value",
            "use": "Reference site for machine sales",
            "key_refs": ["Vestas", "GE", "CV OEMs", "Railway"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Formpack Presentations Ingestion")
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
