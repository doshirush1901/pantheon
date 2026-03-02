#!/usr/bin/env python3
"""
Ingest XXL THERMOFORMING Machinery Machinecraft India Presentation knowledge.

Source: data/imports/xxl THERMOFORMING Machinery Machinecraft India Presentation Copy.pdf
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "skills" / "brain"))

from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "xxl THERMOFORMING Machinery Machinecraft India Presentation Copy.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Extract structured knowledge from XXL presentation."""
    items = []
    
    # Company overview
    items.append(KnowledgeItem(
        text="""Machinecraft Technologies XXL Thermoforming Machines Overview:
- Company established with three phases: 1980-1998 (founding), 1998-2018 (growth), 2019 onwards (XL expansion)
- Main plant: 10,000 SQM facility located 3 hours from Mumbai City, India
- All-in-one solution provider: Machinery, Tooling & Raw Material
- Offers complete package: Raw Material supply, Proto Series Run, Tooling, and Machinery""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Machinecraft: 10,000 SQM plant near Mumbai, all-in-one thermoforming solution provider",
        metadata={"topic": "company_overview", "facility_size": "10000_sqm"}
    ))
    
    # XL Machines sales vision
    items.append(KnowledgeItem(
        text="""Machinecraft XL Machines Sales Vision:
- Target: Sell 50 machines per year by 2027
- Growth trajectory: 6 machines (2019) → 7 (2020) → 8 (2021) → 10 (2022) → 12 (2023) → 16 (2024)
- Total: 50 XL machines sold in 5 years since 2019
- Global reach: Canada, United Kingdom, Ireland, France, Netherlands, Denmark, Sweden, Germany, Russia, Japan, India, UAE
- NPD (New Product Development) machines available""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="XL Machines",
        summary="Machinecraft XL machine sales: 50+ machines in 5 years, targeting 50/year by 2027",
        metadata={"topic": "sales_vision", "target_year": 2027, "annual_target": 50}
    ))
    
    # XL Machine installations with sizes
    items.append(KnowledgeItem(
        text="""Machinecraft XL Machine Installations (Examples since 2019):
1. Canada: 4.8m x 2.5m forming area
2. Russia: 4.2m x 2m forming area
3. India #1: 3m x 3m forming area
4. India #2: 3.5m x 2.5m forming area
5. India #3: 4m x 2.5m forming area
6. UAE: 4m x 2.5m forming area

Total: 6 XL machines installed since 2019 across these regions.
Maximum part sizes demonstrated: up to 5m x 2.5m and 3.5m x 2.5m x 2m deep.""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="XL Machines",
        summary="XL machines installed in Canada (4.8x2.5m), Russia (4.2x2m), India (3x3m, 3.5x2.5m, 4x2.5m), UAE (4x2.5m)",
        metadata={
            "topic": "installations",
            "countries": ["Canada", "Russia", "India", "UAE"],
            "max_size": "4.8m x 2.5m"
        }
    ))
    
    # XL CNC and Extrusion capabilities
    items.append(KnowledgeItem(
        text="""Machinecraft Investment in XL CNC & Extrusion Line:
- XL CNC machining capability: Tool size up to 4.5m x 2.5m and 1m deep
- Extrusion line capability: Up to 2.5m wide sheets
- Materials supported: HDPE and ABS
- Purpose: Support customers with in-house tooling and material production
- Enables complete turnkey solutions for large thermoformed parts""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="XL CNC & Extrusion",
        summary="XL CNC: tools up to 4.5x2.5m x1m deep; Extrusion: up to 2.5m wide HDPE/ABS sheets",
        metadata={
            "topic": "manufacturing_capabilities",
            "cnc_tool_size": "4.5m x 2.5m x 1m",
            "extrusion_width": "2.5m",
            "materials": ["HDPE", "ABS"]
        }
    ))
    
    # Why Machinecraft - competitive advantages
    items.append(KnowledgeItem(
        text="""Why Machinecraft - Key Differentiators:
1. Standard Brands Used: Uses well-known, reliable component brands
2. Flexible Tailor-Made Machines: Custom machines designed to customer specifications
3. Attrition Free Company: Stable workforce with low employee turnover, ensuring consistent quality and knowledge retention
4. Process Knowhow: Deep expertise in thermoforming processes, not just machine building

These advantages make Machinecraft a trusted partner for large-format thermoforming projects worldwide.""",
        knowledge_type="general",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Machinecraft advantages: standard brands, tailor-made machines, stable workforce, process expertise",
        metadata={"topic": "competitive_advantages"}
    ))
    
    # XL Machine size capabilities
    items.append(KnowledgeItem(
        text="""Machinecraft XL Thermoforming Machine Size Capabilities:
- Standard XL sizes range from 3m x 3m to 5m x 2.5m forming area
- Maximum demonstrated part size: 5m x 2.5m
- Deep draw capability: up to 2m deep (demonstrated on 3.5m x 2.5m machine)
- Machines are custom-built to match specific part requirements
- Can manufacture parts for buses, agricultural equipment, commercial vehicles, and large industrial applications

XL machines are ideal for:
- Bus interior panels and exterior parts
- Agricultural equipment covers and panels
- Large industrial equipment housings
- Commercial vehicle components
- Spa and bath products""",
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="XL Machines",
        summary="XL machines: 3x3m to 5x2.5m forming area, up to 2m deep draw capability",
        metadata={
            "topic": "size_capabilities",
            "min_size": "3m x 3m",
            "max_size": "5m x 2.5m",
            "max_depth": "2m"
        }
    ))
    
    return items


def main():
    print("=" * 60)
    print("Ingesting XXL THERMOFORMING Presentation Knowledge")
    print("=" * 60)
    print(f"\nSource: {SOURCE_FILE}")
    
    items = create_knowledge_items()
    print(f"Extracted {len(items)} knowledge items\n")
    
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.entity}: {item.summary[:60]}...")
    
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
        if result.validation_errors:
            print(f"  Validation: {result.validation_errors}")
    
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
