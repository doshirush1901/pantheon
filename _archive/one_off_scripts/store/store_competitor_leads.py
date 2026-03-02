#!/usr/bin/env python3
"""
Store competitor analysis and EU sales leads in Ira's memory.

Sources:
1. Machinecraft Company Presentation June 2023 - Rushabh Doshi for FRIMO.pptx
2. Competitor Customer Analysis - Single Station Thermoforming.xlsx
3. Copy of Copy of Thermoforming Industry 2016.pdf

Key Competitors: Kiefel, Geiss, Illig, CMS, Cannon (EU premium)
Sales Leads: Companies currently using competitor machines
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
    # THERMOFORMING INDUSTRY OVERVIEW - Market Tiers
    # ==========================================================================
    ("company", "Thermoforming Industry",
     "Market tiers: EU/Japan = premium (top quality, high price), USA/Canada/Turkey = middle, India/China/Brazil = budget", "fact"),
    ("company", "Thermoforming Industry",
     "Global thermoforming machine makers: 30 companies in 14 countries (2016 analysis)", "fact"),
    ("company", "Thermoforming Industry",
     "Germany leads with 6 makers: Kiefel, Illig, Geiss, Gabler, Rudholzer, FRIMO", "fact"),
    ("company", "Thermoforming Industry",
     "Italy has 3 makers: CMS, Comi, OMG - positioned in EU premium tier", "fact"),
    
    # ==========================================================================
    # KIEFEL (Germany) - Top EU Competitor
    # ==========================================================================
    ("company", "Kiefel",
     "Kiefel = Germany's largest thermoformer, HQ Freilassing, 500 employees, €100M turnover (₹600Cr)", "fact"),
    ("company", "Kiefel",
     "Kiefel thick-sheet machines: KL, KLV, KLS, KEK, KU, KEN series for automotive", "fact"),
    ("company", "Kiefel",
     "Kiefel KL-Series: Single station vacuum forming, cycle time 100-120s, for door panels, consoles, instrument panels", "fact"),
    ("company", "Kiefel",
     "Kiefel KLS-Series: Inline 4-up rotary, cycle time 40-60s, for high-volume interior parts", "fact"),
    ("company", "Kiefel",
     "Kiefel IMG capability: In-Mould-Graining packages on KL, KLV, KLS machines", "fact"),
    ("company", "Kiefel",
     "Kiefel edge-folding: KU-Series for post-forming edge fold, 50-70s cycle time", "fact"),
    ("company", "Kiefel",
     "Kiefel packaging: KMD SPEEDFORMER (steel rule cutting), KTR Cup Forming up to 45 cycles/min", "fact"),
    ("company", "Kiefel",
     "Kiefel appliance: KIV/KID inline for refrigerator inner/door liners with 2-bar pressure forming", "fact"),
    ("company", "Kiefel",
     "Kiefel customers (automotive): Faurecia, IAC, Motherson, Johnson Controls, SL Corp", "fact"),
    
    # ==========================================================================
    # GEISS (Germany) - Key EU Competitor
    # ==========================================================================
    ("company", "Geiss",
     "Geiss = German heavy-gauge thermoformer, also makes 5-axis CNC trimming machines", "fact"),
    ("company", "Geiss",
     "Geiss T-Series machines: T7, T8, T9, T10 - increasing platen sizes", "fact"),
    ("company", "Geiss",
     "Geiss T10 = fully servo-driven, electronic synchronization (no mechanical torsion shafts)", "fact"),
    ("company", "Geiss",
     "Geiss automotive customers: Delphi, Faurecia, Johnson Controls, Magna-Intier, Peguform", "fact"),
    ("company", "Geiss",
     "Geiss export = 2/3 of sales volume - UK, Scandinavia, Russia", "fact"),
    
    # ==========================================================================
    # CMS (Italy) - EU Competitor
    # ==========================================================================
    ("company", "CMS",
     "CMS = Italian thick-sheet thermoformer, BR5HP flagship machine", "fact"),
    ("company", "CMS",
     "CMS BR5HP: 1500x1000mm to 3500x2500mm, servo gantry mould table, vacuum + pressure on upper mould", "fact"),
    ("company", "CMS",
     "CMS features: Quick mould change, diagnostics networking, Industry 4.0 ready", "fact"),
    ("company", "CMS",
     "CMS advantage: Dual servo motors (gantry) for precise positioning and high pressure", "fact"),
    
    # ==========================================================================
    # ILLIG (Germany) - EU Competitor
    # ==========================================================================
    ("company", "Illig",
     "Illig = German thermoformer since 1946, 800+ employees, widest machine range", "fact"),
    ("company", "Illig",
     "Illig UA-Series: UA100Ed, UA150g to UA300g for thick sheet processing", "fact"),
    ("company", "Illig",
     "Illig forming area: 960x560mm (UA100Ed) with 300mm stroke", "fact"),
    
    # ==========================================================================
    # OTHER EU COMPETITORS
    # ==========================================================================
    ("company", "OMG",
     "OMG = Italian thermoformer, 800x900mm inline machines, pneumatic clamp & plug", "fact"),
    ("company", "Comi",
     "Comi = Italian thermoformer, desktop to large format machines", "fact"),
    ("company", "Formech",
     "Formech = UK thermoformer, desktop to fully automatic HD series", "fact"),
    ("company", "Tools Factory",
     "Tools Factory = Polish thermoformer, budget EU alternative", "fact"),
    
    # ==========================================================================
    # TURKISH COMPETITORS (Middle tier)
    # ==========================================================================
    ("company", "Inpak",
     "Inpak (Turkey): 50 employees, 30 machines/year, TS-800 at €290K, 75 cycles/min", "fact"),
    ("company", "Yeniyurt",
     "Yeniyurt = Turkish thermoformer, middle-tier pricing", "fact"),
    ("company", "Guven Teknik",
     "Guven Teknik = Turkish thermoformer, middle-tier positioning", "fact"),
    
    # ==========================================================================
    # MACHINECRAFT vs EU COMPETITORS - Positioning
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Machinecraft positioning vs EU: 50-60% lower cost than Kiefel/Geiss/CMS for comparable specs", "fact"),
    ("company", "Machinecraft Technologies",
     "Machinecraft EU partner: FRIMO (Germany) for technology & sales collaboration", "fact"),
    ("company", "Machinecraft Technologies",
     "Machinecraft advantage: Indian cost structure + German-level engineering quality", "fact"),
    ("company", "Machinecraft Technologies",
     "Machinecraft targets: Companies with Illig, Geiss, CMS, Kiefel machines needing replacement or expansion", "fact"),
    
    # ==========================================================================
    # EU SALES LEADS - GEISS CUSTOMERS (Potential Machinecraft Targets)
    # ==========================================================================
    ("contact", "Hombach (Germany)",
     "EU Lead: Hombach, Germany - has GEISS T10, 10 thermoforming machines, automotive parts (BMW, KTM, Bugatti)", "context"),
    ("contact", "Plastika Balumag (Switzerland)",
     "EU Lead: Plastika Balumag, Switzerland - has GEISS T10, 4 large + 3 small machines, aircraft/vehicles/medicine", "context"),
    ("contact", "Plast-tech (UK)",
     "EU Lead: Plast-tech, UK - 7 thermoforming machines, 3000x2000mm capacity, automotive/caravan/motorhome", "context"),
    ("contact", "Lakowa (Germany)",
     "EU Lead: Lakowa, Germany - has GEISS T9, 4000x2300mm capacity, railway/automotive/buses", "context"),
    ("contact", "Durotherm (Germany)",
     "EU Lead: Durotherm, Germany - has GEISS T10, 33 machines (5 twin-sheet), 19 CNCs, automotive/EV/caravan", "context"),
    ("contact", "Parat (Germany/China)",
     "EU Lead: Parat, Germany - €87M turnover, 800 employees, 13 thermoforming, farm machinery/RVs/automotive", "context"),
    ("contact", "J&A Kay (UK)",
     "EU Lead: J&A Kay, UK - has GEISS T8, buses/ambulances/trucks/trains interior panels", "context"),
    ("contact", "Balform (UK)",
     "EU Lead: Balform, UK - has 2x GEISS T10 (£250K each), 50 employees, aviation interiors/aerospace", "context"),
    ("contact", "CWP (UK)",
     "EU Lead: CWP, UK - has GEISS T10, established 1943, thermoforming specialist", "context"),
    ("contact", "DMS Plastics (UK)",
     "EU Lead: DMS Plastics, UK - 4 thermoformers + 5 CNCs, 3000x2000mm capacity, aircraft materials (Ultem, Kydex)", "context"),
    ("contact", "Borsi (Germany)",
     "EU Lead: Borsi, Germany - automotive/POS applications, instrument covers, truck door lining", "context"),
    ("contact", "WKV (Germany)",
     "EU Lead: WKV, Germany - 2250x1250mm capacity, vehicle construction, cabin linings", "context"),
    ("contact", "FM Kunstofftechnik (Germany)",
     "EU Lead: FM Kunststofftechnik, Germany - agricultural vehicles, special vehicles", "context"),
    ("contact", "Linbrunner (Germany)",
     "EU Lead: Linbrunner, Germany - twin-sheet forming capability, 2160x1260mm", "context"),
    ("contact", "Roweko (Germany)",
     "EU Lead: Roweko, Germany - 5 thermoforming machines, 2500x1250mm capacity", "context"),
    ("contact", "Arthur Krugner (Germany)",
     "EU Lead: Arthur Krugner, Germany - has GEISS T8, 2200x3300mm, aviation/vehicle/machine construction", "context"),
    ("contact", "Formvac (Norway)",
     "EU Lead: Formvac, Norway - has GEISS T8, established 1958", "context"),
    ("contact", "Benetexplast (Czech)",
     "EU Lead: Benetexplast, Czech Republic - has GEISS T7, T8 machines", "context"),
    ("contact", "Keraplast (Finland)",
     "EU Lead: Keraplast, Finland - PC material specialist", "context"),
    ("contact", "BTL Plastics (Belgium)",
     "EU Lead: BTL Plastics, Belgium - thermoforming specialist", "context"),
    ("contact", "Purvac (Finland)",
     "EU Lead: Purvac, Finland - thermoforming specialist", "context"),
    ("contact", "Linecross (UK)",
     "EU Lead: Linecross, UK - established 1958, thermoforming specialist", "context"),
    ("contact", "Asoma (Finland)",
     "EU Lead: Asoma, Finland - thermoforming specialist", "context"),
    
    # ==========================================================================
    # COMPETITOR TECHNOLOGY COMPARISON
    # ==========================================================================
    ("product", "Competitor Technology",
     "Kiefel advantage: Complete process solutions (forming + edge-folding + riveting), TEPEO2 technology", "fact"),
    ("product", "Competitor Technology",
     "Geiss advantage: Electronic servo synchronization, integrated CNC trimming, Industry 4.0", "fact"),
    ("product", "Competitor Technology",
     "CMS advantage: Gantry servo system, vacuum+pressure on upper mould, quick mould change", "fact"),
    ("product", "Competitor Technology",
     "Machinecraft advantage: PF1 full servo at fraction of EU cost, fast delivery (2-3 months vs 6-9 months)", "fact"),
    
    # ==========================================================================
    # SALES STRATEGY - POSITIONING
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "EU sales pitch: 'German-quality engineering at Indian pricing - 50% cost savings with same performance'", "fact"),
    ("company", "Machinecraft Technologies",
     "Target customers: Companies with aging Illig/Geiss/CMS machines, or expanding capacity on budget", "fact"),
    ("company", "Machinecraft Technologies",
     "Key differentiator: Full servo PF1-X at price of competitor's pneumatic machines", "fact"),
]

def store_memories():
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING COMPETITOR ANALYSIS & EU SALES LEADS")
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
            print(f"  ✓ [{entity_type}] {memory_text[:50]}...")
        else:
            print(f"  ⊘ (dup) {memory_text[:40]}...")

    print(f"\n✅ Stored {count} competitor/lead items")
    print("\n" + "="*70)
    print("KNOWLEDGE SUMMARY")
    print("="*70)
    print("""
MAIN EU COMPETITORS:
  • Kiefel (Germany) - €100M, 500 employees, KL/KLS/KLV series
  • Geiss (Germany) - T7/T8/T9/T10 servo machines + CNC
  • CMS (Italy) - BR5HP, gantry servo, vacuum+pressure
  • Illig (Germany) - UA series, widest range, 800 employees

MARKET POSITIONING:
  • Premium: EU/Japan (Kiefel, Geiss, Illig, CMS)
  • Middle: USA, Turkey, Canada
  • Budget: India, China, Brazil (Machinecraft here - but German quality)

EU SALES LEADS (22 Companies with GEISS machines):
  • Germany: Hombach, Durotherm, Parat, Lakowa, Borsi, WKV, Linbrunner...
  • UK: Plast-tech, J&A Kay, Balform, CWP, DMS Plastics, Linecross
  • Switzerland: Plastika Balumag
  • Finland: Keraplast, Purvac, Asoma
  • Norway: Formvac
  • Czech: Benetexplast
  • Belgium: BTL Plastics

MACHINECRAFT VALUE PROPOSITION:
  50-60% lower cost than EU competitors
  Full servo at competitor's pneumatic price
  2-3 month delivery vs 6-9 months
""")
    return count

if __name__ == "__main__":
    store_memories()
