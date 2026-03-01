#!/usr/bin/env python3
"""
Ingest SPE 2018 Agricultural Equipment Study

John Deere Materials Engineer presentation on thermoforming applications
in agriculture equipment. Shows what PF1 can make for agri market.

Note: Twin sheet applications shown here require specialized equipment,
but all single-sheet thermoforming can be done on PF1.

Source: SPE-2018-Ag-Equip-study-in-plastic-post.pdf
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

SOURCE_FILE = "SPE-2018-Ag-Equip-study-in-plastic-post.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from SPE agriculture study."""
    items = []

    # 1. Market Overview
    items.append(KnowledgeItem(
        text="""Agricultural Equipment Thermoforming Market - SPE 2018 Study

SOURCE: John Deere Materials Engineer (Greg McCunn) presentation
MARKETS: USA, Europe (dominant agricultural equipment regions)

KEY INSIGHT: Thermoforming is replacing traditional processes in agri equipment:
- Replaces: RTM + gel coat, SMC, sheet metal stamping
- Benefits: Lower tooling cost, molded-in color (no paint), lighter weight

MAJOR OEMs USING THERMOFORMING:
- John Deere (USA) - combines, tractors, balers
- Hagie (USA) - sprayers
- Kubota (Italy/Japan) - round balers
- Claas (Germany) - round balers

KEY APPLICATIONS (PF1-compatible single sheet):
1. Sprayer hoods and grill inserts
2. Combine side panels and styling panels
3. Tractor front hoods
4. Baler styling panels (outer skin)
5. Engine compartment panels
6. Fenders and fairings

MATERIALS USED:
- ABS+PMMA (cap sheet for Class A appearance)
- Diamond ABS (A.Schulman - high heat for engine areas)
- ASA (UV stable)
- Senosan AM50C (excellent DOI - depth of image)

POST-PROCESS REINFORCEMENT:
Many parts use thermoformed skin + reinforcement bonded on B-side:
- Steel plates/brackets bonded with adhesive
- PUR (polyurethane) with glass fiber sprayed on back
- Glass mat + UP resin (RTM backing)
This is common practice for large agri panels.""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Agri Equipment Market Overview",
        summary="Agri thermoforming: John Deere, Hagie, Kubota, Claas; replaces RTM/SMC; ABS+PMMA dominant",
        metadata={
            "topic": "agri_market_overview",
            "oems": ["John Deere", "Hagie", "Kubota", "Claas"],
            "markets": ["USA", "Europe"]
        }
    ))

    # 2. Single Sheet Applications (PF1-compatible)
    items.append(KnowledgeItem(
        text="""PF1-Compatible Agri Applications - Single Sheet Thermoforming

These applications can be made on Machinecraft PF1 machines:

1. SPRAYER HOODS & GRILL INSERTS
   - Example: Hagie Sprayer grill insert
   - Material: A.Schulman Diamond ABS (high heat)
   - Replaces: RTM + gel coat (significant cost savings)
   - Features: Metal attachment features, adhesive mounting
   - Size: Medium-large format

2. COMBINE STYLING PANELS
   - Side panels, front hoods, rear covers
   - Material: ABS/PMMA for Class A appearance
   - Construction: Thermoform + steel reinforcement bonded on B-side
   - Design: Multiple smaller panels bolt together for large assemblies

3. TRACTOR FRONT HOODS (Upper panels)
   - Material: ABS/PMMA outer surface
   - Process: Thermoform + S-RIM/LFI backing
   - Note: PUR with glass fiber backing hides through ABS/PMMA
   - PF1 makes the thermoformed skin; backing is post-process

4. BALER OUTER SKINS
   - Material: ABS/PMMA, excellent DOI (depth of image)
   - Construction: Single sheet + steel reinforcement glued
   - Kubota, Claas, John Deere applications

5. ENGINE COMPARTMENT COVERS
   - Grain tank covers (outer skin)
   - Material: ABS+PMMA (UV stable)
   - Features: Hat sections for rigidity, drain holes

SIZING FOR PF1:
- Most panels: 1500-2500mm range
- Large assemblies: Multiple panels bolted together
- PF1-5028 or similar ideal for largest single panels""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="PF1 Agri Single Sheet Apps",
        summary="PF1 agri apps: Sprayer hoods (Diamond ABS), combine panels, tractor hoods, baler skins",
        metadata={
            "topic": "pf1_agri_single_sheet",
            "applications": ["Sprayer hood", "Combine panel", "Tractor hood", "Baler skin"]
        }
    ))

    # 3. TEC Process (Thermoform + Composite)
    items.append(KnowledgeItem(
        text="""TEC Process - Thermoform + Composite Reinforcement

TEC = Tooless Engineering Composite
Supplier: Plastics Unlimited, Preston IA (USA)

PROCESS:
1. Thermoform ABS+PMMA outer skin on PF1
2. Apply fiberglass mat + UP resin backing
3. Optional: Balsa wood core for stiffness
4. Low pressure RTM process for backing

SANDWICH CONSTRUCTION:
- CET PMMA film (cap)
- Select ABS (structural)
- UP Resin layer
- Fiberglass mat
- UP Resin layer
- Fiberglass mat

APPLICATIONS:
- Grain tank covers (thinner profile than twin sheet)
- Powerfold grain tank covers
- Combine cooling air intake panels

BENEFITS:
- No A-surface hardware (clean appearance)
- Metal brackets molded in
- Foam core stiffening sections molded in
- Steel plate mounting supports molded in
- Low pressure process (low overhead)
- Cost effective tooling

KEY EXAMPLE: John Deere Combine MY2005
- PMMA/ABS thermoformed outer skin
- Glass mat + UP resin backing
- Vacuum bag inner surface

PF1 ROLE: Makes the thermoformed skin
Post-process: RTM backing applied separately""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="TEC Process Agri",
        summary="TEC: Thermoform skin (PF1) + RTM backing; Plastics Unlimited; grain tank covers, combine panels",
        metadata={
            "topic": "tec_process",
            "supplier": "Plastics Unlimited, Preston IA",
            "process": "thermoform + RTM"
        }
    ))

    # 4. S-RIM Process (Thermoform + PUR)
    items.append(KnowledgeItem(
        text="""S-RIM Process - Thermoform over Structural RIM

S-RIM = Structural Reaction Injection Molding
LFI = Long Fiber Injection (John Deere terminology)

PROCESS:
1. Thermoform ABS/PMMA skin on PF1
2. Spray PUR (polyurethane) with glass fiber on B-side
3. Creates rigid structural panel

APPLICATION EXAMPLE: John Deere Tractor Hood
- Upper panel: ABS/PMMA (Class A appearance)
- Backing: PUR with glass fiber
- PUR w/GF will NOT read through ABS/PMMA (hidden)

- Lower panel: PUR post-painted (dull surface)
- Cannot use ABS/PMMA (glass fiber would read through paint)

DESIGN DETAILS:
- Bent flange stiffens joints, prevents debris buildup
- PUR w/GF reinforcement plates at connection points
- PUR w/o GF used between different PUR sections

SUPPLIERS:
- Fritzmeier (Hinrichssegen, Germany - near Munich)
- Process viewed 2007, used extensively by 2017

KEY LEARNING:
- PF1 makes the Class A thermoformed skin
- S-RIM/LFI backing provides structural rigidity
- Combined = lightweight structural panel with premium appearance

CLAAS ROUND BALER EXAMPLE:
- ABS/PMMA skin + PUR GF backing
- First introduced FPS 2006 Amana IA""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="S-RIM Process Agri",
        summary="S-RIM: Thermoform (PF1) + PUR glass fiber backing; tractor hoods, baler panels; Fritzmeier supplier",
        metadata={
            "topic": "srim_process",
            "suppliers": ["Fritzmeier (Germany)"],
            "applications": ["Tractor hood", "Baler panel"]
        }
    ))

    # 5. Two-Sheet Construction (Post-bond)
    items.append(KnowledgeItem(
        text="""Two-Sheet Thermoforming - Post-Bond Construction

NOTE: This is DIFFERENT from twin-sheet (simultaneous forming)
Two-Sheet = Form separately on PF1, bond together post-process

PROCESS:
1. Thermoform OUTER skin (Class A - ABS/PMMA)
2. Thermoform INNER skin (lower cost structural ABS)
3. Trim both sheets separately
4. Bond together with adhesive (steel support between layers)
5. Final trim after bonding

KEY SUPPLIER: Vitalo, Meulebeke Belgium
- Molder and development partner for John Deere
- Also: Allied Plastics, Twin Lakes WI (USA)

APPLICATIONS:
- John Deere combine side panels
- Kubota round baler (manufactured in Italy)
- Large styling panels

DESIGN CONSIDERATIONS:
1. Inner panel trimmed short of outer (allows alignment tolerance)
2. Drain openings required for condensation
3. Molded drain tubes in inner panel
4. Bond on two sides for corner strength
5. Glue fixture provides alignment

MATERIAL STACK (European):
- PMMA clear (top)
- JD Green
- ABS green/black/recycled
- ASA

BENEFITS vs RTM:
- Two-sheet panel: (4) attachment points, (6) fasteners
- RTM panel: (6) attachment pads, (20) fasteners, 1" tube frame
- Significant weight and assembly time reduction

PF1 ROLE: Forms both inner and outer skins
Post-process: Trim, bond, final trim""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Two-Sheet Agri Process",
        summary="Two-sheet: Form separately on PF1, post-bond; Vitalo Belgium; JD combines, Kubota balers",
        metadata={
            "topic": "two_sheet_process",
            "suppliers": ["Vitalo (Belgium)", "Allied Plastics (WI)"],
            "difference": "Not twin-sheet - formed separately, bonded post"
        }
    ))

    # 6. Design Guidelines
    items.append(KnowledgeItem(
        text="""Agri Panel Design Guidelines - From John Deere Experience

THERMAL EXPANSION MANAGEMENT:
- Thermoplastic CTE >> steel CTE
- Attachment locations must be slotted (not fixed holes)
- Compression limiters prevent soft joints and over-torque
- Large margins needed for fit and thermal expansion

APPEARANCE MANAGEMENT:
- Consistent parallel gap perception (no A or V gaps)
- Yellow/color behind gaps
- Rounded return edges
- Flat surface next to sheet metal = better image than painted orange peel

REINFORCEMENT METHODS:
1. Steel plates bonded to B-side with adhesive
2. Backing plates at attachment locations
3. Reinforcement ring if porosity issues (S-RIM)
4. Drain holes required for condensation

GLUE LINE VISIBILITY WARNING:
- Individual glue lines visible when dirt attracted to static charge
- SOLUTION: Anti-static green material as outer layer
- John Deere implemented Oct 2017 after field testing

PANEL ASSEMBLY STRATEGY:
- Multiple smaller panels combined for large assemblies
- Bolt together at joints
- Plastic carries no load (steel does)
- Optimizable: reduce steel structure weight

PROCESS CROSSOVER ECONOMICS:
- Thermoforming wins at lower volumes vs SMC
- Crossover point = tooling cost + (part price × parts made)
- RTM/SMC tooling higher, but lower per-part cost at volume
- Thermoforming ideal for agricultural equipment volumes""",
        knowledge_type="operational",
        source_file=SOURCE_FILE,
        entity="Agri Panel Design Guidelines",
        summary="Agri design: Slot attachments (CTE), anti-static material, drain holes, steel reinforcement bonding",
        metadata={
            "topic": "agri_design_guidelines",
            "key_issues": ["Thermal expansion", "Static/dirt", "Attachment", "Reinforcement"]
        }
    ))

    # 7. Key Suppliers & Partners
    items.append(KnowledgeItem(
        text="""Agri Thermoforming Suppliers - Potential Machinecraft Targets

USA SUPPLIERS (Midwest cluster):
1. Plastics Unlimited - Preston, IA
   - TEC process specialist
   - John Deere, Hagie supplier
   - Capabilities: Thermoform + RTM backing

2. Allied Plastics - Twin Lakes, WI
   - Two-sheet construction
   - John Deere development partner

3. Wilbert - White Bear Lake, MN
   - Twin sheet tooling
   - Interchangeable insert molds

EUROPEAN SUPPLIERS:
1. Vitalo - Meulebeke, Belgium
   - Two-sheet construction expert
   - John Deere primary EU molder
   - Multi-layer PMMA/ABS capability
   - Excellent DOI (depth of image) specialty

2. Fritzmeier - Hinrichssegen, Germany (near Munich)
   - S-RIM/LFI process specialist
   - Claas, John Deere supplier

OEM CONTACTS:
- John Deere: Materials Engineering (Greg McCunn, presenter)
- Hagie: Sprayer hoods
- Kubota: Italy manufacturing (round balers)
- Claas: Germany (round balers)

SALES OPPORTUNITY:
These suppliers need large format PF1 machines for:
- ABS/PMMA skin production
- Single sheet forming for two-sheet construction
- High quality Class A surface capability

Machinecraft advantage:
- Large format (2500mm+) capability
- Servo precision for consistent parts
- CSA/CE certification for NA/EU markets
- 40-50% cost vs Illig/Geiss""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Agri Thermoforming Suppliers",
        summary="Agri suppliers: Plastics Unlimited (IA), Vitalo (Belgium), Fritzmeier (Germany); JD partners",
        metadata={
            "topic": "agri_suppliers",
            "usa": ["Plastics Unlimited", "Allied Plastics", "Wilbert"],
            "europe": ["Vitalo", "Fritzmeier"]
        }
    ))

    # 8. Sales Strategy for Agri Market
    items.append(KnowledgeItem(
        text="""Agri Equipment Sales Strategy - Machinecraft PF1

TARGET MARKET:
- Agricultural OEMs (John Deere, Hagie, Kubota, Claas, AGCO, CNH)
- Tier 1 agri plastics suppliers (Plastics Unlimited, Vitalo, Allied)
- Markets: USA Midwest, Western Europe (Germany, Belgium, Italy)

VALUE PROPOSITION:
1. REPLACES RTM + GEL COAT
   - Lower tooling cost
   - Molded-in color (no paint)
   - Faster cycle times

2. COMPOSITE SKIN PRODUCTION
   - PF1 makes Class A thermoformed skin
   - Post-process reinforcement (RTM, S-RIM, steel bonding)
   - Customer may need PF1 + composite capability

3. TWO-SHEET CAPABILITY
   - Form both inner and outer skins on same PF1
   - Universal frames for size flexibility
   - Quick changeover between skin sizes

MACHINE RECOMMENDATIONS:
- PF1-2525 to PF1-5028: Most agri panel sizes
- Universal frames: Multiple panel sizes
- Pro tier: High volume, multiple products
- Quartz heaters: ABS/PMMA require precise heating

APPLICATION SIZING:
| Part | Typical Size | PF1 Model |
|------|--------------|-----------|
| Sprayer grill | 1000x1500mm | PF1-1520 |
| Combine side panel | 2000x2500mm | PF1-2525 |
| Baler outer skin | 1500x2000mm | PF1-2020 |
| Large hood panel | 2500x5000mm | PF1-5028 |

KEY SELLING POINTS:
- John Deere switched from SMC/RTM to thermoforming
- Weight reduction + cost reduction + no paint
- PF1 servo precision = consistent Class A surface
- European suppliers (Vitalo) use large format machines

COMPETITOR DISPLACEMENT:
- Illig/Geiss machines at Vitalo, Plastics Unlimited
- Machinecraft 40-50% cost advantage
- Target machine replacement cycle""",
        knowledge_type="commercial",
        source_file=SOURCE_FILE,
        entity="Agri Sales Strategy",
        summary="Agri strategy: Target OEMs + Tier 1 suppliers; replaces RTM; PF1-2525 to 5028; Illig displacement",
        metadata={
            "topic": "agri_sales_strategy",
            "targets": ["OEMs", "Tier 1 suppliers"],
            "machines": ["PF1-2525", "PF1-5028"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("SPE 2018 Agricultural Equipment Study Ingestion")
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
