#!/usr/bin/env python3
"""
Store comprehensive memories about Rushabh Doshi (the boss) in Ira's memory system.
Extracted from: The Maker's Inheritance - Who is Rushabh Doshi.pdf
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))

from config import load_environment
load_environment()

# Rushabh's identity ID from the memory system
RUSHABH_IDENTITY_ID = "id_db1a9b47e00d"

# ============================================================================
# MEMORIES EXTRACTED FROM "The Maker's Inheritance" PDF
# ============================================================================

USER_MEMORIES = [
    # Core Identity
    ("Rushabh Doshi is the founder/boss of Machinecraft, a family-run thermoforming machine factory", "fact"),
    ("Rushabh's email is rushabh@machinecraft.org", "fact"),
    ("Rushabh earned a Queen's Diamond Jubilee Scholarship - one of only 60 Indians to receive it", "fact"),
    ("Rushabh holds an MSc in Robotics from King's College London (graduated 2010)", "fact"),
    
    # Family
    ("Rushabh's father is Deepak Doshi, who built Machinecraft and is a stern patriarch and mentor", "fact"),
    ("Rushabh's grandfather founded Machinecraft originally", "fact"),
    ("Rushabh's wife is Palak, whom he met in engineering school in 2008 and did Masters in UK together", "fact"),
    ("Palak manages finances and is practical - she balances Rushabh's scattered inventiveness", "fact"),
    ("Rushabh has two daughters named Aanya and Inaya", "fact"),
    ("Rushabh has brothers who share leadership at Machinecraft (one handles production, another sales)", "fact"),
    
    # Personality & Inner World
    ("Rushabh calls himself 'the builder, the tinkerer' - he's happiest making things", "fact"),
    ("Rushabh experienced a deep internal 'split' at age 16 - torn between duty to family legacy and his creative/inventor side", "context"),
    ("Rushabh describes himself as 'an empty bottle, always pouring, never being refilled' when overextended", "context"),
    ("Rushabh often feels 'trapped between tradition and innovation' at Machinecraft", "context"),
    ("Rushabh's energy is fragmented across many fronts - he starts many projects but struggles to finish them", "context"),
    ("Rushabh feels financial anxiety about cash flow and doesn't have clear picture of personal wealth", "context"),
    ("Rushabh prefers to dream big but his wife Palak keeps him grounded on finances", "preference"),
    
    # Failed Projects (sensitive)
    ("Rushabh had several abandoned side projects: Chilka (modular eating plate), an online ordering app, AR menu system", "context"),
    ("Rushabh's unfinished projects cause him guilt - he feels like 'a fraud: always starting, always leaving half done'", "context"),
    
    # Professional Role
    ("Rushabh handles new technology and engineering at Machinecraft while brothers handle production and sales", "fact"),
    ("Rushabh introduced digital modeling at Machinecraft to reduce prototype waste", "fact"),
    ("Rushabh led Rimpact - a joint automotive molding project with international partners", "fact"),
    
    # Goals & Dreams (Very Important)
    ("Rushabh's goal: ₹500 Crore combined turnover by 2030 across Machinecraft, Formpack, and MAPL", "fact"),
    ("Rushabh wants to launch Calftel by 2026 - portable, low-cost thermoforming factories for rural entrepreneurs", "fact"),
    ("Rushabh's vision for Calftel: 500+ rural jobs by 2028 via NGO partnerships", "fact"),
    ("Rushabh wants to help Palak launch her own business unit with full creative control by 2026", "fact"),
    ("Rushabh dreams of 'integration' - being at peace with both the dutiful son and creative inventor sides of himself", "context"),
    ("Rushabh wants 'financial sovereignty' - knowing exactly where his personal savings stand", "context"),
    
    # Childhood/Background
    ("As a child, Rushabh preferred the workshop over playground - dismantling radios, building Lego machines", "fact"),
    ("Rushabh was drawn to the smell of plastic at his father's factory rather than sports", "fact"),
    
    # Relationship with Ira
    ("Rushabh is Ira's creator and boss - she should treat him with appropriate respect but also as a trusted confidant", "context"),
]

ENTITY_MEMORIES = [
    # Machinecraft
    ("company", "Machinecraft", "Family-run thermoforming machine factory founded by Rushabh's grandfather, built up by his father Deepak", "fact"),
    ("company", "Machinecraft", "Has been operating since 1976 - a multi-generational family business", "fact"),
    ("company", "Machinecraft", "Exports to dozens of countries with multiple machine models and product lines", "fact"),
    ("company", "Machinecraft", "Leadership is divided among Rushabh (technology), and his brothers (production and sales)", "fact"),
    
    # Formpack
    ("company", "Formpack", "One of Rushabh's business ventures, part of the ₹500 Cr goal by 2030", "fact"),
    
    # MAPL
    ("company", "MAPL", "New business arm of Rushabh's operations, part of the ₹500 Cr goal by 2030", "fact"),
    
    # Calftel
    ("company", "Calftel", "Rushabh's moonshot initiative: portable, low-cost thermoforming factories for rural entrepreneurs", "fact"),
    ("company", "Calftel", "Goal: pilot orders via NGOs, 500+ rural jobs by 2028", "fact"),
    
    # Rimpact
    ("company", "Rimpact", "Joint venture project for automotive molding with international partners, led by Rushabh", "fact"),
    
    # People
    ("contact", "Deepak Doshi", "Rushabh's father, stern patriarch who built Machinecraft, values heritage and tradition", "fact"),
    ("contact", "Palak Doshi", "Rushabh's wife, former professor turned financial manager, practical and grounding", "fact"),
    ("contact", "Aanya Doshi", "Rushabh's daughter", "fact"),
    ("contact", "Inaya Doshi", "Rushabh's daughter", "fact"),
]


def store_memories():
    """Store all memories in the persistent memory system."""
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 60)
    print("STORING MEMORIES ABOUT RUSHABH DOSHI (THE BOSS)")
    print("=" * 60)
    
    # Store user memories
    print(f"\n📝 Storing {len(USER_MEMORIES)} user memories...")
    user_count = 0
    for memory_text, memory_type in USER_MEMORIES:
        result = pm.store_memory(
            identity_id=RUSHABH_IDENTITY_ID,
            memory_text=memory_text,
            memory_type=memory_type,
            source_channel="system",
            source_conversation_id="maker_inheritance_pdf",
            confidence=1.0,
            embed=True
        )
        if result:
            user_count += 1
            print(f"  ✓ [{memory_type}] {memory_text[:60]}...")
        else:
            print(f"  ⊘ (duplicate) {memory_text[:40]}...")
    
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
    print(f"COMPLETE: Stored {user_count} user memories, {entity_count} entity memories")
    print("=" * 60)
    
    # Update identity name
    update_identity_name()
    
    return user_count, entity_count


def update_identity_name():
    """Update the identity links to include Rushabh's name."""
    import json
    
    state_dir = PROJECT_ROOT / "openclaw/agents/ira/src/memory/state"
    links_file = state_dir / "identity_links.json"
    
    if links_file.exists():
        links = json.loads(links_file.read_text())
        if RUSHABH_IDENTITY_ID in links.get("identities", {}):
            links["identities"][RUSHABH_IDENTITY_ID]["name"] = "Rushabh Doshi"
            links["identities"][RUSHABH_IDENTITY_ID]["role"] = "boss"
            links["identities"][RUSHABH_IDENTITY_ID]["email"] = "rushabh@machinecraft.org"
            links_file.write_text(json.dumps(links, indent=2))
            print("\n✓ Updated identity_links.json with Rushabh's name and role")


if __name__ == "__main__":
    store_memories()
