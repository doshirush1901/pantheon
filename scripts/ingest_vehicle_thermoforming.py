#!/usr/bin/env python3
"""
Ingest thermoforming-vehicle-construction-e.pdf knowledge.

Source: data/imports/thermoforming-vehicle-construction-e.pdf
Contains automotive thermoforming applications - relevant for PF1 machine sales.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "skills" / "brain"))

from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "thermoforming-vehicle-construction-e.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Extract structured knowledge from vehicle construction thermoforming PDF."""
    items = []
    
    # Benefits of thermoforming for vehicles
    items.append(KnowledgeItem(
        text="""Benefits of Thermoforming for Vehicle Construction:
- Low tool costs compared to injection molding
- Fast development and manufacturing times for tools
- Simple and cost-effective tool changes/modifications
- Short reaction times for fast changing design and model cycles
- Zero/prototype series can be produced via cheap prototype tools
- Series tools have minimal wear - can produce up to 20,000 moulded parts
- Even huge mould sizes can be produced inexpensively
- Through-coloured plastics available in all colours - no painting required
- High-quality design surfaces with excellent UV protection
- Matte, high gloss, or metallic optics feasible
- Injection-moulded optics possible through etched tools
- Exact design corners and edges achievable
- Two-sided parts with different shapes possible (twin-sheet)
- Low weight with high stability
- 100% recyclable materials

Key advantage: High cost-effectiveness in small batches while still economic for series up to 20,000 parts.""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Automotive Thermoforming",
        summary="Thermoforming benefits for vehicles: low tool cost, fast development, no painting needed, 20k+ production runs",
        metadata={"industry": "automotive", "topic": "benefits", "max_production": 20000}
    ))
    
    # Positive vs Negative deformation
    items.append(KnowledgeItem(
        text="""Thermoforming Process Types for Vehicle Parts:

POSITIVE DEFORMATION:
- Tool located at bottom of plastic sheet
- Sheet pulled OVER the tool
- Visible side does NOT contact tool
- Best for: High-gloss or metallic surfaces with excellent brilliance
- Grooves defined by positive deformation with large selection available
- Radii determined by sheet thickness but still shapeable
- Graining integrated directly into sheet material

NEGATIVE DEFORMATION:
- Plastic sheet pulled INTO the mould
- Visible side IS the tool-fitting side
- Enables very fine radii and detailed edge curves
- Allows strong undercuts
- Surface structure can be etched directly into tool
- Produces perfect injection-moulded optics/appearance
- Best for: Fine edges, injection-mould look, complex geometries

Choose positive for gloss/metallic exteriors, negative for detailed interiors with injection-mould appearance.""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="Thermoforming Process",
        summary="Positive deformation for gloss/metallic exteriors; Negative for fine edges and injection-mould look interiors",
        metadata={"industry": "automotive", "topic": "process_types"}
    ))
    
    # Exterior body parts applications
    items.append(KnowledgeItem(
        text="""Automotive EXTERIOR Parts Made by Thermoforming (e.g., Streetscooter electric van):

Body panels producible via positive vacuum forming:
- Left/Right Fenders - through-coloured, no painting needed
- Engine Bonnet/Hood
- Front Grill
- Door Panels (exterior)
- Outer Roof Skin
- Mirror Triangles
- B-pillar Covers

Key features for exterior parts:
- Shaped radii with high-gloss surfaces
- Through-coloured plastics eliminate painting costs
- Accurate matching clearances for functional body design
- Attachment mimics pre-integrated for easy vehicle mounting
- UV-resistant materials for exterior durability
- Can match OEM colour specifications

Ideal for electric vehicles, commercial vehicles, buses, and low-volume specialty vehicles.""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Automotive Exterior Parts",
        summary="Thermoformed exterior parts: fenders, bonnets, grills, door panels, roof skins - no painting needed",
        metadata={
            "industry": "automotive",
            "topic": "exterior_applications",
            "parts": ["fender", "bonnet", "grill", "door_panel", "roof_skin", "mirror_triangle", "b_pillar"]
        }
    ))
    
    # Interior parts applications
    items.append(KnowledgeItem(
        text="""Automotive INTERIOR Parts Made by Thermoforming:

POSITIVE DEFORMED interior parts (graining from sheet):
- Door Trims
- Dashboard Covers
- Centre Console
- Boot/Trunk Lining (side and back panels)

NEGATIVE DEFORMED interior parts (VW California example - injection-mould look):
- A-pillar Trim (front and rear)
- B-pillar Trim (front and rear)
- Sliding Door Panel
- Roof Frame Panel
- Tailgate Panel
- Aperture Through-loading
- Socle Wainscotting
- Seat Covers

Interior part advantages:
- Delicate edgings with finest optics
- Grain structure etched into mould for injection-moulded appearance
- Pre-integrated loudspeakers, belt holders possible
- Parts delivered pre-assembled
- Concealed mounting elements included
- Laminated fabric or soft-touch feel surfaces available

Perfect for camper vans, commercial vehicles, buses, and automotive interiors requiring premium feel at lower cost than injection molding.""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Automotive Interior Parts",
        summary="Interior thermoformed parts: door trims, dashboards, pillars, panels - injection-mould look achievable",
        metadata={
            "industry": "automotive",
            "topic": "interior_applications",
            "parts": ["door_trim", "dashboard", "centre_console", "boot_lining", "pillar_trim", "roof_panel", "tailgate"]
        }
    ))
    
    # Twin-sheet and special processes
    items.append(KnowledgeItem(
        text="""Twin-Sheet Thermoforming for Automotive:

Twin-sheet process produces moulded parts with:
- Exceptional stability (two layers bonded)
- Different shapes possible on BOTH sides
- Hollow sections for structural rigidity
- Lighter weight than solid alternatives

Applications in vehicles:
- Structural interior panels
- Load floors and trunk components
- Headliners with integrated features
- Door panels with mounting provisions
- Aerodynamic components

Combined with CNC trimming (5-axis controlled milling lines) for precision finishing.
Assembly of individual parts or complete component groups possible in-house.""",
        knowledge_type="process",
        source_file=SOURCE_FILE,
        entity="Twin-Sheet Process",
        summary="Twin-sheet thermoforming for structural automotive parts with different shapes on both sides",
        metadata={"industry": "automotive", "topic": "twin_sheet", "process": "twin_sheet"}
    ))
    
    # Production capabilities
    items.append(KnowledgeItem(
        text="""Thermoforming Production Capabilities for Automotive:

Volume capabilities:
- Prototype/zero series: Cheap prototype tooling
- Small series: Cost-effective production
- Large series: Up to 20,000+ parts economically viable
- 3-shift production for high volume orders

Quality standards achieved:
- IATF 16949:2016 (automotive quality management)
- DIN EN ISO 9001:2015
- EMAS environmental certification
- VDA guidelines compliance for delivery/labeling

Full service offering:
1. Consulting and planning
2. Development and design (CAD)
3. Prototyping (fast and flexible)
4. Series production
5. CNC finishing (5-axis milling)
6. Assembly and pre-mounting
7. Logistics (JIT capable)

This demonstrates thermoforming as a mature, automotive-qualified process suitable for OEM supply.""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Automotive Production",
        summary="Thermoforming for automotive: IATF 16949 certified, prototype to 20k+ series, full service",
        metadata={
            "industry": "automotive",
            "topic": "production_capabilities",
            "certifications": ["IATF_16949", "ISO_9001", "EMAS"]
        }
    ))
    
    # PF1 machine relevance summary
    items.append(KnowledgeItem(
        text="""PF1 Machine Applications in Automotive (Based on Industry Knowledge):

Machinecraft PF1 thermoforming machines are ideal for automotive applications:

EXTERIOR PARTS (positive forming, high-gloss):
- Body panels, fenders, bonnets for electric vehicles
- Commercial vehicle exterior panels
- Bus body components
- Specialty/low-volume vehicle bodies

INTERIOR PARTS (negative forming, injection-look):
- Door trims and panels
- Dashboard components
- Pillar trims (A, B, C pillars)
- Roof panels and headliners
- Trunk/boot linings
- Centre consoles

KEY SELLING POINTS for automotive customers:
1. Low tooling investment vs injection molding
2. Fast prototype-to-production cycle
3. Design flexibility for model changes
4. Through-colour eliminates painting line
5. Production volumes from 1 to 20,000+ units
6. Premium surfaces (gloss, matte, metallic, soft-touch)
7. Pre-assembly capability reduces customer operations

Target customers: EV startups, commercial vehicle OEMs, bus manufacturers, automotive tier suppliers, camper/RV manufacturers.""",
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="PF1 Automotive Applications",
        summary="PF1 for automotive: exterior panels, interior trims, EV bodies, commercial vehicles - low tool cost advantage",
        metadata={
            "industry": "automotive",
            "topic": "pf1_applications",
            "machine_series": "PF1",
            "target_customers": ["ev_startups", "commercial_vehicle_oem", "bus_manufacturer", "tier_supplier", "camper_rv"]
        }
    ))
    
    return items


def main():
    print("=" * 60)
    print("Ingesting Vehicle Construction Thermoforming Knowledge")
    print("=" * 60)
    print(f"\nSource: {SOURCE_FILE}")
    
    items = create_knowledge_items()
    print(f"Extracted {len(items)} knowledge items\n")
    
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.entity}: {item.summary[:55]}...")
    
    print("\n" + "-" * 60)
    print("Starting ingestion...")
    
    ingestor = KnowledgeIngestor(verbose=True)
    result = ingestor.ingest_batch(items)
    
    print("\n" + "=" * 60)
    print(f"RESULT: {result}")
    print("=" * 60)
    
    if result.success:
        print("\n✓ Knowledge ingested successfully!")
        print(f"  - Items ingested: {result.items_ingested}")
        print(f"  - Qdrant main: {result.qdrant_main}")
        print(f"  - Qdrant discovered: {result.qdrant_discovered}")
        print(f"  - Mem0: {result.mem0}")
        print(f"  - JSON backup: {result.json_backup}")
    else:
        print("\n✗ Ingestion failed")
        if result.errors:
            print(f"  Errors: {result.errors}")
    
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
