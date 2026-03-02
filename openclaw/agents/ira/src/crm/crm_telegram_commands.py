#!/usr/bin/env python3
"""
CRM TELEGRAM COMMANDS — Rushabh queries Mnemosyne from his phone
================================================================

Telegram commands that let Rushabh pull CRM data on the go:

    /crm              — Quick pipeline summary
    /crm pipeline     — Full pipeline breakdown
    /crm drip         — Who's ready for drip today
    /crm lead <query> — Look up a specific lead/company
    /crm sync         — Trigger a Gmail sync now
    /crm stats        — Reply rates, scores, performance

These return formatted Telegram messages (plain text, no markdown
issues). Designed to be called from the Telegram gateway's
route_message method.

Usage (from telegram_gateway.py):
    from crm_telegram_commands import handle_crm_command

    if text.lower().startswith("/crm"):
        return handle_crm_command(text, chat_id)
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ira.crm.telegram")

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent))


def handle_crm_command(text: str, chat_id: str = "") -> Optional[str]:
    """
    Handle a /crm command from Telegram. Returns formatted text response.
    Returns None if the command is not recognized (let gateway handle it).
    """
    parts = text.strip().split(None, 2)
    # parts[0] = "/crm", parts[1] = subcommand, parts[2] = args

    if len(parts) == 1:
        return _cmd_quick_summary()

    subcmd = parts[1].lower()

    if subcmd == "pipeline":
        return _cmd_pipeline()
    elif subcmd == "drip":
        return _cmd_drip()
    elif subcmd in ("lead", "lookup", "find"):
        query = parts[2] if len(parts) > 2 else ""
        if not query:
            return "Usage: /crm lead <company or name>"
        return _cmd_lead_lookup(query)
    elif subcmd == "sync":
        return _cmd_sync()
    elif subcmd == "stats":
        return _cmd_stats()
    elif subcmd == "help":
        return _cmd_help()
    else:
        # Treat unknown subcmd as a lead lookup
        query = " ".join(parts[1:])
        return _cmd_lead_lookup(query)


def _get_crm():
    try:
        from ira_crm import get_crm
        return get_crm()
    except Exception as e:
        logger.warning(f"CRM not available: {e}")
        return None


def _cmd_help() -> str:
    return (
        "Mnemosyne CRM Commands\n"
        "---\n"
        "/crm - Quick pipeline summary\n"
        "/crm pipeline - Full pipeline breakdown\n"
        "/crm drip - Leads ready for drip today\n"
        "/crm lead <name> - Look up a lead/company\n"
        "/crm sync - Trigger Gmail sync now\n"
        "/crm stats - Performance stats\n"
        "/crm help - This message"
    )


def _cmd_quick_summary() -> str:
    crm = _get_crm()
    if not crm:
        return "CRM not available."

    stats = crm.get_pipeline_stats()
    drip = crm.get_drip_stats()

    total = stats.get("total_leads", 0)
    by_pri = stats.get("by_priority", {})
    reply_rate = stats.get("reply_rate", 0)
    sent = stats.get("total_emails_sent", 0)
    replies = stats.get("total_replies", 0)

    lines = [
        "Mnemosyne CRM",
        "---",
        f"Leads: {total}",
        f"  Critical: {by_pri.get('critical', 0)} | High: {by_pri.get('high', 0)} | Medium: {by_pri.get('medium', 0)} | Low: {by_pri.get('low', 0)}",
        f"Emails: {sent} sent, {replies} replies ({reply_rate:.0%})",
        f"Drip ready: {drip.get('ready_for_drip', 0)}",
        f"Engaged: {drip.get('engaged', 0)}",
    ]

    if drip.get("bounced", 0) > 0:
        lines.append(f"Bounced: {drip['bounced']}")

    lines.append("\n/crm pipeline | /crm drip | /crm lead <name>")
    return "\n".join(lines)


def _cmd_pipeline() -> str:
    crm = _get_crm()
    if not crm:
        return "CRM not available."

    stats = crm.get_pipeline_stats()
    by_stage = stats.get("by_stage", {})

    lines = [
        "Pipeline Breakdown",
        "---",
    ]

    stage_order = ["new", "contacted", "engaged", "qualified", "proposal", "negotiating", "won", "lost", "dormant"]
    for stage in stage_order:
        count = by_stage.get(stage, 0)
        if count > 0 or stage in ("new", "contacted", "engaged", "won", "lost"):
            bar = "#" * min(count, 20)
            lines.append(f"  {stage:12s} {count:3d} {bar}")

    # Also show empty stage if leads have blank stage
    blank = by_stage.get("", 0)
    if blank > 0:
        lines.append(f"  {'(unstaged)':12s} {blank:3d}")

    lines.extend([
        "",
        f"Total: {stats.get('total_leads', 0)} leads",
        f"Reply rate: {stats.get('reply_rate', 0):.0%}",
    ])

    return "\n".join(lines)


def _cmd_drip() -> str:
    crm = _get_crm()
    if not crm:
        return "CRM not available."

    leads = crm.get_leads_ready_for_drip(max_results=10)
    if not leads:
        return "No leads due for drip today. Everyone is either too recent or has replied."

    lines = [f"Drip Ready: {len(leads)} leads\n---"]

    for lead in leads:
        days = 0
        if lead.last_email_sent:
            try:
                days = (datetime.now() - datetime.fromisoformat(lead.last_email_sent)).days
            except (ValueError, TypeError):
                pass

        status = f"{days}d ago" if lead.emails_sent > 0 else "never contacted"
        lines.append(
            f"{lead.priority[0].upper()} | {lead.company[:30]:30s} | "
            f"drip {lead.drip_stage}/5 | {status}"
        )

    lines.append(f"\n{len(leads)} leads ready. Ira will send at 08:30.")
    return "\n".join(lines)


def _cmd_lead_lookup(query: str) -> str:
    crm = _get_crm()
    if not crm:
        return "CRM not available."

    contacts = crm.search_contacts(query, limit=3)
    if not contacts:
        return f"No contacts matching '{query}'."

    parts = []
    for contact in contacts:
        lead = crm.get_lead(contact.email)
        conv = crm.get_conversation_summary(contact.email)

        lines = [
            f"{contact.name or contact.email}",
            f"  {contact.company} ({contact.country})",
            f"  Email: {contact.email}",
        ]

        if lead:
            lines.append(f"  Priority: {lead.priority} | Stage: {lead.deal_stage} | Drip: {lead.drip_stage}/5")
            lines.append(f"  Emails: {lead.emails_sent} sent, {lead.emails_received} replies")
            if lead.reply_quality:
                lines.append(f"  Last reply: {lead.reply_quality}")
            if lead.last_email_sent:
                try:
                    days = (datetime.now() - datetime.fromisoformat(lead.last_email_sent)).days
                    lines.append(f"  Last contact: {days}d ago")
                except (ValueError, TypeError):
                    pass
        else:
            lines.append("  (Contact only — not in sales pipeline)")

        if conv:
            lines.append(f"  History: {conv}")

        if contact.notes:
            lines.append(f"  Notes: {contact.notes[:150]}")

        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def _cmd_sync() -> str:
    """Trigger a Gmail sync now."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from crm_gmail_sync import sync
        result = sync(full=False, days=7)
        return (
            f"Gmail sync complete\n"
            f"  Scanned: {result.get('contacts_scanned', 0)} leads\n"
            f"  New conversations: {result.get('new_conversations', 0)}\n"
            f"  New replies: {result.get('new_replies', 0)}"
        )
    except Exception as e:
        return f"Sync failed: {e}"


def _cmd_stats() -> str:
    crm = _get_crm()
    if not crm:
        return "CRM not available."

    stats = crm.get_pipeline_stats()
    drip = crm.get_drip_stats()

    # Try to load self-evaluation
    eval_data = {}
    eval_file = PROJECT_ROOT / "data" / "drip_self_evaluation.json"
    if eval_file.exists():
        try:
            eval_data = json.loads(eval_file.read_text())
        except Exception:
            pass

    lines = [
        "Mnemosyne Stats",
        "---",
        f"Total leads: {stats.get('total_leads', 0)}",
        f"Emails sent: {stats.get('total_emails_sent', 0)}",
        f"Replies: {stats.get('total_replies', 0)}",
        f"Reply rate: {stats.get('reply_rate', 0):.0%}",
        f"Engaged: {drip.get('engaged', 0)}",
        f"Bounced: {drip.get('bounced', 0)}",
    ]

    if eval_data:
        lines.extend([
            "",
            "Ira's Self-Score",
            f"  Score: {eval_data.get('self_score', '?')}/100",
            f"  Engagement rate: {eval_data.get('engagement_rate', 0):.0%}",
        ])
        questions = eval_data.get("reflection_questions", [])
        if questions:
            lines.append(f"  Thinking: {questions[0][:80]}")

    return "\n".join(lines)
