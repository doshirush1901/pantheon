#!/usr/bin/env python3
"""
ATHENA Training Data Extractor (Legacy)
=======================================
NOTE: Use build_training_set.py instead - it uses validated lead data.

Extracts genuine sales conversations from Rushabh's mailbox to build
training data for IRA. Only includes conversations with GENUINE replies
(filters out auto-replies, bounces, vacation notices).

Architecture:
1. Load European sales leads
2. Search for email threads with each lead
3. Filter for genuine conversations only
4. Extract Q&A pairs (customer question → Rushabh response)
5. Categorize by conversation type
6. Save as structured training data

Usage:
    python agents/atlas/training_data_extractor.py
    python agents/atlas/training_data_extractor.py --output data/training/atlas_training.json
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

# Gmail setup
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = PROJECT_ROOT / "credentials_rushabh.json"
TOKEN_FILE = PROJECT_ROOT / "token_rushabh.json"

if not CREDENTIALS_FILE.exists():
    CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
    TOKEN_FILE = PROJECT_ROOT / "token.json"

# Auto-reply detection patterns (from check_european_lead_conversations.py)
AUTO_REPLY_PATTERNS = [
    r'out of (the )?office',
    r'automatic reply',
    r'auto[- ]?reply',
    r'auto[- ]?response',
    r'automatische antwort',  # German
    r'réponse automatique',   # French
    r'abwesenheitsnotiz',     # German OOO
    r'vacation',
    r'holiday',
    r'away from (my )?desk',
    r'maternity leave',
    r'paternity leave',
    r'currently unavailable',
    r'i am currently out',
    r'thank you for your (email|message).*will (get back|respond|reply)',
    r'this is an automated',
    r'do not reply',
    r'noreply',
    r'no-reply',
    r'mailer-daemon',
    r'postmaster',
    r'delivery (status|failure|failed)',
    r'undeliverable',
    r'returned mail',
    r'bounce',
]

AUTO_REPLY_REGEX = re.compile('|'.join(AUTO_REPLY_PATTERNS), re.IGNORECASE)

# Categories for training data
CATEGORY_PATTERNS = {
    'pricing_inquiry': ['price', 'cost', 'quote', 'quotation', 'offer', 'rate', 'budget', 'investment', '€', '$', 'usd', 'eur'],
    'technical_specs': ['spec', 'dimension', 'size', 'thickness', 'capacity', 'depth', 'width', 'power', 'voltage', 'kw'],
    'logistics': ['install', 'delivery', 'shipping', 'schedule', 'timeline', 'lead time', 'transit', 'freight'],
    'support': ['spare', 'part', 'repair', 'issue', 'problem', 'error', 'fault', 'maintenance', 'service'],
    'materials': ['material', 'abs', 'hips', 'pp', 'pet', 'hdpe', 'pvc', 'sheet', 'plastic', 'gauge'],
    'comparison': ['compare', 'difference', 'vs', 'versus', 'competitor', 'illig', 'kiefel', 'geiss'],
    'meeting_request': ['visit', 'meet', 'demo', 'show', 'see', 'tour', 'appointment', 'call'],
    'application': ['application', 'product', 'produce', 'make', 'form', 'packaging', 'tray', 'blister'],
}


@dataclass
class TrainingPair:
    """A single Q&A training pair."""
    id: str
    category: str
    company: str
    subject: str
    customer_question: str
    rushabh_response: str
    customer_email: str
    thread_id: str
    timestamp: int
    is_first_contact: bool = False
    is_followup: bool = False
    conversation_turn: int = 1


@dataclass
class TrainingDataset:
    """Complete training dataset."""
    metadata: Dict
    qa_pairs: List[TrainingPair] = field(default_factory=list)
    conversations: List[Dict] = field(default_factory=list)


def is_auto_reply(email_data: Dict) -> bool:
    """Check if an email is an auto-reply."""
    subject = email_data.get('subject', '').lower()
    body = email_data.get('body', '').lower()
    from_addr = email_data.get('from', '').lower()
    
    if AUTO_REPLY_REGEX.search(subject):
        return True
    
    if AUTO_REPLY_REGEX.search(body[:500]):
        return True
    
    if any(x in from_addr for x in ['noreply', 'no-reply', 'mailer-daemon', 'postmaster', 'notification']):
        return True
    
    return False


def is_genuine_reply(email_data: Dict) -> bool:
    """Check if an email is a genuine reply (not auto-reply, has real content)."""
    if is_auto_reply(email_data):
        return False
    
    body = email_data.get('body', '')
    if len(body.strip()) < 30:  # Need at least 30 chars of content
        return False
    
    # Check for newsletter/marketing patterns
    newsletter_patterns = ['unsubscribe', 'view in browser', 'email preferences', 'click here to']
    if any(p in body.lower() for p in newsletter_patterns):
        return False
    
    return True


def categorize_message(text: str) -> str:
    """Categorize a message based on content."""
    text_lower = text.lower()
    
    for category, keywords in CATEGORY_PATTERNS.items():
        if any(kw in text_lower for kw in keywords):
            return category
    
    return 'general_inquiry'


def clean_body(body: str) -> str:
    """Clean email body - remove signatures, quotes, HTML."""
    # Remove quoted replies
    body = re.split(r'On .+? wrote:', body, flags=re.DOTALL)[0]
    body = re.split(r'From: .+?@', body, flags=re.DOTALL)[0]
    
    # Remove signatures
    for sig in ['With Best Regards', 'Best Regards', 'Kind Regards', 'Thanks,', 
                '-- ', 'Sent from my', '*Rushabh Doshi*', 'Cheers\nRushabh',
                'Director Responsible', 'Business Development', 'Click here']:
        if sig in body:
            body = body.split(sig)[0]
    
    # Clean up formatting
    body = re.sub(r'\[cid:[^\]]+\]', '', body)  # Remove image references
    body = re.sub(r'<[^>]+>', '', body)  # Remove HTML tags
    body = re.sub(r'https?://\S+', '[link]', body)  # Normalize URLs
    body = re.sub(r'\n{3,}', '\n\n', body)  # Normalize whitespace
    
    return body.strip()


def extract_body(payload: Dict) -> str:
    """Extract plain text body from Gmail payload."""
    if 'body' in payload and payload['body'].get('data'):
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        return clean_body(body)
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                return clean_body(body)
            if 'parts' in part:
                result = extract_body(part)
                if result:
                    return result
    return ""


class TrainingDataExtractor:
    """Extracts training data from Gmail conversations."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.service = None
        self.pair_id = 0
        
        if not dry_run:
            self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API."""
        print("[auth] Starting authentication...", flush=True)
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            
            creds = None
            if TOKEN_FILE.exists():
                creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), GMAIL_SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    TOKEN_FILE.write_text(creds.to_json())
                else:
                    if not CREDENTIALS_FILE.exists():
                        raise FileNotFoundError(f"Credentials not found: {CREDENTIALS_FILE}")
                    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), GMAIL_SCOPES)
                    creds = flow.run_local_server(port=0)
                    TOKEN_FILE.write_text(creds.to_json())
            
            self.service = build('gmail', 'v1', credentials=creds)
            profile = self.service.users().getProfile(userId='me').execute()
            print(f"[auth] Connected as: {profile.get('emailAddress')}", flush=True)
            
        except Exception as e:
            print(f"[error] Authentication failed: {e}")
            self.dry_run = True
    
    def search_threads(self, query: str, max_results: int = 50) -> List[str]:
        """Search for thread IDs matching query."""
        if self.dry_run:
            return []
        
        thread_ids = set()
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            for msg in results.get('messages', []):
                email_data = self.service.users().messages().get(
                    userId='me', id=msg['id'], format='metadata'
                ).execute()
                thread_ids.add(email_data.get('threadId'))
        except Exception as e:
            print(f"  [warn] Search error: {e}")
        
        return list(thread_ids)
    
    def get_thread(self, thread_id: str) -> Optional[Dict]:
        """Get full thread data."""
        if self.dry_run:
            return None
        
        try:
            return self.service.users().threads().get(
                userId='me', id=thread_id, format='full'
            ).execute()
        except:
            return None
    
    def extract_training_pairs_from_thread(self, thread: Dict, company: str = "") -> List[TrainingPair]:
        """Extract Q&A training pairs from a conversation thread."""
        pairs = []
        messages = thread.get('messages', [])
        
        if len(messages) < 2:
            return pairs
        
        # Parse all messages
        parsed_messages = []
        for msg in messages:
            headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}
            sender = headers.get('from', '')
            body = extract_body(msg['payload'])
            
            if len(body) < 30:
                continue
            
            is_rushabh = 'machinecraft.org' in sender.lower()
            
            msg_data = {
                'sender': sender,
                'is_rushabh': is_rushabh,
                'subject': headers.get('subject', '').replace('Re: ', '').replace('RE: ', ''),
                'body': body[:1500],  # Limit body size
                'timestamp': int(msg.get('internalDate', 0)),
                'thread_id': thread.get('id', ''),
            }
            
            # Only include genuine customer replies
            if not is_rushabh and not is_genuine_reply(msg_data):
                continue
            
            parsed_messages.append(msg_data)
        
        # Sort by timestamp
        parsed_messages.sort(key=lambda x: x['timestamp'])
        
        # Check we have both sides of conversation
        has_customer = any(not m['is_rushabh'] for m in parsed_messages)
        has_rushabh = any(m['is_rushabh'] for m in parsed_messages)
        
        if not (has_customer and has_rushabh):
            return pairs
        
        # Create Q&A pairs: customer message → next Rushabh response
        turn = 0
        for i, msg in enumerate(parsed_messages):
            if not msg['is_rushabh']:  # Customer message
                # Find Rushabh's next response
                for j in range(i + 1, len(parsed_messages)):
                    if parsed_messages[j]['is_rushabh']:
                        turn += 1
                        self.pair_id += 1
                        
                        pair = TrainingPair(
                            id=f'qa_{self.pair_id}',
                            category=categorize_message(msg['body']),
                            company=company,
                            subject=msg['subject'],
                            customer_question=msg['body'],
                            rushabh_response=parsed_messages[j]['body'],
                            customer_email=msg['sender'][:60],
                            thread_id=msg['thread_id'],
                            timestamp=msg['timestamp'],
                            is_first_contact=(turn == 1),
                            is_followup=(turn > 1),
                            conversation_turn=turn,
                        )
                        pairs.append(pair)
                        break
        
        return pairs
    
    def extract_from_european_leads(self, leads_file: Path, limit: int = None) -> TrainingDataset:
        """Extract training data from European leads conversations."""
        print(f"\n{'='*70}")
        print("  EXTRACTING TRAINING DATA FROM EUROPEAN LEADS")
        print(f"{'='*70}\n")
        
        # Load leads
        if not leads_file.exists():
            print(f"[error] Leads file not found: {leads_file}")
            return TrainingDataset(metadata={})
        
        with open(leads_file, 'r') as f:
            data = json.load(f)
        
        leads = data.get('leads', [])
        if limit:
            leads = leads[:limit]
        
        print(f"[info] Processing {len(leads)} leads...")
        
        all_pairs = []
        all_conversations = []
        leads_with_genuine = 0
        
        for i, lead in enumerate(leads, 1):
            company = lead.get('company', 'Unknown')
            print(f"[{i}/{len(leads)}] {company}...", end=' ', flush=True)
            
            # Build search query from company name
            base_name = company.lower()
            base_name = re.sub(r'\s*(gmbh|ag|ltd|group|ab|a/s|s\.a\.).*$', '', base_name, flags=re.IGNORECASE)
            base_name = re.sub(r'[^a-z0-9\s]', '', base_name).strip()
            
            if len(base_name) < 3:
                print("(skipped - name too short)")
                continue
            
            # Search for threads
            query = f'({base_name}) -unsubscribe -newsletter'
            thread_ids = self.search_threads(query, max_results=20)
            
            if not thread_ids:
                print("(no threads)")
                continue
            
            company_pairs = []
            for thread_id in thread_ids[:5]:  # Max 5 threads per lead
                thread = self.get_thread(thread_id)
                if thread:
                    pairs = self.extract_training_pairs_from_thread(thread, company)
                    company_pairs.extend(pairs)
            
            if company_pairs:
                leads_with_genuine += 1
                all_pairs.extend(company_pairs)
                print(f"✓ {len(company_pairs)} pairs")
            else:
                print("(no genuine replies)")
        
        # Build dataset
        categories = {}
        for pair in all_pairs:
            categories[pair.category] = categories.get(pair.category, 0) + 1
        
        dataset = TrainingDataset(
            metadata={
                'extracted_at': datetime.now().isoformat(),
                'source': str(leads_file),
                'total_leads': len(leads),
                'leads_with_genuine_conversations': leads_with_genuine,
                'total_qa_pairs': len(all_pairs),
                'categories': categories,
            },
            qa_pairs=all_pairs,
        )
        
        return dataset
    
    def extract_from_search_queries(self, queries: List[str]) -> TrainingDataset:
        """Extract training data using broader search queries."""
        print(f"\n{'='*70}")
        print("  EXTRACTING TRAINING DATA FROM SEARCH QUERIES")
        print(f"{'='*70}\n")
        
        all_thread_ids = set()
        
        for query in queries:
            print(f"[search] {query[:50]}...", end=' ', flush=True)
            thread_ids = self.search_threads(query, max_results=30)
            all_thread_ids.update(thread_ids)
            print(f"{len(thread_ids)} threads")
        
        print(f"\n[info] Total unique threads: {len(all_thread_ids)}")
        
        all_pairs = []
        for thread_id in all_thread_ids:
            thread = self.get_thread(thread_id)
            if thread:
                pairs = self.extract_training_pairs_from_thread(thread)
                all_pairs.extend(pairs)
        
        categories = {}
        for pair in all_pairs:
            categories[pair.category] = categories.get(pair.category, 0) + 1
        
        return TrainingDataset(
            metadata={
                'extracted_at': datetime.now().isoformat(),
                'source': 'search_queries',
                'queries_used': queries,
                'total_qa_pairs': len(all_pairs),
                'categories': categories,
            },
            qa_pairs=all_pairs,
        )


def save_dataset(dataset: TrainingDataset, output_file: Path):
    """Save training dataset to JSON."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        'metadata': dataset.metadata,
        'qa_pairs': [asdict(p) for p in dataset.qa_pairs],
    }
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"\n[saved] {len(dataset.qa_pairs)} training pairs → {output_file}")


def print_summary(dataset: TrainingDataset):
    """Print dataset summary."""
    print(f"\n{'='*70}")
    print("  TRAINING DATA SUMMARY")
    print(f"{'='*70}")
    
    print(f"""
Total Q&A Pairs:        {dataset.metadata.get('total_qa_pairs', 0)}
Leads with Genuine:     {dataset.metadata.get('leads_with_genuine_conversations', 'N/A')}
""")
    
    print("Categories:")
    for cat, count in sorted(dataset.metadata.get('categories', {}).items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    
    # Sample pairs
    print(f"\n{'='*70}")
    print("  SAMPLE TRAINING PAIRS")
    print(f"{'='*70}")
    
    for pair in dataset.qa_pairs[:3]:
        print(f"\n--- {pair.id} [{pair.category}] ---")
        print(f"Company: {pair.company}")
        print(f"Turn: {pair.conversation_turn} | First: {pair.is_first_contact}")
        print(f"\n[CUSTOMER]: {pair.customer_question[:200]}...")
        print(f"\n[RUSHABH]: {pair.rushabh_response[:200]}...")


def main():
    parser = argparse.ArgumentParser(description="Extract training data from email conversations")
    parser.add_argument('--output', type=str, default='data/training/atlas_training_data.json')
    parser.add_argument('--leads', type=str, default='data/imports/european_leads_structured.json')
    parser.add_argument('--limit', type=int, default=None, help="Limit number of leads")
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    extractor = TrainingDataExtractor(dry_run=args.dry_run)
    
    # Extract from European leads
    leads_file = PROJECT_ROOT / args.leads
    dataset = extractor.extract_from_european_leads(leads_file, limit=args.limit)
    
    # Also extract from broader search queries
    search_queries = [
        'subject:(quote OR quotation) -unsubscribe',
        'subject:(inquiry OR enquiry) -newsletter',
        'subject:thermoforming -unsubscribe',
        'subject:(PF1 OR "PF-1" OR AM-P)',
        'subject:(price OR pricing) category:primary',
        'subject:(machine OR machines) -newsletter',
    ]
    
    search_dataset = extractor.extract_from_search_queries(search_queries)
    
    # Merge datasets
    existing_ids = {p.thread_id for p in dataset.qa_pairs}
    for pair in search_dataset.qa_pairs:
        if pair.thread_id not in existing_ids:
            dataset.qa_pairs.append(pair)
            existing_ids.add(pair.thread_id)
    
    # Update metadata
    categories = {}
    for pair in dataset.qa_pairs:
        categories[pair.category] = categories.get(pair.category, 0) + 1
    
    dataset.metadata['total_qa_pairs'] = len(dataset.qa_pairs)
    dataset.metadata['categories'] = categories
    
    # Save and summarize
    output_file = PROJECT_ROOT / args.output
    save_dataset(dataset, output_file)
    print_summary(dataset)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
