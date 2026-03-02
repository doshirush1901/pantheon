"""
Service Health Tracker

Makes failures in external services (Mem0, Qdrant, Neo4j) visible instead of
silently degrading to empty results. Tracks failure counts over a rolling window
and escalates logging when a service is degraded.

Usage:
    from openclaw.agents.ira.src.core.service_health import record_failure, record_success, get_health_summary

    try:
        result = mem0.search(query, uid)
        record_success("mem0")
    except Exception as e:
        record_failure("mem0", str(e))
"""

import logging
import time
from collections import defaultdict
from typing import Any, Dict

logger = logging.getLogger("ira.service_health")

WINDOW_SECONDS = 600  # 10-minute rolling window
DEGRADED_THRESHOLD = 3  # failures in window before escalating to ERROR

_failures: Dict[str, list] = defaultdict(list)
_last_success: Dict[str, float] = {}


def record_failure(service: str, error: str) -> None:
    now = time.time()
    _failures[service].append(now)
    _failures[service] = [t for t in _failures[service] if now - t < WINDOW_SECONDS]
    count = len(_failures[service])

    if count >= DEGRADED_THRESHOLD:
        logger.error(
            "SERVICE_DEGRADED: %s has failed %d times in %ds. Latest: %s",
            service, count, WINDOW_SECONDS, error,
        )
    else:
        logger.warning("SERVICE_FAILURE: %s: %s", service, error)


def record_success(service: str) -> None:
    _last_success[service] = time.time()
    _failures[service].clear()


def get_health_summary() -> Dict[str, Any]:
    """Return a snapshot of service health for /health command or monitoring."""
    now = time.time()
    summary = {}
    all_services = set(list(_failures.keys()) + list(_last_success.keys()))

    for svc in sorted(all_services):
        recent_failures = [t for t in _failures.get(svc, []) if now - t < WINDOW_SECONDS]
        last_ok = _last_success.get(svc)
        summary[svc] = {
            "status": "degraded" if len(recent_failures) >= DEGRADED_THRESHOLD else "ok",
            "failures_10m": len(recent_failures),
            "last_success_ago_s": round(now - last_ok) if last_ok else None,
        }

    return summary


def format_health_report() -> str:
    """Human-readable health report for Telegram /health command."""
    summary = get_health_summary()
    if not summary:
        return "No service activity recorded yet."

    lines = ["Service Health:"]
    for svc, info in summary.items():
        icon = "RED" if info["status"] == "degraded" else "GREEN"
        ago = f"{info['last_success_ago_s']}s ago" if info["last_success_ago_s"] is not None else "never"
        lines.append(f"  [{icon}] {svc}: {info['failures_10m']} failures (last OK: {ago})")
    return "\n".join(lines)
