"""
Cadmus — Chief Marketing Officer
=================================

Named after the Phoenician prince who brought the alphabet to Greece,
Cadmus documents Machinecraft's customer success stories and serves them
to the sales team.

Two modes:
  BUILD  — compile emails, project data, and specs into a structured case study
           (now with multi-agent enrichment: Atlas, Alexandros, Iris, CRM,
            Hermes, Delphi, and machine_specs)
  SERVE  — find and return relevant case studies for outreach / proposals

Storage:
  data/case_studies/index.json         — master registry
  data/case_studies/<slug>/case_study.json  — structured data per project
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.agents.cadmus")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent
CASE_STUDIES_DIR = PROJECT_ROOT / "data" / "case_studies"
INDEX_PATH = CASE_STUDIES_DIR / "index.json"
LINKEDIN_DATA_DIR = (
    PROJECT_ROOT / "data" / "imports" / "16_LINKEDIN DATA"
    / "Complete_LinkedInDataExport_03-03-2026.zip"
)
LINKEDIN_SHARES_CSV = LINKEDIN_DATA_DIR / "Shares.csv"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CaseStudy:
    id: str
    customer_name: str
    project_title: str
    industry: str
    country: str
    machine_model: str
    application: str
    material: str
    year: int

    challenge: str = ""
    solution: str = ""
    technical_highlights: list = field(default_factory=list)
    outcome: str = ""
    quote_worthy: list = field(default_factory=list)

    tags: list = field(default_factory=list)
    relevant_for_machines: list = field(default_factory=list)
    relevant_for_materials: list = field(default_factory=list)
    relevant_for_industries: list = field(default_factory=list)

    source_data_path: str = ""
    key_visuals: list = field(default_factory=list)

    summary_one_liner: str = ""
    summary_paragraph: str = ""
    full_document: str = ""

    # NDA-safe public version (no customer/OEM names)
    anonymous_name: str = ""
    anonymous_one_liner: str = ""
    anonymous_paragraph: str = ""

    order_value_range: str = ""
    status: str = "published"


def _load_index() -> Dict[str, Any]:
    if INDEX_PATH.exists():
        try:
            return json.loads(INDEX_PATH.read_text())
        except Exception:
            logger.warning("Corrupt index.json — rebuilding")
    return {"case_studies": []}


def _save_index(index: Dict[str, Any]) -> None:
    CASE_STUDIES_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False))


def _save_case_study(cs: CaseStudy) -> Path:
    slug_dir = CASE_STUDIES_DIR / cs.id
    slug_dir.mkdir(parents=True, exist_ok=True)
    out = slug_dir / "case_study.json"
    out.write_text(json.dumps(asdict(cs), indent=2, ensure_ascii=False))
    if cs.full_document:
        (slug_dir / "case_study_full.md").write_text(cs.full_document)
    return out


def _load_case_study(cs_id: str) -> Optional[CaseStudy]:
    path = CASE_STUDIES_DIR / cs_id / "case_study.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return CaseStudy(**{k: v for k, v in data.items() if k in CaseStudy.__dataclass_fields__})
    except Exception as e:
        logger.warning("Failed to load case study %s: %s", cs_id, e)
        return None


def register_case_study(cs: CaseStudy) -> None:
    """Save a case study and update the master index."""
    _save_case_study(cs)
    index = _load_index()
    existing_ids = {entry["id"] for entry in index["case_studies"]}
    entry = {
        "id": cs.id,
        "customer_name": cs.customer_name,
        "project_title": cs.project_title,
        "industry": cs.industry,
        "country": cs.country,
        "machine_model": cs.machine_model,
        "application": cs.application,
        "material": cs.material,
        "year": cs.year,
        "tags": cs.tags,
        "relevant_for_machines": cs.relevant_for_machines,
        "relevant_for_materials": cs.relevant_for_materials,
        "relevant_for_industries": cs.relevant_for_industries,
        "summary_one_liner": cs.summary_one_liner,
        "status": cs.status,
    }
    if cs.id in existing_ids:
        index["case_studies"] = [
            entry if e["id"] == cs.id else e for e in index["case_studies"]
        ]
    else:
        index["case_studies"].append(entry)
    _save_index(index)
    logger.info("Registered case study: %s", cs.id)


# ---------------------------------------------------------------------------
# SERVE — find relevant case studies
# ---------------------------------------------------------------------------

def _score_match(entry: Dict, query_lower: str, filters: Dict[str, str]) -> int:
    """Score how well an index entry matches the search criteria."""
    score = 0
    all_text = " ".join([
        entry.get("customer_name", ""),
        entry.get("project_title", ""),
        entry.get("application", ""),
        entry.get("material", ""),
        entry.get("industry", ""),
        entry.get("country", ""),
        entry.get("machine_model", ""),
        " ".join(entry.get("tags", [])),
        entry.get("summary_one_liner", ""),
    ]).lower()

    if query_lower:
        for word in query_lower.split():
            if word in all_text:
                score += 10

    for key in ("industry", "material", "country", "machine_type", "application"):
        val = filters.get(key, "").lower()
        if not val:
            continue
        if val in all_text:
            score += 15
        for tag in entry.get("tags", []):
            if val in tag.lower():
                score += 5
        for m in entry.get("relevant_for_machines", []):
            if val in m.lower():
                score += 8
        for mat in entry.get("relevant_for_materials", []):
            if val in mat.lower():
                score += 8
        for ind in entry.get("relevant_for_industries", []):
            if val in ind.lower():
                score += 8

    return score


async def find_case_studies(
    query: str = "",
    industry: str = "",
    material: str = "",
    machine_type: str = "",
    application: str = "",
    country: str = "",
    format: str = "paragraph",
    context: Dict[str, Any] = None,
) -> str:
    """Find case studies matching criteria. Returns formatted text for use in emails/proposals."""
    index = _load_index()
    entries = index.get("case_studies", [])
    if not entries:
        return "No case studies documented yet. Use build_case_study to create the first one."

    filters = {
        "industry": industry,
        "material": material,
        "machine_type": machine_type,
        "application": application,
        "country": country,
    }
    query_lower = query.lower()

    # Populate from hard_rules.txt at runtime — these are example placeholders
    BLACKLISTED_CUSTOMERS = {"[blocked_customer_1]", "[blocked_customer_2]", "[blocked_customer_3]"}

    scored = []
    for entry in entries:
        if entry.get("status") != "published":
            continue
        cname = (entry.get("customer_name") or "").lower()
        if any(bl in cname for bl in BLACKLISTED_CUSTOMERS):
            continue
        s = _score_match(entry, query_lower, filters)
        if s > 0 or not any(filters.values()):
            scored.append((s, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:5]

    if not top:
        return f"No case studies found matching: {query} {' '.join(f'{k}={v}' for k, v in filters.items() if v)}"

    results = []
    for score, entry in top:
        cs_id = entry["id"]
        if format == "full":
            cs = _load_case_study(cs_id)
            if cs and cs.full_document:
                results.append(cs.full_document)
                continue

        if format == "one_liner":
            liner = entry.get("summary_one_liner", "")
            if liner:
                results.append(f"• {entry['customer_name']}: {liner}")
                continue

        cs = _load_case_study(cs_id)
        if cs and cs.summary_paragraph:
            results.append(f"**{cs.customer_name} — {cs.project_title}**\n{cs.summary_paragraph}")
        else:
            results.append(
                f"**{entry['customer_name']}** ({entry.get('country', '?')}) — "
                f"{entry.get('project_title', '')}. Machine: {entry.get('machine_model', '?')}. "
                f"{entry.get('summary_one_liner', '')}"
            )

    header = f"Found {len(top)} case stud{'y' if len(top) == 1 else 'ies'}:\n\n"
    return header + "\n\n---\n\n".join(results)


# ---------------------------------------------------------------------------
# ENRICHMENT — fan out to other agents for deep source material
# ---------------------------------------------------------------------------

async def _safe_call(coro, label: str) -> str:
    """Run an async call with error isolation — one agent failing doesn't kill the build."""
    try:
        result = await asyncio.wait_for(coro, timeout=30)
        if result:
            return str(result)
    except asyncio.TimeoutError:
        logger.warning("Cadmus enrichment timeout: %s", label)
    except Exception as e:
        logger.warning("Cadmus enrichment failed (%s): %s", label, e)
    return ""


async def _enrich_from_atlas(customer_name: str) -> str:
    """Pull project summary + logbook from Atlas."""
    try:
        from openclaw.agents.ira.src.agents.atlas import project_summary, project_logbook
    except ImportError:
        return ""

    summary_task = _safe_call(project_summary(customer_name), "atlas.project_summary")
    logbook_task = _safe_call(project_logbook(customer_name), "atlas.project_logbook")
    summary, logbook = await asyncio.gather(summary_task, logbook_task)

    parts = []
    if summary and "no project" not in summary.lower()[:80]:
        parts.append(f"=== ATLAS PROJECT SUMMARY ===\n{summary[:6000]}")
    if logbook and "no project" not in logbook.lower()[:80]:
        parts.append(f"=== ATLAS PROJECT LOGBOOK ===\n{logbook[:4000]}")
    return "\n\n".join(parts)


async def _enrich_from_alexandros(customer_name: str, machine_model: str) -> str:
    """Search the document archive for POs, quotes, warranty certs."""
    try:
        from openclaw.agents.ira.src.agents.alexandros import ask_librarian
    except ImportError:
        return ""

    queries = [
        f"{customer_name} order",
        f"{customer_name} quote",
    ]
    if machine_model:
        queries.append(f"{machine_model} specifications")

    tasks = [_safe_call(ask_librarian(q), f"alexandros:{q[:30]}") for q in queries]
    results = await asyncio.gather(*tasks)
    combined = "\n".join(r for r in results if r and "no documents" not in r.lower()[:60])
    if combined.strip():
        return f"=== ALEXANDROS DOCUMENT ARCHIVE ===\n{combined[:6000]}"
    return ""


async def _enrich_from_crm(customer_name: str) -> str:
    """Pull CRM data — emails, conversations, deal history."""
    try:
        from openclaw.agents.ira.src.skills.invocation import invoke_crm_lookup
    except ImportError:
        return ""

    result = await _safe_call(invoke_crm_lookup(customer_name), "crm.lookup")
    if result and "not found" not in result.lower()[:60]:
        return f"=== CRM / MNEMOSYNE — CUSTOMER HISTORY ===\n{result[:4000]}"
    return ""


async def _enrich_from_iris(customer_name: str, industry: str, country: str) -> str:
    """Pull industry news and market context."""
    try:
        from openclaw.agents.ira.src.tools.newsdata_client import search_news
    except ImportError:
        return ""

    query = f"{industry} {country} manufacturing" if industry else f"{customer_name} manufacturing"
    result = await _safe_call(search_news(query=query, max_results=3), "iris.news")
    if result and "no results" not in result.lower()[:60]:
        return f"=== IRIS — INDUSTRY NEWS & MARKET CONTEXT ===\n{result[:3000]}"
    return ""


def _enrich_from_machine_specs(machine_model: str) -> str:
    """Pull full machine specifications from the database."""
    if not machine_model:
        return ""
    try:
        from openclaw.agents.ira.src.brain.machine_database import get_machine
        from dataclasses import asdict as _asdict
    except ImportError:
        return ""

    spec = get_machine(machine_model)
    if not spec:
        clean = re.sub(r"[/\-]?S/?A$", "", machine_model)
        spec = get_machine(clean)
    if not spec:
        base = machine_model.split("-")[0] + "-" + machine_model.split("-")[1] if "-" in machine_model else ""
        if base:
            spec = get_machine(base)

    if spec:
        d = _asdict(spec)
        lines = [f"=== MACHINE SPECS — {spec.model} ==="]
        for k, v in d.items():
            if v and k not in ("source_documents",):
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)
    return ""


def _enrich_from_hermes(customer_name: str, country: str) -> str:
    """Pull existing proof stories from Hermes board_meeting."""
    try:
        from openclaw.agents.ira.src.agents.hermes.board_meeting import DUTCH_TIDES_STORY
    except ImportError:
        return ""

    stories = []
    if DUTCH_TIDES_STORY and ("dutch" in customer_name.lower() or country.lower() in ("netherlands", "nl")):
        stories.append(DUTCH_TIDES_STORY)

    if stories:
        return "=== HERMES PROOF STORIES ===\n" + "\n".join(stories)
    return ""


def _enrich_from_delphi() -> str:
    """Pull Rushabh's voice guidance for tone calibration."""
    try:
        from openclaw.agents.ira.src.agents.delphi import get_delphi_guidance
    except ImportError:
        return ""

    guidance = get_delphi_guidance()
    if guidance:
        return f"=== DELPHI — RUSHABH'S VOICE PROFILE ===\n{guidance[:2000]}"
    return ""


async def gather_enrichment(
    customer_name: str,
    machine_model: str = "",
    industry: str = "",
    country: str = "",
) -> str:
    """Fan out to the pantheon and assemble enriched source material.

    Called by build_case_study before LLM synthesis. Each agent call is
    isolated — if one fails or times out, the others still contribute.
    """
    logger.info(
        "Cadmus enrichment: customer=%s machine=%s industry=%s country=%s",
        customer_name, machine_model, industry, country,
    )

    sync_parts = [
        _enrich_from_machine_specs(machine_model),
        _enrich_from_hermes(customer_name, country),
        _enrich_from_delphi(),
    ]

    async_tasks = [
        _enrich_from_atlas(customer_name),
        _enrich_from_alexandros(customer_name, machine_model),
        _enrich_from_crm(customer_name),
        _enrich_from_iris(customer_name, industry, country),
    ]
    async_results = await asyncio.gather(*async_tasks)

    all_parts = [p for p in sync_parts + list(async_results) if p]

    enrichment = "\n\n".join(all_parts)
    logger.info(
        "Cadmus enrichment complete: %d sections, %d chars",
        len(all_parts), len(enrichment),
    )
    return enrichment


# ---------------------------------------------------------------------------
# BUILD — create a case study (LLM-assisted synthesis)
# ---------------------------------------------------------------------------

def _load_voice_samples(max_samples: int = 5, max_chars: int = 4000) -> str:
    """Load real LinkedIn posts from Shares.csv as voice samples for the LLM."""
    if not LINKEDIN_SHARES_CSV.exists():
        return ""
    try:
        import csv
        samples = []
        with open(LINKEDIN_SHARES_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = row.get("ShareCommentary", "").strip().replace('""', '"')
                if len(text) > 100 and any(
                    kw in text.lower()
                    for kw in ["machinecraft", "thermoforming", "vacuum forming",
                               "pf1", "specs", "machine", "forming area"]
                ):
                    samples.append(text[:800])
                    if len(samples) >= max_samples * 3:
                        break

        # Pick the best mix: 1 long product post, 1 customer story, 1 short teaser, 1 India pride, 1 specs post
        best = []
        for s in samples:
            sl = s.lower()
            if "specs that slap" in sl or "forming area" in sl or "kw" in sl:
                if not any("specs" in b.lower() for b in best):
                    best.append(s)
            elif any(name in sl for name in ["customer", "partnership", "delivered", "commissioned"]):
                if not any("customer" in b.lower() for b in best):
                    best.append(s)
            elif "frugal innovation" in sl or "india" in sl and "european" in sl:
                best.append(s)
            elif len(s) < 200:
                best.append(s)
            if len(best) >= max_samples:
                break

        if len(best) < max_samples:
            for s in samples:
                if s not in best:
                    best.append(s)
                if len(best) >= max_samples:
                    break

        result = "\n\n---\n\n".join(best[:max_samples])
        return result[:max_chars]
    except Exception as e:
        logger.debug("Failed to load voice samples: %s", e)
        return ""


async def build_case_study(
    query: str = "",
    context: Dict[str, Any] = None,
    enrich: bool = True,
) -> str:
    """Build or update a case study with multi-agent enrichment.

    Cadmus now makes "phone calls" to the pantheon before synthesizing:
      - Atlas:      project summary, logbook, timeline, milestones
      - Alexandros:  POs, quotes, warranty certs from the document archive
      - Mnemosyne:   CRM data — emails, conversations, deal stage
      - Iris:        industry news and market context
      - Hermes:      existing proof stories for the customer/region
      - Delphi:      Rushabh's voice profile for tone calibration
      - machine_specs: full technical specifications for the machine

    Set enrich=False to skip agent calls (uses only case_study_data.md).
    """
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return "(OpenAI not available for case study synthesis)"

    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

    # --- Phase 1: Load existing source data from disk ---
    source_data = ""
    for d in CASE_STUDIES_DIR.iterdir():
        if d.is_dir():
            data_file = d / "case_study_data.md"
            if data_file.exists() and not (d / "case_study.json").exists():
                source_data += f"\n\n=== SOURCE DATA FROM {d.name} ===\n"
                source_data += data_file.read_text()[:15000]

    # --- Phase 2: Extract hints from query for enrichment targeting ---
    customer_hint = ""
    machine_hint = ""
    industry_hint = ""
    country_hint = ""

    if context:
        customer_hint = context.get("customer_name", "")
        machine_hint = context.get("machine_model", "")
        industry_hint = context.get("industry", "")
        country_hint = context.get("country", "")

    if not customer_hint and query:
        parts = re.split(r"[—\-–]", query)
        if parts:
            customer_hint = parts[0].strip()

    machine_match = re.search(
        r"(PF1[A-Z\-]*[\d]+[A-Z/]*|MC-IMG-\d+|e-UNO-\d+|AM-\d+|IMG-\d+|ATF-\d+)",
        query, re.IGNORECASE,
    )
    if machine_match and not machine_hint:
        machine_hint = machine_match.group(1)

    # --- Phase 3: Fan out to the pantheon ---
    enrichment = ""
    if enrich and customer_hint:
        logger.info("Cadmus calling the pantheon for: %s", customer_hint)
        enrichment = await gather_enrichment(
            customer_name=customer_hint,
            machine_model=machine_hint,
            industry=industry_hint,
            country=country_hint,
        )

    # --- Phase 4: Voice samples ---
    voice_samples = _load_voice_samples()

    # --- Phase 5: LLM synthesis with enriched data ---
    system = """You are Cadmus, Machinecraft's Chief Marketing Officer.
Your job is to synthesize raw project data into a structured case study.
You have been given enriched data from multiple internal agents — use ALL of it.

DATA SOURCES YOU MAY RECEIVE:
- ATLAS PROJECT SUMMARY: Real project data, timelines, milestones, payment status
- ATLAS PROJECT LOGBOOK: CRM-style timeline of emails, payments, events
- ALEXANDROS DOCUMENT ARCHIVE: Actual PO text, quote details, warranty certificates
- CRM / MNEMOSYNE: Email history, conversation summaries, deal stage
- IRIS NEWS: Industry trends and market context for the customer's sector
- HERMES PROOF STORIES: Pre-written reference stories for this customer/region
- DELPHI VOICE PROFILE: Rushabh's communication style patterns and gaps
- MACHINE SPECS: Full technical specifications from the machine database
- SOURCE DATA: Pre-assembled project notes and research

INSTRUCTIONS:
1. Cross-reference ALL sources. If Atlas says "installed Feb 2025" and the source data says
   "delivered 2024", use the Atlas date (it's from the live project database).
2. Pull SPECIFIC numbers from machine specs — exact kW, m3/hr, mm dimensions. Never round.
3. Use CRM email history to add relationship depth — how long the engagement lasted,
   how many touchpoints, what the customer's journey looked like.
4. Use Iris news to add market context — why this project matters in the broader industry.
5. Use Delphi guidance to calibrate your voice to Rushabh's actual writing style.

PERSONALITY — RUSHABH'S MARKETING VOICE:
- OPEN WITH A HOOK: "Spa OEMs: What's your thermoformer doing when asked to pull a 2800x2800 mm acrylic shell? Ours says, 'Bring it on.'"
- CONFIDENT & PUNCHY: "Specs that slap:" / "No hot spots. No guesswork. No slowdowns."
- LEAD WITH NUMBERS: Concrete specs first — forming area in mm, kW, m3/hr, tonnes.
- TRANSLATE SPECS TO BENEFITS: After specs, "What it means:" section.
- INDIA PRIDE: Frame as frugal innovation — same quality, competitive price, from India.
- TARGET AUDIENCE CALLOUT: "Who's it for?" — name specific processors, industries, regions.
- END WITH CTA: "Let's talk." / "Want to stop burning energy on old presses?"
- QUOTE-WORTHY LINES: Punchy enough for LinkedIn or email.
- EMOJI: Sparingly — 🏭 🚀 ✅ 🇮🇳. Not every sentence.
- HASHTAG STYLE: lowercase, industry-specific: #thermoforming #automotive #hdpe #MadeInIndia

Output ONLY valid JSON matching this schema (no markdown fences, no commentary):
{
  "id": "slug-id",
  "customer_name": "...",
  "project_title": "...",
  "industry": "...",
  "country": "...",
  "machine_model": "...",
  "application": "...",
  "material": "...",
  "year": 2022,
  "challenge": "2-3 sentences: what the customer needed and why it was hard. Be specific about dimensions, materials, technical difficulty. Use real data from Atlas/Alexandros if available.",
  "solution": "2-3 sentences: what Machinecraft built and why it was special. Include specific specs from the machine database. Lead with the innovation.",
  "technical_highlights": ["Each highlight: concrete spec from machine_specs + what it means for the customer. At least 5 highlights. Use EXACT numbers."],
  "outcome": "2-3 sentences: results, production status, relationship expansion. Reference Atlas logbook events if available. Concrete outcomes.",
  "quote_worthy": ["4+ punchy lines in Rushabh's voice — confident, specific, usable in LinkedIn posts or sales emails. ANONYMIZED."],
  "tags": ["at least 12 tags: industry, material, process, geography, application, machine-series, use-case"],
  "relevant_for_machines": ["List ALL Machinecraft models that prospects with similar needs might consider"],
  "relevant_for_materials": ["All materials this case study is relevant for"],
  "relevant_for_industries": ["All industries this case study could serve as social proof for"],
  "summary_one_liner": "One punchy sentence for email snippets — Rushabh's voice, specific claim, ANONYMIZED",
  "summary_paragraph": "3-5 sentences for proposals — customer's scale, technical innovation, outcome. ANONYMIZED.",
  "anonymous_name": "NDA-safe description: 'A leading Dutch hydroponics company' not the real name",
  "anonymous_one_liner": "Same as summary_one_liner but guaranteed no customer/OEM names",
  "anonymous_paragraph": "Same as summary_paragraph but guaranteed no customer/OEM names",
  "order_value_range": "Approximate range (e.g. ₹2-3 Crore, EUR 150-200K) — never exact figures",
  "status": "published"
}

Rules:
- NEVER include exact order values, only ranges
- NEVER include personal email addresses or phone numbers
- NEVER use customer names or OEM names in public-facing fields (summary_one_liner, summary_paragraph, quote_worthy, anonymous_*). We have NDAs.
  Use anonymous descriptions: "A $200M automotive group" not the actual name.
  The customer_name field in the JSON is for INTERNAL use only.
- DO include specific machine specs, materials, dimensions, kW ratings
- Tags should be lowercase, at least 12
- ALWAYS populate anonymous_name, anonymous_one_liner, anonymous_paragraph
- The full_document field is NOT in the JSON — you only produce the structured data"""

    user_msg = f"Build a case study from this data:\n\nUser request: {query}"

    if source_data:
        user_msg += f"\n\n{source_data}"

    if enrichment:
        user_msg += f"\n\n{'='*60}\nENRICHED DATA FROM THE PANTHEON (Atlas, Alexandros, CRM, Iris, Hermes, Delphi, machine_specs)\n{'='*60}\n{enrichment}"

    if voice_samples:
        user_msg += f"\n\n=== RUSHABH'S REAL LINKEDIN POSTS (match this voice) ===\n{voice_samples}"

    model = "gpt-4o" if enrichment else "gpt-4o-mini"
    max_tokens = 4000 if enrichment else 3000

    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg[:28000]},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)
        cs = CaseStudy(**{k: v for k, v in data.items() if k in CaseStudy.__dataclass_fields__})

        cs.source_data_path = f"data/case_studies/{cs.id}/"
        cs.full_document = _generate_full_document(cs)

        register_case_study(cs)

        enrichment_note = ""
        if enrichment:
            agents_used = []
            if "ATLAS" in enrichment:
                agents_used.append("Atlas")
            if "ALEXANDROS" in enrichment:
                agents_used.append("Alexandros")
            if "CRM" in enrichment or "MNEMOSYNE" in enrichment:
                agents_used.append("Mnemosyne")
            if "IRIS" in enrichment:
                agents_used.append("Iris")
            if "HERMES" in enrichment:
                agents_used.append("Hermes")
            if "DELPHI" in enrichment:
                agents_used.append("Delphi")
            if "MACHINE SPECS" in enrichment:
                agents_used.append("machine_specs")
            enrichment_note = f"\nEnriched by: {', '.join(agents_used)}"

        return (
            f"Case study built and registered: **{cs.customer_name} — {cs.project_title}**\n\n"
            f"ID: `{cs.id}`\n"
            f"Machine: {cs.machine_model}\n"
            f"Tags: {', '.join(cs.tags)}{enrichment_note}\n\n"
            f"**One-liner:** {cs.summary_one_liner}\n\n"
            f"**Paragraph:**\n{cs.summary_paragraph}\n\n"
            f"Saved to `data/case_studies/{cs.id}/case_study.json`\n"
            f"Full document at `data/case_studies/{cs.id}/case_study_full.md`"
        )
    except json.JSONDecodeError as e:
        logger.error("Cadmus JSON parse error: %s\nRaw: %s", e, raw[:500])
        return f"(Case study build failed — LLM returned invalid JSON: {e})"
    except Exception as e:
        logger.error("Cadmus build error: %s", e, exc_info=True)
        return f"(Case study build error: {e})"


def _generate_full_document(cs: CaseStudy) -> str:
    """Generate a full markdown case study document from structured data."""
    lines = [
        f"# {cs.customer_name} — {cs.project_title}",
        "",
        f"**Industry:** {cs.industry} | **Country:** {cs.country} | **Year:** {cs.year}",
        f"**Machine:** {cs.machine_model} | **Material:** {cs.material}",
        "",
        "---",
        "",
        "## The Challenge",
        "",
        cs.challenge,
        "",
        "## The Solution",
        "",
        cs.solution,
        "",
        "## Specs That Matter",
        "",
    ]
    for h in cs.technical_highlights:
        lines.append(f"- {h}")
    lines += [
        "",
        "## The Outcome",
        "",
        cs.outcome,
        "",
    ]
    if cs.quote_worthy:
        lines += ["## In Rushabh's Words", ""]
        for q in cs.quote_worthy:
            lines.append(f"> {q}")
            lines.append("")
    tags_str = " ".join(f"#{t}" for t in cs.tags[:10]) if cs.tags else ""
    lines += [
        "---",
        "",
        f"*{cs.summary_one_liner}*",
        "",
    ]
    if tags_str:
        lines.append(tags_str)
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# DRAFT — LinkedIn post from case study or topic
# ---------------------------------------------------------------------------

_LINKEDIN_POST_SYSTEM = """You are Cadmus, Machinecraft's CMO, ghostwriting LinkedIn posts for Rushabh Doshi.

You have studied 700+ of Rushabh's real LinkedIn posts. Here is how he writes:

STRUCTURE (pick one per post):
A) Hook question → Specs bullet list → "What it means:" benefits → "Who's it for?" → CTA + hashtags
B) Customer story → Country flag → What they make → Machine specs → Partnership pride → hashtags
C) Short teaser (1-3 lines) + video/link placeholder → hashtags
D) Bold announcement → Emoji bullet list → Vision statement → CTA + hashtags
E) Personal story → Business lesson → Tie back to Machinecraft → hashtags

VOICE RULES:
- First person. "We" or "I", never "Machinecraft is pleased to..."
- Open with a HOOK — question, bold claim, or teaser. Never start with "We are excited to..."
- SPECS FIRST: "3500 x 2000 mm forming area" not "large forming area". Always include mm, kW, m3/hr.
- After specs, TRANSLATE: "What it means: No hot spots. No guesswork. No slowdowns."
- CONFIDENT but not arrogant. "Ours says, 'Bring it on.'" / "Specs that slap:"
- INDIA PRIDE when relevant: 🇮🇳, #MadeInIndia, frugal innovation narrative
- CUSTOMER NAMES with country flags: "[Customer] - a proud Dutch 🇳🇱 firm"
- EMOJI: moderate. Flags, 🏭, 🚀, ✅, →, 💪. Never every line.
- END with CTA: "Let's talk." / "DM me" / "What are your thoughts?" / question to audience
- HASHTAGS: 5-12 at bottom. Always #thermoforming #Machinecraft. Mix industry + geography + process.
- Multi-language hashtags when targeting Europe: #thermoformage #Thermoformen #termoformado
- LENGTH: 100-300 words for standard posts. Can go longer for major announcements.
- NO generic corporate speak. NO "we are pleased to announce". NO passive voice.
- Include [VIDEO] or [IMAGE] placeholder where Rushabh should attach media.

NEVER include:
- Exact order values or pricing
- Personal email addresses or phone numbers
- CUSTOMER NAMES or OEM NAMES — we have NDAs. Use anonymous descriptions instead:
  "A $200M automotive components group in India" NOT "Customer-H"
  "A leading Indian automaker" NOT "Mahindra"
  "A Dutch hydroponic startup" NOT "Customer-A"
  Keep it specific enough to be credible (industry, country, size) but never name the company.
- Competitor names (position against "European machines" generically)
- Machine model numbers that could identify the customer (use series names like "PF1 series" instead of "PF1-3520/S/A" if the custom config is unique to one customer)"""


async def draft_linkedin_post(
    topic: str = "",
    case_study_id: str = "",
    post_type: str = "customer_story",
    context: Dict[str, Any] = None,
) -> str:
    """Draft a LinkedIn post in Rushabh's voice.

    Args:
        topic: What the post is about (free text). Used if no case_study_id.
        case_study_id: ID of a published case study to turn into a post.
        post_type: One of: customer_story, product_launch, teaser, announcement,
                   india_pride, event, personal_story
    """
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return "(OpenAI not available for LinkedIn post drafting)"

    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

    # Load case study data if provided — use ANONYMOUS versions for LinkedIn
    cs_context = ""
    if case_study_id:
        cs = _load_case_study(case_study_id)
        if cs:
            anon_name = cs.anonymous_name or f"A client in {cs.country}"

            # Scrub all customer/OEM names from text fields before sending to LLM
            def _scrub(text: str) -> str:
                """Remove customer and OEM names from text."""
                import json as _j
                scrub_path = CASE_STUDIES_DIR / cs.id / "scrub_names.json"
                # Build scrub map from case study data
                scrub_map = {}
                if cs.customer_name:
                    for part in cs.customer_name.split("/"):
                        name = part.strip()
                        if len(name) > 2:
                            scrub_map[name] = anon_name
                # Also load custom scrub map if exists
                if scrub_path.exists():
                    try:
                        scrub_map.update(_j.loads(scrub_path.read_text()))
                    except Exception:
                        pass
                # Common OEM names to scrub
                oem_scrubs = {
                    "Mahindra & Mahindra": "a leading Indian automaker",
                    "Mahindra": "a leading Indian automaker",
                    "Scorpio": "pickup truck",
                    "M&M": "the automaker",
                    "Aeroklas": "a Thai tooling partner",
                    "FRIMO": "a German technology partner",
                }
                scrub_map.update(oem_scrubs)
                result = text
                for name, replacement in sorted(scrub_map.items(), key=lambda x: -len(x[0])):
                    result = result.replace(name, replacement)
                return result

            cs_context = (
                f"CASE STUDY DATA (PRE-ANONYMIZED — all names already removed):\n"
                f"Customer: {anon_name}\n"
                f"Project type: pickup truck bedliners\n"
                f"Machine series: PF1 series (custom)\n"
                f"Material: {cs.material}\n"
                f"Industry: {cs.industry} | Country: {cs.country} | Year: {cs.year}\n"
                f"Challenge: {_scrub(cs.challenge)}\n"
                f"Solution: {_scrub(cs.solution)}\n"
                f"Technical highlights:\n"
                + "\n".join(f"  - {_scrub(h)}" for h in cs.technical_highlights)
                + f"\nOutcome: {_scrub(cs.outcome)}\n"
                f"Quote-worthy lines:\n"
                + "\n".join(f"  - {_scrub(q)}" for q in cs.quote_worthy)
                + f"\nCRITICAL: Do NOT mention any company names. The customer is '{anon_name}'. "
                f"The end customer is 'a leading Indian automaker'. No exceptions.\n"
            )

    # Load voice samples
    voice_samples = _load_voice_samples(max_samples=6, max_chars=5000)

    user_msg = f"Draft a LinkedIn post.\n\nPost type: {post_type}\nTopic: {topic}\n"
    if cs_context:
        user_msg += f"\n{cs_context}"
    if voice_samples:
        user_msg += f"\n\n=== RUSHABH'S REAL POSTS (match this exact voice) ===\n{voice_samples}"

    user_msg += (
        "\n\nWrite the post now. Output ONLY the post text — no commentary, "
        "no 'here's a draft', no markdown headers. Just the raw LinkedIn post "
        "ready to copy-paste. Include [IMAGE] or [VIDEO] placeholders where "
        "Rushabh should attach media."
    )

    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _LINKEDIN_POST_SYSTEM},
                {"role": "user", "content": user_msg[:12000]},
            ],
            temperature=0.7,
            max_tokens=1500,
        )
        draft = resp.choices[0].message.content.strip()

        # Save draft for review
        drafts_dir = PROJECT_ROOT / "data" / "cadmus" / "linkedin_drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        slug = re.sub(r"[^a-z0-9]+", "-", (case_study_id or topic)[:40].lower()).strip("-")
        draft_path = drafts_dir / f"{datetime.now().strftime('%Y%m%d_%H%M')}_{slug}.md"
        draft_path.write_text(f"# LinkedIn Post Draft\n\n**Type:** {post_type}\n**Topic:** {topic or case_study_id}\n**Generated:** {datetime.now().isoformat()}\n\n---\n\n{draft}\n")

        return (
            f"**LinkedIn Post Draft** ({post_type})\n"
            f"Saved to `{draft_path.relative_to(PROJECT_ROOT)}`\n\n"
            f"---\n\n"
            f"{draft}\n\n"
            f"---\n\n"
            f"*Review and edit before posting. Add images/videos where marked.*"
        )
    except Exception as e:
        logger.error("LinkedIn post draft error: %s", e)
        return f"(LinkedIn post draft error: {e})"


async def draft_linkedin_post_with_visuals(
    topic: str = "",
    case_study_id: str = "",
    post_type: str = "customer_story",
    visual_style: str = "carousel",
    context: Dict[str, Any] = None,
) -> str:
    """Draft a LinkedIn post AND generate visuals using Manus API.

    This is the premium version — uses Manus (expensive) to create
    professional images, carousels, or slide decks.

    Args:
        topic: What the post is about.
        case_study_id: Optional case study ID to base content on.
        post_type: customer_story, product_launch, teaser, etc.
        visual_style: "carousel" (LinkedIn image carousel), "infographic",
                      "slide_deck" (MBB-style PPTX), or "hero_image" (single image).
    """
    from .manus_client import manus_generate, get_manus_spend_today

    # Check daily spend before calling Manus
    spend = get_manus_spend_today()
    DAILY_CREDIT_LIMIT = 50
    if spend["credits"] >= DAILY_CREDIT_LIMIT:
        return (
            f"Manus daily credit limit reached ({spend['credits']}/{DAILY_CREDIT_LIMIT} credits, "
            f"{spend['tasks']} tasks today). Falling back to text-only draft."
        )

    # First, draft the text post (cheap, via GPT-4o-mini)
    text_draft = await draft_linkedin_post(topic, case_study_id, post_type, context)

    # Extract just the post text for Manus context
    post_body = text_draft
    parts = text_draft.split("---")
    if len(parts) >= 3:
        post_body = parts[1].strip()

    # Build case study context for Manus
    cs_detail = ""
    if case_study_id:
        cs = _load_case_study(case_study_id)
        if cs:
            anon_name = cs.anonymous_name or f"A client in {cs.country}"
            cs_detail = (
                f"Customer (anonymous): {anon_name}\n"
                f"Application: {cs.application}\n"
                f"Machine: PF1 series (custom)\n"
                f"Material: {cs.material}\n"
                f"Key specs: {'; '.join(cs.technical_highlights[:4])}\n"
            )

    # Build Manus prompt based on visual style
    visual_prompts = {
        "carousel": (
            f"Create a professional LinkedIn carousel (4-6 slides) for an industrial machinery company called Machinecraft.\n\n"
            f"Brand: Machinecraft (Indian thermoforming machine manufacturer, est. 1976)\n"
            f"Style: Clean, modern, data-driven. Dark blue (#1a365d) and white primary colors. "
            f"Bold specs in large font. Professional but not corporate-boring.\n\n"
            f"Post topic: {topic}\n"
            f"{cs_detail}\n"
            f"Post text for context:\n{post_body[:2000]}\n\n"
            f"Each slide should have:\n"
            f"- A bold headline\n"
            f"- 1-2 key specs or data points in large font\n"
            f"- Clean layout with plenty of whitespace\n"
            f"- Machinecraft branding (subtle logo placement)\n\n"
            f"Slides: 1) Hook/title, 2-4) Key specs and benefits, 5) CTA\n"
            f"IMPORTANT: Do NOT use any customer names or OEM names. Keep it anonymous.\n"
            f"Output as individual PNG images, one per slide."
        ),
        "infographic": (
            f"Create a professional infographic for LinkedIn about: {topic}\n\n"
            f"Brand: Machinecraft (Indian thermoforming machine manufacturer)\n"
            f"Style: Clean, data-driven, dark blue (#1a365d) and white.\n"
            f"{cs_detail}\n"
            f"Include key specs, process flow, and benefits.\n"
            f"IMPORTANT: Do NOT use any customer names. Keep anonymous.\n"
            f"Output as a single tall PNG image optimized for LinkedIn."
        ),
        "slide_deck": (
            f"Create a professional MBB-style (McKinsey/BCG/Bain) presentation deck about: {topic}\n\n"
            f"Company: Machinecraft Technologies (Indian thermoforming machine manufacturer, est. 1976, 35+ countries)\n"
            f"{cs_detail}\n"
            f"Post text for context:\n{post_body[:2000]}\n\n"
            f"Style: Data-driven, clean, minimal text per slide, strong headlines, "
            f"use charts/diagrams where possible. 6-10 slides.\n"
            f"IMPORTANT: Do NOT use any customer names or OEM names. Keep anonymous.\n"
            f"Output as PPTX file."
        ),
        "hero_image": (
            f"Create a single professional hero image for a LinkedIn post about: {topic}\n\n"
            f"Brand: Machinecraft (industrial thermoforming machines)\n"
            f"Style: Clean, modern, industrial. Show the concept visually.\n"
            f"{cs_detail}\n"
            f"IMPORTANT: Do NOT include any customer names. Keep anonymous.\n"
            f"Output as a single PNG image, 1200x628px (LinkedIn recommended)."
        ),
    }

    manus_prompt = visual_prompts.get(visual_style, visual_prompts["carousel"])

    # Use lite profile for simple images, full profile for slide decks
    profile = "manus-1.6-lite" if visual_style in ("hero_image", "infographic") else "manus-1.6"

    logger.info("Calling Manus for %s visual (profile: %s)", visual_style, profile)
    manus_result = await manus_generate(
        prompt=manus_prompt,
        agent_profile=profile,
        max_wait_seconds=300,
    )

    if manus_result.error:
        return (
            f"{text_draft}\n\n"
            f"---\n\n"
            f"**Manus visual generation failed:** {manus_result.error}\n"
            f"Use the text-only draft above and add your own images."
        )

    # Build response with files
    file_list = []
    for f in manus_result.files:
        local = f.get("local_path", f.get("url", ""))
        file_list.append(f"- `{f['filename']}` ({f.get('mime_type', '?')}) → {local}")

    return (
        f"{text_draft}\n\n"
        f"---\n\n"
        f"**Manus Visuals Generated** ({visual_style})\n"
        f"Credits used: {manus_result.credits_used}\n"
        f"Task: {manus_result.task_url}\n\n"
        f"**Files:**\n" + "\n".join(file_list) + "\n\n"
        f"Downloaded to: `data/cadmus/manus_outputs/`\n\n"
        f"*Attach these images to your LinkedIn post.*"
    )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class Cadmus:
    """Chief Marketing Officer — documents and serves case studies.

    build_case_study now fans out to the pantheon for enrichment:
      Atlas, Alexandros, Mnemosyne, Iris, Hermes, Delphi, machine_specs
    """

    async def find_case_studies(self, **kwargs) -> str:
        return await find_case_studies(**kwargs)

    async def build_case_study(
        self, query: str = "", context: Dict[str, Any] = None, enrich: bool = True,
    ) -> str:
        return await build_case_study(query, context, enrich=enrich)

    async def gather_enrichment(self, **kwargs) -> str:
        """Expose enrichment as a standalone call for debugging/preview."""
        return await gather_enrichment(**kwargs)

    async def draft_linkedin_post(self, **kwargs) -> str:
        return await draft_linkedin_post(**kwargs)

    async def draft_linkedin_post_with_visuals(self, **kwargs) -> str:
        return await draft_linkedin_post_with_visuals(**kwargs)

    def list_case_studies(self) -> List[Dict]:
        index = _load_index()
        return index.get("case_studies", [])


_instance: Optional[Cadmus] = None


def get_cadmus() -> Cadmus:
    global _instance
    if _instance is None:
        _instance = Cadmus()
    return _instance
