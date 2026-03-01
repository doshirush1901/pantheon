#!/usr/bin/env python3
"""
MINERVA RAG CORRECTIONS — Vectorized Lesson & Rule Storage
===========================================================
Stores Minerva's corrections, hard rules, and product facts as vectors
in Qdrant so they surface via semantic retrieval at inference time,
rather than being injected as static prompt text.

Also provides Mem0-backed customer conversation memory so Ira recalls
prior context when the same customer writes again.

Usage:
    # Bulk-load all corrections into Qdrant
    python -m agents.minerva.rag_corrections

    # Or from Python
    from agents.minerva.rag_corrections import store_corrections_in_qdrant
    store_corrections_in_qdrant()
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "brain"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "memory"))
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "apollo"))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

try:
    from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem
    INGESTOR_AVAILABLE = True
except ImportError:
    INGESTOR_AVAILABLE = False
    logger.warning("KnowledgeIngestor not available — Qdrant storage disabled")

try:
    from mem0_memory import get_mem0_service, Mem0MemoryService
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    logger.warning("Mem0 service not available — customer memory disabled")

try:
    from grounded_coach import SERIES_KNOWLEDGE
    SERIES_AVAILABLE = True
except ImportError:
    SERIES_KNOWLEDGE = {}
    SERIES_AVAILABLE = False
    logger.warning("SERIES_KNOWLEDGE not available — product fact ingestion will be skipped")


LESSONS_FILE = PROJECT_ROOT / "data" / "learned_lessons" / "continuous_learnings.json"
HARD_RULES_FILE = PROJECT_ROOT / "data" / "brain" / "hard_rules.txt"

CORRECTION_METADATA = {"doc_type": "minerva_correction", "source": "training"}


# =============================================================================
# QDRANT CORRECTION STORAGE
# =============================================================================

def _load_lessons() -> List[Dict[str, Any]]:
    """Load lessons from continuous_learnings.json."""
    if not LESSONS_FILE.exists():
        logger.warning("Lessons file not found: %s", LESSONS_FILE)
        return []
    try:
        data = json.loads(LESSONS_FILE.read_text())
        return data.get("lessons", [])
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error("Failed to parse lessons file: %s", exc)
        return []


def _load_hard_rules() -> List[str]:
    """Load hard rules, splitting on blank-line-separated rule blocks."""
    if not HARD_RULES_FILE.exists():
        logger.warning("Hard rules file not found: %s", HARD_RULES_FILE)
        return []
    try:
        raw = HARD_RULES_FILE.read_text()
        rules: List[str] = []
        current: List[str] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("RULE ") and current:
                rules.append("\n".join(current).strip())
                current = [line]
            elif stripped.startswith("=") and not current:
                continue
            else:
                current.append(line)
        if current:
            rules.append("\n".join(current).strip())
        return [r for r in rules if len(r) > 20]
    except Exception as exc:
        logger.error("Failed to read hard rules: %s", exc)
        return []


def _lesson_to_chunk(lesson: Dict[str, Any]) -> str:
    """Convert a lesson dict into a retrieval-friendly text chunk."""
    trigger = lesson.get("trigger", "unknown situation")
    correct = lesson.get("correct_action", lesson.get("lesson", ""))
    incorrect = lesson.get("incorrect_action", "")
    source = lesson.get("source", lesson.get("learned_from", "training"))

    parts = [f"CORRECTION: When customer asks about {trigger}, the correct answer is {correct}."]
    if incorrect:
        parts.append(f"Common mistake: {incorrect}.")
    parts.append(f"Source: {source}")
    return " ".join(parts)


def _series_to_chunk(series_name: str, info: Dict[str, Any]) -> str:
    """Convert a SERIES_KNOWLEDGE entry into a retrieval-friendly text chunk."""
    machine_type = info.get("type", "UNKNOWN")
    features = ", ".join(info.get("key_features", []))
    automation = info.get("automation_options", [])
    applications = ", ".join(info.get("applications", []))
    rules = " ".join(info.get("critical_rules", []))

    auto_desc = ", ".join(automation) if automation else "NONE"
    return (
        f"PRODUCT FACT: {series_name} Series is a {machine_type} machine. "
        f"Key features: {features}. "
        f"Automation options: {auto_desc}. "
        f"Applications: {applications}. "
        f"{rules}"
    )


def store_corrections_in_qdrant() -> Dict[str, Any]:
    """
    Bulk-load all corrections, hard rules, and product facts into Qdrant
    via KnowledgeIngestor so they surface during semantic retrieval.

    Returns:
        Summary dict with counts and any errors.
    """
    if not INGESTOR_AVAILABLE:
        return {"success": False, "error": "KnowledgeIngestor not available"}

    ingestor = KnowledgeIngestor(verbose=True, skip_duplicates=True)
    items: List[KnowledgeItem] = []

    lessons = _load_lessons()
    for lesson in lessons:
        chunk = _lesson_to_chunk(lesson)
        items.append(KnowledgeItem(
            text=chunk,
            knowledge_type="minerva_correction",
            source_file="continuous_learnings.json",
            entity=lesson.get("category", "general"),
            metadata={
                **CORRECTION_METADATA,
                "lesson_id": lesson.get("id", ""),
                "severity": lesson.get("severity", "normal"),
                "category": lesson.get("category", ""),
            },
        ))

    hard_rules = _load_hard_rules()
    for i, rule_text in enumerate(hard_rules):
        items.append(KnowledgeItem(
            text=f"HARD RULE: {rule_text}",
            knowledge_type="minerva_correction",
            source_file="hard_rules.txt",
            entity="hard_rule",
            metadata={
                **CORRECTION_METADATA,
                "rule_index": i,
            },
        ))

    if SERIES_AVAILABLE:
        for series_name, info in SERIES_KNOWLEDGE.items():
            chunk = _series_to_chunk(series_name, info)
            items.append(KnowledgeItem(
                text=chunk,
                knowledge_type="minerva_correction",
                source_file="grounded_coach.py",
                entity=series_name,
                metadata={
                    **CORRECTION_METADATA,
                    "series": series_name,
                    "machine_type": info.get("type", ""),
                },
            ))

    if not items:
        logger.warning("No correction items to ingest")
        return {"success": False, "error": "No items found", "items": 0}

    logger.info("Ingesting %d correction items into Qdrant...", len(items))
    result = ingestor.ingest_batch(items)

    summary = {
        "success": result.success,
        "items_ingested": result.items_ingested,
        "items_skipped": result.items_skipped,
        "lessons_loaded": len(lessons),
        "hard_rules_loaded": len(hard_rules),
        "series_loaded": len(SERIES_KNOWLEDGE) if SERIES_AVAILABLE else 0,
        "qdrant_main": result.qdrant_main,
        "qdrant_discovered": result.qdrant_discovered,
        "errors": result.errors,
    }
    logger.info("Ingestion complete: %s", summary)
    return summary


def store_single_correction(lesson: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store one correction as a vector immediately (e.g. after a live training session).

    Args:
        lesson: Dict with keys: trigger, correct_action, incorrect_action, source, etc.

    Returns:
        Summary dict with ingestion result.
    """
    if not INGESTOR_AVAILABLE:
        return {"success": False, "error": "KnowledgeIngestor not available"}

    chunk = _lesson_to_chunk(lesson)
    ingestor = KnowledgeIngestor(verbose=False, skip_duplicates=True)
    result = ingestor.ingest(
        text=chunk,
        knowledge_type="minerva_correction",
        source_file="live_correction",
        entity=lesson.get("category", "general"),
        metadata={
            **CORRECTION_METADATA,
            "lesson_id": lesson.get("id", ""),
            "severity": lesson.get("severity", "normal"),
            "ingested_at": datetime.now().isoformat(),
        },
    )
    return {
        "success": result.success,
        "items_ingested": result.items_ingested,
        "errors": result.errors,
    }


# =============================================================================
# MEM0 CUSTOMER CONVERSATION MEMORY
# =============================================================================

def store_conversation_in_mem0(
    customer_email: str,
    conversation_turns: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Store a customer conversation in Mem0 so Ira recalls context next time.

    Args:
        customer_email: The customer's email address (used as user_id).
        conversation_turns: List of dicts, each with at least a "content" key
                            and optionally "role", "summary", "timestamp".

    Returns:
        Summary dict with stored memory IDs.
    """
    if not MEM0_AVAILABLE:
        return {"success": False, "error": "Mem0 service not available", "stored": []}

    try:
        mem0 = get_mem0_service()
    except Exception as exc:
        logger.error("Failed to initialise Mem0: %s", exc)
        return {"success": False, "error": str(exc), "stored": []}

    stored_ids: List[Optional[str]] = []
    for i, turn in enumerate(conversation_turns):
        text = turn.get("summary") or turn.get("content", "")
        if not text:
            continue
        ts = turn.get("timestamp", datetime.now().isoformat())
        mem_id = mem0.add_memory(
            text=text,
            user_id=customer_email,
            metadata={
                "channel": "email",
                "turn": i + 1,
                "timestamp": ts,
            },
        )
        stored_ids.append(mem_id)

    return {
        "success": True,
        "stored": stored_ids,
        "turns_processed": len(stored_ids),
    }


def recall_customer_context(customer_email: str, current_query: str) -> str:
    """
    Retrieve relevant memories for a returning customer.

    Args:
        customer_email: The customer's email address.
        current_query: The customer's latest message / question.

    Returns:
        Formatted string of relevant memories ready for prompt injection,
        or empty string if nothing found.
    """
    if not MEM0_AVAILABLE:
        return ""

    try:
        mem0 = get_mem0_service()
    except Exception as exc:
        logger.error("Failed to initialise Mem0: %s", exc)
        return ""

    memories = mem0.search(query=current_query, user_id=customer_email, limit=5)
    if not memories:
        return ""

    lines = ["Previous context with this customer:"]
    for mem in memories:
        lines.append(f"- {mem.memory}")
    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=" * 60)
    print("MINERVA RAG CORRECTIONS — Bulk Loader")
    print("=" * 60)

    summary = store_corrections_in_qdrant()

    print()
    print(f"  Lessons loaded:     {summary.get('lessons_loaded', 0)}")
    print(f"  Hard rules loaded:  {summary.get('hard_rules_loaded', 0)}")
    print(f"  Series loaded:      {summary.get('series_loaded', 0)}")
    print(f"  Items ingested:     {summary.get('items_ingested', 0)}")
    print(f"  Items skipped:      {summary.get('items_skipped', 0)}")
    print(f"  Qdrant main:        {summary.get('qdrant_main', False)}")
    print(f"  Qdrant discovered:  {summary.get('qdrant_discovered', False)}")
    if summary.get("errors"):
        print(f"  Errors:             {summary['errors']}")
    print()
    print("Done." if summary.get("success") else "Failed — see errors above.")
