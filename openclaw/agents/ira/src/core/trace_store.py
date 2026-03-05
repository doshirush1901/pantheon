"""
Persistent Agent Trace Store — JSONL log of every pipeline execution.

Each request produces one trace record containing:
- Request metadata (timestamp, user, channel, request_id)
- Ordered list of agent activations with timing and status
- Pipeline outcome (total elapsed, tool count, sphinx/truth-hint short-circuit)

Traces are appended to data/logs/agent_traces.jsonl — one JSON object per line.
Designed for offline analysis: which agents are slow, which combos are common,
where the pipeline bottlenecks.
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.trace_store")

_TRACE_LOG_PATH = Path("data/logs/agent_traces.jsonl")
_write_lock = threading.Lock()


class PipelineTrace:
    """Accumulates events for a single pipeline execution, then flushes to disk."""

    def __init__(
        self,
        request_id: str,
        user_id: str = "unknown",
        channel: str = "api",
        message_preview: str = "",
    ):
        self.request_id = request_id
        self.user_id = user_id
        self.channel = channel
        self.message_preview = message_preview[:120]
        self.started_at = time.time()
        self.events: List[Dict[str, Any]] = []
        self._flushed = False

    def record(self, event: Dict[str, Any]):
        """Record a pipeline event (tool call, agent activation, etc.)."""
        event.setdefault("ts", round(time.time() - self.started_at, 3))
        self.events.append(event)

    def record_tool(
        self,
        tool: str,
        agent: str,
        status: str = "ok",
        elapsed_s: float = 0,
        round_num: int = 0,
    ):
        self.record({
            "type": "tool",
            "tool": tool,
            "agent": agent,
            "status": status,
            "elapsed_s": round(elapsed_s, 2),
            "round": round_num,
        })

    def record_agent(self, agent: str, activity: str, phase: str = ""):
        self.record({
            "type": "agent",
            "agent": agent,
            "activity": activity,
            "phase": phase,
        })

    def record_shortcircuit(self, reason: str):
        """Record when the pipeline short-circuits (truth hint, Sphinx gate, etc.)."""
        self.record({"type": "shortcircuit", "reason": reason})

    def flush(
        self,
        success: bool = True,
        tool_count: int = 0,
        total_rounds: int = 0,
        cost_usd: float = 0,
    ):
        """Write the completed trace to disk. Safe to call multiple times (only writes once)."""
        if self._flushed:
            return
        self._flushed = True

        elapsed = round(time.time() - self.started_at, 2)
        record = {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "channel": self.channel,
            "message_preview": self.message_preview,
            "started_at": self.started_at,
            "elapsed_s": elapsed,
            "success": success,
            "tool_count": tool_count,
            "total_rounds": total_rounds,
            "cost_usd": round(cost_usd, 4),
            "events": self.events,
        }
        _append_trace(record)


def _append_trace(record: Dict[str, Any]):
    """Thread-safe append of a single JSON line to the trace log."""
    try:
        _TRACE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, default=str) + "\n"
        with _write_lock:
            with open(_TRACE_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception as e:
        logger.warning("[TraceStore] Failed to write trace: %s", e)


def get_trace_log_path() -> Path:
    return _TRACE_LOG_PATH
