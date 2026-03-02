#!/usr/bin/env python3
"""
SALES SCHEDULER - Daily Automation Tasks
=========================================

Runs scheduled sales automation tasks:
- Daily proactive outreach check (9:00 AM)
- Stale quote follow-up reminders (10:00 AM)
- Weekly pipeline summary (Monday 8:00 AM)

Can be run as:
1. Standalone daemon: python scheduler.py --daemon
2. Single run: python scheduler.py --once
3. Cron job: Add to crontab
4. Systemd service: See ira_scheduler.service

Usage:
    # Run once (for cron)
    python scheduler.py --once
    
    # Run as daemon
    python scheduler.py --daemon
    
    # Run specific task
    python scheduler.py --task outreach
"""

import os
import sys
import json
import time
import schedule
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

SKILL_DIR = Path(__file__).parent
SKILLS_DIR = SKILL_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(SKILL_DIR))
sys.path.insert(0, str(SKILLS_DIR / "crm"))
sys.path.insert(0, str(AGENT_DIR))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)


def log_task(task_name: str, result: Dict[str, Any], success: bool = True):
    """Log task execution to file."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "task": task_name,
        "success": success,
        "result": result,
    }
    
    log_file = LOG_DIR / "scheduler.log"
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    status = "✅" if success else "❌"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {status} {task_name}: {result.get('summary', 'done')}")


def run_proactive_outreach() -> Dict[str, Any]:
    """Run daily proactive outreach check."""
    try:
        from proactive_outreach import run_daily_outreach
        result = run_daily_outreach()
        log_task("proactive_outreach", {
            "summary": f"Found {result.get('candidates_found', 0)} candidates",
            **result
        })
        return result
    except Exception as e:
        log_task("proactive_outreach", {"error": str(e)}, success=False)
        return {"error": str(e)}


def run_follow_up_check() -> Dict[str, Any]:
    """Run stale quote follow-up check."""
    try:
        from follow_up_automation import run_daily_follow_up_check
        result = run_daily_follow_up_check()
        log_task("follow_up_check", {
            "summary": f"Generated {result.get('suggestions_generated', 0)} suggestions",
            **result
        })
        return result
    except Exception as e:
        log_task("follow_up_check", {"error": str(e)}, success=False)
        return {"error": str(e)}


def run_pipeline_summary() -> Dict[str, Any]:
    """Run weekly pipeline summary."""
    try:
        sys.path.insert(0, str(SKILLS_DIR / "crm"))
        from quote_lifecycle import get_tracker
        
        tracker = get_tracker()
        stats = tracker.get_pipeline_stats()
        
        summary = {
            "total_quotes": stats.get("total", 0),
            "pending": stats.get("pending", 0),
            "won": stats.get("won", 0),
            "lost": stats.get("lost", 0),
            "win_rate": f"{stats.get('win_rate', 0):.1%}" if stats.get("win_rate") else "N/A",
        }
        
        telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("RUSHABH_TELEGRAM_ID", "5700751574")
        
        if telegram_token:
            import requests
            
            message = f"📊 *Weekly Pipeline Summary*\n"
            message += f"━━━━━━━━━━━━━━━━━\n"
            message += f"Total Quotes: {summary['total_quotes']}\n"
            message += f"Pending: {summary['pending']}\n"
            message += f"Won: {summary['won']}\n"
            message += f"Lost: {summary['lost']}\n"
            message += f"Win Rate: {summary['win_rate']}\n"
            
            requests.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
                timeout=10,
            )
            summary["notification_sent"] = True
        
        log_task("pipeline_summary", {"summary": f"Pipeline: {summary['total_quotes']} quotes", **summary})
        return summary
        
    except Exception as e:
        log_task("pipeline_summary", {"error": str(e)}, success=False)
        return {"error": str(e)}


def run_european_drip() -> Dict[str, Any]:
    """Run European drip campaign - check for leads ready for next email."""
    try:
        sys.path.insert(0, str(SKILLS_DIR / "crm"))
        from european_drip_campaign import get_campaign
        campaign = get_campaign()
        ready = campaign.get_leads_ready_for_outreach()

        result = {
            "summary": f"{len(ready)} European leads ready for next drip email",
            "leads_ready": len(ready),
            "leads": [{"id": l.get("id"), "stage": l.get("stage")} for l in ready[:10]],
        }

        if ready:
            telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            chat_id = os.environ.get("RUSHABH_TELEGRAM_ID", "5700751574")
            if telegram_token:
                import requests
                msg = f"🇪🇺 *European Drip Campaign*\n{len(ready)} leads ready for next email.\n"
                for l in ready[:5]:
                    msg += f"  • {l.get('company', l.get('id', '?'))} (stage {l.get('stage', '?')})\n"
                if len(ready) > 5:
                    msg += f"  ...and {len(ready) - 5} more\n"
                msg += "\nApprove via /drip approve <id>"
                requests.post(
                    f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                    json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
                    timeout=10,
                )
                result["notification_sent"] = True

        log_task("european_drip", result)
        return result
    except Exception as e:
        log_task("european_drip", {"error": str(e)}, success=False)
        return {"error": str(e)}


def run_vital_signs() -> Dict[str, Any]:
    """Run vital signs report (Beyond the Brain respiratory rhythm)."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from ira_vital_signs import generate_report, format_report, send_to_telegram
        report = generate_report()
        text = format_report(report)
        sent = send_to_telegram(text)
        log_task("vital_signs", {"summary": "Sent to Telegram" if sent else "Generated (no Telegram)", "sent": sent})
        return {"sent": sent}
    except Exception as e:
        log_task("vital_signs", {"error": str(e)}, success=False)
        return {"error": str(e)}


def run_crm_gmail_sync() -> Dict[str, Any]:
    """Sync Mnemosyne's CRM with Gmail — pick up new replies and conversations."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from crm_gmail_sync import sync
        result = sync(full=False, days=7)
        log_task("crm_gmail_sync", {
            "summary": f"Scanned {result.get('contacts_scanned', 0)}, {result.get('new_replies', 0)} new replies",
            **result,
        })
        return result
    except Exception as e:
        log_task("crm_gmail_sync", {"error": str(e)}, success=False)
        return {"error": str(e)}


def run_autonomous_drip() -> Dict[str, Any]:
    """Run Ira's autonomous drip engine."""
    try:
        from autonomous_drip_engine import get_engine
        engine = get_engine()
        engine.check_replies()
        batch = engine.run_daily_batch()
        eval_result = engine.self_evaluate()
        result = {
            "emails_sent": batch.emails_sent,
            "self_score": eval_result.get("self_score", 0),
        }
        log_task("autonomous_drip", {
            "summary": f"Sent {batch.emails_sent}, score {eval_result.get('self_score', 0)}/100",
            **result,
        })
        return result
    except Exception as e:
        log_task("autonomous_drip", {"error": str(e)}, success=False)
        return {"error": str(e)}


def run_hermes_outreach() -> Dict[str, Any]:
    """Run Hermes pro sales outreach — contextual drip with deep personalization."""
    try:
        import asyncio
        sys.path.insert(0, str(SKILLS_DIR.parent / "agents" / "hermes"))
        from agent import get_hermes

        hermes = get_hermes()
        result = asyncio.run(hermes.run_outreach_batch(dry_run=False))
        log_task("hermes_outreach", {
            "summary": f"Sent {result.get('sent', 0)}/{result.get('batch_size', 0)}",
            **{k: v for k, v in result.items() if k != "emails"},
        })
        return result
    except Exception as e:
        log_task("hermes_outreach", {"error": str(e)}, success=False)
        return {"error": str(e)}


def run_all_daily_tasks():
    """Run all daily tasks."""
    print(f"\n{'='*50}")
    print(f"Running daily sales tasks - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")
    
    run_crm_gmail_sync()
    time.sleep(2)
    run_hermes_outreach()
    time.sleep(2)
    run_proactive_outreach()
    time.sleep(2)
    run_follow_up_check()
    time.sleep(2)
    run_european_drip()


def run_once():
    """Run all tasks once (for cron)."""
    run_all_daily_tasks()
    
    if datetime.now().weekday() == 0:
        run_pipeline_summary()


def run_daemon():
    """Run as daemon with scheduled tasks."""
    print(f"Starting sales scheduler daemon at {datetime.now().isoformat()}")
    print(f"Log file: {LOG_DIR / 'scheduler.log'}")
    
    schedule.every().day.at("07:30").do(run_vital_signs)
    schedule.every(30).minutes.do(run_crm_gmail_sync)
    schedule.every().day.at("08:30").do(run_hermes_outreach)
    schedule.every().day.at("09:00").do(run_proactive_outreach)
    schedule.every().day.at("09:30").do(run_european_drip)
    schedule.every().day.at("10:00").do(run_follow_up_check)
    schedule.every().monday.at("08:00").do(run_pipeline_summary)
    
    print("\nScheduled tasks:")
    print("  - Vital signs: Daily at 07:30")
    print("  - CRM Gmail sync: Every 30 minutes (Mnemosyne stays live)")
    print("  - Hermes outreach: Daily at 08:30 (contextual drip with deep personalization)")
    print("  - Proactive outreach: Daily at 09:00")
    print("  - European drip: Daily at 09:30 (legacy manual review)")
    print("  - Follow-up check: Daily at 10:00")
    print("  - Pipeline summary: Monday at 08:00")
    print("\nPress Ctrl+C to stop.\n")
    
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sales Scheduler")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--once", action="store_true", help="Run all tasks once")
    parser.add_argument("--task", choices=["outreach", "followup", "pipeline", "drip", "vitals", "auto_drip", "hermes"], help="Run specific task")
    args = parser.parse_args()
    
    if args.daemon:
        run_daemon()
    elif args.once:
        run_once()
    elif args.task:
        if args.task == "outreach":
            run_proactive_outreach()
        elif args.task == "followup":
            run_follow_up_check()
        elif args.task == "pipeline":
            run_pipeline_summary()
        elif args.task == "drip":
            run_european_drip()
        elif args.task == "vitals":
            run_vital_signs()
        elif args.task == "auto_drip":
            run_autonomous_drip()
        elif args.task == "hermes":
            run_hermes_outreach()
    else:
        parser.print_help()
