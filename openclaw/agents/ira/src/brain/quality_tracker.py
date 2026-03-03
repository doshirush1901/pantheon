"""
Quality Trend Tracker
=====================

Stores per-interaction quality scores in SQLite so Ira's improvement
can be measured over time.  Sophia calls ``record_quality()`` after
every reflection; Athena can call ``quality_trend`` as a tool.

DB location: data/quality/quality_scores.db
"""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.quality_tracker")

_DB_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "quality"
_DB_PATH = _DB_DIR / "quality_scores.db"

_conn: Optional[sqlite3.Connection] = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is not None:
        return _conn
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.execute("""
        CREATE TABLE IF NOT EXISTS quality_scores (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT    NOT NULL,
            query_hash  TEXT    NOT NULL,
            channel     TEXT    NOT NULL DEFAULT 'api',
            user_id     TEXT    NOT NULL DEFAULT 'unknown',
            factual     REAL    NOT NULL DEFAULT 0,
            helpfulness REAL    NOT NULL DEFAULT 0,
            completeness REAL   NOT NULL DEFAULT 0,
            tone        REAL    NOT NULL DEFAULT 0,
            structure   REAL    NOT NULL DEFAULT 0,
            responsiveness REAL NOT NULL DEFAULT 0,
            overall     REAL    NOT NULL DEFAULT 0,
            issues      TEXT    NOT NULL DEFAULT '[]',
            msg_len     INTEGER NOT NULL DEFAULT 0,
            resp_len    INTEGER NOT NULL DEFAULT 0
        )
    """)
    _conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_qs_ts ON quality_scores(ts)
    """)
    _conn.commit()
    return _conn


def record_quality(
    message: str,
    response: str,
    quality_score: Any,
    issues: List[str],
    channel: str = "api",
    user_id: str = "unknown",
) -> None:
    """Insert a quality record after Sophia's reflection."""
    try:
        conn = _get_conn()
        q_hash = hashlib.sha256(message.encode()).hexdigest()[:16]
        conn.execute(
            """INSERT INTO quality_scores
               (ts, query_hash, channel, user_id,
                factual, helpfulness, completeness, tone, structure, responsiveness,
                overall, issues, msg_len, resp_len)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(),
                q_hash,
                channel,
                user_id,
                quality_score.factual_accuracy,
                quality_score.helpfulness,
                quality_score.completeness,
                quality_score.tone,
                quality_score.structure,
                quality_score.responsiveness,
                quality_score.overall,
                json.dumps(issues),
                len(message),
                len(response),
            ),
        )
        conn.commit()
    except Exception as e:
        logger.debug("Quality recording failed: %s", e)


def get_quality_trend(days: int = 30) -> Dict[str, Any]:
    """Average quality scores grouped by day for the last *days* days."""
    try:
        conn = _get_conn()
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            """SELECT date(ts) as day,
                      COUNT(*) as n,
                      ROUND(AVG(overall), 3) as avg_overall,
                      ROUND(AVG(factual), 3) as avg_factual,
                      ROUND(AVG(helpfulness), 3) as avg_helpful,
                      ROUND(AVG(completeness), 3) as avg_complete,
                      ROUND(AVG(tone), 3) as avg_tone,
                      ROUND(AVG(structure), 3) as avg_structure
               FROM quality_scores
               WHERE ts >= ?
               GROUP BY date(ts)
               ORDER BY day""",
            (cutoff,),
        ).fetchall()

        trend = []
        for r in rows:
            trend.append({
                "date": r[0], "count": r[1], "overall": r[2],
                "factual": r[3], "helpfulness": r[4], "completeness": r[5],
                "tone": r[6], "structure": r[7],
            })

        total = conn.execute(
            "SELECT COUNT(*), ROUND(AVG(overall),3) FROM quality_scores WHERE ts >= ?",
            (cutoff,),
        ).fetchone()

        return {
            "period_days": days,
            "total_interactions": total[0] if total else 0,
            "avg_overall": total[1] if total else 0,
            "daily_trend": trend,
        }
    except Exception as e:
        logger.warning("Quality trend query failed: %s", e)
        return {"error": str(e)}


def get_improvement_report() -> str:
    """Compare last 7 days vs previous 7 days — human-readable."""
    try:
        conn = _get_conn()
        now = datetime.now()
        week_ago = (now - timedelta(days=7)).isoformat()
        two_weeks_ago = (now - timedelta(days=14)).isoformat()

        def _avg(start: str, end: str):
            row = conn.execute(
                """SELECT COUNT(*), ROUND(AVG(overall),3),
                          ROUND(AVG(factual),3), ROUND(AVG(helpfulness),3)
                   FROM quality_scores WHERE ts >= ? AND ts < ?""",
                (start, end),
            ).fetchone()
            return row or (0, 0, 0, 0)

        curr = _avg(week_ago, now.isoformat())
        prev = _avg(two_weeks_ago, week_ago)

        if curr[0] == 0:
            return "No quality data for the last 7 days yet. Keep chatting with Ira!"

        lines = [
            "**Quality Improvement Report**\n",
            f"Last 7 days: {curr[0]} interactions, avg quality {curr[1]}",
        ]
        if prev[0] > 0:
            delta = round((curr[1] or 0) - (prev[1] or 0), 3)
            direction = "up" if delta > 0 else ("down" if delta < 0 else "flat")
            lines.append(f"Previous 7 days: {prev[0]} interactions, avg quality {prev[1]}")
            lines.append(f"Trend: **{direction}** ({'+' if delta > 0 else ''}{delta})")
        else:
            lines.append("(No data from the previous week to compare.)")

        # Top issues this week
        issues_rows = conn.execute(
            """SELECT issues FROM quality_scores WHERE ts >= ?""",
            (week_ago,),
        ).fetchall()
        issue_counts: Dict[str, int] = {}
        for (raw,) in issues_rows:
            for issue in json.loads(raw):
                tag = issue.split(":")[0].strip()
                issue_counts[tag] = issue_counts.get(tag, 0) + 1
        if issue_counts:
            top = sorted(issue_counts.items(), key=lambda x: -x[1])[:5]
            lines.append("\nTop issues this week:")
            for tag, count in top:
                lines.append(f"  - {tag}: {count}x")

        return "\n".join(lines)
    except Exception as e:
        return f"Quality report unavailable: {e}"
