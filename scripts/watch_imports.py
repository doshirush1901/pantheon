#!/usr/bin/env python3
"""
HEARTBEAT: Auto-Ingest File Watcher
====================================

Watches data/imports/ for new files and automatically ingests them
into Ira's knowledge base. Designed to run as a cron job or daemon.

Usage:
    # One-shot: process any new files since last run
    python scripts/watch_imports.py

    # Continuous watch mode (checks every 60s)
    python scripts/watch_imports.py --watch

    # Cron (every 15 minutes):
    */15 * * * * cd /path/to/Ira && python scripts/watch_imports.py

The watcher tracks which files have been processed in
data/brain/heartbeat_state.json to avoid re-processing.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
BRAIN_DIR = PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "brain"
IMPORTS_DIR = PROJECT_ROOT / "data" / "imports"
STATE_FILE = PROJECT_ROOT / "data" / "brain" / "heartbeat_state.json"

SCANNABLE_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".docx", ".doc", ".csv", ".txt",
    ".pptx", ".ppt", ".json", ".md",
}

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BRAIN_DIR))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [HEARTBEAT] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PROJECT_ROOT / "logs" / "heartbeat.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {"processed_files": {}, "last_run": None, "total_ingested": 0}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def find_new_files(state: dict) -> list:
    """Find files in data/imports/ that haven't been processed yet."""
    processed = state.get("processed_files", {})
    new_files = []

    for fp in IMPORTS_DIR.rglob("*"):
        if not fp.is_file():
            continue
        if fp.suffix.lower() not in SCANNABLE_EXTENSIONS:
            continue
        if fp.name.startswith("."):
            continue

        rel_path = str(fp.relative_to(IMPORTS_DIR))
        mtime = fp.stat().st_mtime
        prev = processed.get(rel_path)

        if prev is None or prev.get("mtime", 0) < mtime:
            new_files.append(fp)

    new_files.sort(key=lambda f: f.stat().st_mtime)
    return new_files


def ingest_file(filepath: Path) -> dict:
    """Ingest a single file into Ira's knowledge base."""
    try:
        from document_extractor import DocumentExtractor
        from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem

        extractor = DocumentExtractor()
        extraction = extractor.extract(str(filepath))

        if not extraction.success:
            return {"success": False, "error": extraction.error or "extraction failed"}

        ingestor = KnowledgeIngestor()
        item = KnowledgeItem(
            text=extraction.text,
            knowledge_type="general",
            source_file=filepath.name,
            summary=f"Auto-ingested: {filepath.name}",
            metadata={
                "source": "heartbeat_auto_ingest",
                "pages": extraction.page_count,
                "extractor": extraction.extractor_used,
            },
        )
        result = ingestor.ingest_batch([item])

        return {
            "success": result.success,
            "items": result.items_ingested,
            "rejected": result.items_rejected,
            "skipped": result.items_skipped,
        }
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


def run_once():
    """Process any new files since last run."""
    state = load_state()
    new_files = find_new_files(state)

    if not new_files:
        logger.info("No new files to process.")
        state["last_run"] = datetime.now().isoformat()
        save_state(state)
        return 0

    logger.info(f"Found {len(new_files)} new/modified files to process.")
    ingested = 0

    for fp in new_files:
        rel_path = str(fp.relative_to(IMPORTS_DIR))
        logger.info(f"  Processing: {rel_path}")

        result = ingest_file(fp)

        state["processed_files"][rel_path] = {
            "mtime": fp.stat().st_mtime,
            "processed_at": datetime.now().isoformat(),
            "result": result,
        }

        if result.get("success"):
            ingested += 1
            logger.info(f"    ✓ Ingested ({result.get('items', 0)} items)")
        else:
            logger.warning(f"    ✗ Failed: {result.get('error', 'unknown')}")

    state["last_run"] = datetime.now().isoformat()
    state["total_ingested"] = state.get("total_ingested", 0) + ingested
    save_state(state)

    logger.info(f"Done. Ingested {ingested}/{len(new_files)} files. Total lifetime: {state['total_ingested']}")
    return ingested


def watch_loop(interval: int = 60):
    """Continuously watch for new files."""
    logger.info(f"Starting watch mode (interval: {interval}s). Press Ctrl+C to stop.")
    while True:
        try:
            run_once()
        except Exception as e:
            logger.error(f"Watch cycle error: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Heartbeat: auto-ingest new files")
    parser.add_argument("--watch", action="store_true", help="Continuous watch mode")
    parser.add_argument("--interval", type=int, default=60, help="Watch interval in seconds")
    args = parser.parse_args()

    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)

    if args.watch:
        watch_loop(args.interval)
    else:
        run_once()
