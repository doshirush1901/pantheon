#!/usr/bin/env python3
"""
EXCRETION: Quality Filter for Knowledge Ingestion
==================================================

The "Excretion" organ in Ira's digestive architecture. Filters out low-quality,
noisy, or redundant content BEFORE it enters the knowledge base.

Biological analogy: Waste disposal — identifying and discarding content that
does not contribute to the agent's knowledge.

Quality checks:
- Min word count (default 50 words) — rejects tiny fragments
- Information density — rejects repetitive, number-heavy, or boilerplate text
- Boilerplate patterns — common noise (copyright, nav bars, "loading...")

Usage:
    from quality_filter import filter_by_quality, QualityFilterConfig
    
    passed, rejected = filter_by_quality(items, config=QualityFilterConfig())
"""

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

BRAIN_DIR = Path(__file__).parent
PROJECT_ROOT = BRAIN_DIR.parent.parent.parent.parent.parent
EXCRETION_LOG = PROJECT_ROOT / "data" / "knowledge" / "excretion_log.jsonl"


@dataclass
class QualityFilterConfig:
    """Configurable thresholds for quality filtering."""
    min_words: int = 50
    min_unique_word_ratio: float = 0.15
    max_numeric_ratio: float = 0.7
    require_english: bool = False
    log_rejected: bool = True
    semantic_dedup_threshold: float = 0.95  # cosine similarity above this = near-duplicate


# Common boilerplate patterns that indicate low-value content
BOILERPLATE_PATTERNS = [
    r"^\s*(loading|please wait|click here|read more)\s*$",
    r"©\s*\d{4}",
    r"all rights reserved",
    r"confidential\s*$",
    r"page\s+\d+\s+of\s+\d+",
    r"^[\d\s\.\-]+$",
    r"^\s*[-=_]{20,}\s*$",
    r"^\s*\[.*\]\s*$",
    r"^(yes|no|n/a|tbd)\s*$",
]


def _word_count(text: str) -> int:
    """Count words (split on whitespace)."""
    return len(text.split()) if text.strip() else 0


def _unique_word_ratio(text: str) -> float:
    """Ratio of unique words to total words. Low = repetitive."""
    words = text.lower().split()
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def _numeric_ratio(text: str) -> float:
    """Ratio of numeric/symbol chars to total. High = table dump, not prose."""
    if not text.strip():
        return 0.0
    digits = sum(1 for c in text if c.isdigit())
    symbols = sum(1 for c in text if c in ".,;:-+*/%=€₹$")
    total = len([c for c in text if not c.isspace()])
    if total == 0:
        return 0.0
    return (digits + symbols) / total


def _is_boilerplate(text: str) -> bool:
    """Check if text matches known boilerplate patterns."""
    t = text.strip().lower()[:500]
    for pat in BOILERPLATE_PATTERNS:
        if re.search(pat, t, re.IGNORECASE):
            return True
    return False


def _passes_quality(text: str, config: QualityFilterConfig) -> Tuple[bool, Optional[str]]:
    """Check if a single text chunk passes quality. Returns (passed, rejection_reason)."""
    if not text or not text.strip():
        return False, "empty"

    words = _word_count(text)
    if words < config.min_words:
        return False, f"too_short:{words}_words"

    if _is_boilerplate(text):
        return False, "boilerplate"

    unique_ratio = _unique_word_ratio(text)
    if unique_ratio < config.min_unique_word_ratio:
        return False, f"repetitive:unique_ratio={unique_ratio:.2f}"

    num_ratio = _numeric_ratio(text)
    if num_ratio > config.max_numeric_ratio:
        return False, f"numeric_heavy:ratio={num_ratio:.2f}"

    return True, None


def filter_by_quality(
    items: List[Any],
    config: Optional[QualityFilterConfig] = None,
    text_attr: str = "text",
) -> Tuple[List[Any], List[dict]]:
    """Filter knowledge items by quality. Returns (passed_items, rejected_with_reasons).

    Args:
        items: List of objects with a .text attribute (e.g. KnowledgeItem)
        config: Quality thresholds; uses defaults if None
        text_attr: Attribute name for text content (default "text")

    Returns:
        (passed_items, rejected_list) where rejected_list has {"item": ..., "reason": ...}
    """
    config = config or QualityFilterConfig()
    passed = []
    rejected = []

    for item in items:
        text = getattr(item, text_attr, None)
        if text is None:
            rejected.append({"item": item, "reason": "no_text_attr"})
            continue

        ok, reason = _passes_quality(str(text), config)
        if ok:
            passed.append(item)
        else:
            rejected.append({"item": item, "reason": reason})
            if config.log_rejected:
                _log_rejection(item, reason, text[:200])

    if rejected:
        logger.info(f"[EXCRETION] Filtered {len(rejected)} low-quality items, {len(passed)} passed")

    return passed, rejected


def _log_rejection(item: Any, reason: str, text_preview: str) -> None:
    """Append to excretion audit log."""
    try:
        EXCRETION_LOG.parent.mkdir(parents=True, exist_ok=True)
        import json
        entry = {
            "reason": reason,
            "source_file": getattr(item, "source_file", ""),
            "entity": getattr(item, "entity", ""),
            "preview": text_preview[:200],
        }
        with open(EXCRETION_LOG, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        logger.debug(f"Excretion log write failed: {e}")


def check_semantic_duplicate(
    text: str,
    collection_name: str = "ira_chunks_v4_voyage",
    threshold: float = 0.95,
    qdrant_url: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """Check if text is a near-duplicate of existing content in Qdrant.

    Generates an embedding for the text and queries Qdrant for chunks with
    cosine similarity above the threshold.

    Returns:
        (is_duplicate, matching_source_file_or_None)
    """
    import os

    try:
        import voyageai
        from qdrant_client import QdrantClient
    except ImportError:
        return False, None

    voyage_key = os.environ.get("VOYAGE_API_KEY")
    if not voyage_key:
        return False, None

    try:
        voyage = voyageai.Client(api_key=voyage_key)
        embedding = voyage.embed([text], model="voyage-3", input_type="document").embeddings[0]
    except Exception as e:
        logger.debug(f"[SEMANTIC_DEDUP] Embedding failed: {e}")
        return False, None

    try:
        url = qdrant_url or os.environ.get("QDRANT_URL", "http://localhost:6333")
        client = QdrantClient(url=url)
        results = client.query_points(
            collection_name=collection_name,
            query=embedding,
            limit=1,
            with_payload=True,
        ).points
    except Exception as e:
        logger.debug(f"[SEMANTIC_DEDUP] Qdrant query failed: {e}")
        return False, None

    if results and results[0].score >= threshold:
        match = results[0]
        source = (match.payload or {}).get("filename", "unknown")
        logger.info(
            f"[SEMANTIC_DEDUP] Near-duplicate detected (score={match.score:.3f}) "
            f"matching '{source}'"
        )
        return True, source

    return False, None


def filter_semantic_duplicates(
    items: List[Any],
    config: Optional[QualityFilterConfig] = None,
    collection_name: str = "ira_chunks_v4_voyage",
    text_attr: str = "text",
) -> Tuple[List[Any], List[dict]]:
    """Filter items that are near-duplicates of existing Qdrant content.

    Returns:
        (unique_items, duplicate_list) where duplicate_list has {"item", "reason", "match_source"}
    """
    config = config or QualityFilterConfig()
    unique = []
    duplicates = []

    for item in items:
        text = getattr(item, text_attr, None)
        if text is None:
            unique.append(item)
            continue

        is_dup, match_source = check_semantic_duplicate(
            str(text),
            collection_name=collection_name,
            threshold=config.semantic_dedup_threshold,
        )
        if is_dup:
            reason = f"semantic_duplicate:match={match_source}"
            duplicates.append({"item": item, "reason": reason, "match_source": match_source})
            if config.log_rejected:
                _log_rejection(item, reason, str(text)[:200])
        else:
            unique.append(item)

    if duplicates:
        logger.info(f"[SEMANTIC_DEDUP] Rejected {len(duplicates)} near-duplicates, {len(unique)} unique")

    return unique, duplicates


def run_waste_disposal(
    collection_name: str = "ira_chunks_v4_voyage",
    qdrant_url: Optional[str] = None,
    config: Optional[QualityFilterConfig] = None,
    dry_run: bool = True,
    batch_size: int = 100,
) -> dict:
    """EXCRETION: Periodically remove low-quality content from Qdrant.

    Scrolls through the collection, re-runs quality filter on each point's text,
    and deletes points that fail. Use dry_run=True to audit without deleting.

    Returns:
        {"scanned": N, "failed_quality": M, "deleted": K (or 0 if dry_run)}
    """
    config = config or QualityFilterConfig()
    result = {"scanned": 0, "failed_quality": 0, "deleted": 0}

    try:
        from qdrant_client import QdrantClient
        import os
        url = qdrant_url or os.environ.get("QDRANT_URL", "http://localhost:6333")
        client = QdrantClient(url=url)
    except ImportError:
        logger.warning("qdrant-client not installed; waste disposal skipped")
        return result
    except Exception as e:
        logger.warning(f"Qdrant connection failed: {e}")
        return result

    to_delete = []
    offset = None

    while True:
        try:
            records, offset = client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as e:
            logger.warning(f"Qdrant scroll failed: {e}")
            break

        if not records:
            break

        for pt in records:
            result["scanned"] += 1
            text = (pt.payload or {}).get("text") or (pt.payload or {}).get("raw_text") or ""
            ok, reason = _passes_quality(text, config)
            if not ok:
                result["failed_quality"] += 1
                to_delete.append(pt.id)
                if config.log_rejected:
                    _log_rejection(
                        type("Item", (), {"source_file": pt.payload.get("filename", ""), "entity": pt.payload.get("machines", [""])[0] if pt.payload.get("machines") else ""})(),
                        reason,
                        text[:200],
                    )

        if offset is None:
            break

    if to_delete and not dry_run:
        try:
            from qdrant_client.models import PointIdsList
            client.delete(
                collection_name=collection_name,
                points_selector=PointIdsList(points=to_delete),
            )
            result["deleted"] = len(to_delete)
            logger.info(f"[EXCRETION] Waste disposal: deleted {len(to_delete)} low-quality points from {collection_name}")
        except Exception as e:
            logger.warning(f"Qdrant delete failed: {e}")

    elif to_delete and dry_run:
        logger.info(f"[EXCRETION] Waste disposal (dry run): would delete {len(to_delete)} low-quality points from {collection_name}")

    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="EXCRETION: Quality filter and waste disposal")
    parser.add_argument("--waste-disposal", action="store_true", help="Run waste disposal on Qdrant")
    parser.add_argument("--collection", default="ira_chunks_v4_voyage", help="Qdrant collection name")
    parser.add_argument("--execute", action="store_true", help="Actually delete (default: dry run)")
    args = parser.parse_args()

    if args.waste_disposal:
        r = run_waste_disposal(
            collection_name=args.collection,
            dry_run=not args.execute,
        )
        print(f"Scanned: {r['scanned']} | Failed quality: {r['failed_quality']} | Deleted: {r['deleted']}")
    else:
        print("Use --waste-disposal to run waste disposal. Use --execute to actually delete.")
