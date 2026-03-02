#!/usr/bin/env python3
"""
Ingest Motherson Phillips SPM Project

Special Purpose Machine for MRI interior parts using pressure forming.
Medical device application with polycarbonate materials.

Source: 2021 Jan Motherson Phillips SPM.pptx
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

SOURCE_FILE = "2021 Jan Motherson Phillips SPM.pptx"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from Motherson Phillips SPM project."""
    items = []

    # 1. Project Overview
    items.append(KnowledgeItem(
        text="""Motherson Phillips SPM Project - MRI Machine Interior Parts

CUSTOMER: Motherson Phillips (Tier 1 automotive/medical supplier)
APPLICATION: Interior parts for MRI (Magnetic Resonance Imaging) machines
DATE: January 2021

PROJECT SCOPE:
- Special Purpose Machine (SPM) for pressure thermoforming
- MRI machine interior shells and components
- Material: Polycarbonate (PC) - various thicknesses
- Complete manufacturing cell: Form → Cut → Glue → Check

MACHINE REQUIREMENTS:
| Equipment | Power | Bed Size | Price |
|-----------|-------|----------|-------|
| Pressure Thermoforming (50 ton) | 20 KW | 600x800mm | ₹85 Lakhs |
| 5 Axis Cutting Router | 10 KW | 600x800mm | ₹65 Lakhs |
| TOTAL MACHINES | | | ₹1.5 CR |

WHY PRESSURE FORMING FOR MRI:
1. Polycarbonate requires pressure for detail
2. Medical-grade surface finish needed
3. Dimensional accuracy for assembly
4. Non-magnetic material (critical for MRI)
5. Clear/optical grade PC available

KEY LEARNING:
This shows Machinecraft capability for medical device manufacturing
with special purpose machines - not just standard catalog machines.""",
        knowledge_type="case_study",
        source_file=SOURCE_FILE,
        entity="Motherson Phillips MRI Project Overview",
        summary="Motherson Phillips MRI SPM: Pressure forming + 5-axis cutting; PC material; ₹1.5CR machines",
        metadata={
            "topic": "motherson_mri_overview",
            "customer": "Motherson Phillips",
            "application": "MRI interior parts",
            "investment": "₹1.5 CR machines"
        }
    ))

    # 2. Process Flow
    items.append(KnowledgeItem(
        text="""MRI Parts Manufacturing Process - 4-Step Cell

COMPLETE MANUFACTURING CELL DESIGN:

STEP 1: THERMOFORMING SHELL
- Process: Pressure thermoforming (50 ton)
- Machine: SPM 600x800mm bed
- Materials: PC 0.5mm, 1mm, 1.5mm, 6mm thickness
- Multi-cavity tools for efficiency
- Cycle time: 2-8 mins depending on part/thickness

STEP 2: CUTTING HOLES & SLOTS
- Process: 5-axis CNC router cutting
- Individual fixtures per part
- Precision holes, slots, edge trimming
- Cycle time: 8-12 mins per part set
- DOG connector strips cut with parts

STEP 3: GLUING DOG CONNECTOR STRIPS
- Process: Manual adhesive application
- Loctite or similar adhesive
- Dedicated gluing fixture
- Cycle time: 5 mins
- 2 parts glued together with strip

STEP 4: CHECKING THE PART
- Process: Fit check in checking fixture
- Verifies mating of assembled parts
- Dedicated checking fixture per part
- Cycle time: 3-4 mins

TOTAL CYCLE TIME EXAMPLE (RFQ2):
- Forming: 8 mins
- Cutting: 12 mins
- Gluing: 5 mins
- Checking: 3 mins
- TOTAL: ~28 mins per part set

KEY INSIGHT: Complete turnkey cell design
Not just selling a machine - selling a manufacturing solution.""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="MRI Parts Process Flow",
        summary="MRI 4-step cell: Pressure form → 5-axis cut → Glue assembly → Check fit; 28min cycle",
        metadata={
            "topic": "mri_process_flow",
            "steps": ["Thermoform", "Cut", "Glue", "Check"],
            "cycle_time": "28 mins total"
        }
    ))

    # 3. Part Specifications
    items.append(KnowledgeItem(
        text="""MRI Interior Parts Specifications - Motherson Phillips

RFQ2 PARTS (Larger, thicker):

Part 1 & 2 (2-cavity tool):
- Size: 557 x 320 x 94 mm
- DOG strip: 557 x 42 x 86 mm
- Material: PC 6mm thick
- Frame size: 512 x 607 mm
- Sheet required: 562 x 657 mm
- Cycle time: 8 mins forming

Part 3 (Complex, 3 components):
- Component 1: 662 x 413 x 105 mm (1-cavity)
- Component 2: 659 x 422 x 167 mm (1-cavity) - deepest draw
- Component 3: 662 x 413 x 105 mm (1-cavity)
- Material: PC (thickness varies)

Part 5 (2-cavity):
- Component 1: 550 x 141 x 132 mm
- Component 2: 523 x 141 x 159 mm

RFQ1 PARTS (Smaller, thinner):

16 shell parts total:
- Typical size: 317 x 176 x 26 mm
- Material: PC 0.5mm, 1mm, 1.5mm
- Grouped by thickness for forming efficiency
- Frame size: 467 x 518 mm
- Sheet required: 517 x 568 mm
- Cycle time: 2 mins forming

MATERIAL VARIANTS:
- PC 0.5mm - thinnest shells
- PC 1mm - standard shells  
- PC 1.5mm - structural shells
- PC 6mm - thick structural parts
- KYDEX 1.5mm - alternative material
- HYZOD GP-PC Clear 4.78mm (3/16") - optical grade""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="MRI Parts Specifications",
        summary="MRI parts: PC 0.5-6mm; sizes 317x176 to 662x422mm; 16 shells RFQ1, complex assembly RFQ2",
        metadata={
            "topic": "mri_part_specs",
            "materials": ["PC 0.5mm", "PC 1mm", "PC 1.5mm", "PC 6mm", "KYDEX", "HYZOD"],
            "part_count": "16+ shells"
        }
    ))

    # 4. Tooling Investment
    items.append(KnowledgeItem(
        text="""MRI Project Tooling Investment - Motherson Phillips

RFQ2 TOOLING (Complex parts):

| Tool Type | Quantity | Group | Cost |
|-----------|----------|-------|------|
| Forming tools | 6 tools | Grouped | ₹47 Lakhs |
| Cutting fixtures | 8 fixtures | Individual | ₹29.5 Lakhs |
| Gluing fixtures | 4 fixtures | Per assembly | ₹11 Lakhs |
| Checking fixtures | 4 fixtures | Per assembly | ₹22 Lakhs |
| TOTAL RFQ2 | | | ₹109.5 Lakhs |

TOOLING DETAILS:
- 2-cavity forming tools where possible
- Individual cutting fixtures per part geometry
- DOG strips cut on same router with fixture
- Glue type (Loctite) determines fixture design

RFQ1 TOOLING (16 shell parts):

| Tool Type | Quantity | Cost |
|-----------|----------|------|
| Pressure forming tools | 16 shells (grouped) | ₹18 Lakhs |
| 5-axis cutting fixtures | 16 individual | ₹29 Lakhs |
| Checking fixtures | 16 individual | ₹21 Lakhs |
| TOTAL RFQ1 | | ₹68 Lakhs |

GROUPING STRATEGY:
- Forming tools grouped by material thickness
- Optimizes sheet utilization
- Reduces tool changes
- Same thickness parts formed together

TOTAL PROJECT TOOLING:
- RFQ2: ₹109.5 Lakhs
- RFQ1: ₹68 Lakhs
- GRAND TOTAL: ₹177.5 Lakhs (~₹1.78 CR)

COMPLETE PROJECT INVESTMENT:
- Machines: ₹1.5 CR
- Tooling: ₹1.78 CR
- TOTAL: ₹3.28 CR""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="MRI Tooling Investment",
        summary="MRI tooling: ₹1.09CR (RFQ2) + ₹0.68CR (RFQ1) = ₹1.78CR; total project ₹3.28CR with machines",
        metadata={
            "topic": "mri_tooling_costs",
            "rfq2_tools": "₹109.5 Lakhs",
            "rfq1_tools": "₹68 Lakhs",
            "total_project": "₹3.28 CR"
        }
    ))

    # 5. SPM Machine Specs
    items.append(KnowledgeItem(
        text="""Special Purpose Machine (SPM) Specifications - MRI Project

PRESSURE THERMOFORMING MACHINE:

Specification | Value
-------------|-------
Type | Pressure Forming
Force | 50 ton
Bed Size | 600 x 800 mm
Power | 20 KW
Price | ₹85 Lakhs

FEATURES REQUIRED:
- Pressure forming capability (not just vacuum)
- 50 ton force for 6mm PC forming
- Precision temperature control
- Clean room compatible design
- Medical-grade surface finish capability

WHY 50 TON PRESSURE:
- PC 6mm requires significant force
- Detail definition in medical parts
- Dimensional accuracy requirements
- Consistent wall thickness

5-AXIS CUTTING ROUTER:

Specification | Value
-------------|-------
Type | 5-Axis CNC Router
Bed Size | 600 x 800 mm
Power | 10 KW
Price | ₹65 Lakhs

FEATURES:
- 5-axis for complex contours
- Fixture-based part holding
- Precision hole positioning
- Edge trimming capability

MACHINE PAIRING LOGIC:
- Same bed size (600x800mm) for both machines
- Parts flow directly from former to cutter
- Fixtures designed for both operations
- Complete cell efficiency

SPM vs STANDARD MACHINE:
- Smaller bed (600x800 vs standard 1500mm+)
- Higher pressure (50 ton vs vacuum only)
- Medical application specific
- Turnkey solution approach""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="MRI SPM Specifications",
        summary="MRI SPM: 50-ton pressure former + 5-axis router; 600x800mm bed; ₹1.5CR combined",
        metadata={
            "topic": "mri_spm_specs",
            "former": "50 ton, 600x800mm, ₹85L",
            "router": "5-axis, 600x800mm, ₹65L"
        }
    ))

    # 6. Medical/MRI Market Application
    items.append(KnowledgeItem(
        text="""Medical Device Market - MRI Application Insights

WHY POLYCARBONATE FOR MRI:
1. NON-MAGNETIC - Critical for MRI environment
   - Metal components interfere with imaging
   - PC is completely non-ferrous
   
2. OPTICAL CLARITY - Clear variants available
   - HYZOD GP-PC Clear for transparent parts
   - Medical imaging compatibility
   
3. DIMENSIONAL STABILITY
   - Consistent performance in hospital environment
   - Temperature/humidity stable
   
4. IMPACT RESISTANCE
   - Patient safety consideration
   - Durable in clinical use

5. STERILIZATION COMPATIBLE
   - Can withstand cleaning protocols
   - Chemical resistance

PRESSURE FORMING ADVANTAGES FOR MEDICAL:
- Better detail than vacuum forming
- Tighter tolerances achievable
- Class A surface finish
- Consistent wall thickness
- Complex geometry capability

MARKET OPPORTUNITY:
- Medical imaging equipment (MRI, CT, X-ray)
- Diagnostic equipment housings
- Patient positioning devices
- Equipment enclosures
- Control panel housings

SUPPLIERS IN THIS SPACE:
- Motherson (Tier 1, India)
- Phillips Healthcare (OEM)
- Siemens Healthineers
- GE Healthcare

MACHINECRAFT POSITIONING:
- SPM capability for specific applications
- Complete cell design (not just forming)
- Tooling design expertise
- Lower cost than European SPM suppliers""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="MRI Medical Market Application",
        summary="MRI/medical: PC non-magnetic, clear, stable; pressure forming for detail; Phillips/Siemens/GE targets",
        metadata={
            "topic": "medical_mri_application",
            "material_benefits": ["Non-magnetic", "Clear", "Stable", "Impact resistant"],
            "oems": ["Phillips", "Siemens", "GE Healthcare"]
        }
    ))

    # 7. Sales Strategy - SPM Projects
    items.append(KnowledgeItem(
        text="""SPM Sales Strategy - Lessons from Motherson Phillips

PROJECT APPROACH:
1. Not selling a catalog machine
2. Designing a complete manufacturing solution
3. Machines + Tooling + Process = Turnkey cell

QUOTATION STRUCTURE:
| Item | Investment |
|------|------------|
| Pressure Former (SPM) | ₹85 Lakhs |
| 5-Axis Router | ₹65 Lakhs |
| Forming Tools | ₹47-65 Lakhs |
| Cutting Fixtures | ₹29 Lakhs |
| Gluing Fixtures | ₹11 Lakhs |
| Checking Fixtures | ₹21-22 Lakhs |

VALUE-ADD SERVICES:
- Process design (4-step cell)
- Cycle time estimation
- Tooling grouping optimization
- Sheet size optimization
- Complete fixture design

CUSTOMER BENEFITS:
- Single source responsibility
- Integrated solution
- Known cycle times
- Validated process
- Reduced project risk

PRICING STRATEGY:
- Machine margin: Standard
- Tooling margin: Higher (design value)
- Integration value: Premium justified

TARGET CUSTOMERS FOR SPM:
- Medical device manufacturers
- Aerospace interior suppliers
- Electronics enclosure makers
- Defense equipment suppliers
- Any application needing:
  - Pressure forming
  - Specialized materials
  - Tight tolerances
  - Complete cell solution

FOLLOW-UP OPPORTUNITY:
- Recurring tooling orders
- Spare parts
- Process optimization
- Capacity expansion machines""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="SPM Sales Strategy",
        summary="SPM strategy: Turnkey cell (machines+tooling+fixtures); ₹3.3CR project; single source value",
        metadata={
            "topic": "spm_sales_strategy",
            "approach": "turnkey solution",
            "total_project": "₹3.28 CR"
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Motherson Phillips SPM Project Ingestion")
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
