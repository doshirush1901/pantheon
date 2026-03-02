#!/usr/bin/env python3
"""
KNOWLEDGE HYGIENE - Phase 6: Active Metabolism / Kidney System
==============================================================

Beyond the Brain: Like the kidneys filter blood, this module identifies
and flags knowledge that is stale, contradictory, or violates hard rules.

Does NOT delete directly - produces reports and queues for:
- Dream mode (re-ingest corrected content)
- Human review (feedback_backlog)
- Immune remediation (recurring issues)

Usage:
    from knowledge_hygiene import run_knowledge_hygiene

    report = run_knowledge_hygiene()
"""

import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent
# data/brain is at project root for worktree compatibility
HARD_RULES_HYGIENE_FILE = PROJECT_ROOT / "data" / "brain" / "hard_rules_hygiene.json"
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))

logger = logging.getLogger(__name__)

# Fallback when JSON not found
DEFAULT_HARD_RULE_PATTERNS = [
    {"id": "am_max_1_5mm", "wrong": [r"am.*2\s*mm"], "correct": "AM Series: ≤1.5mm ONLY", "entity": "AM Series"},
    {"id": "pf1_heavy_gauge", "wrong": [r"pf1.*thin", r"pf1.*packaging"], "correct": "PF1 is heavy-gauge", "entity": "PF1"},
    {"id": "pf2_bath_only", "wrong": [r"pf2.*automotive"], "correct": "PF2 is bath only", "entity": "PF2"},
]


def _load_hard_rules() -> List[Dict]:
    """Load hard rules from hard_rules_hygiene.json (synced with hard_rules.txt)."""
    if HARD_RULES_HYGIENE_FILE.exists():
        try:
            data = json.loads(HARD_RULES_HYGIENE_FILE.read_text())
            rules = data.get("rules", [])
            return [
                {
                    "id": r["id"],
                    "entity": r.get("entity", ""),
                    "correct": r.get("correct", ""),
                    "wrong": r.get("wrong_patterns", r.get("wrong", [])),
                    "exclude": r.get("exclude_patterns", []),
                }
                for r in rules
            ]
        except Exception as e:
            logger.warning(f"Could not load hard_rules_hygiene.json: {e}")
    return [
        {"id": r["id"], "entity": r["entity"], "correct": r["correct"], "wrong": r["wrong"], "exclude": []}
        for r in DEFAULT_HARD_RULE_PATTERNS
    ]


@dataclass
class HygieneIssue:
    """A knowledge hygiene issue detected."""
    id: str
    severity: str  # 'critical', 'warning', 'info'
    category: str  # 'contradiction', 'hard_rule_violation', 'stale', 'correction_mismatch'
    message: str
    entity: str = ""
    source: str = ""  # qdrant_chunk_id, mem0_id, file path
    details: Dict = field(default_factory=dict)
    suggested_action: str = ""


@dataclass
class HygieneReport:
    """Result of a knowledge hygiene run."""
    timestamp: str
    issues: List[HygieneIssue]
    corrections_checked: int
    chunks_scanned: int
    duration_seconds: float
    remediated: int = 0  # Facts injected into Mem0

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "issues_count": len(self.issues),
            "corrections_checked": self.corrections_checked,
            "chunks_scanned": self.chunks_scanned,
            "duration_seconds": round(self.duration_seconds, 2),
            "remediated": self.remediated,
            "issues": [
                {
                    "id": i.id,
                    "severity": i.severity,
                    "category": i.category,
                    "message": i.message,
                    "entity": i.entity,
                    "suggested_action": i.suggested_action,
                }
                for i in self.issues
            ],
        }


def _get_qdrant():
    """Lazy load Qdrant client."""
    try:
        from qdrant_client import QdrantClient
        from config import QDRANT_URL, COLLECTIONS
        return QdrantClient(url=os.environ.get("QDRANT_URL", QDRANT_URL))
    except ImportError:
        return None


def _get_corrections() -> List[Dict]:
    """Load learned corrections."""
    try:
        sys.path.insert(0, str(BRAIN_DIR))
        from correction_learner import get_learner
        learner = get_learner()
        return [
            {
                "entity": c.entity,
                "original": c.original,
                "corrected": c.corrected,
                "id": c.id,
            }
            for c in learner.corrections.values()
            if c.correction_type == "fact"
        ]
    except Exception as e:
        logger.warning(f"Could not load corrections: {e}")
        return []


def _scan_qdrant_for_violations(
    collection: str, rules: List[Dict], limit: int = 500
) -> List[Tuple[str, str, Dict]]:
    """
    Scan Qdrant chunks for hard rule violations.
    Returns list of (chunk_id, text, payload, rule) for chunks that may violate rules.
    Respects exclude_patterns to reduce false positives.
    """
    client = _get_qdrant()
    if not client:
        return []

    issues = []
    try:
        results, _ = client.scroll(
            collection_name=collection,
            limit=limit,
            with_payload=True,
        )

        for point in results:
            payload = point.payload or {}
            text = (payload.get("text") or "").lower()
            chunk_id = str(point.id)

            for rule in rules:
                exclude = rule.get("exclude", [])
                if any(re.search(p, text, re.IGNORECASE) for p in exclude):
                    continue  # Skip if exclusion matches (e.g. "not 2mm" = correct)
                for wrong_pat in rule.get("wrong", []):
                    if re.search(wrong_pat, text, re.IGNORECASE):
                        issues.append((chunk_id, payload.get("text", "")[:300], payload, rule))
                        break
    except Exception as e:
        logger.warning(f"Qdrant scan failed: {e}")

    return issues


def _check_correction_consistency(corrections: List[Dict]) -> List[HygieneIssue]:
    """Check if any corrections imply existing knowledge might be wrong."""
    issues = []
    for c in corrections:
        orig = (c.get("original") or "").lower()
        if "2mm" in orig or "2 mm" in orig:
            if "am" in orig or "am series" in orig:
                issues.append(HygieneIssue(
                    id=f"correction_{c.get('id', 'unknown')}",
                    severity="info",
                    category="correction_mismatch",
                    message=f"Correction exists: '{c.get('original', '')[:50]}' -> '{c.get('corrected', '')[:50]}'",
                    entity=c.get("entity", "AM Series"),
                    source="correction_learner",
                    details=c,
                    suggested_action="Ensure Qdrant/Mem0 chunks reflect corrected fact",
                ))
    return issues


def _check_hard_rules() -> List[HygieneIssue]:
    """Scan knowledge base for hard rule violations (rules from hard_rules_hygiene.json)."""
    issues = []
    rules = _load_hard_rules()
    collections = ["ira_chunks_v4_voyage", "ira_discovered_knowledge"]

    for coll in collections:
        try:
            violations = _scan_qdrant_for_violations(coll, rules, limit=300)
            for chunk_id, text, payload, rule in violations:
                issues.append(HygieneIssue(
                    id=f"hard_rule_{rule['id']}_{chunk_id[:8]}",
                    severity="critical",
                    category="hard_rule_violation",
                    message=f"Chunk may violate: {rule['correct']}",
                    entity=rule.get("entity", ""),
                    source=f"qdrant:{coll}:{chunk_id}",
                    details={"text_preview": text[:200], "rule": rule},
                    suggested_action="Re-ingest with corrected content or flag for removal",
                ))
        except Exception as e:
            logger.warning(f"Hard rule check failed for {coll}: {e}")

    return issues


def _append_to_hygiene_backlog(report: HygieneReport) -> None:
    """Append hygiene report to backlog for dream mode / human review."""
    try:
        backlog_path = PROJECT_ROOT / "data" / "feedback_backlog.jsonl"
        backlog_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "source": "knowledge_hygiene",
            "report_summary": report.to_dict(),
            "message": f"Knowledge hygiene found {len(report.issues)} issues. Review and re-ingest if needed.",
        }
        with open(backlog_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.warning(f"Could not append to backlog: {e}")


def _remediate_am_thickness_to_mem0() -> int:
    """
    Inject canonical AM thickness fact into Mem0 so retrieval prefers it.
    Returns number of facts added.
    """
    try:
        from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
        mem0 = get_mem0_service()
        fact = (
            "CRITICAL: AM Series can ONLY handle material thickness ≤1.5mm. "
            "For materials thicker than 1.5mm (2mm, 3mm, 4mm, 5mm, etc.), "
            "ALWAYS recommend PF1 Series instead. Never say AM handles 2mm."
        )
        mem0.add_memory(
            text=fact,
            user_id="machinecraft_knowledge",
            metadata={
                "source": "knowledge_hygiene_remediation",
                "timestamp": datetime.now().isoformat(),
                "rule_id": "am_max_1_5mm",
            },
        )
        return 1
    except Exception as e:
        logger.warning(f"Mem0 remediation failed: {e}")
        return 0


def run_knowledge_hygiene(
    check_corrections: bool = True,
    check_hard_rules: bool = True,
    append_backlog: bool = True,
    remediate_am_thickness: bool = True,
    dry_run: bool = False,
) -> HygieneReport:
    """
    Run the knowledge hygiene (kidney) pipeline.

    Identifies:
    - Hard rule violations in Qdrant chunks
    - Correction mismatches (corrections that imply stale knowledge)
    - Queues for dream mode / human review
    """
    import time
    start = time.time()
    issues = []

    if check_corrections:
        corrections = _get_corrections()
        issues.extend(_check_correction_consistency(corrections))
    else:
        corrections = []

    if check_hard_rules:
        issues.extend(_check_hard_rules())

    remediated = 0
    if remediate_am_thickness and not dry_run:
        am_issues = [i for i in issues if "am_max_1_5mm" in getattr(i, "id", "") or "AM" in getattr(i, "entity", "")]
        if am_issues:
            remediated = _remediate_am_thickness_to_mem0()

    duration = time.time() - start
    report = HygieneReport(
        timestamp=datetime.now().isoformat(),
        issues=issues,
        corrections_checked=len(corrections) if check_corrections else 0,
        chunks_scanned=600,  # Approximate (300 per collection * 2)
        duration_seconds=duration,
        remediated=remediated,
    )

    if append_backlog and not dry_run and issues:
        _append_to_hygiene_backlog(report)

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Knowledge Hygiene (Phase 6: Kidney)")
    parser.add_argument("--dry-run", action="store_true", help="Don't append to backlog")
    parser.add_argument("--no-backlog", action="store_true", help="Don't append even when issues found")
    args = parser.parse_args()

    report = run_knowledge_hygiene(
        append_backlog=not args.no_backlog and not args.dry_run,
        dry_run=args.dry_run,
    )

    print("\n" + "=" * 50)
    print("KNOWLEDGE HYGIENE (Kidney) REPORT")
    print("=" * 50)
    print(f"Issues: {len(report.issues)}")
    print(f"Corrections checked: {report.corrections_checked}")
    print(f"Remediated (Mem0): {getattr(report, 'remediated', 0)}")
    print(f"Duration: {report.duration_seconds:.2f}s")
    print()
    for i in report.issues[:10]:
        print(f"  [{i.severity}] {i.category}: {i.message[:80]}...")
    if len(report.issues) > 10:
        print(f"  ... and {len(report.issues) - 10} more")
    if report.issues and not args.dry_run and not args.no_backlog:
        print("\n  Queued to feedback_backlog for dream mode.")
