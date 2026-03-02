#!/usr/bin/env python3
"""
EUROPEAN DRIP MARKETING CAMPAIGN
=================================

Automated drip marketing sequence for European thermoforming leads.
Based on detailed company profiles and sales approaches from market research.

Features:
- 5-stage drip sequence with industry-specific personalization
- Priority-based send scheduling (CRITICAL leads get accelerated sequence)
- Sales approach integration from company profiles
- A/B testing support for subject lines

Usage:
    from european_drip_campaign import EuropeanDripCampaign, get_campaign
    
    campaign = get_campaign()
    
    # Get next email for a lead
    email = campaign.get_next_email("eu-012")  # TSN Kunststoffverarbeitung
    
    # Generate personalized email
    email_content = campaign.generate_email("eu-003", stage=1)
    
    # Get all leads ready for outreach today
    ready_leads = campaign.get_leads_ready_for_outreach()
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import random

SKILL_DIR = Path(__file__).parent
PROJECT_ROOT = SKILL_DIR.parent.parent.parent.parent.parent
BRAIN_DIR = SKILL_DIR.parent / "brain"

# Add brain dir to path for luxury polish imports
sys.path.insert(0, str(BRAIN_DIR))

# Import luxury email polish
try:
    from email_polish_luxury import (
        polish_with_llm,
        get_elegant_signature,
        get_rushabh_opener,
        get_rushabh_closer,
        get_expertise_touch,
        get_warm_touch,
        format_elegant_header,
        IraPersonality,
        OPENAI_AVAILABLE
    )
    LUXURY_POLISH_AVAILABLE = True
except ImportError:
    LUXURY_POLISH_AVAILABLE = False
    OPENAI_AVAILABLE = False

LEADS_FILE = PROJECT_ROOT / "data" / "imports" / "european_leads_structured.json"
CAMPAIGN_STATE_FILE = PROJECT_ROOT / "data" / "european_campaign_state.json"
CONVERSATIONS_FILE = PROJECT_ROOT / "data" / "european_lead_conversations.json"
CONTACTS_CSV = PROJECT_ROOT / "data" / "imports" / "European & US Contacts for Single Station Nov 203.csv"

# Lead intelligence for real-time context (Iris agent)
try:
    # Try importing from Iris agent first
    sys.path.insert(0, str(PROJECT_ROOT / "agents" / "iris"))
    from agent import Iris, enrich_lead_for_email
    INTELLIGENCE_AVAILABLE = True
    IRIS_AVAILABLE = True
except ImportError:
    try:
        # Fallback to local module
        from lead_intelligence import enrich_lead_for_email
        INTELLIGENCE_AVAILABLE = True
        IRIS_AVAILABLE = False
    except ImportError:
        INTELLIGENCE_AVAILABLE = False
        IRIS_AVAILABLE = False


# =============================================================================
# IRA INTRODUCTION - WHO SHE IS
# =============================================================================

IRA_INTRODUCTION = """I'm Ira, Machinecraft's sales assistant. I work alongside Rushabh to help \
thermoforming companies find the right equipment for their needs.

I have access to our full product catalog, pricing, and specifications - so I can \
give you quick answers and put together quotes. Rushabh oversees everything and \
handles the important stuff (negotiations, site visits, final approvals).

Think of me as your first point of contact - here to save you time and get things moving."""

IRA_INTRODUCTION_SHORT = """I'm Ira, Machinecraft's sales assistant. I work with Rushabh to help \
thermoforming companies find the right machines. I can answer questions, share specs, and put \
together quotes - Rushabh handles the final details."""

IRA_INTRODUCTION_MINIMAL = """I'm Ira, working with Rushabh at Machinecraft. I'm here to help \
you find the right thermoforming solution."""


def get_ira_intro(style: str = "short") -> str:
    """Get Ira's introduction based on style preference."""
    if style == "full":
        return IRA_INTRODUCTION
    elif style == "minimal":
        return IRA_INTRODUCTION_MINIMAL
    return IRA_INTRODUCTION_SHORT


# =============================================================================
# CONVERSATION HISTORY LOADING
# =============================================================================

def load_conversation_history() -> Dict[str, Any]:
    """Load conversation history from JSON file."""
    try:
        if CONVERSATIONS_FILE.exists():
            with open(CONVERSATIONS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"[drip_campaign] Error loading conversations: {e}")
    return {"genuine_conversations": [], "contacted_no_reply": [], "not_contacted": []}


def load_quote_history() -> Dict[str, Dict[str, Any]]:
    """
    Load quote history from CSV file.
    Returns dict keyed by company name (lowercase) with quote details.
    """
    import csv
    quotes = {}
    
    # Try different encodings
    encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
    
    for encoding in encodings:
        try:
            if CONTACTS_CSV.exists():
                with open(CONTACTS_CSV, "r", encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        company = row.get("Company Name", "").strip()
                        if company and (row.get("Quotes") or row.get("Comments")):
                            quotes[company.lower()] = {
                                "company": company,
                                "contact_name": f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip(),
                                "email": row.get("Email Address", ""),
                                "meeting": row.get("Physical / Web Meeting", ""),
                                "quote_specs": row.get("Quotes", ""),
                                "quote_date": row.get("Date", ""),
                                "comments": row.get("Comments", ""),
                            }
                break  # Success, exit encoding loop
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"[drip_campaign] Error loading quotes: {e}")
            break
    
    return quotes


def get_conversation_summary(lead_id: str, company: str) -> Optional[str]:
    """
    Get a summary of past conversations with a lead.
    
    Returns None if no meaningful history exists.
    Returns a natural language summary if there is history.
    """
    conversations = load_conversation_history()
    quotes = load_quote_history()
    
    summary_parts = []
    
    # Check for genuine conversations
    for conv in conversations.get("genuine_conversations", []):
        if conv.get("lead_id") == lead_id or conv.get("company", "").lower() == company.lower():
            emails_sent = conv.get("emails_sent", 0)
            genuine_replies = conv.get("genuine_replies", 0)
            last_contact = conv.get("last_contact", "")
            
            # Extract meaningful info from threads
            threads = conv.get("conversation_threads", [])
            meaningful_threads = [t for t in threads if "Machinecraft" in t.get("subject", "") 
                                  or "RFQ" in t.get("subject", "")
                                  or "meeting" in t.get("subject", "").lower()
                                  or "quote" in t.get("preview", "").lower()]
            
            if genuine_replies > 0:
                # Format the date nicely
                if last_contact:
                    try:
                        # Try to extract year and month
                        date_parts = last_contact.split()
                        if len(date_parts) >= 4:
                            month_year = f"{date_parts[2]} {date_parts[3]}" if date_parts[3].isdigit() else date_parts[2]
                            summary_parts.append(f"We've exchanged {genuine_replies} emails (last contact: {month_year})")
                    except:
                        summary_parts.append(f"We've exchanged {genuine_replies} emails previously")
                else:
                    summary_parts.append(f"We've exchanged {genuine_replies} emails previously")
                
                # Check for specific topics
                for thread in meaningful_threads[:2]:
                    preview = thread.get("preview", "")[:100]
                    if "quote" in preview.lower() or "price" in preview.lower():
                        summary_parts.append("You showed interest in our pricing")
                        break
                    elif "machine" in preview.lower():
                        summary_parts.append("We discussed machine requirements")
                        break
            break
    
    # Check for contacted but no reply
    for conv in conversations.get("contacted_no_reply", []):
        if conv.get("lead_id") == lead_id or conv.get("company", "").lower() == company.lower():
            emails_sent = conv.get("emails_sent", 0)
            if emails_sent > 0:
                summary_parts.append(f"We reached out previously ({emails_sent} emails)")
            break
    
    # Check for quote history from CSV
    company_lower = company.lower()
    if company_lower in quotes:
        quote_info = quotes[company_lower]
        if quote_info.get("quote_specs"):
            summary_parts.append(f"We quoted you on a {quote_info['quote_specs']} machine")
        if quote_info.get("meeting"):
            summary_parts.append(f"We met at {quote_info['meeting']}")
        if quote_info.get("comments"):
            # Extract key info from comments
            comments = quote_info["comments"]
            if "K-show" in comments or "K2022" in comments or "K2019" in comments:
                summary_parts.append("We connected at the K trade fair")
            elif "lost to" in comments.lower():
                summary_parts.append("We know you went with another supplier last time - things may have changed")
    
    # Also check partial matches for company name in quotes
    for key, quote_info in quotes.items():
        if key in company_lower or company_lower in key:
            if quote_info.get("quote_specs") and "quoted" not in str(summary_parts).lower():
                summary_parts.append(f"We quoted you on a {quote_info['quote_specs']} machine")
                break
    
    if not summary_parts:
        return None
    
    # Combine into natural language
    if len(summary_parts) == 1:
        return summary_parts[0] + "."
    elif len(summary_parts) == 2:
        return f"{summary_parts[0]}, and {summary_parts[1].lower()}."
    else:
        return f"{summary_parts[0]}. {'. '.join(summary_parts[1:3])}."


class CampaignStage(Enum):
    """Drip campaign stages."""
    INTRO = 1           # Initial introduction
    VALUE_PROP = 2      # Value proposition with case study
    TECHNICAL = 3       # Technical specs and demo offer
    SOCIAL_PROOF = 4    # References and testimonials
    CLOSING = 5         # Urgency/event hook


class LeadPriority(Enum):
    """Lead priority levels."""
    CRITICAL = "critical"   # Immediate action (TSN, Soplami)
    HIGH = "high"           # Near-term opportunity
    MEDIUM = "medium"       # Standard nurture
    LOW = "low"             # Long-term cultivation


@dataclass
class CampaignLead:
    """A lead in the drip campaign."""
    lead_id: str
    company: str
    country: str
    priority: LeadPriority
    current_stage: int = 0
    last_email_sent: Optional[datetime] = None
    emails_sent: int = 0
    opened: int = 0
    replied: bool = False
    unsubscribed: bool = False
    notes: str = ""
    # Autonomous drip tracking fields
    reply_quality: str = ""  # "engaged", "polite_decline", "auto_reply", "bounce"
    reply_at: Optional[datetime] = None
    thread_id: str = ""
    last_batch_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "lead_id": self.lead_id,
            "company": self.company,
            "country": self.country,
            "priority": self.priority.value,
            "current_stage": self.current_stage,
            "last_email_sent": self.last_email_sent.isoformat() if self.last_email_sent else None,
            "emails_sent": self.emails_sent,
            "opened": self.opened,
            "replied": self.replied,
            "unsubscribed": self.unsubscribed,
            "notes": self.notes,
            "reply_quality": self.reply_quality,
            "reply_at": self.reply_at.isoformat() if self.reply_at else None,
            "thread_id": self.thread_id,
            "last_batch_id": self.last_batch_id,
        }


# ============================================================================
# EMAIL TEMPLATES - Organized by Stage and Industry
# ============================================================================

SUBJECT_LINES = {
    CampaignStage.INTRO: [
        "Capacity expansion solutions for {company}",
        "Machinecraft + {company}: A potential fit?",
        "Quick question about your thermoforming operations",
        "For {contact_name}: Thermoforming innovation from India",
    ],
    CampaignStage.VALUE_PROP: [
        "How {similar_company} reduced cycle times by 20%",
        "Case study: {industry} thermoforming success",
        "The ROI of modern thermoforming equipment",
        "{company} — are you seeing these challenges too?",
    ],
    CampaignStage.TECHNICAL: [
        "PF Series specifications for {company}",
        "Technical deep-dive: Machinecraft capabilities",
        "Demo invitation: See our machines in action",
        "Engineering data for your evaluation",
    ],
    CampaignStage.SOCIAL_PROOF: [
        "What European manufacturers say about Machinecraft",
        "References available for {company}",
        "From one {industry} supplier to another",
        "Trusted by {reference_count}+ thermoformers worldwide",
    ],
    CampaignStage.CLOSING: [
        "Plastindia follow-up: Special terms for {company}",
        "Limited availability: Factory visit invitation",
        "Before you finalize your equipment decision",
        "Quick call this week, {contact_name}?",
    ],
}


# Industry-specific templates
TEMPLATES_BY_INDUSTRY = {
    "automotive": {
        CampaignStage.INTRO: """Dear {contact_name},

I'm reaching out because {company}'s work in automotive thermoforming caught our attention. At Machinecraft, we've been helping automotive suppliers across Europe and Asia achieve faster cycle times and better part consistency.

Given your focus on {specific_capability}, I thought there might be a fit worth exploring — particularly around:

• Capacity expansion without the premium European machine price tag
• Pressure forming capabilities for crisp automotive interior details
• 5-axis CNC routing for complex trim operations

Would you be open to a brief call to see if there's mutual interest?

Best regards,
Rushabh Doshi
Machinecraft Technologies
rushabh@machinecraft.org""",

        CampaignStage.VALUE_PROP: """Dear {contact_name},

Following up on my previous note — I wanted to share how we helped a German automotive supplier (similar profile to {company}) achieve:

✓ 18% reduction in cycle time on dashboard panels
✓ Significant energy savings with our zoned heating system
✓ Consistent wall thickness on deep-draw parts

{custom_value_prop}

The key was our PF series machine's precise temperature control — critical for the ABS/PC blends you likely work with.

Would a 15-minute call make sense to discuss your current capacity situation?

Best,
Rushabh""",
    },
    
    "aerospace": {
        CampaignStage.INTRO: """Dear {contact_name},

Machinecraft has been tracking {company}'s work in aerospace thermoforming with interest. Your capabilities with {specific_capability} align well with what our advanced thermoforming systems can deliver.

We specialize in:
• High-temperature polymer forming (PEEK, Ultem, Kydex)
• Optical-quality acrylic and polycarbonate processing
• Machines with aerospace-grade process documentation and repeatability

For companies pushing the boundaries of thermoplastic composites and advanced materials, we've found our engineering-first approach resonates.

Would you be interested in a technical discussion about how Machinecraft might support your R&D or production needs?

Best regards,
Rushabh Doshi
Machinecraft Technologies""",
    },
    
    "appliances": {
        CampaignStage.INTRO: """Dear {contact_name},

I noticed {company} produces thermoformed components for the appliance industry — an area where Machinecraft has strong experience with manufacturers in Asia and Europe.

For appliance applications, our machines excel at:
• High-volume liner production with consistent wall thickness
• Energy-efficient heating systems (important for HIPS and ABS)
• Quick mold changeover for multiple product variants

{custom_intro}

Would you be open to exploring whether Machinecraft could support your production needs — whether for capacity expansion or equipment modernization?

Best regards,
Rushabh Doshi
Machinecraft Technologies""",
    },
    
    "general": {
        CampaignStage.INTRO: """Dear {contact_name},

I'm reaching out from Machinecraft Technologies in India. We manufacture thermoforming machines, 5-axis CNC routers, and supply specialty sheet materials to thermoformers across Europe and Asia.

{company}'s profile stood out to us — your work in {industries} suggests you might benefit from:

• Our PF series thermoformers (vacuum and pressure forming, large format capability)
• Shoda 5-axis CNC routers for precise trimming
• StellarX ABS/ASA sheets with excellent UV resistance

We've built a reputation for delivering robust, cost-effective equipment with strong after-sales support in Europe.

Would you be interested in a brief conversation about your current equipment needs?

Best regards,
Rushabh Doshi
Machinecraft Technologies
rushabh@machinecraft.org""",

        CampaignStage.VALUE_PROP: """Dear {contact_name},

Following up on my previous email — I wanted to share some concrete results our customers have seen:

A thermoformer in {relevant_region} recently told us:
"{testimonial_quote}"

For {company}, the relevant benefits might include:
{bullet_points}

{custom_value_prop}

I'd be happy to share more detailed case studies or technical specifications if helpful.

Best,
Rushabh""",

        CampaignStage.TECHNICAL: """Dear {contact_name},

I wanted to provide some technical details that might be useful as you evaluate equipment options:

**PF Series Thermoformers**
• Forming area: Up to 3500 x 2500 mm
• Sheet thickness: 0.5 - 15 mm
• Heating: Ceramic/quartz with zone control
• Vacuum/pressure: Dual capability standard
• Cycle time: Competitive with European machines

**Shoda 5-Axis CNC Routers**
• Work envelope: Customizable to your needs
• Precision: ±0.1mm repeatability
• Dust collection: Integrated system

{custom_technical}

Would a video call work to walk through specifications relevant to {company}'s applications? I can also arrange a demo visit if you're interested.

Best,
Rushabh""",

        CampaignStage.SOCIAL_PROOF: """Dear {contact_name},

I wanted to share what some of our European customers have said:

"{reference_quote_1}"
— {reference_1}

"{reference_quote_2}"
— {reference_2}

We also work with manufacturers in {relevant_industries} who face similar challenges to {company}.

If it would help, I can connect you with a reference customer for a candid conversation about their experience with Machinecraft.

Would that be useful?

Best,
Rushabh""",

        CampaignStage.CLOSING: """Dear {contact_name},

I wanted to reach out one more time before closing out my notes on {company}.

{urgency_hook}

If thermoforming equipment isn't a priority right now, I completely understand — I'll simply note that for when timing is better.

But if there's any interest in exploring Machinecraft's solutions, I'm happy to:
• Arrange a video call at your convenience
• Send detailed technical specifications
• Connect you with a European reference
• Discuss a plant visit or demo

Either way, I appreciate your time reading these emails.

Best regards,
Rushabh Doshi
Machinecraft Technologies
+91 98XXX XXXXX
rushabh@machinecraft.org""",
    },
}

# Special templates for CRITICAL priority leads
CRITICAL_TEMPLATES = {
    "TSN Kunststoffverarbeitung": {
        CampaignStage.INTRO: """Dear {contact_name},

Congratulations on TSN's major expansion — the $25M investment in your new Querétaro facility is impressive news.

At Machinecraft, we specialize in exactly what you'll need for that plant: turnkey thermoforming systems that can be deployed quickly across multiple locations.

Given your timeline for the Mexico facility, I wanted to reach out immediately to offer:

• Complete machine + router + tooling packages
• Identical equipment for Germany and Mexico (process consistency)
• Support infrastructure for North America
• Competitive pricing that makes sense for your growth phase

TSN's vehicle conversion expertise combined with Machinecraft's thermoforming solutions could be a powerful match.

Can we arrange a call this week to discuss your equipment requirements for the new plant?

Best regards,
Rushabh Doshi
CEO, Machinecraft Technologies
rushabh@machinecraft.org
+91 98XXX XXXXX""",
    },
    
    "Soplami": {
        CampaignStage.INTRO: """Dear {contact_name},

I saw the news about Soplami's factory extension in Muret — congratulations on the growth. With 50+ years of aerospace thermoforming expertise, you're clearly at the forefront of the industry.

As you equip your expanded facility, I wanted to introduce Machinecraft as a potential partner for:

• Heavy-duty thermoformers for large aerospace parts
• Machines optimized for optical-quality acrylic and polycarbonate
• Custom configurations to match your canopy forming requirements
• Quick delivery to support your expansion timeline

We understand the precision required for aerospace applications — our machines feature process logging, recipe storage, and the repeatability your quality documentation demands.

Could we arrange a discussion about your equipment needs for the new capacity?

Cordialement,
Rushabh Doshi
Machinecraft Technologies
rushabh@machinecraft.org""",
    },
}


# Urgency hooks for closing emails
URGENCY_HOOKS = {
    "trade_show": "We'll be at Plastindia and K Show later this year — if you're attending, I'd love to arrange a meeting or demo at our booth.",
    "capacity": "If you're facing capacity constraints heading into your busy season, we can typically deliver within {lead_time} weeks.",
    "pricing": "We're currently offering favorable terms for first orders in {country} as we expand our European presence.",
    "demo": "We're arranging a European demo tour in {timeframe} — {company} would be welcome to see our machines in action.",
    "reference": "One of your neighbors in {country} recently started using our equipment — I could arrange an introduction if that would help.",
}


class EuropeanDripCampaign:
    """
    Manages drip marketing campaign for European thermoforming leads.
    """
    
    # Timing between emails (in days) by priority
    SEND_INTERVALS = {
        LeadPriority.CRITICAL: [0, 3, 7, 14, 21],      # Accelerated
        LeadPriority.HIGH: [0, 5, 12, 21, 35],         # Faster nurture
        LeadPriority.MEDIUM: [0, 7, 14, 28, 45],       # Standard
        LeadPriority.LOW: [0, 14, 30, 60, 90],         # Slow cultivation
    }
    
    def __init__(self, leads_file: str = None, state_file: str = None):
        self.leads_file = Path(leads_file) if leads_file else LEADS_FILE
        self.state_file = Path(state_file) if state_file else CAMPAIGN_STATE_FILE
        
        self.leads_data = self._load_leads()
        self.campaign_state = self._load_state()
    
    def _load_leads(self) -> Dict[str, Any]:
        """Load leads from JSON file."""
        try:
            with open(self.leads_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"leads": [], "metadata": {}}
    
    def _load_state(self) -> Dict[str, CampaignLead]:
        """Load campaign state from file."""
        state = {}
        try:
            with open(self.state_file) as f:
                data = json.load(f)
                for lead_id, lead_data in data.get("leads", {}).items():
                    state[lead_id] = CampaignLead(
                        lead_id=lead_data["lead_id"],
                        company=lead_data["company"],
                        country=lead_data["country"],
                        priority=LeadPriority(lead_data["priority"]),
                        current_stage=lead_data.get("current_stage", 0),
                        last_email_sent=datetime.fromisoformat(lead_data["last_email_sent"]) if lead_data.get("last_email_sent") else None,
                        emails_sent=lead_data.get("emails_sent", 0),
                        opened=lead_data.get("opened", 0),
                        replied=lead_data.get("replied", False),
                        unsubscribed=lead_data.get("unsubscribed", False),
                        notes=lead_data.get("notes", "")
                    )
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        return state
    
    def _save_state(self):
        """Save campaign state to file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "updated_at": datetime.now().isoformat(),
            "leads": {lead_id: lead.to_dict() for lead_id, lead in self.campaign_state.items()}
        }
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def initialize_leads(self) -> int:
        """Initialize all leads from the leads file into campaign state."""
        count = 0
        for lead in self.leads_data.get("leads", []):
            lead_id = lead["id"]
            if lead_id not in self.campaign_state:
                priority_str = lead.get("priority", "medium").lower()
                if priority_str == "critical":
                    priority = LeadPriority.CRITICAL
                elif priority_str == "high":
                    priority = LeadPriority.HIGH
                elif priority_str == "low":
                    priority = LeadPriority.LOW
                else:
                    priority = LeadPriority.MEDIUM
                
                self.campaign_state[lead_id] = CampaignLead(
                    lead_id=lead_id,
                    company=lead["company"],
                    country=lead["country"],
                    priority=priority
                )
                count += 1
        
        self._save_state()
        return count
    
    def get_lead_profile(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Get full lead profile from leads data."""
        for lead in self.leads_data.get("leads", []):
            if lead["id"] == lead_id:
                return lead
        return None
    
    def _get_industry_category(self, lead_profile: Dict[str, Any]) -> str:
        """Determine primary industry category for template selection."""
        industries = lead_profile.get("industries", [])
        industries_lower = [i.lower() for i in industries]
        
        if any("auto" in i or "vehicle" in i for i in industries_lower):
            return "automotive"
        elif any("aero" in i or "aircraft" in i or "defense" in i for i in industries_lower):
            return "aerospace"
        elif any("appliance" in i or "fridge" in i or "washer" in i for i in industries_lower):
            return "appliances"
        else:
            return "general"
    
    def generate_email(
        self, 
        lead_id: str, 
        stage: int = None,
        contact_name: str = "Team",
        custom_vars: Dict[str, str] = None,
        use_luxury_polish: bool = True,
    ) -> Dict[str, str]:
        """
        Generate a personalized email for a lead at a specific stage.
        
        Args:
            lead_id: The lead identifier
            stage: Drip stage (1-5)
            contact_name: Name for greeting
            custom_vars: Custom template variables
            use_luxury_polish: Apply luxury email formatting (default True)
        
        Returns dict with 'subject', 'body', 'stage', 'priority'.
        """
        lead_profile = self.get_lead_profile(lead_id)
        if not lead_profile:
            return None
        
        campaign_lead = self.campaign_state.get(lead_id)
        if stage is None:
            stage = (campaign_lead.current_stage if campaign_lead else 0) + 1
        
        stage_enum = CampaignStage(min(stage, 5))
        company = lead_profile["company"]
        country = lead_profile["country"]
        industries = lead_profile.get("industries", [])
        
        # Check for critical template override
        if company in CRITICAL_TEMPLATES and stage_enum in CRITICAL_TEMPLATES[company]:
            template = CRITICAL_TEMPLATES[company][stage_enum]
        else:
            industry = self._get_industry_category(lead_profile)
            templates = TEMPLATES_BY_INDUSTRY.get(industry, TEMPLATES_BY_INDUSTRY["general"])
            template = templates.get(stage_enum, TEMPLATES_BY_INDUSTRY["general"].get(stage_enum, ""))
        
        # Get subject line
        subjects = SUBJECT_LINES.get(stage_enum, ["Following up with {company}"])
        subject = random.choice(subjects)
        
        # Build variables for template
        vars_dict = {
            "company": company,
            "contact_name": contact_name,
            "country": country,
            "industries": ", ".join(industries[:2]) if industries else "thermoforming",
            "specific_capability": lead_profile.get("capabilities", ["thermoforming"])[0] if lead_profile.get("capabilities") else "thermoforming",
            "custom_intro": "",
            "custom_value_prop": lead_profile.get("sales_approach", ""),
            "custom_technical": "",
            "relevant_region": "Europe",
            "testimonial_quote": "The Machinecraft team understood our requirements and delivered exactly what we needed.",
            "bullet_points": self._generate_bullet_points(lead_profile),
            "reference_quote_1": "Excellent support and machine quality.",
            "reference_1": "European Thermoformer",
            "reference_quote_2": "Our cycle times improved significantly.",
            "reference_2": "Automotive Supplier",
            "relevant_industries": ", ".join(industries[:2]) if industries else "various industries",
            "urgency_hook": self._get_urgency_hook(lead_profile),
            "lead_time": "12-16",
            "timeframe": "Q2 2026",
            "reference_count": "50",
            "similar_company": "a German thermoformer",
            "industry": industries[0] if industries else "thermoforming",
        }
        
        # Merge custom variables
        if custom_vars:
            vars_dict.update(custom_vars)
        
        # For Stage 1: Add conversation history, Ira introduction, and real-time intelligence
        conversation_summary = None
        ira_intro = None
        intel_hooks = {}
        
        if stage_enum == CampaignStage.INTRO:
            # Get conversation history
            conversation_summary = get_conversation_summary(lead_id, company)
            # Get Ira's introduction (short for drip, full for first-ever contact)
            ira_intro = get_ira_intro("minimal" if conversation_summary else "short")
            
            vars_dict["conversation_summary"] = conversation_summary or ""
            vars_dict["ira_intro"] = ira_intro
            
            # Get real-time intelligence (news, industry trends, geopolitics)
            if INTELLIGENCE_AVAILABLE:
                try:
                    intel_hooks = enrich_lead_for_email(
                        lead_id=lead_id,
                        company=company,
                        country=country,
                        industries=industries,
                        website=lead_profile.get("website", ""),
                    )
                    vars_dict.update(intel_hooks)
                except Exception as e:
                    print(f"[drip_campaign] Intelligence enrichment failed: {e}")
        
        # Format template
        try:
            body = template.format(**vars_dict)
            subject = subject.format(**vars_dict)
        except KeyError as e:
            body = template
            subject = f"Following up with {company}"
        
        # For Stage 1: Inject conversation context, Ira intro, and intelligence at the right place
        if stage_enum == CampaignStage.INTRO and (conversation_summary or ira_intro or intel_hooks):
            body = self._inject_intro_context(
                body, contact_name, conversation_summary, ira_intro, intel_hooks
            )
        
        # Apply luxury polish if enabled
        if use_luxury_polish and LUXURY_POLISH_AVAILABLE:
            body = self._apply_luxury_polish(body, contact_name, lead_profile, stage=stage)
        
        priority = lead_profile.get("priority", "medium")
        
        return {
            "subject": subject,
            "body": body,
            "stage": stage,
            "priority": priority,
            "lead_id": lead_id,
            "company": company,
        }
    
    def _inject_intro_context(
        self,
        body: str,
        contact_name: str,
        conversation_summary: Optional[str],
        ira_intro: Optional[str],
        intel_hooks: Dict[str, str] = None,
    ) -> str:
        """
        Inject conversation history, Ira introduction, and real-time intelligence into Stage 1 emails.
        
        This creates a warm, contextual opening that:
        1. Opens with timely news hook (if available)
        2. Acknowledges past interactions (if any)
        3. Introduces Ira and her role
        4. Weaves in industry context
        5. Flows naturally into the main email content
        """
        intel_hooks = intel_hooks or {}
        
        # Find the first paragraph break to insert context after greeting
        paragraphs = body.split('\n\n')
        
        if len(paragraphs) < 2:
            return body
        
        # Build the context section
        context_parts = []
        
        # 1. NEWS HOOK - Most impactful opener (if we have fresh news)
        if intel_hooks.get("news_hook"):
            context_parts.append(intel_hooks["news_hook"])
        elif intel_hooks.get("timely_opener"):
            context_parts.append(intel_hooks["timely_opener"])
        
        # 2. CONVERSATION SUMMARY - Acknowledge history
        if conversation_summary:
            context_parts.append(f"Quick context: {conversation_summary}")
        
        # 3. IRA INTRODUCTION - Who she is
        if ira_intro:
            context_parts.append(ira_intro)
        
        # 4. INDUSTRY HOOK - Weave into value prop (add to body, not intro)
        # This goes into the main content, not the opener
        
        if not context_parts:
            return body
        
        # Create the context block
        context_block = "\n\n".join(context_parts)
        
        # Insert after the greeting (first paragraph)
        greeting = paragraphs[0]
        rest = '\n\n'.join(paragraphs[1:])
        
        # If we have an industry hook, try to weave it into the value prop section
        if intel_hooks.get("industry_hook") and "Here's the thing" in rest:
            industry_hook = intel_hooks["industry_hook"]
            rest = rest.replace(
                "Here's the thing",
                f"{industry_hook}\n\nHere's the thing"
            )
        
        return f"{greeting}\n\n{context_block}\n\n{rest}"
    
    def _apply_luxury_polish(
        self, 
        body: str, 
        contact_name: str, 
        lead_profile: Dict[str, Any],
        stage: int = 1,
    ) -> str:
        """
        Apply luxury email formatting with Ira's personality.
        
        Features:
        - Rushabh-style opener
        - Beautiful typography with breathing room
        - Expertise touches based on industry
        - Elegant signature
        - Optional LLM polish for human warmth
        """
        if not LUXURY_POLISH_AVAILABLE:
            return body
        
        industries = lead_profile.get("industries", [])
        materials = lead_profile.get("materials_processed", [])
        
        # Extract first material for expertise touch
        material_hint = materials[0] if materials else None
        application_hint = industries[0] if industries else None
        
        # Get Ira personality touches
        opener = get_rushabh_opener(contact_name if contact_name != "Team" else None)
        closer = get_rushabh_closer()
        expertise = get_expertise_touch(material=material_hint, application=application_hint)
        warm_touch = get_warm_touch("confidence")
        
        # Upgrade the opener if it's a generic "Dear" style
        if body.startswith("Dear"):
            body = body.replace(f"Dear {contact_name},", opener, 1)
        
        # Add expertise touch if we have one and it's not already in body
        if expertise and expertise not in body:
            # Insert after first paragraph
            paragraphs = body.split('\n\n')
            if len(paragraphs) > 1:
                paragraphs[1] = expertise + "\n\n" + paragraphs[1]
                body = '\n\n'.join(paragraphs)
        
        # Replace standard signature with elegant one
        signature_patterns = [
            "Best regards,\nRushabh Doshi",
            "Best regards,\nRushabh",
            "Best,\nRushabh",
            "Cordialement,\nRushabh Doshi",
        ]
        for pattern in signature_patterns:
            if pattern in body:
                body = body.replace(pattern, "")
                break
        
        # Remove old contact info if present
        body = body.replace("Machinecraft Technologies\nrushabh@machinecraft.org", "")
        body = body.replace("+91 98XXX XXXXX", "")
        
        # Clean up extra whitespace
        body = body.strip()
        
        # Add elegant signature
        elegant_sig = get_elegant_signature("professional")
        body = body + "\n" + elegant_sig
        
        # Apply LLM polish for human touch (if available)
        if OPENAI_AVAILABLE:
            try:
                body = polish_with_llm(
                    body,
                    customer_name=contact_name if contact_name != "Team" else None,
                    context=f"Drip campaign email for {lead_profile.get('company')} in {application_hint or 'general'} industry",
                    personality_level="balanced"
                )
            except Exception as e:
                print(f"[drip_campaign] LLM polish skipped: {e}")
        
        return body
    
    def generate_email_luxury(
        self,
        lead_id: str,
        stage: int = None,
        contact_name: str = None,
        custom_context: str = None,
    ) -> Dict[str, str]:
        """
        Generate a luxury-polished drip email with full Ira personality.
        
        This is the premium version that uses LLM polish for maximum
        human warmth and brand voice.
        
        Args:
            lead_id: Lead identifier
            stage: Campaign stage (1-5)
            contact_name: Recipient name (will try to find from profile if None)
            custom_context: Additional context for personalization
        
        Returns:
            Dict with 'subject', 'body', 'stage', etc.
        """
        lead_profile = self.get_lead_profile(lead_id)
        if not lead_profile:
            return None
        
        # Try to get contact name from profile
        if not contact_name:
            key_contacts = lead_profile.get("key_contacts_to_find", [])
            if key_contacts:
                contact_name = key_contacts[0].split()[0] if key_contacts[0] else "Team"
            else:
                contact_name = "Team"
        
        # Generate base email
        email = self.generate_email(
            lead_id=lead_id,
            stage=stage,
            contact_name=contact_name,
            use_luxury_polish=True,
        )
        
        if not email:
            return None
        
        # Add metadata for review
        email["polished"] = True
        email["contact_name"] = contact_name
        email["key_contacts"] = lead_profile.get("key_contacts_to_find", [])
        email["sales_approach"] = lead_profile.get("sales_approach", "")
        email["purchasing_signals"] = lead_profile.get("purchasing_readiness", {}).get("signals", [])
        
        return email
    
    def _generate_bullet_points(self, lead_profile: Dict[str, Any]) -> str:
        """Generate relevant bullet points based on lead profile."""
        fit = lead_profile.get("machinecraft_fit", {})
        products = fit.get("products", [])
        opportunity = fit.get("opportunity", "")
        
        bullets = []
        if "PF series" in str(products):
            bullets.append("• PF series thermoformers for capacity expansion")
        if "Shoda" in str(products) or "router" in str(products).lower():
            bullets.append("• 5-axis CNC routing for precision trimming")
        if "sheet" in str(products).lower() or "StellarX" in str(products):
            bullets.append("• High-quality sheet materials (ABS, ASA, specialty blends)")
        if "tooling" in str(products).lower():
            bullets.append("• Thermoforming tooling and mold services")
        
        if not bullets:
            bullets = [
                "• Modern thermoforming equipment at competitive pricing",
                "• Strong after-sales support in Europe",
                "• Turnkey solutions from machine to tooling"
            ]
        
        return "\n".join(bullets[:4])
    
    def _get_urgency_hook(self, lead_profile: Dict[str, Any]) -> str:
        """Get appropriate urgency hook for the lead."""
        company = lead_profile["company"]
        country = lead_profile["country"]
        
        hooks = [
            URGENCY_HOOKS["trade_show"],
            URGENCY_HOOKS["demo"].format(timeframe="Q2 2026", company=company),
            URGENCY_HOOKS["reference"].format(country=country),
        ]
        
        return random.choice(hooks)
    
    def get_leads_ready_for_outreach(self) -> List[Dict[str, Any]]:
        """Get all leads that are ready for their next email."""
        ready = []
        now = datetime.now()
        
        for lead_id, lead in self.campaign_state.items():
            if lead.unsubscribed or lead.replied:
                continue
            
            if lead.current_stage >= 5:
                continue
            
            intervals = self.SEND_INTERVALS[lead.priority]
            next_stage = lead.current_stage + 1
            
            if next_stage > len(intervals):
                continue
            
            if lead.last_email_sent is None:
                # Never sent — ready now
                ready.append({
                    "lead_id": lead_id,
                    "company": lead.company,
                    "country": lead.country,
                    "priority": lead.priority.value,
                    "next_stage": next_stage,
                    "days_until_ready": 0,
                })
            else:
                days_since = (now - lead.last_email_sent).days
                interval = intervals[lead.current_stage] if lead.current_stage < len(intervals) else intervals[-1]
                days_until = interval - days_since
                
                if days_until <= 0:
                    ready.append({
                        "lead_id": lead_id,
                        "company": lead.company,
                        "country": lead.country,
                        "priority": lead.priority.value,
                        "next_stage": next_stage,
                        "days_until_ready": 0,
                    })
        
        # Sort by priority (critical first) then by company name
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        ready.sort(key=lambda x: (priority_order.get(x["priority"], 2), x["company"]))
        
        return ready
    
    def record_email_sent(self, lead_id: str, stage: int = None):
        """Record that an email was sent to a lead."""
        if lead_id not in self.campaign_state:
            return False
        
        lead = self.campaign_state[lead_id]
        lead.last_email_sent = datetime.now()
        lead.emails_sent += 1
        if stage:
            lead.current_stage = stage
        else:
            lead.current_stage += 1
        
        self._save_state()
        return True
    
    def get_next_email(self, lead_id: str) -> Optional[Dict[str, str]]:
        """Get the next email to send for a lead (convenience wrapper)."""
        campaign_lead = self.campaign_state.get(lead_id)
        if not campaign_lead:
            return None
        next_stage = campaign_lead.current_stage + 1
        return self.generate_email(lead_id, stage=next_stage, use_luxury_polish=False)

    def record_reply(self, lead_id: str, notes: str = "", quality: str = ""):
        """Record that a lead replied (stops drip sequence)."""
        if lead_id not in self.campaign_state:
            return False
        
        lead = self.campaign_state[lead_id]
        lead.replied = True
        if notes:
            lead.notes = notes
        if quality:
            lead.reply_quality = quality
            lead.reply_at = datetime.now()
        
        self._save_state()
        return True
    
    def get_campaign_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the campaign."""
        total = len(self.campaign_state)
        by_priority = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        by_stage = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        replied = 0
        unsubscribed = 0
        
        for lead in self.campaign_state.values():
            by_priority[lead.priority.value] += 1
            by_stage[lead.current_stage] += 1
            if lead.replied:
                replied += 1
            if lead.unsubscribed:
                unsubscribed += 1
        
        return {
            "total_leads": total,
            "by_priority": by_priority,
            "by_stage": by_stage,
            "replied": replied,
            "unsubscribed": unsubscribed,
            "ready_for_outreach": len(self.get_leads_ready_for_outreach()),
        }


# Singleton instance
_campaign_instance = None

def get_campaign() -> EuropeanDripCampaign:
    """Get or create the campaign singleton."""
    global _campaign_instance
    if _campaign_instance is None:
        _campaign_instance = EuropeanDripCampaign()
    return _campaign_instance


# CLI interface for testing
if __name__ == "__main__":
    
    campaign = get_campaign()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "init":
            count = campaign.initialize_leads()
            print(f"Initialized {count} new leads")
            
        elif cmd == "summary":
            summary = campaign.get_campaign_summary()
            print(json.dumps(summary, indent=2))
            
        elif cmd == "ready":
            ready = campaign.get_leads_ready_for_outreach()
            print(f"\n{len(ready)} leads ready for outreach:\n")
            for lead in ready[:10]:
                print(f"  [{lead['priority'].upper()}] {lead['company']} ({lead['country']}) - Stage {lead['next_stage']}")
            
        elif cmd == "email" and len(sys.argv) > 2:
            lead_id = sys.argv[2]
            stage = int(sys.argv[3]) if len(sys.argv) > 3 else None
            email = campaign.generate_email(lead_id, stage=stage, use_luxury_polish=False)
            if email:
                print(f"\n{'='*60}")
                print(f"TO: {email['company']}")
                print(f"SUBJECT: {email['subject']}")
                print(f"PRIORITY: {email['priority']}")
                print(f"STAGE: {email['stage']}")
                print(f"{'='*60}\n")
                print(email['body'])
            else:
                print(f"Lead {lead_id} not found")
        
        elif cmd == "luxury" and len(sys.argv) > 2:
            # Generate luxury polished email
            lead_id = sys.argv[2]
            stage = int(sys.argv[3]) if len(sys.argv) > 3 else None
            
            print(f"\n{'─'*60}")
            print("LUXURY POLISH EMAIL GENERATION")
            print(f"{'─'*60}")
            print(f"Luxury Polish Available: {LUXURY_POLISH_AVAILABLE}")
            print(f"OpenAI Available: {OPENAI_AVAILABLE}")
            print(f"{'─'*60}\n")
            
            email = campaign.generate_email_luxury(lead_id, stage=stage)
            if email:
                print(f"TO: {email['company']}")
                print(f"CONTACT: {email.get('contact_name', 'N/A')}")
                print(f"SUBJECT: {email['subject']}")
                print(f"PRIORITY: {email['priority']}")
                print(f"STAGE: {email['stage']}")
                print(f"POLISHED: {email.get('polished', False)}")
                print(f"\n{'─'*60}")
                print("SALES APPROACH:")
                print(email.get('sales_approach', 'N/A'))
                print(f"{'─'*60}")
                print("KEY CONTACTS TO FIND:")
                for contact in email.get('key_contacts', []):
                    print(f"  • {contact}")
                print(f"{'─'*60}\n")
                print("EMAIL BODY:")
                print(f"{'─'*60}\n")
                print(email['body'])
            else:
                print(f"Lead {lead_id} not found")
        
        elif cmd == "compare" and len(sys.argv) > 2:
            # Compare standard vs luxury polish
            lead_id = sys.argv[2]
            stage = int(sys.argv[3]) if len(sys.argv) > 3 else 1
            
            print(f"\n{'═'*70}")
            print("COMPARISON: Standard vs Luxury Polish")
            print(f"{'═'*70}")
            
            # Generate standard email
            standard = campaign.generate_email(lead_id, stage=stage, use_luxury_polish=False)
            if not standard:
                print(f"Lead {lead_id} not found")
            else:
                print(f"\n{'─'*70}")
                print("STANDARD EMAIL (no luxury polish)")
                print(f"{'─'*70}\n")
                print(standard['body'][:1500])
                if len(standard['body']) > 1500:
                    print("\n...[truncated]")
                
                # Generate luxury email
                print(f"\n{'─'*70}")
                print("LUXURY POLISHED EMAIL (with Ira personality)")
                print(f"{'─'*70}\n")
                luxury = campaign.generate_email_luxury(lead_id, stage=stage)
                print(luxury['body'][:2000])
                if len(luxury['body']) > 2000:
                    print("\n...[truncated]")
        
        elif cmd == "intel" and len(sys.argv) > 2:
            # Test lead intelligence
            lead_id = sys.argv[2]
            lead_profile = campaign.get_lead_profile(lead_id)
            
            if not lead_profile:
                print(f"Lead {lead_id} not found")
            else:
                print(f"\n{'─'*60}")
                print(f"LEAD INTELLIGENCE: {lead_profile['company']}")
                print(f"{'─'*60}")
                print(f"Intelligence Available: {INTELLIGENCE_AVAILABLE}")
                print(f"{'─'*60}\n")
                
                if INTELLIGENCE_AVAILABLE:
                    hooks = enrich_lead_for_email(
                        lead_id=lead_id,
                        company=lead_profile["company"],
                        country=lead_profile.get("country", ""),
                        industries=lead_profile.get("industries", []),
                        website=lead_profile.get("website", ""),
                    )
                    
                    print("INTELLIGENCE HOOKS:")
                    for key, value in hooks.items():
                        print(f"  {key}: {value}")
                    
                    if not hooks:
                        print("  (No intelligence gathered - may need JINA_API_KEY)")
                else:
                    print("Lead intelligence not available - import failed")
        
        else:
            print("Usage:")
            print("  python european_drip_campaign.py init                 - Initialize leads")
            print("  python european_drip_campaign.py summary              - Show campaign summary")
            print("  python european_drip_campaign.py ready                - Show leads ready")
            print("  python european_drip_campaign.py email <lead_id> [stage]   - Standard email")
            print("  python european_drip_campaign.py luxury <lead_id> [stage]  - Luxury polished email")
            print("  python european_drip_campaign.py compare <lead_id> [stage] - Compare both versions")
            print("  python european_drip_campaign.py intel <lead_id>           - Test lead intelligence")
    else:
        # Default: show summary
        print("European Drip Campaign")
        print("=" * 40)
        print(f"Luxury Polish:     {'✓ Available' if LUXURY_POLISH_AVAILABLE else '✗ Not available'}")
        print(f"OpenAI Polish:     {'✓ Available' if OPENAI_AVAILABLE else '✗ Not available'}")
        print(f"Iris Intelligence: {'✓ Available' if IRIS_AVAILABLE else '✗ Not available (fallback)' if INTELLIGENCE_AVAILABLE else '✗ Not available'}")
        print("=" * 40)
        summary = campaign.get_campaign_summary()
        print(f"Total leads: {summary['total_leads']}")
        print(f"Ready for outreach: {summary['ready_for_outreach']}")
        print(f"\nBy priority: {summary['by_priority']}")
