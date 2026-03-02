#!/usr/bin/env python3
"""
Store Machinecraft Machine Selection Guide knowledge in Ira's memory.
Source: Machinecraft Machine Selection Guide.pdf

This is the master reference for recommending the right machine to customers.
8 series, 60+ models, with pricing and application mapping.
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

ENTITY_MEMORIES = [
    # ==========================================================================
    # PORTFOLIO OVERVIEW
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Machine portfolio: 60+ models across 8 series - PF1 Classic, PF1-X, IMG, AM, FCS, PF1-M, PF1-L, PF1-W", "fact"),
    ("company", "Machinecraft Technologies",
     "Selection process: 1) Define application, 2) Assess material/volume requirements, 3) Follow decision tree", "fact"),
    
    # ==========================================================================
    # PF1 CLASSIC SERIES - Mid-Tier Industrial
    # ==========================================================================
    ("product", "PF1 Classic",
     "PF1 Classic: 31 variants, 500x650 to 3000x2000mm, semi-automation, Mid-Tier pricing", "fact"),
    ("product", "PF1 Classic",
     "PF1 Classic India price: ₹15L - ₹85L range depending on size and options", "fact"),
    ("product", "PF1 Classic",
     "PF1 Classic applications: Industrial & general products, general packaging, lowest TCO", "fact"),
    ("product", "PF1 Classic",
     "PF1 Classic volume: Best for LOW volume (<100K parts/year) production", "fact"),
    
    # ==========================================================================
    # PF1-X SERIES - Premium Industrial
    # ==========================================================================
    ("product", "PF1-X Series",
     "PF1-X Series: 24 variants, 800x1000 to 5000x2800mm, full automation, Premium tier", "fact"),
    ("product", "PF1-X Series",
     "PF1-X Series India price: ₹45L - ₹2.5Cr range depending on size and options", "fact"),
    ("product", "PF1-X Series",
     "PF1-X Series applications: Premium industrial, large automotive parts, full servo-driven", "fact"),
    ("product", "PF1-X Series",
     "PF1-X Series volume: Best for MEDIUM volume (100K-1M parts/year) production", "fact"),
    
    # ==========================================================================
    # IMG SERIES - Automotive Interiors
    # ==========================================================================
    ("product", "IMG Series",
     "IMG Series: 2 variants, 500x1200 to 1200x2000mm, full automation, Premium tier", "fact"),
    ("product", "IMG Series",
     "IMG Series India price: ₹1.25Cr - ₹1.5Cr for automotive interior graining machines", "fact"),
    ("product", "IMG Series",
     "IMG Series applications: Automotive interior graining (dashboards, door trims, consoles)", "fact"),
    ("product", "IMG Series",
     "IMG Series volume: Best for MEDIUM volume (100K-1M parts/year) automotive programs", "fact"),
    
    # ==========================================================================
    # AM SERIES - High Volume Packaging
    # ==========================================================================
    ("product", "AM Series",
     "AM Series: 2 variants, 500x650mm, roll-fed, Mid-Tier pricing", "fact"),
    ("product", "AM Series",
     "AM Series India price: ₹28L - ₹47L for roll-fed vacuum forming", "fact"),
    ("product", "AM Series",
     "AM Series applications: Packaging, high volume thin-gauge production", "fact"),
    ("product", "AM Series",
     "AM Series volume: Best for HIGH volume (>1M parts/year) packaging production", "fact"),
    
    # ==========================================================================
    # FCS SERIES - Inline Form-Cut-Stack
    # ==========================================================================
    ("product", "FCS Series",
     "FCS Series: 2 variants, 500x600 to 600x900mm, full automation, Premium tier", "fact"),
    ("product", "FCS Series",
     "FCS Series India price: ₹65L - ₹95L for inline form-cut-stack machines", "fact"),
    ("product", "FCS Series",
     "FCS Series applications: Inline form-cut-stack for rigid packaging (trays, containers)", "fact"),
    ("product", "FCS Series",
     "FCS Series volume: Best for HIGH volume (>1M parts/year) packaging production", "fact"),
    
    # ==========================================================================
    # PF1-M SERIES - 3D Car Mats
    # ==========================================================================
    ("product", "PF1-M Series",
     "PF1-M Series: 3 variants, 800x1500 to 1400x1900mm, sheet-fed or roll-fed", "fact"),
    ("product", "PF1-M Series",
     "PF1-M Series India price: ₹35L - ₹75L for 3D car mat production", "fact"),
    ("product", "PF1-M Series",
     "PF1-M Series applications: 3D automotive floor mats, TPE/TPO materials", "fact"),
    ("product", "PF1-M Series",
     "PF1-M Series volume: Best for MEDIUM volume (100K-1M parts/year) car mat production", "fact"),
    
    # ==========================================================================
    # PF1-L SERIES - Luggage Shells
    # ==========================================================================
    ("product", "PF1-L Series",
     "PF1-L Series: 1 variant, 800x1000mm, double station configuration", "fact"),
    ("product", "PF1-L Series",
     "PF1-L Series India price: ₹25L - ₹35L for hard shell luggage production", "fact"),
    ("product", "PF1-L Series",
     "PF1-L Series applications: Hard shell travel luggage, PC/ABS materials", "fact"),
    ("product", "PF1-L Series",
     "PF1-L Series volume: Best for LOW volume (<100K parts/year) luggage production", "fact"),
    
    # ==========================================================================
    # PF1-W SERIES - Wellness (Bathtubs/Spas)
    # ==========================================================================
    ("product", "PF1-W Series",
     "PF1-W Series: 3 variants, 800x1200 to 3000x3000mm, automatic operation", "fact"),
    ("product", "PF1-W Series",
     "PF1-W Series India price: ₹45L - ₹1.25Cr for bathtub/spa production", "fact"),
    ("product", "PF1-W Series",
     "PF1-W Series applications: Bathtubs, spas, shower trays - acrylic/ABS materials", "fact"),
    ("product", "PF1-W Series",
     "PF1-W Series volume: Best for LOW volume (<100K parts/year) wellness products", "fact"),
    
    # ==========================================================================
    # MATERIAL SELECTION GUIDE
    # ==========================================================================
    ("product", "Machine Selection",
     "Materials supported: ABS, HIPS, PVC, PET, PP, PC - check thickness compatibility per series", "fact"),
    ("product", "Machine Selection",
     "Material thickness: Thin (0.2-0.5mm) = AM/FCS, Medium (0.5-2mm) = PF1 Classic/X, Thick (2-6mm) = PF1-X/W", "fact"),
    ("product", "Machine Selection",
     "Part size guide: Small (<500mm) = AM/FCS, Medium (500-2000mm) = PF1 Classic/X, Large (>2000mm) = PF1-X/W", "fact"),
    
    # ==========================================================================
    # VOLUME-BASED SELECTION
    # ==========================================================================
    ("product", "Machine Selection",
     "Low volume (<100K/year): Recommend PF1 Classic, PF1-L, PF1-W - batch production focus", "fact"),
    ("product", "Machine Selection",
     "Medium volume (100K-1M/year): Recommend PF1-X, PF1-M, IMG - continuous run capability", "fact"),
    ("product", "Machine Selection",
     "High volume (>1M/year): Recommend AM, FCS - roll-fed inline production", "fact"),
    
    # ==========================================================================
    # APPLICATION-BASED SELECTION
    # ==========================================================================
    ("product", "Machine Selection",
     "Packaging & Food: AM Series (roll-fed), FCS Series (form-cut-stack), PF1 Classic (general)", "fact"),
    ("product", "Machine Selection",
     "Automotive: IMG Series (interior graining), PF1-M (car mats), PF1-X (large parts)", "fact"),
    ("product", "Machine Selection",
     "Industrial & General: PF1 Classic (31 variants, lowest TCO), PF1-X (servo-driven, automation)", "fact"),
    ("product", "Machine Selection",
     "Specialized: PF1-W (bathtubs/spas), PF1-L (luggage shells)", "fact"),
    
    # ==========================================================================
    # PRICE SUMMARY TABLE
    # ==========================================================================
    ("product", "Machine Selection",
     "Price overview: PF1 Classic ₹15-85L | PF1-X ₹45L-2.5Cr | IMG ₹1.25-1.5Cr | AM ₹28-47L | FCS ₹65-95L", "fact"),
    ("product", "Machine Selection",
     "Price overview: PF1-M ₹35-75L | PF1-L ₹25-35L | PF1-W ₹45L-1.25Cr", "fact"),
    
    # ==========================================================================
    # SALES CONSULTATION
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Sales process: Free technical consultation → Custom quote → Factory visit to see machines in action", "fact"),
]

def store_memories():
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING MACHINE SELECTION GUIDE KNOWLEDGE")
    print("=" * 70)
    
    count = 0
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
            count += 1
            print(f"  ✓ {memory_text[:55]}...")
        else:
            print(f"  ⊘ (dup) {memory_text[:40]}...")

    print(f"\n✅ Stored {count} selection guide items")
    print("\n" + "="*70)
    print("MACHINE SELECTION QUICK REFERENCE")
    print("="*70)
    print("""
8 SERIES PORTFOLIO (60+ Models):

┌─────────────────┬────────────────────┬────────────────────┬─────────────────┐
│ Series          │ Size Range         │ Price (INR)        │ Best For        │
├─────────────────┼────────────────────┼────────────────────┼─────────────────┤
│ PF1 Classic     │ 500x650-3000x2000  │ ₹15L - ₹85L        │ General/Low Vol │
│ PF1-X Series    │ 800x1000-5000x2800 │ ₹45L - ₹2.5Cr      │ Premium/Med Vol │
│ IMG Series      │ 500x1200-1200x2000 │ ₹1.25Cr - ₹1.5Cr   │ Auto Interior   │
│ AM Series       │ 500x650mm          │ ₹28L - ₹47L        │ Packaging/High  │
│ FCS Series      │ 500x600-600x900    │ ₹65L - ₹95L        │ Form-Cut-Stack  │
│ PF1-M Series    │ 800x1500-1400x1900 │ ₹35L - ₹75L        │ 3D Car Mats     │
│ PF1-L Series    │ 800x1000mm         │ ₹25L - ₹35L        │ Luggage Shells  │
│ PF1-W Series    │ 800x1200-3000x3000 │ ₹45L - ₹1.25Cr     │ Bathtubs/Spas   │
└─────────────────┴────────────────────┴────────────────────┴─────────────────┘

VOLUME GUIDE:
  Low (<100K/yr):    PF1 Classic, PF1-L, PF1-W
  Medium (100K-1M):  PF1-X, PF1-M, IMG
  High (>1M/yr):     AM, FCS
""")
    return count

if __name__ == "__main__":
    store_memories()
