#!/usr/bin/env python3
"""
Store comprehensive Machinecraft sales knowledge in Ira's memory system.
Extracted from: Machinecraft Technologies Evolution and Performance (1976–2025).pdf

This is CRITICAL knowledge for Ira as a sales agent for Machinecraft.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def load_env():
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))

load_env()

RUSHABH_IDENTITY_ID = "id_db1a9b47e00d"

# ============================================================================
# MACHINECRAFT SALES KNOWLEDGE - ENTITY MEMORIES
# ============================================================================

ENTITY_MEMORIES = [
    # ==========================================================================
    # COMPANY OVERVIEW & POSITIONING
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "India's most advanced maker of thermoforming machines - exports to 40+ countries", "fact"),
    ("company", "Machinecraft Technologies",
     "Family-led global machinery company with ~140 employees, turnover ₹60+ Cr, goal: ₹300 Cr by 2030", "fact"),
    ("company", "Machinecraft Technologies",
     "Value proposition: European-quality machines at one-third the price - drives global competitiveness", "fact"),
    ("company", "Machinecraft Technologies",
     "2025 goal: Become #1 integrated thermoforming ecosystem in Asia (machinery + tooling + sheets + parts)", "fact"),
    ("company", "Machinecraft Technologies",
     "Offers ~24 distinct machine models covering most thermoforming needs as of 2025", "fact"),
    
    # ==========================================================================
    # PRODUCT LINES - PF1 SERIES (FLAGSHIP HEAVY-GAUGE)
    # ==========================================================================
    ("product", "PF1 Series",
     "Flagship servo-driven vacuum forming machines with automatic sheet loading for heavy-gauge thermoforming", "fact"),
    ("product", "PF1 Series",
     "Sizes from ~1200x860mm up to 3560x2560mm forming area - modular workhorses", "fact"),
    ("product", "PF1 Series",
     "Applications: automotive body panels, vehicle interiors, appliance housings, sanitary ware (shower trays), industrial packaging", "fact"),
    ("product", "PF1-XL Series",
     "Extra-large format extending to ~4x2.2 meters for aircraft interior panels, big truck/tractor components, billboard signage", "fact"),
    ("product", "PF2 Series",
     "Simplified heavy-gauge formers - pneumatic, manual-loaded for small batches and prototyping", "fact"),
    
    # ==========================================================================
    # PRODUCT LINES - COMPACT & SPECIALTY
    # ==========================================================================
    ("product", "UNO Series",
     "Compact single-station thermoformer suited for labs, prototyping, and startups", "fact"),
    ("product", "DUO Series",
     "Compact double-station thermoformer for labs and small production runs", "fact"),
    ("product", "SPA Series",
     "Deep-draw vacuum former for wellness products - spa tubs and bathtubs with 3000x3000mm forming area", "fact"),
    
    # ==========================================================================
    # PRODUCT LINES - PACKAGING (THIN-GAUGE, ROLL-FED)
    # ==========================================================================
    ("product", "AM Series",
     "Entry-level roll-fed vacuum formers (e.g. AM-5060 for 500x600mm) for small clamshells and trays", "fact"),
    ("product", "FCS Series",
     "Form-Cut-Stack automated pressure forming machines (600x800mm and 800x1200mm) for high-volume packaging", "fact"),
    ("product", "FCS Series",
     "Applications: yogurt cups, food trays, medical blister packs - tens of thousands per hour", "fact"),
    ("product", "TFM Series",
     "Thermoforming with integrated trimming for demanding packaging applications", "fact"),
    
    # ==========================================================================
    # PRODUCT LINES - AUTOMOTIVE INTERIOR
    # ==========================================================================
    ("product", "IMG-S Series",
     "In-Mold Graining/Skinning machines for soft-touch surfaces on dashboards, door panels, console parts", "fact"),
    ("product", "IMG-S Series",
     "Vacuum-forms heated PVC/TPU foil into grain-textured mold, fuses onto substrate for luxury finishes", "fact"),
    ("product", "TOM Technology",
     "Three-Dimensional Overlay film lamination (with FVF Japan) - decorative films on 3D parts", "fact"),
    ("product", "TOM Technology",
     "Applications: automotive interiors, home appliance panels, sanitary fittings with high-end decorative trim", "fact"),
    
    # ==========================================================================
    # AUXILIARY PRODUCTS
    # ==========================================================================
    ("product", "CNC Trimming Systems",
     "5-axis CNC routers and 3-axis trimming machines for finishing formed parts, especially heavy-gauge automotive", "fact"),
    ("product", "Machinecraft Tooling",
     "In-house tooling capability at Umargam - molds and dies for thermoforming, reduces lead times", "fact"),
    
    # ==========================================================================
    # SALES PERFORMANCE DATA
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Revenue FY2019: ~₹40 Cr, FY2020: ~₹30 Cr (COVID), FY2022: ~₹60 Cr (record), FY2024: ~₹60 Cr", "fact"),
    ("company", "Machinecraft Technologies",
     "2025 target: ₹70 Cr revenue (+15-20%), ~60 machines, ₹18-20 Cr net profit (~25% margin)", "fact"),
    ("company", "Machinecraft Technologies",
     "Typical volume: ~50 machines/year, average selling price rising due to shift to premium/larger systems", "fact"),
    ("company", "Machinecraft Technologies",
     "Exports: ~55% of sales (up from 30% in 2020), markets include Europe, Middle East, Latin America, Asia", "fact"),
    ("company", "Machinecraft Technologies",
     "Large custom automotive/wind-energy machines cost ₹4-5 Cr each", "fact"),
    
    # ==========================================================================
    # MANUFACTURING & CAPABILITIES
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Factory: Umargam, Gujarat (150km from Mumbai) - opened 2019, expanded to ~40,000 sq ft by 2023", "fact"),
    ("company", "Machinecraft Technologies",
     "Capacity: 30-40 heavy machines/year plus dozens of smaller units at full utilization", "fact"),
    ("company", "Machinecraft Technologies",
     "Equipment: CNC laser/plasma cutting, CNC machining centers, PLC programming workshop, test bay", "fact"),
    ("company", "Machinecraft Technologies",
     "CE compliance for European exports - machines certified to European safety standards", "fact"),
    ("company", "Machinecraft Technologies",
     "Built India's largest vacuum forming machine (4.25m x 2.5m) in 2021 for windmill blade components", "fact"),
    
    # ==========================================================================
    # CUSTOMER SEGMENTS
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Customer segments: automotive OEM suppliers, sanitaryware producers, luggage makers, industrial components, food packaging, R&D labs", "fact"),
    ("company", "Machinecraft Technologies",
     "Key automotive clients include Tier-1 suppliers: IAC, Grupo Antolin, Motherson, TACO", "fact"),
    ("company", "Machinecraft Technologies",
     "Applications: bathtubs, dashboards, refrigerator liners, food trays, medical packaging, aircraft panels, signage", "fact"),
    
    # ==========================================================================
    # PARTNERSHIPS
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "FVF Thermoforming (Japan) partnership since 2022: TOM film lamination technology for decorative surfaces", "fact"),
    ("company", "Machinecraft Technologies",
     "Former FRIMO (Germany) partnership 2019-2022: Gained automotive interior know-how before FRIMO's bankruptcy", "fact"),
    ("company", "Machinecraft Technologies",
     "Lanulfi (Italy) partnership: Toolmaking collaboration for global thermoforming molds", "fact"),
    
    # ==========================================================================
    # COMPETITIVE POSITIONING
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Competes with: Illig (German, packaging), Rajoo Engineers (Indian), GN Thermoforming (Canadian)", "fact"),
    ("company", "Machinecraft Technologies",
     "Differentiator: Full ecosystem (machines + tooling + sheets via Indu + parts via Formpack) - one-stop solution", "fact"),
    ("company", "Machinecraft Technologies",
     "Price advantage: European-quality at ~1/3 the cost of Western competitors", "fact"),
    
    # ==========================================================================
    # KEY MILESTONES
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "1976: Founded by B.P. Doshi, built one of India's first vacuum forming machines", "fact"),
    ("company", "Machinecraft Technologies",
     "1998: K-Show Germany debut - sold first automated vacuum former in Europe", "fact"),
    ("company", "Machinecraft Technologies",
     "2010s: 2,500+ machine installations across 35+ countries achieved", "fact"),
    ("company", "Machinecraft Technologies",
     "2020 COVID: Developed vaccine refrigerator liners in 8 weeks, supplied cold storage to 24 countries", "fact"),
    ("company", "Machinecraft Technologies",
     "Values: 'We keep our word, we build globally respected machines, we support each other like family'", "fact"),
]


def store_memories():
    """Store all Machinecraft sales knowledge."""
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING MACHINECRAFT SALES KNOWLEDGE FOR IRA")
    print("=" * 70)
    
    # Store entity memories
    print(f"\n🏭 Storing {len(ENTITY_MEMORIES)} Machinecraft knowledge items...")
    entity_count = 0
    for entity_type, entity_name, memory_text, memory_type in ENTITY_MEMORIES:
        result = pm.store_entity_memory(
            entity_type=entity_type,
            entity_name=entity_name,
            memory_text=memory_text,
            memory_type=memory_type,
            source_channel="system",
            source_identity_id=RUSHABH_IDENTITY_ID,
            confidence=1.0,
            embed=True
        )
        if result:
            entity_count += 1
            print(f"  ✓ [{entity_type}:{entity_name}] {memory_text[:55]}...")
        else:
            print(f"  ⊘ (duplicate) {memory_text[:40]}...")
    
    print("\n" + "=" * 70)
    print(f"COMPLETE: Stored {entity_count} sales knowledge items")
    print("=" * 70)
    print("\nIra now has comprehensive knowledge about:")
    print("  • Company overview and positioning")
    print("  • All product lines (PF1, AM, FCS, IMG, TOM, etc.)")
    print("  • Sales performance and targets")
    print("  • Manufacturing capabilities")
    print("  • Customer segments")
    print("  • Partnerships and competitive positioning")
    print("  • Key milestones and achievements")
    
    return entity_count


if __name__ == "__main__":
    store_memories()
