"""
Unified Identity Module
=======================

Single source of truth for contact identity across all Ira systems.

Usage:
    from openclaw.agents.ira.src.identity import (
        get_identity_service,
        resolve_identity,
        link_identities,
        get_customer_context,
        CustomerContext,
    )
    
    # Resolve a contact
    contact_id = resolve_identity("email", "john@example.com")
    
    # Link across channels
    link_identities("email", "john@example.com", "telegram", "123456")
    
    # Get customer context for personalized responses
    context = get_customer_context(contact_id)
"""

from .unified_identity import (
    UnifiedIdentityService,
    Contact,
    get_identity_service,
    resolve_identity,
    link_identities,
)

from .customer_context import (
    CustomerContext,
    CustomerRelationship,
    CommunicationStyle,
    CustomerTier,
    CustomerContextManager,
    get_customer_context,
    get_customer_context_manager,
)

__all__ = [
    # Unified Identity
    "UnifiedIdentityService",
    "Contact",
    "get_identity_service",
    "resolve_identity",
    "link_identities",
    # Customer Context
    "CustomerContext",
    "CustomerRelationship",
    "CommunicationStyle",
    "CustomerTier",
    "CustomerContextManager",
    "get_customer_context",
    "get_customer_context_manager",
]
