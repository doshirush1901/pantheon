#!/usr/bin/env python3
"""
Relationship Store - SQLite Persistence for Relationship Data
==============================================================

Stores all relationship state in SQLite so it survives restarts.
Links identities across channels (email + telegram = same person).

Tables:
- contacts: Core contact info with unified identity
- relationship_state: Warmth, scores, interaction counts
- memorable_moments: Personal shares, celebrations, difficulties
- learned_preferences: Communication style preferences
- conversation_health: Quality scores and trends
- behavioral_patterns: Topics, timing, query patterns
- insights: Generated insights per contact
"""

import json
import sys
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Use centralized config
AGENT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(AGENT_DIR))

try:
    from config import (
        ensure_schema, get_sqlite_connection, get_logger,
        setup_import_paths
    )
    setup_import_paths()
    CONFIG_AVAILABLE = True
    _logger = get_logger(__name__)
except ImportError:
    CONFIG_AVAILABLE = False
    import logging
    _logger = logging.getLogger(__name__)

# Database path
DATA_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "crm"
RELATIONSHIP_DB = DATA_DIR / "relationships.db"

# Schema version for migrations
SCHEMA_VERSION = 1

SCHEMA = """
-- Unified contacts with cross-channel identity linking
CREATE TABLE IF NOT EXISTS contacts (
    contact_id TEXT PRIMARY KEY,
    unified_identity_id TEXT,
    name TEXT,
    email TEXT,
    telegram_id TEXT,
    company TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_contacts_identity ON contacts(unified_identity_id);
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);
CREATE INDEX IF NOT EXISTS idx_contacts_telegram ON contacts(telegram_id);

-- Relationship state (warmth, scores)
CREATE TABLE IF NOT EXISTS relationship_state (
    contact_id TEXT PRIMARY KEY,
    warmth TEXT DEFAULT 'stranger',
    warmth_score REAL DEFAULT 0.0,
    interaction_count INTEGER DEFAULT 0,
    positive_interactions INTEGER DEFAULT 0,
    last_interaction TEXT,
    relationship_started TEXT,
    personal_context TEXT DEFAULT '{}',
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id)
);

-- Memorable moments
CREATE TABLE IF NOT EXISTS memorable_moments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT,
    moment_type TEXT,
    content TEXT,
    context TEXT DEFAULT '{}',
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    followup_due TEXT,
    followup_done INTEGER DEFAULT 0,
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id)
);

CREATE INDEX IF NOT EXISTS idx_moments_contact ON memorable_moments(contact_id);
CREATE INDEX IF NOT EXISTS idx_moments_followup ON memorable_moments(followup_due, followup_done);

-- Learned preferences
CREATE TABLE IF NOT EXISTS learned_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT,
    preference_type TEXT,
    value TEXT,
    confidence REAL DEFAULT 0.5,
    learned_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id)
);

CREATE INDEX IF NOT EXISTS idx_prefs_contact ON learned_preferences(contact_id);

-- Communication style profile
CREATE TABLE IF NOT EXISTS style_profiles (
    contact_id TEXT PRIMARY KEY,
    formality_score REAL DEFAULT 50.0,
    detail_score REAL DEFAULT 50.0,
    technical_score REAL DEFAULT 50.0,
    pace_score REAL DEFAULT 50.0,
    emoji_score REAL DEFAULT 30.0,
    humor_score REAL DEFAULT 30.0,
    avg_message_length REAL DEFAULT 100.0,
    messages_analyzed INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id)
);

-- Conversation health tracking
CREATE TABLE IF NOT EXISTS conversation_health (
    contact_id TEXT PRIMARY KEY,
    health_score REAL DEFAULT 50.0,
    trend TEXT DEFAULT 'stable',
    risk_level TEXT DEFAULT 'low',
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id)
);

-- Turn quality history
CREATE TABLE IF NOT EXISTS turn_quality (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT,
    turn_id TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    overall_score REAL,
    engagement_score REAL,
    rapport_score REAL,
    satisfaction_score REAL,
    effectiveness_score REAL,
    signals TEXT DEFAULT '[]',
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id)
);

CREATE INDEX IF NOT EXISTS idx_quality_contact ON turn_quality(contact_id);
CREATE INDEX IF NOT EXISTS idx_quality_time ON turn_quality(timestamp);

-- Behavioral patterns
CREATE TABLE IF NOT EXISTS behavioral_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT,
    pattern_type TEXT,
    pattern_key TEXT,
    count INTEGER DEFAULT 1,
    first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
    last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id)
);

CREATE INDEX IF NOT EXISTS idx_patterns_contact ON behavioral_patterns(contact_id);

-- Generated insights
CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT,
    insight_type TEXT,
    title TEXT,
    description TEXT,
    confidence REAL DEFAULT 0.5,
    actionable INTEGER DEFAULT 0,
    action_suggestion TEXT,
    generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    shared INTEGER DEFAULT 0,
    was_useful INTEGER,
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id)
);

CREATE INDEX IF NOT EXISTS idx_insights_contact ON insights(contact_id);

-- Emotional history
CREATE TABLE IF NOT EXISTS emotional_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    primary_state TEXT,
    intensity TEXT,
    confidence REAL,
    signals TEXT DEFAULT '[]',
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id)
);

CREATE INDEX IF NOT EXISTS idx_emotional_contact ON emotional_history(contact_id);

-- Memory surfacing tracking
CREATE TABLE IF NOT EXISTS memory_surfacing (
    memory_id TEXT PRIMARY KEY,
    contact_id TEXT,
    last_surfaced TEXT,
    surface_count INTEGER DEFAULT 0,
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id)
);
"""

# Convert SCHEMA to migrations format
SCHEMA_MIGRATIONS = {
    1: [stmt.strip() for stmt in SCHEMA.split(';') if stmt.strip() and not stmt.strip().startswith('--')],
    # Future migrations go here:
    # 2: ["ALTER TABLE contacts ADD COLUMN ...", ...],
}


class RelationshipStore:
    """
    SQLite-backed storage for all relationship data.
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(RELATIONSHIP_DB)
        self._ensure_db()
    
    def _ensure_db(self):
        """Create database and tables if needed, applying migrations as needed."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        if CONFIG_AVAILABLE:
            # Use centralized schema versioning
            self._conn_cached = ensure_schema(
                self.db_path,
                "relationship_store",
                SCHEMA_VERSION,
                SCHEMA_MIGRATIONS,
            )
        else:
            # Fallback: Apply schema directly without versioning
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                conn.executescript(SCHEMA)
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection with WAL mode and best practices."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    
    # =========================================================================
    # IDENTITY LINKING (Delegates to UnifiedIdentityService)
    # =========================================================================
    
    def get_or_create_contact(
        self,
        contact_id: str,
        name: str = "",
        email: str = None,
        telegram_id: str = None,
        company: str = None
    ) -> str:
        """
        Get or create a contact, linking identities across channels.
        
        Now delegates to UnifiedIdentityService for canonical identity.
        Returns the unified contact_id.
        """
        # Delegate to unified identity service
        try:
            from unified_identity import get_identity_service
            identity_svc = get_identity_service()
            
            # Resolve or create via unified service
            unified_contact_id = None
            if email:
                unified_contact_id = identity_svc.resolve("email", email, create_if_missing=True, name=name)
                if telegram_id:
                    identity_svc.link("email", email, "telegram", telegram_id)
            elif telegram_id:
                unified_contact_id = identity_svc.resolve("telegram", telegram_id, create_if_missing=True, name=name)
            else:
                unified_contact_id = contact_id
            
            # Update name/company if provided
            if unified_contact_id and (name or company):
                identity_svc.update_contact(unified_contact_id, name=name, company=company)
            
            contact_id = unified_contact_id or contact_id
        except ImportError as e:
            _logger.debug(f"Identity module not available, using local logic: {e}")
        
        with self._get_conn() as conn:
            # Check if contact exists
            row = conn.execute(
                "SELECT * FROM contacts WHERE contact_id = ?",
                (contact_id,)
            ).fetchone()
            
            if row:
                return row["contact_id"]
            
            # Check for identity linking by email
            unified_id = contact_id
            if email:
                existing = conn.execute(
                    "SELECT unified_identity_id FROM contacts WHERE email = ?",
                    (email,)
                ).fetchone()
                if existing:
                    unified_id = existing["unified_identity_id"]
            
            # Check for identity linking by telegram
            if telegram_id and unified_id == contact_id:
                existing = conn.execute(
                    "SELECT unified_identity_id FROM contacts WHERE telegram_id = ?",
                    (telegram_id,)
                ).fetchone()
                if existing:
                    unified_id = existing["unified_identity_id"]
            
            # Create new contact
            now = datetime.now().isoformat()
            conn.execute("""
                INSERT INTO contacts (contact_id, unified_identity_id, name, email, telegram_id, company, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (contact_id, unified_id, name, email, telegram_id, company, now, now))
            
            # Create relationship state
            conn.execute("""
                INSERT OR IGNORE INTO relationship_state (contact_id, relationship_started)
                VALUES (?, ?)
            """, (contact_id, now))
            
            # Create style profile
            conn.execute("""
                INSERT OR IGNORE INTO style_profiles (contact_id)
                VALUES (?)
            """, (contact_id,))
            
            # Create conversation health
            conn.execute("""
                INSERT OR IGNORE INTO conversation_health (contact_id)
                VALUES (?)
            """, (contact_id,))
            
            conn.commit()
            
            return contact_id
    
    def link_identity(self, contact_id: str, email: str = None, telegram_id: str = None) -> bool:
        """
        Link a contact to an email or telegram ID.
        Returns True if linking found an existing identity.
        """
        with self._get_conn() as conn:
            unified_id = None
            
            if email:
                existing = conn.execute(
                    "SELECT unified_identity_id FROM contacts WHERE email = ? AND contact_id != ?",
                    (email, contact_id)
                ).fetchone()
                if existing:
                    unified_id = existing["unified_identity_id"]
                conn.execute(
                    "UPDATE contacts SET email = ? WHERE contact_id = ?",
                    (email, contact_id)
                )
            
            if telegram_id:
                existing = conn.execute(
                    "SELECT unified_identity_id FROM contacts WHERE telegram_id = ? AND contact_id != ?",
                    (telegram_id, contact_id)
                ).fetchone()
                if existing:
                    unified_id = unified_id or existing["unified_identity_id"]
                conn.execute(
                    "UPDATE contacts SET telegram_id = ? WHERE contact_id = ?",
                    (telegram_id, contact_id)
                )
            
            if unified_id:
                conn.execute(
                    "UPDATE contacts SET unified_identity_id = ? WHERE contact_id = ?",
                    (unified_id, contact_id)
                )
                conn.commit()
                return True
            
            conn.commit()
            return False
    
    def get_unified_contacts(self, unified_identity_id: str) -> List[Dict]:
        """Get all contacts linked to a unified identity."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM contacts WHERE unified_identity_id = ?",
                (unified_identity_id,)
            ).fetchall()
            return [dict(r) for r in rows]
    
    # =========================================================================
    # RELATIONSHIP STATE
    # =========================================================================
    
    def get_relationship_state(self, contact_id: str) -> Optional[Dict]:
        """Get relationship state for a contact."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM relationship_state WHERE contact_id = ?",
                (contact_id,)
            ).fetchone()
            return dict(row) if row else None
    
    def update_relationship_state(
        self,
        contact_id: str,
        warmth: str = None,
        warmth_score: float = None,
        interaction_count: int = None,
        positive_interactions: int = None,
        personal_context: Dict = None
    ) -> None:
        """Update relationship state."""
        with self._get_conn() as conn:
            updates = []
            params = []
            
            if warmth is not None:
                updates.append("warmth = ?")
                params.append(warmth)
            if warmth_score is not None:
                updates.append("warmth_score = ?")
                params.append(warmth_score)
            if interaction_count is not None:
                updates.append("interaction_count = ?")
                params.append(interaction_count)
            if positive_interactions is not None:
                updates.append("positive_interactions = ?")
                params.append(positive_interactions)
            if personal_context is not None:
                updates.append("personal_context = ?")
                params.append(json.dumps(personal_context))
            
            updates.append("last_interaction = ?")
            params.append(datetime.now().isoformat())
            
            if updates:
                params.append(contact_id)
                conn.execute(f"""
                    UPDATE relationship_state SET {', '.join(updates)}
                    WHERE contact_id = ?
                """, params)
                conn.commit()
    
    def increment_interaction(self, contact_id: str, is_positive: bool = True) -> Dict:
        """Increment interaction count and return new state."""
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE relationship_state 
                SET interaction_count = interaction_count + 1,
                    positive_interactions = positive_interactions + ?,
                    last_interaction = ?
                WHERE contact_id = ?
            """, (1 if is_positive else 0, datetime.now().isoformat(), contact_id))
            conn.commit()
            
            return self.get_relationship_state(contact_id)
    
    # =========================================================================
    # MEMORABLE MOMENTS
    # =========================================================================
    
    def add_moment(
        self,
        contact_id: str,
        moment_type: str,
        content: str,
        context: Dict = None,
        followup_days: int = None
    ) -> int:
        """Add a memorable moment."""
        with self._get_conn() as conn:
            followup_due = None
            if followup_days:
                followup_due = (datetime.now() + timedelta(days=followup_days)).isoformat()
            
            cursor = conn.execute("""
                INSERT INTO memorable_moments (contact_id, moment_type, content, context, followup_due)
                VALUES (?, ?, ?, ?, ?)
            """, (contact_id, moment_type, content, json.dumps(context or {}), followup_due))
            conn.commit()
            return cursor.lastrowid
    
    def get_moments(self, contact_id: str, limit: int = 10) -> List[Dict]:
        """Get memorable moments for a contact."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM memorable_moments 
                WHERE contact_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (contact_id, limit)).fetchall()
            return [dict(r) for r in rows]
    
    def get_pending_followups(self, contact_id: str = None) -> List[Dict]:
        """Get moments needing follow-up."""
        with self._get_conn() as conn:
            if contact_id:
                rows = conn.execute("""
                    SELECT * FROM memorable_moments
                    WHERE contact_id = ? AND followup_due <= ? AND followup_done = 0
                    ORDER BY followup_due
                """, (contact_id, datetime.now().isoformat())).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM memorable_moments
                    WHERE followup_due <= ? AND followup_done = 0
                    ORDER BY followup_due
                """, (datetime.now().isoformat(),)).fetchall()
            return [dict(r) for r in rows]
    
    def mark_followup_done(self, moment_id: int) -> None:
        """Mark a follow-up as done."""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE memorable_moments SET followup_done = 1 WHERE id = ?",
                (moment_id,)
            )
            conn.commit()
    
    # =========================================================================
    # STYLE PROFILES
    # =========================================================================
    
    def get_style_profile(self, contact_id: str) -> Optional[Dict]:
        """Get style profile for a contact."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM style_profiles WHERE contact_id = ?",
                (contact_id,)
            ).fetchone()
            return dict(row) if row else None
    
    def update_style_profile(
        self,
        contact_id: str,
        formality_score: float = None,
        detail_score: float = None,
        technical_score: float = None,
        pace_score: float = None,
        emoji_score: float = None,
        humor_score: float = None,
        avg_message_length: float = None,
        messages_analyzed: int = None
    ) -> None:
        """Update style profile."""
        with self._get_conn() as conn:
            updates = []
            params = []
            
            for field, value in [
                ("formality_score", formality_score),
                ("detail_score", detail_score),
                ("technical_score", technical_score),
                ("pace_score", pace_score),
                ("emoji_score", emoji_score),
                ("humor_score", humor_score),
                ("avg_message_length", avg_message_length),
                ("messages_analyzed", messages_analyzed),
            ]:
                if value is not None:
                    updates.append(f"{field} = ?")
                    params.append(value)
            
            if updates:
                updates.append("updated_at = ?")
                params.append(datetime.now().isoformat())
                params.append(contact_id)
                
                conn.execute(f"""
                    UPDATE style_profiles SET {', '.join(updates)}
                    WHERE contact_id = ?
                """, params)
                conn.commit()
    
    # =========================================================================
    # CONVERSATION HEALTH
    # =========================================================================
    
    def get_conversation_health(self, contact_id: str) -> Optional[Dict]:
        """Get conversation health for a contact."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM conversation_health WHERE contact_id = ?",
                (contact_id,)
            ).fetchone()
            return dict(row) if row else None
    
    def update_conversation_health(
        self,
        contact_id: str,
        health_score: float,
        trend: str,
        risk_level: str
    ) -> None:
        """Update conversation health."""
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE conversation_health 
                SET health_score = ?, trend = ?, risk_level = ?, last_updated = ?
                WHERE contact_id = ?
            """, (health_score, trend, risk_level, datetime.now().isoformat(), contact_id))
            conn.commit()
    
    def add_turn_quality(
        self,
        contact_id: str,
        turn_id: str,
        overall_score: float,
        engagement_score: float,
        rapport_score: float,
        satisfaction_score: float,
        effectiveness_score: float,
        signals: List[str]
    ) -> None:
        """Add a turn quality record."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO turn_quality 
                (contact_id, turn_id, overall_score, engagement_score, rapport_score, 
                 satisfaction_score, effectiveness_score, signals)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (contact_id, turn_id, overall_score, engagement_score, rapport_score,
                  satisfaction_score, effectiveness_score, json.dumps(signals)))
            conn.commit()
    
    def get_turn_history(self, contact_id: str, limit: int = 20) -> List[Dict]:
        """Get turn quality history."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM turn_quality
                WHERE contact_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (contact_id, limit)).fetchall()
            return [dict(r) for r in rows]
    
    def get_at_risk_contacts(self, threshold: float = 40.0) -> List[Dict]:
        """Get contacts with low health scores or declining trends."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT ch.*, c.name, rs.warmth, rs.interaction_count
                FROM conversation_health ch
                JOIN contacts c ON ch.contact_id = c.contact_id
                LEFT JOIN relationship_state rs ON ch.contact_id = rs.contact_id
                WHERE ch.health_score < ? OR ch.trend = 'declining'
                ORDER BY ch.health_score ASC
            """, (threshold,)).fetchall()
            return [dict(r) for r in rows]
    
    # =========================================================================
    # BEHAVIORAL PATTERNS
    # =========================================================================
    
    def record_pattern(
        self,
        contact_id: str,
        pattern_type: str,
        pattern_key: str,
        metadata: Dict = None
    ) -> None:
        """Record or increment a behavioral pattern."""
        with self._get_conn() as conn:
            existing = conn.execute("""
                SELECT id, count FROM behavioral_patterns
                WHERE contact_id = ? AND pattern_type = ? AND pattern_key = ?
            """, (contact_id, pattern_type, pattern_key)).fetchone()
            
            now = datetime.now().isoformat()
            if existing:
                conn.execute("""
                    UPDATE behavioral_patterns
                    SET count = count + 1, last_seen = ?, metadata = ?
                    WHERE id = ?
                """, (now, json.dumps(metadata or {}), existing["id"]))
            else:
                conn.execute("""
                    INSERT INTO behavioral_patterns 
                    (contact_id, pattern_type, pattern_key, metadata)
                    VALUES (?, ?, ?, ?)
                """, (contact_id, pattern_type, pattern_key, json.dumps(metadata or {})))
            
            conn.commit()
    
    def get_patterns(self, contact_id: str, pattern_type: str = None) -> List[Dict]:
        """Get behavioral patterns for a contact."""
        with self._get_conn() as conn:
            if pattern_type:
                rows = conn.execute("""
                    SELECT * FROM behavioral_patterns
                    WHERE contact_id = ? AND pattern_type = ?
                    ORDER BY count DESC
                """, (contact_id, pattern_type)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM behavioral_patterns
                    WHERE contact_id = ?
                    ORDER BY count DESC
                """, (contact_id,)).fetchall()
            return [dict(r) for r in rows]
    
    # =========================================================================
    # INSIGHTS
    # =========================================================================
    
    def add_insight(
        self,
        contact_id: str,
        insight_type: str,
        title: str,
        description: str,
        confidence: float = 0.5,
        actionable: bool = False,
        action_suggestion: str = None
    ) -> int:
        """Add an insight."""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO insights 
                (contact_id, insight_type, title, description, confidence, actionable, action_suggestion)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (contact_id, insight_type, title, description, confidence, 
                  1 if actionable else 0, action_suggestion))
            conn.commit()
            return cursor.lastrowid
    
    def get_insights(
        self,
        contact_id: str,
        unshared_only: bool = True,
        actionable_only: bool = False
    ) -> List[Dict]:
        """Get insights for a contact."""
        with self._get_conn() as conn:
            conditions = ["contact_id = ?"]
            params = [contact_id]
            
            if unshared_only:
                conditions.append("shared = 0")
            if actionable_only:
                conditions.append("actionable = 1")
            
            rows = conn.execute(f"""
                SELECT * FROM insights
                WHERE {' AND '.join(conditions)}
                ORDER BY confidence DESC, generated_at DESC
            """, params).fetchall()
            return [dict(r) for r in rows]
    
    def mark_insight_shared(self, insight_id: int, was_useful: bool = None) -> None:
        """Mark an insight as shared."""
        with self._get_conn() as conn:
            if was_useful is not None:
                conn.execute(
                    "UPDATE insights SET shared = 1, was_useful = ? WHERE id = ?",
                    (1 if was_useful else 0, insight_id)
                )
            else:
                conn.execute(
                    "UPDATE insights SET shared = 1 WHERE id = ?",
                    (insight_id,)
                )
            conn.commit()
    
    # =========================================================================
    # EMOTIONAL HISTORY
    # =========================================================================
    
    def record_emotion(
        self,
        contact_id: str,
        primary_state: str,
        intensity: str,
        confidence: float,
        signals: List[str]
    ) -> None:
        """Record an emotional reading."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO emotional_history 
                (contact_id, primary_state, intensity, confidence, signals)
                VALUES (?, ?, ?, ?, ?)
            """, (contact_id, primary_state, intensity, confidence, json.dumps(signals)))
            conn.commit()
    
    def get_emotional_history(self, contact_id: str, limit: int = 10) -> List[Dict]:
        """Get emotional history for a contact."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM emotional_history
                WHERE contact_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (contact_id, limit)).fetchall()
            return [dict(r) for r in rows]
    
    # =========================================================================
    # MEMORY SURFACING
    # =========================================================================
    
    def mark_memory_surfaced(self, memory_id: str, contact_id: str) -> None:
        """Mark a memory as surfaced."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO memory_surfacing (memory_id, contact_id, last_surfaced, surface_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(memory_id) DO UPDATE SET
                    last_surfaced = excluded.last_surfaced,
                    surface_count = surface_count + 1
            """, (memory_id, contact_id, datetime.now().isoformat()))
            conn.commit()
    
    def get_memory_surfacing(self, memory_id: str) -> Optional[Dict]:
        """Get surfacing info for a memory."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM memory_surfacing WHERE memory_id = ?",
                (memory_id,)
            ).fetchone()
            return dict(row) if row else None
    
    def was_recently_surfaced(self, memory_id: str, days: int = 7) -> bool:
        """Check if a memory was surfaced within N days."""
        info = self.get_memory_surfacing(memory_id)
        if not info:
            return False
        
        last = datetime.fromisoformat(info["last_surfaced"])
        return (datetime.now() - last).days < days
    
    # =========================================================================
    # DASHBOARD QUERIES
    # =========================================================================
    
    def get_dashboard_metrics(self) -> Dict:
        """Get aggregate metrics for the dashboard."""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM contacts").fetchone()["c"]
            
            warmth_dist = {}
            for row in conn.execute("""
                SELECT warmth, COUNT(*) as c FROM relationship_state GROUP BY warmth
            """).fetchall():
                warmth_dist[row["warmth"]] = row["c"]
            
            health_stats = conn.execute("""
                SELECT AVG(health_score) as avg_health,
                       SUM(CASE WHEN risk_level IN ('medium', 'high') THEN 1 ELSE 0 END) as at_risk,
                       SUM(CASE WHEN trend = 'declining' THEN 1 ELSE 0 END) as declining
                FROM conversation_health
            """).fetchone()
            
            pending_followups = conn.execute("""
                SELECT COUNT(*) as c FROM memorable_moments
                WHERE followup_due <= ? AND followup_done = 0
            """, (datetime.now().isoformat(),)).fetchone()["c"]
            
            return {
                "total_contacts": total,
                "warmth_distribution": warmth_dist,
                "average_health": health_stats["avg_health"] or 50.0,
                "at_risk_count": health_stats["at_risk"] or 0,
                "declining_count": health_stats["declining"] or 0,
                "pending_followups": pending_followups,
            }


# Module-level singleton
_store: Optional[RelationshipStore] = None


def get_relationship_store() -> RelationshipStore:
    """Get or create the relationship store singleton."""
    global _store
    if _store is None:
        _store = RelationshipStore()
    return _store


def bootstrap_from_persistent_memory() -> Dict[str, int]:
    """
    Import existing contacts from persistent_memory into relationship store.
    
    This ensures users you've already interacted with get relationship profiles.
    Safe to call multiple times - only creates new contacts that don't exist.
    
    Returns counts of imported/skipped contacts.
    """
    import psycopg2
    
    store = get_relationship_store()
    imported = 0
    skipped = 0
    
    try:
        # Use centralized config
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from config import DATABASE_URL
            pg_url = DATABASE_URL
        except ImportError:
            pg_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
        
        if not pg_url:
            return {"imported": 0, "skipped": 0, "error": "No DATABASE_URL"}
        
        conn = psycopg2.connect(pg_url)
        conn.set_session(autocommit=True)
        cursor = conn.cursor()
        
        # Get all unique identity_ids from persistent memory
        cursor.execute("""
            SELECT DISTINCT identity_id FROM ira_memory.user_memories
            WHERE identity_id IS NOT NULL AND identity_id != ''
        """)
        
        identity_ids = [row[0] for row in cursor.fetchall()]
        
        for identity_id in identity_ids:
            # Parse identity_id (usually email or telegram ID)
            email = None
            telegram_id = None
            name = identity_id
            
            if "@" in identity_id:
                email = identity_id
                name = identity_id.split("@")[0].replace(".", " ").title()
            elif identity_id.startswith("telegram:"):
                telegram_id = identity_id.replace("telegram:", "")
            elif identity_id.isdigit():
                telegram_id = identity_id
            
            # Check if already exists
            existing = store.get_or_create_contact(
                name=name,
                email=email,
                telegram_id=telegram_id
            )
            
            # Count the user's memories to estimate interaction_count
            cursor.execute("""
                SELECT COUNT(*) FROM ira_memory.user_memories
                WHERE identity_id = %s AND is_active = TRUE
            """, (identity_id,))
            memory_count = cursor.fetchone()[0]
            
            # If this is a new contact (check interaction_count in relationship_state)
            with store._get_conn() as sqlite_conn:
                state = sqlite_conn.execute("""
                    SELECT interaction_count FROM relationship_state
                    WHERE contact_id = ?
                """, (existing,)).fetchone()
                
                if state and state["interaction_count"] > 0:
                    skipped += 1
                else:
                    # Initialize relationship state based on memory count
                    warmth = "familiar" if memory_count >= 5 else "acquaintance"
                    store.update_relationship_state(
                        contact_id=existing,
                        warmth=warmth,
                        interaction_count=memory_count,
                        last_interaction=datetime.now().isoformat()
                    )
                    imported += 1
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        return {"imported": imported, "skipped": skipped, "error": str(e)}
    
    return {"imported": imported, "skipped": skipped, "error": None}
