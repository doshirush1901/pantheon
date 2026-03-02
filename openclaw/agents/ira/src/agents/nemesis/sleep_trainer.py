"""
Nemesis Sleep Trainer — Rewire Ira's Brain During Sleep
========================================================

Runs during nap.py to systematically apply accumulated corrections to
every layer of Ira's knowledge:

1. **Truth Hints** — Generate new TruthHint entries for repeated corrections
   and append to learned_truth_hints.py (loaded at startup)
2. **Qdrant** — Index correction facts into the discovered_knowledge collection
   so semantic search finds them
3. **Mem0** — Reinforce corrections with higher-priority metadata
4. **Training Guidance** — Generate a training_guidance.json that gets injected
   into the system prompt, listing recent corrections as "watch out for" rules
5. **Learned Corrections JSON** — Update the brain's learned_corrections.json

Returns a summary dict suitable for the NapJournal.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.nemesis.trainer")

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent.parent

TRAINING_GUIDANCE_FILE = PROJECT_ROOT / "data" / "nemesis" / "training_guidance.json"
LEARNED_CORRECTIONS_FILE = (
    PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "brain" / "learned_corrections.json"
)
LEARNED_TRUTH_HINTS_FILE = (
    PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "brain" / "learned_truth_hints.json"
)

try:
    from openclaw.agents.ira.config import FAST_LLM_MODEL, get_openai_client
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    FAST_LLM_MODEL = "gpt-4o-mini"


def _get_client():
    if CONFIG_AVAILABLE:
        return get_openai_client()
    try:
        from openai import OpenAI
        return OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    except Exception:
        return None


def _atomic_json_write(path: Path, data: Any):
    """Atomically write JSON to avoid partial reads during concurrent access."""
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def run_sleep_training(dry_run: bool = False) -> Dict[str, Any]:
    """Main entry point — called from nap.py.
    
    Processes all unapplied corrections and applies them across
    Ira's knowledge layers.
    """
    from . import correction_store as store

    start = time.time()
    results = {
        "corrections_processed": 0,
        "truth_hints_added": 0,
        "qdrant_indexed": 0,
        "mem0_reinforced": 0,
        "guidance_rules": 0,
        "learned_corrections_updated": 0,
    }

    corrections = store.get_unapplied_corrections(limit=100)
    if not corrections:
        logger.info("[NEMESIS TRAINER] No unapplied corrections — nothing to train on")
        return results

    logger.info(f"[NEMESIS TRAINER] Processing {len(corrections)} unapplied corrections")

    # Phase 1: Generate truth hints from repeated/critical corrections
    hints_added = _generate_truth_hints(corrections, dry_run)
    results["truth_hints_added"] = hints_added

    # Phase 2: Index into Qdrant
    qdrant_count = _index_to_qdrant(corrections, dry_run)
    results["qdrant_indexed"] = qdrant_count

    # Phase 3: Reinforce in Mem0 with high priority
    mem0_count = _reinforce_mem0(corrections, dry_run)
    results["mem0_reinforced"] = mem0_count

    # Phase 4: Generate training guidance for system prompt
    guidance_count = _generate_training_guidance(corrections, dry_run)
    results["guidance_rules"] = guidance_count

    # Phase 5: Update learned_corrections.json
    lc_count = _update_learned_corrections(corrections, dry_run)
    results["learned_corrections_updated"] = lc_count

    # Mark all as applied
    if not dry_run:
        applied_to_parts = []
        if hints_added:
            applied_to_parts.append("truth_hints")
        if qdrant_count:
            applied_to_parts.append("qdrant")
        if mem0_count:
            applied_to_parts.append("mem0")
        if guidance_count:
            applied_to_parts.append("training_guidance")
        if lc_count:
            applied_to_parts.append("learned_corrections")
        applied_to = ",".join(applied_to_parts) or "none"

        for c in corrections:
            store.mark_correction_applied(c["id"], applied_to)

        store.record_training_run(
            phase="sleep_train",
            corrections_applied=len(corrections),
            truth_hints_added=hints_added,
            qdrant_indexed=qdrant_count,
            mem0_stored=mem0_count,
            prompt_rules_added=guidance_count,
            duration_seconds=time.time() - start,
            summary=f"Processed {len(corrections)} corrections across {applied_to}",
        )

    results["corrections_processed"] = len(corrections)
    elapsed = time.time() - start
    logger.info(
        f"[NEMESIS TRAINER] Done in {elapsed:.1f}s: "
        f"{results['corrections_processed']} corrections → "
        f"{hints_added} hints, {qdrant_count} qdrant, "
        f"{mem0_count} mem0, {guidance_count} guidance rules"
    )
    return results


# =====================================================================
# Phase 1: Truth Hints
# =====================================================================

def _generate_truth_hints(corrections: List[Dict], dry_run: bool) -> int:
    """Generate truth hints from corrections that are repeated or critical.
    
    Only creates hints for corrections that are:
    - Seen 2+ times (repeated mistake), OR
    - Severity = critical
    """
    candidates = [
        c for c in corrections
        if c.get("occurrences", 1) >= 2 or c.get("severity") == "critical"
    ]
    if not candidates:
        return 0

    client = _get_client()
    if not client:
        return _generate_truth_hints_simple(candidates, dry_run)

    try:
        corrections_text = "\n".join(
            f"- Entity: {c.get('entity', 'general')} | "
            f"Category: {c.get('category', '?')} | "
            f"Wrong: {c['wrong_info'][:100]} | "
            f"Correct: {c['correct_info'][:100]} | "
            f"Seen {c.get('occurrences', 1)}x"
            for c in candidates[:20]
        )

        resp = client.chat.completions.create(
            model=FAST_LLM_MODEL,
            messages=[
                {"role": "system", "content": (
                    "Generate truth hints from these corrections. Each hint is a pre-cached "
                    "correct answer that Ira can use to avoid repeating mistakes.\n\n"
                    "Return a JSON array of hints:\n"
                    "[\n"
                    "  {\n"
                    '    "id": "correction_<entity>_<topic>",\n'
                    '    "question_patterns": ["regex pattern 1", "regex pattern 2"],\n'
                    '    "answer": "The correct, authoritative answer",\n'
                    '    "category": "machine_spec|pricing|customer|process",\n'
                    '    "keywords": ["keyword1", "keyword2"]\n'
                    "  }\n"
                    "]\n\n"
                    "Rules:\n"
                    "- Use \\b word boundaries in regex patterns\n"
                    "- Answer should be definitive and include the correction\n"
                    "- Keywords should be lowercase words that must appear in the query\n"
                    "- Only generate hints where a clear, cacheable answer exists\n"
                    "- Skip tone/style corrections (not suitable for truth hints)"
                )},
                {"role": "user", "content": corrections_text},
            ],
            max_tokens=1500,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        raw = json.loads(resp.choices[0].message.content)
        hints = raw if isinstance(raw, list) else raw.get("hints", raw.get("truth_hints", []))

        if not hints:
            return 0

        if not dry_run:
            _save_learned_hints(hints)

        logger.info(f"[NEMESIS TRAINER] Generated {len(hints)} truth hints")
        return len(hints)

    except Exception as e:
        logger.warning(f"[NEMESIS TRAINER] Truth hint generation failed: {e}")
        return _generate_truth_hints_simple(candidates, dry_run)


def _generate_truth_hints_simple(candidates: List[Dict], dry_run: bool) -> int:
    """Fallback: generate simple truth hints without LLM."""
    hints = []
    for c in candidates:
        entity = c.get("entity")
        if not entity:
            continue
        entity_lower = entity.lower().replace("-", "[-\\s]?")
        hints.append({
            "id": f"nemesis_{c['id']}",
            "question_patterns": [f"\\b{entity_lower}\\b"],
            "answer": c["correct_info"],
            "category": c.get("category", "general"),
            "keywords": [w.lower() for w in entity.split() if len(w) > 2][:3],
            "source": "nemesis_sleep_train",
        })

    if hints and not dry_run:
        _save_learned_hints(hints)
    return len(hints)


def _save_learned_hints(new_hints: List[Dict]) -> None:
    """Append new hints to the learned truth hints file."""
    existing = []
    if LEARNED_TRUTH_HINTS_FILE.exists():
        try:
            existing = json.loads(LEARNED_TRUTH_HINTS_FILE.read_text())
        except Exception:
            existing = []

    existing_ids = {h.get("id") for h in existing}
    for hint in new_hints:
        if hint.get("id") not in existing_ids:
            hint["added_at"] = datetime.now().isoformat()
            hint["source"] = "nemesis_sleep_train"
            existing.append(hint)

    _atomic_json_write(LEARNED_TRUTH_HINTS_FILE, existing)
    logger.info(f"[NEMESIS TRAINER] Saved {len(existing)} total learned truth hints")


# =====================================================================
# Phase 2: Qdrant Indexing
# =====================================================================

def _index_to_qdrant(corrections: List[Dict], dry_run: bool) -> int:
    """Index correction facts into Qdrant for semantic retrieval."""
    if dry_run:
        return len(corrections)

    try:
        from openclaw.agents.ira.src.brain.knowledge_ingestor import KnowledgeIngestor
        ingestor = KnowledgeIngestor()
    except ImportError:
        logger.warning("[NEMESIS TRAINER] KnowledgeIngestor not available, skipping Qdrant")
        return 0

    indexed = 0
    for c in corrections:
        text = (
            f"CORRECTION: {c['correct_info']}\n"
            f"Previously wrong: {c['wrong_info']}\n"
            f"Entity: {c.get('entity', 'general')}\n"
            f"Category: {c.get('category', 'general')}"
        )
        try:
            knowledge_type_map = {
                "spec": "machine_spec",
                "price": "pricing",
                "customer": "customer",
                "process": "process",
            }
            ktype = knowledge_type_map.get(c.get("category", ""), "general")

            ingestor.ingest_batch([{
                "text": text,
                "entity": c.get("entity", "correction"),
                "knowledge_type": ktype,
                "metadata": {
                    "source": "nemesis_sleep_train",
                    "correction_id": c["id"],
                    "severity": c.get("severity", "important"),
                },
            }])
            indexed += 1
        except Exception as e:
            logger.warning(f"[NEMESIS TRAINER] Qdrant indexing failed for {c['id']}: {e}")

    return indexed


# =====================================================================
# Phase 3: Mem0 Reinforcement
# =====================================================================

def _reinforce_mem0(corrections: List[Dict], dry_run: bool) -> int:
    """Reinforce corrections in Mem0 with high-priority metadata.
    
    During real-time ingestion, corrections are stored with normal priority.
    During sleep, we reinforce critical/repeated ones with elevated priority.
    """
    if dry_run:
        return len([c for c in corrections if c.get("severity") in ("critical", "important")])

    try:
        from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
        mem0 = get_mem0_service()
    except ImportError:
        logger.warning("[NEMESIS TRAINER] Mem0 not available, skipping reinforcement")
        return 0

    reinforced = 0
    for c in corrections:
        if c.get("severity") not in ("critical", "important"):
            continue

        user_id_map = {
            "spec": "machinecraft_knowledge",
            "price": "machinecraft_pricing",
            "customer": "machinecraft_customers",
            "process": "machinecraft_processes",
        }
        user_id = user_id_map.get(c.get("category", ""), "machinecraft_general")

        try:
            mem0.add_memory(
                text=f"VERIFIED CORRECTION (sleep-reinforced): {c['correct_info']}",
                user_id=user_id,
                metadata={
                    "source": "nemesis_sleep_reinforcement",
                    "priority": "highest",
                    "entity": c.get("entity"),
                    "severity": c.get("severity"),
                    "occurrences": c.get("occurrences", 1),
                    "timestamp": datetime.now().isoformat(),
                },
            )
            reinforced += 1
        except Exception as e:
            logger.warning(f"[NEMESIS TRAINER] Mem0 reinforcement failed for {c['id']}: {e}")

    return reinforced


# =====================================================================
# Phase 4: Training Guidance (injected into system prompt)
# =====================================================================

def _generate_training_guidance(corrections: List[Dict], dry_run: bool) -> int:
    """Generate training guidance rules that get injected into the system prompt.
    
    The tool_orchestrator reads training_guidance.json at startup and appends
    these rules to the system prompt as "LEARNED CORRECTIONS" section.
    """
    rules = []
    for c in corrections:
        if c.get("severity") in ("critical", "important"):
            entity = c.get("entity", "")
            prefix = f"[{entity}] " if entity else ""
            rules.append({
                "rule": f"{prefix}{c['correct_info']}",
                "severity": c.get("severity", "important"),
                "category": c.get("category", "general"),
                "source": c.get("source", "unknown"),
                "occurrences": c.get("occurrences", 1),
            })

    if not rules:
        return 0

    if not dry_run:
        TRAINING_GUIDANCE_FILE.parent.mkdir(parents=True, exist_ok=True)

        existing = []
        if TRAINING_GUIDANCE_FILE.exists():
            try:
                existing = json.loads(TRAINING_GUIDANCE_FILE.read_text())
            except Exception:
                existing = []

        existing_rules = {r.get("rule") for r in existing}
        for rule in rules:
            if rule["rule"] not in existing_rules:
                rule["added_at"] = datetime.now().isoformat()
                existing.append(rule)

        # Keep only the most recent 50 rules
        existing = sorted(
            existing,
            key=lambda r: (
                0 if r.get("severity") == "critical" else 1,
                -r.get("occurrences", 1),
            ),
        )[:50]

        _atomic_json_write(TRAINING_GUIDANCE_FILE, existing)
        logger.info(f"[NEMESIS TRAINER] Saved {len(existing)} training guidance rules")

    return len(rules)


def get_training_guidance_for_prompt() -> str:
    """Read training guidance and format it for injection into the system prompt.
    
    Called by tool_orchestrator.py at prompt-build time.
    """
    if not TRAINING_GUIDANCE_FILE.exists():
        return ""

    try:
        rules = json.loads(TRAINING_GUIDANCE_FILE.read_text())
        if not rules:
            return ""

        lines = ["\n\n## LEARNED CORRECTIONS (from Nemesis — do NOT repeat these mistakes)\n"]
        for r in rules[:30]:
            severity_icon = "🚨" if r.get("severity") == "critical" else "⚠️"
            lines.append(f"{severity_icon} {r['rule']}")

        return "\n".join(lines)
    except Exception:
        return ""


# =====================================================================
# Phase 5: Learned Corrections JSON
# =====================================================================

def _update_learned_corrections(corrections: List[Dict], dry_run: bool) -> int:
    """Update the brain's learned_corrections.json with new corrections."""
    if dry_run:
        return len(corrections)

    existing = {"corrections": [], "competitors": [], "existing_customers": []}
    if LEARNED_CORRECTIONS_FILE.exists():
        try:
            existing = json.loads(LEARNED_CORRECTIONS_FILE.read_text())
        except Exception:
            pass

    existing_ids = {c.get("id") for c in existing.get("corrections", [])}
    added = 0

    for c in corrections:
        if c["id"] in existing_ids:
            continue
        existing["corrections"].append({
            "id": c["id"],
            "correction_type": c.get("category", "fact"),
            "original": c["wrong_info"][:200],
            "corrected": c["correct_info"][:200],
            "entity": c.get("entity", ""),
            "context": c.get("coach_note", ""),
            "timestamp": c.get("timestamp", datetime.now().isoformat()),
            "confidence": 1.0,
        })
        added += 1

    if added:
        existing["last_updated"] = datetime.now().isoformat()
        _atomic_json_write(LEARNED_CORRECTIONS_FILE, existing)
        logger.info(f"[NEMESIS TRAINER] Added {added} to learned_corrections.json")

    return added
