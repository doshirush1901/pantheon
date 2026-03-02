#!/usr/bin/env python3
"""
IRA CRM — Ira's Own Customer Relationship Manager
===================================================

One database. One source of truth. No third-party CRM needed.

Ira owns her contacts, leads, conversations, deals, and email history
in a single SQLite database. Everything the autonomous drip engine,
dream reflection, and self-evaluator need lives here.

Tables:
    contacts     — every person Ira knows (email, name, company, country)
    leads        — sales pipeline (stage, priority, source, deal value)
    conversations — email thread history per contact (for personalization)
    email_log    — every email Ira sends/receives (for reply tracking)
    deal_events  — stage changes, notes, timestamps (audit trail)

Usage:
    from ira_crm import get_crm, IraCRM

    crm = get_crm()

    # Add a contact
    crm.upsert_contact("hans@example.de", name="Hans", company="TSN", country="Germany")

    # Get leads ready for drip
    leads = crm.get_leads_ready_for_drip()

    # Log an email sent
    crm.log_email_sent("hans@example.de", subject="...", thread_id="...", stage=1)

    # Record a reply
    crm.record_reply("hans@example.de", thread_id="...", quality="engaged")

    # Get conversation context for personalization
    context = crm.get_conversation_context("hans@example.de")
"""

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger("ira.crm")

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
CRM_DB_PATH = PROJECT_ROOT / "crm" / "ira_crm.db"

DEAL_STAGES = [
    "new",          # Just added, no contact yet
    "contacted",    # First email sent
    "engaged",      # They replied with interest
    "qualified",    # Confirmed need + budget
    "proposal",     # Quote/proposal sent
    "negotiating",  # Back and forth on terms
    "won",          # Deal closed
    "lost",         # Deal lost
    "dormant",      # Gone quiet, may revive
]

LEAD_PRIORITIES = ["critical", "high", "medium", "low"]

REPLY_QUALITIES = ["engaged", "polite_decline", "auto_reply", "bounce", "unsubscribe"]

DRIP_INTERVALS_DAYS = {
    "critical": [0, 3, 7, 14, 21],
    "high":     [0, 5, 12, 21, 35],
    "medium":   [0, 7, 14, 28, 45],
    "low":      [0, 14, 30, 60, 90],
}


@dataclass
class Contact:
    email: str
    name: str = ""
    first_name: str = ""
    last_name: str = ""
    company: str = ""
    country: str = ""
    phone: str = ""
    title: str = ""
    industry: str = ""
    source: str = ""
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Lead:
    email: str
    company: str
    country: str
    priority: str = "medium"
    deal_stage: str = "new"
    deal_value: float = 0.0
    deal_currency: str = "EUR"
    drip_stage: int = 0
    last_email_sent: Optional[str] = None
    last_reply_at: Optional[str] = None
    reply_quality: str = ""
    emails_sent: int = 0
    emails_received: int = 0
    thread_id: str = ""
    tags: str = ""
    notes: str = ""
    # Joined from contacts
    name: str = ""
    first_name: str = ""
    title: str = ""
    industry: str = ""


@dataclass
class ConversationEntry:
    email: str
    direction: str  # "outbound" or "inbound"
    subject: str = ""
    preview: str = ""
    date: str = ""
    thread_id: str = ""
    source: str = ""  # "gmail", "drip", "manual"


class IraCRM:
    """
    Ira's unified CRM. Single SQLite database, clean API.
    """

    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path) if db_path else CRM_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS contacts (
                    email       TEXT PRIMARY KEY,
                    name        TEXT DEFAULT '',
                    first_name  TEXT DEFAULT '',
                    last_name   TEXT DEFAULT '',
                    company     TEXT DEFAULT '',
                    country     TEXT DEFAULT '',
                    phone       TEXT DEFAULT '',
                    title       TEXT DEFAULT '',
                    industry    TEXT DEFAULT '',
                    source      TEXT DEFAULT '',
                    notes       TEXT DEFAULT '',
                    created_at  TEXT DEFAULT (datetime('now')),
                    updated_at  TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS leads (
                    email         TEXT PRIMARY KEY REFERENCES contacts(email),
                    company       TEXT DEFAULT '',
                    country       TEXT DEFAULT '',
                    priority      TEXT DEFAULT 'medium',
                    deal_stage    TEXT DEFAULT 'new',
                    deal_value    REAL DEFAULT 0,
                    deal_currency TEXT DEFAULT 'EUR',
                    drip_stage    INTEGER DEFAULT 0,
                    last_email_sent TEXT,
                    last_reply_at   TEXT,
                    reply_quality   TEXT DEFAULT '',
                    emails_sent     INTEGER DEFAULT 0,
                    emails_received INTEGER DEFAULT 0,
                    thread_id       TEXT DEFAULT '',
                    tags            TEXT DEFAULT '',
                    notes           TEXT DEFAULT '',
                    created_at    TEXT DEFAULT (datetime('now')),
                    updated_at    TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    email     TEXT REFERENCES contacts(email),
                    direction TEXT CHECK(direction IN ('outbound', 'inbound')),
                    subject   TEXT DEFAULT '',
                    preview   TEXT DEFAULT '',
                    date      TEXT DEFAULT '',
                    thread_id TEXT DEFAULT '',
                    source    TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS email_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    email       TEXT REFERENCES contacts(email),
                    direction   TEXT CHECK(direction IN ('sent', 'received')),
                    subject     TEXT DEFAULT '',
                    body_preview TEXT DEFAULT '',
                    thread_id   TEXT DEFAULT '',
                    drip_stage  INTEGER,
                    batch_id    TEXT DEFAULT '',
                    reply_quality TEXT DEFAULT '',
                    sent_at     TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS deal_events (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    email     TEXT REFERENCES contacts(email),
                    event     TEXT,
                    old_value TEXT DEFAULT '',
                    new_value TEXT DEFAULT '',
                    notes     TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_leads_priority ON leads(priority);
                CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(deal_stage);
                CREATE INDEX IF NOT EXISTS idx_leads_drip ON leads(drip_stage);
                CREATE INDEX IF NOT EXISTS idx_conversations_email ON conversations(email);
                CREATE INDEX IF NOT EXISTS idx_email_log_email ON email_log(email);
                CREATE INDEX IF NOT EXISTS idx_email_log_thread ON email_log(thread_id);
            """)

    # =========================================================================
    # CONTACTS
    # =========================================================================

    def upsert_contact(self, email: str, **kwargs) -> bool:
        """Insert or update a contact. Pass any Contact fields as kwargs."""
        email = email.lower().strip()
        if not email or "@" not in email:
            return False

        with self._conn() as conn:
            existing = conn.execute("SELECT email FROM contacts WHERE email = ?", (email,)).fetchone()

            if existing:
                sets = []
                vals = []
                for k, v in kwargs.items():
                    if k in ("name", "first_name", "last_name", "company", "country",
                             "phone", "title", "industry", "source", "notes"):
                        if v:  # only update non-empty values
                            sets.append(f"{k} = ?")
                            vals.append(v)
                if sets:
                    sets.append("updated_at = datetime('now')")
                    vals.append(email)
                    conn.execute(f"UPDATE contacts SET {', '.join(sets)} WHERE email = ?", vals)
            else:
                fields = {"email": email}
                for k in ("name", "first_name", "last_name", "company", "country",
                           "phone", "title", "industry", "source", "notes"):
                    fields[k] = kwargs.get(k, "")
                cols = ", ".join(fields.keys())
                placeholders = ", ".join("?" for _ in fields)
                conn.execute(f"INSERT INTO contacts ({cols}) VALUES ({placeholders})", list(fields.values()))

        return True

    def get_contact(self, email: str) -> Optional[Contact]:
        email = email.lower().strip()
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM contacts WHERE email = ?", (email,)).fetchone()
            if row:
                return Contact(**dict(row))
        return None

    def search_contacts(self, query: str, limit: int = 20) -> List[Contact]:
        q = f"%{query.lower()}%"
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM contacts WHERE lower(email) LIKE ? OR lower(name) LIKE ? "
                "OR lower(company) LIKE ? OR lower(country) LIKE ? LIMIT ?",
                (q, q, q, q, limit)
            ).fetchall()
            return [Contact(**dict(r)) for r in rows]

    def get_all_contacts(self) -> List[Contact]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM contacts ORDER BY company, name").fetchall()
            return [Contact(**dict(r)) for r in rows]

    # =========================================================================
    # LEADS
    # =========================================================================

    def upsert_lead(self, email: str, **kwargs) -> bool:
        """Insert or update a lead. Contact must exist first."""
        email = email.lower().strip()

        # Auto-create contact if needed
        contact_fields = {}
        for k in ("name", "first_name", "last_name", "company", "country",
                   "phone", "title", "industry", "source"):
            if k in kwargs:
                contact_fields[k] = kwargs.pop(k)
        if contact_fields:
            self.upsert_contact(email, **contact_fields)
        elif not self.get_contact(email):
            self.upsert_contact(email, company=kwargs.get("company", ""), country=kwargs.get("country", ""))

        with self._conn() as conn:
            existing = conn.execute("SELECT email FROM leads WHERE email = ?", (email,)).fetchone()

            if existing:
                sets = []
                vals = []
                for k, v in kwargs.items():
                    if k in ("company", "country", "priority", "deal_stage", "deal_value",
                             "deal_currency", "drip_stage", "last_email_sent", "last_reply_at",
                             "reply_quality", "emails_sent", "emails_received", "thread_id",
                             "tags", "notes"):
                        sets.append(f"{k} = ?")
                        vals.append(v)
                if sets:
                    sets.append("updated_at = datetime('now')")
                    vals.append(email)
                    conn.execute(f"UPDATE leads SET {', '.join(sets)} WHERE email = ?", vals)
            else:
                fields = {"email": email}
                for k in ("company", "country", "priority", "deal_stage", "deal_value",
                           "deal_currency", "drip_stage", "tags", "notes"):
                    fields[k] = kwargs.get(k, {"deal_value": 0, "drip_stage": 0}.get(k, ""))
                if not fields.get("company"):
                    c = self.get_contact(email)
                    if c:
                        fields["company"] = c.company
                        fields["country"] = fields.get("country") or c.country
                cols = ", ".join(fields.keys())
                placeholders = ", ".join("?" for _ in fields)
                conn.execute(f"INSERT INTO leads ({cols}) VALUES ({placeholders})", list(fields.values()))

        return True

    def get_lead(self, email: str) -> Optional[Lead]:
        email = email.lower().strip()
        with self._conn() as conn:
            row = conn.execute("""
                SELECT l.*, c.name, c.first_name, c.title, c.industry
                FROM leads l JOIN contacts c ON l.email = c.email
                WHERE l.email = ?
            """, (email,)).fetchone()
            if row:
                return Lead(**{k: row[k] for k in row.keys() if k in Lead.__dataclass_fields__})
        return None

    def get_leads_ready_for_drip(self, max_results: int = 20) -> List[Lead]:
        """Get leads that are due for their next drip email."""
        now = datetime.now()
        results = []

        with self._conn() as conn:
            rows = conn.execute("""
                SELECT l.*, c.name, c.first_name, c.title, c.industry
                FROM leads l JOIN contacts c ON l.email = c.email
                WHERE l.deal_stage NOT IN ('won', 'lost')
                  AND l.reply_quality NOT IN ('unsubscribe', 'bounce')
                  AND l.drip_stage < 5
                ORDER BY
                    CASE l.priority
                        WHEN 'critical' THEN 0
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                    END,
                    l.company
            """).fetchall()

            for row in rows:
                lead = Lead(**{k: row[k] for k in row.keys() if k in Lead.__dataclass_fields__})
                intervals = DRIP_INTERVALS_DAYS.get(lead.priority, DRIP_INTERVALS_DAYS["medium"])

                if lead.last_email_sent is None:
                    results.append(lead)
                else:
                    try:
                        last_sent = datetime.fromisoformat(lead.last_email_sent)
                        idx = min(lead.drip_stage, len(intervals) - 1)
                        wait_days = intervals[idx]
                        if (now - last_sent).days >= wait_days:
                            results.append(lead)
                    except (ValueError, TypeError):
                        results.append(lead)

                if len(results) >= max_results:
                    break

        return results

    def get_leads_by_stage(self, stage: str) -> List[Lead]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT l.*, c.name, c.first_name, c.title, c.industry
                FROM leads l JOIN contacts c ON l.email = c.email
                WHERE l.deal_stage = ?
                ORDER BY l.priority, l.company
            """, (stage,)).fetchall()
            return [Lead(**{k: r[k] for k in r.keys() if k in Lead.__dataclass_fields__}) for r in rows]

    def get_all_leads(self) -> List[Lead]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT l.*, c.name, c.first_name, c.title, c.industry
                FROM leads l JOIN contacts c ON l.email = c.email
                ORDER BY
                    CASE l.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END,
                    l.company
            """).fetchall()
            return [Lead(**{k: r[k] for k in r.keys() if k in Lead.__dataclass_fields__}) for r in rows]

    # =========================================================================
    # EMAIL TRACKING
    # =========================================================================

    def log_email_sent(self, email: str, subject: str, thread_id: str = "",
                       drip_stage: int = None, batch_id: str = "", body_preview: str = ""):
        """Log an outbound drip email."""
        email = email.lower().strip()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO email_log (email, direction, subject, body_preview, thread_id, drip_stage, batch_id) "
                "VALUES (?, 'sent', ?, ?, ?, ?, ?)",
                (email, subject, body_preview[:500], thread_id, drip_stage, batch_id)
            )
            conn.execute(
                "UPDATE leads SET emails_sent = emails_sent + 1, last_email_sent = datetime('now'), "
                "drip_stage = COALESCE(?, drip_stage), thread_id = COALESCE(NULLIF(?, ''), thread_id), "
                "deal_stage = CASE WHEN deal_stage = 'new' THEN 'contacted' ELSE deal_stage END, "
                "updated_at = datetime('now') WHERE email = ?",
                (drip_stage, thread_id, email)
            )

    def record_reply(self, email: str, thread_id: str = "", quality: str = "engaged",
                     subject: str = "", preview: str = ""):
        """Record an inbound reply from a lead."""
        email = email.lower().strip()
        now = datetime.now().isoformat()

        with self._conn() as conn:
            conn.execute(
                "INSERT INTO email_log (email, direction, subject, body_preview, thread_id, reply_quality) "
                "VALUES (?, 'received', ?, ?, ?, ?)",
                (email, subject, preview[:500], thread_id, quality)
            )
            # Update lead
            new_stage = "engaged" if quality == "engaged" else None
            conn.execute(
                "UPDATE leads SET emails_received = emails_received + 1, "
                "last_reply_at = ?, reply_quality = ?, "
                "deal_stage = CASE WHEN ? = 'engaged' AND deal_stage IN ('new', 'contacted') "
                "  THEN 'engaged' ELSE deal_stage END, "
                "updated_at = datetime('now') WHERE email = ?",
                (now, quality, quality, email)
            )

        # Add to conversations
        self.add_conversation(email, "inbound", subject=subject, preview=preview,
                              thread_id=thread_id, source="reply")

    def update_deal_stage(self, email: str, new_stage: str, notes: str = ""):
        """Move a lead to a new deal stage."""
        email = email.lower().strip()
        if new_stage not in DEAL_STAGES:
            return False

        with self._conn() as conn:
            old = conn.execute("SELECT deal_stage FROM leads WHERE email = ?", (email,)).fetchone()
            old_stage = old["deal_stage"] if old else "unknown"

            conn.execute(
                "UPDATE leads SET deal_stage = ?, updated_at = datetime('now') WHERE email = ?",
                (new_stage, email)
            )
            conn.execute(
                "INSERT INTO deal_events (email, event, old_value, new_value, notes) "
                "VALUES (?, 'stage_change', ?, ?, ?)",
                (email, old_stage, new_stage, notes)
            )
        return True

    # =========================================================================
    # CONVERSATIONS (for drip personalization)
    # =========================================================================

    def add_conversation(self, email: str, direction: str, subject: str = "",
                         preview: str = "", date: str = "", thread_id: str = "",
                         source: str = ""):
        email = email.lower().strip()
        if not date:
            date = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO conversations (email, direction, subject, preview, date, thread_id, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (email, direction, subject, preview[:500], date, thread_id, source)
            )

    def get_conversation_context(self, email: str, limit: int = 10) -> List[ConversationEntry]:
        """Get recent conversation history for personalization."""
        email = email.lower().strip()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE email = ? ORDER BY date DESC LIMIT ?",
                (email, limit)
            ).fetchall()
            return [ConversationEntry(**{
                k: r[k] for k in ("email", "direction", "subject", "preview", "date", "thread_id", "source")
            }) for r in rows]

    def get_conversation_summary(self, email: str) -> Optional[str]:
        """Get a natural language summary of past interactions for email personalization."""
        entries = self.get_conversation_context(email, limit=20)
        if not entries:
            return None

        inbound = [e for e in entries if e.direction == "inbound"]
        outbound = [e for e in entries if e.direction == "outbound"]

        parts = []
        if inbound:
            parts.append(f"We've exchanged {len(inbound)} replies")
            latest = inbound[0]
            if latest.date:
                try:
                    d = datetime.fromisoformat(latest.date.replace("Z", "+00:00")).strftime("%B %Y")
                    parts[-1] += f" (last: {d})"
                except (ValueError, AttributeError):
                    pass
            # Check for topics
            all_subjects = " ".join(e.subject.lower() for e in inbound)
            if "quote" in all_subjects or "price" in all_subjects:
                parts.append("You showed interest in our pricing")
            elif "machine" in all_subjects or "spec" in all_subjects:
                parts.append("We discussed machine requirements")
        elif outbound:
            parts.append(f"We reached out previously ({len(outbound)} emails)")

        if not parts:
            return None
        return ". ".join(parts) + "."

    # =========================================================================
    # STATS & REPORTING
    # =========================================================================

    def get_pipeline_stats(self) -> Dict[str, Any]:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) as n FROM leads").fetchone()["n"]
            by_stage = {}
            for row in conn.execute("SELECT deal_stage, COUNT(*) as n FROM leads GROUP BY deal_stage"):
                by_stage[row["deal_stage"]] = row["n"]
            by_priority = {}
            for row in conn.execute("SELECT priority, COUNT(*) as n FROM leads GROUP BY priority"):
                by_priority[row["priority"]] = row["n"]

            total_sent = conn.execute("SELECT COALESCE(SUM(emails_sent), 0) as n FROM leads").fetchone()["n"]
            total_received = conn.execute("SELECT COALESCE(SUM(emails_received), 0) as n FROM leads").fetchone()["n"]
            reply_rate = total_received / total_sent if total_sent > 0 else 0

            return {
                "total_leads": total,
                "by_stage": by_stage,
                "by_priority": by_priority,
                "total_emails_sent": total_sent,
                "total_replies": total_received,
                "reply_rate": round(reply_rate, 4),
            }

    def get_drip_stats(self) -> Dict[str, Any]:
        with self._conn() as conn:
            ready = len(self.get_leads_ready_for_drip())
            engaged = conn.execute(
                "SELECT COUNT(*) as n FROM leads WHERE reply_quality = 'engaged'"
            ).fetchone()["n"]
            bounced = conn.execute(
                "SELECT COUNT(*) as n FROM leads WHERE reply_quality = 'bounce'"
            ).fetchone()["n"]
            unsub = conn.execute(
                "SELECT COUNT(*) as n FROM leads WHERE reply_quality = 'unsubscribe'"
            ).fetchone()["n"]

            return {
                "ready_for_drip": ready,
                "engaged": engaged,
                "bounced": bounced,
                "unsubscribed": unsub,
            }


# Singleton
_crm: Optional[IraCRM] = None


def get_crm(db_path: str = None) -> IraCRM:
    global _crm
    if _crm is None:
        _crm = IraCRM(db_path)
    return _crm


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Ira CRM")
    parser.add_argument("--stats", action="store_true", help="Show pipeline stats")
    parser.add_argument("--leads", action="store_true", help="List all leads")
    parser.add_argument("--ready", action="store_true", help="Show leads ready for drip")
    parser.add_argument("--search", type=str, help="Search contacts")
    parser.add_argument("--contact", type=str, help="Show contact details")
    args = parser.parse_args()

    crm = get_crm()

    if args.stats:
        stats = crm.get_pipeline_stats()
        print(json.dumps(stats, indent=2))
    elif args.leads:
        for lead in crm.get_all_leads():
            print(f"  [{lead.priority:8s}] {lead.company:40s} {lead.email:35s} stage={lead.deal_stage} drip={lead.drip_stage}")
    elif args.ready:
        for lead in crm.get_leads_ready_for_drip():
            print(f"  [{lead.priority:8s}] {lead.company:40s} {lead.email:35s} drip_stage={lead.drip_stage}")
    elif args.search:
        for c in crm.search_contacts(args.search):
            print(f"  {c.name:30s} {c.email:35s} {c.company}")
    elif args.contact:
        c = crm.get_contact(args.contact)
        if c:
            print(json.dumps(c.__dict__, indent=2))
        else:
            print(f"Contact not found: {args.contact}")
    else:
        parser.print_help()
