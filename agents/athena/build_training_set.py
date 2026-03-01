#!/usr/bin/env python3
"""
ATHENA Training Set Builder
===========================

Builds a comprehensive training dataset from:
1. Validated European lead conversations (european_lead_conversations.json)
2. Full email threads from Rushabh's mailbox
3. Conversation patterns extracted from genuine replies

The goal is to create 500+ Q&A pairs that teach IRA how Rushabh
actually communicates with sales leads.

Usage:
    python agents/athena/build_training_set.py
    python agents/athena/build_training_set.py --min-pairs 500
"""

import argparse
import base64
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Files
VALIDATED_LEADS_FILE = PROJECT_ROOT / "data" / "european_lead_conversations.json"
LEADS_CSV_FILE = PROJECT_ROOT / "data" / "imports" / "European & US Contacts for Single Station Nov 203.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "training" / "athena_training_set.json"

# Gmail setup
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_FILE = PROJECT_ROOT / "token_rushabh.json"

# Auto-reply patterns to filter out
AUTO_REPLY_PATTERNS = [
    r'out of (the )?office', r'automatic reply', r'auto[- ]?reply',
    r'automatische antwort', r'réponse automatique', r'abwesenheitsnotiz',
    r'vacation', r'holiday', r'delivery (status|failure)',
    r'undeliverable', r'mailer-daemon', r'postmaster', r'noreply',
]
AUTO_REPLY_REGEX = re.compile('|'.join(AUTO_REPLY_PATTERNS), re.IGNORECASE)


@dataclass
class TrainingPair:
    """A single Q&A training pair."""
    id: str
    category: str
    company: str
    contact_name: str
    subject: str
    customer_question: str
    rushabh_response: str
    conversation_context: str
    turn_number: int
    is_first_contact: bool
    tags: List[str] = field(default_factory=list)


@dataclass
class TrainingSet:
    """Complete training dataset for ATHENA."""
    metadata: Dict
    pairs: List[TrainingPair] = field(default_factory=list)


class GmailExtractor:
    """Extracts full conversation threads from Gmail."""
    
    def __init__(self):
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail."""
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            
            if not TOKEN_FILE.exists():
                print(f"[error] Token file not found: {TOKEN_FILE}")
                return
            
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), GMAIL_SCOPES)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            
            self.service = build('gmail', 'v1', credentials=creds)
            profile = self.service.users().getProfile(userId='me').execute()
            print(f"[auth] Connected as: {profile.get('emailAddress')}")
            
        except Exception as e:
            print(f"[error] Gmail auth failed: {e}")
    
    def get_thread_messages(self, thread_id: str) -> List[Dict]:
        """Get all messages in a thread."""
        if not self.service:
            return []
        
        try:
            thread = self.service.users().threads().get(
                userId='me', id=thread_id, format='full'
            ).execute()
            
            messages = []
            for msg in thread.get('messages', []):
                headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}
                body = self._extract_body(msg['payload'])
                
                messages.append({
                    'id': msg['id'],
                    'thread_id': thread_id,
                    'from': headers.get('from', ''),
                    'to': headers.get('to', ''),
                    'subject': headers.get('subject', ''),
                    'date': headers.get('date', ''),
                    'body': body,
                    'timestamp': int(msg.get('internalDate', 0)),
                })
            
            return sorted(messages, key=lambda x: x['timestamp'])
            
        except Exception as e:
            print(f"  [warn] Error getting thread: {e}")
            return []
    
    def search_threads(self, query: str, max_results: int = 50) -> List[str]:
        """Search for thread IDs."""
        if not self.service:
            return []
        
        thread_ids = set()
        try:
            results = self.service.users().messages().list(
                userId='me', q=query, maxResults=max_results
            ).execute()
            
            for msg in results.get('messages', []):
                email_data = self.service.users().messages().get(
                    userId='me', id=msg['id'], format='metadata'
                ).execute()
                thread_ids.add(email_data.get('threadId'))
        except:
            pass
        
        return list(thread_ids)
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract and clean email body."""
        body = ''
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
        
        return self._clean_body(body)
    
    def _clean_body(self, body: str) -> str:
        """Clean email body - remove signatures, quotes."""
        # Remove quoted replies
        body = re.split(r'On .+? wrote:', body, flags=re.DOTALL)[0]
        body = re.split(r'From: .+?@', body, flags=re.DOTALL)[0]
        
        # Remove signatures
        for sig in ['With Best Regards', 'Best Regards', 'Kind Regards', 
                   'Cheers\nRushabh', '*Rushabh Doshi*', '-- \n', 
                   'Director Responsible', 'S pozdravem', 'freundliche Grüße']:
            if sig in body:
                body = body.split(sig)[0]
        
        # Clean formatting
        body = re.sub(r'\[cid:[^\]]+\]', '', body)
        body = re.sub(r'<[^>]+>', '', body)
        body = re.sub(r'\n{3,}', '\n\n', body)
        
        return body.strip()


def is_genuine_message(msg: Dict) -> bool:
    """Check if a message is genuine (not auto-reply)."""
    subject = msg.get('subject', '').lower()
    body = msg.get('body', '').lower()
    from_addr = msg.get('from', '').lower()
    
    if AUTO_REPLY_REGEX.search(subject) or AUTO_REPLY_REGEX.search(body[:300]):
        return False
    
    if any(x in from_addr for x in ['noreply', 'no-reply', 'newsletter', 'marketing']):
        return False
    
    if len(body.strip()) < 30:
        return False
    
    return True


def categorize_message(text: str) -> Tuple[str, List[str]]:
    """Categorize a message and extract tags."""
    text_lower = text.lower()
    tags = []
    
    # Detect category
    if any(w in text_lower for w in ['price', 'cost', 'quote', 'quotation', '€', '$', 'budget']):
        category = 'pricing'
        tags.append('pricing')
    elif any(w in text_lower for w in ['spec', 'dimension', 'thickness', 'capacity', 'power']):
        category = 'technical'
        tags.append('specs')
    elif any(w in text_lower for w in ['spare', 'part', 'repair', 'service', 'error']):
        category = 'support'
        tags.append('service')
    elif any(w in text_lower for w in ['delivery', 'ship', 'install', 'timeline']):
        category = 'logistics'
        tags.append('logistics')
    elif any(w in text_lower for w in ['material', 'abs', 'hips', 'pp', 'pet', 'sheet']):
        category = 'materials'
        tags.append('materials')
    elif any(w in text_lower for w in ['visit', 'meet', 'demo', 'show', 'k-messe', 'trade']):
        category = 'meeting'
        tags.append('meeting')
    else:
        category = 'general'
    
    # Additional tags
    if any(w in text_lower for w in ['pf1', 'pf-1', 'pf1-x']):
        tags.append('PF1')
    if any(w in text_lower for w in ['am-p', 'am series', 'am-']):
        tags.append('AM-series')
    if any(w in text_lower for w in ['urgent', 'asap', 'immediately']):
        tags.append('urgent')
    if any(w in text_lower for w in ['competitor', 'illig', 'kiefel', 'geiss', 'cms']):
        tags.append('competitor')
    
    return category, tags


def extract_contact_name(from_addr: str) -> str:
    """Extract contact name from email address."""
    # "Pavel Votruba <pavel@email.com>" -> "Pavel Votruba"
    match = re.match(r'^([^<]+)<', from_addr)
    if match:
        return match.group(1).strip().strip('"')
    return from_addr.split('@')[0]


class ATHENATrainingSetBuilder:
    """Builds comprehensive training set for ATHENA."""
    
    def __init__(self):
        self.gmail = GmailExtractor()
        self.pairs: List[TrainingPair] = []
        self.pair_id = 0
    
    def load_validated_leads(self) -> Dict:
        """Load validated lead conversations."""
        if not VALIDATED_LEADS_FILE.exists():
            print(f"[error] Validated leads file not found: {VALIDATED_LEADS_FILE}")
            return {}
        
        with open(VALIDATED_LEADS_FILE, 'r') as f:
            return json.load(f)
    
    def extract_from_validated_leads(self, data: Dict) -> int:
        """Extract training pairs from validated genuine conversations."""
        genuine = data.get('genuine_conversations', [])
        print(f"\n[info] Processing {len(genuine)} leads with genuine conversations...")
        
        pairs_added = 0
        
        for lead in genuine:
            company = lead.get('company', 'Unknown')
            threads = lead.get('conversation_threads', [])
            
            if not threads:
                continue
            
            print(f"  → {company}: {len(threads)} threads...", end=' ')
            
            # Get full thread data for each genuine reply
            for thread_info in threads:
                from_addr = thread_info.get('from', '')
                
                # Skip non-sales messages (FRIMO invitations, LinkedIn, newsletters)
                if any(x in from_addr.lower() for x in ['frimo.com', 'linkedin', 'newsletter', 'xing']):
                    continue
                
                # Search for the full thread in Gmail
                subject = thread_info.get('subject', '')
                if not subject:
                    continue
                
                # Clean subject for search
                search_subject = re.sub(r'^(Re:|AW:|Fwd:)\s*', '', subject, flags=re.IGNORECASE)[:50]
                thread_ids = self.gmail.search_threads(f'subject:"{search_subject}"', max_results=5)
                
                for thread_id in thread_ids[:2]:
                    messages = self.gmail.get_thread_messages(thread_id)
                    pairs_added += self._extract_pairs_from_thread(messages, company)
            
            print(f"{pairs_added} pairs total")
        
        return pairs_added
    
    def extract_from_broader_search(self) -> int:
        """Extract additional training pairs from broader searches."""
        print("\n[info] Running broader email searches...")
        
        search_queries = [
            'subject:(quotation OR quote) from:@',  # Incoming quotes
            'subject:inquiry from:@ -newsletter',
            'subject:thermoforming -unsubscribe',
            'subject:(PF1 OR "AM-P") from:@',
            'subject:(price OR pricing) from:@ -newsletter',
            'from:durotherm.cz',  # Known good lead
            'from:parat',  # Known good lead
            'from:plastisart.com',  # Potential lead
        ]
        
        all_thread_ids = set()
        for query in search_queries:
            print(f"  → Searching: {query[:40]}...", end=' ')
            thread_ids = self.gmail.search_threads(query, max_results=30)
            all_thread_ids.update(thread_ids)
            print(f"{len(thread_ids)} threads")
        
        print(f"  → Total unique threads: {len(all_thread_ids)}")
        
        pairs_added = 0
        for thread_id in all_thread_ids:
            messages = self.gmail.get_thread_messages(thread_id)
            pairs_added += self._extract_pairs_from_thread(messages, "")
        
        return pairs_added
    
    def _extract_pairs_from_thread(self, messages: List[Dict], company: str) -> int:
        """Extract Q&A pairs from a conversation thread."""
        if len(messages) < 2:
            return 0
        
        pairs_added = 0
        
        # Categorize messages by sender
        customer_msgs = []
        rushabh_msgs = []
        
        for msg in messages:
            if not is_genuine_message(msg):
                continue
            
            from_addr = msg.get('from', '').lower()
            
            if 'machinecraft.org' in from_addr:
                rushabh_msgs.append(msg)
            else:
                # Check if it's from a business domain (not personal gmail etc for spam)
                domain = from_addr.split('@')[-1].split('>')[0] if '@' in from_addr else ''
                if domain and not any(x in domain for x in ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']):
                    customer_msgs.append(msg)
                elif len(msg.get('body', '')) > 100:  # Allow longer personal emails
                    customer_msgs.append(msg)
        
        # Need both sides
        if not customer_msgs or not rushabh_msgs:
            return 0
        
        # Sort by timestamp
        customer_msgs.sort(key=lambda x: x['timestamp'])
        rushabh_msgs.sort(key=lambda x: x['timestamp'])
        
        # Create Q&A pairs
        for i, cust_msg in enumerate(customer_msgs):
            # Find Rushabh's next response
            for rush_msg in rushabh_msgs:
                if rush_msg['timestamp'] > cust_msg['timestamp']:
                    self.pair_id += 1
                    
                    category, tags = categorize_message(cust_msg['body'])
                    contact = extract_contact_name(cust_msg['from'])
                    
                    # Determine company if not provided
                    if not company:
                        domain = cust_msg['from'].split('@')[-1].split('>')[0]
                        company = domain.split('.')[0].title() if domain else 'Unknown'
                    
                    pair = TrainingPair(
                        id=f'athena_{self.pair_id}',
                        category=category,
                        company=company,
                        contact_name=contact,
                        subject=cust_msg['subject'].replace('Re: ', '').replace('AW: ', '')[:80],
                        customer_question=cust_msg['body'][:1500],
                        rushabh_response=rush_msg['body'][:1500],
                        conversation_context=f"Turn {i+1} of conversation with {company}",
                        turn_number=i + 1,
                        is_first_contact=(i == 0),
                        tags=tags,
                    )
                    
                    self.pairs.append(pair)
                    pairs_added += 1
                    break
        
        return pairs_added
    
    def build(self, min_pairs: int = 100) -> TrainingSet:
        """Build the complete training set."""
        print("="*70)
        print("  ATHENA TRAINING SET BUILDER")
        print("="*70)
        
        # Load validated leads
        validated_data = self.load_validated_leads()
        
        # Extract from validated leads
        validated_pairs = self.extract_from_validated_leads(validated_data)
        print(f"\n[result] Pairs from validated leads: {validated_pairs}")
        
        # If we need more, do broader search
        if len(self.pairs) < min_pairs:
            print(f"\n[info] Need more pairs (have {len(self.pairs)}, need {min_pairs})")
            broader_pairs = self.extract_from_broader_search()
            print(f"[result] Pairs from broader search: {broader_pairs}")
        
        # Build final dataset
        categories = {}
        for pair in self.pairs:
            categories[pair.category] = categories.get(pair.category, 0) + 1
        
        companies = {}
        for pair in self.pairs:
            companies[pair.company] = companies.get(pair.company, 0) + 1
        
        dataset = TrainingSet(
            metadata={
                'built_at': datetime.now().isoformat(),
                'total_pairs': len(self.pairs),
                'categories': categories,
                'companies': dict(sorted(companies.items(), key=lambda x: -x[1])[:10]),
                'source': 'ATHENA Training Set Builder',
            },
            pairs=self.pairs,
        )
        
        return dataset
    
    def save(self, dataset: TrainingSet, output_path: Path):
        """Save the training set."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'metadata': dataset.metadata,
            'pairs': [asdict(p) for p in dataset.pairs],
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"\n[saved] {len(dataset.pairs)} training pairs → {output_path}")


def print_summary(dataset: TrainingSet):
    """Print training set summary."""
    print(f"\n{'='*70}")
    print("  ATHENA TRAINING SET SUMMARY")
    print(f"{'='*70}")
    
    print(f"""
Total Q&A Pairs:     {dataset.metadata['total_pairs']}
Built At:            {dataset.metadata['built_at']}
""")
    
    print("Categories:")
    for cat, count in sorted(dataset.metadata['categories'].items(), key=lambda x: -x[1]):
        pct = count / dataset.metadata['total_pairs'] * 100
        print(f"  {cat}: {count} ({pct:.0f}%)")
    
    print("\nTop Companies:")
    for company, count in list(dataset.metadata['companies'].items())[:5]:
        print(f"  {company}: {count}")
    
    # Sample pairs
    print(f"\n{'='*70}")
    print("  SAMPLE TRAINING PAIRS")
    print(f"{'='*70}")
    
    for pair in dataset.pairs[:3]:
        print(f"\n--- {pair.id} [{pair.category}] ---")
        print(f"Company: {pair.company} | Contact: {pair.contact_name}")
        print(f"Subject: {pair.subject}")
        print(f"Tags: {pair.tags}")
        print(f"\n[CUSTOMER]:\n{pair.customer_question[:300]}...")
        print(f"\n[RUSHABH]:\n{pair.rushabh_response[:300]}...")


def main():
    parser = argparse.ArgumentParser(description="ATHENA Training Set Builder")
    parser.add_argument('--min-pairs', type=int, default=100, help="Minimum pairs to collect")
    parser.add_argument('--output', type=str, default=str(OUTPUT_FILE))
    args = parser.parse_args()
    
    builder = ATHENATrainingSetBuilder()
    dataset = builder.build(min_pairs=args.min_pairs)
    
    print_summary(dataset)
    
    builder.save(dataset, Path(args.output))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
