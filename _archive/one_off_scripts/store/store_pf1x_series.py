#!/usr/bin/env python3
"""
Store PF1-X Series (Premium Export/Flagship) knowledge in Ira's memory.

Source: Machinecraft Vacuum Forming Machines – Full Model List with Sizes & Descriptions (2).pdf

The PF1-X is the flagship series competing with:
- Geiss T10 (Germany)
- CMS Eidos (Italy)

This is the premium heavy-gauge thermoforming platform for export markets.
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
    # PF1-X SERIES OVERVIEW
    # ==========================================================================
    ("product", "PF1-X Series",
     "PF1-X = Machinecraft FLAGSHIP vacuum forming platform - closed chamber, full servo, premium export grade", "fact"),
    ("product", "PF1-X Series",
     "PF1-X positioning: Competes directly with Geiss T10 (Germany) and CMS Eidos (Italy) in European market", "fact"),
    ("product", "PF1-X Series",
     "PF1-X category: Heavy-gauge thermoforming for sub-contractors serving automotive, agri, EVs, industrial", "fact"),
    ("product", "PF1-X Series",
     "PF1-X key differentiator: Closed chamber design + servo motion + smart HMI at 50-60% lower cost than EU competitors", "fact"),
    
    # ==========================================================================
    # CLOSED CHAMBER SYSTEM
    # ==========================================================================
    ("product", "PF1-X Series",
     "Closed-chamber benefit: Minimizes heat loss, uniform vacuum distribution, reduces external air disturbance", "fact"),
    ("product", "PF1-X Series",
     "Closed-chamber capability: Preblow bubble for male tools, sheet sag control, better surface finish", "fact"),
    ("product", "PF1-X Series",
     "Closed-chamber result: Improved dimensional accuracy, cycle time efficiency, part repeatability", "fact"),
    
    # ==========================================================================
    # VACUUM SYSTEM
    # ==========================================================================
    ("product", "PF1-X Series",
     "Vacuum pump: Oil-lubricated rotary vane, up to 300 m³/hr, brands: Busch, Becker (German)", "fact"),
    ("product", "PF1-X Series",
     "Vacuum tank: 600-4000 liters capacity, instant suction during forming, consistent pressure", "fact"),
    ("product", "PF1-X Series",
     "Servo vacuum valve (option): Festo proportional valve for multi-stage vacuuming (30%, 60%, 100%)", "fact"),
    ("product", "PF1-X Series",
     "Preblow system: Pre-inflates heated sheet before mold contact, ensures even wall thickness", "fact"),
    ("product", "PF1-X Series",
     "Part release: Air-ejection pulse between mold and part for clean release", "fact"),
    
    # ==========================================================================
    # SERVO CONTROL SYSTEM
    # ==========================================================================
    ("product", "PF1-X Series",
     "Servo-controlled movements: Clamp frame (X-Y), Lower platen (Z), optional plug assist - all servo", "fact"),
    ("product", "PF1-X Series",
     "Servo brands: Mitsubishi Electric (Japan) for PLC, HMI, and servo drives", "fact"),
    ("product", "PF1-X Series",
     "Servo benefit: Precise, repeatable motion, smooth mold rise/descent, programmable positions", "fact"),
    
    # ==========================================================================
    # HEATING SYSTEM OPTIONS
    # ==========================================================================
    ("product", "PF1-X Series",
     "Dual-sided heating: Independent top and bottom IR heaters, zone-wise control, recipe presets", "fact"),
    ("product", "PF1-X Series",
     "Heater Option 1 - IR Ceramic: Standard, long-wave IR, best for thick ABS/HDPE/PP, 30-60 sec heat-up", "fact"),
    ("product", "PF1-X Series",
     "Heater Option 2 - IR Quartz: Mid-tier, 10-15 sec startup, energy efficient, good for 3-6mm sheets", "fact"),
    ("product", "PF1-X Series",
     "Heater Option 3 - IR Halogen Flash: Premium, <6 sec warmup, 30-50% energy savings, thin/fast-cycle", "fact"),
    ("product", "PF1-X Series",
     "Heater brands: Elstein, TQS, Ceramicx (European quality)", "fact"),
    
    # ==========================================================================
    # HMI & CONTROL
    # ==========================================================================
    ("product", "PF1-X Series",
     "HMI: 10.1\" touchscreen (upgradeable to 15\"), Mitsubishi, multi-level password protection", "fact"),
    ("product", "PF1-X Series",
     "HMI features: Recipe storage on SD card, alarm history, real-time heater/I/O visualization", "fact"),
    ("product", "PF1-X Series",
     "Control panel: Rittal/Hoffman cabinet, SSR for each heater zone, PID thermal control", "fact"),
    ("product", "PF1-X Series",
     "IIoT option: Internet-enabled remote diagnostics, cloud monitoring, web alerts/reports", "fact"),
    
    # ==========================================================================
    # QUICK CHANGE SYSTEM
    # ==========================================================================
    ("product", "PF1-X Series",
     "Quick tool change: Ball transfer grid on lower platen, mold glides in/out with minimal effort", "fact"),
    ("product", "PF1-X Series",
     "Tool lift assist: Air cylinders lift tool 10-15mm above platen for easy sliding - zero manual lift", "fact"),
    ("product", "PF1-X Series",
     "Tool clamping options: Manual M10 bolts (base) or Quick pneumatic clamping (premium)", "fact"),
    
    # ==========================================================================
    # COOLING SYSTEM
    # ==========================================================================
    ("product", "PF1-X Series",
     "Cooling Option 1 - Centrifugal fans: Standard, adjustable louvers, good for flat/shallow parts", "fact"),
    ("product", "PF1-X Series",
     "Cooling Option 2 - Central ducted: Premium, high-CFM blower, targeted nozzles, faster cycles", "fact"),
    
    # ==========================================================================
    # AUTOLOADER OPTION
    # ==========================================================================
    ("product", "PF1-X Series",
     "Autoloader: Servo-controlled pick & place, pallet-based sheet stack, vacuum suction cups", "fact"),
    ("product", "PF1-X Series",
     "Autoloader features: X-Y servo centering, air-blow separator, double-pick detection sensors", "fact"),
    ("product", "PF1-X Series",
     "Autoloader benefit: Simultaneous loading + unloading, reduces labor, eliminates alignment errors", "fact"),
    
    # ==========================================================================
    # SAFETY & COMPLIANCE
    # ==========================================================================
    ("product", "PF1-X Series",
     "Safety: Light curtains (Sick/Keyence), E-stops, 2-level heater/platen locking, CE compliant", "fact"),
    ("product", "PF1-X Series",
     "Safety interlocks: Heaters, doors, pressure circuits all interlocked per CE standards", "fact"),
    
    # ==========================================================================
    # COMPONENT BRANDS (PREMIUM)
    # ==========================================================================
    ("product", "PF1-X Series",
     "PLC/HMI/Servos: Mitsubishi Electric (Japan) - global support, excellent diagnostics", "fact"),
    ("product", "PF1-X Series",
     "Pneumatics: Festo/SMC - FRL units, high-quality valves", "fact"),
    ("product", "PF1-X Series",
     "Sensors: Keyence/Sick/P+F - safety devices and precision sensing", "fact"),
    ("product", "PF1-X Series",
     "Vacuum: Busch/Becker (Germany) - industrial rotary vane pumps", "fact"),
    ("product", "PF1-X Series",
     "Switchgear: Eaton/Siemens - circuit protection", "fact"),
    
    # ==========================================================================
    # PF1-X MODEL LINEUP (11 Sizes)
    # ==========================================================================
    ("product", "PF1-X-1012",
     "PF1-X-1012: 1200×1000mm max, 800×500mm min - smallest PF1-X, entry export model", "fact"),
    ("product", "PF1-X-1015",
     "PF1-X-1015: 1500×1000mm max, 500×500mm min - compact industrial applications", "fact"),
    ("product", "PF1-X-1215",
     "PF1-X-1215: 1500×1200mm max, 700×500mm min - mid-size for automotive panels", "fact"),
    ("product", "PF1-X-1520",
     "PF1-X-1520: 2000×1500mm max, 1000×500mm min - popular size for door panels, dashboards", "fact"),
    ("product", "PF1-X-1525",
     "PF1-X-1525: 2500×1500mm max, 1500×500mm min - agricultural panels, EV battery covers", "fact"),
    ("product", "PF1-X-1528",
     "PF1-X-1528: 2800×1500mm max, 2000×500mm min - large automotive/commercial vehicle", "fact"),
    ("product", "PF1-X-3020",
     "PF1-X-3020: 3000×2000mm max, 2000×1000mm min - commercial vehicle panels, agri-equipment", "fact"),
    ("product", "PF1-X-3520",
     "PF1-X-3520: 3500×2000mm max, 2500×1000mm min - large format industrial panels", "fact"),
    ("product", "PF1-X-4020",
     "PF1-X-4020: 4000×2000mm max, 3000×1000mm min - bus/coach panels, construction", "fact"),
    ("product", "PF1-X-4525",
     "PF1-X-4525: 4500×2500mm max, 3500×1500mm min - mass transit, large industrial", "fact"),
    ("product", "PF1-X-5028",
     "PF1-X-5028: 5000×2800mm max, 4000×2000mm min - LARGEST PF1-X, swimming pools, spas", "fact"),
    
    # ==========================================================================
    # COMPETITIVE POSITIONING
    # ==========================================================================
    ("product", "PF1-X Series",
     "PF1-X vs Geiss T10: Same servo precision, closed chamber, but 50-60% lower price", "fact"),
    ("product", "PF1-X Series",
     "PF1-X vs CMS Eidos: Comparable automation level, Mitsubishi controls, more cost-effective", "fact"),
    ("product", "PF1-X Series",
     "PF1-X export markets: Europe, North America, Australia, Middle East - premium tier customers", "fact"),
    ("product", "PF1-X Series",
     "PF1-X value proposition: European-level quality & features at Indian manufacturing cost", "fact"),
    
    # ==========================================================================
    # TARGET APPLICATIONS
    # ==========================================================================
    ("product", "PF1-X Series",
     "PF1-X applications: Automotive (EV battery covers, dashboards, door panels), Agriculture (tractor panels)", "fact"),
    ("product", "PF1-X Series",
     "PF1-X applications: Commercial vehicles (bus panels, truck parts), Construction (building panels)", "fact"),
    ("product", "PF1-X Series",
     "PF1-X applications: Wellness (spa shells, bath tubs), Industrial (equipment enclosures)", "fact"),
    
    # ==========================================================================
    # SALES TALKING POINTS
    # ==========================================================================
    ("product", "PF1-X Series",
     "Sales pitch: 'European precision at Indian value - Geiss T10 features without Geiss T10 price'", "fact"),
    ("product", "PF1-X Series",
     "Sales pitch: 'Full servo, closed chamber, Mitsubishi controls - same spec as EU machines'", "fact"),
    ("product", "PF1-X Series",
     "Sales pitch: 'Modular upgrades - start manual, grow to fully automated line'", "fact"),
]

def store_memories():
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING PF1-X SERIES (FLAGSHIP EXPORT) KNOWLEDGE")
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

    print(f"\n✅ Stored {count} PF1-X Series items")
    print("\n" + "="*70)
    print("PF1-X SERIES SUMMARY (FLAGSHIP EXPORT)")
    print("="*70)
    print("""
COMPETITIVE POSITIONING:
  vs Geiss T10 (Germany): Same specs, 50-60% lower price
  vs CMS Eidos (Italy): Comparable automation, better value

KEY DIFFERENTIATORS:
  ✓ Closed-chamber forming (heat retention, vacuum uniformity)
  ✓ Full servo control (Mitsubishi PLC/drives)
  ✓ Premium components (Busch/Becker vacuum, Festo pneumatics)
  ✓ CE safety compliance (Sick/Keyence light curtains)

MODEL LINEUP (11 sizes):
  PF1-X-1012  1200×1000mm   Entry export model
  PF1-X-1015  1500×1000mm   Compact industrial
  PF1-X-1215  1500×1200mm   Automotive panels
  PF1-X-1520  2000×1500mm   Popular: dashboards, doors
  PF1-X-1525  2500×1500mm   Agri panels, EV batteries
  PF1-X-1528  2800×1500mm   Commercial vehicle
  PF1-X-3020  3000×2000mm   Large automotive/agri
  PF1-X-3520  3500×2000mm   Industrial panels
  PF1-X-4020  4000×2000mm   Bus/coach panels
  PF1-X-4525  4500×2500mm   Mass transit
  PF1-X-5028  5000×2800mm   LARGEST: spas, pools

TARGET MARKETS: Europe, N. America, Australia, Middle East
""")
    return count

if __name__ == "__main__":
    store_memories()
