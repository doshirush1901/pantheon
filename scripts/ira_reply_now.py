#!/usr/bin/env python3
"""
IRA REPLY NOW - Smart email responder
=====================================

CRITICAL RULE: Only reply to threads where the founder sent the LAST message.
Ira waits for the founder to reply before sending another message.

Logic:
1. Check inbox for threads with recent activity
2. For each thread, check who sent the LAST message
3. Only reply if the founder (not Ira) sent the last message
4. Store thread state to avoid duplicate replies

Usage:
    python scripts/ira_reply_now.py           # Last 1 hour
    python scripts/ira_reply_now.py --hours 4 # Last 4 hours
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

# Import email polish pipeline
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/src/brain"))
try:
    from email_polish import EmailPolisher
    from email_styling import EmailStyler, RecipientRelationship
    POLISH_AVAILABLE = True
except ImportError:
    POLISH_AVAILABLE = False
    print("[warn] Email polish not available - emails will lack Ira's personality")

# State file to track replied threads
STATE_FILE = PROJECT_ROOT / "openclaw/agents/ira/workspace/email_reply_state.json"


def load_state() -> dict:
    """Load reply state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"replied_message_ids": [], "last_check": None}


def save_state(state: dict):
    """Save reply state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_recent_ira_sent_subjects(service, hours: int = 24) -> set:
    """Get subjects of emails Ira sent recently to avoid duplicates."""
    try:
        results = service.users().messages().list(
            userId='me', 
            labelIds=['SENT'], 
            maxResults=100
        ).execute()
        
        subjects = set()
        for m in results.get('messages', []):
            msg = service.users().messages().get(userId='me', id=m['id'], format='metadata').execute()
            headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
            from_addr = headers.get('from', '').lower()
            if 'ira' in from_addr:
                subj = headers.get('subject', '').lower().strip()
                # Normalize subject (remove Re:, Fwd:, etc.)
                subj = subj.replace('re:', '').replace('fwd:', '').strip()
                subjects.add(subj)
        return subjects
    except:
        return set()


def get_threads_needing_reply(hours: int = 1):
    """
    Get threads where the founder sent the LAST message (Ira needs to reply).
    
    CRITICAL: 
    - Only return threads where the founder's message is the most recent
    - Skip threads where Ira already replied recently
    - Check both state file AND sent folder to prevent spam
    """
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    import base64
    import re
    
    token_path = PROJECT_ROOT / 'token.json'
    creds = Credentials.from_authorized_user_file(str(token_path))
    service = build('gmail', 'v1', credentials=creds)
    
    state = load_state()
    replied_ids = set(state.get("replied_message_ids", [])[-500:])
    
    # IMPORTANT: Check what Ira already sent to avoid duplicates
    print("Checking Ira's sent folder for recent replies...")
    recent_sent_subjects = get_recent_ira_sent_subjects(service, hours=24)
    print(f"  Found {len(recent_sent_subjects)} recent subjects Ira replied to")
    
    # Get threads with recent activity from the founder
    after_date = datetime.now() - timedelta(hours=hours)
    query = f"after:{after_date.strftime('%Y/%m/%d')} from:founder@example-company.org"
    
    results = service.users().messages().list(userId='me', q=query, maxResults=30).execute()
    messages = results.get('messages', [])
    
    threads_to_reply = []
    seen_threads = set()
    
    for msg_ref in messages:
        thread_id = msg_ref.get('threadId', msg_ref['id'])
        
        # Skip if we've already processed this thread
        if thread_id in seen_threads:
            continue
        seen_threads.add(thread_id)
        
        # Get FULL thread to check who sent the last message
        thread = service.users().threads().get(userId='me', id=thread_id, format='full').execute()
        thread_messages = thread.get('messages', [])
        
        if not thread_messages:
            continue
        
        # Get the LAST message in the thread
        last_msg = thread_messages[-1]
        last_msg_id = last_msg['id']
        
        # Skip if we already replied to this message
        if last_msg_id in replied_ids:
            continue
        
        # Check who sent the last message
        headers = {h['name'].lower(): h['value'] for h in last_msg.get('payload', {}).get('headers', [])}
        from_email = headers.get('from', '').lower()
        
        # CRITICAL: Only reply if the founder sent the last message
        # Skip if Ira sent the last message (we're waiting for the founder)
        if 'ira@' in from_email or 'ira@machinecraft' in from_email:
            print(f"  [SKIP] Thread '{headers.get('subject', '?')[:40]}' - Ira sent last, waiting for the founder")
            continue
        
        # Also check if Ira already replied to this subject recently
        subject = headers.get('subject', '').lower().replace('re:', '').replace('fwd:', '').strip()
        if subject in recent_sent_subjects:
            print(f"  [SKIP] Thread '{headers.get('subject', '?')[:40]}' - Ira already replied (in sent folder)")
            continue
        
        # This is a thread where the founder sent the last message - we need to reply!
        # Parse the message
        from_raw = headers.get('from', '')
        from_match = re.match(r'(?:"?([^"<]*)"?\s*)?<?([^>]+)>?', from_raw)
        from_name = from_match.group(1).strip() if from_match and from_match.group(1) else ''
        from_email_clean = from_match.group(2).strip() if from_match else from_raw
        
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
        
        # Clean body - remove quoted content and signatures
        lines = body.split('\n')
        clean_lines = []
        for line in lines:
            if line.strip().startswith('>') or 'wrote:' in line:
                break
            if line.strip() == '--' or line.strip() == '—':
                break
            if 'With Best Regards' in line:
                break
            clean_lines.append(line)
        body = '\n'.join(clean_lines).strip()
        
        # Skip if body is too short
        if len(body) < 10:
            continue
        
        threads_to_reply.append({
            'id': last_msg_id,
            'thread_id': thread_id,
            'subject': headers.get('subject', '(no subject)'),
            'from_name': from_name,
            'from_email': from_email_clean,
            'body': body,
        })
    
    return threads_to_reply


def generate_reply(email: dict) -> str:
    """Generate Ira's reply with counter-questions and proper polish."""
    client = openai.OpenAI()
    
    system_prompt = """You are Ira, Machinecraft's AI sales assistant.

When the founder messages you:
1. ACKNOWLEDGE his point
2. ADD your perspective or insight
3. ASK 1-2 follow-up questions

Keep it conversational and concise. Don't be robotic.

About you:
- Purpose: Sales, market research, business development
- Boss: the founder
- Company: Machinecraft - thermoforming machines
- Personality: Dry wit, confident, knowledgeable

Do NOT include greeting or signature - those will be added separately."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Reply to the founder:\n\n{email['body']}"}
        ],
        max_tokens=400,
        temperature=0.7,
    )
    
    raw_reply = response.choices[0].message.content.strip()
    
    # Apply email polish pipeline if available
    if POLISH_AVAILABLE:
        polisher = EmailPolisher()
        styler = EmailStyler()
        
        # Step 1: Polish with Ira's personality + the founder's style
        polish_result = polisher.polish(
            draft_email=raw_reply,
            recipient_style={
                "formality_score": 35,  # the founder is casual
                "detail_score": 70,
                "technical_score": 80,
                "humor_score": 70,
            },
            emotional_state="neutral",
            warmth="trusted",  # the founder is boss/trusted
            use_llm=True,
        )
        polished = polish_result.polished
        
        # Step 2: Format with brand styling
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
        # Fallback without polish
        return f"Founder,\n\n{raw_reply}\n\n- Ira"


def main():
    parser = argparse.ArgumentParser(description="Ira Reply Now - Smart Responder")
    parser.add_argument("--hours", type=int, default=1, help="Hours to look back")
    parser.add_argument("--dry-run", action="store_true", help="Don't send, just show")
    args = parser.parse_args()
    
    print(f"""
╔════════════════════════════════════════════════════════════════════╗
║                     IRA REPLY NOW (SMART)                          ║
║  Only replies when the founder sent the last message               ║
║  Waits for the founder's reply before sending again                ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    print(f"Checking threads from last {args.hours} hour(s)...\n")
    
    threads = get_threads_needing_reply(hours=args.hours)
    
    if not threads:
        print("✓ No threads need a reply - Ira is up to date!")
        print("  (Either Ira sent the last message, or no new emails)")
        return
    
    print(f"Found {len(threads)} thread(s) where the founder is waiting for Ira's reply\n")
    
    state = load_state()
    replied_ids = state.get("replied_message_ids", [])
    
    for i, thread in enumerate(threads, 1):
        print(f"{'='*60}")
        print(f"[{i}/{len(threads)}] Subject: {thread['subject']}")
        print(f"Founder said: {thread['body'][:100]}...")
        print(f"{'='*60}")
        
        reply = generate_reply(thread)
        print(f"\nIRA'S REPLY:\n{reply}\n")
        
        if not args.dry_run:
            subject = thread['subject']
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"
            
            success = send_email_gmail(
                to_email=thread['from_email'],
                subject=subject,
                body=reply,
                from_email="ira@example-company.in",
            )
            
            if success:
                print(f"✅ Sent!")
                replied_ids.append(thread['id'])
            else:
                print(f"❌ Failed")
        else:
            print("[DRY RUN - not sent]")
        
        print()
    
    # Save state
    if not args.dry_run:
        state["replied_message_ids"] = replied_ids[-500:]
        state["last_check"] = datetime.now().isoformat()
        save_state(state)
    
    print(f"{'='*60}")
    print(f"Done! Replied to {len(threads)} thread(s)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
