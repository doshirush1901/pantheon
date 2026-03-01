#!/usr/bin/env python3
"""
SCHEDULED TASK RUNNER
=====================

Runs scheduled tasks for IRA:
- European drip campaign outreach
- Follow-up automation suggestions
- Customer health monitoring

Usage (manual):
    python scripts/run_scheduled_tasks.py --task drip
    python scripts/run_scheduled_tasks.py --task followups
    python scripts/run_scheduled_tasks.py --task health
    python scripts/run_scheduled_tasks.py --all

Usage (cron/launchd):
    # Run all tasks daily at 8 AM
    0 8 * * * cd /path/to/Ira && python scripts/run_scheduled_tasks.py --all
    
    # Run drip campaign every weekday at 9 AM
    0 9 * * 1-5 cd /path/to/Ira && python scripts/run_scheduled_tasks.py --task drip
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/src/crm"))

# Load environment
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("scheduled_tasks")

# Output directory for task results
OUTPUT_DIR = PROJECT_ROOT / "data" / "scheduled_tasks"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def run_drip_campaign():
    """
    Run European drip campaign outreach.
    
    Gets leads ready for outreach and generates email content.
    Returns draft emails for review (doesn't send automatically).
    """
    logger.info("=" * 60)
    logger.info("EUROPEAN DRIP CAMPAIGN")
    logger.info("=" * 60)
    
    try:
        from european_drip_campaign import get_campaign, EuropeanDripCampaign
        
        campaign = get_campaign()
        
        # Get leads ready for outreach
        ready_leads = campaign.get_leads_ready_for_outreach()
        
        if not ready_leads:
            logger.info("No leads ready for outreach today")
            return {"status": "no_leads", "count": 0}
        
        logger.info(f"Found {len(ready_leads)} leads ready for outreach")
        
        # Generate emails for each lead
        drafts = []
        for lead in ready_leads[:5]:  # Limit to 5 per run
            email = campaign.get_next_email(lead.lead_id)
            if email:
                drafts.append({
                    "lead_id": lead.lead_id,
                    "company": lead.company,
                    "country": lead.country,
                    "stage": lead.current_stage + 1,
                    "subject": email.get("subject", ""),
                    "body_preview": email.get("body", "")[:200] + "...",
                    "generated_at": datetime.now().isoformat()
                })
                logger.info(f"  - {lead.company} (Stage {lead.current_stage + 1})")
        
        # Save drafts for review
        output_file = OUTPUT_DIR / f"drip_drafts_{datetime.now().strftime('%Y%m%d')}.json"
        with open(output_file, 'w') as f:
            json.dump(drafts, f, indent=2)
        
        logger.info(f"Saved {len(drafts)} draft emails to {output_file}")
        
        return {"status": "success", "count": len(drafts), "output_file": str(output_file)}
        
    except ImportError as e:
        logger.error(f"European drip campaign not available: {e}")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        logger.error(f"Error running drip campaign: {e}")
        return {"status": "error", "error": str(e)}


def run_followup_suggestions():
    """
    Generate follow-up suggestions for stale quotes.
    
    Uses follow_up_automation to identify quotes needing attention.
    """
    logger.info("=" * 60)
    logger.info("FOLLOW-UP AUTOMATION")
    logger.info("=" * 60)
    
    try:
        from follow_up_automation import get_engine, FollowUpEngine
        
        engine = get_engine()
        
        # Generate follow-up suggestions
        suggestions = engine.generate_suggestions()
        
        if not suggestions:
            logger.info("No follow-ups needed today")
            return {"status": "no_followups", "count": 0}
        
        logger.info(f"Generated {len(suggestions)} follow-up suggestions")
        
        # Format for output
        formatted_suggestions = []
        for suggestion in suggestions:
            formatted_suggestions.append({
                "quote_id": suggestion.quote_id,
                "customer": suggestion.customer_email,
                "company": suggestion.company,
                "product": suggestion.product,
                "amount": suggestion.quote_amount,
                "priority": suggestion.priority.value,
                "reason": suggestion.reason.value,
                "days_inactive": suggestion.days_since_activity,
                "suggested_action": suggestion.suggested_action,
                "suggested_message": suggestion.suggested_message[:200] + "..." if len(suggestion.suggested_message) > 200 else suggestion.suggested_message
            })
            logger.info(f"  - {suggestion.customer_email}: {suggestion.reason.value} ({suggestion.priority.value})")
        
        # Save suggestions for review
        output_file = OUTPUT_DIR / f"followup_suggestions_{datetime.now().strftime('%Y%m%d')}.json"
        with open(output_file, 'w') as f:
            json.dump(formatted_suggestions, f, indent=2)
        
        logger.info(f"Saved {len(formatted_suggestions)} suggestions to {output_file}")
        
        # Queue for morning review
        try:
            engine.queue_for_review(suggestions)
        except Exception:
            pass  # Non-critical
        
        return {"status": "success", "count": len(suggestions), "output_file": str(output_file)}
        
    except ImportError as e:
        logger.error(f"Follow-up automation not available: {e}")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        logger.error(f"Error generating follow-ups: {e}")
        return {"status": "error", "error": str(e)}


def run_health_monitoring():
    """
    Monitor customer health and identify at-risk relationships.
    """
    logger.info("=" * 60)
    logger.info("CUSTOMER HEALTH MONITORING")
    logger.info("=" * 60)
    
    try:
        from customer_health import get_scorer, HealthScorer
        
        scorer = get_scorer()
        
        # Get at-risk customers
        at_risk = scorer.get_at_risk_customers()
        
        if not at_risk:
            logger.info("No at-risk customers identified")
            return {"status": "healthy", "at_risk_count": 0}
        
        logger.info(f"Found {len(at_risk)} at-risk customers")
        
        # Format health report
        health_report = []
        for customer in at_risk:
            health_report.append({
                "email": customer.customer_email,
                "score": customer.score,
                "risk_level": customer.risk_level.value,
                "trend": customer.trend.value if customer.trend else "unknown",
                "days_since_contact": customer.metrics.days_since_contact if customer.metrics else 0,
                "recommendation": customer.recommendation if hasattr(customer, 'recommendation') else "Re-engage"
            })
            logger.info(f"  - {customer.customer_email}: Score {customer.score}/100 ({customer.risk_level.value})")
        
        # Save health report
        output_file = OUTPUT_DIR / f"health_report_{datetime.now().strftime('%Y%m%d')}.json"
        with open(output_file, 'w') as f:
            json.dump(health_report, f, indent=2)
        
        logger.info(f"Saved health report to {output_file}")
        
        return {"status": "attention_needed", "at_risk_count": len(at_risk), "output_file": str(output_file)}
        
    except ImportError as e:
        logger.error(f"Health scorer not available: {e}")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        logger.error(f"Error monitoring health: {e}")
        return {"status": "error", "error": str(e)}


def run_all_tasks():
    """Run all scheduled tasks."""
    logger.info("\n" + "=" * 70)
    logger.info("RUNNING ALL SCHEDULED TASKS")
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70 + "\n")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tasks": {}
    }
    
    # Run each task
    results["tasks"]["drip_campaign"] = run_drip_campaign()
    print()  # Spacing
    results["tasks"]["followup_suggestions"] = run_followup_suggestions()
    print()  # Spacing
    results["tasks"]["health_monitoring"] = run_health_monitoring()
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("TASK SUMMARY")
    logger.info("=" * 70)
    for task, result in results["tasks"].items():
        status = result.get("status", "unknown")
        count = result.get("count", result.get("at_risk_count", 0))
        logger.info(f"  {task}: {status} ({count} items)")
    
    # Save summary
    summary_file = OUTPUT_DIR / f"task_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nFull results saved to: {summary_file}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="IRA Scheduled Task Runner")
    parser.add_argument(
        "--task",
        choices=["drip", "followups", "health"],
        help="Specific task to run"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all scheduled tasks"
    )
    
    args = parser.parse_args()
    
    if args.all:
        run_all_tasks()
    elif args.task == "drip":
        run_drip_campaign()
    elif args.task == "followups":
        run_followup_suggestions()
    elif args.task == "health":
        run_health_monitoring()
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python scripts/run_scheduled_tasks.py --all")
        print("  python scripts/run_scheduled_tasks.py --task drip")


if __name__ == "__main__":
    main()
