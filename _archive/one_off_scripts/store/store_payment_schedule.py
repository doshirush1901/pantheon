#!/usr/bin/env python3
"""
Store Machinecraft Payment Schedule in Ira's memory.

Source: Machinecraft machine payment schedule.pdf (Updated: Feb 26, 2026)

This data helps Ira:
1. Follow up with clients on pending payments
2. Track payment milestones per order
3. Prioritize collection calls
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
    # PAYMENT SCHEDULE OVERVIEW
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Payment schedule (Feb 2026): 12 active orders, ₹12.5Cr total pending receivables", "fact"),
    ("company", "Machinecraft Technologies",
     "Payment tracking: CW9-CW21 (Feb-May 2026), weekly collection targets set", "fact"),
    
    # ==========================================================================
    # ORDER 1: KTX IMG Press (Japan)
    # ==========================================================================
    ("contact", "KTX",
     "Order 23011: KTX IMG Press, ¥3.99Cr (~₹2.34Cr), Advance: ₹68.5L, Pending: ₹1.66Cr", "context"),
    ("contact", "KTX",
     "KTX payment status: Japan customer, IMG technology machine, significant pending balance", "context"),
    
    # ==========================================================================
    # ORDER 2: NCC PF1-A-2015 (USA)
    # ==========================================================================
    ("contact", "NCC",
     "Order 23025: NCC PF1-A-2015-06, $70,000, NO advance received, Full ₹63.6L due CW10 (Mar 2-8)", "context"),
    ("contact", "NCC",
     "NCC payment URGENT: Zero advance, full payment of ₹63.6L needed by Mar 8, 2026", "context"),
    
    # ==========================================================================
    # ORDER 3: RIDAT ATF RAFTER (UK)
    # ==========================================================================
    ("contact", "RIDAT",
     "Order 24013: RIDAT ATF RAFTER, £1.41L (~₹1.74Cr), NO advance, Full due CW10 (Mar 2-8)", "context"),
    ("contact", "RIDAT",
     "RIDAT payment URGENT: UK customer, zero advance, ₹1.74Cr full payment due Mar 8, 2026", "context"),
    
    # ==========================================================================
    # ORDER 4: MP3 PF1-X-0707 (Italy)
    # ==========================================================================
    ("contact", "MP3",
     "Order 24021: MP3 PF1-X-0707, €70,000, Advance: ₹22.2L, Pending: ₹52.9L due CW10", "context"),
    ("contact", "MP3",
     "MP3 payment: Italy customer, PF1-X export machine, ₹52.9L due by Mar 8, 2026", "context"),
    
    # ==========================================================================
    # ORDER 5: Pinnacle PF1-X-5028 (India)
    # ==========================================================================
    ("contact", "Pinnacle",
     "Order 25002: Pinnacle PF1-X-5028, ₹3.94Cr, Advance: ₹1.82Cr (46%), Pending: ₹2.83Cr", "context"),
    ("contact", "Pinnacle",
     "Pinnacle payment split: ₹2.44Cr due CW10 (Mar), ₹39.4L due CW14 (Apr 6-12)", "context"),
    ("contact", "Pinnacle",
     "Pinnacle: Largest domestic order, PF1-X-5028 (biggest size), good advance already paid", "context"),
    
    # ==========================================================================
    # ORDER 6: NCC PF1-A-3020 (USA)
    # ==========================================================================
    ("contact", "NCC",
     "Order 25005: NCC PF1-A-3020-08, $86,000, NO advance, Full ₹78.2L due CW11 (Mar 9-15)", "context"),
    ("contact", "NCC",
     "NCC second order: Larger machine, zero advance, ₹78.2L due mid-March 2026", "context"),
    
    # ==========================================================================
    # ORDER 7: Venkateshwar PF1-C-3020 (India)
    # ==========================================================================
    ("contact", "Venkateshwar",
     "Order 25006: Venkateshwar PF1-C-3020, ₹85L, Advance: ₹83.5L (98%!), Only ₹16.8L pending", "context"),
    ("contact", "Venkateshwar",
     "Venkateshwar PF1-C: Almost fully paid, ₹16.8L balance due CW13 (Mar 23-29)", "context"),
    
    # ==========================================================================
    # ORDER 8: Venkateshwar RT-4A 3020 (India)
    # ==========================================================================
    ("contact", "Venkateshwar",
     "Order 25007: Venkateshwar RT-4A 3020, ₹32L, NO advance, Full ₹37.8L due CW13", "context"),
    ("contact", "Venkateshwar",
     "Venkateshwar RT-4A: Second machine, zero advance - needs collection focus Mar 23-29", "context"),
    
    # ==========================================================================
    # ORDER 9: Nagoya Jushi PF1-X-1325 (Japan)
    # ==========================================================================
    ("contact", "Nagoya Jushi",
     "Order 25020: Nagoya Jushi PF1-X-1325, ¥4.4Cr, Advance: ₹78.3L, Pending: ₹1.8Cr due CW10", "context"),
    ("contact", "Nagoya Jushi",
     "Nagoya Jushi: Japan export customer, PF1-X series, ₹1.8Cr due by Mar 8, 2026", "context"),
    
    # ==========================================================================
    # ORDER 10: Mirek AM 6050 (India)
    # ==========================================================================
    ("contact", "Mirek",
     "Order 25023: Mirek AM 6050, ₹7.6L, Advance: ₹3.8L (50%), Pending: ₹5.17L due CW12", "context"),
    ("contact", "Mirek",
     "Mirek: Small AM machine order, half paid, ₹5.17L balance due Mar 16-22", "context"),
    
    # ==========================================================================
    # ORDER 11: Arrdev PF2-2424 (India)
    # ==========================================================================
    ("contact", "Arrdev",
     "Order 26001: Arrdev PF2-2424, ₹54L, Advance: ₹17.5L (32%), Pending: ₹46.2L due CW17", "context"),
    ("contact", "Arrdev",
     "Arrdev: PF2 twin-station machine, ₹46.2L due Apr 20-26, 2026", "context"),
    
    # ==========================================================================
    # ORDER 12: NRC Canada PF1-X-0707 (Canada)
    # ==========================================================================
    ("contact", "NRC Canada",
     "Order 26002: NRC Canada PF1-X-0707, $161,020, NO advance, Total ₹1.46Cr pending", "context"),
    ("contact", "NRC Canada",
     "NRC Canada payment split: ₹44.6L CW10, ₹89.3L CW15, ₹12.5L CW21 - staged payments", "context"),
    ("contact", "NRC Canada",
     "NRC Canada: New export customer, PF1-X series, needs payment tracking across 3 milestones", "context"),
    
    # ==========================================================================
    # WEEKLY COLLECTION TARGETS
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "CW10 (Mar 2-8) CRITICAL: ₹2.96Cr due - NCC, RIDAT, MP3, Pinnacle, Nagoya Jushi, NRC Canada", "context"),
    ("company", "Machinecraft Technologies",
     "CW11 (Mar 9-15): ₹54.6L due - NCC PF1-A-3020 full payment", "context"),
    ("company", "Machinecraft Technologies",
     "CW13 (Mar 23-29): ₹54.6L due - Venkateshwar both orders (PF1-C + RT-4A)", "context"),
    ("company", "Machinecraft Technologies",
     "CW14 (Apr 6-12): ₹39.4L due - Pinnacle second installment", "context"),
    ("company", "Machinecraft Technologies",
     "CW15 (Apr 13-19): ₹1.42Cr due - NRC Canada major installment", "context"),
    ("company", "Machinecraft Technologies",
     "CW17 (Apr 20-26): ₹46.2L due - Arrdev PF2-2424", "context"),
    ("company", "Machinecraft Technologies",
     "CW18 (Apr 27-May 3): ₹3.54Cr due - KTX IMG Press balance (largest single payment)", "context"),
    ("company", "Machinecraft Technologies",
     "CW21 (May 18-24): ₹89.3L due - NRC Canada final installment", "context"),
    
    # ==========================================================================
    # COLLECTION PRIORITIES
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "URGENT: NCC (2 orders), RIDAT - zero advance received, full amounts due Mar 2026", "context"),
    ("company", "Machinecraft Technologies",
     "Good standing: Venkateshwar (98% paid), Pinnacle (46% paid), Mirek (50% paid)", "context"),
    ("company", "Machinecraft Technologies",
     "Export collections: KTX (Japan), Nagoya Jushi (Japan), MP3 (Italy), RIDAT (UK), NRC (Canada)", "context"),
]

def store_memories():
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING PAYMENT SCHEDULE (FEB 2026)")
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

    print(f"\n✅ Stored {count} payment schedule items")
    print("\n" + "="*70)
    print("PAYMENT SCHEDULE SUMMARY (Feb-May 2026)")
    print("="*70)
    print("""
TOTAL PENDING RECEIVABLES: ₹12.5 Crores

PRIORITY COLLECTIONS (URGENT - No Advance):
  ⚠️  NCC (Order 23025):     ₹63.6L due CW10 (Mar 2-8)
  ⚠️  RIDAT:                 ₹1.74Cr due CW10 (Mar 2-8)  
  ⚠️  NCC (Order 25005):     ₹78.2L due CW11 (Mar 9-15)
  ⚠️  Venkateshwar RT-4A:    ₹37.8L due CW13 (Mar 23-29)
  ⚠️  NRC Canada:            ₹1.46Cr staged (CW10/15/21)

GOOD STANDING (Advance Paid):
  ✓ Venkateshwar PF1-C:     98% paid, only ₹16.8L left
  ✓ Pinnacle:               46% paid, ₹2.83Cr pending
  ✓ Mirek:                  50% paid, only ₹5.17L left

WEEKLY TARGETS:
  CW10 (Mar 2-8):    ₹2.96Cr  ← CRITICAL WEEK
  CW11 (Mar 9-15):   ₹54.6L
  CW13 (Mar 23-29):  ₹54.6L  
  CW14 (Apr 6-12):   ₹39.4L
  CW15 (Apr 13-19):  ₹1.42Cr
  CW17 (Apr 20-26):  ₹46.2L
  CW18 (Apr 27-May): ₹3.54Cr ← KTX large payment
  CW21 (May 18-24):  ₹89.3L
""")
    return count

if __name__ == "__main__":
    store_memories()
