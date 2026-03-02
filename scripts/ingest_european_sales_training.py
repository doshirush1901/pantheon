#!/usr/bin/env python3
"""
Ingest European Sales Training Data

This adds the extracted sales conversations from won European deals
to Ira's knowledge base for learning successful sales patterns.

Training data includes:
- 137 Q&A pairs from 14 European customers
- Sales stage classification (inquiry, technical, quote, negotiation, closing)
- Rushabh's winning techniques identified
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

PROJECT_ROOT = Path(__file__).parent.parent
SOURCE_FILE = "european_sales_training.json"


def load_training_data():
    """Load the extracted training data."""
    training_file = PROJECT_ROOT / "data" / "training" / "european_sales_training.json"
    with open(training_file) as f:
        return json.load(f)


def load_journeys_data():
    """Load the journey summaries."""
    journeys_file = PROJECT_ROOT / "data" / "training" / "european_sales_journeys.json"
    with open(journeys_file) as f:
        return json.load(f)


def create_knowledge_items(training_data, journeys_data) -> list[KnowledgeItem]:
    """Create knowledge items from training data."""
    items = []

    # 1. Overall sales techniques summary
    techniques_summary = """MACHINECRAFT EUROPEAN SALES WINNING TECHNIQUES

Based on analysis of 14 won deals totaling €3.9M+ across Europe (2001-2025).

KEY TECHNIQUES USED BY RUSHABH:

1. FACTORY VISIT INVITATIONS
   - Offer to take prospects to see machines running at existing customers
   - Example: "I'll pick you up at Amsterdam Airport and we can visit Batelaan together"
   - Used in: 11 of 14 deals

2. CUSTOMER REFERENCES BY GEOGRAPHY
   - Always mention nearby installations
   - Example: "We have 2 machines in Sweden, 1 in Denmark, 4 in UK, 3 in Netherlands..."
   - Creates credibility and reduces perceived risk

3. TRADE SHOW MEETINGS (K-SHOW)
   - Use K-show in Düsseldorf for relationship building
   - Schedule meetings well in advance
   - Used in: 8 of 14 deals

4. FLEXIBLE PRICING FOR STRATEGIC MARKETS
   - "Let's discuss your target price, we are keen to enter [country] market"
   - Willingness to negotiate for new market entry
   - Balance between price and reference value

5. DELIVERY COMMITMENT
   - Clear timeline promises
   - Milestone-based delivery tracking
   - Critical for European buyers

SALES CYCLE STAGES:
1. Inquiry → Quick response, establish credibility with references
2. Technical → Detailed specs, application knowledge, CE certification
3. Quote → Clear pricing with options, competitive positioning
4. Negotiation → Payment terms, delivery, training, warranty
5. Closing → PO request, advance payment, production start"""

    items.append(KnowledgeItem(
        text=techniques_summary,
        knowledge_type="sales_knowledge",
        source_file=SOURCE_FILE,
        entity="Machinecraft",
        summary="European sales techniques: factory visits, references, trade shows, flexible pricing",
        metadata={
            "topic": "european_sales_techniques",
            "deals_analyzed": 14,
            "total_value": 3900000,
        }
    ))

    # 2. Create knowledge items for each customer journey
    for journey in journeys_data.get("journeys", []):
        customer = journey["customer"]
        country = journey["country"]
        machine = journey["machine"]
        value = journey["deal_value"]
        techniques = journey.get("rushabh_techniques", [])
        stages = journey.get("stages_covered", [])

        journey_text = f"""SALES JOURNEY: {customer} ({country})

DEAL SUMMARY:
- Machine: {machine}
- Value: €{value:,}
- Year: {journey['deal_year']}
- Total emails: {journey['total_emails']}

SALES STAGES COVERED: {', '.join(stages)}

TECHNIQUES USED: {', '.join(techniques) if techniques else 'Standard follow-up'}

KEY INSIGHTS:
- {'Factory visit offered' if 'factory_visit_invitation' in techniques else 'No factory visit'}
- {'Customer references cited' if 'customer_reference' in techniques else 'Limited references'}
- {'Trade show meeting' if 'trade_show_meeting' in techniques else 'Direct outreach'}
- {'Special pricing discussed' if 'special_pricing' in techniques else 'Standard pricing'}
- {'Delivery commitment emphasized' if 'delivery_commitment' in techniques else 'Standard terms'}"""

        items.append(KnowledgeItem(
            text=journey_text,
            knowledge_type="sales_knowledge",
            source_file=SOURCE_FILE,
            entity=customer,
            summary=f"{customer} ({country}): €{value:,} - {machine}",
            metadata={
                "topic": f"sales_journey_{customer.lower().replace(' ', '_')}",
                "customer": customer,
                "country": country,
                "deal_value": value,
                "techniques": techniques,
            }
        ))

    # 3. Create Q&A training examples (sample best ones)
    examples = training_data.get("examples", [])
    
    # Group by stage and pick best examples
    stage_examples = {}
    for ex in examples:
        stage = ex.get("stage", "general")
        if stage not in stage_examples:
            stage_examples[stage] = []
        # Only include examples with substantial response
        if len(ex.get("rushabh_response", "")) > 100:
            stage_examples[stage].append(ex)

    for stage, exs in stage_examples.items():
        if not exs:
            continue
        
        # Take top 3 examples per stage
        top_examples = exs[:3]
        
        examples_text = f"""EUROPEAN SALES Q&A EXAMPLES - {stage.upper()} STAGE

"""
        for i, ex in enumerate(top_examples, 1):
            examples_text += f"""Example {i} ({ex['customer']}, {ex['country']} - €{ex['deal_value']:,}):

Customer message:
{ex['customer_message'][:400]}...

Rushabh's response:
{ex['rushabh_response'][:400]}...

---

"""

        items.append(KnowledgeItem(
            text=examples_text,
            knowledge_type="sales_knowledge",
            source_file=SOURCE_FILE,
            entity="Machinecraft",
            summary=f"Sales Q&A examples for {stage} stage ({len(top_examples)} examples)",
            metadata={
                "topic": f"sales_qa_{stage}",
                "stage": stage,
                "example_count": len(top_examples),
            }
        ))

    return items


def main():
    print("=" * 60)
    print("European Sales Training Data Ingestion")
    print("=" * 60)

    training_data = load_training_data()
    journeys_data = load_journeys_data()

    print(f"\nLoaded {training_data['total_examples']} training examples")
    print(f"Loaded {len(journeys_data['journeys'])} customer journeys")

    items = create_knowledge_items(training_data, journeys_data)

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
