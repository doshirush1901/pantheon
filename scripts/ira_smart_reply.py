#!/usr/bin/env python3
"""
IRA SMART REPLY - Knowledge-Augmented Email Responder
======================================================

When Ira receives an email, she:
1. Extracts key topics from the email
2. Searches her memory (Mem0) for relevant knowledge
3. Searches documents (PDFs) for additional context
4. Generates an informed reply using all available knowledge

This is the SMART reply system - Ira thinks before she speaks.

Usage:
    python scripts/ira_smart_reply.py           # Check last 1 hour
    python scripts/ira_smart_reply.py --hours 4 # Check last 4 hours
"""

import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta

# Setup
PROJECT_ROOT = Path(__file__).parent.parent
for line in (PROJECT_ROOT / ".env").read_text().splitlines():
    if line.strip() and not line.startswith('#') and '=' in line:
        key, _, value = line.partition('=')
        os.environ[key.strip()] = value.strip().strip('"')

sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/src/brain"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/src/memory"))

import openai
from knowledge_validator import send_email_gmail
from knowledge_retriever import KnowledgeRetriever

# Import email polish pipeline
try:
    from email_polish import EmailPolisher
    from email_styling import EmailStyler, RecipientRelationship
    POLISH_AVAILABLE = True
except ImportError:
    POLISH_AVAILABLE = False
    print("[warn] Email polish not available - emails will lack Ira's personality")

# State file
STATE_FILE = PROJECT_ROOT / "openclaw/agents/ira/workspace/smart_reply_state.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"replied_subjects": []}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_threads_needing_reply(service, hours: int = 1) -> list:
    """Get threads where the founder sent the last message."""
    import base64
    import re
    
    # Check what Ira already replied to
    sent_results = service.users().messages().list(
        userId='me', 
        labelIds=['SENT'], 
        maxResults=100
    ).execute()
    
    replied_subjects = set()
    for m in sent_results.get('messages', []):
        msg = service.users().messages().get(userId='me', id=m['id'], format='metadata').execute()
        headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
        if 'ira' in headers.get('from', '').lower():
            subj = headers.get('subject', '').lower().replace('re:', '').strip()
            replied_subjects.add(subj)
    
    # Get threads from the founder
    after_date = datetime.now() - timedelta(hours=hours)
    query = f"after:{after_date.strftime('%Y/%m/%d')} from:founder@example-company.org"
    
    results = service.users().messages().list(userId='me', q=query, maxResults=30).execute()
    messages = results.get('messages', [])
    
    threads = []
    seen = set()
    
    for msg_ref in messages:
        thread_id = msg_ref.get('threadId', msg_ref['id'])
        if thread_id in seen:
            continue
        seen.add(thread_id)
        
        # Get thread
        thread = service.users().threads().get(userId='me', id=thread_id, format='full').execute()
        thread_msgs = thread.get('messages', [])
        if not thread_msgs:
            continue
        
        # Check who sent last message
        last_msg = thread_msgs[-1]
        headers = {h['name'].lower(): h['value'] for h in last_msg.get('payload', {}).get('headers', [])}
        from_email = headers.get('from', '').lower()
        
        # Skip if Ira sent last
        if 'ira@' in from_email:
            continue
        
        # Skip if already replied
        subject = headers.get('subject', '').lower().replace('re:', '').strip()
        if subject in replied_subjects:
            continue
        
        # Get body
        body = ""
        payload = last_msg.get('payload', {})
        if payload.get('body', {}).get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        for part in payload.get('parts', []):
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    break
        
        # Clean body
        lines = body.split('\n')
        clean = []
        for line in lines:
            if line.strip().startswith('>') or 'wrote:' in line or 'With Best Regards' in line:
                break
            clean.append(line)
        body = '\n'.join(clean).strip()
        
        if len(body) < 10:
            continue
        
        threads.append({
            'id': last_msg['id'],
            'thread_id': thread_id,
            'subject': headers.get('subject', '(no subject)'),
            'from_email': headers.get('from', ''),
            'body': body,
        })
    
    return threads


def generate_smart_reply(email: dict, retriever: KnowledgeRetriever) -> str:
    """Generate a knowledge-augmented reply with proper polish."""
    client = openai.OpenAI()
    
    # Step 1: Retrieve relevant knowledge
    print("  🧠 Searching knowledge base...")
    knowledge = retriever.retrieve(email['body'], user_id="system_ira")
    
    knowledge_context = ""
    if knowledge.has_knowledge():
        knowledge_context = f"""

RELEVANT KNOWLEDGE FROM IRA'S BRAIN:
{knowledge.get_context(max_tokens=1500)}

Use this knowledge to inform your response. Cite specific facts when relevant."""
        print(f"    Found {knowledge.total_hits} relevant knowledge items")
    else:
        print("    No specific knowledge found - using general knowledge")
    
    # Step 2: Generate informed reply
    system_prompt = f"""You are Ira, Machinecraft's AI sales assistant with deep knowledge of thermoforming technology.

When responding:
1. CHECK your knowledge first - use the facts provided below
2. SHARE specific technical details when relevant
3. ACKNOWLEDGE the person's point
4. ADD your insight based on your knowledge
5. ASK follow-up questions to continue the dialogue

Your personality: Dry British humor, confident, knowledgeable, direct but warm.

About Machinecraft: Thermoforming machines (PF1 series, IMG machines), vacuum forming, pressure forming.
{knowledge_context}

Do NOT include greeting or signature - those will be added separately."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Reply to the founder:\n\n{email['body']}"}
        ],
        max_tokens=600,
        temperature=0.7,
    )
    
    raw_reply = response.choices[0].message.content.strip()
    
    # Step 3: Polish with Ira's personality + brand styling
    if POLISH_AVAILABLE:
        print("  ✨ Polishing with Ira's voice...")
        polisher = EmailPolisher()
        styler = EmailStyler()
        
        # Polish with personality
        polish_result = polisher.polish(
            draft_email=raw_reply,
            recipient_style={
                "formality_score": 35,
                "detail_score": 70,
                "technical_score": 80,
                "humor_score": 70,
            },
            emotional_state="neutral",
            warmth="trusted",
            use_llm=True,
        )
        polished = polish_result.polished
        
        # Format with brand styling
        formatted = styler.format_email_response(
            content=polished,
            recipient_name="Founder",
            relationship=RecipientRelationship.TRUSTED,
            include_greeting=True,
            include_closing=True,
            include_signature=True,
            signature_name="Ira",
            signature_title="Machinecraft",
            add_offer_help=False,
        )
        
        return formatted
    else:
        return f"Founder,\n\n{raw_reply}\n\n- Ira"


def main():
    parser = argparse.ArgumentParser(description="Ira Smart Reply")
    parser.add_argument("--hours", type=int, default=1, help="Hours to look back")
    parser.add_argument("--dry-run", action="store_true", help="Don't send")
    args = parser.parse_args()
    
    print(f"""
╔════════════════════════════════════════════════════════════════════╗
║                   IRA SMART REPLY                                  ║
║  Knowledge-augmented responses - Ira thinks before she speaks      ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    # Initialize
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    
    token_path = PROJECT_ROOT / 'token.json'
    creds = Credentials.from_authorized_user_file(str(token_path))
    service = build('gmail', 'v1', credentials=creds)
    
    retriever = KnowledgeRetriever()
    
    # Get threads needing reply
    print(f"Checking threads from last {args.hours} hour(s)...")
    threads = get_threads_needing_reply(service, hours=args.hours)
    
    if not threads:
        print("\n✓ No threads need a reply - Ira is up to date!")
        return
    
    print(f"\nFound {len(threads)} thread(s) needing smart reply\n")
    
    for i, thread in enumerate(threads, 1):
        print(f"{'='*60}")
        print(f"[{i}/{len(threads)}] Subject: {thread['subject']}")
        print(f"Founder: {thread['body'][:100]}...")
        print(f"{'='*60}")
        
        # Generate smart reply
        reply = generate_smart_reply(thread, retriever)
        print(f"\n📧 IRA'S SMART REPLY:\n{reply}\n")
        
        if not args.dry_run:
            subject = thread['subject']
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"
            
            success = send_email_gmail(
                to_email="founder@example-company.org",
                subject=subject,
                body=reply,
                from_email="ira@example-company.in",
            )
            print(f"{'✅ Sent!' if success else '❌ Failed'}")
        else:
            print("[DRY RUN - not sent]")
        
        print()
    
    print(f"{'='*60}")
    print(f"Done! Processed {len(threads)} thread(s) with smart replies")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
