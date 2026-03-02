#!/usr/bin/env python3
"""
Store Machinecraft Nov 2025 Order Book in Ira's memory.
Source: Machinecraft Nov 2025 Order Book.xlsx

This contains active orders, customer details, machine models, and delivery status.
Critical for CRM - tracking customer orders and machine delivery timelines.
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

# Order book data as of Nov 2025
ENTITY_MEMORIES = [
    # ==========================================================================
    # ORDER BOOK SUMMARY
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Order book Nov 2025: 16 active projects across India, Netherlands, Japan, Italy, UK", "fact"),
    ("company", "Machinecraft Technologies",
     "Order book regions: India (11 orders), Japan (2), Netherlands (1), Italy (1), UK (1)", "fact"),
    
    # ==========================================================================
    # COMPLETED / SHIPPING ORDERS
    # ==========================================================================
    ("contact", "DutchTides",
     "Customer: DutchTides (Netherlands) - PF1-X-6419, Status: Packing & Shipping, Deadline: Nov 15, 2025", "context"),
    ("contact", "DutchTides",
     "DutchTides order 24006: Large PF1-X 6400x1900mm machine for Netherlands market", "context"),
    
    ("contact", "Venkateshwar",
     "Customer: Venkateshwar (India) - PF1-C-3020, Status: Complete, Awaiting wet trial, Deadline: Nov 30, 2025", "context"),
    ("contact", "Venkateshwar",
     "Venkateshwar order needs: Mould, sheets, tool base, sheet frame for wet trial", "context"),
    ("contact", "Venkateshwar",
     "Customer: Venkateshwar (India) - RT-4A 3020, Status: Complete, Deadline: Nov 30, 2025", "context"),
    
    ("contact", "RIDAT",
     "Customer: RIDAT (UK) - ATF RAFTER, Status: Complete, Awaiting customer approval", "context"),
    
    ("contact", "Priti",
     "Customer: Priti (India) - AM 6050, Status: Complete, Awaiting customer payment", "context"),
    
    ("contact", "Convertex",
     "Customer: Convertex (India) - AM 6050, Status: Complete, Awaiting customer payment", "context"),
    
    # ==========================================================================
    # IN PRODUCTION - FABRICATION/ASSEMBLY
    # ==========================================================================
    ("contact", "Pinnacle",
     "Customer: Pinnacle (India) - PF1-X-5028-UA, Status: Fabrication, Awaiting painting, Deadline: Dec 15, 2025", "context"),
    ("contact", "Pinnacle",
     "Pinnacle order 25002: PF1-X with 5000x2800mm forming area, universal autoloader", "context"),
    
    ("contact", "Formpack",
     "Customer: Formpack/PlastIndia (India) - AM-P-1206, Status: Final Assembly, Awaiting programming, Deadline: Dec 15, 2025", "context"),
    ("contact", "Formpack",
     "Formpack AM-P-1206 needs: Mould, sheets for commissioning", "context"),
    
    ("contact", "Formpack",
     "Customer: Formpack (India) - PF1-A-3020, Status: Fabrication, project 25004", "context"),
    
    ("contact", "Alphafoam",
     "Customer: Alphafoam (India) - PF1-A-2015 and PF1-X-2015, Status: Fabrication, projects 23025/23026", "context"),
    
    # ==========================================================================
    # IN DESIGN & ORDERING PHASE
    # ==========================================================================
    ("contact", "Formpack",
     "Customer: Formpack/PlastIndia (India) - NGF0912, Status: Design + Ordering, Deadline: Jan 15, 2026", "context"),
    ("contact", "Formpack",
     "NGF0912 next steps: Hydraulic system ordering, PTFE coating, electrical panel assembly", "context"),
    
    ("contact", "Nagoya Jushi",
     "Customer: Nagoya Jushi (Japan) - PF1-X-1325-U, Status: Design + Ordering, Deadline: Feb 15, 2026", "context"),
    ("contact", "Nagoya Jushi",
     "Nagoya Jushi order 25020: PF1-X 1300x2500mm with universal frames for Japan market", "context"),
    ("contact", "Nagoya Jushi",
     "Nagoya Jushi next steps: 3D CAD, electrical drawing, BOM, ordering gearbox/servos", "context"),
    
    ("contact", "MP3",
     "Customer: MP3 (Italy) - PF1-X-0707-U, Status: Design + Ordering, Deadline: Mar 15, 2026", "context"),
    ("contact", "MP3",
     "MP3 order 24021: Compact PF1-X 700x700mm with universal frames for Italy", "context"),
    ("contact", "MP3",
     "MP3 next steps: 3D CAD, electrical drawing, BOM, ordering gearbox/servos", "context"),
    
    ("contact", "Formpack",
     "Customer: Formpack (India) - FCS XL, Status: Design + Ordering, Deadline: Apr 15, 2026", "context"),
    ("contact", "Formpack",
     "FCS XL order 22032: Extra-large Form-Cut-Stack machine for Formpack", "context"),
    
    ("contact", "KTX",
     "Customer: KTX (Japan) - IMG Press, Status: Design + Ordering, Deadline: May 15, 2026", "context"),
    ("contact", "KTX",
     "KTX order 23011: IMG (In-Mold Graining) press for Japanese automotive market", "context"),
    ("contact", "KTX",
     "KTX next steps: 3D CAD, electrical drawing, BOM, ordering gearbox/servos", "context"),
    
    # ==========================================================================
    # CUSTOMER RELATIONSHIP SUMMARY
    # ==========================================================================
    ("contact", "Formpack",
     "Formpack relationship: Major repeat customer, 4 active orders (AM-P-1206, NGF0912, FCS XL, PF1-A-3020)", "context"),
    ("contact", "Alphafoam",
     "Alphafoam relationship: 2 machines in fabrication (PF1-A-2015, PF1-X-2015)", "context"),
    ("contact", "Venkateshwar",
     "Venkateshwar relationship: 2 machines complete (PF1-C-3020, RT-4A 3020), ready for wet trial", "context"),
    
    # ==========================================================================
    # INTERNATIONAL ORDERS SUMMARY
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "International orders Nov 2025: DutchTides (NL), Nagoya Jushi (JP), MP3 (IT), KTX (JP), RIDAT (UK)", "fact"),
    ("company", "Machinecraft Technologies",
     "Japan market: 2 orders - Nagoya Jushi (PF1-X-1325), KTX (IMG Press) - high-value exports", "fact"),
    ("company", "Machinecraft Technologies",
     "Europe market: DutchTides (Netherlands), MP3 (Italy), RIDAT (UK) - PF1-X machines", "fact"),
    
    # ==========================================================================
    # MACHINE TYPE BREAKDOWN
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Order book machines: PF1-X (6 units), PF1-C (1), PF1-A (2), AM (3), FCS (1), IMG (1), RT (1), ATF (1)", "fact"),
    ("company", "Machinecraft Technologies",
     "Most ordered: PF1-X Series dominates with 6 units in various sizes (0707 to 6419)", "fact"),
]

def store_memories():
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING ORDER BOOK (NOV 2025)")
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

    print(f"\n✅ Stored {count} order book items")
    print("\n" + "="*70)
    print("ORDER BOOK SUMMARY (Nov 2025)")
    print("="*70)
    print("""
ORDERS BY STATUS:
┌──────────────────────┬────────────────────────────────────────────────────┐
│ Status               │ Orders                                             │
├──────────────────────┼────────────────────────────────────────────────────┤
│ Packing/Shipping     │ DutchTides (NL) - PF1-X-6419                       │
│ Complete (Wet Trial) │ Venkateshwar (IN) - PF1-C-3020, RT-4A              │
│ Complete (Payment)   │ Priti, Convertex (IN) - AM 6050                    │
│ Complete (Approval)  │ RIDAT (UK) - ATF RAFTER                            │
│ Fabrication          │ Pinnacle, Formpack, Alphafoam (IN)                 │
│ Final Assembly       │ Formpack (IN) - AM-P-1206                          │
│ Design + Ordering    │ Nagoya Jushi (JP), MP3 (IT), KTX (JP), Formpack    │
└──────────────────────┴────────────────────────────────────────────────────┘

INTERNATIONAL CUSTOMERS:
  • Netherlands: DutchTides - PF1-X-6419 (shipping Nov 15)
  • Japan: Nagoya Jushi (PF1-X), KTX (IMG Press)
  • Italy: MP3 - PF1-X-0707-U
  • UK: RIDAT - ATF RAFTER

TOP DOMESTIC CUSTOMERS:
  • Formpack/PlastIndia - 4 active orders
  • Alphafoam - 2 machines
  • Venkateshwar - 2 machines complete
""")
    return count

if __name__ == "__main__":
    store_memories()
