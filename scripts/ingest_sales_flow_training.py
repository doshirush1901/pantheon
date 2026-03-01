#!/usr/bin/env python3
"""
Ingest Sales Flow Training Data into Ira's Knowledge Base

This loads:
1. Sales flow diagram and stage transitions
2. Stage detection training examples
3. Action recommendations for each stage
"""

import json
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

def main():
    ingestor = KnowledgeIngestor()
    items = []
    
    # 1. Load and ingest the flow diagram
    flow_diagram_path = PROJECT_ROOT / "data" / "knowledge" / "sales_flow_diagram.md"
    with open(flow_diagram_path) as f:
        flow_diagram = f.read()
    
    items.append(KnowledgeItem(
        text=flow_diagram,
        knowledge_type="sales_process",
        source_file=str(flow_diagram_path),
        entity="European Sales Flow",
        summary="""Complete sales flow diagram showing the progression from First Contact to Won deal.
Key stages: first_contact → discovery → technical → quote_request → quote_sent → factory_visit → negotiation → closing → won.
Factory visit is a powerful accelerator - deals with factory visits close 2-3x faster.
Average cycle: 6-12 months. Fast deals: 2-3 months. Long deals: 22+ months.""",
        metadata={
            "total_stages": 14,
            "total_transitions_analyzed": 234,
            "customers_analyzed": 5,
            "stages": [
                "first_contact", "discovery", "technical", "quote_request", "quote_sent",
                "factory_visit_offer", "factory_visit_confirmed", "post_visit_followup",
                "quote_followup", "negotiation", "objection_handling", "revised_quote",
                "closing", "won", "nurture"
            ],
            "key_accelerators": ["factory_visit", "reference_site_tour", "technical_deep_dive"]
        }
    ))
    
    # 2. Load and ingest stage definitions
    stage_training_path = PROJECT_ROOT / "data" / "training" / "sales_stage_training.json"
    with open(stage_training_path) as f:
        stage_training = json.load(f)
    
    stage_text = json.dumps(stage_training["stage_definitions"], indent=2)
    items.append(KnowledgeItem(
        text=stage_text,
        knowledge_type="sales_stage_classifier",
        source_file=str(stage_training_path),
        entity="Sales Stage Detection",
        summary="""Training data for classifying which stage a sales conversation is in.
Use pattern matching on subject and body to detect: first_contact, discovery, technical, 
quote_request, quote_sent, factory_visit_offer, negotiation, objection_handling, closing.
Key patterns: trade show/K-show for first_contact, specifications/dimensions for technical,
pricing/cost/budget for quote_request, discount/terms for negotiation, PO/proforma for closing.""",
        metadata={
            "stage_definitions": stage_training["stage_definitions"],
            "classification_examples": stage_training.get("stage_detection_training", [])[:20]
        }
    ))
    
    # 3. Load and ingest action recommendations
    action_training_path = PROJECT_ROOT / "data" / "training" / "sales_action_training.json"
    with open(action_training_path) as f:
        action_training = json.load(f)
    
    action_text = json.dumps(action_training["actions"], indent=2)
    items.append(KnowledgeItem(
        text=action_text,
        knowledge_type="sales_actions",
        source_file=str(action_training_path),
        entity="Sales Action Recommendations",
        summary="""Recommended actions for each sales stage based on successful European deals.
first_contact: Send introduction + video + offer call
discovery: Ask qualifying questions (application, material, volume, timeline)
technical: Provide specs, case studies, offer reference call
quote_request: Prepare quote within 24-48 hours
quote_sent: Confirm receipt, offer walkthrough call
factory_visit_offer: Invite to Dutch Tides or India factory
quote_followup: Check in, answer questions
negotiation: Understand position, offer value-adds
objection_handling: Address with facts, references, demonstration
closing: Facilitate with proforma, payment terms, timeline""",
        metadata={
            "actions": action_training["actions"],
            "source": action_training["source"]
        }
    ))
    
    # 4. Create individual stage knowledge items for quick retrieval
    for action in action_training["actions"]:
        stage_guide_text = f"""Sales Stage: {action['stage'].replace('_', ' ').title()}
Description: {action['stage_description']}
Recommended Action: {action['recommended_action']}
Example Response: {action['example_response']}
Typical Next Stages: {', '.join(action['next_stages'])}"""
        
        items.append(KnowledgeItem(
            text=stage_guide_text,
            knowledge_type="sales_stage_guide",
            source_file=str(action_training_path),
            entity=f"Stage: {action['stage']}",
            summary=stage_guide_text,
            metadata={
                "stage": action["stage"],
                "next_stages": action["next_stages"]
            }
        ))
    
    # 5. Load actual flow patterns for learning
    flow_patterns_path = PROJECT_ROOT / "data" / "training" / "sales_flow_patterns.json"
    with open(flow_patterns_path) as f:
        flow_patterns = json.load(f)
    
    # Create customer-specific journey examples
    for flow in flow_patterns["flows"]:
        if flow["transitions"]:
            journey_text = f"""Sales Journey: {flow['customer']}
Total emails: {flow['total_emails']}
Stages visited: {', '.join(flow['stages_visited'])}
Stage transitions: {len(flow['transitions'])}

Sample transitions:
""" + "\n".join([
                f"  {t['date']}: {t['from_stage']} → {t['to_stage']} ({t['triggered_by']})"
                for t in flow['transitions'][:10]
            ])
            
            items.append(KnowledgeItem(
                text=journey_text,
                knowledge_type="sales_journey_example",
                source_file=str(flow_patterns_path),
                entity=f"Sales Journey: {flow['customer']}",
                summary=f"""Complete sales journey for {flow['customer']}.
Total emails: {flow['total_emails']}
Stages visited: {', '.join(flow['stages_visited'])}
Number of stage transitions: {len(flow['transitions'])}""",
                metadata={
                    "customer": flow["customer"],
                    "transitions": flow["transitions"][:20],
                    "timeline_sample": flow["timeline"][:15]
                }
            ))
    
    # 6. Create transition pattern training
    common_patterns = [
        {
            "pattern": "first_contact → discovery → technical → quote_request → closing",
            "description": "Fast-track pattern for technically savvy buyers",
            "typical_duration": "2-4 months",
            "success_rate": "High when customer has clear requirements"
        },
        {
            "pattern": "first_contact → discovery → technical → factory_visit → negotiation → closing",
            "description": "Standard pattern with factory visit accelerator",
            "typical_duration": "4-8 months",
            "success_rate": "Very high - factory visits convert well"
        },
        {
            "pattern": "first_contact → nurture → discovery → technical → quote_request → closing",
            "description": "Long-cycle pattern for budget-constrained buyers",
            "typical_duration": "12-24 months",
            "success_rate": "Good with persistent nurturing"
        },
        {
            "pattern": "technical → objection_handling → factory_visit → closing",
            "description": "Objection recovery pattern",
            "typical_duration": "Varies (depends on objection resolution)",
            "success_rate": "Moderate - depends on objection type"
        }
    ]
    
    patterns_text = """Most common successful sales patterns from European deals:

1. FAST-TRACK: first_contact → discovery → technical → quote → closing (2-4 months)
   Best for: Technically savvy buyers with clear requirements and budget

2. STANDARD w/ VISIT: first_contact → discovery → technical → factory_visit → closing (4-8 months)
   Best for: High-value deals, skeptical buyers, competitive situations

3. LONG-CYCLE: first_contact → nurture → discovery → technical → closing (12-24 months)
   Best for: Budget-constrained buyers, market development

4. OBJECTION RECOVERY: technical → objection_handling → factory_visit → closing
   Use when: Customer hesitates, mentions competitors, delays decision

KEY INSIGHT: Factory visit is the most powerful accelerator for moving deals forward.
Reference sites: Dutch Tides (Netherlands), Dezet (Netherlands), India factory"""
    
    items.append(KnowledgeItem(
        text=patterns_text,
        knowledge_type="sales_patterns",
        source_file=str(flow_patterns_path),
        entity="Common Sales Patterns",
        summary="""Most common successful sales patterns from European deals:
1. FAST-TRACK: first_contact → discovery → technical → quote → closing (2-4 months)
2. STANDARD w/ VISIT: first_contact → discovery → technical → factory_visit → closing (4-8 months)
3. LONG-CYCLE: first_contact → nurture → discovery → technical → closing (12-24 months)
4. OBJECTION RECOVERY: technical → objection_handling → factory_visit → closing

Key insight: Factory visit is the most powerful accelerator for moving deals forward.""",
        metadata={
            "patterns": common_patterns,
            "key_insight": "Factory visits to reference sites (Dutch Tides, Dezet) accelerate deals significantly"
        }
    ))
    
    # Ingest all items
    print(f"Ingesting {len(items)} knowledge items...")
    ingestor.ingest_batch(items)
    print("✓ Sales flow training data ingested successfully")
    
    # Summary
    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    print(f"Total items ingested: {len(items)}")
    print("\nItem breakdown:")
    print("  - 1 x Sales Flow Diagram")
    print("  - 1 x Stage Detection Training")
    print("  - 1 x Action Recommendations")
    print(f"  - {len(action_training['actions'])} x Individual Stage Guides")
    print(f"  - {len(flow_patterns['flows'])} x Customer Journey Examples")
    print("  - 1 x Common Sales Patterns")


if __name__ == "__main__":
    main()
