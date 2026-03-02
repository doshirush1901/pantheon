#!/usr/bin/env python3
"""
Extract conversations from Rushabh's mailbox for Single Station Inquiry Form leads.
These are inbound inquiries - learn how Rushabh responded to them.
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

# Auto-reply patterns to filter out
AUTO_REPLY_PATTERNS = [
    r'out of (the )?office', r'automatic reply', r'auto[- ]?reply',
    r'auto[- ]?response', r'automatische antwort', r'vacation',
    r'holiday', r'away from (my )?desk', r'maternity leave',
    r'currently unavailable', r'do not reply', r'noreply',
    r'mailer-daemon', r'postmaster', r'delivery (status|failure)',
    r'undeliverable', r'returned mail', r'bounce',
]
AUTO_REPLY_REGEX = re.compile('|'.join(AUTO_REPLY_PATTERNS), re.IGNORECASE)


def is_auto_reply(msg_data):
    """Check if message is an auto-reply."""
    subject = msg_data.get('subject', '').lower()
    body = msg_data.get('body', '').lower()
    
    if AUTO_REPLY_REGEX.search(subject):
        return True
    if AUTO_REPLY_REGEX.search(body[:500]):
        return True
    return False


def clean_email_body(body):
    """Clean email body, remove quotes and signatures."""
    if not body:
        return ""
    
    # Remove quoted replies
    lines = body.split('\n')
    clean_lines = []
    for line in lines:
        if line.startswith('>'):
            continue
        if 'On ' in line and ' wrote:' in line:
            break
        if '-----Original Message-----' in line:
            break
        if 'From:' in line and 'Sent:' in lines[lines.index(line)+1:lines.index(line)+3]:
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


def search_threads_for_lead(service, email):
    """Search for email threads involving a lead."""
    try:
        # Search for threads with this email
        query = f"from:{email} OR to:{email}"
        results = service.users().threads().list(
            userId='me',
            q=query,
            maxResults=10
        ).execute()
        
        return results.get('threads', [])
    except Exception as e:
        print(f"  Error searching for {email}: {e}")
        return []


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
            if msg_data:
                messages.append(msg_data)
        
        return messages
    except Exception as e:
        print(f"  Error getting thread {thread_id}: {e}")
        return []


def parse_message(msg):
    """Parse a Gmail message."""
    headers = {h['name'].lower(): h['value'] for h in msg['payload'].get('headers', [])}
    
    # Get body
    body = ""
    payload = msg['payload']
    
    if 'body' in payload and payload['body'].get('data'):
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
    elif 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                break
    
    return {
        'from': headers.get('from', ''),
        'to': headers.get('to', ''),
        'subject': headers.get('subject', ''),
        'date': headers.get('date', ''),
        'body': clean_email_body(body),
    }


def extract_qa_pairs(messages, lead_email):
    """Extract Q&A pairs from thread messages."""
    pairs = []
    
    # Sort by date
    rushabh_msgs = []
    customer_msgs = []
    
    for msg in messages:
        if is_auto_reply(msg):
            continue
        
        from_addr = msg.get('from', '').lower()
        body = msg.get('body', '')
        
        if len(body.strip()) < 20:  # Skip very short messages
            continue
        
        if 'machinecraft' in from_addr:
            rushabh_msgs.append(msg)
        elif lead_email.lower() in from_addr.lower():
            customer_msgs.append(msg)
    
    # Pair up customer questions with Rushabh responses
    for i, cust_msg in enumerate(customer_msgs):
        # Find Rushabh's response (next message from him after this customer message)
        for rush_msg in rushabh_msgs:
            # Simple pairing - Rushabh's message subject matches or references customer's
            if cust_msg['subject'].lower() in rush_msg['subject'].lower() or \
               rush_msg['subject'].lower() in cust_msg['subject'].lower():
                pairs.append({
                    'customer_question': cust_msg['body'],
                    'rushabh_response': rush_msg['body'],
                    'subject': cust_msg['subject'],
                })
                break
    
    return pairs


def main():
    print("=" * 70)
    print("EXTRACTING CONVERSATIONS FROM INQUIRY FORM LEADS")
    print("=" * 70)
    
    # Load leads
    leads_file = PROJECT_ROOT / "data" / "training" / "inquiry_form_leads.json"
    with open(leads_file) as f:
        leads = json.load(f)
    
    print(f"Loaded {len(leads)} leads from inquiry form")
    
    # Initialize Gmail
    service = get_gmail_service()
    if not service:
        return
    
    # Track results
    conversations_found = []
    leads_with_threads = 0
    total_pairs = 0
    
    for i, lead in enumerate(leads):
        email = lead['email']
        company = lead['company']
        
        print(f"\n[{i+1}/{len(leads)}] Searching: {email} ({company})")
        
        # Search for threads
        threads = search_threads_for_lead(service, email)
        
        if threads:
            leads_with_threads += 1
            print(f"  Found {len(threads)} thread(s)")
            
            for thread in threads[:3]:  # Limit to 3 threads per lead
                messages = get_thread_messages(service, thread['id'])
                
                if len(messages) >= 2:
                    pairs = extract_qa_pairs(messages, email)
                    
                    if pairs:
                        total_pairs += len(pairs)
                        print(f"  Extracted {len(pairs)} Q&A pair(s)")
                        
                        for pair in pairs:
                            conversations_found.append({
                                'lead': lead,
                                'question': pair['customer_question'][:500],
                                'response': pair['rushabh_response'][:500],
                                'subject': pair['subject'],
                            })
        else:
            print("  No threads found")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Leads searched: {len(leads)}")
    print(f"Leads with threads: {leads_with_threads}")
    print(f"Total Q&A pairs extracted: {total_pairs}")
    
    # Save results
    output_file = PROJECT_ROOT / "data" / "training" / "inquiry_form_conversations.json"
    with open(output_file, 'w') as f:
        json.dump({
            'extracted_at': datetime.now().isoformat(),
            'total_leads': len(leads),
            'leads_with_conversations': leads_with_threads,
            'total_pairs': total_pairs,
            'conversations': conversations_found,
        }, f, indent=2, default=str)
    
    print(f"\nSaved to {output_file}")
    
    # Show sample conversations
    if conversations_found:
        print("\n" + "=" * 70)
        print("SAMPLE CONVERSATIONS")
        print("=" * 70)
        for conv in conversations_found[:3]:
            print(f"\n--- {conv['lead']['company']} ({conv['lead']['email']}) ---")
            print(f"Subject: {conv['subject']}")
            print(f"\nCustomer: {conv['question'][:200]}...")
            print(f"\nRushabh: {conv['response'][:200]}...")


if __name__ == "__main__":
    main()
