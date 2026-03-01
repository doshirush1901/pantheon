#!/usr/bin/env python3
"""
European Sales Lead Conversation Checker
=========================================

Checks Rushabh's mailbox (rushabh@machinecraft.org) to identify which European
sales leads have had genuine email conversations (sent email + received genuine reply).

Filters out:
- Auto-replies (out of office, vacation, automatic response)
- Delivery failures
- Bounce messages

Usage:
    python scripts/check_european_lead_conversations.py
    python scripts/check_european_lead_conversations.py --dry-run
    python scripts/check_european_lead_conversations.py --output results.json
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
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

EUROPEAN_LEADS_FILE = PROJECT_ROOT / "data" / "imports" / "european_leads_structured.json"
OUTPUT_FILE = PROJECT_ROOT / "data" / "european_lead_conversations.json"

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = PROJECT_ROOT / "credentials_rushabh.json"
TOKEN_FILE = PROJECT_ROOT / "token_rushabh.json"

if not CREDENTIALS_FILE.exists():
    CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
    TOKEN_FILE = PROJECT_ROOT / "token.json"

AUTO_REPLY_PATTERNS = [
    r'out of (the )?office',
    r'automatic reply',
    r'auto[- ]?reply',
    r'auto[- ]?response',
    r'automatische antwort',
    r'réponse automatique',
    r'abwesenheitsnotiz',
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


@dataclass
class EmailExchange:
    """Record of an email exchange with a lead."""
    company: str
    lead_id: str
    contact_email: str
    emails_sent: int = 0
    emails_received: int = 0
    genuine_replies: int = 0
    auto_replies: int = 0
    first_contact: Optional[str] = None
    last_contact: Optional[str] = None
    conversation_threads: List[Dict] = field(default_factory=list)
    has_genuine_conversation: bool = False


@dataclass
class ConversationSummary:
    """Summary of all European lead conversations."""
    checked_at: str
    total_leads: int
    leads_contacted: int
    leads_with_replies: int
    leads_with_genuine_conversations: int
    exchanges: List[EmailExchange] = field(default_factory=list)


class GmailSearcher:
    """Search Gmail for email exchanges with European leads."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.service = None
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
            
            print(f"[auth] Looking for token at: {TOKEN_FILE}", flush=True)
            creds = None
            if TOKEN_FILE.exists():
                print("[auth] Loading existing token...", flush=True)
                creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), GMAIL_SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    print("[auth] Refreshing credentials...", flush=True)
                    creds.refresh(Request())
                    TOKEN_FILE.write_text(creds.to_json())
                else:
                    if not CREDENTIALS_FILE.exists():
                        raise FileNotFoundError(
                            f"Credentials not found: {CREDENTIALS_FILE}\n"
                            "Run: python agents/prometheus/setup_dual_oauth.py"
                        )
                    print("[auth] Starting OAuth flow...", flush=True)
                    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), GMAIL_SCOPES)
                    creds = flow.run_local_server(port=0)
                    TOKEN_FILE.write_text(creds.to_json())
            
            print("[auth] Building Gmail service...", flush=True)
            self.service = build('gmail', 'v1', credentials=creds)
            
            print("[auth] Getting user profile...", flush=True)
            profile = self.service.users().getProfile(userId='me').execute()
            print(f"[auth] Connected as: {profile.get('emailAddress')}", flush=True)
            
        except ImportError as e:
            print(f"[error] Gmail API not installed: {e}", flush=True)
            print("[error] Run: pip install google-api-python-client google-auth-oauthlib", flush=True)
            self.dry_run = True
        except Exception as e:
            print(f"[error] Authentication failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
            self.dry_run = True
    
    def search_company_emails(self, company_name: str, company_domains: List[str] = None) -> Dict:
        """Search for all emails related to a company."""
        if self.dry_run:
            return {"sent": [], "received": []}
        
        results = {"sent": [], "received": []}
        
        company_search = company_name.lower().replace(" ", " OR ").replace("gmbh", "").replace("ag", "").replace("ltd", "").strip()
        company_search = ' OR '.join([w for w in company_search.split() if len(w) > 2][:3])
        
        try:
            sent_results = self.service.users().messages().list(
                userId='me',
                q=f'in:sent ({company_search})',
                maxResults=50
            ).execute()
            
            for msg in sent_results.get('messages', []):
                email_data = self._get_email_details(msg['id'])
                if email_data and self._is_relevant_to_company(email_data, company_name):
                    results["sent"].append(email_data)
        except Exception as e:
            print(f"  [warn] Error searching sent emails: {e}")
        
        try:
            received_results = self.service.users().messages().list(
                userId='me',
                q=f'-in:sent ({company_search})',
                maxResults=50
            ).execute()
            
            for msg in received_results.get('messages', []):
                email_data = self._get_email_details(msg['id'])
                if email_data and self._is_relevant_to_company(email_data, company_name):
                    results["received"].append(email_data)
        except Exception as e:
            print(f"  [warn] Error searching received emails: {e}")
        
        return results
    
    def search_by_domain_pattern(self, company_name: str) -> Dict:
        """Search using domain patterns derived from company name."""
        if self.dry_run:
            return {"sent": [], "received": []}
        
        results = {"sent": [], "received": []}
        
        base_name = company_name.lower()
        base_name = re.sub(r'\s*(gmbh|ag|ltd|group|ab|a/s|s\.a\.|co\.? ?kg|holding).*$', '', base_name, flags=re.IGNORECASE)
        base_name = re.sub(r'[^a-z0-9]', '', base_name)
        
        if len(base_name) < 3:
            return results
        
        domain_patterns = [
            f"@{base_name}.",
            f"@{base_name[:8]}",
        ]
        
        for pattern in domain_patterns:
            try:
                search_results = self.service.users().messages().list(
                    userId='me',
                    q=f'from:({pattern}) OR to:({pattern})',
                    maxResults=30
                ).execute()
                
                for msg in search_results.get('messages', []):
                    email_data = self._get_email_details(msg['id'])
                    if email_data:
                        if self._is_sent_email(email_data):
                            if email_data not in results["sent"]:
                                results["sent"].append(email_data)
                        else:
                            if email_data not in results["received"]:
                                results["received"].append(email_data)
            except Exception:
                pass
        
        return results
    
    def _get_email_details(self, message_id: str) -> Optional[Dict]:
        """Get email details."""
        try:
            msg = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}
            body = self._extract_body(msg['payload'])
            
            return {
                'id': message_id,
                'thread_id': msg.get('threadId'),
                'from': headers.get('from', ''),
                'to': headers.get('to', ''),
                'subject': headers.get('subject', ''),
                'date': headers.get('date', ''),
                'body': body[:1000],
                'labels': msg.get('labelIds', []),
            }
        except Exception:
            return None
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract plain text body."""
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                if 'parts' in part:
                    result = self._extract_body(part)
                    if result:
                        return result
        return ""
    
    def _is_sent_email(self, email_data: Dict) -> bool:
        """Check if this is a sent email."""
        return 'SENT' in email_data.get('labels', [])
    
    def _is_relevant_to_company(self, email_data: Dict, company_name: str) -> bool:
        """Check if email is related to the company."""
        company_words = [w.lower() for w in company_name.split() if len(w) > 2]
        company_words = [w for w in company_words if w not in ['gmbh', 'ltd', 'group', 'the', 'and']]
        
        if not company_words:
            return False
        
        search_text = f"{email_data.get('from', '')} {email_data.get('to', '')} {email_data.get('subject', '')} {email_data.get('body', '')[:500]}".lower()
        
        matches = sum(1 for w in company_words if w in search_text)
        return matches >= min(2, len(company_words))


def is_auto_reply(email_data: Dict) -> bool:
    """Check if an email is an auto-reply."""
    subject = email_data.get('subject', '').lower()
    body = email_data.get('body', '').lower()
    from_addr = email_data.get('from', '').lower()
    
    if AUTO_REPLY_REGEX.search(subject):
        return True
    
    if AUTO_REPLY_REGEX.search(body[:500]):
        return True
    
    if any(x in from_addr for x in ['noreply', 'no-reply', 'mailer-daemon', 'postmaster']):
        return True
    
    return False


def is_genuine_reply(email_data: Dict) -> bool:
    """Check if an email is a genuine reply (not auto-reply)."""
    if is_auto_reply(email_data):
        return False
    
    body = email_data.get('body', '')
    if len(body.strip()) < 20:
        return False
    
    return True


def load_european_leads() -> List[Dict]:
    """Load European leads from JSON file."""
    if not EUROPEAN_LEADS_FILE.exists():
        print(f"[error] European leads file not found: {EUROPEAN_LEADS_FILE}")
        return []
    
    with open(EUROPEAN_LEADS_FILE, 'r') as f:
        data = json.load(f)
    
    return data.get('leads', [])


def check_all_leads(searcher: GmailSearcher, leads: List[Dict], verbose: bool = True, limit: int = None) -> ConversationSummary:
    """Check conversation status for all European leads."""
    if limit:
        leads = leads[:limit]
    
    summary = ConversationSummary(
        checked_at=datetime.now().isoformat(),
        total_leads=len(leads),
        leads_contacted=0,
        leads_with_replies=0,
        leads_with_genuine_conversations=0,
    )
    
    print(f"\n{'='*70}")
    print(f"  CHECKING {len(leads)} EUROPEAN SALES LEADS")
    print(f"{'='*70}\n")
    sys.stdout.flush()
    
    for i, lead in enumerate(leads, 1):
        company = lead.get('company', 'Unknown')
        lead_id = lead.get('id', f'unknown-{i}')
        
        print(f"[{i}/{len(leads)}] {company}...", flush=True)
        
        exchange = EmailExchange(
            company=company,
            lead_id=lead_id,
            contact_email="",
        )
        
        emails = searcher.search_company_emails(company)
        
        if not emails["sent"] and not emails["received"]:
            emails = searcher.search_by_domain_pattern(company)
        
        exchange.emails_sent = len(emails["sent"])
        exchange.emails_received = len(emails["received"])
        
        if exchange.emails_sent > 0:
            summary.leads_contacted += 1
        
        for email in emails["received"]:
            if is_genuine_reply(email):
                exchange.genuine_replies += 1
                exchange.conversation_threads.append({
                    "type": "genuine_reply",
                    "from": email.get('from', ''),
                    "subject": email.get('subject', ''),
                    "date": email.get('date', ''),
                    "preview": email.get('body', '')[:200],
                })
            else:
                exchange.auto_replies += 1
        
        if exchange.genuine_replies > 0:
            exchange.has_genuine_conversation = True
            summary.leads_with_genuine_conversations += 1
        
        if exchange.emails_received > 0:
            summary.leads_with_replies += 1
        
        all_emails = emails["sent"] + emails["received"]
        if all_emails:
            dates = [e.get('date', '') for e in all_emails if e.get('date')]
            if dates:
                exchange.first_contact = min(dates)
                exchange.last_contact = max(dates)
        
        status = ""
        if exchange.has_genuine_conversation:
            status = "✓ GENUINE CONVERSATION"
        elif exchange.auto_replies > 0:
            status = f"~ Auto-reply only ({exchange.auto_replies})"
        elif exchange.emails_sent > 0:
            status = f"→ Sent {exchange.emails_sent}, no reply"
        else:
            status = "○ No contact"
        
        print(f"    {status}")
        
        summary.exchanges.append(exchange)
    
    return summary


def print_summary(summary: ConversationSummary):
    """Print a formatted summary."""
    print(f"\n{'='*70}")
    print("  EUROPEAN SALES LEADS - CONVERSATION SUMMARY")
    print(f"{'='*70}")
    
    print(f"""
Total Leads:                    {summary.total_leads}
Leads Contacted (email sent):   {summary.leads_contacted}
Leads with Any Reply:           {summary.leads_with_replies}
Leads with GENUINE Conversation: {summary.leads_with_genuine_conversations}
""")
    
    genuine = [e for e in summary.exchanges if e.has_genuine_conversation]
    if genuine:
        print("\n" + "="*70)
        print("  COMPANIES WITH GENUINE CONVERSATIONS")
        print("="*70)
        for e in genuine:
            print(f"\n  ✓ {e.company}")
            print(f"    Emails sent: {e.emails_sent}")
            print(f"    Genuine replies: {e.genuine_replies}")
            if e.conversation_threads:
                for thread in e.conversation_threads[:2]:
                    print(f"    └─ From: {thread.get('from', '')[:50]}")
                    print(f"       Subject: {thread.get('subject', '')[:50]}")
                    print(f"       Date: {thread.get('date', '')}")
    else:
        print("\n  No genuine conversations found yet.")
    
    contacted_no_reply = [e for e in summary.exchanges if e.emails_sent > 0 and e.genuine_replies == 0]
    if contacted_no_reply:
        print("\n" + "="*70)
        print("  CONTACTED BUT NO GENUINE REPLY")
        print("="*70)
        for e in contacted_no_reply:
            status = f"(auto-reply: {e.auto_replies})" if e.auto_replies > 0 else "(no reply)"
            print(f"  → {e.company}: sent {e.emails_sent} {status}")
    
    not_contacted = [e for e in summary.exchanges if e.emails_sent == 0]
    if not_contacted:
        print("\n" + "="*70)
        print(f"  NOT YET CONTACTED ({len(not_contacted)} leads)")
        print("="*70)
        for e in not_contacted[:10]:
            print(f"  ○ {e.company}")
        if len(not_contacted) > 10:
            print(f"  ... and {len(not_contacted) - 10} more")


def save_results(summary: ConversationSummary, output_file: Path):
    """Save results to JSON file."""
    results = {
        "checked_at": summary.checked_at,
        "total_leads": summary.total_leads,
        "leads_contacted": summary.leads_contacted,
        "leads_with_replies": summary.leads_with_replies,
        "leads_with_genuine_conversations": summary.leads_with_genuine_conversations,
        "genuine_conversations": [
            asdict(e) for e in summary.exchanges if e.has_genuine_conversation
        ],
        "contacted_no_reply": [
            asdict(e) for e in summary.exchanges if e.emails_sent > 0 and e.genuine_replies == 0
        ],
        "not_contacted": [
            asdict(e) for e in summary.exchanges if e.emails_sent == 0
        ],
    }
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[saved] Results written to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Check European lead conversations")
    parser.add_argument('--dry-run', action='store_true', help="Run without Gmail access")
    parser.add_argument('--output', type=str, default=str(OUTPUT_FILE), help="Output JSON file")
    parser.add_argument('--verbose', '-v', action='store_true', help="Verbose output")
    parser.add_argument('--limit', type=int, default=None, help="Limit number of leads to check")
    args = parser.parse_args()
    
    leads = load_european_leads()
    if not leads:
        print("[error] No leads found")
        return 1
    
    print(f"[info] Loaded {len(leads)} European leads", flush=True)
    
    searcher = GmailSearcher(dry_run=args.dry_run)
    
    summary = check_all_leads(searcher, leads, verbose=args.verbose, limit=args.limit)
    
    print_summary(summary)
    
    save_results(summary, Path(args.output))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
