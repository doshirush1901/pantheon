#!/usr/bin/env python3
"""
HEARTBEAT: Import Watcher — Auto-ingest new files in data/imports/

Watches the data/imports/ directory tree for new or modified files and
automatically ingests them into Ira's knowledge base via KnowledgeIngestor.

Usage:
    # One-shot scan (for cron):
    python scripts/watch_imports.py --once

    # Continuous watch (for daemon):
    python scripts/watch_imports.py --watch --interval 60

    # Dry run (show what would be ingested):
    python scripts/watch_imports.py --once --dry-run
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
AGENT_DIR = PROJECT_ROOT / "openclaw" / "agents" / "ira"
BRAIN_DIR = AGENT_DIR / "src" / "brain"
IMPORTS_DIR = PROJECT_ROOT / "data" / "imports"
STATE_FILE = PROJECT_ROOT / "data" / "brain" / "import_watcher_state.json"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [HEARTBEAT] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SCANNABLE_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".docx", ".doc", ".csv", ".txt",
    ".json", ".md", ".pptx", ".ppt", ".html", ".htm",
}


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {"ingested_files": {}, "last_scan": None}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def find_new_files(state: dict) -> list:
    """Find files in data/imports/ that haven't been ingested or have changed."""
    ingested = state.get("ingested_files", {})
    new_files = []

    for fp in IMPORTS_DIR.rglob("*"):
        if not fp.is_file() or fp.name.startswith("."):
            continue
        if fp.suffix.lower() not in SCANNABLE_EXTENSIONS:
            continue

        key = str(fp.relative_to(PROJECT_ROOT))
        stat = fp.stat()
        file_sig = f"{stat.st_size}:{stat.st_mtime:.0f}"

        if key not in ingested or ingested[key].get("sig") != file_sig:
            new_files.append(fp)

    return sorted(new_files, key=lambda f: f.stat().st_mtime)


def ingest_file(fp: Path, dry_run: bool = False) -> dict:
    """Ingest a single file into Ira's knowledge base."""
    rel = fp.relative_to(PROJECT_ROOT)
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Ingesting: {rel}")

    if dry_run:
        return {"file": str(rel), "status": "dry_run", "items": 0}

    try:
        from document_extractor import DocumentExtractor
        from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

        extractor = DocumentExtractor()
        extraction = extractor.extract(str(fp))

        if not extraction.success:
            logger.warning(f"  Extraction failed: {extraction.error}")
            return {"file": str(rel), "status": "extraction_failed", "error": extraction.error}

        knowledge_type = "general"
        name_lower = fp.stem.lower()
        if any(w in name_lower for w in ("quote", "price", "offer", "cost")):
            knowledge_type = "pricing"
        elif any(w in name_lower for w in ("customer", "order", "client")):
            knowledge_type = "customer"
        elif any(w in name_lower for w in ("spec", "technical", "datasheet")):
            knowledge_type = "machine_spec"

        item = KnowledgeItem(
            text=extraction.text,
            knowledge_type=knowledge_type,
            source_file=fp.name,
            summary=f"Auto-ingested: {fp.name}",
            metadata={
                "source": "heartbeat_watcher",
                "path": str(rel),
                "pages": extraction.page_count,
                "extractor": extraction.extractor_used,
            },
        )

        ingestor = KnowledgeIngestor()
        result = ingestor.ingest_batch([item])

        logger.info(
            f"  → {result.items_ingested} ingested, "
            f"{result.items_skipped} skipped, "
            f"{result.items_excreted} excreted"
        )
        return {
            "file": str(rel),
            "status": "success" if result.success else "partial",
            "items": result.items_ingested,
            "skipped": result.items_skipped,
            "excreted": result.items_excreted,
        }

    except Exception as e:
        logger.error(f"  Error: {e}")
        return {"file": str(rel), "status": "error", "error": str(e)}


def scan_once(dry_run: bool = False):
    """One-shot scan: find new files and ingest them."""
    state = load_state()
    new_files = find_new_files(state)

    if not new_files:
        logger.info("No new files to ingest.")
        state["last_scan"] = datetime.now().isoformat()
        save_state(state)
        return

    logger.info(f"Found {len(new_files)} new/modified files")

    for fp in new_files:
        result = ingest_file(fp, dry_run=dry_run)
        if not dry_run and result.get("status") in ("success", "partial"):
            key = str(fp.relative_to(PROJECT_ROOT))
            stat = fp.stat()
            state["ingested_files"][key] = {
                "sig": f"{stat.st_size}:{stat.st_mtime:.0f}",
                "ingested_at": datetime.now().isoformat(),
                "items": result.get("items", 0),
            }

    state["last_scan"] = datetime.now().isoformat()
    if not dry_run:
        save_state(state)

    logger.info("Scan complete.")


def watch_loop(interval: int = 60, dry_run: bool = False):
    """Continuous watch: scan at regular intervals."""
    logger.info(f"Watching {IMPORTS_DIR} every {interval}s (Ctrl+C to stop)")
    while True:
        try:
            scan_once(dry_run=dry_run)
        except Exception as e:
            logger.error(f"Scan error: {e}")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Heartbeat: Auto-ingest new files")
    parser.add_argument("--once", action="store_true", help="One-shot scan")
    parser.add_argument("--watch", action="store_true", help="Continuous watch")
    parser.add_argument("--interval", type=int, default=60, help="Watch interval (seconds)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be ingested")
    args = parser.parse_args()

    if args.watch:
        watch_loop(interval=args.interval, dry_run=args.dry_run)
    else:
        scan_once(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
