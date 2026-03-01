#!/usr/bin/env python3
"""
Customer Data Enricher
======================

Enriches ira_customers collection with data extracted from emails:
- Country detection from email domains, signatures
- Machine models from email content
- Company website detection
- Industry/application detection

Usage:
    python customer_enricher.py              # Run enrichment
    python customer_enricher.py --dry-run    # Preview changes
"""

import argparse
import logging
import os
import re
import sys

logger = logging.getLogger(__name__)
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import from centralized config
BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

try:
    from config import (
        DATABASE_URL, QDRANT_URL, OPENAI_API_KEY,
        COLLECTIONS,
    )
    CONFIG_LOADED = True
except ImportError:
    CONFIG_LOADED = False
    # Fallback to direct env loading
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))
    
    DATABASE_URL = os.environ.get("DATABASE_URL") or "postgresql://ira:ira_password@localhost:5432/ira_db"
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    COLLECTIONS = {"customers": "ira_customers"}

# Country domain mappings
DOMAIN_COUNTRY = {
    '.de': 'Germany', '.fr': 'France', '.uk': 'UK', '.co.uk': 'UK',
    '.it': 'Italy', '.es': 'Spain', '.nl': 'Netherlands', '.be': 'Belgium',
    '.ch': 'Switzerland', '.at': 'Austria', '.se': 'Sweden', '.no': 'Norway',
    '.dk': 'Denmark', '.fi': 'Finland', '.pl': 'Poland', '.cz': 'Czech Republic',
    '.in': 'India', '.cn': 'China', '.jp': 'Japan', '.kr': 'South Korea',
    '.au': 'Australia', '.nz': 'New Zealand', '.ca': 'Canada', '.mx': 'Mexico',
    '.br': 'Brazil', '.ar': 'Argentina', '.za': 'South Africa', '.ae': 'UAE',
    '.sa': 'Saudi Arabia', '.tr': 'Turkey', '.ru': 'Russia', '.us': 'USA',
    '.ee': 'Estonia', '.lv': 'Latvia', '.lt': 'Lithuania', '.dz': 'Algeria',
    '.eg': 'Egypt', '.ma': 'Morocco', '.ng': 'Nigeria', '.ke': 'Kenya',
    '.th': 'Thailand', '.vn': 'Vietnam', '.id': 'Indonesia', '.my': 'Malaysia',
    '.sg': 'Singapore', '.ph': 'Philippines', '.tw': 'Taiwan', '.hk': 'Hong Kong',
}

# Machine patterns
MACHINE_PATTERNS = {
    'PF1': r'\bPF[-\s]?1[-\s]?[XCSPRA]?[-\s]?\d*',
    'PF2': r'\bPF[-\s]?2[-\s]?[XCSPRA]?[-\s]?\d*',
    'AM-M': r'\bAM[-\s]?M[-\s]?\d*',
    'AM-V': r'\bAM[-\s]?V[-\s]?\d*',
    'AM-P': r'\bAM[-\s]?P[-\s]?\d*',
    'FCS': r'\bFCS[-\s]?\d+',
    'ATF': r'\bATF[-\s]?\d+',
    'IMG': r'\bIMG[-\s]?\d+',
}

# Application keywords
APPLICATION_KEYWORDS = {
    'automotive': ['automotive', 'car', 'vehicle', 'dashboard', 'door panel', 'bumper'],
    'packaging': ['packaging', 'tray', 'blister', 'clamshell', 'container', 'food packaging'],
    'medical': ['medical', 'pharma', 'hospital', 'healthcare', 'sterile'],
    'aerospace': ['aerospace', 'aircraft', 'aviation'],
    'electronics': ['electronics', 'electronic', 'pcb', 'circuit'],
    'consumer': ['consumer goods', 'household', 'appliance'],
    'industrial': ['industrial', 'machinery', 'equipment'],
}


def get_qdrant_client():
    """Get Qdrant client using centralized config."""
    try:
        from config import get_qdrant_client as _get_qdrant_client
        return _get_qdrant_client()
    except ImportError:
        from qdrant_client import QdrantClient
        return QdrantClient(url=QDRANT_URL)


def detect_country_from_email(email: str) -> Optional[str]:
    """Detect country from email domain."""
    if not email or '@' not in email:
        return None
    
    domain = email.lower().split('@')[-1]
    
    # Check country TLDs
    for tld, country in sorted(DOMAIN_COUNTRY.items(), key=lambda x: -len(x[0])):
        if domain.endswith(tld):
            return country
    
    return None


def detect_machines_from_text(text: str) -> List[str]:
    """Extract machine models from text."""
    machines = []
    for machine_type, pattern in MACHINE_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            if machine_type not in machines:
                machines.append(machine_type)
    return machines


def detect_applications_from_text(text: str) -> List[str]:
    """Detect industry/application from text."""
    text_lower = text.lower()
    applications = []
    
    for app, keywords in APPLICATION_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            applications.append(app)
    
    return applications


def get_customer_email_data(email: str) -> Dict:
    """Get aggregated data from emails for a customer using Qdrant."""
    from qdrant_client.models import Filter, FieldCondition, MatchText
    
    qdrant = get_qdrant_client()
    domain = email.split('@')[-1] if '@' in email else email
    
    all_text = ""
    all_machines = []
    email_count = 0
    
    # Try multiple email collections (from config or defaults)
    email_collections = [
        COLLECTIONS.get("emails_voyage", "ira_emails_voyage_v2"),
        COLLECTIONS.get("emails_openai_large", "ira_emails_openai_large_v3"),
        "ira_emails_voyage_v2",  # Legacy fallback
    ]
    for collection in email_collections:
        try:
            # Search by company_domain in payload
            results, _ = qdrant.scroll(
                collection_name=collection,
                scroll_filter=Filter(
                    should=[
                        FieldCondition(key="company_domain", match=MatchText(text=domain)),
                        FieldCondition(key="from_email", match=MatchText(text=domain)),
                    ]
                ),
                limit=50,
                with_payload=True,
            )
            
            for point in results:
                payload = point.payload or {}
                email_count += 1
                
                if payload.get("subject"):
                    all_text += " " + payload["subject"]
                if payload.get("text"):
                    all_text += " " + payload["text"][:500]
                if payload.get("machines"):
                    all_machines.extend(payload["machines"])
            
            if email_count > 0:
                break  # Found data, no need to check other collections
                
        except Exception as e:
            continue  # Try next collection
    
    return {
        "email_count": email_count,
        "combined_text": all_text,
        "machines_from_db": list(set(all_machines)),
    }


def enrich_customers(dry_run: bool = False):
    """Enrich customer records with data from emails."""
    logger.info("=" * 60)
    logger.info("  CUSTOMER ENRICHMENT")
    logger.info("=" * 60)
    
    from qdrant_client import QdrantClient
    
    qdrant = get_qdrant_client()
    
    # Get all customers
    all_customers = []
    offset = None
    
    customer_collection = COLLECTIONS.get("customers", "ira_customers")
    while True:
        points, offset = qdrant.scroll(
            collection_name=customer_collection,
            limit=100,
            offset=offset,
            with_payload=True,
        )
        all_customers.extend(points)
        if offset is None:
            break
    
    logger.info("Loaded %d customers", len(all_customers))
    
    enriched = 0
    updates = []
    
    for customer in all_customers:
        payload = customer.payload
        email = payload.get("email", "")
        company = payload.get("company_name", "")
        
        if not email:
            continue
        
        changes = {}
        
        # 1. Detect country if missing
        if not payload.get("country"):
            country = detect_country_from_email(email)
            if country:
                changes["country"] = country
        
        # 2. Get data from emails
        email_data = get_customer_email_data(email)
        
        if email_data["email_count"] > 0:
            # Extract machines
            if not payload.get("machine_model"):
                machines = email_data["machines_from_db"]
                if not machines:
                    machines = detect_machines_from_text(email_data["combined_text"])
                if machines:
                    changes["machine_model"] = ", ".join(machines[:3])
                    changes["machine_type"] = machines[0] if machines else ""
            
            # Extract applications
            if not payload.get("application"):
                apps = detect_applications_from_text(email_data["combined_text"])
                if apps:
                    changes["application"] = ", ".join(apps[:2])
            
            # Add email count
            changes["email_count"] = email_data["email_count"]
        
        if changes:
            updates.append({
                "id": customer.id,
                "company": company,
                "email": email,
                "changes": changes,
            })
            enriched += 1
    
    logger.info("Customers to enrich: %d/%d", enriched, len(all_customers))
    
    # Show sample updates
    logger.info("Sample enrichments:")
    for u in updates[:5]:
        logger.info("  %s (%s)", u['company'], u['email'])
        for k, v in u['changes'].items():
            logger.info("    + %s: %s", k, v)
    
    if dry_run:
        logger.info("[DRY RUN] No changes applied")
        return
    
    # Apply updates
    logger.info("Applying updates...")
    
    for u in updates:
        try:
            qdrant.set_payload(
                collection_name=customer_collection,
                payload=u["changes"],
                points=[u["id"]],
            )
        except Exception as e:
            logger.warning("Error updating %s: %s", u['company'], e)
    
    logger.info("Enriched %d customers", enriched)


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Customer Data Enricher")
    parser.add_argument('--dry-run', action='store_true', help='Preview changes')
    args = parser.parse_args()
    
    enrich_customers(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
