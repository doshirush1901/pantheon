#!/usr/bin/env python3
"""
CRM GMAIL SYNC — Keeps Mnemosyne's CRM live from Rushabh's mailbox
===================================================================

Scans Gmail for threads with known CRM contacts, updates:
- Conversation history (new threads, replies)
- Reply tracking (who replied, quality classification)
- Deal stage auto-progression (replied = engaged)
- New contacts discovered in email threads

Designed to run as a cron job every 30-60 minutes, or on-demand.

Usage:
    # Cron (every 30 min)
    */30 * * * * cd /path/to/Ira && python scripts/crm_gmail_sync.py

    # Manual
    python scripts/crm_gmail_sync.py
    python scripts/crm_gmail_sync.py --full    # Scan all contacts, not just leads
    python scripts/crm_gmail_sync.py --days 7  # Only look at last 7 days
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/src/crm"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("crm_gmail_sync")

IRA_EMAIL = os.getenv("IRA_EMAIL", "ira@machinecraft.org")
RUSHABH_EMAIL = os.getenv("RUSHABH_EMAIL", "rushabh@machinecraft.org")


def sync(full: bool = False, days: int = 14):
    """Run the Gmail -> CRM sync."""
    from ira_crm import get_crm

    crm = get_crm()

    # Init Gmail
    try:
        from email_openclaw_bridge import GmailClient, GMAIL_AVAILABLE
        if not GMAIL_AVAILABLE:
            logger.error("Gmail API not available")
            return {"error": "Gmail not available"}
        gmail = GmailClient()
    except Exception as e:
        logger.error(f"Gmail init failed: {e}")
        return {"error": str(e)}

    # Get contacts to scan
    if full:
        contacts = crm.get_all_contacts()
    else:
        leads = crm.get_all_leads()
        contacts = [crm.get_contact(l.email) for l in leads]
        contacts = [c for c in contacts if c]

    if not contacts:
        logger.info("No contacts to scan")
        return {"scanned": 0}

    logger.info(f"Scanning Gmail for {len(contacts)} {'contacts' if full else 'leads'} (last {days}d)")

    after_date = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
    scanned = 0
    new_conversations = 0
    new_replies = 0

    for contact in contacts:
        email = contact.email
        if not email or "@placeholder" in email:
            continue

        try:
            query = f"(from:{email} OR to:{email}) after:{after_date}"
            results = gmail.service.users().messages().list(
                userId="me", q=query, maxResults=20,
            ).execute()

            messages = results.get("messages", [])
            if not messages:
                continue

            scanned += 1

            for msg_info in messages[:15]:
                try:
                    details = gmail._get_email_details(msg_info["id"])
                    if not details:
                        continue

                    sender = details.get("from", "")
                    subject = details.get("subject", "")
                    body = details.get("body", "") or details.get("snippet", "")
                    date = details.get("date", "")
                    thread_id = details.get("thread_id", "")

                    is_from_lead = email.lower() in sender.lower()
                    is_from_ira = IRA_EMAIL.lower() in sender.lower()
                    is_from_rushabh = RUSHABH_EMAIL.lower() in sender.lower()

                    if is_from_lead:
                        direction = "inbound"
                    elif is_from_ira or is_from_rushabh:
                        direction = "outbound"
                    else:
                        continue

                    # Check if we already have this conversation entry (by thread + date)
                    existing = crm.get_conversation_context(email, limit=50)
                    already_logged = any(
                        e.thread_id == thread_id and e.subject == subject and e.direction == direction
                        for e in existing
                    )

                    if not already_logged:
                        crm.add_conversation(
                            email, direction=direction,
                            subject=subject, preview=body[:300],
                            date=date, thread_id=thread_id,
                            source="gmail_sync",
                        )
                        new_conversations += 1

                        # If inbound, this is a reply — update the lead
                        if direction == "inbound":
                            quality = _classify_reply(body)
                            lead = crm.get_lead(email)
                            if lead and not lead.last_reply_at:
                                crm.record_reply(
                                    email, thread_id=thread_id,
                                    quality=quality, subject=subject,
                                    preview=body[:300],
                                )
                                new_replies += 1
                                logger.info(f"  Reply from {contact.company}: {quality}")

                except Exception as e:
                    logger.debug(f"  Message parse error: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Gmail scan error for {email}: {e}")
            continue

    result = {
        "timestamp": datetime.now().isoformat(),
        "contacts_scanned": scanned,
        "new_conversations": new_conversations,
        "new_replies": new_replies,
    }

    logger.info(f"Sync complete: {scanned} scanned, {new_conversations} conversations, {new_replies} replies")
    return result


def _classify_reply(body: str) -> str:
    """Classify the quality of a reply."""
    if not body:
        return "unknown"
    body_lower = body.lower()

    if any(w in body_lower for w in ["out of office", "auto-reply", "automatic reply", "away from"]):
        return "auto_reply"
    if any(w in body_lower for w in ["undeliverable", "bounce", "failed delivery"]):
        return "bounce"
    if any(w in body_lower for w in ["unsubscribe", "remove me", "stop emailing"]):
        return "unsubscribe"
    if any(w in body_lower for w in [
        "interested", "tell me more", "send me", "quote", "pricing",
        "call", "meeting", "schedule", "discuss", "specifications",
        "brochure", "when can", "how much",
    ]):
        return "engaged"
    if len(body.strip()) > 50:
        return "engaged"

    return "polite_decline"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CRM Gmail Sync")
    parser.add_argument("--full", action="store_true", help="Scan all contacts, not just leads")
    parser.add_argument("--days", type=int, default=14, help="Look back N days (default 14)")
    args = parser.parse_args()

    result = sync(full=args.full, days=args.days)
    print(json.dumps(result, indent=2))
