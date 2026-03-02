#!/usr/bin/env python3
"""
Ingest Clients MC EUROPE.xlsx - Additional European Client Contacts & Intelligence

Contains contacts for existing European clients with emails and notes.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

SOURCE_FILE = "Clients MC EUROPE.xlsx"

# European Client Contacts with notes
EUROPEAN_CLIENT_CONTACTS = [
    # Active contacts with emails
    {"name": "Lazlo / Helmajer Laszlo", "company": "Pro-form Kft", "country": "Hungary", 
     "email": "hl@pro-form.hu", "website": "www.pro-form.hu",
     "machine": "PF-1/1000x1000",
     "notes": "Client since 2002, but recently no contact and has taken machines from CMS. Needs re-engagement."},
    
    {"name": "Goran Bjarle", "company": "Stegoplast", "country": "Sweden",
     "email": "goran.bjarle@stegoplast.se", "website": "www.stegoplast.se",
     "machine": "PF-1", "notes": "Active Swedish customer"},
    
    {"name": "Jaques", "company": "Imatex", "country": "Belgium",
     "email": "info@imatex.be", "website": "www.imatex.be",
     "machine": "PF-1 with Autoloader", "notes": "Long-term Belgian customer"},
    
    {"name": "Kenneth", "company": "Rhino", "country": "Sweden",
     "email": "kenneth@rhino.se", "website": "www.rhino.se",
     "machine": "PF-1", "notes": "Active Swedish customer"},
    
    {"name": "Milan Tsaic", "company": "Fima", "country": "Serbia",
     "email": "tsaic.milan@gmail.com", "website": "www.fima.rs",
     "machine": "EPS Pallet", "notes": "Serbian contact - EPS/packaging focus"},
    
    {"name": "Zoltan Miszlai", "company": "Szkaliczki", "country": "Hungary",
     "email": "zoltan.miszlai@szkaliczki.hu", "website": "www.szkaliczki.hu",
     "notes": "Hungarian contact"},
    
    {"name": "Tamas Pajor", "company": "Polypack Kft", "country": "Hungary",
     "email": None, "website": "www.polypack.hu",
     "machine": "PF-1/1500x1200 + INP-5065",
     "notes": "Two machines - PF-1 and Inline Pressure Former. Repeat customer."},
    
    {"name": "Rickard", "company": "Anatomic Sitt AB", "country": "Sweden",
     "email": "rickard@anatomicsitt.com", "website": "www.anatomicsitt.com/en",
     "machine": "PF-1", "notes": "Ergonomic seating manufacturer"},
    
    # Key reference contacts (Netherlands)
    {"name": "Kenrick Van Hoek", "company": "Batelaan", "country": "Netherlands",
     "email": None, "website": None,
     "machine": "PF1-1015, PF1-1315",
     "notes": "⚠️ CLOSED 2026 - Company was sold and operations shut down. NOT AVAILABLE for reference visits."},
    
    {"name": "Jurriaan van den Bos, Jaap Van Pooy", "company": "Dutch Tides", "country": "Netherlands",
     "email": None, "website": None,
     "machine": "PF1-X-6520 (6x2m)",
     "notes": "PRIMARY Netherlands reference. Hydroponics startup near Den Haag. Excellent for factory visits."},
]

# Swedish customers (largest European market)
SWEDISH_CUSTOMERS = [
    "Stegoplast",
    "Rhino",
    "Dragon Company",
    "Cenova Innovation & Production AB",
    "Isotec i Mora AB",
    "Packit Sweden AB",
    "Fermprodukter AB",
    "BD Plastindustri AB",
    "Anatomic Sitt AB",
]

# UK customers
UK_CUSTOMERS = [
    "World Panel Ltd",
    "BI Composites Limited",
    "Artform",
    "MHP Industries Ltd",
    "ABG Ltd",
    "Phase 3 Plastics Ltd",
    "Nelipack Ireland",
]


def create_knowledge_items() -> list[KnowledgeItem]:
    items = []

    # 1. Contact directory
    contact_text = "EUROPEAN CLIENT CONTACTS DIRECTORY\n\n"
    for c in EUROPEAN_CLIENT_CONTACTS:
        if c.get("email"):
            contact_text += f"• {c['company']} ({c['country']})\n"
            contact_text += f"  Contact: {c['name']}\n"
            contact_text += f"  Email: {c['email']}\n"
            if c.get('website'):
                contact_text += f"  Website: {c['website']}\n"
            if c.get('machine'):
                contact_text += f"  Machine: {c['machine']}\n"
            if c.get('notes'):
                contact_text += f"  Notes: {c['notes']}\n"
            contact_text += "\n"

    items.append(KnowledgeItem(
        text=contact_text,
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="European client contact directory with emails",
        metadata={
            "topic": "client_contacts",
            "region": "Europe",
            "contact_count": len([c for c in EUROPEAN_CLIENT_CONTACTS if c.get("email")])
        }
    ))

    # 2. Sweden market overview
    sweden_text = f"""SWEDEN - LARGEST EUROPEAN MARKET FOR MACHINECRAFT

Total Swedish Customers: {len(SWEDISH_CUSTOMERS)}
All machines: PF-1 Series (Vacuum Forming)

Swedish Customer List:
"""
    for s in SWEDISH_CUSTOMERS:
        sweden_text += f"• {s}\n"
    
    sweden_text += """
Key Swedish Contacts:
• Goran Bjarle (Stegoplast) - goran.bjarle@stegoplast.se
• Kenneth (Rhino) - kenneth@rhino.se
• Rickard (Anatomic Sitt) - rickard@anatomicsitt.com

Sweden is Machinecraft's strongest European market by customer count."""

    items.append(KnowledgeItem(
        text=sweden_text,
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="Sweden",
        summary=f"Sweden: {len(SWEDISH_CUSTOMERS)} customers - largest European market",
        metadata={
            "topic": "market_overview",
            "country": "Sweden",
            "customer_count": len(SWEDISH_CUSTOMERS)
        }
    ))

    # 3. UK market overview
    uk_text = f"""UK CUSTOMERS - MACHINECRAFT

Total UK Customers: {len(UK_CUSTOMERS)}
All machines: PF-1 Series (Vacuum Forming)
Notable: Nelipack Ireland has PF-1 with Roll Feeder

UK Customer List:
"""
    for c in UK_CUSTOMERS:
        uk_text += f"• {c}\n"

    items.append(KnowledgeItem(
        text=uk_text,
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="UK",
        summary=f"UK: {len(UK_CUSTOMERS)} customers",
        metadata={
            "topic": "market_overview",
            "country": "UK",
            "customer_count": len(UK_CUSTOMERS)
        }
    ))

    # 4. Hungary - repeat customer note
    items.append(KnowledgeItem(
        text="""HUNGARY - REPEAT CUSTOMER EXAMPLE

Polypack Kft (www.polypack.hu) - Hungary
Contact: Tamas Pajor

MACHINES PURCHASED:
1. Vacuum Forming Machine Type-PF-1/1500x1200
2. INLINE PRESSURE FORMING MACHINE TYPE-INP-5065

Polypack is a great example of a repeat customer who expanded from vacuum forming 
to inline pressure forming. This is a common upsell path.

Note: Pro-form Kft (hl@pro-form.hu) was a 2002 customer but has since bought from CMS.
This is a win-back opportunity.""",
        knowledge_type="customer_intelligence",
        source_file=SOURCE_FILE,
        entity="Polypack Kft",
        summary="Hungary: Polypack bought 2 machines (PF-1 + INP-5065) - upsell example",
        metadata={
            "topic": "repeat_customer",
            "country": "Hungary",
            "machines": ["PF-1/1500x1200", "INP-5065"]
        }
    ))

    return items


def main():
    print("=" * 60)
    print("Ingesting Clients MC EUROPE.xlsx")
    print("=" * 60)

    items = create_knowledge_items()

    print(f"\nCreated {len(items)} knowledge items:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. [{item.knowledge_type}] {item.summary}")

    ingestor = KnowledgeIngestor()
    results = ingestor.ingest_batch(items)

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()
