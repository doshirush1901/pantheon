"""
BOARD MEETING RESEARCHER — Research-First Intelligence for Every Lead
=====================================================================

The lesson from the European campaign: the emails that worked were the ones
where we ran a full "board meeting" before writing — Tavily for company news,
CRM for past interactions, Alexandros for past quotes, and an LLM to synthesize
the angle. The emails that didn't work skipped all of that.

This module encodes that process so every email gets the same depth of research,
whether we're sending 7 or 700.

Five research steps per lead:
    1. Tavily search — company-specific news
    2. CRM history — past interactions, conversations, deal events
    3. Archive search — past quotes, proposals, documents
    4. Company profile — what they do, what they bought, their industry
    5. Proof stories — Dutch Tides, Cadmus case studies, regional references

Then an LLM synthesis step that sees all 5 outputs and produces:
    - news_hook: opening line based on real company news
    - personal_hook: reference to past interaction if any
    - company_insight: what we know about their thermoforming needs
    - machine_recommendation: which machine and why
    - proof_point: most relevant reference story
    - subject_line: curiosity-driven subject

Usage:
    researcher = BoardMeetingResearcher()
    intel = await researcher.research(lead)
    # intel["news_hook"], intel["subject_line"], etc.
"""

import hashlib
import json
import logging
import os
import re
import sqlite3
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.hermes.board_meeting")

AGENT_DIR = Path(__file__).resolve().parent
SRC_DIR = AGENT_DIR.parent.parent
_candidate = AGENT_DIR.parent.parent.parent.parent.parent.parent
if not (_candidate / "data" / "brain").exists():
    _candidate = Path.cwd()
    while _candidate != _candidate.parent:
        if (_candidate / "data" / "brain").exists():
            break
        _candidate = _candidate.parent
PROJECT_ROOT = _candidate

CACHE_DIR = PROJECT_ROOT / "data" / "cache" / "board_meeting"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL_DAYS = 7

CRM_DB = PROJECT_ROOT / "crm" / "ira_crm.db"
IMPORTS_METADATA = PROJECT_ROOT / "data" / "brain" / "imports_metadata.json"
QUOTES_DIR = PROJECT_ROOT / "data" / "imports" / "01_Quotes_and_Proposals"
CASE_STUDIES_INDEX = PROJECT_ROOT / "data" / "case_studies" / "index.json"

DUTCH_TIDES_STORY = (
    "We just installed a PF1-X-6520 for Dutch Tides in the Netherlands — "
    "6.5 x 2 meters forming area, producing massive hydroponic trays in 4mm PS "
    "at ~150 seconds per cycle. It's the largest thermoformer in Europe. "
    "We supplied the machine, the sheets, and spent two weeks on-site fine-tuning "
    "the process with their team."
)

try:
    import openai
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False


class BoardMeetingResearcher:
    """Research-first intelligence gathering for every lead.

    Runs the same process that produced the high-quality European emails:
    deep research first, then LLM synthesis to find the best angle.
    """

    def __init__(self):
        self._tavily_key = os.environ.get("TAVILY_API_KEY", "")
        self._metadata_cache: Optional[Dict] = None

    async def research(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Run the full board meeting for a single lead."""
        company = lead.get("company", "")
        email = lead.get("email", "")
        country = lead.get("country", "")
        notes = lead.get("notes", "")

        results: Dict[str, Any] = {
            "company_news": "",
            "crm_history": "",
            "archive_docs": "",
            "company_profile": "",
            "proof_stories": "",
            "news_hook": "",
            "personal_hook": "",
            "company_insight": "",
            "machine_recommendation": "",
            "proof_point": "",
            "subject_line": "",
            "past_interactions": "",
            "past_documents": "",
        }

        if not company:
            return results

        results["company_news"] = self._tavily_search(company, country)
        results["company_research"] = self._tavily_company_research(company, country)
        results["website_scrape"] = self._scrape_website(email, company)
        results["gmail_history"] = self._gmail_search(email, company)
        results["crm_history"] = self._crm_history(email, company)
        results["archive_docs"] = self._archive_search(company)
        results["archive_deep"] = self._archive_deep_read(company)
        results["company_profile"] = self._build_profile(lead)
        results["proof_stories"] = self._get_proof_stories(country)

        # Prometheus uses website scrape as primary source, Tavily as fallback
        company_context = results["website_scrape"] or results["company_research"]
        results["product_fit"] = self._prometheus_product_fit(
            company, company_context, notes,
        )
        results["regional_intel"] = self._tyche_regional_data(country)

        # Aliases for dossier enrichment
        interaction_parts = []
        if results["gmail_history"]:
            interaction_parts.append(results["gmail_history"])
        if results["crm_history"]:
            interaction_parts.append(results["crm_history"])
        results["past_interactions"] = "\n".join(interaction_parts)
        results["past_documents"] = (
            results["archive_docs"]
            + ("\n" + results["archive_deep"] if results["archive_deep"] else "")
        )

        guidance = self._synthesize_guidance(company, country, results)
        results.update(guidance)

        return results

    # ------------------------------------------------------------------
    # Step 1: Tavily search — company-specific news
    # ------------------------------------------------------------------

    def _tavily_search(self, company: str, country: str) -> str:
        if not self._tavily_key:
            return ""

        cache_key = hashlib.md5(f"{company}:{country}".lower().encode()).hexdigest()
        cache_file = CACHE_DIR / f"tavily_{cache_key}.json"

        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text())
                cached_at = datetime.fromisoformat(cached.get("cached_at", "2000-01-01"))
                if datetime.now() - cached_at < timedelta(days=CACHE_TTL_DAYS):
                    return cached.get("text", "")
            except Exception:
                pass

        query = f"{company} {country} news 2025 2026"
        try:
            payload = json.dumps({
                "api_key": self._tavily_key,
                "query": query,
                "max_results": 3,
                "search_depth": "basic",
            }).encode()
            req = urllib.request.Request(
                "https://api.tavily.com/search",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            articles = []
            for r in data.get("results", [])[:3]:
                title = r.get("title", "")[:120]
                content = r.get("content", "")[:300]
                if title:
                    articles.append(f"- {title}: {content}")

            text = "\n".join(articles) if articles else ""

            cache_file.write_text(json.dumps({
                "cached_at": datetime.now().isoformat(),
                "query": query,
                "text": text,
            }))
            return text

        except Exception as e:
            logger.debug("Tavily search failed for %s: %s", company, e)
            return ""

    # ------------------------------------------------------------------
    # Step 1b: Tavily company research — what do they actually make?
    # ------------------------------------------------------------------

    def _tavily_company_research(self, company: str, country: str) -> str:
        """Search for what the company does, their products, their industry.
        This is the missing piece — without it we can't recommend the right machine."""
        if not self._tavily_key:
            return ""

        cache_key = hashlib.md5(f"research:{company}:{country}".lower().encode()).hexdigest()
        cache_file = CACHE_DIR / f"research_{cache_key}.json"

        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text())
                cached_at = datetime.fromisoformat(cached.get("cached_at", "2000-01-01"))
                if datetime.now() - cached_at < timedelta(days=CACHE_TTL_DAYS):
                    return cached.get("text", "")
            except Exception:
                pass

        query = f"{company} {country} products manufacturing what do they make"
        try:
            payload = json.dumps({
                "api_key": self._tavily_key,
                "query": query,
                "max_results": 3,
                "search_depth": "basic",
            }).encode()
            req = urllib.request.Request(
                "https://api.tavily.com/search",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            articles = []
            for r in data.get("results", [])[:3]:
                title = r.get("title", "")[:120]
                content = r.get("content", "")[:400]
                if title:
                    articles.append(f"- {title}: {content}")

            text = "\n".join(articles) if articles else ""

            cache_file.write_text(json.dumps({
                "cached_at": datetime.now().isoformat(),
                "query": query,
                "text": text,
            }))
            return text

        except Exception as e:
            logger.debug("Tavily company research failed for %s: %s", company, e)
            return ""

    # ------------------------------------------------------------------
    # Step 1c: Website scrape — read the company's actual website
    # ------------------------------------------------------------------

    def _scrape_website(self, email: str, company: str) -> str:
        """Search the company's actual website via Tavily with domain filtering.
        This is the ground truth — generic Tavily can match the wrong entity,
        but searching within their domain gives us what THEY say about themselves."""
        if not self._tavily_key:
            return ""

        domain = ""
        if email and "@" in email:
            domain = email.split("@")[1]
            if domain in (
                "gmail.com", "yahoo.com", "yahoo.co.in", "hotmail.com",
                "outlook.com", "rediffmail.com", "aol.com", "icloud.com",
                "hotmail.de", "yahoo.in", "live.com", "protonmail.com",
            ):
                domain = ""

        if not domain:
            return ""

        cache_key = hashlib.md5(f"website:{domain}".encode()).hexdigest()
        cache_file = CACHE_DIR / f"website_{cache_key}.json"

        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text())
                cached_at = datetime.fromisoformat(cached.get("cached_at", "2000-01-01"))
                if datetime.now() - cached_at < timedelta(days=CACHE_TTL_DAYS):
                    return cached.get("text", "")
            except Exception:
                pass

        # Use Tavily with include_domains to search ONLY their website
        query = f"{company} products about company"
        try:
            payload = json.dumps({
                "api_key": self._tavily_key,
                "query": query,
                "max_results": 5,
                "search_depth": "advanced",
                "include_domains": [domain, f"www.{domain}"],
            }).encode()
            req = urllib.request.Request(
                "https://api.tavily.com/search",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())

            articles = []
            for r in data.get("results", [])[:5]:
                title = r.get("title", "")[:120]
                content = r.get("content", "")[:500]
                url = r.get("url", "")
                if title or content:
                    articles.append(f"[{url}] {title}\n{content}")

            text = "\n\n".join(articles) if articles else ""

            cache_file.write_text(json.dumps({
                "cached_at": datetime.now().isoformat(),
                "domain": domain,
                "text": text[:3000],
            }))
            return text[:3000]

        except Exception as e:
            logger.debug("Website scrape via Tavily failed for %s: %s", domain, e)
            return ""

    # ------------------------------------------------------------------
    # Step 1d: Gmail search — actual email threads with this contact
    # ------------------------------------------------------------------

    def _gmail_search(self, email: str, company: str) -> str:
        """Search Gmail for actual email threads with this contact.
        This catches things the CRM misses — like Jaquar's PF1-X-3030 installation."""
        if not email or "placeholder" in email:
            return ""

        try:
            from openclaw.agents.ira.src.tools.google_tools import gmail_search
            # Search by email address
            results = gmail_search(query=f"from:{email} OR to:{email}", max_results=10)
            if results and "No messages" not in results and "Error" not in results:
                return results[:2000]

            # Fallback: search by company name
            if company:
                results = gmail_search(query=company, max_results=5)
                if results and "No messages" not in results and "Error" not in results:
                    return results[:1500]
        except Exception as e:
            logger.debug("Gmail search failed for %s: %s", email, e)

        return ""

    # ------------------------------------------------------------------
    # Step 2: CRM history — past interactions
    # ------------------------------------------------------------------

    def _crm_history(self, email: str, company: str) -> str:
        if not CRM_DB.exists():
            return ""

        try:
            conn = sqlite3.connect(str(CRM_DB))
            conn.row_factory = sqlite3.Row

            lines = []

            # Conversations
            convos = conn.execute(
                "SELECT direction, subject, preview, date FROM conversations "
                "WHERE email = ? ORDER BY date DESC LIMIT 10",
                (email,),
            ).fetchall()
            if convos:
                lines.append(f"PAST CONVERSATIONS ({len(convos)}):")
                for c in convos:
                    date = (c["date"] or "")[:16]
                    direction = "SENT" if c["direction"] == "outbound" else "RECEIVED"
                    preview = (c["preview"] or "")[:200].replace("\n", " ").replace("\r", "")
                    lines.append(f"  [{date}] {direction}: {c['subject'] or '(no subject)'}")
                    if preview:
                        lines.append(f"    {preview}")

            # Email log
            emails = conn.execute(
                "SELECT direction, subject, body_preview, sent_at, batch_id FROM email_log "
                "WHERE email = ? ORDER BY sent_at DESC LIMIT 5",
                (email,),
            ).fetchall()
            if emails:
                lines.append(f"\nEMAILS SENT/RECEIVED ({len(emails)}):")
                for e in emails:
                    date = (e["sent_at"] or "")[:16]
                    lines.append(f"  [{date}] {e['direction']}: {e['subject'] or '(no subject)'} (batch: {e['batch_id'] or 'manual'})")

            # Deal events
            events = conn.execute(
                "SELECT event, old_value, new_value, notes, created_at FROM deal_events "
                "WHERE email = ? ORDER BY created_at DESC LIMIT 5",
                (email,),
            ).fetchall()
            if events:
                lines.append(f"\nDEAL EVENTS ({len(events)}):")
                for ev in events:
                    lines.append(f"  [{(ev['created_at'] or '')[:16]}] {ev['event']}: {ev['old_value']} -> {ev['new_value']}")

            conn.close()
            return "\n".join(lines) if lines else ""

        except Exception as e:
            logger.debug("CRM history failed for %s: %s", email, e)
            return ""

    # ------------------------------------------------------------------
    # Step 3: Archive search — past quotes, proposals, documents
    # ------------------------------------------------------------------

    def _archive_search(self, company: str) -> str:
        results = []

        # Search filenames in Quotes directory
        if QUOTES_DIR.exists():
            company_words = [w.lower() for w in company.split() if len(w) > 2]
            for f in QUOTES_DIR.iterdir():
                fname = f.name.lower()
                if any(w in fname for w in company_words):
                    results.append(f"QUOTE: {f.name} ({f.stat().st_size // 1024} KB)")

        # Search imports metadata
        if IMPORTS_METADATA.exists() and not self._metadata_cache:
            try:
                self._metadata_cache = json.loads(IMPORTS_METADATA.read_text())
            except Exception:
                self._metadata_cache = {}

        if self._metadata_cache:
            files_dict = self._metadata_cache.get("files", self._metadata_cache)
            if isinstance(files_dict, dict):
                company_lower = company.lower()
                for filename, info in files_dict.items():
                    if isinstance(info, dict):
                        searchable = f"{filename} {info.get('summary', '')} {' '.join(info.get('entities', []))}".lower()
                        if company_lower in searchable or any(
                            w in searchable for w in company_lower.split() if len(w) > 3
                        ):
                            summary = info.get("summary", "")[:150]
                            if summary:
                                results.append(f"DOC: {filename} — {summary}")
                            else:
                                results.append(f"DOC: {filename}")

        return "\n".join(results[:10]) if results else ""

    # ------------------------------------------------------------------
    # Step 4: Company profile — what we know about them
    # ------------------------------------------------------------------

    def _build_profile(self, lead: Dict) -> str:
        parts = []
        company = lead.get("company", "")
        notes = lead.get("notes", "")
        source = lead.get("source", "")
        name = lead.get("name", "")
        country = lead.get("country", "")

        if name:
            parts.append(f"Contact: {name}")
        if country:
            parts.append(f"Country: {country}")
        if source:
            parts.append(f"Source: {source}")

        # Parse structured info from notes
        if "Past customer" in notes or "PAST CUSTOMER" in notes:
            parts.append("TYPE: Past Machinecraft customer")
            purchased = re.search(r"Purchased:\s*(.+?)(?:\.|$|\|)", notes)
            if purchased:
                parts.append(f"Previously purchased: {purchased.group(1).strip()}")
            region = re.search(r"Region:\s*(.+?)(?:\||$)", notes)
            if region:
                parts.append(f"Location: {region.group(1).strip()}")

        elif "PlastIndia" in source:
            parts.append("TYPE: Visited Machinecraft booth at PlastIndia 2023")
            city = re.search(r"City:\s*(.+?)$", notes)
            if city:
                parts.append(f"Location: {city.group(1).strip()}")

        elif "LLM Prospects" in source:
            parts.append("TYPE: Active prospect with conversation history")
            score = re.search(r"Score:\s*([\d.]+)", notes)
            if score:
                parts.append(f"Lead score: {score.group(1)}")
            comms = re.search(r"(\d+)\s*comms", notes)
            if comms:
                parts.append(f"Past communications: {comms.group(1)}")
            quotes = re.search(r"(\d+)\s*quotes", notes)
            if quotes:
                parts.append(f"Quote discussions: {quotes.group(1)}")

        if notes and not any(k in notes for k in ("Past customer", "PlastIndia", "Score:")):
            parts.append(f"Notes: {notes[:200]}")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Step 3b: Alexandros deep read — extract content from past quotes
    # ------------------------------------------------------------------

    def _archive_deep_read(self, company: str) -> str:
        """Actually read past quote PDFs to extract pricing, specs, what was offered."""
        if not QUOTES_DIR.exists():
            return ""

        company_words = [w.lower() for w in company.split() if len(w) > 2]
        matched_files = []
        for f in QUOTES_DIR.iterdir():
            if f.suffix.lower() != ".pdf":
                continue
            fname = f.name.lower()
            if any(w in fname for w in company_words):
                matched_files.append(f)

        if not matched_files:
            return ""

        extracts = []
        for f in matched_files[:2]:
            try:
                import pdfplumber
                with pdfplumber.open(f) as pdf:
                    text = ""
                    for page in pdf.pages[:3]:
                        text += (page.extract_text() or "")
                    if text:
                        snippet = text[:800].strip()
                        extracts.append(f"FROM {f.name}:\n{snippet}")
            except ImportError:
                extracts.append(f"PDF found but pdfplumber not available: {f.name}")
            except Exception as e:
                logger.debug("Failed to read %s: %s", f.name, e)

        return "\n\n".join(extracts) if extracts else ""

    # ------------------------------------------------------------------
    # Step 5b: Prometheus product fit — what can they thermoform?
    # ------------------------------------------------------------------

    def _prometheus_product_fit(
        self, company: str, company_research: str, notes: str
    ) -> str:
        """Given what the company makes, identify specific thermoformable products."""
        if not _OPENAI_AVAILABLE or not company_research:
            return ""

        try:
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{
                    "role": "user",
                    "content": (
                        f"Company: {company}\n"
                        f"What they do: {company_research[:500]}\n"
                        f"Past purchases from Machinecraft: {notes[:300]}\n\n"
                        "Based on what this company makes, list 2-3 SPECIFIC products "
                        "they could thermoform (or already thermoform). For each product:\n"
                        "- Name the specific product\n"
                        "- State the material (ABS, HIPS, PP, HDPE, PVC, PS, PET, PC, PMMA, etc.)\n"
                        "- State the thickness range\n"
                        "- Route to the correct machine:\n"
                        "  THICK GAUGE (>1.5mm) → PF1 series: PC, ABS, HDPE, PP thick, PMMA, ASA, "
                        "automotive, luggage, sanitaryware, spas, industrial, roofing sheets\n"
                        "  THIN GAUGE (<=1.5mm) → AM or FCS series: PET, HIPS, PP thin, PS, "
                        "food trays, cups, lids, blisters, disposable packaging\n\n"
                        "IMPORTANT: PC (polycarbonate) is ALWAYS thick gauge → PF1. Never AM/FCS.\n"
                        "Be specific to THEIR products. Keep it to 3-5 lines, plain text."
                    ),
                }],
                temperature=0.5,
                max_tokens=300,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.debug("Prometheus product fit failed for %s: %s", company, e)
            return ""

    # ------------------------------------------------------------------
    # Step 5c: Tyche regional data — conversion rates for this region
    # ------------------------------------------------------------------

    def _tyche_regional_data(self, country: str) -> str:
        """Pull pipeline analytics for this region to inform the sales approach."""
        if not CRM_DB.exists():
            return ""

        try:
            conn = sqlite3.connect(str(CRM_DB))
            conn.row_factory = sqlite3.Row

            total = conn.execute(
                "SELECT COUNT(*) as n FROM leads WHERE country = ?", (country,)
            ).fetchone()["n"]
            contacted = conn.execute(
                "SELECT COUNT(*) as n FROM leads WHERE country = ? AND deal_stage = 'contacted'",
                (country,),
            ).fetchone()["n"]
            won = conn.execute(
                "SELECT COUNT(*) as n FROM leads WHERE country = ? AND deal_stage = 'won'",
                (country,),
            ).fetchone()["n"]
            lost = conn.execute(
                "SELECT COUNT(*) as n FROM leads WHERE country = ? AND deal_stage = 'lost'",
                (country,),
            ).fetchone()["n"]
            replied = conn.execute(
                "SELECT COUNT(*) as n FROM leads WHERE country = ? AND emails_received > 0",
                (country,),
            ).fetchone()["n"]
            sent_total = conn.execute(
                "SELECT COALESCE(SUM(emails_sent), 0) as n FROM leads WHERE country = ?",
                (country,),
            ).fetchone()["n"]

            conn.close()

            if total == 0:
                return ""

            parts = [f"PIPELINE DATA FOR {country.upper()}:"]
            parts.append(f"  Total leads: {total}")
            parts.append(f"  Contacted: {contacted}")
            if won + lost > 0:
                win_rate = won / (won + lost) * 100
                parts.append(f"  Win rate: {win_rate:.0f}% ({won}W/{lost}L)")
            if sent_total > 0:
                reply_rate = replied / total * 100 if total > 0 else 0
                parts.append(f"  Reply rate: {reply_rate:.0f}% ({replied}/{total} leads replied)")

            return "\n".join(parts)

        except Exception as e:
            logger.debug("Tyche regional data failed for %s: %s", country, e)
            return ""

    # ------------------------------------------------------------------
    # Step 5: Proof stories — relevant references
    # ------------------------------------------------------------------

    def _get_proof_stories(self, country: str) -> str:
        # RULES: Never mention ALP Group (blacklisted). Never mention OEM names.
        # Provide stories across DIFFERENT materials so the LLM can pick the relevant one.
        stories = [
            f"FLAGSHIP (PS, large format): {DUTCH_TIDES_STORY}",
            "AUTOMOTIVE (thick gauge): We supply PF1-C machines to Indian automotive "
            "manufacturers producing dashboard panels, door trims, and structural "
            "components in 2-6mm ABS and PP.",
            "PACKAGING (thin gauge): Our AM series runs at Indian packaging companies "
            "producing food trays, cups, and containers in PET/HIPS/PP at high speed.",
            "CAR MATS: Our ATF roll-fed and PF1-M (car mat specific) machines produce "
            "automotive floor mats and trunk liners. Multiple Indian car mat manufacturers "
            "use Machinecraft ATF machines.",
            "SANITARYWARE: PF1 machines producing bathtubs, shower trays, and spa shells "
            "in 4-8mm acrylic and ABS at facilities in India and the Middle East.",
            "ROOFING/PC SHEETS: PF1-C machines forming polycarbonate and UPVC roofing "
            "profiles and sheets at Indian roofing manufacturers.",
            "IMG (automotive interiors): IMG series for in-mold graining of textured "
            "automotive interior panels — dashboard skins, door panel skins with "
            "Class-A grain finish in TPO.",
        ]

        # Cadmus case studies
        if CASE_STUDIES_INDEX.exists():
            try:
                index = json.loads(CASE_STUDIES_INDEX.read_text())
                for cs in index if isinstance(index, list) else index.get("case_studies", []):
                    one_liner = cs.get("anonymous_one_liner") or cs.get("one_liner", "")
                    if one_liner:
                        stories.append(f"CASE STUDY: {one_liner}")
            except Exception:
                pass

        # Regional references
        country_lower = country.lower()
        if "india" in country_lower:
            stories.append(
                "INDIA: Machines installed across India — automotive, packaging, "
                "sanitaryware, roofing, luggage, and industrial applications."
            )
        elif any(r in country_lower for r in ("germany", "austria", "switzerland")):
            stories.append(
                "DACH: CE-certified machines across Germany, Austria, Netherlands. "
                "Technology partnership with European integrators."
            )
        elif any(r in country_lower for r in ("netherlands", "belgium")):
            stories.append(
                "BENELUX: Dutch Tides (Netherlands) runs our flagship PF1-X-6520."
            )

        stories.append(
            "\nRULE: Pick the proof story that matches the prospect's MATERIAL and "
            "APPLICATION. If they make PC roofing, use the roofing story. If they make "
            "car mats, use the car mat story. If they make food trays, use the packaging "
            "story. NEVER use an irrelevant material example."
        )

        return "\n".join(stories)

    # ------------------------------------------------------------------
    # Step 6: LLM synthesis — the "board meeting"
    # ------------------------------------------------------------------

    def _synthesize_guidance(
        self, company: str, country: str, research: Dict[str, Any]
    ) -> Dict[str, str]:
        """LLM sees all research and decides the best angle for the email."""
        defaults = {
            "news_hook": "",
            "personal_hook": "",
            "company_insight": "",
            "machine_recommendation": "",
            "proof_point": DUTCH_TIDES_STORY,
            "subject_line": "",
        }

        if not _OPENAI_AVAILABLE:
            return defaults

        context_parts = [f"COMPANY: {company} ({country})"]
        if research.get("website_scrape"):
            context_parts.append(
                f"\nCOMPANY WEBSITE (scraped directly — THIS IS THE GROUND TRUTH about what they do):\n"
                f"{research['website_scrape'][:2000]}"
            )
        if research.get("company_research"):
            context_parts.append(f"\nWEB SEARCH RESULTS (may match wrong entity — trust website over this):\n{research['company_research']}")
        if research.get("product_fit"):
            context_parts.append(f"\nPRODUCT FIT ANALYSIS (Prometheus — specific thermoformable products):\n{research['product_fit']}")
        if research["company_news"]:
            context_parts.append(f"\nCOMPANY NEWS (recent):\n{research['company_news']}")
        if research.get("gmail_history"):
            context_parts.append(
                f"\nGMAIL HISTORY (actual email threads — THIS IS THE MOST RELIABLE source "
                f"of what we discussed, quoted, sold, or installed):\n{research['gmail_history']}"
            )
        if research["crm_history"]:
            context_parts.append(f"\nCRM HISTORY (database records):\n{research['crm_history']}")
        if research["archive_docs"]:
            context_parts.append(f"\nARCHIVE DOCUMENTS (past quotes/proposals):\n{research['archive_docs']}")
        if research.get("archive_deep"):
            context_parts.append(f"\nQUOTE CONTENT (extracted from past PDFs):\n{research['archive_deep']}")
        if research["company_profile"]:
            context_parts.append(f"\nCOMPANY PROFILE (from our CRM):\n{research['company_profile']}")
        if research.get("regional_intel"):
            context_parts.append(f"\nREGIONAL PIPELINE DATA (Tyche):\n{research['regional_intel']}")
        if research["proof_stories"]:
            context_parts.append(f"\nAVAILABLE PROOF STORIES:\n{research['proof_stories']}")

        system = (
            "You are helping Rushabh Doshi, Sales Head at Machinecraft Technologies, prepare "
            "a sales email. Rushabh writes like a real person — warm, direct, no corporate "
            "fluff. He says 'Hi!' not 'Dear Sir'. He keeps it conversational.\n\n"
            "Given research about a prospect, synthesize the best angle.\n\n"
            "ABSOLUTE RULES — VIOLATING THESE IS A CRITICAL ERROR:\n\n"
            "1. NEVER FABRICATE PURCHASE HISTORY.\n"
            "   - ONLY say 'you bought X from us' if the COMPANY PROFILE section explicitly "
            "says 'Past Machinecraft customer' and lists what they 'Previously purchased'.\n"
            "   - If the CRM profile does NOT say 'Past Machinecraft customer', they are a LEAD, "
            "not a customer. Never claim they bought anything from Machinecraft.\n"
            "   - If a conversation mentions a machine model (e.g. 'PF1-3030' in a subject line), "
            "that does NOT mean they bought it from us. It could be a competitor's machine.\n\n"
            "2. NEVER MENTION THESE:\n"
            "   - ALP Group — blacklisted company, never reference them\n"
            "   - OEM names (Mahindra, Maruti, Tata, etc.) — never name-drop OEM customers\n"
            "   - Instead say 'a leading Indian automotive manufacturer' or 'a major OEM'\n\n"
            "3. MACHINE RECOMMENDATION — MATERIAL & APPLICATION ROUTING:\n"
            "   THICK GAUGE (>1.5mm) → PF1 series (PF1-C preferred in India):\n"
            "   - PC (polycarbonate), ABS, HDPE, PP thick, PMMA, ASA\n"
            "   - Luggage, sanitaryware, spas, bathtubs, industrial housings\n"
            "   - Roofing sheets, polycarbonate sheets, FRP components\n\n"
            "   THIN GAUGE (<=1.5mm) → AM or FCS series:\n"
            "   - PET, HIPS, PP thin, PS for packaging\n"
            "   - Food trays, cups, lids, blisters, clamshells, disposable containers\n"
            "   - Storage baskets, lightweight packaging of any kind\n\n"
            "   AUTOMOTIVE INTERIOR (dashboards, door panels, pillar trims, instrument panels):\n"
            "   - IMG series (in-mold graining) for textured grain surfaces in TPO\n"
            "   - Vacuum lamination for soft-touch interiors\n"
            "   - Standard PF1 CANNOT do automotive interior — it needs modified tooling\n"
            "   - Only recommend PF1 for automotive if it's non-interior cosmetic parts "
            "(e.g. bedliners, fender liners, wheel arch covers, underbody shields)\n\n"
            "   If they bought an AM or INP machine → they are packaging. Recommend AM/FCS.\n"
            "   If they bought a PF1 machine → they are thick gauge. Recommend PF1.\n\n"
            "4. INDIA MARKET PREFERENCES:\n"
            "   - Indian customers prefer PF1-C (pneumatic) over PF1-X (all-servo) — more affordable.\n"
            "   - Only recommend PF1-X if they need servo precision or very large forming areas.\n"
            "   - For Indian packaging companies, AM series is the standard.\n\n"
            "5. PF1 series does VACUUM FORMING only. Never mention pressure forming for PF1.\n\n"
            "6. If unsure what they make, say so — don't guess.\n\n"
            "7. CHECK CONTACT VALIDITY: If LinkedIn data shows the contact no longer works at "
            "the company, note that in the output.\n\n"
            "8. PAST CUSTOMERS vs NEW LEADS — DIFFERENT TONE:\n"
            "   If COMPANY PROFILE says 'Past Machinecraft customer':\n"
            "   - Reference the EXACT machine they bought and ask how it's running\n"
            "   - Mention the city/facility if known\n"
            "   - Tone: reconnecting with someone you know, not selling cold\n"
            "   - Suggest upgrades, add-ons, or new machines for new applications\n"
            "   If they are a NEW LEAD (no purchase history):\n"
            "   - Tone: introducing yourself based on research\n"
            "   - Never pretend you know them if you don't\n\n"
            "9. GMAIL HISTORY IS GOLD:\n"
            "   If GMAIL HISTORY shows past email threads, READ THEM CAREFULLY.\n"
            "   - What did they ask about? What machine were they interested in?\n"
            "   - What was quoted? What was discussed?\n"
            "   - Reference these specifics in the email.\n"
            "   - If they asked about car mats → recommend ATF/PF1-M, not PF1-C.\n"
            "   - If they asked about packaging → recommend AM/FCS, not PF1.\n\n"
            "10. PROOF STORY MUST MATCH MATERIAL:\n"
            "   - If prospect works with PC → use the roofing/PC story\n"
            "   - If prospect makes car mats → use the car mat story\n"
            "   - If prospect does packaging → use the packaging story\n"
            "   - NEVER use an HDPE example for a PC company or vice versa\n\n"
            "Return valid JSON with these fields:\n"
            "- news_hook: A casual, specific opening. Never generic.\n"
            "- personal_hook: For past customers, reference their machine and facility. "
            "For new leads with Gmail history, reference what they asked about. Empty if neither.\n"
            "- company_insight: One sentence about what they ACTUALLY make.\n"
            "- machine_recommendation: Which machine fits based on routing rules AND "
            "Gmail history (what they asked about). For auto OEM suppliers → IMG series. "
            "For car mat companies → ATF/PF1-M.\n"
            "- proof_point: Most relevant proof story matching their MATERIAL. "
            "NEVER mention ALP Group or OEM names.\n"
            "- subject_line: Short, curiosity-driven. Reference their products.\n"
        )

        try:
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": "\n".join(context_parts)},
                ],
                temperature=0.7,
                max_tokens=800,
            )
            result = json.loads(response.choices[0].message.content)
            for key in defaults:
                if result.get(key):
                    defaults[key] = result[key]
            return defaults

        except Exception as e:
            logger.warning("Board meeting synthesis failed for %s: %s", company, e)
            return defaults


# Singleton
_researcher: Optional[BoardMeetingResearcher] = None


def get_researcher() -> BoardMeetingResearcher:
    global _researcher
    if _researcher is None:
        _researcher = BoardMeetingResearcher()
    return _researcher
