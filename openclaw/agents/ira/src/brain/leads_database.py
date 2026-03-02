#!/usr/bin/env python3
"""
LEADS DATABASE - Query CRM/Leads data for Ira

Provides access to European & US contacts spreadsheet data.
Ira can query leads by region, industry, status, etc.

Usage:
    from leads_database import LeadsDatabase, query_leads
    
    # Get hot leads in Europe
    leads = query_leads(region="Europe", hot_only=True)
    
    # Get leads by country
    leads = query_leads(country="Germany")
"""

import csv
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
LEADS_CSV = PROJECT_ROOT / "data" / "imports" / "European & US Contacts for Single Station Nov 203.csv"


@dataclass
class Lead:
    """A sales lead/contact."""
    email: str
    first_name: str
    last_name: str
    country: str
    company: str
    meeting_info: str = ""
    quotes: str = ""
    date: str = ""
    comments: str = ""
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_hot(self) -> bool:
        """Determine if this is a 'hot' lead based on activity."""
        # Has recent meeting or quote activity
        if self.meeting_info or self.quotes:
            return True
        # Has meaningful comments indicating engagement
        if self.comments and len(self.comments) > 20:
            return True
        return False
    
    @property
    def has_quote(self) -> bool:
        return bool(self.quotes)
    
    @property
    def had_meeting(self) -> bool:
        return bool(self.meeting_info)
    
    def to_summary(self) -> str:
        """Generate a brief summary of this lead."""
        parts = [f"**{self.full_name}** at {self.company} ({self.country})"]
        if self.meeting_info:
            parts.append(f"  - Meeting: {self.meeting_info}")
        if self.quotes:
            parts.append(f"  - Quote: {self.quotes}")
        if self.comments:
            parts.append(f"  - Notes: {self.comments[:100]}...")
        return "\n".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "email": self.email,
            "name": self.full_name,
            "company": self.company,
            "country": self.country,
            "meeting": self.meeting_info,
            "quote": self.quotes,
            "date": self.date,
            "comments": self.comments,
            "is_hot": self.is_hot,
        }


class LeadsDatabase:
    """
    Query interface for leads/contacts data.
    """
    
    def __init__(self, csv_path: Path = None):
        self.csv_path = csv_path or LEADS_CSV
        self._leads: List[Lead] = []
        self._loaded = False
    
    def _load(self):
        """Load leads from CSV."""
        if self._loaded:
            return
        
        if not self.csv_path.exists():
            logger.error("Leads CSV not found: %s", self.csv_path)
            return
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    lead = Lead(
                        email=row.get('Email Address', '').strip(),
                        first_name=row.get('First Name', '').strip(),
                        last_name=row.get('Last Name', '').strip(),
                        country=row.get('Address', '').strip(),
                        company=row.get('Company Name', '').strip(),
                        meeting_info=row.get('Physical / Web Meeting', '').strip(),
                        quotes=row.get('Quotes', '').strip(),
                        date=row.get('Date', '').strip(),
                        comments=row.get('Comments', '').strip(),
                    )
                    if lead.email:  # Only add if has email
                        self._leads.append(lead)
            
            self._loaded = True
            logger.info("Loaded %d leads from CSV", len(self._leads))
            
        except Exception as e:
            logger.error("Error loading leads: %s", e)
    
    def query(
        self,
        region: str = None,
        country: str = None,
        hot_only: bool = False,
        has_quote: bool = None,
        had_meeting: bool = None,
        company_contains: str = None,
        limit: int = 20,
    ) -> List[Lead]:
        """
        Query leads with filters.
        
        Args:
            region: "Europe", "US", or None for all
            country: Specific country name
            hot_only: Only return leads with activity
            has_quote: Filter by quote status
            had_meeting: Filter by meeting status
            company_contains: Search company names
            limit: Max results to return
        
        Returns:
            List of matching Lead objects
        """
        self._load()
        
        results = self._leads.copy()
        
        # Region filter
        if region:
            region_lower = region.lower()
            if "europe" in region_lower:
                european_countries = {
                    'austria', 'belgium', 'czech republic', 'denmark', 'finland',
                    'france', 'germany', 'greece', 'hungary', 'ireland', 'italy',
                    'netherlands', 'norway', 'poland', 'portugal', 'spain', 'sweden',
                    'switzerland', 'uk', 'united kingdom', 'faroe islands'
                }
                results = [l for l in results if l.country.lower() in european_countries]
            elif "us" in region_lower or "america" in region_lower:
                results = [l for l in results if l.country.lower() in {'usa', 'us', 'united states'}]
        
        # Country filter
        if country:
            country_lower = country.lower()
            results = [l for l in results if country_lower in l.country.lower()]
        
        # Hot leads only
        if hot_only:
            results = [l for l in results if l.is_hot]
        
        # Quote filter
        if has_quote is not None:
            results = [l for l in results if l.has_quote == has_quote]
        
        # Meeting filter
        if had_meeting is not None:
            results = [l for l in results if l.had_meeting == had_meeting]
        
        # Company search
        if company_contains:
            search = company_contains.lower()
            results = [l for l in results if search in l.company.lower()]
        
        # Sort by "hotness" - leads with more activity first
        results.sort(key=lambda l: (l.is_hot, bool(l.meeting_info), bool(l.quotes)), reverse=True)
        
        return results[:limit]
    
    def get_european_hot_leads(self, limit: int = 10) -> List[Lead]:
        """Get hot leads in Europe - convenience method."""
        return self.query(region="Europe", hot_only=True, limit=limit)
    
    def get_leads_by_country(self, country: str, limit: int = 20) -> List[Lead]:
        """Get leads from a specific country."""
        return self.query(country=country, limit=limit)
    
    def get_all_countries(self) -> List[str]:
        """Get list of all countries in the database."""
        self._load()
        countries = set(l.country for l in self._leads if l.country)
        return sorted(countries)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        self._load()
        
        hot_count = sum(1 for l in self._leads if l.is_hot)
        quoted_count = sum(1 for l in self._leads if l.has_quote)
        met_count = sum(1 for l in self._leads if l.had_meeting)
        
        countries = {}
        for l in self._leads:
            countries[l.country] = countries.get(l.country, 0) + 1
        
        return {
            "total_leads": len(self._leads),
            "hot_leads": hot_count,
            "with_quotes": quoted_count,
            "had_meetings": met_count,
            "countries": countries,
        }
    
    def format_leads_report(self, leads: List[Lead], title: str = "Leads Report") -> str:
        """Format leads into a readable report."""
        if not leads:
            return "No leads found matching the criteria."
        
        lines = [f"## {title}", f"Found {len(leads)} leads:\n"]
        
        for i, lead in enumerate(leads, 1):
            lines.append(f"### {i}. {lead.full_name} - {lead.company}")
            lines.append(f"- **Country:** {lead.country}")
            lines.append(f"- **Email:** {lead.email}")
            if lead.meeting_info:
                lines.append(f"- **Meeting:** {lead.meeting_info}")
            if lead.quotes:
                lines.append(f"- **Quote:** {lead.quotes}")
            if lead.comments:
                lines.append(f"- **Notes:** {lead.comments}")
            lines.append("")
        
        return "\n".join(lines)


# Singleton instance
_db: Optional[LeadsDatabase] = None


def get_leads_db() -> LeadsDatabase:
    """Get singleton LeadsDatabase instance."""
    global _db
    if _db is None:
        _db = LeadsDatabase()
    return _db


def query_leads(
    region: str = None,
    country: str = None,
    hot_only: bool = False,
    limit: int = 20,
) -> List[Lead]:
    """Convenience function to query leads."""
    return get_leads_db().query(
        region=region,
        country=country,
        hot_only=hot_only,
        limit=limit,
    )


def get_european_hot_leads(limit: int = 10) -> str:
    """Get formatted report of hot European leads."""
    db = get_leads_db()
    leads = db.get_european_hot_leads(limit=limit)
    return db.format_leads_report(leads, title="Hot European Leads")


# CLI for testing
if __name__ == "__main__":
    import sys
    
    db = LeadsDatabase()
    
    print("=" * 60)
    print("LEADS DATABASE")
    print("=" * 60)
    
    stats = db.get_stats()
    print(f"\nTotal leads: {stats['total_leads']}")
    print(f"Hot leads: {stats['hot_leads']}")
    print(f"With quotes: {stats['with_quotes']}")
    print(f"Had meetings: {stats['had_meetings']}")
    
    print("\n--- European Hot Leads ---")
    report = get_european_hot_leads(limit=5)
    print(report)
    
    print("\n--- Countries ---")
    print(", ".join(db.get_all_countries()))
