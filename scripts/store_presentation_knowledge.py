#!/usr/bin/env python3
"""
Store Machinecraft sales presentation knowledge in Ira's memory.
Extracted from: Machinecraft Presentation - Aug 2024.pdf

This represents how Rushabh presents the company to prospects.
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
# PRESENTATION KNOWLEDGE - HOW RUSHABH PRESENTS MACHINECRAFT
# ============================================================================

ENTITY_MEMORIES = [
    # ==========================================================================
    # COMPANY INTRO PITCH
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Pitch: 'Machinecraft designs & manufactures thermoforming machines & tooling for industrial applications'", "fact"),
    ("company", "Machinecraft Technologies",
     "Key stats for presentations: >20 machines/year, 50 employees, 40 years in existence, 3rd generation family-run", "fact"),
    ("company", "Machinecraft Technologies",
     "Sales reach: 45+ countries including India, GCC, Europe, Canada, Russia, Japan", "fact"),
    
    # ==========================================================================
    # GENERATIONAL HISTORY STRUCTURE
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Company history timeline: 1st Gen (1980-1998), 2nd Gen (1998-2018), 3rd Gen (2019 onwards)", "fact"),
    
    # ==========================================================================
    # LOCATION DETAILS
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Location: Office in Mumbai City, Manufacturing plant in Umargam (100 miles from Mumbai, 1km from Arabian Sea)", "fact"),
    ("company", "Machinecraft Technologies",
     "Manufacturing facility: 12,000 sqm greenfield site established 2019", "fact"),
    
    # ==========================================================================
    # VALUE PROPOSITION - ALL-IN-ONE SOLUTION
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Unique selling point: ALL-IN-ONE SOLUTION - Machinery, Proto-Runs, Tooling & Sheets all from one source", "fact"),
    ("company", "Machinecraft Technologies",
     "Turnkey offering covers: Raw Material supply → Proto Series Run → Tooling → Machinery", "fact"),
    
    # ==========================================================================
    # SHOWCASE PROJECTS FOR SALES
    # ==========================================================================
    ("product", "Bathtub Machine",
     "Specs: Max 2100x1600mm, depth 860mm, zero sag, universal frames, auto loading/unloading, fully servo driven", "fact"),
    ("product", "Spa Machine",
     "Specs: Max 3000x3000mm, depth 1200mm, zero sag, universal frames, auto loading/unloading, fully servo driven", "fact"),
    ("product", "Large Signage Machine",
     "Biggest project: 4.8x2.5m forming area, 500mm depth, CSA certified, quick tool change, for large scale signages", "fact"),
    ("product", "Tractor Parts Machine",
     "Specs: 4200x2500mm, depth 650mm, zero sag, auto loading, servo driven, central cooling - for tractor components", "fact"),
    ("product", "Bedliner Machine",
     "Specs: 3500x2500mm, depth 1050mm, sag allowed for HDPE, bottom heater moves with sag, for pickup truck bedliners", "fact"),
    
    # ==========================================================================
    # TOOLING CAPABILITY
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Tooling production: 200 tools produced in 2023, GRP & Aluminium tools, Lanulfi Italy partnership (2024)", "fact"),
    
    # ==========================================================================
    # CNC CAPABILITIES
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "CNC machines: BFW (1500x650mm), Haas (1372x610mm), Jyoti-Huron (820x510mm), Large Jyoti-Huron (3500x2000mm)", "fact"),
    ("company", "Machinecraft Technologies",
     "CNC precision: Position accuracy 0.02mm, repeatability 0.008-0.018mm, spindle speeds 6000-10000 rpm", "fact"),
    
    # ==========================================================================
    # NEW DEVELOPMENTS
    # ==========================================================================
    ("product", "TOM Machine",
     "New development: 3-Dimensional Overlay Double Chamber Machine for laminating PC films over ceramic", "fact"),
    ("product", "TOM Machine",
     "TOM application: Add metallic/wooden finish waterproof on ceramic surfaces", "fact"),
    
    # ==========================================================================
    # CONTACT INFO FOR SALES
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Sales contact: Rushabh Doshi, rushabh@machinecraft.org, +91 9833112903, www.machinecraft.org", "fact"),
    
    # ==========================================================================
    # KEY MACHINE FEATURES TO HIGHLIGHT IN SALES
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Standard features to highlight: Zero Sag, Universal Frames, Auto Loading/Unloading, Fully Servo Driven", "fact"),
    ("company", "Machinecraft Technologies",
     "Quick Tool Change System available on larger machines - highlight for high-mix production customers", "fact"),
]


def store_memories():
    """Store presentation knowledge."""
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING MACHINECRAFT PRESENTATION/SALES PITCH KNOWLEDGE")
    print("=" * 70)
    
    print(f"\n📊 Storing {len(ENTITY_MEMORIES)} presentation items...")
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
    print(f"COMPLETE: Stored {entity_count} presentation knowledge items")
    print("=" * 70)
    print("\nIra now knows how Rushabh presents Machinecraft:")
    print("  • Company intro pitch and key stats")
    print("  • Generational history structure")
    print("  • ALL-IN-ONE solution value proposition")
    print("  • Showcase projects (bathtubs, spas, signage, tractors, bedliners)")
    print("  • Tooling and CNC capabilities")
    print("  • New TOM machine developments")
    print("  • Key features to highlight in sales")
    
    return entity_count


if __name__ == "__main__":
    store_memories()
