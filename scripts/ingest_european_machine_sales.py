#!/usr/bin/env python3
"""
Ingest European Machine Sales Leads - September 2025

58 European thermoformer prospects with email engagement history.
Organized by country with contact frequency and recency data.

Source: European_Machine_Sales_20250902.xlsx
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "European_Machine_Sales_20250902.xlsx"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from European sales leads."""
    items = []

    # 1. European Leads Overview
    items.append(KnowledgeItem(
        text="""European Machine Sales Leads Overview (September 2025)

TOTAL PROSPECTS: 58 companies
REGION: Western & Central Europe
DATA DATE: September 2, 2025

GEOGRAPHIC DISTRIBUTION:
1. Germany: 26 companies (largest market)
2. Netherlands: 6 companies
3. Switzerland: 4 companies
4. Italy: 4 companies
5. Belgium: 3 companies
6. UK: 3 companies
7. Ireland: 3 companies
8. France: 2 companies
9. Sweden: 2 companies
10. Others: Austria, Norway, Romania, Slovenia, Portugal, Czech Republic

ENGAGEMENT METRICS:
- Total emails sent across all prospects
- Last contact date tracked
- Days since last contact calculated
- Response tracking (Did They Reply)

TOP ENGAGED PROSPECTS (Most Emails Sent):
1. Plastikabalumag (Switzerland) - 13 emails
2. Celag (Italy) - 13 emails
3. Dezet (Netherlands) - 9 emails
4. TC-M (Belgium) - 9 emails
5. Grewa-Tech (Germany) - 9 emails
6. Autocomponent (Belgium) - 8 emails
7. Consortium Cases (Ireland) - 7 emails

RECENT CONTACTS (2025):
1. Uniroma3 (Italy) - Aug 2025 - PF1-R-0707 offer
2. Dezet (Netherlands) - Aug 2025 - PF1-X-1210 K-Show unit
3. Forma3D (Portugal) - May 2025
4. Grewa-Tech (Germany) - Jan 2025
5. Driskes (Germany) - Jan 2025""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="European Sales Overview",
        summary="EU sales: 58 prospects, Germany dominant (26), top engaged: Plastikabalumag, Celag, Dezet",
        metadata={
            "topic": "eu_overview",
            "total_leads": 58,
            "primary_market": "Germany"
        }
    ))

    # 2. Germany Leads (Largest Market)
    items.append(KnowledgeItem(
        text="""European Sales - Germany Leads (26 Companies)

HIGH ENGAGEMENT (5+ emails):
1. Grewa-Tech
   - Contact: Mehmet Eroglu
   - Email: m.eroglu@grewa-tech.de
   - Emails: 9
   - Last: Jan 2025
   - Subject: RFQ - 3D Punch Tool + Machine

2. WeFabricate
   - Contact: Teun van de Sande
   - Email: teun.van.de.sande@wefabricate.com
   - Emails: 6
   - Last: Mar 2023
   - Note: Met in person

3. Hesse-Thermoformung
   - Contact: Klaus Heuer
   - Email: klaus.heuer@hesse-thermoformung.de
   - Emails: 5
   - Last: Oct 2023

4. Hetronik
   - Contact: A. Farrenkopf
   - Email: a.farrenkopf@hetronik.de
   - Emails: 4
   - Subject: HC500 for SOEHNER machine

5. Driskes
   - Contact: Christian
   - Email: christian@driskes.de
   - Emails: 4
   - Last: Jan 2025

6. Exeron
   - Contact: Stefan Pross
   - Email: stefan.pross@exeron.de
   - Emails: 4
   - Note: Teams meeting requested

7. LK-Thermo
   - Contact: A. Drumm
   - Email: a.drumm@lk-thermo.de
   - Emails: 4
   - Subject: Tooling quote request

MEDIUM ENGAGEMENT (2-3 emails):
- Elcokunststoffe: udo.schwarzkopf@elcokunststoffe.de
- Singlepalst: info@singlepalst.de
- Energie-Gipscomm: info@energie-gipscomm.de
- Plastisart: jf.deltenre@plastisart.com

SINGLE TOUCHPOINT (1 email):
- Plastforma, Reinraum-Mieten, S-KV, Miki-Plastik
- Fritsch-Verpackungen, Agoform, Meta-Technik
- Asch-Kunststofftechnik, Traytec, Polyplast
- Linbrunner, Thermoform-Plastics""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Germany Sales Leads",
        summary="Germany: 26 leads, top: Grewa-Tech (9 emails), WeFabricate (6), Hesse (5), Driskes (4)",
        metadata={
            "topic": "germany_leads",
            "country": "Germany",
            "lead_count": 26
        }
    ))

    # 3. Benelux & Switzerland Leads
    items.append(KnowledgeItem(
        text="""European Sales - Benelux & Switzerland Leads

NETHERLANDS (6 companies):
1. Dezet - PRIORITY
   - Email: info@dezet.nl
   - Emails: 9
   - Last: Aug 2025 (very recent!)
   - Subject: PF1-X-1210 K-Show Display Unit
   - Note: Hot prospect, final offer sent

2. VDL Wientjes Roden
   - Contact: C. Mulder
   - Email: c.mulder@vdlwientjesroden.nl
   - Emails: 2
   - Note: Part of VDL Group

3. HCCNet
   - Contact: Ernan Grooters
   - Email: ernan.grooters@hccnet.nl
   - Emails: 2
   - Note: Meeting arranged in Mar 2023

4. Multitray
   - Contact: Ian
   - Email: ian@multitray.nl
   - Subject: SPM for Carry Trays

5. Visscher-Caravelle
   - Contact: Michiel van Berkum
   - Email: michielvanberkum@visscher-caravelle.nl

6. CNCTeam
   - Email: gerwinpelle@cncteam.nl

BELGIUM (3 companies):
1. TC-M - HIGH ENGAGEMENT
   - Contact: PLH
   - Email: plh@tc-m.be
   - Emails: 9
   - Subject: ARJO thermoforming technology

2. Autocomponent - HIGH ENGAGEMENT
   - Contact: A. Bezruchkin
   - Email: a.bezruchkin@autocomponent.info
   - Emails: 8
   - Subject: Vacuum Lamination for Avtovaz

3. ANL-Plastics
   - Contact: Patrick Nelissen
   - Email: patrick.nelissen@anl-plastics.be

SWITZERLAND (4 companies):
1. Plastikabalumag - HIGHEST ENGAGEMENT
   - Contact: Patrick Gygax
   - Email: patrick.gygax@plastikabalumag.ch
   - Emails: 13 (most in database!)
   - Subject: Overpressure Thermoforming Machine proposal
   - Note: Custom development project

2. AMTZ
   - Contact: Sahithi
   - Email: sahithi.ch@amtz.in
   - Emails: 3

3. Batelaan
   - Contact: C. Chrispijn
   - Email: c.chrispijn@batelaan.nl

4. Minerex
   - Contact: Radomir Lazic
   - Email: radomir.lazic@minerex.ch
   - Subject: 2x thermoforming press + 1x cutting
   - Quote: €160K + €30K = €190K""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Benelux Switzerland Leads",
        summary="Benelux/CH: Dezet HOT (Aug 2025), Plastikabalumag (13 emails), TC-M, Minerex €190K quote",
        metadata={
            "topic": "benelux_swiss_leads",
            "countries": ["Netherlands", "Belgium", "Switzerland"],
            "lead_count": 13
        }
    ))

    # 4. UK, Ireland & Nordic Leads
    items.append(KnowledgeItem(
        text="""European Sales - UK, Ireland & Nordic Leads

IRELAND (3 companies):
1. Consortium Cases - HIGH ENGAGEMENT
   - Contact: Steven
   - Email: steven@consortcases.ie
   - Emails: 7
   - Subject: 2x3m PF1 offer
   - Note: Large format machine inquiry

2. AIP
   - Contact: John
   - Email: john@aip.ie

3. (Additional Ireland contact in main list)

UK (3 companies):
1. Big-Bear
   - Contact: Emma H / Steve Church
   - Email: emmah@big-bear.co.uk, stevechurch@big-bear.co.uk
   - Emails: 3
   - Subject: Thermoforming machine offer

2. Mykor
   - Contact: Jack
   - Email: jack@mykor.co.uk
   - Emails: 2
   - Subject: Thermoforming inquiry

SWEDEN (2 companies):
1. Stegoplast
   - Contact: Goran Bjarle
   - Email: goran.bjarle@stegoplast.se

2. Formaplast
   - Contact: Roine
   - Email: roine@formaplast.se

NORWAY:
1. Plexx
   - Contact: ASJ
   - Email: asj@plexx.no

AUSTRIA (2 companies):
1. Glimberger
   - Contact: M. Hirsch
   - Email: m.hirsch@glimberger.at

2. Syntec
   - Contact: G. Schwarzbraun
   - Email: g.schwarzbraun@syntec.at
   - Emails: 2
   - Subject: RFQ for ABS PMMA""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="UK Ireland Nordic Leads",
        summary="UK/IE/Nordic: Consortium Cases (7 emails, 2x3m PF1), Big-Bear (3), Syntec ABS PMMA",
        metadata={
            "topic": "uk_ireland_nordic",
            "countries": ["UK", "Ireland", "Sweden", "Norway", "Austria"],
            "lead_count": 10
        }
    ))

    # 5. Southern & Eastern Europe Leads
    items.append(KnowledgeItem(
        text="""European Sales - Southern & Eastern Europe Leads

ITALY (4 companies):
1. Celag - HIGHEST ENGAGEMENT
   - Email: commerciale@celag.it
   - Emails: 13 (tied for most!)
   - Subject: RFQ Router 1200x2000 5-axis
   - Note: CNC router inquiry

2. Uniroma3 - MOST RECENT
   - Contact: Annalisa Genovesi
   - Email: annalisa.genovesi@uniroma3.it
   - Emails: 1
   - Last: Aug 11, 2025 (22 days ago)
   - Subject: PF1-R-0707 offer
   - Note: University/research institution

3. Omipa
   - Email: omipa@omipa.it
   - Subject: ABS PMMA Line for ALP India

4. Utentra
   - Email: info@utentra.it
   - Subject: Quote Fan

FRANCE (2 companies):
1. Alphaform
   - Contact: Philippe Veyrenche
   - Email: pveyrenche@alphaform.fr
   - Emails: 2
   - Subject: Machine de thermoformage

2. Thermoformeuse
   - Email: info@thermoformeuse.fr
   - Note: Website/agent discussion

PORTUGAL:
1. Forma3D - RECENT
   - Contact: Eduardo Pinto
   - Email: pinto@forma3d.pt
   - Emails: 3
   - Last: May 2025
   - Subject: Exclusive machine offers

EASTERN EUROPE:
1. Slovenia - Plastoform
   - Contact: Peter Gorenc
   - Email: p.gorenc@plastoform.si
   - Emails: 4

2. Romania - Belform
   - Contact: Adrian Tone
   - Email: adrian.tone@belform.ro

3. Czech Republic - Durotherm
   - Contact: Pavel Votruba
   - Email: pavel.votruba@durotherm.cz
   - Subject: Machines shipping near Heilbronn""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="Southern Eastern Europe Leads",
        summary="S/E Europe: Celag Italy (13 emails), Uniroma3 (Aug 2025 PF1-R), Forma3D Portugal recent",
        metadata={
            "topic": "southern_eastern_europe",
            "countries": ["Italy", "France", "Portugal", "Slovenia", "Romania", "Czech Republic"],
            "lead_count": 10
        }
    ))

    # 6. Priority Action List
    items.append(KnowledgeItem(
        text="""European Sales - Priority Action List

IMMEDIATE FOLLOW-UP (2025 contacts):
1. Uniroma3 (Italy) - Aug 2025
   - PF1-R-0707 offer sent
   - ACTION: Follow up on offer

2. Dezet (Netherlands) - Aug 2025
   - PF1-X-1210 K-Show display unit offer
   - ACTION: Close the deal before K-Show

3. Forma3D (Portugal) - May 2025
   - Exclusive offers sent
   - ACTION: Re-engage with updated pricing

4. Grewa-Tech (Germany) - Jan 2025
   - 3D Punch Tool + Machine RFQ
   - ACTION: Check project status

5. Driskes (Germany) - Jan 2025
   - RFQ for Reliance India project
   - ACTION: Follow up on project

RE-ENGAGEMENT TARGETS (High historical engagement):
1. Plastikabalumag (CH) - 13 emails, last Aug 2024
   - Custom overpressure machine project
   - ACTION: Project status check

2. Celag (Italy) - 13 emails, last Feb 2023
   - CNC Router 1200x2000 5-axis
   - ACTION: Re-engage with new offerings

3. TC-M (Belgium) - 9 emails, last Jul 2024
   - ARJO thermoforming technology
   - ACTION: Project update request

4. Consortium Cases (Ireland) - 7 emails, last Apr 2024
   - 2x3m PF1 large format
   - ACTION: Budget/timeline check

QUOTATION OPPORTUNITIES:
- Minerex (CH): €190K for 2x press + 1x cutting
- Consortium Cases (IE): Large format PF1
- Autocomponent (BE): Vacuum lamination for Avtovaz""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="EU Priority Actions",
        summary="Priority: Dezet/Uniroma3 (Aug 2025), Plastikabalumag/Celag (13 emails), Minerex €190K",
        metadata={
            "topic": "priority_actions",
            "immediate_followup": 5,
            "re_engagement": 4
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("European Machine Sales Leads Ingestion")
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
