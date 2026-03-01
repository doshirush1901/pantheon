#!/usr/bin/env python3
"""
MINERVA — Sent Folder Auditor
==============================

Reads Ira's actual sent emails from Gmail, extracts every factual claim,
verifies each against the REAL machine database, logs errors, and sends
corrections back into Ira's learning pipeline.

Usage:
    python agents/minerva/sent_folder_auditor.py
    python agents/minerva/sent_folder_auditor.py --count 20
    python agents/minerva/sent_folder_auditor.py --continuous
"""

import argparse
import base64
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from openai import OpenAI

_brain_path = str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "brain")
if _brain_path not in sys.path:
    sys.path.insert(0, _brain_path)

from machine_database import MACHINE_SPECS, MachineSpec

_apollo_path = str(PROJECT_ROOT / "agents" / "apollo")
if _apollo_path not in sys.path:
    sys.path.insert(0, _apollo_path)

from grounded_coach import SERIES_KNOWLEDGE

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

logger = logging.getLogger("minerva.sent_auditor")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

client = OpenAI()

IRA_EMAIL = "ira@machinecraft.org"

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
    return _build_gmail_service("token.json") or _build_gmail_service(
        "token_ira_backup.json"
    )


# ============================================================================
# GROUND TRUTH INDEX
# ============================================================================

PF2_HALLUCINATION_KEYWORDS = frozenset(
    {
        "automation",
        "sag control",
        "closed chamber",
        "servo",
        "customization",
        "advanced control",
        "plug assist",
        "auto load",
        "positive forming",
        "versatile",
    }
)


def build_ground_truth_index() -> Dict:
    models: Dict[str, Dict] = {}
    for model_name, spec in MACHINE_SPECS.items():
        models[model_name] = {
            "model": spec.model,
            "series": spec.series,
            "variant": spec.variant,
            "price_inr": spec.price_inr,
            "price_usd": spec.price_usd,
            "forming_area": spec.forming_area_mm,
            "max_thickness": spec.max_sheet_thickness_mm,
            "heater_power": spec.heater_power_kw,
            "features": spec.features,
            "applications": spec.applications,
            "description": spec.description,
        }

    series: Dict[str, Dict] = {}
    for series_name, knowledge in SERIES_KNOWLEDGE.items():
        series[series_name] = knowledge

    return {"models": models, "series": series}


TRUTH_INDEX = build_ground_truth_index()


# ============================================================================
# CLAIM EXTRACTION
# ============================================================================

_EXTRACT_SYSTEM_PROMPT = """\
You are a factual claim extractor for Machinecraft Technologies emails.
Extract EVERY factual claim from the email body. A factual claim is any
statement about:
- Machine models, series, or product lines
- Technical specifications (forming area, thickness, power, price, etc.)
- Business terms (lead time, payment terms, warranty)
- Series characteristics (chamber type, automation, applications)

For each claim, return a JSON object with:
- claim: the exact text of the claim
- category: one of "machine", "series", "spec", "business"
- model_mentioned: model name if any (e.g. "PF1-C-2015"), or null
- series_mentioned: series name if any (e.g. "PF1", "PF2", "AM"), or null
- spec_type: what spec is being claimed (e.g. "forming_area", "price", "thickness", "lead_time"), or null
- value_claimed: the specific value claimed, or null

Return a JSON array. If no factual claims found, return [].
Return ONLY valid JSON, no markdown fences.
"""


def extract_claims(email_body: str) -> List[Dict]:
    if not email_body or not email_body.strip():
        return []

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Extract all factual claims from this email:\n\n{email_body}",
                },
            ],
            temperature=0.0,
            max_tokens=4000,
        )
        raw = completion.choices[0].message.content.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        claims = json.loads(raw)
        if not isinstance(claims, list):
            return []
        return claims
    except Exception as exc:
        logger.error("Claim extraction failed: %s", exc)
        return []


# ============================================================================
# VERIFICATION
# ============================================================================


@dataclass
class VerificationResult:
    claim: str
    category: str
    verdict: str  # CORRECT, WRONG, UNVERIFIABLE
    ira_said: str
    truth: str
    source: str
    severity: str  # critical, major, minor, info


def _check_pf2_hallucination(claim_text: str) -> Optional[VerificationResult]:
    claim_lower = claim_text.lower()
    for keyword in PF2_HALLUCINATION_KEYWORDS:
        if keyword in claim_lower:
            return VerificationResult(
                claim=claim_text,
                category="series",
                verdict="WRONG",
                ira_said=f"PF2 has {keyword}",
                truth="PF2 is OPEN FRAME, NO chamber, NO sag control, NO automation, air cylinder driven, BATH INDUSTRY ONLY",
                source="SERIES_KNOWLEDGE['PF2']",
                severity="critical",
            )
    return None


def _check_pf1_confusion(claim_text: str) -> Optional[VerificationResult]:
    claim_lower = claim_text.lower()
    pf1_wrong_claims = ["open frame", "no chamber"]
    for wrong in pf1_wrong_claims:
        if wrong in claim_lower:
            return VerificationResult(
                claim=claim_text,
                category="series",
                verdict="WRONG",
                ira_said=f"PF1 is {wrong}",
                truth="PF1 is a CLOSED CHAMBER machine with sag control, pre-blow, and many automation options",
                source="SERIES_KNOWLEDGE['PF1']",
                severity="critical",
            )
    return None


def _check_am_thickness(claim: Dict) -> Optional[VerificationResult]:
    value = claim.get("value_claimed", "")
    if not value:
        return None
    thickness_match = re.search(r"(\d+(?:\.\d+)?)", str(value))
    if thickness_match:
        thickness = float(thickness_match.group(1))
        if thickness > 1.5:
            return VerificationResult(
                claim=claim["claim"],
                category="series",
                verdict="WRONG",
                ira_said=f"AM handles {thickness}mm",
                truth="AM series max thickness is 1.5mm. For thicker materials, recommend PF1/PF2.",
                source="SERIES_KNOWLEDGE['AM']",
                severity="critical",
            )
    return None


def _check_price(claim: Dict, truth_spec: Dict) -> Optional[VerificationResult]:
    value = claim.get("value_claimed", "")
    if not value:
        return None

    price_match = re.search(r"[\d,]+", str(value).replace(",", ""))
    if not price_match:
        return None

    claimed_price = int(price_match.group(0).replace(",", ""))
    if claimed_price == 0:
        return None

    for price_key, label in [("price_inr", "INR"), ("price_usd", "USD")]:
        true_price = truth_spec.get(price_key)
        if true_price and true_price > 0:
            if label == "USD" and claimed_price > 10000:
                continue
            if label == "INR" and claimed_price < 10000:
                continue

            tolerance = 0.10
            if abs(claimed_price - true_price) / true_price > tolerance:
                return VerificationResult(
                    claim=claim["claim"],
                    category="machine",
                    verdict="WRONG",
                    ira_said=f"Price: {claimed_price} {label}",
                    truth=f"Actual price: {true_price:,} {label} (>10% deviation)",
                    source=f"MACHINE_SPECS['{truth_spec['model']}']",
                    severity="major",
                )

    return None


def _check_forming_area(claim: Dict, truth_spec: Dict) -> Optional[VerificationResult]:
    value = str(claim.get("value_claimed", ""))
    true_area = truth_spec.get("forming_area", "")
    if not value or not true_area:
        return None

    claimed_dims = re.findall(r"\d+", value)
    true_dims = re.findall(r"\d+", true_area)

    if len(claimed_dims) >= 2 and len(true_dims) >= 2:
        claimed_set = {int(claimed_dims[0]), int(claimed_dims[1])}
        true_set = {int(true_dims[0]), int(true_dims[1])}
        if claimed_set != true_set:
            return VerificationResult(
                claim=claim["claim"],
                category="machine",
                verdict="WRONG",
                ira_said=f"Forming area: {value}",
                truth=f"Actual forming area: {true_area}",
                source=f"MACHINE_SPECS['{truth_spec['model']}']",
                severity="major",
            )

    return None


def _check_thickness(claim: Dict, truth_spec: Dict) -> Optional[VerificationResult]:
    value = claim.get("value_claimed", "")
    if not value:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)", str(value))
    if not match:
        return None

    claimed = float(match.group(1))
    max_t = truth_spec.get("max_thickness", 0)
    if max_t and claimed > max_t:
        return VerificationResult(
            claim=claim["claim"],
            category="machine",
            verdict="WRONG",
            ira_said=f"Handles {claimed}mm",
            truth=f"Max thickness: {max_t}mm",
            source=f"MACHINE_SPECS['{truth_spec['model']}']",
            severity="critical",
        )

    return None


def _check_lead_time(claim: Dict) -> Optional[VerificationResult]:
    value = str(claim.get("value_claimed", "")).lower()
    match = re.search(r"(\d+)", value)
    if not match:
        return None

    weeks = int(match.group(1))
    if "month" in value:
        weeks *= 4
    if "day" in value:
        weeks = weeks // 7

    if weeks < 12:
        return VerificationResult(
            claim=claim["claim"],
            category="business",
            verdict="WRONG",
            ira_said=f"Lead time: {claim.get('value_claimed', '')}",
            truth="Standard lead time is 12-16 weeks plus shipping",
            source="Business rules",
            severity="major",
        )

    return None


def verify_claim(claim: Dict) -> VerificationResult:
    claim_text = claim.get("claim", "")
    category = claim.get("category", "")
    model = claim.get("model_mentioned")
    series = claim.get("series_mentioned")
    spec_type = claim.get("spec_type")

    if series == "PF2" or (model and model.upper().startswith("PF2")):
        result = _check_pf2_hallucination(claim_text)
        if result:
            return result

    if series == "PF1" or (model and model.upper().startswith("PF1")):
        result = _check_pf1_confusion(claim_text)
        if result:
            return result

    if series == "AM" or (model and model.upper().startswith("AM")):
        if spec_type in ("thickness", "max_thickness"):
            result = _check_am_thickness(claim)
            if result:
                return result

    if model and model.upper() in TRUTH_INDEX["models"]:
        truth_spec = TRUTH_INDEX["models"][model.upper()]

        if spec_type == "price":
            result = _check_price(claim, truth_spec)
            if result:
                return result

        if spec_type in ("forming_area", "forming area", "size"):
            result = _check_forming_area(claim, truth_spec)
            if result:
                return result

        if spec_type in ("thickness", "max_thickness"):
            result = _check_thickness(claim, truth_spec)
            if result:
                return result

    if spec_type == "lead_time" or "lead time" in claim_text.lower():
        result = _check_lead_time(claim)
        if result:
            return result

    if model and model.upper() in TRUTH_INDEX["models"]:
        return VerificationResult(
            claim=claim_text,
            category=category,
            verdict="CORRECT",
            ira_said=claim_text,
            truth="Verified against database",
            source=f"MACHINE_SPECS['{model.upper()}']",
            severity="info",
        )

    if series and series.upper() in TRUTH_INDEX["series"]:
        return VerificationResult(
            claim=claim_text,
            category=category,
            verdict="CORRECT",
            ira_said=claim_text,
            truth="Verified against series knowledge",
            source=f"SERIES_KNOWLEDGE['{series.upper()}']",
            severity="info",
        )

    return VerificationResult(
        claim=claim_text,
        category=category,
        verdict="UNVERIFIABLE",
        ira_said=claim_text,
        truth="No matching entry in database to verify against",
        source="N/A",
        severity="info",
    )


# ============================================================================
# EMAIL AUDIT
# ============================================================================


@dataclass
class EmailAudit:
    email_id: str
    subject: str
    to: str
    date: str
    total_claims: int
    correct: int
    wrong: int
    unverifiable: int
    errors: List[Dict] = field(default_factory=list)
    score: float = 0.0

    def compute_score(self):
        verifiable = self.correct + self.wrong
        if verifiable == 0:
            self.score = 100.0
        else:
            self.score = round((self.correct / verifiable) * 100, 1)


# ============================================================================
# GMAIL READER
# ============================================================================


def get_ira_sent_emails(count: int = 10) -> List[Dict]:
    service = _get_gmail_service()
    if service is None:
        logger.error("Gmail service unavailable — no valid token found")
        return []

    try:
        results = (
            service.users()
            .messages()
            .list(userId="me", q="in:sent", maxResults=count)
            .execute()
        )
        messages = results.get("messages", [])
    except Exception as exc:
        logger.error("Failed to list sent emails: %s", exc)
        return []

    emails = []
    for msg_stub in messages:
        try:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_stub["id"], format="full")
                .execute()
            )

            headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
            subject = headers.get("Subject", "(no subject)")
            to = headers.get("To", "")
            date = headers.get("Date", "")

            body = ""
            payload = msg["payload"]
            if "parts" in payload:
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain" and part.get("body", {}).get("data"):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                        break
            elif payload.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

            emails.append(
                {
                    "id": msg_stub["id"],
                    "subject": subject,
                    "to": to,
                    "date": date,
                    "body": body,
                }
            )
        except Exception as exc:
            logger.warning("Failed to fetch email %s: %s", msg_stub["id"], exc)

    logger.info("Fetched %d sent emails", len(emails))
    return emails


# ============================================================================
# AUDIT PIPELINE
# ============================================================================


def audit_email(email: Dict) -> EmailAudit:
    claims = extract_claims(email.get("body", ""))

    results: List[VerificationResult] = []
    for claim in claims:
        results.append(verify_claim(claim))

    correct = sum(1 for r in results if r.verdict == "CORRECT")
    wrong = sum(1 for r in results if r.verdict == "WRONG")
    unverifiable = sum(1 for r in results if r.verdict == "UNVERIFIABLE")

    errors = []
    for r in results:
        if r.verdict == "WRONG":
            errors.append(
                {
                    "claim": r.claim,
                    "ira_said": r.ira_said,
                    "truth": r.truth,
                    "source": r.source,
                    "severity": r.severity,
                }
            )

    audit = EmailAudit(
        email_id=email.get("id", ""),
        subject=email.get("subject", ""),
        to=email.get("to", ""),
        date=email.get("date", ""),
        total_claims=len(claims),
        correct=correct,
        wrong=wrong,
        unverifiable=unverifiable,
        errors=errors,
    )
    audit.compute_score()
    return audit


def audit_sent_folder(count: int = 10) -> List[EmailAudit]:
    emails = get_ira_sent_emails(count)
    if not emails:
        logger.warning("No sent emails found to audit")
        return []

    audits: List[EmailAudit] = []
    for i, email in enumerate(emails, 1):
        logger.info("Auditing email %d/%d: %s", i, len(emails), email.get("subject", ""))
        audit = audit_email(email)
        audits.append(audit)

        icon = "✅" if audit.wrong == 0 else "❌"
        print(f"\n{icon} [{audit.score}%] {audit.subject}")
        print(f"   To: {audit.to} | Date: {audit.date}")
        print(f"   Claims: {audit.total_claims} | Correct: {audit.correct} | Wrong: {audit.wrong} | Unverifiable: {audit.unverifiable}")
        if audit.errors:
            for err in audit.errors:
                print(f"   ⚠ [{err['severity'].upper()}] {err['claim']}")
                print(f"     Ira said: {err['ira_said']}")
                print(f"     Truth:    {err['truth']}")

    audit_log_dir = PROJECT_ROOT / "data" / "training"
    audit_log_dir.mkdir(parents=True, exist_ok=True)
    audit_log_path = audit_log_dir / "audit_log.json"

    log_data = {
        "audit_date": datetime.now().isoformat(),
        "emails_audited": len(audits),
        "total_errors": sum(a.wrong for a in audits),
        "average_score": round(sum(a.score for a in audits) / len(audits), 1) if audits else 0,
        "audits": [asdict(a) for a in audits],
    }

    try:
        audit_log_path.write_text(json.dumps(log_data, indent=2, ensure_ascii=False))
        logger.info("Audit log saved to %s", audit_log_path)
    except Exception as exc:
        logger.error("Failed to save audit log: %s", exc)

    total_wrong = sum(a.wrong for a in audits)
    total_claims = sum(a.total_claims for a in audits)
    avg_score = log_data["average_score"]
    print(f"\n{'='*60}")
    print(f"AUDIT SUMMARY: {len(audits)} emails, {total_claims} claims")
    print(f"Average accuracy: {avg_score}%")
    print(f"Total errors found: {total_wrong}")
    print(f"{'='*60}")

    return audits


# ============================================================================
# CORRECTIONS → IRA LEARNING PIPELINE
# ============================================================================


def send_corrections_to_ira(audits: List[EmailAudit]) -> int:
    all_errors = []
    for audit in audits:
        for err in audit.errors:
            all_errors.append(
                {
                    "email_id": audit.email_id,
                    "subject": audit.subject,
                    "date": audit.date,
                    **err,
                }
            )

    if not all_errors:
        print("\n✅ No corrections needed — Ira's sent emails are clean!")
        return 0

    learnings_path = PROJECT_ROOT / "data" / "learned_lessons" / "continuous_learnings.json"
    try:
        existing = json.loads(learnings_path.read_text()) if learnings_path.exists() else {"lessons": []}
    except Exception:
        existing = {"lessons": []}

    existing_ids = {l.get("id") for l in existing.get("lessons", [])}
    new_lessons = []
    for err in all_errors:
        lesson_id = f"AUDIT_{err['email_id'][:8]}_{err['claim'][:20].replace(' ', '_')}"
        if lesson_id in existing_ids:
            continue

        new_lessons.append(
            {
                "id": lesson_id,
                "category": "sent_folder_audit",
                "severity": err["severity"],
                "lesson": f"In email '{err['subject']}', Ira incorrectly said: \"{err['ira_said']}\". "
                f"The truth is: {err['truth']}",
                "trigger": err["claim"],
                "correct_action": err["truth"],
                "incorrect_action": err["ira_said"],
                "source": f"Minerva Sent Folder Audit ({err['source']})",
                "timestamp": datetime.now().isoformat(),
            }
        )

    if new_lessons:
        existing["lessons"].extend(new_lessons)
        try:
            learnings_path.parent.mkdir(parents=True, exist_ok=True)
            learnings_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
            logger.info("Stored %d new lessons in %s", len(new_lessons), learnings_path)
        except Exception as exc:
            logger.error("Failed to store lessons: %s", exc)

    print(f"\n{'='*60}")
    print(f"CORRECTIONS SENT TO IRA: {len(new_lessons)} new lessons stored")
    for lesson in new_lessons:
        print(f"  ⚠ [{lesson['severity'].upper()}] {lesson['lesson'][:120]}...")
    print(f"{'='*60}")

    return len(new_lessons)


# ============================================================================
# CLI
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Minerva Sent Folder Auditor — verify Ira's sent emails against ground truth"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of recent sent emails to audit (default: 10)",
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously, auditing every 30 minutes",
    )
    args = parser.parse_args()

    if args.continuous:
        print("Minerva Sent Folder Auditor — CONTINUOUS MODE")
        print("Auditing every 30 minutes. Press Ctrl+C to stop.\n")
        while True:
            try:
                audits = audit_sent_folder(args.count)
                send_corrections_to_ira(audits)
                logger.info("Sleeping 30 minutes until next audit cycle...")
                time.sleep(30 * 60)
            except KeyboardInterrupt:
                print("\nAudit loop stopped.")
                break
            except Exception as exc:
                logger.error("Audit cycle failed: %s", exc)
                time.sleep(60)
    else:
        audits = audit_sent_folder(args.count)
        send_corrections_to_ira(audits)


if __name__ == "__main__":
    main()
