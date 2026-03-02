#!/usr/bin/env python3
"""
FULL SIMULATION RUNNER — Multi-Turn Email Training with Minerva Coaching
=========================================================================

Runs multi-turn email simulations between Rushabh (customer) and Ira
(sales assistant), with Minerva acting as a grounded pre-send coach.

Each round:
  1. Generate unique customer scenarios via scenario_generator
  2. For each scenario, run a multi-turn email conversation
  3. Minerva reviews every Ira draft; nudges revisions when needed
  4. Track mistakes, store lessons, measure accuracy
  5. If accuracy < target, rewire and run another round with NEW scenarios

Usage:
    python agents/apollo/full_simulation_runner.py
    python agents/apollo/full_simulation_runner.py --target 0.85 --max-rounds 3
    python agents/apollo/full_simulation_runner.py --dream
"""

import argparse
import base64
import json
import logging
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# Brain — generate_answer
# ---------------------------------------------------------------------------
_brain_path = str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "brain")
if _brain_path not in sys.path:
    sys.path.insert(0, _brain_path)

from generate_answer import generate_answer

# ---------------------------------------------------------------------------
# Grounded coach (Minerva)
# ---------------------------------------------------------------------------
from grounded_coach import coach_review, coach_nudge_for_revision

# ---------------------------------------------------------------------------
# Scenario generator
# ---------------------------------------------------------------------------
from scenario_generator import generate_unique_scenarios

# ---------------------------------------------------------------------------
# Overnight training helpers (optional)
# ---------------------------------------------------------------------------
try:
    from overnight_training import ELORating, MistakeLog, store_training_lesson
except ImportError:

    class ELORating:
        """Minimal ELO tracker when overnight_training is absent."""

        def __init__(self, initial: float = 1200.0):
            self.rating = initial

        def update(self, score: float) -> float:
            delta = (score - 5.0) * 8.0
            self.rating += delta
            return self.rating

    class MistakeLog:
        """Minimal mistake accumulator."""

        def __init__(self):
            self.mistakes: List[Dict] = []

        def add(self, sim_id: str, turn: int, errors: List[str], guidance: str):
            self.mistakes.append(
                {
                    "sim_id": sim_id,
                    "turn": turn,
                    "errors": errors,
                    "guidance": guidance,
                    "ts": datetime.now().isoformat(),
                }
            )

        def summary(self) -> str:
            if not self.mistakes:
                return "No mistakes recorded."
            lines = [f"  [{m['sim_id'][:8]}] turn {m['turn']}: {m['errors'][0]}" for m in self.mistakes[:20]]
            return f"{len(self.mistakes)} total mistakes:\n" + "\n".join(lines)

    def store_training_lesson(lesson: str, source: str = "simulation") -> None:
        path = PROJECT_ROOT / "data" / "learned_lessons" / "simulation_lessons.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        lessons: List[Dict] = []
        if path.exists():
            try:
                lessons = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        lessons.append({"lesson": lesson, "source": source, "ts": datetime.now().isoformat()})
        path.write_text(json.dumps(lessons, indent=2))


# ---------------------------------------------------------------------------
# IraAgent — full pipeline (optional, fallback to generate_answer)
# ---------------------------------------------------------------------------
IRA_AGENT_AVAILABLE = False
_ira_agent_instance = None

try:
    from openclaw.agents.ira.agent import IraAgent

    IRA_AGENT_AVAILABLE = True
except ImportError:
    IraAgent = None

# ---------------------------------------------------------------------------
# Gmail dual-auth setup
# ---------------------------------------------------------------------------
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

RUSHABH_EMAIL = "rushabh@machinecraft.org"
IRA_EMAIL = "ira@machinecraft.org"

logger = logging.getLogger("apollo.full_sim")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ============================================================================
# GMAIL HELPERS
# ============================================================================

def _build_gmail_service(token_name: str) -> Optional[Any]:
    """Build a Gmail API service from a token file, or return None."""
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


def _get_rushabh_service() -> Optional[Any]:
    return _build_gmail_service("token_rushabh.json") or _build_gmail_service("token.json")


def _get_ira_service() -> Optional[Any]:
    return _build_gmail_service("token.json") or _build_gmail_service("token_ira_backup.json")


def _send_email(
    service: Any,
    from_addr: str,
    to_addr: str,
    subject: str,
    body: str,
    thread_id: Optional[str] = None,
) -> Optional[Dict]:
    if service is None:
        return None
    msg = MIMEText(body)
    msg["to"] = to_addr
    msg["from"] = from_addr
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload: Dict[str, Any] = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id
    try:
        return service.users().messages().send(userId="me", body=payload).execute()
    except Exception as exc:
        logger.error("Email send failed: %s", exc)
        return None


# ============================================================================
# SIMULATION LOG
# ============================================================================

@dataclass
class SimulationLog:
    sim_id: str
    title: str
    turns: List[Dict] = field(default_factory=list)
    mistakes: List[Dict] = field(default_factory=list)
    corrections: List[str] = field(default_factory=list)
    final_score: float = 0.0
    expected_series: str = ""
    actual_series_mentioned: str = ""
    outcome: str = "incomplete"

    def to_dict(self) -> Dict:
        return {
            "sim_id": self.sim_id,
            "title": self.title,
            "turns": self.turns,
            "mistakes": self.mistakes,
            "corrections": self.corrections,
            "final_score": self.final_score,
            "expected_series": self.expected_series,
            "actual_series_mentioned": self.actual_series_mentioned,
            "outcome": self.outcome,
        }


# ============================================================================
# IRA RESPONSE — full pipeline with fallback
# ============================================================================

_SERIES_RE = re.compile(r"\b(PF1|PF2|AM|IMG|FCS|UNO|DUO|PLAY)\b", re.IGNORECASE)


def _get_ira_agent() -> Optional[Any]:
    global _ira_agent_instance
    if not IRA_AGENT_AVAILABLE:
        return None
    if _ira_agent_instance is None:
        try:
            _ira_agent_instance = IraAgent()
        except Exception as exc:
            logger.warning("IraAgent init failed, using generate_answer fallback: %s", exc)
            return None
    return _ira_agent_instance


def _ira_respond(
    question: str,
    conversation_history: str = "",
    nudge: str = "",
    from_email: str = "",
    thread_id: str = "",
) -> str:
    """
    Get Ira's response.  Tries the full IraAgent pipeline first
    (memory, RAG, conversation tracking), then falls back to
    generate_answer with conversation context prepended.
    """
    effective_query = question
    if nudge:
        effective_query = (
            f"{question}\n\n"
            f"[COACH FEEDBACK — please revise accordingly]\n{nudge}"
        )

    agent = _get_ira_agent()
    if agent is not None:
        try:
            resp = agent.process_email(
                body=effective_query,
                from_email=from_email or "simulation@machinecraft.org",
                subject="Simulation inquiry",
                thread_id=thread_id or None,
            )
            if resp and resp.message:
                return resp.message
        except Exception as exc:
            logger.warning("IraAgent.process_email failed, falling back: %s", exc)

    context_pack: Dict[str, Any] = {}
    if conversation_history:
        context_pack["rolling_summary"] = conversation_history[-3000:]
        context_pack["recent_messages"] = [
            {"role": "user", "content": conversation_history[-1500:]}
        ]

    result = generate_answer(intent=effective_query, context_pack=context_pack, channel="email")
    return result.text if hasattr(result, "text") else str(result)


# ============================================================================
# SINGLE SIMULATION
# ============================================================================

def run_simulation(
    sim: Dict,
    rushabh_service: Optional[Any],
    ira_service: Optional[Any],
    mistake_log: MistakeLog,
    sim_num: int = 1,
) -> SimulationLog:
    """
    Run one multi-turn simulation.

    For each customer turn:
      1. (Optionally) send real email from Rushabh
      2. Ira generates a response via the full pipeline
      3. Minerva reviews the draft
      4. If REVISE: nudge Ira, allow up to 2 revision attempts
      5. (Optionally) send approved response from Ira's account
      6. Log mistakes, store lessons, accumulate conversation context
    """
    sim_id = sim.get("id", str(uuid.uuid4()))
    title = sim.get("title", f"Simulation {sim_num}")
    expected_series = sim.get("expected_machine_series", "")
    turns = sim.get("turns", [])

    log = SimulationLog(
        sim_id=sim_id,
        title=title,
        expected_series=expected_series,
    )

    conversation_context = ""
    thread_id = ""
    last_score = 0.0

    print(f"\n{'=' * 70}")
    print(f"  SIM #{sim_num}: {title}")
    print(f"  Expected series: {expected_series}")
    print(f"{'=' * 70}")

    for turn_idx, turn in enumerate(turns):
        turn_num = turn_idx + 1
        customer_msg = turn.get("content", "")

        print(f"\n  --- Turn {turn_num}/{len(turns)} ---")
        print(f"  CUSTOMER: {customer_msg[:120]}...")

        # 1. Send real email from Rushabh (if Gmail available)
        subject = f"[SIM-{sim_id[:8]}] {title}"
        if turn_num > 1:
            subject = f"Re: {subject}"
        sent = _send_email(rushabh_service, RUSHABH_EMAIL, IRA_EMAIL, subject, customer_msg, thread_id or None)
        if sent:
            thread_id = thread_id or sent.get("threadId", "")

        # 2. Ira generates response with accumulated context
        conversation_context += f"\nCustomer: {customer_msg}\n"
        ira_draft = _ira_respond(
            question=customer_msg,
            conversation_history=conversation_context,
            from_email=RUSHABH_EMAIL,
            thread_id=thread_id,
        )
        print(f"  IRA DRAFT: {ira_draft[:150]}...")

        # 3. Minerva reviews
        review = coach_review(customer_msg, ira_draft)
        verdict = review.get("verdict", "REVISE")
        score = review.get("overall_score", 0.0)
        print(f"  MINERVA: {verdict} (score: {score}/10)")

        # 4. Revision loop (max 2 attempts)
        revision_count = 0
        while verdict == "REVISE" and revision_count < 2:
            revision_count += 1
            errors = review.get("factual_errors", [])
            guidance = review.get("correction_guidance", "")

            print(f"    ERRORS: {errors}")
            print(f"    GUIDANCE: {guidance[:100]}...")

            mistake_log.add(sim_id, turn_num, errors, guidance)
            log.mistakes.append({"turn": turn_num, "revision": revision_count, "errors": errors})

            nudge = coach_nudge_for_revision(customer_msg, ira_draft, review)
            ira_draft = _ira_respond(
                question=customer_msg,
                conversation_history=conversation_context,
                nudge=nudge,
                from_email=RUSHABH_EMAIL,
                thread_id=thread_id,
            )
            print(f"    REVISED (attempt {revision_count}): {ira_draft[:120]}...")

            review = coach_review(customer_msg, ira_draft)
            verdict = review.get("verdict", "REVISE")
            score = review.get("overall_score", 0.0)
            print(f"    MINERVA: {verdict} (score: {score}/10)")

        # 5. Send approved response from Ira
        _send_email(ira_service, IRA_EMAIL, RUSHABH_EMAIL, f"Re: {subject}", ira_draft, thread_id or None)

        # 6. Store lesson
        lesson = review.get("lesson", "")
        if lesson:
            store_training_lesson(lesson, source=f"sim-{sim_id[:8]}")
            log.corrections.append(lesson)

        # 7. Accumulate context for next turn
        conversation_context += f"Ira: {ira_draft}\n"
        last_score = score

        log.turns.append(
            {
                "turn": turn_num,
                "customer": customer_msg[:500],
                "ira_final": ira_draft[:500],
                "score": score,
                "verdict": verdict,
                "revisions": revision_count,
            }
        )

    # After all turns: check if the correct series was recommended
    all_ira_text = " ".join(t.get("ira_final", "") for t in log.turns)
    mentioned = set(m.upper() for m in _SERIES_RE.findall(all_ira_text))
    log.actual_series_mentioned = ", ".join(sorted(mentioned)) if mentioned else "NONE"

    if expected_series.upper() in mentioned:
        log.outcome = "CORRECT"
    else:
        log.outcome = "WRONG_SERIES"

    log.final_score = last_score

    print(f"\n  RESULT: {log.outcome}  |  Expected: {expected_series}  |  Mentioned: {log.actual_series_mentioned}")
    print(f"  Final score: {log.final_score}/10  |  Mistakes: {len(log.mistakes)}")

    return log


# ============================================================================
# FULL TRAINING LOOP
# ============================================================================

def run_all_simulations(
    target_accuracy: float = 0.9,
    max_rounds: int = 5,
    sims_per_round: int = 10,
) -> Dict:
    """
    Multi-round training loop.

    Each round generates UNIQUE scenarios, runs them, and checks accuracy.
    If accuracy >= target, stop.  Otherwise attempt brain rewire and run
    another round with fresh scenarios.
    """
    rushabh_service = _get_rushabh_service()
    ira_service = _get_ira_service()

    if rushabh_service:
        print("Gmail (Rushabh): connected")
    else:
        print("Gmail (Rushabh): NOT available — running in offline mode")
    if ira_service:
        print("Gmail (Ira): connected")
    else:
        print("Gmail (Ira): NOT available — running in offline mode")

    elo = ELORating()
    trajectory: List[Dict] = []

    for round_num in range(1, max_rounds + 1):
        print(f"\n{'#' * 70}")
        print(f"  ROUND {round_num}/{max_rounds}  |  Target accuracy: {target_accuracy:.0%}")
        print(f"{'#' * 70}")

        scenarios = generate_unique_scenarios(count=sims_per_round)
        print(f"  Generated {len(scenarios)} unique scenarios")

        mistake_log = MistakeLog()
        logs: List[SimulationLog] = []

        for idx, sim in enumerate(scenarios, 1):
            sim_log = run_simulation(sim, rushabh_service, ira_service, mistake_log, sim_num=idx)
            logs.append(sim_log)

        # Compute accuracy
        correct = sum(1 for l in logs if l.outcome == "CORRECT")
        total = len(logs)
        accuracy = correct / total if total > 0 else 0.0
        avg_score = sum(l.final_score for l in logs) / total if total > 0 else 0.0
        elo.update(avg_score)

        # Distance from reality audit
        print(f"\n{'=' * 70}")
        print(f"  DISTANCE FROM REALITY AUDIT — Round {round_num}")
        print(f"{'=' * 70}")
        for l in logs:
            tag = "PASS" if l.outcome == "CORRECT" else "FAIL"
            print(
                f"  [{tag}] {l.title[:50]:<50}  "
                f"expected={l.expected_series:<5}  "
                f"got={l.actual_series_mentioned:<12}  "
                f"score={l.final_score:.1f}"
            )
        print(f"\n  Accuracy: {accuracy:.0%} ({correct}/{total})")
        print(f"  Avg score: {avg_score:.1f}/10")
        print(f"  ELO: {elo.rating:.0f}")
        print(f"  Mistakes this round: {len(mistake_log.mistakes)}")

        round_result = {
            "round": round_num,
            "accuracy": accuracy,
            "avg_score": avg_score,
            "elo": elo.rating,
            "correct": correct,
            "total": total,
            "mistakes": len(mistake_log.mistakes),
        }
        trajectory.append(round_result)

        if accuracy >= target_accuracy:
            print(f"\n  TARGET REACHED ({accuracy:.0%} >= {target_accuracy:.0%}). Stopping.")
            break

        if round_num < max_rounds:
            print(f"\n  Accuracy {accuracy:.0%} < {target_accuracy:.0%}. Attempting brain rewire...")
            try:
                from brain_rewire import rewire_brain

                rewire_brain()
                print("  Brain rewire complete. Starting next round with NEW scenarios.")
            except ImportError:
                print("  brain_rewire not available — continuing with next round anyway.")

    # Print improvement trajectory
    print(f"\n{'=' * 70}")
    print("  IMPROVEMENT TRAJECTORY")
    print(f"{'=' * 70}")
    for r in trajectory:
        bar = "#" * int(r["accuracy"] * 40)
        print(
            f"  Round {r['round']}: {r['accuracy']:>5.0%} |{bar:<40}| "
            f"score={r['avg_score']:.1f}  elo={r['elo']:.0f}"
        )

    # Persist results
    output_dir = PROJECT_ROOT / "data" / "training"
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"full_sim_results_{ts}.json"
    output_file.write_text(
        json.dumps(
            {
                "timestamp": ts,
                "target_accuracy": target_accuracy,
                "max_rounds": max_rounds,
                "sims_per_round": sims_per_round,
                "trajectory": trajectory,
            },
            indent=2,
        )
    )
    print(f"\n  Results saved to {output_file}")

    return {"trajectory": trajectory, "output_file": str(output_file)}


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Full multi-turn email simulation with Minerva coaching"
    )
    parser.add_argument(
        "--target",
        type=float,
        default=0.9,
        help="Target accuracy to stop training (default: 0.9)",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=5,
        help="Maximum training rounds (default: 5)",
    )
    parser.add_argument(
        "--sims",
        type=int,
        default=10,
        help="Simulations per round (default: 10)",
    )
    parser.add_argument(
        "--dream",
        action="store_true",
        help="Trigger dream/sleep mode after training completes",
    )
    args = parser.parse_args()

    print(
        f"\n"
        f"{'=' * 70}\n"
        f"  FULL SIMULATION RUNNER\n"
        f"  Target: {args.target:.0%}  |  Max rounds: {args.max_rounds}  |  Sims/round: {args.sims}\n"
        f"{'=' * 70}"
    )

    results = run_all_simulations(
        target_accuracy=args.target,
        max_rounds=args.max_rounds,
        sims_per_round=args.sims,
    )

    if args.dream:
        print("\n  Triggering dream mode for memory consolidation...")
        try:
            from openclaw.agents.ira.skills.memory.dream_orchestrator import DreamOrchestrator

            orchestrator = DreamOrchestrator()
            orchestrator.run()
            print("  Dream mode complete.")
        except ImportError:
            try:
                from openclaw.agents.ira.src.brain.dream_mode import run_dream_mode

                run_dream_mode()
                print("  Dream mode complete (via brain dream_mode).")
            except ImportError:
                print("  Dream mode not available — skipping.")


if __name__ == "__main__":
    main()
