#!/usr/bin/env python3
"""
Store PF1 machine production Gantt chart knowledge in Ira's memory.
Extracted from: Gannt Chart Machine - XL Machine - Machinecraft (1).xlsx

This defines the production phases and timeline for building a PF1 machine.
Critical for CRM - answering "What's my machine status?" questions.
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
# PF1 PRODUCTION GANTT CHART - PHASES & TIMELINE
# Total timeline: ~9 weeks (2+ months)
# ============================================================================

ENTITY_MEMORIES = [
    # ==========================================================================
    # OVERALL PRODUCTION TIMELINE
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "PF1 machine production timeline: ~9 weeks (2+ months) from PO to FAT", "fact"),
    ("company", "Machinecraft Technologies",
     "PF1 production phases: Design → Purchasing → Fabrication → Assembly → Wiring → Programming → FAT", "fact"),
    
    # ==========================================================================
    # PHASE 1: ORDER & PAYMENT (Week 1)
    # ==========================================================================
    ("product", "PF1 Production",
     "Phase 1 - Order: PO receipt, 1st payment received (Week 1)", "fact"),
    
    # ==========================================================================
    # PHASE 2: MACHINE DESIGN (Weeks 1-3)
    # ==========================================================================
    ("product", "PF1 Production",
     "Phase 2 - Design (Weeks 1-3): Basic Concept, 2D Sketch, 3D Modelling", "fact"),
    ("product", "PF1 Production",
     "Design tasks: Servo calculations, Gearbox calculations, Electrical drawing, Pneumatic drawing", "fact"),
    ("product", "PF1 Production",
     "Design deliverable: BOM (Bill of Materials) generation completes design phase", "fact"),
    
    # ==========================================================================
    # PHASE 3: PURCHASING (Weeks 2-4)
    # ==========================================================================
    ("product", "PF1 Production",
     "Phase 3 - Purchasing (Weeks 2-4): Vendor negotiation, Purchase orders placed", "fact"),
    ("product", "PF1 Production",
     "Purchasing runs parallel with design - components ordered as specs finalize", "fact"),
    
    # ==========================================================================
    # PHASE 4: FABRICATION/MANUFACTURING (Weeks 3-6)
    # ==========================================================================
    ("product", "PF1 Production",
     "Phase 4 - Fabrication (Weeks 3-6): Steel cutting, machining, welding of frame components", "fact"),
    ("product", "PF1 Production",
     "Fabrication includes: Frame fabrication, platen machining, guide rod manufacturing", "fact"),
    ("product", "PF1 Production",
     "Fabrication final step: Powder coating of all fabricated parts", "fact"),
    
    # ==========================================================================
    # PHASE 5: ASSEMBLY (Weeks 5-7)
    # ==========================================================================
    ("product", "PF1 Production",
     "Phase 5 - Assembly (Weeks 5-7): Forming Press, Heating Station, Loading Station, Sheet Frame", "fact"),
    ("product", "PF1 Production",
     "Assembly sequence: Press assembly first, then heating oven, then loading system", "fact"),
    
    # ==========================================================================
    # PHASE 6: ELECTRICAL & PNEUMATIC (Weeks 6-8)
    # ==========================================================================
    ("product", "PF1 Production",
     "Phase 6a - Electrical Wiring (Weeks 6-7): Wiring of motors, heaters, sensors, safety systems", "fact"),
    ("product", "PF1 Production",
     "Phase 6b - Panel Assembly (Week 7): Control panel wiring, PLC, HMI installation", "fact"),
    ("product", "PF1 Production",
     "Phase 6c - Pneumatic Assembly (Week 7): Pneumatic valves, cylinders, tubing installation", "fact"),
    
    # ==========================================================================
    # PHASE 7: SOFTWARE & TESTING (Weeks 8-9)
    # ==========================================================================
    ("product", "PF1 Production",
     "Phase 7a - Programming (Week 8): PLC programming, HMI configuration, motion tuning", "fact"),
    ("product", "PF1 Production",
     "Phase 7b - Debugging (Weeks 8-9): System testing, parameter tuning, issue resolution", "fact"),
    
    # ==========================================================================
    # PHASE 8: FAT (Week 9)
    # ==========================================================================
    ("product", "PF1 Production",
     "Phase 8 - FAT (Week 9): Factory Acceptance Test - customer inspection and trial runs", "fact"),
    ("product", "PF1 Production",
     "FAT marks production completion - machine ready for dispatch after 2nd payment", "fact"),
    
    # ==========================================================================
    # CRM STATUS UPDATES (For customer communication)
    # ==========================================================================
    ("product", "PF1 Production",
     "Customer status Week 1-2: 'Your machine is in design phase - finalizing 3D models and BOM'", "fact"),
    ("product", "PF1 Production",
     "Customer status Week 3-4: 'Components ordered, fabrication has begun on main frame'", "fact"),
    ("product", "PF1 Production",
     "Customer status Week 5-6: 'Fabrication complete, machine assembly in progress'", "fact"),
    ("product", "PF1 Production",
     "Customer status Week 7-8: 'Electrical and pneumatic installation, programming started'", "fact"),
    ("product", "PF1 Production",
     "Customer status Week 9: 'Machine in testing phase, preparing for FAT - please confirm visit dates'", "fact"),
]

def store_memories():
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 60)
    print("STORING PF1 PRODUCTION GANTT CHART KNOWLEDGE")
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

    print(f"\n✅ Stored {count} production Gantt items")
    print("\nPF1 Production Timeline (~9 weeks):")
    print("  Week 1-2:  Design (concept, 3D, drawings, BOM)")
    print("  Week 2-4:  Purchasing (vendor nego, POs)")
    print("  Week 3-6:  Fabrication (cutting, machining, coating)")
    print("  Week 5-7:  Assembly (press, heater, loader)")
    print("  Week 6-8:  Electrical, Pneumatic, Panel")
    print("  Week 8-9:  Programming, Debugging")
    print("  Week 9:    FAT (Factory Acceptance Test)")
    return count

if __name__ == "__main__":
    store_memories()
