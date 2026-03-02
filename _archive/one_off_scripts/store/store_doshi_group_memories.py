#!/usr/bin/env python3
"""
Store comprehensive memories about the Doshi Family Group companies in Ira's memory system.
Extracted from: Machinecraft Co Doc.pdf
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

# Rushabh's identity ID
RUSHABH_IDENTITY_ID = "id_db1a9b47e00d"

# ============================================================================
# DOSHI FAMILY GROUP - COMPANY MEMORIES
# ============================================================================

ENTITY_MEMORIES = [
    # ==========================================================================
    # DOSHI FAMILY GROUP (Umbrella)
    # ==========================================================================
    ("company", "Doshi Family Group", 
     "The parent group of Machinecraft, Formpack, and Indu Advanced Polymers - diversified businesses in plastics and manufacturing", "fact"),
    ("company", "Doshi Family Group", 
     "Three-generation family business started by B.P. Doshi in 1976, now run by second and third generations", "fact"),
    ("company", "Doshi Family Group", 
     "Ecosystem: Machinecraft designs machines, Formpack manufactures products, IAP provides materials - vertical integration", "fact"),
    
    # ==========================================================================
    # MACHINECRAFT TECHNOLOGIES (Flagship)
    # ==========================================================================
    ("company", "Machinecraft Technologies", 
     "India's leading manufacturer of automatic thermoforming machines, founded 1976 by B.P. Doshi - the group's flagship company", "fact"),
    ("company", "Machinecraft Technologies", 
     "Over 2,500 machine installations across 35+ countries worldwide", "fact"),
    ("company", "Machinecraft Technologies", 
     "Products: Custom thermal vacuum forming machines, CNC trimming routers, plastic sheet extrusion lines, and auxiliary systems", "fact"),
    ("company", "Machinecraft Technologies", 
     "Serves automotive OEMs, appliances (refrigerator liners), sanitaryware, food packaging, and healthcare industries", "fact"),
    ("company", "Machinecraft Technologies", 
     "Turnkey solutions provider: machinery, tooling, prototyping, and plastic sheet supply", "fact"),
    ("company", "Machinecraft Technologies", 
     "New manufacturing plant in Umargam, Gujarat (150km north of Mumbai) opened in 2020", "fact"),
    ("company", "Machinecraft Technologies", 
     "Key milestone: First fully automatic vacuum forming machine sold in Europe via K Show 1998 in Germany", "fact"),
    ("company", "Machinecraft Technologies", 
     "COVID contribution: Developed vaccine refrigerator liners in under 8 weeks, supplied cold storage boxes to 24 countries", "fact"),
    ("company", "Machinecraft Technologies", 
     "Founder B.P. Doshi was a polymer chemist trained at UDCT Mumbai - built India's first vacuum forming machine", "fact"),
    
    # ==========================================================================
    # FORMPACK
    # ==========================================================================
    ("company", "Formpack", 
     "Manufacturing arm of Doshi Group producing thermoformed plastic components and assemblies, founded 2019", "fact"),
    ("company", "Formpack", 
     "Located in Umbergaon, Gujarat (adjacent to Machinecraft plant)", "fact"),
    ("company", "Formpack", 
     "Products: Automotive parts (tractor canopies, interior panels, HVAC covers), windmill components, medical device housings, packaging trays", "fact"),
    ("company", "Formpack", 
     "In-house processes: Heavy-gauge thermoforming, CNC trimming, plastic welding/joining, thermoplastic sheet extrusion", "fact"),
    ("company", "Formpack", 
     "Preferred Tier-2 supplier to automotive and industrial clients, also development partner for custom polymer parts", "fact"),
    ("company", "Formpack", 
     "COVID achievement: Rapidly developed vaccine refrigerator liners/cold storage boxes for pandemic response", "fact"),
    
    # ==========================================================================
    # INDU ADVANCED POLYMERS (IAP)
    # ==========================================================================
    ("company", "Indu Advanced Polymers", 
     "Materials and sheet extrusion division of Doshi Group, also known as Indu Thermoformers Pvt. Ltd.", "fact"),
    ("company", "Indu Advanced Polymers", 
     "Produces high-quality plastic sheets (ABS, ASA, HDPE, PS) as raw material for thermoforming", "fact"),
    ("company", "Indu Advanced Polymers", 
     "Capabilities: Thin-gauge films for packaging to thick-gauge plates for industrial applications", "fact"),
    ("company", "Indu Advanced Polymers", 
     "Special formulations: UV resistance, flame retardancy, multi-layer composites", "fact"),
    ("company", "Indu Advanced Polymers", 
     "Supplies Formpack's operations with custom sheets and serves external customers", "fact"),
    ("company", "Indu Advanced Polymers", 
     "Brings polymer science expertise to group - advising on material selection, recycling, new polymer development", "fact"),
    
    # ==========================================================================
    # PARTNERSHIPS
    # ==========================================================================
    ("company", "FRIMO", 
     "German partner of Machinecraft since 2019 - leader in automotive polymer technologies", "fact"),
    ("company", "FRIMO", 
     "Partnership brings 'Thermoforming++' processes to India: vacuum lamination, in-mold graining (IMG), long-fiber injection (LFI)", "fact"),
    
    ("company", "FVF", 
     "Japanese partner of Machinecraft - specializes in decorating and surface finishing technologies for plastic parts", "fact"),
    
    # ==========================================================================
    # KEY PEOPLE IN THE BUSINESS
    # ==========================================================================
    ("contact", "B.P. Doshi", 
     "Founder of Machinecraft (1976), polymer chemist trained at UDCT Mumbai, built India's first vacuum forming machine", "fact"),
    ("contact", "B.P. Doshi", 
     "Rushabh's grandfather - started the Doshi Family Group legacy in plastics manufacturing", "fact"),
    
    ("contact", "Deepak Doshi", 
     "Second generation leader at Machinecraft, joined around 1990, son of founder B.P. Doshi", "fact"),
    ("contact", "Deepak Doshi", 
     "Rushabh's father - stern patriarch who built up Machinecraft into a global business", "fact"),
    
    ("contact", "Rajesh Doshi", 
     "Second generation at Machinecraft, joined around 1990, son of founder B.P. Doshi", "fact"),
    ("contact", "Rajesh Doshi", 
     "Rushabh's uncle - mentors third generation in operations", "fact"),
]


def store_memories():
    """Store all Doshi Family Group company memories."""
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 60)
    print("STORING DOSHI FAMILY GROUP COMPANY DATA")
    print("=" * 60)
    
    # Store entity memories
    print(f"\n🏢 Storing {len(ENTITY_MEMORIES)} entity memories...")
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
            print(f"  ✓ [{entity_type}:{entity_name}] {memory_text[:50]}...")
        else:
            print(f"  ⊘ (duplicate) {memory_text[:40]}...")
    
    print("\n" + "=" * 60)
    print(f"COMPLETE: Stored {entity_count} entity memories about Doshi Family Group")
    print("=" * 60)
    
    return entity_count


if __name__ == "__main__":
    store_memories()
