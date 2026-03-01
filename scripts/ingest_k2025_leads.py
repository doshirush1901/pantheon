#!/usr/bin/env python3
"""
Ingest K2025 Leads - K-Show Germany Trade Show Leads

65 international leads from K-Show 2025 in Dusseldorf, Germany.
Major plastics trade fair - high quality global leads.

Source: K2025 Leads.xlsx
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "K2025 Leads.xlsx"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from K2025 leads."""
    items = []

    # 1. K2025 Leads Overview
    items.append(KnowledgeItem(
        text="""K2025 Trade Show Leads Overview

SOURCE: K-Show 2025, Dusseldorf, Germany
TOTAL LEADS: 65 contacts
EVENT: World's largest plastics trade fair (triennial)
DATA FIELDS: Company, Person, Position, Email, Country, Website, Machine Interest, Price Quoted, Comments

GEOGRAPHIC DISTRIBUTION:
- Europe: ~30 leads (Germany, Turkey, UK, Italy, France, Spain, Portugal, Sweden, Denmark, Romania, Bulgaria, Ukraine, Ireland, Netherlands)
- Middle East/Africa: ~10 leads (UAE, Oman, Iran, Algeria, Nigeria, South Africa)
- Americas: ~10 leads (USA, Canada, Mexico, Brazil)
- Asia-Pacific: ~10 leads (India, Korea, Japan, Bangladesh)
- Other: ~5 leads (Israel, Australia)

LEAD QUALITY:
- Decision makers (CEOs, MDs, VPs, Directors)
- International buyers with purchasing authority
- Some already have specific machine inquiries
- Some have existing Machinecraft machines (upgrade potential)

MACHINE INTERESTS ALREADY EXPRESSED:
- PF1-C series: 3 leads (NPPF UAE, Al-Hilal Oman, LUX Algeria)
- PF1-X series: 3 leads (Ozgul Turkey, Global Mfg SA, LUX Algeria)
- PF1 general: 2 leads (Sazcilar Turkey, Lakatos Brazil)
- AM series: 1 lead (Vintec India)

TOTAL QUOTED VALUE: ~€800K+""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2025 Leads Overview",
        summary="K2025: 65 global leads, Europe/ME/Americas dominant, ~€800K quoted, decision makers",
        metadata={
            "topic": "k2025_overview",
            "event": "K-Show 2025",
            "total_leads": 65
        }
    ))

    # 2. European Leads
    items.append(KnowledgeItem(
        text="""K2025 - European Leads (High Priority)

GERMANY:
1. Schleicher GmbH
   - Contact: Ludwig Schleicher (CEO)
   - Email: ludwig.jun.schleicher@schleicher-gmbh.de
   - Website: www.schleicher-gmbh.de

2. W&K Industrietechnik
   - Contact: Yannik Reinl (Sales)
   - Email: y.reinl@wk-industrietechnik.de
   - Website: www.wk-industrietechnik.de

3. RPC
   - Contact: Dominik Weiten (Sales)
   - Email: dominik.weiten@rpc-group.de
   - Website: www.rpc-group.de

TURKEY (Strong Market):
1. Sazcilar
   - Contact: Eray Turkyimaz (Business Dev Manager)
   - Email: eray.turkyilmaz@sazcilar.com.tr
   - Website: www.sazcilar.com.tr
   - Interest: PF1
   - Note: Has 2 old Frimo vacuum forming machines

2. Formic Plastic
   - Contact: Ufuk Kartal (General Manager)
   - Email: ufukkartal@formicplastic.com
   - Website: www.formicplastic.com

3. Ozgul Plastik
   - Contact: Serdar Gulmez
   - Interest: PF1-X-5028
   - Price: €500K
   - Note: Large format requirement

4. Apesan
   - Contact: Burak (CEO)
   - Email: burak@apesan.com.tr

UK:
1. Palram
   - Contact: Garry Turley
   - Email: gturley@palram.com

2. Corex Plastics
   - Contact: Andy Lovett
   - Email: andy@corexplastics.co.uk

FRANCE:
1. Molding France
   - Contact: Alexandre Morgan (President)
   - Email: a.morgan@molding-france.com
   - Website: www.molding-france.com

ITALY:
1. Europlex
   - Email: grouppoeuroplex@pec.it

SPAIN:
1. Bermaq
   - Contact: Marc Canudas (CEO)
   - Email: mcanudas@bermaq.com

2. Martinez Inigo SA
   - Contact: Alfonso Martinez
   - Note: Connected with Bermaq

OTHERS:
- Bulgaria: Mouse (Plamen Stoykov, CEO)
- Ukraine: All Comp (Mehmet Yilmaz)
- Romania: Bright Distribution (George Niculcea)
- Sweden: Anatomic SITT (Krister, COO)
- Denmark: Vink Moulding (Lars Tropp)
- Portugal: Forma3D (Eduardo Pinto, CEO)
- Ireland: Donite (Stephen Kissick), Moulding Technologies (Patrick Tiernan)
- Netherlands: Baader Food, Polyplastics B.V""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2025 European Leads",
        summary="Europe: Germany, Turkey (4 leads incl €500K PF1-X), UK, France, Spain - key markets",
        metadata={
            "topic": "european_leads",
            "region": "Europe",
            "lead_count": 30
        }
    ))

    # 3. Middle East & Africa Leads
    items.append(KnowledgeItem(
        text="""K2025 - Middle East & Africa Leads

UAE:
1. NPPF Dubai
   - Contact: Mohammad Al Saghir (General Manager)
   - Email: m.alsaghir@nppfdubai.ae
   - Website: www.nppfdubai.com
   - Interest: PF1-C-2412
   - Note: Active inquiry

2. Al Bassam
   - Contact: Dr. Souheil M. Al Bassam (MD)
   - Email: suhail@albassam.ae
   - Interest: Basic pneumatic machine for shower trays and bathtub
   - Note: Entry-level requirement

OMAN:
1. Al-Hilal Industrial Group
   - Contact: Zakaria Al Kindi (CEO)
   - Email: zakaria@hilalgroup.com
   - Website: www.hilalgroup.com
   - Interest: PF1-C-2012
   - Price: $65K quoted
   - Note: Has 20-year old Machinecraft machine! Bathtub 1.2m x 2m
   - IMPORTANT: Existing customer - upgrade opportunity

IRAN:
1. Saaf Film
   - Contact: Ashgar Rezapour (Member of Board)
   - Email: rezapour@saaf-film.com
   - Website: www.saaf-film.com

ALGERIA:
1. Master Focus
   - Contact: Nassim Lounis (Sales Manager)
   - Email: sales@masterfocus.dz
   - Website: www.masterfocus.dz
   - Application: Shower Tray

2. LUX Pump Comp
   - Contact: Karim Iddir (Manager)
   - Email: sarlluxpump@hotmail.com
   - Interest: PF1-X-1210 AND PF1-C-1210
   - Price: €170K + €50K quoted
   - Application: Shower trays and thermoformed sink

NIGERIA:
1. OK Plast
   - Contact: Hussam Kandil (Managing Director)
   - Email: hussam.kandil@okplastng.com
   - Website: www.okplast.com.ng

SOUTH AFRICA:
1. Global Manufacturing Solutions
   - Contact: Antony Chantler (Director)
   - Email: antony@global-ms.co.za
   - Interest: PF1-X-1210 and PF1-X-2020 (no auto-loader)
   - Note: Has 5 old Geiss machines
   - Action: Send video of Autoframe
   - Application: Convert tractor parts from GRP to thermo-plastic""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2025 ME Africa Leads",
        summary="ME/Africa: Al-Hilal (existing customer!), NPPF, LUX (€220K), Global Mfg SA - high potential",
        metadata={
            "topic": "me_africa_leads",
            "region": ["Middle East", "Africa"],
            "lead_count": 10
        }
    ))

    # 4. Americas Leads
    items.append(KnowledgeItem(
        text="""K2025 - Americas Leads

USA:
1. DUO Form
   - Contact: Austin Meadows (VP of Sales)
   - Email: ameadows@duoformplastics.com
   - Website: www.duoformplastics.com
   - Note: Major US thermoformer

2. Mayco International
   - Contact: Chris Heikkila
   - Note: Potential automotive supplier

CANADA:
1. Plas-tech
   - Contact: Mike Aube (Sales Manager)
   - Email: mike@plastechonline.com
   - Website: www.plastechonline.com

2. Woodbridge Group
   - Contact: Michel De Verteuil (Engineering Manager)
   - Email: michel_deverteuil@woodbridgegroup.com
   - Website: www.woodbridgegroup.com
   - Note: Major automotive foam/plastics supplier

3. Plasticom Inc
   - Contact: Craig Lobson (President)
   - Email: craiglobson@plasticominc.com

MEXICO:
1. Poly-Material
   - Contact: James Seo (CEO)
   - Email: james@poly-material.com
   - Website: www.poly-material.com
   - Application: HDPE 4mm transit trays, many sizes

2. Excel Nobleza Gaulapack
   - Contact: Miguel Angel Herrero
   - Email: miguel.herrero@excelnobleza.com.mx
   - Website: https://excelnobleza.com.mx

BRAZIL:
1. Lakatos
   - Contact: Roberto
   - Interest: PF1
   - Application: Was going to send inquiry for trunk liner
   - Note: Automotive application - follow up needed""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2025 Americas Leads",
        summary="Americas: DUO Form, Woodbridge (Tier-1), Lakatos Brazil (trunk liner) - NA expansion",
        metadata={
            "topic": "americas_leads",
            "region": "Americas",
            "lead_count": 10
        }
    ))

    # 5. Asia-Pacific Leads
    items.append(KnowledgeItem(
        text="""K2025 - Asia-Pacific Leads

INDIA:
1. Carris / Aquatech Tanks
   - Contact: Santih Jacob (Technical Director)
   - Email: sanithjacob@aquatechtanks.com
   - Website: www.aquatechtanks.com

2. Pranav Engineering Works
   - Contact: Uma Deshpande
   - Email: uma@pranavengg.com

3. Moksha Bobbins
   - Contact: Shreye
   - Email: shreye@mokshabobbins.com

4. Premier / Plasmotec
   - Contact: Anit Bhatia
   - Email: a.bhatia@plasmotec.com

5. MMT
   - Contact: Rajesh Kapila
   - Email: popmedia@mmtd.in

6. Vintec (Bangalore)
   - Contact: K Prasad (MD)
   - Interest: AM with press - Abhishek type
   - Note: Specific AM machine inquiry

KOREA:
1. LG Electronics
   - Contact: Minseok Kang (Sales Manager)
   - Email: minseok1.kang@lge.com
   - Website: www.lge.com
   - Note: Major electronics conglomerate - high potential

JAPAN:
1. Nagoya Jushi
   - Contact: Satoshi (COO)
   - Note: Potential OEM partner market

BANGLADESH:
1. Mir Group
   - Contact: Jahangir Haider
   - Email: jahangir.haider@mirgroup-bd.com

AUSTRALIA:
1. Vesco Plastics (Tasmania)
   - Contact: Cris

ISRAEL:
1. TwitoPlast
   - Contact: Amnon
   - Email: amnon@twitoplast.co.il""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2025 APAC Leads",
        summary="APAC: LG Electronics Korea (major), Nagoya Jushi Japan, 6 India leads, Vintec AM inquiry",
        metadata={
            "topic": "apac_leads",
            "region": "Asia-Pacific",
            "lead_count": 12
        }
    ))

    # 6. Hot Leads with Machine Interests
    items.append(KnowledgeItem(
        text="""K2025 - Hot Leads with Specific Machine Interests

HIGHEST PRIORITY (Quoted/Specific Interest):

1. Ozgul Plastik (Turkey)
   - Machine: PF1-X-5028
   - Price: €500,000
   - Contact: Serdar Gulmez
   - Note: Large format - premium deal

2. LUX Pump Comp (Algeria)
   - Machines: PF1-X-1210 + PF1-C-1210
   - Price: €170K + €50K = €220K total
   - Contact: Karim Iddir
   - Email: sarlluxpump@hotmail.com
   - Application: Shower trays, thermoformed sinks

3. Al-Hilal Industrial (Oman) - EXISTING CUSTOMER
   - Machine: PF1-C-2012
   - Price: $65K quoted
   - Contact: Zakaria Al Kindi (CEO)
   - Email: zakaria@hilalgroup.com
   - Note: Has 20-year old Machinecraft machine! Upgrade opportunity
   - Application: Bathtub 1.2m x 2m

4. NPPF Dubai (UAE)
   - Machine: PF1-C-2412
   - Contact: Mohammad Al Saghir (GM)
   - Email: m.alsaghir@nppfdubai.ae

5. Global Manufacturing Solutions (South Africa)
   - Machines: PF1-X-1210 + PF1-X-2020 (no auto-loader)
   - Contact: Antony Chantler
   - Email: antony@global-ms.co.za
   - Note: Has 5 old Geiss machines
   - Action: Send Autoframe video
   - Application: Tractor parts (GRP to thermoplastic conversion)

6. Sazcilar (Turkey)
   - Machine: PF1
   - Contact: Eray Turkyimaz
   - Email: eray.turkyilmaz@sazcilar.com.tr
   - Note: Has 2 old Frimo vacuum forming machines

7. Vintec (India)
   - Machine: AM with press (Abhishek type)
   - Contact: K Prasad (MD)
   - Location: Bangalore

8. Al Bassam (UAE)
   - Machine: Basic pneumatic for shower trays/bathtub
   - Contact: Dr. Souheil Al Bassam (MD)
   - Email: suhail@albassam.ae

TOTAL PIPELINE VALUE: ~€850K+

FOLLOW-UP ACTIONS:
- Al-Hilal: Priority - existing customer upgrade
- Ozgul: High value deal - personal attention
- LUX Algeria: Two-machine deal
- Global Mfg SA: Send Autoframe video immediately
- Sazcilar/Vintec: Replacement market""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2025 Hot Leads",
        summary="Hot leads: €850K+ pipeline, Al-Hilal existing customer, Ozgul €500K, LUX €220K",
        metadata={
            "topic": "hot_leads",
            "pipeline_value": "850K+ EUR",
            "lead_count": 8
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("K2025 Leads Ingestion (K-Show Germany)")
    print("Source: " + SOURCE_FILE)
    print("=" * 60)

    items = create_knowledge_items()

    print(f"\nCreated {len(items)} knowledge items:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.summary[:55]}...")

    ingestor = KnowledgeIngestor()
    results = ingestor.ingest_batch(items)

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
