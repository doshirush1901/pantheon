#!/usr/bin/env python3
"""
Ingest bathroom sanitaryware thermoforming knowledge from KSA project profile.

Source: data/imports/RMbathroom bath for KSA .pdf
Content: Project profile for thermoformed bathroom products in Saudi Arabia

Knowledge extracted:
- Vacuum forming process for bathroom products
- Product specifications (bathtubs, shower trays, wash basins)
- Material characteristics (acrylic capped ABS)
- Equipment requirements (8080BVF machine)
- Post-processing (GRP/FRP reinforcement)
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
AGENT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

from src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem


def create_bathroom_knowledge_items() -> list[KnowledgeItem]:
    """Extract knowledge items from the bathroom sanitaryware project profile."""
    source_file = "RMbathroom bath for KSA .pdf"
    items = []
    
    # 1. Application Overview - Thermoformed Bathroom Sanitaryware
    items.append(KnowledgeItem(
        text="""THERMOFORMED BATHROOM SANITARYWARE APPLICATION

Thermoforming (vacuum forming) is an excellent process for manufacturing bathroom sanitaryware products including bathtubs, shower trays, wash basins, jacuzzis, vanity units, and facia panels.

Key advantages for bathroom products:
- Wide product flexibility - vast variety of shapes, sizes, and colors
- Energy efficient manufacturing process
- Low mould/tooling costs compared to injection molding
- Low capital investment requirements
- High turnover productivity
- Products have warm, pleasant feel to touch
- Wide range of attractive colors possible
- Color fastness and no yellowing over time
- Easy scratch removal and repair
- Excellent moulding properties with flexibility
- No discoloring from iron oxide stains
- Firm grip surface for feet (safety)
- Low heat conductivity for comfortable bathing
- Lightweight for easy installation
- Pore-free, hygienic surface
- High gloss finish
- Easy to clean

Material: Acrylic or acrylic-capped ABS sheets (3-5mm thickness range)
Reinforcement: GRP/FRP or Polyurethane resin sprayed on underside

This application is ideal for:
- Housing construction projects
- Hospitality/hotel bathroom fit-outs
- Residential bathroom manufacturing
- Commercial bathroom product lines
- Middle East and emerging market housing growth""",
        knowledge_type="application",
        source_file=source_file,
        entity="Bathroom Sanitaryware",
        summary="Thermoforming for bathroom products - bathtubs, shower trays, wash basins with acrylic/ABS 3-5mm sheets",
        metadata={
            "industry": "bathroom_sanitaryware",
            "region": "KSA",
            "materials": ["acrylic", "acrylic-capped ABS"],
            "products": ["bathtubs", "shower trays", "wash basins", "jacuzzis", "vanity units"],
        }
    ))
    
    # 2. Vacuum Forming Process for Bathroom Products
    items.append(KnowledgeItem(
        text="""VACUUM FORMING PROCESS FOR BATHROOM SANITARYWARE

Basic Process Cycle:
1. A cold thermoplastic sheet (acrylic or ABS) is clamped into the frame
2. Heat source (infrared heaters) is brought to the sheet to soften it
3. Heat source is removed when sheet reaches forming temperature
4. The softened material is vacuum formed onto the mould
5. The forming is allowed to cool in the mould
6. The formed product is removed from the machine
7. Underside is sprayed with reinforcement resin
8. Excess material is trimmed off
9. Edge finishing - polishing/buffing for smoothness
10. Fixing holes drilled for taps, waste outlets
11. Cradle brackets fixed (for baths, shower trays, wash basins)

Reinforcement Options:
- GRP/FRP (Glass Reinforced Plastic): Most common, sprayed with pistol gun until required thickness
- Polyurethane (PU) resin: More environmentally friendly, recyclable
- Recycled thermoplastics: Newest eco-friendly option

Note: GRP reinforced products are NOT recyclable. PU and thermoplastic reinforcement are preferred for environmental reasons.

Trimming Process:
- Router-based cutting station removes excess material
- Holes drilled for taps and waste fittings
- Edges buffed for smooth finish

Packing:
- Stretch wrap system for protection during storage and transport""",
        knowledge_type="process",
        source_file=source_file,
        entity="Bathroom Vacuum Forming Process",
        summary="Vacuum forming cycle for bathtubs/sanitaryware with GRP/PU reinforcement and trimming",
        metadata={
            "process_type": "vacuum_forming",
            "application": "bathroom_sanitaryware",
            "reinforcement_types": ["GRP/FRP", "Polyurethane", "recycled thermoplastics"],
        }
    ))
    
    # 3. Product Specifications - Bathtubs
    items.append(KnowledgeItem(
        text="""THERMOFORMED BATHTUB SPECIFICATIONS

LUXURY BATHTUB:
- Dimensions: 1850mm x 850mm (1.85m x 0.85m)
- Material thickness: 4.5mm acrylic/ABS
- Mould cavities: 1-up (single cavity)
- Cycle time: 8 minutes per piece
- Annual capacity per machine: 15,000 units
- Mould cost: £5,000

STANDARD BATHTUB:
- Dimensions: 1750mm x 800mm (1.75m x 0.80m)
- Material thickness: 4.5mm acrylic/ABS
- Mould cavities: 2-up (double cavity for smaller size)
- Cycle time: 8 minutes per cycle
- Annual capacity per machine: 15,000 units
- Mould cost: £4,500

JACUZZI/WHIRLPOOL BATH:
- Dimensions: 1850mm x 1850mm (1.85m x 1.85m)
- Material thickness: 5.0mm acrylic/ABS (thicker for larger area)
- Mould cavities: 1-up
- Cycle time: 8 minutes per piece
- Annual capacity per machine: 15,000 units
- Mould cost: £5,000

Material consumption per bathtub:
- Thermoplastic sheet: 12-42 metric tons/year for production line
- PU Resin for reinforcement: 21-75 metric tons/year
- CaCO3 Filler: 21-75 metric tons/year

Note: Bathtubs require 4.5-5mm material thickness for structural integrity and are always reinforced with resin on the underside.""",
        knowledge_type="application",
        source_file=source_file,
        entity="Thermoformed Bathtubs",
        summary="Bathtub specs: Luxury 1850x850mm, Standard 1750x800mm, Jacuzzi 1850x1850mm, 4.5-5mm material, 8 min cycle",
        metadata={
            "product": "bathtubs",
            "material_thickness_mm": [4.5, 5.0],
            "cycle_time_min": 8,
            "reinforcement": "required",
        }
    ))
    
    # 4. Product Specifications - Shower Trays and Wash Basins
    items.append(KnowledgeItem(
        text="""THERMOFORMED SHOWER TRAYS AND WASH BASINS

SHOWER TRAY:
- Dimensions: 800mm x 800mm (standard square)
- Material thickness: 4.0mm acrylic/ABS
- Mould cavities: 2-up (double cavity)
- Cycle time: 7 minutes per cycle
- Annual capacity: 34,200 units
- Reinforcement: Required (PU or GRP)

WASH BASIN:
- Dimensions: 850mm x 600mm
- Material thickness: 3.0mm acrylic/ABS
- Mould cavities: 4-up (quad cavity)
- Cycle time: 7 minutes per cycle
- Annual capacity: 68,500 units
- Reinforcement: Required

HAND BASIN (smaller):
- Dimensions: 400mm x 500mm
- Material thickness: 3.0mm acrylic/ABS
- Mould cavities: 6-up (multiple cavity)
- Cycle time: 7 minutes per cycle
- Annual capacity: 102,800 units

VANITY UNITS:
- Dimensions: 600mm x 400mm
- Material thickness: 3.0mm
- Mould cavities: 4-up
- Cycle time: 5 minutes per cycle
- Annual capacity: 96,000 units
- Reinforcement: Not required for vanity units""",
        knowledge_type="application",
        source_file=source_file,
        entity="Shower Trays and Wash Basins",
        summary="Shower tray 800x800mm 4mm, Wash basin 850x600mm 3mm, Hand basin 400x500mm, 5-7 min cycles",
        metadata={
            "products": ["shower_tray", "wash_basin", "hand_basin", "vanity_unit"],
            "material_thickness_mm": [3.0, 4.0],
            "cycle_time_min": [5, 7],
        }
    ))
    
    # 5. Product Specifications - Facia Panels and Accessories
    items.append(KnowledgeItem(
        text="""THERMOFORMED FACIA PANELS AND ACCESSORIES

FACIA PANEL - FRONT (Bath surround):
- Dimensions: 1850mm x 600mm
- Material thickness: 3.0mm
- Mould cavities: 1-up
- Cycle time: 5 minutes
- Annual capacity: 24,000 units
- Mould cost: £4,200
- Reinforcement: NOT required

FACIA PANEL - END/SIDE:
- Dimensions: 850mm x 600mm
- Material thickness: 3.0mm
- Mould cavities: 2-up
- Cycle time: 5 minutes
- Annual capacity: 48,000 units
- Mould cost: £4,300
- Reinforcement: NOT required

TABLE & COUNTER TOPS:
- Dimensions: 1000mm x up to 2000mm
- Material thickness: 2.5mm
- Mould cavities: 1-up
- Cycle time: 4 minutes
- Annual capacity: 30,000 units

WC PARTITION PANELS:
- Dimensions: 1000mm x up to 2000mm
- Material thickness: 3.0mm
- Cycle time: 4 minutes
- Annual capacity: 48,000 units

CEILING PANELS:
- Dimensions: 600mm x 600mm
- Material thickness: 0.75mm (thin gauge)
- Mould cavities: 9-up
- Cycle time: 3 minutes
- Annual capacity: 360,000 units

Note: Flat panels and non-structural items do NOT require reinforcement, reducing cost and cycle time.""",
        knowledge_type="application",
        source_file=source_file,
        entity="Facia Panels and Accessories",
        summary="Facia panels 3mm, counter tops 2.5mm, ceiling panels 0.75mm, no reinforcement needed",
        metadata={
            "products": ["facia_panels", "counter_tops", "wc_partitions", "ceiling_panels"],
            "material_thickness_mm": [0.75, 2.5, 3.0],
            "reinforcement": "not_required",
        }
    ))
    
    # 6. Material Characteristics
    items.append(KnowledgeItem(
        text="""ACRYLIC MATERIAL CHARACTERISTICS FOR BATHROOM SANITARYWARE

Acrylic and acrylic-capped ABS sheets are the preferred materials for thermoformed bathroom products.

Material Properties:
- Warm, pleasant feeling to touch (unlike cold ceramic)
- Wide range of attractive colors available
- Excellent color fastness - no fading
- Easy scratch removal and repair
- Excellent moulding properties with flexibility
- No yellowing after long periods of use
- No discoloring from iron oxide (rust) stains
- Firm grip surface for feet (important safety feature)
- Low heat conductivity - more comfortable bath temperature
- Lightweight - easy installation
- Pore-free, hygienic surface (bacteria resistant)
- High gloss surface finish
- Easy to clean and maintain

Material Suppliers:
- SENOPLAST (Austria) - developed acrylic-capped ABS sheets
- Originally developed by ICI (Australia, 1950s)

Thickness Ranges by Product:
- Bathtubs: 4.5-5.0mm (structural requirement)
- Shower trays: 4.0mm
- Wash basins: 3.0mm
- Facia panels: 3.0mm
- Counter tops: 2.5mm
- Ceiling panels: 0.75mm (thin gauge)

Note: Thicker materials required for structural products that bear weight. Thinner materials for decorative/non-structural items.""",
        knowledge_type="process",
        source_file=source_file,
        entity="Acrylic Sanitaryware Materials",
        summary="Acrylic/ABS properties for bathroom products - warm touch, color fast, hygienic, 0.75-5mm thickness range",
        metadata={
            "material_type": "acrylic",
            "suppliers": ["SENOPLAST", "ICI"],
            "thickness_range_mm": [0.75, 5.0],
        }
    ))
    
    # 7. Equipment Requirements
    items.append(KnowledgeItem(
        text="""EQUIPMENT FOR BATHROOM SANITARYWARE THERMOFORMING

PRIMARY MACHINE:
Model: 8080BVF Heavy Duty Sandwich Heater Thermoformer (Ridat)
- Forming area: 800mm x 800mm to 2000mm x 1000mm (for bathtub production)
- Features: Sandwich heater configuration, heated clamp frame, automatic forming cycle
- Price: Approximately £96,000 (GBP)
- Suitable for: All bathroom products from bathtubs to ceiling panels

ANCILLARY EQUIPMENT (Total ~£28,000):
- Spraying rigs with guns (3 units): £11,000 - for GRP/PU reinforcement
- Edge trimming rigs with router: £8,500 - for excess material removal
- Heavy duty pallet trucks (2 units): £2,000 - material handling
- Shrink wrapping equipment: £4,500 - finished product packaging
- Hand tools (hole saw, buffing machine): £1,000
- Miscellaneous (barrel mixer etc.): £1,000

SERVICE EQUIPMENT (~£13,700):
- Air compressor: 30hp Ingersoll Rand - £12,500
- Mould temperature controller: 6KW, 80-90°C - £1,200

INFRASTRUCTURE REQUIREMENTS:
- Factory space: ~1,000 square meters total
  - Production: 350 sqm
  - Raw material storage: 80 sqm
  - Finished products: 200 sqm
  - Tools storage: 180 sqm
  - Maintenance: 30 sqm
  - Despatch: 60 sqm
  - Administration: 100 sqm
- Power: 200KW, 3-phase, 4-wire supply
- Compressed air: 30hp capacity

STAFFING:
- Skilled operators: 4
- Unskilled labor: 5
- Tool setter/maintenance: 1""",
        knowledge_type="machine_spec",
        source_file=source_file,
        entity="Bathroom Equipment Requirements",
        summary="8080BVF thermoformer £96K, spray rigs, trimming equipment, 1000sqm factory, 200KW power",
        metadata={
            "machine_model": "8080BVF",
            "machine_type": "sandwich_heater_thermoformer",
            "application": "bathroom_sanitaryware",
            "total_equipment_cost_gbp": 137700,
        }
    ))
    
    # 8. Mould/Tooling Information
    items.append(KnowledgeItem(
        text="""MOULDS AND TOOLING FOR BATHROOM SANITARYWARE

Mould Costs (GBP):
- Luxury Bathtub mould (1-up): £5,000
- Standard Bathtub mould (1-up): £4,500
- Jacuzzi/Whirlpool mould (1-up): £5,000
- Facia Panel Front mould (1-up): £4,200
- Facia Panel End mould (2-up): £4,300

Total initial mould investment: ~£23,000 for basic product range

Multi-Cavity Moulds:
- 1-up: Large products (bathtubs, jacuzzis, large panels)
- 2-up: Medium products (standard bathtubs, shower trays, end panels)
- 4-up: Smaller products (wash basins, vanity units)
- 6-up: Small products (hand basins)
- 9-up: Very small/flat products (ceiling panels)

Key Mould Considerations:
- Lower cost than injection moulds due to simpler construction
- Material: Typically cast aluminum or machined aluminum
- Can include texture/pattern details
- Easy to modify for design changes
- Shorter lead times than injection moulds

Note: Mould costs are significantly lower than injection moulding, making thermoforming ideal for medium volume bathroom product production.""",
        knowledge_type="commercial",
        source_file=source_file,
        entity="Bathroom Mould Costs",
        summary="Bathtub mould £4,500-5,000, facia panel £4,200-4,300, total ~£23,000 initial investment",
        metadata={
            "mould_type": "thermoforming",
            "application": "bathroom_sanitaryware",
            "cost_range_gbp": [4200, 5000],
        }
    ))
    
    # 9. Financial Overview
    items.append(KnowledgeItem(
        text="""FINANCIAL OVERVIEW - BATHROOM SANITARYWARE PLANT (KSA)

FIXED CAPITAL INVESTMENT (GBP):
- Land and Building: TBA (location dependent)
- Capital Plant & Equipment: £96,000
- Ancillary & Hand Tools: £28,000
- Service Equipment: £13,700
- Tooling & Moulds: £23,000
- Engineering fees: £10,000
- Shipping & Commissioning: £10,000
- Pre-operative expenses: £10,000
- Contingency & Price Escalation: £9,300

TOTAL FIXED CAPITAL: £200,000 (excluding land/building)

WORKING CAPITAL REQUIREMENTS:
- Raw material inventory: 2 months
- Wages and salaries: 2 months
- Overheads: 2 months
- Debtors/receivables: 2 months

KEY FINANCIAL ADVANTAGES:
1. Lower capital investment vs injection moulding
2. Lower mould costs (£4,000-5,000 vs £50,000+ for injection)
3. Flexible product mix - same machine makes all products
4. Quick changeover between products
5. Lower energy consumption per unit
6. High productivity with automated cycles

This investment level is suitable for:
- Medium-scale production
- Housing project supply contracts
- Regional bathroom product distribution""",
        knowledge_type="commercial",
        source_file=source_file,
        entity="Bathroom Plant Investment",
        summary="Total £200K capital investment (excl. land), £96K equipment, £23K moulds, lower cost than injection",
        metadata={
            "investment_gbp": 200000,
            "region": "KSA",
            "application": "bathroom_sanitaryware",
        }
    ))
    
    return items


def main():
    """Run the bathroom sanitaryware knowledge ingestion."""
    print("=" * 70)
    print("BATHROOM SANITARYWARE THERMOFORMING KNOWLEDGE INGESTION")
    print("Source: RMbathroom bath for KSA .pdf")
    print("=" * 70)
    
    ingestor = KnowledgeIngestor(verbose=True, skip_duplicates=True)
    
    items = create_bathroom_knowledge_items()
    print(f"\nExtracted {len(items)} knowledge items:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.entity}")
    
    print("\nIngesting to knowledge base...")
    result = ingestor.ingest_batch(items)
    
    print("\n" + "=" * 70)
    print("INGESTION RESULT:")
    print(result)
    print("=" * 70)
    
    return result.success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
