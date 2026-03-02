#!/usr/bin/env python3
"""
Send Ira Intro — Email + Telegram
==================================
Sends an intro message to Rushabh via email and Telegram so he knows Ira is live.

Run from IRA root:
    python scripts/send_ira_intro.py
    python scripts/send_ira_intro.py --email-only
    python scripts/send_ira_intro.py --telegram-only
"""

import argparse
import base64
import logging
import os
import sys
from email.mime.text import MIMEText
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ira_intro")

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load env
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

INTRO_BODY = """Hi Rushabh,

Ira is awake and ready. 🟢

I'm now listening on:
• Email — reply to this thread or send a new message
• Telegram — send me a message or /help for commands

All fixes from the audit are applied. You can start interacting — I'll log our conversations and learn from your feedback during my nightly dream cycle.

— Ira
"""

INTRO_TELEGRAM = """🟢 Ira is awake and ready!

I'm listening on email and Telegram. You can start interacting now — I'll log our conversations and learn from your feedback during my nightly dream cycle.

/help for commands.
"""


def send_email(to: str) -> bool:
    """Send intro email via Gmail API."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        token_file = PROJECT_ROOT / "token.json"
        creds_file = PROJECT_ROOT / "credentials.json"
        if not token_file.exists():
            logger.error("token.json not found — run Gmail OAuth flow first")
            return False

        creds = Credentials.from_authorized_user_file(str(token_file), ["https://www.googleapis.com/auth/gmail.modify"])
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                logger.error("Gmail credentials expired — re-authenticate")
                return False

        service = build("gmail", "v1", credentials=creds)
        msg = MIMEText(INTRO_BODY)
        msg["to"] = to
        msg["from"] = os.environ.get("IRA_EMAIL", "ira@machinecraft.org")
        msg["subject"] = "Ira is awake — ready to interact"
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        logger.info("Intro email sent to %s", to)
        return True
    except Exception as e:
        logger.error("Email send failed: %s", e)
        return False


def send_telegram() -> bool:
    """Send intro message via Telegram API."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("RUSHABH_TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return False
    if not chat_id:
        logger.error("RUSHABH_TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID not set")
        return False

    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": INTRO_TELEGRAM}, timeout=10)
        if r.ok:
            logger.info("Intro Telegram message sent")
            return True
        logger.error("Telegram API: %s %s", r.status_code, r.text[:200])
        return False
    except Exception as e:
        logger.error("Telegram send failed: %s", e)
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--email-only", action="store_true")
    ap.add_argument("--telegram-only", action="store_true")
    args = ap.parse_args()

    email_ok = True
    telegram_ok = True

    if not args.telegram_only:
        to = os.environ.get("RUSHABH_EMAIL", "rushabh@machinecraft.org")
        email_ok = send_email(to)
    if not args.email_only:
        telegram_ok = send_telegram()

    if email_ok and telegram_ok:
        logger.info("Intro sent successfully")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
