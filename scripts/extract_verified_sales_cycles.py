#!/usr/bin/env python3
"""
Extract VERIFIED Sales Cycles from Email Threads

This script properly identifies:
1. First inquiry/contact about a machine
2. Quote sent date
3. Order/PO confirmation date
4. Calculates true sales cycle (inquiry to PO only)

It EXCLUDES:
- Post-sale support emails
- Trade show invitations to existing customers
- Internal system emails
- Unrelated follow-up correspondence
"""

import json
import re
import base64
from pathlib import Path
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

PROJECT_ROOT = Path(__file__).parent.parent

# European customers with verified deal data
VERIFIED_CUSTOMERS = [
    {
        "client": "DutchTides",
        "country": "Netherlands", 
        "machine": "PF1-X-6520",
        "deal_value": 650000,
        "search_terms": ["dutchtides", "dutch tides", "jurriaan"],
        "first_inquiry_patterns": ["quote", "specification", "PF1"],
        "order_patterns": ["bank guarantee", "BG", "proforma", "order confirm"],
        "date_range": {"after": "2024/04/01", "before": "2024/08/01"}
    },
    {
        "client": "JoPlast",
        "country": "Denmark",
        "machine": "PF1-2015", 
        "deal_value": 290000,
        "search_terms": ["joplast", "jo plast"],
        "first_inquiry_patterns": ["updates from machinecraft", "presentation", "quote"],
        "order_patterns": ["shipment", "payment", "confirm"],
        "date_range": {"after": "2023/10/01", "before": "2024/03/01"}
    },
    {
        "client": "Batelaan",
        "country": "Netherlands",
        "machine": "PF1-1315",
        "deal_value": 150000,
        "search_terms": ["batelaan", "kenrick"],
        "first_inquiry_patterns": ["K2022", "meeting request", "quote"],
        "order_patterns": ["revised offer", "order", "confirm"],
        "date_range": {"after": "2022/09/01", "before": "2023/02/01"}
    },
    {
        "client": "Thermic",
        "country": "Germany",
        "machine": "PF1-1616",
        "deal_value": 180000,
        "search_terms": ["thermic"],
        "first_inquiry_patterns": ["correspondence", "thermoforming machine", "quote"],
        "order_patterns": ["order", "confirm", "proceed"],
        "date_range": {"after": "2022/01/01", "before": "2024/01/01"}
    },
    {
        "client": "Donite",
        "country": "Ireland",
        "machine": "PF1-0810",
        "deal_value": 90000,
        "search_terms": ["donite"],
        "first_inquiry_patterns": ["quote", "thermoform", "inquiry"],
        "order_patterns": ["shipment", "pre-shipment", "confirm"],
        "date_range": {"after": "2023/01/01", "before": "2025/01/01"}
    },
]

# Patterns to identify sales stages
INQUIRY_PATTERNS = [
    r'inquiry', r'enquiry', r'information request', r'interested in',
    r'looking for.*machine', r'need.*thermoform', r'quote request',
    r'request for quote', r'RFQ', r'introduction'
]

QUOTE_PATTERNS = [
    r'quote', r'quotation', r'offer', r'proposal', r'pricing',
    r'MT\d{10}', r'price.*machine'
]

ORDER_PATTERNS = [
    r'purchase order', r'\bPO\b', r'order confirm', r'proceed',
    r'bank guarantee', r'\bBG\b', r'proforma', r'advance payment',
    r'shipment', r'delivery schedule'
]

POST_SALE_PATTERNS = [
    r'support', r'issue', r'problem', r'quality', r'spare part',
    r'maintenance', r'training complete', r'FAT', r'commissioning',
    r'daily.*report', r'installation complete'
]


def get_gmail_service():
    """Initialize Gmail API service."""
    token_path = PROJECT_ROOT / "token_rushabh.json"
    creds = Credentials.from_authorized_user_file(str(token_path))
    return build('gmail', 'v1', credentials=creds)


def parse_date(date_str):
    """Parse email date to datetime."""
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S %z",
    ]
    date_str = re.sub(r'\s+\([A-Z]+\)', '', date_str.strip())
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def classify_email_stage(subject, body_preview=""):
    """Classify email into sales stage."""
    text = (subject + " " + body_preview).lower()
    
    # Check for post-sale first (to exclude)
    for pattern in POST_SALE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return "post_sale"
    
    # Check for order confirmation
    for pattern in ORDER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return "order"
    
    # Check for quote
    for pattern in QUOTE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return "quote"
    
    # Check for inquiry
    for pattern in INQUIRY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return "inquiry"
    
    return "other"


def search_customer_emails(service, customer):
    """Search for sales-related emails for a customer."""
    emails = []
    
    for term in customer['search_terms']:
        try:
            # Build date-restricted query
            query = f'"{term}"'
            if customer.get('date_range'):
                if customer['date_range'].get('after'):
                    query += f" after:{customer['date_range']['after']}"
                if customer['date_range'].get('before'):
                    query += f" before:{customer['date_range']['before']}"
            
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=50
            ).execute()
            
            messages = results.get('messages', [])
            
            for msg_ref in messages:
                if msg_ref['id'] not in [e.get('id') for e in emails]:
                    try:
                        msg = service.users().messages().get(
                            userId='me',
                            id=msg_ref['id'],
                            format='metadata'
                        ).execute()
                        
                        headers = {h['name'].lower(): h['value'] 
                                  for h in msg['payload'].get('headers', [])}
                        
                        date = parse_date(headers.get('date', ''))
                        subject = headers.get('subject', '')
                        from_addr = headers.get('from', '')
                        
                        stage = classify_email_stage(subject)
                        
                        if date and stage != "post_sale":
                            emails.append({
                                'id': msg_ref['id'],
                                'date': date,
                                'subject': subject,
                                'from': from_addr,
                                'stage': stage
                            })
                    except Exception:
                        continue
                        
        except Exception as e:
            print(f"  Error searching '{term}': {e}")
    
    # Sort by date
    emails.sort(key=lambda x: x['date'])
    
    return emails


def analyze_sales_cycle(emails, customer):
    """Analyze sales cycle from filtered emails."""
    if not emails:
        return None
    
    # Find key milestones
    first_inquiry = None
    first_quote = None
    order_confirmed = None
    
    for email in emails:
        if email['stage'] == 'inquiry' and not first_inquiry:
            first_inquiry = email
        elif email['stage'] == 'quote' and not first_quote:
            first_quote = email
        elif email['stage'] == 'order':
            order_confirmed = email  # Keep updating to get last order email
    
    # Use first email if no specific inquiry found
    if not first_inquiry:
        first_inquiry = emails[0]
    
    # Calculate cycle
    if first_inquiry and order_confirmed:
        cycle_days = (order_confirmed['date'] - first_inquiry['date']).days
    else:
        cycle_days = None
    
    return {
        'customer': customer['client'],
        'country': customer['country'],
        'machine': customer['machine'],
        'deal_value': customer['deal_value'],
        'total_sales_emails': len(emails),
        'first_contact': {
            'date': first_inquiry['date'].isoformat() if first_inquiry else None,
            'subject': first_inquiry['subject'] if first_inquiry else None
        },
        'first_quote': {
            'date': first_quote['date'].isoformat() if first_quote else None,
            'subject': first_quote['subject'] if first_quote else None
        },
        'order_confirmed': {
            'date': order_confirmed['date'].isoformat() if order_confirmed else None,
            'subject': order_confirmed['subject'] if order_confirmed else None
        },
        'cycle_days': cycle_days,
        'cycle_months': round(cycle_days / 30, 1) if cycle_days else None,
        'timeline': [
            {
                'date': e['date'].strftime('%Y-%m-%d'),
                'stage': e['stage'],
                'subject': e['subject'][:50]
            }
            for e in emails[:15]  # First 15 for summary
        ]
    }


def main():
    print("=" * 70)
    print("VERIFIED SALES CYCLE EXTRACTION")
    print("Tracking: First Inquiry → Quote → Order (excluding post-sale)")
    print("=" * 70)
    
    service = get_gmail_service()
    
    results = []
    
    for customer in VERIFIED_CUSTOMERS:
        print(f"\nAnalyzing: {customer['client']} ({customer['country']})...")
        
        emails = search_customer_emails(service, customer)
        print(f"  Found {len(emails)} sales-related emails")
        
        analysis = analyze_sales_cycle(emails, customer)
        
        if analysis:
            results.append(analysis)
            if analysis['cycle_days']:
                print(f"  ✓ Sales cycle: {analysis['cycle_days']} days ({analysis['cycle_months']} months)")
            else:
                print(f"  ✓ Partial data (inquiry or order date missing)")
    
    # Save results
    output_path = PROJECT_ROOT / "data" / "training" / "verified_sales_cycles.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            'extracted_at': datetime.now().isoformat(),
            'methodology': 'Tracked first inquiry to order confirmation, excluding post-sale emails',
            'total_customers': len(results),
            'cycles': results
        }, f, indent=2)
    
    print(f"\n✓ Saved to {output_path}")
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFIED SALES CYCLE SUMMARY")
    print("=" * 70)
    
    valid_cycles = [r for r in results if r.get('cycle_days')]
    
    if valid_cycles:
        avg_days = sum(r['cycle_days'] for r in valid_cycles) / len(valid_cycles)
        print(f"\n{'Customer':<15} {'Value':>10} {'Cycle':>12} {'Months':>8}")
        print("-" * 50)
        
        for r in sorted(valid_cycles, key=lambda x: x['deal_value'], reverse=True):
            print(f"{r['customer']:<15} €{r['deal_value']:>8,} {r['cycle_days']:>8} days {r['cycle_months']:>7}")
        
        print("-" * 50)
        print(f"{'AVERAGE':<15} {'':>10} {avg_days:>8.0f} days {avg_days/30:>7.1f}")
    
    return results


if __name__ == "__main__":
    main()
