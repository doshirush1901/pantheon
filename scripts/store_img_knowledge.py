#!/usr/bin/env python3
"""
Store IMG (In-Mold Graining) technology and MC-IMG-1350 specs in Ira's memory.

Sources:
1. IMGS -1350_ Machinecraft IAC Project Summary (2).pdf - Technical specs
2. Soft-Feel Interiors in the EV Era_ How IMG Thermoforming is Driving Premium Cabin Experiences.pdf - Use cases

IMG = In-Mold Graining - FRIMO-originated technology for premium automotive interiors
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))

from config import load_environment
load_environment()

RUSHABH_IDENTITY_ID = "id_db1a9b47e00d"

ENTITY_MEMORIES = [
    # ==========================================================================
    # WHAT IS IMG? - Technology Overview
    # ==========================================================================
    ("product", "IMG Technology",
     "IMG = In-Mold Graining - advanced thermoforming where preheated plastic sheet is vacuum-formed onto precision-textured mold", "fact"),
    ("product", "IMG Technology",
     "IMG originated from FRIMO (Germany) - 'FRIMO Thermoforming technology' for automotive soft-touch interiors", "fact"),
    ("product", "IMG Technology",
     "IMG creates premium textures, realistic leather grains, custom geometric finishes WITHOUT secondary wrapping or painting", "fact"),
    ("product", "IMG Technology",
     "IMG vs traditional vacuum forming: IMG presses film directly against mold - NO grain distortion or texture washout", "fact"),
    
    # ==========================================================================
    # IMG BENEFITS - Sales Points
    # ==========================================================================
    ("product", "IMG Technology",
     "IMG benefit 1: High-definition grains with no texture distortion - flawless KTX leather grains or laser-engraved geometric patterns", "fact"),
    ("product", "IMG Technology",
     "IMG benefit 2: No secondary processing - texture is built-in, eliminates grain stamping, adhesive bonding, manual wrapping", "fact"),
    ("product", "IMG Technology",
     "IMG benefit 3: Scalability - Machinecraft IMG achieves 120-second cycle times for high-volume production", "fact"),
    ("product", "IMG Technology",
     "IMG benefit 4: Material versatility - works with TPU, TPO, PVC skins, vegan leather, sustainable composites", "fact"),
    ("product", "IMG Technology",
     "IMG benefit 5: Design freedom - multi-texture zones in single skin (e.g. matte upper dash + perforated lower panel)", "fact"),
    
    # ==========================================================================
    # IMG USE CASES - Where It's Used
    # ==========================================================================
    ("product", "IMG Technology",
     "IMG primary use: AUTOMOTIVE SOFT-TOUCH INTERIORS - dashboards, door trims, center consoles, instrument panels", "fact"),
    ("product", "IMG Technology",
     "IMG especially critical for EVs - quiet cabins make interior quality more noticeable, premium feel expected", "fact"),
    ("product", "IMG Technology",
     "IMG applications: Soft-feel dashboard skins, door panel trims, pillar covers, console panels, armrests", "fact"),
    ("product", "IMG Technology",
     "IMG supports EV sustainability: recycled PET, bio-based polymers, vegan leather, PVC-free synthetic skins", "fact"),
    
    # ==========================================================================
    # IMG PROCESS FLOW
    # ==========================================================================
    ("product", "IMG Technology",
     "IMG process: 1) Auto sheet loading → 2) Sheet clamping → 3) IR heating → 4) Vacuum forming onto textured tool → 5) Cooling & release", "fact"),
    ("product", "IMG Technology",
     "IMG tooling: Precision nickel or aluminum tools with laser-engraved grain patterns (imported from US/Germany suppliers)", "fact"),
    
    # ==========================================================================
    # INDUSTRY TRENDS - Why IMG Matters Now
    # ==========================================================================
    ("product", "IMG Technology",
     "EV interior trend: Passengers more focused on cabin comfort with engine noise gone - premium materials benchmark", "fact"),
    ("product", "IMG Technology",
     "EV interiors = 40% of vehicle's total plastic content - push toward recycled plastics, bio-based polymers", "fact"),
    ("product", "IMG Technology",
     "IMG adopters: Global Tier-I suppliers like Forvia, Antolin, Motherson, IAC evaluating IMG for premium EV interiors", "fact"),
    
    # ==========================================================================
    # MC-IMG-1350 TECHNICAL SPECIFICATIONS (IAC Project)
    # ==========================================================================
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 = Machinecraft IMG machine supplied to IAC International Automotive India for Suzuki Y17 program", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 installed at IAC Manesar facility, Feb 2025 - turnkey solution including installation & commissioning", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 platen size: Max 1900x900mm (top & bottom), Working area 1800x800mm", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 tool size: Max 1300x550mm, Height 800mm (upper & lower)", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 blank sheet: Max 1350x600mm, Min 800x400mm", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 daylight opening: 2200mm, Top & bottom platen travel: 1050mm each", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 clamping force: ~10 tonnes, Load capacity: 2000kg per platen", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 vacuum system: 2x vacuum tanks (1000L each), 2x vacuum pumps (100 m³/hr each)", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 platen speed: Max 250mm/s, Min 30mm/s - servo controlled precision", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 heating: IR Quartz 650W elements, 2 grids (6x9 each) top & bottom, Max heating area 1500x650mm", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 power: Heating 70.2kW + Servo 21.8kW = Total ~100kW connected load", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 drives: Full electric servo motor driven (platens, sheet frame adjustments, autoloader)", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 pneumatics: Festo make, certified tanks, valves, adjustable vacuum cups", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 control: Mitsubishi FX5U PLC + 10-inch HMI touchscreen, Mitsubishi servos", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 gearboxes: SEW & Bonfiglioli brands", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 safety: Light sensors, 3-color tower lamp, Harting connectors, safety interlocks", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 cooling: 4x adjustable air blowers (EBM Papst make)", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 quick tool change: Ball transfer units (bottom platen), pneumatic tool clamping", "fact"),
    ("product", "MC-IMG-1350",
     "MC-IMG-1350 clamp frame: Servo motor driven, adjustable in XY directions", "fact"),
    
    # ==========================================================================
    # IAC PROJECT - Case Study Reference
    # ==========================================================================
    ("company", "IAC International Automotive",
     "IAC International Automotive India - Tier-I supplier, purchased MC-IMG-1350 for Suzuki Y17 program, Manesar facility", "fact"),
    ("product", "MC-IMG-1350",
     "IAC project results: Machine built in 5 months, 120-second cycle time, premium grain, zero defects, lower scrap rate", "fact"),
    ("product", "MC-IMG-1350",
     "IAC project: IMG-S tool imported from US-based tooling supplier for premium grain quality", "fact"),
    
    # ==========================================================================
    # IMG SALES POSITIONING
    # ==========================================================================
    ("product", "IMG Series",
     "IMG sales pitch: 'Premium soft-touch interiors for EV era - no secondary ops, 120s cycle, sustainable materials'", "fact"),
    ("product", "IMG Series",
     "IMG target customers: Tier-I automotive interior suppliers (IAC, Forvia, Antolin, Motherson, SL Corp)", "fact"),
    ("product", "IMG Series",
     "IMG positioning: 'Future-proof your interior production for premium EV programs with IMG thermoforming'", "fact"),
]

def store_memories():
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING IMG (IN-MOLD GRAINING) TECHNOLOGY KNOWLEDGE")
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
            print(f"  ✓ {memory_text[:60]}...")
        else:
            print(f"  ⊘ (dup) {memory_text[:45]}...")

    print(f"\n✅ Stored {count} IMG knowledge items")
    print("\n" + "="*70)
    print("IMG KNOWLEDGE SUMMARY")
    print("="*70)
    print("""
WHAT IS IMG?
  In-Mold Graining - FRIMO-originated thermoforming technology
  Vacuum forms preheated sheet onto precision-textured mold
  Creates premium leather grains, soft-touch surfaces, geometric patterns

WHERE IS IMG USED?
  • Automotive soft-touch interiors (dashboards, door trims, consoles)
  • Especially critical for EVs - quiet cabins = premium expectations
  • Tier-I suppliers: IAC, Forvia, Antolin, Motherson

WHY IMG?
  ✓ No texture distortion (vs traditional vacuum forming)
  ✓ No secondary ops (wrapping, painting, stamping)
  ✓ 120-second cycle times (scalable)
  ✓ Works with TPU, TPO, PVC, vegan leather, sustainable materials

MC-IMG-1350 SPECS (IAC Project):
  Platen: 1900x900mm | Tool: 1300x550mm | Blank: 1350x600mm max
  10-tonne clamp | 100kW load | Mitsubishi PLC/servo | Festo pneumatics
""")
    return count

if __name__ == "__main__":
    store_memories()
