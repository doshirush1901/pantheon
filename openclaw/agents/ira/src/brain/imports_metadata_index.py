#!/usr/bin/env python3
"""
IMPORTS METADATA INDEX - LLM-Summarized File Database
=====================================================

Scans every file in data/imports/, extracts a text preview, and uses
GPT-4o-mini to generate structured metadata for each file:
  - summary: what the document is about
  - doc_type: quote, catalogue, order, presentation, email, spreadsheet, etc.
  - machines: machine models mentioned (PF1-C-2015, AM-5060, etc.)
  - topics: pricing, specs, customer, application, lead, etc.
  - entities: company names, people, countries
  - keywords: searchable terms

The index is stored as data/brain/imports_metadata.json and used by
nn_research.py for intelligent file selection.

Usage:
    # Build the full index (takes ~15-30 min for 500 files)
    python imports_metadata_index.py

    # Or from code:
    from imports_metadata_index import build_index, search_index
    build_index()                          # full rebuild
    results = search_index("PF1-2015 price")  # instant lookup
"""

import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

BRAIN_DIR = Path(__file__).parent
AGENT_DIR = BRAIN_DIR.parent.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))

IMPORTS_DIR = PROJECT_ROOT / "data" / "imports"
INDEX_PATH = PROJECT_ROOT / "data" / "brain" / "imports_metadata.json"
INDEX_PROGRESS_PATH = PROJECT_ROOT / "data" / "brain" / "imports_index_progress.json"

SUPPORTED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv", ".docx", ".txt", ".pptx", ".json", ".md"}
TEXT_PREVIEW_CHARS = 2000  # first 2000 chars for LLM summary
LLM_MODEL = "gpt-4o-mini"


# ===========================================================================
# TEXT EXTRACTION (lightweight — first N chars only)
# ===========================================================================

def _extract_preview(filepath: Path) -> str:
    """Extract a text preview from a file for LLM summarization."""
    try:
        from document_extractor import extract_document
        text = extract_document(str(filepath))
        return text[:TEXT_PREVIEW_CHARS] if text else ""
    except ImportError:
        pass
    except Exception as e:
        logger.debug("Could not extract %s: %s", filepath.name, e)
        return ""

    # Fallback for simple types
    if filepath.suffix.lower() in (".txt", ".json", ".csv", ".md"):
        try:
            return filepath.read_text(errors="ignore")[:TEXT_PREVIEW_CHARS]
        except Exception:
            return ""
    return ""


def _file_hash(filepath: Path) -> str:
    """Quick hash based on filename + size + mtime (not content — too slow for 500 files)."""
    stat = filepath.stat()
    key = f"{filepath.name}:{stat.st_size}:{int(stat.st_mtime)}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


# ===========================================================================
# LLM METADATA GENERATION
# ===========================================================================

def _generate_metadata_llm(filename: str, text_preview: str) -> Optional[Dict]:
    """Use LLM to generate structured metadata from a file preview."""
    try:
        import openai
    except ImportError:
        return None

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None

    prompt = f"""Analyze this document and return structured metadata as JSON.

FILENAME: {filename}

TEXT PREVIEW (first {TEXT_PREVIEW_CHARS} chars):
{text_preview[:TEXT_PREVIEW_CHARS]}

Return ONLY valid JSON with these fields:
{{
    "summary": "1-2 sentence description of what this document is about",
    "doc_type": "one of: quote, catalogue, order, presentation, email, spreadsheet, report, manual, contract, lead_list, customer_data, technical_spec, brochure, invoice, other",
    "machines": ["list of machine models mentioned, e.g. PF1-C-2015, AM-5060"],
    "topics": ["list from: pricing, specs, customer, application, lead, order, contract, presentation, marketing, technical, installation, warranty, shipping, competitor, market_research, training"],
    "entities": ["company names, person names, countries mentioned"],
    "keywords": ["5-10 important searchable terms from the document"]
}}"""

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "Extract structured metadata from documents. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.1,
        )
        text = response.choices[0].message.content.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)
    except Exception as e:
        logger.warning("LLM metadata failed for %s: %s", filename, e)
        return None


def _generate_metadata_local(filename: str, text_preview: str) -> Dict:
    """Fast local metadata extraction without LLM (fallback / for files with no text)."""
    name_lower = filename.lower()

    machines = re.findall(
        r'(PF1[-\s]?[A-Z]?[-\s]?\d+[-\s]?\d*|AM[-\s]?\w+\d+|IMG[-\s]?\d+|FCS[-\s]?\w+|UNO[-\s]?\w+|DUO[-\s]?\w+)',
        filename + " " + text_preview[:500], re.IGNORECASE)
    machines = list(set(m.upper().replace(" ", "-") for m in machines))

    doc_type = "other"
    type_keywords = {
        "quote": ["quote", "quotation", "offer", "price"],
        "catalogue": ["catalogue", "catalog", "brochure"],
        "order": ["order", "po", "purchase"],
        "presentation": ["ppt", "presentation", "pptx"],
        "email": ["gmail", "email", "mail"],
        "spreadsheet": ["xlsx", "xls", "csv"],
        "manual": ["manual", "instruction", "operating"],
        "contract": ["contract", "nda", "agreement"],
        "lead_list": ["lead", "contact", "inquiry", "visitor"],
        "technical_spec": ["spec", "technical", "table"],
    }
    for dtype, kws in type_keywords.items():
        if any(kw in name_lower for kw in kws):
            doc_type = dtype
            break

    words = re.findall(r'\b\w{4,}\b', (filename + " " + text_preview[:300]).lower())
    keywords = list(set(words))[:10]

    return {
        "summary": f"Document: {filename}",
        "doc_type": doc_type,
        "machines": machines,
        "topics": [],
        "entities": [],
        "keywords": keywords,
    }


# ===========================================================================
# INDEX BUILDING
# ===========================================================================

def _load_index() -> Dict:
    if INDEX_PATH.exists():
        try:
            return json.loads(INDEX_PATH.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {"files": {}, "built_at": None, "total_files": 0, "version": 2}


def _save_index(index: Dict):
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False))


def _save_progress(done: int, total: int, current_file: str):
    INDEX_PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PROGRESS_PATH.write_text(json.dumps({
        "done": done, "total": total, "current": current_file,
        "percent": round(done / total * 100, 1) if total else 0,
        "updated_at": datetime.now().isoformat(),
    }, indent=2))


def build_index(use_llm: bool = True, force: bool = False,
                progress_callback=None) -> Dict:
    """
    Build or update the metadata index for all files in data/imports/.

    Args:
        use_llm: Use GPT-4o-mini for summaries (True) or local-only (False)
        force: Rebuild even if file hash hasn't changed
        progress_callback: Optional fn(done, total, filename) for progress reporting

    Returns:
        Stats dict with counts
    """
    index = _load_index() if not force else {"files": {}, "built_at": None, "total_files": 0, "version": 2}
    existing_hashes = {v.get("hash") for v in index.get("files", {}).values()}

    all_files = []
    for fp in IMPORTS_DIR.rglob("*"):
        if fp.is_file() and not fp.name.startswith(".") and fp.suffix.lower() in SUPPORTED_EXTENSIONS:
            all_files.append(fp)

    total = len(all_files)
    new_count = 0
    skipped = 0
    errors = 0

    for i, fp in enumerate(all_files):
        fhash = _file_hash(fp)
        rel_path = str(fp.relative_to(IMPORTS_DIR))

        # Skip if already indexed and hash matches
        if not force and rel_path in index["files"] and index["files"][rel_path].get("hash") == fhash:
            skipped += 1
            continue

        if progress_callback:
            progress_callback(i + 1, total, fp.name)
        _save_progress(i + 1, total, fp.name)

        try:
            preview = _extract_preview(fp)

            if use_llm and preview and len(preview) > 50:
                metadata = _generate_metadata_llm(fp.name, preview)
                if not metadata:
                    metadata = _generate_metadata_local(fp.name, preview)
            else:
                metadata = _generate_metadata_local(fp.name, preview)

            index["files"][rel_path] = {
                "name": fp.name,
                "path": str(fp),
                "hash": fhash,
                "size_kb": fp.stat().st_size // 1024,
                "extension": fp.suffix.lower(),
                "indexed_at": datetime.now().isoformat(),
                **metadata,
            }
            new_count += 1

            # Save periodically (every 20 files)
            if new_count % 20 == 0:
                _save_index(index)

            # Rate limit LLM calls
            if use_llm and preview and len(preview) > 50:
                time.sleep(0.3)

        except Exception as e:
            logger.warning("Error indexing %s: %s", fp.name, e)
            errors += 1

    index["built_at"] = datetime.now().isoformat()
    index["total_files"] = len(index["files"])
    _save_index(index)

    # Clean up progress file
    if INDEX_PROGRESS_PATH.exists():
        INDEX_PROGRESS_PATH.unlink()

    stats = {"total": total, "new": new_count, "skipped": skipped, "errors": errors}
    logger.info("Index built: %s", stats)
    return stats


def build_index_local_only() -> Dict:
    """Build index using only local extraction (no LLM, instant)."""
    return build_index(use_llm=False, force=True)


# ===========================================================================
# SEARCH — used by nn_research.py
# ===========================================================================

def search_index(query: str, limit: int = 10) -> List[Dict]:
    """
    Search the metadata index for files relevant to a query.

    Scores files by:
    - Machine model match (highest weight)
    - Topic/keyword overlap
    - Entity match
    - Summary text match

    Returns list of {path, name, score, summary, doc_type, machines, ...}
    """
    index = _load_index()
    if not index.get("files"):
        return []

    query_lower = query.lower()
    query_words = set(re.findall(r'\b\w{3,}\b', query_lower))

    # Extract machine models from query
    query_machines = set(
        m.upper().replace(" ", "-") for m in
        re.findall(r'(PF1[-\s]?[A-Z]?[-\s]?\d+[-\s]?\d*|AM[-\s]?\w+|IMG[-\s]?\d+|FCS[-\s]?\w+|UNO[-\s]?\w+|DUO[-\s]?\w+)',
                   query, re.IGNORECASE)
    )

    results = []
    for rel_path, meta in index["files"].items():
        score = 0.0

        # Machine model match — strongest signal
        file_machines = set(m.upper() for m in meta.get("machines", []))
        machine_overlap = query_machines & file_machines
        score += len(machine_overlap) * 5.0

        # Keyword overlap
        file_keywords = set(k.lower() for k in meta.get("keywords", []))
        kw_overlap = query_words & file_keywords
        score += len(kw_overlap) * 1.0

        # Topic overlap
        file_topics = set(t.lower() for t in meta.get("topics", []))
        topic_words = {"pricing": {"price", "cost", "quote", "lakh", "usd", "inr"},
                       "specs": {"spec", "specification", "technical", "heater", "vacuum", "forming"},
                       "customer": {"customer", "order", "client", "company"},
                       "application": {"application", "automotive", "bathtub", "packaging"}}
        for topic, trigger_words in topic_words.items():
            if trigger_words & query_words and topic in file_topics:
                score += 2.0

        # Entity match
        for entity in meta.get("entities", []):
            if entity.lower() in query_lower:
                score += 3.0

        # Summary text match
        summary = meta.get("summary", "").lower()
        summary_hits = sum(1 for w in query_words if w in summary and len(w) > 3)
        score += summary_hits * 0.5

        # Filename match (lighter weight — metadata should dominate)
        name_lower = meta.get("name", "").lower()
        name_hits = sum(1 for w in query_words if w in name_lower and len(w) > 3)
        score += name_hits * 0.3

        if score > 0.3:
            results.append({
                "path": meta.get("path", ""),
                "name": meta.get("name", ""),
                "score": round(score, 2),
                "summary": meta.get("summary", ""),
                "doc_type": meta.get("doc_type", ""),
                "machines": meta.get("machines", []),
                "topics": meta.get("topics", []),
            })

    results.sort(key=lambda x: -x["score"])
    return results[:limit]


def get_index_stats() -> Dict:
    """Get stats about the current index."""
    index = _load_index()
    files = index.get("files", {})

    if not files:
        return {"indexed": 0, "built_at": None}

    doc_types = {}
    total_machines = set()
    for meta in files.values():
        dt = meta.get("doc_type", "other")
        doc_types[dt] = doc_types.get(dt, 0) + 1
        for m in meta.get("machines", []):
            total_machines.add(m)

    # Check if there are unindexed files
    all_files = 0
    if IMPORTS_DIR.exists():
        all_files = sum(1 for f in IMPORTS_DIR.rglob("*")
                        if f.is_file() and not f.name.startswith(".")
                        and f.suffix.lower() in SUPPORTED_EXTENSIONS)

    return {
        "indexed": len(files),
        "total_on_disk": all_files,
        "unindexed": all_files - len(files),
        "built_at": index.get("built_at"),
        "doc_types": doc_types,
        "unique_machines": len(total_machines),
        "top_machines": sorted(total_machines)[:20],
    }


def get_index_progress() -> Optional[Dict]:
    """Get current indexing progress (if running)."""
    if INDEX_PROGRESS_PATH.exists():
        try:
            return json.loads(INDEX_PROGRESS_PATH.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return None


# ===========================================================================
# CLI
# ===========================================================================

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Build imports metadata index")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM summaries (fast local-only)")
    parser.add_argument("--force", action="store_true", help="Force rebuild all entries")
    args = parser.parse_args()

    def progress(done, total, name):
        print(f"  [{done}/{total}] {name}")

    stats = build_index(use_llm=not args.no_llm, force=args.force, progress_callback=progress)
    print(f"\nDone: {stats}")
    print(f"Index saved to: {INDEX_PATH}")
