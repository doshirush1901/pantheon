#!/usr/bin/env python3
"""
Customer Context Manager - Customer Profile & Context Awareness
================================================================

Implements Strategy 7 from DEEP_REPLY_IMPROVEMENT_STRATEGY.md:
- Customer profile integration
- Past inquiry tracking
- Communication style adaptation
- Relationship context

This enables IRA to understand WHO is asking, not just WHAT they're asking,
allowing for personalized, context-aware responses.

Usage:
    from openclaw.agents.ira.src.identity.customer_context import (
        CustomerContext, get_customer_context, CustomerContextManager
    )
    
    context = get_customer_context(identity_id)
    print(context.role)  # "Technical Manager"
    print(context.preferred_style)  # "detailed, technical"
"""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

SKILLS_DIR = Path(__file__).parent.parent
AGENT_DIR = SKILLS_DIR.parent

try:
    sys.path.insert(0, str(AGENT_DIR))
    from config import get_logger, get_openai_client, FAST_LLM_MODEL
    CONFIG_AVAILABLE = True
    logger = get_logger(__name__)
except ImportError:
    CONFIG_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)
    FAST_LLM_MODEL = "gpt-4.1-mini"

try:
    from unified_identity import get_identity_service, Contact
except ImportError:
    try:
        from .unified_identity import get_identity_service, Contact
    except ImportError:
        get_identity_service = None
        Contact = None


class CustomerRelationship(str, Enum):
    """Type of relationship with the customer."""
    INTERNAL = "internal"
    PROSPECT = "prospect"
    ACTIVE_CUSTOMER = "active_customer"
    PAST_CUSTOMER = "past_customer"
    PARTNER = "partner"
    COMPETITOR = "competitor"
    UNKNOWN = "unknown"


class CommunicationStyle(str, Enum):
    """Preferred communication style."""
    TECHNICAL_DETAILED = "technical_detailed"
    TECHNICAL_CONCISE = "technical_concise"
    BUSINESS_FORMAL = "business_formal"
    CASUAL_FRIENDLY = "casual_friendly"
    EXECUTIVE_BRIEF = "executive_brief"
    DEFAULT = "default"


class CustomerTier(str, Enum):
    """Customer value tier."""
    VIP = "vip"
    HIGH_VALUE = "high_value"
    STANDARD = "standard"
    EMERGING = "emerging"
    UNKNOWN = "unknown"


@dataclass
class PastInquiry:
    """Record of a past customer inquiry."""
    timestamp: str
    subject: str
    intent: str
    machines_discussed: List[str] = field(default_factory=list)
    outcome: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "subject": self.subject,
            "intent": self.intent,
            "machines_discussed": self.machines_discussed,
            "outcome": self.outcome,
        }


@dataclass
class CustomerContext:
    """
    Complete customer context for personalized responses.
    
    Contains:
    - Identity information (name, company, role)
    - Relationship type and tier
    - Communication preferences
    - Past inquiry history
    - Business context
    """
    identity_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    industry: Optional[str] = None
    relationship: CustomerRelationship = CustomerRelationship.UNKNOWN
    tier: CustomerTier = CustomerTier.UNKNOWN
    preferred_style: CommunicationStyle = CommunicationStyle.DEFAULT
    past_inquiries: List[PastInquiry] = field(default_factory=list)
    known_applications: List[str] = field(default_factory=list)
    previous_machines: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    last_contact: Optional[str] = None
    total_interactions: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "identity_id": self.identity_id,
            "name": self.name,
            "email": self.email,
            "company": self.company,
            "role": self.role,
            "industry": self.industry,
            "relationship": self.relationship.value,
            "tier": self.tier.value,
            "preferred_style": self.preferred_style.value,
            "past_inquiries": [p.to_dict() for p in self.past_inquiries],
            "known_applications": self.known_applications,
            "previous_machines": self.previous_machines,
            "preferences": self.preferences,
            "notes": self.notes,
            "last_contact": self.last_contact,
            "total_interactions": self.total_interactions,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomerContext":
        """Create from dictionary."""
        return cls(
            identity_id=data.get("identity_id", ""),
            name=data.get("name"),
            email=data.get("email"),
            company=data.get("company"),
            role=data.get("role"),
            industry=data.get("industry"),
            relationship=CustomerRelationship(data.get("relationship", "unknown")),
            tier=CustomerTier(data.get("tier", "unknown")),
            preferred_style=CommunicationStyle(data.get("preferred_style", "default")),
            past_inquiries=[
                PastInquiry(**p) for p in data.get("past_inquiries", [])
            ],
            known_applications=data.get("known_applications", []),
            previous_machines=data.get("previous_machines", []),
            preferences=data.get("preferences", {}),
            notes=data.get("notes", []),
            last_contact=data.get("last_contact"),
            total_interactions=data.get("total_interactions", 0),
        )
    
    def to_prompt_context(self) -> str:
        """Format context for inclusion in LLM prompts."""
        parts = ["[Customer Context]"]
        
        if self.name:
            parts.append(f"Name: {self.name}")
        if self.company:
            parts.append(f"Company: {self.company}")
        if self.role:
            parts.append(f"Role: {self.role}")
        if self.industry:
            parts.append(f"Industry: {self.industry}")
        
        parts.append(f"Relationship: {self.relationship.value}")
        
        if self.preferred_style != CommunicationStyle.DEFAULT:
            style_desc = {
                CommunicationStyle.TECHNICAL_DETAILED: "prefers detailed technical explanations",
                CommunicationStyle.TECHNICAL_CONCISE: "prefers brief technical responses",
                CommunicationStyle.BUSINESS_FORMAL: "prefers formal business communication",
                CommunicationStyle.CASUAL_FRIENDLY: "prefers casual, friendly tone",
                CommunicationStyle.EXECUTIVE_BRIEF: "prefers executive-level summaries",
            }.get(self.preferred_style, "")
            if style_desc:
                parts.append(f"Communication: {style_desc}")
        
        if self.previous_machines:
            parts.append(f"Previous machines discussed: {', '.join(self.previous_machines[:5])}")
        
        if self.known_applications:
            parts.append(f"Known applications: {', '.join(self.known_applications[:3])}")
        
        if self.past_inquiries:
            recent = self.past_inquiries[-3:]
            inquiry_strs = [f"  - {p.subject} ({p.intent})" for p in recent]
            parts.append("Recent inquiries:\n" + "\n".join(inquiry_strs))
        
        return "\n".join(parts)
    
    def get_style_instructions(self) -> str:
        """Get communication style instructions for response generation."""
        instructions = {
            CommunicationStyle.TECHNICAL_DETAILED: (
                "Provide detailed technical information with specifications, "
                "engineering explanations, and comprehensive data. Include tables "
                "and comparisons where relevant."
            ),
            CommunicationStyle.TECHNICAL_CONCISE: (
                "Be technically accurate but concise. Focus on key specs and "
                "actionable information. Avoid lengthy explanations."
            ),
            CommunicationStyle.BUSINESS_FORMAL: (
                "Use professional, formal business language. Focus on value "
                "propositions, ROI, and business benefits. Be respectful of their time."
            ),
            CommunicationStyle.CASUAL_FRIENDLY: (
                "Be warm and conversational while remaining professional. "
                "Use simple language and relatable examples."
            ),
            CommunicationStyle.EXECUTIVE_BRIEF: (
                "Provide executive summary format. Lead with conclusions, "
                "key numbers, and recommendations. Keep it under 200 words."
            ),
            CommunicationStyle.DEFAULT: (
                "Be helpful, professional, and informative. Match the tone "
                "and complexity to the customer's query."
            ),
        }
        return instructions.get(self.preferred_style, instructions[CommunicationStyle.DEFAULT])
    
    @property
    def is_internal(self) -> bool:
        """Check if this is an internal user."""
        return self.relationship == CustomerRelationship.INTERNAL
    
    @property
    def is_high_value(self) -> bool:
        """Check if this is a high-value customer."""
        return self.tier in [CustomerTier.VIP, CustomerTier.HIGH_VALUE]


class CustomerContextManager:
    """
    Manages customer context retrieval and enrichment.
    
    Integrates with:
    - UnifiedIdentityService for contact data
    - Mem0 for memory-based context
    - Relationship store for history
    """
    
    INTERNAL_DOMAINS = ["machinecraft.org", "machinecraft.com", "machinecraft.in"]
    
    def __init__(self):
        self._context_cache: Dict[str, CustomerContext] = {}
        self._cache_ttl = timedelta(minutes=30)
        self._cache_times: Dict[str, datetime] = {}
    
    def get_context(
        self,
        identity_id: str,
        email: Optional[str] = None,
        telegram_id: Optional[str] = None,
        enrich: bool = True,
    ) -> CustomerContext:
        """
        Get customer context for an identity.
        
        Args:
            identity_id: The unified identity ID
            email: Optional email address (for identity resolution)
            telegram_id: Optional telegram ID
            enrich: Whether to enrich from memory (default True)
        
        Returns:
            CustomerContext object
        """
        cache_key = identity_id or email or telegram_id or "unknown"
        
        if cache_key in self._context_cache:
            cache_time = self._cache_times.get(cache_key)
            if cache_time and datetime.now() - cache_time < self._cache_ttl:
                return self._context_cache[cache_key]
        
        context = CustomerContext(identity_id=identity_id or "unknown")
        
        if get_identity_service:
            self._enrich_from_identity(context, identity_id, email, telegram_id)
        
        if enrich:
            self._enrich_from_memory(context)
        
        self._detect_relationship(context)
        self._infer_communication_style(context)
        
        self._context_cache[cache_key] = context
        self._cache_times[cache_key] = datetime.now()
        
        return context
    
    def _enrich_from_identity(
        self,
        context: CustomerContext,
        identity_id: Optional[str],
        email: Optional[str],
        telegram_id: Optional[str],
    ) -> None:
        """Enrich context from UnifiedIdentityService."""
        try:
            service = get_identity_service()
            contact = None
            
            if identity_id:
                contact = service.get_contact(identity_id)
            elif email:
                resolved_id = service.resolve("email", email, create_if_missing=False)
                if resolved_id:
                    contact = service.get_contact(resolved_id)
                    context.identity_id = resolved_id
            elif telegram_id:
                resolved_id = service.resolve("telegram", telegram_id, create_if_missing=False)
                if resolved_id:
                    contact = service.get_contact(resolved_id)
                    context.identity_id = resolved_id
            
            if contact:
                context.name = contact.name
                context.email = contact.email
                context.company = contact.company
                context.last_contact = contact.updated_at
                
                if contact.metadata:
                    context.role = contact.metadata.get("role")
                    context.industry = contact.metadata.get("industry")
                    context.notes = contact.metadata.get("notes", [])
                    
        except Exception as e:
            logger.warning(f"Failed to enrich from identity service: {e}")
    
    def _enrich_from_memory(self, context: CustomerContext) -> None:
        """Enrich context from Mem0 memories."""
        try:
            try:
                from ..memory.mem0_memory import get_mem0_service
            except ImportError:
                from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
            
            mem0 = get_mem0_service()
            
            memories = mem0.get_all(context.identity_id)
            
            for mem in memories:
                text = mem.memory.lower()
                
                if "prefers" in text or "likes" in text or "style" in text:
                    if "technical" in text and "detailed" in text:
                        context.preferred_style = CommunicationStyle.TECHNICAL_DETAILED
                    elif "brief" in text or "concise" in text:
                        context.preferred_style = CommunicationStyle.TECHNICAL_CONCISE
                    elif "formal" in text:
                        context.preferred_style = CommunicationStyle.BUSINESS_FORMAL
                
                if "works with" in text or "application" in text:
                    for app in ["automotive", "packaging", "medical", "aerospace", "food"]:
                        if app in text:
                            if app not in context.known_applications:
                                context.known_applications.append(app)
                
                if "pf1" in text or "am-" in text or "re-" in text:
                    import re
                    machines = re.findall(r'\b(PF[-\s]?1[-\s]?[A-Z]?[-\s]?\d+|AM[-\s]?\d+|RE[-\s]?\d+)\b', 
                                          mem.memory, re.IGNORECASE)
                    for m in machines:
                        normalized = m.upper().replace(" ", "-")
                        if normalized not in context.previous_machines:
                            context.previous_machines.append(normalized)
            
            context.total_interactions = len(memories)
            
        except Exception as e:
            logger.debug(f"Failed to enrich from memory: {e}")
    
    def _detect_relationship(self, context: CustomerContext) -> None:
        """Detect the relationship type from available data."""
        if context.email:
            domain = context.email.split("@")[-1].lower() if "@" in context.email else ""
            if domain in self.INTERNAL_DOMAINS:
                context.relationship = CustomerRelationship.INTERNAL
                context.tier = CustomerTier.VIP
                return
        
        if context.previous_machines:
            context.relationship = CustomerRelationship.ACTIVE_CUSTOMER
            if len(context.previous_machines) >= 3:
                context.tier = CustomerTier.HIGH_VALUE
            else:
                context.tier = CustomerTier.STANDARD
        elif context.total_interactions > 10:
            context.relationship = CustomerRelationship.PROSPECT
            context.tier = CustomerTier.EMERGING
        else:
            context.relationship = CustomerRelationship.UNKNOWN
            context.tier = CustomerTier.UNKNOWN
    
    def _infer_communication_style(self, context: CustomerContext) -> None:
        """Infer communication style from role and history."""
        if context.preferred_style != CommunicationStyle.DEFAULT:
            return
        
        if context.role:
            role_lower = context.role.lower()
            if any(w in role_lower for w in ["engineer", "technical", "r&d", "production"]):
                context.preferred_style = CommunicationStyle.TECHNICAL_DETAILED
            elif any(w in role_lower for w in ["ceo", "director", "president", "owner"]):
                context.preferred_style = CommunicationStyle.EXECUTIVE_BRIEF
            elif any(w in role_lower for w in ["manager", "head", "lead"]):
                context.preferred_style = CommunicationStyle.BUSINESS_FORMAL
            elif any(w in role_lower for w in ["purchasing", "procurement", "buyer"]):
                context.preferred_style = CommunicationStyle.BUSINESS_FORMAL
        
        if context.is_internal:
            context.preferred_style = CommunicationStyle.TECHNICAL_DETAILED
    
    def record_interaction(
        self,
        identity_id: str,
        subject: str,
        intent: str,
        machines: Optional[List[str]] = None,
        outcome: Optional[str] = None,
    ) -> None:
        """
        Record a customer interaction for future context.
        
        Args:
            identity_id: Customer identity ID
            subject: Subject/topic of the interaction
            intent: Detected intent type
            machines: Machines discussed
            outcome: Outcome of the interaction
        """
        inquiry = PastInquiry(
            timestamp=datetime.now().isoformat(),
            subject=subject,
            intent=intent,
            machines_discussed=machines or [],
            outcome=outcome,
        )
        
        if identity_id in self._context_cache:
            context = self._context_cache[identity_id]
            context.past_inquiries.append(inquiry)
            if len(context.past_inquiries) > 20:
                context.past_inquiries = context.past_inquiries[-20:]
            
            if machines:
                for m in machines:
                    if m not in context.previous_machines:
                        context.previous_machines.append(m)
        
        logger.debug(f"Recorded interaction for {identity_id}: {subject}")
    
    def update_style_preference(
        self,
        identity_id: str,
        style: CommunicationStyle,
    ) -> None:
        """Update a customer's preferred communication style."""
        if identity_id in self._context_cache:
            self._context_cache[identity_id].preferred_style = style
        
        logger.info(f"Updated style preference for {identity_id}: {style.value}")
    
    def clear_cache(self, identity_id: Optional[str] = None) -> None:
        """Clear context cache."""
        if identity_id:
            self._context_cache.pop(identity_id, None)
            self._cache_times.pop(identity_id, None)
        else:
            self._context_cache.clear()
            self._cache_times.clear()


_manager: Optional[CustomerContextManager] = None


def get_customer_context_manager() -> CustomerContextManager:
    """Get singleton CustomerContextManager instance."""
    global _manager
    if _manager is None:
        _manager = CustomerContextManager()
    return _manager


def get_customer_context(
    identity_id: str,
    email: Optional[str] = None,
    telegram_id: Optional[str] = None,
) -> CustomerContext:
    """
    Convenience function to get customer context.
    
    Args:
        identity_id: The unified identity ID
        email: Optional email address
        telegram_id: Optional telegram ID
    
    Returns:
        CustomerContext object
    """
    return get_customer_context_manager().get_context(
        identity_id, email, telegram_id
    )


if __name__ == "__main__":
    manager = get_customer_context_manager()
    
    test_ctx = CustomerContext(
        identity_id="test_123",
        name="John Doe",
        company="Acme Plastics",
        role="Technical Manager",
        industry="Automotive",
        relationship=CustomerRelationship.ACTIVE_CUSTOMER,
        tier=CustomerTier.HIGH_VALUE,
        preferred_style=CommunicationStyle.TECHNICAL_DETAILED,
        previous_machines=["PF1-C-2015", "AM-5060"],
        known_applications=["automotive", "interior trim"],
    )
    
    print("Customer Context Test")
    print("=" * 60)
    print(test_ctx.to_prompt_context())
    print()
    print("Style Instructions:")
    print(test_ctx.get_style_instructions())
    print()
    print("Dict representation:")
    print(json.dumps(test_ctx.to_dict(), indent=2))
