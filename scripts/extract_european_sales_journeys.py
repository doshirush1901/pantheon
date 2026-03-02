#!/usr/bin/env python3
"""
Extract complete sales journey conversations from European customers.
These are WON deals - learn how Rushabh moved from inquiry to PO.

Key customers to analyze:
- High value: DutchTides, JoPlast, Soehner, Thermic, Batelaan
- Repeat customers: Anatomic Sitt, BD-Plastindustri, Ridat
- Various countries: Donite (Ireland), Plastochim (France), Mp3 (Italy)
"""

import json
import os
import re
import base64
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

PROJECT_ROOT = Path(__file__).parent.parent

# European customers from MC Europe.xlsx (sorted by importance for training)
EUROPEAN_CUSTOMERS = [
    # High value deals - most valuable for learning
    {"client": "DutchTides", "country": "Netherlands", "machine": "PF1-6019", "year": 2025, "price": 650000, "search_terms": ["dutchtides", "dutch tides"]},
    {"client": "JoPlast", "country": "Denmark", "machine": "PF1-2015", "year": 2024, "price": 290000, "search_terms": ["joplast", "jo plast", "jo-plast"]},
    {"client": "Soehner", "country": "Germany", "machine": "PF1-1318", "year": 2023, "price": 270000, "search_terms": ["soehner", "söhner"]},
    {"client": "Thermic", "country": "Germany", "machine": "PF1-1616", "year": 2023, "price": 180000, "search_terms": ["thermic"]},
    
    # Strategic repeat customers - shows relationship building
    {"client": "Batelaan", "country": "Netherlands", "machine": "PF1-1315", "year": 2022, "price": 150000, "search_terms": ["batelaan"]},
    {"client": "Anatomic Sitt", "country": "Sweden", "machine": "PF1-810", "year": 2022, "price": 70000, "search_terms": ["anatomic sitt", "anatomicsitt", "krister"]},
    {"client": "BD-Plastindustri", "country": "Sweden", "machine": "PF-1500x1500", "year": 2016, "price": 90000, "search_terms": ["bd-plastindustri", "bd plastindustri"]},
    
    # International diversity
    {"client": "Donite", "country": "Ireland", "machine": "PF1-0810", "year": 2022, "price": 90000, "search_terms": ["donite"]},
    {"client": "Plastochim", "country": "France", "machine": "PF1-0808", "year": 2022, "price": 65000, "search_terms": ["plastochim"]},
    {"client": "Mp3", "country": "Italy", "machine": "PF1-707", "year": 2025, "price": 80000, "search_terms": ["mp3 italy", "mp3 srl"]},
    {"client": "Forma Plast", "country": "Sweden", "machine": "PF1-1015", "year": 2012, "price": 110000, "search_terms": ["forma plast", "formaplast"]},
    
    # OEM partner - different sales dynamic
    {"client": "Ridat", "country": "UK", "machine": "PF1-1015", "year": 2021, "price": 100000, "search_terms": ["ridat"]},
    
    # Other customers
    {"client": "Pro-form Kft", "country": "Hungary", "machine": "PF-1/1000x1000", "year": 2015, "price": 60000, "search_terms": ["pro-form", "proform kft"]},
    {"client": "Romind", "country": "Romania", "machine": "PF-1", "year": 2005, "price": 90000, "search_terms": ["romind"]},
]

# Sales stage indicators
SALES_STAGE_PATTERNS = {
    "inquiry": [r"interest", r"inquiry", r"enquiry", r"information", r"brochure", r"catalog", r"learn more"],
    "technical": [r"specification", r"spec sheet", r"technical", r"heater", r"servo", r"size", r"dimension", r"capacity"],
    "quote": [r"quote", r"quotation", r"price", r"pricing", r"cost", r"budget", r"offer"],
    "negotiation": [r"discount", r"payment term", r"delivery", r"shipping", r"installation", r"training", r"warranty"],
    "closing": [r"purchase order", r"po", r"confirm", r"order", r"proceed", r"accept", r"agreement"],
}

AUTO_REPLY_PATTERNS = [
    r'out of (the )?office', r'automatic reply', r'auto[- ]?reply',
    r'auto[- ]?response', r'automatische antwort', r'vacation',
    r'currently unavailable', r'do not reply', r'noreply',
    r'mailer-daemon', r'delivery (status|failure)', r'undeliverable',
]
AUTO_REPLY_REGEX = re.compile('|'.join(AUTO_REPLY_PATTERNS), re.IGNORECASE)


def is_auto_reply(msg_data):
    """Check if message is an auto-reply."""
    subject = msg_data.get('subject', '').lower()
    body = msg_data.get('body', '')[:500].lower()
    return AUTO_REPLY_REGEX.search(subject) or AUTO_REPLY_REGEX.search(body)


def detect_sales_stage(text):
    """Detect which sales stage this message belongs to."""
    text_lower = text.lower()
    stages_found = []
    
    for stage, patterns in SALES_STAGE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                stages_found.append(stage)
                break
    
    return stages_found if stages_found else ["general"]


def clean_email_body(body):
    """Clean email body, remove quotes and signatures."""
    if not body:
        return ""
    
    lines = body.split('\n')
    clean_lines = []
    
    for line in lines:
        if line.startswith('>'):
            continue
        if 'On ' in line and ' wrote:' in line:
            break
        if '-----Original Message-----' in line:
            break
        if 'Von:' in line and ('Gesendet:' in body or 'Betreff:' in body):
            break
        clean_lines.append(line)
    
    return '\n'.join(clean_lines).strip()


def get_gmail_service():
    """Initialize Gmail API service."""
    token_path = PROJECT_ROOT / "token_rushabh.json"
    
    if not token_path.exists():
        print(f"Error: Token file not found at {token_path}")
        return None
    
    creds = Credentials.from_authorized_user_file(str(token_path))
    return build('gmail', 'v1', credentials=creds)


def search_customer_threads(service, customer):
    """Search for all email threads with a customer."""
    all_threads = []
    
    for search_term in customer["search_terms"]:
        try:
            # Search in both directions
            query = f'("{search_term}")'
            results = service.users().threads().list(
                userId='me',
                q=query,
                maxResults=50
            ).execute()
            
            threads = results.get('threads', [])
            for t in threads:
                if t['id'] not in [x['id'] for x in all_threads]:
                    all_threads.append(t)
                    
        except Exception as e:
            print(f"    Error searching '{search_term}': {e}")
    
    return all_threads


def get_thread_messages(service, thread_id):
    """Get all messages in a thread."""
    try:
        thread = service.users().threads().get(
            userId='me',
            id=thread_id,
            format='full'
        ).execute()
        
        messages = []
        for msg in thread.get('messages', []):
            msg_data = parse_message(msg)
            if msg_data and not is_auto_reply(msg_data):
                messages.append(msg_data)
        
        return messages
    except Exception as e:
        print(f"    Error getting thread {thread_id}: {e}")
        return []


def parse_message(msg):
    """Parse a Gmail message."""
    headers = {h['name'].lower(): h['value'] for h in msg['payload'].get('headers', [])}
    
    body = ""
    payload = msg['payload']
    
    if 'body' in payload and payload['body'].get('data'):
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
    elif 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                break
            elif 'parts' in part:
                for subpart in part['parts']:
                    if subpart['mimeType'] == 'text/plain' and subpart['body'].get('data'):
                        body = base64.urlsafe_b64decode(subpart['body']['data']).decode('utf-8', errors='ignore')
                        break
    
    # Parse date
    date_str = headers.get('date', '')
    
    return {
        'from': headers.get('from', ''),
        'to': headers.get('to', ''),
        'subject': headers.get('subject', ''),
        'date': date_str,
        'body': clean_email_body(body),
        'message_id': msg.get('id', ''),
    }


def analyze_sales_journey(messages, customer):
    """Analyze the sales journey from messages."""
    if not messages:
        return None
    
    journey = {
        "customer": customer["client"],
        "country": customer["country"],
        "machine": customer["machine"],
        "deal_value": customer["price"],
        "deal_year": customer["year"],
        "total_emails": len(messages),
        "stages_covered": set(),
        "timeline": [],
        "key_moments": [],
        "rushabh_techniques": [],
    }
    
    for msg in messages:
        from_addr = msg['from'].lower()
        is_rushabh = 'machinecraft' in from_addr or 'rushabh' in from_addr
        
        stages = detect_sales_stage(msg['subject'] + ' ' + msg['body'])
        journey["stages_covered"].update(stages)
        
        entry = {
            "date": msg['date'],
            "from": "Rushabh" if is_rushabh else "Customer",
            "subject": msg['subject'],
            "stages": stages,
            "body_preview": msg['body'][:500] if msg['body'] else "",
        }
        journey["timeline"].append(entry)
        
        # Identify key techniques used by Rushabh
        if is_rushabh:
            body_lower = msg['body'].lower()
            if 'visit' in body_lower or 'factory' in body_lower:
                journey["rushabh_techniques"].append("factory_visit_invitation")
            if 'reference' in body_lower or 'customer' in body_lower:
                journey["rushabh_techniques"].append("customer_reference")
            if 'k show' in body_lower or 'k-show' in body_lower or 'trade fair' in body_lower:
                journey["rushabh_techniques"].append("trade_show_meeting")
            if 'discount' in body_lower or 'special' in body_lower:
                journey["rushabh_techniques"].append("special_pricing")
            if 'delivery' in body_lower or 'lead time' in body_lower:
                journey["rushabh_techniques"].append("delivery_commitment")
    
    journey["stages_covered"] = list(journey["stages_covered"])
    journey["rushabh_techniques"] = list(set(journey["rushabh_techniques"]))
    
    return journey


def extract_training_examples(journey):
    """Extract training examples from a sales journey."""
    examples = []
    
    timeline = journey.get("timeline", [])
    
    for i, entry in enumerate(timeline):
        if entry["from"] == "Customer" and i + 1 < len(timeline):
            # Look for Rushabh's response
            for j in range(i + 1, min(i + 3, len(timeline))):
                if timeline[j]["from"] == "Rushabh":
                    examples.append({
                        "customer": journey["customer"],
                        "country": journey["country"],
                        "deal_value": journey["deal_value"],
                        "stage": entry["stages"][0] if entry["stages"] else "general",
                        "customer_message": entry["body_preview"],
                        "rushabh_response": timeline[j]["body_preview"],
                        "subject": entry["subject"],
                    })
                    break
    
    return examples


def main():
    print("=" * 70)
    print("EXTRACTING EUROPEAN CUSTOMER SALES JOURNEYS")
    print("=" * 70)
    print(f"Analyzing {len(EUROPEAN_CUSTOMERS)} European customers")
    print("Focus: Complete sales cycle from inquiry to PO\n")
    
    service = get_gmail_service()
    if not service:
        return
    
    all_journeys = []
    all_training_examples = []
    customers_with_data = 0
    
    for i, customer in enumerate(EUROPEAN_CUSTOMERS):
        print(f"\n[{i+1}/{len(EUROPEAN_CUSTOMERS)}] {customer['client']} ({customer['country']})")
        print(f"    Machine: {customer['machine']} | Value: €{customer['price']:,} | Year: {customer['year']}")
        
        threads = search_customer_threads(service, customer)
        
        if threads:
            print(f"    Found {len(threads)} thread(s)")
            
            all_messages = []
            for thread in threads[:10]:  # Limit threads per customer
                messages = get_thread_messages(service, thread['id'])
                all_messages.extend(messages)
            
            # Remove duplicates by message_id
            seen_ids = set()
            unique_messages = []
            for msg in all_messages:
                if msg['message_id'] not in seen_ids:
                    seen_ids.add(msg['message_id'])
                    unique_messages.append(msg)
            
            if unique_messages:
                customers_with_data += 1
                print(f"    Total emails: {len(unique_messages)}")
                
                journey = analyze_sales_journey(unique_messages, customer)
                if journey:
                    all_journeys.append(journey)
                    print(f"    Stages covered: {', '.join(journey['stages_covered'])}")
                    print(f"    Techniques used: {', '.join(journey['rushabh_techniques']) if journey['rushabh_techniques'] else 'N/A'}")
                    
                    # Extract training examples
                    examples = extract_training_examples(journey)
                    all_training_examples.extend(examples)
                    print(f"    Training examples: {len(examples)}")
        else:
            print("    No threads found")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Customers searched: {len(EUROPEAN_CUSTOMERS)}")
    print(f"Customers with email data: {customers_with_data}")
    print(f"Total sales journeys: {len(all_journeys)}")
    print(f"Total training examples: {len(all_training_examples)}")
    
    # Save results
    output_dir = PROJECT_ROOT / "data" / "training"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save journeys
    journeys_file = output_dir / "european_sales_journeys.json"
    with open(journeys_file, 'w') as f:
        json.dump({
            'extracted_at': datetime.now().isoformat(),
            'total_customers': len(EUROPEAN_CUSTOMERS),
            'customers_with_data': customers_with_data,
            'journeys': all_journeys,
        }, f, indent=2, default=str)
    print(f"\nSaved journeys to {journeys_file}")
    
    # Save training examples
    training_file = output_dir / "european_sales_training.json"
    with open(training_file, 'w') as f:
        json.dump({
            'extracted_at': datetime.now().isoformat(),
            'total_examples': len(all_training_examples),
            'examples': all_training_examples,
        }, f, indent=2, default=str)
    print(f"Saved training data to {training_file}")
    
    # Show sample
    if all_training_examples:
        print("\n" + "=" * 70)
        print("SAMPLE TRAINING EXAMPLES")
        print("=" * 70)
        for ex in all_training_examples[:3]:
            print(f"\n--- {ex['customer']} ({ex['country']}) - €{ex['deal_value']:,} ---")
            print(f"Stage: {ex['stage']}")
            print(f"Subject: {ex['subject']}")
            print(f"\nCustomer: {ex['customer_message'][:300]}...")
            print(f"\nRushabh: {ex['rushabh_response'][:300]}...")


if __name__ == "__main__":
    main()
