#!/usr/bin/env python3
"""
Store Machinecraft Master Applications Database knowledge in Ira's memory.
Source: Machinecraft Master Applications Database - Executive Summary.pdf

This is strategic business intelligence:
- 24 applications across 7 industries
- Customer examples and market potential
- Machine-application mapping
- Sales strategy recommendations
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
    # DATABASE OVERVIEW
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Applications database: 24 distinct applications across 7 major industries, mapped to 59 machine models", "fact"),
    ("company", "Machinecraft Technologies",
     "Market coverage: 8 key European companies analyzed with application mapping and opportunity assessment", "fact"),
    
    # ==========================================================================
    # INDUSTRY 1: AUTOMOTIVE (Highest Priority - 25% market)
    # ==========================================================================
    ("product", "Market Applications",
     "AUTOMOTIVE (25% market, Highest Priority): Front panels, door panels, fenders, consoles, 3D car mats", "fact"),
    ("product", "Market Applications",
     "Automotive key customers: Arthur Krüger GmbH (Germany), Berbetores Industrial (Spain)", "fact"),
    ("product", "Market Applications",
     "Automotive machines: PF1 Classic, PF1-X, PF1-M Series - focus on precision, automation, Class A surfaces", "fact"),
    
    # ==========================================================================
    # INDUSTRY 2: COMMERCIAL VEHICLE (Very High Priority - 15% market)
    # ==========================================================================
    ("product", "Market Applications",
     "COMMERCIAL VEHICLE (15% market, Very High Priority): Bus driver compartments, truck aerodynamic components", "fact"),
    ("product", "Market Applications",
     "Commercial vehicle key customer: Promens Zlín (Czech Republic) - Tier 1 supplier to Škoda, Volvo, John Deere", "fact"),
    ("product", "Market Applications",
     "Commercial vehicle machines: PF1-X, FCS Series - target Tier 1 suppliers, complement RIM/SMC tech", "fact"),
    
    # ==========================================================================
    # INDUSTRY 3: MEDICAL (High Growth - 20% market)
    # ==========================================================================
    ("product", "Market Applications",
     "MEDICAL (20% market, High Growth): Medical device trays, pharmaceutical blister packs, surgical instrument trays", "fact"),
    ("product", "Market Applications",
     "Medical key customer: Nelipak (Ireland) - Global leader in medical packaging", "fact"),
    ("product", "Market Applications",
     "Medical machines: IMG, PF1-X, FCS Series - focus on quality, compliance, high-volume repeatability", "fact"),
    
    # ==========================================================================
    # INDUSTRY 4: AGRICULTURAL (Stable - 10% market)
    # ==========================================================================
    ("product", "Market Applications",
     "AGRICULTURAL (10% market, Stable): Engine hoods, fenders, interior components for farm equipment", "fact"),
    ("product", "Market Applications",
     "Agricultural key customers: Promens Zlín, agricultural equipment manufacturers", "fact"),
    ("product", "Market Applications",
     "Agricultural machines: PF1-X, PF1 Classic - chemical resistance and durability focus", "fact"),
    
    # ==========================================================================
    # INDUSTRY 5: FOOD PACKAGING (Volume - 15% market)
    # ==========================================================================
    ("product", "Market Applications",
     "FOOD PACKAGING (15% market, Volume Opportunity): Fresh meat packaging, coffee capsules, dairy containers", "fact"),
    ("product", "Market Applications",
     "Food packaging machines: FCS Series, light gauge systems - high-speed production, food safety compliance", "fact"),
    
    # ==========================================================================
    # KEY CUSTOMER PROFILES - TIER 1 OPPORTUNITIES
    # ==========================================================================
    ("contact", "Promens Zlín",
     "EU Lead: Promens Zlín (Czech Republic) - Tier 1 with RIM/SMC/vacuum forming, serves Škoda/Volvo/John Deere", "context"),
    ("contact", "Promens Zlín",
     "Promens Zlín opportunity: HIGHEST PRIORITY - excellent fit for PF1-X and FCS, complement existing tech", "context"),
    
    ("contact", "Arthur Krüger GmbH",
     "EU Lead: Arthur Krüger GmbH (Germany) - established thermoformer, automotive focus, upgrade opportunity", "context"),
    ("contact", "Arthur Krüger GmbH",
     "Arthur Krüger strategy: Upgrade to single-sheet precision systems, established relationship", "context"),
    
    ("contact", "Nelipak",
     "EU Lead: Nelipak (Ireland) - Global medical packaging leader, high-volume production focus", "context"),
    ("contact", "Nelipak",
     "Nelipak opportunity: Target high-speed medical packaging lines, quality/compliance focus", "context"),
    
    # ==========================================================================
    # KEY CUSTOMER PROFILES - GROWTH OPPORTUNITIES
    # ==========================================================================
    ("contact", "Berbetores Industrial",
     "EU Lead: Berbetores Industrial (Spain) - automotive focus, growth opportunity", "context"),
    ("contact", "Durotherm Holding",
     "EU Lead: Durotherm Holding (Germany) - industrial applications specialist", "context"),
    ("contact", "VDL Wientjes Roden",
     "EU Lead: VDL Wientjes Roden (Netherlands) - industrial upgrade opportunity", "context"),
    
    # ==========================================================================
    # MACHINE-APPLICATION MAPPING
    # ==========================================================================
    ("product", "PF1-X Series",
     "PF1-X applications: Automotive precision components, medical device packaging, commercial vehicle interiors, agricultural equipment", "fact"),
    ("product", "PF1 Classic",
     "PF1 Classic applications: Automotive exterior panels, industrial covers/housings, agricultural components, general thermoforming", "fact"),
    ("product", "FCS Series",
     "FCS applications: Medical packaging (high volume), food packaging, commercial vehicle production, industrial applications", "fact"),
    ("product", "PF1-L Series",
     "PF1-L applications: Luggage shells - specialized niche market", "fact"),
    ("product", "PF1-M Series",
     "PF1-M applications: 3D car mats - automotive aftermarket and OEM", "fact"),
    ("product", "PF1-W Series",
     "PF1-W applications: Wellness products - bathtubs, shower trays, spas", "fact"),
    ("product", "AMV-M Series",
     "AMV-M applications: Car mat production - roll-fed automotive floor mats", "fact"),
    
    # ==========================================================================
    # STRATEGIC RECOMMENDATIONS
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Sales priority 1: Contact Promens Zlín - Highest priority Tier 1 supplier with immediate needs", "context"),
    ("company", "Machinecraft Technologies",
     "Sales priority 2: Engage Arthur Krüger - established relationship, upgrade opportunity", "context"),
    ("company", "Machinecraft Technologies",
     "Sales priority 3: Approach Nelipak - global medical packaging leader", "context"),
    
    # ==========================================================================
    # MARKET ENTRY STRATEGY BY INDUSTRY
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Strategy - Automotive: Focus on precision and automation advantages for Class A surfaces", "context"),
    ("company", "Machinecraft Technologies",
     "Strategy - Medical: Emphasize quality, compliance, and repeatability", "context"),
    ("company", "Machinecraft Technologies",
     "Strategy - Commercial Vehicle: Target Tier 1 suppliers and OEMs", "context"),
    ("company", "Machinecraft Technologies",
     "Strategy - Food Packaging: Highlight high-speed production capabilities", "context"),
    
    # ==========================================================================
    # GEOGRAPHIC FOCUS
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "EU Primary markets: Germany, Czech Republic, Netherlands (established)", "context"),
    ("company", "Machinecraft Technologies",
     "EU Secondary markets: Spain, Denmark, Sweden (growth opportunities)", "context"),
    ("company", "Machinecraft Technologies",
     "Global focus: Medical and food packaging applications worldwide", "context"),
    
    # ==========================================================================
    # PRODUCT POSITIONING
    # ==========================================================================
    ("product", "PF1-X Series",
     "PF1-X positioning: Premium automation and precision for demanding applications", "fact"),
    ("product", "FCS Series",
     "FCS positioning: High-volume production efficiency for packaging markets", "fact"),
    ("product", "Specialized Series",
     "Specialized series positioning: Niche market leadership (PF1-L, PF1-M, PF1-W)", "fact"),
]

def store_memories():
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING APPLICATIONS DATABASE & MARKET INTELLIGENCE")
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

    print(f"\n✅ Stored {count} market intelligence items")
    print("\n" + "="*70)
    print("MARKET OPPORTUNITIES SUMMARY")
    print("="*70)
    print("""
INDUSTRY PRIORITIES (by market share):

┌────────────────────┬─────────┬──────────────────────────────────────────────┐
│ Industry           │ Market  │ Key Applications                             │
├────────────────────┼─────────┼──────────────────────────────────────────────┤
│ AUTOMOTIVE         │ 25%     │ Panels, fenders, consoles, 3D mats           │
│ MEDICAL            │ 20%     │ Device trays, blister packs, surgical trays  │
│ COMMERCIAL VEHICLE │ 15%     │ Bus compartments, truck aerodynamics         │
│ FOOD PACKAGING     │ 15%     │ Meat packaging, coffee capsules, dairy       │
│ AGRICULTURAL       │ 10%     │ Engine hoods, fenders, interior components   │
└────────────────────┴─────────┴──────────────────────────────────────────────┘

TOP 3 SALES PRIORITIES:
  1. Promens Zlín (Czech) - Tier 1, Škoda/Volvo/John Deere
  2. Arthur Krüger GmbH (Germany) - Automotive, upgrade opportunity  
  3. Nelipak (Ireland) - Global medical packaging leader

MACHINE RECOMMENDATIONS BY MARKET:
  Premium (PF1-X): Automotive precision, medical, commercial vehicle
  Volume (FCS): Medical packaging, food, commercial vehicle
  Mainstream (PF1 Classic): Automotive exterior, industrial, agricultural
  Niche: PF1-L (luggage), PF1-M (car mats), PF1-W (wellness)
""")
    return count

if __name__ == "__main__":
    store_memories()
