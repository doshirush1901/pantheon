#!/usr/bin/env python3
"""
P2: Reconcile pending Qdrant embeds (P1-8 follow-up).

When PostgreSQL write succeeds but Qdrant embed fails, persistent_memory
appends a record to data/brain/pending_qdrant_embeds.jsonl. This script
processes that file: re-embeds each pending memory into Qdrant, then
removes processed lines. Run periodically (e.g. cron or after dream mode).

Usage:
  python scripts/reconcile_pending_qdrant_embeds.py [--dry-run]
"""

import argparse
import json
import sys
from pathlib import Path

# Allow importing from openclaw
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PENDING_PATH = REPO_ROOT / "data" / "brain" / "pending_qdrant_embeds.jsonl"


def main():
    ap = argparse.ArgumentParser(description="Reconcile pending Qdrant embeds from Postgres-only writes")
    ap.add_argument("--dry-run", action="store_true", help="Only print what would be done")
    args = ap.parse_args()

    if not PENDING_PATH.exists():
        print("No pending embeds file found. Nothing to do.")
        return 0

    lines = PENDING_PATH.read_text().strip().splitlines()
    if not lines:
        print("Pending file is empty. Nothing to do.")
        return 0

    try:
        from openclaw.agents.ira.src.memory.persistent_memory import get_persistent_memory
    except ImportError:
        print("ERROR: Could not import persistent_memory. Run from repo root with PYTHONPATH=.", file=sys.stderr)
        return 1

    pm = get_persistent_memory()
    processed = []
    failed = []

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            failed.append((i, line, "Invalid JSON"))
            continue

        kind = rec.get("kind")
        memory_id = rec.get("memory_id")

        if args.dry_run:
            print(f"[dry-run] Would process: kind={kind} memory_id={memory_id}")
            processed.append(i)
            continue

        try:
            if kind == "user":
                identity_id = rec.get("identity_id", "")
                memory_text = rec.get("memory_text", "")
                if memory_id and identity_id and memory_text:
                    pm._embed_memory(int(memory_id), identity_id, memory_text)
                    processed.append(i)
                else:
                    failed.append((i, line, "Missing identity_id or memory_text"))
            elif kind == "entity":
                entity_type = rec.get("entity_type", "")
                normalized_name = rec.get("normalized_name", "")
                memory_text = rec.get("memory_text", "")
                if memory_id and entity_type and normalized_name and memory_text:
                    pm._embed_entity_memory(
                        int(memory_id), entity_type, normalized_name, memory_text
                    )
                    processed.append(i)
                else:
                    failed.append((i, line, "Missing entity fields"))
            else:
                failed.append((i, line, f"Unknown kind: {kind}"))
        except Exception as e:
            failed.append((i, line, str(e)))

    if processed and not args.dry_run:
        # Rewrite file keeping only lines that were not processed (and not failed invalid)
        keep_indices = {i for i in range(len(lines)) if i not in processed}
        new_lines = [lines[i] for i in sorted(keep_indices) if lines[i].strip()]
        PENDING_PATH.write_text("\n".join(new_lines) + ("\n" if new_lines else ""))
        print(f"Processed {len(processed)} pending embeds. {len(new_lines)} remaining.")
    elif processed and args.dry_run:
        print(f"[dry-run] Would process {len(processed)} embeds.")

    if failed:
        print(f"Failed {len(failed)}: ", file=sys.stderr)
        for idx, ln, err in failed[:10]:
            print(f"  Line {idx}: {err}", file=sys.stderr)
        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more", file=sys.stderr)

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
