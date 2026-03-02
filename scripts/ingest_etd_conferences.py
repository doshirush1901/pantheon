#!/usr/bin/env python3
"""
ETD CONFERENCE PRESENTATIONS INGESTION
=======================================

Ingests ~110 PDFs from the European Thermoforming Division (ETD) conference
presentations (2008–2018) plus Euromould 2009 into Ira's knowledge base.

These are industry conference talks covering thermoforming technology, materials,
tooling, automation, sustainability, Industry 4.0, and market trends — a goldmine
for Ira's thermoforming domain expertise.

Usage:
    python scripts/ingest_etd_conferences.py                    # Full run
    python scripts/ingest_etd_conferences.py --dry-run          # Preview only
    python scripts/ingest_etd_conferences.py --dry-run --limit 5
    python scripts/ingest_etd_conferences.py --year 2016        # Only one year
    python scripts/ingest_etd_conferences.py --resume           # Resume from progress
    python scripts/ingest_etd_conferences.py --batch 20         # Memory-safe batches
"""

import argparse
import gc
import json
import logging
import os
import re
import signal
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ETD_DIR = PROJECT_ROOT / "data" / "imports" / "ETD Conference Presentations"
PROGRESS_FILE = PROJECT_ROOT / "data" / "brain" / "etd_ingest_progress.json"
HASHES_FILE = PROJECT_ROOT / "data" / "knowledge" / "ingested_hashes.json"

THERMOFORMING_TOPICS = [
    "thermoforming", "vacuum forming", "pressure forming", "twin sheet",
    "plug assist", "mold", "tooling", "heating", "cooling", "trimming",
    "material distribution", "wall thickness", "draw ratio", "sheet sag",
    "clamping", "forming window", "crystallinity", "orientation",
    "in-mold", "IML", "IMG", "decoration", "grain", "texture",
    "automation", "Industry 4.0", "simulation", "FEA",
    "PET", "PP", "PS", "ABS", "HIPS", "PC", "PMMA", "PEEK", "PVC",
    "bioplastic", "recycling", "sustainability", "circular economy",
    "packaging", "automotive", "aerospace", "medical",
    "heavy gauge", "thin gauge", "thick sheet", "roll-fed",
]

MACHINE_PATTERNS = [
    r'PF1-[A-Z]?-?\d{4}',
    r'PF2-\d+[xX]\d+',
    r'AM-?[A-Z]?-?\d{4}',
    r'AMP-?\d{4}',
    r'AMC-?\d{4}',
    r'IMG[SL]?-?\d{4}',
    r'FCS-?\d{4}',
    r'ATF-?\d{4}',
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def discover_pdfs(year_filter: Optional[str] = None) -> List[Dict]:
    """Walk the ETD directory and return metadata for each PDF."""
    pdfs = []
    if not ETD_DIR.exists():
        logger.error("ETD directory not found: %s", ETD_DIR)
        return pdfs

    for dirpath, _, files in os.walk(ETD_DIR):
        subdir = os.path.basename(dirpath)
        year = ""
        if "ETD" in subdir:
            year = subdir.replace("ETD ", "").strip()
            conference = f"ETD {year}"
        elif "Euromould" in subdir:
            year = subdir.replace("Euromould ", "").strip()
            conference = f"Euromould {year}"
        else:
            continue

        if year_filter and year != year_filter:
            continue

        for f in sorted(files):
            if not f.lower().endswith('.pdf') or f.startswith('.'):
                continue
            fpath = os.path.join(dirpath, f)
            pdfs.append({
                "path": fpath,
                "filename": f,
                "conference": conference,
                "year": year,
                "size_kb": os.path.getsize(fpath) / 1024,
            })

    pdfs.sort(key=lambda x: (x["year"], x["filename"]))
    return pdfs


def parse_presentation_metadata(filename: str) -> Dict:
    """Extract speaker, company, and topic from the filename convention."""
    name = Path(filename).stem

    # Strip leading number/prefix (e.g. "05 ", "15a ", "PPT 05 ")
    name = re.sub(r'^(?:PPT\s+)?\d+[a-z]?\s+', '', name, flags=re.IGNORECASE)

    parts = [p.strip() for p in name.split(',')]

    topic = parts[0] if parts else name
    company = parts[1].strip() if len(parts) > 1 else ""
    speaker = parts[2].strip() if len(parts) > 2 else ""

    # Some filenames use " - " as separator instead of ","
    if not company and ' - ' in topic:
        segments = topic.split(' - ')
        topic = segments[0].strip()
        if len(segments) > 1:
            speaker = segments[-1].strip()
        if len(segments) > 2:
            company = segments[1].strip()

    return {"topic": topic, "company": company, "speaker": speaker}


def extract_machines_from_text(text: str) -> List[str]:
    machines = set()
    for pattern in MACHINE_PATTERNS:
        for m in re.findall(pattern, text, re.IGNORECASE):
            machines.add(m.upper().replace(' ', '-'))
    return list(machines)


def extract_topics_from_text(text: str) -> List[str]:
    text_lower = text.lower()
    found = []
    for topic in THERMOFORMING_TOPICS:
        if topic.lower() in text_lower:
            found.append(topic)
    return found[:15]


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


def check_qdrant_health() -> bool:
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:6333/collections", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def wait_for_qdrant(max_wait: int = 120) -> bool:
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
# LLM extraction — conference-presentation-aware
# ---------------------------------------------------------------------------

def extract_knowledge_items_llm(
    text: str,
    filename: str,
    conference: str,
    year: str,
    meta: Dict,
    machines_hint: List[str],
    topics_hint: List[str],
) -> List[Dict[str, Any]]:
    """Use GPT-4o-mini to extract structured knowledge from a conference presentation."""
    import openai

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return _extract_knowledge_local(text, filename, conference, year, meta, machines_hint, topics_hint)

    max_chars = 14000
    truncated = text[:max_chars]
    if len(text) > max_chars:
        truncated += f"\n\n[... truncated, {len(text) - max_chars} more chars ...]"

    prompt = f"""Extract structured knowledge from this thermoforming industry conference presentation.

CONFERENCE: {conference} (year {year})
PRESENTATION: {meta['topic']}
COMPANY: {meta['company'] or 'unknown'}
SPEAKER: {meta['speaker'] or 'unknown'}
DETECTED MACHINES: {', '.join(machines_hint) if machines_hint else 'none'}
DETECTED TOPICS: {', '.join(topics_hint[:8]) if topics_hint else 'none'}

DOCUMENT TEXT:
{truncated}

Return a JSON array of knowledge items. Each should capture ONE distinct insight:
[
  {{
    "text": "Full knowledge text (2-5 sentences, self-contained, include the conference/year context)",
    "summary": "One-line summary",
    "entity": "Primary entity (technology, material, process, company, or machine model)",
    "knowledge_type": "thermoforming_industry",
    "confidence": 0.85,
    "tags": ["tag1", "tag2"]
  }}
]

Focus on extracting:
- Technical insights about thermoforming processes, materials, or tooling
- Industry trends and market data (growth rates, market sizes, regional data)
- New technologies, innovations, or research findings
- Case studies and real-world applications
- Material properties and processing parameters
- Comparisons between thermoforming and competing technologies
- Sustainability and recycling developments
- Automation and Industry 4.0 applications to thermoforming

Rules:
- Extract 3-12 items depending on content richness
- Each item MUST be self-contained and useful without the original slides
- Always mention the conference and year in the text for provenance
- Set confidence 0.7-0.85 (these are conference presentations, not verified specs)
- Skip items that are just slide titles or agenda items with no substance
- Return ONLY valid JSON array"""

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You extract structured knowledge from thermoforming conference presentations. Return only valid JSON arrays."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=3000,
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
        return _extract_knowledge_local(text, filename, conference, year, meta, machines_hint, topics_hint)


def _extract_knowledge_local(
    text: str,
    filename: str,
    conference: str,
    year: str,
    meta: Dict,
    machines_hint: List[str],
    topics_hint: List[str],
) -> List[Dict[str, Any]]:
    """Fallback: build knowledge items from raw text without LLM."""
    entity = machines_hint[0] if machines_hint else (meta["company"] or meta["topic"])

    excerpt = text[:4000].strip()
    if not excerpt or len(excerpt) < 30:
        return []

    summary = f"{conference}: {meta['topic']}"
    if meta["company"]:
        summary += f" ({meta['company']})"

    return [{
        "text": f"From {conference} presentation '{meta['topic']}'"
               + (f" by {meta['speaker']}" if meta['speaker'] else "")
               + (f" ({meta['company']})" if meta['company'] else "")
               + f":\n\n{excerpt}",
        "summary": summary,
        "entity": entity,
        "knowledge_type": "thermoforming_industry",
        "confidence": 0.7,
        "tags": topics_hint[:5],
    }]


# ---------------------------------------------------------------------------
# Core ingestion
# ---------------------------------------------------------------------------

def ingest_single(
    pdf_info: Dict,
    ingestor,
    KnowledgeItem,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Extract and ingest a single ETD presentation PDF."""
    from document_extractor import extract_pdf

    fpath = pdf_info["path"]
    fname = pdf_info["filename"]
    conference = pdf_info["conference"]
    year = pdf_info["year"]
    meta = parse_presentation_metadata(fname)

    result = {
        "file": fname, "conference": conference,
        "status": "skipped", "items": 0,
    }

    text = extract_pdf(fpath, max_pages=100)
    if not text or len(text.split()) < 20:
        result["status"] = "no_text"
        logger.info("  Insufficient text in %s (%d words)", fname, len(text.split()) if text else 0)
        return result

    machines = extract_machines_from_text(text)
    topics = extract_topics_from_text(text)

    items = extract_knowledge_items_llm(
        text, fname, conference, year, meta, machines, topics,
    )

    if not items:
        result["status"] = "no_items"
        logger.info("  No knowledge items extracted from %s", fname)
        return result

    result["items"] = len(items)

    if dry_run:
        result["status"] = "dry_run"
        for it in items[:3]:
            logger.info("    [preview] entity=%s summary=%s",
                        it.get("entity", "?"), (it.get("summary", "") or "")[:100])
        return result

    ki_list = []
    for it in items:
        tags = it.get("tags", topics[:5])
        ki = KnowledgeItem(
            text=it.get("text", ""),
            knowledge_type=it.get("knowledge_type", "thermoforming_industry"),
            source_file=f"ETD/{conference}/{fname}",
            summary=it.get("summary", ""),
            entity=it.get("entity", ""),
            metadata={
                "conference": conference,
                "year": year,
                "speaker": meta["speaker"],
                "company": meta["company"],
                "presentation_topic": meta["topic"],
                "tags": tags,
                "source_type": "conference_presentation",
            },
            confidence=it.get("confidence", 0.8),
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
    year_filter: Optional[str] = None,
    resume: bool = False,
    sleep_between: float = 0.5,
):
    """Main ingestion loop for ETD conference presentations."""
    pdfs = discover_pdfs(year_filter=year_filter)

    if resume:
        progress = load_progress()
        completed_set = set(progress.get("completed_files", []))
        pdfs = [p for p in pdfs if p["path"] not in completed_set]

    total_available = len(pdfs)
    if limit > 0:
        pdfs = pdfs[:limit]

    logger.info("=" * 70)
    logger.info("ETD CONFERENCE PRESENTATIONS INGESTION")
    logger.info("=" * 70)
    logger.info("Files to process:  %d / %d available", len(pdfs), total_available)
    logger.info("Dry run:           %s", dry_run)
    logger.info("Year filter:       %s", year_filter or "all")
    logger.info("Resume:            %s", resume)
    logger.info("=" * 70)

    if not pdfs:
        logger.info("Nothing to ingest!")
        return

    by_conf = defaultdict(int)
    for p in pdfs:
        by_conf[p["conference"]] += 1
    logger.info("Breakdown:")
    for conf in sorted(by_conf):
        logger.info("  %-20s %d files", conf, by_conf[conf])

    ingestor = None
    KnowledgeItem = None
    if not dry_run:
        if not wait_for_qdrant():
            logger.error("Cannot proceed without Qdrant. Exiting.")
            return
        from knowledge_ingestor import KnowledgeIngestor, KnowledgeItem as KI
        KnowledgeItem = KI
        ingestor = KnowledgeIngestor(verbose=True, use_graph=False)

    progress_data = load_progress() if resume else {"completed_files": []}
    completed = list(progress_data.get("completed_files", []))

    stats = {
        "total": len(pdfs), "ingested": 0, "skipped": 0,
        "errors": 0, "no_text": 0, "dry_run": 0,
        "items_total": 0, "by_conference": defaultdict(int),
        "started_at": datetime.now().isoformat(),
    }

    class FileTimeout(Exception):
        pass

    def _alarm_handler(signum, frame):
        raise FileTimeout("File processing timed out")

    for idx, pdf_info in enumerate(pdfs, 1):
        logger.info("\n[%d/%d] (%s) %s",
                    idx, len(pdfs), pdf_info["conference"], pdf_info["filename"])

        if not dry_run:
            signal.signal(signal.SIGALRM, _alarm_handler)
            signal.alarm(120)

        try:
            result = ingest_single(pdf_info, ingestor, KnowledgeItem, dry_run=dry_run)
        except FileTimeout:
            result = {"file": pdf_info["filename"], "conference": pdf_info["conference"],
                      "status": "timeout", "items": 0}
            logger.warning("  TIMEOUT after 120s, skipping")
        except Exception as e:
            result = {"file": pdf_info["filename"], "conference": pdf_info["conference"],
                      "status": "ingest_error", "items": 0, "error": str(e)}
            logger.error("  Unexpected error: %s", e)
        finally:
            if not dry_run:
                signal.alarm(0)

        status = result["status"]
        items = result.get("items", 0)
        stats["items_total"] += items

        if status == "ingested":
            stats["ingested"] += 1
            stats["by_conference"][pdf_info["conference"]] += 1
        elif status == "dry_run":
            stats["dry_run"] += 1
        elif status in ("no_text", "no_items"):
            stats["no_text"] += 1
        else:
            stats["errors"] += 1

        logger.info("  -> %s (items: %d)", status, items)

        if not dry_run and status in ("ingested", "no_text", "no_items", "timeout"):
            completed.append(pdf_info["path"])
            save_progress(completed)

        if not dry_run and status == "ingested":
            time.sleep(sleep_between)

        if idx % 20 == 0:
            gc.collect()
            if not dry_run and not check_qdrant_health():
                logger.warning("Qdrant went down at file %d. Waiting...", idx)
                if not wait_for_qdrant():
                    logger.error("Qdrant unrecoverable. Stopping at file %d.", idx)
                    break

    if not dry_run:
        save_progress(completed)

    stats["finished_at"] = datetime.now().isoformat()

    logger.info("\n" + "=" * 70)
    logger.info("ETD INGESTION COMPLETE")
    logger.info("=" * 70)
    logger.info("Total processed:     %d", stats["total"])
    logger.info("Ingested:            %d", stats["ingested"])
    logger.info("No usable text:      %d", stats["no_text"])
    logger.info("Errors:              %d", stats["errors"])
    logger.info("Knowledge items:     %d", stats["items_total"])
    if dry_run:
        logger.info("Dry run previews:    %d", stats["dry_run"])
    logger.info("")
    logger.info("By conference:")
    for conf in sorted(stats["by_conference"]):
        logger.info("  %-20s %d files", conf, stats["by_conference"][conf])

    return stats


# ---------------------------------------------------------------------------
# Subprocess batch mode (memory-safe for large runs)
# ---------------------------------------------------------------------------

def run_batched_ingestion(
    batch_size: int = 20,
    limit: int = 0,
    year_filter: Optional[str] = None,
    sleep_between: float = 0.5,
):
    import subprocess

    pdfs = discover_pdfs(year_filter=year_filter)
    progress = load_progress()
    completed_set = set(progress.get("completed_files", []))
    pdfs = [p for p in pdfs if p["path"] not in completed_set]

    if limit > 0:
        pdfs = pdfs[:limit]

    logger.info("=" * 70)
    logger.info("BATCHED ETD INGESTION")
    logger.info("=" * 70)
    logger.info("Total pending:     %d", len(pdfs))
    logger.info("Batch size:        %d", batch_size)
    logger.info("=" * 70)

    if not pdfs:
        logger.info("Nothing to ingest!")
        return

    batch_num = 0
    processed = 0
    while processed < len(pdfs):
        batch_num += 1
        batch_limit = min(batch_size, len(pdfs) - processed)
        logger.info("\n--- Batch %d: files %d-%d of %d ---",
                    batch_num, processed + 1, processed + batch_limit, len(pdfs))

        cmd = [
            sys.executable, __file__,
            "--resume",
            "--limit", str(batch_limit),
            "--sleep", str(sleep_between),
        ]
        if year_filter:
            cmd.extend(["--year", year_filter])

        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), timeout=900)

        if result.returncode != 0:
            logger.warning("Batch %d exited with code %d, continuing...",
                           batch_num, result.returncode)

        processed += batch_limit
        logger.info("--- Batch %d complete. Processed so far: %d ---",
                    batch_num, processed)

    logger.info("\n" + "=" * 70)
    logger.info("ALL BATCHES COMPLETE")
    logger.info("=" * 70)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Ingest ETD Conference Presentations into Ira's knowledge base"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without ingesting")
    parser.add_argument("--limit", type=int, default=0, help="Max files to process (0 = all)")
    parser.add_argument("--year", type=str, default=None,
                        help="Only process a specific year (e.g. 2016)")
    parser.add_argument("--resume", action="store_true", help="Resume from last progress")
    parser.add_argument("--sleep", type=float, default=0.5,
                        help="Seconds between ingestions (default 0.5)")
    parser.add_argument("--batch", type=int, default=0, metavar="SIZE",
                        help="Process in subprocess batches (memory-safe)")
    args = parser.parse_args()

    if args.batch > 0:
        run_batched_ingestion(
            batch_size=args.batch,
            limit=args.limit,
            year_filter=args.year,
            sleep_between=args.sleep,
        )
        return

    run_ingestion(
        dry_run=args.dry_run,
        limit=args.limit,
        year_filter=args.year,
        resume=args.resume,
        sleep_between=args.sleep,
    )


if __name__ == "__main__":
    main()
