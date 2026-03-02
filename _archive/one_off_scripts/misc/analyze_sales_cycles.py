#!/usr/bin/env python3
"""
Analyze Sales Cycles from European Customer Email Threads

Extracts detailed metrics:
- Sales cycle duration (first email to PO/close)
- Number of emails exchanged
- Sales stage flow
- Response times
- Key milestones
"""

import json
import os
import re
import base64
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

PROJECT_ROOT = Path(__file__).parent.parent

# European customers with confirmed sales
EUROPEAN_CUSTOMERS = [
    {"client": "DutchTides", "search_terms": ["dutchtides", "dutch tides", "jurriaan", "jaap van pooy"], "deal_year": 2025, "deal_value": 650000},
    {"client": "Dezet", "search_terms": ["dezet"], "deal_year": 2025, "deal_value": 180000},
    {"client": "JoPlast", "search_terms": ["joplast", "jo plast", "jo-plast"], "deal_year": 2024, "deal_value": 290000},
    {"client": "Soehner", "search_terms": ["soehner", "söhner"], "deal_year": 2024, "deal_value": 270000},
    {"client": "Thermic", "search_terms": ["thermic gmbh", "thermic"], "deal_year": 2023, "deal_value": 180000},
    {"client": "Batelaan", "search_terms": ["batelaan", "kenrick"], "deal_year": 2022, "deal_value": 150000},
    {"client": "Anatomic Sitt", "search_terms": ["anatomic sitt", "anatomicsitt"], "deal_year": 2023, "deal_value": 70000},
    {"client": "BD-Plastindustri", "search_terms": ["bd-plastindustri", "bd plastindustri"], "deal_year": 2021, "deal_value": 90000},
    {"client": "Donite", "search_terms": ["donite"], "deal_year": 2023, "deal_value": 90000},
    {"client": "Forma Plast", "search_terms": ["forma plast", "formaplast"], "deal_year": 2020, "deal_value": 110000},
    {"client": "Ridat", "search_terms": ["ridat"], "deal_year": 2019, "deal_value": 100000},
    {"client": "Imatex", "search_terms": ["imatex", "jaques"], "deal_year": 2001, "deal_value": 50000},
    {"client": "Minini Plastic", "search_terms": ["minini", "mininiplastic", "scaramella", "coggiola"], "deal_year": None, "deal_value": None},  # Active lead
    {"client": "Mp3 Italy", "search_terms": ["mp3", "mp3 italy"], "deal_year": 2025, "deal_value": 80000},
]

SALES_STAGE_PATTERNS = {
    "first_contact": [r"first\s+time", r"introduction", r"referred\s+by", r"found\s+you", r"saw\s+your", r"met\s+at"],
    "inquiry": [r"interest", r"inquiry", r"enquiry", r"information", r"brochure", r"catalog", r"learn\s+more", r"looking\s+for"],
    "technical": [r"specification", r"spec\s+sheet", r"technical", r"heater", r"servo", r"dimension", r"capacity", r"forming\s+area"],
    "quote": [r"quote", r"quotation", r"price", r"pricing", r"cost", r"budget", r"offer", r"proposal"],
    "factory_visit": [r"factory\s+visit", r"see\s+the\s+machine", r"visit\s+your", r"come\s+to\s+india", r"demonstration"],
    "negotiation": [r"discount", r"payment\s+term", r"delivery", r"shipping", r"installation", r"training", r"warranty", r"negotiate"],
    "closing": [r"purchase\s+order", r"\bpo\b", r"confirm", r"order\s+confirm", r"proceed", r"accept", r"agreement", r"contract"],
    "po_received": [r"po\s+attached", r"purchase\s+order\s+attached", r"order\s+placed", r"confirmed\s+order", r"po\s+number"],
}


def get_gmail_service():
    token_path = PROJECT_ROOT / "token_rushabh.json"
    creds = Credentials.from_authorized_user_file(str(token_path))
    return build('gmail', 'v1', credentials=creds)


def parse_date(date_str):
    """Parse email date string to datetime."""
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
    ]
    # Clean the date string
    date_str = re.sub(r'\s+\([A-Z]+\)', '', date_str)
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def detect_stages(text):
    """Detect sales stages from email content."""
    text_lower = text.lower()
    detected = []
    for stage, patterns in SALES_STAGE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                detected.append(stage)
                break
    return detected


def get_body(payload):
    """Extract email body from payload."""
    body = ''
    if 'body' in payload and payload['body'].get('data'):
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
    elif 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain':
                if part.get('body', {}).get('data'):
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    break
            elif 'parts' in part:
                for subpart in part['parts']:
                    if subpart.get('mimeType') == 'text/plain':
                        if subpart.get('body', {}).get('data'):
                            body = base64.urlsafe_b64decode(subpart['body']['data']).decode('utf-8', errors='ignore')
                            break
                if body:
                    break
    return body


def analyze_customer_threads(service, customer):
    """Analyze all email threads for a customer."""
    all_messages = []
    
    for term in customer['search_terms']:
        try:
            results = service.users().messages().list(
                userId='me',
                q=f'"{term}"',
                maxResults=100
            ).execute()
            
            messages = results.get('messages', [])
            for msg_ref in messages:
                if msg_ref['id'] not in [m.get('id') for m in all_messages]:
                    try:
                        msg = service.users().messages().get(
                            userId='me', 
                            id=msg_ref['id'], 
                            format='full'
                        ).execute()
                        all_messages.append(msg)
                    except Exception:
                        continue
        except Exception:
            continue
    
    if not all_messages:
        return None
    
    # Parse all messages
    parsed_messages = []
    for msg in all_messages:
        headers = {h['name'].lower(): h['value'] for h in msg['payload'].get('headers', [])}
        
        from_addr = headers.get('from', '')
        subject = headers.get('subject', '')
        date_str = headers.get('date', '')
        date = parse_date(date_str)
        
        body = get_body(msg['payload'])
        
        is_rushabh = 'rushabh' in from_addr.lower() or 'machinecraft' in from_addr.lower()
        
        stages = detect_stages(subject + ' ' + body)
        
        parsed_messages.append({
            'date': date,
            'date_str': date_str,
            'from': 'Rushabh' if is_rushabh else 'Customer',
            'from_full': from_addr,
            'subject': subject,
            'stages': stages,
            'body_preview': body[:300] if body else ''
        })
    
    # Sort by date
    parsed_messages = [m for m in parsed_messages if m['date']]
    parsed_messages.sort(key=lambda x: x['date'])
    
    if not parsed_messages:
        return None
    
    # Calculate metrics
    first_email = parsed_messages[0]
    last_email = parsed_messages[-1]
    
    duration_days = (last_email['date'] - first_email['date']).days
    
    rushabh_count = sum(1 for m in parsed_messages if m['from'] == 'Rushabh')
    customer_count = sum(1 for m in parsed_messages if m['from'] == 'Customer')
    
    # Find key milestones
    milestones = {
        'first_contact': None,
        'first_quote': None,
        'factory_visit_mentioned': None,
        'negotiation_start': None,
        'po_received': None
    }
    
    for msg in parsed_messages:
        if 'inquiry' in msg['stages'] or 'first_contact' in msg['stages']:
            if not milestones['first_contact']:
                milestones['first_contact'] = msg['date']
        if 'quote' in msg['stages']:
            if not milestones['first_quote']:
                milestones['first_quote'] = msg['date']
        if 'factory_visit' in msg['stages']:
            if not milestones['factory_visit_mentioned']:
                milestones['factory_visit_mentioned'] = msg['date']
        if 'negotiation' in msg['stages']:
            if not milestones['negotiation_start']:
                milestones['negotiation_start'] = msg['date']
        if 'po_received' in msg['stages'] or 'closing' in msg['stages']:
            milestones['po_received'] = msg['date']  # Keep updating to get last one
    
    # Determine stage flow
    stage_flow = []
    seen_stages = set()
    for msg in parsed_messages:
        for stage in msg['stages']:
            if stage not in seen_stages and stage not in ['general']:
                stage_flow.append(stage)
                seen_stages.add(stage)
    
    return {
        'customer': customer['client'],
        'deal_year': customer.get('deal_year'),
        'deal_value': customer.get('deal_value'),
        'total_emails': len(parsed_messages),
        'rushabh_emails': rushabh_count,
        'customer_emails': customer_count,
        'first_email_date': first_email['date'].isoformat() if first_email['date'] else None,
        'last_email_date': last_email['date'].isoformat() if last_email['date'] else None,
        'sales_cycle_days': duration_days,
        'stage_flow': stage_flow,
        'milestones': {k: v.isoformat() if v else None for k, v in milestones.items()},
        'timeline_summary': [
            {
                'date': m['date'].strftime('%Y-%m-%d') if m['date'] else 'Unknown',
                'from': m['from'],
                'subject': m['subject'][:60],
                'stages': m['stages']
            }
            for m in parsed_messages[:20]  # First 20 for summary
        ]
    }


def main():
    print("=" * 70)
    print("SALES CYCLE ANALYSIS - European Customers")
    print("=" * 70)
    
    service = get_gmail_service()
    
    results = []
    
    for customer in EUROPEAN_CUSTOMERS:
        print(f"\nAnalyzing: {customer['client']}...")
        analysis = analyze_customer_threads(service, customer)
        
        if analysis:
            results.append(analysis)
            print(f"  ✓ {analysis['total_emails']} emails over {analysis['sales_cycle_days']} days")
        else:
            print(f"  ✗ No email data found")
    
    # Save detailed results
    output_path = PROJECT_ROOT / "data" / "training" / "sales_cycle_analysis.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            'analyzed_at': datetime.now().isoformat(),
            'total_customers': len(results),
            'analyses': results
        }, f, indent=2)
    
    print(f"\n✓ Saved detailed analysis to {output_path}")
    
    # Generate summary report
    print("\n" + "=" * 70)
    print("SALES CYCLE SUMMARY REPORT")
    print("=" * 70)
    
    # Sort by deal value for reporting
    results_sorted = sorted([r for r in results if r.get('deal_value')], 
                           key=lambda x: x.get('deal_value', 0), reverse=True)
    
    print(f"\n{'Customer':<20} {'Value':>10} {'Emails':>8} {'Days':>8} {'Stage Flow'}")
    print("-" * 70)
    
    total_days = 0
    total_emails = 0
    count = 0
    
    for r in results_sorted:
        value_str = f"€{r['deal_value']:,}" if r.get('deal_value') else "Active"
        flow = " → ".join(r['stage_flow'][:5]) if r['stage_flow'] else "N/A"
        print(f"{r['customer']:<20} {value_str:>10} {r['total_emails']:>8} {r['sales_cycle_days']:>8} {flow[:30]}")
        
        if r['sales_cycle_days'] > 0:
            total_days += r['sales_cycle_days']
            total_emails += r['total_emails']
            count += 1
    
    if count > 0:
        avg_days = total_days / count
        avg_emails = total_emails / count
        print("-" * 70)
        print(f"{'AVERAGE':<20} {'':>10} {avg_emails:>8.0f} {avg_days:>8.0f}")
    
    # Key insights
    print("\n" + "=" * 70)
    print("KEY INSIGHTS")
    print("=" * 70)
    
    if results_sorted:
        fastest = min(results_sorted, key=lambda x: x['sales_cycle_days'] if x['sales_cycle_days'] > 30 else 9999)
        longest = max(results_sorted, key=lambda x: x['sales_cycle_days'])
        most_emails = max(results_sorted, key=lambda x: x['total_emails'])
        
        print(f"\n• Fastest Close: {fastest['customer']} - {fastest['sales_cycle_days']} days")
        print(f"• Longest Cycle: {longest['customer']} - {longest['sales_cycle_days']} days") 
        print(f"• Most Engaged: {most_emails['customer']} - {most_emails['total_emails']} emails")
        
        # Common stage patterns
        print(f"\n• Average Sales Cycle: {avg_days:.0f} days ({avg_days/30:.1f} months)")
        print(f"• Average Emails: {avg_emails:.0f} emails per deal")
    
    return results


if __name__ == "__main__":
    main()
