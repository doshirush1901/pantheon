#!/usr/bin/env python3
"""
VITAL SIGNS - Unified Health Dashboard for All Body Systems
=============================================================

This is the "doctor's checkup" -- a single function that collects
health metrics from all six body systems and produces a unified
report. Think of it as Ira's annual physical.

Can be called:
    - On demand via Telegram command (/vitals)
    - Daily by the respiratory system's morning summary
    - By dream mode as part of the nightly consolidation

Usage:
    from holistic.vital_signs import collect_vital_signs

    report = collect_vital_signs()
    print(report["overall_health"])  # "healthy", "needs_attention", "critical"
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("ira.vital_signs")

HOLISTIC_DIR = Path(__file__).parent
PROJECT_ROOT = HOLISTIC_DIR.parent.parent.parent.parent

VITALS_LOG = PROJECT_ROOT / "data" / "holistic" / "vitals_log.jsonl"


@dataclass
class VitalSigns:
    """Complete vital signs snapshot."""
    timestamp: str
    overall_health: str
    overall_score: float
    immune: Dict
    respiratory: Dict
    endocrine: Dict
    musculoskeletal: Dict
    sensory: Dict
    metabolic: Dict
    alerts: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


def collect_vital_signs() -> Dict:
    """
    Collect vital signs from all six body systems.
    Returns a comprehensive health report.
    """
    timestamp = datetime.now().isoformat()
    alerts = []
    recommendations = []
    system_scores = {}

    # --- IMMUNE SYSTEM ---
    try:
        from openclaw.agents.ira.src.holistic.immune_system import get_immune_system
        immune = get_immune_system()
        immune_report = immune.get_inflammation_report()

        if immune_report["inflammation_level"] == "critical":
            system_scores["immune"] = 0.2
            alerts.append(f"IMMUNE: Critical inflammation - {immune_report['critical_issues']}")
        elif immune_report["inflammation_level"] == "elevated":
            system_scores["immune"] = 0.5
            alerts.append(f"IMMUNE: Elevated inflammation - {immune_report['warning_issues']}")
        elif immune_report["inflammation_level"] == "moderate":
            system_scores["immune"] = 0.7
        else:
            system_scores["immune"] = 1.0
    except Exception as e:
        immune_report = {"error": str(e)}
        system_scores["immune"] = 0.5
        logger.warning(f"[VITALS] Immune system check failed: {e}")

    # --- RESPIRATORY SYSTEM ---
    try:
        from openclaw.agents.ira.src.holistic.respiratory_system import get_respiratory_system
        respiratory = get_respiratory_system()
        respiratory_report = respiratory.get_rhythm_report()
        arrhythmias = respiratory.check_arrhythmia()

        if arrhythmias:
            system_scores["respiratory"] = max(0.3, 1.0 - len(arrhythmias) * 0.2)
            for issue in arrhythmias:
                alerts.append(f"RESPIRATORY: {issue}")
        else:
            system_scores["respiratory"] = 1.0

        hrv = respiratory_report.get("hrv", {})
        if hrv.get("status") == "unstable":
            recommendations.append("Response latencies are unstable - check for bottlenecks")
    except Exception as e:
        respiratory_report = {"error": str(e)}
        system_scores["respiratory"] = 0.5
        logger.warning(f"[VITALS] Respiratory system check failed: {e}")

    # --- ENDOCRINE SYSTEM ---
    try:
        from openclaw.agents.ira.src.holistic.endocrine_system import get_endocrine_system
        endocrine = get_endocrine_system()
        endocrine_report = endocrine.get_endocrine_report()

        stressed = endocrine_report.get("stressed_agents", [])
        if len(stressed) >= 3:
            system_scores["endocrine"] = 0.3
            alerts.append(f"ENDOCRINE: Multiple agents chronically stressed: {stressed}")
        elif stressed:
            system_scores["endocrine"] = 0.6
            recommendations.append(f"Agents under stress: {stressed}")
        else:
            system_scores["endocrine"] = 1.0

        for name, profile in endocrine_report.get("profiles", {}).items():
            if profile.get("total_invocations", 0) == 0:
                recommendations.append(f"Agent '{name}' has never been invoked - activate it")
    except Exception as e:
        endocrine_report = {"error": str(e)}
        system_scores["endocrine"] = 0.5
        logger.warning(f"[VITALS] Endocrine system check failed: {e}")

    # --- MUSCULOSKELETAL SYSTEM ---
    try:
        from openclaw.agents.ira.src.holistic.musculoskeletal_system import get_musculoskeletal_system
        musculo = get_musculoskeletal_system()
        musculo_report = musculo.get_exercise_report()

        atrophied = musculo_report.get("atrophied_groups", [])
        if atrophied:
            system_scores["musculoskeletal"] = max(0.3, 1.0 - len(atrophied) * 0.15)
            recommendations.append(f"Atrophied muscle groups (need exercise): {atrophied}")
        elif musculo_report.get("total_actions", 0) == 0:
            system_scores["musculoskeletal"] = 0.4
            recommendations.append("No actions recorded yet - Ira needs to start doing things")
        else:
            system_scores["musculoskeletal"] = 0.8
    except Exception as e:
        musculo_report = {"error": str(e)}
        system_scores["musculoskeletal"] = 0.5
        logger.warning(f"[VITALS] Musculoskeletal system check failed: {e}")

    # --- SENSORY SYSTEM ---
    try:
        from openclaw.agents.ira.src.holistic.sensory_system import get_sensory_integrator
        sensory = get_sensory_integrator()
        sensory_report = sensory.get_sensory_report()

        richness = sensory_report.get("sensory_richness", "blind")
        if richness == "blind":
            system_scores["sensory"] = 0.1
            alerts.append("SENSORY: No active channels - Ira is blind")
        elif richness == "monocular":
            system_scores["sensory"] = 0.5
            recommendations.append("Only one channel active - activate more senses")
        elif richness == "moderate":
            system_scores["sensory"] = 0.7
        else:
            system_scores["sensory"] = 1.0

        dormant = sensory_report.get("dormant_channels", [])
        if dormant:
            recommendations.append(f"Dormant channels (never used): {dormant}")
    except Exception as e:
        sensory_report = {"error": str(e)}
        system_scores["sensory"] = 0.5
        logger.warning(f"[VITALS] Sensory system check failed: {e}")

    # --- METABOLIC SYSTEM ---
    try:
        from openclaw.agents.ira.src.holistic.metabolic_system import get_metabolic_system
        metabolic = get_metabolic_system()
        metabolic_report = metabolic.get_metabolic_report()

        if metabolic_report.get("cleanup_overdue"):
            system_scores["metabolic"] = 0.4
            recommendations.append("Knowledge cleanup is overdue - run metabolic cycle")
        elif metabolic_report.get("health") == "needs_attention":
            system_scores["metabolic"] = 0.6
        else:
            system_scores["metabolic"] = 0.8
    except Exception as e:
        metabolic_report = {"error": str(e)}
        system_scores["metabolic"] = 0.5
        logger.warning(f"[VITALS] Metabolic system check failed: {e}")

    # --- OVERALL ASSESSMENT ---
    avg_score = sum(system_scores.values()) / max(len(system_scores), 1)
    min_score = min(system_scores.values()) if system_scores else 0

    if min_score < 0.3 or avg_score < 0.4:
        overall_health = "critical"
    elif min_score < 0.5 or avg_score < 0.6:
        overall_health = "needs_attention"
    elif avg_score < 0.8:
        overall_health = "fair"
    else:
        overall_health = "healthy"

    report = {
        "timestamp": timestamp,
        "overall_health": overall_health,
        "overall_score": round(avg_score, 3),
        "system_scores": {k: round(v, 3) for k, v in system_scores.items()},
        "immune": immune_report,
        "respiratory": respiratory_report,
        "endocrine": endocrine_report,
        "musculoskeletal": musculo_report,
        "sensory": sensory_report,
        "metabolic": metabolic_report,
        "alerts": alerts,
        "recommendations": recommendations,
    }

    _persist_vitals(report)

    return report


def format_vitals_telegram(report: Dict) -> str:
    """Format vital signs for Telegram display."""
    health_emoji = {
        "healthy": "💚",
        "fair": "💛",
        "needs_attention": "🟠",
        "critical": "🔴",
    }

    score_bar = lambda s: "█" * int(s * 10) + "░" * (10 - int(s * 10))

    lines = [
        f"{health_emoji.get(report['overall_health'], '⚪')} *IRA VITAL SIGNS*",
        f"Overall: {report['overall_health'].upper()} ({report['overall_score']:.0%})",
        "",
        "*System Scores:*",
    ]

    system_names = {
        "immune": "🛡 Immune",
        "respiratory": "🫁 Respiratory",
        "endocrine": "⚗️ Endocrine",
        "musculoskeletal": "💪 Musculoskeletal",
        "sensory": "👁 Sensory",
        "metabolic": "🔄 Metabolic",
    }

    for key, name in system_names.items():
        score = report.get("system_scores", {}).get(key, 0)
        lines.append(f"  {name}: `{score_bar(score)}` {score:.0%}")

    if report.get("alerts"):
        lines.append("")
        lines.append("*⚠️ Alerts:*")
        for alert in report["alerts"][:5]:
            lines.append(f"  • {alert}")

    if report.get("recommendations"):
        lines.append("")
        lines.append("*💡 Recommendations:*")
        for rec in report["recommendations"][:5]:
            lines.append(f"  • {rec}")

    resp_report = report.get("respiratory", {})
    hrv = resp_report.get("hrv", {})
    if hrv.get("mean_latency_ms"):
        lines.append("")
        lines.append("*📊 Pipeline Health:*")
        lines.append(f"  Avg latency: {hrv['mean_latency_ms']:.0f}ms")
        lines.append(f"  HRV: {hrv.get('hrv', 'N/A')} ({hrv.get('status', 'N/A')})")

    endo_report = report.get("endocrine", {})
    if endo_report.get("profiles"):
        lines.append("")
        lines.append("*🧪 Agent Confidence:*")
        for name, profile in sorted(
            endo_report["profiles"].items(),
            key=lambda x: -x[1].get("effective_confidence", 0),
        ):
            conf = profile.get("effective_confidence", 0)
            stress_marker = " ⚠️" if profile.get("chronically_stressed") else ""
            lines.append(f"  {name}: {conf:.0%}{stress_marker}")

    return "\n".join(lines)


def _persist_vitals(report: Dict):
    """Save vital signs to log for historical tracking."""
    VITALS_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        summary = {
            "timestamp": report["timestamp"],
            "overall_health": report["overall_health"],
            "overall_score": report["overall_score"],
            "system_scores": report.get("system_scores", {}),
            "alert_count": len(report.get("alerts", [])),
            "recommendation_count": len(report.get("recommendations", [])),
        }
        with open(VITALS_LOG, "a") as f:
            f.write(json.dumps(summary) + "\n")
    except Exception as e:
        logger.warning(f"[VITALS] Failed to persist vitals: {e}")
