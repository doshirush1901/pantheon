#!/usr/bin/env python3
"""
Store Machinecraft India pricing in Ira's memory.
Extracted from: Machinecraft Price List for Plastindia (1).pdf

CRITICAL: This is INR pricing for Indian market sales.
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
# INDIA PRICING - ALL PRICES IN INR (LAKHS)
# ============================================================================

ENTITY_MEMORIES = [
    # ==========================================================================
    # AM SERIES - ENTRY LEVEL ROLL-FED
    # ==========================================================================
    ("product", "AM-5060",
     "India price: ₹7.5 Lakhs - Standard AM machine 500x600mm", "fact"),
    ("product", "AM-6060",
     "India price: ₹9 Lakhs - Standard AM machine 600x600mm", "fact"),
    ("product", "AM-5060-P",
     "India price: ₹15 Lakhs - AM machine 500x600mm with inline hydro-pneumatic press", "fact"),
    ("product", "AM-7080-CM",
     "India price: ₹28 Lakhs - AM machine 700x800mm for Car mat application", "fact"),
    ("product", "AM-100180-CM",
     "India price: ₹50 Lakhs - AM machine 1000x1800mm for Car mat application", "fact"),
    
    # ==========================================================================
    # AM PRESSURE FORMING
    # ==========================================================================
    ("product", "AMP-5060",
     "India price: ₹35 Lakhs - AM pressure forming machine 500x600mm", "fact"),
    ("product", "AMP-6070-S",
     "India price: ₹50 Lakhs - AM pressure forming 500x600mm servo driven", "fact"),
    
    # ==========================================================================
    # FCS INLINE SERIES - FORM CUT STACK
    # ==========================================================================
    ("product", "FCS 6050-3ST",
     "India price: ₹1 Crore - Form/Cut/Stack inline, pneumatic, 3 station", "fact"),
    ("product", "FCS 6050-4ST",
     "India price: ₹1.25 Crore - Form/Cut/Hole/Stack inline, pneumatic, 4 station", "fact"),
    ("product", "FCS 7060-3ST",
     "India price: ₹1.5 Crore - Form/Cut/Stack inline, SERVO, 3 station", "fact"),
    ("product", "FCS 7060-4ST",
     "India price: ₹1.75 Crore - Form/Cut/Hole/Stack inline, SERVO, 4 station", "fact"),
    
    # ==========================================================================
    # UNO SERIES - COMPACT SINGLE STATION
    # ==========================================================================
    ("product", "UNO 0806",
     "India price: ₹15 Lakhs - Single station, top heater only, 800x600mm", "fact"),
    ("product", "UNO 1208",
     "India price: ₹20 Lakhs - Single station, top heater only, 1200x800mm", "fact"),
    ("product", "UNO 1208-2H",
     "India price: ₹25 Lakhs - Single station, sandwich heater (twin), 1200x800mm", "fact"),
    
    # ==========================================================================
    # DUO SERIES - DOUBLE STATION
    # ==========================================================================
    ("product", "DUO 0806",
     "India price: ₹20 Lakhs - Double station, single heater, 800x600mm", "fact"),
    ("product", "DUO 1208",
     "India price: ₹25 Lakhs - Double station, single heater, 1200x800mm", "fact"),
    
    # ==========================================================================
    # IMG SERIES - IN-MOLD GRAINING
    # ==========================================================================
    ("product", "IMG 1205",
     "India price: ₹1.25 Crore - IMG machine 1200x500mm for automotive interiors", "fact"),
    ("product", "IMG 2012",
     "India price: ₹1.75 Crore - IMG machine 2000x1200mm for automotive interiors", "fact"),
    
    # ==========================================================================
    # PLAY - DESKTOP/EDUCATIONAL
    # ==========================================================================
    ("product", "PLAY 450 DT",
     "India price: ₹3.5 Lakhs - Small desktop machine, all movements manual, for education/prototyping", "fact"),
    
    # ==========================================================================
    # PF1 PNEUMATIC SERIES - FLAGSHIP HEAVY-GAUGE
    # ==========================================================================
    ("product", "PF1-C-1008",
     "India price: ₹33 Lakhs - Standard Pneumatic PF1, 1000x800mm", "fact"),
    ("product", "PF1-C-1208",
     "India price: ₹35 Lakhs - Standard Pneumatic PF1, 1200x800mm", "fact"),
    ("product", "PF1-C-1212",
     "India price: ₹38 Lakhs - Standard Pneumatic PF1, 1200x1200mm", "fact"),
    ("product", "PF1-C-1510",
     "India price: ₹40 Lakhs - Standard Pneumatic PF1, 1500x1000mm", "fact"),
    ("product", "PF1-C-1812",
     "India price: ₹45 Lakhs - Standard Pneumatic PF1, 1800x1200mm", "fact"),
    ("product", "PF1-C-2010",
     "India price: ₹50 Lakhs - Standard Pneumatic PF1, 2000x1000mm", "fact"),
    ("product", "PF1-C-2015",
     "India price: ₹60 Lakhs - Standard Pneumatic PF1, 2000x1500mm", "fact"),
    ("product", "PF1-C-2020",
     "India price: ₹65 Lakhs - Standard Pneumatic PF1, 2000x2000mm", "fact"),
    ("product", "PF1-C-2515",
     "India price: ₹70 Lakhs - Standard Pneumatic PF1, 2500x1500mm", "fact"),
    ("product", "PF1-C-3015",
     "India price: ₹75 Lakhs - Standard Pneumatic PF1, 3000x1500mm", "fact"),
    ("product", "PF1-C-3020",
     "India price: ₹80 Lakhs - Standard Pneumatic PF1, 3000x2000mm", "fact"),
    
    # ==========================================================================
    # PF1 WITH ROLL FEEDER
    # ==========================================================================
    ("product", "PF1-R-1510",
     "India price: ₹55 Lakhs - PF1 with roll feeder, 1500x1000mm", "fact"),
    
    # ==========================================================================
    # PF2 PNEUMATIC - OPEN TYPE
    # ==========================================================================
    ("product", "PF2-P2010",
     "India price: ₹35 Lakhs - Open type PF2 pneumatic, 2000x1000mm", "fact"),
    ("product", "PF2-P2020",
     "India price: ₹52 Lakhs - Open type PF2 pneumatic, 2000x2000mm", "fact"),
    ("product", "PF2-P2424",
     "India price: ₹60 Lakhs - Open type PF2 pneumatic, 2400x2400mm", "fact"),
    
    # ==========================================================================
    # PRICING SUMMARY FOR QUICK REFERENCE
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "India pricing range: ₹3.5 Lakhs (PLAY desktop) to ₹1.75 Crore (IMG 2012)", "fact"),
    ("company", "Machinecraft Technologies",
     "Entry-level AM machines start at ₹7.5-9 Lakhs (India pricing)", "fact"),
    ("company", "Machinecraft Technologies",
     "Heavy-gauge PF1 pneumatic range: ₹33-80 Lakhs depending on size (India pricing)", "fact"),
    ("company", "Machinecraft Technologies",
     "Inline FCS packaging machines: ₹1-1.75 Crore (India pricing)", "fact"),
    ("company", "Machinecraft Technologies",
     "Compact UNO/DUO machines: ₹15-25 Lakhs ideal for startups (India pricing)", "fact"),
]


def store_memories():
    """Store India pricing knowledge."""
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING MACHINECRAFT INDIA PRICING (INR)")
    print("=" * 70)
    
    print(f"\n💰 Storing {len(ENTITY_MEMORIES)} pricing items...")
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
            print(f"  ✓ [{entity_type}:{entity_name}] {memory_text[:55]}...")
        else:
            print(f"  ⊘ (duplicate) {memory_text[:40]}...")
    
    print("\n" + "=" * 70)
    print(f"COMPLETE: Stored {entity_count} India pricing items")
    print("=" * 70)
    print("\nIra now knows India market pricing:")
    print("  • AM Series: ₹7.5L - ₹50L")
    print("  • AM Pressure Forming: ₹35L - ₹50L")
    print("  • FCS Inline: ₹1Cr - ₹1.75Cr")
    print("  • UNO/DUO Compact: ₹15L - ₹25L")
    print("  • IMG Automotive: ₹1.25Cr - ₹1.75Cr")
    print("  • PF1 Heavy-gauge: ₹33L - ₹80L")
    print("  • PF2 Open-type: ₹35L - ₹60L")
    print("  • PLAY Desktop: ₹3.5L")
    
    return entity_count


if __name__ == "__main__":
    store_memories()
