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


def run_morning_briefing() -> Dict[str, Any]:
    """Proactive daily briefing — one Telegram message with everything Rushabh needs."""
    try:
        import asyncio
        sections = []

        # 1. Pipeline health
        try:
            sys.path.insert(0, str(SKILLS_DIR / "crm"))
            from ira_crm import get_crm
            crm = get_crm()
            pipeline = crm.get_pipeline_summary() if hasattr(crm, "get_pipeline_summary") else {}
            if pipeline:
                sections.append(f"**Pipeline:** {pipeline.get('total', '?')} leads, {pipeline.get('engaged', '?')} engaged, {pipeline.get('at_risk', '?')} at risk")
        except Exception:
            pass

        # 2. Unread emails
        try:
            sys.path.insert(0, str(PROJECT_ROOT))
            from openclaw.agents.ira.src.tools.google_tools import gmail_read_inbox
            inbox = gmail_read_inbox(max_results=5, unread_only=True)
            if inbox and not inbox.startswith("("):
                email_count = inbox.count("From:")
                sections.append(f"**Inbox:** {email_count} unread email{'s' if email_count != 1 else ''}")
        except Exception:
            pass

        # 3. Drip-ready leads
        try:
            from european_drip_campaign import get_campaign
            campaign = get_campaign()
            ready = campaign.get_leads_ready_for_outreach()
            if ready:
                names = ", ".join(l.get("company", l.get("id", "?")) for l in ready[:5])
                sections.append(f"**Follow-ups due:** {len(ready)} leads ({names}{'...' if len(ready) > 5 else ''})")
        except Exception:
            pass

        # 4. Financial snapshot
        try:
            from openclaw.agents.ira.src.skills.invocation import invoke_order_book
            loop = asyncio.new_event_loop()
            try:
                finance = loop.run_until_complete(invoke_order_book())
                if finance and len(finance) > 20:
                    for line in finance.split("\n")[:3]:
                        if any(kw in line.lower() for kw in ["total", "collected", "outstanding", "order book"]):
                            sections.append(f"**Finance:** {line.strip()}")
                            break
            finally:
                loop.close()
        except Exception:
            pass

        # 5. Corrections applied overnight
        try:
            from openclaw.agents.ira.src.agents.nemesis.agent import get_nemesis
            nemesis = get_nemesis()
            stats = nemesis.get_stats() if hasattr(nemesis, "get_stats") else {}
            unapplied = stats.get("unapplied", 0) if stats else 0
            if unapplied:
                sections.append(f"**Nemesis:** {unapplied} correction{'s' if unapplied != 1 else ''} pending (run /dream to apply)")
        except Exception:
            pass

        # 6. Quality trend
        try:
            from openclaw.agents.ira.src.brain.quality_tracker import get_improvement_report
            qr = get_improvement_report()
            if qr and "No quality data" not in qr:
                for line in qr.split("\n"):
                    if "Trend:" in line or "avg quality" in line.lower():
                        sections.append(f"**Quality:** {line.strip()}")
                        break
        except Exception:
            pass

        if not sections:
            sections.append("All systems nominal. No urgent items.")

        briefing = "Good morning, Rushabh.\n\n"
        briefing += "\n".join(f"  {s}" for s in sections)
        briefing += "\n\nReply with any question or say 'details' for a deep dive on any item."

        telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("RUSHABH_TELEGRAM_CHAT_ID") or os.environ.get("RUSHABH_TELEGRAM_ID", "5700751574")
        if telegram_token:
            import requests
            requests.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                json={"chat_id": chat_id, "text": briefing},
                timeout=15,
            )

        log_task("morning_briefing", {"summary": f"{len(sections)} sections", "sent": bool(telegram_token)})
        return {"sections": len(sections), "sent": bool(telegram_token)}
    except Exception as e:
        log_task("morning_briefing", {"error": str(e)}, success=False)
        return {"error": str(e)}


def run_prometheus_weekly_sweep() -> Dict[str, Any]:
    """Weekly Prometheus discovery sweep — scan all industries and notify."""
    try:
        import asyncio
        sys.path.insert(0, str(PROJECT_ROOT))
        from openclaw.agents.ira.src.agents.prometheus.agent import get_prometheus

        prometheus = get_prometheus()
        loop = asyncio.new_event_loop()
        try:
            report = loop.run_until_complete(prometheus.run_discovery_sweep(top_n=10))
        finally:
            loop.close()

        top_opps = report.get("top_opportunities", [])[:5]

        msg = "**Weekly Market Discovery (Prometheus)**\n\n"
        msg += f"Scanned {report.get('industries_scanned', '?')} industries, "
        msg += f"found {report.get('total_opportunities', '?')} opportunities.\n\n"

        if top_opps:
            msg += "**Top 5 Opportunities:**\n"
            for i, opp in enumerate(top_opps, 1):
                name = opp.get("product", opp.get("name", "?"))
                score = opp.get("score", "?")
                industry = opp.get("industry", "?")
                machine = opp.get("recommended_machine", "?")
                msg += f"  {i}. {name} ({industry}) — Score: {score}, Machine: {machine}\n"

        msg += "\nSay 'details on opportunity N' or 'hand top 3 to Hermes' to act."

        telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("RUSHABH_TELEGRAM_CHAT_ID") or os.environ.get("RUSHABH_TELEGRAM_ID", "5700751574")
        if telegram_token:
            import requests
            requests.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                json={"chat_id": chat_id, "text": msg},
                timeout=15,
            )

        # Save report
        report_dir = PROJECT_ROOT / "data" / "discovery"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f"weekly_sweep_{datetime.now().strftime('%Y%m%d')}.json"
        report_file.write_text(json.dumps(report, indent=2, default=str))

        log_task("prometheus_weekly_sweep", {
            "summary": f"{report.get('total_opportunities', 0)} opportunities found",
            "top_score": top_opps[0].get("score") if top_opps else 0,
        })
        return report
    except Exception as e:
        log_task("prometheus_weekly_sweep", {"error": str(e)}, success=False)
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
    schedule.every().day.at("08:00").do(run_morning_briefing)
    schedule.every(30).minutes.do(run_crm_gmail_sync)
    schedule.every().day.at("08:30").do(run_hermes_outreach)
    schedule.every().day.at("09:00").do(run_proactive_outreach)
    schedule.every().day.at("09:30").do(run_european_drip)
    schedule.every().day.at("10:00").do(run_follow_up_check)
    schedule.every().monday.at("08:00").do(run_pipeline_summary)
    schedule.every().wednesday.at("11:00").do(run_prometheus_weekly_sweep)
    
    print("\nScheduled tasks:")
    print("  - Vital signs: Daily at 07:30")
    print("  - Morning briefing: Daily at 08:00 (proactive Telegram summary)")
    print("  - CRM Gmail sync: Every 30 minutes (Mnemosyne stays live)")
    print("  - Hermes outreach: Daily at 08:30 (contextual drip with deep personalization)")
    print("  - Proactive outreach: Daily at 09:00")
    print("  - European drip: Daily at 09:30 (legacy manual review)")
    print("  - Follow-up check: Daily at 10:00")
    print("  - Pipeline summary: Monday at 08:00")
    print("  - Prometheus sweep: Wednesday at 11:00 (weekly market discovery)")
    print("\nPress Ctrl+C to stop.\n")
    
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sales Scheduler")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--once", action="store_true", help="Run all tasks once")
    parser.add_argument("--task", choices=[
        "outreach", "followup", "pipeline", "drip", "vitals",
        "auto_drip", "hermes", "briefing", "prometheus",
    ], help="Run specific task")
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
        elif args.task == "briefing":
            run_morning_briefing()
        elif args.task == "prometheus":
            run_prometheus_weekly_sweep()
    else:
        parser.print_help()
