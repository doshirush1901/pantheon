#!/usr/bin/env python3
"""
DRIP DREAM REFLECTION
=====================

Ira's nightly dream reflection for drip campaigns. This runs during
the dream cycle (2 AM) and does the deep thinking that can't happen
during the busy sending day.

What happens in Ira's dreams:
    1. Review today's batch — what was sent, who replied, who didn't
    2. Deep self-evaluation — score herself honestly
    3. Pattern analysis — what's working across all batches
    4. Generate hypotheses — WHY aren't they replying?
    5. Creative ideation — new approaches, subject lines, angles
    6. Strategy evolution — update the active strategy for tomorrow
    7. Dream journal — record insights for long-term learning

The output is stored in drip_dream_ideas.json and drip_strategies.json,
which the autonomous_drip_engine reads the next morning to apply
new ideas to the next batch.

This is how Ira improves exponentially — each night she reflects,
each morning she applies, each evening she measures.

Usage:
    # Called from run_nightly_dream.sh
    python -m openclaw.agents.ira.src.sales.drip_dream_reflection

    # Or directly
    from drip_dream_reflection import run_drip_dream
    insights = run_drip_dream(verbose=True)
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("ira.drip_dream")

SKILL_DIR = Path(__file__).parent
SKILLS_DIR = SKILL_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(SKILL_DIR))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

DREAM_IDEAS_FILE = PROJECT_ROOT / "data" / "drip_dream_ideas.json"
DREAM_JOURNAL_FILE = PROJECT_ROOT / "data" / "drip_dream_journal.jsonl"
STRATEGY_FILE = PROJECT_ROOT / "data" / "drip_strategies.json"
SELF_EVAL_FILE = PROJECT_ROOT / "data" / "drip_self_evaluation.json"
BATCH_HISTORY_FILE = PROJECT_ROOT / "data" / "drip_batch_history.jsonl"

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def run_drip_dream(verbose: bool = False) -> Dict[str, Any]:
    """
    Run Ira's nightly drip campaign dream reflection.

    Returns a dict with insights, new ideas, and updated strategy.
    """
    logger.info("=" * 60)
    logger.info("DRIP DREAM REFLECTION — Ira is dreaming about sales...")
    logger.info("=" * 60)

    results = {
        "timestamp": datetime.now().isoformat(),
        "phases_completed": [],
        "ideas_generated": 0,
        "strategy_updated": False,
        "journal_entry": "",
    }

    # Phase 1: Check replies from today
    logger.info("\n[DREAM PHASE 1] Checking today's replies...")
    reply_data = _check_todays_replies()
    results["reply_check"] = reply_data
    results["phases_completed"].append("reply_check")
    if verbose:
        logger.info(f"  New replies: {reply_data.get('new_replies', 0)}")

    # Phase 2: Run self-evaluation
    logger.info("\n[DREAM PHASE 2] Self-evaluation...")
    eval_report = _run_self_evaluation()
    results["self_evaluation"] = {
        "score": eval_report.get("self_score", 0),
        "reply_rate": eval_report.get("reply_rate", 0),
        "total_sent": eval_report.get("total_sent", 0),
    }
    results["phases_completed"].append("self_evaluation")
    if verbose:
        logger.info(f"  Score: {eval_report.get('self_score', 0)}/100")
        logger.info(f"  Reply rate: {eval_report.get('reply_rate', 0):.1%}")

    # Phase 3: Deep reflection — the creative part
    logger.info("\n[DREAM PHASE 3] Deep reflection — generating new ideas...")
    ideas = _dream_generate_ideas(eval_report)
    results["ideas_generated"] = len(ideas)
    results["phases_completed"].append("idea_generation")
    if verbose:
        for idea in ideas[:3]:
            logger.info(f"  Idea: {idea.get('idea', '')[:80]}...")

    # Phase 4: Strategy evolution
    logger.info("\n[DREAM PHASE 4] Evolving strategy for tomorrow...")
    strategy_updated = _evolve_strategy(eval_report, ideas)
    results["strategy_updated"] = strategy_updated
    results["phases_completed"].append("strategy_evolution")

    # Phase 5: Dream journal entry
    logger.info("\n[DREAM PHASE 5] Writing dream journal...")
    journal_entry = _write_dream_journal(eval_report, ideas, reply_data)
    results["journal_entry"] = journal_entry
    results["phases_completed"].append("dream_journal")

    # Phase 6: Notify via Telegram (morning summary queued)
    logger.info("\n[DREAM PHASE 6] Queuing morning summary...")
    _queue_morning_summary(eval_report, ideas)
    results["phases_completed"].append("morning_summary_queued")

    logger.info("\n" + "=" * 60)
    logger.info(f"DRIP DREAM COMPLETE — {len(ideas)} new ideas, strategy {'updated' if strategy_updated else 'unchanged'}")
    logger.info("=" * 60)

    return results


def _check_todays_replies() -> Dict[str, Any]:
    """Check for new replies using the autonomous engine."""
    try:
        from autonomous_drip_engine import get_engine
        engine = get_engine()
        return engine.check_replies()
    except Exception as e:
        logger.warning(f"Reply check failed: {e}")
        return {"error": str(e), "new_replies": 0}


def _run_self_evaluation() -> Dict[str, Any]:
    """Run self-evaluation using the evaluator."""
    try:
        from campaign_self_evaluator import CampaignSelfEvaluator
        evaluator = CampaignSelfEvaluator()
        report = evaluator.full_evaluation(period_days=30)
        return report.to_dict()
    except Exception as e:
        logger.warning(f"Self-evaluation failed: {e}")
        return {"error": str(e), "self_score": 0, "reply_rate": 0}


def _dream_generate_ideas(eval_report: Dict) -> List[Dict]:
    """
    The creative dreaming phase.

    Ira thinks deeply about her performance and generates new ideas.
    This is where the "quantum leap" improvement happens — she doesn't
    just iterate, she reimagines.
    """
    ideas = []

    if not OPENAI_AVAILABLE:
        return _generate_fallback_ideas(eval_report)

    score = eval_report.get("self_score", 0)
    reply_rate = eval_report.get("reply_rate", 0)
    what_went_wrong = eval_report.get("what_went_wrong", [])
    what_went_right = eval_report.get("what_went_right", [])
    hypotheses = eval_report.get("hypotheses", [])
    replied_companies = eval_report.get("replied_companies", [])
    silent_companies = eval_report.get("silent_companies", [])

    try:
        client = openai.OpenAI()
        result = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": (
                    "You are Ira, an AI sales agent for Machinecraft Technologies. "
                    "It's 2 AM and you're in your dream reflection cycle. You're "
                    "thinking deeply about your drip email campaigns.\n\n"
                    "You need to generate CREATIVE, SPECIFIC ideas for improving "
                    "your emails tomorrow. Think like a combination of:\n"
                    "- A growth hacker who obsesses over reply rates\n"
                    "- A B2B sales expert who understands European manufacturing\n"
                    "- A copywriter who knows how to write compelling cold emails\n"
                    "- A psychologist who understands what makes people respond\n\n"
                    "Generate 5-8 specific, actionable ideas. Each idea should be "
                    "something you can implement TOMORROW in your next batch.\n\n"
                    "Output as JSON: {\"ideas\": [{\"idea\": \"...\", \"category\": "
                    "\"subject_line|opening|value_prop|cta|timing|personalization|format\", "
                    "\"expected_impact\": \"high|medium|low\", \"reasoning\": \"...\"}]}"
                )},
                {"role": "user", "content": (
                    f"MY CURRENT PERFORMANCE:\n"
                    f"Score: {score}/100\n"
                    f"Reply rate: {reply_rate:.1%}\n"
                    f"Total sent: {eval_report.get('total_sent', 0)}\n"
                    f"Engaged replies: {eval_report.get('engaged_replies', 0)}\n\n"
                    f"WHAT WENT WRONG:\n"
                    + "\n".join(f"- {w}" for w in what_went_wrong[:5])
                    + f"\n\nWHAT WENT RIGHT:\n"
                    + "\n".join(f"- {w}" for w in what_went_right[:5])
                    + f"\n\nMY HYPOTHESES:\n"
                    + "\n".join(f"- {h}" for h in hypotheses[:5])
                    + f"\n\nCOMPANIES THAT REPLIED: {', '.join(replied_companies[:10])}"
                    + f"\n\nCOMPANIES THAT STAYED SILENT: {', '.join(silent_companies[:10])}"
                    + "\n\nDream deeply. What should I try tomorrow?"
                )},
            ],
            temperature=0.9,  # Higher creativity for dream mode
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        content = result.choices[0].message.content
        data = json.loads(content)
        raw_ideas = data.get("ideas", [])

        for idea_data in raw_ideas:
            ideas.append({
                "idea": idea_data.get("idea", ""),
                "category": idea_data.get("category", "general"),
                "expected_impact": idea_data.get("expected_impact", "medium"),
                "reasoning": idea_data.get("reasoning", ""),
                "generated_at": datetime.now().isoformat(),
                "source": "dream_reflection",
                "status": "active",
                "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
            })

    except Exception as e:
        logger.warning(f"LLM dream ideation failed: {e}")
        ideas = _generate_fallback_ideas(eval_report)

    # Save ideas
    DREAM_IDEAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DREAM_IDEAS_FILE.write_text(json.dumps(ideas, indent=2))

    return ideas


def _generate_fallback_ideas(eval_report: Dict) -> List[Dict]:
    """Generate ideas without LLM."""
    reply_rate = eval_report.get("reply_rate", 0)
    ideas = []

    if reply_rate < 0.05:
        ideas.extend([
            {
                "idea": "Try the 'curious question' approach: subject line is a genuine "
                        "question about their operation, body is 2-3 sentences max",
                "category": "format",
                "expected_impact": "high",
                "reasoning": "Short emails with questions have higher reply rates in B2B",
            },
            {
                "idea": "Research each lead's LinkedIn for recent posts or job changes, "
                        "reference something specific they shared",
                "category": "personalization",
                "expected_impact": "high",
                "reasoning": "Shows genuine interest, not mass mailing",
            },
            {
                "idea": "Try sending on Tuesday or Wednesday at 10 AM local time "
                        "instead of the current schedule",
                "category": "timing",
                "expected_impact": "medium",
                "reasoning": "Mid-week mornings are peak email engagement times",
            },
        ])
    else:
        ideas.extend([
            {
                "idea": "Double down on what's working — analyze the emails that got "
                        "replies and use the same structure for the next batch",
                "category": "format",
                "expected_impact": "high",
                "reasoning": "Replicate success patterns",
            },
            {
                "idea": "For companies that replied, ask for a referral to similar "
                        "companies in their network",
                "category": "value_prop",
                "expected_impact": "medium",
                "reasoning": "Warm introductions convert 5x better than cold outreach",
            },
        ])

    now = datetime.now()
    for idea in ideas:
        idea["generated_at"] = now.isoformat()
        idea["source"] = "dream_reflection_fallback"
        idea["status"] = "active"
        idea["expires_at"] = (now + timedelta(days=7)).isoformat()

    DREAM_IDEAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DREAM_IDEAS_FILE.write_text(json.dumps(ideas, indent=2))

    return ideas


def _evolve_strategy(eval_report: Dict, ideas: List[Dict]) -> bool:
    """
    Evolve the active strategy based on evaluation and new ideas.

    If the current strategy is underperforming, switch to a new one.
    If it's working, refine it with new ideas.
    """
    try:
        from campaign_self_evaluator import CampaignSelfEvaluator
        evaluator = CampaignSelfEvaluator()
        trend = evaluator.get_trend()
    except Exception:
        trend = {"trend": "unknown"}

    current_strategies = {}
    if STRATEGY_FILE.exists():
        try:
            current_strategies = json.loads(STRATEGY_FILE.read_text())
        except Exception:
            pass

    score = eval_report.get("self_score", 0)

    # If score is below 30, generate completely new strategies
    if score < 30:
        logger.info("  Score below 30 — generating new strategies from scratch")
        try:
            from campaign_self_evaluator import CampaignSelfEvaluator, EvaluationReport
            evaluator = CampaignSelfEvaluator()
            # Convert dict back to report for strategy generation
            report = EvaluationReport(**{
                k: v for k, v in eval_report.items()
                if k in EvaluationReport.__dataclass_fields__
            })
            evaluator.generate_new_strategies(report)
            return True
        except Exception as e:
            logger.warning(f"Strategy regeneration failed: {e}")

    # If trend is declining, also regenerate
    if trend.get("trend") == "declining":
        logger.info("  Performance declining — evolving strategy")
        try:
            from campaign_self_evaluator import CampaignSelfEvaluator
            evaluator = CampaignSelfEvaluator()
            evaluator.generate_new_strategies()
            return True
        except Exception:
            pass

    # Otherwise, inject dream ideas into current strategy
    if ideas:
        high_impact = [i for i in ideas if i.get("expected_impact") == "high"]
        if high_impact:
            current_strategies["dream_ideas_applied"] = [
                i["idea"] for i in high_impact[:3]
            ]
            current_strategies["last_dream_update"] = datetime.now().isoformat()
            STRATEGY_FILE.parent.mkdir(parents=True, exist_ok=True)
            STRATEGY_FILE.write_text(json.dumps(current_strategies, indent=2))
            return True

    return False


def _write_dream_journal(
    eval_report: Dict, ideas: List[Dict], reply_data: Dict
) -> str:
    """Write a dream journal entry — Ira's personal reflection log."""
    score = eval_report.get("self_score", 0)
    reply_rate = eval_report.get("reply_rate", 0)
    new_replies = reply_data.get("new_replies", 0)

    # Build journal entry
    entry_parts = [
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Score: {score}/100 | Reply rate: {reply_rate:.1%}",
        "",
    ]

    if new_replies > 0:
        entry_parts.append(f"Got {new_replies} new replies today. That feels good.")
    elif eval_report.get("total_sent", 0) > 0:
        entry_parts.append("No new replies today. I need to think about why.")

    # What I learned
    wrongs = eval_report.get("what_went_wrong", [])
    if wrongs:
        entry_parts.append("\nWhat I need to fix:")
        for w in wrongs[:3]:
            entry_parts.append(f"  - {w[:100]}")

    rights = eval_report.get("what_went_right", [])
    if rights:
        entry_parts.append("\nWhat's working:")
        for r in rights[:3]:
            entry_parts.append(f"  - {r[:100]}")

    # New ideas for tomorrow
    if ideas:
        entry_parts.append(f"\nNew ideas for tomorrow ({len(ideas)} total):")
        for idea in ideas[:3]:
            entry_parts.append(f"  - [{idea.get('category', '?')}] {idea.get('idea', '')[:80]}")

    entry_text = "\n".join(entry_parts)

    # Append to journal
    DREAM_JOURNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DREAM_JOURNAL_FILE, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "entry": entry_text,
            "score": score,
            "reply_rate": reply_rate,
            "ideas_count": len(ideas),
        }) + "\n")

    return entry_text


def _queue_morning_summary(eval_report: Dict, ideas: List[Dict]):
    """
    Queue a morning summary to send to Rushabh via Telegram
    when Ira 'wakes up'.
    """
    score = eval_report.get("self_score", 0)
    reply_rate = eval_report.get("reply_rate", 0)
    total_sent = eval_report.get("total_sent", 0)
    engaged = eval_report.get("engaged_replies", 0)

    summary = {
        "type": "drip_morning_summary",
        "timestamp": datetime.now().isoformat(),
        "score": score,
        "reply_rate": reply_rate,
        "total_sent": total_sent,
        "engaged": engaged,
        "new_ideas": len(ideas),
        "top_ideas": [i.get("idea", "")[:100] for i in ideas[:3]],
    }

    morning_file = PROJECT_ROOT / "data" / "drip_morning_summary.json"
    morning_file.parent.mkdir(parents=True, exist_ok=True)
    morning_file.write_text(json.dumps(summary, indent=2))


# Direct execution
if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(description="Ira Drip Dream Reflection")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--journal", action="store_true", help="Show dream journal")
    args = parser.parse_args()

    if args.journal:
        if DREAM_JOURNAL_FILE.exists():
            for line in DREAM_JOURNAL_FILE.read_text().strip().split("\n")[-5:]:
                if line.strip():
                    entry = json.loads(line)
                    print(entry.get("entry", ""))
                    print("-" * 40)
        else:
            print("No dream journal entries yet.")
    else:
        results = run_drip_dream(verbose=args.verbose or True)
        print(f"\nDream complete:")
        print(f"  Phases: {', '.join(results['phases_completed'])}")
        print(f"  Ideas generated: {results['ideas_generated']}")
        print(f"  Strategy updated: {results['strategy_updated']}")
        if results.get("journal_entry"):
            print(f"\nJournal entry:\n{results['journal_entry']}")
