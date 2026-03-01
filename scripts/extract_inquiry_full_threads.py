#!/usr/bin/env python3
"""
Extract FULL conversation threads from Rushabh's mailbox for Inquiry Form leads.
Better extraction that captures complete email exchanges.
"""

import json
import os
import re
import base64
from pathlib import Path
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

PROJECT_ROOT = Path(__file__).parent.parent

# Auto-reply patterns
AUTO_REPLY_PATTERNS = [
    r'out of (the )?office', r'automatic reply', r'auto[- ]?reply',
    r'vacation', r'holiday', r'away from desk', r'maternity leave',
    r'do not reply', r'noreply', r'mailer-daemon', r'postmaster',
    r'delivery (status|failure)', r'undeliverable',
]
AUTO_REPLY_REGEX = re.compile('|'.join(AUTO_REPLY_PATTERNS), re.IGNORECASE)


def is_genuine_message(msg):
    """Check if message is genuine (not auto-reply, has content)."""
    subject = msg.get('subject', '').lower()
    body = msg.get('body', '').strip()
    
    if AUTO_REPLY_REGEX.search(subject):
        return False
    if len(body) < 30:
        return False
    return True


def clean_body(body):
    """Clean email body."""
    if not body:
        return ""
    
    # Remove image references
    body = re.sub(r'\[image:.*?\]', '', body)
    body = re.sub(r'\[cid:.*?\]', '', body)
    
    # Remove excessive whitespace
    body = re.sub(r'\n{3,}', '\n\n', body)
    body = re.sub(r' {3,}', ' ', body)
    
    return body.strip()


def get_gmail_service():
    """Initialize Gmail API."""
    token_path = PROJECT_ROOT / "token_rushabh.json"
    creds = Credentials.from_authorized_user_file(str(token_path))
    return build('gmail', 'v1', credentials=creds)


def get_message_body(msg):
    """Extract plain text body from message."""
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
    
    return clean_body(body)


def process_lead(service, lead, max_threads=5):
    """Process a lead and extract conversations."""
    email = lead['email']
    results = []
    
    # Clean email (some have multiple emails)
    if '/' in email:
        emails = [e.strip() for e in email.split('/')]
    else:
        emails = [email]
    
    for email_addr in emails:
        try:
            # Search threads
            query = f"(from:{email_addr} OR to:{email_addr}) -unsubscribe -newsletter"
            response = service.users().threads().list(
                userId='me', q=query, maxResults=max_threads
            ).execute()
            
            threads = response.get('threads', [])
            
            for thread_info in threads:
                thread = service.users().threads().get(
                    userId='me', id=thread_info['id'], format='full'
                ).execute()
                
                messages = thread.get('messages', [])
                
                # Extract each message
                thread_messages = []
                for msg in messages:
                    headers = {h['name'].lower(): h['value'] for h in msg['payload'].get('headers', [])}
                    
                    msg_data = {
                        'from': headers.get('from', ''),
                        'to': headers.get('to', ''),
                        'subject': headers.get('subject', ''),
                        'date': headers.get('date', ''),
                        'body': get_message_body(msg),
                    }
                    
                    if is_genuine_message(msg_data):
                        thread_messages.append(msg_data)
                
                if len(thread_messages) >= 2:  # Need at least 2 messages
                    # Separate customer and Rushabh messages
                    pairs = extract_pairs_from_thread(thread_messages, email_addr)
                    results.extend(pairs)
                    
        except Exception as e:
            print(f"    Error: {e}")
    
    return results


def extract_pairs_from_thread(messages, lead_email):
    """Extract Q&A pairs from a thread."""
    pairs = []
    
    # Categorize messages
    rushabh_msgs = []
    customer_msgs = []
    
    for msg in messages:
        from_addr = msg['from'].lower()
        if 'machinecraft' in from_addr:
            rushabh_msgs.append(msg)
        elif lead_email.lower() in from_addr:
            customer_msgs.append(msg)
    
    # Match customer questions with Rushabh responses
    # Simple approach: pair consecutive messages
    all_msgs = sorted(messages, key=lambda x: x['date'])
    
    for i, msg in enumerate(all_msgs):
        from_addr = msg['from'].lower()
        
        # If this is a customer message, look for Rushabh's next response
        if lead_email.lower() in from_addr:
            # Find next message from Rushabh
            for j in range(i+1, len(all_msgs)):
                next_msg = all_msgs[j]
                if 'machinecraft' in next_msg['from'].lower():
                    pairs.append({
                        'customer_question': msg['body'][:2000],
                        'rushabh_response': next_msg['body'][:2000],
                        'subject': msg['subject'],
                        'customer_date': msg['date'],
                        'response_date': next_msg['date'],
                    })
                    break
    
    return pairs


def main():
    print("=" * 70)
    print("FULL THREAD EXTRACTION FROM INQUIRY FORM LEADS")
    print("=" * 70)
    
    # Load leads
    leads_file = PROJECT_ROOT / "data" / "training" / "inquiry_form_leads.json"
    with open(leads_file) as f:
        leads = json.load(f)
    
    print(f"Loaded {len(leads)} leads")
    
    # Initialize Gmail
    service = get_gmail_service()
    
    all_pairs = []
    leads_with_pairs = 0
    
    for i, lead in enumerate(leads):
        print(f"\n[{i+1}/{len(leads)}] {lead['company']} ({lead['email'][:30]}...)")
        
        pairs = process_lead(service, lead, max_threads=3)
        
        if pairs:
            leads_with_pairs += 1
            all_pairs.extend([{
                'lead': lead,
                **pair
            } for pair in pairs])
            print(f"  Found {len(pairs)} Q&A pair(s)")
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Leads with conversations: {leads_with_pairs}/{len(leads)}")
    print(f"Total Q&A pairs: {len(all_pairs)}")
    
    # Categorize pairs
    categories = {}
    for pair in all_pairs:
        cat = pair['lead'].get('interest', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"\nBy customer interest:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    
    # Save to file
    output_file = PROJECT_ROOT / "data" / "training" / "inquiry_form_full_conversations.json"
    with open(output_file, 'w') as f:
        json.dump({
            'extracted_at': datetime.now().isoformat(),
            'total_leads': len(leads),
            'leads_with_conversations': leads_with_pairs,
            'total_pairs': len(all_pairs),
            'pairs': all_pairs,
        }, f, indent=2, default=str)
    
    print(f"\nSaved to {output_file}")
    
    # Show samples
    if all_pairs:
        print("\n" + "=" * 70)
        print("SAMPLE CONVERSATIONS (first 5)")
        print("=" * 70)
        
        for pair in all_pairs[:5]:
            lead = pair['lead']
            print(f"\n{'='*50}")
            print(f"Company: {lead['company']}")
            print(f"Interest: {lead.get('interest', 'N/A')}")
            print(f"Specs wanted: {lead.get('forming_area', '')} / {lead.get('materials', '')}")
            print(f"Subject: {pair['subject']}")
            print(f"\n--- CUSTOMER ---")
            print(pair['customer_question'][:400])
            print(f"\n--- RUSHABH ---")
            print(pair['rushabh_response'][:400])


if __name__ == "__main__":
    main()
