#!/usr/bin/env python3
"""
NN RESEARCH MODE - Iterative Nearest-Neighbor Knowledge Discovery
=================================================================

When Ira doesn't know something:
1. Acknowledge the gap
2. Scan data/imports/ using NN filename matching (boosted by learned paths)
3. Extract text, LLM-parse the answer
4. Send to Rushabh via Telegram
5. If CONFIRMED → store in knowledge + record the search path for learning
6. If REJECTED → automatically retry with next-best files (loop until found)

The search path learning means Ira gets faster at finding answers over time.

Usage:
    from nn_research import research_and_report, handle_research_feedback
"""

import json
import logging
import os
import re
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

BRAIN_DIR = Path(__file__).parent
AGENT_DIR = BRAIN_DIR.parent.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))

IMPORTS_DIR = PROJECT_ROOT / "data" / "imports"
DATA_BRAIN = PROJECT_ROOT / "data" / "brain"
RESEARCH_LOG_PATH = DATA_BRAIN / "nn_research_log.json"
PENDING_FEEDBACK_PATH = DATA_BRAIN / "nn_pending_feedback.json"
SEARCH_PATHS_PATH = DATA_BRAIN / "nn_search_paths.json"
FILE_MANIFEST_PATH = DATA_BRAIN / "file_manifest.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


# ===========================================================================
# LEARNED SEARCH PATHS — Ira remembers which files answered which queries
# ===========================================================================

class SearchPathMemory:
    """
    Stores mappings: query_keywords → file patterns that worked.
    Next time a similar query comes in, those files get a massive boost.
    """

    def __init__(self):
        self._data = self._load()

    def _load(self) -> Dict:
        if SEARCH_PATHS_PATH.exists():
            try:
                return json.loads(SEARCH_PATHS_PATH.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return {"paths": [], "stats": {"total_searches": 0, "total_found": 0}}

    def _save(self):
        DATA_BRAIN.mkdir(parents=True, exist_ok=True)
        SEARCH_PATHS_PATH.write_text(json.dumps(self._data, indent=2))

    def record_success(self, query: str, keywords: List[str], winning_files: List[str],
                       rejected_files: List[str], attempts: int):
        """Record a successful search path so we learn from it."""
        self._data["paths"].append({
            "keywords": keywords[:10],
            "winning_files": winning_files[:3],
            "rejected_files": rejected_files[:10],
            "attempts": attempts,
            "query_sample": query[:200],
            "timestamp": datetime.now().isoformat(),
        })
        self._data["paths"] = self._data["paths"][-500:]
        self._data["stats"]["total_found"] = self._data["stats"].get("total_found", 0) + 1
        self._save()

    def record_search(self):
        self._data["stats"]["total_searches"] = self._data["stats"].get("total_searches", 0) + 1
        self._save()

    def get_file_boosts(self, keywords: List[str]) -> Dict[str, float]:
        """
        Given query keywords, return filename → boost score based on past successes.
        Files that answered similar queries before get a big boost.
        Files that were rejected for similar queries get penalized.
        """
        boosts: Dict[str, float] = {}
        kw_set = set(k.lower() for k in keywords)

        for path_entry in self._data.get("paths", []):
            stored_kws = set(k.lower() for k in path_entry.get("keywords", []))
            overlap = kw_set & stored_kws
            if not overlap:
                continue

            relevance = len(overlap) / max(len(kw_set), 1)
            if relevance < 0.3:
                continue

            for f in path_entry.get("winning_files", []):
                boosts[f] = boosts.get(f, 0) + relevance * 3.0

            for f in path_entry.get("rejected_files", []):
                boosts[f] = boosts.get(f, 0) - relevance * 1.0

        return boosts


_search_memory = None

def _get_search_memory() -> SearchPathMemory:
    global _search_memory
    if _search_memory is None:
        _search_memory = SearchPathMemory()
    return _search_memory


# ===========================================================================
# FILE MANIFEST — Human-written descriptions of what's inside each file
# ===========================================================================

class FileManifest:
    """
    Maps filenames to human-written descriptions of their contents.
    When a user uploads a file via Telegram with a caption like
    "Updated PF1-C pricing for 2026 including servo variants",
    that description is stored here so NN research can match queries
    against file *contents* — not just filenames.
    """

    def __init__(self):
        self._data = self._load()

    def _load(self) -> Dict:
        if FILE_MANIFEST_PATH.exists():
            try:
                return json.loads(FILE_MANIFEST_PATH.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return {"files": {}, "stats": {"total_files": 0}}

    def _save(self):
        DATA_BRAIN.mkdir(parents=True, exist_ok=True)
        FILE_MANIFEST_PATH.write_text(json.dumps(self._data, indent=2))

    def add_file(self, filename: str, description: str, original_name: str = None,
                 file_path: str = None):
        """Register a file with its human-written description."""
        entry = self._data["files"].get(filename, {})
        descriptions = entry.get("descriptions", [])
        descriptions.append({
            "text": description,
            "timestamp": datetime.now().isoformat(),
        })
        self._data["files"][filename] = {
            "descriptions": descriptions[-10:],
            "original_name": original_name or filename,
            "file_path": file_path,
            "last_updated": datetime.now().isoformat(),
        }
        self._data["stats"]["total_files"] = len(self._data["files"])
        self._save()

    def get_description_boost(self, filename: str, keywords: List[str]) -> float:
        """Score how well a file's descriptions match the query keywords."""
        entry = self._data["files"].get(filename)
        if not entry:
            return 0.0

        all_desc_text = " ".join(
            d["text"].lower() for d in entry.get("descriptions", [])
        )
        if not all_desc_text:
            return 0.0

        score = 0.0
        for kw in keywords:
            kw_lower = kw.lower().replace("-", " ")
            if kw_lower in all_desc_text:
                score += 2.0
                if len(kw_lower) >= 6:
                    score += 1.0
        return score

    def get_all_descriptions(self, filename: str) -> str:
        """Get concatenated descriptions for a file (used by LLM context)."""
        entry = self._data["files"].get(filename)
        if not entry:
            return ""
        return "\n".join(d["text"] for d in entry.get("descriptions", []))


_file_manifest = None

def get_file_manifest() -> FileManifest:
    global _file_manifest
    if _file_manifest is None:
        _file_manifest = FileManifest()
    return _file_manifest


# ===========================================================================
# FILE SCORING
# ===========================================================================

def _extract_keywords(query: str) -> List[str]:
    keywords = []
    models = re.findall(
        r'(PF1[-\s]?[A-Z]?[-\s]?\d+[-\s]?\d*|AM[-\s]?\w+|IMG[-\s]?\d+|FCS[-\s]?\w+|UNO[-\s]?\w+|DUO[-\s]?\w+)',
        query, re.IGNORECASE)
    keywords.extend([m.upper().replace(" ", "-") for m in models])

    words = re.findall(r'\b\w{3,}\b', query.lower())
    stop = {"the", "for", "and", "what", "how", "does", "which", "this", "that",
            "with", "from", "have", "has", "are", "was", "were", "been", "will",
            "can", "could", "would", "should", "about", "into", "over", "after",
            "before", "machine", "best", "suited", "base", "price"}
    keywords.extend([w for w in words if w not in stop])
    return list(dict.fromkeys(keywords))


def _score_file(filepath: Path, keywords: List[str], boosts: Dict[str, float],
                manifest: FileManifest = None) -> float:
    name_lower = filepath.stem.lower().replace("-", " ").replace("_", " ")
    score = 0.0

    for kw in keywords:
        kw_lower = kw.lower().replace("-", " ")
        if kw_lower in name_lower:
            score += 1.0
            if len(kw_lower) >= 6:
                score += 0.5

    suffix = filepath.suffix.lower()
    score += {".pdf": 0.1, ".xlsx": 0.15, ".xls": 0.15, ".csv": 0.1, ".docx": 0.1}.get(suffix, 0)

    for term in ["quote", "offer", "catalogue", "catalog", "spec", "quotation", "manual"]:
        if term in name_lower:
            score += 0.3

    # Apply learned boosts/penalties
    fname = filepath.name
    score += boosts.get(fname, 0)

    # Apply manifest description boost — human-written context about file contents
    if manifest:
        score += manifest.get_description_boost(fname, keywords)

    return score


def find_relevant_files(query: str, exclude: Set[str] = None, limit: int = 5) -> List[Dict]:
    """
    Find relevant files using a 3-layer scoring system:
      1. Metadata index (LLM summaries) — strongest signal
      2. Learned search paths — boosts from past successes
      3. Filename keyword matching + FileManifest — fallback
    """
    exclude = exclude or set()
    keywords = _extract_keywords(query)
    if not keywords:
        return []

    memory = _get_search_memory()
    memory.record_search()
    boosts = memory.get_file_boosts(keywords)
    manifest = get_file_manifest()

    # --- Layer 1: Metadata index (if available) ---
    metadata_scores: Dict[str, Dict] = {}
    try:
        from imports_metadata_index import search_index, get_index_stats
        stats = get_index_stats()
        if stats.get("indexed", 0) > 0:
            indexed_results = search_index(query, limit=limit + len(exclude) + 20)
            for r in indexed_results:
                fname = r.get("name", "")
                if fname not in exclude:
                    metadata_scores[fname] = {
                        "path": r["path"], "name": fname,
                        "meta_score": r["score"],
                        "summary": r.get("summary", ""),
                        "doc_type": r.get("doc_type", ""),
                    }
    except ImportError:
        pass
    except Exception as e:
        logger.debug("Metadata index unavailable: %s", e)

    # --- Layer 2+3: Filename scoring + manifest + search path boosts ---
    candidates = []
    for fp in IMPORTS_DIR.rglob("*"):
        if not fp.is_file() or fp.name.startswith("."):
            continue
        if fp.suffix.lower() not in (".pdf", ".xlsx", ".xls", ".csv", ".docx", ".txt", ".pptx", ".json"):
            continue
        if fp.name in exclude:
            continue

        filename_score = _score_file(fp, keywords, boosts, manifest)
        meta_entry = metadata_scores.get(fp.name)
        meta_score = meta_entry["meta_score"] if meta_entry else 0

        # Combined score: metadata dominates when available
        combined = meta_score * 2.0 + filename_score
        if combined > 0.2:
            entry = {
                "path": str(fp), "name": fp.name,
                "score": round(combined, 2),
            }
            if meta_entry:
                entry["summary"] = meta_entry.get("summary", "")
                entry["doc_type"] = meta_entry.get("doc_type", "")
            candidates.append(entry)

    candidates.sort(key=lambda x: -x["score"])
    return candidates[:limit]


# ===========================================================================
# DOCUMENT EXTRACTION + LLM
# ===========================================================================

def _extract_text(filepath: str, max_chars: int = 15000) -> str:
    try:
        from document_extractor import extract_document
        text = extract_document(filepath)
        return text[:max_chars] if text else ""
    except ImportError:
        pass
    p = Path(filepath)
    if p.suffix.lower() in (".txt", ".json", ".csv"):
        return p.read_text(errors="ignore")[:max_chars]
    return ""


def _extract_answer_with_llm(query: str, documents: List[Dict]) -> Optional[str]:
    try:
        import openai
    except ImportError:
        return None

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None

    manifest = get_file_manifest()
    doc_texts = []
    for doc in documents[:3]:
        text = _extract_text(doc["path"])
        if text:
            header = f"--- {doc['name']} ---"
            desc = manifest.get_all_descriptions(doc["name"])
            if desc:
                header += f"\n[Uploader notes: {desc}]"
            doc_texts.append(f"{header}\n{text[:5000]}")

    if not doc_texts:
        return None

    prompt = f"""You are a Machinecraft Technologies knowledge assistant.
Extract the specific answer to this question from the documents below.
Be precise and factual. If the documents don't contain the answer, say "NOT FOUND".
Pay special attention to "Uploader notes" — these are human descriptions of what each document contains.

QUESTION: {query}

DOCUMENTS:
{"".join(doc_texts)}

Answer concisely with the specific data requested. Include the source document name."""

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Extract precise factual answers from Machinecraft documents."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800, temperature=0.1,
        )
        answer = response.choices[0].message.content.strip()
        if "NOT FOUND" in answer.upper():
            return None
        return answer
    except Exception as e:
        logger.error("LLM extraction failed: %s", e)
        return None


# ===========================================================================
# TELEGRAM
# ===========================================================================

def _send_telegram(text: str, chat_id: str = ""):
    import requests
    token = TELEGRAM_BOT_TOKEN
    cid = chat_id or TELEGRAM_CHAT_ID
    if not token or not cid:
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": cid, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        logger.error("Telegram send failed: %s", e)
        return False


# ===========================================================================
# PENDING FEEDBACK — tracks the full search journey
# ===========================================================================

def _load_pending() -> List[Dict]:
    if PENDING_FEEDBACK_PATH.exists():
        try:
            return json.loads(PENDING_FEEDBACK_PATH.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return []


def _save_pending(pending: List[Dict]):
    DATA_BRAIN.mkdir(parents=True, exist_ok=True)
    PENDING_FEEDBACK_PATH.write_text(json.dumps(pending[-50:], indent=2))


def _save_pending_entry(research_id: str, query: str, answer: str,
                        sources: List[str], tried_files: List[str],
                        attempt: int, chat_id: str):
    pending = _load_pending()
    # Remove any previous entry for this query (superseded by retry)
    pending = [p for p in pending if p.get("query") != query or p.get("status") != "pending"]
    pending.append({
        "id": research_id,
        "query": query,
        "answer": answer,
        "sources": sources,
        "tried_files": tried_files,
        "attempt": attempt,
        "chat_id": chat_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    })
    _save_pending(pending)


# ===========================================================================
# FEEDBACK HANDLER — confirm learns, reject retries
# ===========================================================================

def handle_research_feedback(research_id: str, is_positive: bool) -> str:
    """
    Handle /confirm or /reject.
    - Confirm: store answer + record search path for learning
    - Reject: mark files as tried, immediately search next-best files
    """
    pending = _load_pending()
    target = None
    for entry in pending:
        if entry["id"] == research_id:
            target = entry
            break

    if not target:
        return f"Research `{research_id}` not found."

    query = target["query"]
    chat_id = target.get("chat_id", "")
    tried = target.get("tried_files", [])
    attempt = target.get("attempt", 1)

    if is_positive:
        # === CONFIRM: learn and store ===
        target["status"] = "confirmed"
        _save_pending(pending)

        keywords = _extract_keywords(query)
        rejected_files = [f for f in tried if f not in target.get("sources", [])]
        memory = _get_search_memory()
        memory.record_success(
            query=query,
            keywords=keywords,
            winning_files=target.get("sources", []),
            rejected_files=rejected_files,
            attempts=attempt,
        )

        _store_in_knowledge(query, target["answer"], target["sources"])
        _log_research("confirmed", query, target["answer"], target["sources"],
                      attempts=attempt, tried_files=tried)

        return (
            f"\u2705 **Learned!** Stored answer for: _{query}_\n"
            f"Found in {attempt} attempt(s). Search path recorded for faster lookups next time."
        )

    else:
        # === REJECT: retry with next-best files ===
        target["status"] = "rejected"
        _save_pending(pending)

        _log_research("rejected", query, target.get("answer"), target.get("sources", []),
                      attempts=attempt, tried_files=tried)

        # Trigger retry in background
        _retry_research_async(query, chat_id, tried, attempt + 1)

        return (
            f"\u274c Rejected. Searching next batch of files... (attempt {attempt + 1})\n"
            f"Already tried: {len(tried)} files"
        )


def _retry_research_async(query: str, chat_id: str, tried_files: List[str], attempt: int):
    """Retry research in background, excluding already-tried files."""
    def _run():
        try:
            _do_research(query, chat_id, set(tried_files), attempt)
        except Exception as e:
            logger.error("Retry research failed: %s", e)
            _send_telegram(f"\u274c Research retry failed: {e}", chat_id)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


# ===========================================================================
# CORE RESEARCH PIPELINE
# ===========================================================================

def _do_research(query: str, chat_id: str, exclude: Set[str], attempt: int):
    """Single research attempt. Finds files, extracts answer, sends to Telegram."""
    files = find_relevant_files(query, exclude=exclude, limit=5)

    if not files:
        _send_telegram(
            f"\U0001f6d1 **Search exhausted** (attempt {attempt})\n\n"
            f"Tried {len(exclude)} files, no more candidates for:\n_{query}_\n\n"
            f"This data might not be in our files. Consider adding the source document to `data/imports/`.",
            chat_id,
        )
        _log_research("exhausted", query, None, [], attempts=attempt, tried_files=list(exclude))
        return

    new_sources = [f["name"] for f in files[:3]]
    all_tried = list(exclude) + [f["name"] for f in files]

    if attempt > 1:
        _send_telegram(
            f"\U0001f504 **Retry #{attempt}** — trying {len(files)} new files...\n"
            f"Top candidates: {', '.join(new_sources)}",
            chat_id,
        )

    answer = _extract_answer_with_llm(query, files)

    if not answer:
        # LLM couldn't extract from these files either — auto-retry with next batch
        if attempt < 8:  # max 8 attempts
            _send_telegram(
                f"\U0001f50d No answer in these files. Trying next batch... (attempt {attempt})",
                chat_id,
            )
            _do_research(query, chat_id, set(all_tried), attempt + 1)
        else:
            _send_telegram(
                f"\U0001f6d1 **Gave up after {attempt} attempts.**\n"
                f"Searched {len(all_tried)} files for: _{query}_\n"
                f"The answer might not be in our documents.",
                chat_id,
            )
            _log_research("gave_up", query, None, [], attempts=attempt, tried_files=all_tried)
        return

    research_id = uuid.uuid4().hex[:8]
    _save_pending_entry(research_id, query, answer, new_sources, all_tried, attempt, chat_id)
    _log_research("found", query, answer, new_sources, attempts=attempt, tried_files=all_tried)

    msg = (
        f"\U0001f50d **NN Research Result** [`{research_id}`] (attempt {attempt})\n\n"
        f"**Query:** {query}\n\n"
        f"**Answer:**\n{answer}\n\n"
        f"**Sources:** {', '.join(new_sources)}\n"
        f"**Files searched:** {len(all_tried)} total\n\n"
        f"\u2705 `/confirm {research_id}` \u2014 Correct! Learn this\n"
        f"\u274c `/reject {research_id}` \u2014 Wrong, try next files"
    )
    _send_telegram(msg, chat_id)


def research_and_report(query: str, chat_id: str = "") -> Optional[str]:
    """Full NN research pipeline (synchronous, first attempt)."""
    _do_research(query, chat_id, exclude=set(), attempt=1)
    return None  # answer delivered async via Telegram


def research_async(query: str, chat_id: str = ""):
    """Run research in a background thread. Non-blocking."""
    def _run():
        try:
            file_count = sum(1 for f in IMPORTS_DIR.rglob("*") if f.is_file() and not f.name.startswith("."))
            _send_telegram(
                f"\U0001f50d **Researching...**\n_{query}_\n\n"
                f"Scanning {file_count} files in data/imports/...",
                chat_id,
            )
            _do_research(query, chat_id, exclude=set(), attempt=1)
        except Exception as e:
            logger.error("Async research failed: %s", e)
            _send_telegram(f"\u274c Research failed: {e}", chat_id)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread


# ===========================================================================
# KNOWLEDGE STORAGE
# ===========================================================================

def _store_in_knowledge(query: str, answer: str, sources: List[str]):
    weights_path = DATA_BRAIN / "training_weights.json"
    try:
        weights = {}
        if weights_path.exists():
            weights = json.loads(weights_path.read_text())
        reinforcements = weights.get("reinforcements", [])
        reinforcements.insert(0, {"category": "discovered", "fact": f"Q: {query} A: {answer}"})
        weights["reinforcements"] = reinforcements[:20]
        weights_path.write_text(json.dumps(weights, indent=2))
    except Exception as e:
        logger.error("Failed to store in training weights: %s", e)

    _log_research("stored", query, answer, sources)

    try:
        from knowledge_discovery import KnowledgeDiscoverer
        discoverer = KnowledgeDiscoverer()
        discoverer._store_discovery(query, answer, "nn_research", sources)
    except Exception as e:
        logger.debug("Could not store in Qdrant: %s", e)


def _log_research(status: str, query: str, answer: Optional[str], sources: List[str],
                  attempts: int = 1, tried_files: List[str] = None):
    log = []
    if RESEARCH_LOG_PATH.exists():
        try:
            log = json.loads(RESEARCH_LOG_PATH.read_text())
        except (json.JSONDecodeError, IOError):
            log = []

    log.append({
        "status": status,
        "query": query,
        "answer": answer[:500] if answer else None,
        "sources": sources,
        "attempts": attempts,
        "files_searched": len(tried_files) if tried_files else 0,
        "timestamp": datetime.now().isoformat(),
    })
    log = log[-200:]
    RESEARCH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESEARCH_LOG_PATH.write_text(json.dumps(log, indent=2))
