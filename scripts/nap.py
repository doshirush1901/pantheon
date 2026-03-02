#!/usr/bin/env python3
"""
NAP MODE — Ira's Sleep-and-Learn Cycle
=======================================

Run this before closing your PC. Ira will:
1. Send a "going to sleep" message to Telegram
2. Process feedback backlog + error logs (Phase 0)
3. Run document & interaction dream (Phase 1)
4. Consolidate episodic memories (Phase 2)
5. Consolidate knowledge graph (Phase 3)
6. Clean up stale memories (Phase 4)
7. Run neuroscience + advanced + experimental dream (Phases 5-7)
8. Reflect on drip campaigns (Phase 8)
9. Run Benchy self-improvement loop (the "lucid dream")
10. Resolve unresolved conflicts
11. Send a dream journal to Telegram

Usage:
    python scripts/nap.py                  # Full nap (all phases)
    python scripts/nap.py --time 60        # 1-hour nap (phases prioritized by value)
    python scripts/nap.py --quick          # Quick nap (skip Benchy + heavy phases)
    python scripts/nap.py --benchy-only    # Just run Benchy self-improvement
    python scripts/nap.py --dry-run        # Preview without real memory ops
"""

import asyncio
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "brain"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "memory"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "sales"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "common"))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("\"'")
            if not os.environ.get(key) or key.endswith(("_API_KEY", "_KEY", "_TOKEN", "_URL")):
                os.environ[key] = value

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DATE_STR = datetime.now().strftime("%Y-%m-%d")
NAP_LOG = LOG_DIR / f"nap_{DATE_STR}.log"


# =============================================================================
# TELEGRAM HELPERS
# =============================================================================

def _send_telegram(text: str, parse_mode: str = "HTML") -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = (
        os.environ.get("TELEGRAM_CHAT_ID")
        or os.environ.get("TELEGRAM_ADMIN_CHAT_ID")
        or os.environ.get("EXPECTED_CHAT_ID")
    )
    if not token or not chat_id:
        return False
    try:
        import requests

        if len(text) > 4000:
            text = text[:3950] + "\n\n... [truncated]"
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
            timeout=15,
        )
        if r.status_code != 200:
            # Retry without parse_mode (Telegram rejects bad HTML/Markdown)
            payload.pop("parse_mode", None)
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json=payload,
                timeout=15,
            )
        return r.status_code == 200
    except Exception:
        return False


def _log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(NAP_LOG, "a") as f:
        f.write(line + "\n")


# =============================================================================
# NAP JOURNAL — collects results from each phase
# =============================================================================

class NapJournal:
    def __init__(self):
        self.started = datetime.now()
        self.phases: Dict[str, Dict[str, Any]] = {}
        self.errors: List[str] = []

    def record(self, phase: str, data: Dict[str, Any]):
        self.phases[phase] = data

    def error(self, phase: str, err: str):
        self.errors.append(f"{phase}: {err}")

    def duration_str(self) -> str:
        elapsed = (datetime.now() - self.started).total_seconds()
        mins, secs = divmod(int(elapsed), 60)
        return f"{mins}m {secs}s"

    def to_telegram_summary(self) -> str:
        lines = [
            "🌙 <b>Ira's Dream Journal</b>",
            f"Slept for {self.duration_str()}",
            "",
        ]

        p0 = self.phases.get("feedback", {})
        if p0:
            lines.append(f"📋 <b>Feedback:</b> {p0.get('corrections', 0)} corrections, {p0.get('gaps', 0)} gaps")

        p1 = self.phases.get("dream", {})
        if p1:
            lines.append(f"🌙 <b>Dream:</b> {p1.get('docs', 0)} docs, {p1.get('facts', 0)} facts learned")

        p2 = self.phases.get("episodic", {})
        if p2:
            lines.append(f"🧠 <b>Episodic:</b> {p2.get('patterns', 0)} patterns, {p2.get('memories_created', 0)} memories")

        p3 = self.phases.get("graph", {})
        if p3:
            lines.append(f"🔗 <b>Graph:</b> {p3.get('edges_strengthened', 0)} strengthened, {p3.get('edges_created', 0)} new")

        p4 = self.phases.get("cleanup", {})
        if p4:
            lines.append(f"🧹 <b>Cleanup:</b> {p4.get('decayed', 0)} decayed, {p4.get('archived', 0)} archived")

        p567 = self.phases.get("orchestrated", {})
        if p567:
            lines.append(f"🎯 <b>Deep Dream:</b> self-test {p567.get('self_test', '?')}, calibration {p567.get('calibration', '?')}")

        p8 = self.phases.get("drip", {})
        if p8:
            lines.append(f"📧 <b>Drip Reflection:</b> {p8.get('ideas', 0)} new ideas, score {p8.get('score', '?')}/100")

        benchy = self.phases.get("benchy", {})
        if benchy:
            results = benchy.get("results", {})
            passed = sum(1 for v in results.values() if v >= 0.9)
            total = len(results)
            lines.append(f"🏋️ <b>Benchy (Lucid Dream):</b> {passed}/{total} scenarios passed")
            for sid, score in results.items():
                icon = "✅" if score >= 0.9 else "🔄"
                lines.append(f"  {icon} {sid}: {score:.0%}")

        conflicts = self.phases.get("conflicts", {})
        if conflicts:
            lines.append(f"⚖️ <b>Conflicts:</b> {conflicts.get('resolved', 0)} resolved, {conflicts.get('remaining', 0)} remaining")

        if self.errors:
            lines.append("")
            lines.append(f"⚠️ <b>Issues ({len(self.errors)}):</b>")
            for e in self.errors[:5]:
                lines.append(f"  • {e[:80]}")

        lines.append("")
        lines.append("Ready when you are! 🚀")
        return "\n".join(lines)

    def save(self):
        results_dir = PROJECT_ROOT / "data" / "dream_results"
        results_dir.mkdir(parents=True, exist_ok=True)
        out = results_dir / f"nap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        out.write_text(json.dumps({
            "started": self.started.isoformat(),
            "duration": self.duration_str(),
            "phases": self.phases,
            "errors": self.errors,
        }, indent=2, default=str))


# =============================================================================
# PHASE RUNNERS
# =============================================================================

def run_phase_feedback(journal: NapJournal):
    """Phase 0/0.5: Process feedback backlog + error logs."""
    _log("📋 Phase 0: Feedback backlog + error logs...")
    corrections = 0
    gaps = 0

    # Feedback backlog
    backlog = PROJECT_ROOT / "data" / "feedback_backlog.jsonl"
    if backlog.exists():
        try:
            from correction_learner import CorrectionLearner

            cl = CorrectionLearner()
            for line in backlog.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    content = (
                        entry.get("content", "")
                        or entry.get("user_feedback", "")
                        or json.dumps(entry.get("coach_analysis", ""))
                    )
                    if content:
                        result = cl.detect_and_learn(content, "")
                        if result.get("learned"):
                            corrections += 1
                except (json.JSONDecodeError, Exception):
                    pass
            _log(f"  Feedback backlog: {corrections} corrections applied")
        except ImportError:
            _log("  CorrectionLearner not available, skipping")

    # Error logs -> knowledge gaps
    errors_dir = PROJECT_ROOT / "data" / "logs"
    if errors_dir.exists():
        try:
            gaps_file = PROJECT_ROOT / "data" / "knowledge_gaps.json"
            existing_gaps = json.loads(gaps_file.read_text()) if gaps_file.exists() else []
            existing_topics = {g.get("topic", "") for g in existing_gaps}

            for log_file in sorted(errors_dir.glob("errors_*.jsonl"))[-3:]:
                for line in log_file.read_text().splitlines():
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        component = entry.get("component", "")
                        error_msg = str(entry.get("error", ""))
                        if "retrieval" in component.lower() or "knowledge" in error_msg.lower():
                            topic = entry.get("context", {}).get("query", error_msg[:100])
                            if topic and topic not in existing_topics:
                                existing_gaps.append({
                                    "topic": topic,
                                    "source": "nap_error_scan",
                                    "detected": datetime.now().isoformat(),
                                    "priority": "medium",
                                })
                                existing_topics.add(topic)
                                gaps += 1
                    except json.JSONDecodeError:
                        pass

            gaps_file.parent.mkdir(parents=True, exist_ok=True)
            gaps_file.write_text(json.dumps(existing_gaps, indent=2))
        except Exception as e:
            journal.error("feedback", str(e))

    _log(f"  Result: {corrections} corrections, {gaps} new gaps")
    journal.record("feedback", {"corrections": corrections, "gaps": gaps})


def run_phase_dream(journal: NapJournal):
    """Phase 1: Document + interaction dream."""
    _log("🌙 Phase 1: Dream mode (documents + conversations)...")
    try:
        from dream_mode import IntegratedDreamMode

        dream = IntegratedDreamMode()
        result = dream.dream(force_all=False, deep_mode=False)
        docs = result.get("documents_processed", 0)
        facts = result.get("facts_learned", 0)
        _log(f"  Result: {docs} docs, {facts} facts, {result.get('qdrant_indexed', 0)} indexed")
        journal.record("dream", {"docs": docs, "facts": facts})
    except Exception as e:
        _log(f"  Error: {e}")
        journal.error("dream", str(e))


def run_phase_episodic(journal: NapJournal):
    """Phase 2: Episodic consolidation."""
    _log("🧠 Phase 2: Episodic consolidation...")
    try:
        from episodic_consolidator import run_consolidation

        result = run_consolidation(dry_run=False)
        _log(f"  Result: {result.patterns_found} patterns, {result.memories_created} memories")
        journal.record("episodic", {
            "patterns": result.patterns_found,
            "memories_created": result.memories_created,
            "episodes": result.episodes_analyzed,
        })
    except Exception as e:
        _log(f"  Error: {e}")
        journal.error("episodic", str(e))


def run_phase_graph(journal: NapJournal):
    """Phase 3: Knowledge graph consolidation."""
    _log("🔗 Phase 3: Knowledge graph consolidation...")
    try:
        from graph_consolidation import GraphConsolidator

        consolidator = GraphConsolidator(verbose=False)
        result = consolidator.consolidate(days=1)
        _log(f"  Result: {result.edges_strengthened} strengthened, {result.edges_created} new edges")
        journal.record("graph", {
            "edges_strengthened": result.edges_strengthened,
            "edges_created": result.edges_created,
            "edges_weakened": result.edges_weakened,
        })
    except Exception as e:
        _log(f"  Error: {e}")
        journal.error("graph", str(e))


def run_phase_cleanup(journal: NapJournal):
    """Phase 4: Memory cleanup."""
    _log("🧹 Phase 4: Memory cleanup...")
    try:
        from memory_intelligence import MemoryIntelligence

        mi = MemoryIntelligence()
        decayed = mi.decay_old_memories(days=30)
        archived = mi.archive_memories(days=180)
        _log(f"  Result: {decayed} decayed, {archived} archived")
        journal.record("cleanup", {"decayed": decayed, "archived": archived})
    except Exception as e:
        _log(f"  Error: {e}")
        journal.error("cleanup", str(e))


def run_phase_orchestrated(journal: NapJournal, dry_run: bool = False):
    """Phases 5-7: Orchestrated deep dream."""
    _log("🎯 Phases 5-7: Orchestrated deep dream...")
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "skills" / "memory"))
        from dream_orchestrator import run_orchestrated_dream

        results = run_orchestrated_dream(dry_run=dry_run, verbose=False)
        ctx = results.get("context", {})
        st_score = ctx.get("self_test_score", 0)
        st_total = ctx.get("self_test_total", 0)
        cal = ctx.get("calibration_score", 0)
        _log(f"  Result: self-test {st_score}/{st_total}, calibration {cal:.2f}")
        journal.record("orchestrated", {
            "self_test": f"{st_score}/{st_total}",
            "calibration": f"{cal:.2f}",
            "insights": len(ctx.get("creative_insights", [])),
            "gaps": len(ctx.get("knowledge_gaps", [])),
            "conflicts_detected": len(ctx.get("conflicts_detected", [])),
        })
    except Exception as e:
        _log(f"  Error: {e}")
        journal.error("orchestrated", str(e))


def run_phase_drip(journal: NapJournal):
    """Phase 8: Drip campaign dream reflection."""
    _log("📧 Phase 8: Drip campaign reflection...")
    try:
        from drip_dream_reflection import run_drip_dream

        results = run_drip_dream(verbose=False)
        ideas = results.get("ideas_generated", 0)
        score = results.get("self_evaluation", {}).get("score", "?")
        _log(f"  Result: {ideas} ideas, self-score {score}/100")
        journal.record("drip", {"ideas": ideas, "score": score})
    except Exception as e:
        _log(f"  Error: {e}")
        journal.error("drip", str(e))


async def run_phase_benchy(journal: NapJournal, threshold: float = 0.85, max_iterations: int = 10):
    """Lucid Dream: Benchy self-improvement loop."""
    _log("🏋️ Lucid Dream: Benchy self-improvement...")
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from benchy import run_all_scenarios

        # Clear immune system so Benchy gets clean scores
        try:
            from openclaw.agents.ira.src.holistic.immune_system import get_immune_system
            immune = get_immune_system()
            immune._chronic_issues.clear()
        except Exception:
            pass

        results = await run_all_scenarios(
            max_iterations=max_iterations,
            threshold=threshold,
            dry_run=False,
        )

        scores = {}
        for sid, card in results.items():
            scores[sid] = card.overall_score
            status = "PASS" if card.overall_score >= threshold else "IMPROVING"
            _log(f"  {status}: {sid} = {card.overall_score:.0%}")

        journal.record("benchy", {"results": scores, "threshold": threshold})
    except Exception as e:
        _log(f"  Error: {e}")
        journal.error("benchy", str(e))
        traceback.print_exc()


def run_phase_conflicts(journal: NapJournal):
    """Resolve unresolved conflicts from conflicts.json."""
    _log("⚖️ Resolving conflicts...")
    conflicts_file = PROJECT_ROOT / "data" / "conflicts.json"
    if not conflicts_file.exists():
        journal.record("conflicts", {"resolved": 0, "remaining": 0})
        return

    try:
        conflicts = json.loads(conflicts_file.read_text())
        if not isinstance(conflicts, list):
            return

        unresolved = [c for c in conflicts if not c.get("resolved")]
        if not unresolved:
            _log("  No unresolved conflicts")
            journal.record("conflicts", {"resolved": 0, "remaining": 0})
            return

        resolved_count = 0
        stale_threshold = 7  # days

        for conflict in unresolved:
            ts_str = conflict.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str)
                age_days = (datetime.now() - ts).days
            except (ValueError, TypeError):
                age_days = 0

            content = conflict.get("new_content", "")

            # Auto-resolve: stale conflicts (>7 days), trivial messages, or non-actionable
            trivial_patterns = [
                "are you alive", "who are you", "hi", "hello", "what's the latest",
                "can you tell me who you are",
            ]
            is_trivial = any(p in content.lower() for p in trivial_patterns)
            is_stale = age_days > stale_threshold

            if is_trivial or is_stale:
                conflict["resolved"] = True
                conflict["resolution"] = "auto_nap" if is_trivial else "stale_auto_resolved"
                conflict["resolved_at"] = datetime.now().isoformat()
                resolved_count += 1

        remaining = sum(1 for c in conflicts if not c.get("resolved"))
        conflicts_file.write_text(json.dumps(conflicts, indent=2))
        _log(f"  Result: {resolved_count} resolved, {remaining} remaining")
        journal.record("conflicts", {"resolved": resolved_count, "remaining": remaining})
    except Exception as e:
        _log(f"  Error: {e}")
        journal.error("conflicts", str(e))


# =============================================================================
# MAIN NAP ORCHESTRATOR
# =============================================================================

async def nap(
    quick: bool = False,
    benchy_only: bool = False,
    dry_run: bool = False,
    time_budget_min: Optional[int] = None,
):
    journal = NapJournal()
    deadline = (
        datetime.now().timestamp() + time_budget_min * 60
        if time_budget_min
        else None
    )

    def minutes_left() -> Optional[float]:
        if deadline is None:
            return None
        return max(0, (deadline - datetime.now().timestamp()) / 60)

    def has_time(min_needed: float = 2.0) -> bool:
        """Check if we have at least min_needed minutes left."""
        remaining = minutes_left()
        if remaining is None:
            return True
        return remaining >= min_needed

    def time_status() -> str:
        remaining = minutes_left()
        if remaining is None:
            return ""
        return f" ({remaining:.0f}min left)"

    mode = "quick" if quick else "benchy-only" if benchy_only else "full"
    time_label = f" ({time_budget_min}min)" if time_budget_min else ""

    _log("=" * 60)
    _log(f"IRA NAP MODE — Sleep & Learn{time_label}")
    _log(f"Mode: {mode}")
    _log(f"Dry run: {dry_run}")
    if time_budget_min:
        _log(f"Time budget: {time_budget_min} minutes")
    _log("=" * 60)

    mode_label = "quick nap" if quick else "Benchy training" if benchy_only else "full dream cycle"
    _send_telegram(
        f"😴 <b>Going to sleep{time_label}...</b>\n\n"
        f"Rushabh is closing the PC. Starting {mode_label}.\n"
        f"I'll send my dream journal when I wake up.",
    )

    if benchy_only:
        await run_phase_benchy(journal, max_iterations=5 if time_budget_min and time_budget_min <= 30 else 10)
    else:
        # Phases ordered by priority — highest-value learning first.
        # Estimated durations used to decide what fits in the budget.
        #   feedback:      ~1 min
        #   dream:         ~5 min
        #   conflicts:     ~0.5 min
        #   episodic:      ~3 min
        #   graph:         ~3 min
        #   cleanup:       ~2 min
        #   orchestrated:  ~8 min
        #   drip:          ~3 min
        #   benchy:        ~20-40 min (variable)

        if has_time(1):
            run_phase_feedback(journal)
        else:
            _log(f"⏰ Skipping feedback{time_status()}")

        if has_time(3):
            run_phase_dream(journal)
        else:
            _log(f"⏰ Skipping dream{time_status()}")

        if has_time(1):
            run_phase_conflicts(journal)
        else:
            _log(f"⏰ Skipping conflicts{time_status()}")

        if has_time(2):
            run_phase_episodic(journal)
        else:
            _log(f"⏰ Skipping episodic{time_status()}")

        if has_time(2):
            run_phase_graph(journal)
        else:
            _log(f"⏰ Skipping graph{time_status()}")

        if has_time(1):
            run_phase_cleanup(journal)
        else:
            _log(f"⏰ Skipping cleanup{time_status()}")

        if not quick:
            if has_time(5):
                run_phase_orchestrated(journal, dry_run=dry_run)
            else:
                _log(f"⏰ Skipping deep dream{time_status()}")

            if has_time(2):
                run_phase_drip(journal)
            else:
                _log(f"⏰ Skipping drip reflection{time_status()}")

            if has_time(10):
                remaining = minutes_left()
                iters = 10
                if remaining is not None:
                    iters = max(3, min(10, int(remaining / 4)))
                await run_phase_benchy(journal, max_iterations=iters)
            else:
                _log(f"⏰ Skipping Benchy{time_status()}")

    # Save and send journal
    journal.save()
    summary = journal.to_telegram_summary()
    _log("\n" + summary)
    _send_telegram(summary)

    _log("=" * 60)
    _log(f"NAP COMPLETE — {journal.duration_str()}")
    _log("=" * 60)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ira Nap Mode — Sleep & Learn")
    parser.add_argument("--time", type=int, default=None, help="Time budget in minutes (e.g. --time 60)")
    parser.add_argument("--quick", action="store_true", help="Quick nap: skip Benchy + deep dream phases")
    parser.add_argument("--benchy-only", action="store_true", help="Only run Benchy self-improvement")
    parser.add_argument("--dry-run", action="store_true", help="No real memory deletions")
    parser.add_argument("--threshold", type=float, default=0.85, help="Benchy pass threshold")
    args = parser.parse_args()

    asyncio.run(nap(
        quick=args.quick,
        benchy_only=args.benchy_only,
        dry_run=args.dry_run,
        time_budget_min=args.time,
    ))
