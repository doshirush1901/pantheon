"""
Ira Customer Tool - Customer data lookup

Capabilities:
- Search customers by name, email, company
- Get customer history and preferences
- Find related email threads

Usage:
    from openclaw.agents.ira.tools import ira_customer_lookup
    
    result = ira_customer_lookup("Acme Corp")
    print(result.name, result.machines)
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOLS_DIR = Path(__file__).parent
AGENT_DIR = TOOLS_DIR.parent
SRC_DIR = AGENT_DIR / "src"

sys.path.insert(0, str(AGENT_DIR))


@dataclass
class CustomerProfile:
    """A customer profile."""
    name: str
    email: str = ""
    company: str = ""
    country: str = ""
    machines: List[str] = field(default_factory=list)
    industries: List[str] = field(default_factory=list)
    last_contact: Optional[str] = None
    relationship_score: float = 0.0


@dataclass
class CustomerLookupResult:
    """Result from customer lookup."""
    found: bool
    customer: Optional[CustomerProfile] = None
    similar: List[CustomerProfile] = field(default_factory=list)
    source: str = "qdrant"


class IraCustomerTool:
    """
    Tool for customer data lookup.
    """
    
    def __init__(self):
        self._qdrant = None
    
    def _get_qdrant(self):
        if self._qdrant is None:
            try:
                from qdrant_client import QdrantClient
                from config import QDRANT_URL
                self._qdrant = QdrantClient(url=QDRANT_URL)
            except ImportError:
                import os
                from qdrant_client import QdrantClient
                self._qdrant = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))
        return self._qdrant
    
    def lookup(
        self,
        query: str,
        by_email: bool = False,
    ) -> CustomerLookupResult:
        """
        Look up a customer.
        
        Args:
            query: Customer name, email, or company
            by_email: Search by email specifically
            
        Returns:
            CustomerLookupResult
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchText
            from config import COLLECTIONS
            
            qdrant = self._get_qdrant()
            collection = COLLECTIONS.get("customers", "ira_customers")
            
            # Try exact match first
            if by_email or "@" in query:
                filter_cond = Filter(
                    must=[FieldCondition(key="email", match=MatchText(text=query.lower()))]
                )
            else:
                filter_cond = Filter(
                    should=[
                        FieldCondition(key="company", match=MatchText(text=query)),
                        FieldCondition(key="name", match=MatchText(text=query)),
                    ]
                )
            
            results, _ = qdrant.scroll(
                collection_name=collection,
                scroll_filter=filter_cond,
                limit=5,
                with_payload=True,
            )
            
            if results:
                # Found exact match
                payload = results[0].payload or {}
                
                def to_list(val):
                    if isinstance(val, list):
                        return val
                    return []
                
                customer = CustomerProfile(
                    name=payload.get("name", ""),
                    email=payload.get("email", ""),
                    company=payload.get("company", payload.get("name", "")),
                    country=payload.get("country", ""),
                    machines=to_list(payload.get("machines", [])),
                    industries=to_list(payload.get("industries", [])),
                    last_contact=payload.get("last_contact"),
                    relationship_score=payload.get("relationship_score", 0.0),
                )
                
                similar = []
                for r in results[1:]:
                    p = r.payload or {}
                    similar.append(CustomerProfile(
                        name=p.get("name", ""),
                        email=p.get("email", ""),
                        company=p.get("company", ""),
                    ))
                
                return CustomerLookupResult(
                    found=True,
                    customer=customer,
                    similar=similar,
                )
            
            return CustomerLookupResult(found=False)
            
        except Exception as e:
            return CustomerLookupResult(
                found=False,
                source=f"error: {e}",
            )
    
    def get_history(
        self,
        email: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get email history with a customer.
        
        Args:
            email: Customer email
            limit: Max emails to return
            
        Returns:
            List of email summaries
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchText
            from config import COLLECTIONS
            
            qdrant = self._get_qdrant()
            
            # Search email collections
            email_collections = [
                COLLECTIONS.get("emails_voyage", "ira_emails_voyage_v2"),
            ]
            
            emails = []
            domain = email.split("@")[-1] if "@" in email else email
            
            for collection in email_collections:
                try:
                    results, _ = qdrant.scroll(
                        collection_name=collection,
                        scroll_filter=Filter(
                            should=[
                                FieldCondition(key="from_email", match=MatchText(text=domain)),
                                FieldCondition(key="to_email", match=MatchText(text=domain)),
                            ]
                        ),
                        limit=limit,
                        with_payload=True,
                    )
                    
                    for r in results:
                        p = r.payload or {}
                        emails.append({
                            "subject": p.get("subject", ""),
                            "from": p.get("from_email", ""),
                            "date": p.get("date", ""),
                            "snippet": (p.get("text", "") or "")[:200],
                        })
                    
                    if emails:
                        break
                        
                except Exception:
                    continue
            
            return emails
            
        except Exception:
            return []


def ira_customer_lookup(
    query: str,
    by_email: bool = False,
) -> CustomerLookupResult:
    """
    Look up a customer.
    
    Args:
        query: Customer name, email, or company
        by_email: Search by email specifically
        
    Returns:
        CustomerLookupResult
    """
    tool = IraCustomerTool()
    return tool.lookup(query, by_email=by_email)
