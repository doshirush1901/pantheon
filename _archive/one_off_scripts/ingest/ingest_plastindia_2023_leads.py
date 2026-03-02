#!/usr/bin/env python3
"""
Ingest PlastIndia 2023 Visitor List - India Leads Database

69 potential/current client contacts from PlastIndia 2023 trade show.
Segmented by industry and region for targeted sales outreach.

Source: PlastIndia 2023 Visitor List.xlsx
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "PlastIndia 2023 Visitor List.xlsx"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the PlastIndia leads."""
    items = []

    # 1. Leads Database Overview
    items.append(KnowledgeItem(
        text="""PlastIndia 2023 Visitor List - Leads Overview

SOURCE: PlastIndia 2023 Trade Show
TOTAL LEADS: 69 contacts
MARKET: India (primary) + Middle East
DATA FIELDS: Name, Company, Mobile, Email, Location, Website

INDUSTRY SEGMENTS REPRESENTED:
1. Automotive & Auto Components (~25 leads)
2. Packaging & Containers (~10 leads)
3. Composites & FRP (~8 leads)
4. Consumer Products (~8 leads)
5. Industrial Products (~10 leads)
6. EV & New Energy (~5 leads)
7. Others (~3 leads)

GEOGRAPHIC DISTRIBUTION:
- NCR (Delhi/Faridabad/Gurgaon/Noida): ~25 leads
- Maharashtra (Mumbai/Pune/Nashik): ~15 leads
- Gujarat (Ahmedabad/Rajkot): ~8 leads
- Karnataka (Bangalore): ~6 leads
- Tamil Nadu (Chennai/Trichy): ~4 leads
- Madhya Pradesh (Indore/Pithampur): ~3 leads
- Haryana (Sonepat/Manesar): ~5 leads
- International (Oman/Qatar): ~3 leads

LEAD QUALITY:
- Direct contact details (mobile + email)
- Decision makers / senior roles
- Visited Machinecraft booth at PlastIndia
- Expressed interest in thermoforming""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="PlastIndia 2023 Leads",
        summary="PlastIndia 2023: 69 India leads, 7 segments, NCR/Maharashtra/Gujarat dominant, booth visitors",
        metadata={
            "topic": "leads_overview",
            "total_leads": 69,
            "event": "PlastIndia 2023"
        }
    ))

    # 2. Automotive & Auto Components Leads
    items.append(KnowledgeItem(
        text="""PlastIndia 2023 - Automotive & Auto Components Leads

HIGH PRIORITY AUTOMOTIVE LEADS:

1. IAC (International Automotive Components)
   - Contact: Rushikesh Purkar
   - Mobile: 919561087954
   - Email: rushikesh.purkar@iacgroup.com
   - Location: Baner, Pune (MH)
   - Note: Global Tier-1, IMG machine customer prospect

2. Pinnacle Industries
   - Contact: Dhiraj Suryawanshi
   - Mobile: 919503362300
   - Email: dsuryawanshi@pinnacleindustries.com
   - Location: Pithampur, MP
   - Website: www.pinnacleindustries.com
   - Note: Bus/CV interior manufacturer

3. Ather Energy Pvt. Ltd.
   - Contact: Pritam Adhikary
   - Mobile: 919123765026
   - Email: pritam.adhikary@atherengery.com
   - Location: Bengaluru, Karnataka
   - Website: www.atherengery.com
   - Note: EV manufacturer, potential for EV interior parts

4. Mutual Automotive Pvt. Ltd. (4 contacts)
   - UD Gandhi: 919820227395, udgandhi@mutualautomotive.in
   - DK Gandhi: 919820053890, dkgandhi@mutualautomotive.in
   - HD Gandhi: 919820103668, hdgandhi@mutualautomotive.in
   - Gaurang Pandya: 916354789183, gaurang.pandya@mutualautomotive.in
   - Location: Andheri, Mumbai
   - Website: www.mutualautomotive.in

5. Victoria Auto
   - Contact: Rakesh Kumar Gautam
   - Mobile: 917042846667, 9999483947
   - Email: r.gautam@victoria.co.in
   - Location: Faridabad
   - Website: www.victoria.co.in

6. Motherson
   - Contact: Deepak Kumar
   - Mobile: 919716434384
   - Email: deepak.kumar11@mothersons.com
   - Location: IMT Manesar, Gurugram
   - Website: www.motherson.com
   - Note: Major Tier-1, high potential

7. Spark Minda (2 contacts)
   - Ranjit Nambiar: 919552526240, ranjit.nambiar@mindacorporation.com
   - P.C Jayan: 919552526239, pc.jayan@mindacorporation.com
   - Location: Greater Noida
   - Website: www.sparkmind.com
   - Note: Major Tier-1, lighting/switches

8. NTF
   - Contact: Vinod Kumar
   - Mobile: 919357961351
   - Email: vidonkumar@ntfindia.com
   - Location: IMT Manesar, Gurgaon
   - Website: www.ntfindia.com

9. Autokame (2 contacts)
   - Rakesh Chhabra: rakesh.chhabra@autokame.co.in
   - Sandeep Chhabra: sandeep.chhabra@autokame.co.in
   - Location: Sonepat, Haryana
   - Website: www.autokame.in""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Automotive Leads",
        summary="Automotive leads: IAC, Pinnacle, Ather, Mutual, Motherson, Spark Minda - Tier-1 prospects",
        metadata={
            "topic": "automotive_leads",
            "segment": "Automotive",
            "lead_count": 15
        }
    ))

    # 3. Packaging & Industrial Leads
    items.append(KnowledgeItem(
        text="""PlastIndia 2023 - Packaging & Industrial Leads

PACKAGING LEADS:

1. Formo Plast
   - Contact: Romil Shah
   - Mobile: 919893218969
   - Email: info@formoplast.in, formoplastindia@gmail.com
   - Location: Indore, MP
   - Website: www.formoplast.in
   - Note: Thermoformer - potential machine buyer or competitor

2. Navyug Packaging
   - Contact: Shreyans Daga
   - Mobile: 8080021555
   - Email: office.navyug@gmail.com
   - Location: Sakinaka, Mumbai
   - Website: www.navyugpackaging.in

3. Eagle Pack
   - Contact: Jatin Arora
   - Mobile: 919739901169
   - Email: jatin@eaglepack.in

4. Starco Metaplast (2 contacts)
   - Sandeep Jain: md@starcometaplast.com
   - Aksay Jain
   - Location: Sahibabad, Ghaziabad
   - Website: www.starcometaplast.com

5. Lee-Ten Plast
   - Contact: Sanjay Gajera
   - Mobile: 919924499074
   - Email: lee10plast@gmail.com
   - Location: Rajkot, Gujarat

INDUSTRIAL PRODUCTS LEADS:

1. Ukay Metal Industries Pvt. Ltd.
   - Contact: Rajendra Katore
   - Mobile: 919822011686
   - Email: katore.ranjedra@ukayindustries.net
   - Location: Nashik, Maharashtra
   - Website: www.ukayindustries.co.in

2. Durotuff (2 contacts)
   - Nilpesh Patel: 9825801615, sales@durotuff.com (Baddi, HP)
   - Sanjeev Yadav: 9560934111, sanjeev@durotuff.com (Noida)
   - Website: www.durotuff.com

3. Premier
   - Contact: Shyam Ji Trivedi
   - Mobile: 919953570287
   - Email: shyam@premierindoplast.com
   - Location: Faridabad, Haryana
   - Website: www.premierindoplast.com

4. Craftsmen (2 contacts)
   - Rajesh Khanna: 918307696600, rkhanna@craftsmengroup.co.in
   - CA Sanjay Bakhri: 919811058243, sanjay@craftsmengroup.co.in
   - Location: Sonepat, Haryana
   - Website: www.craftsmengroup.co.in""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Packaging Industrial Leads",
        summary="Packaging/Industrial: Formo Plast, Navyug, Starco, Durotuff, Premier, Craftsmen",
        metadata={
            "topic": "packaging_industrial_leads",
            "segment": ["Packaging", "Industrial"],
            "lead_count": 12
        }
    ))

    # 4. Composites & Specialty Leads
    items.append(KnowledgeItem(
        text="""PlastIndia 2023 - Composites & Specialty Leads

COMPOSITES / FRP LEADS:

1. Cosmos Fiber Glass Ltd
   - Contact: Rohit Rungta
   - Email: rohit.rungta@cosmosfg.com
   - Location: Faridabad, Haryana
   - Website: www.cosmosfg.com

2. Sthenos Composites
   - Contact: Sanjog Jain
   - Mobile: 919689921912
   - Email: sanjog.jain@sthenoscomposites.com
   - Location: Khed, Pune (MH)

3. A-Thon Allterrain Pvt Ltd.
   - Contact: Jeff
   - Email: jeff@a-thonalterrain.com
   - Location: Indiranagar, Bangalore

CONSUMER PRODUCTS LEADS:

1. Venus Luggage
   - Contact: Ramesh Jindal
   - Mobile: 9312222016
   - Email: jindalramesh@gmail.com
   - Location: Bawana, Delhi

2. Welcome Auto Center
   - Contact: Ayush Madan
   - Mobile: 919899938948
   - Email: madan_ayush@hotmail.com
   - Location: Kashmere Gate, Delhi
   - Website: www.welcomeautocentre.com

3. Prius Auto
   - Contact: Manish Sharma
   - Mobile: 7056604001
   - Email: quality@priusauto.com
   - Location: Sonepat, Haryana
   - Website: www.priusauto.com

4. AC Auto Connections
   - Contact: Himanshu Kurkreja
   - Mobile: 919953955000
   - Email: info@autoconnections.in
   - Location: Kalkaji, New Delhi
   - Website: www.autoconnections.in

WELLNESS / SANITARY LEADS:

1. MM Aqua (2 contacts)
   - Manish Kumar: 919599182968, manish.kumar@mmaqua.in
   - Suresh Kumar: 919953088607, suresh.kumar@mmqaua.in
   - Location: Gurgaon, Haryana
   - Website: www.mmaqua.in
   - Note: Potential for bathroom/sanitary thermoforming""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Composites Specialty Leads",
        summary="Composites: Cosmos FG, Sthenos, A-Thon; Consumer: Venus, Welcome, Prius; Sanitary: MM Aqua",
        metadata={
            "topic": "composites_specialty_leads",
            "segment": ["Composites", "Consumer", "Wellness"],
            "lead_count": 10
        }
    ))

    # 5. International Leads (Middle East)
    items.append(KnowledgeItem(
        text="""PlastIndia 2023 - International Leads (Middle East)

OMAN LEADS:

1. National Plastic Oman (3 contacts)
   - A.K. Rajesh Babu: 96899352297, rajesh.babu@nationalplasticoman.com
   - Badrinath M C: 96899885482, badrinath.c@nationalplasticoman.com
   - Antonio Goes: 96899339225, antoniogoes@alhosnigroup.com
   - Location: Muttrah, Muscat, Sultanate of Oman
   - Website: www.nationalplasticoman.com, www.alhosnigroup.com
   - Note: Part of Al Hosni Group, major Oman manufacturer

QATAR LEADS:

1. UFPP (United Foam & Plastic Products)
   - Contact: Ashok Arumugam
   - Mobile: 97466222539
   - Email: ashok@ufpp-qatar.com
   - Location: Doha, Qatar

MIDDLE EAST OPPORTUNITY:
- Growing plastics market in GCC
- Indian companies often have ME operations
- Export potential for Machinecraft machines
- FCS series for food packaging in ME market""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="International Leads",
        summary="Middle East: National Plastic Oman (Al Hosni Group), UFPP Qatar - GCC export opportunity",
        metadata={
            "topic": "international_leads",
            "region": "Middle East",
            "lead_count": 4
        }
    ))

    # 6. Complete Contact List for CRM
    items.append(KnowledgeItem(
        text="""PlastIndia 2023 - All Contacts Summary for CRM Import

HIGH PRIORITY LEADS (Tier-1 Auto / Large):
1. IAC - Rushikesh Purkar - 919561087954
2. Motherson - Deepak Kumar - 919716434384
3. Spark Minda - Ranjit Nambiar - 919552526240
4. Pinnacle Industries - Dhiraj Suryawanshi - 919503362300
5. Ather Energy - Pritam Adhikary - 919123765026
6. Mutual Automotive - UD Gandhi - 919820227395
7. National Plastic Oman - Rajesh Babu - 96899352297

MEDIUM PRIORITY (Growing Companies):
8. Victoria Auto - Rakesh Gautam - 917042846667
9. Craftsmen - Rajesh Khanna - 918307696600
10. Durotuff - Nilpesh Patel - 9825801615
11. Premier - Shyam Trivedi - 919953570287
12. Formo Plast - Romil Shah - 919893218969
13. MM Aqua - Manish Kumar - 919599182968
14. Navyug Packaging - Shreyans Daga - 8080021555

FOLLOW-UP ACTIONS:
- Import to CRM with PlastIndia 2023 source tag
- Segment by industry for targeted campaigns
- High priority: Personal follow-up call
- Medium priority: Email campaign
- All: Add to newsletter list

MACHINE RECOMMENDATIONS BY SEGMENT:
- Automotive Tier-1: PF1-X, IMG series
- Packaging: FCS series, AM series
- Consumer products: PF1-C series
- Composites: PF1-C large format
- Sanitary/Wellness: PF1-S, PF2 series""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="CRM Contact Summary",
        summary="CRM import: 7 high priority (Tier-1), 7 medium priority, segment by industry for campaigns",
        metadata={
            "topic": "crm_summary",
            "high_priority": 7,
            "medium_priority": 7
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("PlastIndia 2023 Visitor List Ingestion")
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
