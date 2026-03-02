#!/usr/bin/env python3
"""
DAILY RHYTHM - The Breathing Cycle That Synchronizes All Systems
=================================================================

This is the orchestrator that runs the daily inhale/exhale cycle:

    MORNING (Inhale - Gather & Prepare):
        1. Record heartbeat
        2. Collect vital signs
        3. Run immune sweep (check chronic issues)
        4. Apply endocrine inactivity decay
        5. Send morning summary to Telegram

    EVENING (Exhale - Consolidate & Clean):
        1. Run metabolic cleanup cycle
        2. Extract myokines from action log
        3. Record dream mode start
        4. (Dream mode runs separately via run_nightly_dream.sh)
        5. Record dream mode completion

    PER-REQUEST (Single Breath):
        1. Record breath timing
        2. Process any validation warnings through immune system
        3. Record sensory perception
        4. Record action if applicable
        5. Signal endocrine system with outcome

Usage:
    # Morning cycle (run from cron or startup)
    python -m holistic.daily_rhythm --morning

    # Evening cycle (run before dream mode)
    python -m holistic.daily_rhythm --evening

    # Vital signs check
    python -m holistic.daily_rhythm --vitals
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("ira.daily_rhythm")

HOLISTIC_DIR = Path(__file__).parent
SRC_DIR = HOLISTIC_DIR.parent
PROJECT_ROOT = SRC_DIR.parent.parent.parent.parent


def run_morning_cycle() -> Dict:
    """
    Morning inhale: gather information, assess health, prepare for the day.
    """
    logger.info("[RHYTHM] Starting morning cycle (inhale)")
    results = {"timestamp": datetime.now().isoformat(), "phase": "morning"}

    # 1. Heartbeat
    try:
        from openclaw.agents.ira.src.holistic.respiratory_system import get_respiratory_system
        resp = get_respiratory_system()
        hb = resp.record_heartbeat()
        results["heartbeat"] = hb
        logger.info(f"[RHYTHM] Heartbeat recorded (gap={hb.get('gap_detected', False)})")
    except Exception as e:
        results["heartbeat_error"] = str(e)
        logger.error(f"[RHYTHM] Heartbeat failed: {e}")

    # 2. Vital signs
    try:
        from openclaw.agents.ira.src.holistic.vital_signs import collect_vital_signs
        vitals = collect_vital_signs()
        results["vitals"] = {
            "overall_health": vitals["overall_health"],
            "overall_score": vitals["overall_score"],
            "alerts": vitals.get("alerts", []),
            "recommendations": vitals.get("recommendations", []),
        }
        logger.info(f"[RHYTHM] Vitals: {vitals['overall_health']} ({vitals['overall_score']:.0%})")
    except Exception as e:
        results["vitals_error"] = str(e)
        logger.error(f"[RHYTHM] Vitals collection failed: {e}")

    # 3. Immune sweep
    try:
        from openclaw.agents.ira.src.holistic.immune_system import get_immune_system
        immune = get_immune_system()
        sweep = immune.run_sweep()
        results["immune_sweep"] = sweep
        logger.info(f"[RHYTHM] Immune sweep: {len(sweep.get('remediated', []))} remediated")

        from openclaw.agents.ira.src.holistic.respiratory_system import get_respiratory_system
        get_respiratory_system().record_system_event("immune_sweep")
    except Exception as e:
        results["immune_sweep_error"] = str(e)
        logger.error(f"[RHYTHM] Immune sweep failed: {e}")

    # 4. Endocrine decay
    try:
        from openclaw.agents.ira.src.holistic.endocrine_system import get_endocrine_system
        endo = get_endocrine_system()
        decayed = endo.apply_inactivity_decay()
        results["endocrine_decay"] = decayed
        if decayed:
            logger.info(f"[RHYTHM] Endocrine decay: {decayed}")
    except Exception as e:
        results["endocrine_decay_error"] = str(e)
        logger.error(f"[RHYTHM] Endocrine decay failed: {e}")

    # 5. Morning summary
    try:
        _send_morning_summary(results)
        results["morning_summary_sent"] = True

        from openclaw.agents.ira.src.holistic.respiratory_system import get_respiratory_system
        get_respiratory_system().record_morning_summary()
    except Exception as e:
        results["morning_summary_error"] = str(e)
        logger.error(f"[RHYTHM] Morning summary failed: {e}")

    logger.info("[RHYTHM] Morning cycle complete")
    return results


def run_evening_cycle() -> Dict:
    """
    Evening exhale: clean up, consolidate, prepare for dream mode.
    """
    logger.info("[RHYTHM] Starting evening cycle (exhale)")
    results = {"timestamp": datetime.now().isoformat(), "phase": "evening"}

    # 1. Metabolic cleanup
    try:
        from openclaw.agents.ira.src.holistic.metabolic_system import get_metabolic_system
        metabolic = get_metabolic_system()
        cleanup = metabolic.run_cleanup_cycle()
        results["metabolic_cleanup"] = {
            op: {
                "scanned": r.items_scanned,
                "cleaned": r.items_cleaned,
                "details": r.details,
            }
            for op, r in cleanup.items()
        }

        from openclaw.agents.ira.src.holistic.respiratory_system import get_respiratory_system
        get_respiratory_system().record_system_event("metabolic_cleanup")
        logger.info("[RHYTHM] Metabolic cleanup complete")
    except Exception as e:
        results["metabolic_cleanup_error"] = str(e)
        logger.error(f"[RHYTHM] Metabolic cleanup failed: {e}")

    # 2. Extract myokines for dream mode
    try:
        from openclaw.agents.ira.src.holistic.musculoskeletal_system import get_musculoskeletal_system
        musculo = get_musculoskeletal_system()
        myokines = musculo.get_unprocessed_myokines(limit=50)
        results["myokines_for_dream"] = len(myokines)
        logger.info(f"[RHYTHM] {len(myokines)} myokines ready for dream mode")
    except Exception as e:
        results["myokines_error"] = str(e)

    # 3. Final heartbeat before dream
    try:
        from openclaw.agents.ira.src.holistic.respiratory_system import get_respiratory_system
        resp = get_respiratory_system()
        resp.record_heartbeat()
    except Exception:
        pass

    logger.info("[RHYTHM] Evening cycle complete -- ready for dream mode")
    return results


def process_request_breath(
    request_id: str,
    total_latency_ms: float,
    phase_timings: Optional[Dict[str, float]] = None,
    success: bool = True,
    channel: str = "unknown",
    query: Optional[str] = None,
    response: Optional[str] = None,
    warnings: Optional[list] = None,
    contact_id: Optional[str] = None,
):
    """
    Process a single request/response cycle through all body systems.
    This is the per-request integration point.
    """
    # Respiratory: record the breath
    try:
        from openclaw.agents.ira.src.holistic.respiratory_system import get_respiratory_system
        resp = get_respiratory_system()
        resp.record_breath(request_id, total_latency_ms, phase_timings, success, channel)
    except Exception:
        pass

    # Immune: process any validation warnings
    if warnings:
        try:
            from openclaw.agents.ira.src.holistic.immune_system import get_immune_system
            immune = get_immune_system()
            action = immune.process_validation_issue(query or "", response or "", warnings)
            if action.blocked:
                logger.warning(f"[RHYTHM] Immune system blocked response for {request_id}")
        except Exception:
            pass

    # Sensory: record the perception
    if contact_id and query:
        try:
            from openclaw.agents.ira.src.holistic.sensory_system import get_sensory_integrator
            sensory = get_sensory_integrator()
            sensory.record_perception(
                channel=channel,
                contact_id=contact_id,
                content_summary=query[:500],
            )
        except Exception:
            pass


def _send_morning_summary(results: Dict):
    """Send morning summary via Telegram."""
    try:
        from openclaw.agents.ira.src.brain.error_monitor import TELEGRAM_BOT_TOKEN, EXPECTED_CHAT_ID
        if not TELEGRAM_BOT_TOKEN or not EXPECTED_CHAT_ID:
            logger.info("[RHYTHM] Telegram not configured, skipping morning summary")
            return

        import requests as http_requests

        vitals = results.get("vitals", {})
        health = vitals.get("overall_health", "unknown")
        score = vitals.get("overall_score", 0)

        health_emoji = {
            "healthy": "💚", "fair": "💛",
            "needs_attention": "🟠", "critical": "🔴",
        }

        lines = [
            f"{health_emoji.get(health, '⚪')} *Good morning, Rushabh!*",
            f"Ira's health: *{health.upper()}* ({score:.0%})",
            "",
        ]

        alerts = vitals.get("alerts", [])
        if alerts:
            lines.append("*Alerts:*")
            for a in alerts[:3]:
                lines.append(f"  ⚠️ {a}")
            lines.append("")

        sweep = results.get("immune_sweep", {})
        remediated = sweep.get("remediated", [])
        if remediated:
            lines.append(f"🛡 Auto-remediated: {', '.join(remediated)}")

        recs = vitals.get("recommendations", [])
        if recs:
            lines.append("")
            lines.append("*Today's focus:*")
            for r in recs[:3]:
                lines.append(f"  💡 {r}")

        lines.append("")
        lines.append("_Use /vitals for full report_")

        message = "\n".join(lines)

        http_requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": EXPECTED_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
        logger.info("[RHYTHM] Morning summary sent to Telegram")

    except Exception as e:
        logger.error(f"[RHYTHM] Failed to send morning summary: {e}")


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Ira Daily Rhythm")
    parser.add_argument("--morning", action="store_true", help="Run morning cycle")
    parser.add_argument("--evening", action="store_true", help="Run evening cycle")
    parser.add_argument("--vitals", action="store_true", help="Collect and display vital signs")
    parser.add_argument("--heartbeat", action="store_true", help="Record a single heartbeat")

    args = parser.parse_args()

    if args.morning:
        results = run_morning_cycle()
        print(json.dumps(results, indent=2, default=str))

    elif args.evening:
        results = run_evening_cycle()
        print(json.dumps(results, indent=2, default=str))

    elif args.vitals:
        from openclaw.agents.ira.src.holistic.vital_signs import (
            collect_vital_signs,
            format_vitals_telegram,
        )
        vitals = collect_vital_signs()
        print(format_vitals_telegram(vitals))

    elif args.heartbeat:
        from openclaw.agents.ira.src.holistic.respiratory_system import get_respiratory_system
        resp = get_respiratory_system()
        hb = resp.record_heartbeat()
        print(f"Heartbeat recorded: {json.dumps(hb)}")

    else:
        parser.print_help()
