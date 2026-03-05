"""
RealTimeHub — conversation-scoped temporary store for mid-conversation learnings.

Patterns live in memory, keyed by user_id. They are:
  - Read by the system prompt on every turn (immediate application)
  - Persisted to a JSONL file so the nightly consolidation phase can
    promote durable patterns into long-term memory (Mem0 / truth hints)
  - Cleared after nightly consolidation

This is deliberately NOT Mem0 or Qdrant — we don't want transient
conversational facts polluting the long-term knowledge base.
"""

import json
import logging
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("ira.realtime_hub")

_PROJECT_ROOT = Path(__file__).resolve().parents[5]
_HUB_DIR = _PROJECT_ROOT / "data" / "realtime_learnings"
_HUB_FILE = _HUB_DIR / "patterns.jsonl"


class PatternType(str, Enum):
    FACT = "fact"
    CORRECTION = "correction"
    PREFERENCE = "preference"


@dataclass
class LearnedPattern:
    pattern_type: PatternType
    content: str
    user_id: str
    conversation_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    confidence: float = 0.8
    promoted: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["pattern_type"] = self.pattern_type.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "LearnedPattern":
        d = dict(d)
        d["pattern_type"] = PatternType(d["pattern_type"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class RealTimeHub:
    """
    Thread-safe in-memory hub for real-time learned patterns.

    Patterns are grouped by user_id. The hub also appends every pattern
    to a JSONL file so the nightly consolidation can review them.
    """

    def __init__(self):
        self._patterns: Dict[str, List[LearnedPattern]] = {}
        self._lock = threading.Lock()
        _HUB_DIR.mkdir(parents=True, exist_ok=True)

    def publish(self, pattern: LearnedPattern) -> None:
        with self._lock:
            self._patterns.setdefault(pattern.user_id, []).append(pattern)
        self._persist(pattern)
        logger.info(
            "[RealTimeHub] Published %s for user=%s: %s",
            pattern.pattern_type.value,
            pattern.user_id,
            pattern.content[:80],
        )

    def get_patterns(
        self,
        user_id: str,
        pattern_type: Optional[PatternType] = None,
        limit: int = 20,
    ) -> List[LearnedPattern]:
        with self._lock:
            patterns = list(self._patterns.get(user_id, []))
        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]
        return patterns[-limit:]

    def get_all_patterns(self) -> List[LearnedPattern]:
        with self._lock:
            all_p = []
            for user_patterns in self._patterns.values():
                all_p.extend(user_patterns)
        return all_p

    def format_for_prompt(self, user_id: str) -> str:
        """Format patterns as a system prompt injection block."""
        patterns = self.get_patterns(user_id, limit=15)
        if not patterns:
            return ""

        lines = ["\nREAL-TIME LEARNINGS (from this conversation — apply immediately):"]
        for p in patterns:
            prefix = {
                PatternType.CORRECTION: "CORRECTION",
                PatternType.FACT: "FACT",
                PatternType.PREFERENCE: "PREFERENCE",
            }.get(p.pattern_type, "NOTE")
            lines.append(f"- [{prefix}] {p.content}")
        return "\n".join(lines)

    def clear_user(self, user_id: str) -> int:
        with self._lock:
            removed = len(self._patterns.pop(user_id, []))
        return removed

    def clear_all(self) -> int:
        with self._lock:
            total = sum(len(v) for v in self._patterns.values())
            self._patterns.clear()
        return total

    def _persist(self, pattern: LearnedPattern) -> None:
        try:
            with open(_HUB_FILE, "a") as f:
                f.write(json.dumps(pattern.to_dict()) + "\n")
        except Exception as e:
            logger.warning("[RealTimeHub] Failed to persist pattern: %s", e)

    @staticmethod
    def load_persisted() -> List[LearnedPattern]:
        """Load all patterns from the JSONL file (used by nightly consolidation)."""
        if not _HUB_FILE.exists():
            return []
        patterns = []
        for line in _HUB_FILE.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                patterns.append(LearnedPattern.from_dict(json.loads(line)))
            except Exception as e:
                logger.warning("[RealTimeHub] Skipping malformed line: %s", e)
        return patterns

    @staticmethod
    def clear_persisted() -> None:
        """Clear the JSONL file after nightly consolidation."""
        try:
            if _HUB_FILE.exists():
                _HUB_FILE.write_text("")
                logger.info("[RealTimeHub] Cleared persisted patterns file")
        except Exception as e:
            logger.warning("[RealTimeHub] Failed to clear persisted file: %s", e)


_hub_instance: Optional[RealTimeHub] = None
_hub_lock = threading.Lock()


def get_realtime_hub() -> RealTimeHub:
    global _hub_instance
    if _hub_instance is None:
        with _hub_lock:
            if _hub_instance is None:
                _hub_instance = RealTimeHub()
    return _hub_instance
