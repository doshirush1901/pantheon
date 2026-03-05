#!/usr/bin/env python3
"""
Delphi — The Inner Voice (Rushabh's Oracle)
=============================================

Delphi is Ira's inner voice. She learns how Rushabh communicates by mining
real email conversations, running shadow simulations to measure the gap,
and injecting learned style guidance directly into Ira's system prompt.

She doesn't speak to customers. She whispers to Ira:
  "Rushabh would keep this to 3 sentences."
  "Rushabh would push for the close here."
  "Rushabh would mention the flagship European reference."

Three modes:
    1. BUILD     — Mine Gmail, build interaction map, extract style patterns
    2. SIMULATE  — Run customer personas through Ira, measure delta vs Rushabh
    3. GUIDANCE  — Inject learned patterns into system prompt (the inner voice)

Named after the Oracle at Delphi — the inner voice that guided heroes.
"""

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ira.delphi")

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "delphi"
INTERACTION_MAP_FILE = DATA_DIR / "interaction_map.json"
STYLE_PROFILE_FILE = DATA_DIR / "rushabh_style_profile.json"
SIMULATION_LOG_FILE = DATA_DIR / "simulation_log.jsonl"
DELTA_REPORT_FILE = DATA_DIR / "delta_report.json"

RUSHABH_ALIASES = {
    "founder@example-company.in", "founder@example-company.co.in",
    "founder@example-company.org", "founder@example-company.in",
    "sales@machinecraft.in",
}

# Populated at runtime from CRM / order book — these are example placeholders
PRIORITY_CUSTOMERS = [
    "[Customer 1]",
    "[Customer 2]",
    "[Customer 3]",
    "[Customer 4]",
    "[Customer 5]",
    "[Customer 6]",
    "[Customer 7]",
    "[Customer 8]",
    "[Customer 9]",
    "[Customer 10]",
    "[Customer 11]",
    "[Customer 12]",
    "[Customer 13]",
    "[Customer 14]",
    "[Customer 15]",
]


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class EmailTurn:
    sender: str          # "rushabh" or "customer"
    text: str
    subject: str = ""
    timestamp: str = ""
    word_count: int = 0

@dataclass
class CustomerInteraction:
    """All interactions with one customer."""
    company: str
    contact_name: str
    contact_email: str
    country: str = ""
    threads: List[Dict] = field(default_factory=list)
    rushabh_messages: List[str] = field(default_factory=list)
    customer_messages: List[str] = field(default_factory=list)
    total_exchanges: int = 0
    machines_discussed: List[str] = field(default_factory=list)
    deal_stage: str = ""
    style_notes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RushabhStyleProfile:
    """Distilled patterns from Rushabh's actual emails."""
    avg_word_count: float = 0.0
    median_word_count: float = 0.0
    greeting_distribution: Dict[str, int] = field(default_factory=dict)
    closer_distribution: Dict[str, int] = field(default_factory=dict)
    common_phrases: List[str] = field(default_factory=list)
    action_phrases: List[str] = field(default_factory=list)
    tone_markers: Dict[str, float] = field(default_factory=dict)
    per_customer_style: Dict[str, Dict] = field(default_factory=dict)
    sample_replies: List[Dict] = field(default_factory=list)
    total_messages_analyzed: int = 0
    built_at: str = ""


# =============================================================================
# 1. BUILD — Mine Gmail, build interaction map
# =============================================================================

async def build_interaction_map(
    max_customers: int = 15,
    max_threads_per_customer: int = 5,
) -> Dict[str, CustomerInteraction]:
    """Mine Gmail for Rushabh's customer conversations and build the map."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        import sys
        _tools_dir = str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "tools")
        _agent_dir = str(PROJECT_ROOT / "openclaw" / "agents" / "ira")
        if _tools_dir not in sys.path:
            sys.path.insert(0, _tools_dir)
        if _agent_dir not in sys.path:
            sys.path.insert(0, _agent_dir)
        from google_tools import gmail_search, gmail_get_thread
    except ImportError as e:
        logger.error("Could not import google_tools: %s", e)
        return {}

    interactions: Dict[str, CustomerInteraction] = {}

    customer_seeds = _load_customer_seeds()
    logger.info("Loaded %d customer seeds for interaction mining", len(customer_seeds))

    for idx, seed in enumerate(customer_seeds[:max_customers]):
        company = seed["company"]
        email = seed.get("email", "")
        domain = seed.get("domain", "")

        logger.info("[%d/%d] Mining: %s (%s)", idx + 1, min(max_customers, len(customer_seeds)), company, email or domain)

        search_terms = []
        if email and "@" in email and "placeholder" not in email:
            search_terms.append(f"from:{email}")
            search_terms.append(f"to:{email}")
        elif domain and "." in domain and "placeholder" not in domain:
            search_terms.append(f"from:@{domain}")
            search_terms.append(f"to:@{domain}")
        else:
            short_name = company.split()[0] if company else ""
            if short_name and len(short_name) >= 3:
                search_terms.append(f"{short_name} from:me newer_than:24m")
                search_terms.append(f"{short_name} to:me newer_than:24m")

        all_turns: List[EmailTurn] = []
        threads_data = []
        thread_ids_seen = set()

        try:
            import google_tools as _gt
            _gmail_svc = _gt._get_gmail_service()
        except Exception:
            _gmail_svc = None

        for term in search_terms:
            if len(thread_ids_seen) >= max_threads_per_customer:
                break
            try:
                results = gmail_search(term, max_results=max_threads_per_customer * 3)
                if not results or "No results" in results:
                    continue

                for match in re.finditer(r"\[id:(\S+?)\]", results):
                    if len(thread_ids_seen) >= max_threads_per_customer:
                        break
                    mid = match.group(1)
                    tid = None
                    if _gmail_svc:
                        try:
                            msg_meta = _gmail_svc.users().messages().get(
                                userId="me", id=mid, format="metadata",
                            ).execute()
                            tid = msg_meta.get("threadId")
                        except Exception:
                            pass
                    if tid and tid not in thread_ids_seen:
                        thread_ids_seen.add(tid)
            except Exception as e:
                logger.warning("  Search failed for %s: %s", term, e)

        for tid in list(thread_ids_seen)[:max_threads_per_customer]:
            try:
                raw = gmail_get_thread(tid, max_messages=20)
                if not raw or len(raw) < 100:
                    continue
                turns = _parse_thread_messages(raw)
                if turns and len(turns) >= 2:
                    att_texts = _extract_thread_attachments(tid, _gmail_svc)
                    if att_texts:
                        logger.info("    Thread %s: %d attachments extracted", tid[:8], len(att_texts))
                        for turn in turns:
                            if _ATTACHMENT_SIGNALS.search(turn.text):
                                att_content = next(iter(att_texts.values()), "")
                                if att_content:
                                    turn.text += att_content
                                    turn.word_count = len(turn.text.split())

                    threads_data.append({
                        "thread_id": tid,
                        "turns": [asdict(t) for t in turns],
                        "turn_count": len(turns),
                    })
                    all_turns.extend(turns)
                    logger.info("    Thread %s: %d turns (%d rushabh, %d customer)",
                                tid[:8], len(turns),
                                sum(1 for t in turns if t.sender == "rushabh"),
                                sum(1 for t in turns if t.sender == "customer"))
            except Exception as e:
                logger.warning("  Thread %s failed: %s", tid[:8], e)

        if not all_turns:
            continue

        rushabh_msgs = [t.text for t in all_turns if t.sender == "rushabh"]
        customer_msgs = [t.text for t in all_turns if t.sender == "customer"]
        machines = list(set(re.findall(
            r"PF\d-[A-Z]{0,2}-?\d{4}|AM[P]?-\d{4}|IMG-\d{4}",
            " ".join(t.text for t in all_turns), re.IGNORECASE,
        )))

        interaction = CustomerInteraction(
            company=company,
            contact_name=seed.get("name", ""),
            contact_email=email,
            country=seed.get("country", ""),
            threads=threads_data,
            rushabh_messages=rushabh_msgs,
            customer_messages=customer_msgs,
            total_exchanges=len(all_turns),
            machines_discussed=machines,
            deal_stage=seed.get("deal_stage", ""),
        )

        interaction.style_notes = _analyze_style_per_customer(rushabh_msgs)
        interactions[company] = interaction

        logger.info("  %s: %d threads, %d Rushabh msgs, %d customer msgs, machines: %s",
                     company, len(threads_data), len(rushabh_msgs),
                     len(customer_msgs), machines)

    INTERACTION_MAP_FILE.write_text(json.dumps(
        {k: asdict(v) for k, v in interactions.items()}, indent=2, default=str,
    ))
    logger.info("Interaction map saved: %d customers, %s",
                len(interactions), INTERACTION_MAP_FILE)

    profile = _build_style_profile(interactions)
    STYLE_PROFILE_FILE.write_text(json.dumps(asdict(profile), indent=2))
    logger.info("Style profile saved: %d messages analyzed", profile.total_messages_analyzed)

    return interactions


def _load_customer_seeds() -> List[Dict]:
    """Load customer seeds from all available data sources."""
    seeds = []
    seen_companies = set()

    orders_file = PROJECT_ROOT / "data" / "knowledge" / "customer_orders.json"
    if orders_file.exists():
        try:
            data = json.loads(orders_file.read_text())
            for o in data.get("orders", []):
                company = o.get("customer", "")
                if company and company not in seen_companies:
                    seen_companies.add(company)
                    seeds.append({
                        "company": company,
                        "email": "",
                        "domain": _guess_domain(company),
                        "country": o.get("country", ""),
                        "deal_stage": "order",
                        "priority": 1,
                    })
        except Exception:
            pass

    eu_convos_file = PROJECT_ROOT / "data" / "european_lead_conversations.json"
    if eu_convos_file.exists():
        try:
            data = json.loads(eu_convos_file.read_text())
            for c in data.get("genuine_conversations", []):
                company = c.get("company", "")
                if company and company not in seen_companies:
                    seen_companies.add(company)
                    seeds.append({
                        "company": company,
                        "email": c.get("contact_email", ""),
                        "domain": "",
                        "country": c.get("country", ""),
                        "deal_stage": "conversation",
                        "priority": 2,
                    })
        except Exception:
            pass

    inquiry_file = PROJECT_ROOT / "data" / "training" / "inquiry_form_leads.json"
    if inquiry_file.exists():
        try:
            leads = json.loads(inquiry_file.read_text())
            for l in leads:
                company = l.get("company", l.get("Company Name", ""))
                email = l.get("email", l.get("Email", ""))
                if company and company not in seen_companies and email:
                    seen_companies.add(company)
                    domain = email.split("@")[-1] if "@" in email else ""
                    seeds.append({
                        "company": company,
                        "email": email,
                        "domain": domain,
                        "name": l.get("name", ""),
                        "country": "",
                        "deal_stage": "inquiry",
                        "priority": 3,
                    })
        except Exception:
            pass

    import sqlite3
    crm_path = PROJECT_ROOT / "crm" / "ira_crm.db"
    if crm_path.exists():
        try:
            conn = sqlite3.connect(str(crm_path))
            cur = conn.cursor()
            cur.execute("""
                SELECT email, name, company, country FROM contacts
                WHERE email NOT LIKE '%placeholder%' AND company IS NOT NULL AND company != ''
                ORDER BY company
            """)
            for row in cur.fetchall():
                company = row[2]
                if company and company not in seen_companies:
                    seen_companies.add(company)
                    seeds.append({
                        "company": company,
                        "email": row[0],
                        "domain": row[0].split("@")[-1] if "@" in row[0] else "",
                        "name": row[1] or "",
                        "country": row[3] or "",
                        "deal_stage": "contact",
                        "priority": 4,
                    })
            conn.close()
        except Exception:
            pass

    seeds.sort(key=lambda s: s.get("priority", 99))
    return seeds


def _guess_domain(company: str) -> str:
    """Guess email domain from company name."""
    clean = re.sub(r'\s*(pvt|ltd|gmbh|co\.?|inc|llc|fzco|s\.r\.l\.?|ab|ag)\s*\.?', '', company, flags=re.IGNORECASE)
    clean = re.sub(r'[^a-zA-Z0-9]', '', clean).lower()
    return clean[:20] if clean else ""


_ATTACHMENT_SIGNALS = re.compile(
    r"\bPFA\b|please find attach|attached (?:herewith|please|is|are|the)|"
    r"find enclosed|enclos(?:ed|ing)|see attach|attaching|attachment",
    re.IGNORECASE,
)

_EXTRACTABLE_MIMES = {
    "application/pdf", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword", "text/plain", "text/csv",
}


def _extract_thread_attachments(thread_id: str, gmail_service) -> Dict[str, str]:
    """Download and extract text from attachments in a thread.

    Returns dict mapping message_index to extracted text summary.
    """
    if not gmail_service:
        return {}

    try:
        thread = gmail_service.users().threads().get(
            userId="me", id=thread_id, format="metadata",
        ).execute()
    except Exception:
        return {}

    attachment_texts: Dict[str, str] = {}
    att_dir = str(DATA_DIR / "attachments")
    Path(att_dir).mkdir(parents=True, exist_ok=True)

    for msg in thread.get("messages", []):
        msg_id = msg["id"]
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        snippet = msg.get("snippet", "")

        has_signal = bool(_ATTACHMENT_SIGNALS.search(snippet))
        has_parts = _has_attachment_parts(msg.get("payload", {}))

        if not (has_signal or has_parts):
            continue

        try:
            from google_tools import gmail_get_attachments
            attachments = gmail_get_attachments(msg_id, download_dir=att_dir)
        except Exception as e:
            logger.debug("Attachment download failed for %s: %s", msg_id[:8], e)
            continue

        for att in attachments:
            mime = att.get("mime_type", "")
            path = att.get("path", "")
            filename = att.get("filename", "")

            if not path or not Path(path).exists():
                continue

            extracted = ""
            try:
                if "pdf" in mime.lower():
                    from openclaw.agents.ira.src.brain.document_extractor import extract_pdf
                    extracted = extract_pdf(path)
                elif "spreadsheet" in mime.lower() or "excel" in mime.lower() or filename.endswith((".xlsx", ".xls")):
                    from openclaw.agents.ira.src.brain.document_extractor import extract_document
                    extracted = extract_document(path)
                elif "word" in mime.lower() or filename.endswith((".docx", ".doc")):
                    from openclaw.agents.ira.src.brain.document_extractor import extract_document
                    extracted = extract_document(path)
                elif "text" in mime.lower() or filename.endswith((".txt", ".csv")):
                    extracted = Path(path).read_text(errors="ignore")[:5000]
            except Exception as e:
                logger.debug("Extraction failed for %s: %s", filename, e)
                continue

            if extracted and len(extracted.strip()) > 20:
                truncated = extracted[:3000]
                attachment_texts[msg_id] = (
                    f"\n[ATTACHMENT: {filename}]\n{truncated}\n[/ATTACHMENT]"
                )
                logger.info("    Extracted attachment: %s (%d chars)", filename, len(truncated))

    return attachment_texts


def _has_attachment_parts(payload: Dict) -> bool:
    """Check if a message payload has downloadable attachment parts."""
    for part in payload.get("parts", []):
        if part.get("filename") and part.get("body", {}).get("attachmentId"):
            return True
        if "parts" in part and _has_attachment_parts(part):
            return True
    return False


def _parse_thread_messages(raw: str) -> List[EmailTurn]:
    """Parse a full gmail_get_thread output into ordered turns.

    Top-level messages have From: immediately followed by Date: on the
    next line. Quoted messages inside bodies also have From: but are NOT
    followed by Date:. We split only on the real message boundaries.
    """
    if not raw or len(raw) < 100:
        return []

    boundary = re.compile(r"^From:\s+(.+)\nDate:\s+(.+)", re.MULTILINE)
    matches = list(boundary.finditer(raw))
    if not matches:
        return []

    turns: List[EmailTurn] = []
    for idx, match in enumerate(matches):
        from_raw = match.group(1).strip()
        date_raw = match.group(2).strip()

        msg_start = match.end()
        msg_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw)
        body_raw = raw[msg_start:msg_end]

        subj_match = re.search(r"^Subject:\s*(.+?)$", body_raw, re.MULTILINE)

        first_blank = body_raw.find("\n\n")
        separator = re.search(r"\n-{20,}\n", body_raw)
        body_start = max(first_blank, separator.end() if separator and separator.start() < 200 else -1)
        body = body_raw[body_start:].strip() if body_start > 0 else body_raw.strip()

        body = re.sub(r"----+\s*Original message\s*----+.*", "", body, flags=re.DOTALL | re.IGNORECASE)
        body = re.sub(r"\nOn .{10,100} wrote:\s*\n.*", "", body, flags=re.DOTALL)
        body = re.sub(r"\[cid:\S+\]", "", body)
        body = re.sub(r"\[https?://\S+?\]", "", body)
        body = re.sub(r"<https?://\S+?>", "", body)
        body = re.sub(r"\n{3,}", "\n\n", body)

        body = body.strip()
        if len(body) < 10:
            continue
        body = body[:2000]

        from_email = ""
        em = re.search(r"[\w.+-]+@[\w.-]+", from_raw)
        if em:
            from_email = em.group(0).lower()

        is_rushabh = from_email in RUSHABH_ALIASES or "rushabh" in from_raw.lower()

        turns.append(EmailTurn(
            sender="rushabh" if is_rushabh else "customer",
            text=body,
            subject=subj_match.group(1).strip() if subj_match else "",
            timestamp=date_raw,
            word_count=len(body.split()),
        ))

    return turns


def _parse_single_message(raw: str) -> Optional[EmailTurn]:
    """Parse a single gmail_read_message output into an EmailTurn."""
    if not raw or len(raw) < 50:
        return None

    from_match = re.search(r"From:\s*(.+?)(?:\n|$)", raw)
    subj_match = re.search(r"Subject:\s*(.+?)(?:\n|$)", raw)
    date_match = re.search(r"Date:\s*(.+?)(?:\n|$)", raw)
    if not from_match:
        return None

    from_raw = from_match.group(1).strip()
    from_email = ""
    em = re.search(r"[\w.+-]+@[\w.-]+", from_raw)
    if em:
        from_email = em.group(0).lower()

    labels_match = re.search(r"Labels:\s*(.+?)(?:\n|$)", raw)
    header_end = 0
    for hdr in ["Labels:", "Date:", "CC:", "BCC:", "To:", "Subject:", "From:"]:
        idx = raw.find(hdr)
        if idx >= 0:
            line_end = raw.find("\n", idx)
            if line_end > header_end:
                header_end = line_end

    body = raw[header_end:].strip()[:3000] if header_end > 0 else raw[200:].strip()[:3000]

    is_rushabh = from_email in RUSHABH_ALIASES or "rushabh" in from_raw.lower()

    return EmailTurn(
        sender="rushabh" if is_rushabh else "customer",
        text=body,
        subject=subj_match.group(1).strip() if subj_match else "",
        timestamp=date_match.group(1).strip() if date_match else "",
        word_count=len(body.split()),
    )


def _parse_thread_turns(raw: str) -> List[EmailTurn]:
    """Parse raw gmail_get_thread output into turns."""
    if not raw or len(raw) < 50:
        return []

    messages = re.split(r"(?:^|\n)---+\s*Message\s*\d+", raw)
    if len(messages) < 2:
        messages = re.split(r"\n(?=From:)", raw)

    turns = []
    for block in messages:
        if len(block.strip()) < 20:
            continue

        from_match = re.search(r"From:\s*(.+?)(?:\n|$)", block)
        subj_match = re.search(r"Subject:\s*(.+?)(?:\n|$)", block)
        date_match = re.search(r"Date:\s*(.+?)(?:\n|$)", block)
        if not from_match:
            continue

        from_raw = from_match.group(1).strip()
        from_email = ""
        em = re.search(r"[\w.+-]+@[\w.-]+", from_raw)
        if em:
            from_email = em.group(0).lower()

        body_start = max(block.find("\n\n"), block.find("\nBody:"))
        body = block[body_start:].strip() if body_start > 0 else block
        body = re.sub(r"^Body:\s*", "", body)[:3000]

        is_rushabh = from_email in RUSHABH_ALIASES or "rushabh" in from_raw.lower()

        turns.append(EmailTurn(
            sender="rushabh" if is_rushabh else "customer",
            text=body,
            subject=subj_match.group(1).strip() if subj_match else "",
            timestamp=date_match.group(1).strip() if date_match else "",
            word_count=len(body.split()),
        ))

    return turns


def _analyze_style_per_customer(rushabh_msgs: List[str]) -> Dict:
    """Analyze Rushabh's style in messages to a specific customer."""
    if not rushabh_msgs:
        return {}

    word_counts = [len(m.split()) for m in rushabh_msgs]
    greetings = {}
    closers = {}

    for msg in rushabh_msgs:
        first_line = msg.strip().split("\n")[0].strip()
        for g in ["Hi!", "Hi ", "Hey", "Hello", "Dear"]:
            if first_line.startswith(g):
                greetings[g] = greetings.get(g, 0) + 1
                break

        last_lines = msg.strip().split("\n")[-3:]
        last_text = " ".join(last_lines).lower()
        for c in ["let me know", "questions?", "make sense?", "best,", "regards,", "thanks,"]:
            if c in last_text:
                closers[c] = closers.get(c, 0) + 1

    return {
        "avg_words": round(sum(word_counts) / len(word_counts), 1) if word_counts else 0,
        "min_words": min(word_counts) if word_counts else 0,
        "max_words": max(word_counts) if word_counts else 0,
        "msg_count": len(rushabh_msgs),
        "greetings": greetings,
        "closers": closers,
    }


def _build_style_profile(interactions: Dict[str, CustomerInteraction]) -> RushabhStyleProfile:
    """Build aggregate style profile from all interactions."""
    all_msgs = []
    all_word_counts = []
    greetings: Dict[str, int] = {}
    closers: Dict[str, int] = {}
    per_customer = {}

    for company, interaction in interactions.items():
        for msg in interaction.rushabh_messages:
            all_msgs.append(msg)
            all_word_counts.append(len(msg.split()))

        if interaction.style_notes:
            for g, count in interaction.style_notes.get("greetings", {}).items():
                greetings[g] = greetings.get(g, 0) + count
            for c, count in interaction.style_notes.get("closers", {}).items():
                closers[c] = closers.get(c, 0) + count
            per_customer[company] = interaction.style_notes

    common_phrases = _extract_common_phrases(all_msgs)

    sorted_wc = sorted(all_word_counts) if all_word_counts else [0]
    median_wc = sorted_wc[len(sorted_wc) // 2]

    sample_replies = []
    for company, interaction in interactions.items():
        for i, thread in enumerate(interaction.threads[:2]):
            turns = thread.get("turns", [])
            for j, turn in enumerate(turns):
                if turn.get("sender") == "customer" and j + 1 < len(turns):
                    next_turn = turns[j + 1]
                    if next_turn.get("sender") == "rushabh":
                        sample_replies.append({
                            "company": company,
                            "customer_said": turn["text"][:500],
                            "rushabh_replied": next_turn["text"][:500],
                        })
                        if len(sample_replies) >= 30:
                            break

    return RushabhStyleProfile(
        avg_word_count=round(sum(all_word_counts) / len(all_word_counts), 1) if all_word_counts else 0,
        median_word_count=float(median_wc),
        greeting_distribution=greetings,
        closer_distribution=closers,
        common_phrases=common_phrases[:30],
        action_phrases=[p for p in common_phrases if any(a in p.lower() for a in ["let me", "i'll", "let's", "i will", "shall"])],
        tone_markers={
            "uses_exclamation": sum(1 for m in all_msgs if "!" in m[:50]) / max(len(all_msgs), 1),
            "uses_emoji": sum(1 for m in all_msgs if re.search(r"[\U0001F600-\U0001F64F]", m)) / max(len(all_msgs), 1),
            "starts_with_hi": sum(1 for m in all_msgs if m.strip().lower().startswith("hi")) / max(len(all_msgs), 1),
            "ends_with_question": sum(1 for m in all_msgs if m.strip().endswith("?")) / max(len(all_msgs), 1),
        },
        per_customer_style=per_customer,
        sample_replies=sample_replies[:30],
        total_messages_analyzed=len(all_msgs),
        built_at=datetime.now().isoformat(),
    )


def _extract_common_phrases(messages: List[str], min_count: int = 2) -> List[str]:
    """Extract phrases Rushabh uses repeatedly."""
    phrase_counts: Dict[str, int] = {}

    for msg in messages:
        sentences = re.split(r'[.!?\n]', msg)
        for sent in sentences:
            sent = sent.strip()
            if 3 <= len(sent.split()) <= 12:
                normalized = sent.lower().strip()
                phrase_counts[normalized] = phrase_counts.get(normalized, 0) + 1

    repeated = [(phrase, count) for phrase, count in phrase_counts.items() if count >= min_count]
    repeated.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in repeated[:50]]


# =============================================================================
# 2. SIMULATE — Run customer personas through Ira, measure delta
# =============================================================================

INTENT_DIMS = [
    "right_questions", "right_machine", "right_next_step",
    "objection_handling", "deal_awareness", "customer_context",
    "strategic_intent",
]

SALES_STAGES = ["discovery", "technical", "negotiation", "objection", "closing"]

INDUSTRIES = [
    "automotive interior trim", "packaging (food trays)", "medical device housings",
    "EV battery enclosures", "refrigerator liners", "luggage shells",
    "construction panels", "spa/bathtub shells", "aerospace components",
    "agricultural equipment covers",
]

COUNTRIES = ["Germany", "India", "UAE", "USA", "Brazil", "Japan", "Italy", "Turkey", "Mexico", "Russia"]


def _generate_customer_message(
    stage: str, industry: str, country: str, company: str,
    conversation_history: str, turn_number: int,
) -> str:
    """Generate a unique customer message using GPT-4o. Different every run."""
    import openai
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

    stage_instructions = {
        "discovery": "You're making first contact. Describe your application, material, and rough size needs. Ask what machine they'd recommend.",
        "technical": "You've seen a proposal. Ask detailed technical questions: servo vs pneumatic, heater types, cycle times, depth capability.",
        "negotiation": "You've received a quote. The price is higher than expected. Push back, ask about payment terms, mention budget.",
        "objection": "You have concerns: lead time too long, competitor offered faster, worried about support in your country.",
        "closing": "Almost ready to order. Ask about installation, training, warranty, payment schedule. Push for final confirmation.",
    }

    intel_context = _load_random_intelligence()

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": (
                f"You are a real industrial buyer at {company} ({country}), {industry} industry.\n"
                f"B2B sales conversation with Machinecraft Technologies (thermoforming machines).\n\n"
                f"STAGE: {stage}\nINSTRUCTION: {stage_instructions.get(stage, 'Continue naturally.')}\n\n"
                f"Write ONE realistic customer message. Be specific — dimensions in mm, materials "
                f"(ABS, HDPE, PP, TPO), production volumes. Sound like a real buyer.\n"
                f"Keep it 2-5 sentences. Use 'Dear Rushabh' or 'Hi Rushabh' as greeting.\n\n"
                f"CONTEXT FROM REAL DEALS:\n{intel_context[:800]}"
            )},
            {"role": "user", "content": (
                f"Turn {turn_number}. Previous:\n{conversation_history[-600:]}\nWrite customer's next message."
                if conversation_history else f"Turn 1. Write the customer's opening inquiry."
            )},
        ],
        max_tokens=250, temperature=0.8,
    )
    return resp.choices[0].message.content.strip()


def _load_random_intelligence() -> str:
    """Load a random conversation intelligence file for context."""
    import random
    intel_dir = DATA_DIR / "conversation_intelligence"
    if not intel_dir.exists():
        return ""
    files = list(intel_dir.glob("*.json"))
    if not files:
        return ""
    try:
        data = json.loads(random.choice(files).read_text())
        parts = []
        for stage in data.get("conversation_stages", [])[:2]:
            if stage.get("customer_questions"):
                parts.append(f"Real questions: {stage['customer_questions'][:2]}")
            if stage.get("rushabh_moves"):
                parts.append(f"Rushabh moves: {stage['rushabh_moves'][:2]}")
        return "\n".join(parts)
    except Exception:
        return ""


def _ask_what_would_rushabh_do(
    customer_message: str, stage: str, conversation_history: str,
) -> Tuple[str, str]:
    """Ask GPT-4o what Rushabh would do, using playbook as few-shot examples."""
    import openai
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

    playbook_examples = _get_relevant_playbook_examples(customer_message, stage)

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": (
                "You are the Sales Director of Machinecraft Technologies.\n"
                "Based on your REAL email patterns, write what you would reply.\n\n"
                "YOUR PATTERNS:\n" + playbook_examples + "\n\n"
                "RULES: SHORT (10-30 words), start with Hi!/Hey/Dear, end with next step, use :) occasionally.\n"
                "Output JSON: {\"intent\": \"strategic goal\", \"message\": \"your reply\"}"
            )},
            {"role": "user", "content": (
                f"Stage: {stage}\nConversation:\n{conversation_history[-500:]}\n\n"
                f"Customer: {customer_message[:400]}\nWhat would you reply?"
            )},
        ],
        max_tokens=200, temperature=0.3,
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        data = json.loads(raw)
        return data.get("intent", ""), data.get("message", "")
    except Exception:
        return "advance the sale", raw


def _get_relevant_playbook_examples(customer_message: str, stage: str) -> str:
    """Get playbook examples relevant to the current situation."""
    playbook_file = DATA_DIR / "rushabh_playbook.json"
    if not playbook_file.exists():
        return "(no playbook)"
    try:
        playbook = json.loads(playbook_file.read_text())
    except Exception:
        return "(no playbook)"

    stage_map = {
        "discovery": ["general", "technical"],
        "technical": ["technical", "general"],
        "negotiation": ["price_negotiation", "objection"],
        "objection": ["objection", "price_negotiation", "timeline"],
        "closing": ["closing", "next_step", "scheduling"],
    }
    relevant = [p for p in playbook if p["situation"] in stage_map.get(stage, ["general"])]
    if not relevant:
        relevant = playbook[:5]
    lines = []
    for p in relevant[:4]:
        lines.append(f"Customer: \"{p['customer'][:120]}\"")
        lines.append(f"Rushabh ({p['rushabh_word_count']}w): \"{p['rushabh'][:120]}\"")
        if p.get("anti_pattern"):
            lines.append(f"  AVOID: {p['anti_pattern'][:100]}")
        lines.append("")
    return "\n".join(lines)


INTENT_SCORE_PROMPT = """Score sales AI (Ira) vs Rushabh on INTENT. 0-10 each.
1. right_questions: Asked right qualifying questions?
2. right_machine: Recommended correct specific model?
3. right_next_step: Proposed concrete next step?
4. objection_handling: Handled concern like Rushabh?
5. deal_awareness: Understands deal stage?
6. customer_context: References customer situation?
7. strategic_intent: Overall intent aligned?

STAGE: {stage}  CUSTOMER: {customer}
RUSHABH INTENT: {rushabh_intent}  RUSHABH SAYS: {rushabh_message}
IRA SAYS: {ira}

JSON: {{"right_questions":N,"right_machine":N,"right_next_step":N,"objection_handling":N,"deal_awareness":N,"customer_context":N,"strategic_intent":N,"reasoning":"2-3 sentences"}}"""


def _score_intent(customer_msg, rushabh_intent, rushabh_message, ira_response, stage):
    raw = ""
    try:
        import openai
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a scoring judge. Output ONLY valid JSON, no prose."},
                {"role": "user", "content": INTENT_SCORE_PROMPT.format(
                    stage=stage, customer=customer_msg[:500],
                    rushabh_intent=rushabh_intent[:250], rushabh_message=rushabh_message[:250],
                    ira=ira_response[:500],
                )},
            ],
            max_tokens=500, temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        data = json.loads(raw)
        if "Ira" in data and isinstance(data["Ira"], dict):
            data = data["Ira"]
        elif not any(k in data for k in INTENT_DIMS):
            for v in data.values():
                if isinstance(v, dict) and any(k in v for k in INTENT_DIMS):
                    data = v
                    break
        reasoning = str(data.pop("reasoning", ""))
        scores = {k: float(v) for k, v in data.items() if k in INTENT_DIMS}
        if scores:
            return scores, reasoning
    except Exception:
        pass

    scores = {}
    for dim in INTENT_DIMS:
        m = re.search(rf'"{dim}"\s*:\s*(\d+(?:\.\d+)?)', raw)
        if m:
            scores[dim] = float(m.group(1))
    if scores:
        return scores, "regex parse"
    return {d: 5.0 for d in INTENT_DIMS}, f"parse failed: {raw[:100]}"


def _auto_learn_from_failures(results):
    """Extract failures below 5/10 and add to playbook automatically."""
    playbook_file = DATA_DIR / "rushabh_playbook.json"
    try:
        playbook = json.loads(playbook_file.read_text()) if playbook_file.exists() else []
    except Exception:
        playbook = []

    new_entries = 0
    stage_to_situation = {
        "discovery": "technical", "technical": "technical",
        "negotiation": "price_negotiation", "objection": "objection", "closing": "closing",
    }
    for r in results:
        avg = sum(r["scores"].values()) / len(r["scores"]) if r["scores"] else 10
        if avg >= 5.0:
            continue
        playbook.append({
            "situation": stage_to_situation.get(r.get("stage", ""), "general"),
            "thread": f"delphi_auto_r{r.get('round', '?')}",
            "customer": r.get("customer_message", "")[:300],
            "rushabh": r.get("rushabh_message", "")[:300],
            "rushabh_word_count": len(r.get("rushabh_message", "").split()),
            "anti_pattern": f"Ira scored {avg:.1f}/10. {r.get('reasoning', '')[:150]}",
        })
        new_entries += 1

    if new_entries:
        playbook_file.write_text(json.dumps(playbook, indent=2))
        logger.info("[Delphi] Auto-learned %d entries from failures", new_entries)
    return new_entries


async def run_shadow_simulation(
    num_conversations: int = 5,
    turns_per_conversation: int = 3,
    stream_telegram: bool = True,
) -> Dict:
    """Dynamic shadow simulation — unique conversations every run.

    1. GPT-4o generates unique customer messages (different every time)
    2. Ira responds via full pipeline
    3. "What would Rushabh do?" oracle provides comparison
    4. Scored on 7 intent dimensions
    5. Failures auto-added to playbook
    """
    import random
    from openclaw.agents.ira.src.core.tool_orchestrator import process_with_tools

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    prev_report = {}
    if DELTA_REPORT_FILE.exists():
        try:
            prev_report = json.loads(DELTA_REPORT_FILE.read_text())
        except Exception:
            pass
    prev_overall = prev_report.get("overall_intent_alignment",
                                    prev_report.get("overall_alignment", 0))
    round_num = prev_report.get("round", 0) + 1

    if stream_telegram:
        _send_telegram(
            f"\U0001F52E DELPHI ROUND {round_num}\n" + "\u2501" * 35 +
            f"\nPrevious: {prev_overall}/10\n"
            f"{num_conversations} unique conversations x {turns_per_conversation} turns\n"
            f"Every conversation is NEW"
        )

    all_results = []
    turn_count = 0

    for conv_idx in range(num_conversations):
        stage = random.choice(SALES_STAGES)
        industry = random.choice(INDUSTRIES)
        country = random.choice(COUNTRIES)
        prefixes = ["Alpha", "Beta", "Nova", "Prime", "Apex", "Global", "Euro", "Pacific"]
        suffixes = {"Germany": "GmbH", "Japan": "Corp", "India": "Ltd", "Italy": "S.r.l."}
        company = f"{random.choice(prefixes)} {industry.split('(')[0].strip().split()[-1].title()} {suffixes.get(country, 'Inc')}"

        conversation_history = ""

        for turn_idx in range(turns_per_conversation):
            turn_count += 1

            customer_msg = _generate_customer_message(
                stage, industry, country, company, conversation_history, turn_idx + 1,
            )

            t0 = time.time()
            try:
                ira_response = await process_with_tools(
                    message=customer_msg, channel="shadow_training",
                    user_id=f"delphi_r{round_num}_{conv_idx}",
                    context={"is_internal": True, "conversation_history": conversation_history},
                )
            except Exception as e:
                ira_response = f"(ERROR: {e})"
            latency = time.time() - t0

            rushabh_intent, rushabh_message = _ask_what_would_rushabh_do(
                customer_msg, stage, conversation_history,
            )

            scores, reasoning = _score_intent(
                customer_msg, rushabh_intent, rushabh_message, ira_response or "", stage,
            )

            result = {
                "round": round_num, "conversation": conv_idx + 1, "turn": turn_count,
                "stage": stage, "company": company, "country": country, "industry": industry,
                "customer_message": customer_msg[:1000],
                "ira_response": (ira_response or "")[:1000],
                "rushabh_intent": rushabh_intent[:500],
                "rushabh_message": rushabh_message[:500],
                "scores": scores, "reasoning": reasoning, "latency_s": round(latency, 1),
            }
            all_results.append(result)

            with open(SIMULATION_LOG_FILE, "a") as f:
                f.write(json.dumps(result, default=str) + "\n")

            if stream_telegram:
                avg = sum(scores.values()) / len(scores) if scores else 0
                bar = "\u2588" * int(avg) + "\u2591" * (10 - int(avg))
                weak = [k for k, v in sorted(scores.items(), key=lambda x: x[1]) if v < 6]
                _send_telegram(
                    f"Turn {turn_count} | {stage}/{company}\n"
                    f"Customer: {customer_msg[:120]}\n\n"
                    f"Rushabh would: {rushabh_message[:120]}\n\n"
                    f"Ira: {(ira_response or '')[:120]}\n\n"
                    f"{avg:.1f}/10 {bar}" +
                    (f"\nGaps: {', '.join(weak[:3])}" if weak else "") +
                    (f"\n{reasoning[:100]}" if reasoning else "")
                )

            conversation_history += f"\nCustomer: {customer_msg[:250]}\nIra: {(ira_response or '')[:250]}\n"

            stage_progression = {
                "discovery": "technical", "technical": "negotiation",
                "negotiation": "objection", "objection": "closing", "closing": "closing",
            }
            stage = stage_progression.get(stage, stage)
            await asyncio.sleep(1)

    new_learned = _auto_learn_from_failures(all_results)

    report = _build_delta_report(all_results, round_num, prev_report)
    DELTA_REPORT_FILE.write_text(json.dumps(report, indent=2))

    if stream_telegram:
        _stream_report_telegram(report, prev_report, new_learned)

    return report


def _build_delta_report(results, round_num, prev_report):
    dim_scores = {d: [] for d in INTENT_DIMS}
    for r in results:
        for d in INTENT_DIMS:
            if d in r.get("scores", {}):
                dim_scores[d].append(r["scores"][d])

    avg_scores = {d: round(sum(s)/len(s), 2) if s else 0 for d, s in dim_scores.items()}
    overall = round(sum(avg_scores.values()) / len(avg_scores), 2) if avg_scores else 0

    prev_scores = prev_report.get("dimension_scores", {})
    prev_overall = prev_report.get("overall_intent_alignment",
                                    prev_report.get("overall_alignment", 0))

    gap_formula = {}
    for d, score in avg_scores.items():
        gap = round(10.0 - score, 2)
        gap_formula[d] = {
            "score": score, "gap": gap, "weight": round(gap / 10.0, 3),
            "priority": "critical" if score < 5 else "high" if score < 7 else "medium" if score < 8.5 else "low",
            "delta_from_prev": round(score - prev_scores.get(d, 0), 2),
        }

    return {
        "timestamp": datetime.now().isoformat(), "round": round_num,
        "total_turns": len(results), "overall_intent_alignment": overall,
        "dimension_scores": avg_scores, "gap_formula": gap_formula,
        "previous_overall": prev_overall, "improvement": round(overall - prev_overall, 2),
    }




def _stream_report_telegram(report: Dict, prev_report: Dict = None, new_learned: int = 0):
    overall = report.get("overall_intent_alignment", report.get("overall_alignment", 0))
    prev_overall = (prev_report or {}).get("overall_intent_alignment",
                                           (prev_report or {}).get("overall_alignment", 0))
    prev_scores = (prev_report or {}).get("dimension_scores", {})
    imp = round(overall - prev_overall, 2) if prev_overall else 0
    arrow = "\u2B06" if imp > 0 else "\u2B07" if imp < 0 else "\u27A1"
    round_num = report.get("round", "?")

    bar = "\u2588" * int(overall) + "\u2591" * (10 - int(overall))
    msg = (
        f"\U0001F4CA ROUND {round_num} RESULTS\n" + "\u2501" * 35 + "\n\n"
        f"Overall: {prev_overall} \u2192 {overall} ({arrow} {imp:+.2f})\n"
        f"Turns: {report['total_turns']} | Playbook: +{new_learned} entries\n\n"
    )
    for d, s in sorted(report["dimension_scores"].items(), key=lambda x: x[1]):
        old = prev_scores.get(d, 0)
        delta = round(s - old, 1)
        icon = "\U0001F534" if s < 5 else "\U0001F7E1" if s < 7 else "\U0001F7E2"
        msg += f"  {icon} {d}: {s}/10 ({delta:+.1f})\n"
    msg += f"\n\U0001F9EE Delphi inner voice recalibrated"
    _send_telegram(msg)


def _send_telegram(text: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("EXPECTED_CHAT_ID", "")
    if not token or not chat_id:
        return
    import requests
    if len(text) > 4000:
        text = text[:3950] + "\n... [truncated]"
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text}, timeout=15,
        )
    except Exception:
        pass


# =============================================================================
# 3. CONSULT — Live voice agent: "How would Rushabh reply?"
# =============================================================================

_delphi_instance = None

class Delphi:
    """The inner voice — Rushabh's Oracle."""

    def __init__(self):
        self.style_profile: Optional[RushabhStyleProfile] = None
        self.interaction_map: Dict = {}
        self._load()

    def _load(self):
        if STYLE_PROFILE_FILE.exists():
            try:
                data = json.loads(STYLE_PROFILE_FILE.read_text())
                self.style_profile = RushabhStyleProfile(**{
                    k: v for k, v in data.items()
                    if k in RushabhStyleProfile.__dataclass_fields__
                })
            except Exception as e:
                logger.warning("Echo: failed to load style profile: %s", e)

        if INTERACTION_MAP_FILE.exists():
            try:
                self.interaction_map = json.loads(INTERACTION_MAP_FILE.read_text())
            except Exception:
                pass

    @property
    def is_trained(self) -> bool:
        return self.style_profile is not None and self.style_profile.total_messages_analyzed > 0

    async def consult(
        self,
        customer_message: str,
        company: str = "",
        context: str = "",
    ) -> str:
        """Ask Echo: how would Rushabh reply to this?

        Returns a Rushabh-style draft that Ira can use as guidance.
        """
        if not self.is_trained:
            return ""

        profile = self.style_profile
        customer_style = profile.per_customer_style.get(company, {})

        similar_replies = self._find_similar_replies(customer_message, company)

        system_prompt = self._build_voice_prompt(profile, customer_style, similar_replies)

        try:
            import openai
            client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

            user_content = f"Customer message: {customer_message[:1500]}"
            if context:
                user_content += f"\n\nConversation context: {context[:500]}"
            if company:
                user_content += f"\n\nCompany: {company}"

            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=300,
                temperature=0.3,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.warning("Echo consult failed: %s", e)
            return ""

    def _build_voice_prompt(
        self,
        profile: RushabhStyleProfile,
        customer_style: Dict,
        similar_replies: List[Dict],
    ) -> str:
        parts = [
            "You are channeling the Sales Director of Machinecraft Technologies.",
            "Write EXACTLY as Rushabh would — not as a polished AI. Match his real patterns:",
            "",
            f"WORD COUNT: Rushabh averages {profile.avg_word_count:.0f} words (median {profile.median_word_count:.0f}). Be CONCISE.",
        ]

        if profile.greeting_distribution:
            top_greetings = sorted(profile.greeting_distribution.items(), key=lambda x: x[1], reverse=True)[:3]
            parts.append(f"GREETINGS: {', '.join(f'{g} ({c}x)' for g, c in top_greetings)}")

        if profile.closer_distribution:
            top_closers = sorted(profile.closer_distribution.items(), key=lambda x: x[1], reverse=True)[:3]
            parts.append(f"CLOSERS: {', '.join(f'{c} ({n}x)' for c, n in top_closers)}")

        if profile.common_phrases:
            parts.append(f"PHRASES HE USES: {'; '.join(profile.common_phrases[:10])}")

        tone = profile.tone_markers
        if tone.get("starts_with_hi", 0) > 0.5:
            parts.append("ALWAYS starts with 'Hi!' or 'Hey'")
        if tone.get("uses_exclamation", 0) > 0.3:
            parts.append("Uses exclamation marks in greetings (warm, not excessive)")

        if customer_style:
            parts.append(f"\nWITH THIS CUSTOMER: avg {customer_style.get('avg_words', '?')} words, "
                         f"{customer_style.get('msg_count', '?')} past messages")

        if similar_replies:
            parts.append("\nEXAMPLES OF RUSHABH'S ACTUAL REPLIES TO SIMILAR MESSAGES:")
            for sr in similar_replies[:3]:
                parts.append(f"  Customer: {sr['customer_said'][:200]}")
                parts.append(f"  Rushabh:  {sr['rushabh_replied'][:200]}")
                parts.append("")

        parts.append("\nRULES: Be Rushabh. Short. Warm. Direct. Action-oriented. No corporate fluff.")
        return "\n".join(parts)

    def _find_similar_replies(self, message: str, company: str) -> List[Dict]:
        """Find Rushabh's replies to similar customer messages."""
        if not self.style_profile or not self.style_profile.sample_replies:
            return []

        msg_lower = message.lower()
        keywords = set(re.findall(r'\b\w{4,}\b', msg_lower))

        scored = []
        for sr in self.style_profile.sample_replies:
            reply_keywords = set(re.findall(r'\b\w{4,}\b', sr["customer_said"].lower()))
            overlap = len(keywords & reply_keywords)
            company_bonus = 2 if sr.get("company", "") == company else 0
            scored.append((overlap + company_bonus, sr))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [sr for _, sr in scored[:5] if _ > 0]

    def get_style_summary(self) -> str:
        """Return a human-readable summary of Rushabh's style."""
        if not self.is_trained:
            return "Echo is not trained yet. Run build_interaction_map() first."

        p = self.style_profile
        lines = [
            f"Rushabh's Communication Style (from {p.total_messages_analyzed} emails):",
            f"  Average length: {p.avg_word_count:.0f} words (median {p.median_word_count:.0f})",
        ]
        if p.greeting_distribution:
            top = sorted(p.greeting_distribution.items(), key=lambda x: x[1], reverse=True)[:3]
            lines.append(f"  Top greetings: {', '.join(f'{g} ({c}x)' for g, c in top)}")
        if p.closer_distribution:
            top = sorted(p.closer_distribution.items(), key=lambda x: x[1], reverse=True)[:3]
            lines.append(f"  Top closers: {', '.join(f'{c} ({n}x)' for c, n in top)}")
        if p.common_phrases:
            lines.append(f"  Signature phrases: {'; '.join(p.common_phrases[:5])}")
        lines.append(f"  Customers profiled: {len(p.per_customer_style)}")
        return "\n".join(lines)


def get_delphi() -> Delphi:
    global _delphi_instance
    if _delphi_instance is None:
        _delphi_instance = Delphi()
    return _delphi_instance


# Keep backward compat
def get_echo() -> Delphi:
    return get_delphi()


async def consult_rushabh_voice(
    customer_message: str,
    company: str = "",
    context: str = "",
) -> str:
    """Convenience function: ask Delphi how Rushabh would reply."""
    return await get_delphi().consult(customer_message, company, context)


def get_delphi_guidance() -> str:
    """Generate system prompt injection — Delphi's inner voice.

    Reads the style profile and delta report directly from JSON files.
    Returns empty string if no training data exists yet.
    """
    if not STYLE_PROFILE_FILE.exists():
        return ""

    try:
        profile = json.loads(STYLE_PROFILE_FILE.read_text())
    except Exception:
        return ""

    total = profile.get("total_messages_analyzed") or profile.get("total_messages") or 0
    if not total:
        return ""

    avg_words = profile.get("avg_word_count") or profile.get("avg_words") or 50
    median_words = profile.get("median_word_count") or profile.get("median_words") or 20
    greetings = profile.get("greeting_distribution") or profile.get("greetings") or {}
    closers = profile.get("closer_distribution") or profile.get("closers") or {}
    tone = profile.get("tone_markers") or profile.get("tone") or {}

    lines = [
        "",
        "═══════════════════════════════════════════════════",
        "DELPHI — RUSHABH'S INNER VOICE (learned from real emails)",
        "═══════════════════════════════════════════════════",
        "You are channeling the founder's communication style.",
        f"These patterns come from analyzing {total} of his actual customer emails.",
        "",
        f"LENGTH: Rushabh averages {avg_words:.0f} words (median {median_words}). Keep responses SHORT.",
    ]

    if greetings:
        top = sorted(greetings.items(), key=lambda x: x[1], reverse=True)[:4]
        lines.append(f"GREETINGS: {', '.join(f'{g.strip()!r} ({c}x)' for g, c in top)}. Match this.")

    if closers:
        top = sorted(closers.items(), key=lambda x: x[1], reverse=True)[:4]
        lines.append(f"CLOSERS: {', '.join(f'{c!r} ({n}x)' for c, n in top)}.")

    warmth_ratio = tone.get("uses_emoji_or_exclamation") or tone.get("uses_exclamation") or 0
    if warmth_ratio > 0.15:
        lines.append(f"WARMTH: Rushabh uses :) and ! in {warmth_ratio:.0%} of messages. Be warm.")
    question_ratio = tone.get("ends_with_question", 0)
    if question_ratio > 0.2:
        lines.append(f"ENGAGEMENT: {question_ratio:.0%} of Rushabh's messages end with a question. Ask questions.")

    if DELTA_REPORT_FILE.exists():
        try:
            delta = json.loads(DELTA_REPORT_FILE.read_text())
            gap = delta.get("gap_formula", {})
            overall = delta.get("overall_intent_alignment", delta.get("overall_alignment", 0))
            weak_dims = [(d, info) for d, info in gap.items()
                         if info.get("priority") in ("critical", "high")]
            if weak_dims:
                lines.append("")
                lines.append(f"⚠️ KNOWN GAPS (shadow training: {overall}/10 overall — fix these):")
                _gap_advice = {
                    # Intent-based dimensions
                    "right_questions": "Ask the RIGHT qualifying questions: What's the application? Material & thickness? Sheet size? Max depth? Budget? Rushabh always qualifies before recommending.",
                    "right_machine": "Recommend the SPECIFIC correct machine model (e.g. PF1-C-2015, not 'PF1 series'). Check thickness→AM vs PF1 routing. Include price.",
                    "right_next_step": "Propose the EXACT next step Rushabh would: 'Let me send you the offer' / 'Can we do a web call Saturday?' / 'Awaiting your PO :)'. Be specific, not vague.",
                    "objection_handling": "Handle objections like Rushabh: on price, try to meet mid-way ('Can I send revised quote for $330K?'). On lead time, hold firm (12-16 weeks). On competitors, emphasize quality.",
                    "deal_awareness": "Know where the deal is: discovery→technical→quote→negotiation→close. Don't ask qualifying questions when the customer is ready to buy. Don't push for PO when they're still exploring.",
                    "customer_context": "Reference the customer's SPECIFIC situation: their project name, past orders, the machine they're replacing, their production target. Rushabh always personalizes.",
                    "strategic_intent": "Think like Rushabh: every message should move the deal forward. Qualify→Propose→Close. Don't just answer questions — advance the sale.",
                    # Style-based dimensions (kept for backward compat)
                    "conciseness": f"You are TOO VERBOSE. Rushabh writes {median_words} words median. Cut length drastically.",
                    "tone_match": "Sound like Rushabh — warm, direct, casual. 'Hi!' not 'Dear'. 'Let me know' not 'Please do not hesitate'.",
                    "action_orientation": "Always propose a next step. 'Let me send specs' / 'When can we call?' / 'Awaiting your PO :)'",
                    "sales_instinct": "Qualify harder. Ask about budget. Push toward close. Mention reference customers.",
                    "personalization": "Reference the customer's specific project, past orders, and conversation history.",
                    "information_density": "Every sentence must add value. No filler. No 'I hope this email finds you well'.",
                    "technical_accuracy": "Double-check model numbers and prices against the database.",
                    "overall_alignment": "Ask yourself: would Rushabh actually send this? If not, rewrite shorter and warmer.",
                }
                for dim, info in sorted(weak_dims, key=lambda x: x[1]["score"]):
                    score = info["score"]
                    advice = _gap_advice.get(dim, f"Improve {dim}.")
                    lines.append(f"  • {dim.upper()} ({score}/10): {advice}")
        except Exception:
            pass

    playbook_file = DATA_DIR / "rushabh_playbook.json"
    if playbook_file.exists():
        try:
            playbook = json.loads(playbook_file.read_text())
            if playbook:
                lines.append("")
                lines.append("═══════════════════════════════════════════════════")
                lines.append("HOW RUSHABH ACTUALLY RESPONDS (real examples from his emails):")
                lines.append("═══════════════════════════════════════════════════")

                by_situation: Dict[str, list] = {}
                for entry in playbook:
                    by_situation.setdefault(entry["situation"], []).append(entry)

                _situation_labels = {
                    "price_negotiation": "WHEN CUSTOMER TALKS PRICE",
                    "closing": "WHEN DEAL IS CLOSING",
                    "scheduling": "WHEN SCHEDULING CALLS/MEETINGS",
                    "technical": "WHEN CUSTOMER ASKS TECHNICAL QUESTIONS",
                    "terms": "WHEN DISCUSSING TERMS/WARRANTY",
                    "timeline": "WHEN CUSTOMER MENTIONS DELAYS",
                }

                for sit, label in _situation_labels.items():
                    entries = by_situation.get(sit, [])
                    if not entries:
                        continue
                    lines.append(f"\n  {label}:")
                    for e in entries[:2]:
                        lines.append(f"    Customer: \"{e['customer'][:150]}\"")
                        lines.append(f"    Rushabh:  \"{e['rushabh'][:150]}\"")
        except Exception:
            pass

    lines.append("")
    lines.append("═══════════════════════════════════════════════════")
    lines.append("CRITICAL ANTI-PATTERNS (Ira keeps making these mistakes):")
    lines.append("═══════════════════════════════════════════════════")
    lines.append("• DO NOT dump full truth hints as responses. Extract the key fact and say it in 1-2 sentences.")
    lines.append("• DO NOT call finance/CRM tools when customer is ready to buy. Just confirm and close.")
    lines.append("• DO NOT write responses with ## headers, bullet lists, or 'CORRECTED DRAFT'. Write like a human email.")
    lines.append("• DO NOT give a 200-word answer when 20 words will do. Rushabh's median is 20 words.")
    lines.append("• ALWAYS end with a next step or question. Never end with just information.")
    lines.append("")
    lines.append("REMEMBER: Be Rushabh. Short. Warm. Direct. Action-oriented. No corporate fluff. Use :) when appropriate.")
    lines.append("When in doubt, look at the examples above and ask: what would Rushabh do here?")

    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Echo — Rushabh Voice Agent")
    parser.add_argument("command", choices=["build", "simulate", "consult", "summary"],
                        help="build=mine Gmail, simulate=run shadow test, consult=ask Echo, summary=show style")
    parser.add_argument("--max-customers", type=int, default=15)
    parser.add_argument("--conversations", type=int, default=5, help="Number of conversations per round")
    parser.add_argument("--turns", type=int, default=3, help="Turns per conversation")
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--message", type=str, default="", help="Customer message for consult mode")
    parser.add_argument("--company", type=str, default="", help="Company name for consult mode")
    args = parser.parse_args()

    if args.command == "build":
        asyncio.run(build_interaction_map(max_customers=args.max_customers))
    elif args.command == "simulate":
        asyncio.run(run_shadow_simulation(
            num_conversations=args.conversations,
            turns_per_conversation=args.turns,
            stream_telegram=not args.no_telegram,
        ))
    elif args.command == "consult":
        if not args.message:
            print("Usage: --message 'customer message here' --company 'Company Name'")
        else:
            reply = asyncio.run(consult_rushabh_voice(args.message, args.company))
            print(f"\nEcho (Rushabh voice):\n{reply}")
    elif args.command == "summary":
        print(get_echo().get_style_summary())
