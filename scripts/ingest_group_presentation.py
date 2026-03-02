#!/usr/bin/env python3
"""
Ingest General Group Presentation - July 2024 knowledge.

Source: data/imports/General Group Presentation - July 2024.pdf
Contains Machinecraft Group overview, structure, financials, and highlights.
Note: Customer logo images on slides 9-10 are not text-extractable.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "skills" / "brain"))

from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "General Group Presentation - July 2024.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Extract structured knowledge from Group presentation."""
    items = []
    
    # Company history
    items.append(KnowledgeItem(
        text="""Machinecraft Group History:

THREE GENERATIONS OF LEADERSHIP:
- 1st Generation (1980-1998): Founding era
- 2nd Generation (1998-2018): Growth and expansion
- 3rd Generation (2019 onwards): Current leadership, international expansion

Parent company established since 1976.
Currently 7 family members involved across 3rd generation.
Nearly 50 years of thermoforming expertise.""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machinecraft Group",
        summary="Machinecraft: 3 generations since 1976, now in 3rd gen leadership with 7 family members",
        metadata={"topic": "history", "founded": 1976}
    ))
    
    # Group structure
    items.append(KnowledgeItem(
        text="""Machinecraft Group Structure - Three Companies:

1. MACHINECRAFT (Main Company):
   - Designs & manufactures thermoforming machines and tooling
   - >20 machines manufactured per year
   - Turnover: >3.5 Mil EUR (2023-24)
   - 50 employees
   - 40 years in existence
   - Sales in 45+ countries: India, GCC, Europe, Russia, Canada

2. FORMPACK:
   - Sub-contract vacuum former for industrial products
   - >800 tonnes processed per year
   - >200 tools manufactured per year
   - Turnover: >2.5 Mil EUR (2023-24)
   - 50 employees
   - Materials: ABS, PC, PET-G, HDPE, ASA, KYDEX
   - Industries: Industrial Covers, EV, Bus, Truck, Aerospace, Railway, Energy

3. INDU:
   - Plastic sheet producer (extrusion)
   - 3-layer materials: ABS, PS, PE-HD
   - >1500 tonnes processed per year
   - Sheet thickness up to 10mm
   - Maximum width: 2.5m
   - Turnover: >2.5 Mil EUR (2023-24)
   - 40 employees
   - Sales in India & GCC

TOTAL GROUP: ~140 employees, 8 Mil EUR turnover (2023-24)""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machinecraft Group",
        summary="Machinecraft Group: 3 companies (Machinecraft, Formpack, Indu), 140 employees, 8M EUR turnover",
        metadata={
            "topic": "group_structure",
            "companies": ["Machinecraft", "Formpack", "Indu"],
            "employees": 140,
            "turnover_2023": "8M EUR"
        }
    ))
    
    # Financial overview
    items.append(KnowledgeItem(
        text="""Machinecraft Group Financial Overview (July 2024):

TURNOVER 2023-24:
- Machinecraft: >3.5 Mil EUR
- Formpack: >2.5 Mil EUR
- Indu: >2.5 Mil EUR
- Group Total: ~8 Mil EUR

PROJECTED TURNOVER 2024-25:
- Group Total: 10 Mil EUR
- Growth Rate: 20% year-over-year

PRODUCTION CAPACITY:
- Machines: >20 units/year
- Tooling: >200 tools/year
- Formpack processing: >800 tonnes/year
- Indu extrusion: >1500 tonnes/year""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machinecraft Group",
        summary="Machinecraft Group: 8M EUR (2023-24), projected 10M EUR (2024-25), 20% growth target",
        metadata={
            "topic": "financials",
            "turnover_2023": "8M EUR",
            "turnover_2024_projected": "10M EUR",
            "growth_rate": "20%"
        }
    ))
    
    # Location
    items.append(KnowledgeItem(
        text="""Machinecraft Group Location:

HEAD OFFICE:
- Mumbai City, India

MANUFACTURING PLANT:
- Location: Umargam, Gujarat, India
- Distance from Mumbai: 150 km
- Near Arabian Sea (1 km from coast)

Mumbai is India's financial capital and major port city.
Umargam provides cost-effective manufacturing with good logistics access.""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machinecraft Group",
        summary="Machinecraft: Mumbai office, Umargam plant (150km from Mumbai, near Arabian Sea)",
        metadata={
            "topic": "location",
            "office": "Mumbai",
            "plant": "Umargam",
            "distance_km": 150
        }
    ))
    
    # All-in-one solution
    items.append(KnowledgeItem(
        text="""Machinecraft Group - All-in-One Solution:

The Machinecraft Group offers a complete thermoforming solution:

1. RAW MATERIAL (Indu):
   - In-house sheet extrusion
   - ABS, ASA, HDPE sheets
   - Up to 10mm thickness, 2.5m width

2. PROTO SERIES RUN (Formpack):
   - Prototype development
   - Short-run production
   - Process validation

3. TOOLING (Machinecraft + Formpack):
   - Tool design and manufacture
   - >200 tools per year capacity

4. MACHINERY (Machinecraft):
   - Thermoforming machine design
   - Manufacturing and installation
   - >20 machines per year

This vertical integration allows customers to source everything from one group,
ensuring compatibility and single-point accountability.""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machinecraft Group",
        summary="Machinecraft: all-in-one solution - raw material, proto runs, tooling, and machinery from one group",
        metadata={"topic": "value_proposition", "offering": "vertically_integrated"}
    ))
    
    # Machinecraft specific highlights
    items.append(KnowledgeItem(
        text="""Machinecraft (Machine Division) Highlights:

PRODUCTION:
- >20 thermoforming machines manufactured per year
- Custom-designed machines for customer requirements

GLOBAL REACH:
- Sales in 45+ countries
- Key markets: India, GCC (Gulf), Europe, Russia, Canada

EXPERIENCE:
- 40+ years in thermoforming industry
- 3 generations of family expertise

CAPABILITIES:
- Single station vacuum forming
- Roll feeder machines
- XL/XXL large format machines
- Twin-sheet forming
- Complete tooling design and manufacture

NEW DEVELOPMENTS (2024):
- 2 new machine launches planned
- Automotive machinery expansion""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Machinecraft: 20+ machines/year, 45+ countries, 40 years experience, 2 new launches in 2024",
        metadata={
            "topic": "machinecraft_highlights",
            "machines_per_year": 20,
            "countries": "45+",
            "years_experience": 40
        }
    ))
    
    # Formpack highlights
    items.append(KnowledgeItem(
        text="""Formpack (Subcontract Forming Division) Highlights:

PRODUCTION CAPACITY:
- >800 tonnes of material processed per year
- >200 tools manufactured per year

MATERIALS PROCESSED:
- ABS (Acrylonitrile Butadiene Styrene)
- PC (Polycarbonate)
- PET-G (Polyethylene Terephthalate Glycol)
- HDPE (High Density Polyethylene)
- ASA (Acrylonitrile Styrene Acrylate)
- KYDEX (Thermoplastic sheet)

INDUSTRIES SERVED:
- Industrial Covers
- Electric Vehicles (EV)
- Bus interiors/exteriors
- Truck components
- Aerospace parts
- Railway interiors
- Energy sector equipment

This makes Formpack a strong reference for Machinecraft machinery capabilities.""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Formpack",
        summary="Formpack: 800+ tonnes/year, serves EV, Bus, Truck, Aerospace, Railway - demonstrates machine capability",
        metadata={
            "topic": "formpack_highlights",
            "capacity_tonnes": 800,
            "tools_per_year": 200,
            "industries": ["industrial", "ev", "bus", "truck", "aerospace", "railway", "energy"]
        }
    ))
    
    # Indu highlights
    items.append(KnowledgeItem(
        text="""Indu (Sheet Extrusion Division) Highlights:

PRODUCTION:
- >1500 tonnes of sheet produced per year

MATERIALS:
- ABS (Acrylonitrile Butadiene Styrene)
- ASA (Acrylonitrile Styrene Acrylate) - UV resistant
- HDPE (High Density Polyethylene)

CAPABILITIES:
- 3-layer co-extrusion
- Sheet thickness: up to 10mm
- Maximum sheet width: 2.5m

MARKETS:
- India
- GCC (Gulf Cooperation Council countries)

In-house sheet extrusion allows Machinecraft Group to:
- Control material quality
- Offer custom colors and formulations
- Provide competitive pricing
- Ensure material availability""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Indu",
        summary="Indu: 1500+ tonnes/year sheet extrusion, ABS/ASA/HDPE, up to 10mm thick, 2.5m wide",
        metadata={
            "topic": "indu_highlights",
            "capacity_tonnes": 1500,
            "max_thickness": "10mm",
            "max_width": "2.5m",
            "materials": ["ABS", "ASA", "HDPE"]
        }
    ))
    
    # Customer references note
    items.append(KnowledgeItem(
        text="""Machinecraft Group Customer References:

The group has customer references in:

INDIA:
- Multiple industrial customers
- EV manufacturers
- Bus and truck OEMs
- Aerospace suppliers
- Railway component makers

OVERSEAS (45+ countries):
- Europe
- GCC (Gulf countries)
- Russia
- Canada
- And other international markets

Key industries served:
- Automotive (EV, Bus, Truck)
- Aerospace
- Railway
- Industrial equipment
- Energy sector

Note: Customer logos are available in the July 2024 presentation slides 9-10.""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machinecraft Group",
        summary="Machinecraft: customer references in 45+ countries - India, Europe, GCC, Russia, Canada",
        metadata={
            "topic": "customer_references",
            "regions": ["India", "Europe", "GCC", "Russia", "Canada"],
            "countries_count": "45+"
        }
    ))
    
    return items


def main():
    print("=" * 60)
    print("Ingesting Machinecraft Group Presentation Knowledge")
    print("=" * 60)
    print(f"\nSource: {SOURCE_FILE}")
    
    items = create_knowledge_items()
    print(f"Extracted {len(items)} knowledge items\n")
    
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.entity}: {item.summary[:50]}...")
    
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
