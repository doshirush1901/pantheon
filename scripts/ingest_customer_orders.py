#!/usr/bin/env python3
"""
Ingest Customer Orders Data

This script ingests detailed customer order history from actual POs and quotations
into Ira's knowledge base for:
- Understanding real pricing benchmarks
- Learning customer application patterns
- Knowing delivery timelines and payment terms
- Reference installations by geography
- Machine specification patterns by use case

Data sources:
- Orders Data folder PDFs (POs, quotes, work orders)
- 15+ confirmed orders across India, Europe, UAE, Canada
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

PROJECT_ROOT = Path(__file__).parent.parent
SOURCE_FILE = "customer_orders.json"


def load_orders_data():
    """Load the customer orders data."""
    orders_file = PROJECT_ROOT / "data" / "knowledge" / "customer_orders.json"
    with open(orders_file) as f:
        return json.load(f)


def create_knowledge_items(orders_data) -> list[KnowledgeItem]:
    """Create knowledge items from orders data."""
    items = []

    # 1. Overall orders summary
    orders_summary = """MACHINECRAFT CUSTOMER ORDERS HISTORY (2020-2025)

SUMMARY:
- Total confirmed orders analyzed: 15+
- Geographic spread: India, UAE, UK, Germany, Italy, Sweden, Russia, Canada, Netherlands
- Machine types sold: PF1, PF2, IMG, UNO, FCS, AM Series
- Order value range: €70,000 to INR 3.94 Crore

KEY PRICING BENCHMARKS:

European Pricing (EUR):
- UNO-8060 (compact 800x600mm): €87,000
- PF1-1616/S/A (medium with autoloader 1600x1600mm): €189,000  
- PF1-750x75 (small): €70,000

Indian Pricing (INR):
- PF1-2010 (bathtub 2000x1000mm): ₹28 Lakhs
- IMG-1608 (automotive): ₹1.9 Crore
- PF1-5028 XL (5000x2800mm): ₹3.94 Crore

STANDARD PAYMENT TERMS:
- 25-30% advance with PO/LC
- 65-70% before dispatch / at FAT
- 5-10% after successful installation
- European: Often staged (30/25/25/15/5)
- Large orders: May include PBG (Performance Bank Guarantee)

LEAD TIME PATTERNS:
- Small machines (UNO): 8-16 weeks
- Medium PF1: 16-24 weeks
- Large/XL machines: 20-28 weeks
- IMG machines: 24-28 weeks

WARRANTY:
- Standard: 12-24 months from installation
- Excludes: Consumables, power damage, improper handling"""

    items.append(KnowledgeItem(
        text=orders_summary,
        knowledge_type="pricing",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Customer orders summary: 15+ orders across 9 countries, pricing benchmarks",
        metadata={
            "topic": "orders_summary",
            "orders_analyzed": 15,
            "countries": 9,
        }
    ))

    # 2. Create knowledge item for each order
    for order in orders_data.get("orders", []):
        customer = order["customer"]
        machine = order["machine_model"]
        country = order["country"]
        year = order["year"]
        forming_area = order.get("forming_area_mm", "N/A")
        application = order.get("application", "General thermoforming")
        value = order.get("value")
        currency = order.get("currency", "")
        lead_time = order.get("lead_time_weeks", "TBD")
        payment = order.get("payment_terms", "Standard")
        warranty = order.get("warranty_months", 12)
        key_specs = order.get("key_specs", {})

        # Format value string
        if value:
            if currency == "EUR":
                value_str = f"€{value:,}"
            elif currency == "INR":
                if value >= 10000000:
                    value_str = f"₹{value/10000000:.2f} Crore"
                elif value >= 100000:
                    value_str = f"₹{value/100000:.1f} Lakhs"
                else:
                    value_str = f"₹{value:,}"
            else:
                value_str = f"{currency} {value:,}"
        else:
            value_str = "Price on request"

        # Build specs string
        specs_lines = []
        for key, val in key_specs.items():
            formatted_key = key.replace("_", " ").title()
            if isinstance(val, bool):
                if val:
                    specs_lines.append(f"- {formatted_key}: Yes")
            else:
                specs_lines.append(f"- {formatted_key}: {val}")
        specs_str = "\n".join(specs_lines) if specs_lines else "- Standard configuration"

        order_text = f"""CONFIRMED ORDER: {customer} ({country}, {year})

MACHINE: {machine}
FORMING AREA: {forming_area} mm
APPLICATION: {application}
ORDER VALUE: {value_str}

TECHNICAL SPECIFICATIONS:
{specs_str}

COMMERCIAL TERMS:
- Lead Time: {lead_time} weeks
- Payment: {payment}
- Warranty: {warranty} months

REFERENCE: This is a confirmed order from {customer} in {country}. 
The {machine} was supplied for {application.lower()} application."""

        items.append(KnowledgeItem(
            text=order_text,
            knowledge_type="customer",
            source_file=SOURCE_FILE,
            entity=customer,
            summary=f"{customer} ({country}): {machine} for {application}",
            metadata={
                "topic": f"order_{customer.lower().replace(' ', '_')}",
                "customer": customer,
                "country": country,
                "machine_model": machine,
                "year": year,
                "application": application,
                "value": value,
                "currency": currency,
            }
        ))

    # 3. Create geographic reference summary
    orders = orders_data.get("orders", [])
    
    # Group by country
    country_orders = {}
    for order in orders:
        country = order["country"]
        if country not in country_orders:
            country_orders[country] = []
        country_orders[country].append(order)

    geo_text = """MACHINECRAFT GLOBAL INSTALLATIONS BY GEOGRAPHY

REFERENCE INSTALLATIONS FOR SALES CONVERSATIONS:

"""
    for country, country_order_list in sorted(country_orders.items()):
        geo_text += f"\n{country.upper()}:\n"
        for order in country_order_list:
            geo_text += f"- {order['customer']}: {order['machine_model']} ({order['year']}) - {order.get('application', 'N/A')}\n"

    geo_text += """
USE IN SALES:
- Cite nearby installations to build credibility
- Offer factory visits to see machines running
- Reference similar applications when prospecting
- Use K-show meetings for relationship building"""

    items.append(KnowledgeItem(
        text=geo_text,
        knowledge_type="sales_knowledge",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Geographic reference installations for sales conversations",
        metadata={
            "topic": "geographic_references",
            "countries": list(country_orders.keys()),
        }
    ))

    # 4. Application-based knowledge
    app_groups = {}
    for order in orders:
        app = order.get("application", "General")
        if app not in app_groups:
            app_groups[app] = []
        app_groups[app].append(order)

    app_text = """MACHINECRAFT MACHINES BY APPLICATION

PROVEN APPLICATIONS WITH CONFIRMED ORDERS:

"""
    for app, app_orders in sorted(app_groups.items()):
        app_text += f"\n{app.upper()}:\n"
        for order in app_orders:
            specs = order.get("key_specs", {})
            app_text += f"- {order['machine_model']} for {order['customer']} ({order['country']})\n"
            if "production_rate" in specs:
                app_text += f"  Production: {specs['production_rate']}\n"
            if "cycle_time_seconds" in specs:
                app_text += f"  Cycle time: {specs['cycle_time_seconds']} seconds\n"

    items.append(KnowledgeItem(
        text=app_text,
        knowledge_type="application",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Machines grouped by application with proven references",
        metadata={
            "topic": "applications_reference",
            "applications": list(app_groups.keys()),
        }
    ))

    # 5. Component suppliers reference
    components = orders_data.get("standard_components", {})
    comp_text = """MACHINECRAFT STANDARD COMPONENT SUPPLIERS

All machines use premium components from established suppliers:

"""
    for comp_type, suppliers in components.items():
        formatted_type = comp_type.replace("_", " ").title()
        if isinstance(suppliers, list):
            comp_text += f"{formatted_type}:\n"
            for i, supplier in enumerate(suppliers):
                priority = "Primary" if i == 0 else "Secondary"
                comp_text += f"  - {supplier} ({priority})\n"
        comp_text += "\n"

    comp_text += """
QUALITY ASSURANCE:
- All electrical components meet CE standards
- UL/CSA compliance available for North America
- German/European brands preferred for reliability
- Japanese automation for precision"""

    items.append(KnowledgeItem(
        text=comp_text,
        knowledge_type="machine_spec",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="Standard component suppliers: Mitsubishi, Siemens, FESTO, etc.",
        metadata={
            "topic": "component_suppliers",
        }
    ))

    # 6. Automotive industry orders (key vertical)
    auto_orders = [o for o in orders if "automotive" in o.get("application", "").lower() 
                   or "IMG" in o.get("machine_type", "")]
    
    if auto_orders:
        auto_text = """MACHINECRAFT AUTOMOTIVE INDUSTRY ORDERS

KEY AUTOMOTIVE CUSTOMERS & INSTALLATIONS:

"""
        for order in auto_orders:
            auto_text += f"""
{order['customer']} ({order['country']}):
- Machine: {order['machine_model']}
- Application: {order.get('application', 'Automotive parts')}
- Year: {order['year']}
- Key specs: {', '.join([f"{k}: {v}" for k, v in order.get('key_specs', {}).items()][:3])}
"""

        auto_text += """
AUTOMOTIVE SEGMENT INSIGHTS:
- IMG machines for soft-feel interior parts
- PF1 for instrument panels, door panels
- Typical lead time: 24-28 weeks
- Payment often includes PBG
- Siemens PLC preferred by auto OEMs"""

        items.append(KnowledgeItem(
            text=auto_text,
            knowledge_type="customer",
            source_file=SOURCE_FILE,
            entity="Machinecraft Automotive",
            summary="Automotive industry orders: IAC, PSG, Premier Plasmotec",
            metadata={
                "topic": "automotive_orders",
                "segment": "automotive",
            }
        ))

    return items


def main():
    print("=" * 60)
    print("Customer Orders Data Ingestion")
    print("=" * 60)

    orders_data = load_orders_data()

    print(f"\nLoaded {len(orders_data.get('orders', []))} customer orders")
    print(f"Countries: {', '.join(orders_data['metadata']['countries'])}")

    items = create_knowledge_items(orders_data)

    print(f"\nCreated {len(items)} knowledge items:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.summary[:55]}...")

    print("\nIngesting to Qdrant and Mem0...")
    ingestor = KnowledgeIngestor()
    results = ingestor.ingest_batch(items)

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    
    # Summary
    if results:
        print(f"Qdrant main: {results.qdrant_main}")
        print(f"Qdrant discovered: {results.qdrant_discovered}")
        print(f"Mem0: {results.mem0}")
        print(f"Neo4j: {results.neo4j}")

    return results


if __name__ == "__main__":
    main()
