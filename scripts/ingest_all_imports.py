#!/usr/bin/env python3
"""
BULK IMPORTS INGESTION
======================

Ingests all un-ingested files from data/imports/ into Ira's central knowledge base.

Reads the metadata index (data/brain/imports_metadata.json) to know what files exist
and their doc_type/machines/topics, then cross-references the audit log and ingested
hashes to skip already-ingested files. For each remaining file, extracts full text,
uses GPT to produce structured knowledge items, and feeds them through KnowledgeIngestor
to all 4 destinations (Qdrant main, Qdrant discovered, Mem0, JSON backup).

Usage:
    python scripts/ingest_all_imports.py                        # Full run
    python scripts/ingest_all_imports.py --dry-run              # Preview only
    python scripts/ingest_all_imports.py --dry-run --limit 10   # Preview 10 files
    python scripts/ingest_all_imports.py --doc-type quote       # Only quotes
    python scripts/ingest_all_imports.py --report               # Generate audit report
    python scripts/ingest_all_imports.py --resume               # Resume from last progress
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
AGENT_DIR = PROJECT_ROOT / "openclaw" / "agents" / "ira"
BRAIN_DIR = AGENT_DIR / "src" / "brain"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

IMPORTS_DIR = PROJECT_ROOT / "data" / "imports"
INDEX_PATH = PROJECT_ROOT / "data" / "brain" / "imports_metadata.json"
AUDIT_LOG = PROJECT_ROOT / "data" / "knowledge" / "audit.jsonl"
HASHES_FILE = PROJECT_ROOT / "data" / "knowledge" / "ingested_hashes.json"
PROGRESS_FILE = PROJECT_ROOT / "data" / "brain" / "bulk_ingest_progress.json"
REPORT_FILE = PROJECT_ROOT / "data" / "brain" / "ingestion_audit_report.json"

DOC_TYPE_TO_KNOWLEDGE_TYPE = {
    "catalogue": "machine_spec",
    "technical_spec": "machine_spec",
    "manual": "machine_spec",
    "quote": "pricing",
    "order": "customer",
    "contract": "customer",
    "presentation": "general",
    "spreadsheet": "market_intelligence",
    "lead_list": "market_intelligence",
    "email": "customer",
    "report": "general",
    "brochure": "machine_spec",
    "invoice": "customer",
    "customer_data": "customer",
    "other": "general",
}

PRIORITY_ORDER = [
    "catalogue",
    "technical_spec",
    "manual",
    "brochure",
    "presentation",
    "report",
    "spreadsheet",
    "lead_list",
    "email",
    "contract",
    "order",
    "quote",
    "other",
    "invoice",
    "customer_data",
]

MACHINE_PATTERNS = [
    r'PF1-[A-Z]?-?\d{4}',
    r'PF1\s+\d{4}',
    r'PF2-\d+[xX]\d+',
    r'AM-?[A-Z]?-?\d{4}',
    r'AMP-?\d{4}',
    r'AMC-?\d{4}',
    r'IMG[SL]?-?\d{4}',
    r'FCS-?\d{4}',
    r'ATF-?\d{4}',
    r'RT-?\d[A-Z]-?\d{4}',
    r'EFX-?\d{4}',
    r'AO-?\d{4}',
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_metadata_index() -> Dict:
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text())
    return {"files": {}}


def load_audit_sources() -> set:
    """Return lowercased source filenames from the audit log."""
    sources: set = set()
    if not AUDIT_LOG.exists():
        return sources
    for line in AUDIT_LOG.read_text().splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            for src in entry.get("source_files", []):
                sources.add(src.lower().strip())
        except json.JSONDecodeError:
            continue
    return sources


def file_was_ingested(filename: str, audit_sources: set) -> bool:
    fl = filename.lower().strip()
    for src in audit_sources:
        if fl in src or src in fl:
            return True
    return False


def load_progress() -> Dict:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {"completed_files": [], "last_updated": None}


def save_progress(completed: List[str]):
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps({
        "completed_files": completed,
        "last_updated": datetime.now().isoformat(),
        "count": len(completed),
    }, indent=2))


def extract_machines_from_text(text: str) -> List[str]:
    machines = set()
    for pattern in MACHINE_PATTERNS:
        for m in re.findall(pattern, text, re.IGNORECASE):
            machines.add(m.upper().replace(' ', '-'))
    return list(machines)


def priority_key(doc_type: str) -> int:
    try:
        return PRIORITY_ORDER.index(doc_type)
    except ValueError:
        return len(PRIORITY_ORDER)


def check_qdrant_health() -> bool:
    """Return True if Qdrant is reachable."""
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:6333/collections", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def wait_for_qdrant(max_wait: int = 120) -> bool:
    """Block until Qdrant is reachable, return False if timeout."""
    import subprocess
    if check_qdrant_health():
        return True
    logger.warning("Qdrant not reachable. Attempting to start Docker + Qdrant...")
    try:
        subprocess.run(["open", "-a", "Docker"], check=False, timeout=5)
    except Exception:
        pass
    waited = 0
    while waited < max_wait:
        time.sleep(5)
        waited += 5
        # Try starting the container each iteration
        try:
            subprocess.run(["docker", "start", "ira-qdrant"],
                           check=False, timeout=10, capture_output=True)
        except Exception:
            pass
        if check_qdrant_health():
            logger.info("Qdrant is up after %ds", waited)
            return True
        if waited % 15 == 0:
            logger.info("  Waiting for Qdrant... (%ds)", waited)
    logger.error("Qdrant did not come up within %ds", max_wait)
    return False


# ---------------------------------------------------------------------------
# Audit report
# ---------------------------------------------------------------------------

def generate_audit_report() -> Dict:
    """Produce a full audit of ingested vs un-ingested files."""
    index = load_metadata_index()
    audit_sources = load_audit_sources()

    ingested = []
    not_ingested = []

    for rel_path, meta in index.get("files", {}).items():
        fname = meta.get("name", "")
        entry = {
            "rel_path": rel_path,
            "name": fname,
            "doc_type": meta.get("doc_type", "other"),
            "size_kb": meta.get("size_kb", 0),
            "machines": meta.get("machines", []),
            "topics": meta.get("topics", []),
            "entities": meta.get("entities", []),
            "summary": meta.get("summary", ""),
            "extension": meta.get("extension", ""),
        }
        if file_was_ingested(fname, audit_sources):
            entry["status"] = "ingested"
            ingested.append(entry)
        else:
            entry["status"] = "not_ingested"
            not_ingested.append(entry)

    by_type = defaultdict(list)
    for f in not_ingested:
        by_type[f["doc_type"]].append(f["name"])

    report = {
        "generated_at": datetime.now().isoformat(),
        "total_indexed": len(index.get("files", {})),
        "total_ingested": len(ingested),
        "total_not_ingested": len(not_ingested),
        "not_ingested_by_doc_type": {
            dt: {"count": len(files), "files": sorted(files)}
            for dt, files in sorted(by_type.items(), key=lambda x: -len(x[1]))
        },
        "not_ingested_files": sorted(not_ingested, key=lambda x: (priority_key(x["doc_type"]), x["name"])),
        "ingested_files": sorted(ingested, key=lambda x: x["name"]),
    }

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    logger.info("Audit report written to %s", REPORT_FILE)

    logger.info("\n=== INGESTION AUDIT REPORT ===")
    logger.info("Total indexed:      %d", report["total_indexed"])
    logger.info("Already ingested:   %d", report["total_ingested"])
    logger.info("NOT ingested:       %d", report["total_not_ingested"])
    logger.info("")
    logger.info("Breakdown by doc_type (not ingested):")
    for dt, info in report["not_ingested_by_doc_type"].items():
        logger.info("  %-18s %d files", dt, info["count"])

    return report


# ---------------------------------------------------------------------------
# LLM extraction — turns raw text into structured knowledge items
# ---------------------------------------------------------------------------

def extract_knowledge_items_llm(
    text: str,
    filename: str,
    doc_type: str,
    machines_hint: List[str],
    topics_hint: List[str],
    entities_hint: List[str],
) -> List[Dict[str, Any]]:
    """Use GPT-4o-mini to extract structured knowledge from document text."""
    import openai

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return _extract_knowledge_local(text, filename, doc_type, machines_hint)

    knowledge_type = DOC_TYPE_TO_KNOWLEDGE_TYPE.get(doc_type, "general")

    # Truncate very large texts to save tokens
    max_chars = 12000
    truncated = text[:max_chars]
    if len(text) > max_chars:
        truncated += f"\n\n[... truncated, {len(text) - max_chars} more chars ...]"

    prompt = f"""Extract structured knowledge from this document for a thermoforming machine company's knowledge base.

FILENAME: {filename}
DOC_TYPE: {doc_type}
KNOWN MACHINES: {', '.join(machines_hint) if machines_hint else 'none detected'}
KNOWN TOPICS: {', '.join(topics_hint) if topics_hint else 'none detected'}
KNOWN ENTITIES: {', '.join(entities_hint) if entities_hint else 'none detected'}

DOCUMENT TEXT:
{truncated}

Return a JSON array of knowledge items. Each item should capture ONE distinct fact or piece of information:
[
  {{
    "text": "Full knowledge text (2-5 sentences, self-contained, include context)",
    "summary": "One-line summary for memory storage",
    "entity": "Primary entity (machine model like PF1-C-2015, or company name, or topic)",
    "knowledge_type": "{knowledge_type}",
    "confidence": 0.9
  }}
]

Rules:
- Extract 3-10 items per document (more for rich documents, fewer for simple ones)
- Each item must be self-contained and useful without the original document
- For quotes: extract machine model, pricing, customer, application, key specs
- For presentations: extract key claims, capabilities, case studies
- For orders: extract customer, machine ordered, timeline, value
- For emails: extract inquiry details, customer needs, application
- For catalogues: extract machine capabilities, key specs, applications
- For contracts: extract parties, scope, terms
- Set confidence lower (0.6-0.8) for inferred information
- Return ONLY valid JSON array"""

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Extract structured knowledge from documents. Return only valid JSON arrays."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        items = json.loads(raw)
        if not isinstance(items, list):
            items = [items]
        return items
    except Exception as e:
        logger.warning("LLM extraction failed for %s: %s", filename, e)
        return _extract_knowledge_local(text, filename, doc_type, machines_hint)


def _extract_knowledge_local(
    text: str, filename: str, doc_type: str, machines_hint: List[str],
) -> List[Dict[str, Any]]:
    """Fallback: build a single knowledge item from raw text without LLM."""
    knowledge_type = DOC_TYPE_TO_KNOWLEDGE_TYPE.get(doc_type, "general")
    machines = machines_hint or extract_machines_from_text(text)
    entity = machines[0] if machines else filename

    # Take a meaningful excerpt
    excerpt = text[:3000].strip()
    if not excerpt or len(excerpt) < 20:
        return []

    return [{
        "text": excerpt,
        "summary": f"{doc_type.replace('_', ' ').title()} document: {filename}",
        "entity": entity,
        "knowledge_type": knowledge_type,
        "confidence": 0.7,
    }]


# ---------------------------------------------------------------------------
# Quote-specific batch processing
# ---------------------------------------------------------------------------

PRICE_PATTERNS = [
    (r'(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:/-|lakhs?|lacs?)?', 'INR'),
    (r'(?:USD|\$)\s*([\d,]+(?:\.\d+)?)', 'USD'),
    (r'(?:EUR|€)\s*([\d,]+(?:\.\d+)?)', 'EUR'),
    (r'([\d,]+)\s*(?:INR|Rs)', 'INR'),
]


def extract_quote_knowledge(
    text: str, filename: str, machines_hint: List[str],
) -> List[Dict[str, Any]]:
    """Specialised extractor for quote PDFs — regex first, LLM enrichment."""
    machines = machines_hint or extract_machines_from_text(text)

    prices: List[Dict] = []
    for pattern, currency in PRICE_PATTERNS:
        for m in re.findall(pattern, text, re.IGNORECASE):
            try:
                val = float(m.replace(',', ''))
                if val < 1000:
                    val *= 100000
                if currency == 'USD':
                    val *= 83
                elif currency == 'EUR':
                    val *= 90
                if 200_000 <= val <= 500_000_000:
                    prices.append({"amount": int(val), "currency": currency, "original": m})
            except (ValueError, TypeError):
                continue

    # Deduplicate prices
    seen_amounts: set = set()
    unique_prices: List[Dict] = []
    for p in prices:
        if p["amount"] not in seen_amounts:
            seen_amounts.add(p["amount"])
            unique_prices.append(p)
    prices = unique_prices[:5]

    # Customer extraction from text
    customer = ""
    for pat in [
        r'(?:To|Attention|Attn)[:\s]+([A-Z][A-Za-z\s]+(?:Ltd|Inc|Corp|Pvt|LLC|GmbH|S\.?A\.?)?)',
        r'Quote\s+(?:for|to)\s+([A-Z][A-Za-z\s]+)',
        r'Offer\s+(?:for|to)\s+([A-Z][A-Za-z\s]+)',
    ]:
        match = re.search(pat, text[:3000])
        if match:
            name = match.group(1).strip()
            if 'machinecraft' not in name.lower() and 3 < len(name) < 50:
                customer = re.sub(r'\s+', ' ', name)
                break

    entity = machines[0] if machines else (customer or filename)
    prices_str = ', '.join(f"{p['currency']} {p['original']}" for p in prices[:3])
    machines_str = ', '.join(machines[:3])

    summary = f"Quote for {machines_str or 'thermoforming machine'}"
    if customer:
        summary += f" to {customer}"
    if prices_str:
        summary += f" — {prices_str}"

    items = [{
        "text": text[:5000],
        "summary": summary,
        "entity": entity,
        "knowledge_type": "pricing",
        "confidence": 0.85,
        "metadata": {
            "doc_type": "machine_quote",
            "machines": machines,
            "prices": prices,
            "customer": customer,
        },
    }]
    return items


# ---------------------------------------------------------------------------
# Core ingestion loop
# ---------------------------------------------------------------------------

def get_files_to_ingest(
    doc_type_filter: Optional[str] = None,
    resume: bool = False,
) -> List[Dict]:
    """Return metadata entries for files that still need ingestion, sorted by priority."""
    index = load_metadata_index()
    audit_sources = load_audit_sources()
    progress = load_progress() if resume else {"completed_files": []}
    completed_set = set(progress.get("completed_files", []))

    pending = []
    for rel_path, meta in index.get("files", {}).items():
        fname = meta.get("name", "")
        if file_was_ingested(fname, audit_sources):
            continue
        if resume and rel_path in completed_set:
            continue
        dt = meta.get("doc_type", "other")
        if doc_type_filter and dt != doc_type_filter:
            continue
        pending.append({
            "rel_path": rel_path,
            "abs_path": meta.get("path", str(IMPORTS_DIR / rel_path)),
            "name": fname,
            "doc_type": dt,
            "size_kb": meta.get("size_kb", 0),
            "machines": meta.get("machines", []),
            "topics": meta.get("topics", []),
            "entities": meta.get("entities", []),
            "summary": meta.get("summary", ""),
            "extension": meta.get("extension", ""),
        })

    pending.sort(key=lambda f: (priority_key(f["doc_type"]), f["name"]))
    return pending


def ingest_file(
    file_info: Dict,
    ingestor,
    KnowledgeItem,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Extract and ingest a single file. Returns a result dict."""
    from document_extractor import extract_document

    fpath = Path(file_info["abs_path"])
    fname = file_info["name"]
    doc_type = file_info["doc_type"]
    result = {"file": fname, "doc_type": doc_type, "status": "skipped", "items": 0}

    if not fpath.exists():
        result["status"] = "missing"
        logger.warning("  File not found: %s", fpath)
        return result

    # Extract text
    try:
        text = extract_document(str(fpath))
    except Exception as e:
        result["status"] = "extract_error"
        result["error"] = str(e)
        logger.warning("  Extraction error for %s: %s", fname, e)
        return result

    if not text or len(text.strip()) < 30:
        result["status"] = "no_text"
        logger.info("  No usable text in %s", fname)
        return result

    # Extract knowledge items
    if doc_type == "quote":
        items = extract_quote_knowledge(
            text, fname, file_info.get("machines", []),
        )
    else:
        items = extract_knowledge_items_llm(
            text, fname, doc_type,
            machines_hint=file_info.get("machines", []),
            topics_hint=file_info.get("topics", []),
            entities_hint=file_info.get("entities", []),
        )

    if not items:
        result["status"] = "no_items"
        logger.info("  No knowledge items extracted from %s", fname)
        return result

    result["items"] = len(items)

    if dry_run:
        result["status"] = "dry_run"
        for it in items[:2]:
            logger.info("    [preview] entity=%s type=%s summary=%s",
                        it.get("entity", "?"), it.get("knowledge_type", "?"),
                        (it.get("summary", "") or "")[:80])
        return result

    # Pre-storage verification: check entities against emails and existing knowledge
    try:
        from ingestion_verifier import verify_knowledge_item
        verified_items = []
        for it in items:
            entity = it.get("entity", "")
            vr = verify_knowledge_item(
                entity=entity,
                text=it.get("text", ""),
                knowledge_type=it.get("knowledge_type", "general"),
                source_file=fname,
                confidence=it.get("confidence", 0.9),
                skip_llm=(doc_type == "quote"),  # skip LLM for quotes (too many)
            )
            it["entity"] = vr.verified_entity
            it["confidence"] = vr.confidence
            if vr.entity_type != "unknown":
                it.setdefault("metadata", {})["entity_type"] = vr.entity_type
            if vr.action == "reject":
                logger.info("    [rejected] entity=%s reason=%s", entity, vr.issues)
                continue
            if vr.action == "queue_for_review":
                logger.info("    [queued] entity=%s conf=%.2f reason=%s",
                            entity, vr.confidence, vr.review_reason[:60])
            if vr.issues:
                it.setdefault("metadata", {})["verification_issues"] = vr.issues
            verified_items.append(it)
        items = verified_items
    except ImportError:
        pass  # verifier not available, proceed without it

    if not items:
        result["status"] = "no_items"
        result["items"] = 0
        logger.info("  All items rejected by verifier for %s", fname)
        return result

    # Build KnowledgeItem objects and ingest
    ki_list = []
    for it in items:
        ki = KnowledgeItem(
            text=it.get("text", ""),
            knowledge_type=it.get("knowledge_type", DOC_TYPE_TO_KNOWLEDGE_TYPE.get(doc_type, "general")),
            source_file=fname,
            summary=it.get("summary", ""),
            entity=it.get("entity", ""),
            metadata={
                k: v for k, v in it.get("metadata", {}).items()
                if isinstance(v, (str, int, float, bool, list))
            },
            confidence=it.get("confidence", 0.9),
        )
        ki_list.append(ki)

    try:
        ing_result = ingestor.ingest_batch(ki_list)
        result["status"] = "ingested" if ing_result.success else "ingest_error"
        result["items_ingested"] = ing_result.items_ingested
        result["items_skipped"] = ing_result.items_skipped
        if ing_result.errors:
            result["errors"] = ing_result.errors
    except Exception as e:
        result["status"] = "ingest_error"
        result["error"] = str(e)
        logger.error("  Ingest error for %s: %s", fname, e)

    return result


def run_ingestion(
    dry_run: bool = False,
    limit: int = 0,
    doc_type_filter: Optional[str] = None,
    resume: bool = False,
    sleep_between: float = 0.5,
):
    """Main ingestion loop."""
    pending = get_files_to_ingest(doc_type_filter=doc_type_filter, resume=resume)
    total = len(pending)

    if limit > 0:
        pending = pending[:limit]

    logger.info("=" * 70)
    logger.info("BULK IMPORTS INGESTION")
    logger.info("=" * 70)
    logger.info("Files to process:  %d / %d total pending", len(pending), total)
    logger.info("Dry run:           %s", dry_run)
    logger.info("Doc type filter:   %s", doc_type_filter or "all")
    logger.info("Resume:            %s", resume)
    logger.info("=" * 70)

    if not pending:
        logger.info("Nothing to ingest — all files are already in the knowledge base!")
        return

    # Show breakdown
    type_counts = defaultdict(int)
    for f in pending:
        type_counts[f["doc_type"]] += 1
    logger.info("Breakdown:")
    for dt in PRIORITY_ORDER:
        if dt in type_counts:
            logger.info("  %-18s %d files", dt, type_counts[dt])

    # Lazy-load ingestor only when actually ingesting
    ingestor = None
    KnowledgeItem = None
    if not dry_run:
        if not wait_for_qdrant():
            logger.error("Cannot proceed without Qdrant. Exiting.")
            return
        from knowledge_ingestor import KnowledgeIngestor
        from knowledge_ingestor import KnowledgeItem as KI
        KnowledgeItem = KI
        ingestor = KnowledgeIngestor(verbose=True, use_graph=False)

    progress_data = load_progress() if resume else {"completed_files": []}
    completed = list(progress_data.get("completed_files", []))

    stats = {
        "total": len(pending),
        "ingested": 0,
        "skipped": 0,
        "errors": 0,
        "no_text": 0,
        "dry_run": 0,
        "by_type": defaultdict(int),
        "started_at": datetime.now().isoformat(),
    }

    import signal, gc

    # Memory monitoring
    try:
        sys.path.insert(0, str(AGENT_DIR / "core"))
        from memory_monitor import MemoryMonitor, get_rss_gb
        monitor = MemoryMonitor(label="bulk_ingest")
        monitor.check("start")
        MEMORY_LIMIT = float(os.environ.get("IRA_MEMORY_LIMIT_GB", "8"))
    except ImportError:
        monitor = None
        MEMORY_LIMIT = 8.0
        def get_rss_gb():
            try:
                import resource
                rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                if os.uname().sysname == "Darwin":
                    return rss / (1 << 30)
                return (rss * 1024) / (1 << 30)
            except Exception:
                return 0.0

    class FileTimeout(Exception):
        pass

    def _alarm_handler(signum, frame):
        raise FileTimeout("File processing timed out")

    for idx, file_info in enumerate(pending, 1):
        # Memory safety check before each file
        rss = get_rss_gb()
        if rss >= MEMORY_LIMIT:
            logger.critical(
                "Memory limit reached (%.1f GB >= %.1f GB) at file %d/%d. "
                "Stopping to prevent system freeze. Re-run with --resume to continue.",
                rss, MEMORY_LIMIT, idx, len(pending),
            )
            gc.collect()
            rss = get_rss_gb()
            if rss >= MEMORY_LIMIT:
                break

        logger.info("\n[%d/%d] (%s) %s", idx, len(pending), file_info["doc_type"], file_info["name"])

        # Per-file timeout (90s) to avoid infinite hangs
        if not dry_run:
            signal.signal(signal.SIGALRM, _alarm_handler)
            signal.alarm(90)

        try:
            result = ingest_file(file_info, ingestor, KnowledgeItem, dry_run=dry_run)
        except FileTimeout:
            result = {"file": file_info["name"], "doc_type": file_info["doc_type"],
                      "status": "timeout", "items": 0}
            logger.warning("  TIMEOUT after 90s, skipping")
        except Exception as e:
            result = {"file": file_info["name"], "doc_type": file_info["doc_type"],
                      "status": "ingest_error", "items": 0, "error": str(e)}
            logger.error("  Unexpected error: %s", e)
        finally:
            if not dry_run:
                signal.alarm(0)

        status = result["status"]
        if status == "ingested":
            stats["ingested"] += 1
            stats["by_type"][file_info["doc_type"]] += 1
        elif status == "dry_run":
            stats["dry_run"] += 1
        elif status in ("no_text", "no_items", "missing"):
            stats["no_text"] += 1
        else:
            stats["errors"] += 1

        logger.info("  -> %s (items: %d)", status, result.get("items", 0))

        # Save progress after every file to survive crashes
        if not dry_run and status in ("ingested", "no_text", "no_items", "missing", "timeout"):
            completed.append(file_info["rel_path"])
            save_progress(completed)

        # Rate limit to avoid API hammering
        if not dry_run and status == "ingested":
            time.sleep(sleep_between)

        # Periodically check Qdrant health and GC
        if idx % 20 == 0:
            gc.collect()
            if not dry_run and not check_qdrant_health():
                logger.warning("Qdrant went down at file %d. Waiting...", idx)
                if not wait_for_qdrant():
                    logger.error("Qdrant unrecoverable. Stopping at file %d.", idx)
                    break

    # Final progress save
    if not dry_run:
        save_progress(completed)

    stats["finished_at"] = datetime.now().isoformat()

    logger.info("\n" + "=" * 70)
    logger.info("INGESTION COMPLETE")
    logger.info("=" * 70)
    logger.info("Total processed:   %d", stats["total"])
    logger.info("Ingested:          %d", stats["ingested"])
    logger.info("No usable text:    %d", stats["no_text"])
    logger.info("Errors:            %d", stats["errors"])
    if dry_run:
        logger.info("Dry run previews:  %d", stats["dry_run"])
    logger.info("")
    logger.info("By doc type:")
    for dt, count in sorted(stats["by_type"].items(), key=lambda x: -x[1]):
        logger.info("  %-18s %d", dt, count)

    return stats


# ---------------------------------------------------------------------------
# Subprocess-based batch mode (memory-safe)
# ---------------------------------------------------------------------------

def run_batched_ingestion(
    batch_size: int = 25,
    limit: int = 0,
    doc_type_filter: Optional[str] = None,
    sleep_between: float = 0.5,
):
    """
    Process files in subprocess batches to avoid memory accumulation.
    Each batch runs as a child process that exits cleanly, freeing all memory.
    """
    import subprocess

    pending = get_files_to_ingest(doc_type_filter=doc_type_filter, resume=True)
    total = len(pending)

    if limit > 0:
        pending = pending[:limit]

    logger.info("=" * 70)
    logger.info("BATCHED IMPORTS INGESTION")
    logger.info("=" * 70)
    logger.info("Total pending:     %d", total)
    logger.info("Processing:        %d", len(pending))
    logger.info("Batch size:        %d", batch_size)
    logger.info("=" * 70)

    if not pending:
        logger.info("Nothing to ingest!")
        return

    batch_num = 0
    processed = 0
    while processed < len(pending):
        batch_num += 1
        batch_limit = min(batch_size, len(pending) - processed)
        logger.info("\n--- Batch %d: files %d-%d of %d ---",
                    batch_num, processed + 1, processed + batch_limit, len(pending))

        cmd = [
            sys.executable, __file__,
            "--resume",
            "--limit", str(batch_limit),
            "--sleep", str(sleep_between),
        ]
        if doc_type_filter:
            cmd.extend(["--doc-type", doc_type_filter])

        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), timeout=600)

        if result.returncode != 0:
            logger.warning("Batch %d exited with code %d, continuing...", batch_num, result.returncode)

        processed += batch_limit
        logger.info("--- Batch %d complete. Total processed so far: %d ---", batch_num, processed)

    logger.info("\n" + "=" * 70)
    logger.info("ALL BATCHES COMPLETE")
    logger.info("=" * 70)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Bulk ingest all un-ingested imports")
    parser.add_argument("--dry-run", action="store_true", help="Preview without ingesting")
    parser.add_argument("--limit", type=int, default=0, help="Max files to process (0 = all)")
    parser.add_argument("--doc-type", type=str, default=None,
                        help="Only process this doc_type (e.g. quote, catalogue, presentation)")
    parser.add_argument("--report", action="store_true", help="Generate audit report and exit")
    parser.add_argument("--resume", action="store_true", help="Resume from last saved progress")
    parser.add_argument("--sleep", type=float, default=0.5,
                        help="Seconds to sleep between ingestions (default 0.5)")
    parser.add_argument("--batch", type=int, default=0, metavar="SIZE",
                        help="Process in subprocess batches of SIZE files (memory-safe)")
    args = parser.parse_args()

    if args.report:
        generate_audit_report()
        return

    if args.batch > 0:
        run_batched_ingestion(
            batch_size=args.batch,
            limit=args.limit,
            doc_type_filter=args.doc_type,
            sleep_between=args.sleep,
        )
        return

    run_ingestion(
        dry_run=args.dry_run,
        limit=args.limit,
        doc_type_filter=args.doc_type,
        resume=args.resume,
        sleep_between=args.sleep,
    )


if __name__ == "__main__":
    main()
