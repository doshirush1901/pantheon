#!/usr/bin/env python3
"""
Store AM Series catalogue knowledge in Ira's memory.
Extracted from: AM Machine Catalogue.pdf

AM Series = Thin-gauge roll-fed vacuum forming machines, mainly sold in India.
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
# AM SERIES CATALOGUE KNOWLEDGE
# ============================================================================

ENTITY_MEMORIES = [
    # ==========================================================================
    # AM SERIES OVERVIEW
    # ==========================================================================
    ("product", "AM Series",
     "AM Series = Thin-gauge roll-fed vacuum forming machines - MADE WITH PRIDE IN INDIA", "fact"),
    ("product", "AM Series",
     "AM Series designed for fast, precise, repeatable production of thermoformed parts", "fact"),
    ("product", "AM Series",
     "AM Series mainly sold in India market - entry-level packaging/forming solution", "fact"),
    
    # ==========================================================================
    # STANDARD DESIGN FEATURES
    # ==========================================================================
    ("product", "AM Series",
     "AM standard features: Heavy-duty C-channel fabricated structure, pneumatic-driven movements", "fact"),
    ("product", "AM Series",
     "AM standard features: 4-pillar guided press, servo motor driven chain indexing", "fact"),
    
    # ==========================================================================
    # PROCESS FLOW (for sales explanation)
    # ==========================================================================
    ("product", "AM Series",
     "AM process: 1) Sheet Loading - roll onto integrated stand, 2) Sheet Feeding - servo spiked chain grips & indexes", "fact"),
    ("product", "AM Series",
     "AM process: 3) Heating - uniform heating to optimum temp, 4) Forming - press closes, vacuum pulls sheet over mould", "fact"),
    ("product", "AM Series",
     "AM process: 5) Part Release - compressed air ejects formed part cleanly without distortion", "fact"),
    
    # ==========================================================================
    # SPECIFICATIONS (AM-5060 BASE MODEL)
    # ==========================================================================
    ("product", "AM-5060",
     "AM-5060 specs: Max forming area 500x600mm, male depth 90mm, female depth 100mm", "fact"),
    ("product", "AM-5060",
     "AM-5060 specs: Sheet thickness 0.2-1.2mm, max sheet width 700mm", "fact"),
    ("product", "AM-5060",
     "AM-5060 specs: Vacuum pump 40m³/hr, vacuum tank 200L", "fact"),
    ("product", "AM-5060",
     "AM-5060 power: 400V 50Hz 3P+N+PE, consumption 15kW, air 6 bar @ 200 L/min", "fact"),
    
    # ==========================================================================
    # HEATING SYSTEM
    # ==========================================================================
    ("product", "AM Series",
     "AM heating: Two-index heating zone, trough-type ceramic heaters (24 x 500W = 12kW)", "fact"),
    ("product", "AM Series",
     "AM heating: 8 thermocouple zones, independent heater temperature control via dedicated controller", "fact"),
    ("product", "AM Series",
     "AM heating: Trough yellow ceramic heaters provide efficient radiant heat and long life", "fact"),
    
    # ==========================================================================
    # FORMING STATION
    # ==========================================================================
    ("product", "AM Series",
     "AM forming station: CNC-machined base platen for high precision, 4 tie rods with CI bushings", "fact"),
    ("product", "AM Series",
     "AM forming: Universal tool mounting for quick changes - both male and female tools", "fact"),
    ("product", "AM Series",
     "AM forming: Plug assist compatible, upper/lower platens independently driven", "fact"),
    ("product", "AM Series",
     "AM tooling flexibility: Upper platen locks down for female tools, lower fixed for male tools", "fact"),
    
    # ==========================================================================
    # VACUUM SYSTEM
    # ==========================================================================
    ("product", "AM Series",
     "AM vacuum: High-flow 1-inch vacuum valve for instant evacuation, heavy-duty hose", "fact"),
    ("product", "AM Series",
     "AM vacuum: Air piston-driven pump (reliable, long life), optimally sized tank for high-speed cycles", "fact"),
    
    # ==========================================================================
    # CHAIN INDEXING SYSTEM
    # ==========================================================================
    ("product", "AM Series",
     "AM indexing: 750W servo motor + spiked transmission chain for precision repeatability", "fact"),
    ("product", "AM Series",
     "AM indexing: Heavy-duty worm gearbox (zero backlash), index length settable in 1mm increments via HMI", "fact"),
    
    # ==========================================================================
    # CONTROL SYSTEM
    # ==========================================================================
    ("product", "AM Series",
     "AM control: Dedicated PLC+HMI system, 'Next Generation Control' with 15+ years operator feedback", "fact"),
    ("product", "AM Series",
     "AM HMI features: 7\" full-color touchscreen, recipe management, real-time monitoring, alarms, counters", "fact"),
    ("product", "AM Series",
     "AM recipe system: Save/recall parameters for multiple moulds - reduces setup time between jobs", "fact"),
    
    # ==========================================================================
    # AUTOMATION OPTIONS
    # ==========================================================================
    ("product", "AM Series Inline Press",
     "AM option: Inline hydro-pneumatic press (40 tons) for individual cavity cutting after forming", "fact"),
    ("product", "AM Series Inline Press",
     "AM inline press: Combines pneumatic speed + hydraulic force, cuts clean burr-free edges per cavity", "fact"),
    ("product", "AM Series Inline Press",
     "AM inline press benefit: Parts ready for removal without post-processing needed", "fact"),
    
    ("product", "AM Series Shot Cutter",
     "AM option: Pneumatic shot cutter for clean consistent trimming after each cycle", "fact"),
    ("product", "AM Series Shot Cutter",
     "AM shot cutter: Pneumatic clamp holds sheet, rodless cylinder drives knife across width", "fact"),
    ("product", "AM Series Shot Cutter",
     "AM shot cutter note: Cut parts still need offline trimming station to remove web", "fact"),
    
    # ==========================================================================
    # SALES MESSAGING
    # ==========================================================================
    ("product", "AM Series",
     "AM sales pitch: 'Step into Automation - labor shortages, productivity, efficiency - easier & more affordable than you think'", "fact"),
    ("product", "AM Series",
     "AM target customers: Small-medium packaging producers looking to automate, budget-conscious buyers", "fact"),
    
    # ==========================================================================
    # COMPONENT BRANDS
    # ==========================================================================
    ("product", "AM Series",
     "AM components: Pneumatics (quality brands), PLC+HMI (automation), switchgears, heater controller, gearbox, power chain", "fact"),
]


def store_memories():
    """Store AM Series catalogue knowledge."""
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING AM SERIES CATALOGUE KNOWLEDGE")
    print("=" * 70)
    
    print(f"\n📦 Storing {len(ENTITY_MEMORIES)} AM Series items...")
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
    print(f"COMPLETE: Stored {entity_count} AM Series catalogue items")
    print("=" * 70)
    print("\nIra now knows AM Series details:")
    print("  • Overview & positioning (thin-gauge, roll-fed, India market)")
    print("  • Process flow (loading → feeding → heating → forming → release)")
    print("  • AM-5060 specifications")
    print("  • Heating system (ceramic, zones, control)")
    print("  • Forming station (CNC platen, universal tooling)")
    print("  • Vacuum & indexing systems")
    print("  • Control system (PLC, HMI, recipes)")
    print("  • Automation options (inline press, shot cutter)")
    
    return entity_count


if __name__ == "__main__":
    store_memories()
