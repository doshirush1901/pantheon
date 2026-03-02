#!/usr/bin/env python3
"""
TAKEOUT INGEST - Email Ingestion Stats & Management
====================================================

Provides stats and management commands for email/document ingestion.

Commands:
    /takeout status   → Basic ingestion stats
    /takeout stats    → Detailed stats with domains/events
    /takeout domains  → Top email domains
    /takeout events   → Event type breakdown
    /takeout runs     → Recent ingestion runs
"""

import json
import logging
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from config import PROJECT_ROOT
except ImportError:
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent

KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"
AUDIT_LOG = KNOWLEDGE_DIR / "audit.jsonl"
INGESTED_HASHES = KNOWLEDGE_DIR / "ingested_hashes.json"
CHAT_LOG = PROJECT_ROOT / "data" / "chat_log"
EMAILS_KNOWLEDGE = PROJECT_ROOT / "data" / "emails_knowledge.json"


def _load_audit_entries() -> List[Dict]:
    """Load audit log entries."""
    entries = []
    if not AUDIT_LOG.exists():
        return entries
    try:
        for line in AUDIT_LOG.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except IOError:
        pass
    return entries


def _load_ingested_hashes() -> Dict:
    """Load ingested document hashes."""
    if not INGESTED_HASHES.exists():
        return {}
    try:
        return json.loads(INGESTED_HASHES.read_text())
    except (json.JSONDecodeError, IOError):
        return {}


def _count_knowledge_files() -> Dict[str, int]:
    """Count knowledge JSON files and their entries."""
    counts = {}
    if not KNOWLEDGE_DIR.exists():
        return counts
    for f in KNOWLEDGE_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            if isinstance(data, list):
                counts[f.stem] = len(data)
            elif isinstance(data, dict):
                counts[f.stem] = len(data.get("entries", data.get("items", [1])))
        except (json.JSONDecodeError, IOError):
            counts[f.stem] = 0
    return counts


def _get_email_domains(entries: List[Dict]) -> Counter:
    """Extract email domains from audit entries."""
    domains = Counter()
    for entry in entries:
        source = entry.get("source", "") or entry.get("source_file", "")
        if "@" in source:
            domain = source.split("@")[-1].lower()
            domains[domain] += 1
        elif "domain" in entry:
            domains[entry["domain"]] += 1
    return domains


def _get_event_types(entries: List[Dict]) -> Counter:
    """Count event types from audit entries."""
    types = Counter()
    for entry in entries:
        event_type = entry.get("type", entry.get("action", "unknown"))
        types[event_type] += 1
    return types


def handle_takeout_command(text: str) -> str:
    """
    Main entry point for /takeout commands.

    Args:
        text: Full command text (e.g. "/takeout status")

    Returns:
        Formatted response string for Telegram
    """
    parts = text.strip().split()
    subcommand = parts[1].lower() if len(parts) > 1 else "status"

    if subcommand == "status":
        return _handle_status()
    elif subcommand == "stats":
        return _handle_detailed_stats()
    elif subcommand == "domains":
        return _handle_domains()
    elif subcommand == "events":
        return _handle_events()
    elif subcommand == "runs":
        return _handle_runs()
    else:
        return (
            "📧 **Takeout Commands**\n\n"
            "• `/takeout status` — Basic ingestion stats\n"
            "• `/takeout stats` — Detailed stats\n"
            "• `/takeout domains` — Top email domains\n"
            "• `/takeout events` — Event type breakdown\n"
            "• `/takeout runs` — Recent ingestion runs\n"
        )


def _handle_status() -> str:
    """Basic ingestion status."""
    hashes = _load_ingested_hashes()
    hash_count = hashes.get("count", len(hashes)) if isinstance(hashes, dict) else 0
    entries = _load_audit_entries()
    knowledge_files = _count_knowledge_files()

    total_knowledge = sum(knowledge_files.values())

    return (
        f"📧 **Ingestion Status**\n\n"
        f"• Documents ingested: **{hash_count}**\n"
        f"• Audit log entries: **{len(entries)}**\n"
        f"• Knowledge files: **{len(knowledge_files)}**\n"
        f"• Total knowledge entries: **{total_knowledge}**\n"
    )


def _handle_detailed_stats() -> str:
    """Detailed stats with domains and events."""
    entries = _load_audit_entries()
    domains = _get_email_domains(entries)
    events = _get_event_types(entries)
    knowledge_files = _count_knowledge_files()

    lines = ["📊 **Detailed Ingestion Stats**\n"]

    lines.append(f"**Audit entries:** {len(entries)}")

    if domains:
        lines.append(f"\n**Top Domains ({len(domains)} total):**")
        for domain, count in domains.most_common(5):
            lines.append(f"  • {domain}: {count}")

    if events:
        lines.append(f"\n**Event Types ({len(events)} total):**")
        for event, count in events.most_common(5):
            lines.append(f"  • {event}: {count}")

    if knowledge_files:
        lines.append(f"\n**Knowledge Files:**")
        for name, count in sorted(knowledge_files.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  • {name}: {count} entries")

    return "\n".join(lines)


def _handle_domains() -> str:
    """Top email domains."""
    entries = _load_audit_entries()
    domains = _get_email_domains(entries)

    if not domains:
        return "📧 No email domain data found in audit log."

    lines = [f"📧 **Top Email Domains** ({len(domains)} total)\n"]
    for domain, count in domains.most_common(10):
        lines.append(f"  • {domain}: {count}")

    return "\n".join(lines)


def _handle_events() -> str:
    """Event type breakdown."""
    entries = _load_audit_entries()
    events = _get_event_types(entries)

    if not events:
        return "📊 No event data found in audit log."

    lines = [f"📊 **Event Types** ({len(events)} total)\n"]
    for event, count in events.most_common(15):
        lines.append(f"  • {event}: {count}")

    return "\n".join(lines)


def _handle_runs() -> str:
    """Recent ingestion runs."""
    entries = _load_audit_entries()

    ingestion_runs = [
        e for e in entries
        if e.get("type") in ("ingest", "ingestion", "document_ingested", "batch_ingest")
        or "ingest" in e.get("action", "").lower()
    ]

    if not ingestion_runs:
        all_entries = entries[-10:] if entries else []
        if not all_entries:
            return "📋 No ingestion runs found in audit log."

        lines = ["📋 **Recent Audit Entries** (last 10)\n"]
        for entry in reversed(all_entries):
            ts = entry.get("timestamp", entry.get("created_at", "?"))
            action = entry.get("type", entry.get("action", "unknown"))
            source = entry.get("source", entry.get("source_file", ""))
            lines.append(f"  • {ts[:16]} | {action} | {source}")
        return "\n".join(lines)

    recent = ingestion_runs[-10:]
    lines = [f"📋 **Recent Ingestion Runs** ({len(ingestion_runs)} total, showing last {len(recent)})\n"]
    for run in reversed(recent):
        ts = run.get("timestamp", run.get("created_at", "?"))
        source = run.get("source", run.get("source_file", "unknown"))
        count = run.get("count", run.get("items", "?"))
        lines.append(f"  • {ts[:16]} | {source} | {count} items")

    return "\n".join(lines)
