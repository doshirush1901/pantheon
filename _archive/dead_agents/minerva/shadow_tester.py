#!/usr/bin/env python3
"""
MINERVA — Shadow Tester
========================

Monitors Ira's real incoming emails, generates a draft response,
has Minerva audit it, and presents both to Rushabh for review
before sending.

Usage:
    python agents/minerva/shadow_tester.py --count 5
    python agents/minerva/shadow_tester.py --continuous
"""

import argparse
import base64
import json
import logging
import sys
import time
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent

sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

_brain_path = str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "brain")
if _brain_path not in sys.path:
    sys.path.insert(0, _brain_path)

from generate_answer import generate_answer

_apollo_path = str(PROJECT_ROOT / "agents" / "apollo")
if _apollo_path not in sys.path:
    sys.path.insert(0, _apollo_path)

from grounded_coach import coach_review

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

logger = logging.getLogger("minerva.shadow_tester")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

IRA_EMAIL = "ira@machinecraft.org"
RUSHABH_EMAIL = "rushabh@machinecraft.org"

LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_FILE = LOG_DIR / "shadow_test_results.jsonl"


# ============================================================================
# GMAIL SERVICE
# ============================================================================

def _build_gmail_service(token_name: str) -> Optional[Any]:
    if not GMAIL_AVAILABLE:
        return None
    candidates = [
        PROJECT_ROOT / token_name,
        PROJECT_ROOT / "tokens" / token_name,
        Path.home() / ".credentials" / token_name,
    ]
    for path in candidates:
        if path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(path))
                return build("gmail", "v1", credentials=creds)
            except Exception as exc:
                logger.warning("Token %s found but failed: %s", path, exc)
    return None


def _get_gmail_service() -> Optional[Any]:
    return (
        _build_gmail_service("token.json")
        or _build_gmail_service("token_ira_backup.json")
    )


def _decode_body(payload: Dict) -> str:
    """Recursively extract plain-text body from a Gmail message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        text = _decode_body(part)
        if text:
            return text

    body_data = payload.get("body", {}).get("data")
    if body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

    return ""


def _extract_header(headers: List[Dict], name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


# ============================================================================
# GET UNREAD CUSTOMER EMAILS
# ============================================================================

def get_unread_customer_emails(count: int = 5) -> List[Dict]:
    """
    Read Ira's inbox for unread emails, excluding messages from
    Rushabh and from Ira herself.

    Returns list of {id, from, subject, body, thread_id}.
    """
    service = _get_gmail_service()
    if not service:
        logger.error("Gmail service unavailable — check token.json")
        return []

    query = f"is:unread -from:{RUSHABH_EMAIL} -from:{IRA_EMAIL}"
    try:
        result = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=count)
            .execute()
        )
    except Exception as exc:
        logger.error("Failed to list messages: %s", exc)
        return []

    messages = result.get("messages", [])
    if not messages:
        logger.info("No unread customer emails found.")
        return []

    emails: List[Dict] = []
    for msg_stub in messages:
        try:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_stub["id"], format="full")
                .execute()
            )
            headers = msg.get("payload", {}).get("headers", [])
            emails.append({
                "id": msg["id"],
                "from": _extract_header(headers, "From"),
                "subject": _extract_header(headers, "Subject"),
                "body": _decode_body(msg.get("payload", {})),
                "thread_id": msg.get("threadId", ""),
            })
        except Exception as exc:
            logger.warning("Failed to fetch message %s: %s", msg_stub["id"], exc)

    logger.info("Fetched %d unread customer emails", len(emails))
    return emails


# ============================================================================
# SHADOW TEST AN EMAIL
# ============================================================================

def shadow_test_email(email: Dict) -> Dict:
    """
    Generate Ira's draft response for an email and run Minerva's
    coach_review against it.

    Returns {email, draft, review, verdict, score, errors}.
    """
    question = email.get("body", "")
    subject = email.get("subject", "")
    full_context = f"Subject: {subject}\n\n{question}" if subject else question

    logger.info("Generating draft for: %s", subject[:80])
    try:
        response_obj = generate_answer(
            intent=full_context,
            channel="email",
            use_multi_pass=True,
        )
        draft = response_obj.response if hasattr(response_obj, "response") else str(response_obj)
    except Exception as exc:
        logger.error("generate_answer failed: %s", exc)
        draft = f"[GENERATION FAILED: {exc}]"

    logger.info("Running Minerva coach review...")
    try:
        review = coach_review(question=full_context, response=draft, category="recommendation")
    except Exception as exc:
        logger.error("coach_review failed: %s", exc)
        review = {
            "verdict": "REVISE",
            "overall_score": 0.0,
            "factual_errors": [f"Review failed: {exc}"],
        }

    return {
        "email": email,
        "draft": draft,
        "review": review,
        "verdict": review.get("verdict", "REVISE"),
        "score": review.get("overall_score", 0.0),
        "errors": review.get("factual_errors", []),
    }


# ============================================================================
# SEND REVIEW TO RUSHABH
# ============================================================================

def send_review_to_rushabh(email: Dict, draft: str, review: Dict) -> bool:
    """
    Compose and send a review email to Rushabh showing the original
    customer email, Ira's draft, and Minerva's audit.

    Returns True on success.
    """
    service = _get_gmail_service()
    if not service:
        logger.error("Gmail service unavailable — cannot send review")
        return False

    verdict = review.get("verdict", "REVISE")
    score = review.get("overall_score", 0.0)
    errors = review.get("factual_errors", [])
    missing = review.get("missing_information", [])
    guidance = review.get("correction_guidance", "")
    wins = review.get("wins", "")

    errors_block = "\n".join(f"  - {e}" for e in errors) if errors else "  None found"
    missing_block = "\n".join(f"  - {m}" for m in missing) if missing else "  None"

    subject = f"[Minerva Shadow] {verdict} ({score}/10) — {email.get('subject', 'No subject')}"

    body = f"""\
MINERVA SHADOW TEST REVIEW
{'=' * 50}

VERDICT: {verdict}  |  SCORE: {score}/10
{'=' * 50}

--- ORIGINAL CUSTOMER EMAIL ---
From: {email.get('from', 'Unknown')}
Subject: {email.get('subject', 'No subject')}

{email.get('body', '')[:2000]}

--- IRA'S DRAFT RESPONSE ---

{draft[:3000]}

--- MINERVA'S AUDIT ---

Score Breakdown:
{json.dumps(review.get('scores', {}), indent=2)}

Factual Errors:
{errors_block}

Missing Information:
{missing_block}

Correction Guidance:
  {guidance or 'None'}

What the draft does well:
  {wins or 'N/A'}

{'=' * 50}
OPTIONS:
  APPROVE — send Ira's draft as-is to the customer
  REVISE  — Ira will fix the issues above and re-draft

Reply to this email with your decision.
"""

    mime_msg = MIMEText(body)
    mime_msg["to"] = RUSHABH_EMAIL
    mime_msg["from"] = IRA_EMAIL
    mime_msg["subject"] = subject

    raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()

    try:
        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        logger.info("Review email sent to %s: %s", RUSHABH_EMAIL, subject[:60])
        return True
    except Exception as exc:
        logger.error("Failed to send review email: %s", exc)
        return False


# ============================================================================
# LOGGING
# ============================================================================

def _log_result(result: Dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "email_id": result["email"].get("id"),
        "from": result["email"].get("from"),
        "subject": result["email"].get("subject"),
        "verdict": result["verdict"],
        "score": result["score"],
        "errors": result["errors"],
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ============================================================================
# SHADOW LOOP
# ============================================================================

def run_shadow_loop(count: int = 5) -> List[Dict]:
    """
    Fetch unread customer emails, shadow-test each one, send reviews
    to Rushabh, and log everything.

    Returns list of result dicts.
    """
    emails = get_unread_customer_emails(count=count)
    if not emails:
        logger.info("No emails to process.")
        return []

    results: List[Dict] = []
    for i, email in enumerate(emails, 1):
        logger.info(
            "[%d/%d] Shadow testing: %s",
            i, len(emails), email.get("subject", "No subject")[:60],
        )

        result = shadow_test_email(email)
        results.append(result)

        send_review_to_rushabh(email, result["draft"], result["review"])
        _log_result(result)

        logger.info(
            "  → %s (score: %.1f) | errors: %d",
            result["verdict"],
            result["score"],
            len(result["errors"]),
        )

    approved = sum(1 for r in results if r["verdict"] == "APPROVE")
    logger.info(
        "Shadow loop complete: %d/%d approved, avg score %.1f",
        approved,
        len(results),
        sum(r["score"] for r in results) / len(results) if results else 0,
    )

    return results


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Minerva Shadow Tester — audit Ira's drafts before sending",
    )
    parser.add_argument(
        "--count", type=int, default=5,
        help="Number of unread emails to process (default: 5)",
    )
    parser.add_argument(
        "--continuous", action="store_true",
        help="Run continuously, polling every 5 minutes",
    )
    args = parser.parse_args()

    if args.continuous:
        logger.info("Starting continuous shadow testing (Ctrl+C to stop)...")
        while True:
            try:
                run_shadow_loop(count=args.count)
                logger.info("Sleeping 5 minutes before next poll...")
                time.sleep(300)
            except KeyboardInterrupt:
                logger.info("Stopped by user.")
                break
            except Exception as exc:
                logger.error("Loop error: %s — retrying in 60s", exc)
                time.sleep(60)
    else:
        run_shadow_loop(count=args.count)


if __name__ == "__main__":
    main()
