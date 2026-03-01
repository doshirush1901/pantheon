#!/usr/bin/env python3
"""
Store FCS (Form Cut Stack) series knowledge in Ira's memory.
Source: FCS Machinecraft Brochure Oct22.pdf

FCS = Roll-fed inline Form-Cut-Stack machines for rigid packaging
Applications: Material handling trays, medical trays, electronics, food packaging, FMCG, ESD trays
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
    # FCS SERIES OVERVIEW
    # ==========================================================================
    ("product", "FCS Series",
     "FCS = Form Cut Stack - roll-fed inline thermoforming machines for rigid packaging production", "fact"),
    ("product", "FCS Series",
     "FCS process: Roll feeding → Heating → Forming → Steel-rule cutting → Robotic stacking", "fact"),
    ("product", "FCS Series",
     "FCS variants: Eco (pneumatic), Pro (servo motors), XXL (large format 630x900mm)", "fact"),
    
    # ==========================================================================
    # FCS APPLICATIONS - Target Markets
    # ==========================================================================
    ("product", "FCS Series",
     "FCS applications - Food: Fruit/vegetable packaging, ready meal trays, bakery, dairy containers", "fact"),
    ("product", "FCS Series",
     "FCS applications - Industrial: Material handling trays, ESD trays, electronics packaging", "fact"),
    ("product", "FCS Series",
     "FCS applications - Other: Medical packaging, retail trays, tableware (plates, cups, glasses)", "fact"),
    ("product", "FCS Series",
     "FCS ideal for: Rigid packaging in PS, PET, rPET, PP materials - thin-gauge roll-fed production", "fact"),
    
    # ==========================================================================
    # FCS MACHINE STATIONS - Process Flow
    # ==========================================================================
    ("product", "FCS Series",
     "FCS Station 1 - Unwinder: Roll sheet unwinding with pneumatic brake, max roll diameter varies by model", "fact"),
    ("product", "FCS Series",
     "FCS Station 2 - Feeding: Spike chain transport, servo-driven indexing for precise sheet positioning", "fact"),
    ("product", "FCS Series",
     "FCS Station 3 - Heating: Top & bottom IR quartz heaters, individual zone control via HMI, pyrometer option", "fact"),
    ("product", "FCS Series",
     "FCS Station 4 - Forming: Vacuum + pressure (up to 6 bar), plug assist, spring-type sheet clamping", "fact"),
    ("product", "FCS Series",
     "FCS Station 5 - Cutting: Toggle press with steel-rule die, up to 60 tonnes punching force, heated tool option for PET", "fact"),
    ("product", "FCS Series",
     "FCS Station 6 - Stacking: Robotic stacker (servo + pneumatic), up/down or A/B stacking, count setting on HMI", "fact"),
    ("product", "FCS Series",
     "FCS optional: Conveyor belt for stacked parts, trim winding for skeleton waste", "fact"),
    
    # ==========================================================================
    # FCS TECHNICAL FEATURES
    # ==========================================================================
    ("product", "FCS Series",
     "FCS forming: Vacuum + pressure forming up to 6 bar - enough for fine detail on trays", "fact"),
    ("product", "FCS Series",
     "FCS cutting: Toggle-type press design, servo-driven, 60-tonne punching force, XY fine alignment", "fact"),
    ("product", "FCS Series",
     "FCS heating: IR quartz elements, top & bottom heaters, individual temperature control per zone", "fact"),
    ("product", "FCS Series",
     "FCS control: Mitsubishi PLC & servo motors (Japan), 10-inch color HMI touchscreen, recipe storage on SD card", "fact"),
    
    # ==========================================================================
    # FCS TOOLING
    # ==========================================================================
    ("product", "FCS Series",
     "FCS forming tool: CNC machined aluminum, vacuum/pressure compatible", "fact"),
    ("product", "FCS Series",
     "FCS cutting tool: Steel-ruled die system, floating design for even lip cut", "fact"),
    ("product", "FCS Series",
     "FCS stacking fixture: Custom-built per product design", "fact"),
    
    # ==========================================================================
    # FCS MODEL SPECIFICATIONS
    # ==========================================================================
    ("product", "FCS 4060",
     "FCS 4060: 400x600mm forming area, 100mm depth, 15kW total, single top heater 12kW", "fact"),
    ("product", "FCS 5060",
     "FCS 5060: 500x600mm forming area, 100mm depth, 19kW total, single top heater 16kW", "fact"),
    ("product", "FCS 6060",
     "FCS 6060: 600x600mm forming area, 100mm depth, 23kW total, single top heater 20kW", "fact"),
    ("product", "FCS 4060-S",
     "FCS 4060-S: 400x600mm with top+bottom heaters (12kW+8kW), 23kW total, for thicker materials", "fact"),
    ("product", "FCS 5060-S",
     "FCS 5060-S: 500x600mm with top+bottom heaters (16kW+11kW), 29kW total", "fact"),
    ("product", "FCS 6080-S",
     "FCS 6080-S: 600x800mm with top+bottom heaters (25kW+18kW), 45kW total, 120mm depth", "fact"),
    ("product", "FCS 8012-S",
     "FCS 8012-S: 800x1200mm (XXL), 150mm depth, 84kW total, top 48kW + bottom 34kW heaters, 1600 ipm vacuum", "fact"),
    
    # ==========================================================================
    # FCS PAST PROJECTS - References
    # ==========================================================================
    ("product", "FCS Series",
     "FCS reference: FCS 5065 Pro in South Africa - rPET coffee lids production", "fact"),
    ("product", "FCS Series",
     "FCS reference: FCS 5060 in UK, Serbia, Russia, India - PS chocolate trays", "fact"),
    ("product", "FCS Series",
     "FCS reference: FCS 5065 Pro in Hungary & Canada - PP trays production", "fact"),
    
    # ==========================================================================
    # FCS SALES POSITIONING
    # ==========================================================================
    ("product", "FCS Series",
     "FCS sales pitch: 'Complete inline solution - form, cut, stack in one machine for rigid packaging'", "fact"),
    ("product", "FCS Series",
     "FCS target customers: Food packaging, medical tray, electronics packaging, material handling tray manufacturers", "fact"),
    ("product", "FCS Series",
     "FCS advantage: Steel-rule cutting (lower tooling cost vs matched metal), robotic stacking, Mitsubishi controls", "fact"),
    
    # ==========================================================================
    # RELATED AM SERIES (also in brochure)
    # ==========================================================================
    ("product", "AM Series",
     "AM Series specs: 400x600 to 800x1200mm, 100-150mm depth, 15-84kW power, 600-1600 ipm vacuum", "fact"),
    ("product", "AM Series",
     "AM with pressure forming: Air pressure box on upper OR lower platen for detailed parts", "fact"),
    ("product", "TFM Series",
     "TFM Series: Deep-draw cup forming, toggle press for form+cut in place, robotic stacker, 35 cycles/min", "fact"),
    ("product", "AM Series",
     "AM special application: Lamella clarifier production with ultrasonic welding for water filtration plants", "fact"),
]

def store_memories():
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING FCS (FORM CUT STACK) SERIES KNOWLEDGE")
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

    print(f"\n✅ Stored {count} FCS knowledge items")
    print("\n" + "="*70)
    print("FCS SERIES SUMMARY")
    print("="*70)
    print("""
WHAT IS FCS?
  Form-Cut-Stack = Roll-fed inline thermoforming for rigid packaging
  Process: Unwind → Feed → Heat → Form → Cut → Stack

APPLICATIONS:
  • Food: Fruit/veg trays, ready meals, bakery, dairy
  • Industrial: Material handling trays, ESD trays, electronics
  • Medical: Medical packaging trays
  • Consumer: Tableware, cups, plates, retail trays

MODELS:
  FCS 4060    400x600mm   15kW    100mm depth
  FCS 5060    500x600mm   19kW    100mm depth
  FCS 6060    600x600mm   23kW    100mm depth
  FCS 6080-S  600x800mm   45kW    120mm depth (top+bottom heaters)
  FCS 8012-S  800x1200mm  84kW    150mm depth (XXL)

KEY FEATURES:
  • Steel-rule die cutting (60-tonne toggle press)
  • Up to 6 bar pressure forming
  • Robotic stacking (up/down or A/B)
  • Mitsubishi PLC/servo/HMI
  • Heated cutting tool option for PET
""")
    return count

if __name__ == "__main__":
    store_memories()
