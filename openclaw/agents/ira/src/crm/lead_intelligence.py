#!/usr/bin/env python3
"""
LEAD INTELLIGENCE - Real-time context for drip campaign emails
================================================================

Enriches sales outreach with:
1. Recent company news (expansions, acquisitions, leadership changes)
2. Industry trends affecting the lead
3. Geopolitical context (trade, regulations, supply chain)
4. Company-specific hooks from their website

This makes drip emails timely, relevant, and personalized beyond templates.

Usage:
    from lead_intelligence import LeadIntelligence
    
    intel = LeadIntelligence()
    context = intel.get_lead_context("eu-012", "TSN Kunststoffverarbeitung")
    
    # Returns:
    # {
    #     "news_hook": "Congrats on the $25M Mexico plant investment!",
    #     "industry_context": "EV demand is driving automotive thermoforming growth",
    #     "geopolitical_hook": "Many EU firms are nearshoring to Mexico...",
    #     "company_insight": "Your vehicle conversion expertise...",
    # }
"""

import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import requests

# Project paths
SKILL_DIR = Path(__file__).parent
PROJECT_ROOT = SKILL_DIR.parent.parent.parent.parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "cache" / "lead_intelligence"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# OpenAI for analysis
try:
    import openai
    client = openai.OpenAI()
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Jina for web scraping
JINA_API_KEY = os.getenv('JINA_API_KEY', '')


# =============================================================================
# NEWS & INDUSTRY DATA SOURCES
# =============================================================================

INDUSTRY_NEWS_SOURCES = [
    "https://www.plasticsnews.com",
    "https://www.plasticstoday.com", 
    "https://www.ptonline.com",
]

GEOPOLITICAL_CONTEXTS = {
    "germany": {
        "current": "German manufacturing facing energy cost pressures, driving efficiency investments",
        "opportunity": "Cost-competitive equipment from Asia gaining traction",
    },
    "france": {
        "current": "French aerospace sector strong, growing demand for thermoformed interiors",
        "opportunity": "Premium forming capabilities for aerospace applications",
    },
    "uk": {
        "current": "Post-Brexit UK manufacturers seeking diverse supply chains",
        "opportunity": "Direct partnerships outside EU supply chains",
    },
    "sweden": {
        "current": "Nordic focus on sustainability driving material innovation",
        "opportunity": "Machines optimized for recycled/bio-based materials",
    },
    "mexico": {
        "current": "Nearshoring boom - US/EU companies expanding Mexico operations",
        "opportunity": "Equipment for new facilities, North American support",
    },
    "eu_general": {
        "current": "EU plastics regulations tightening, focus on recyclability",
        "opportunity": "Forming equipment for sustainable materials",
    },
}

INDUSTRY_TRENDS_2026 = {
    "automotive": {
        "trend": "EV revolution driving demand for lightweight thermoformed parts",
        "hook": "EV interiors need precise, lightweight forming - exactly what we specialize in",
        "keywords": ["ev", "electric", "battery", "interior", "trim", "panel"],
    },
    "aerospace": {
        "trend": "Aircraft production ramping up post-pandemic, cabin interiors in high demand",
        "hook": "Aerospace-grade forming with the repeatability your quality docs demand",
        "keywords": ["aircraft", "cabin", "interior", "canopy", "aerospace"],
    },
    "packaging": {
        "trend": "Sustainable packaging push - thermoformed trays for food, medical",
        "hook": "High-output forming for recyclable packaging materials",
        "keywords": ["packaging", "tray", "blister", "food", "medical"],
    },
    "sanitary": {
        "trend": "Housing construction uptick driving bathtub/shower pan demand",
        "hook": "Deep-draw forming for sanitary ware - our PF1 series sweet spot",
        "keywords": ["bathtub", "shower", "sanitary", "bath", "acrylic"],
    },
    "refrigeration": {
        "trend": "Cold chain expansion, commercial refrigeration equipment demand up",
        "hook": "Twin-sheet forming for insulated panels and liners",
        "keywords": ["refrigerat", "cooler", "freezer", "insul", "cold"],
    },
}


@dataclass
class LeadContext:
    """Intelligence context for a lead."""
    lead_id: str
    company: str
    
    # News & events
    news_hook: Optional[str] = None
    news_source: Optional[str] = None
    news_date: Optional[str] = None
    
    # Industry context
    industry_trend: Optional[str] = None
    industry_hook: Optional[str] = None
    
    # Geopolitical
    geo_context: Optional[str] = None
    geo_opportunity: Optional[str] = None
    
    # Company-specific
    company_insight: Optional[str] = None
    recent_activity: Optional[str] = None
    
    # Metadata
    refreshed_at: str = ""
    cache_hit: bool = False


class LeadIntelligence:
    """
    Real-time intelligence engine for sales leads.
    
    Fetches and caches:
    - Company news from web search
    - Industry trends relevant to the lead
    - Geopolitical context for their region
    - Company-specific insights from their website
    """
    
    def __init__(self, cache_ttl_hours: int = 24):
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        })
    
    def get_lead_context(
        self,
        lead_id: str,
        company: str,
        country: str = "",
        industries: List[str] = None,
        website: str = "",
        force_refresh: bool = False,
    ) -> LeadContext:
        """
        Get comprehensive intelligence context for a lead.
        
        Args:
            lead_id: Lead identifier
            company: Company name
            country: Country for geopolitical context
            industries: List of industries for trend matching
            website: Company website for scraping
            force_refresh: Bypass cache
        
        Returns:
            LeadContext with all available intelligence
        """
        # Check cache first
        if not force_refresh:
            cached = self._load_cache(lead_id)
            if cached:
                return cached
        
        context = LeadContext(
            lead_id=lead_id,
            company=company,
            refreshed_at=datetime.now().isoformat(),
        )
        
        # 1. Get news hook
        news = self._get_company_news(company, country)
        if news:
            context.news_hook = news.get("hook")
            context.news_source = news.get("source")
            context.news_date = news.get("date")
        
        # 2. Get industry context
        if industries:
            industry_ctx = self._get_industry_context(industries)
            context.industry_trend = industry_ctx.get("trend")
            context.industry_hook = industry_ctx.get("hook")
        
        # 3. Get geopolitical context
        if country:
            geo_ctx = self._get_geo_context(country)
            context.geo_context = geo_ctx.get("current")
            context.geo_opportunity = geo_ctx.get("opportunity")
        
        # 4. Get company insights (if website available)
        if website:
            insight = self._scrape_company_insight(company, website)
            context.company_insight = insight
        
        # Cache the result
        self._save_cache(lead_id, context)
        
        return context
    
    def _get_company_news(self, company: str, country: str = "") -> Optional[Dict]:
        """
        Search for recent news about the company.
        
        Uses DuckDuckGo or Google News via Jina reader.
        """
        try:
            # Search query
            query = f"{company} thermoforming news 2025 2026"
            if country:
                query += f" {country}"
            
            # Use Jina to search
            search_url = f"https://s.jina.ai/{requests.utils.quote(query)}"
            
            headers = {'Accept': 'application/json'}
            if JINA_API_KEY:
                headers['Authorization'] = f'Bearer {JINA_API_KEY}'
            
            response = self.session.get(search_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # Parse results
                results = response.json() if response.headers.get('content-type', '').startswith('application/json') else {"data": []}
                
                # Look for relevant news
                for result in results.get("data", [])[:5]:
                    title = result.get("title", "")
                    snippet = result.get("description", "")
                    url = result.get("url", "")
                    
                    # Check if it's actually about this company
                    company_lower = company.lower()
                    if company_lower in title.lower() or company_lower in snippet.lower():
                        # Extract a hook from the news
                        hook = self._extract_news_hook(title, snippet, company)
                        if hook:
                            return {
                                "hook": hook,
                                "source": url,
                                "date": datetime.now().strftime("%Y-%m"),
                            }
            
        except Exception as e:
            print(f"[lead_intelligence] News search failed: {e}")
        
        return None
    
    def _extract_news_hook(self, title: str, snippet: str, company: str) -> Optional[str]:
        """
        Extract a usable news hook from search results.
        
        Looks for: expansions, investments, acquisitions, new products, leadership
        """
        text = f"{title} {snippet}".lower()
        
        # Expansion/investment news
        if any(word in text for word in ["expand", "invest", "new plant", "new facility", "million", "growth"]):
            if OPENAI_AVAILABLE:
                return self._llm_extract_hook(title, snippet, company, "expansion")
            return f"I saw news about {company}'s expansion plans"
        
        # Acquisition news
        if any(word in text for word in ["acqui", "merge", "bought", "purchase"]):
            if OPENAI_AVAILABLE:
                return self._llm_extract_hook(title, snippet, company, "acquisition")
            return f"Congratulations on the recent acquisition news"
        
        # New product/capability
        if any(word in text for word in ["launch", "new product", "introduce", "capability"]):
            if OPENAI_AVAILABLE:
                return self._llm_extract_hook(title, snippet, company, "product")
            return f"Saw the news about {company}'s new capabilities"
        
        # Leadership change
        if any(word in text for word in ["ceo", "appoint", "hire", "leadership"]):
            if OPENAI_AVAILABLE:
                return self._llm_extract_hook(title, snippet, company, "leadership")
            return f"Congratulations on the leadership news"
        
        return None
    
    def _llm_extract_hook(self, title: str, snippet: str, company: str, news_type: str) -> str:
        """Use LLM to create a natural news hook."""
        if not OPENAI_AVAILABLE:
            return None
        
        prompt = f"""Extract a brief, natural news hook from this headline/snippet for use in a sales email.
        
Company: {company}
News type: {news_type}
Title: {title}
Snippet: {snippet}

Write ONE sentence that naturally acknowledges this news. Be specific but concise.
Examples:
- "Congrats on the $25M investment in your new Mexico facility!"
- "I saw the news about your expansion into aerospace thermoforming."
- "Your recent partnership with [X] caught my attention."

Just the sentence, no quotes or explanation."""

        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except:
            return None
    
    def _get_industry_context(self, industries: List[str]) -> Dict[str, str]:
        """Get relevant industry trend context."""
        for industry in industries:
            industry_lower = industry.lower()
            
            # Check each trend category
            for category, data in INDUSTRY_TRENDS_2026.items():
                # Check if industry matches category or keywords
                if category in industry_lower or any(kw in industry_lower for kw in data["keywords"]):
                    return {
                        "trend": data["trend"],
                        "hook": data["hook"],
                        "category": category,
                    }
        
        # Default to general manufacturing
        return {
            "trend": "Manufacturing efficiency investments driving equipment upgrades",
            "hook": "Competitive thermoforming equipment for your production needs",
            "category": "general",
        }
    
    def _get_geo_context(self, country: str) -> Dict[str, str]:
        """Get geopolitical context for a country."""
        country_lower = country.lower()
        
        # Direct match
        if country_lower in GEOPOLITICAL_CONTEXTS:
            return GEOPOLITICAL_CONTEXTS[country_lower]
        
        # EU countries
        eu_countries = ["germany", "france", "italy", "spain", "netherlands", "belgium", 
                       "austria", "czech", "poland", "romania", "hungary"]
        if any(c in country_lower for c in eu_countries):
            return GEOPOLITICAL_CONTEXTS["eu_general"]
        
        # Nordic
        nordic = ["sweden", "norway", "denmark", "finland"]
        if any(c in country_lower for c in nordic):
            return GEOPOLITICAL_CONTEXTS.get("sweden", GEOPOLITICAL_CONTEXTS["eu_general"])
        
        return {
            "current": "Global supply chain diversification ongoing",
            "opportunity": "Direct partnerships with established manufacturers",
        }
    
    def _scrape_company_insight(self, company: str, website: str) -> Optional[str]:
        """
        Scrape company website for recent news/insights.
        
        Looks for: news page, press releases, recent updates.
        """
        try:
            # Try news/press page
            for path in ["/news", "/press", "/about-us", "/company"]:
                url = website.rstrip("/") + path
                
                # Use Jina reader
                jina_url = f"https://r.jina.ai/{url}"
                headers = {'Accept': 'text/plain'}
                if JINA_API_KEY:
                    headers['Authorization'] = f'Bearer {JINA_API_KEY}'
                
                response = self.session.get(jina_url, headers=headers, timeout=15)
                
                if response.status_code == 200 and len(response.text) > 500:
                    # Look for recent dates in content
                    text = response.text[:5000]
                    
                    # Check for 2025/2026 dates
                    if "2026" in text or "2025" in text:
                        # Extract insight with LLM
                        if OPENAI_AVAILABLE:
                            return self._llm_extract_insight(text, company)
                    break
                    
        except Exception as e:
            print(f"[lead_intelligence] Company scrape failed: {e}")
        
        return None
    
    def _llm_extract_insight(self, website_content: str, company: str) -> Optional[str]:
        """Use LLM to extract a useful insight from website content."""
        if not OPENAI_AVAILABLE:
            return None
        
        prompt = f"""From this website content, extract ONE recent noteworthy thing about {company}.

Content (truncated):
{website_content[:3000]}

Focus on: recent news, new capabilities, expansion, partnerships, certifications, or investments.
If nothing recent/noteworthy, say "None".

Write one brief, specific sentence or "None"."""

        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.5,
            )
            result = response.choices[0].message.content.strip()
            if result.lower() != "none" and len(result) > 10:
                return result
        except:
            pass
        
        return None
    
    def _cache_key(self, lead_id: str) -> str:
        """Generate cache filename."""
        return f"{lead_id}_{hashlib.md5(lead_id.encode()).hexdigest()[:8]}.json"
    
    def _load_cache(self, lead_id: str) -> Optional[LeadContext]:
        """Load cached context if fresh."""
        cache_file = CACHE_DIR / self._cache_key(lead_id)
        
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                refreshed = datetime.fromisoformat(data.get("refreshed_at", "2000-01-01"))
                
                if datetime.now() - refreshed < self.cache_ttl:
                    context = LeadContext(**data)
                    context.cache_hit = True
                    return context
            except:
                pass
        
        return None
    
    def _save_cache(self, lead_id: str, context: LeadContext):
        """Save context to cache."""
        cache_file = CACHE_DIR / self._cache_key(lead_id)
        
        try:
            cache_file.write_text(json.dumps(asdict(context), indent=2))
        except Exception as e:
            print(f"[lead_intelligence] Cache save failed: {e}")


# =============================================================================
# INTEGRATION WITH DRIP CAMPAIGN
# =============================================================================

def enrich_lead_for_email(
    lead_id: str,
    company: str,
    country: str = "",
    industries: List[str] = None,
    website: str = "",
) -> Dict[str, str]:
    """
    Get email-ready intelligence for a lead.
    
    Returns a dict with pre-formatted hooks ready to insert into emails.
    """
    intel = LeadIntelligence()
    context = intel.get_lead_context(
        lead_id=lead_id,
        company=company,
        country=country,
        industries=industries or [],
        website=website,
    )
    
    result = {}
    
    # News hook (most valuable)
    if context.news_hook:
        result["news_hook"] = context.news_hook
    
    # Industry hook
    if context.industry_hook:
        result["industry_hook"] = context.industry_hook
    
    # Geo context (for value prop)
    if context.geo_opportunity:
        result["geo_hook"] = context.geo_opportunity
    
    # Company insight
    if context.company_insight:
        result["company_insight"] = context.company_insight
    
    # Combined "timely_opener" for Stage 1
    if context.news_hook:
        result["timely_opener"] = context.news_hook
    elif context.company_insight:
        result["timely_opener"] = context.company_insight
    elif context.industry_trend:
        result["timely_opener"] = f"With {context.industry_trend.lower()}, I thought of {company}."
    
    return result


# =============================================================================
# CLI FOR TESTING
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        company = sys.argv[1]
        country = sys.argv[2] if len(sys.argv) > 2 else ""
        industries = sys.argv[3].split(",") if len(sys.argv) > 3 else []
        website = sys.argv[4] if len(sys.argv) > 4 else ""
        
        print(f"\n{'─'*60}")
        print(f"LEAD INTELLIGENCE: {company}")
        print(f"{'─'*60}\n")
        
        intel = LeadIntelligence()
        context = intel.get_lead_context(
            lead_id="test",
            company=company,
            country=country,
            industries=industries,
            website=website,
            force_refresh=True,
        )
        
        print(f"News Hook: {context.news_hook or 'None found'}")
        print(f"News Source: {context.news_source or 'N/A'}")
        print(f"Industry Trend: {context.industry_trend or 'N/A'}")
        print(f"Industry Hook: {context.industry_hook or 'N/A'}")
        print(f"Geo Context: {context.geo_context or 'N/A'}")
        print(f"Geo Opportunity: {context.geo_opportunity or 'N/A'}")
        print(f"Company Insight: {context.company_insight or 'N/A'}")
        print(f"\nCache hit: {context.cache_hit}")
        print(f"Refreshed: {context.refreshed_at}")
        
        print(f"\n{'─'*60}")
        print("EMAIL-READY HOOKS:")
        print(f"{'─'*60}")
        
        hooks = enrich_lead_for_email(
            "test", company, country, industries, website
        )
        for key, value in hooks.items():
            print(f"  {key}: {value}")
    else:
        print("Usage: python lead_intelligence.py <company> [country] [industries] [website]")
        print("Example: python lead_intelligence.py 'TSN Kunststoffverarbeitung' 'Germany' 'automotive,vehicle' 'https://tsn-group.de'")
