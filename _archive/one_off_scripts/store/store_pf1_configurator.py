#!/usr/bin/env python3
"""
Store PF1 Configurator Design and Inquiry Form insights in Ira's memory.

Sources:
1. Machinecraft PF1 Thermoformer Configurator Design.pdf - Configuration options
2. Single Station Inquiry Form (Responses) (2).xlsx - 69 real customer inquiries

This knowledge helps Ira guide customers through machine configuration.
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
    # CONFIGURATOR OVERVIEW
    # ==========================================================================
    ("product", "PF1 Configurator",
     "PF1 configurator: Step-by-step machine selection - 1) Select size, 2) Configure options, 3) Generate quote", "fact"),
    ("product", "PF1 Configurator",
     "PF1 model naming: Number indicates forming area in cm (PF1-1020 = 1000x2000mm, PF1-3025 = 3000x2500mm)", "fact"),
    
    # ==========================================================================
    # OPTION 1: FRAME TYPE & SIZE ADJUSTMENT
    # ==========================================================================
    ("product", "PF1 Configuration",
     "Frame Option 1 - Fixed Frames: Manual adjustment, robust steel/aluminum, 1-2 hour changeover time, base price included", "fact"),
    ("product", "PF1 Configuration",
     "Frame Option 2 - Universal Frames: Servo-driven motorized adjustment, automatic X/Y sizing via HMI, fast changeover", "fact"),
    ("product", "PF1 Configuration",
     "Universal frames: Preset sheet sizes programmable, premium option adds significant cost but saves changeover time", "fact"),
    
    # ==========================================================================
    # OPTION 2: SHEET LOADING SYSTEM
    # ==========================================================================
    ("product", "PF1 Configuration",
     "Loading Option 1 - Manual with Light Guard: Operator loads sheets by hand, light curtain safety, economic choice", "fact"),
    ("product", "PF1 Configuration",
     "Loading Option 2 - Roll Feeder: For sheets up to 2mm thickness, continuous roll feeding, higher throughput", "fact"),
    ("product", "PF1 Configuration",
     "Loading Option 3 - Robotic Autoloader: Automatic sheet loading AND part unloading, highest automation level", "fact"),
    
    # ==========================================================================
    # OPTION 3: TOOL CLAMPING
    # ==========================================================================
    ("product", "PF1 Configuration",
     "Tool Clamping Option 1 - M10 Bolts: Manual bolting to platen, lowest cost, longer tool change time", "fact"),
    ("product", "PF1 Configuration",
     "Tool Clamping Option 2 - Quick Pneumatic: Pneumatic clamping system, fast tool changes, mid-range option", "fact"),
    ("product", "PF1 Configuration",
     "Tool Clamping Option 3 - Pneumatic with Auto-Alignment: Automatic tool positioning + pneumatic clamp, fastest", "fact"),
    
    # ==========================================================================
    # OPTION 4: TOOL LOADING
    # ==========================================================================
    ("product", "PF1 Configuration",
     "Tool Loading Option 1 - Forklift: Use forklift to load/unload tools, most common for large tools", "fact"),
    ("product", "PF1 Configuration",
     "Tool Loading Option 2 - Ball Transfer Units: Rolling ball table for easy manual tool sliding, quicker changes", "fact"),
    
    # ==========================================================================
    # OPTION 5: HEATER MOVEMENT
    # ==========================================================================
    ("product", "PF1 Configuration",
     "Heater Movement Option 1 - Pneumatic: High-temperature cylinder driven, economic option", "fact"),
    ("product", "PF1 Configuration",
     "Heater Movement Option 2 - Electric Servo: Fast, precise positioning, energy efficient, premium option", "fact"),
    
    # ==========================================================================
    # OPTION 6: HEATER TYPE
    # ==========================================================================
    ("product", "PF1 Configuration",
     "Heater Option 1 - IR Quartz: Energy saving, fast heat-up, most popular choice for efficiency", "fact"),
    ("product", "PF1 Configuration",
     "Heater Option 2 - IR Ceramic: Rugged, durable, good for harsh environments, slower heat-up", "fact"),
    ("product", "PF1 Configuration",
     "Heater Option 3 - IR Halogen Flash: Very fast heating, special applications, highest energy use", "fact"),
    
    # ==========================================================================
    # OPTION 7: BOTTOM TABLE MOVEMENT
    # ==========================================================================
    ("product", "PF1 Configuration",
     "Bottom Table Option 1 - Pneumatic: Economic option, adequate for most applications", "fact"),
    ("product", "PF1 Configuration",
     "Bottom Table Option 2 - Electric Servo: Fast & energy efficient, precise control, premium", "fact"),
    
    # ==========================================================================
    # OPTION 8: UPPER TABLE MOVEMENT
    # ==========================================================================
    ("product", "PF1 Configuration",
     "Upper Table Option 1 - Pneumatic with Motorised Height: Economic option with height adjustment capability", "fact"),
    ("product", "PF1 Configuration",
     "Upper Table Option 2 - Electric Servo: Fast & energy efficient, full servo control, premium", "fact"),
    
    # ==========================================================================
    # OPTION 9: HEATER CONTROLLER
    # ==========================================================================
    ("product", "PF1 Configuration",
     "Heater Controller Option 1 - Solid State Relay: Standard control, reliable, economic", "fact"),
    ("product", "PF1 Configuration",
     "Heater Controller Option 2 - Special Heatronik Type: Detects faulty heaters automatically, premium diagnostic", "fact"),
    
    # ==========================================================================
    # OPTION 10: COOLING SYSTEM
    # ==========================================================================
    ("product", "PF1 Configuration",
     "Cooling Option 1 - Centrifugal Fans: Economic cooling, standard option", "fact"),
    ("product", "PF1 Configuration",
     "Cooling Option 2 - Central Ducted Cooling: Premium cooling, better temperature control, higher cost", "fact"),
    
    # ==========================================================================
    # INQUIRY FORM INSIGHTS - 69 Customer Submissions
    # ==========================================================================
    ("product", "PF1 Market Insights",
     "Inquiry data: 69 submissions from 2022-2025, global customers, revealing configuration preferences", "fact"),
    
    # TOP INDUSTRIES FROM INQUIRIES
    ("product", "PF1 Market Insights",
     "Top industry: Automotive (Passenger + Commercial Vehicles) - 40%+ of inquiries, ABS/TPO/PC materials", "fact"),
    ("product", "PF1 Market Insights",
     "Other industries: Sanitary-ware, Refrigeration, Pallets/Material Handling, Luggage, Medical, Agriculture", "fact"),
    
    # MOST REQUESTED FORMING AREAS
    ("product", "PF1 Market Insights",
     "Popular sizes: 1000x1500mm, 1200x2000mm, 2000x2500mm, 2000x3000mm - medium to large machines", "fact"),
    ("product", "PF1 Market Insights",
     "Large machine demand: 2500x4500mm, 3000x4000mm, 3000x5000mm - commercial vehicle/mass transit", "fact"),
    
    # MOST REQUESTED DEPTHS
    ("product", "PF1 Market Insights",
     "Popular depths: 400mm, 500mm, 650mm, 750mm - 400-750mm range covers 80% of inquiries", "fact"),
    ("product", "PF1 Market Insights",
     "Deep draw requests: 1050mm depth for special applications (large parts, spas, tanks)", "fact"),
    
    # MATERIALS TRENDS
    ("product", "PF1 Market Insights",
     "Top material requested: ABS (most common), followed by PC, PMMA, TPO, PE-HD, PP", "fact"),
    ("product", "PF1 Market Insights",
     "Multi-material requests: Many customers need ABS+PC, ABS+PMMA, or 'all materials' capability", "fact"),
    
    # SHEET THICKNESS TRENDS
    ("product", "PF1 Market Insights",
     "Common thickness: 'up to 6mm' most requested, followed by 'up to 8mm' and 'up to 10mm'", "fact"),
    ("product", "PF1 Market Insights",
     "Thin material requests: 'up to 2mm' for luggage, car mats, TPE applications", "fact"),
    
    # MOST SELECTED OPTIONS (from form data)
    ("product", "PF1 Market Insights",
     "Popular loading choice: 'Economic - Manual with Light Guard Safety' - 50%+ of inquiries", "fact"),
    ("product", "PF1 Market Insights",
     "Popular loading upgrade: 'Automatic Robot for Sheet Loading & Unloading' - 25% of inquiries", "fact"),
    ("product", "PF1 Market Insights",
     "Popular frame choice: 'Universal Frames for Automatic Sheet Size Setting' - 60%+ choose this", "fact"),
    ("product", "PF1 Market Insights",
     "Popular heater: 'IR Quartz Type (Energy Saving)' - 70%+ choose this for efficiency", "fact"),
    ("product", "PF1 Market Insights",
     "Popular servo upgrade: 'Electric Servo Motor Driven' for heater, bottom, upper tables - premium customers", "fact"),
    
    # NOTABLE CUSTOMERS FROM INQUIRIES
    ("contact", "Ather Energy",
     "Inquiry lead: Ather Energy (India) - EV manufacturer, 1200x2000mm, ABS, full servo, robotic loading", "context"),
    ("contact", "Toyota Gibraltar",
     "Inquiry lead: Toyota Gibraltar Stockholding Ltd - automotive, 2000x2500mm, all materials, 10mm", "context"),
    ("contact", "NTF India",
     "Inquiry lead: NTF India Pvt. Ltd. - automotive/medical, 2000x3000mm, ABS/PMMA/PC, robotic loading", "context"),
    ("contact", "Big Bear Plastic Products",
     "Inquiry lead: Big Bear Plastic Products (UK) - commercial vehicles, 3000x5000mm, full servo, robotic", "context"),
    ("contact", "Forbes Marshall",
     "Inquiry lead: Forbes Marshall (India) - R&D prototyping, small machine, ABS/Acrylic/PS/PC", "context"),
    ("contact", "AMTZ",
     "Inquiry lead: AMTZ (India) - medical device enclosures, 1000x1000mm, ABS 2-7mm", "context"),
    
    # ==========================================================================
    # CONFIGURATION RECOMMENDATIONS
    # ==========================================================================
    ("product", "PF1 Configuration",
     "Budget config: Fixed frames + Manual loading + M10 bolts + Pneumatic drives + IR Ceramic + Centrifugal fans", "fact"),
    ("product", "PF1 Configuration",
     "Standard config: Universal frames + Manual with light guard + Quick pneumatic clamp + IR Quartz + SSR control", "fact"),
    ("product", "PF1 Configuration",
     "Premium config: Universal frames + Robotic loading + Auto-alignment clamp + Full servo drives + Heatronik + Ducted cooling", "fact"),
]

def store_memories():
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING PF1 CONFIGURATOR & INQUIRY INSIGHTS")
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

    print(f"\n✅ Stored {count} configurator/inquiry items")
    print("\n" + "="*70)
    print("PF1 CONFIGURATION OPTIONS SUMMARY")
    print("="*70)
    print("""
CONFIGURABLE OPTIONS:

1. FRAME TYPE
   □ Fixed Frames (base) - 1-2hr changeover
   □ Universal Frames (premium) - auto XY adjustment

2. SHEET LOADING
   □ Manual with Light Guard (economic)
   □ Roll Feeder (for <2mm sheets)
   □ Robotic Autoloader (premium)

3. TOOL CLAMPING
   □ M10 Bolts (base)
   □ Quick Pneumatic (standard)
   □ Pneumatic + Auto-Alignment (premium)

4. HEATER TYPE
   □ IR Ceramic (rugged)
   □ IR Quartz (energy saving) ← MOST POPULAR
   □ IR Halogen Flash (fast)

5. DRIVE SYSTEMS
   □ Pneumatic (economic)
   □ Electric Servo (premium) ← TRENDING UP

INQUIRY TRENDS (69 customers):
  • Top Industry: Automotive (40%+)
  • Popular Sizes: 1200x2000, 2000x2500, 2000x3000mm
  • Top Material: ABS (then PC, PMMA, TPO)
  • Preferred: Universal frames (60%), IR Quartz (70%)
""")
    return count

if __name__ == "__main__":
    store_memories()
