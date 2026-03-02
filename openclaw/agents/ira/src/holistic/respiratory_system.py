#!/usr/bin/env python3
"""
RESPIRATORY SYSTEM - Operational Heartbeat and Daily Rhythm
============================================================

Biological parallel:
    Breathing rhythm synchronizes neural oscillations across the brain.
    Nasal breathing entrains brainwaves in hippocampus and prefrontal cortex.
    Without rhythm, the brain's subsystems work in isolation.

Ira parallel:
    Ira has no reliable cadence. Dream mode is meant to be nightly but
    there's no confirmation it ran. There's no inhale/exhale cycle.
    This module establishes the rhythm that synchronizes all other systems.

Rhythm:
    - Heartbeat:  Every 5 minutes, record that Ira is alive
    - Inhale:     Morning cycle -- gather, ingest, learn
    - Exhale:     Evening cycle -- dream, consolidate, report
    - Breath:     Per-request timing for pipeline health (like HRV)

Usage:
    from holistic.respiratory_system import get_respiratory_system

    resp = get_respiratory_system()
    resp.record_heartbeat()
    resp.record_breath(request_id, latency_ms, phase_timings)
    rhythm_report = resp.get_rhythm_report()
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

try:
    from openclaw.agents.ira.config import atomic_write_json, append_jsonl
except ImportError:
    from config import atomic_write_json, append_jsonl

logger = logging.getLogger("ira.respiratory_system")

HOLISTIC_DIR = Path(__file__).parent
SRC_DIR = HOLISTIC_DIR.parent
PROJECT_ROOT = SRC_DIR.parent.parent.parent.parent

HEARTBEAT_FILE = PROJECT_ROOT / "data" / "holistic" / "heartbeat.json"
BREATH_LOG = PROJECT_ROOT / "data" / "holistic" / "breath_log.jsonl"
RHYTHM_STATE = PROJECT_ROOT / "data" / "holistic" / "rhythm_state.json"


@dataclass
class Breath:
    """A single request/response cycle -- like one breath."""
    request_id: str
    timestamp: str
    total_latency_ms: float
    phase_timings: Dict[str, float] = field(default_factory=dict)
    success: bool = True
    channel: str = "unknown"


@dataclass
class DailyRhythm:
    """Tracks the daily inhale/exhale cycle."""
    date: str
    dream_mode_ran: bool = False
    dream_mode_completed: bool = False
    dream_mode_duration_s: float = 0
    morning_summary_sent: bool = False
    total_breaths: int = 0
    avg_latency_ms: float = 0
    p95_latency_ms: float = 0
    errors_count: int = 0
    immune_sweep_ran: bool = False
    metabolic_cleanup_ran: bool = False


class RespiratorySystem:
    """
    Ira's respiratory system: establishes operational rhythm and monitors
    pipeline health through breath-by-breath timing.
    """

    HEARTBEAT_INTERVAL_S = 300  # 5 minutes
    BREATH_WINDOW = 100  # Keep last N breaths for HRV calculation

    def __init__(self):
        self._state = self._load_state()
        self._recent_breaths: List[Breath] = []
        self._last_heartbeat = 0.0

    def _load_state(self) -> Dict:
        RHYTHM_STATE.parent.mkdir(parents=True, exist_ok=True)
        if RHYTHM_STATE.exists():
            try:
                return json.loads(RHYTHM_STATE.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "last_heartbeat": None,
            "heartbeat_count": 0,
            "today": None,
            "daily_rhythms": {},
            "consecutive_heartbeats": 0,
            "longest_gap_s": 0,
        }

    def _save_state(self):
        RHYTHM_STATE.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(RHYTHM_STATE, self._state)

    def record_heartbeat(self) -> Dict:
        """
        Record that Ira is alive. Should be called every 5 minutes by
        the watchdog or main loop.

        Returns heartbeat status including any gap detection.
        """
        now = time.time()
        now_iso = datetime.now().isoformat()
        result = {"alive": True, "gap_detected": False, "gap_seconds": 0}

        last = self._state.get("last_heartbeat")
        if last:
            try:
                last_dt = datetime.fromisoformat(last)
                gap = (datetime.now() - last_dt).total_seconds()
                if gap > self.HEARTBEAT_INTERVAL_S * 3:
                    result["gap_detected"] = True
                    result["gap_seconds"] = gap
                    logger.warning(
                        f"[RESPIRATORY] Heartbeat gap detected: {gap:.0f}s "
                        f"(expected <{self.HEARTBEAT_INTERVAL_S * 3}s)"
                    )
                    if gap > self._state.get("longest_gap_s", 0):
                        self._state["longest_gap_s"] = gap
            except (ValueError, TypeError):
                pass

        self._state["last_heartbeat"] = now_iso
        self._state["heartbeat_count"] = self._state.get("heartbeat_count", 0) + 1
        self._state["consecutive_heartbeats"] = (
            self._state.get("consecutive_heartbeats", 0) + 1
        )

        heartbeat_data = {
            "timestamp": now_iso,
            "count": self._state["heartbeat_count"],
            "uptime_heartbeats": self._state["consecutive_heartbeats"],
        }
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(HEARTBEAT_FILE, heartbeat_data)

        self._ensure_daily_rhythm()
        self._save_state()
        self._last_heartbeat = now

        return result

    def record_breath(
        self,
        request_id: str,
        total_latency_ms: float,
        phase_timings: Optional[Dict[str, float]] = None,
        success: bool = True,
        channel: str = "unknown",
    ):
        """
        Record a single request/response cycle (one breath).
        Phase timings map phase names to milliseconds.
        """
        breath = Breath(
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
            total_latency_ms=total_latency_ms,
            phase_timings=phase_timings or {},
            success=success,
            channel=channel,
        )

        self._recent_breaths.append(breath)
        if len(self._recent_breaths) > self.BREATH_WINDOW:
            self._recent_breaths = self._recent_breaths[-self.BREATH_WINDOW:]

        self._update_daily_stats(breath)

        entry = {
            "request_id": request_id,
            "timestamp": breath.timestamp,
            "latency_ms": total_latency_ms,
            "phases": phase_timings or {},
            "success": success,
            "channel": channel,
        }
        BREATH_LOG.parent.mkdir(parents=True, exist_ok=True)
        try:
            append_jsonl(BREATH_LOG, entry)
        except Exception as e:
            logger.warning(f"[RESPIRATORY] Failed to log breath: {e}")

    def _ensure_daily_rhythm(self):
        """Ensure we have a daily rhythm entry for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._state.get("today") != today:
            self._state["today"] = today
            if today not in self._state.get("daily_rhythms", {}):
                self._state.setdefault("daily_rhythms", {})[today] = {
                    "dream_mode_ran": False,
                    "dream_mode_completed": False,
                    "dream_mode_duration_s": 0,
                    "morning_summary_sent": False,
                    "total_breaths": 0,
                    "avg_latency_ms": 0,
                    "p95_latency_ms": 0,
                    "errors_count": 0,
                    "immune_sweep_ran": False,
                    "metabolic_cleanup_ran": False,
                }

            old_dates = sorted(self._state.get("daily_rhythms", {}).keys())
            while len(old_dates) > 30:
                del self._state["daily_rhythms"][old_dates.pop(0)]

    def _update_daily_stats(self, breath: Breath):
        """Update today's rhythm stats with a new breath."""
        self._ensure_daily_rhythm()
        today = datetime.now().strftime("%Y-%m-%d")
        rhythm = self._state["daily_rhythms"].get(today, {})

        rhythm["total_breaths"] = rhythm.get("total_breaths", 0) + 1
        if not breath.success:
            rhythm["errors_count"] = rhythm.get("errors_count", 0) + 1

        n = rhythm["total_breaths"]
        old_avg = rhythm.get("avg_latency_ms", 0)
        rhythm["avg_latency_ms"] = old_avg + (breath.total_latency_ms - old_avg) / n

        latencies = [b.total_latency_ms for b in self._recent_breaths]
        if latencies:
            latencies_sorted = sorted(latencies)
            p95_idx = int(len(latencies_sorted) * 0.95)
            rhythm["p95_latency_ms"] = latencies_sorted[min(p95_idx, len(latencies_sorted) - 1)]

        self._state["daily_rhythms"][today] = rhythm
        self._save_state()

    def record_dream_mode(self, completed: bool, duration_s: float):
        """Record that dream mode ran (or failed)."""
        self._ensure_daily_rhythm()
        today = datetime.now().strftime("%Y-%m-%d")
        rhythm = self._state["daily_rhythms"].get(today, {})
        rhythm["dream_mode_ran"] = True
        rhythm["dream_mode_completed"] = completed
        rhythm["dream_mode_duration_s"] = duration_s
        self._state["daily_rhythms"][today] = rhythm
        self._save_state()
        logger.info(
            f"[RESPIRATORY] Dream mode {'completed' if completed else 'failed'} "
            f"in {duration_s:.1f}s"
        )

    def record_morning_summary(self):
        """Record that the morning summary was sent."""
        self._ensure_daily_rhythm()
        today = datetime.now().strftime("%Y-%m-%d")
        self._state["daily_rhythms"][today]["morning_summary_sent"] = True
        self._save_state()

    def record_system_event(self, event_name: str):
        """Record that a system event occurred (immune sweep, metabolic cleanup, etc.)."""
        self._ensure_daily_rhythm()
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"{event_name}_ran"
        if key in self._state["daily_rhythms"].get(today, {}):
            self._state["daily_rhythms"][today][key] = True
            self._save_state()

    def calculate_hrv(self) -> Dict:
        """
        Calculate Heart Rate Variability equivalent: variability in
        response latencies. High HRV (moderate variability) = healthy.
        Very low HRV (uniform) = possibly stuck. Very high = unstable.
        """
        if len(self._recent_breaths) < 5:
            return {"hrv": None, "status": "insufficient_data", "sample_size": len(self._recent_breaths)}

        latencies = [b.total_latency_ms for b in self._recent_breaths]
        mean_lat = sum(latencies) / len(latencies)
        variance = sum((x - mean_lat) ** 2 for x in latencies) / len(latencies)
        std_dev = variance ** 0.5
        cv = std_dev / mean_lat if mean_lat > 0 else 0

        if cv < 0.1:
            status = "very_stable"
        elif cv < 0.3:
            status = "healthy"
        elif cv < 0.6:
            status = "variable"
        else:
            status = "unstable"

        return {
            "hrv": round(cv, 3),
            "mean_latency_ms": round(mean_lat, 1),
            "std_dev_ms": round(std_dev, 1),
            "status": status,
            "sample_size": len(latencies),
        }

    def get_rhythm_report(self) -> Dict:
        """Get comprehensive rhythm report for vital signs."""
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        today_rhythm = self._state.get("daily_rhythms", {}).get(today, {})
        yesterday_rhythm = self._state.get("daily_rhythms", {}).get(yesterday, {})

        hrv = self.calculate_hrv()

        last_dream = yesterday_rhythm.get("dream_mode_completed", False)
        dream_streak = 0
        for i in range(30):
            d = (datetime.now() - timedelta(days=i + 1)).strftime("%Y-%m-%d")
            r = self._state.get("daily_rhythms", {}).get(d, {})
            if r.get("dream_mode_completed"):
                dream_streak += 1
            else:
                break

        return {
            "heartbeat": {
                "last": self._state.get("last_heartbeat"),
                "total_count": self._state.get("heartbeat_count", 0),
                "consecutive": self._state.get("consecutive_heartbeats", 0),
                "longest_gap_s": self._state.get("longest_gap_s", 0),
            },
            "today": {
                "breaths": today_rhythm.get("total_breaths", 0),
                "avg_latency_ms": round(today_rhythm.get("avg_latency_ms", 0), 1),
                "p95_latency_ms": round(today_rhythm.get("p95_latency_ms", 0), 1),
                "errors": today_rhythm.get("errors_count", 0),
                "dream_mode_ran": today_rhythm.get("dream_mode_ran", False),
                "morning_summary": today_rhythm.get("morning_summary_sent", False),
            },
            "hrv": hrv,
            "dream_streak": dream_streak,
            "last_dream_completed": last_dream,
        }

    def check_arrhythmia(self) -> List[str]:
        """
        Check for rhythm problems (arrhythmia).
        Returns list of issues found.
        """
        issues = []
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        yesterday_rhythm = self._state.get("daily_rhythms", {}).get(yesterday, {})
        if not yesterday_rhythm.get("dream_mode_completed"):
            issues.append("Dream mode did not complete last night")

        last_hb = self._state.get("last_heartbeat")
        if last_hb:
            try:
                gap = (datetime.now() - datetime.fromisoformat(last_hb)).total_seconds()
                if gap > self.HEARTBEAT_INTERVAL_S * 6:
                    issues.append(f"Heartbeat gap: {gap/60:.0f} minutes since last heartbeat")
            except (ValueError, TypeError):
                issues.append("Cannot parse last heartbeat timestamp")

        hrv = self.calculate_hrv()
        if hrv.get("status") == "unstable":
            issues.append(f"Response latency is unstable (HRV={hrv.get('hrv', '?')})")

        today_rhythm = self._state.get("daily_rhythms", {}).get(today, {})
        if today_rhythm.get("total_breaths", 0) > 10:
            error_rate = today_rhythm.get("errors_count", 0) / today_rhythm["total_breaths"]
            if error_rate > 0.3:
                issues.append(f"High error rate today: {error_rate:.0%}")

        return issues


_instance: Optional[RespiratorySystem] = None


def get_respiratory_system() -> RespiratorySystem:
    global _instance
    if _instance is None:
        _instance = RespiratorySystem()
    return _instance
