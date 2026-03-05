"""
CHIRON — The Sales Trainer
===========================

Named after the wisest centaur in Greek mythology who trained Achilles, Heracles,
and Jason — the greatest heroes. Chiron trains Hermes (outreach) and Athena (orchestrator)
on how to sell. He's the first male trainer in the pantheon.

Chiron's job:
    1. OBSERVE — Watches sales interactions (emails sent, replies received, deals won/lost)
    2. LOG — Records every sales pattern, technique, and lesson into the training log
    3. TEACH — Injects learned strategies into Hermes' system prompt and Athena's context
    4. COACH — When drafting emails, provides real-time coaching notes based on the situation

Personality:
    - Experienced, calm, methodical. Thinks in patterns and frameworks.
    - Speaks like a seasoned sales coach: "This is a stale deal — don't just check in.
      Find a news hook, create urgency, give them a reason to act today."
    - Never generic. Every piece of advice is grounded in a real example from the log.
    - Protective of Machinecraft's brand — no desperate or pushy tactics.

Data:
    - sales_training.md — The master log of all learned patterns (ST-001, ST-002, ...)
    - Nemesis correction store — Sales-category corrections
    - Email thread history — What worked, what didn't

Usage:
    from openclaw.agents.ira.src.agents.chiron import get_chiron, get_coaching_notes

    chiron = get_chiron()
    chiron.log_pattern(title=..., trigger=..., ...)
    notes = chiron.get_coaching_notes(situation="stale deal, no reply 7 days, customer in Germany")
    guidance = get_sales_guidance_for_prompt()
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.chiron")

AGENT_DIR = Path(__file__).resolve().parent
DATA_DIR = AGENT_DIR.parent.parent.parent / "data"
TRAINING_LOG = DATA_DIR / "sales_training.md"
ANALYZED_THREADS_FILE = DATA_DIR / "cache" / "chiron_analyzed_threads.json"

_chiron_instance = None


class Chiron:
    """The Sales Trainer — observes, logs, and teaches sales patterns."""

    def __init__(self):
        self._ensure_log_exists()

    def _ensure_log_exists(self):
        if not TRAINING_LOG.exists():
            TRAINING_LOG.parent.mkdir(parents=True, exist_ok=True)
            TRAINING_LOG.write_text(
                "# Ira Sales Training Log\n\n"
                "Patterns learned from Rushabh or observed during real sales interactions.\n"
                "Chiron reads this at runtime and teaches Hermes and Athena.\n\n---\n"
            )

    def _next_entry_number(self) -> int:
        try:
            content = TRAINING_LOG.read_text()
            nums = [int(m.group(1)) for m in re.finditer(r"## ST-(\d+)", content)]
            return max(nums, default=0) + 1
        except Exception:
            return 1

    def log_pattern(
        self,
        title: str,
        trigger: str,
        wrong_approach: str,
        right_approach: str,
        example: str = "",
        tool_chain: str = "",
        when_to_apply: str = "",
        source: str = "rushabh_teaching",
        severity: str = "Important",
    ) -> str:
        """Log a new sales pattern to the training log.

        Returns confirmation string with the entry ID.
        """
        num = self._next_entry_number()

        entry = f"""
## ST-{num:03d} | {title}
**Learned:** {datetime.now().strftime('%Y-%m-%d')} | **Source:** {source} | **Severity:** {severity}

**Trigger:** {trigger}

**Wrong approach:** {wrong_approach}

**Right approach:**
{right_approach}
"""
        if example:
            entry += f"\n**Real example:**\n{example}\n"
        if tool_chain:
            entry += f"\n**Tool chain:** {tool_chain}\n"
        if when_to_apply:
            entry += f"\n**When to apply:** {when_to_apply}\n"
        entry += "\n---\n"

        try:
            with open(TRAINING_LOG, "a") as f:
                f.write(entry)
            logger.info("[Chiron] Logged ST-%03d: %s (source: %s)", num, title, source)
            return f"[Chiron] Sales training ST-{num:03d} logged: {title}"
        except Exception as e:
            logger.warning("[Chiron] Failed to log pattern: %s", e)
            return f"(Chiron logging error: {e})"

    def get_all_patterns(self) -> str:
        """Return the full training log content."""
        try:
            if not TRAINING_LOG.exists():
                return ""
            return TRAINING_LOG.read_text().strip()
        except Exception:
            return ""

    def get_pattern_summaries(self) -> List[Dict[str, str]]:
        """Parse the training log into structured summaries for injection."""
        content = self.get_all_patterns()
        if not content:
            return []

        patterns = []
        for block in re.split(r"\n---\n", content):
            title_match = re.search(r"## ST-(\d+) \| (.+)", block)
            trigger_match = re.search(r"\*\*Trigger:\*\* (.+)", block)
            if title_match and trigger_match:
                patterns.append({
                    "id": f"ST-{title_match.group(1)}",
                    "title": title_match.group(2).strip(),
                    "trigger": trigger_match.group(1).strip(),
                })
        return patterns

    def get_coaching_notes(self, situation: str) -> str:
        """Given a sales situation, return relevant coaching notes from the training log.

        Uses keyword matching against triggers. For complex matching,
        this can be upgraded to semantic search via Qdrant.
        """
        patterns = self.get_all_patterns()
        if not patterns:
            return ""

        situation_lower = situation.lower()
        relevant = []

        for block in re.split(r"\n---\n", patterns):
            stripped = block.strip()
            if not stripped or (stripped.startswith("#") and not stripped.startswith("## ST-")):
                continue
            trigger_match = re.search(r"\*\*Trigger:\*\* (.+)", block)
            if not trigger_match:
                continue

            trigger = trigger_match.group(1).lower()
            title_match = re.search(r"## ST-\d+ \| (.+)", block)
            title = title_match.group(1) if title_match else "unknown"

            score = 0
            keywords = re.findall(r"\w+", trigger)
            for kw in keywords:
                if len(kw) > 3 and kw in situation_lower:
                    score += 1

            stale_signals = ["no reply", "silent", "stale", "hasn't replied", "no response", "ghosted", "not replied", "gone silent", "days", "follow up", "follow-up"]
            sit_has_stale = any(s in situation_lower for s in stale_signals)
            trig_has_stale = any(s in trigger for s in stale_signals)
            if sit_has_stale and trig_has_stale:
                score += 3

            full_block_lower = block.lower()
            context_keywords = re.findall(r"\w+", situation_lower)
            for kw in context_keywords:
                if len(kw) > 4 and kw in full_block_lower:
                    score += 0.5

            if score >= 2:
                right_match = re.search(
                    r"\*\*Right approach:\*\*\n(.*?)(?=\n\*\*|\n##|\n---|\Z)",
                    block,
                    re.DOTALL,
                )
                approach = right_match.group(1).strip() if right_match else ""
                relevant.append((score, title, approach))

        if not relevant:
            return ""

        relevant.sort(key=lambda x: -x[0])
        lines = ["[Chiron's coaching notes]"]
        for _, title, approach in relevant[:3]:
            lines.append(f"\n• {title}:")
            if approach:
                lines.append(f"  {approach[:500]}")
        return "\n".join(lines)


    # ------------------------------------------------------------------
    # AUTO-LEARN: Pull leads from CRM, fetch their email threads, analyze
    # ------------------------------------------------------------------

    def _load_analyzed_threads(self) -> set:
        try:
            if ANALYZED_THREADS_FILE.exists():
                return set(json.loads(ANALYZED_THREADS_FILE.read_text()))
        except Exception:
            pass
        return set()

    def _save_analyzed_threads(self, thread_ids: set):
        try:
            ANALYZED_THREADS_FILE.parent.mkdir(parents=True, exist_ok=True)
            ANALYZED_THREADS_FILE.write_text(json.dumps(sorted(thread_ids)))
        except Exception as e:
            logger.debug("[Chiron] Failed to save analyzed threads: %s", e)

    def get_leads_for_analysis(self, max_leads: int = 10) -> List[Dict[str, str]]:
        """Pull high-value leads from CRM that have email history worth analyzing."""
        leads_out = []
        try:
            from openclaw.agents.ira.src.crm.ira_crm import get_crm
            crm = get_crm()
            all_leads = crm.get_all_leads()

            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            active_stages = {"engaged", "qualified", "proposal", "negotiating", "won"}

            candidates = [
                l for l in all_leads
                if l.deal_stage in active_stages and l.emails_sent and l.emails_sent >= 2
            ]
            candidates.sort(key=lambda l: (
                priority_order.get(l.priority, 4),
                -(l.deal_value or 0),
            ))

            for lead in candidates[:max_leads]:
                leads_out.append({
                    "email": lead.email,
                    "company": lead.company or "",
                    "name": getattr(lead, "name", "") or "",
                    "deal_stage": lead.deal_stage or "",
                    "deal_value": str(lead.deal_value or ""),
                    "thread_id": getattr(lead, "thread_id", "") or "",
                })
        except ImportError:
            logger.warning("[Chiron] CRM not available — cannot pull leads")
        except Exception as e:
            logger.warning("[Chiron] Failed to pull leads: %s", e)

        return leads_out

    def fetch_thread_for_lead(self, lead: Dict[str, str]) -> Optional[str]:
        """Fetch the email thread for a lead via Gmail search."""
        try:
            from openclaw.agents.ira.src.tools.google_tools import gmail_search, gmail_get_thread

            thread_id = lead.get("thread_id", "")
            if thread_id:
                content = gmail_get_thread(thread_id=thread_id, max_messages=20)
                if content and "messages" not in content.lower()[:50] or len(content) > 200:
                    return content

            email = lead.get("email", "")
            company = lead.get("company", "")
            query = f"from:{email} OR to:{email}" if email else company
            search_result = gmail_search(query=query, max_results=5)

            if not search_result or "No emails found" in search_result:
                return None

            thread_match = re.search(r"\[thread:(\w+)\]", search_result)
            if thread_match:
                tid = thread_match.group(1)
                return gmail_get_thread(thread_id=tid, max_messages=20)

            return search_result

        except ImportError:
            logger.warning("[Chiron] Gmail tools not available")
            return None
        except Exception as e:
            logger.debug("[Chiron] Failed to fetch thread for %s: %s", lead.get("email"), e)
            return None

    def analyze_thread(self, thread_content: str, lead: Dict[str, str]) -> List[Dict[str, str]]:
        """Use GPT to extract sales lessons from an email thread."""
        if not thread_content or len(thread_content) < 200:
            return []

        try:
            import openai
            client = openai.OpenAI()

            company = lead.get("company", "unknown")
            deal_value = lead.get("deal_value", "")
            deal_stage = lead.get("deal_stage", "")

            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": (
                        "You are Chiron, the sales trainer for Machinecraft Technologies "
                        "(industrial thermoforming machines, India). Analyze this email thread "
                        "and extract reusable sales lessons. Focus on: negotiation tactics, "
                        "objection handling, follow-up timing, relationship dynamics, "
                        "what worked, what didn't. Only extract patterns that are genuinely "
                        "reusable — skip trivial observations. If the thread is too short or "
                        "has no useful lessons, return an empty array.\n\n"
                        "Return JSON: {\"lessons\": [{\"title\": \"...\", \"trigger\": \"...\", "
                        "\"wrong_approach\": \"...\", \"right_approach\": \"...\", "
                        "\"example\": \"...\"}]}"
                    )},
                    {"role": "user", "content": (
                        f"Company: {company} | Deal: {deal_value} {lead.get('deal_currency', '')} "
                        f"| Stage: {deal_stage}\n\n"
                        f"Email thread:\n{thread_content[:15000]}"
                    )},
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            lessons = result.get("lessons", [])
            return [l for l in lessons if l.get("title") and l.get("right_approach")]

        except Exception as e:
            logger.warning("[Chiron] Thread analysis failed for %s: %s", lead.get("company"), e)
            return []

    def auto_learn_from_leads(self, max_leads: int = 5, dry_run: bool = False) -> Dict[str, Any]:
        """Main auto-learn loop: pull leads → fetch threads → analyze → log patterns.

        Called during nap/dream. Returns stats on what was learned.
        """
        result = {
            "leads_scanned": 0,
            "threads_fetched": 0,
            "lessons_extracted": 0,
            "lessons_logged": 0,
            "leads_analyzed": [],
        }

        analyzed = self._load_analyzed_threads()
        leads = self.get_leads_for_analysis(max_leads=max_leads)
        result["leads_scanned"] = len(leads)

        if not leads:
            logger.info("[Chiron] No leads to analyze")
            return result

        for lead in leads:
            email = lead.get("email", "")
            company = lead.get("company", email)
            thread_key = lead.get("thread_id") or email

            if thread_key in analyzed:
                logger.debug("[Chiron] Already analyzed %s — skipping", company)
                continue

            logger.info("[Chiron] Analyzing email thread for %s...", company)
            thread = self.fetch_thread_for_lead(lead)
            if not thread or len(thread) < 300:
                analyzed.add(thread_key)
                continue

            result["threads_fetched"] += 1
            lessons = self.analyze_thread(thread, lead)
            result["lessons_extracted"] += len(lessons)

            for lesson in lessons:
                if dry_run:
                    logger.info("[Chiron/DryRun] Would log: %s", lesson.get("title"))
                    result["lessons_logged"] += 1
                    continue

                existing = self.get_all_patterns().lower()
                title_lower = lesson.get("title", "").lower()
                if any(t in existing for t in title_lower.split()[:3] if len(t) > 5):
                    dupe_check = sum(1 for w in title_lower.split() if len(w) > 4 and w in existing)
                    if dupe_check >= 3:
                        logger.debug("[Chiron] Skipping likely duplicate: %s", lesson.get("title"))
                        continue

                self.log_pattern(
                    title=lesson.get("title", ""),
                    trigger=lesson.get("trigger", ""),
                    wrong_approach=lesson.get("wrong_approach", ""),
                    right_approach=lesson.get("right_approach", ""),
                    example=lesson.get("example", ""),
                    source=f"chiron_auto_learn/{company}",
                )
                result["lessons_logged"] += 1

            analyzed.add(thread_key)
            result["leads_analyzed"].append(company)

        self._save_analyzed_threads(analyzed)

        logger.info(
            "[Chiron] Auto-learn complete: %d leads scanned, %d threads fetched, "
            "%d lessons extracted, %d logged",
            result["leads_scanned"], result["threads_fetched"],
            result["lessons_extracted"], result["lessons_logged"],
        )
        return result


def get_chiron() -> Chiron:
    """Get or create the singleton Chiron instance."""
    global _chiron_instance
    if _chiron_instance is None:
        _chiron_instance = Chiron()
    return _chiron_instance


def get_sales_guidance_for_prompt() -> str:
    """Load sales training for injection into system prompts (Athena + Hermes).

    Returns a formatted string of all learned patterns, or empty string if none.
    """
    try:
        chiron = get_chiron()
        content = chiron.get_all_patterns()
        if not content or len(content) < 50:
            return ""
        return f"\nCHIRON'S SALES TRAINING (learned patterns from real deals):\n{content}\n"
    except Exception as e:
        logger.debug("[Chiron] Failed to load sales guidance: %s", e)
        return ""


def get_coaching_notes(situation: str) -> str:
    """Get situation-specific coaching notes for email drafting."""
    try:
        return get_chiron().get_coaching_notes(situation)
    except Exception:
        return ""


def auto_learn_from_leads(max_leads: int = 5, dry_run: bool = False) -> Dict[str, Any]:
    """Convenience: run Chiron's auto-learn loop on CRM leads."""
    return get_chiron().auto_learn_from_leads(max_leads=max_leads, dry_run=dry_run)
