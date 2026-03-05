"""
Correction Store — Nemesis's Memory
====================================

A unified, structured store for every correction, failure, and lesson Ira
has ever received. This is the single source of truth that Nemesis reads
from and writes to.

Three tables:
  corrections  — individual factual corrections (wrong → right)
  failures     — response-level failures (query + bad response + diagnosis)
  training_log — record of what was applied during sleep training

All stored in SQLite for fast querying, aggregation, and pattern detection.
"""

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.nemesis.store")

_DB_DIR = Path(__file__).parent.parent.parent.parent.parent.parent.parent / "data" / "nemesis"
_DB_PATH = _DB_DIR / "nemesis.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS corrections (
    id          TEXT PRIMARY KEY,
    timestamp   TEXT NOT NULL,
    source      TEXT NOT NULL,           -- telegram_feedback | sophia_reflection | immune_system | manual
    wrong_info  TEXT NOT NULL,
    correct_info TEXT NOT NULL,
    entity      TEXT,                     -- PF1-C-2015, [Customer], AM Series, etc.
    category    TEXT,                     -- spec | price | fact | customer | process | tone
    severity    TEXT DEFAULT 'important', -- critical | important | minor | style
    query       TEXT,                     -- original user query
    bad_response TEXT,                    -- Ira's wrong response (truncated)
    coach_note  TEXT,                     -- coach/LLM analysis of what went wrong
    applied     INTEGER DEFAULT 0,       -- 1 = applied during sleep training
    applied_to  TEXT,                     -- comma-separated: mem0,truth_hints,qdrant,system_prompt
    applied_at  TEXT,
    occurrences INTEGER DEFAULT 1,       -- how many times this same mistake was seen
    superseded  INTEGER DEFAULT 0        -- 1 = replaced by a newer correction for same entity+category
);

CREATE TABLE IF NOT EXISTS failures (
    id          TEXT PRIMARY KEY,
    timestamp   TEXT NOT NULL,
    source      TEXT NOT NULL,
    query       TEXT NOT NULL,
    response    TEXT NOT NULL,
    issues      TEXT,                     -- JSON array of issue codes
    quality_score REAL,
    coach_note  TEXT,
    corrections_extracted INTEGER DEFAULT 0,
    applied     INTEGER DEFAULT 0,
    applied_at  TEXT
);

CREATE TABLE IF NOT EXISTS training_log (
    id          TEXT PRIMARY KEY,
    timestamp   TEXT NOT NULL,
    phase       TEXT NOT NULL,            -- sleep_train | quick_train | manual
    corrections_applied INTEGER DEFAULT 0,
    truth_hints_added   INTEGER DEFAULT 0,
    qdrant_indexed      INTEGER DEFAULT 0,
    mem0_stored         INTEGER DEFAULT 0,
    prompt_rules_added  INTEGER DEFAULT 0,
    duration_seconds    REAL,
    summary     TEXT
);

CREATE INDEX IF NOT EXISTS idx_corrections_applied ON corrections(applied);
CREATE INDEX IF NOT EXISTS idx_corrections_entity ON corrections(entity);
CREATE INDEX IF NOT EXISTS idx_corrections_category ON corrections(category);
CREATE INDEX IF NOT EXISTS idx_corrections_severity ON corrections(severity);
CREATE INDEX IF NOT EXISTS idx_failures_applied ON failures(applied);
"""

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Thread-local SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _DB_DIR.mkdir(parents=True, exist_ok=True)
        _local.conn = sqlite3.connect(str(_DB_PATH), timeout=10)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.executescript(_SCHEMA)
        _migrate_superseded(_local.conn)
    return _local.conn


def _migrate_superseded(conn: sqlite3.Connection) -> None:
    """Add superseded column to existing databases that lack it."""
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(corrections)").fetchall()}
        if "superseded" not in cols:
            conn.execute("ALTER TABLE corrections ADD COLUMN superseded INTEGER DEFAULT 0")
            conn.commit()
            logger.info("[NEMESIS] Migrated corrections table: added superseded column")
    except Exception as e:
        logger.debug("[NEMESIS] superseded migration skipped: %s", e)


@contextmanager
def _tx():
    """Transaction context manager."""
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def record_correction(
    *,
    wrong_info: str,
    correct_info: str,
    source: str = "telegram_feedback",
    entity: Optional[str] = None,
    category: Optional[str] = None,
    severity: str = "important",
    query: Optional[str] = None,
    bad_response: Optional[str] = None,
    coach_note: Optional[str] = None,
) -> str:
    """Record a correction. Returns the correction ID.
    
    If a very similar correction already exists (same entity + category),
    increments the occurrence count instead of creating a duplicate.
    """
    ts = datetime.now().isoformat()
    cid = f"corr_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(correct_info) % 10000:04d}"

    with _tx() as conn:
        if entity and category:
            existing = conn.execute(
                "SELECT id, occurrences, correct_info FROM corrections "
                "WHERE entity = ? AND category = ? AND applied = 0 AND superseded = 0 "
                "ORDER BY timestamp DESC LIMIT 1",
                (entity, category),
            ).fetchone()
            if existing:
                if existing["correct_info"].strip() == correct_info.strip():
                    conn.execute(
                        "UPDATE corrections SET occurrences = occurrences + 1, "
                        "coach_note = ?, timestamp = ? WHERE id = ?",
                        (coach_note, ts, existing["id"]),
                    )
                    logger.info(f"[NEMESIS] Correction updated (x{existing['occurrences'] + 1}): {existing['id']}")
                    return existing["id"]
                else:
                    logger.warning(
                        "[NEMESIS] Conflicting corrections for %s/%s — "
                        "old: %s | new: %s — superseding old %s",
                        entity, category,
                        existing["correct_info"][:80], correct_info[:80],
                        existing["id"],
                    )
                    conn.execute(
                        "UPDATE corrections SET superseded = 1 WHERE id = ?",
                        (existing["id"],),
                    )

        conn.execute(
            "INSERT INTO corrections "
            "(id, timestamp, source, wrong_info, correct_info, entity, category, "
            " severity, query, bad_response, coach_note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cid, ts, source, wrong_info[:2000], correct_info[:2000],
             entity, category, severity,
             (query or "")[:1000], (bad_response or "")[:2000], coach_note),
        )
    logger.info(f"[NEMESIS] Correction recorded: {cid} ({category}/{severity})")
    return cid


def record_failure(
    *,
    query: str,
    response: str,
    source: str = "sophia_reflection",
    issues: Optional[List[str]] = None,
    quality_score: Optional[float] = None,
    coach_note: Optional[str] = None,
) -> str:
    """Record a response failure."""
    ts = datetime.now().isoformat()
    fid = f"fail_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(query) % 10000:04d}"

    with _tx() as conn:
        conn.execute(
            "INSERT INTO failures "
            "(id, timestamp, source, query, response, issues, quality_score, coach_note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (fid, ts, source, query[:1000], response[:2000],
             json.dumps(issues or []), quality_score, coach_note),
        )
    logger.info(f"[NEMESIS] Failure recorded: {fid}")
    return fid


def get_unapplied_corrections(limit: int = 100) -> List[Dict[str, Any]]:
    """Get corrections that haven't been applied during sleep training yet."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM corrections WHERE applied = 0 AND superseded = 0 ORDER BY "
        "CASE severity WHEN 'critical' THEN 0 WHEN 'important' THEN 1 "
        "WHEN 'minor' THEN 2 ELSE 3 END, occurrences DESC, timestamp DESC "
        "LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_unapplied_failures(limit: int = 50) -> List[Dict[str, Any]]:
    """Get failures not yet processed."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM failures WHERE applied = 0 ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def mark_correction_applied(cid: str, applied_to: str) -> None:
    """Mark a correction as applied during training."""
    with _tx() as conn:
        conn.execute(
            "UPDATE corrections SET applied = 1, applied_to = ?, applied_at = ? WHERE id = ?",
            (applied_to, datetime.now().isoformat(), cid),
        )


def mark_failure_applied(fid: str) -> None:
    """Mark a failure as processed."""
    with _tx() as conn:
        conn.execute(
            "UPDATE failures SET applied = 1, applied_at = ? WHERE id = ?",
            (datetime.now().isoformat(), fid),
        )


def record_training_run(
    *,
    phase: str,
    corrections_applied: int = 0,
    truth_hints_added: int = 0,
    qdrant_indexed: int = 0,
    mem0_stored: int = 0,
    prompt_rules_added: int = 0,
    duration_seconds: float = 0,
    summary: str = "",
) -> str:
    """Log a training run."""
    ts = datetime.now().isoformat()
    tid = f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    with _tx() as conn:
        conn.execute(
            "INSERT INTO training_log "
            "(id, timestamp, phase, corrections_applied, truth_hints_added, "
            " qdrant_indexed, mem0_stored, prompt_rules_added, duration_seconds, summary) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (tid, ts, phase, corrections_applied, truth_hints_added,
             qdrant_indexed, mem0_stored, prompt_rules_added, duration_seconds, summary),
        )
    return tid


def get_correction_stats() -> Dict[str, Any]:
    """Aggregate stats for Nemesis's report."""
    conn = _get_conn()

    total = conn.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]
    unapplied = conn.execute("SELECT COUNT(*) FROM corrections WHERE applied = 0").fetchone()[0]
    by_category = {
        r[0] or "unknown": r[1]
        for r in conn.execute(
            "SELECT category, COUNT(*) FROM corrections GROUP BY category"
        ).fetchall()
    }
    by_severity = {
        r[0]: r[1]
        for r in conn.execute(
            "SELECT severity, COUNT(*) FROM corrections GROUP BY severity"
        ).fetchall()
    }
    repeat_offenders = [
        dict(r) for r in conn.execute(
            "SELECT entity, category, SUM(occurrences) as total_occ "
            "FROM corrections WHERE entity IS NOT NULL "
            "GROUP BY entity, category HAVING total_occ > 1 "
            "ORDER BY total_occ DESC LIMIT 10"
        ).fetchall()
    ]
    training_runs = conn.execute("SELECT COUNT(*) FROM training_log").fetchone()[0]

    return {
        "total_corrections": total,
        "unapplied": unapplied,
        "by_category": by_category,
        "by_severity": by_severity,
        "repeat_offenders": repeat_offenders,
        "training_runs": training_runs,
    }


def get_recent_corrections(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent corrections for display."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, timestamp, source, wrong_info, correct_info, entity, "
        "category, severity, occurrences, applied "
        "FROM corrections ORDER BY timestamp DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]
