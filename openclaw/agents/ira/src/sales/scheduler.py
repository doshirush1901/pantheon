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
        chat_id = os.environ.get("ADMIN_TELEGRAM_ID", os.environ.get("RUSHABH_TELEGRAM_ID", ""))
        
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


def run_all_daily_tasks():
    """Run all daily tasks."""
    print(f"\n{'='*50}")
    print(f"Running daily sales tasks - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")
    
    run_proactive_outreach()
    time.sleep(2)
    run_follow_up_check()


def run_once():
    """Run all tasks once (for cron)."""
    run_all_daily_tasks()
    
    if datetime.now().weekday() == 0:
        run_pipeline_summary()


def run_daemon():
    """Run as daemon with scheduled tasks."""
    print(f"Starting sales scheduler daemon at {datetime.now().isoformat()}")
    print(f"Log file: {LOG_DIR / 'scheduler.log'}")
    
    schedule.every().day.at("09:00").do(run_proactive_outreach)
    schedule.every().day.at("10:00").do(run_follow_up_check)
    schedule.every().monday.at("08:00").do(run_pipeline_summary)
    
    print("\nScheduled tasks:")
    print("  - Proactive outreach: Daily at 09:00")
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
    parser.add_argument("--task", choices=["outreach", "followup", "pipeline"], help="Run specific task")
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
    else:
        parser.print_help()
