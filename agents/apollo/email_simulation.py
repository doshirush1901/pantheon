#!/usr/bin/env python3
"""
APOLLO Real Email Simulation
=============================

Sends ACTUAL emails to IRA and waits for real responses.
Creates a genuine email trail in Rushabh's inbox for review.

Usage:
    python agents/apollo/email_simulation.py --persona european --turns 4
"""

import os
import sys
import json
import time
import base64
import random
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
for line in (PROJECT_ROOT / ".env").read_text().splitlines():
    if line.strip() and not line.startswith('#') and '=' in line:
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip().strip('"'))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import openai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Import personas from run_simulation (same directory)
APOLLO_DIR = Path(__file__).parent
sys.path.insert(0, str(APOLLO_DIR))
from run_simulation import PERSONAS, generate_customer_email

# =============================================================================
# CONFIG
# =============================================================================

IRA_EMAIL = "ira@machinecraft.org"
RUSHABH_EMAIL = "rushabh@machinecraft.org"  # Rushabh sends AS the simulated customer
REPLY_WAIT_SECONDS = 60  # How long to wait for IRA to reply
MAX_WAIT_RETRIES = 5

client = openai.OpenAI()


# =============================================================================
# GMAIL HELPERS
# =============================================================================

def get_gmail_service(as_rushabh: bool = True):
    """
    Get Gmail API service.
    
    Args:
        as_rushabh: If True, use Rushabh's token (to send as customer).
                   If False, use IRA's token.
    """
    if as_rushabh:
        token_file = PROJECT_ROOT / "token_rushabh.json"
        if not token_file.exists():
            # Fallback to main token
            token_file = PROJECT_ROOT / "token.json"
    else:
        token_file = PROJECT_ROOT / "token.json"
    
    if not token_file.exists():
        raise FileNotFoundError(f"Gmail token not found at {token_file}")
    
    creds = Credentials.from_authorized_user_file(str(token_file))
    return build('gmail', 'v1', credentials=creds)


def send_email_to_ira(service, subject: str, body: str, thread_id: str = None) -> dict:
    """
    Send an email TO IRA from Rushabh's account.
    
    Rushabh acts as the simulated customer - IRA sees the email and responds.
    The conversation thread is visible in Rushabh's inbox.
    """
    message = MIMEMultipart()
    message['to'] = IRA_EMAIL
    message['subject'] = subject
    
    # Add simulation header so we know this is a training email
    message['X-Apollo-Simulation'] = 'true'
    
    # Add body
    message.attach(MIMEText(body, 'plain'))
    
    # Encode
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    body_payload = {'raw': raw}
    
    # If we have a thread ID, add it to continue the thread
    if thread_id:
        body_payload['threadId'] = thread_id
    
    try:
        sent = service.users().messages().send(
            userId='me',
            body=body_payload
        ).execute()
        return {
            'id': sent.get('id', ''),
            'threadId': sent.get('threadId', ''),
        }
    except Exception as e:
        print(f"Error sending email: {e}")
        return {'id': '', 'threadId': ''}


def wait_for_reply(service, subject: str, after_time: datetime, max_wait: int = 300) -> Optional[str]:
    """
    Wait for IRA's reply to a specific email.
    
    Args:
        service: Gmail API service
        subject: Subject line to look for (Re: ...)
        after_time: Only look for messages after this time
        max_wait: Maximum seconds to wait
    
    Returns:
        Reply body text, or None if timeout
    """
    query = f'subject:"Re: {subject}" from:ira@machinecraft.org'
    wait_interval = 30
    total_waited = 0
    
    while total_waited < max_wait:
        print(f"   ⏳ Waiting for IRA's reply... ({total_waited}s/{max_wait}s)")
        
        try:
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=5
            ).execute()
            
            messages = results.get('messages', [])
            
            for msg_info in messages:
                msg = service.users().messages().get(
                    userId='me',
                    id=msg_info['id'],
                    format='full'
                ).execute()
                
                # Check timestamp
                internal_date = int(msg.get('internalDate', 0)) / 1000
                msg_time = datetime.fromtimestamp(internal_date)
                
                if msg_time > after_time:
                    # Found a reply after our message
                    body = extract_email_body(msg)
                    return body
        
        except Exception as e:
            print(f"   ⚠️ Error checking for reply: {e}")
        
        time.sleep(wait_interval)
        total_waited += wait_interval
    
    return None


def extract_email_body(message: dict) -> str:
    """Extract body text from Gmail message."""
    payload = message.get('payload', {})
    
    # Try to get plain text body
    if 'body' in payload and payload['body'].get('data'):
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    
    # Check parts
    parts = payload.get('parts', [])
    for part in parts:
        if part.get('mimeType') == 'text/plain':
            data = part.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')
    
    return "[Could not extract email body]"


# =============================================================================
# SIMULATION
# =============================================================================

def run_email_simulation(
    persona_type: str = "european",
    max_turns: int = 4,
    reply_wait: int = 300,
):
    """
    Run a REAL email simulation.
    
    Flow:
    1. APOLLO generates customer message
    2. Rushabh's account sends it TO IRA (simulating customer contact)
    3. IRA's auto-reply system responds
    4. APOLLO reads IRA's reply and generates follow-up
    5. Repeat...
    
    The full conversation thread is visible in Rushabh's inbox.
    """
    persona = PERSONAS.get(persona_type, PERSONAS["european"])
    conversation = []
    thread_id = None  # Track email thread
    
    # Generate unique subject for this simulation
    sim_id = datetime.now().strftime("%m%d%H%M")
    base_subject = f"[TRAINING-{sim_id}] {persona['name']} from {persona['company']}"
    
    print("\n" + "="*70)
    print("📧 APOLLO REAL EMAIL SIMULATION")
    print("="*70)
    print(f"\n📋 Simulating Customer:")
    print(f"   Name: {persona['name']}")
    print(f"   Company: {persona['company']}")
    print(f"   Industry: {persona['industry']}")
    print(f"   Budget: {persona['currency']} {persona['budget']}")
    print(f"\n📬 Email Flow:")
    print(f"   From: Rushabh's account (acting as customer)")
    print(f"   To: {IRA_EMAIL}")
    print(f"   Subject: {base_subject}")
    print(f"\n⏱️  Will wait up to {reply_wait}s for IRA's reply each turn")
    print("="*70)
    
    # Get Gmail service (use Rushabh's token to send as customer)
    try:
        service = get_gmail_service(as_rushabh=True)
        
        # Verify which account we're using
        profile = service.users().getProfile(userId='me').execute()
        sender_email = profile.get('emailAddress', 'unknown')
        print(f"✓ Gmail connected as: {sender_email}")
        print(f"  (Rushabh sends simulation emails, IRA auto-reply responds)\n")
    except Exception as e:
        print(f"❌ Gmail connection failed: {e}")
        print("   Make sure token_rushabh.json exists and is valid")
        return None
    
    for turn in range(1, max_turns + 1):
        print(f"\n{'─'*70}")
        print(f"📧 TURN {turn}/{max_turns}")
        print(f"{'─'*70}")
        
        # Generate customer email based on conversation history
        customer_email = generate_customer_email(persona, conversation, turn)
        
        # Add signature to make it look like a real email
        customer_email_with_sig = f"""{customer_email}

---
{persona['name']}
{persona['role']}
{persona['company']}
{persona['location']}
[APOLLO Training Simulation]"""
        
        # Subject stays the same (replies in same thread)
        subject = base_subject
        
        print(f"\n👤 CUSTOMER ({persona['name']}):")
        print(f"   {customer_email[:150]}...")
        
        # Send email TO IRA
        send_time = datetime.now()
        result = send_email_to_ira(
            service=service,
            subject=subject,
            body=customer_email_with_sig,
            thread_id=thread_id,
        )
        
        if not result['id']:
            print("   ❌ Failed to send email")
            break
        
        thread_id = result['threadId']  # Track thread for replies
        print(f"   ✓ Sent to IRA (thread: {thread_id[:12]}...)")
        
        # Wait for IRA's reply
        print(f"\n🤖 Waiting for IRA's response...")
        ira_reply = wait_for_reply(
            service=service,
            subject=base_subject,
            after_time=send_time,
            max_wait=reply_wait,
        )
        
        if ira_reply:
            # Clean up the reply (remove quoted text)
            clean_reply = clean_email_reply(ira_reply)
            print(f"\n🤖 IRA replied:")
            print(f"   {clean_reply[:200]}...")
        else:
            print("   ⏰ Timeout - IRA didn't reply")
            print("   💡 Tip: Make sure IRA's auto-reply is running (scripts/ira_auto_loop.py)")
            clean_reply = "[No reply received - IRA auto-reply may not be running]"
        
        # Store conversation
        conversation.append({
            "turn": turn,
            "customer": customer_email,
            "ira": clean_reply,
            "subject": subject,
            "sent_at": send_time.isoformat(),
            "thread_id": thread_id,
        })
        
        # Pause between turns (let IRA process)
        if turn < max_turns and ira_reply:
            print("\n   ⏳ Pausing 10s before next turn...")
            time.sleep(10)
    
    # Save results
    output_dir = PROJECT_ROOT / "data" / "simulations"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"email_sim_{persona_type}_{timestamp}.json"
    
    results = {
        "type": "real_email_simulation",
        "persona": persona,
        "subject": base_subject,
        "thread_id": thread_id,
        "turns": len(conversation),
        "conversation": conversation,
        "generated_at": datetime.now().isoformat(),
    }
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*70)
    print("✅ EMAIL SIMULATION COMPLETE")
    print(f"   Total turns: {len(conversation)}")
    print(f"   Results saved: {output_file}")
    print(f"\n   📬 CHECK RUSHABH'S INBOX!")
    print(f"   Subject: {base_subject}")
    print(f"   Thread ID: {thread_id}")
    print("="*70)
    
    return results


def clean_email_reply(body: str) -> str:
    """Clean up email reply by removing quoted text."""
    lines = body.split('\n')
    clean_lines = []
    
    for line in lines:
        # Stop at quoted content markers
        if line.startswith('>') or line.startswith('On ') and ' wrote:' in line:
            break
        if '---' in line and 'Original Message' in line:
            break
        clean_lines.append(line)
    
    return '\n'.join(clean_lines).strip()


# =============================================================================
# ALTERNATIVE: Direct IRA Call (No real email)
# =============================================================================

def run_direct_simulation(
    persona_type: str = "european",
    max_turns: int = 4,
):
    """
    Run simulation by directly calling IRA's brain (no actual emails).
    
    This is faster for testing but doesn't create real email trails.
    """
    from run_simulation import run_simulation
    return run_simulation(
        persona_type=persona_type,
        max_turns=max_turns,
        interactive=False,
        use_real_ira=True,
    )


def check_ira_running() -> bool:
    """Check if IRA's auto-reply is running."""
    import subprocess
    result = subprocess.run(
        ["pgrep", "-f", "ira_auto_loop"],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def start_ira_auto_reply():
    """Start IRA's auto-reply in the background."""
    import subprocess
    
    script_path = PROJECT_ROOT / "scripts" / "ira_auto_loop.py"
    log_file = PROJECT_ROOT / "data" / "simulations" / "ira_auto_reply.log"
    
    print(f"🚀 Starting IRA auto-reply...")
    print(f"   Log: {log_file}")
    
    # Start in background
    with open(log_file, 'w') as log:
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),
        )
    
    print(f"   PID: {process.pid}")
    time.sleep(5)  # Give it time to start
    
    return process.pid


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="APOLLO Real Email Simulation")
    parser.add_argument("--persona", "-p", type=str, default="european",
                       choices=list(PERSONAS.keys()),
                       help="Customer persona to simulate")
    parser.add_argument("--turns", "-t", type=int, default=4,
                       help="Number of email exchanges")
    parser.add_argument("--wait", "-w", type=int, default=300,
                       help="Max seconds to wait for IRA's reply")
    parser.add_argument("--direct", "-d", action="store_true",
                       help="Use direct IRA call instead of real emails")
    parser.add_argument("--start-ira", action="store_true",
                       help="Start IRA auto-reply before simulation")
    
    args = parser.parse_args()
    
    if args.direct:
        print("Running in DIRECT mode (no real emails)")
        run_direct_simulation(
            persona_type=args.persona,
            max_turns=args.turns,
        )
    else:
        print("\n📧 APOLLO Real Email Simulation")
        print("="*50)
        
        # Check if IRA is running
        if not check_ira_running():
            print("⚠️  IRA auto-reply is NOT running")
            
            if args.start_ira:
                start_ira_auto_reply()
                print("   ✓ Started IRA auto-reply")
            else:
                print("\nOptions:")
                print("  1. Run with --start-ira to auto-start IRA")
                print("  2. Manually run: python scripts/ira_auto_loop.py &")
                print("  3. Run with --direct for simulation without real emails")
                
                response = input("\nStart IRA auto-reply now? [y/N] ").strip().lower()
                if response == 'y':
                    start_ira_auto_reply()
                else:
                    print("\n⏭️  Proceeding without IRA auto-reply...")
                    print("   (IRA won't respond to emails)")
        else:
            print("✓ IRA auto-reply is running")
        
        print()
        run_email_simulation(
            persona_type=args.persona,
            max_turns=args.turns,
            reply_wait=args.wait,
        )
