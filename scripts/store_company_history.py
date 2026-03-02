#!/usr/bin/env python3
"""
Store Machinecraft Technologies Evolution & Performance (1976-2025) in Ira's memory.

Source: Machinecraft Technologies Evolution and Performance (1976–2025).pdf

This is CORE COMPANY KNOWLEDGE covering:
- Complete 50-year history
- Financial performance (2019-2025)
- Product line evolution
- Leadership & family structure
- Global partnerships
- Future targets
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
    # FOUNDING & ORIGINS (1976)
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Founded 1976 by B.P. Doshi (Bhanuchandra P. Doshi), polymer chemist from UDCT Mumbai", "fact"),
    ("company", "Machinecraft Technologies",
     "Origin story: Built one of India's first vacuum forming machines, Make-in-India before it was a slogan", "fact"),
    ("company", "Machinecraft Technologies",
     "Birthplace: Mumbai, 1976 - started with engineering mind and belief India could build better machines", "fact"),
    
    # ==========================================================================
    # DOSHI FAMILY LEADERSHIP
    # ==========================================================================
    ("contact", "B.P. Doshi",
     "B.P. Doshi (Bhanuchandra) = Founder, Chairman, polymer chemist from UDCT Mumbai, started Machinecraft 1976", "fact"),
    ("contact", "Deepak Doshi",
     "Deepak Doshi = 2nd gen, joined 1986, opened export markets (Middle East, Europe), father of Rushabh", "fact"),
    ("contact", "Rajesh Doshi",
     "Rajesh Doshi = 2nd gen, joined 1994, introduced CAD designs and PLC controls, father of Manan", "fact"),
    ("contact", "Rushabh Doshi",
     "Rushabh Doshi = 3rd gen, joined 2013, education in robotics, implemented digital project management (Asana)", "fact"),
    ("contact", "Manan Doshi",
     "Manan Doshi = 3rd gen, joined 2018, parametric CAD design, transitioned machines from pneumatic to servo", "fact"),
    
    # ==========================================================================
    # MAJOR MILESTONES
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "1980s-90s: 2nd generation expanded business, took machines abroad, introduced PLCs, CAD, safety systems", "fact"),
    ("company", "Machinecraft Technologies",
     "1990: New factory outside Mumbai, began showcasing at international expos like Germany's K-Show", "fact"),
    ("company", "Machinecraft Technologies",
     "1998: First automated vacuum-forming machines sold in Europe", "fact"),
    ("company", "Machinecraft Technologies",
     "K 2001: Debuted fully automatic machines, met European CE safety norms", "fact"),
    ("company", "Machinecraft Technologies",
     "Early 2010s: Machines installed in 35+ countries, ~50 machines/year production", "fact"),
    ("company", "Machinecraft Technologies",
     "2014: Launched Indu Thermoformers - sister company making plastic products and sheets", "fact"),
    ("company", "Machinecraft Technologies",
     "2018: Strategic partnership with FRIMO (Germany) for automotive interior technologies", "fact"),
    ("company", "Machinecraft Technologies",
     "2019: Opened Umargam factory (Gujarat) - 21,000 sq ft, purpose-built for larger automated machines", "fact"),
    ("company", "Machinecraft Technologies",
     "2020: COVID hit, revenue dropped 25%, but retained 100 employees - 'people first, always'", "fact"),
    ("company", "Machinecraft Technologies",
     "2020: Launched Formpack - making thermoformed parts (wind energy, agri, heavy vehicles)", "fact"),
    ("company", "Machinecraft Technologies",
     "2021: Built India's LARGEST vacuum forming machine - 4.25m x 2.5m for windmill blade components", "fact"),
    ("company", "Machinecraft Technologies",
     "2022: FRIMO filed bankruptcy, but Machinecraft had absorbed valuable know-how by then", "fact"),
    ("company", "Machinecraft Technologies",
     "2022: New alliance with FVF Thermoforming (Japan) for TOM (3D Overlay) film lamination technology", "fact"),
    ("company", "Machinecraft Technologies",
     "K 2022: Major exhibit at Düsseldorf to reconnect with global buyers post-pandemic", "fact"),
    ("company", "Machinecraft Technologies",
     "2024: Umargam facility doubled to ~40,000 sq ft (3,800 m²)", "fact"),
    
    # ==========================================================================
    # FINANCIAL PERFORMANCE
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "FY2019: ~₹40Cr revenue, ~50 machines, ~18% EBITDA (baseline before Umargam)", "fact"),
    ("company", "Machinecraft Technologies",
     "FY2020: COVID impact, reduced output, V-shaped recovery followed", "fact"),
    ("company", "Machinecraft Technologies",
     "FY2021-2024: Steady growth trajectory, 50+ machines/year, strong export recovery", "fact"),
    ("company", "Machinecraft Technologies",
     "Export share has grown significantly, now majority of revenue", "fact"),
    
    # ==========================================================================
    # GROUP STRUCTURE
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Group companies: Machinecraft (machines), Formpack (parts), Indu (sheets) - integrated ecosystem", "fact"),
    ("company", "Machinecraft Technologies",
     "Group size: ~140 people, ₹60+ Cr turnover (2025)", "fact"),
    ("company", "Machinecraft Technologies",
     "Indu Thermoformers (2014): Makes ABS, ASA, HDPE sheets for machines and external sale", "fact"),
    ("company", "Machinecraft Technologies",
     "Formpack (2020): Produces thermoformed parts - wind energy covers, agri machinery, heavy vehicles", "fact"),
    
    # ==========================================================================
    # PRODUCT LINE (24 MODELS)
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Product portfolio 2025: ~24 distinct machine models across heavy-gauge, packaging, automotive, trimming", "fact"),
    ("product", "PF1 Series",
     "PF1 Series: Flagship servo-driven vacuum formers, 1200x860mm to 3560x2560mm, modular workhorses", "fact"),
    ("product", "PF1-XL Series",
     "PF1-XL Series: Extra-large format up to 4x2.2m, for aircraft panels, trucks, tractors, signage", "fact"),
    ("product", "PF2 Series",
     "PF2 Series: Pneumatic manual-loaded machines for small batches and prototyping", "fact"),
    ("product", "SPA Series",
     "SPA Series: Deep-draw formers for spa tubs, bathtubs - 3000x3000mm forming area, extra depth", "fact"),
    ("product", "AM Series",
     "AM Series: Entry-level roll-fed vacuum formers for small clamshells and trays", "fact"),
    ("product", "FCS Series",
     "FCS Series: Form-Cut-Stack automated pressure forming with in-mold cutting for packaging", "fact"),
    ("product", "TFM Series",
     "TFM Series: Thermoforming with integrated trimming for high-volume packaging", "fact"),
    ("product", "IMG-S Series",
     "IMG-S Series: In-Mold Graining/Skinning for soft-touch automotive interiors (dashboards, door panels)", "fact"),
    ("product", "TOM Technology",
     "TOM (3D Overlay): Film lamination technology via FVF Japan - decorative films on 3D parts", "fact"),
    
    # ==========================================================================
    # VALUE PROPOSITION
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Value prop: European-quality machines at 1/3 the price - drove early global growth", "fact"),
    ("company", "Machinecraft Technologies",
     "Competitive advantage: significantly lower cost than European competitors for comparable specs", "fact"),
    ("company", "Machinecraft Technologies",
     "Strategy: One-stop solution provider - machine + mold + downstream trimming", "fact"),
    
    # ==========================================================================
    # PARTNERSHIPS
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "FRIMO partnership (2018-2022): German automotive tooling, IMG/vacuum lamination know-how", "fact"),
    ("company", "Machinecraft Technologies",
     "FVF partnership (2022+): Japan TOM technology for 3D film overlay lamination", "fact"),
    ("company", "Machinecraft Technologies",
     "Tier-1 contacts via FRIMO: IAC, Grupo Antolin, Motherson, TACO - quoted 10+ OEM programs", "fact"),
    ("company", "Machinecraft Technologies",
     "Lanulfi partnership (Italy): Toolmaking collaboration", "fact"),
    
    # ==========================================================================
    # GLOBAL PRESENCE
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Export markets: 40+ countries - Europe, Middle East, North America, Latin America, Asia", "fact"),
    ("company", "Machinecraft Technologies",
     "Key trade shows: K-Show (Germany), triennial presence since 1990s", "fact"),
    ("company", "Machinecraft Technologies",
     "2023 expansion: New distributors in Latin America, Eastern Europe", "fact"),
    
    # ==========================================================================
    # FACILITIES
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Umargam factory: Gujarat, ~150km from Mumbai, 40,000 sq ft (2024), purpose-built for large machines", "fact"),
    ("company", "Machinecraft Technologies",
     "Tooling hub strategy: Building in-house tooling capability to supply global partners", "fact"),
    
    # ==========================================================================
    # VISION 2030
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Vision 2030: #1 integrated thermoforming ecosystem in Asia - machinery, tooling, sheets, parts", "fact"),
    ("company", "Machinecraft Technologies",
     "2030 target: ₹300Cr turnover (5x growth from ₹60Cr)", "fact"),
    ("company", "Machinecraft Technologies",
     "Strategy 2030: Lead in innovation, customer trust, global competitiveness - Indian engineering vs the best", "fact"),
    
    # ==========================================================================
    # CULTURE & VALUES
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Core values: 'We keep our word', 'We build globally respected machines', 'Support each other like family'", "fact"),
    ("company", "Machinecraft Technologies",
     "COVID response: No layoffs, absorbed HR cost spike (15% to 25% of revenue), drew on cash reserves", "fact"),
    ("company", "Machinecraft Technologies",
     "Governance reform (2020): Formal Board of Directors, 3rd gen operational control, independent advisor", "fact"),
    
    # ==========================================================================
    # APPLICATIONS
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Heavy-gauge applications: Automotive panels, vehicle interiors, appliance housings, sanitary ware, spa tubs", "fact"),
    ("company", "Machinecraft Technologies",
     "Packaging applications: Food trays, cups, medical blisters, electronics packaging, FMCG", "fact"),
    ("company", "Machinecraft Technologies",
     "Specialty applications: Wind energy (blade components), aircraft interiors, billboard signage", "fact"),
    
    # ==========================================================================
    # COMPETITIVE LANDSCAPE
    # ==========================================================================
    ("company", "Machinecraft Technologies",
     "Competitors: Illig, Kiefel, Geiss, CMS (EU) - Machinecraft positioned as value alternative", "fact"),
    ("company", "Machinecraft Technologies",
     "Competitors: Illig, Kiefel, Geiss, CMS (EU) - Machinecraft positioned as strong value alternative in global market", "fact"),
]

def store_memories():
    from openclaw.agents.ira.src.memory.persistent_memory import PersistentMemory
    
    pm = PersistentMemory()
    
    print("=" * 70)
    print("STORING MACHINECRAFT COMPANY HISTORY & PERFORMANCE")
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

    print(f"\n✅ Stored {count} company history items")
    print("\n" + "="*70)
    print("MACHINECRAFT TECHNOLOGIES SUMMARY")
    print("="*70)
    print("""
🏭 COMPANY AT A GLANCE (2025):
  Founded: 1976 (Mumbai) by B.P. Doshi
  Factory: Umargam, Gujarat (40,000 sq ft)
  Team: ~140 people
  Revenue: ₹60+ Cr (FY24), targeting ₹70Cr (FY25)
  Exports: 40+ countries, 55% of revenue

👨‍👩‍👦 DOSHI FAMILY LEADERSHIP:
  1st Gen: B.P. Doshi (Founder, Chairman)
  2nd Gen: Deepak Doshi (Exports), Rajesh Doshi (Engineering)
  3rd Gen: Rushabh Doshi (Digital/Ops), Manan Doshi (Design/Servo)

📈 FINANCIAL TRAJECTORY:
  FY2019: ₹40Cr (baseline)
  FY2020: ₹30Cr (-25%, COVID)
  FY2021: ₹45Cr (+50%, V-recovery)
  FY2022: ₹60Cr (record)
  FY2025: ₹70Cr target

🔧 PRODUCT LINES (24 models):
  Heavy-gauge: PF1, PF1-X, PF1-XL, PF2, SPA
  Packaging: AM, FCS, TFM
  Automotive: IMG-S, TOM, Press Lamination

🤝 KEY PARTNERSHIPS:
  FRIMO (Germany, 2018-22): Automotive interior tech
  FVF Japan (2022+): TOM film lamination
  Tier-1s: IAC, Grupo Antolin, Motherson, TACO

🎯 VISION 2030:
  Target: ₹300Cr revenue (5x growth)
  Goal: #1 integrated thermoforming ecosystem in Asia
""")
    return count

if __name__ == "__main__":
    store_memories()
