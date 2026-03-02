#!/usr/bin/env python3
"""
MNEMOSYNE — The Keeper of Relationships
========================================

Named after the Greek goddess of memory and mother of the Muses,
Mnemosyne is Ira's CRM agent. She remembers every contact, every
conversation, every deal, every email thread. She is the institutional
memory of Machinecraft's sales operation.

Personality:
    - Meticulous and organized, but warm — she cares about people, not just data
    - She remembers details others forget: "Last time we spoke, Hans mentioned
      his daughter was starting university"
    - Protective of relationships — she'll push back if Ira tries to email
      someone too aggressively
    - She has opinions: "This lead has gone cold. Try a different angle."
    - She speaks in facts, not fluff: "3 emails sent, 0 replies, 47 days silent"

Role in the Pantheon:
    Athena asks Mnemosyne: "Who should we email today?"
    Mnemosyne replies: "Here are 5 leads ready for drip. TSN is critical —
    they haven't replied to 2 emails. I'd suggest a completely different
    approach. Parat replied last week, they're warm — follow up on the
    quote they asked about."

Functions:
    lookup_contact(query)     — Find a contact by name, email, or company
    get_lead_brief(email)     — Full brief on a lead (for Calliope to write emails)
    get_drip_candidates()     — Who's ready for the next drip email
    get_pipeline_overview()   — Full pipeline health for Athena
    record_interaction(...)   — Log an email, call, or meeting
    suggest_next_action(email) — What should we do next with this lead?

Usage:
    from openclaw.agents.ira.src.agents.crm_agent.agent import (
        lookup_contact, get_lead_brief, get_drip_candidates,
        get_pipeline_overview, suggest_next_action,
    )

    # Athena asks: "Tell me about TSN"
    brief = await lookup_contact("TSN")

    # Athena asks: "Who should we email today?"
    candidates = await get_drip_candidates()
"""

import json
import logging
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.mnemosyne")

AGENT_DIR = Path(__file__).parent.parent.parent.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent
sys.path.insert(0, str(AGENT_DIR / "src" / "crm"))

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

MNEMOSYNE_SYSTEM_PROMPT = """You are Mnemosyne, the Keeper of Relationships at Machinecraft Technologies.
You are part of Ira's pantheon of agents. You manage the CRM — every contact,
lead, conversation, and deal flows through you.

Your personality:
- Meticulous with data but warm about people. You remember the human details.
- You speak in concrete facts: numbers, dates, names. Never vague.
- You have opinions about sales strategy based on the data you see.
- You're protective of relationships — you'll flag if someone is being over-contacted.
- You think in terms of pipeline health, not just individual leads.

When asked about a contact or lead, give a brief that includes:
1. Who they are (name, company, country, role)
2. Relationship history (emails exchanged, replies, last contact)
3. Deal status (stage, value if known)
4. Your recommendation (what to do next)

Keep responses concise and actionable. You're briefing Athena, not writing an essay."""


@dataclass
class LeadBrief:
    """Mnemosyne's brief on a lead — everything needed to write a personalized email."""
    email: str
    name: str
    company: str
    country: str
    title: str
    industry: str
    priority: str
    deal_stage: str
    drip_stage: int
    emails_sent: int
    emails_received: int
    last_email_sent: Optional[str]
    last_reply_at: Optional[str]
    reply_quality: str
    days_since_contact: int
    conversation_summary: Optional[str]
    notes: str
    recommendation: str

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_text(self) -> str:
        lines = [
            f"{self.name} at {self.company} ({self.country})",
            f"Priority: {self.priority} | Stage: {self.deal_stage} | Drip: {self.drip_stage}/5",
            f"Emails: {self.emails_sent} sent, {self.emails_received} received",
        ]
        if self.last_email_sent:
            lines.append(f"Last email: {self.last_email_sent} ({self.days_since_contact}d ago)")
        if self.reply_quality:
            lines.append(f"Last reply: {self.reply_quality}")
        if self.conversation_summary:
            lines.append(f"History: {self.conversation_summary}")
        if self.notes:
            lines.append(f"Notes: {self.notes[:200]}")
        lines.append(f"Recommendation: {self.recommendation}")
        return "\n".join(lines)


def _get_crm():
    """Lazy-load the CRM."""
    try:
        from ira_crm import get_crm
        return get_crm()
    except ImportError:
        logger.warning("Ira CRM not available")
        return None


async def lookup_contact(query: str, context: Optional[Dict] = None) -> str:
    """
    Look up a contact, lead, or company in Ira's CRM.

    Mnemosyne searches by name, email, or company and returns
    a human-readable brief with relationship history and recommendations.
    """
    crm = _get_crm()
    if not crm:
        return "CRM not available. I can't look up contacts right now."

    results = crm.search_contacts(query, limit=5)
    if not results:
        return f"I don't have anyone matching '{query}' in my records."

    briefs = []
    for contact in results:
        lead = crm.get_lead(contact.email)
        conv_summary = crm.get_conversation_summary(contact.email)

        if lead:
            days_since = 0
            if lead.last_email_sent:
                try:
                    last = datetime.fromisoformat(lead.last_email_sent)
                    days_since = (datetime.now() - last).days
                except (ValueError, TypeError):
                    pass

            recommendation = _generate_recommendation(lead, days_since, conv_summary)

            brief = LeadBrief(
                email=contact.email,
                name=contact.name or f"{contact.first_name} {contact.last_name}".strip(),
                company=contact.company or lead.company,
                country=contact.country or lead.country,
                title=contact.title,
                industry=contact.industry or lead.industry,
                priority=lead.priority,
                deal_stage=lead.deal_stage,
                drip_stage=lead.drip_stage,
                emails_sent=lead.emails_sent,
                emails_received=lead.emails_received,
                last_email_sent=lead.last_email_sent,
                last_reply_at=lead.last_reply_at,
                reply_quality=lead.reply_quality,
                days_since_contact=days_since,
                conversation_summary=conv_summary,
                notes=lead.notes,
                recommendation=recommendation,
            )
            briefs.append(brief.to_text())
        else:
            briefs.append(
                f"{contact.name or contact.email} at {contact.company} ({contact.country})\n"
                f"  Contact only — not in sales pipeline yet.\n"
                f"  Notes: {contact.notes[:150] if contact.notes else 'None'}"
            )

    return "\n\n---\n\n".join(briefs)


async def get_lead_brief(email: str, context: Optional[Dict] = None) -> str:
    """Get a full brief on a specific lead for email personalization."""
    crm = _get_crm()
    if not crm:
        return "CRM not available."

    lead = crm.get_lead(email)
    if not lead:
        return f"No lead found for {email}."

    contact = crm.get_contact(email)
    conv_summary = crm.get_conversation_summary(email)
    conversations = crm.get_conversation_context(email, limit=5)

    days_since = 0
    if lead.last_email_sent:
        try:
            days_since = (datetime.now() - datetime.fromisoformat(lead.last_email_sent)).days
        except (ValueError, TypeError):
            pass

    recommendation = _generate_recommendation(lead, days_since, conv_summary)

    parts = [
        f"LEAD BRIEF: {contact.name if contact else email}",
        f"Company: {lead.company} | Country: {lead.country}",
        f"Priority: {lead.priority} | Deal: {lead.deal_stage}",
        f"Drip stage: {lead.drip_stage}/5 | Emails: {lead.emails_sent} sent, {lead.emails_received} replies",
    ]

    if days_since > 0:
        parts.append(f"Last contact: {days_since} days ago")
    if lead.reply_quality:
        parts.append(f"Reply quality: {lead.reply_quality}")
    if conv_summary:
        parts.append(f"\nConversation history: {conv_summary}")
    if conversations:
        parts.append("\nRecent threads:")
        for c in conversations[:3]:
            arrow = "<-" if c.direction == "inbound" else "->"
            parts.append(f"  {arrow} {c.subject[:60]} ({c.date[:10] if c.date else '?'})")
    if contact and contact.notes:
        parts.append(f"\nNotes: {contact.notes[:300]}")

    parts.append(f"\nMnemosyne's recommendation: {recommendation}")

    return "\n".join(parts)


async def get_drip_candidates(context: Optional[Dict] = None) -> str:
    """
    Get leads ready for the next drip email.

    Mnemosyne returns a prioritized list with her recommendations
    for each lead.
    """
    crm = _get_crm()
    if not crm:
        return "CRM not available."

    leads = crm.get_leads_ready_for_drip(max_results=15)
    if not leads:
        return "No leads are due for drip emails right now. Everyone is either too recent or has replied."

    lines = [f"DRIP CANDIDATES: {len(leads)} leads ready\n"]

    for lead in leads:
        days_since = 0
        if lead.last_email_sent:
            try:
                days_since = (datetime.now() - datetime.fromisoformat(lead.last_email_sent)).days
            except (ValueError, TypeError):
                pass

        conv = crm.get_conversation_summary(lead.email)
        rec = _generate_recommendation(lead, days_since, conv)

        lines.append(
            f"[{lead.priority.upper():8s}] {lead.company:35s} "
            f"drip={lead.drip_stage} sent={lead.emails_sent} "
            f"{'REPLIED' if lead.emails_received > 0 else f'{days_since}d silent'}"
        )
        lines.append(f"           -> {rec}")

    return "\n".join(lines)


async def get_pipeline_overview(context: Optional[Dict] = None) -> str:
    """Full pipeline health overview for Athena."""
    crm = _get_crm()
    if not crm:
        return "CRM not available."

    stats = crm.get_pipeline_stats()
    drip = crm.get_drip_stats()

    lines = [
        "PIPELINE OVERVIEW",
        f"Total leads: {stats['total_leads']}",
        f"Reply rate: {stats['reply_rate']:.1%}",
        f"Emails sent: {stats['total_emails_sent']} | Replies: {stats['total_replies']}",
        "",
        "By stage:",
    ]
    for stage, count in sorted(stats.get("by_stage", {}).items()):
        lines.append(f"  {stage or 'new':15s} {count}")

    lines.extend([
        "",
        "By priority:",
    ])
    for pri, count in sorted(stats.get("by_priority", {}).items()):
        lines.append(f"  {pri:15s} {count}")

    lines.extend([
        "",
        f"Drip ready: {drip['ready_for_drip']}",
        f"Engaged: {drip['engaged']}",
        f"Bounced: {drip['bounced']}",
        f"Unsubscribed: {drip['unsubscribed']}",
    ])

    return "\n".join(lines)


async def suggest_next_action(email: str, context: Optional[Dict] = None) -> str:
    """Mnemosyne suggests what to do next with a specific lead."""
    crm = _get_crm()
    if not crm:
        return "CRM not available."

    lead = crm.get_lead(email)
    if not lead:
        return f"No lead found for {email}."

    days_since = 0
    if lead.last_email_sent:
        try:
            days_since = (datetime.now() - datetime.fromisoformat(lead.last_email_sent)).days
        except (ValueError, TypeError):
            pass

    conv = crm.get_conversation_summary(email)
    return _generate_recommendation(lead, days_since, conv)


def _generate_recommendation(lead, days_since: int, conv_summary: Optional[str]) -> str:
    """Mnemosyne's opinion on what to do next."""

    if lead.reply_quality == "bounce":
        return "Email bounced. Verify the address or find an alternative contact at this company."

    if lead.reply_quality == "unsubscribe":
        return "They asked to stop. Respect it. Remove from drip."

    if lead.reply_quality == "engaged":
        if days_since > 7:
            return "They showed interest but it's been a week. Follow up with specifics — quote, specs, or meeting invite."
        return "Warm lead! They're engaged. Move to proposal stage if ready, or keep the conversation going."

    if lead.reply_quality == "polite_decline":
        if days_since > 60:
            return "They declined before but it's been 2+ months. Try a fresh angle — new product, case study, or industry news."
        return "They politely declined recently. Give them space. Try again in a couple months with something new."

    # No reply yet
    if lead.emails_sent == 0:
        return "Fresh lead. Send the first drip email — personalized intro with a specific hook."

    if lead.emails_sent >= 3 and lead.emails_received == 0:
        if days_since > 30:
            return (
                f"3+ emails, zero replies, {days_since}d silent. "
                "This approach isn't working. Try something radically different: "
                "shorter email, different subject line, or try reaching them on LinkedIn."
            )
        return "Multiple emails with no response. Space it out and try a different angle next time."

    if lead.emails_sent >= 1 and lead.emails_received == 0:
        if days_since > 14:
            return "Sent an email 2+ weeks ago, no reply. Time for the next drip stage — try a value-prop or case study angle."
        return "Recently emailed, waiting for response. Give it a few more days."

    if conv_summary:
        return f"Has history: {conv_summary} Continue the conversation thread."

    return "Standard drip sequence. Send the next stage email."


# Expose for __init__.py
__all__ = [
    "lookup_contact",
    "get_lead_brief",
    "get_drip_candidates",
    "get_pipeline_overview",
    "suggest_next_action",
    "LeadBrief",
]
