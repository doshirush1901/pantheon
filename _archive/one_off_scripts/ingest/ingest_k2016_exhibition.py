#!/usr/bin/env python3
"""
Ingest K2016 Exhibition Inquiry Data

73 inquiries from K2016 trade show in Dusseldorf with regional analysis.
Historical data useful for understanding long-term prospect relationships.

Source: K2016 - Data for Exhibition Inquiry & Analysis.xlsx
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

SOURCE_FILE = "K2016 - Data for Exhibition Inquiry & Analysis.xlsx"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from K2016 exhibition data."""
    items = []

    # 1. K2016 Overview & Analysis
    items.append(KnowledgeItem(
        text="""K2016 Exhibition Inquiry Data - Overview & Analysis

EVENT: K2016, Dusseldorf, Germany (October 2016)
TOTAL INQUIRIES: 73 contacts
DATA: Customer inquiries with machine interest, applications, and sizes

REGIONAL DISTRIBUTION (Top Markets):
1. India: 16 inquiries (largest)
2. Middle East: 11 (UAE 5, Jordan 3, Algeria 4)
3. Europe: 23 (Germany 3, Hungary 3, Sweden 3, Belgium 2, Portugal 2, etc.)
4. Africa: 7 (South Africa 2, Kenya 1, Nigeria 1)
5. Australia/East Asia: 2
6. South America: 2 (Brazil 1, Peru 1)

MACHINE INTEREST:
- PF1: 43 inquiries (59% - dominant)
- INLINE: 17 inquiries (23%)
- AM: 4 inquiries (5%)

APPLICATION CATEGORIES:
- Automotive: 5
- EPS/Pallets: 5
- Bathtubs: 4
- Food trays/Clamshells: 3
- Grape boxes: 3
- Lids: 2
- Skylights: 2
- Machine covers: 2
- Luggage: 1
- Bus seats: 1
- Snow pushers: 1

HISTORICAL SIGNIFICANCE:
- Many K2016 contacts became long-term prospects
- Several appear in K2022, K2025, and other lists
- Shows evolution of customer relationships over 10 years""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2016 Overview",
        summary="K2016: 73 inquiries, India 16, Europe 23, ME 11; PF1 43 (59%), INLINE 17; 10yr prospect history",
        metadata={
            "topic": "k2016_overview",
            "event": "K2016",
            "total_leads": 73
        }
    ))

    # 2. India Market Leads
    items.append(KnowledgeItem(
        text="""K2016 - India Market Leads (16 contacts)

1. Nitin Sanghi - Pragati Plast
   - Email: nitin@pragatiplast.com
   - Web: www.pragatiplast.com

2. Pritul Jain
   - Email: pritul@pritul.com
   - Interest: PF1
   - Application: Machine Cover

3. Brijesh Tilara - Tilara Polyplast
   - Email: brijesh@tilarapolyplast.com
   - Web: www.tilaraployplast.com

4. Harish Doshi - Biopac India
   - Email: hdoshi@biopacindia.com
   - Web: www.biopacindia.com

5. Vishal - Rhyfeel
   - Email: info@rhyfeel.com
   - Interest: PF1, 1100x1100
   - Application: EPS Pallet

6. Anurag - RGP Moulds
   - Email: anurag.rfm@gmail.com
   - Interest: PF1
   - Web: www.rgp-moulds.com

7. Ketan - Atlantic Polymers
   - Email: atlanticpolymers2008@gmail.com
   - Interest: PF1
   - Application: Paver block

8. Divyesh - Pinakin Plastoforming
   - Email: divyesh@pinakinplastoforming.com
   - Interest: INLINE
   - Web: www.pinakinplastoforming.com

9. Vijay Nehete - Ukay Industries
   - Email: nehete.vijay@ukayindustries.net
   - Interest: PF1, 1500x2000
   - Application: Automotive, with Autoloader
   - Cross-ref: Diamond Mine, PlastIndia

10. Prakash - Prakash Technoplast
    - Email: pmv@prakashtechnoplast.com
    - Interest: PF1
    - Application: Automotive

11. Reddy - Vintec Industries
    - Email: kpr@vintecind.com
    - Interest: INLINE
    - Application: Toy Trays
    - Cross-ref: Diamond Mine (K Prasad)

12. Wassan - Hyco
    - Email: hemantwassan@hyco.co.in
    - Interest: PF1
    - Application: Automats
    - Status: Already quoted
    - Cross-ref: Diamond Mine

13. Manmohan - Prince Polypaint
    - Email: princepolypaints@gmail.com
    - Interest: PF1
    - Application: Lamp/Split

14. Sainath - Unipet Industries
    - Email: sainath@unipetindustries.com
    - Web: www.unipetindustries.com""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2016 India Leads",
        summary="K2016 India: 16 leads, Ukay (automotive), Vintec, Hyco (quoted), Pragati, Biopac, Pinakin",
        metadata={
            "topic": "k2016_india",
            "region": "India",
            "lead_count": 16
        }
    ))

    # 3. Middle East & Africa Leads
    items.append(KnowledgeItem(
        text="""K2016 - Middle East & Africa Leads

UAE (5 contacts):
1. Bassam - Al Bassam
   - Email: suhail@albassam.ae
   - Interest: PF1, 1000x2000
   - Application: Panel
   - Price: ~€50,000
   - Cross-ref: K2025 (still active!)

2. Abhilash - SPT
   - Email: abhilash@sptme.com
   - Interest: PF1
   - Application: EPS Pallet

3. Sagir - NPPF Dubai
   - Email: m.alsagir@nppfdubai.ae
   - Interest: PF1, 1000x1200
   - Application: EPS Pallet, HIPS, antistatic
   - Cross-ref: K2025 (still active!)

4. Iham
   - Interest: INLINE, 500x600
   - Application: Containers
   - Price: 3-station €1.1K, servo €1.5K

5. Seyed - Razak Chemie
   - Email: info@razakchemie.com
   - Interest: PF1
   - Application: EPS Pallet

JORDAN (3 contacts):
6. Kamel - Al Hussam Pack
   - Email: ceo@alhuaampack.com
   - Web: www.alhussampack.com

7. Khadeer - Alsafa Co
   - Email: gabbar.khdeer@alsafaco.com
   - Interest: PF1
   - Application: Luggage

ALGERIA (4 contacts):
8. Musthapa - Plastique 3000
   - Email: info@plastique3000.com
   - Web: www.plastique3000.com

9. Mouzaia
   - Email: belkacemikhelil@yahoo.fr
   - Interest: INLINE
   - Application: Boxes

SOUTH AFRICA (2 contacts):
10. Tom - Neupack
    - Email: tom@neupack.co.za
    - Interest: PF1, INLINE, AM
    - Application: PoP (Point of Purchase)
    - Note: Has Illig & Geiss thick sheet machines

11. Raeed
    - Email: mavalane@gmail.com
    - Interest: INLINE, AM
    - Application: Grape Clamshells
    - Note: Visiting Mumbai, has PET line from RR

KENYA:
12. Sanjay - Blow Plast Kenya
    - Email: sanjay@blowplastkenya.com
    - Interest: PF1
    - Application: EPS Pallet
    - Web: www.thermopackkenya.com

SAUDI ARABIA:
13. Ihab - STP
    - Email: i.hamdy@stp.com.sa
    - Interest: PF1

EGYPT:
14. Mohammed - Getco
    - Email: info@getco-eg.com
    - Note: Will visit Mumbai""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2016 Middle East Africa",
        summary="K2016 ME/Africa: Al Bassam €50K, NPPF (both still active K2025!), Neupack SA (has Illig/Geiss)",
        metadata={
            "topic": "k2016_middle_east_africa",
            "region": ["Middle East", "Africa"],
            "lead_count": 14
        }
    ))

    # 4. Europe Leads
    items.append(KnowledgeItem(
        text="""K2016 - Europe Leads (23 contacts)

GERMANY:
1. Hans Buehler - Ben Plastic
   - Email: hr.buehler@ben-plastic.com

HUNGARY:
2. Lazlo - Pro-Form
   - Email: hl@pro-form.hu
   - Interest: PF1
   - Web: www.pro-form.hu
   - Cross-ref: K2022 (Zoltán, €159K quote)

SWEDEN:
3. Goran Bjarle - Stegoplast
   - Email: goran.bjarle@stegoplast.se
   - Interest: PF1
   - Note: Past Customer
   - Cross-ref: European Sales, K2022

4. Ayub Adam - Arlaplast
   - Email: ayub.adam@arlaplast.com
   - Web: www.alraplast.com

FINLAND:
5. Mikko Ranne - Motoseal
   - Email: mikko.ranne@motoseal.fi
   - Interest: PF1, 1000x2000
   - Application: Snow pushers, trolleys
   - Price: 700 deep €1.5K, 500 deep €1.2K, servo mould
   - Cross-ref: K2022, LLM

BELGIUM:
6. Jaques - Imatex
   - Email: info@imatex.be
   - Interest: PF1
   - Note: Past Customer

PORTUGAL:
7. Pedro Araujo - Polisport
   - Email: pedro.araujo@polisport.com
   - Interest: PF1

8. Zacarias Cavaco - Fibraline
   - Email: zacariascavaco@fibraline.pt
   - Interest: PF1, 2500x3000
   - Application: Car Parts
   - Price: €1.5K quoted

ITALY:
9. Imer - Technoform
   - Email: technoform@ittc.net
   - Interest: PF1, 1000x1500
   - Application: Shower Panels

AUSTRIA:
10. Christa Hauser - Novavert
    - Email: novavert@aon.at
    - Interest: PF1, 1200x2000
    - Application: Skylight

ALBANIA:
11. Bensik Zhapa - Bendish
    - Email: info@bendishpk.al
    - Interest: PF1
    - Application: Bathtubs

12. Krenor
    - Email: tomialb@hotmail.com
    - Interest: INLINE
    - Application: Trays

BULGARIA:
13. Nenko - Ecopro
    - Email: ecopro@abv.bg
    - Interest: PF1, 2000x2000
    - Application: Well Covers

DENMARK:
14. Thomas Rossen - Selandia
    - Email: rossen@selandiaplast.dk
    - Interest: INLINE
    - Application: Food containers

POLAND:
15. Olszewski
    - Email: olsz1@op.pl
    - Interest: PF1

TURKEY:
16. Sabri - Akplast
    - Email: sabri@akplast.com
    - Interest: PF1, 1200x1400
    - Application: Bus seat

IRAN:
17. Naser
    - Interest: PF1, 2000x2500
    - Application: Bathtubs
    - Price: $1.3K quoted""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2016 Europe Leads",
        summary="K2016 Europe: Pro-Form HU (→K2022), Stegoplast SE (past customer), Motoseal FI (→K2022,LLM)",
        metadata={
            "topic": "k2016_europe",
            "region": "Europe",
            "lead_count": 17
        }
    ))

    # 5. Americas & Asia-Pacific Leads
    items.append(KnowledgeItem(
        text="""K2016 - Americas & Asia-Pacific Leads

USA:
1. Mandip Ghai - Fabri-Kal
   - Email: mghai@fabri-kal.com
   - Interest: INLINE
   - Application: Cup
   - Note: Major US thermoformer

BRAZIL:
2. Paulo - Electro Forming
   - Email: paulo@electro-forming.com
   - Web: www.electro-forming.com

ECUADOR:
3. Zavier - Resomak
   - Email: ventasc@resomak.com
   - Interest: PF1

PERU:
4. Luis - Melaform
   - Email: lamb-62@hotmail.com
   - Web: www.melaform.com.pe

AUSTRALIA:
5. Bipin - Omega Packaging
   - Email: bipin@omegapakaging.com.au
   - Interest: INLINE
   - Application: Lids (97 and 117 dia)
   - Web: piberpackaging.com.au

INDONESIA:
6. William - Wings Corp
   - Email: meliana.kornelius@wingscorp.com
   - Interest: INLINE
   - Note: 300 pcs/hr requirement
   - Web: www.wingscorp.com

7. Benhein - Matahari
   - Email: benhein@mataharipackaging.com
   - Interest: INLINE
   - Application: Food Tray, Grape box
   - Price: 100K EUR quoted

SINGAPORE:
8. Low - Welteq
   - Email: lowsb@welteq.com
   - Web: welteq.com

PAKISTAN:
9. Tahir - Machpart
   - Email: info@machpart.com
   - Interest: AM, INLINE
   - Application: Orange Tray
   - Note: 10,000 pcs/day requirement

OMAN:
10. Saif - Bin Salim Trading
    - Email: saif@binsalim.com
    - Interest: PF1
    - Note: 3 year warranty requested

NIGERIA:
11. Maxwell - Plastimax
    - Email: maxwell@plastimaxng.com
    - Interest: AM + Press
    - Note: Has Geiss machine""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2016 Americas APAC",
        summary="K2016 Americas/APAC: Fabri-Kal USA (major), Wings Indonesia, Matahari €100K, Nigeria (has Geiss)",
        metadata={
            "topic": "k2016_americas_apac",
            "region": ["Americas", "APAC"],
            "lead_count": 11
        }
    ))

    # 6. Long-term Prospect Tracking
    items.append(KnowledgeItem(
        text="""K2016 - Long-term Prospect Relationships (10 Year Tracking)

PROSPECTS STILL ACTIVE (K2016 → K2022/K2025):

1. Al Bassam (UAE)
   - K2016: €50K panel quote
   - K2025: Still inquiring for shower trays/bathtubs
   - 9 years of engagement!

2. NPPF Dubai (UAE)
   - K2016: EPS Pallet inquiry
   - K2025: PF1-C-2412 interest
   - Continuous relationship

3. Pro-Form Hungary
   - K2016: Lazlo inquiry
   - K2022: Zoltán €159K quote sent
   - Active customer development

4. Stegoplast Sweden
   - K2016: Past customer (Goran)
   - K2022: Follow-up
   - European Sales list
   - LLM warm lead

5. Motoseal Finland
   - K2016: Mikko, snow pushers
   - K2022: Continued interest
   - LLM warm lead

6. Ukay Industries India
   - K2016: Vijay, automotive
   - PlastIndia 2023: Active
   - Diamond Mine: Listed

7. Vintec India
   - K2016: Reddy, toy trays
   - Diamond Mine: AM interest
   - Long-term prospect

8. Hyco India
   - K2016: Already quoted
   - Diamond Mine: ABS, TPE
   - Continuous engagement

KEY LEARNING:
- Average conversion timeline: 3-7 years for large equipment
- Persistence pays off - many K2016 prospects became K2022/K2025 customers
- Trade show presence builds long-term brand recognition
- Cross-reference new inquiries with historical data""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="K2016 Long-term Tracking",
        summary="10yr tracking: Al Bassam, NPPF, Pro-Form, Stegoplast, Motoseal still active from K2016",
        metadata={
            "topic": "k2016_longterm",
            "years_tracked": 10,
            "active_prospects": 8
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("K2016 Exhibition Data Ingestion")
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
