#!/usr/bin/env python3
"""
Store FCS 6070-3S EUR quotation knowledge in Ira's memory.
Extracted from: EUR_Quotation_ Machinecraft FCS 6070-3S.docx (1).pdf

This is the European market quotation for the FCS Series inline thermoformer.
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
    # FCS 6070-3S Overview
    ("product", "FCS 6070-3S",
     "FCS 6070-3S = Form-Cut-Stack 3-station fully automatic thermoformer for high-volume packaging", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S integrates Forming, Cutting, and Stacking in one continuous roll-fed process", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S designed for 24/7 industrial production, CE certified for European market", "fact"),
    
    # Technical Specifications
    ("product", "FCS 6070-3S",
     "FCS 6070-3S forming area: 600 x 700 mm net usable area", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S max sheet width: 870 mm, thickness range 0.3-1.4 mm", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S max forming depth: 150 mm, pressure forming up to 4 bar", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S speed: Up to 50 cycles/min dry run - high throughput", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S heating: ~90 kW IR heaters (Elstein Germany), multi-zone control", "fact"),
    
    # Stations & Features
    ("product", "FCS 6070-3S",
     "FCS 6070-3S forming station: Servo-driven press with pressure forming capability", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S cutting station: Servo-driven trimming press with steel rule die, X-Y motorized adjustment", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S stacking: Down-stacking system with conveyor, servo-driven", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S mold change time: 15-30 minutes with pneumatic quick-lock system", "fact"),
    
    # Components (Premium European brands)
    ("product", "FCS 6070-3S",
     "FCS 6070-3S components: Mitsubishi PLC/HMI/Servos (Japan), FESTO pneumatics (Germany)", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S components: Elstein heaters, Becker/Busch vacuum pump, Bonfiglioli/SEW gearboxes", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S control: Mitsubishi 15\" color touchscreen HMI, recipe management, alarm diagnostics", "fact"),
    
    # EUR PRICING (IMPORTANT FOR EUROPEAN SALES)
    ("product", "FCS 6070-3S",
     "FCS 6070-3S EUR price: €165,000 Ex-Works India (excludes duties/shipping)", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S EUR payment: 30% advance, 60% before dispatch, 10% after commissioning", "fact"),
    
    # Commercial Terms
    ("product", "FCS 6070-3S",
     "FCS 6070-3S lead time: 6 months from PO & advance", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S delivery: EXW India, seaworthy wooden crate packing included", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S installation: 5 days on-site supervision included, travel/lodging at buyer's cost", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S warranty: 12 months from dispatch, spare parts available 10+ years", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S quote validity: 60 days", "fact"),
    
    # Scope of Supply
    ("product", "FCS 6070-3S",
     "FCS 6070-3S includes: Machine, heating oven, all 3 stations, sheet transport, trim winder, control panel", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S includes: Vacuum system, pneumatics, safety guarding (CE), documentation, FAT & training", "fact"),
    ("product", "FCS 6070-3S",
     "FCS 6070-3S excludes: Production tooling/molds, raw material, compressed air, chilled water at site", "fact"),
    
    # Safety & Certification
    ("product", "FCS 6070-3S",
     "FCS 6070-3S safety: Full CE compliance, safety doors with interlocks, e-stops, light curtains", "fact"),
    
    # FCS Series General
    ("product", "FCS Series",
     "FCS Series = Form-Cut-Stack inline thermoformers for high-volume packaging (cups, trays, containers)", "fact"),
    ("product", "FCS Series",
     "FCS Series European pricing starts at €165,000 for 6070-3S model", "fact"),
]

def store_memories():
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 60)
    print("STORING FCS 6070-3S EUR QUOTATION KNOWLEDGE")
    print("=" * 60)
    
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

    print(f"\n✅ Stored {count} FCS 6070-3S EUR items")
    print("\nFCS 6070-3S Summary:")
    print("  • 3-station Form-Cut-Stack")
    print("  • 600x700mm forming, 150mm depth")
    print("  • Up to 50 cycles/min")
    print("  • EUR €165,000 Ex-Works")
    print("  • 6 months lead time")
    print("  • CE certified, premium components")
    return count

if __name__ == "__main__":
    store_memories()
