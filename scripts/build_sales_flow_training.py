#!/usr/bin/env python3
"""
Build Sales Flow Training Data from Email Patterns

This script:
1. Extracts actual stage transitions from email threads
2. Identifies common patterns across successful deals
3. Generates a Mermaid flow diagram
4. Creates training examples for each stage/transition
5. Builds Q&A pairs teaching Ira how to handle each stage

Output:
- sales_flow_diagram.md - Visual Mermaid diagram
- sales_flow_training.json - Stage-based training data
- sales_stage_classifier_training.json - Examples to classify conversation stage
"""

import json
import re
import base64
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

PROJECT_ROOT = Path(__file__).parent.parent

# Verified European customers with complete email history
CUSTOMERS = [
    {"client": "DutchTides", "search_terms": ["dutchtides", "dutch tides", "jurriaan"], 
     "first_contact": "2022-09", "order": "2024-07", "value": 650000},
    {"client": "JoPlast", "search_terms": ["joplast", "jo plast"], 
     "first_contact": "2022-10", "order": "2023-05", "value": 290000},
    {"client": "Batelaan", "search_terms": ["batelaan", "kenrick"], 
     "first_contact": "2022-10", "order": "2022-12", "value": 150000},
    {"client": "Thermic", "search_terms": ["thermic"], 
     "first_contact": "2022-05", "order": "2023-12", "value": 180000},
    {"client": "Donite", "search_terms": ["donite"], 
     "first_contact": "2023-04", "order": "2024-06", "value": 90000},
]

# Sales stages with detection patterns
STAGES = {
    "first_contact": {
        "patterns": [r"introduction", r"first time", r"k2022", r"k-show", r"met at", r"trade show", 
                    r"found you", r"interested in.*machine"],
        "description": "Initial contact - trade show, website, referral",
        "next_stages": ["discovery", "nurture"],
    },
    "discovery": {
        "patterns": [r"what.*application", r"what.*produce", r"tell me about", r"your requirements",
                    r"material", r"sheet size", r"production volume"],
        "description": "Understanding customer needs and application",
        "next_stages": ["technical", "quote_request"],
    },
    "technical": {
        "patterns": [r"specification", r"spec sheet", r"forming area", r"heater", r"servo", 
                    r"cycle time", r"dimension", r"capacity", r"technical.*question"],
        "description": "Technical discussions and specification matching",
        "next_stages": ["quote_request", "factory_visit_offer"],
    },
    "quote_request": {
        "patterns": [r"request.*quote", r"rfq", r"pricing", r"cost", r"budget", r"how much",
                    r"send.*quote", r"need.*quotation"],
        "description": "Customer requests pricing/quotation",
        "next_stages": ["quote_sent"],
    },
    "quote_sent": {
        "patterns": [r"quote.*attached", r"quotation.*sent", r"offer.*attached", r"MT\d{10}",
                    r"please find.*quote", r"pricing.*document"],
        "description": "Quote delivered to customer",
        "next_stages": ["quote_followup", "factory_visit_offer", "negotiation"],
    },
    "factory_visit_offer": {
        "patterns": [r"factory visit", r"visit.*factory", r"see.*machine", r"demonstration",
                    r"come to india", r"visit.*netherlands", r"dutch tides", r"reference site"],
        "description": "Offering factory visit or reference site tour",
        "next_stages": ["factory_visit_confirmed", "quote_followup"],
    },
    "factory_visit_confirmed": {
        "patterns": [r"visit confirmed", r"booking.*flight", r"travel.*india", r"looking forward.*visit",
                    r"accommodation", r"pick.*airport"],
        "description": "Factory visit scheduled",
        "next_stages": ["post_visit_followup"],
    },
    "post_visit_followup": {
        "patterns": [r"thank.*visit", r"after.*visit", r"enjoyed.*meeting", r"as discussed",
                    r"following.*visit", r"great.*meet"],
        "description": "Follow-up after factory visit",
        "next_stages": ["negotiation", "revised_quote"],
    },
    "quote_followup": {
        "patterns": [r"follow.*up", r"checking in", r"any.*questions", r"thoughts.*quote",
                    r"received.*quote", r"review.*offer"],
        "description": "Following up on sent quote",
        "next_stages": ["negotiation", "objection_handling", "nurture"],
    },
    "negotiation": {
        "patterns": [r"discount", r"reduce.*price", r"payment.*term", r"delivery.*time",
                    r"warranty", r"installation", r"training", r"negotiate"],
        "description": "Price/terms negotiation",
        "next_stages": ["revised_quote", "closing", "objection_handling"],
    },
    "objection_handling": {
        "patterns": [r"concern", r"hesitant", r"not sure", r"competitor", r"cms", r"illig",
                    r"cheaper", r"alternative", r"delay.*decision"],
        "description": "Handling customer objections/concerns",
        "next_stages": ["negotiation", "factory_visit_offer", "nurture"],
    },
    "revised_quote": {
        "patterns": [r"revised.*quote", r"updated.*offer", r"new.*pricing", r"adjusted.*price",
                    r"special.*offer", r"revised.*proposal"],
        "description": "Sending revised quotation",
        "next_stages": ["closing", "negotiation"],
    },
    "closing": {
        "patterns": [r"purchase order", r"\bpo\b", r"proceed", r"confirm.*order", r"accept.*offer",
                    r"bank guarantee", r"\bbg\b", r"proforma", r"advance payment"],
        "description": "Order confirmation and closing",
        "next_stages": ["won"],
    },
    "won": {
        "patterns": [r"order.*confirmed", r"payment.*received", r"production.*started",
                    r"thank.*order", r"welcome.*machinecraft"],
        "description": "Deal won - order confirmed",
        "next_stages": [],
    },
    "nurture": {
        "patterns": [r"keep.*touch", r"check.*later", r"next year", r"budget.*cycle",
                    r"not.*ready", r"future", r"stay.*contact"],
        "description": "Long-term nurturing for not-ready prospects",
        "next_stages": ["discovery", "quote_request"],
    },
}


def get_gmail_service():
    token_path = PROJECT_ROOT / "token_rushabh.json"
    creds = Credentials.from_authorized_user_file(str(token_path))
    return build('gmail', 'v1', credentials=creds)


def parse_date(date_str):
    formats = ["%a, %d %b %Y %H:%M:%S %z", "%d %b %Y %H:%M:%S %z"]
    date_str = re.sub(r'\s+\([A-Z]+\)', '', date_str.strip())
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def detect_stage(subject, body):
    """Detect the sales stage from email content."""
    text = (subject + " " + body).lower()
    
    stage_scores = {}
    for stage, config in STAGES.items():
        score = 0
        for pattern in config["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                score += 1
        if score > 0:
            stage_scores[stage] = score
    
    if stage_scores:
        return max(stage_scores, key=stage_scores.get)
    return "general"


def get_body(payload):
    body = ''
    if 'body' in payload and payload['body'].get('data'):
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
    elif 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                break
            elif 'parts' in part:
                for subpart in part['parts']:
                    if subpart.get('mimeType') == 'text/plain' and subpart.get('body', {}).get('data'):
                        body = base64.urlsafe_b64decode(subpart['body']['data']).decode('utf-8', errors='ignore')
                        break
    return body[:1500]  # Limit for processing


def extract_customer_flow(service, customer):
    """Extract the stage flow for a customer's email thread."""
    all_messages = []
    
    for term in customer['search_terms']:
        try:
            results = service.users().messages().list(
                userId='me', q=f'"{term}"', maxResults=100
            ).execute()
            
            for msg_ref in results.get('messages', []):
                if msg_ref['id'] not in [m['id'] for m in all_messages]:
                    try:
                        msg = service.users().messages().get(
                            userId='me', id=msg_ref['id'], format='full'
                        ).execute()
                        
                        headers = {h['name'].lower(): h['value'] 
                                  for h in msg['payload'].get('headers', [])}
                        
                        date = parse_date(headers.get('date', ''))
                        if not date:
                            continue
                        
                        from_addr = headers.get('from', '')
                        subject = headers.get('subject', '')
                        body = get_body(msg['payload'])
                        
                        is_rushabh = 'rushabh' in from_addr.lower() or 'machinecraft' in from_addr.lower()
                        stage = detect_stage(subject, body)
                        
                        all_messages.append({
                            'id': msg_ref['id'],
                            'date': date,
                            'from': 'Rushabh' if is_rushabh else 'Customer',
                            'subject': subject,
                            'body_preview': body[:300],
                            'stage': stage,
                        })
                    except Exception:
                        continue
        except Exception:
            continue
    
    # Sort by date
    all_messages.sort(key=lambda x: x['date'])
    
    # Extract stage transitions
    transitions = []
    prev_stage = None
    
    for msg in all_messages:
        if msg['stage'] != 'general' and msg['stage'] != prev_stage:
            transitions.append({
                'date': msg['date'].strftime('%Y-%m-%d'),
                'from_stage': prev_stage or 'start',
                'to_stage': msg['stage'],
                'trigger_subject': msg['subject'],
                'triggered_by': msg['from'],
                'example_content': msg['body_preview'][:200]
            })
            prev_stage = msg['stage']
    
    return {
        'customer': customer['client'],
        'total_emails': len(all_messages),
        'stages_visited': list(set(m['stage'] for m in all_messages if m['stage'] != 'general')),
        'transitions': transitions,
        'timeline': [
            {'date': m['date'].strftime('%Y-%m-%d'), 'stage': m['stage'], 
             'from': m['from'], 'subject': m['subject'][:40]}
            for m in all_messages if m['stage'] != 'general'
        ][:30]  # First 30 relevant emails
    }


def build_flow_diagram(all_flows):
    """Build a Mermaid diagram from extracted flows."""
    # Count transitions
    transition_counts = Counter()
    for flow in all_flows:
        for t in flow['transitions']:
            key = (t['from_stage'], t['to_stage'])
            transition_counts[key] += 1
    
    diagram = """# European Sales Flow Diagram

Based on analysis of {} successful deals.

```mermaid
flowchart TD
    subgraph "AWARENESS"
        A[First Contact<br/>Trade Show / Website / Referral]
    end
    
    subgraph "DISCOVERY"
        B[Discovery<br/>Understanding Needs]
        C[Technical Discussion<br/>Specs & Requirements]
    end
    
    subgraph "PROPOSAL"
        D[Quote Request]
        E[Quote Sent]
        F[Factory Visit Offer]
        G[Factory Visit]
    end
    
    subgraph "NEGOTIATION"
        H[Quote Follow-up]
        I[Negotiation<br/>Price & Terms]
        J[Objection Handling]
        K[Revised Quote]
    end
    
    subgraph "CLOSE"
        L[Closing<br/>PO / BG / Payment]
        M[WON 🎉]
    end
    
    subgraph "NURTURE"
        N[Long-term Nurture]
    end
    
    A --> B
    A --> N
    B --> C
    B --> D
    C --> D
    C --> F
    D --> E
    E --> F
    E --> H
    E --> I
    F --> G
    G --> I
    H --> I
    H --> J
    H --> N
    I --> K
    I --> L
    J --> F
    J --> I
    J --> N
    K --> I
    K --> L
    L --> M
    N --> B
    N --> D
    
    style M fill:#90EE90
    style A fill:#87CEEB
    style L fill:#FFD700
```

## Stage Transition Frequency

| From | To | Count |
|------|-----|-------|
""".format(len(all_flows))
    
    # Add transition counts
    for (from_stage, to_stage), count in sorted(transition_counts.items(), key=lambda x: -x[1]):
        if from_stage != 'start' and count > 0:
            diagram += f"| {from_stage} | {to_stage} | {count} |\n"
    
    return diagram


def generate_stage_training(all_flows):
    """Generate training examples for each stage."""
    stage_examples = defaultdict(list)
    
    for flow in all_flows:
        for t in flow['transitions']:
            stage_examples[t['to_stage']].append({
                'customer': flow['customer'],
                'trigger': t['trigger_subject'],
                'triggered_by': t['triggered_by'],
                'content_preview': t['example_content'],
                'previous_stage': t['from_stage']
            })
    
    training_data = {
        'stage_definitions': {
            stage: {
                'description': config['description'],
                'patterns': config['patterns'],
                'typical_next_stages': config['next_stages']
            }
            for stage, config in STAGES.items()
        },
        'stage_examples': dict(stage_examples),
        'stage_detection_training': []
    }
    
    # Generate classification training examples
    for stage, examples in stage_examples.items():
        for ex in examples[:5]:  # Top 5 per stage
            training_data['stage_detection_training'].append({
                'input': f"Subject: {ex['trigger']}\nContent: {ex['content_preview'][:100]}",
                'expected_stage': stage,
                'reasoning': f"This is {stage} because it matches patterns for {STAGES.get(stage, {}).get('description', stage)}"
            })
    
    return training_data


def generate_action_training(all_flows):
    """Generate training on what action to take at each stage."""
    action_training = []
    
    # Based on successful patterns
    stage_actions = {
        "first_contact": {
            "action": "Send introduction email with company overview, video links, and offer to discuss needs",
            "example_response": "Thank you for connecting at K2022! Machinecraft is a 3rd generation thermoforming OEM with 1000+ installations globally. I'd love to understand your production needs. Here's a video of our PF1-X series: [link]. When would be a good time for a brief call?",
        },
        "discovery": {
            "action": "Ask qualifying questions about application, materials, volumes, and timeline",
            "example_response": "To recommend the right machine, could you share: 1) What products will you form? 2) What material and thickness? 3) Target cycle time? 4) Expected production volume?",
        },
        "technical": {
            "action": "Provide detailed specifications, share relevant case studies, offer technical call",
            "example_response": "Based on your 4mm ABS sheets, I recommend our PF1-X-1510. Attached is the full spec sheet. We have a similar installation at [customer] - would you like me to arrange a reference call?",
        },
        "quote_request": {
            "action": "Prepare and send detailed quotation within 24-48 hours",
            "example_response": "Thank you for your interest! I'm preparing a detailed quotation for the PF1-X-1510 with the options we discussed. You'll have it by tomorrow.",
        },
        "quote_sent": {
            "action": "Confirm receipt and offer to walk through the quote",
            "example_response": "I've sent the quotation (Ref: MT20240601). Would you like to schedule a call to walk through the specifications and options?",
        },
        "factory_visit_offer": {
            "action": "Offer to arrange visit to nearby reference site or India factory",
            "example_response": "I'd like to invite you to see our machine in operation. We have a recent installation at Dutch Tides near Den Haag, Netherlands - about 1 hour from Schiphol. I can arrange a visit and pick you up from the airport.",
        },
        "quote_followup": {
            "action": "Check in on quote review, offer to answer questions, share additional info",
            "example_response": "Just checking in on the quotation I sent last week. Have you had a chance to review it? Happy to clarify any specifications or discuss options.",
        },
        "negotiation": {
            "action": "Understand their position, offer value-adds, work toward win-win",
            "example_response": "I understand budget is a consideration. Let me see what we can do on delivery timing or training scope. What's your target timeline for installation?",
        },
        "objection_handling": {
            "action": "Address specific concern with facts, references, or demonstration",
            "example_response": "I understand the concern about service support. We have 2 machines in Sweden and provide 48-hour technician arrival guarantee. Here's contact info for our Swedish customer who can share their experience.",
        },
        "closing": {
            "action": "Facilitate order process - proforma, payment terms, timeline",
            "example_response": "Excellent! I'll prepare the proforma invoice today. Our standard terms are 30% advance, 40% before shipping, 30% after commissioning. The production timeline is approximately 12-14 weeks.",
        },
    }
    
    for stage, data in stage_actions.items():
        action_training.append({
            "stage": stage,
            "stage_description": STAGES.get(stage, {}).get('description', ''),
            "recommended_action": data["action"],
            "example_response": data["example_response"],
            "next_stages": STAGES.get(stage, {}).get('next_stages', [])
        })
    
    return action_training


def main():
    print("=" * 70)
    print("BUILDING SALES FLOW TRAINING DATA")
    print("=" * 70)
    
    service = get_gmail_service()
    all_flows = []
    
    for customer in CUSTOMERS:
        print(f"\nExtracting flow for: {customer['client']}...")
        flow = extract_customer_flow(service, customer)
        all_flows.append(flow)
        print(f"  ✓ {len(flow['transitions'])} stage transitions, {len(flow['stages_visited'])} stages")
    
    # Build outputs
    print("\nGenerating training data...")
    
    # 1. Flow diagram
    diagram = build_flow_diagram(all_flows)
    diagram_path = PROJECT_ROOT / "data" / "knowledge" / "sales_flow_diagram.md"
    with open(diagram_path, 'w') as f:
        f.write(diagram)
    print(f"  ✓ Saved flow diagram to {diagram_path}")
    
    # 2. Stage training
    stage_training = generate_stage_training(all_flows)
    stage_path = PROJECT_ROOT / "data" / "training" / "sales_stage_training.json"
    with open(stage_path, 'w') as f:
        json.dump(stage_training, f, indent=2)
    print(f"  ✓ Saved stage training to {stage_path}")
    
    # 3. Action training
    action_training = generate_action_training(all_flows)
    action_path = PROJECT_ROOT / "data" / "training" / "sales_action_training.json"
    with open(action_path, 'w') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'source': 'European customer email analysis',
            'actions': action_training
        }, f, indent=2)
    print(f"  ✓ Saved action training to {action_path}")
    
    # 4. Complete flow data
    flow_path = PROJECT_ROOT / "data" / "training" / "sales_flow_patterns.json"
    with open(flow_path, 'w') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'total_customers': len(all_flows),
            'flows': all_flows
        }, f, indent=2)
    print(f"  ✓ Saved flow patterns to {flow_path}")
    
    # Summary
    print("\n" + "=" * 70)
    print("TRAINING DATA SUMMARY")
    print("=" * 70)
    
    all_stages = set()
    all_transitions = []
    for flow in all_flows:
        all_stages.update(flow['stages_visited'])
        all_transitions.extend(flow['transitions'])
    
    print(f"\nCustomers analyzed: {len(all_flows)}")
    print(f"Unique stages found: {len(all_stages)}")
    print(f"Total transitions: {len(all_transitions)}")
    print(f"\nStages covered: {', '.join(sorted(all_stages))}")
    
    return all_flows


if __name__ == "__main__":
    main()
