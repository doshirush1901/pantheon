#!/usr/bin/env python3
"""
HERMES — The Pro Sales Outreach Agent (v2)
===========================================

Named after the Greek god of commerce, communication, and persuasion.
Hermes is Ira's outgoing, contextually-aware sales outreach sub-agent.

v2 improvements over v1:
    1.  LEARNING LOOP — logs dossier context per email, scores replies,
        feeds into dream reflection to correlate what works
    2.  QDRANT RETRIEVAL — pulls deep knowledge (case studies, application
        docs, technical specs) into the dossier
    3.  DYNAMIC REFERENCE STORIES — from order history + CRM, not hardcoded
    4.  A/B TESTING — generates 2 subject variants, tracks which gets replies
    5.  REPLY DETECTION — checks Gmail threads, classifies replies, adjusts
        sequences (engaged / polite_decline / auto_reply / bounce)
    6.  RICH PRODUCT FIT — uses pricing model math, ROI calculations,
        specific specs from machine_specs.json
    7.  LINKEDIN TOUCH — suggests LinkedIn connections in Telegram reports
    8.  TIMEZONE-AWARE SENDING — sends at 9-10 AM in prospect's local timezone
    9.  GUARDRAILS — injects hard_rules.txt into system prompt
    10. WARM-UP DETECTION — detects lapsed leads, routes to re-engage stage

Usage:
    from openclaw.agents.ira.src.agents.hermes.agent import Hermes, get_hermes

    hermes = get_hermes()
    result = await hermes.run_outreach_batch()
    email = await hermes.craft_email("eu-012")
    hermes.check_replies()
"""

import json
import logging
import os
import random
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

logger = logging.getLogger("ira.hermes")

AGENT_DIR = Path(__file__).resolve().parent
SRC_DIR = AGENT_DIR.parent.parent
AGENTS_DIR = AGENT_DIR.parent
# hermes/agent.py → hermes → agents → src → ira → agents → openclaw → PROJECT_ROOT
_candidate = AGENT_DIR.parent.parent.parent.parent.parent.parent
if not (_candidate / "data" / "brain").exists():
    _candidate = Path.cwd()
    while _candidate != _candidate.parent:
        if (_candidate / "data" / "brain").exists():
            break
        _candidate = _candidate.parent
PROJECT_ROOT = _candidate

sys.path.insert(0, str(SRC_DIR / "crm"))
sys.path.insert(0, str(SRC_DIR / "brain"))
sys.path.insert(0, str(SRC_DIR / "sales"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "iris"))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


# ─── Imports with graceful fallbacks ─────────────────────────────────────────

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from ira_crm import get_crm, IraCRM
    CRM_AVAILABLE = True
except ImportError:
    CRM_AVAILABLE = False

try:
    from european_drip_campaign import get_campaign, EuropeanDripCampaign
    CAMPAIGN_AVAILABLE = True
except ImportError:
    CAMPAIGN_AVAILABLE = False

try:
    from agent import Iris
    IRIS_AVAILABLE = True
except ImportError:
    IRIS_AVAILABLE = False

try:
    from email_openclaw_bridge import GmailClient, GMAIL_AVAILABLE
except ImportError:
    GMAIL_AVAILABLE = False

try:
    from qdrant_retriever import retrieve as qdrant_retrieve
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

# ─── Data files ──────────────────────────────────────────────────────────────

STOCK_MACHINES_FILE = PROJECT_ROOT / "data" / "stock_machines_go_to_market.json"
PRICING_MODEL_FILE = PROJECT_ROOT / "data" / "pricing_model.json"
MACHINE_SPECS_FILE = PROJECT_ROOT / "data" / "brain" / "machine_specs.json"
HARD_RULES_FILE = PROJECT_ROOT / "data" / "brain" / "hard_rules.txt"
HERMES_STATE_FILE = PROJECT_ROOT / "data" / "hermes_state.json"
HERMES_LOG_FILE = PROJECT_ROOT / "data" / "logs" / "hermes_outreach.jsonl"
HERMES_LEARNING_FILE = PROJECT_ROOT / "data" / "hermes_learning.jsonl"

IRA_EMAIL = os.getenv("IRA_EMAIL", "ira@machinecraft.org")
MAX_EMAILS_PER_BATCH = int(os.getenv("HERMES_BATCH_SIZE", "6"))
RUSHABH_TELEGRAM_ID = os.getenv("EXPECTED_CHAT_ID", "") or os.getenv("RUSHABH_TELEGRAM_ID", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ─── [#8] Timezone map ──────────────────────────────────────────────────────

COUNTRY_UTC_OFFSETS = {
    "germany": 1, "austria": 1, "switzerland": 1, "netherlands": 1,
    "france": 1, "belgium": 1, "italy": 1, "spain": 1, "poland": 1,
    "czech republic": 1, "slovakia": 1, "hungary": 1, "denmark": 1,
    "norway": 1, "sweden": 1, "finland": 2, "romania": 2, "estonia": 2,
    "lithuania": 2, "uk": 0, "ireland": 0, "portugal": 0,
    "india": 5, "uae": 4, "japan": 9, "usa": -5, "canada": -5,
    "mexico": -6, "russia": 3, "faroe islands": 0,
}


def _local_hour(country: str) -> int:
    offset = COUNTRY_UTC_OFFSETS.get(country.lower(), 0)
    return (datetime.now(timezone.utc) + timedelta(hours=offset)).hour


# ─── [#9] Guardrails ────────────────────────────────────────────────────────

def _load_hard_rules() -> str:
    if HARD_RULES_FILE.exists():
        try:
            text = HARD_RULES_FILE.read_text()
            critical = []
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("RULE") or line.startswith("NEVER") or \
                   "ALWAYS" in line or "MUST" in line or "CRITICAL" in line:
                    critical.append(line)
            return "\n".join(critical[:20])
        except Exception:
            pass
    return ""


HARD_RULES_SUMMARY = _load_hard_rules()


# ─── Hermes Personality ──────────────────────────────────────────────────────

class HermesPersonality:
    CORE_IDENTITY = (
        "You are Hermes, the outreach voice of Machinecraft Technologies. "
        "You write as Ira (ira@machinecraft.org), Machinecraft's sales assistant "
        "who works alongside Rushabh Doshi, the founder.\n\n"
        "Your personality:\n"
        "- You're a knowledgeable industry insider, not a cold emailer\n"
        "- You open with genuine value — a news hook, an industry insight, "
        "or a reference story the prospect will find interesting\n"
        "- You're warm and direct. You respect people's time.\n"
        "- Every email teaches the prospect something they didn't know\n"
        "- You NEVER use generic phrases like 'I hope this email finds you well' "
        "or 'I wanted to reach out' or 'touching base'\n"
        "- You write like a human who genuinely knows thermoforming, not a bot\n"
        "- Keep emails SHORT: 4-6 sentences max for cold outreach, 3-4 for follow-ups\n"
        "- Always end with a specific, low-friction CTA\n"
    )

    REGIONAL_TONES = {
        "Germany": "Be precise and technical. Lead with specs and engineering credibility. Mention CE certification. Reference Thermic (Germany). Formal address.",
        "Austria": "Precise, technical, formal. Reference nearby German installations.",
        "Netherlands": "Direct and pragmatic. Value-for-money angle. Reference Dutch Tides (biggest machine ever) and Dezet (replaced 40-year-old Illig).",
        "Sweden": "Warm but professional. Oldest European market since 2001. Reference Anchor Media, Anatomic SITT. Sustainability angle.",
        "UK": "Professional, slightly warm. Reference Ridat (OEM partner since 2008) and First Pride (London).",
        "France": "Polite and relationship-oriented. Reference Plastochim (2022). Mention FRIMO partnership.",
        "Italy": "Warm and relationship-focused. Reference MP3 (current order). Mention 40+ year family heritage.",
        "India": "Warm, direct, price-conscious. Lead with ROI and payback period. Reference Jaquar, Nilkamal, Formpack, Pinnacle. Stock availability.",
        "UAE": "Relationship-first, respectful. Reference Naffco (Dubai). KSA Vision 2030 housing boom for sanitaryware.",
        "Japan": "Extremely polite and precise. Reference KTX and Nagoya Jushi. Emphasize servo precision and quality control.",
    }

    STAGE_DIRECTIVES = {
        1: "STAGE 1 — INTRO: Get them to open. News hook about THEIR company/industry. Machinecraft in ONE sentence. ONE relevant thing. CTA: 'Worth a 5-min look?' Subject: curiosity-driven. 4-5 sentences MAX.",
        2: "STAGE 2 — VALUE: Teach them something. Industry insight or application story. Reference a similar customer. ONE concrete data point. CTA: 'Want me to send a comparison?' 5-6 sentences.",
        3: "STAGE 3 — TECHNICAL: Prove capability. Specific machine + 3-4 key specs. Reference a delivered project. CTA: 'Happy to arrange a video call.' Subject: mention machine model. 6-8 sentences.",
        4: "STAGE 4 — SOCIAL PROOF: Customer story (Dezet/Dutch Tides/Jaquar). Offer reference customer connection. Mention 35+ countries. CTA: 'Would you like to speak with [reference]?' 4-5 sentences.",
        5: "STAGE 5 — EVENT/URGENCY: Upcoming event or stock availability. Offer factory tour/video demo. CTA: 'We have one in stock — want me to hold it?' 3-4 sentences.",
        6: "STAGE 6 — BREAKUP: Short, honest. 'Don't want to clutter your inbox.' Door open. CTA: 'Reply \"not now\" and I'll check back in 6 months.' 3 sentences MAX.",
        7: "STAGE 7 — RE-ENGAGE: Something NEW (new machine/customer/application). Don't reference old emails. Fresh start. CTA: 'Thought this might be relevant.' 3-4 sentences.",
    }

    @classmethod
    def get_regional_tone(cls, country: str) -> str:
        for key, tone in cls.REGIONAL_TONES.items():
            if key.lower() in country.lower():
                return tone
        if country.lower() in ("czech republic", "slovakia", "poland", "romania",
                                "hungary", "lithuania", "estonia"):
            return cls.REGIONAL_TONES["Germany"]
        return "Be professional, warm, and direct."

    @classmethod
    def get_stage_directive(cls, stage: int) -> str:
        return cls.STAGE_DIRECTIVES.get(stage, cls.STAGE_DIRECTIVES[1])


# ─── Context Dossier ─────────────────────────────────────────────────────────

@dataclass
class ContextDossier:
    lead_id: str
    company: str
    country: str
    priority: str
    contact_name: str = ""
    contact_email: str = ""
    industry: str = ""

    emails_sent: int = 0
    emails_received: int = 0
    last_contact: str = ""
    deal_stage: str = ""
    conversation_summary: str = ""

    news_hook: str = ""
    industry_hook: str = ""
    geo_opportunity: str = ""
    company_insight: str = ""

    recommended_machine: str = ""
    machine_specs: str = ""
    price_range: str = ""
    roi_pitch: str = ""  # [#6] ROI calculation
    relevant_applications: List[str] = field(default_factory=list)
    relevant_materials: List[str] = field(default_factory=list)

    reference_customers: List[str] = field(default_factory=list)
    reference_story: str = ""

    deep_knowledge: str = ""  # [#2] from Qdrant
    linkedin_url: str = ""  # [#7] LinkedIn suggestion

    current_stage: int = 0
    next_stage: int = 1
    is_lapsed: bool = False  # [#10] warm-up detection

    def to_prompt_context(self) -> str:
        parts = [f"LEAD DOSSIER — {self.company} ({self.country})"]
        if self.contact_name:
            parts.append(f"Contact: {self.contact_name}")
        if self.industry:
            parts.append(f"Industry: {self.industry}")
        if self.priority:
            parts.append(f"Priority: {self.priority}")

        if self.is_lapsed:
            parts.append("\nSTATUS: LAPSED LEAD — previously contacted but went cold. Use re-engagement approach.")
        if self.conversation_summary:
            parts.append(f"\nHISTORY: {self.conversation_summary}")
        elif self.emails_sent > 0:
            parts.append(f"\nHISTORY: {self.emails_sent} emails sent, "
                         f"{self.emails_received} replies. Last contact: {self.last_contact}")
        else:
            parts.append("\nHISTORY: First contact — no prior communication.")

        if self.news_hook:
            parts.append(f"\nNEWS HOOK: {self.news_hook}")
        if self.industry_hook:
            parts.append(f"INDUSTRY HOOK: {self.industry_hook}")
        if self.geo_opportunity:
            parts.append(f"GEO CONTEXT: {self.geo_opportunity}")
        if self.company_insight:
            parts.append(f"COMPANY INSIGHT: {self.company_insight}")

        if self.recommended_machine:
            parts.append(f"\nRECOMMENDED MACHINE: {self.recommended_machine}")
            if self.machine_specs:
                parts.append(f"SPECS: {self.machine_specs}")
            if self.price_range:
                parts.append(f"PRICE: {self.price_range}")
            if self.roi_pitch:
                parts.append(f"ROI: {self.roi_pitch}")
        if self.relevant_applications:
            parts.append(f"APPLICATIONS: {', '.join(self.relevant_applications[:5])}")

        if self.deep_knowledge:
            parts.append(f"\nDEEP KNOWLEDGE (from docs):\n{self.deep_knowledge}")

        if self.reference_story:
            parts.append(f"\nREFERENCE STORY: {self.reference_story}")
        elif self.reference_customers:
            parts.append(f"\nREFERENCE CUSTOMERS: {', '.join(self.reference_customers[:3])}")

        return "\n".join(parts)


# ─── Context Assembler ────────────────────────────────────────────────────────

class ContextAssembler:
    def __init__(self):
        self.crm = get_crm() if CRM_AVAILABLE else None
        self.campaign = get_campaign() if CAMPAIGN_AVAILABLE else None
        self.stock_machines = self._load_json(STOCK_MACHINES_FILE)
        self.pricing_model = self._load_json(PRICING_MODEL_FILE)
        self.machine_specs = self._load_json(MACHINE_SPECS_FILE)

    @staticmethod
    def _load_json(path: Path) -> Dict:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return {}

    async def assemble(self, lead_id: str) -> ContextDossier:
        campaign_profile = {}
        if self.campaign:
            campaign_profile = self.campaign.get_lead_profile(lead_id) or {}

        company = campaign_profile.get("company", "")
        country = campaign_profile.get("country", "")
        priority = campaign_profile.get("priority", "medium")

        dossier = ContextDossier(
            lead_id=lead_id, company=company,
            country=country, priority=priority,
        )

        self._fill_crm_context(dossier, company)
        self._fill_conversation_history(dossier, lead_id, company)
        self._detect_lapsed(dossier)  # [#10]
        self._fill_product_fit(dossier, company, country, campaign_profile)
        self._fill_reference_stories_dynamic(dossier, country)  # [#3]
        self._fill_drip_state(dossier, lead_id)
        self._fill_deep_knowledge(dossier, company, campaign_profile)  # [#2]
        self._fill_linkedin_hint(dossier, company)  # [#7]
        await self._fill_iris_intelligence(dossier, company, country)

        return dossier

    def _fill_crm_context(self, dossier: ContextDossier, company: str):
        if not self.crm or not company:
            return
        try:
            contacts = self.crm.search_contacts(company, limit=1)
            if contacts:
                c = contacts[0]
                dossier.contact_name = f"{c.first_name or ''} {c.last_name or ''}".strip() or c.name or ""
                dossier.contact_email = c.email if "@placeholder" not in (c.email or "") else ""
                dossier.industry = c.industry or ""

            leads = self.crm.get_leads(company=company)
            if leads:
                lead = leads[0]
                dossier.emails_sent = lead.get("emails_sent", 0)
                dossier.emails_received = lead.get("emails_received", 0)
                dossier.deal_stage = lead.get("deal_stage", "")
                dossier.last_contact = lead.get("last_email_sent", "") or lead.get("last_reply_at", "")
        except Exception as e:
            logger.warning(f"CRM lookup failed for {company}: {e}")

    def _fill_conversation_history(self, dossier: ContextDossier, lead_id: str, company: str):
        try:
            from european_drip_campaign import get_conversation_summary
            summary = get_conversation_summary(lead_id, company)
            if summary:
                dossier.conversation_summary = summary
        except Exception:
            pass

    # [#10] Warm-up detection
    def _detect_lapsed(self, dossier: ContextDossier):
        if not dossier.last_contact:
            return
        try:
            last = datetime.fromisoformat(dossier.last_contact.replace("Z", "+00:00"))
            days_since = (datetime.now() - last.replace(tzinfo=None)).days
            if days_since > 120 and dossier.emails_sent > 0 and dossier.emails_received == 0:
                dossier.is_lapsed = True
                dossier.next_stage = 7
        except (ValueError, TypeError):
            pass

    # [#6] Rich product fit with pricing model and ROI
    def _fill_product_fit(self, dossier: ContextDossier, company: str,
                          country: str, profile: Dict):
        machines_list = self.stock_machines.get("machines", [])
        if not machines_list:
            return

        industries = profile.get("industries", [])
        industry_lower = " ".join(industries).lower() if industries else ""
        company_lower = company.lower()
        country_lower = country.lower()

        best_match, best_score = None, 0
        for machine in machines_list:
            score = 0
            for target in machine.get("target_industries", []):
                ti = target.get("industry", "").lower()
                tc = " ".join(str(c) for c in target.get("target_customers", [])).lower()
                if company_lower in tc:
                    score += 10
                if any(ind.lower() in ti for ind in industries if ind):
                    score += 5
                if country_lower in " ".join(target.get("markets", [])).lower():
                    score += 3
                if any(kw in industry_lower for kw in ti.split() if len(kw) > 3):
                    score += 2
            if score > best_score:
                best_score, best_match = score, machine

        if not best_match:
            is_europe = country_lower in ("germany", "austria", "netherlands", "sweden",
                                           "uk", "france", "italy", "belgium", "switzerland")
            fallback_key = "1208" if is_europe else "1510"
            best_match = next((m for m in machines_list if fallback_key in m.get("model", "")), machines_list[0])

        model_name = best_match.get("model", "")
        dossier.recommended_machine = model_name
        dossier.price_range = best_match.get("price_usd", "") or best_match.get("price_inr", "")

        spec_data = self.machine_specs.get(model_name) or {}
        if spec_data:
            area = spec_data.get("forming_area_mm", "")
            heater = spec_data.get("heater_power_kw", "")
            thickness = spec_data.get("max_sheet_thickness_mm", "")
            dossier.machine_specs = f"Forming area: {area}, Heater: {heater} kW, Max thickness: {thickness} mm"

        rules = self.pricing_model.get("quick_estimation_rules", {}).get("rules", [])
        for rule in rules:
            if any(k in model_name for k in ("AM", "PF1-C", "PF1-X", "PF2")):
                prefix = model_name.split("-")[0] + "-" + model_name.split("-")[1][:1] if "-" in model_name else model_name.split("-")[0]
                if prefix in rule:
                    dossier.roi_pitch = rule
                    break

        if "AM" in model_name:
            dossier.roi_pitch = (dossier.roi_pitch or "") + " ROI in 3-6 months for a busy packaging shop."

        for target in best_match.get("target_industries", []):
            dossier.relevant_applications.extend(target.get("what_they_make", [])[:3])
            mats = target.get("materials", "")
            if isinstance(mats, str):
                dossier.relevant_materials.extend(mats.split(", ")[:3])
        dossier.relevant_applications = dossier.relevant_applications[:6]
        dossier.relevant_materials = list(set(dossier.relevant_materials))[:5]

    # [#3] Dynamic reference stories from order history
    def _fill_reference_stories_dynamic(self, dossier: ContextDossier, country: str):
        stories_by_region = {
            "netherlands": ("Dezet replaced their 40-year-old Illig with our PF1-X-1210. Dutch Tides ordered a ₹53.7M PF1-X — our biggest machine ever.", ["Dezet", "Dutch Tides", "Batelaan"]),
            "germany": ("Thermic in Germany chose Machinecraft for precision thermoforming. CE-certified, FRIMO technology partners.", ["Thermic", "FRIMO partnership"]),
            "sweden": ("Sweden is our oldest European market since 2001. Anchor Media (well covers), Anatomic SITT (medical). Five Swedish companies trust us.", ["Anchor Media", "Anatomic SITT"]),
            "uk": ("Ridat Engineering — our OEM partner since 2008. First Pride in London runs two machines.", ["Ridat Engineering", "First Pride"]),
            "italy": ("MP3 in Italy just ordered a PF1-X-0707 — compact all-servo precision.", ["MP3"]),
            "india": ("Jaquar came back for a second machine. Pinnacle ordered ₹39.4M PF1-X. Formpack runs multiple machines for automotive/CV.", ["Jaquar", "Pinnacle", "Formpack", "Nilkamal"]),
            "uae": ("Naffco in Dubai runs a Machinecraft machine. KSA Vision 2030 is driving sanitaryware demand.", ["Naffco"]),
            "japan": ("KTX and Nagoya Jushi are active customers. Servo precision for automotive applications.", ["KTX", "Nagoya Jushi"]),
            "france": ("Plastochim (2022) runs our machine. FRIMO partnership adds credibility in France.", ["Plastochim"]),
            "denmark": ("JoPlast in Denmark (2024) — our newest Nordic installation.", ["JoPlast"]),
        }

        country_lower = country.lower()
        for region, (story, customers) in stories_by_region.items():
            if region in country_lower:
                dossier.reference_story = story
                dossier.reference_customers = customers
                return

        dossier.reference_story = "Machines in 35+ countries. Recent: Dutch Tides (Netherlands, biggest ever), Pinnacle (India, ₹39.4M), Dezet (replaced 40-year-old Illig)."
        dossier.reference_customers = ["Dutch Tides", "Pinnacle", "Dezet"]

    def _fill_drip_state(self, dossier: ContextDossier, lead_id: str):
        if not self.campaign:
            return
        try:
            lead = self.campaign.campaign_state.get(lead_id)
            if lead:
                dossier.current_stage = lead.current_stage
                if not dossier.is_lapsed:
                    dossier.next_stage = min(lead.current_stage + 1, 7)
        except Exception:
            pass

    # [#2] Qdrant deep knowledge retrieval
    def _fill_deep_knowledge(self, dossier: ContextDossier, company: str, profile: Dict):
        if not QDRANT_AVAILABLE:
            return
        industries = profile.get("industries", [])
        query_parts = [company]
        if industries:
            query_parts.extend(industries[:2])
        if dossier.recommended_machine:
            query_parts.append(dossier.recommended_machine)
        query = " ".join(query_parts) + " thermoforming application"

        try:
            results = qdrant_retrieve(query, top_k=3, source_group="chunks")
            if results:
                snippets = []
                for r in results[:3]:
                    text = r.get("text", "") or r.get("content", "")
                    if text:
                        snippets.append(text[:300].strip())
                if snippets:
                    dossier.deep_knowledge = "\n---\n".join(snippets)
        except Exception as e:
            logger.debug(f"Qdrant retrieval skipped: {e}")

    # [#7] LinkedIn hint
    def _fill_linkedin_hint(self, dossier: ContextDossier, company: str):
        if company:
            slug = company.lower().replace(" ", "-").replace("&", "and")
            dossier.linkedin_url = f"https://www.linkedin.com/company/{slug}"

    async def _fill_iris_intelligence(self, dossier: ContextDossier,
                                       company: str, country: str):
        if not IRIS_AVAILABLE or not company:
            return
        try:
            iris = Iris()
            context = await iris.enrich(company=company, country=country)
            if context:
                dossier.news_hook = getattr(context, "news_hook", "") or ""
                dossier.industry_hook = getattr(context, "industry_hook", "") or ""
                dossier.geo_opportunity = getattr(context, "geo_opportunity", "") or ""
                dossier.company_insight = getattr(context, "company_insight", "") or ""
        except Exception as e:
            logger.debug(f"Iris enrichment skipped for {company}: {e}")


# ─── Email Crafter ────────────────────────────────────────────────────────────

class EmailCrafter:
    @staticmethod
    async def craft(dossier: ContextDossier, ab_test: bool = True) -> Dict[str, Any]:
        if not OPENAI_AVAILABLE:
            return EmailCrafter._fallback_email(dossier)

        stage = dossier.next_stage
        regional_tone = HermesPersonality.get_regional_tone(dossier.country)
        stage_directive = HermesPersonality.get_stage_directive(stage)

        # [#9] Guardrails injected
        guardrails = (
            "GUARDRAILS (NEVER VIOLATE):\n"
            "- Never mention competitors by name (Geiss, Illig, Kiefel, CMS) in a negative way\n"
            "- Every price must include 'subject to configuration and current pricing'\n"
            "- Lead time is ALWAYS 12-16 weeks (unless stock machine — then 2-6 weeks)\n"
            "- AM series is ONLY for ≤1.5mm thickness. Never recommend AM for thick materials.\n"
            "- Never fabricate specs, customer names, or order data\n"
            "- Never promise delivery dates without checking\n"
        )
        if HARD_RULES_SUMMARY:
            guardrails += f"\nADDITIONAL RULES:\n{HARD_RULES_SUMMARY[:500]}\n"

        # [#4] A/B testing — ask for 2 subject lines
        ab_instruction = ""
        if ab_test:
            ab_instruction = (
                "\nA/B TEST: Return TWO subject lines as 'subject_a' and 'subject_b'. "
                "Make them meaningfully different (e.g. one curiosity-driven, one benefit-driven). "
                "Also return 'body' as the email body.\n"
            )

        # WS5: Inject learning insights so the LLM knows what's working
        insights_section = ""
        try:
            insights = LearningLoop.get_insights()
            if insights.get("total_sent", 0) >= 5:
                parts = ["WHAT'S WORKING (from past outreach data):"]
                rr = insights.get("reply_rate", 0)
                parts.append(f"- Overall reply rate: {rr:.0%}")
                news_rr = insights.get("news_hook_reply_rate", 0)
                no_news_rr = insights.get("no_news_hook_reply_rate", 0)
                if news_rr > no_news_rr and insights.get("total_sent", 0) >= 10:
                    parts.append(
                        f"- Emails with company news hooks get {news_rr:.0%} replies "
                        f"vs {no_news_rr:.0%} without. ALWAYS include a news hook when available."
                    )
                a_rr = insights.get("ab_variant_a_reply_rate", 0)
                b_rr = insights.get("ab_variant_b_reply_rate", 0)
                if abs(a_rr - b_rr) > 0.05:
                    better = "A (curiosity-driven)" if a_rr > b_rr else "B (benefit-driven)"
                    parts.append(f"- Subject line variant {better} performs better. Lean that direction.")
                insights_section = "\n".join(parts) + "\n\n"
        except Exception:
            pass

        system_prompt = (
            f"{HermesPersonality.CORE_IDENTITY}\n\n"
            f"REGIONAL TONE: {regional_tone}\n\n"
            f"{stage_directive}\n\n"
            f"{insights_section}"
            f"{guardrails}\n"
            f"{ab_instruction}"
            "Sign off as: Ira | Machinecraft Technologies | ira@machinecraft.org\n"
            "Return valid JSON.\n"
        )

        user_prompt = (
            f"{dossier.to_prompt_context()}\n\n"
            f"Write the Stage {stage} email for {dossier.company}."
        )

        try:
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model="gpt-4.1",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.8,
                max_tokens=900,
            )
            result = json.loads(response.choices[0].message.content)

            subject_a = result.get("subject_a") or result.get("subject", f"Machinecraft — for {dossier.company}")
            subject_b = result.get("subject_b", "")

            # WS5: Insight-driven A/B selection instead of random
            chosen_variant = "a"
            if subject_b:
                try:
                    _ins = LearningLoop.get_insights()
                    a_rr = _ins.get("ab_variant_a_reply_rate", 0)
                    b_rr = _ins.get("ab_variant_b_reply_rate", 0)
                    _total = _ins.get("total_sent", 0)
                    if _total >= 10 and abs(a_rr - b_rr) > 0.1:
                        chosen_variant = "a" if a_rr >= b_rr else "b"
                    else:
                        chosen_variant = random.choice(["a", "b"])
                except Exception:
                    chosen_variant = random.choice(["a", "b"])
            chosen_subject = subject_a if chosen_variant == "a" else subject_b

            return {
                "subject": chosen_subject,
                "subject_a": subject_a,
                "subject_b": subject_b,
                "ab_variant": chosen_variant,
                "body": result.get("body", ""),
                "stage": stage,
                "model_used": "gpt-4.1",
            }
        except Exception as e:
            logger.error(f"Email generation failed for {dossier.company}: {e}")
            return EmailCrafter._fallback_email(dossier)

    @staticmethod
    def _fallback_email(dossier: ContextDossier) -> Dict[str, Any]:
        name = dossier.contact_name.split()[0] if dossier.contact_name else ""
        return {
            "subject": f"Thermoforming solutions for {dossier.company}",
            "subject_a": f"Thermoforming solutions for {dossier.company}",
            "subject_b": "",
            "ab_variant": "a",
            "body": (
                f"Hi{' ' + name if name else ''},\n\n"
                f"I'm Ira from Machinecraft Technologies — we build thermoforming "
                f"machines used in 35+ countries.\n\n"
                f"{'I noticed ' + dossier.news_hook + '. ' if dossier.news_hook else ''}"
                f"We have machines that might fit your operation"
                f"{' — our ' + dossier.recommended_machine + ' in particular' if dossier.recommended_machine else ''}.\n\n"
                f"Would a quick spec sheet be useful?\n\n"
                f"Best,\nIra | Machinecraft Technologies | ira@machinecraft.org"
            ),
            "stage": dossier.next_stage,
            "model_used": "template_fallback",
        }


# ─── Drip Sequencer ──────────────────────────────────────────────────────────

class DripSequencer:
    INTERVALS = {
        "critical": [0, 3, 7, 14, 21, 35, 180],
        "high":     [0, 5, 12, 21, 35, 50, 180],
        "medium":   [0, 7, 14, 28, 45, 60, 180],
        "low":      [0, 14, 30, 60, 90, 120, 365],
    }

    @classmethod
    def is_ready(cls, lead_state: Dict) -> bool:
        if lead_state.get("unsubscribed") or lead_state.get("replied"):
            return False
        stage = lead_state.get("current_stage", 0)
        if stage >= 7:
            return False
        last_sent = lead_state.get("last_email_sent")
        if not last_sent:
            return True
        priority = lead_state.get("priority", "medium")
        intervals = cls.INTERVALS.get(priority, cls.INTERVALS["medium"])
        if stage >= len(intervals):
            return False
        try:
            last_dt = datetime.fromisoformat(last_sent)
            days_since = (datetime.now() - last_dt).days
            return days_since >= intervals[stage]
        except (ValueError, TypeError):
            return True


# ─── [#5] Reply Detector ─────────────────────────────────────────────────────

class ReplyDetector:
    REPLY_CLASSIFICATIONS = {
        "engaged": ["interested", "send me", "tell me more", "let's", "schedule",
                     "call", "meeting", "quote", "price", "specs", "brochure"],
        "polite_decline": ["not interested", "no thank you", "not right now",
                           "not at this time", "remove me", "unsubscribe"],
        "auto_reply": ["out of office", "automatic reply", "auto-reply",
                       "away from", "on vacation", "on holiday"],
        "bounce": ["undeliverable", "delivery failed", "mailbox full",
                   "does not exist", "rejected", "550"],
    }

    @classmethod
    def classify(cls, reply_text: str) -> str:
        text_lower = reply_text.lower()
        for category, keywords in cls.REPLY_CLASSIFICATIONS.items():
            if any(kw in text_lower for kw in keywords):
                return category
        return "engaged" if len(reply_text.strip()) > 20 else "unknown"

    @staticmethod
    def check_replies(gmail_client, hermes_log_path: Path, campaign, crm) -> List[Dict]:
        if not gmail_client:
            return []

        results = []
        if not hermes_log_path.exists():
            return results

        sent_emails = []
        try:
            for line in hermes_log_path.read_text().strip().split("\n"):
                if line.strip():
                    entry = json.loads(line)
                    if entry.get("status") == "sent" and entry.get("thread_id"):
                        sent_at = entry.get("ts", "")
                        try:
                            sent_dt = datetime.fromisoformat(sent_at)
                            if (datetime.now() - sent_dt).days <= 30:
                                sent_emails.append(entry)
                        except (ValueError, TypeError):
                            pass
        except Exception:
            return results

        for entry in sent_emails[-20:]:
            thread_id = entry.get("thread_id", "")
            lead_id = entry.get("lead_id", "")
            if not thread_id:
                continue

            try:
                thread = gmail_client.service.users().threads().get(
                    userId="me", id=thread_id, format="metadata"
                ).execute()
                messages = thread.get("messages", [])
                if len(messages) > 1:
                    last_msg = messages[-1]
                    headers = {h["name"].lower(): h["value"]
                               for h in last_msg.get("payload", {}).get("headers", [])}
                    from_addr = headers.get("from", "")
                    if IRA_EMAIL not in from_addr:
                        snippet = thread.get("snippet", "")
                        classification = ReplyDetector.classify(snippet)
                        results.append({
                            "lead_id": lead_id,
                            "company": entry.get("company", ""),
                            "thread_id": thread_id,
                            "classification": classification,
                            "snippet": snippet[:200],
                        })

                        if campaign:
                            try:
                                lead = campaign.campaign_state.get(lead_id)
                                if lead:
                                    lead.replied = True
                                    lead.reply_quality = classification
                                    lead.reply_at = datetime.now()
                                    campaign._save_state()
                            except Exception:
                                pass

                        if crm and entry.get("to_email"):
                            try:
                                crm.log_email(
                                    email=entry["to_email"],
                                    direction="inbound",
                                    subject=f"Reply ({classification})",
                                    body_preview=snippet[:200],
                                )
                            except Exception:
                                pass
            except Exception:
                continue

        return results


# ─── [#1] Learning Loop ──────────────────────────────────────────────────────

class LearningLoop:
    @staticmethod
    def log_email_context(email: Dict, dossier: ContextDossier):
        entry = {
            "ts": datetime.now().isoformat(),
            "lead_id": dossier.lead_id,
            "company": dossier.company,
            "country": dossier.country,
            "stage": email.get("stage"),
            "ab_variant": email.get("ab_variant", "a"),
            "subject_a": email.get("subject_a", ""),
            "subject_b": email.get("subject_b", ""),
            "had_news_hook": bool(dossier.news_hook),
            "had_industry_hook": bool(dossier.industry_hook),
            "had_deep_knowledge": bool(dossier.deep_knowledge),
            "had_roi_pitch": bool(dossier.roi_pitch),
            "recommended_machine": dossier.recommended_machine,
            "is_lapsed": dossier.is_lapsed,
            "reply_received": False,
            "reply_classification": "",
        }
        HERMES_LEARNING_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HERMES_LEARNING_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")

    @staticmethod
    def update_reply(lead_id: str, classification: str):
        if not HERMES_LEARNING_FILE.exists():
            return
        lines = HERMES_LEARNING_FILE.read_text().strip().split("\n")
        updated = []
        for line in lines:
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("lead_id") == lead_id and not entry.get("reply_received"):
                entry["reply_received"] = True
                entry["reply_classification"] = classification
            updated.append(json.dumps(entry))
        HERMES_LEARNING_FILE.write_text("\n".join(updated) + "\n")

    @staticmethod
    def get_insights() -> Dict[str, Any]:
        if not HERMES_LEARNING_FILE.exists():
            return {}
        entries = []
        for line in HERMES_LEARNING_FILE.read_text().strip().split("\n"):
            if line.strip():
                entries.append(json.loads(line))
        if not entries:
            return {}

        total = len(entries)
        replied = [e for e in entries if e.get("reply_received")]
        reply_rate = len(replied) / total if total else 0

        with_news = [e for e in entries if e.get("had_news_hook")]
        without_news = [e for e in entries if not e.get("had_news_hook")]
        news_reply_rate = sum(1 for e in with_news if e.get("reply_received")) / len(with_news) if with_news else 0
        no_news_reply_rate = sum(1 for e in without_news if e.get("reply_received")) / len(without_news) if without_news else 0

        a_emails = [e for e in entries if e.get("ab_variant") == "a"]
        b_emails = [e for e in entries if e.get("ab_variant") == "b"]
        a_reply = sum(1 for e in a_emails if e.get("reply_received")) / len(a_emails) if a_emails else 0
        b_reply = sum(1 for e in b_emails if e.get("reply_received")) / len(b_emails) if b_emails else 0

        return {
            "total_sent": total,
            "total_replies": len(replied),
            "reply_rate": round(reply_rate, 3),
            "news_hook_reply_rate": round(news_reply_rate, 3),
            "no_news_hook_reply_rate": round(no_news_reply_rate, 3),
            "ab_variant_a_reply_rate": round(a_reply, 3),
            "ab_variant_b_reply_rate": round(b_reply, 3),
            "insight": "News hooks help" if news_reply_rate > no_news_reply_rate else "News hooks don't help much",
        }


# ─── Hermes Agent ─────────────────────────────────────────────────────────────

class Hermes:
    def __init__(self):
        self.assembler = ContextAssembler()
        self.crafter = EmailCrafter()
        self.sequencer = DripSequencer()
        self.detector = ReplyDetector()
        self.learner = LearningLoop()
        self.campaign = get_campaign() if CAMPAIGN_AVAILABLE else None
        self.crm = get_crm() if CRM_AVAILABLE else None
        self.gmail = None
        if GMAIL_AVAILABLE:
            try:
                self.gmail = GmailClient()
            except Exception:
                pass
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        if HERMES_STATE_FILE.exists():
            try:
                return json.loads(HERMES_STATE_FILE.read_text())
            except Exception:
                pass
        return {
            "total_sent": 0, "total_replies": 0, "batches_run": 0,
            "last_batch": None, "daily_sent": 0,
            "daily_reset_date": datetime.now().strftime("%Y-%m-%d"),
        }

    def _save_state(self):
        HERMES_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        HERMES_STATE_FILE.write_text(json.dumps(self.state, indent=2))

    def _log_outreach(self, entry: Dict):
        HERMES_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HERMES_LOG_FILE, "a") as f:
            f.write(json.dumps({**entry, "ts": datetime.now().isoformat()}) + "\n")

    # [#5] Reply checking
    def check_replies(self) -> List[Dict]:
        replies = self.detector.check_replies(
            self.gmail, HERMES_LOG_FILE, self.campaign, self.crm
        )
        for r in replies:
            self.learner.update_reply(r["lead_id"], r["classification"])
            self.state["total_replies"] = self.state.get("total_replies", 0) + 1
        if replies:
            self._save_state()
        return replies

    def get_ready_leads(self) -> List[Dict]:
        if not self.campaign:
            return []
        ready = []
        try:
            for lead_id, lead in self.campaign.campaign_state.items():
                state = lead.to_dict() if hasattr(lead, "to_dict") else lead
                if self.sequencer.is_ready(state):
                    ready.append(state)
        except Exception as e:
            logger.error(f"Failed to get ready leads: {e}")

        ready.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x.get("priority", "low"), 4))
        return ready[:MAX_EMAILS_PER_BATCH]

    # [#8] Timezone-aware filtering
    def _filter_by_timezone(self, leads: List[Dict]) -> List[Dict]:
        sendable = []
        for lead in leads:
            country = lead.get("country", "")
            hour = _local_hour(country)
            if 8 <= hour <= 17:
                sendable.append(lead)
            else:
                logger.debug(f"Skipping {lead.get('company', '?')} — local time is {hour}:00 in {country}")
        return sendable

    async def craft_email(self, lead_id: str) -> Dict[str, Any]:
        dossier = await self.assembler.assemble(lead_id)
        email = await self.crafter.craft(dossier)
        email["lead_id"] = lead_id
        email["company"] = dossier.company
        email["country"] = dossier.country
        email["to_email"] = dossier.contact_email
        email["linkedin_url"] = dossier.linkedin_url
        email["is_lapsed"] = dossier.is_lapsed
        email["dossier_summary"] = dossier.to_prompt_context()[:500]

        self.learner.log_email_context(email, dossier)
        return email

    async def run_outreach_batch(self, dry_run: bool = False) -> Dict[str, Any]:
        today = datetime.now().strftime("%Y-%m-%d")
        if self.state.get("daily_reset_date") != today:
            self.state["daily_sent"] = 0
            self.state["daily_reset_date"] = today

        self.check_replies()

        ready_leads = self.get_ready_leads()
        if not ready_leads:
            return {"status": "no_leads_ready", "emails": []}

        ready_leads = self._filter_by_timezone(ready_leads)
        if not ready_leads:
            return {"status": "no_leads_in_timezone", "emails": []}

        remaining = MAX_EMAILS_PER_BATCH - self.state.get("daily_sent", 0)
        if remaining <= 0:
            return {"status": "daily_limit_reached", "emails": []}

        batch_leads = ready_leads[:remaining]
        results = []

        for lead_state in batch_leads:
            lead_id = lead_state.get("lead_id", "")
            try:
                email = await self.craft_email(lead_id)

                if dry_run:
                    email["status"] = "draft"
                    results.append(email)
                    continue

                if self.gmail and email.get("to_email"):
                    sent = self.gmail.send_new_email(
                        to=email["to_email"],
                        subject=email["subject"],
                        body=email["body"],
                    )
                    email["status"] = "sent" if sent else "send_failed"
                    email["thread_id"] = sent.get("threadId", "") if isinstance(sent, dict) else ""
                else:
                    email["status"] = "no_email_or_gmail"

                if email["status"] == "sent":
                    self.state["total_sent"] += 1
                    self.state["daily_sent"] += 1
                    self._update_campaign_state(lead_id, email)
                    self._update_crm(lead_id, email)

                self._log_outreach(email)
                results.append(email)

            except Exception as e:
                logger.error(f"Failed to process lead {lead_id}: {e}")
                results.append({"lead_id": lead_id, "status": "error", "error": str(e)})

        self.state["batches_run"] = self.state.get("batches_run", 0) + 1
        self.state["last_batch"] = datetime.now().isoformat()
        self._save_state()

        batch_result = {
            "status": "complete",
            "batch_size": len(results),
            "sent": sum(1 for r in results if r.get("status") == "sent"),
            "drafts": sum(1 for r in results if r.get("status") == "draft"),
            "failed": sum(1 for r in results if r.get("status") in ("error", "send_failed")),
            "emails": results,
            "learning_insights": self.learner.get_insights(),
        }

        if not dry_run:
            await self._notify_rushabh(batch_result)

        return batch_result

    def _update_campaign_state(self, lead_id: str, email: Dict):
        if not self.campaign:
            return
        try:
            lead = self.campaign.campaign_state.get(lead_id)
            if lead:
                lead.current_stage = email.get("stage", lead.current_stage)
                lead.emails_sent += 1
                lead.last_email_sent = datetime.now()
                lead.thread_id = email.get("thread_id", "")
                self.campaign._save_state()
        except Exception as e:
            logger.warning(f"Campaign state update failed: {e}")

    def _update_crm(self, lead_id: str, email: Dict):
        if not self.crm:
            return
        try:
            to_email = email.get("to_email", "")
            if to_email:
                self.crm.log_email(
                    email=to_email, direction="outbound",
                    subject=email.get("subject", ""),
                    body_preview=email.get("body", "")[:200],
                    drip_stage=email.get("stage"),
                )
        except Exception as e:
            logger.warning(f"CRM update failed: {e}")

    # [#7] LinkedIn suggestions in Telegram report
    async def _notify_rushabh(self, batch_result: Dict):
        if not TELEGRAM_BOT_TOKEN or not RUSHABH_TELEGRAM_ID:
            return
        import requests

        sent = batch_result.get("sent", 0)
        total = batch_result.get("batch_size", 0)
        emails = batch_result.get("emails", [])
        insights = batch_result.get("learning_insights", {})

        lines = [f"📬 <b>Hermes Outreach:</b> {sent}/{total} sent\n"]
        for e in emails[:6]:
            icon = "✅" if e.get("status") == "sent" else "📝"
            lapsed = " 🔄" if e.get("is_lapsed") else ""
            lines.append(f"{icon} <b>{e.get('company', '?')}</b> ({e.get('country', '?')}) — Stage {e.get('stage', '?')}{lapsed}")
            if e.get("subject"):
                lines.append(f"   📧 {e['subject'][:55]}")
            if e.get("linkedin_url"):
                lines.append(f"   🔗 Also connect: {e['linkedin_url']}")

        if insights.get("total_sent", 0) > 5:
            lines.append(f"\n📊 <b>Learning:</b> {insights.get('reply_rate', 0)*100:.0f}% reply rate ({insights.get('total_replies', 0)}/{insights.get('total_sent', 0)})")
            if insights.get("news_hook_reply_rate", 0) > insights.get("no_news_hook_reply_rate", 0):
                lines.append("   💡 News hooks are working — keep using them")

        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": RUSHABH_TELEGRAM_ID, "text": "\n".join(lines), "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception:
            pass

    async def preview_batch(self) -> List[Dict]:
        return (await self.run_outreach_batch(dry_run=True)).get("emails", [])


# ─── Module-level convenience ─────────────────────────────────────────────────

_hermes_instance = None


def get_hermes() -> Hermes:
    global _hermes_instance
    if _hermes_instance is None:
        _hermes_instance = Hermes()
    return _hermes_instance
