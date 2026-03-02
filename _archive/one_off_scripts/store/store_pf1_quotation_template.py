#!/usr/bin/env python3
"""
Store PF1 Series quotation template knowledge in Ira's memory.
Extracted from: PF1-C-1515 _ Machinecraft PF1 Quotation.pdf

This is the template format for generating high-value project quotes.
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
# PF1 QUOTATION TEMPLATE KNOWLEDGE
# ============================================================================

ENTITY_MEMORIES = [
    # ==========================================================================
    # PF1 SERIES OVERVIEW FOR QUOTES
    # ==========================================================================
    ("product", "PF1 Series",
     "PF1 is heavy-gauge, single-station cut-sheet thermoforming machine line - custom-built to client requirements", "fact"),
    ("product", "PF1 Series",
     "PF1 sizes range from ~800×1000mm up to extra-large 5000×2500mm formats", "fact"),
    ("product", "PF1 Series",
     "PF1 closed-chamber design prevents sheet sag via pre-blow air pressure control (zero-sag)", "fact"),
    ("product", "PF1 Series",
     "PF1 handles sheet thickness typically 2-12mm, ideal for automotive, aerospace, industrial applications", "fact"),
    
    # ==========================================================================
    # QUOTATION INPUT PARAMETERS (What to ask customer)
    # ==========================================================================
    ("product", "PF1 Quotation",
     "Required inputs: Forming Area (LxD mm), Max Stroke Z, Sheet Thickness Range, Materials to form", "fact"),
    ("product", "PF1 Quotation",
     "Required inputs: Clamp Frame type (fixed vs quick-change), Sheet Loading (manual vs auto)", "fact"),
    ("product", "PF1 Quotation",
     "Required inputs: Heating config (single top heater vs double sandwich heater), Platen drive (pneumatic vs servo)", "fact"),
    ("product", "PF1 Quotation",
     "Single heater: max 4mm sheet, Double heater: up to 10mm sheet thickness", "fact"),
    
    # ==========================================================================
    # STANDARD SPECIFICATIONS
    # ==========================================================================
    ("product", "PF1 Series",
     "Materials suited: PS, ABS, ASA, ABS-PMMA, PC, PP, PE-HD, TPO", "fact"),
    ("product", "PF1 Series",
     "Vacuum pump capacity ~60 m³/hr, Compressed air requirement ~6 bar (100 psi)", "fact"),
    ("product", "PF1 Series",
     "Control: PLC controller with 7\" color touchscreen HMI, recipe storage, zone control, diagnostics", "fact"),
    ("product", "PF1 Series",
     "Components: PLC/HMI/Servos=Mitsubishi Japan, Pneumatics=Janatics, Vacuum=Zen Air, Fans=EBM Papst", "fact"),
    
    # ==========================================================================
    # CLASSIC/BASE CONFIGURATION
    # ==========================================================================
    ("product", "PF1 Classic Config",
     "Classic config: sandwich IR ceramic heaters, pneumatic platen, manual sheet loading, fixed clamp frames", "fact"),
    ("product", "PF1 Classic Config",
     "Classic config includes: single-stage vacuum system, centrifugal fans, basic PLC+HMI control", "fact"),
    
    # ==========================================================================
    # HEATING SYSTEM DETAILS
    # ==========================================================================
    ("product", "PF1 Heating System",
     "Heating: IR ceramic elements with SSR and digital PID control via HMI, zone-by-zone control", "fact"),
    ("product", "PF1 Heating System",
     "Heater power example (1515): ~48kW single heater, ~86-96kW double heater", "fact"),
    ("product", "PF1 Heating System",
     "Optional: Pyrometer in center of top heater oven for precise temperature measurement", "fact"),
    
    # ==========================================================================
    # CLAMP FRAME SYSTEM
    # ==========================================================================
    ("product", "PF1 Clamp Frames",
     "Standard: Fixed welded frames - need to change each time sheet size changes (60-120 min changeover)", "fact"),
    ("product", "PF1 Clamp Frames",
     "Machine supplied with 1x frame at max aperture, additional frames can be ordered at extra cost", "fact"),
    ("product", "PF1 Clamp Frames",
     "Ask customer: What are your possible sheet sizes? We can quote frames for each size", "fact"),
    
    # ==========================================================================
    # ZERO-SAG / PREBLOW SYSTEM
    # ==========================================================================
    ("product", "PF1 Zero-Sag",
     "Zero-sag: Closed chamber below sheet line, pulsated air maintains sheet level during heating", "fact"),
    ("product", "PF1 Zero-Sag",
     "Light sensor below sheet prevents sagging onto bottom heater, preblow photocell above sheet", "fact"),
    ("product", "PF1 Zero-Sag",
     "Preblow bubble for male tools achieves even wall thickness in final part", "fact"),
    
    # ==========================================================================
    # PLATEN DRIVE OPTIONS
    # ==========================================================================
    ("product", "PF1 Platen Drive",
     "Standard: Pneumatic platen with 4x cylinders and rack & pinion - fixed speed", "fact"),
    ("product", "PF1 Platen Drive",
     "Upgrade option: Servo-motor driven platen allows acceleration/deceleration profile control", "fact"),
    
    # ==========================================================================
    # PRICING EXAMPLE (PF1-C-1515)
    # ==========================================================================
    ("product", "PF1-C-1515",
     "PF1-C-1515 (1500x1500mm): ₹34.5L single heater, ₹46.5L double heater, ex-works Umargam", "fact"),
    ("product", "PF1-C-1515",
     "PF1-C-1515 specs: 400mm Z stroke, 2-10mm sheet, ~55kW single/~95kW double connected load", "fact"),
    
    # ==========================================================================
    # COMMERCIAL TERMS FOR QUOTES
    # ==========================================================================
    ("product", "PF1 Quotation",
     "Lead time: ~3.5-4 months from advance payment (confirm based on options and production schedule)", "fact"),
    ("product", "PF1 Quotation",
     "Delivery terms: Ex-works Umargam, Gujarat. Packing/freight/insurance/installation extra", "fact"),
    ("product", "PF1 Quotation",
     "Payment terms: 50% advance with PO, 50% against FAT approval before dispatch", "fact"),
    ("product", "PF1 Quotation",
     "Quote validity: 8 days from issue date, prices subject to change thereafter", "fact"),
    ("product", "PF1 Quotation",
     "Warranty: 1-year limited warranty from commissioning, covers mfg defects, excludes consumables/wear parts", "fact"),
    ("product", "PF1 Quotation",
     "Installation: On-site commissioning + operator training included, travel/lodging for technician extra", "fact"),
    ("product", "PF1 Quotation",
     "After-sales: Remote VPN support (with IoT module), on-site visits if remote can't resolve", "fact"),
    
    # ==========================================================================
    # QUOTE GENERATION CHECKLIST
    # ==========================================================================
    ("product", "PF1 Quotation",
     "Quote checklist: 1) Forming area LxD, 2) Max depth/stroke, 3) Sheet thickness range, 4) Materials", "fact"),
    ("product", "PF1 Quotation",
     "Quote checklist: 5) Single/double heater, 6) Pneumatic/servo platen, 7) Manual/auto loading", "fact"),
    ("product", "PF1 Quotation",
     "Quote checklist: 8) Frame sizes needed, 9) Any special options (pyrometer, IoT, etc.)", "fact"),
]


def store_memories():
    """Store PF1 quotation template knowledge."""
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING PF1 QUOTATION TEMPLATE KNOWLEDGE")
    print("=" * 70)
    
    print(f"\n📋 Storing {len(ENTITY_MEMORIES)} quotation template items...")
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
    print(f"COMPLETE: Stored {entity_count} quotation template items")
    print("=" * 70)
    print("\nIra now knows how to build PF1 quotes:")
    print("  • Required customer inputs (forming area, thickness, materials)")
    print("  • Configuration options (heater, platen, loading, frames)")
    print("  • Technical specifications (vacuum, control, components)")
    print("  • Zero-sag/preblow system details")
    print("  • Commercial terms (payment, delivery, warranty, validity)")
    print("  • Quote generation checklist")
    
    return entity_count


if __name__ == "__main__":
    store_memories()
