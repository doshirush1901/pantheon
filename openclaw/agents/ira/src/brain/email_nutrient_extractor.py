#!/usr/bin/env python3
"""
EMAIL NUTRIENT EXTRACTOR — The Growth Hormone
===============================================

Biological parallel:
    Growth hormone doesn't add knowledge directly — it accelerates the
    development of every system. For Ira, every email Rushabh sends or
    receives is concentrated protein: real prices, real objections, real
    negotiations, real closing patterns.

    This module extracts structured knowledge from emails and converts
    them into KnowledgeItems that feed the full digestive pipeline.

What gets extracted from each email:
    1. Sales facts — machines, pricing, delivery timelines, configurations
    2. Customer intelligence — company, contact, requirements, objections
    3. Communication patterns — how Rushabh opens, negotiates, closes
    4. Raw thread context — chunked for RAG retrieval

Usage:
    from email_nutrient_extractor import extract_email_knowledge

    items = extract_email_knowledge(
        subject="Re: PF1-C-2015 Quote for PackRight GmbH",
        body="Hi Hans, thanks for your interest...",
        from_email="rushabh@machinecraft.org",
        to_email="hans@packright.de",
        direction="outbound",
    )
    # -> List[KnowledgeItem] ready for KnowledgeIngestor.ingest_batch()
"""

import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ira.email_nutrient_extractor")

BRAIN_DIR = Path(__file__).parent
SRC_DIR = BRAIN_DIR.parent
AGENT_DIR = SRC_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))

try:
    from knowledge_ingestor import KnowledgeItem
except ImportError:
    from dataclasses import dataclass, field

    @dataclass
    class KnowledgeItem:
        text: str
        knowledge_type: str
        source_file: str
        summary: str = ""
        entity: str = ""
        metadata: Dict[str, Any] = field(default_factory=dict)
        embedding: List[float] = field(default_factory=list)
        id: str = ""
        content_hash: str = ""
        version: int = 1
        confidence: float = 1.0

        def __post_init__(self):
            if not self.content_hash:
                self.content_hash = hashlib.sha256(self.text.encode()).hexdigest()[:16]
            if not self.id:
                self.id = f"{self.knowledge_type}_{self.content_hash}"
            if not self.summary:
                self.summary = self.text[:200] + "..." if len(self.text) > 200 else self.text


# ---------------------------------------------------------------------------
# Regex patterns (reused from ingest_quotes.py)
# ---------------------------------------------------------------------------

MACHINE_PATTERNS = [
    r'PF1-[A-Z]?-?\d{4}',
    r'PF1-\d{4}',
    r'PF2-\d+[xX]\d+',
    r'AM-[A-Z]?-?\d{4}',
    r'AMP-\d{4}',
    r'IMG-\d{4}',
    r'FCS-\d{4}',
    r'ATF-\d{4}',
    r'RT-\d[A-Z]-\d{4}',
    r'UNO-\d{4}',
    r'DUO-\d{4}',
    r'(?:PF1|PF2|AM|FCS|ATF|IMG)\s+series',
]

PRICE_PATTERNS = [
    r'INR\s*[\d,]+(?:\.\d+)?(?:\s*/-)?',
    r'₹\s*[\d,]+(?:\.\d+)?',
    r'USD\s*[\d,]+(?:\.\d+)?',
    r'\$\s*[\d,]+(?:\.\d+)?',
    r'EUR\s*[\d,]+(?:\.\d+)?',
    r'€\s*[\d,]+(?:\.\d+)?',
    r'GBP\s*[\d,]+(?:\.\d+)?',
    r'£\s*[\d,]+(?:\.\d+)?',
]

APPLICATION_KEYWORDS = {
    "automotive": ["automotive", "car", "vehicle", "dashboard", "interior", "panel", "bumper"],
    "packaging": ["packaging", "tray", "blister", "clamshell", "container", "food"],
    "industrial": ["industrial", "enclosure", "cover", "housing", "tank", "bin"],
    "signage": ["signage", "sign", "letter", "display", "advertising"],
    "aerospace": ["aerospace", "aircraft", "aviation"],
    "medical": ["medical", "healthcare", "hospital", "pharmaceutical"],
    "construction": ["construction", "building", "architectural"],
}

COMPETITOR_PATTERNS = [
    r'\b(ILLIG|illig)\b',
    r'\b(GEISS|geiss|Geiss)\b',
    r'\b(GN\s*Thermoforming|GN thermoforming)\b',
    r'\b(Kiefel|KIEFEL)\b',
    r'\b(Brown|BROWN)\s+Machine\b',
    r'\b(Ridat|RIDAT)\b',
    r'\b(Formech|FORMECH)\b',
    r'\b(Thermoforming\s+Systems)\b',
]

SKIP_SUBJECTS = [
    r'out of office', r'automatic reply', r'auto-reply', r'unsubscribe',
    r'newsletter', r'subscription', r'receipt', r'invoice', r'payment',
    r'password reset', r'verify your email', r'confirm your',
    r'delivery notification', r'shipping confirmation',
    r'calendar invitation', r'meeting accepted', r'meeting declined',
    r'transaction alert', r'credit card', r'credit limit',
    r'coming soon to netflix', r'your stay at', r'booking confirmation',
    r'payment.*unsuccessful', r'failed.payment',
    r'accelerator applications', r'applications are open',
]

SKIP_SENDERS = [
    r'@netflix\.com', r'@kotak\.(com|bank)', r'@redditmail\.com',
    r'@github\.com', r'@booking\.com', r'@archiproducts\.com',
    r'@linkedin\.com', r'@facebook\.com', r'@twitter\.com',
    r'@google\.com', r'@youtube\.com', r'@amazon\.',
    r'@stripe\.com', r'@paypal\.com', r'@razorpay\.com',
    r'noreply@', r'no-reply@', r'donotreply@',
    r'notifications@', r'alerts@', r'mailer-daemon@',
    r'failed-payments', r'bankalerts@', r'creditcardalerts@',
    r'email\.campaign@', r'brands@', r'info@members\.',
]

MACHINECRAFT_DOMAINS = ["machinecraft.org", "machinecraft.in"]


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _extract_machines(text: str) -> List[str]:
    machines = set()
    for pattern in MACHINE_PATTERNS:
        for match in re.findall(pattern, text, re.IGNORECASE):
            machines.add(match.upper().replace(" ", "-"))
    return sorted(machines)


def _extract_prices(text: str) -> List[str]:
    prices = []
    for pattern in PRICE_PATTERNS:
        prices.extend(re.findall(pattern, text))
    return prices[:8]


def _extract_applications(text: str) -> List[str]:
    text_lower = text.lower()
    return [app for app, kws in APPLICATION_KEYWORDS.items() if any(kw in text_lower for kw in kws)]


def _extract_competitors(text: str) -> List[str]:
    competitors = set()
    for pattern in COMPETITOR_PATTERNS:
        for match in re.findall(pattern, text):
            name = match if isinstance(match, str) else match[0] if match else ""
            if name:
                competitors.add(name.strip())
    return sorted(competitors)


def _extract_company(text: str) -> str:
    patterns = [
        r'(?:from|at|with|for)\s+([A-Z][A-Za-z\s&]+(?:Ltd|Inc|Corp|Pvt|LLC|GmbH|S\.?A\.?|AG|Co\.?))',
        r'To:\s*([^<\n]+)',
        r'Dear\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        r'([A-Z][A-Za-z\s&]+(?:Ltd|Inc|Corp|Pvt|LLC|GmbH|S\.?A\.?|AG|Co\.?))',
    ]
    for pattern in patterns:
        match = re.search(pattern, text[:3000])
        if match:
            name = re.sub(r'\s+', ' ', match.group(1).strip())
            if 3 < len(name) < 60 and "machinecraft" not in name.lower():
                return name
    return ""


def _extract_contact_name(text: str) -> str:
    patterns = [
        r'(?:Dear|Hi|Hello|Hey)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        r'(?:Best|Regards|Thanks),?\s*\n\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text[:2000])
        if match:
            name = match.group(1).strip()
            if 2 < len(name) < 40 and name.lower() not in ("rushabh", "ira", "team", "sir", "madam"):
                return name
    return ""


def _should_skip(subject: str, body: str, from_email: str = "") -> bool:
    subj_lower = (subject or "").lower()
    if any(re.search(p, subj_lower) for p in SKIP_SUBJECTS):
        return True
    if from_email and any(re.search(p, from_email.lower()) for p in SKIP_SENDERS):
        return True
    if len((body or "").strip()) < 30:
        return True
    return False


def _is_outbound(from_email: str) -> bool:
    return any(from_email.lower().endswith(d) for d in MACHINECRAFT_DOMAINS)


def _email_source_id(subject: str, from_email: str, date_str: str = "") -> str:
    raw = f"{subject}|{from_email}|{date_str}"
    return f"email_{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# LLM-based structured extraction (optional, for richer knowledge)
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """\
You are analyzing a sales email for a thermoforming machine manufacturer (Machinecraft Technologies).
Extract structured knowledge. Return ONLY valid JSON.

EMAIL:
Subject: {subject}
From: {from_email}
To: {to_email}
Direction: {direction}

Body:
{body}

Extract this JSON (omit keys with no data):
{{
  "machines_discussed": ["PF1-C-2015", ...],
  "prices_mentioned": ["INR 60,00,000", "USD 74,000", ...],
  "customer_company": "Company Name",
  "contact_person": "Name",
  "customer_requirements": "brief summary of what they need",
  "material_and_thickness": "e.g. 4mm ABS, 0.8mm rPET",
  "forming_area_needed": "e.g. 1200x800mm",
  "application": "automotive / packaging / signage / etc",
  "competitors_mentioned": ["ILLIG", ...],
  "objections_or_concerns": "budget, timeline, etc",
  "commitments_made": "delivery date, price lock, etc",
  "next_steps": "follow-up, meeting, quote, etc",
  "deal_stage": "inquiry / negotiation / quote_sent / closing / closed_won / closed_lost",
  "key_insight": "one sentence: the most important thing to remember from this email"
}}"""


def _llm_extract(subject: str, body: str, from_email: str, to_email: str, direction: str) -> Optional[Dict]:
    try:
        import openai
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return None

        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You extract structured sales data from emails. Return ONLY valid JSON."},
                {"role": "user", "content": _EXTRACTION_PROMPT.format(
                    subject=subject, body=body[:4000], from_email=from_email,
                    to_email=to_email, direction=direction,
                )},
            ],
            temperature=0.0,
            max_tokens=800,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
        return json.loads(raw)
    except Exception as e:
        logger.debug(f"LLM extraction failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------

def extract_email_knowledge(
    subject: str,
    body: str,
    from_email: str,
    to_email: str = "",
    direction: str = "",
    date_str: str = "",
    thread_history: str = "",
    use_llm: bool = True,
) -> List[KnowledgeItem]:
    """
    Extract structured knowledge from a single email.

    Returns a list of KnowledgeItem objects ready for KnowledgeIngestor.ingest_batch().
    Produces up to 4 items: sales facts, customer intel, communication style, raw context.
    """
    if _should_skip(subject, body, from_email):
        return []

    if not direction:
        direction = "outbound" if _is_outbound(from_email) else "inbound"

    full_text = f"Subject: {subject}\n\n{body}"
    source_id = _email_source_id(subject, from_email, date_str)

    machines = _extract_machines(full_text)
    prices = _extract_prices(full_text)
    applications = _extract_applications(full_text)
    competitors = _extract_competitors(full_text)
    company = _extract_company(full_text)
    contact = _extract_contact_name(body)

    llm_data = {}
    if use_llm and (machines or prices or len(body) > 200):
        llm_data = _llm_extract(subject, body, from_email, to_email, direction) or {}

    company = llm_data.get("customer_company") or company
    contact = llm_data.get("contact_person") or contact
    machines = llm_data.get("machines_discussed") or machines
    prices = llm_data.get("prices_mentioned") or prices
    competitors = llm_data.get("competitors_mentioned") or competitors

    primary_entity = machines[0] if machines else company or ""
    items: List[KnowledgeItem] = []

    base_metadata = {
        "source": "email_nutrient_extractor",
        "from_email": from_email,
        "to_email": to_email,
        "direction": direction,
        "date": date_str,
        "subject": subject,
    }

    # --- Item 1: Sales facts (machines, pricing, specs) ---
    if machines or prices:
        parts = []
        if machines:
            parts.append(f"Machines discussed: {', '.join(machines)}")
        if prices:
            parts.append(f"Prices mentioned: {', '.join(prices[:5])}")
        if llm_data.get("material_and_thickness"):
            parts.append(f"Material: {llm_data['material_and_thickness']}")
        if llm_data.get("forming_area_needed"):
            parts.append(f"Forming area: {llm_data['forming_area_needed']}")
        if llm_data.get("commitments_made"):
            parts.append(f"Commitments: {llm_data['commitments_made']}")
        if llm_data.get("next_steps"):
            parts.append(f"Next steps: {llm_data['next_steps']}")

        context_line = f"Email {'from' if direction == 'inbound' else 'to'} {company or from_email}"
        if date_str:
            context_line += f" on {date_str}"
        parts.insert(0, context_line)

        sales_text = "\n".join(parts)
        kt = "pricing" if prices else "machine_spec"

        items.append(KnowledgeItem(
            text=sales_text,
            knowledge_type=kt,
            source_file=source_id,
            entity=primary_entity,
            summary=f"{'Quote' if prices else 'Specs'} discussion: {', '.join(machines[:3])} — {company or from_email}",
            metadata={**base_metadata, "machines": machines, "prices": prices,
                      "applications": applications, "deal_stage": llm_data.get("deal_stage", "")},
        ))

    # --- Item 2: Customer intelligence ---
    if company or llm_data.get("customer_requirements"):
        parts = []
        if company:
            parts.append(f"Company: {company}")
        if contact:
            parts.append(f"Contact: {contact}")
        if llm_data.get("customer_requirements"):
            parts.append(f"Requirements: {llm_data['customer_requirements']}")
        if llm_data.get("application"):
            parts.append(f"Application: {llm_data['application']}")
        if competitors:
            parts.append(f"Competitors mentioned: {', '.join(competitors)}")
        if llm_data.get("objections_or_concerns"):
            parts.append(f"Objections: {llm_data['objections_or_concerns']}")
        if llm_data.get("deal_stage"):
            parts.append(f"Deal stage: {llm_data['deal_stage']}")
        if llm_data.get("key_insight"):
            parts.append(f"Key insight: {llm_data['key_insight']}")

        customer_text = "\n".join(parts)
        items.append(KnowledgeItem(
            text=customer_text,
            knowledge_type="customer",
            source_file=source_id,
            entity=company or contact or from_email,
            summary=f"Customer intel: {company or contact or from_email}",
            metadata={**base_metadata, "company": company, "contact": contact,
                      "competitors": competitors, "deal_stage": llm_data.get("deal_stage", "")},
        ))

    # --- Item 3: Communication style (outbound only) ---
    if direction == "outbound" and len(body) > 100:
        opener = body.strip().split("\n")[0][:200]
        items.append(KnowledgeItem(
            text=f"Rushabh's email to {company or to_email}:\nOpener: {opener}\nSubject: {subject}\n\n{body[:1500]}",
            knowledge_type="sales_process",
            source_file=source_id,
            entity="rushabh_style",
            summary=f"Communication style: email to {company or to_email}",
            metadata={**base_metadata, "style_type": "email_outbound"},
            confidence=0.7,
        ))

    # --- Item 4: Raw email for RAG context (always, if substantial) ---
    if len(body) > 100:
        raw_text = f"Subject: {subject}\nFrom: {from_email}\nTo: {to_email}\nDate: {date_str}\n\n{body}"
        if thread_history:
            raw_text = f"{raw_text}\n\n--- Thread History ---\n{thread_history[:3000]}"

        items.append(KnowledgeItem(
            text=raw_text[:6000],
            knowledge_type="general",
            source_file=source_id,
            entity=primary_entity or company or "",
            summary=f"Email: {subject[:80]} — {from_email} -> {to_email}",
            metadata={**base_metadata, "is_raw_email": True},
            confidence=0.5,
        ))

    return items
