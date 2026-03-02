#!/usr/bin/env python3
"""
Ingest Thermoforming Machine Market Data - Europe

Contains:
- K2016 exhibition leads
- ETD 2018 European thermoformers database
- Existing Machinecraft customers in Europe
"""

import sys
import os
import importlib.util

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

spec = importlib.util.spec_from_file_location(
    "knowledge_ingestor",
    os.path.join(project_root, "openclaw/agents/ira/src/brain/knowledge_ingestor.py")
)
knowledge_ingestor_module = importlib.util.module_from_spec(spec)
sys.modules["knowledge_ingestor"] = knowledge_ingestor_module
spec.loader.exec_module(knowledge_ingestor_module)

KnowledgeIngestor = knowledge_ingestor_module.KnowledgeIngestor
KnowledgeItem = knowledge_ingestor_module.KnowledgeItem

SOURCE_FILE = "Thermoforming Machine Market Data - Europe.xlsx"


def create_knowledge_items() -> list:
    """Create knowledge items from European market data."""
    items = []

    # 1. K2016 Exhibition Leads
    items.append(KnowledgeItem(
        text="""K2016 Exhibition Leads - European Prospects:

LEADS FROM K2016 EXHIBITION (Düsseldorf, Germany):

1. Pedro - Portugal
   - Company: Polisport
   - Email: pedro.araujo@polisport.com
   - Web: www.polisport.com
   - Application: (motorcycle parts, sports equipment)

2. Nenko - Bulgaria
   - Company: EcoPro
   - Email: ecopro@abv.bg
   - Web: www.ecoprobg.com
   - Application: Well Covers using PF1

3. Peter - Belgium
   - Company: Vitalo
   - Email: peter.lichherte@be.vitalo.net
   - Web: www.vitalo.net
   - Application: PF1

4. Neiminen - Finland
   - Company: Kera Group
   - Email: juha.neiminen@keragroup.fi
   - Web: www.keragroup.fi
   - Application: Skylights using PF1

5. Milan - Serbia
   - Company: Fima
   - Email: tsaic.milan@gmail.com
   - Web: www.fima.rs
   - Application: EPS Pallet

6. Zoltan - Hungary
   - Company: Szkaliczki
   - Email: zoltan.miszlai@szkaliczki.hu
   - Web: www.szkaliczki.hu
   - Application: PF1, INLINE, SPM

7. Guenter - Austria
   - Company: Syntec
   - Email: g.schwarzbraun@syntec.at
   - Web: www.syntec.at
   - Application: Automotive, Ads

8. Sverre - Denmark
   - Company: Velux
   - Email: sverre.simonsen@velux.com
   - Web: velux.com
   - Application: EPS Window part

9. Jurgen - Germany
   - Company: Inno und Sales
   - Email: j.kitscheke@innoundsales.de
   - Web: innoundsales.de
   - Application: PF1

10. Franz - Germany
    - Company: Polleres
    - Email: f.lang@polleres.com
    - Web: www.polleres.com
    - Application: Transport, Trays, Germination

11. Kamer - Russia
    - Company: Sibeco Russia
    - Email: kamer@sibeco-russia.ru
    - Web: www.sibeco.net
    - Application: Bus Seats

12. Zacarias - Portugal
    - Company: Fibraline/Linextras
    - Email: zacariascavaco@fibraline.pt
    - Web: www.linextras.com
    - Application: Car Parts

13. Gabriel - Romania
    - Company: Crisco
    - Email: office@crisco.ro
    - Web: www.crisco.ro

14. Hans - Germany
    - Company: Ben Plastic
    - Email: hr.buehler@ben-plastic.com

15. Imer - Italy
    - Company: Technoform
    - Email: technoform@ittc.net
    - Web: technoformsrl.it
    - Application: Shower Panels

16. Mikko - Finland
    - Company: Motoseal/Masitools
    - Email: mikko.ranne@motoseal.fi
    - Web: masitools.com
    - Application: Snow pushers, trolleys

17. HBW Gubesch - Germany
    - Contact: A. Schenk, J. Nagy
    - Email: a.schenk@hbw-gubesch.de, j.nagy@hbw-gubesch.de
    - Web: www.hbw-gubesch.de

APPLICATIONS IDENTIFIED FOR PF1:
- Well covers (Bulgaria)
- Skylights (Finland)
- Automotive parts (Austria, Portugal)
- Transport trays, germination trays (Germany)
- Bus seats (Russia)
- Shower panels (Italy)
- Snow pushers, trolleys (Finland)""",
        knowledge_type="lead",
        source_file=SOURCE_FILE,
        entity="K2016 European Leads",
        summary="17 leads from K2016 exhibition - Portugal, Bulgaria, Belgium, Finland, Serbia, Hungary, Austria, Germany, Russia, Romania, Italy",
        metadata={
            "event": "K2016",
            "location": "Düsseldorf, Germany",
            "lead_count": 17,
            "countries": ["Portugal", "Bulgaria", "Belgium", "Finland", "Serbia", "Hungary", "Austria", "Denmark", "Germany", "Russia", "Romania", "Italy"],
            "pf1_applications": ["well_covers", "skylights", "automotive", "transport_trays", "bus_seats", "shower_panels", "snow_pushers"]
        }
    ))

    # 2. ETD 2018 European Thermoformers Database
    items.append(KnowledgeItem(
        text="""ETD 2018 European Thermoformers Database:

THICK SHEET THERMOFORMERS (PF1 Targets):

1. Arthur Krugner - Germany
   - Contact: Nils Kruger (LinkedIn)
   - Focus: Thick Sheet, Automotive
   - Machine Type: PF1

2. Berbetores Industrial - Spain
   - Contact: Miguel Berbetores Gonzales
   - Focus: Thick Sheet, Automotive
   - Machine Type: PF1

3. C&K Plastics - USA
   - Contact: Robert Carrier
   - Focus: Thick Sheet
   - Machine Type: PF1

4. Durotherm Holding - Germany
   - Contact: Norbert Keck
   - Focus: Thick Sheet
   - Machine Type: PF1

5. Gibo Plast - Denmark
   - Contact: Lars Bering
   - Focus: Thick Sheet
   - Machine Type: PF1

6. Nelipak - Ireland
   - Contact: David McAndrew
   - Focus: Thick Sheet, Medical
   - Machine Type: PF1

7. Nycopac - Sweden
   - Contact: Gusten Bergmark
   - Focus: Thick Sheet, Pallets
   - Machine Type: PF1

8. Plexx AS - Norway
   - Contact: Arild Johnsen
   - Focus: Thick Sheet
   - Machine Type: PF1

9. Promens - Czech Republic
   - Contact: Zdenek Rajch
   - Focus: Thick Sheet, Automotive
   - Machine Type: PF1

10. Roncato - Italy
    - Contact: Cristiano Roncato
    - Focus: Thick Sheet, Luggage
    - Machine Type: PF1

11. Seaborne Plastics - United Kingdom
    - Contact: Martin Bollands
    - Focus: Thick Sheet
    - Machine Type: PF1

12. Solera Thermoform - Italy
    - Contact: Riccardo Palatresi
    - Focus: Thick Sheet, Agriculture
    - Machine Type: PF1

13. VDL Wientjes Roden - Netherlands
    - Contact: Chris Mulder
    - Focus: Thick Sheet
    - Machine Type: PF1

THIN SHEET THERMOFORMERS (FCS/Inline Targets):

1. August Benker - Germany
   - Contact: Anne Charlotte Schollhorn
   - Focus: Thin Sheet
   - Machine Type: FCS/Inline

2. Bachmann Forming - Switzerland
   - Contact: Reto Bachmann
   - Focus: Thin Sheet, Food Packaging
   - Machine Type: FCS

3. EstPak Plastik - Estonia
   - Contact: Marek Harjak
   - Focus: Thin Sheet
   - Machine Type: FCS/Inline

4. Faerch Plast - Denmark
   - Contact: Thomas Tang
   - Focus: Thin Sheet, CPET
   - Machine Type: FCS

5. Hordijk Verpakking - Netherlands
   - Contact: Fons Groenen
   - Focus: Thin Sheet, Packaging
   - Machine Type: FCS

6. Miko Pac - Belgium
   - Contact: IIja Leppens
   - Focus: Packaging
   - Machine Type: FCS

7. Neluplast - Germany
   - Contact: Florian Ennemoser
   - Focus: Thin Sheet, Packaging
   - Machine Type: FCS

8. Santis Packaging - Switzerland
   - Contact: Peter Bugajew
   - Focus: Thin Sheet, Packaging
   - Machine Type: FCS

9. Satatuote - Finland
   - Contact: Heikki Marva
   - Focus: Thin Sheet, Medical Packaging
   - Machine Type: FCS

10. Technoplast - France
    - Contact: Jean-Luc Payen
    - Focus: Thin Sheet
    - Machine Type: FCS/Inline

11. Thrace Plastics Pack - Greece
    - Contact: Ioannis Stathis
    - Focus: Packaging
    - Machine Type: FCS

12. Unipa Kunstoffen - Germany
    - Contact: Hedwig Herberger
    - Focus: Packaging, Trays
    - Machine Type: FCS

OTHER:
- Neon Art M (Russia) - Rustam Galiev""",
        knowledge_type="lead",
        source_file=SOURCE_FILE,
        entity="ETD 2018 European Database",
        summary="26 European thermoformers - 13 thick sheet (PF1 targets) and 12 thin sheet (FCS targets) companies",
        metadata={
            "source": "ETD 2018",
            "total_companies": 26,
            "thick_sheet_count": 13,
            "thin_sheet_count": 12,
            "pf1_target_countries": ["Germany", "Spain", "USA", "Denmark", "Ireland", "Sweden", "Norway", "Czech Republic", "Italy", "UK", "Netherlands"],
            "fcs_target_countries": ["Germany", "Switzerland", "Estonia", "Denmark", "Netherlands", "Belgium", "Finland", "France", "Greece"],
            "key_applications": ["automotive", "medical", "pallets", "luggage", "agriculture", "food_packaging", "CPET"]
        }
    ))

    # 3. Existing European Customers
    items.append(KnowledgeItem(
        text="""Machinecraft Existing Customers in Europe:

NETHERLANDS:
1. Batelaan
   - Contact: Mr. Kenrick Van Hoek
   - Machine: PF1 (multiple sizes)
   - Status: Active customer, reference account

HUNGARY:
2. Pro-form Kft.
   - Web: www.pro-form.hu
   - Contact: Mr. Helmajer Laszlo
   - Email: hl@pro-form.hu
   - Machine: PF-1/1000x1000

3. Polypack Kft. (2 machines)
   - Web: www.polypack.hu
   - Contact: Mr. Tamas Pajor
   - Email: polypack@t-online.hu
   - Machines:
     * PF-1/1500x1200
     * INLINE PRESSURE FORMING INP-5065

SWEDEN (8 customers):
4. Stegoplast
   - Web: www.stegoplast.se
   - Contact: Goran
   - Email: goran.bjarle@stegoplast.se
   - Machine: PF-1

5. Imatex (Belgium, but listed with Sweden group)
   - Web: www.imatex.be
   - Contact: Jaques
   - Email: info@imatex.be
   - Machine: PF-1 with Autoloader

6. Rhino
   - Web: www.rhino.se
   - Contact: Kenneth
   - Email: kenneth@rhino.se
   - Machine: PF-1

7. Dragon Company
   - Machine: PF-1

8. Cenova Innovation & Production AB
   - Web: http://cenova.se/
   - Machine: PF-1

9. Isotec I Mora AB
   - Web: https://www.isotec.se/
   - Machine: PF-1

10. Packit Sweden AB
    - Machine: PF-1

11. Fermproduketer AB
    - Machine: PF-1

12. BD Plastindustri AB
    - Web: http://www.bd-plastindustri.se/
    - Machine: PF-1

13. Anatomic Sitt AB
    - Web: http://www.anatomicsitt.com/en/
    - Email: rickard@anatomicsitt.com
    - Machine: PF-1

NORWAY:
14. BT Plast Halden A/S
    - Web: http://www.btplast.no/
    - Machine: PF-1

UNITED KINGDOM (6 customers):
15. World Panel Ltd.
    - Machine: PF-1

16. BI Composites Limited
    - Machine: PF-1

17. Artform
    - Machine: PF-1

18. MHP Industries Ltd.
    - Machine: PF-1

19. ABG Ltd.
    - Machine: PF-1

20. Phase 3 Plastics Ltd.
    - Machine: PF-1

21. Nelipack Ireland
    - Machine: PF-1 with Roll Feeder

ROMANIA:
22. Romind T&G SRL
    - Machine: PF-1

RUSSIA:
23. Pishche-Poli-Plast
    - Machine: INLINE PRESSURE FORMING INP-5065

BELGIUM:
24. Imatex
    - Machine: PF-1 with Autoloader

SUMMARY BY COUNTRY:
- Sweden: 10 customers (largest European market)
- UK: 7 customers
- Hungary: 2 customers (3 machines)
- Netherlands: 1 customer (reference)
- Norway: 1 customer
- Romania: 1 customer
- Russia: 1 customer
- Belgium: 1 customer

MACHINE TYPES SOLD:
- PF-1 (vacuum forming): 21 units
- PF-1 with Autoloader: 2 units
- PF-1 with Roll Feeder: 1 unit
- INP-5065 (inline pressure): 2 units

Total: ~26 machines to 24 European customers""",
        knowledge_type="client",
        source_file=SOURCE_FILE,
        entity="European Customer Base",
        summary="24 existing European customers - Sweden (10), UK (7), Hungary (2), others; primarily PF-1 machines",
        metadata={
            "total_customers": 24,
            "total_machines": 26,
            "top_market": "Sweden",
            "country_breakdown": {
                "Sweden": 10,
                "UK": 7,
                "Hungary": 2,
                "Netherlands": 1,
                "Norway": 1,
                "Romania": 1,
                "Russia": 1,
                "Belgium": 1
            },
            "machine_types": {
                "PF1": 21,
                "PF1_Autoloader": 2,
                "PF1_Roll_Feeder": 1,
                "INP_5065": 2
            }
        }
    ))

    # 4. European Market Analysis
    items.append(KnowledgeItem(
        text="""European Thermoforming Market Analysis (Based on K2016, ETD 2018, Customer Data):

MARKET SEGMENTATION:

1. THICK SHEET / HEAVY GAUGE (PF1 Market):
   - Automotive: Germany, Spain, Austria, Czech Republic, Portugal
   - Medical/Healthcare: Ireland, Finland
   - Industrial: Denmark, Norway, Netherlands, UK, Sweden
   - Agriculture: Italy
   - Consumer (Luggage): Italy
   - Building/Construction: Finland (skylights), Denmark (windows)

2. THIN SHEET / PACKAGING (FCS Market):
   - Food Packaging: Switzerland, Denmark, Netherlands
   - Medical Packaging: Finland
   - General Packaging: Germany, Belgium, Estonia, France, Greece

KEY GEOGRAPHIC INSIGHTS:

NORDIC REGION (Strong PF1 Market):
- Sweden: 10 existing customers - STRONGEST market
- Finland: Active leads (Kera, Motoseal, Satatuote)
- Denmark: Mix of thick (Gibo) and thin (Faerch)
- Norway: Growing (Plexx, BT Plast)

CENTRAL EUROPE:
- Germany: Large market, mix of thick/thin sheet
  * Key targets: Arthur Krugner, Durotherm, HBW Gubesch
- Austria: Automotive focus (Syntec)
- Switzerland: Food packaging (Bachmann, Santis)
- Czech Republic: Automotive (Promens)

WESTERN EUROPE:
- Netherlands: Reference customer (Batelaan), packaging (Hordijk, VDL)
- Belgium: Mixed (Vitalo, Miko Pac, Imatex)
- France: Thin sheet (Technoplast)
- UK: 7 existing customers, thick sheet industrial

SOUTHERN EUROPE:
- Italy: Thick sheet (Roncato-luggage, Solera-agriculture, Technoform-showers)
- Spain: Automotive (Berbetores)
- Portugal: Automotive/motorcycle (Polisport, Fibraline)
- Greece: Packaging (Thrace Plastics)

EASTERN EUROPE:
- Hungary: 2 customers, both PF1 and Inline
- Romania: Growing (Crisco, Romind)
- Bulgaria: Well covers (EcoPro)
- Serbia: EPS (Fima)
- Estonia: Thin sheet (EstPak)
- Russia: Bus seats, inline machines

SALES STRATEGY RECOMMENDATIONS:

1. EXPAND IN SWEDEN:
   - Already strongest market (10 customers)
   - Reference visits to Anatomic Sitt, Stegoplast
   - Target: 5 more PF1 sales

2. DEVELOP UK FURTHER:
   - 7 customers but no detailed contacts
   - Focus on automotive, medical
   - Nelipack Ireland shows medical potential

3. CRACK GERMANY:
   - Largest European market
   - Multiple leads but few customers
   - Partner with local agent
   - Target: Automotive tier suppliers

4. GROW SOUTHERN EUROPE:
   - Italy has diverse applications
   - Spain/Portugal: Automotive focus
   - Consider local service capability

5. EASTERN EUROPE OPPORTUNITY:
   - Hungary proven market
   - Romania, Bulgaria emerging
   - Price-sensitive but growing""",
        knowledge_type="market_intelligence",
        source_file=SOURCE_FILE,
        entity="European Market Analysis",
        summary="European market segmentation - Nordic strong for PF1, Germany largest untapped, clear thick/thin sheet segments",
        metadata={
            "analysis_sources": ["K2016", "ETD 2018", "Customer Data"],
            "strongest_market": "Sweden",
            "largest_opportunity": "Germany",
            "pf1_focus_regions": ["Nordic", "UK", "Central Europe"],
            "fcs_focus_regions": ["Germany", "Switzerland", "Benelux"],
            "recommended_actions": ["expand_sweden", "develop_uk", "crack_germany", "grow_southern_europe", "eastern_europe_opportunity"]
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("European Market Data Ingestion")
    print("Source: " + SOURCE_FILE)
    print("=" * 60)

    items = create_knowledge_items()

    print(f"\nCreated {len(items)} knowledge items:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.summary[:60]}...")

    ingestor = KnowledgeIngestor()
    results = ingestor.ingest_batch(items)

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
