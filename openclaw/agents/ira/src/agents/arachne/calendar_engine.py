"""
Arachne — Content Calendar Engine
==================================

Manages the content calendar: scheduling, querying, and status tracking
for LinkedIn posts and newsletters.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.agents.arachne.calendar")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent
ARACHNE_DIR = PROJECT_ROOT / "data" / "arachne"
CALENDAR_PATH = ARACHNE_DIR / "calendar.json"
DIST_LOG_PATH = ARACHNE_DIR / "distribution_log.jsonl"

_DEFAULT_ROTATION = [
    ("customer_story", "Customer story"),
    ("product_spotlight", "Product spotlight"),
    ("personal_story", "Personal / India pride"),
    ("industry_insight", "Industry insight"),
    ("technical_tip", "Technical tip"),
    ("event", "Event / announcement"),
]

LINKEDIN_SCHEDULE = {
    0: "customer_story",      # Monday
    2: "product_spotlight",   # Wednesday
    4: "personal_story",      # Friday
}


def _load_calendar() -> Dict[str, Any]:
    ARACHNE_DIR.mkdir(parents=True, exist_ok=True)
    if CALENDAR_PATH.exists():
        try:
            return json.loads(CALENDAR_PATH.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load calendar: %s", e)
    return {"items": []}


def _save_calendar(data: Dict[str, Any]) -> None:
    ARACHNE_DIR.mkdir(parents=True, exist_ok=True)
    CALENDAR_PATH.write_text(json.dumps(data, indent=2))


def _next_id(channel: str, scheduled_date: str) -> str:
    prefix = "LI" if channel == "linkedin" else "NL"
    date_part = scheduled_date.replace("-", "")
    cal = _load_calendar()
    existing = [
        it["id"] for it in cal["items"]
        if it["id"].startswith(f"{prefix}-{date_part}")
    ]
    seq = len(existing) + 1
    return f"{prefix}-{date_part}-{seq:03d}"


def schedule_item(
    channel: str,
    scheduled_date: str,
    title: str,
    content_ref: str = "",
    source: str = "",
    sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Add an item to the content calendar. Returns the created item."""
    cal = _load_calendar()
    item_id = _next_id(channel, scheduled_date)
    item = {
        "id": item_id,
        "channel": channel,
        "scheduled_date": scheduled_date,
        "status": "draft",
        "title": title,
        "content_ref": content_ref,
        "source": source,
        "approved": False,
        "sent_for_approval": False,
        "published": False,
        "created_at": datetime.utcnow().isoformat(),
    }
    if channel == "newsletter" and sections:
        item["sections"] = sections
    cal["items"].append(item)
    _save_calendar(cal)
    logger.info("Scheduled %s item %s for %s: %s", channel, item_id, scheduled_date, title)
    return item


def get_calendar_view(
    channel: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Query calendar items with optional filters."""
    cal = _load_calendar()
    items = cal["items"]

    if channel:
        items = [it for it in items if it["channel"] == channel]
    if status:
        items = [it for it in items if it.get("status") == status]
    if from_date:
        items = [it for it in items if it.get("scheduled_date", "") >= from_date]
    if to_date:
        items = [it for it in items if it.get("scheduled_date", "") <= to_date]

    return sorted(items, key=lambda x: x.get("scheduled_date", ""))


def get_item(item_id: str) -> Optional[Dict[str, Any]]:
    cal = _load_calendar()
    for it in cal["items"]:
        if it["id"] == item_id:
            return it
    return None


def update_item(item_id: str, **updates) -> Optional[Dict[str, Any]]:
    """Update fields on a calendar item. Returns updated item or None."""
    cal = _load_calendar()
    for it in cal["items"]:
        if it["id"] == item_id:
            it.update(updates)
            _save_calendar(cal)
            return it
    return None


def approve_item(item_id: str) -> Optional[Dict[str, Any]]:
    return update_item(item_id, approved=True, status="approved")


def skip_item(item_id: str) -> Optional[Dict[str, Any]]:
    return update_item(item_id, status="skipped")


def mark_published(item_id: str) -> Optional[Dict[str, Any]]:
    return update_item(item_id, published=True, status="published",
                       published_at=datetime.utcnow().isoformat())


def get_due_items(channel: Optional[str] = None) -> List[Dict[str, Any]]:
    """Items scheduled for today or earlier that haven't been published or skipped."""
    today = date.today().isoformat()
    cal = _load_calendar()
    due = []
    for it in cal["items"]:
        if it.get("published") or it.get("status") in ("skipped", "published"):
            continue
        if it.get("scheduled_date", "9999") <= today:
            if channel and it["channel"] != channel:
                continue
            due.append(it)
    return sorted(due, key=lambda x: x.get("scheduled_date", ""))


def log_distribution(item_id: str, channel: str, details: Dict[str, Any]) -> None:
    """Append a distribution event to the log."""
    ARACHNE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "item_id": item_id,
        "channel": channel,
        **details,
    }
    with open(DIST_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def get_distribution_log(limit: int = 20) -> List[Dict[str, Any]]:
    """Read recent distribution log entries."""
    if not DIST_LOG_PATH.exists():
        return []
    entries = []
    try:
        for line in DIST_LOG_PATH.read_text().strip().split("\n"):
            if line.strip():
                entries.append(json.loads(line))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read distribution log: %s", e)
    return entries[-limit:]


def auto_populate_linkedin_calendar(weeks_ahead: int = 4) -> int:
    """Fill the LinkedIn calendar with the default rotation for the next N weeks.

    Only adds slots that don't already exist. Returns count of items added.
    """
    cal = _load_calendar()
    existing_dates = {
        (it["channel"], it["scheduled_date"])
        for it in cal["items"]
    }

    added = 0
    today = date.today()
    start = today - timedelta(days=today.weekday())  # Monday of this week

    for week in range(weeks_ahead):
        for day_offset, post_type in LINKEDIN_SCHEDULE.items():
            target = start + timedelta(weeks=week, days=day_offset)
            if target < today:
                continue
            ds = target.isoformat()
            if ("linkedin", ds) in existing_dates:
                continue

            label = next(
                (lbl for pt, lbl in _DEFAULT_ROTATION if pt == post_type),
                post_type,
            )
            schedule_item(
                channel="linkedin",
                scheduled_date=ds,
                title=f"[Slot] {label}",
                source="auto_rotation",
            )
            added += 1

    return added


def schedule_next_newsletter() -> Optional[Dict[str, Any]]:
    """Schedule the next monthly newsletter if one isn't already scheduled.

    Targets the last Friday of the current month.
    """
    today = date.today()
    if today.month == 12:
        first_next = date(today.year + 1, 1, 1)
    else:
        first_next = date(today.year, today.month + 1, 1)
    last_day = first_next - timedelta(days=1)
    # Walk back to Friday (weekday 4)
    while last_day.weekday() != 4:
        last_day -= timedelta(days=1)

    target_date = last_day.isoformat()

    cal = _load_calendar()
    for it in cal["items"]:
        if it["channel"] == "newsletter" and it["scheduled_date"] == target_date:
            return it  # already scheduled

    month_name = today.strftime("%B %Y")
    return schedule_item(
        channel="newsletter",
        scheduled_date=target_date,
        title=f"{month_name} Newsletter",
        sections=["new_orders", "case_study", "product_spotlight", "event", "industry_insight"],
    )
