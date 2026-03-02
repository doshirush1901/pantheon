#!/usr/bin/env python3
"""
METABOLIC SYSTEM - Active Knowledge Hygiene and Cleanup
========================================================

Biological parallel:
    The liver maintains glucose. Kidneys filter waste. Adipose tissue
    regulates inflammation. These aren't glamorous but without them
    the brain starves or poisons itself.

Ira parallel:
    Ira has passive decay (unified_decay.py) but no active cleanup.
    Stale knowledge sits forever. Contradictions accumulate. Low-quality
    memories dilute retrieval. This module is the active "kidney" that
    filters, cleans, and maintains the knowledge environment.

Cleanup operations:
    1. Contradiction detection and resolution
    2. Stale knowledge identification and archival
    3. Duplicate detection and merging
    4. Low-confidence memory pruning
    5. Knowledge base statistics and health metrics

Usage:
    from holistic.metabolic_system import get_metabolic_system

    metabolic = get_metabolic_system()
    report = metabolic.run_cleanup_cycle()
    stats = metabolic.get_knowledge_stats()
"""

import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("ira.metabolic_system")

HOLISTIC_DIR = Path(__file__).parent
SRC_DIR = HOLISTIC_DIR.parent
PROJECT_ROOT = SRC_DIR.parent.parent.parent.parent

METABOLIC_STATE = PROJECT_ROOT / "data" / "holistic" / "metabolic_state.json"
CLEANUP_LOG = PROJECT_ROOT / "data" / "holistic" / "cleanup_log.jsonl"
KNOWLEDGE_AUDIT_DIR = PROJECT_ROOT / "data" / "knowledge"


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    operation: str
    items_scanned: int = 0
    items_flagged: int = 0
    items_cleaned: int = 0
    items_archived: int = 0
    details: List[str] = field(default_factory=list)


class MetabolicSystem:
    """
    Ira's metabolic system: actively maintains the knowledge environment
    through periodic cleanup, contradiction detection, and hygiene operations.
    """

    STALE_THRESHOLD_DAYS = 90
    CONTRADICTION_KEYWORDS = [
        ("≤1.5mm", "≤2mm"),
        ("only suitable for", "can handle"),
        ("not recommended", "recommended"),
        ("discontinued", "available"),
        ("closed", "operational"),
    ]

    def __init__(self):
        self._state = self._load_state()

    def _load_state(self) -> Dict:
        METABOLIC_STATE.parent.mkdir(parents=True, exist_ok=True)
        if METABOLIC_STATE.exists():
            try:
                return json.loads(METABOLIC_STATE.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "last_cleanup": None,
            "total_cleanups": 0,
            "total_items_cleaned": 0,
            "total_contradictions_found": 0,
            "total_stale_archived": 0,
            "knowledge_stats": {},
        }

    def _save_state(self):
        METABOLIC_STATE.parent.mkdir(parents=True, exist_ok=True)
        METABOLIC_STATE.write_text(json.dumps(self._state, indent=2))

    def run_cleanup_cycle(self) -> Dict[str, CleanupResult]:
        """
        Run a full cleanup cycle. Called by the respiratory system's
        daily rhythm or manually.
        """
        results = {}

        results["validation_cleanup"] = self._cleanup_validation_issues()
        results["knowledge_audit"] = self._audit_knowledge_files()
        results["feedback_hygiene"] = self._cleanup_feedback_logs()
        results["state_consistency"] = self._check_state_consistency()
        results["qdrant_hygiene"] = self.scan_qdrant_hygiene()

        self._state["last_cleanup"] = datetime.now().isoformat()
        self._state["total_cleanups"] = self._state.get("total_cleanups", 0) + 1

        total_cleaned = sum(r.items_cleaned for r in results.values())
        self._state["total_items_cleaned"] = (
            self._state.get("total_items_cleaned", 0) + total_cleaned
        )

        self._log_cleanup(results)
        self._save_state()

        logger.info(
            f"[METABOLIC] Cleanup cycle complete: "
            f"{total_cleaned} items cleaned across {len(results)} operations"
        )

        return results

    def _cleanup_validation_issues(self) -> CleanupResult:
        """
        Clean up the knowledge_health_state.json validation issues.
        Remove duplicates, consolidate recurring issues, archive old ones.
        """
        result = CleanupResult(operation="validation_cleanup")

        health_state_file = (
            SRC_DIR / "brain" / "knowledge_health_state.json"
        )
        if not health_state_file.exists():
            return result

        try:
            state = json.loads(health_state_file.read_text())
            issues = state.get("validation_issues", [])
            result.items_scanned = len(issues)

            if not issues:
                return result

            seen_signatures = {}
            deduplicated = []
            for issue in issues:
                query = issue.get("query", "")[:100]
                warnings = tuple(sorted(issue.get("warnings", [])))
                sig = f"{query}|{warnings}"

                if sig in seen_signatures:
                    seen_signatures[sig]["count"] = seen_signatures[sig].get("count", 1) + 1
                    result.items_flagged += 1
                else:
                    seen_signatures[sig] = issue
                    seen_signatures[sig]["count"] = 1
                    deduplicated.append(issue)

            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            recent = []
            archived = []
            for issue in deduplicated:
                ts = issue.get("timestamp", "")
                if ts >= cutoff:
                    recent.append(issue)
                else:
                    archived.append(issue)
                    result.items_archived += 1

            result.items_cleaned = result.items_scanned - len(recent)

            if archived:
                archive_file = KNOWLEDGE_AUDIT_DIR / "archived_validation_issues.jsonl"
                archive_file.parent.mkdir(parents=True, exist_ok=True)
                with open(archive_file, "a") as f:
                    for item in archived:
                        f.write(json.dumps(item) + "\n")

            state["validation_issues"] = recent
            health_state_file.write_text(json.dumps(state, indent=2))

            result.details.append(
                f"Deduplicated {result.items_flagged} issues, "
                f"archived {result.items_archived} old issues, "
                f"{len(recent)} remain"
            )

        except Exception as e:
            result.details.append(f"Error: {e}")
            logger.warning(f"[METABOLIC] Validation cleanup failed: {e}")

        return result

    def _audit_knowledge_files(self) -> CleanupResult:
        """Audit knowledge backup files for staleness and size."""
        result = CleanupResult(operation="knowledge_audit")

        knowledge_dir = KNOWLEDGE_AUDIT_DIR
        if not knowledge_dir.exists():
            return result

        now = datetime.now()
        stats = {"total_files": 0, "total_size_mb": 0, "stale_files": []}

        for f in knowledge_dir.glob("*.json"):
            if f.is_file():
                stats["total_files"] += 1
                size_mb = f.stat().st_size / (1024 * 1024)
                stats["total_size_mb"] += size_mb
                result.items_scanned += 1

                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                age_days = (now - mtime).days
                if age_days > self.STALE_THRESHOLD_DAYS:
                    stats["stale_files"].append({
                        "file": f.name,
                        "age_days": age_days,
                        "size_mb": round(size_mb, 2),
                    })
                    result.items_flagged += 1

        self._state["knowledge_stats"] = {
            "total_files": stats["total_files"],
            "total_size_mb": round(stats["total_size_mb"], 2),
            "stale_files_count": len(stats["stale_files"]),
            "last_audit": now.isoformat(),
        }

        if stats["stale_files"]:
            result.details.append(
                f"{len(stats['stale_files'])} knowledge files older than "
                f"{self.STALE_THRESHOLD_DAYS} days"
            )

        return result

    def _cleanup_feedback_logs(self) -> CleanupResult:
        """Clean up feedback and dream backlog files."""
        result = CleanupResult(operation="feedback_hygiene")

        log_files = [
            PROJECT_ROOT / "data" / "feedback_log.jsonl",
            PROJECT_ROOT / "data" / "feedback_backlog.jsonl",
        ]

        for log_file in log_files:
            if not log_file.exists():
                continue

            try:
                lines = log_file.read_text().strip().split("\n")
                result.items_scanned += len(lines)

                if len(lines) > 500:
                    kept = lines[-200:]
                    archived = lines[:-200]
                    result.items_cleaned += len(archived)

                    archive_path = log_file.parent / f"archive_{log_file.name}"
                    with open(archive_path, "a") as f:
                        for line in archived:
                            f.write(line + "\n")

                    log_file.write_text("\n".join(kept) + "\n")
                    result.details.append(
                        f"Archived {len(archived)} entries from {log_file.name}"
                    )

            except Exception as e:
                result.details.append(f"Error processing {log_file.name}: {e}")

        return result

    def _check_state_consistency(self) -> CleanupResult:
        """Check for inconsistencies across state files."""
        result = CleanupResult(operation="state_consistency")

        state_files = list((PROJECT_ROOT / "data" / "holistic").glob("*.json"))
        state_files.extend(
            [
                PROJECT_ROOT / "openclaw" / "data" / "learned_lessons" / "agent_scores.json",
                PROJECT_ROOT / "openclaw" / "data" / "outreach_state.json",
            ]
        )

        for sf in state_files:
            if sf.exists():
                result.items_scanned += 1
                try:
                    data = json.loads(sf.read_text())
                    if not isinstance(data, dict):
                        result.items_flagged += 1
                        result.details.append(f"{sf.name}: not a dict (type={type(data).__name__})")
                except json.JSONDecodeError as e:
                    result.items_flagged += 1
                    result.details.append(f"{sf.name}: invalid JSON ({e})")
                except Exception as e:
                    result.items_flagged += 1
                    result.details.append(f"{sf.name}: read error ({e})")

        return result

    def _log_cleanup(self, results: Dict[str, "CleanupResult"]):
        """Log cleanup results for audit trail."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operations": {
                op: {
                    "scanned": r.items_scanned,
                    "flagged": r.items_flagged,
                    "cleaned": r.items_cleaned,
                    "archived": r.items_archived,
                    "details": r.details,
                }
                for op, r in results.items()
            },
        }
        CLEANUP_LOG.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(CLEANUP_LOG, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.warning(f"[METABOLIC] Failed to log cleanup: {e}")

    def scan_qdrant_hygiene(self) -> CleanupResult:
        """
        Scan Qdrant collections for stale, duplicate, or low-quality entries.
        This is the "kidney" function -- filtering waste from the knowledge bloodstream.
        """
        result = CleanupResult(operation="qdrant_hygiene")

        try:
            from qdrant_client import QdrantClient
            import os

            qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
            client = QdrantClient(url=qdrant_url, timeout=30)

            collections_to_scan = [
                "ira_chunks_v4_voyage",
                "ira_discovered_knowledge",
            ]

            for collection_name in collections_to_scan:
                try:
                    info = client.get_collection(collection_name)
                    point_count = info.points_count or 0
                    result.items_scanned += point_count

                    points, _ = client.scroll(
                        collection_name=collection_name,
                        limit=500,
                        with_payload=True,
                    )

                    seen_hashes = {}
                    duplicate_ids = []
                    stale_ids = []
                    empty_ids = []

                    for point in points:
                        payload = point.payload or {}
                        text = payload.get("text", "")

                        if not text or len(text.strip()) < 10:
                            empty_ids.append(point.id)
                            result.items_flagged += 1
                            continue

                        import hashlib
                        text_hash = hashlib.md5(text.encode()).hexdigest()
                        if text_hash in seen_hashes:
                            duplicate_ids.append(point.id)
                            result.items_flagged += 1
                        else:
                            seen_hashes[text_hash] = point.id

                    if empty_ids:
                        result.details.append(
                            f"{collection_name}: {len(empty_ids)} empty/near-empty entries"
                        )
                    if duplicate_ids:
                        result.details.append(
                            f"{collection_name}: {len(duplicate_ids)} duplicate entries"
                        )

                    self._state.setdefault("qdrant_stats", {})[collection_name] = {
                        "total_points": point_count,
                        "duplicates": len(duplicate_ids),
                        "empty": len(empty_ids),
                        "last_scan": datetime.now().isoformat(),
                    }

                except Exception as e:
                    result.details.append(f"{collection_name}: scan error ({e})")

        except ImportError:
            result.details.append("qdrant_client not available")
        except Exception as e:
            result.details.append(f"Qdrant connection error: {e}")

        return result

    def detect_contradictions(self, texts: List[str]) -> List[Dict]:
        """
        Scan a list of knowledge texts for potential contradictions.
        Returns pairs of texts that may contradict each other.
        """
        contradictions = []

        for i, text_a in enumerate(texts):
            for j, text_b in enumerate(texts):
                if j <= i:
                    continue
                for term_a, term_b in self.CONTRADICTION_KEYWORDS:
                    if (
                        (term_a in text_a.lower() and term_b in text_b.lower())
                        or (term_b in text_a.lower() and term_a in text_b.lower())
                    ):
                        contradictions.append({
                            "text_a": text_a[:200],
                            "text_b": text_b[:200],
                            "contradiction_type": f"{term_a} vs {term_b}",
                        })

        self._state["total_contradictions_found"] = (
            self._state.get("total_contradictions_found", 0) + len(contradictions)
        )
        return contradictions

    def get_metabolic_report(self) -> Dict:
        """Get metabolic system status for vital signs."""
        knowledge_stats = self._state.get("knowledge_stats", {})

        last_cleanup = self._state.get("last_cleanup")
        if last_cleanup:
            try:
                hours_since = (
                    datetime.now() - datetime.fromisoformat(last_cleanup)
                ).total_seconds() / 3600
            except (ValueError, TypeError):
                hours_since = None
        else:
            hours_since = None

        return {
            "last_cleanup": last_cleanup,
            "hours_since_cleanup": round(hours_since, 1) if hours_since else None,
            "total_cleanups": self._state.get("total_cleanups", 0),
            "total_items_cleaned": self._state.get("total_items_cleaned", 0),
            "total_contradictions_found": self._state.get("total_contradictions_found", 0),
            "knowledge_stats": knowledge_stats,
            "cleanup_overdue": hours_since is not None and hours_since > 36,
            "health": (
                "healthy" if hours_since and hours_since < 36 else
                "needs_attention" if hours_since and hours_since < 72 else
                "overdue"
            ),
        }


_instance: Optional[MetabolicSystem] = None


def get_metabolic_system() -> MetabolicSystem:
    global _instance
    if _instance is None:
        _instance = MetabolicSystem()
    return _instance
