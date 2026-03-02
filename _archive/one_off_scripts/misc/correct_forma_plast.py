#!/usr/bin/env python3
"""
CORRECTION: Forma Plast AB is NOT a direct Machinecraft customer.
They have a second-hand machine only.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem


def main():
    items = []

    items.append(KnowledgeItem(
        text="""CORRECTION: FORMA PLAST AB (Sweden) IS NOT A DIRECT CUSTOMER

⚠️ IMPORTANT CORRECTION:
Forma Plast AB in Ockelbo, Sweden is NOT a direct Machinecraft customer.

FACTS:
• They own a SECOND-HAND Machinecraft machine (PF-1/1000*1300/AL with feeder)
• They did NOT purchase directly from Machinecraft
• They have tried to SELL their used machine (their customer went bankrupt)
• Contact: Roine Andersson, VD/CEO - roine@formaplast.se
• Website: www.formaplast.se

STATUS: Lead only, not a customer
- Met at K2019 trade show
- Regular email contact for trade show invitations (Elmia, K-Show)
- They have not purchased a new machine from us

DO NOT count Forma Plast in:
• Customer references
• Sales cycle statistics
• European customer counts
• Revenue calculations

They remain a potential lead for future new machine sales.""",
        knowledge_type="customer_intelligence",
        source_file="correction_2026_02_28.md",
        entity="Forma Plast AB",
        summary="CORRECTION: Forma Plast is NOT a customer (has second-hand machine only)",
        metadata={
            "topic": "customer_correction",
            "status": "not_customer",
            "country": "Sweden",
            "priority": "high"
        }
    ))

    # Also correct the Swedish customer count
    items.append(KnowledgeItem(
        text="""CORRECTED SWEDISH CUSTOMER LIST (February 2026)

ACTUAL Swedish Machinecraft Customers (Direct Sales):
1. BD-Plastindustri AB - PF-1500x1500 (2016), PF-800x1000 (2011)
2. Anatomic Sitt AB - PF-1000x1500 (2016)
3. Rhino AB - Autoloader 900x1300 (2003)
4. Allpryl AB - PF-1000x2000 (2001)
5. Stegoplast - PF-1
6. Dragon Company - PF-1
7. Cenova Innovation & Production AB - PF-1
8. Isotec i Mora AB - PF-1
9. Packit Sweden AB - PF-1
10. Fermprodukter AB - PF-1

EXCLUDED (NOT direct customers):
• Forma Plast AB - Has second-hand machine, NOT a direct customer

Total Direct Swedish Customers: 10 (not 11)
Sweden remains Machinecraft's largest European market by customer count.""",
        knowledge_type="customer_intelligence",
        source_file="correction_2026_02_28.md",
        entity="Sweden",
        summary="CORRECTED: 10 Swedish customers (Forma Plast excluded - second-hand only)",
        metadata={
            "topic": "market_correction",
            "country": "Sweden",
            "customer_count": 10
        }
    ))

    print("=" * 60)
    print("CORRECTION: Forma Plast Status Update")
    print("=" * 60)
    print("\nForma Plast AB is NOT a direct customer.")
    print("They have a second-hand Machinecraft machine only.\n")

    ingestor = KnowledgeIngestor()
    results = ingestor.ingest_batch(items)

    print("\n✓ Correction ingested into knowledge base")
    return results


if __name__ == "__main__":
    main()
