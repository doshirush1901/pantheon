"""
Service Health Tracker

Tracks the health of external services (Mem0, Qdrant, Neo4j, OpenAI) so that
silent failures become visible. When a service fails repeatedly, it escalates
from debug to WARNING to ERROR level logging.

Usage:
    from openclaw.agents.ira.src.core.service_health import record_failure, record_success, get_health_summary

    try:
        result = mem0.search(query, user_id)
        record_success("mem0")
    except Exception as e:
        record_failure("mem0", str(e))

    # In /health command:
    summary = get_health_summary()
"""

import logging
import time
from collections import defaultdict
from typing import Dict, Optional

logger = logging.getLogger("ira.service_health")

_failures: Dict[str, list] = defaultdict(list)
_last_success: Dict[str, float] = {}
_failure_window_seconds = 600  # 10 minutes


def record_failure(service: str, error: str) -> None:
    """Record a service failure. Escalates log level based on failure frequency."""
    now = time.time()
    _failures[service].append(now)
    _failures[service] = [t for t in _failures[service] if now - t < _failure_window_seconds]
    count = len(_failures[service])

    if count >= 5:
        logger.error(f"SERVICE_DOWN: {service} has failed {count} times in 10 min. Latest: {error}")
    elif count >= 3:
        logger.warning(f"SERVICE_DEGRADED: {service} has failed {count} times in 10 min. Latest: {error}")
    else:
        logger.warning(f"SERVICE_FAILURE: {service}: {error}")


def record_success(service: str) -> None:
    """Record a successful service call. Clears the failure window."""
    _last_success[service] = time.time()
    if service in _failures:
        _failures[service].clear()


def get_health_summary() -> Dict[str, dict]:
    """Get a summary of all tracked services for diagnostics.
    
    Returns dict like:
        {"mem0": {"status": "healthy", "failures_10m": 0, "last_success_ago_s": 12},
         "qdrant": {"status": "degraded", "failures_10m": 4, "last_success_ago_s": 300}}
    """
    now = time.time()
    all_services = set(list(_failures.keys()) + list(_last_success.keys()))
    summary = {}

    for svc in sorted(all_services):
        recent_failures = len([t for t in _failures.get(svc, []) if now - t < _failure_window_seconds])
        last_ok = _last_success.get(svc)
        last_ok_ago: Optional[int] = round(now - last_ok) if last_ok else None

        if recent_failures >= 5:
            status = "down"
        elif recent_failures >= 3:
            status = "degraded"
        elif recent_failures >= 1:
            status = "flaky"
        else:
            status = "healthy"

        summary[svc] = {
            "status": status,
            "failures_10m": recent_failures,
            "last_success_ago_s": last_ok_ago,
        }

    return summary


def format_health_report() -> str:
    """Format health summary as a human-readable string for Telegram /health."""
    summary = get_health_summary()
    if not summary:
        return "No service activity tracked yet."

    status_icons = {"healthy": "✅", "flaky": "⚠️", "degraded": "🟡", "down": "🔴"}
    lines = ["**Service Health Report**\n"]
    for svc, info in summary.items():
        icon = status_icons.get(info["status"], "❓")
        ago = f"{info['last_success_ago_s']}s ago" if info["last_success_ago_s"] is not None else "never"
        lines.append(f"{icon} **{svc}**: {info['status']} ({info['failures_10m']} failures/10m, last OK: {ago})")

    return "\n".join(lines)
