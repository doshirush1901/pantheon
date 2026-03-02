#!/usr/bin/env python3
"""
Store AM-V-5060 quote knowledge in Ira's memory.
Extracted from: AM-V-5060 Quote Master Format (1).pdf
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
    # AM-V-5060 Overview
    ("product", "AM-V-5060",
     "AM-V-5060 = Roll-fed VACUUM forming machine, 500x600mm forming area, for thin-gauge packaging", "fact"),
    ("product", "AM-V-5060",
     "AM-V-5060 applications: Thin gauge packaging, disposables, containers (HIPS, PVC, PET, ABS)", "fact"),
    ("product", "AM-V-5060",
     "AM-V-5060 is continuous roll-fed - auto sheet advance, heating, forming, cutting in one process", "fact"),
    
    # Key Features
    ("product", "AM-V-5060",
     "AM-V-5060 dry cycle speed: Up to 12 cycles/minute - high-speed production", "fact"),
    ("product", "AM-V-5060",
     "AM-V-5060 precision: Servo indexing with ±0.5mm accuracy, minimal operator intervention", "fact"),
    
    # Specifications
    ("product", "AM-V-5060",
     "AM-V-5060 specs: 500x600mm forming area, depth 100mm below / 90mm above sheet line", "fact"),
    ("product", "AM-V-5060",
     "AM-V-5060 specs: Sheet width 670mm max, thickness 0.3-1.5mm", "fact"),
    ("product", "AM-V-5060",
     "AM-V-5060 power: 16kW, 400V 3-phase, air 6 bar clean & dry, vacuum pump 600 LPM", "fact"),
    
    # Configuration Details
    ("product", "AM-V-5060",
     "AM-V-5060 heating: 32 IR ceramic elements (8x4), 8-zone PID control, TOP-SIDE ONLY, movable oven", "fact"),
    ("product", "AM-V-5060",
     "AM-V-5060 feeding: Servo spike chain (1/2\" duplex, 1\" spike spacing), 750W servo motor with precision gearbox", "fact"),
    ("product", "AM-V-5060",
     "AM-V-5060 forming: Pneumatic press with vacuum capability, manual tool change via bolting", "fact"),
    ("product", "AM-V-5060",
     "AM-V-5060 cutting: Automatic pneumatic shear at exit - continuous operation", "fact"),
    ("product", "AM-V-5060",
     "AM-V-5060 control: PLC with HMI touchscreen, safety interlocks, emergency stops", "fact"),
    
    # Pricing (IMPORTANT)
    ("product", "AM-V-5060",
     "AM-V-5060 India price: ₹7.6 Lakhs base machine + 18% GST", "fact"),
    ("product", "AM-V-5060",
     "AM-V-5060 options: Installation ₹50,000, Training (2 days) ₹50,000", "fact"),
    
    # Commercial Terms
    ("product", "AM-V-5060",
     "AM-V-5060 lead time: 2 months from PO & advance payment", "fact"),
    ("product", "AM-V-5060",
     "AM-V-5060 payment: 50% advance with PO, 50% before dispatch, EXW Gujarat", "fact"),
    ("product", "AM-V-5060",
     "AM-V-5060 warranty: 12 months from commissioning, quote valid 30 days", "fact"),
]

def store_memories():
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 60)
    print("STORING AM-V-5060 QUOTE KNOWLEDGE")
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

    print(f"\n✅ Stored {count} AM-V-5060 items")
    print("\nAM-V-5060 Summary:")
    print("  • Roll-fed vacuum forming, 500x600mm")
    print("  • 12 cycles/min, ±0.5mm precision")
    print("  • Price: ₹7.6 Lakhs + GST")
    print("  • Lead time: 2 months")
    return count

if __name__ == "__main__":
    store_memories()
