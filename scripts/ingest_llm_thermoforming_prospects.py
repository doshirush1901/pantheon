#!/usr/bin/env python3
"""
Ingest LLM Thermoforming Prospects - AI-Scored Leads Database

96 thermoforming prospects scored by LLM analysis with temperature ratings,
engagement metrics, and personalized outreach recommendations.

Source: LLM_Thermoforming_Prospects_20250902.xlsx
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "LLM_Thermoforming_Prospects_20250902.xlsx"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from LLM-scored prospects."""
    items = []

    # 1. LLM Prospects Overview
    items.append(KnowledgeItem(
        text="""LLM Thermoforming Prospects - AI-Scored Lead Database Overview

TOTAL PROSPECTS: 96 companies
DATA DATE: September 2, 2025
SCORING METHOD: LLM analysis of email communications

TEMPERATURE CLASSIFICATION:
🔥 BLAZING HOT (Score 96-100): 7 leads - Highest conversion potential
🔥 RED HOT (Score 75-95): 1 lead - Strong engagement
🟠 HOT (Score 64-74): 3 leads - Good prospects
🟡 WARM (Score 40-63): ~20 leads - Nurture candidates
🔵 COOL (Score <40): ~65 leads - Long-term prospects

SCORING FACTORS:
- Total Communications (email count)
- Quote Mentions (pricing discussions)
- Meeting Mentions (engagement depth)
- Conversation continuity
- Response patterns

TOP HOT SCORES:
1. IAC Group - Score 100 (24 comms, 10 quotes)
2. FVF Japan - Score 100 (19 comms, 4 quotes)
3. Mutual Automotive - Score 100 (10 comms, 10 quotes)
4. Soehner - Score 100 (9 comms, 7 quotes)
5. Batelaan - Score 96 (10 comms, 2 quotes)
6. WeFabricate - Score 96 (6 comms, 6 quotes)
7. Minerex - Score 96 (6 comms, 6 quotes)

USER PRIORITY LEADS (Manually flagged):
1. Forma3D - K2025 meeting planned
2. VacMould Displays - Australia display market""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="LLM Prospects Overview",
        summary="LLM-scored leads: 96 prospects, 7 blazing hot (IAC, FVF, Mutual), temperature-based targeting",
        metadata={
            "topic": "llm_prospects_overview",
            "total_leads": 96,
            "blazing_hot": 7
        }
    ))

    # 2. Blazing Hot Leads (Score 96-100)
    items.append(KnowledgeItem(
        text="""LLM Prospects - BLAZING HOT Leads (Score 96-100)

1. IAC GROUP - Score 100 ⭐ HIGHEST PRIORITY
   - Contact: Mohit Karandikar
   - Email: mohit.karandikar@iacgroup.com
   - Communications: 24 (most in database)
   - Quote Mentions: 10
   - Meeting Mentions: 4
   - Note: Major Tier-1 automotive supplier
   - Cross-ref: PlastIndia 2023 leads (Rushikesh Purkar)

2. FVF (Fuse Vacuum Forming) Japan - Score 100
   - Contact: T. Yabuki (矢葺)
   - Email: t-yabuki@fvf.co.jp
   - Communications: 19
   - Quote Mentions: 4
   - Meeting Mentions: 9
   - Note: Japan OEM partner for PF1-X series
   - Cross-ref: Japan pricing ingested earlier

3. MUTUAL AUTOMOTIVE - Score 100
   - Contact: Gaurang Pandya
   - Email: gaurang.pandya@mutualautomotive.in
   - Communications: 10
   - Quote Mentions: 10 (100% quote rate!)
   - Meeting Mentions: 8
   - Cross-ref: PlastIndia 2023 leads (4 contacts)

4. SOEHNER - Score 100
   - Contact: Theo Doll
   - Email: t.doll@soehner.de
   - Communications: 9
   - Quote Mentions: 7
   - Meeting Mentions: 6
   - Note: German thermoformer

5. BATELAAN - Score 96
   - Contact: Chris Chrispijn
   - Email: c.chrispijn@batelaan.nl
   - Communications: 10
   - Quote Mentions: 2
   - Meeting Mentions: 7
   - Cross-ref: European Machine Sales list

6. WEFABRICATE - Score 96
   - Contact: Teun van de Sande
   - Email: teun.van.de.sande@wefabricate.com
   - Communications: 6
   - Quote Mentions: 6 (100% quote rate)
   - Meeting Mentions: 6
   - Cross-ref: European Machine Sales list

7. MINEREX - Score 96
   - Contact: Radomir Lazic
   - Email: radomir.lazic@minerex.ch
   - Communications: 6
   - Quote Mentions: 6 (100% quote rate)
   - Meeting Mentions: 6
   - Quote Value: €190K (2x press + cutting)
   - Cross-ref: European Machine Sales list""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Blazing Hot Leads",
        summary="Blazing hot: IAC (24 comms), FVF Japan, Mutual Auto, Soehner, Batelaan, WeFabricate, Minerex",
        metadata={
            "topic": "blazing_hot_leads",
            "temperature": "BLAZING HOT",
            "lead_count": 7
        }
    ))

    # 3. Hot & Red Hot Leads
    items.append(KnowledgeItem(
        text="""LLM Prospects - RED HOT & HOT Leads

RED HOT (Score 75):
1. FORMA3D - Score 75 ⭐ USER PRIORITY
   - Contact: Eduardo Pinto
   - Email: pinto@forma3d.pt
   - Communications: 8
   - Quote Mentions: 1
   - Meeting Mentions: 2
   - Status: K2025 meeting planned
   - Personalized Subject: "K2025 Meeting Coordination"
   - Cross-ref: K2025 leads, European Machine Sales

HOT (Score 64-73):
2. AUTOCOMPONENT - Score 73
   - Contact: Anton Bezruchkin
   - Email: a.bezruchkin@autocomponent.info
   - Communications: 8
   - Quote Mentions: 5
   - Meeting Mentions: 3
   - Note: Avtovaz vacuum lamination project
   - Cross-ref: European Machine Sales (Belgium)

3. TRIMAXGROUP - Score 64
   - Contact: Radha Gupta
   - Email: radhagupta@trimaxgroup.de
   - Communications: 4
   - Quote Mentions: 4 (100% quote rate)
   - Meeting Mentions: 4

4. METROLUX FLOWERS - Score 64
   - Contact: Fitsum
   - Email: fitsum@metroluxflowers.com
   - Communications: 4
   - Quote Mentions: 4
   - Meeting Mentions: 4
   - Note: Flower/agriculture packaging?""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Hot Leads",
        summary="Red/Hot: Forma3D (K2025 meeting), Autocomponent (Avtovaz), Trimax, Metrolux - active prospects",
        metadata={
            "topic": "hot_leads",
            "temperature": ["RED HOT", "HOT"],
            "lead_count": 4
        }
    ))

    # 4. Warm Leads
    items.append(KnowledgeItem(
        text="""LLM Prospects - WARM Leads (Score 40-63)

WARM LEADS WITH HIGH COMMUNICATION COUNT:

1. FLORMA - Score 56
   - Contact: Uzik
   - Email: uzik@florma.co.il
   - Communications: 16 (high volume)
   - Quote Mentions: 0
   - Meeting Mentions: 1
   - Note: Israel market

2. SAYPLASTICS - Score 42
   - Contact: Louie Smith
   - Email: lsmith@sayplastics.com
   - Communications: 14
   - Quote Mentions: 0
   - Note: High communication, low quote conversion

3. VISSCHER-CARAVELLE - Score 51
   - Contact: Michiel van Berkum
   - Email: michielvanberkum@visscher-caravelle.nl
   - Communications: 4
   - Quote Mentions: 3
   - Cross-ref: European Machine Sales (Netherlands)

4. VACMOULD DISPLAYS - Score 50 ⭐ USER PRIORITY
   - Contact: Jim Biberias
   - Email: jbiberias@vacmoulddisplays.com.au
   - Communications: 4
   - Meeting Mentions: 1
   - Note: Australia display market opportunity
   - Personalized Subject: "Australia Market Opportunity"

5. SINGLEPALST - Score 49
   - Email: info@singlepalst.de
   - Communications: 4
   - Quote Mentions: 1
   - Cross-ref: European Machine Sales (Germany)

6. PLASTIKABALUMAG - Score 48
   - Contact: Reto Bamert
   - Email: reto.bamert@plastikabalumag.ch
   - Communications: 6
   - Quote Mentions: 6 (100% quote rate)
   - Note: Custom overpressure machine project
   - Cross-ref: European Machine Sales (most emails - 13)

7. CNCTEAM - Score 48
   - Contact: Berry van den Nieuwelaar
   - Email: berryvandennieuwelaar@cncteam.nl
   - Communications: 4
   - Quote Mentions: 4
   - Cross-ref: European Machine Sales (Netherlands)

8. HESSE-THERMOFORMUNG - Score 48
   - Contact: Klaus Heuer
   - Email: klaus.heuer@hesse-thermoformung.de
   - Communications: 3
   - Quote Mentions: 3
   - Cross-ref: European Machine Sales (Germany)

9. FAURECIA - Score 48
   - Contact: Stephane Fiquet
   - Email: stephane.fiquet@faurecia.com
   - Communications: 3
   - Quote Mentions: 3
   - Note: Major Tier-1 automotive supplier

10. IINET (Australia) - Score 40
    - Contact: CJ Laycock
    - Email: cjlaycock@iinet.net.au
    - Communications: 5
    - Quote Mentions: 5""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Warm Leads",
        summary="Warm: Florma (16 comms), Sayplastics (14), Faurecia (Tier-1), Plastikabalumag, VacMould AU",
        metadata={
            "topic": "warm_leads",
            "temperature": "WARM",
            "lead_count": 10
        }
    ))

    # 5. Cool Leads & Geographic Distribution
    items.append(KnowledgeItem(
        text="""LLM Prospects - COOL Leads & Geographic Distribution

COOL LEADS (Score <40) - Notable Prospects:

1. ASUN - Score 38
   - Email: asun@asun.kr
   - Communications: 5
   - Quote Mentions: 3
   - Note: Korea market

2. SLOVAKOR - Score 38
   - Contact: Richard Mojzis
   - Email: mojzis@slovakor.sk
   - Communications: 3
   - Note: Slovakia market

3. VDM-METALS - Score 36
   - Contact: Eric Vidal
   - Email: eric.vidal@vdm-metals.com
   - Communications: 4

4. DUROTHERM - Score 36
   - Contact: Pavel Votruba
   - Email: pavel.votruba@durotherm.cz
   - Communications: 4
   - Cross-ref: European Machine Sales (Czech)

5. WATTTRON - Score 33
   - Contact: Sascha Bach
   - Email: sascha.bach@watttron.de
   - Communications: 3
   - Note: Germany technology company

6. SEABORNE - Score 33
   - Contact: John Cooper
   - Email: johncooper@seaborne.cz
   - Communications: 3
   - Note: Czech Republic

7. RONIKA - Score 33
   - Email: arturuas@ronika.lt
   - Communications: 3
   - Note: Lithuania market

8. POLYEEPLAST - Score 33
   - Email: info@polyeeplast.com
   - Communications: 3

GEOGRAPHIC DISTRIBUTION (All 96 leads):
- Europe: ~60% (Germany, Netherlands, Switzerland, UK, France, Italy)
- Asia-Pacific: ~20% (Japan, Korea, India, Australia)
- Middle East: ~10% (Israel, Ethiopia)
- Americas: ~10% (USA, others)""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Cool Leads Geographic",
        summary="Cool leads: ASUN Korea, Slovakor, Durotherm Czech, Ronika Lithuania; 60% Europe, 20% APAC",
        metadata={
            "topic": "cool_leads_geographic",
            "temperature": "COOL",
            "lead_count": 8
        }
    ))

    # 6. Action Priority Matrix
    items.append(KnowledgeItem(
        text="""LLM Prospects - Action Priority Matrix

TIER 1: IMMEDIATE ACTION (Blazing Hot, Score 96-100)
Target: Close deals, schedule demos
Companies: IAC Group, FVF Japan, Mutual Automotive, Soehner, Batelaan, WeFabricate, Minerex
Total Opportunity: 7 companies with highest conversion probability

TIER 2: ACTIVE PURSUIT (Hot, Score 64-95)
Target: Send quotes, arrange meetings
Companies: Forma3D (K2025), Autocomponent, Trimax, Metrolux
Actions: Follow up on K2025 meeting, update quotes

TIER 3: NURTURE CAMPAIGN (Warm, Score 40-63)
Target: Regular touchpoints, capability updates
Key Companies: Florma (16 comms), Sayplastics (14 comms), Faurecia (Tier-1), Plastikabalumag
Strategy: Monthly newsletter, case study sharing

TIER 4: LONG-TERM DEVELOPMENT (Cool, Score <40)
Target: Brand awareness, market presence
Strategy: Quarterly updates, trade show invitations

CROSS-REFERENCE OPPORTUNITIES:
- IAC Group: Multiple contacts across PlastIndia, LLM lists
- FVF Japan: Links to Japan pricing, PF1-X OEM partnership
- Mutual Automotive: 4 contacts in PlastIndia, strongest Indian lead
- Minerex: €190K quoted in European list
- Plastikabalumag: 13 emails in European list, custom machine project

PERSONALIZED OUTREACH READY:
- Forma3D: K2025 meeting coordination email prepared
- VacMould Displays: Australia market opportunity email prepared""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="LLM Action Matrix",
        summary="Action matrix: Tier 1 (7 blazing), Tier 2 (4 hot), Tier 3 (nurture), cross-ref with other lists",
        metadata={
            "topic": "action_matrix",
            "tier_1_count": 7,
            "tier_2_count": 4
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("LLM Thermoforming Prospects Ingestion")
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
