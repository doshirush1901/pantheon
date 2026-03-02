#!/usr/bin/env python3
"""
PROACTIVE OUTREACH SYSTEM - Intelligent Customer Follow-Up
==========================================================

Identifies customers who need attention and generates personalized
follow-up messages based on their conversation history.

Features:
- Query episodic memory for customers inactive 30+ days
- Identify customers with open inquiries but no recent contact
- Generate personalized follow-up emails using conversation context
- Daily scheduler integration for automated outreach

Usage:
    from src.sales.proactive_outreach import (
        ProactiveOutreachEngine,
        identify_outreach_candidates,
        draft_follow_up_email,
    )
    
    # Get candidates for outreach
    candidates = identify_outreach_candidates(inactive_days=30)
    
    # Generate personalized follow-up for a customer
    email = draft_follow_up_email(customer_context)
    
    # Run as daily job
    from proactive_outreach import run_daily_outreach
    run_daily_outreach()
"""

import os
import sys
import json
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

SKILL_DIR = Path(__file__).parent
SKILLS_DIR = SKILL_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(SKILLS_DIR / "memory"))
sys.path.insert(0, str(SKILLS_DIR / "identity"))
sys.path.insert(0, str(SKILLS_DIR / "crm"))
sys.path.insert(0, str(AGENT_DIR))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

try:
    from unified_mem0 import get_mem0_client
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False

try:
    from unified_identity import get_identity_service
    IDENTITY_AVAILABLE = True
except ImportError:
    IDENTITY_AVAILABLE = False

try:
    from quote_lifecycle import get_tracker
    CRM_AVAILABLE = True
except ImportError:
    CRM_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OutreachPriority(Enum):
    """Priority level for outreach candidates."""
    URGENT = "urgent"       # High-value, long silent
    HIGH = "high"           # Open inquiry, needs follow-up
    MEDIUM = "medium"       # Regular check-in due
    LOW = "low"             # Routine maintenance


class OutreachReason(Enum):
    """Reason for suggesting outreach."""
    INACTIVE_30_DAYS = "inactive_30_days"
    OPEN_INQUIRY = "open_inquiry"
    STALE_QUOTE = "stale_quote"
    RELATIONSHIP_AT_RISK = "relationship_at_risk"
    UPSELL_OPPORTUNITY = "upsell_opportunity"


@dataclass
class CustomerContext:
    """Context about a customer for generating follow-ups."""
    customer_id: str
    name: str
    email: str
    company: Optional[str] = None
    
    last_contact_date: Optional[datetime] = None
    days_since_contact: int = 0
    
    open_inquiries: List[str] = field(default_factory=list)
    past_products: List[str] = field(default_factory=list)
    
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    relationship_score: float = 0.5
    
    priority: OutreachPriority = OutreachPriority.MEDIUM
    reason: OutreachReason = OutreachReason.INACTIVE_30_DAYS


@dataclass
class OutreachCandidate:
    """A customer identified for proactive outreach."""
    context: CustomerContext
    suggested_action: str
    suggested_subject: str
    suggested_body: str
    confidence: float = 0.8
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "customer_id": self.context.customer_id,
            "name": self.context.name,
            "email": self.context.email,
            "company": self.context.company,
            "days_since_contact": self.context.days_since_contact,
            "priority": self.context.priority.value,
            "reason": self.context.reason.value,
            "suggested_action": self.suggested_action,
            "suggested_subject": self.suggested_subject,
            "confidence": self.confidence,
        }


class ProactiveOutreachEngine:
    """
    Intelligent engine for identifying and engaging dormant customers.
    
    Queries episodic memory to find customers who:
    1. Haven't been contacted in 30+ days
    2. Have open inquiries or stale quotes
    3. Show declining engagement patterns
    """
    
    INACTIVE_THRESHOLD_DAYS = 30
    HIGH_VALUE_THRESHOLD_USD = 25000
    
    EMAIL_TEMPLATES = {
        "inactive_30_days": {
            "subject": "Following up on your thermoforming requirements",
            "intro": "I wanted to reach out as it's been a while since we last connected.",
            "cta": "Would you have time for a brief call this week to discuss your current requirements?"
        },
        "open_inquiry": {
            "subject": "Regarding your {product} inquiry",
            "intro": "I'm following up on your inquiry about {product}.",
            "cta": "Please let me know if you need any additional information or if your requirements have changed."
        },
        "stale_quote": {
            "subject": "Checking in on your {product} quotation",
            "intro": "I wanted to follow up on the quotation I sent for the {product}.",
            "cta": "If timing or budget has changed, I'd be happy to discuss alternatives that might work better."
        },
        "relationship_at_risk": {
            "subject": "We value your partnership",
            "intro": "I noticed we haven't had a chance to connect recently and wanted to check in.",
            "cta": "Is there anything we can do to better support your needs?"
        },
    }
    
    def __init__(self):
        self.identity_service = get_identity_service() if IDENTITY_AVAILABLE else None
        self.crm_tracker = get_tracker() if CRM_AVAILABLE else None
    
    def identify_outreach_candidates(
        self,
        inactive_days: int = 30,
        max_candidates: int = 20,
    ) -> List[OutreachCandidate]:
        """
        Query episodic memory and CRM to find customers needing outreach.
        
        Returns:
            List of OutreachCandidate sorted by priority
        """
        candidates = []
        
        inactive_customers = self._query_inactive_customers(inactive_days)
        for ctx in inactive_customers:
            candidate = self._create_candidate(ctx)
            if candidate:
                candidates.append(candidate)
        
        if self.crm_tracker:
            stale_quotes = self._get_stale_quote_customers()
            for ctx in stale_quotes:
                if not any(c.context.customer_id == ctx.customer_id for c in candidates):
                    candidate = self._create_candidate(ctx)
                    if candidate:
                        candidates.append(candidate)
        
        candidates.sort(key=lambda c: (
            {"urgent": 0, "high": 1, "medium": 2, "low": 3}[c.context.priority.value],
            -c.context.days_since_contact,
        ))
        
        return candidates[:max_candidates]
    
    def _query_inactive_customers(self, days_threshold: int) -> List[CustomerContext]:
        """Query episodic memory for customers with no recent interactions."""
        contexts = []
        
        if MEM0_AVAILABLE:
            try:
                client = get_mem0_client()
                
                cutoff_date = datetime.now() - timedelta(days=days_threshold)
                
                all_memories = client.get_all(
                    user_id="machinecraft_customers",
                    output_format="v1.1"
                )
                
                customer_last_activity = {}
                
                for memory in all_memories.get("memories", []):
                    metadata = memory.get("metadata", {})
                    customer_id = metadata.get("customer_id") or metadata.get("contact_id")
                    
                    if not customer_id:
                        continue
                    
                    created_at = memory.get("created_at", "")
                    try:
                        if isinstance(created_at, str):
                            activity_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        else:
                            activity_date = created_at
                        activity_date = activity_date.replace(tzinfo=None)
                    except (ValueError, AttributeError):
                        continue
                    
                    if customer_id not in customer_last_activity:
                        customer_last_activity[customer_id] = {
                            "last_date": activity_date,
                            "memories": [memory],
                        }
                    else:
                        if activity_date > customer_last_activity[customer_id]["last_date"]:
                            customer_last_activity[customer_id]["last_date"] = activity_date
                        customer_last_activity[customer_id]["memories"].append(memory)
                
                for customer_id, data in customer_last_activity.items():
                    if data["last_date"] < cutoff_date:
                        ctx = self._build_customer_context(
                            customer_id,
                            data["last_date"],
                            data["memories"],
                        )
                        if ctx:
                            contexts.append(ctx)
                
            except Exception as e:
                print(f"[ProactiveOutreach] Mem0 query error: {e}")
        
        return contexts
    
    def _get_stale_quote_customers(self) -> List[CustomerContext]:
        """Get customers with stale quotes from CRM."""
        contexts = []
        
        if self.crm_tracker:
            try:
                stale_quotes = self.crm_tracker.get_stale_quotes(days=14)
                
                seen_customers = set()
                for quote in stale_quotes:
                    customer_key = quote.customer_email
                    if customer_key in seen_customers:
                        continue
                    seen_customers.add(customer_key)
                    
                    ctx = CustomerContext(
                        customer_id=quote.customer_email,
                        name=quote.customer_name or "Customer",
                        email=quote.customer_email,
                        company=quote.company,
                        days_since_contact=quote.days_since_follow_up() or 0,
                        open_inquiries=[quote.product],
                        priority=OutreachPriority.HIGH,
                        reason=OutreachReason.STALE_QUOTE,
                    )
                    contexts.append(ctx)
                    
            except Exception as e:
                print(f"[ProactiveOutreach] CRM query error: {e}")
        
        return contexts
    
    def _build_customer_context(
        self,
        customer_id: str,
        last_activity: datetime,
        memories: List[Dict],
    ) -> Optional[CustomerContext]:
        """Build CustomerContext from identity service and memories."""
        name = customer_id
        email = ""
        company = None
        
        if self.identity_service:
            contact = self.identity_service.get_contact(customer_id)
            if contact:
                name = contact.name or customer_id
                email = contact.email or ""
                company = contact.company
        
        if not email:
            if "@" in customer_id:
                email = customer_id
            else:
                return None
        
        days_since = (datetime.now() - last_activity).days
        
        products_mentioned = []
        conversation_snippets = []
        
        for memory in memories[:10]:
            text = memory.get("memory", "")
            
            for product in ["PF1", "IMG", "FCS", "AM", "ATF"]:
                if product in text.upper() and product not in products_mentioned:
                    products_mentioned.append(product)
            
            conversation_snippets.append({
                "text": text[:200],
                "date": memory.get("created_at", ""),
            })
        
        priority = OutreachPriority.MEDIUM
        if days_since > 60:
            priority = OutreachPriority.HIGH
        if days_since > 90:
            priority = OutreachPriority.URGENT
        
        return CustomerContext(
            customer_id=customer_id,
            name=name,
            email=email,
            company=company,
            last_contact_date=last_activity,
            days_since_contact=days_since,
            open_inquiries=products_mentioned,
            past_products=products_mentioned,
            conversation_history=conversation_snippets,
            priority=priority,
            reason=OutreachReason.INACTIVE_30_DAYS,
        )
    
    def _create_candidate(self, ctx: CustomerContext) -> Optional[OutreachCandidate]:
        """Create OutreachCandidate with suggested follow-up content."""
        template_key = ctx.reason.value
        template = self.EMAIL_TEMPLATES.get(template_key, self.EMAIL_TEMPLATES["inactive_30_days"])
        
        product = ctx.open_inquiries[0] if ctx.open_inquiries else "thermoforming machine"
        
        subject = template["subject"].format(product=product)
        
        first_name = ctx.name.split()[0] if ctx.name else "there"
        
        body = f"""Hi {first_name},

{template['intro'].format(product=product)}

{template['cta']}

Best regards,
Rushabh Doshi
Director - Sales & Marketing
Machinecraft Technologies
+91-22-40140000
rushabh@machinecraft.org"""
        
        action = {
            OutreachReason.INACTIVE_30_DAYS: "Send check-in email",
            OutreachReason.OPEN_INQUIRY: "Follow up on inquiry",
            OutreachReason.STALE_QUOTE: "Follow up on quote",
            OutreachReason.RELATIONSHIP_AT_RISK: "Re-engage customer",
            OutreachReason.UPSELL_OPPORTUNITY: "Suggest upgrade",
        }.get(ctx.reason, "Send follow-up")
        
        return OutreachCandidate(
            context=ctx,
            suggested_action=action,
            suggested_subject=subject,
            suggested_body=body,
            confidence=0.8,
        )


def draft_follow_up_email(customer_context: CustomerContext) -> Dict[str, str]:
    """
    Generate a personalized follow-up email for a customer.
    
    Uses conversation history and context to craft a relevant message.
    
    Args:
        customer_context: CustomerContext with customer details and history
    
    Returns:
        Dict with 'subject' and 'body' keys
    """
    engine = ProactiveOutreachEngine()
    candidate = engine._create_candidate(customer_context)
    
    if candidate:
        return {
            "subject": candidate.suggested_subject,
            "body": candidate.suggested_body,
            "to": customer_context.email,
            "priority": customer_context.priority.value,
        }
    
    first_name = customer_context.name.split()[0] if customer_context.name else "there"
    
    return {
        "subject": "Following up on your thermoforming requirements",
        "body": f"""Hi {first_name},

I wanted to reach out as it's been a while since we last connected.

If you have any thermoforming projects coming up, I'd be happy to discuss how Machinecraft can help.

Best regards,
Rushabh Doshi
Machinecraft Technologies""",
        "to": customer_context.email,
        "priority": "medium",
    }


def identify_outreach_candidates(
    inactive_days: int = 30,
    max_candidates: int = 20,
) -> List[OutreachCandidate]:
    """
    High-level function to identify customers needing outreach.
    
    Args:
        inactive_days: Threshold for considering a customer inactive
        max_candidates: Maximum number of candidates to return
    
    Returns:
        List of OutreachCandidate sorted by priority
    """
    engine = ProactiveOutreachEngine()
    return engine.identify_outreach_candidates(inactive_days, max_candidates)


def run_daily_outreach() -> Dict[str, Any]:
    """
    Run daily outreach check - designed to be called by scheduler.
    
    Returns:
        Summary of outreach candidates identified
    """
    candidates = identify_outreach_candidates(inactive_days=30, max_candidates=10)
    
    result = {
        "candidates_found": len(candidates),
        "urgent": sum(1 for c in candidates if c.context.priority == OutreachPriority.URGENT),
        "high": sum(1 for c in candidates if c.context.priority == OutreachPriority.HIGH),
        "medium": sum(1 for c in candidates if c.context.priority == OutreachPriority.MEDIUM),
        "low": sum(1 for c in candidates if c.context.priority == OutreachPriority.LOW),
        "candidates": [c.to_dict() for c in candidates[:5]],
        "timestamp": datetime.now().isoformat(),
    }
    
    if candidates:
        try:
            telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            chat_id = os.environ.get("ADMIN_TELEGRAM_ID", os.environ.get("RUSHABH_TELEGRAM_ID", ""))
            
            if telegram_token:
                import requests
                
                message = f"📬 *Proactive Outreach Report*\n"
                message += f"━━━━━━━━━━━━━━━━━\n"
                message += f"Found {len(candidates)} customers needing attention:\n"
                message += f"🔴 Urgent: {result['urgent']}\n"
                message += f"🟠 High: {result['high']}\n"
                message += f"🟡 Medium: {result['medium']}\n\n"
                
                for c in candidates[:3]:
                    priority_emoji = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
                    message += f"{priority_emoji.get(c.context.priority.value, '⚪')} "
                    message += f"*{c.context.name}*"
                    if c.context.company:
                        message += f" ({c.context.company})"
                    message += f"\n   {c.context.days_since_contact}d inactive"
                    message += f" | {c.suggested_action}\n\n"
                
                message += "_Reply with customer name to draft follow-up_"
                
                requests.post(
                    f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": "Markdown",
                    },
                    timeout=10,
                )
                result["notification_sent"] = True
        except Exception as e:
            result["notification_error"] = str(e)
    
    return result


_engine: Optional[ProactiveOutreachEngine] = None


def get_outreach_engine() -> ProactiveOutreachEngine:
    """Get singleton outreach engine."""
    global _engine
    if _engine is None:
        _engine = ProactiveOutreachEngine()
    return _engine


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Proactive Outreach System")
    parser.add_argument("--identify", action="store_true", help="Identify outreach candidates")
    parser.add_argument("--days", type=int, default=30, help="Inactive days threshold")
    parser.add_argument("--max", type=int, default=10, help="Max candidates")
    parser.add_argument("--daily", action="store_true", help="Run daily outreach check")
    args = parser.parse_args()
    
    if args.daily:
        print("Running daily outreach check...")
        result = run_daily_outreach()
        print(json.dumps(result, indent=2))
    
    elif args.identify:
        print(f"\nIdentifying customers inactive for {args.days}+ days...")
        candidates = identify_outreach_candidates(args.days, args.max)
        
        print(f"\n📬 Found {len(candidates)} outreach candidates:")
        print("=" * 60)
        
        for c in candidates:
            priority_emoji = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
            print(f"\n{priority_emoji.get(c.context.priority.value, '⚪')} {c.context.name}")
            if c.context.company:
                print(f"   Company: {c.context.company}")
            print(f"   Email: {c.context.email}")
            print(f"   Days since contact: {c.context.days_since_contact}")
            print(f"   Reason: {c.context.reason.value}")
            print(f"   Action: {c.suggested_action}")
    
    else:
        parser.print_help()
