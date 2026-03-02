#!/usr/bin/env python3
"""
HEARTBEAT: Proactive Ingestion from data/imports/
==================================================

The "EAT" step in Ira's metabolic cycle. Watches data/imports/ for new or modified
files and proactively ingests them into the knowledge base. Designed to run
periodically via cron (e.g. every 5 min).

Biological analogy: The heartbeat that keeps nutrients flowing — continuously
checking for new "food" (documents) and digesting them.

Usage:
    python -m openclaw.agents.ira.src.brain.heartbeat_ingest
    python -m openclaw.agents.ira.src.brain.heartbeat_ingest --limit 5
    python -m openclaw.agents.ira.src.brain.heartbeat_ingest --dry-run

Cron example:
    */5 * * * * cd /path/to/Ira && python -m openclaw.agents.ira.src.brain.heartbeat_ingest >> logs/heartbeat.log 2>&1
"""

import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BRAIN_DIR = Path(__file__).parent
AGENT_DIR = BRAIN_DIR.parent.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))

# Load .env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

IMPORTS_DIR = PROJECT_ROOT / "data" / "imports"
HEARTBEAT_STATE = PROJECT_ROOT / "data" / "brain" / "heartbeat_state.json"

SUPPORTED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".docx", ".doc", ".pptx", ".csv", ".txt", ".md", ".json"}
SKIP_PATTERNS = (".extracted.txt", ".gitkeep")


def _load_state() -> Dict:
    if HEARTBEAT_STATE.exists():
        try:
            return json.loads(HEARTBEAT_STATE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {"processed": {}, "last_run": None}


def _save_state(state: Dict) -> None:
    HEARTBEAT_STATE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now().isoformat()
    HEARTBEAT_STATE.write_text(json.dumps(state, indent=2))


def _detect_knowledge_type(filename: str) -> str:
    """Infer knowledge_type from filename."""
    text = filename.lower()
    if any(w in text for w in ("quote", "quotation", "pricing", "offer", "cost", "eur", "usd", "inr")):
        return "pricing"
    if any(w in text for w in ("customer", "client", "order", "contract")):
        return "customer"
    if any(w in text for w in ("spec", "technical", "datasheet", "manual", "catalogue")):
        return "machine_spec"
    if any(w in text for w in ("process", "forming", "thermoform")):
        return "process"
    if any(w in text for w in ("application", "automotive", "packaging", "aerospace")):
        return "application"
    return "general"


def _extract_entities_from_filename(filename: str) -> List[str]:
    """Extract machine models and key entities from filename."""
    models = re.findall(
        r"(PF[12][-\s]?[A-Z]?[-\s]?\d[\d\-]*|AM[-\s]?\d[\w\-]*|IMG[-\s]?\d[\w\-]*|FCS[-\s]?\w+|ATF[-\s]?\w+)",
        filename,
        re.IGNORECASE,
    )
    return [m.upper().replace(" ", "-") for m in models]


def _collect_pending_files(limit: int = 10) -> List[Tuple[Path, str]]:
    """Scan imports dirs and return (path, rel_key) for new/modified files."""
    state = _load_state()
    processed = state.get("processed", {})
    pending = []

    if not IMPORTS_DIR.exists():
        return []
    for fp in IMPORTS_DIR.rglob("*"):
            if not fp.is_file():
                continue
            if fp.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            if any(skip in fp.name for skip in SKIP_PATTERNS):
                continue

            try:
                stat = fp.stat()
                key = f"{fp.relative_to(IMPORTS_DIR)}"
                file_key = f"{key}|{stat.st_mtime}|{stat.st_size}"
                if file_key != processed.get(key):
                    pending.append((fp, key))
                    if len(pending) >= limit:
                        return pending
            except (ValueError, OSError):
                continue
    return pending


def _ingest_file(file_path: Path) -> Tuple[bool, str]:
    """Extract and ingest a single file. Returns (success, message)."""
    try:
        from document_extractor import DocumentExtractor
        from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem
    except ImportError as e:
        return False, f"Import error: {e}"

    extractor = DocumentExtractor()
    extraction = extractor.extract(str(file_path))
    if not extraction.success:
        return False, extraction.error or "Extraction failed"

    text = extraction.text.strip()
    if len(text) < 30:
        return False, "Content too short after extraction"

    knowledge_type = _detect_knowledge_type(file_path.name)
    entities = _extract_entities_from_filename(file_path.name)
    primary_entity = entities[0] if entities else ""

    item = KnowledgeItem(
        text=text,
        knowledge_type=knowledge_type,
        source_file=file_path.name,
        summary=f"Heartbeat ingest: {file_path.name}",
        entity=primary_entity,
        metadata={
            "source": "heartbeat_ingest",
            "file_path": str(file_path),
            "pages": extraction.page_count,
        },
    )

    ingestor = KnowledgeIngestor()
    result = ingestor.ingest_batch([item])

    if result.success:
        return True, f"Ingested {result.items_ingested} items → {knowledge_type}"
    return False, "; ".join(result.errors[:2]) or "Ingestion failed"


def run_heartbeat(limit: int = 5, dry_run: bool = False) -> Dict:
    """Run one heartbeat cycle. Returns summary dict."""
    summary = {
        "scanned": 0,
        "pending": 0,
        "ingested": 0,
        "failed": 0,
        "messages": [],
    }

    pending = _collect_pending_files(limit=limit)
    summary["pending"] = len(pending)

    if not pending:
        logger.info("[HEARTBEAT] No new or modified files")
        return summary

    logger.info(f"[HEARTBEAT] Found {len(pending)} file(s) to process")

    state = _load_state()
    processed = state.get("processed", {})

    for fp, key in pending:
        summary["scanned"] += 1
        if dry_run:
            summary["messages"].append(f"Would ingest: {fp.name}")
            continue

        success, msg = _ingest_file(fp)
        if success:
            summary["ingested"] += 1
            stat = fp.stat()
            processed[key] = f"{key}|{stat.st_mtime}|{stat.st_size}"
            summary["messages"].append(f"✓ {fp.name}: {msg}")
        else:
            summary["failed"] += 1
            summary["messages"].append(f"✗ {fp.name}: {msg}")

    state["processed"] = processed
    if not dry_run:
        _save_state(state)

    return summary


def send_heartbeat_notification(summary: Dict) -> bool:
    """Send a Telegram notification summarizing the heartbeat run.

    Only sends if there was actual work (ingested > 0 or failed > 0).
    """
    if not summary.get("ingested") and not summary.get("failed"):
        return False

    try:
        from config import TELEGRAM_BOT_TOKEN, EXPECTED_CHAT_ID
    except ImportError:
        TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        EXPECTED_CHAT_ID = os.environ.get("EXPECTED_CHAT_ID", "")

    if not TELEGRAM_BOT_TOKEN or not EXPECTED_CHAT_ID:
        logger.debug("[HEARTBEAT] Telegram not configured; skipping notification")
        return False

    lines = ["💓 *Heartbeat Ingest*\n"]
    if summary["ingested"]:
        lines.append(f"✅ Ingested: {summary['ingested']} files")
    if summary["failed"]:
        lines.append(f"❌ Failed: {summary['failed']} files")
    if summary.get("pending"):
        lines.append(f"📂 Pending: {summary['pending']} detected")
    for msg in summary.get("messages", [])[:10]:
        lines.append(f"  {msg}")

    text = "\n".join(lines)

    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": EXPECTED_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
        }, timeout=10)
        return resp.json().get("ok", False)
    except Exception as e:
        logger.warning(f"[HEARTBEAT] Telegram notification failed: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="HEARTBEAT: Proactive ingestion from data/imports/")
    parser.add_argument("--limit", type=int, default=5, help="Max files to process per run")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not ingest")
    parser.add_argument("--notify", action="store_true", help="Send Telegram notification after run")
    args = parser.parse_args()

    summary = run_heartbeat(limit=args.limit, dry_run=args.dry_run)
    for m in summary["messages"]:
        print(m)
    if summary["ingested"] or summary["failed"]:
        print(f"Heartbeat: {summary['ingested']} ingested, {summary['failed']} failed")

    if args.notify and not args.dry_run:
        send_heartbeat_notification(summary)


if __name__ == "__main__":
    main()
