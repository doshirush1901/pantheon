#!/usr/bin/env python3
"""
AUTONOMOUS DRIP ENGINE
======================

Ira's autonomous email outreach system. She sends drip emails from
ira@machinecraft.org on her own, tracks replies, scores herself,
and improves exponentially through dream-mode reflection.

This is the "grown-up Ira" module — she doesn't wait for Rushabh
to approve every email. She sends, tracks, learns, and adapts.

Architecture:
    1. Pick batch of leads ready for outreach (from european_drip_campaign)
    2. For each lead, generate personalized email using conversation history
    3. Send via Gmail API from ira@machinecraft.org
    4. Track what was sent in batch_history
    5. Monitor for replies (poll Gmail threads)
    6. Score herself: reply_rate, engagement_quality
    7. Feed low scores into dream reflection for overnight improvement

Usage:
    from autonomous_drip_engine import AutonomousDripEngine, get_engine

    engine = get_engine()
    result = engine.run_daily_batch()
    engine.check_replies()
    engine.self_evaluate()
"""

import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

logger = logging.getLogger("ira.autonomous_drip")

SKILL_DIR = Path(__file__).parent
SKILLS_DIR = SKILL_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(SKILLS_DIR / "crm"))
sys.path.insert(0, str(SKILLS_DIR / "brain"))
sys.path.insert(0, str(AGENT_DIR))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

# State files
BATCH_HISTORY_FILE = PROJECT_ROOT / "data" / "drip_batch_history.jsonl"
SELF_EVAL_FILE = PROJECT_ROOT / "data" / "drip_self_evaluation.json"
STRATEGY_FILE = PROJECT_ROOT / "data" / "drip_strategies.json"
DREAM_IDEAS_FILE = PROJECT_ROOT / "data" / "drip_dream_ideas.json"

IRA_EMAIL = os.getenv("IRA_EMAIL", "ira@machinecraft.org")
RUSHABH_EMAIL = os.getenv("RUSHABH_EMAIL", "rushabh@machinecraft.org")
MAX_EMAILS_PER_DAY = int(os.getenv("IRA_DRIP_MAX_PER_DAY", "8"))
MIN_HOURS_BETWEEN_SENDS = int(os.getenv("IRA_DRIP_MIN_HOURS", "2"))
REPLY_CHECK_DAYS = int(os.getenv("IRA_DRIP_REPLY_CHECK_DAYS", "14"))

try:
    from european_drip_campaign import get_campaign, EuropeanDripCampaign
    CAMPAIGN_AVAILABLE = True
except ImportError:
    CAMPAIGN_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class BatchStatus(Enum):
    SENT = "sent"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class SentEmail:
    lead_id: str
    company: str
    to_email: str
    subject: str
    stage: int
    sent_at: str
    thread_id: Optional[str] = None
    reply_received: bool = False
    reply_at: Optional[str] = None
    reply_quality: Optional[str] = None  # "engaged", "polite_decline", "auto_reply", "bounce"

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class BatchResult:
    batch_id: str
    sent_at: str
    emails_sent: int
    emails_failed: int
    leads: List[SentEmail]
    strategy_used: str = "default"
    status: str = "sent"

    # Filled in later by self-evaluation
    replies_received: int = 0
    reply_rate: float = 0.0
    self_score: float = 0.0
    reflection: str = ""

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["leads"] = [l.to_dict() if isinstance(l, SentEmail) else l for l in self.leads]
        return d


class AutonomousDripEngine:
    """
    Ira's autonomous drip marketing engine.

    She picks leads, writes emails, sends them, tracks replies,
    and scores herself. Low scores trigger dream-mode reflection
    where she generates new strategies for the next batch.
    """

    def __init__(self):
        self.campaign = get_campaign() if CAMPAIGN_AVAILABLE else None
        self.gmail = None
        self._init_gmail()
        self._init_crm()
        self.strategies = self._load_strategies()
        self.dream_ideas = self._load_dream_ideas()

    def _init_crm(self):
        """Initialize Ira's own CRM."""
        try:
            from ira_crm import get_crm
            self.crm = get_crm()
            logger.info(f"Ira CRM initialized ({self.crm.db_path})")
        except Exception as e:
            self.crm = None
            logger.warning(f"Ira CRM not available: {e}")

    def _init_gmail(self):
        """Initialize Gmail client for sending."""
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
            from email_openclaw_bridge import GmailClient, GMAIL_AVAILABLE
            if GMAIL_AVAILABLE:
                self.gmail = GmailClient()
                logger.info("Gmail client initialized for autonomous drip")
        except Exception as e:
            logger.warning(f"Gmail not available for autonomous drip: {e}")

    def _load_strategies(self) -> Dict[str, Any]:
        """Load current drip strategies (evolved through dream reflection)."""
        if STRATEGY_FILE.exists():
            try:
                return json.loads(STRATEGY_FILE.read_text())
            except Exception:
                pass
        return {
            "current_strategy": "default",
            "tone": "professional_warm",
            "personalization_level": "high",
            "subject_style": "curiosity_driven",
            "follow_up_aggressiveness": "moderate",
            "lessons_applied": [],
            "evolved_at": None,
        }

    def _save_strategies(self):
        STRATEGY_FILE.parent.mkdir(parents=True, exist_ok=True)
        STRATEGY_FILE.write_text(json.dumps(self.strategies, indent=2))

    def _load_dream_ideas(self) -> List[Dict]:
        """Load ideas generated during dream mode."""
        if DREAM_IDEAS_FILE.exists():
            try:
                return json.loads(DREAM_IDEAS_FILE.read_text())
            except Exception:
                pass
        return []

    def _load_batch_history(self) -> List[BatchResult]:
        """Load recent batch history for self-evaluation."""
        batches = []
        if BATCH_HISTORY_FILE.exists():
            try:
                for line in BATCH_HISTORY_FILE.read_text().strip().split("\n"):
                    if line.strip():
                        data = json.loads(line)
                        batches.append(data)
            except Exception:
                pass
        return batches

    def _append_batch(self, batch: BatchResult):
        BATCH_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(BATCH_HISTORY_FILE, "a") as f:
            f.write(json.dumps(batch.to_dict()) + "\n")

    def _get_lead_email(self, lead_id: str) -> Optional[str]:
        """Get email address for a lead from CRM or campaign data."""
        # Try CRM first (has the unified contact database)
        if self.crm and self.campaign:
            profile = self.campaign.get_lead_profile(lead_id)
            if profile:
                company = profile.get("company", "")
                if company:
                    results = self.crm.search_contacts(company, limit=1)
                    if results and "@placeholder" not in results[0].email:
                        return results[0].email

        # Fallback to campaign profile
        if not self.campaign:
            return None
        profile = self.campaign.get_lead_profile(lead_id)
        if not profile:
            return None
        email = profile.get("email") or profile.get("contact_email")
        if email:
            return email
        contacts = profile.get("key_contacts_to_find", [])
        if contacts and isinstance(contacts[0], dict):
            return contacts[0].get("email")
        return None

    def _apply_dream_ideas(self, email_body: str, lead_profile: Dict) -> str:
        """Apply ideas from last night's dream reflection to the email."""
        if not self.dream_ideas or not OPENAI_AVAILABLE:
            return email_body

        active_ideas = [
            idea for idea in self.dream_ideas
            if idea.get("status") == "active"
               and idea.get("expires_at", "9999") > datetime.now().isoformat()
        ]

        if not active_ideas:
            return email_body

        ideas_text = "\n".join(
            f"- {idea['idea']}" for idea in active_ideas[:5]
        )

        try:
            client = openai.OpenAI()
            result = client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": (
                        "You are Ira, Machinecraft's AI sales agent. "
                        "You had some ideas during your dream reflection last night about "
                        "how to make your emails more engaging and get more replies. "
                        "Apply these ideas to improve the email below. "
                        "Keep the core message but make it more compelling. "
                        "Don't add fake data or claims. Keep it authentic.\n\n"
                        f"IDEAS FROM LAST NIGHT'S REFLECTION:\n{ideas_text}"
                    )},
                    {"role": "user", "content": (
                        f"ORIGINAL EMAIL:\n{email_body}\n\n"
                        f"LEAD CONTEXT: {lead_profile.get('company', '')} in "
                        f"{lead_profile.get('country', '')} "
                        f"({', '.join(lead_profile.get('industries', [])[:2])})\n\n"
                        "Rewrite the email applying the dream ideas. "
                        "Output ONLY the rewritten email body."
                    )},
                ],
                temperature=0.6,
                max_tokens=1500,
            )
            improved = result.choices[0].message.content.strip()
            if improved and len(improved) > 50:
                return improved
        except Exception as e:
            logger.warning(f"Dream idea application failed: {e}")

        return email_body

    def run_daily_batch(self, max_emails: int = None, dry_run: bool = False) -> BatchResult:
        """
        Run the daily autonomous drip batch.

        1. Get leads ready for outreach
        2. Generate personalized emails (with dream ideas applied)
        3. Send from ira@machinecraft.org
        4. Record batch for tracking
        5. Notify Rushabh via Telegram
        """
        max_emails = max_emails or MAX_EMAILS_PER_DAY
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info("=" * 60)
        logger.info(f"AUTONOMOUS DRIP BATCH: {batch_id}")
        logger.info(f"Strategy: {self.strategies.get('current_strategy', 'default')}")
        logger.info(f"Dream ideas active: {len([i for i in self.dream_ideas if i.get('status') == 'active'])}")
        logger.info("=" * 60)

        if not self.campaign:
            logger.error("Campaign not available")
            return BatchResult(batch_id=batch_id, sent_at=datetime.now().isoformat(),
                               emails_sent=0, emails_failed=0, leads=[], status="failed")

        ready_leads = self.campaign.get_leads_ready_for_outreach()
        if not ready_leads:
            logger.info("No leads ready for outreach today")
            return BatchResult(batch_id=batch_id, sent_at=datetime.now().isoformat(),
                               emails_sent=0, emails_failed=0, leads=[], status="sent")

        logger.info(f"Found {len(ready_leads)} leads ready, will send up to {max_emails}")

        sent_emails = []
        failed_count = 0

        for lead_info in ready_leads[:max_emails]:
            lead_id = lead_info["lead_id"]
            company = lead_info["company"]
            next_stage = lead_info["next_stage"]

            to_email = self._get_lead_email(lead_id)
            if not to_email:
                logger.warning(f"No email found for {company} ({lead_id}), skipping")
                failed_count += 1
                continue

            # Generate email using existing campaign engine
            email = self.campaign.generate_email_luxury(lead_id, stage=next_stage)
            if not email:
                logger.warning(f"Failed to generate email for {company}")
                failed_count += 1
                continue

            # Apply dream ideas to improve the email
            profile = self.campaign.get_lead_profile(lead_id) or {}
            email["body"] = self._apply_dream_ideas(email["body"], profile)

            if dry_run:
                logger.info(f"  [DRY RUN] Would send to {company} ({to_email}): {email['subject']}")
                sent_emails.append(SentEmail(
                    lead_id=lead_id, company=company, to_email=to_email,
                    subject=email["subject"], stage=next_stage,
                    sent_at=datetime.now().isoformat(),
                ))
                continue

            # Actually send the email
            thread_id = None
            if self.gmail:
                try:
                    thread_id = self.gmail.send_new_email(
                        to=to_email,
                        subject=email["subject"],
                        body=email["body"],
                    )
                    if thread_id:
                        logger.info(f"  SENT to {company} ({to_email}) - thread: {thread_id}")
                        self.campaign.record_email_sent(lead_id, stage=next_stage)
                        # Log in Ira's CRM
                        if self.crm:
                            self.crm.log_email_sent(
                                to_email, subject=email["subject"],
                                thread_id=thread_id, drip_stage=next_stage,
                                batch_id=batch_id, body_preview=email["body"][:300],
                            )
                    else:
                        logger.warning(f"  FAILED to send to {company}")
                        failed_count += 1
                        continue
                except Exception as e:
                    logger.error(f"  Send error for {company}: {e}")
                    failed_count += 1
                    continue
            else:
                logger.warning(f"  Gmail not available, cannot send to {company}")
                failed_count += 1
                continue

            sent_emails.append(SentEmail(
                lead_id=lead_id, company=company, to_email=to_email,
                subject=email["subject"], stage=next_stage,
                sent_at=datetime.now().isoformat(), thread_id=thread_id,
            ))

            # Pace sends to avoid spam triggers
            if len(sent_emails) < max_emails:
                time.sleep(30)

        batch = BatchResult(
            batch_id=batch_id,
            sent_at=datetime.now().isoformat(),
            emails_sent=len(sent_emails),
            emails_failed=failed_count,
            leads=sent_emails,
            strategy_used=self.strategies.get("current_strategy", "default"),
            status="sent" if sent_emails else ("partial" if failed_count else "sent"),
        )

        if not dry_run:
            self._append_batch(batch)
            self._notify_rushabh_batch_sent(batch)

        logger.info(f"\nBatch complete: {len(sent_emails)} sent, {failed_count} failed")
        return batch

    def check_replies(self) -> Dict[str, Any]:
        """
        Check for replies to previously sent drip emails.

        Scans batch history for emails sent in the last REPLY_CHECK_DAYS,
        checks Gmail threads for replies, and updates batch records.
        """
        if not self.gmail:
            return {"error": "Gmail not available"}

        logger.info("Checking for replies to drip emails...")

        batches = self._load_batch_history()
        cutoff = (datetime.now() - timedelta(days=REPLY_CHECK_DAYS)).isoformat()

        total_checked = 0
        new_replies = 0
        updated_batches = []

        for batch_data in batches:
            if batch_data.get("sent_at", "") < cutoff:
                updated_batches.append(batch_data)
                continue

            batch_modified = False
            for lead in batch_data.get("leads", []):
                if lead.get("reply_received"):
                    continue

                thread_id = lead.get("thread_id")
                if not thread_id:
                    continue

                total_checked += 1

                try:
                    thread_history = self.gmail.get_thread_history(thread_id)
                    # Look for messages NOT from Ira (i.e., replies)
                    replies = [
                        msg for msg in thread_history
                        if msg.get("role") == "user"
                           and IRA_EMAIL.lower() not in msg.get("from", "").lower()
                    ]
                    if replies:
                        lead["reply_received"] = True
                        lead["reply_at"] = replies[-1].get("date", datetime.now().isoformat())
                        lead["reply_quality"] = self._classify_reply(replies[-1].get("body", ""))
                        new_replies += 1
                        batch_modified = True
                        logger.info(f"  Reply from {lead['company']}! Quality: {lead['reply_quality']}")
                        # Record in CRM
                        if self.crm:
                            to_email = lead.get("to_email", "")
                            if to_email:
                                self.crm.record_reply(
                                    to_email, thread_id=thread_id,
                                    quality=lead["reply_quality"],
                                    subject=replies[-1].get("subject", ""),
                                    preview=replies[-1].get("body", "")[:300],
                                )
                except Exception as e:
                    logger.debug(f"  Thread check error for {lead.get('company')}: {e}")

            if batch_modified:
                replied = sum(1 for l in batch_data.get("leads", []) if l.get("reply_received"))
                total = len(batch_data.get("leads", []))
                batch_data["replies_received"] = replied
                batch_data["reply_rate"] = replied / total if total > 0 else 0.0

            updated_batches.append(batch_data)

        # Rewrite batch history with updated reply data
        if new_replies > 0:
            BATCH_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(BATCH_HISTORY_FILE, "w") as f:
                for batch_data in updated_batches:
                    f.write(json.dumps(batch_data) + "\n")

        result = {
            "threads_checked": total_checked,
            "new_replies": new_replies,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"Reply check: {total_checked} threads checked, {new_replies} new replies")
        return result

    def _classify_reply(self, reply_body: str) -> str:
        """Classify the quality of a reply."""
        if not reply_body:
            return "unknown"

        body_lower = reply_body.lower()

        if any(w in body_lower for w in ["out of office", "auto-reply", "automatic reply", "away from"]):
            return "auto_reply"
        if any(w in body_lower for w in ["undeliverable", "bounce", "failed delivery", "not found"]):
            return "bounce"
        if any(w in body_lower for w in ["unsubscribe", "remove me", "stop emailing", "not interested"]):
            return "polite_decline"
        if any(w in body_lower for w in [
            "interested", "tell me more", "send me", "quote", "pricing",
            "call", "meeting", "schedule", "discuss", "specifications",
            "brochure", "catalog", "when can", "how much", "what is"
        ]):
            return "engaged"
        if len(reply_body.strip()) > 50:
            return "engaged"

        return "polite_decline"

    def self_evaluate(self) -> Dict[str, Any]:
        """
        Ira evaluates her own drip performance.

        Calculates reply rates, identifies what's working and what isn't,
        and generates a self-assessment that feeds into dream reflection.
        """
        batches = self._load_batch_history()
        if not batches:
            return {"status": "no_data", "message": "No batches sent yet"}

        recent_batches = [
            b for b in batches
            if b.get("sent_at", "") > (datetime.now() - timedelta(days=30)).isoformat()
        ]

        if not recent_batches:
            return {"status": "no_recent_data", "message": "No batches in last 30 days"}

        total_sent = sum(b.get("emails_sent", 0) for b in recent_batches)
        total_replies = sum(b.get("replies_received", 0) for b in recent_batches)
        reply_rate = total_replies / total_sent if total_sent > 0 else 0.0

        engaged_replies = 0
        auto_replies = 0
        bounces = 0
        declines = 0

        for batch in recent_batches:
            for lead in batch.get("leads", []):
                quality = lead.get("reply_quality", "")
                if quality == "engaged":
                    engaged_replies += 1
                elif quality == "auto_reply":
                    auto_replies += 1
                elif quality == "bounce":
                    bounces += 1
                elif quality == "polite_decline":
                    declines += 1

        engagement_rate = engaged_replies / total_sent if total_sent > 0 else 0.0

        # Score herself 0-100
        score = min(100, int(
            (reply_rate * 40) +           # 40% weight on reply rate
            (engagement_rate * 40) +      # 40% weight on engagement quality
            (min(total_sent, 50) / 50 * 20)  # 20% weight on volume (up to 50)
        ))

        # Identify companies that replied vs didn't
        replied_companies = []
        silent_companies = []
        for batch in recent_batches:
            for lead in batch.get("leads", []):
                if lead.get("reply_received") and lead.get("reply_quality") == "engaged":
                    replied_companies.append(lead.get("company", ""))
                elif not lead.get("reply_received"):
                    silent_companies.append(lead.get("company", ""))

        # Generate self-reflection questions
        reflection_questions = []
        if reply_rate < 0.05:
            reflection_questions.extend([
                "Why is nobody replying to me? Are my subject lines boring?",
                "Am I sending at the wrong time of day?",
                "Are my emails too long or too generic?",
                "Do I sound like a robot? How can I sound more human?",
                "Should I try a completely different approach?",
            ])
        elif reply_rate < 0.15:
            reflection_questions.extend([
                "Some people are replying but most aren't. What's different about the ones who reply?",
                "Are my follow-ups too aggressive or not aggressive enough?",
                "Should I try more technical content or more business-value content?",
                "How can I make my subject lines more compelling?",
            ])
        elif reply_rate < 0.30:
            reflection_questions.extend([
                "Good progress but room to improve. What patterns do I see in successful emails?",
                "Can I personalize even more based on their specific industry?",
                "Should I reference more specific news or events?",
            ])
        else:
            reflection_questions.extend([
                "Great reply rate! What am I doing right that I should double down on?",
                "How can I convert these replies into meetings and quotes?",
            ])

        if bounces > 0:
            reflection_questions.append(
                f"I got {bounces} bounces. I need to verify email addresses before sending."
            )

        evaluation = {
            "timestamp": datetime.now().isoformat(),
            "period_days": 30,
            "total_sent": total_sent,
            "total_replies": total_replies,
            "reply_rate": round(reply_rate, 4),
            "engagement_rate": round(engagement_rate, 4),
            "engaged_replies": engaged_replies,
            "auto_replies": auto_replies,
            "bounces": bounces,
            "declines": declines,
            "self_score": score,
            "replied_companies": list(set(replied_companies)),
            "silent_companies": list(set(silent_companies))[:20],
            "reflection_questions": reflection_questions,
            "strategy_used": self.strategies.get("current_strategy", "default"),
            "batches_analyzed": len(recent_batches),
        }

        # Save evaluation
        SELF_EVAL_FILE.parent.mkdir(parents=True, exist_ok=True)
        SELF_EVAL_FILE.write_text(json.dumps(evaluation, indent=2))

        logger.info(f"\nSelf-evaluation: score={score}/100, reply_rate={reply_rate:.1%}")
        logger.info(f"  Engaged: {engaged_replies}, Declines: {declines}, Bounces: {bounces}")

        return evaluation

    def _notify_rushabh_batch_sent(self, batch: BatchResult):
        """Send Telegram notification to Rushabh about the batch."""
        try:
            import requests
            token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            chat_id = os.environ.get("EXPECTED_CHAT_ID", "5700751574")

            if not token:
                return

            companies = ", ".join(e.company for e in batch.leads[:5])
            if len(batch.leads) > 5:
                companies += f" (+{len(batch.leads) - 5} more)"

            strategy = self.strategies.get("current_strategy", "default")
            dream_count = len([i for i in self.dream_ideas if i.get("status") == "active"])

            msg = (
                f"Drip Batch Sent\n"
                f"---\n"
                f"Sent: {batch.emails_sent} | Failed: {batch.emails_failed}\n"
                f"Strategy: {strategy}\n"
            )
            if dream_count > 0:
                msg += f"Dream ideas applied: {dream_count}\n"
            msg += f"Companies: {companies}\n"
            msg += f"\nI'll check for replies and report back."

            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg},
                timeout=10,
            )
        except Exception as e:
            logger.debug(f"Telegram notification failed: {e}")

    def get_performance_summary(self) -> str:
        """Get a human-readable performance summary for Telegram/email."""
        eval_data = {}
        if SELF_EVAL_FILE.exists():
            try:
                eval_data = json.loads(SELF_EVAL_FILE.read_text())
            except Exception:
                pass

        if not eval_data:
            return "No drip performance data yet. I haven't sent any batches."

        score = eval_data.get("self_score", 0)
        reply_rate = eval_data.get("reply_rate", 0)
        total_sent = eval_data.get("total_sent", 0)
        engaged = eval_data.get("engaged_replies", 0)

        lines = [
            f"Drip Performance (last 30 days)",
            f"---",
            f"Score: {score}/100",
            f"Emails sent: {total_sent}",
            f"Reply rate: {reply_rate:.1%}",
            f"Engaged replies: {engaged}",
        ]

        replied = eval_data.get("replied_companies", [])
        if replied:
            lines.append(f"Engaged: {', '.join(replied[:5])}")

        questions = eval_data.get("reflection_questions", [])
        if questions:
            lines.append(f"\nMy thoughts:")
            for q in questions[:3]:
                lines.append(f"  - {q}")

        return "\n".join(lines)


_engine: Optional[AutonomousDripEngine] = None


def get_engine() -> AutonomousDripEngine:
    global _engine
    if _engine is None:
        _engine = AutonomousDripEngine()
    return _engine


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Ira Autonomous Drip Engine")
    parser.add_argument("--send", action="store_true", help="Run daily batch (sends real emails)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no actual sends)")
    parser.add_argument("--check-replies", action="store_true", help="Check for replies")
    parser.add_argument("--evaluate", action="store_true", help="Run self-evaluation")
    parser.add_argument("--summary", action="store_true", help="Print performance summary")
    parser.add_argument("--max", type=int, default=MAX_EMAILS_PER_DAY, help="Max emails to send")
    args = parser.parse_args()

    engine = get_engine()

    if args.send:
        result = engine.run_daily_batch(max_emails=args.max)
        print(json.dumps(result.to_dict(), indent=2))
    elif args.dry_run:
        result = engine.run_daily_batch(max_emails=args.max, dry_run=True)
        print(json.dumps(result.to_dict(), indent=2))
    elif args.check_replies:
        result = engine.check_replies()
        print(json.dumps(result, indent=2))
    elif args.evaluate:
        result = engine.self_evaluate()
        print(json.dumps(result, indent=2))
    elif args.summary:
        print(engine.get_performance_summary())
    else:
        parser.print_help()
