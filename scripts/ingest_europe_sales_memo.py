#!/usr/bin/env python3
"""
Ingest Machinecraft Europe Sales Memo (March 2025)

Contains detailed European customer history, key accounts, and strategic outlook.
Critical for understanding existing customer base and reference installations.

Key markets: Sweden (since 2001), UK (Ridat OEM), Netherlands (Batelaan),
Germany (Thermic), plus Denmark, France, Italy, Ireland.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Machinecraft – Europe Sales Memo.pdf"


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from the Europe sales memo."""
    items = []

    # 1. Company Overview & European Footprint
    items.append(KnowledgeItem(
        text="""Machinecraft European Market Overview (March 2025)

COMPANY PROFILE:
- Third-generation, family-owned manufacturer
- CE-certified vacuum forming machines
- Trusted across 35+ countries
- 40+ years of experience
- Strong emphasis on reliability, support, and innovation

EUROPEAN FOOTPRINT:
Strong presence in key markets:
- Sweden (since 2001 - oldest market)
- United Kingdom (since 2008 - Ridat OEM)
- Netherlands (since 2019 - Batelaan partnership)
- Germany (since 2023 - Thermic milestone)
- Denmark (JoPlast 2024)
- France (Plastochim 2022)
- Italy (Mp3 2025)
- Ireland (Donite 2022)

KEY MILESTONES:
- 2001: First European sale (Sweden via Christer Carlsson)
- 2008: UK Ridat OEM partnership begins
- 2019: Netherlands breakthrough (Batelaan)
- 2020: New Umargam factory launch
- 2023: Germany technical milestone (Thermic)
- 2025: Biggest machine ever - PF1-6022 (6x2m) for Netherlands

STRATEGIC PARTNERSHIPS:
- Ridat Engineering Ltd (UK) - OEM partner
- FRIMO (Germany) - IMG thermoforming and vacuum lamination
- Active agency networks developing in Germany, Turkey, Canada""",
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="European footprint: 35+ countries, key markets Sweden, UK, Netherlands, Germany",
        metadata={
            "topic": "european_overview",
            "countries": 35,
            "experience_years": 40,
            "certification": "CE"
        }
    ))

    # 2. Sweden Market - Oldest Market
    items.append(KnowledgeItem(
        text="""SWEDEN MARKET - Machinecraft's Oldest European Market (Since 2001)

MARKET ENTRY:
- Started in 2001 through sales agent Mr. Christer Carlsson
- Over 10 machines sold and installed within first decade
- Many machines STILL RUNNING today (20+ years)

KEY SWEDISH CUSTOMERS:

1. ALLPRYL AB
   - Machine: PF-1000×2000
   - Installed: 2001
   - Status: Still running after 20+ years
   - Significance: One of earliest European customers

2. FORMA PLAST AB
   - Machine: Autoloader system
   - Installed: 2012

3. BD PLASTINDUSTRI AB
   - Machines: Two machines
   - Installed: 2011 and 2016
   - Note: Repeat customer

4. RHINO AB
   - Machine: Autoloader PF-1300×900
   - Installed: 2003

5. ANATOMIC SITT ⭐ (Featured Success Story)
   - Old machine: Older PF model (operated for years)
   - New machine: PF1-810 (modern generation)
   - Purchased: K 2019 trade show
   - Installed: 2022
   - Significance: REPEAT CUSTOMER - chose Machinecraft again
   - Media Coverage: Featured in PlastNet Sweden
   - Quote: "Indian-made CE-certified machines now confidently 
     compete with European alternatives"

SWEDEN MARKET STATUS:
- Legacy market with strong reference installations
- Re-engaging with success stories like Anatomic Sitt
- Machines have proven 20+ year longevity""",
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Sweden since 2001: Allpryl, Forma Plast, BD Plastindustri, Rhino, Anatomic Sitt",
        metadata={
            "topic": "sweden_customers",
            "market_entry": 2001,
            "machines_sold": "10+",
            "key_customers": ["Allpryl AB", "Forma Plast AB", "BD Plastindustri AB", "Rhino AB", "Anatomic Sitt"],
            "agent": "Christer Carlsson"
        }
    ))

    # 3. UK Market - Ridat OEM Partnership
    items.append(KnowledgeItem(
        text="""UNITED KINGDOM MARKET - Ridat OEM Legacy (Since 2008)

OEM PARTNERSHIP WITH RIDAT ENGINEERING LTD:
- Partnership started: 2008
- Machines supplied: ~50 machines
- Arrangement: CE-certified machines rebranded under Ridat name
- Product lines: Midmatic and semi-automatic thermoforming lines
- Applications: Packaging, display, and industrial

PARTNERSHIP SIGNIFICANCE:
- Helped establish Machinecraft quality and support standards
- Validated capabilities in mature, discerning European market
- Built reputation before direct European sales

OTHER UK CUSTOMERS (Direct Sales):
1. BI COMPOSITES
2. MHP INDUSTRIES
3. ARTFORM
4. WORLD PANEL

UK MARKET STATUS:
- Legacy market with solid customer base
- Strong reference installations
- Proven track record of ~50 machines via Ridat
- Foundation for European credibility""",
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="UK since 2008: ~50 machines via Ridat OEM, plus BI Composites, MHP, Artform, World Panel",
        metadata={
            "topic": "uk_customers",
            "market_entry": 2008,
            "ridat_machines": 50,
            "oem_partner": "Ridat Engineering Ltd",
            "direct_customers": ["BI Composites", "MHP Industries", "Artform", "World Panel"]
        }
    ))

    # 4. Netherlands - Batelaan Story
    items.append(KnowledgeItem(
        text="""NETHERLANDS MARKET - The Batelaan Success Story (Since 2019)

BREAKTHROUGH CUSTOMER: BATELAAN

How It Started:
- Batelaan initially invited Machinecraft to review an OLD GEISS machine
- Based on trust and technical openness, they ordered first machine
- This relationship shaped Machinecraft's modular machine platform

MACHINE HISTORY WITH BATELAAN:

1. First Order (2019):
   - Machine: PF1-1015
   - Feature: Universal frame design (innovative)
   - Significance: First of 14 similar machines sold

2. Upgrade Order (2022):
   - Machine: PF1-1315
   - Significance: Reinforced partnership, satisfied with performance

3. Planned (October 2025):
   - Machine: PF1-6022 ⭐ BIGGEST MACHINE EVER
   - Forming Area: 6 x 2 meters (6000 x 2000 mm)
   - Application: Hydroponic tray production
   - Status: Planned commissioning October 2025

BATELAAN'S IMPACT ON MACHINECRAFT:
- Partnership shaped the modular machine platform
- Led to standardized universal clamping system
- System now compatible across many part geometries
- 14 machines of similar architecture built and delivered

OTHER NETHERLANDS CUSTOMERS:

DUTCHTIDES (2025):
- Machine: XXL PF1-6019
- Price: €650,000
- Significance: High-value XXL machine sale""",
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Netherlands: Batelaan (PF1-1015, PF1-1315, PF1-6022 planned), DutchTides €650K",
        metadata={
            "topic": "netherlands_customers",
            "market_entry": 2019,
            "batelaan_machines": ["PF1-1015", "PF1-1315", "PF1-6022"],
            "biggest_machine": "PF1-6022",
            "biggest_forming_area": "6x2m",
            "dutchtides_value": 650000
        }
    ))

    # 5. Germany Market - Technical Milestone
    items.append(KnowledgeItem(
        text="""GERMANY MARKET - Technical Milestone (Since 2023)

SIGNIFICANCE:
Germany is THE benchmark market for engineering excellence.
Winning German customers validates technical capabilities.

KEY CUSTOMER: THERMIC GMBH

Order Details (2023):
- Machine: PF1-1616
- Price: €180,000
- Application: Industrial plastic fabrication

Technical Configuration:
- Servo movement (precision motion control)
- IR quartz heaters (energy efficient)
- CE-certified safety architecture
- German-spec engineering standards

IMPACT:
- Opened doors to technical sales in high-spec environments
- Validated Machinecraft's ability to meet German expectations
- Proved competitiveness against European machine builders

FRIMO PARTNERSHIP (Germany):
- Partnership Type: Strategic alliance
- Products: IMG thermoforming and vacuum lamination
- Market: Automotive interiors
- Benefit: Expands Machinecraft product portfolio
- Significance: Access to German automotive OEM market

GERMAN MARKET DEVELOPMENT:
- Actively developing agency networks in Germany
- Technical credibility established via Thermic
- FRIMO partnership opens automotive sector
- Target: High-spec industrial and automotive applications""",
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Germany: Thermic GmbH €180K (2023), FRIMO partnership for automotive",
        metadata={
            "topic": "germany_customers",
            "market_entry": 2023,
            "thermic_machine": "PF1-1616",
            "thermic_value": 180000,
            "partnership": "FRIMO",
            "frimo_products": ["IMG thermoforming", "vacuum lamination"]
        }
    ))

    # 6. Post-2019 Growth & New Factory
    items.append(KnowledgeItem(
        text="""POST-2019 GROWTH - New Factory Era

UMARGAM FACTORY LAUNCH (2020):
New generation of CE-certified machines introduced with:

TECHNICAL FEATURES:
- Servo-driven movements (precision, energy efficiency)
- Energy-saving IR heaters
- Automatic sheet loading
- Automatic tool change
- Advanced safety systems
- Closed chamber design for pre-blow & sag forming

PREMIUM COMPONENT BRANDS:
- Siemens (German)
- SEW (German)
- Mitsubishi (Japanese)
- Rittal (German)
- Sick (German)

This technical leap enabled HIGH-VALUE SALES across Europe.

---

EUROPEAN SALES POST-2019 (Chronological):

2019:
- Batelaan (Netherlands) - PF1-1015
  * Universal frame design breakthrough

2022:
- Batelaan (Netherlands) - PF1-1315 (upgrade)
- Plastochim (France) - PF1-0808
- Donite (Ireland) - PF1-0810
- Anatomic Sitt (Sweden) - PF1-810

2023:
- Thermic (Germany) - PF1-1616
  * Price: €180,000
  * Technical milestone in German market

2024:
- JoPlast (Denmark) - PF1-2015
  * Price: €290,000

2025:
- DutchTides (Netherlands) - XXL PF1-6019
  * Price: €650,000
  * Largest value sale
- Mp3 (Italy) - PF1-707
- Batelaan (Netherlands) - PF1-6022 (October 2025)
  * 6x2m forming area - BIGGEST MACHINE EVER
  * Hydroponic tray production""",
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Post-2019: €1.1M+ European sales, 8 countries, new factory enabled growth",
        metadata={
            "topic": "post_2019_growth",
            "factory_launch": 2020,
            "high_value_sales": ["DutchTides €650K", "JoPlast €290K", "Thermic €180K"],
            "countries": ["Netherlands", "Germany", "Denmark", "France", "Ireland", "Sweden", "Italy"]
        }
    ))

    # 7. Complete European Customer List
    items.append(KnowledgeItem(
        text="""COMPLETE EUROPEAN CUSTOMER LIST (As of March 2025)

SWEDEN:
1. Allpryl AB - PF-1000×2000 (2001) - Still running
2. Forma Plast AB - Autoloader system (2012)
3. BD Plastindustri AB - Two machines (2011, 2016)
4. Rhino AB - Autoloader PF-1300×900 (2003)
5. Anatomic Sitt - PF1-810 (2022) - Repeat customer

UNITED KINGDOM (via Ridat OEM + Direct):
6. Ridat Engineering Ltd - ~50 machines OEM (2008-present)
7. BI Composites
8. MHP Industries
9. Artform
10. World Panel

NETHERLANDS:
11. Batelaan - PF1-1015 (2019), PF1-1315 (2022), PF1-6022 (2025)
12. DutchTides - XXL PF1-6019 €650,000 (2025)

GERMANY:
13. Thermic GmbH - PF1-1616 €180,000 (2023)

DENMARK:
14. JoPlast - PF1-2015 €290,000 (2024)

FRANCE:
15. Plastochim - PF1-0808 (2022)

IRELAND:
16. Donite - PF1-0810 (2022)

ITALY:
17. Mp3 - PF1-707 (2025)

---

TOTAL EUROPEAN MACHINES:
- Sweden: 10+ machines (since 2001)
- UK: ~50 machines via Ridat + direct
- Netherlands: 3+ machines (major growth market)
- Germany: 1 machine (strategic entry)
- Other EU: 4+ machines

REFERENCE ACCOUNTS FOR SALES:
Top references by market/application:
- Industrial: Batelaan, Thermic, BI Composites
- Medical/Wellness: Anatomic Sitt
- Packaging: Allpryl, Forma Plast
- High-Volume: JoPlast, DutchTides
- Longevity proof: Allpryl (20+ years running)""",
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="17+ European customers across 8 countries, 60+ total machines installed",
        metadata={
            "topic": "customer_list",
            "total_customers": 17,
            "countries": 8,
            "uk_machines": 50,
            "sweden_machines": 10
        }
    ))

    # 8. Strategic Outlook
    items.append(KnowledgeItem(
        text="""EUROPEAN STRATEGIC OUTLOOK (March 2025)

MARKET STATUS BY REGION:

LEGACY MARKETS (Strong References):
- Sweden: Oldest market, 20+ year proven installations
- UK: ~50 machines via Ridat, established quality reputation

GROWTH MARKETS:
- Netherlands: Batelaan partnership shaped modular platform
- Germany: Thermic opened doors to high-spec technical sales

EMERGING MARKETS:
- Denmark: JoPlast €290K order (2024)
- France: Plastochim (2022)
- Italy: Mp3 (2025)
- Ireland: Donite (2022)

---

STRATEGIC PARTNERSHIPS:

1. FRIMO (Germany):
   - Products: IMG thermoforming, vacuum lamination
   - Market: Automotive interiors
   - Benefit: Expands product portfolio, accesses OEM market

2. Agency Network Development:
   - Germany: Active development
   - Turkey: Active development
   - Canada: Active development
   - Scandinavia: Re-engaging with Anatomic Sitt success

---

KEY COMPETITIVE ADVANTAGES IN EUROPE:
1. CE-certified machines (mandatory for EU)
2. 40+ years experience
3. Premium components (Siemens, Mitsubishi, Sick)
4. Proven longevity (20+ years in Sweden)
5. Technical capability proven in Germany
6. Competitive pricing vs European manufacturers
7. Strong customer support and service

---

GROWTH TRAJECTORY:
- 2001-2019: Foundation building (Sweden, UK)
- 2019-2022: Platform development (Batelaan partnership)
- 2023-2025: Technical validation (Germany) + scale (XXL machines)
- 2025+: Automotive expansion (FRIMO), agency networks""",
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Strategy: Legacy(Sweden/UK), Growth(NL/DE), FRIMO automotive partnership",
        metadata={
            "topic": "strategic_outlook",
            "legacy_markets": ["Sweden", "UK"],
            "growth_markets": ["Netherlands", "Germany"],
            "partnerships": ["FRIMO", "Ridat"],
            "agency_development": ["Germany", "Turkey", "Canada"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("Machinecraft Europe Sales Memo Ingestion")
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
