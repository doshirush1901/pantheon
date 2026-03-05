"""
Chat Log — Rushabh ↔ Ira interaction log for training and dream learning.

Logs every Rushabh-Ira conversation from email and Telegram.
Marks feedback/correction messages for overnight dream processing.

Usage:
    from openclaw.agents.ira.src.conversation.chat_log import log_interaction, get_feedback_backlog
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ira.chat_log")

# Rushabh identifiers (from env or defaults)
RUSHABH_EMAILS = os.environ.get("RUSHABH_EMAILS", "").split(",")
RUSHABH_TELEGRAM_IDS = [x.strip() for x in os.environ.get("RUSHABH_TELEGRAM_IDS", "").split(",") if x.strip()]
if not RUSHABH_EMAILS or RUSHABH_EMAILS == [""]:
    RUSHABH_EMAILS = ["founder@example-company.org", "founder@example.com"]
if not RUSHABH_TELEGRAM_IDS:
    RUSHABH_TELEGRAM_IDS = []

# Feedback keywords — messages containing these are tagged for dream processing
FEEDBACK_KEYWORDS = [
    "fix", "change", "update", "bug", "wrong", "should be", "please change",
    "correct", "incorrect", "mistake", "correction", "update the", "change the",
    "don't", "do not", "stop", "instead", "actually", "rather", "prefer",
    "feedback", "improve", "better if", "suggest", "implement", "add support"
]


def _is_rushabh(channel: str, user_id: Optional[str]) -> bool:
    """Check if user_id belongs to Rushabh."""
    if not user_id:
        return False
    user_lower = user_id.lower().strip()
    if channel == "email":
        return any(e.strip().lower() in user_lower or user_lower in e.strip().lower() 
                  for e in RUSHABH_EMAILS if e)
    if channel == "telegram":
        return str(user_id) in RUSHABH_TELEGRAM_IDS
    return False


def _looks_like_feedback(text: str) -> bool:
    """Heuristic: does this message look like a fix/correction request?"""
    if not text or len(text) < 10:
        return False
    t = text.lower()
    return any(kw in t for kw in FEEDBACK_KEYWORDS)


def _get_log_path() -> Path:
    """Path to append-only JSONL chat log."""
    # openclaw/agents/ira/src/conversation/chat_log.py -> project root is 6 levels up
    base = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
    data_dir = base / "data" / "chat_log"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "rushabh_ira_chat.jsonl"


def log_interaction(
    channel: str,
    user_id: Optional[str],
    role: str,
    content: str,
    metadata: Optional[dict] = None,
) -> None:
    """
    Log one message in the Rushabh-Ira chat log.
    Only logs interactions involving Rushabh.
    """
    if not _is_rushabh(channel, user_id):
        return
    log_path = _get_log_path()
    is_feedback = _looks_like_feedback(content) if role == "user" else False
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "channel": channel,
        "user_id": user_id,
        "role": role,
        "content": content[:5000],
        "is_feedback": is_feedback,
        "metadata": metadata or {},
    }
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Chat log write failed: %s", e)
