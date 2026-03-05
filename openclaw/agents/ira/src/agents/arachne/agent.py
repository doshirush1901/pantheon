"""
Arachne — Newsletter and Content Scheduler
============================================

Named after the mortal weaver who challenged Athena — Arachne weaves
threads of content from Cadmus into a distribution plan. She does NOT
create content (that stays with Cadmus). She owns:

  1. Content Calendar — what to publish, when, on which channel
  2. Newsletter Assembly — monthly email to the customer base
  3. LinkedIn Scheduling — queue posts with approval workflow
  4. Distribution Tracking — what was sent, opened, clicked

Personality:
    - Organized, methodical, never misses a deadline
    - She thinks in calendars and cadences, not individual posts
    - Protective of Rushabh's brand — nothing goes out without approval
    - She tracks what works: open rates, engagement, timing

Role in the Pantheon:
    Cadmus writes the content. Arachne schedules and distributes it.
    Athena asks: "What's on the content calendar this week?"
    Arachne replies: "3 LinkedIn posts queued (Mon/Wed/Fri).
    Wednesday's post needs approval. Newsletter goes out March 28."

Functions:
    content_calendar(action, ...)  — View/manage the content calendar
    assemble_newsletter(...)       — Build the monthly newsletter
    distribution_status(...)       — Check what's been sent/pending

Usage:
    from openclaw.agents.ira.src.agents.arachne import (
        content_calendar, assemble_newsletter_tool, distribution_status,
    )
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.agents.arachne")


async def content_calendar(
    action: str = "view",
    channel: str = "",
    scheduled_date: str = "",
    title: str = "",
    content_ref: str = "",
    item_id: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """View or manage the content calendar.

    Actions:
        view     — Show upcoming scheduled content (default)
        schedule — Add a new item to the calendar
        approve  — Approve a pending item by ID
        skip     — Skip/cancel a pending item by ID
        populate — Auto-populate LinkedIn calendar for the next 4 weeks
    """
    from .calendar_engine import (
        get_calendar_view, schedule_item, approve_item, skip_item,
        auto_populate_linkedin_calendar, schedule_next_newsletter,
        get_item,
    )

    if action == "view":
        from_date = scheduled_date or date.today().isoformat()
        items = get_calendar_view(
            channel=channel or None,
            from_date=from_date,
        )
        if not items:
            return "No upcoming content scheduled. Use action='populate' to auto-fill the LinkedIn calendar."
        return _format_calendar_view(items)

    elif action == "schedule":
        if not channel:
            channel = "linkedin"
        if not scheduled_date:
            scheduled_date = date.today().isoformat()
        if not title:
            return "(Error: title is required to schedule content)"
        item = schedule_item(
            channel=channel,
            scheduled_date=scheduled_date,
            title=title,
            content_ref=content_ref,
        )
        return f"Scheduled: {item['id']} — {item['title']} on {item['scheduled_date']} ({item['channel']})"

    elif action == "approve":
        if not item_id:
            return "(Error: item_id is required to approve content)"
        item = approve_item(item_id)
        if not item:
            return f"(Error: item '{item_id}' not found)"
        return f"Approved: {item['id']} — {item['title']}"

    elif action == "skip":
        if not item_id:
            return "(Error: item_id is required to skip content)"
        item = skip_item(item_id)
        if not item:
            return f"(Error: item '{item_id}' not found)"
        return f"Skipped: {item['id']} — {item['title']}"

    elif action == "populate":
        added = auto_populate_linkedin_calendar(weeks_ahead=4)
        nl = schedule_next_newsletter()
        nl_msg = ""
        if nl:
            nl_msg = f"\nNewsletter: {nl['title']} scheduled for {nl['scheduled_date']}"
        return f"Added {added} LinkedIn slots to the calendar.{nl_msg}"

    else:
        return f"(Error: unknown action '{action}'. Use: view, schedule, approve, skip, populate)"


def _format_calendar_view(items: List[Dict[str, Any]]) -> str:
    lines = [f"Content Calendar — {len(items)} items\n"]
    current_week = ""

    for it in items:
        sd = it.get("scheduled_date", "")
        try:
            d = date.fromisoformat(sd)
            week = f"Week of {(d - __import__('datetime').timedelta(days=d.weekday())).isoformat()}"
        except (ValueError, TypeError):
            week = "Unscheduled"

        if week != current_week:
            current_week = week
            lines.append(f"\n{week}")
            lines.append("-" * len(week))

        status_icon = {
            "draft": "[ ]",
            "approved": "[v]",
            "published": "[x]",
            "skipped": "[-]",
            "pending_assembly": "[~]",
        }.get(it.get("status", "draft"), "[ ]")

        ch = it.get("channel", "?")[:2].upper()
        lines.append(f"  {status_icon} {sd} [{ch}] {it.get('title', '(untitled)')}  (id: {it['id']})")

    pending = sum(1 for it in items if it.get("status") in ("draft", "pending_assembly"))
    approved = sum(1 for it in items if it.get("status") == "approved")
    published = sum(1 for it in items if it.get("status") == "published")
    lines.append(f"\nSummary: {pending} pending, {approved} approved, {published} published")
    return "\n".join(lines)


async def assemble_newsletter_tool(
    title: str = "",
    sections: str = "",
    dry_run: bool = True,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Assemble (and optionally send) the monthly newsletter.

    Args:
        title: Newsletter title. Defaults to "Machinecraft Newsletter — <Month Year>".
        sections: Comma-separated section names to include.
                  Options: new_orders, case_study, product_spotlight, event, industry_insight
        dry_run: If True (default), assemble but don't send. Shows preview + subscriber count.
    """
    from .newsletter import assemble_newsletter, send_newsletter, get_subscriber_list

    section_list = [s.strip() for s in sections.split(",") if s.strip()] if sections else None

    newsletter = await assemble_newsletter(title=title or None, sections=section_list)

    subscribers = get_subscriber_list()
    sub_count = len(subscribers)

    if dry_run:
        preview = newsletter["body_text"][:2000]
        return (
            f"Newsletter assembled: {newsletter['subject']}\n"
            f"Sections: {', '.join(newsletter['sections_gathered'])}\n"
            f"Subscribers: {sub_count}\n"
            f"Archived at: {newsletter['archive_path']}\n\n"
            f"--- PREVIEW ---\n{preview}\n--- END PREVIEW ---\n\n"
            f"To send, call assemble_newsletter with dry_run=false. "
            f"Or approve via Telegram after nap sends the preview."
        )

    if sub_count == 0:
        return (
            f"Newsletter assembled but no subscribers to send to.\n"
            f"Add subscribers via the subscribers.json file or CRM import.\n"
            f"Archived at: {newsletter['archive_path']}"
        )

    result = await send_newsletter(newsletter, dry_run=False)
    return (
        f"Newsletter sent!\n"
        f"Delivered to: {result.get('sent', 0)}/{result.get('total', 0)} subscribers\n"
        f"Errors: {len(result.get('errors', []))}\n"
        f"Archived at: {newsletter['archive_path']}"
    )


async def distribution_status(
    channel: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Check distribution status: what's been sent, what's pending approval."""
    from .calendar_engine import get_calendar_view, get_distribution_log, get_due_items

    lines = ["Distribution Status\n"]

    due = get_due_items(channel=channel or None)
    if due:
        lines.append(f"PENDING ({len(due)} items due):")
        for it in due:
            approved = "approved" if it.get("approved") else "needs approval"
            lines.append(f"  - {it['id']}: {it['title']} ({it['channel']}, {approved})")
    else:
        lines.append("No items currently due for distribution.")

    recent_log = get_distribution_log(limit=10)
    if recent_log:
        lines.append(f"\nRECENT ACTIVITY ({len(recent_log)} entries):")
        for entry in reversed(recent_log):
            ts = entry.get("timestamp", "")[:10]
            ch = entry.get("channel", "?")
            item_id = entry.get("item_id", "?")
            details = entry.get("action", entry.get("sent", ""))
            lines.append(f"  {ts} [{ch}] {item_id}: {details}")

    all_items = get_calendar_view()
    total = len(all_items)
    published = sum(1 for it in all_items if it.get("published"))
    pending = sum(1 for it in all_items if it.get("status") in ("draft", "pending_assembly", "approved"))
    lines.append(f"\nOVERALL: {total} total, {published} published, {pending} pending")

    return "\n".join(lines)


async def handle_approval(item_id: str, action: str = "approve") -> str:
    """Handle Telegram approval/skip commands for Arachne content.

    Called by the Telegram gateway when it receives /arachne_approve or /arachne_skip.
    """
    from .calendar_engine import approve_item, skip_item, get_item, mark_published, log_distribution

    item = get_item(item_id)
    if not item:
        return f"Item '{item_id}' not found in the content calendar."

    if action == "approve":
        approve_item(item_id)

        if item["channel"] == "linkedin":
            try:
                from openclaw.agents.ira.src.tools.google_tools import gmail_send
                content = ""
                content_ref = item.get("content_ref", "")
                if content_ref:
                    from pathlib import Path
                    p = Path(content_ref)
                    if not p.is_absolute():
                        from .calendar_engine import PROJECT_ROOT
                        p = PROJECT_ROOT / p
                    if p.exists():
                        content = p.read_text()

                if content:
                    gmail_send(
                        to=os.environ.get("RUSHABH_EMAIL", "rushabh@machinecraft.org"),
                        subject=f"POST NOW: {item['title']}",
                        body=(
                            f"Approved for posting!\n\n"
                            f"---\n\n{content}\n\n---\n\n"
                            f"Copy-paste to LinkedIn and post.\n\n— Arachne"
                        ),
                    )
                mark_published(item_id)
                log_distribution(item_id, "linkedin", {"action": "approved_and_emailed"})
                return f"Approved and emailed for posting: {item['title']}"
            except Exception as e:
                logger.warning("Approval email failed: %s", e)
                return f"Approved but email failed: {e}"

        elif item["channel"] == "newsletter":
            log_distribution(item_id, "newsletter", {"action": "approved_for_send"})
            return f"Newsletter approved: {item['title']}. It will be sent during the next nap cycle."

    elif action == "skip":
        skip_item(item_id)
        log_distribution(item_id, item["channel"], {"action": "skipped"})
        return f"Skipped: {item['title']}"

    return f"Unknown action: {action}"


async def nap_check_and_notify() -> Dict[str, Any]:
    """Called during nap Phase 8.6. Checks calendar and sends Telegram notifications."""
    from .calendar_engine import get_due_items, update_item, log_distribution

    results = {"linkedin_notified": 0, "newsletter_assembled": False, "errors": []}

    due_linkedin = get_due_items(channel="linkedin")
    for item in due_linkedin:
        if item.get("sent_for_approval"):
            continue
        try:
            content = ""
            content_ref = item.get("content_ref", "")
            if content_ref:
                from pathlib import Path
                from .calendar_engine import PROJECT_ROOT
                p = Path(content_ref)
                if not p.is_absolute():
                    p = PROJECT_ROOT / p
                if p.exists():
                    content = p.read_text()[:1500]

            msg = (
                f"<b>Arachne — LinkedIn Post Ready</b>\n\n"
                f"<b>{item['title']}</b>\n"
                f"Scheduled: {item['scheduled_date']}\n"
                f"ID: <code>{item['id']}</code>\n"
            )
            if content:
                msg += f"\n<i>{content[:500]}...</i>\n"
            msg += (
                f"\nReply:\n"
                f"  <code>/arachne_approve {item['id']}</code> — approve & email for posting\n"
                f"  <code>/arachne_skip {item['id']}</code> — skip this post"
            )

            _send_telegram(msg)
            update_item(item["id"], sent_for_approval=True)
            results["linkedin_notified"] += 1
        except Exception as e:
            results["errors"].append(f"LinkedIn notify {item['id']}: {e}")

    due_newsletter = get_due_items(channel="newsletter")
    for item in due_newsletter:
        if item.get("sent_for_approval"):
            continue
        try:
            from .newsletter import assemble_newsletter, get_subscriber_list
            newsletter = await assemble_newsletter(
                title=item.get("title"),
                sections=item.get("sections"),
            )
            sub_count = len(get_subscriber_list())

            msg = (
                f"<b>Arachne — Newsletter Ready</b>\n\n"
                f"<b>{item['title']}</b>\n"
                f"Sections: {', '.join(newsletter['sections_gathered'])}\n"
                f"Subscribers: {sub_count}\n"
                f"ID: <code>{item['id']}</code>\n\n"
                f"Reply:\n"
                f"  <code>/arachne_approve {item['id']}</code> — approve & send\n"
                f"  <code>/arachne_skip {item['id']}</code> — skip this month"
            )

            _send_telegram(msg)
            update_item(item["id"], sent_for_approval=True, status="pending_approval")
            results["newsletter_assembled"] = True
        except Exception as e:
            results["errors"].append(f"Newsletter assembly: {e}")

    return results


def _send_telegram(message: str) -> None:
    """Send a message to the admin Telegram chat."""
    import requests
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "") or os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        logger.warning("Telegram not configured — skipping notification")
        return
    try:
        text = message[:4000]
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        logger.warning("Telegram send failed: %s", e)
