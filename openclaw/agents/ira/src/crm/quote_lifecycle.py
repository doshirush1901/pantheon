#!/usr/bin/env python3
"""
QUOTE LIFECYCLE TRACKER
========================

Tracks quotes through their lifecycle: Draft → Sent → Follow-up → Won/Lost

Usage:
    from quote_lifecycle import QuoteTracker, get_tracker
    
    tracker = get_tracker()
    
    # Record a new quote
    tracker.record_quote_sent(
        quote_id="PF1-C-3020-001",
        customer_email="john@acme.com",
        product="PF1-C-3020",
        amount=45000,
        currency="USD"
    )
    
    # Record a follow-up
    tracker.record_follow_up("PF1-C-3020-001", "email", "Sent pricing clarification")
    
    # Mark as won/lost
    tracker.mark_won("PF1-C-3020-001", final_amount=43000)
    tracker.mark_lost("PF1-C-3020-001", reason="Chose competitor")
    
    # Get pipeline view
    pipeline = tracker.get_pipeline()
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from contextlib import contextmanager

SKILL_DIR = Path(__file__).parent  # src/crm
SRC_DIR = SKILL_DIR.parent  # src
PROJECT_ROOT = SRC_DIR.parent  # /Users/rushabhdoshi/Desktop/Ira

# Load env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

# Database path
CRM_DIR = PROJECT_ROOT / "crm"
CRM_DIR.mkdir(exist_ok=True)
QUOTES_DB = CRM_DIR / "quotes.db"


class QuoteStatus(Enum):
    """Quote lifecycle stages."""
    DRAFT = "draft"
    SENT = "sent"
    FOLLOW_UP = "follow_up"
    NEGOTIATING = "negotiating"
    WON = "won"
    LOST = "lost"
    EXPIRED = "expired"


class FollowUpType(Enum):
    """Types of follow-up actions."""
    EMAIL = "email"
    CALL = "call"
    TELEGRAM = "telegram"
    MEETING = "meeting"
    REVISED_QUOTE = "revised_quote"


@dataclass
class Quote:
    """A quote record."""
    quote_id: str
    customer_email: str
    customer_name: Optional[str] = None
    company: Optional[str] = None
    product: str = ""
    amount: float = 0.0
    currency: str = "USD"
    status: QuoteStatus = QuoteStatus.DRAFT
    created_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    last_follow_up: Optional[datetime] = None
    follow_up_count: int = 0
    closed_at: Optional[datetime] = None
    final_amount: Optional[float] = None
    lost_reason: Optional[str] = None
    notes: str = ""
    thread_id: Optional[str] = None  # Email thread ID
    
    def days_since_sent(self) -> Optional[int]:
        """Days since quote was sent."""
        if self.sent_at:
            return (datetime.now() - self.sent_at).days
        return None
    
    def days_since_follow_up(self) -> Optional[int]:
        """Days since last follow-up."""
        if self.last_follow_up:
            return (datetime.now() - self.last_follow_up).days
        elif self.sent_at:
            return (datetime.now() - self.sent_at).days
        return None
    
    def is_stale(self, days: int = 7) -> bool:
        """Check if quote needs follow-up."""
        if self.status in [QuoteStatus.WON, QuoteStatus.LOST, QuoteStatus.EXPIRED]:
            return False
        days_inactive = self.days_since_follow_up()
        return days_inactive is not None and days_inactive >= days
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "quote_id": self.quote_id,
            "customer_email": self.customer_email,
            "customer_name": self.customer_name,
            "company": self.company,
            "product": self.product,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "last_follow_up": self.last_follow_up.isoformat() if self.last_follow_up else None,
            "follow_up_count": self.follow_up_count,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "final_amount": self.final_amount,
            "lost_reason": self.lost_reason,
            "notes": self.notes,
            "thread_id": self.thread_id,
            "days_since_sent": self.days_since_sent(),
            "days_since_follow_up": self.days_since_follow_up(),
            "is_stale": self.is_stale(),
        }


@dataclass
class FollowUp:
    """A follow-up action on a quote."""
    id: int
    quote_id: str
    follow_up_type: FollowUpType
    notes: str
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "quote_id": self.quote_id,
            "type": self.follow_up_type.value,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PipelineStats:
    """Quote pipeline statistics."""
    total_quotes: int = 0
    draft: int = 0
    sent: int = 0
    follow_up: int = 0
    negotiating: int = 0
    won: int = 0
    lost: int = 0
    expired: int = 0
    stale_quotes: int = 0
    total_pipeline_value: float = 0.0
    won_value: float = 0.0
    lost_value: float = 0.0
    conversion_rate: float = 0.0
    avg_days_to_close: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class QuoteTracker:
    """
    Tracks quotes through their lifecycle.
    
    Provides:
    - Quote creation and status updates
    - Follow-up tracking
    - Pipeline analytics
    - Stale quote detection
    """
    
    SCHEMA_VERSION = 1
    
    SCHEMA_MIGRATIONS = {
        1: [
            '''CREATE TABLE IF NOT EXISTS quotes (
                quote_id TEXT PRIMARY KEY,
                customer_email TEXT NOT NULL,
                customer_name TEXT,
                company TEXT,
                product TEXT,
                amount REAL DEFAULT 0,
                currency TEXT DEFAULT 'USD',
                status TEXT DEFAULT 'draft',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                sent_at TEXT,
                last_follow_up TEXT,
                follow_up_count INTEGER DEFAULT 0,
                closed_at TEXT,
                final_amount REAL,
                lost_reason TEXT,
                notes TEXT,
                thread_id TEXT
            )''',
            "CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes(status)",
            "CREATE INDEX IF NOT EXISTS idx_quotes_customer ON quotes(customer_email)",
            "CREATE INDEX IF NOT EXISTS idx_quotes_sent ON quotes(sent_at)",
            '''CREATE TABLE IF NOT EXISTS follow_ups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id TEXT NOT NULL,
                follow_up_type TEXT NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quote_id) REFERENCES quotes(quote_id)
            )''',
            "CREATE INDEX IF NOT EXISTS idx_followups_quote ON follow_ups(quote_id)",
            '''CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL
            )''',
        ],
    }
    
    def __init__(self, db_path: Path = QUOTES_DB):
        self.db_path = db_path
        self._ensure_schema()
    
    @contextmanager
    def _get_conn(self):
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _ensure_schema(self):
        """Ensure database schema is up to date."""
        with self._get_conn() as conn:
            # Check current version
            try:
                row = conn.execute("SELECT version FROM schema_version WHERE id = 1").fetchone()
                current_version = row['version'] if row else 0
            except sqlite3.OperationalError:
                current_version = 0
            
            # Apply migrations
            for version in range(current_version + 1, self.SCHEMA_VERSION + 1):
                if version in self.SCHEMA_MIGRATIONS:
                    for sql in self.SCHEMA_MIGRATIONS[version]:
                        conn.execute(sql)
                    
                    if current_version == 0:
                        conn.execute("INSERT INTO schema_version (id, version) VALUES (1, ?)", (version,))
                    else:
                        conn.execute("UPDATE schema_version SET version = ? WHERE id = 1", (version,))
    
    def record_quote_sent(
        self,
        quote_id: str,
        customer_email: str,
        product: str,
        amount: float,
        currency: str = "USD",
        customer_name: Optional[str] = None,
        company: Optional[str] = None,
        thread_id: Optional[str] = None,
        notes: str = "",
    ) -> Quote:
        """Record a quote being sent to a customer."""
        now = datetime.now()
        
        with self._get_conn() as conn:
            # Check if quote exists
            existing = conn.execute(
                "SELECT * FROM quotes WHERE quote_id = ?", (quote_id,)
            ).fetchone()
            
            if existing:
                # Update existing quote
                conn.execute("""
                    UPDATE quotes SET
                        status = 'sent',
                        sent_at = ?,
                        amount = ?,
                        currency = ?,
                        customer_name = COALESCE(?, customer_name),
                        company = COALESCE(?, company),
                        thread_id = COALESCE(?, thread_id),
                        notes = COALESCE(?, notes)
                    WHERE quote_id = ?
                """, (now.isoformat(), amount, currency, customer_name, company, 
                      thread_id, notes, quote_id))
            else:
                # Create new quote
                conn.execute("""
                    INSERT INTO quotes (
                        quote_id, customer_email, customer_name, company, product,
                        amount, currency, status, created_at, sent_at, thread_id, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'sent', ?, ?, ?, ?)
                """, (quote_id, customer_email, customer_name, company, product,
                      amount, currency, now.isoformat(), now.isoformat(), thread_id, notes))
        
        return self.get_quote(quote_id)
    
    def record_follow_up(
        self,
        quote_id: str,
        follow_up_type: str,
        notes: str = "",
    ) -> Optional[FollowUp]:
        """Record a follow-up action on a quote."""
        now = datetime.now()
        
        # Convert string to enum
        try:
            fu_type = FollowUpType(follow_up_type.lower())
        except ValueError:
            fu_type = FollowUpType.EMAIL
        
        with self._get_conn() as conn:
            # Check quote exists
            quote = conn.execute(
                "SELECT * FROM quotes WHERE quote_id = ?", (quote_id,)
            ).fetchone()
            
            if not quote:
                return None
            
            # Insert follow-up
            cursor = conn.execute("""
                INSERT INTO follow_ups (quote_id, follow_up_type, notes, created_at)
                VALUES (?, ?, ?, ?)
            """, (quote_id, fu_type.value, notes, now.isoformat()))
            
            # Update quote
            new_status = "follow_up" if quote['status'] == "sent" else quote['status']
            if new_status not in ["won", "lost", "expired"]:
                new_status = "follow_up"
            
            conn.execute("""
                UPDATE quotes SET
                    status = ?,
                    last_follow_up = ?,
                    follow_up_count = follow_up_count + 1
                WHERE quote_id = ?
            """, (new_status, now.isoformat(), quote_id))
            
            return FollowUp(
                id=cursor.lastrowid,
                quote_id=quote_id,
                follow_up_type=fu_type,
                notes=notes,
                created_at=now,
            )
    
    def mark_won(
        self,
        quote_id: str,
        final_amount: Optional[float] = None,
        notes: str = "",
    ) -> Optional[Quote]:
        """Mark a quote as won."""
        now = datetime.now()
        
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE quotes SET
                    status = 'won',
                    closed_at = ?,
                    final_amount = COALESCE(?, amount),
                    notes = CASE WHEN ? != '' THEN notes || '\n' || ? ELSE notes END
                WHERE quote_id = ?
            """, (now.isoformat(), final_amount, notes, notes, quote_id))
        
        return self.get_quote(quote_id)
    
    def mark_lost(
        self,
        quote_id: str,
        reason: str = "",
        notes: str = "",
    ) -> Optional[Quote]:
        """Mark a quote as lost."""
        now = datetime.now()
        
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE quotes SET
                    status = 'lost',
                    closed_at = ?,
                    lost_reason = ?,
                    notes = CASE WHEN ? != '' THEN notes || '\n' || ? ELSE notes END
                WHERE quote_id = ?
            """, (now.isoformat(), reason, notes, notes, quote_id))
        
        return self.get_quote(quote_id)
    
    def mark_expired(self, quote_id: str) -> Optional[Quote]:
        """Mark a quote as expired."""
        now = datetime.now()
        
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE quotes SET
                    status = 'expired',
                    closed_at = ?
                WHERE quote_id = ?
            """, (now.isoformat(), quote_id))
        
        return self.get_quote(quote_id)
    
    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Get a quote by ID."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM quotes WHERE quote_id = ?", (quote_id,)
            ).fetchone()
            
            if not row:
                return None
            
            return self._row_to_quote(row)
    
    def get_quotes_for_customer(self, customer_email: str) -> List[Quote]:
        """Get all quotes for a customer."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM quotes WHERE customer_email = ? ORDER BY created_at DESC",
                (customer_email,)
            ).fetchall()
            
            return [self._row_to_quote(row) for row in rows]
    
    def get_active_quotes(self) -> List[Quote]:
        """Get all active (non-closed) quotes."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM quotes 
                WHERE status NOT IN ('won', 'lost', 'expired')
                ORDER BY sent_at DESC
            """).fetchall()
            
            return [self._row_to_quote(row) for row in rows]
    
    def get_stale_quotes(self, days: int = 7) -> List[Quote]:
        """Get quotes that need follow-up."""
        cutoff = datetime.now() - timedelta(days=days)
        
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM quotes 
                WHERE status NOT IN ('won', 'lost', 'expired')
                  AND (
                      (last_follow_up IS NOT NULL AND last_follow_up < ?)
                      OR (last_follow_up IS NULL AND sent_at IS NOT NULL AND sent_at < ?)
                  )
                ORDER BY COALESCE(last_follow_up, sent_at) ASC
            """, (cutoff.isoformat(), cutoff.isoformat())).fetchall()
            
            return [self._row_to_quote(row) for row in rows]
    
    def get_follow_ups(self, quote_id: str) -> List[FollowUp]:
        """Get follow-up history for a quote."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM follow_ups 
                WHERE quote_id = ?
                ORDER BY created_at DESC
            """, (quote_id,)).fetchall()
            
            return [
                FollowUp(
                    id=row['id'],
                    quote_id=row['quote_id'],
                    follow_up_type=FollowUpType(row['follow_up_type']),
                    notes=row['notes'] or "",
                    created_at=datetime.fromisoformat(row['created_at']),
                )
                for row in rows
            ]
    
    def get_pipeline_stats(self, days: int = 90) -> PipelineStats:
        """Get pipeline statistics."""
        cutoff = datetime.now() - timedelta(days=days)
        stats = PipelineStats()
        
        with self._get_conn() as conn:
            # Count by status
            for status in QuoteStatus:
                count = conn.execute(
                    "SELECT COUNT(*) as cnt FROM quotes WHERE status = ?",
                    (status.value,)
                ).fetchone()['cnt']
                setattr(stats, status.value, count)
            
            # Total quotes
            stats.total_quotes = sum([
                stats.draft, stats.sent, stats.follow_up, 
                stats.negotiating, stats.won, stats.lost, stats.expired
            ])
            
            # Stale quotes
            stale = self.get_stale_quotes()
            stats.stale_quotes = len(stale)
            
            # Pipeline value (active quotes)
            pipeline_value = conn.execute("""
                SELECT COALESCE(SUM(amount), 0) as total
                FROM quotes 
                WHERE status NOT IN ('won', 'lost', 'expired')
            """).fetchone()['total']
            stats.total_pipeline_value = pipeline_value
            
            # Won value
            won_value = conn.execute("""
                SELECT COALESCE(SUM(COALESCE(final_amount, amount)), 0) as total
                FROM quotes 
                WHERE status = 'won' AND closed_at > ?
            """, (cutoff.isoformat(),)).fetchone()['total']
            stats.won_value = won_value
            
            # Lost value
            lost_value = conn.execute("""
                SELECT COALESCE(SUM(amount), 0) as total
                FROM quotes 
                WHERE status = 'lost' AND closed_at > ?
            """, (cutoff.isoformat(),)).fetchone()['total']
            stats.lost_value = lost_value
            
            # Conversion rate
            closed_quotes = stats.won + stats.lost
            if closed_quotes > 0:
                stats.conversion_rate = (stats.won / closed_quotes) * 100
            
            # Average days to close
            avg_days = conn.execute("""
                SELECT AVG(
                    JULIANDAY(closed_at) - JULIANDAY(sent_at)
                ) as avg_days
                FROM quotes 
                WHERE status IN ('won', 'lost') 
                  AND sent_at IS NOT NULL 
                  AND closed_at IS NOT NULL
                  AND closed_at > ?
            """, (cutoff.isoformat(),)).fetchone()['avg_days']
            stats.avg_days_to_close = avg_days or 0
        
        return stats
    
    def _row_to_quote(self, row: sqlite3.Row) -> Quote:
        """Convert database row to Quote object."""
        return Quote(
            quote_id=row['quote_id'],
            customer_email=row['customer_email'],
            customer_name=row['customer_name'],
            company=row['company'],
            product=row['product'] or "",
            amount=row['amount'] or 0,
            currency=row['currency'] or "USD",
            status=QuoteStatus(row['status']),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            sent_at=datetime.fromisoformat(row['sent_at']) if row['sent_at'] else None,
            last_follow_up=datetime.fromisoformat(row['last_follow_up']) if row['last_follow_up'] else None,
            follow_up_count=row['follow_up_count'] or 0,
            closed_at=datetime.fromisoformat(row['closed_at']) if row['closed_at'] else None,
            final_amount=row['final_amount'],
            lost_reason=row['lost_reason'],
            notes=row['notes'] or "",
            thread_id=row['thread_id'],
        )


# Singleton
_tracker: Optional[QuoteTracker] = None


def get_tracker() -> QuoteTracker:
    """Get singleton quote tracker."""
    global _tracker
    if _tracker is None:
        _tracker = QuoteTracker()
    return _tracker


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Quote Lifecycle Tracker")
    parser.add_argument("--pipeline", action="store_true", help="Show pipeline stats")
    parser.add_argument("--stale", action="store_true", help="Show stale quotes")
    parser.add_argument("--active", action="store_true", help="Show active quotes")
    parser.add_argument("--customer", help="Show quotes for customer email")
    parser.add_argument("--quote", help="Show details for a specific quote")
    args = parser.parse_args()
    
    tracker = get_tracker()
    
    if args.pipeline:
        stats = tracker.get_pipeline_stats()
        print("\n📊 Quote Pipeline Stats")
        print("=" * 40)
        print(f"Total quotes: {stats.total_quotes}")
        print(f"\nBy Status:")
        print(f"  Draft: {stats.draft}")
        print(f"  Sent: {stats.sent}")
        print(f"  Follow-up: {stats.follow_up}")
        print(f"  Negotiating: {stats.negotiating}")
        print(f"  Won: {stats.won}")
        print(f"  Lost: {stats.lost}")
        print(f"  Expired: {stats.expired}")
        print(f"\n💰 Pipeline Value: ${stats.total_pipeline_value:,.2f}")
        print(f"   Won (90d): ${stats.won_value:,.2f}")
        print(f"   Lost (90d): ${stats.lost_value:,.2f}")
        print(f"\n📈 Conversion Rate: {stats.conversion_rate:.1f}%")
        print(f"   Avg Days to Close: {stats.avg_days_to_close:.1f}")
        print(f"\n⚠️  Stale Quotes: {stats.stale_quotes}")
        
    elif args.stale:
        stale = tracker.get_stale_quotes()
        print(f"\n⚠️  Stale Quotes ({len(stale)})")
        print("=" * 40)
        for q in stale:
            days = q.days_since_follow_up()
            print(f"• {q.quote_id} - {q.customer_email}")
            print(f"  Product: {q.product}, Amount: ${q.amount:,.2f}")
            print(f"  Last activity: {days} days ago")
            print()
            
    elif args.active:
        active = tracker.get_active_quotes()
        print(f"\n📋 Active Quotes ({len(active)})")
        print("=" * 40)
        for q in active:
            print(f"• {q.quote_id} [{q.status.value}]")
            print(f"  Customer: {q.customer_email}")
            print(f"  Product: {q.product}, Amount: ${q.amount:,.2f}")
            print()
            
    elif args.customer:
        quotes = tracker.get_quotes_for_customer(args.customer)
        print(f"\n📋 Quotes for {args.customer} ({len(quotes)})")
        print("=" * 40)
        for q in quotes:
            print(f"• {q.quote_id} [{q.status.value}]")
            print(f"  Product: {q.product}, Amount: ${q.amount:,.2f}")
            if q.status == QuoteStatus.WON:
                print(f"  ✅ Won: ${q.final_amount or q.amount:,.2f}")
            elif q.status == QuoteStatus.LOST:
                print(f"  ❌ Lost: {q.lost_reason or 'No reason'}")
            print()
            
    elif args.quote:
        quote = tracker.get_quote(args.quote)
        if quote:
            print(f"\n📋 Quote: {quote.quote_id}")
            print("=" * 40)
            print(json.dumps(quote.to_dict(), indent=2, default=str))
            
            follow_ups = tracker.get_follow_ups(args.quote)
            if follow_ups:
                print(f"\n📝 Follow-ups ({len(follow_ups)}):")
                for fu in follow_ups:
                    print(f"  • {fu.created_at.strftime('%Y-%m-%d')}: {fu.follow_up_type.value}")
                    if fu.notes:
                        print(f"    {fu.notes[:50]}")
        else:
            print(f"Quote not found: {args.quote}")
    else:
        parser.print_help()
