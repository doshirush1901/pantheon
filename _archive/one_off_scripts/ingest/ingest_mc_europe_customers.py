#!/usr/bin/env python3
"""
Ingest MC Europe.xlsx - Complete European Customer Database

Contains all European machine sales from 2001-2025.
38 customers across 10 countries with €3.6M+ in total sales.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "MC Europe.xlsx"

EUROPEAN_CUSTOMERS = [
    {"id": 1, "client": "Mp3", "country": "Italy", "machine": "PF1-707", "year": 2025, "price": 80000},
    {"id": 2, "client": "DutchTides", "country": "Netherlands", "machine": "PF1-6019", "year": 2025, "price": 650000},
    {"id": 3, "client": "JoPlast", "country": "Denmark", "machine": "PF1-2015", "year": 2024, "price": 290000},
    {"id": 4, "client": "Thermic", "country": "Germany", "machine": "PF1-1616", "year": 2023, "price": 180000},
    {"id": 5, "client": "Soehner", "country": "Germany", "machine": "PF1-1318", "year": 2023, "price": 270000},
    {"id": 6, "client": "Plastochim", "country": "France", "machine": "PF1-0808", "year": 2022, "price": 65000},
    {"id": 7, "client": "Donite", "country": "Ireland", "machine": "PF1-0810", "year": 2022, "price": 90000},
    {"id": 8, "client": "Batelaan", "country": "Netherlands", "machine": "PF1-1315", "year": 2022, "price": 150000},
    {"id": 9, "client": "Anatomic Sitt", "country": "Sweden", "machine": "PF1-810", "year": 2022, "price": 70000},
    {"id": 10, "client": "Ridat", "country": "UK", "machine": "PF1-1015", "year": 2021, "price": 100000},
    {"id": 11, "client": "Batelaan", "country": "Netherlands", "machine": "PF1-1015", "year": 2019, "price": 140000},
    {"id": 12, "client": "Anatomic Sitt", "country": "Sweden", "machine": "PF-1000x1500", "year": 2017, "price": 90000},
    {"id": 13, "client": "Ridat", "country": "UK", "machine": "PF1-1010", "year": 2017, "price": 60000},
    {"id": 14, "client": "BD-Plastindustri AB", "country": "Sweden", "machine": "PF-1500x1500", "year": 2016, "price": 90000},
    {"id": 15, "client": "Ridat", "country": "UK", "machine": "PF1-1020", "year": 2016, "price": 80000},
    {"id": 16, "client": "Pro-form Kft.", "country": "Hungary", "machine": "PF-1/1000x1000", "year": 2015, "price": 60000},
    {"id": 17, "client": "Polypack Kft", "country": "Hungary", "machine": "PF-1/1500x1200", "year": 2014, "price": 70000},
    {"id": 18, "client": "Phase 3 Plastics Ltd.", "country": "UK", "machine": "PF-1", "year": 2014, "price": 65000},
    {"id": 19, "client": "MHP Industries Ltd.", "country": "UK", "machine": "PF-1", "year": 2013, "price": 75000},
    # NOTE: Forma Plast AB REMOVED - they have a second-hand Machinecraft machine, not a direct customer
    {"id": 21, "client": "World Panel Ltd.", "country": "UK", "machine": "PF-1", "year": 2012, "price": 60000},
    {"id": 22, "client": "Nelipack Ireland", "country": "UK", "machine": "PF-1 with Roll Feeder", "year": 2012, "price": 70000},
    {"id": 23, "client": "BI Composites Limited", "country": "UK", "machine": "PF-1", "year": 2012, "price": 80000},
    {"id": 24, "client": "BD-Plastindustri AB", "country": "Sweden", "machine": "PF1-0810", "year": 2011, "price": 70000},
    {"id": 25, "client": "Artform", "country": "UK", "machine": "PF-1", "year": 2010, "price": 60000},
    {"id": 26, "client": "ABG Ltd.", "country": "UK", "machine": "PF-1", "year": 2009, "price": 40000},
    {"id": 27, "client": "Stegoplast", "country": "Sweden", "machine": "PF-1", "year": 2008, "price": 70000},
    {"id": 28, "client": "Fermproduketer AB", "country": "Sweden", "machine": "PF-1", "year": 2008, "price": 60000},
    {"id": 29, "client": "Isotec i Mora AB", "country": "Sweden", "machine": "PF-1", "year": 2007, "price": 70000},
    {"id": 30, "client": "Dragon Company", "country": "Sweden", "machine": "PF-1", "year": 2007, "price": 50000},
    {"id": 31, "client": "Packit Sweden AB", "country": "Sweden", "machine": "PF-1", "year": 2006, "price": 80000},
    {"id": 32, "client": "Cenova Innovation & Production AB", "country": "Sweden", "machine": "PF-1", "year": 2006, "price": 70000},
    # NOTE: Romind T&G SRL REMOVED - not a confirmed customer
    {"id": 34, "client": "BT Plas AS", "country": "Sweden", "machine": "PF1-0913", "year": 2004, "price": 40000},
    {"id": 35, "client": "BT Plast Halden A/S", "country": "Norway", "machine": "PF-1", "year": 2004, "price": 80000},
    {"id": 36, "client": "Rhino AB", "country": "Sweden", "machine": "PF1-0913", "year": 2003, "price": 40000},
    {"id": 37, "client": "Allpryl AB", "country": "Sweden", "machine": "PF-1000x2000", "year": 2001, "price": 35000},
    {"id": 38, "client": "Imatex", "country": "Belgium", "machine": "PF-1 with Autoloader", "year": 2001, "price": 50000},
]


def create_knowledge_items() -> list[KnowledgeItem]:
    """Create structured knowledge items from European customer data."""
    items = []

    # Calculate totals by country
    by_country = {}
    for c in EUROPEAN_CUSTOMERS:
        country = c["country"]
        if country not in by_country:
            by_country[country] = {"count": 0, "revenue": 0, "customers": set()}
        by_country[country]["count"] += 1
        by_country[country]["revenue"] += c["price"]
        by_country[country]["customers"].add(c["client"])

    total_revenue = sum(c["price"] for c in EUROPEAN_CUSTOMERS)
    total_machines = len(EUROPEAN_CUSTOMERS)

    # 1. Overview
    country_summary = "\n".join([
        f"- {country}: {data['count']} machines, €{data['revenue']:,}, customers: {', '.join(sorted(data['customers']))}"
        for country, data in sorted(by_country.items(), key=lambda x: -x[1]['revenue'])
    ])

    items.append(KnowledgeItem(
        text=f"""MACHINECRAFT EUROPEAN CUSTOMER DATABASE (2001-2025)

SUMMARY:
- Total machines sold in Europe: {total_machines}
- Total revenue: €{total_revenue:,}
- Countries served: {len(by_country)}
- All machines CE-certified

BREAKDOWN BY COUNTRY:
{country_summary}

TOP 5 SALES BY VALUE:
1. DutchTides (Netherlands) - PF1-6019 - €650,000 (2025)
2. JoPlast (Denmark) - PF1-2015 - €290,000 (2024)
3. Soehner (Germany) - PF1-1318 - €270,000 (2023)
4. Thermic (Germany) - PF1-1616 - €180,000 (2023)
5. Batelaan (Netherlands) - PF1-1315 - €150,000 (2022)

REPEAT CUSTOMERS:
- Batelaan (Netherlands): 2 machines (2019, 2022) - key strategic partner
- Anatomic Sitt (Sweden): 2 machines (2017, 2022) - success story
- BD-Plastindustri AB (Sweden): 2 machines (2011, 2016)
- Ridat (UK): 3 machines (2016, 2017, 2021) - OEM partner

OLDEST CUSTOMERS (Still active references):
- Allpryl AB (Sweden) - since 2001, machine still running
- Imatex (Belgium) - since 2001""",
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary=f"Europe: {total_machines} machines, €{total_revenue:,}, {len(by_country)} countries (2001-2025)",
        metadata={
            "topic": "european_customer_overview",
            "total_machines": total_machines,
            "total_revenue_eur": total_revenue,
            "countries": list(by_country.keys())
        }
    ))

    # 2. Individual customer records by country
    for country, data in sorted(by_country.items(), key=lambda x: -x[1]['revenue']):
        customers_in_country = [c for c in EUROPEAN_CUSTOMERS if c["country"] == country]
        customers_in_country.sort(key=lambda x: -x["year"])

        customer_lines = "\n".join([
            f"- {c['client']}: {c['machine']} (€{c['price']:,}, {c['year']})"
            for c in customers_in_country
        ])

        items.append(KnowledgeItem(
            text=f"""MACHINECRAFT CUSTOMERS IN {country.upper()}

Total machines: {data['count']}
Total revenue: €{data['revenue']:,}

CUSTOMERS:
{customer_lines}""",
            knowledge_type="customer_intelligence",
            source_file=SOURCE_FILE,
            entity="Machinecraft",
            summary=f"{country}: {data['count']} machines, €{data['revenue']:,} - {', '.join(sorted(data['customers']))}",
            metadata={
                "topic": f"customers_{country.lower().replace(' ', '_')}",
                "country": country,
                "machine_count": data["count"],
                "revenue_eur": data["revenue"],
                "customers": list(data["customers"])
            }
        ))

    # 3. Complete customer list (detailed)
    all_customers_text = "\n".join([
        f"{c['id']}. {c['client']} ({c['country']}) - {c['machine']} - €{c['price']:,} ({c['year']})"
        for c in EUROPEAN_CUSTOMERS
    ])

    items.append(KnowledgeItem(
        text=f"""COMPLETE EUROPEAN CUSTOMER LIST - MACHINECRAFT (2001-2025)

{all_customers_text}

All machines are CE-certified for European market.
Data source: MC Europe.xlsx (official sales records)""",
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Complete list of 38 European customers with machine models and prices",
        metadata={
            "topic": "complete_european_customer_list",
            "total_records": len(EUROPEAN_CUSTOMERS)
        }
    ))

    return items


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("MC Europe Customer Database Ingestion")
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
