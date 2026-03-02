#!/usr/bin/env python3
"""
Ingest K2022 Meetings - Trade Show Visitor Leads

77 visitors from K2022 trade show in Dusseldorf with machine interests,
size requirements, and quoted prices.

Source: K2022 Meetings.xlsx
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import directly from the module file
import importlib.util
spec = importlib.util.spec_from_file_location(
    "knowledge_ingestor",
    os.path.join(project_root, "openclaw/agents/ira/src/brain/knowledge_ingestor.py")
)
knowledge_ingestor_module = importlib.util.module_from_spec(spec)
sys.modules["knowledge_ingestor"] = knowledge_ingestor_module
spec.loader.exec_module(knowledge_ingestor_module)

KnowledgeIngestor = knowledge_ingestor_module.KnowledgeIngestor
KnowledgeItem = knowledge_ingestor_module.KnowledgeItem

SOURCE_FILE = "K2022 Meetings.xlsx"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from K2022 meetings."""
    items = []

    # 1. K2022 Meetings Overview
    items.append(KnowledgeItem(
        text="""K2022 Trade Show Meetings - Overview

EVENT: K2022, Dusseldorf, Germany (October 2022)
TOTAL VISITORS: 77 contacts
DATA: Machine interest, size requirements, prices quoted

MACHINE INTEREST BREAKDOWN:
- PF1 series: ~55 visitors (dominant)
- UNO series: ~8 visitors
- AM series: ~5 visitors
- FCS series: ~3 visitors
- Router: ~2 visitors
- Others: RT, SPM

GEOGRAPHIC DISTRIBUTION:
- Europe: ~45 (Germany, Netherlands, France, UK, Italy, etc.)
- Middle East: ~10 (Israel, Egypt, Jordan, KSA, Iran)
- Americas: ~8 (USA, Brazil, Argentina, Chile)
- Asia-Pacific: ~5 (Australia, India)
- Other: ~9 (Uzbekistan, Russia, Faroe Islands, etc.)

QUOTES PROVIDED:
- Multiple quotes in €90K-€330K range
- Some with specific pricing
- Several follow-ups pending

KEY APPLICATIONS MENTIONED:
- Bathtubs, shower trays
- Bus/LCV interiors
- Car mats
- Pallets
- Golf cart parts
- Heat exchangers
- PC shields""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2022 Overview",
        summary="K2022: 77 visitors, PF1 dominant (55), Europe 45, ME 10, Americas 8; €90K-€330K quotes",
        metadata={
            "topic": "k2022_overview",
            "event": "K2022",
            "total_leads": 77
        }
    ))

    # 2. European Leads
    items.append(KnowledgeItem(
        text="""K2022 Meetings - European Leads

GERMANY (Key Market):
1. Robert Minich - Plastforma
   - Email: r.minich@plastforma.de
   - Interest: PF1
   - Note: Illig customer

2. Dennis Gabler - Singlepalst
   - Email: info@singlepalst.de
   - Interest: PF1, 1.25 x 2.5m
   - Note: Illig customer
   - Cross-ref: European Sales, LLM

3. Andre Zimmler / Niklas Willecke - Centrotherm
   - Email: andre.zimmler@centrotherm.com
   - Interest: PF1
   - Application: Heat exchanger
   - Note: Will send RFQ

4. Steffen Plinke - Continental
   - Email: steffen.plinke@continental.com
   - Interest: UNO
   - Note: Tech center China

5. Moritz Bittner - Formary
   - Email: moritz.bittner@formary.de
   - Interest: Thermoformer Platform

6. Wolfgang Bohriner - W3 GmbH
   - Email: wolfgang.boehringer@w3-gmbh.com
   - Interest: PF1
   - Note: Illig customer, visit after Soehner

7. Theo Doll - Soehner
   - Email: T.Doll@soehner.de
   - Interest: PF1
   - Cross-ref: LLM (Score 100)

NETHERLANDS:
8. Chris Chrispijn - Batelaan
   - Email: c.chrispijn@batelaan.nl
   - Cross-ref: European Sales, LLM (Score 96)

9. Henk Wierenga - Beutech
   - Email: henkwierenga@beutech.nl
   - Interest: PF1, 1.2 x 1.2m

10. Michel Berkum - Visscher-Caravelle
    - Email: michielvanberkum@visscher-caravelle.nl
    - Interest: PF1
    - Application: Car mats
    - Cross-ref: European Sales, LLM

11. Chris Mulder - VDL Wientjes Roden
    - Email: c.mulder@vdlwientjesroden.nl
    - Interest: PF1
    - Cross-ref: European Sales

FRANCE:
12. Thierry D'Allard - Stylmonde
    - Email: tdallard@stylmonde.com
    - Interest: UNO

13. Philippe Veyrenche - Alphaform
    - Email: pveyrenche@alphaform.fr
    - Cross-ref: European Sales

14. Nadine Vidal - VDM Metals
    - Email: eric.vidal@vdm-metals.com
    - Interest: PF1, 2.2 x 2.2m

15. Cedric Morange - Formage Plastique
    - Email: cedric.morange@formage-plastique.com
    - Interest: PF1
    - Note: Knows Plastochim

UK/IRELAND:
16. John Cooper - Seaborne
    - Email: johncooper@seaborne.cz
    - Interest: UNO, 800x1000
    - Price: €90K
    - Note: Has 12 x Geiss machines
    - Cross-ref: LLM

17. Michael/Diarmuid/Stephen - Donite (Ireland)
    - Emails: michael@donite.com, diarmund@donite.com, stephen@donite.com
    - Interest: UNO
    - Notes: Handle orientation, tool table holes

18. Nick Doouss - Eastbrook Co
    - Email: nick@eastbrookco.com
    - Interest: PF1, 2 x 2m
    - Price: €310K
    - Application: Bathtubs""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2022 European Leads",
        summary="K2022 Europe: Germany (Soehner, Continental, Centrotherm), NL (Batelaan, VDL), UK (€310K bathtubs)",
        metadata={
            "topic": "k2022_europe",
            "region": "Europe",
            "lead_count": 18
        }
    ))

    # 3. More European & Nordic Leads
    items.append(KnowledgeItem(
        text="""K2022 Meetings - More European & Nordic Leads

PORTUGAL:
1. Eduardo Pinto - Forma3D
   - Email: pinto@forma3d.pt
   - Interest: PF1, 1250 x 1050
   - Note: Roll Feeder + Uni Frame
   - Cross-ref: European Sales, LLM, K2025

ITALY:
2. Andrea Zonta - Self Group
   - Email: andrea.zonta@selfgroup.com
   - Note: Tech Day India interest

3. Massimilano Bertino - Production SPA
   - Email: mbertino@productionspa.it
   - Interest: PF1

SPAIN:
4. Marc Canudas - Bermaq
   - Email: bermaq@bermaq.com
   - Interest: PF1
   - Note: Wants to be representative
   - Cross-ref: K2025

BELGIUM:
5. Jean Delentre - Plastisart
   - Email: jf.deltenre@plastisart.com
   - Interest: PF1
   - Cross-ref: European Sales

POLAND:
6. Tomasz Chojnowski - Maxform
   - Email: tomasz.chojnowski@maxform.pl
   - Interest: PF1, 1 x 2m
   - Price: €190K

CZECH REPUBLIC:
7. Pavel Votruba - Durotherm
   - Email: pavel.votruba@durotherm.cz
   - Interest: PF1, 2.5 x 2.5m
   - Price: €300K
   - Note: Visit to Thermic Energy
   - Cross-ref: European Sales, LLM

HUNGARY:
8. Zoltán Táborosi-Gál - Pro-Form
   - Email: zoltan.taborosi@pro-form.hu
   - Interest: PF1, 1.5 x 1.5m
   - Price: €159K
   - Status: Quote sent

ROMANIA:
9. Tucra Andrei - Eco-Tad
   - Email: office@eco-tad.ro
   - Interest: PF1, 2x3 / 3x3m
   - Application: Roto moulded → vac forming conversion

ESTONIA:
10. Martin Kalmet - Plastik.ee
    - Email: martin@plastik.ee
    - Interest: UNO

LITHUANIA:
11. Arturas - Ronika
    - Email: arturuas@ronika.lt
    - Interest: PF1
    - Application: LFI parts
    - Cross-ref: LLM

SWEDEN:
12. Krister Ericsson - Anatomic SITT
    - Email: krister@anatomicsitt.com
    - Interest: PF1
    - Cross-ref: K2025

DENMARK:
13. Michael Bertelsen - DHP
    - Email: mib@dhp.dk
    - Interest: PF1
    - Note: Gibo sister company

FINLAND:
14. Mikko Ranne - Motoseal
    - Email: mikko.ranne@motoseal.fi
    - Interest: PF1, 1 x 2m x 600
    - Note: Autoloader + heater options
    - Cross-ref: LLM

FAROE ISLANDS:
15. Arni Skaale / Ragnar Sundstein - Look North
    - Email: arni@looknorth.fo
    - Interest: PF1, 1 x 2m
    - Note: Uni Frame, Formech client""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2022 More Europe Nordic",
        summary="K2022 Europe/Nordic: Forma3D PT, Maxform PL €190K, Durotherm CZ €300K, Pro-Form HU €159K",
        metadata={
            "topic": "k2022_europe_nordic",
            "region": ["Europe", "Nordic"],
            "lead_count": 15
        }
    ))

    # 4. Middle East & Africa Leads
    items.append(KnowledgeItem(
        text="""K2022 Meetings - Middle East & Africa Leads

EGYPT:
1. Adel Hassan / Medhat Mahmoud - Duravit
   - Email: adel.hassan@eg.duravit.com
   - Interest: PF1, 2 x 2.5m PRO
   - Application: Tubs (bathtubs)
   - Note: Major sanitary brand

2. Amr Fetoh - Polyeeplast
   - Email: info@polyeeplast.com
   - Interest: PF1
   - Application: PC Shield
   - Cross-ref: LLM

ISRAEL (Strong Market):
3. Menachem Grinshpan - Polycart
   - Email: menachem@polycartt.com
   - Interest: PF1, 4.8 x 2.5 x 1 PRO
   - Note: Large format

4. Uzi Kelberman - Florma
   - Email: uzik@florma.co.il
   - Interest: PF1, 1.4 x 1.4m
   - Note: 25mm deep, PS 0.7, single heater
   - Status: Quote sent
   - Cross-ref: LLM (Score 56)

5. Rotem Arbel - Dhardar
   - Email: info.dhardar@gmail.com
   - Interest: PF1, 1.2 x 2.2m
   - Price: €280K
   - Note: Asked for lower price, pneumatic hand stacking

6. Dolev Hadar
   - Email: dolevhadar2013@gmail.com
   - Interest: PF1 XXL

SAUDI ARABIA:
7. Mohammed Alodan - Suncafe
   - Email: mohammedalodan@suncafe.com.sa
   - Interest: FCS
   - Application: 4-station FCS, glass, lids

JORDAN:
8. Imad Mawalawi - Mawlawi Group
   - Email: imad@mawlawigroup.com
   - Interest: AM

IRAN:
9. S. Ghelmani - Penda Plastic
   - Email: info@pendaplastic.com
   - Interest: PF1, 1.5 x 3m
   - Application: HDPE pallet, 2 cavity, 1300/day
   - Note: Autoloader, no Uni frame

10. Ali Tavakoli
    - Email: amt657@yahoo.com
    - Interest: FCS
    - Application: PET

QATAR:
11. Suraj Raghavan - Rafaele Plastic
    - Email: rafaeleplastic01@gmail.com""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2022 Middle East",
        summary="K2022 ME: Duravit Egypt (tubs), Israel (4 leads incl €280K), KSA FCS, Iran HDPE pallets",
        metadata={
            "topic": "k2022_middle_east",
            "region": "Middle East",
            "lead_count": 11
        }
    ))

    # 5. Americas & Asia-Pacific Leads
    items.append(KnowledgeItem(
        text="""K2022 Meetings - Americas & Asia-Pacific Leads

USA:
1. Matt Shade - GS Engineering
   - Email: mshade@gsengineering.net
   - Interest: PF1, 1.2 x 2m

2. Chris Matzke - Nike
   - Email: chris.matzke@nike.com
   - Interest: PF1 Twin, 17' x 17'
   - Note: Very large format for Nike

BRAZIL:
3. Patrick Rasia - Elri
   - Email: patrick@elri.com.br
   - Interest: PF1

4. Miguel Roca - Barbi
   - Email: mbazan@barbi.ind.br
   - Interest: Router

ARGENTINA:
5. Fernando Maceri - Interforming
   - Email: fimaceri@interforming.com.ar
   - Interest: PF1, 2 x 2 / 4.8 x 2.5m

CHILE:
6. Michael Lost - Socomisch
   - Email: mschmid@socomisch.cl
   - Interest: AM, 500x600
   - Price: €30K + €10K

AUSTRALIA:
7. Jim Biberias - VacMould Displays
   - Email: jbiberias@vacmoulddisplays.com.au
   - Interest: PF1, 2.7 x 1.5m PRO + 1 x 1.5m LITE
   - Price: €330K + €140K
   - Cross-ref: LLM (User Priority)

INDIA:
8. Manish Saraf - Paracoat
   - Email: manish@paracoat.com
   - Interest: PF1
   - Note: Visit to Bhiwadi

9. Pawandeep Anand - Anbros
   - Email: psa@anbros.com
   - Interest: PF1

TURKEY:
10. Horvath Zsolt - Tartay Haz
    - Email: horvath.zsolt@tartayhaz.hu
    - Interest: PF1
    - Application: Interior/Exterior of Bus, LFI

11. Asli Dalgic - HPA Plastik
    - Email: asli.dalgic@hpaplastik.com
    - Interest: PF1
    - Application: Golf cart parts

UZBEKISTAN:
12. Oziq Ovaqat
    - Email: utuganbekov@yahoo.com
    - Interest: AM + Press
    - Price: €30K + €10K

RUSSIA:
13. Evgeny Sinyagin - Oldeng
    - Email: ceo@oldeng.ru
    - Interest: PF1 XXL, 4.8 x 2.5m

CROATIA:
14. Hajrudin Hadzidedic - Inova Odzak
    - Email: inova.odzak@gmail.com
    - Interest: RT, 1.5 x 1.5m
    - Note: Shipping cost included""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2022 Americas APAC",
        summary="K2022 Americas/APAC: Nike USA (17'x17'), VacMould AU €470K, Argentina, Brazil, India visits",
        metadata={
            "topic": "k2022_americas_apac",
            "region": ["Americas", "APAC"],
            "lead_count": 14
        }
    ))

    # 6. Hot Leads with Quotes
    items.append(KnowledgeItem(
        text="""K2022 Meetings - Hot Leads with Quotes/Pricing

QUOTED DEALS (High Priority Follow-up):

1. VacMould Displays (Australia) - €470K TOTAL
   - Contact: Jim Biberias
   - PF1 PRO 2.7 x 1.5m: €330K
   - PF1 LITE 1 x 1.5m: €140K
   - Cross-ref: LLM User Priority

2. Eastbrook Co (UK) - €310K
   - Contact: Nick Doouss
   - PF1 2 x 2m
   - Application: Bathtubs

3. Durotherm (Czech) - €300K
   - Contact: Pavel Votruba
   - PF1 2.5 x 2.5m
   - Note: Visit to Thermic Energy

4. Dhardar (Israel) - €280K
   - Contact: Rotem Arbel
   - PF1 1.2 x 2.2m
   - Note: Price negotiation

5. Maxform (Poland) - €190K
   - Contact: Tomasz Chojnowski
   - PF1 1 x 2m

6. Pro-Form (Hungary) - €159K
   - Contact: Zoltán Táborosi-Gál
   - PF1 1.5 x 1.5m
   - Status: QUOTE SENT

7. Seaborne (UK/Czech) - €90K
   - Contact: John Cooper
   - UNO 800x1000
   - Note: Has 12 Geiss machines

8. Socomisch (Chile) - €40K
   - AM 500x600: €30K + €10K press

9. Uzbekistan - €40K
   - AM + Press: €30K + €10K

TOTAL QUOTED PIPELINE: ~€1.9M+

STRATEGIC NOTES:
- Multiple Illig customers interested (Plastforma, Singlepalst, W3)
- Nike interested in very large format (17' x 17')
- Bermaq wants to be representative (Spain)
- Several Geiss replacement opportunities""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2022 Hot Leads",
        summary="K2022 quoted: VacMould €470K, Eastbrook €310K, Durotherm €300K, total pipeline ~€1.9M+",
        metadata={
            "topic": "k2022_hot_leads",
            "total_pipeline": "1.9M EUR",
            "lead_count": 9
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("K2022 Meetings Leads Ingestion")
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
