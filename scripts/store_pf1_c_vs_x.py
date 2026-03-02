#!/usr/bin/env python3
"""
Store PF1-C vs PF1-X series differentiation in Ira's memory.

PF1-C = Classic (pneumatic, fixed frames, manual loading)
PF1-X = Advanced (servo, universal frames, auto loading)
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
# PF1-C vs PF1-X SERIES DIFFERENTIATION
# ============================================================================

ENTITY_MEMORIES = [
    # ==========================================================================
    # PF1-C SERIES (CLASSIC)
    # ==========================================================================
    ("product", "PF1-C Series",
     "PF1-C = Classic series: air cylinder driven movements (pneumatic), simpler construction", "fact"),
    ("product", "PF1-C Series",
     "PF1-C features: Fixed clamp frames (manual changeover 60-120 min), simpler tool change system", "fact"),
    ("product", "PF1-C Series",
     "PF1-C typically has manual sheet loading/unloading - lower cost, suitable for lower volume production", "fact"),
    ("product", "PF1-C Series",
     "PF1-C pneumatic platen has fixed speed - no acceleration/deceleration profile control", "fact"),
    ("product", "PF1-C Series",
     "PF1-C is more economical option, ideal for: simpler applications, tighter budgets, lower production volumes", "fact"),
    
    # ==========================================================================
    # PF1-X SERIES (ADVANCED/SERVO)
    # ==========================================================================
    ("product", "PF1-X Series",
     "PF1-X = Advanced series: FULL SERVO motor driven movements - precision control", "fact"),
    ("product", "PF1-X Series",
     "PF1-X features: Universal frames (quick format changes), quicker tool change system options", "fact"),
    ("product", "PF1-X Series",
     "PF1-X typically includes autoloader AND auto-unloader - higher automation, faster cycle times", "fact"),
    ("product", "PF1-X Series",
     "PF1-X servo platen allows programmable acceleration/deceleration profiles for sensitive materials", "fact"),
    ("product", "PF1-X Series",
     "PF1-X is premium option, ideal for: high-volume production, frequent format changes, demanding applications", "fact"),
    
    # ==========================================================================
    # COMPARISON FOR SALES CONVERSATIONS
    # ==========================================================================
    ("product", "PF1 Series",
     "PF1-C vs PF1-X: C=Classic (pneumatic, fixed frames, manual), X=Advanced (servo, universal frames, auto)", "fact"),
    ("product", "PF1 Series",
     "Recommend PF1-C when: budget-conscious, single product runs, simpler parts, lower volume", "fact"),
    ("product", "PF1 Series",
     "Recommend PF1-X when: high volume, multiple products, quick changeovers needed, premium quality required", "fact"),
    ("product", "PF1 Series",
     "Key upgrade path: Customer can start with PF1-C and later projects can move to PF1-X as volume grows", "fact"),
]


def store_memories():
    """Store PF1-C vs PF1-X knowledge."""
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING PF1-C vs PF1-X SERIES DIFFERENTIATION")
    print("=" * 70)
    
    print(f"\n🔧 Storing {len(ENTITY_MEMORIES)} items...")
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
            print(f"  ✓ [{entity_name}] {memory_text[:55]}...")
        else:
            print(f"  ⊘ (duplicate) {memory_text[:40]}...")
    
    print("\n" + "=" * 70)
    print(f"COMPLETE: Stored {entity_count} PF1-C vs PF1-X items")
    print("=" * 70)
    print("\nIra now understands:")
    print("  PF1-C (Classic):")
    print("    • Air cylinder/pneumatic driven")
    print("    • Fixed clamp frames (60-120 min changeover)")
    print("    • Manual loading/unloading")
    print("    • Fixed platen speed")
    print("    • Budget-friendly option")
    print("")
    print("  PF1-X (Advanced):")
    print("    • Full servo motor driven")
    print("    • Universal frames (quick changeover)")
    print("    • Autoloader + auto-unloader")
    print("    • Programmable speed profiles")
    print("    • Premium option for high-volume")
    
    return entity_count


if __name__ == "__main__":
    store_memories()
