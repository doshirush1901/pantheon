#!/usr/bin/env python3
"""
IRA VITAL SIGNS - Beyond the Brain: Whole-System Health Report
=============================================================

Generates a daily "vital signs" report that mirrors the human body's health metrics:
- Cardiovascular: Pipeline health, latency, throughput
- Endocrine: Agent scores, feedback balance
- Immune: Knowledge health, recurring issues
- Respiratory: Last dream run, operational rhythm
- Metabolic: Infrastructure status (Qdrant, Mem0, etc.)

Usage:
    python scripts/ira_vital_signs.py
    python scripts/ira_vital_signs.py --telegram   # Send report to Telegram
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Path setup for worktree or main repo
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "brain"))

# Load .env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if not os.environ.get(key):
                os.environ[key] = value


def check_services():
    """Metabolic: Infrastructure status."""
    status = {}
    try:
        import requests
        qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        r = requests.get(qdrant_url, timeout=5)
        status["qdrant"] = r.status_code == 200
    except Exception:
        status["qdrant"] = False

    status["openai"] = bool(os.environ.get("OPENAI_API_KEY"))
    status["voyage"] = bool(os.environ.get("VOYAGE_API_KEY"))
    status["mem0"] = bool(os.environ.get("MEM0_API_KEY"))
    status["telegram"] = bool(os.environ.get("TELEGRAM_BOT_TOKEN"))
    return status


def check_last_dream():
    """Respiratory: When did dream mode last run?"""
    logs_dir = PROJECT_ROOT / "logs"
    if not logs_dir.exists():
        return None, "No logs dir"

    dream_logs = list(logs_dir.glob("dream_*.log"))
    if not dream_logs:
        return None, "No dream logs"

    latest = max(dream_logs, key=lambda p: p.stat().st_mtime)
    mtime = datetime.fromtimestamp(latest.stat().st_mtime)
    age_hours = (datetime.now() - mtime).total_seconds() / 3600
    status = "✅" if age_hours < 30 else "⚠️" if age_hours < 48 else "❌"
    return {
        "last_run": mtime.isoformat(),
        "age_hours": round(age_hours, 1),
        "log_file": latest.name,
        "status": status,
    }, None


def check_knowledge_health():
    """Immune: Knowledge health score and recurring issues."""
    try:
        from knowledge_health import get_health_monitor
        monitor = get_health_monitor()
        report = monitor.run_health_check()
        recurring = monitor.analyze_recurring_issues(threshold=3)
        return {
            "score": report.overall_score,
            "passed": report.checks_passed,
            "failed": report.checks_failed,
            "issues_count": len(report.issues),
            "recurring_types": len(recurring),
            "recurring": [r["signature"] for r in recurring[:5]],
        }
    except Exception as e:
        return {"error": str(e)}


def check_agent_scores():
    """Endocrine: Agent confidence scores."""
    scores_path = PROJECT_ROOT / "openclaw" / "data" / "learned_lessons" / "agent_scores.json"
    if not scores_path.exists():
        scores_path = PROJECT_ROOT / "data" / "learned_lessons" / "agent_scores.json"
    if not scores_path.exists():
        return {"error": "No agent_scores.json"}

    data = json.loads(scores_path.read_text())
    summary = {}
    for agent, info in data.items():
        summary[agent] = {
            "score": info.get("score", 0),
            "successes": info.get("successes", 0),
            "failures": info.get("failures", 0),
        }
    return summary


def check_outreach_state():
    """Musculoskeletal: Outreach activity."""
    state_path = PROJECT_ROOT / "openclaw" / "data" / "outreach_state.json"
    if not state_path.exists():
        return {"sent_today": 0, "status": "No outreach state"}

    data = json.loads(state_path.read_text())
    sent = data.get("sent_today", data.get("daily_count", 0))
    sent_count = len(sent) if isinstance(sent, list) else (sent or 0)
    return {
        "sent_today": sent_count,
        "queued": len(data.get("queue", data.get("queued", []))),
        "daily_count": data.get("daily_count", 0),
        "last_check": data.get("last_check"),
    }


def generate_report():
    """Generate full vital signs report."""
    now = datetime.now()
    report = {
        "timestamp": now.isoformat(),
        "generated_at": now.strftime("%Y-%m-%d %H:%M"),
        "cardiovascular": {"note": "Pipeline health metrics - requires instrumentation"},
        "endocrine": check_agent_scores(),
        "immune": check_knowledge_health(),
        "respiratory": {},
        "metabolic": check_services(),
        "musculoskeletal": check_outreach_state(),
    }

    dream_info, dream_err = check_last_dream()
    if dream_info:
        report["respiratory"] = dream_info
    else:
        report["respiratory"] = {"error": dream_err}

    return report


def format_report(report: dict) -> str:
    """Format report for console or Telegram."""
    lines = [
        "📊 *IRA VITAL SIGNS*",
        f"_{report['generated_at']}_",
        "",
    ]

    # Metabolic (infrastructure)
    lines.append("*Metabolic (Infrastructure):*")
    for svc, ok in report.get("metabolic", {}).items():
        lines.append(f"  {'✅' if ok else '❌'} {svc}")
    lines.append("")

    # Respiratory (dream rhythm)
    resp = report.get("respiratory", {})
    if "error" in resp:
        lines.append(f"*Respiratory:* ⚠️ {resp['error']}")
    else:
        lines.append(f"*Respiratory (Dream):* {resp.get('status', '?')} Last run {resp.get('age_hours', 0):.1f}h ago")
    lines.append("")

    # Immune (knowledge health)
    immune = report.get("immune", {})
    if "error" in immune:
        lines.append(f"*Immune:* ⚠️ {immune['error']}")
    else:
        lines.append(f"*Immune (Knowledge Health):* {immune.get('score', 0):.0f}/100")
        lines.append(f"  Recurring issues: {immune.get('recurring_types', 0)} types")
        if immune.get("recurring"):
            lines.append(f"  → {', '.join(immune['recurring'][:3])}")
    lines.append("")

    # Endocrine (agent scores)
    endo = report.get("endocrine", {})
    if "error" in endo:
        lines.append(f"*Endocrine:* ⚠️ {endo['error']}")
    else:
        lines.append("*Endocrine (Agent Scores):*")
        for agent, data in sorted(endo.items()):
            if isinstance(data, dict):
                s = data.get("score", 0)
                bar = "█" * int(s * 10) + "░" * (10 - int(s * 10))
                lines.append(f"  {agent}: {bar} {s:.2f}")
    lines.append("")

    # Musculoskeletal (outreach)
    musc = report.get("musculoskeletal", {})
    sent = musc.get("sent_today", musc.get("daily_count", 0))
    queued = musc.get("queued", 0)
    lines.append(f"*Musculoskeletal (Outreach):* {sent} sent today, {queued} queued")

    lines.append("")
    lines.append("Type /health for full diagnostic. 🚀")
    return "\n".join(lines)


def send_to_telegram(text: str) -> bool:
    """Send report to Telegram."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_ADMIN_CHAT_ID") or os.environ.get("EXPECTED_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ Telegram not configured (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)")
        return False
    try:
        import requests
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--telegram", action="store_true", help="Send report to Telegram")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--alert-if-stale", type=float, metavar="HOURS", help="Exit 1 if dream hasn't run in N hours (for cron)")
    args = parser.parse_args()

    report = generate_report()

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        text = format_report(report)
        print(text)
        if args.telegram:
            if send_to_telegram(text):
                print("\n📤 Vital signs sent to Telegram")
            else:
                print("\n⚠️ Failed to send to Telegram")

    # Cron heartbeat check: exit 1 if dream is stale
    if args.alert_if_stale is not None:
        resp = report.get("respiratory", {})
        age = resp.get("age_hours")
        if age is None or age > args.alert_if_stale:
            sys.exit(1)
