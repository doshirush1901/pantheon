#!/usr/bin/env python3
"""
IRIS - Lead Intelligence Agent
==============================

The swift messenger goddess who gathers real-time intelligence from across the web.

Iris is a sub-agent in Ira's pantheon, specializing in:
- Company news and announcements
- Industry trends and market shifts  
- Geopolitical context affecting purchasing
- Website scraping for fresh insights

Architecture:
    Athena (Ira) → delegates to → Iris → returns intelligence → used by Calliope for emails

Example:
    iris = Iris()
    context = iris.enrich_lead("eu-012", "TSN", country="Germany", industries=["automotive"])
    print(context.news_hook)  # "Congrats on the $25M Mexico expansion!"
"""

import os
import re
import json
import hashlib
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from urllib.parse import quote

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Project paths
AGENT_DIR = Path(__file__).parent
AGENTS_DIR = AGENT_DIR.parent
PROJECT_ROOT = AGENTS_DIR.parent
CACHE_DIR = PROJECT_ROOT / "data" / "cache" / "iris"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# OpenAI for intelligent extraction
try:
    import openai
    _openai_client = openai.OpenAI()
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Jina for web operations
JINA_API_KEY = os.getenv('JINA_API_KEY', '')


# =============================================================================
# IRIS'S KNOWLEDGE BASE
# =============================================================================

GEOPOLITICAL_CONTEXTS = {
    "germany": {
        "current": "German manufacturing facing energy cost pressures, driving efficiency investments",
        "opportunity": "Cost-competitive equipment from Asia gaining traction",
        "keywords": ["energy", "efficiency", "automation"],
    },
    "france": {
        "current": "French aerospace sector strong, growing demand for thermoformed interiors",
        "opportunity": "Premium forming capabilities for aerospace applications",
        "keywords": ["aerospace", "airbus", "interiors"],
    },
    "uk": {
        "current": "Post-Brexit UK manufacturers seeking diverse supply chains",
        "opportunity": "Direct partnerships outside EU supply chains",
        "keywords": ["brexit", "supply chain", "diversification"],
    },
    "sweden": {
        "current": "Nordic focus on sustainability driving material innovation",
        "opportunity": "Machines optimized for recycled/bio-based materials",
        "keywords": ["sustainability", "recycled", "green"],
    },
    "mexico": {
        "current": "Nearshoring boom - US/EU companies expanding Mexico operations",
        "opportunity": "Equipment for new facilities, North American support",
        "keywords": ["nearshoring", "expansion", "facility"],
    },
    "czech": {
        "current": "Central European manufacturing hub with growing automotive presence",
        "opportunity": "Capacity expansion for automotive tier suppliers",
        "keywords": ["automotive", "supplier", "expansion"],
    },
    "austria": {
        "current": "High-quality manufacturing focus with strong machine tool tradition",
        "opportunity": "Premium positioning aligns with quality expectations",
        "keywords": ["quality", "precision", "engineering"],
    },
    "eu_general": {
        "current": "EU plastics regulations tightening, focus on recyclability",
        "opportunity": "Forming equipment optimized for sustainable materials",
        "keywords": ["regulation", "recyclability", "sustainable"],
    },
}

INDUSTRY_TRENDS_2026 = {
    "automotive": {
        "trend": "EV revolution driving demand for lightweight thermoformed parts",
        "hook": "EV interiors need precise, lightweight forming - exactly what we specialize in",
        "talking_points": [
            "Battery enclosure covers",
            "Lightweight interior panels",
            "Noise/vibration dampening parts",
        ],
        "keywords": ["ev", "electric", "battery", "interior", "trim", "panel", "vehicle"],
    },
    "aerospace": {
        "trend": "Aircraft production ramping up post-pandemic, cabin interiors in high demand",
        "hook": "Aerospace-grade forming with the repeatability your quality docs demand",
        "talking_points": [
            "Cabin interior panels",
            "Canopy/window forming",
            "Overhead bin components",
        ],
        "keywords": ["aircraft", "cabin", "interior", "canopy", "aerospace", "aviation"],
    },
    "packaging": {
        "trend": "Sustainable packaging push - thermoformed trays for food, medical",
        "hook": "High-output forming for recyclable packaging materials",
        "talking_points": [
            "rPET and recycled material forming",
            "Food-grade tray production",
            "Medical blister packaging",
        ],
        "keywords": ["packaging", "tray", "blister", "food", "medical", "sustainable"],
    },
    "sanitary": {
        "trend": "Housing construction uptick driving bathtub/shower pan demand",
        "hook": "Deep-draw forming for sanitary ware - our PF1 series sweet spot",
        "talking_points": [
            "Acrylic bathtub forming",
            "Shower tray production",
            "Spa/jacuzzi components",
        ],
        "keywords": ["bathtub", "shower", "sanitary", "bath", "acrylic", "spa"],
    },
    "refrigeration": {
        "trend": "Cold chain expansion, commercial refrigeration equipment demand up",
        "hook": "Twin-sheet forming for insulated panels and liners",
        "talking_points": [
            "Refrigerator door liners",
            "Commercial cooler panels",
            "Insulated transport containers",
        ],
        "keywords": ["refrigerat", "cooler", "freezer", "insul", "cold", "liner"],
    },
    "signage": {
        "trend": "Retail and outdoor advertising recovering, signage demand steady",
        "hook": "Large-format forming for eye-catching dimensional signage",
        "talking_points": [
            "3D retail signage",
            "Illuminated displays",
            "Point-of-purchase displays",
        ],
        "keywords": ["sign", "display", "retail", "advertis", "illuminat"],
    },
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class IrisContext:
    """Intelligence context gathered by Iris for a lead."""
    lead_id: str
    company: str
    
    # News intelligence
    news_hook: Optional[str] = None
    news_headline: Optional[str] = None
    news_source: Optional[str] = None
    news_date: Optional[str] = None
    
    # Industry intelligence
    industry_trend: Optional[str] = None
    industry_hook: Optional[str] = None
    industry_talking_points: List[str] = field(default_factory=list)
    
    # Geopolitical intelligence
    geo_context: Optional[str] = None
    geo_opportunity: Optional[str] = None
    
    # Company-specific intelligence
    company_insight: Optional[str] = None
    company_focus_areas: List[str] = field(default_factory=list)
    recent_activity: Optional[str] = None
    
    # Ready-to-use hooks for emails
    timely_opener: Optional[str] = None
    value_prop_angle: Optional[str] = None
    
    # Metadata
    confidence: float = 0.0
    sources_checked: List[str] = field(default_factory=list)
    refreshed_at: str = ""
    cache_hit: bool = False
    
    def to_email_vars(self) -> Dict[str, str]:
        """Convert to variables ready for email templates."""
        return {
            "news_hook": self.news_hook or "",
            "industry_hook": self.industry_hook or "",
            "geo_hook": self.geo_opportunity or "",
            "company_insight": self.company_insight or "",
            "timely_opener": self.timely_opener or "",
            "value_prop_angle": self.value_prop_angle or "",
        }


@dataclass  
class NewsResult:
    """A news search result."""
    headline: str
    snippet: str
    url: str
    date: Optional[str] = None
    relevance: float = 0.0


# =============================================================================
# IRIS AGENT
# =============================================================================

class Iris:
    """
    Lead Intelligence Agent - gathers real-time context for sales outreach.
    
    Named after the Greek goddess Iris, the swift messenger who travels
    between worlds gathering information.
    
    Capabilities:
    - Company news search
    - Industry trend analysis
    - Geopolitical context
    - Website scraping
    - Lead enrichment (combines all above)
    """
    
    def __init__(self, cache_ttl_hours: int = 24):
        """
        Initialize Iris.

        Args:
            cache_ttl_hours: How long to cache intelligence (default 24h)
        """
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        # Iris's voice for logging
        self.name = "Iris"
        self._log(f"initialized, ready to gather intelligence")
    
    def _log(self, message: str):
        """Log with Iris's voice."""
        print(f"[{self.name}] {message}")
    
    # =========================================================================
    # CORE INTELLIGENCE METHODS
    # =========================================================================
    
    async def enrich_lead_async(
        self,
        lead_id: str,
        company: str,
        country: str = "",
        industries: List[str] = None,
        website: str = "",
        force_refresh: bool = False,
    ) -> IrisContext:
        """
        Gather comprehensive intelligence for a lead (async).

        This is the main entry point - combines all intelligence sources
        into a ready-to-use context for email personalization.

        Args:
            lead_id: Lead identifier
            company: Company name
            country: Country for geo context
            industries: Industries for trend matching
            website: Company website for scraping
            force_refresh: Bypass cache

        Returns:
            IrisContext with all gathered intelligence
        """
        industries = industries or []

        # Check cache
        if not force_refresh:
            cached = self._load_cache(lead_id)
            if cached:
                self._log(f"cache hit for {company}")
                return cached

        self._log(f"researching {company}...")

        context = IrisContext(
            lead_id=lead_id,
            company=company,
            refreshed_at=datetime.now().isoformat(),
        )

        # Gather intelligence in parallel using native async
        tasks: List[Any] = []
        keys: List[str] = []

        tasks.append(self._search_company_news_async(company, country))
        keys.append("news")

        if industries:
            loop = asyncio.get_event_loop()
            tasks.append(loop.run_in_executor(None, lambda i=industries: self.get_industry_context(i)))
            keys.append("industry")
        else:
            tasks.append(asyncio.sleep(0))
            keys.append("industry")

        if country:
            loop = asyncio.get_event_loop()
            tasks.append(loop.run_in_executor(None, lambda c=country: self.get_geo_context(c)))
            keys.append("geo")
        else:
            tasks.append(asyncio.sleep(0))
            keys.append("geo")

        if website:
            tasks.append(self._scrape_company_website_async(company, website))
            keys.append("website")
        else:
            tasks.append(asyncio.sleep(0))
            keys.append("website")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for key, result in zip(keys, results):
            if isinstance(result, Exception):
                self._log(f"  {key} lookup failed: {result}")
                continue
            if result is None:
                continue
            try:
                if key == "news" and result:
                    context.news_hook = result.get("hook")
                    context.news_headline = result.get("headline")
                    context.news_source = result.get("source")
                    context.news_date = result.get("date")
                    context.sources_checked.append("news_search")
                elif key == "industry" and result:
                    context.industry_trend = result.get("trend")
                    context.industry_hook = result.get("hook")
                    context.industry_talking_points = result.get("talking_points", [])
                    context.sources_checked.append("industry_trends")
                elif key == "geo" and result:
                    context.geo_context = result.get("current")
                    context.geo_opportunity = result.get("opportunity")
                    context.sources_checked.append("geo_context")
                elif key == "website" and result:
                    context.company_insight = result.get("insight")
                    context.company_focus_areas = result.get("focus_areas", [])
                    context.sources_checked.append("website_scrape")
            except Exception as e:
                self._log(f"  {key} parse failed: {e}")

        # Build ready-to-use hooks
        context = self._build_email_hooks(context, company)

        # Calculate confidence
        context.confidence = self._calculate_confidence(context)

        # Cache result
        self._save_cache(lead_id, context)

        self._log(f"  done - confidence: {context.confidence:.0%}")

        return context

    def enrich_lead(
        self,
        lead_id: str,
        company: str,
        country: str = "",
        industries: List[str] = None,
        website: str = "",
        force_refresh: bool = False,
    ) -> IrisContext:
        """Sync wrapper for backward compatibility (BatchProcessor, CLI, etc.)."""
        return asyncio.run(
            self.enrich_lead_async(lead_id, company, country, industries, website, force_refresh)
        )

    async def _search_company_news_async(
        self, company: str, country: str = "", max_results: int = 5
    ) -> Optional[Dict[str, str]]:
        """Async search for company news using aiohttp."""
        if not AIOHTTP_AVAILABLE:
            return None
        try:
            query = f"{company} news 2025 2026"
            if country:
                query += f" {country}"
            query += " thermoforming OR plastics OR manufacturing OR expansion"
            search_url = f"https://s.jina.ai/{quote(query)}"
            headers = {"Accept": "application/json", **self._headers}
            if JINA_API_KEY:
                headers["Authorization"] = f"Bearer {JINA_API_KEY}"
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(search_url, headers=headers) as response:
                    if response.status == 200:
                        try:
                            results = await response.json()
                        except Exception as e:
                            __import__('logging').getLogger(__name__).warning("News search parse error: %s", e, exc_info=True)
                            return None
                        company_lower = company.lower()
                        for result in results.get("data", [])[:max_results]:
                            title = result.get("title", "")
                            snippet = result.get("description", "")
                            if company_lower in title.lower() or company_lower in snippet.lower():
                                hook = self._extract_news_hook(title, snippet, company)
                                if hook:
                                    return {
                                        "hook": hook,
                                        "headline": title,
                                        "source": result.get("url", ""),
                                        "date": datetime.now().strftime("%Y-%m"),
                                    }
        except Exception as e:
            self._log(f"  news search error: {e}")
        return None

    def search_company_news(
        self,
        company: str,
        country: str = "",
        max_results: int = 5,
    ) -> Optional[Dict[str, str]]:
        """Sync wrapper for backward compatibility."""
        return asyncio.run(self._search_company_news_async(company, country, max_results))
    
    def get_industry_context(self, industries: List[str]) -> Dict[str, Any]:
        """
        Get relevant industry trend context.
        
        Matches provided industries against known trends database.
        
        Args:
            industries: List of industry names
        
        Returns:
            Dict with 'trend', 'hook', 'talking_points'
        """
        for industry in industries:
            industry_lower = industry.lower()
            
            # Check each trend category
            for category, data in INDUSTRY_TRENDS_2026.items():
                # Match by category name or keywords
                if category in industry_lower:
                    return {
                        "trend": data["trend"],
                        "hook": data["hook"],
                        "talking_points": data["talking_points"],
                        "category": category,
                    }
                
                # Match by keywords
                if any(kw in industry_lower for kw in data["keywords"]):
                    return {
                        "trend": data["trend"],
                        "hook": data["hook"],
                        "talking_points": data["talking_points"],
                        "category": category,
                    }
        
        # Default fallback
        return {
            "trend": "Manufacturing efficiency investments driving equipment upgrades",
            "hook": "Competitive thermoforming equipment for your production needs",
            "talking_points": [],
            "category": "general",
        }
    
    def get_geo_context(self, country: str) -> Dict[str, str]:
        """
        Get geopolitical context for a country.
        
        Args:
            country: Country name
        
        Returns:
            Dict with 'current' context and 'opportunity' angle
        """
        country_lower = country.lower()
        
        # Direct match
        if country_lower in GEOPOLITICAL_CONTEXTS:
            return GEOPOLITICAL_CONTEXTS[country_lower]
        
        # Partial match
        for key, data in GEOPOLITICAL_CONTEXTS.items():
            if key in country_lower or country_lower in key:
                return data
        
        # EU fallback
        eu_countries = ["germany", "france", "italy", "spain", "netherlands", "belgium",
                       "austria", "czech", "poland", "romania", "hungary", "portugal"]
        if any(c in country_lower for c in eu_countries):
            return GEOPOLITICAL_CONTEXTS["eu_general"]
        
        # Nordic fallback
        nordic = ["sweden", "norway", "denmark", "finland"]
        if any(c in country_lower for c in nordic):
            return GEOPOLITICAL_CONTEXTS.get("sweden", GEOPOLITICAL_CONTEXTS["eu_general"])
        
        # Generic fallback
        return {
            "current": "Global supply chain diversification ongoing",
            "opportunity": "Direct partnerships with established manufacturers",
        }
    
    async def _scrape_company_website_async(
        self, company: str, website: str
    ) -> Optional[Dict[str, Any]]:
        """Async scrape company website using aiohttp."""
        if not AIOHTTP_AVAILABLE:
            return None
        try:
            paths_to_try = ["/news", "/press", "/about", "/about-us", "/company", ""]
            headers = {"Accept": "text/plain", **self._headers}
            if JINA_API_KEY:
                headers["Authorization"] = f"Bearer {JINA_API_KEY}"
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for path in paths_to_try:
                    url = website.rstrip("/") + path
                    jina_url = f"https://r.jina.ai/{url}"
                    async with session.get(jina_url, headers=headers) as response:
                        if response.status == 200:
                            text = await response.text()
                            if len(text) > 500:
                                text = text[:5000]
                                if "2026" in text or "2025" in text:
                                    insight = self._extract_website_insight(text, company)
                                    if insight:
                                        return {
                                            "insight": insight,
                                            "focus_areas": self._extract_focus_areas(text),
                                        }
                                focus_areas = self._extract_focus_areas(text)
                                if focus_areas:
                                    return {"insight": None, "focus_areas": focus_areas}
                                break
        except Exception as e:
            self._log(f"  website scrape error: {e}")
        return None

    def scrape_company_website(
        self,
        company: str,
        website: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Scrape company website (sync wrapper for backward compat).
        """
        return asyncio.run(self._scrape_company_website_async(company, website))

    # =========================================================================
    # EXTRACTION HELPERS
    # =========================================================================
    
    def _extract_news_hook(
        self, 
        title: str, 
        snippet: str, 
        company: str,
    ) -> Optional[str]:
        """Extract a usable news hook from search results."""
        text = f"{title} {snippet}".lower()
        
        # Expansion/investment
        if any(w in text for w in ["expand", "invest", "new plant", "facility", "million", "growth"]):
            return self._llm_extract(
                f"Title: {title}\nSnippet: {snippet}",
                company,
                "expansion news",
                "Write ONE sentence acknowledging this expansion/investment news naturally."
            )
        
        # Acquisition/merger
        if any(w in text for w in ["acqui", "merge", "bought", "purchase"]):
            return self._llm_extract(
                f"Title: {title}\nSnippet: {snippet}",
                company,
                "acquisition",
                "Write ONE sentence congratulating them on this acquisition/merger."
            )
        
        # New product/capability
        if any(w in text for w in ["launch", "new product", "introduce", "capability"]):
            return self._llm_extract(
                f"Title: {title}\nSnippet: {snippet}",
                company,
                "product news",
                "Write ONE sentence referencing their new product/capability."
            )
        
        # Leadership
        if any(w in text for w in ["ceo", "appoint", "hire", "leadership", "executive"]):
            return self._llm_extract(
                f"Title: {title}\nSnippet: {snippet}",
                company,
                "leadership",
                "Write ONE sentence acknowledging the leadership news."
            )
        
        # Award/recognition
        if any(w in text for w in ["award", "recognition", "certif", "achieve"]):
            return self._llm_extract(
                f"Title: {title}\nSnippet: {snippet}",
                company,
                "achievement",
                "Write ONE sentence congratulating them on this achievement."
            )
        
        return None
    
    def _extract_website_insight(self, text: str, company: str) -> Optional[str]:
        """Extract insight from website content."""
        return self._llm_extract(
            text[:3000],
            company,
            "website",
            "Extract ONE recent, noteworthy thing about this company (news, capability, focus). "
            "If nothing recent or noteworthy, respond with 'None'."
        )
    
    def _extract_focus_areas(self, text: str) -> List[str]:
        """Extract company focus areas from website text."""
        focus_areas = []
        
        # Industry keywords
        industry_keywords = {
            "automotive": ["automotive", "vehicle", "car", "truck", "interior trim"],
            "aerospace": ["aerospace", "aircraft", "aviation", "cabin"],
            "packaging": ["packaging", "food", "medical", "blister", "tray"],
            "sanitary": ["bathtub", "shower", "sanitary", "bath", "spa"],
            "signage": ["sign", "display", "retail", "advertising"],
            "refrigeration": ["refrigerat", "cooler", "freezer", "cold chain"],
        }
        
        text_lower = text.lower()
        for industry, keywords in industry_keywords.items():
            if any(kw in text_lower for kw in keywords):
                focus_areas.append(industry)
        
        return focus_areas[:3]  # Max 3
    
    def _llm_extract(
        self, 
        content: str, 
        company: str, 
        context_type: str,
        instruction: str,
    ) -> Optional[str]:
        """Use LLM to extract specific information."""
        if not OPENAI_AVAILABLE:
            return None
        
        prompt = f"""Company: {company}
Context type: {context_type}

Content:
{content}

{instruction}

Respond with just the sentence, no quotes or explanation. If nothing relevant, say "None"."""

        try:
            response = _openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.7,
            )
            result = response.choices[0].message.content.strip()
            if result.lower() != "none" and len(result) > 10:
                return result
        except:
            pass
        
        return None
    
    # =========================================================================
    # EMAIL HOOK BUILDING
    # =========================================================================
    
    def _build_email_hooks(self, context: IrisContext, company: str) -> IrisContext:
        """Build ready-to-use email hooks from gathered intelligence."""
        
        # Timely opener (prioritize news > company insight > industry trend)
        if context.news_hook:
            context.timely_opener = context.news_hook
        elif context.company_insight:
            context.timely_opener = context.company_insight
        elif context.industry_trend:
            context.timely_opener = f"With {context.industry_trend.lower()}, {company} came to mind."
        
        # Value prop angle (based on geo + industry)
        angles = []
        if context.geo_opportunity:
            angles.append(context.geo_opportunity)
        if context.industry_hook:
            angles.append(context.industry_hook)
        
        if angles:
            context.value_prop_angle = angles[0]
        
        return context
    
    def _calculate_confidence(self, context: IrisContext) -> float:
        """Calculate confidence score based on gathered intelligence."""
        score = 0.0
        
        if context.news_hook:
            score += 0.35  # News is most valuable
        if context.industry_hook:
            score += 0.25
        if context.geo_context:
            score += 0.15
        if context.company_insight:
            score += 0.25
        
        return min(score, 1.0)
    
    # =========================================================================
    # CACHE MANAGEMENT
    # =========================================================================
    
    def _cache_key(self, lead_id: str) -> str:
        """Generate cache filename."""
        hash_suffix = hashlib.md5(lead_id.encode()).hexdigest()[:8]
        return f"iris_{lead_id}_{hash_suffix}.json"
    
    def _load_cache(self, lead_id: str) -> Optional[IrisContext]:
        """Load cached context if fresh."""
        cache_file = CACHE_DIR / self._cache_key(lead_id)
        
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                refreshed = datetime.fromisoformat(data.get("refreshed_at", "2000-01-01"))
                
                if datetime.now() - refreshed < self.cache_ttl:
                    context = IrisContext(**data)
                    context.cache_hit = True
                    return context
            except:
                pass
        
        return None
    
    def _save_cache(self, lead_id: str, context: IrisContext):
        """Save context to cache."""
        cache_file = CACHE_DIR / self._cache_key(lead_id)
        
        try:
            cache_file.write_text(json.dumps(asdict(context), indent=2))
        except Exception as e:
            self._log(f"cache save failed: {e}")
    
    def clear_cache(self, lead_id: str = None):
        """Clear cache for a lead or all leads."""
        if lead_id:
            cache_file = CACHE_DIR / self._cache_key(lead_id)
            if cache_file.exists():
                cache_file.unlink()
                self._log(f"cleared cache for {lead_id}")
        else:
            for f in CACHE_DIR.glob("iris_*.json"):
                f.unlink()
            self._log("cleared all cache")


# =============================================================================
# BATCH ENRICHMENT
# =============================================================================

@dataclass
class BatchEnrichmentResult:
    """Result of batch lead enrichment."""
    total_leads: int
    enriched: int
    failed: int
    cache_hits: int
    avg_confidence: float
    elapsed_seconds: float
    results: Dict[str, IrisContext]
    errors: Dict[str, str]
    
    def summary(self) -> str:
        """Get a summary string."""
        return (
            f"Enriched {self.enriched}/{self.total_leads} leads "
            f"({self.cache_hits} cache hits, {self.failed} failed) "
            f"in {self.elapsed_seconds:.1f}s, avg confidence: {self.avg_confidence:.0%}"
        )
    
    def get_by_confidence(self, min_confidence: float = 0.5) -> List[IrisContext]:
        """Get results above a confidence threshold."""
        return [
            ctx for ctx in self.results.values() 
            if ctx.confidence >= min_confidence
        ]
    
    def get_with_news(self) -> List[IrisContext]:
        """Get results that have news hooks."""
        return [
            ctx for ctx in self.results.values()
            if ctx.news_hook
        ]
    
    def to_report(self) -> str:
        """Generate a detailed report."""
        lines = [
            "=" * 70,
            "IRIS BATCH ENRICHMENT REPORT",
            "=" * 70,
            "",
            f"Total Leads: {self.total_leads}",
            f"Successfully Enriched: {self.enriched}",
            f"Cache Hits: {self.cache_hits}",
            f"Failed: {self.failed}",
            f"Average Confidence: {self.avg_confidence:.0%}",
            f"Elapsed Time: {self.elapsed_seconds:.1f} seconds",
            "",
            "─" * 70,
            "RESULTS BY CONFIDENCE",
            "─" * 70,
        ]
        
        # Sort by confidence
        sorted_results = sorted(
            self.results.values(),
            key=lambda x: x.confidence,
            reverse=True
        )
        
        for ctx in sorted_results:
            status = "📰" if ctx.news_hook else "📈" if ctx.industry_hook else "🌍"
            cache = " (cached)" if ctx.cache_hit else ""
            lines.append(
                f"  {status} [{ctx.confidence:.0%}] {ctx.company}{cache}"
            )
            if ctx.timely_opener:
                lines.append(f"      → {ctx.timely_opener[:60]}...")
        
        if self.errors:
            lines.extend([
                "",
                "─" * 70,
                "ERRORS",
                "─" * 70,
            ])
            for lead_id, error in self.errors.items():
                lines.append(f"  ✗ {lead_id}: {error}")
        
        lines.append("=" * 70)
        return "\n".join(lines)


class IrisBatchProcessor:
    """
    Batch processor for enriching multiple leads in parallel.
    
    Uses asyncio + ThreadPoolExecutor for maximum throughput.
    
    Usage:
        processor = IrisBatchProcessor(max_workers=5)
        result = processor.enrich_leads(leads_list)
        print(result.summary())
    """
    
    def __init__(self, max_workers: int = 5, cache_ttl_hours: int = 24):
        """
        Initialize batch processor.
        
        Args:
            max_workers: Maximum concurrent enrichment tasks
            cache_ttl_hours: Cache TTL for Iris instances
        """
        self.max_workers = max_workers
        self.cache_ttl_hours = cache_ttl_hours
        self.iris = Iris(cache_ttl_hours=cache_ttl_hours)
    
    def enrich_leads(
        self,
        leads: List[Dict[str, Any]],
        force_refresh: bool = False,
        progress_callback: callable = None,
    ) -> BatchEnrichmentResult:
        """
        Enrich multiple leads in parallel.
        
        Args:
            leads: List of lead dicts with keys: 
                   id, company, country, industries (optional), website (optional)
            force_refresh: Bypass cache for all leads
            progress_callback: Optional callback(current, total, company) for progress updates
        
        Returns:
            BatchEnrichmentResult with all contexts and summary
        """
        import time
        start_time = time.time()
        
        results: Dict[str, IrisContext] = {}
        errors: Dict[str, str] = {}
        cache_hits = 0
        
        total = len(leads)
        self.iris._log(f"starting batch enrichment for {total} leads (workers={self.max_workers})")
        
        def enrich_one(lead: Dict) -> Tuple[str, Optional[IrisContext], Optional[str]]:
            """Enrich a single lead, return (lead_id, context, error)."""
            lead_id = lead.get("id", lead.get("lead_id", "unknown"))
            try:
                context = self.iris.enrich_lead(
                    lead_id=lead_id,
                    company=lead.get("company", ""),
                    country=lead.get("country", ""),
                    industries=lead.get("industries", []),
                    website=lead.get("website", ""),
                    force_refresh=force_refresh,
                )
                return (lead_id, context, None)
            except Exception as e:
                return (lead_id, None, str(e))
        
        # Process in parallel
        completed = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_lead = {
                executor.submit(enrich_one, lead): lead 
                for lead in leads
            }
            
            for future in as_completed(future_to_lead):
                lead_id, context, error = future.result()
                completed += 1
                
                if context:
                    results[lead_id] = context
                    if context.cache_hit:
                        cache_hits += 1
                else:
                    errors[lead_id] = error or "Unknown error"
                
                # Progress callback
                if progress_callback:
                    company = future_to_lead[future].get("company", lead_id)
                    progress_callback(completed, total, company)
        
        elapsed = time.time() - start_time
        
        # Calculate average confidence
        confidences = [ctx.confidence for ctx in results.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        result = BatchEnrichmentResult(
            total_leads=total,
            enriched=len(results),
            failed=len(errors),
            cache_hits=cache_hits,
            avg_confidence=avg_confidence,
            elapsed_seconds=elapsed,
            results=results,
            errors=errors,
        )
        
        self.iris._log(result.summary())
        
        return result
    
    async def enrich_leads_async(
        self,
        leads: List[Dict[str, Any]],
        force_refresh: bool = False,
    ) -> BatchEnrichmentResult:
        """
        Async version of batch enrichment.
        
        Use this when running inside an async context.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.enrich_leads(leads, force_refresh)
        )
    
    def enrich_from_file(
        self,
        filepath: str,
        force_refresh: bool = False,
    ) -> BatchEnrichmentResult:
        """
        Enrich leads from a JSON file.
        
        Expects file format:
        {
            "leads": [
                {"id": "eu-001", "company": "...", "country": "...", ...},
                ...
            ]
        }
        """
        import json
        from pathlib import Path
        
        data = json.loads(Path(filepath).read_text())
        leads = data.get("leads", data if isinstance(data, list) else [])
        
        return self.enrich_leads(leads, force_refresh)


def batch_enrich_european_leads(
    force_refresh: bool = False,
    max_workers: int = 5,
    priority_filter: List[str] = None,
) -> BatchEnrichmentResult:
    """
    Convenience function to enrich all European leads.
    
    Args:
        force_refresh: Bypass cache
        max_workers: Parallel workers
        priority_filter: Only enrich leads with these priorities (e.g., ["critical", "high"])
    
    Returns:
        BatchEnrichmentResult
    """
    import json
    
    # Load European leads
    leads_file = PROJECT_ROOT / "data" / "imports" / "european_leads_structured.json"
    if not leads_file.exists():
        raise FileNotFoundError(f"Leads file not found: {leads_file}")
    
    data = json.loads(leads_file.read_text())
    leads = data.get("leads", [])
    
    # Filter by priority if specified
    if priority_filter:
        priority_filter_lower = [p.lower() for p in priority_filter]
        leads = [
            lead for lead in leads
            if lead.get("priority", "medium").lower() in priority_filter_lower
        ]
    
    # Run batch enrichment
    processor = IrisBatchProcessor(max_workers=max_workers)
    return processor.enrich_leads(leads, force_refresh=force_refresh)


def enrich_top_25_hot_leads(force_refresh: bool = False) -> BatchEnrichmentResult:
    """
    Enrich the top 25 hottest leads (critical + high priority).
    
    Returns:
        BatchEnrichmentResult with intelligence for hot leads
    """
    return batch_enrich_european_leads(
        force_refresh=force_refresh,
        max_workers=5,
        priority_filter=["critical", "high"]
    )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def enrich_lead_for_email_async(
    lead_id: str,
    company: str,
    country: str = "",
    industries: List[str] = None,
    website: str = "",
) -> Dict[str, str]:
    """
    Async: get email-ready intelligence for a lead.
    Main integration point for iris_skill and other async callers.
    """
    iris = Iris()
    context = await iris.enrich_lead_async(
        lead_id=lead_id,
        company=company,
        country=country,
        industries=industries or [],
        website=website,
    )
    return context.to_email_vars()


def enrich_lead_for_email(
    lead_id: str,
    company: str,
    country: str = "",
    industries: List[str] = None,
    website: str = "",
) -> Dict[str, str]:
    """
    Sync wrapper: get email-ready intelligence for a lead.
    Backward compatibility for drip campaign, etc.
    """
    return asyncio.run(
        enrich_lead_for_email_async(
            lead_id, company, country, industries or [], website
        )
    )


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    import time
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                     IRIS - Intelligence Agent                  ║
║           Swift messenger gathering market intelligence         ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        # =====================================================================
        # BATCH COMMANDS
        # =====================================================================
        
        if cmd == "batch":
            # Batch enrich all European leads
            print("[Iris] Starting batch enrichment of all European leads...\n")
            
            force = "--force" in sys.argv or "-f" in sys.argv
            workers = 5
            for arg in sys.argv:
                if arg.startswith("--workers="):
                    workers = int(arg.split("=")[1])
            
            def progress(current, total, company):
                pct = current / total * 100
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                print(f"\r  [{bar}] {current}/{total} - {company[:30]:<30}", end="", flush=True)
            
            result = batch_enrich_european_leads(
                force_refresh=force,
                max_workers=workers,
            )
            
            print("\n")
            print(result.to_report())
        
        elif cmd == "hot" or cmd == "top25":
            # Batch enrich top 25 hot leads
            print("[Iris] Starting batch enrichment of TOP 25 HOT LEADS...\n")
            
            force = "--force" in sys.argv or "-f" in sys.argv
            
            def progress(current, total, company):
                pct = current / total * 100
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                print(f"\r  [{bar}] {current}/{total} - {company[:30]:<30}", end="", flush=True)
            
            result = enrich_top_25_hot_leads(force_refresh=force)
            
            print("\n")
            print(result.to_report())
            
            # Save results to file
            output_file = PROJECT_ROOT / "data" / "cache" / "iris" / "hot_leads_intelligence.json"
            import json
            output_data = {
                "generated_at": datetime.now().isoformat(),
                "summary": result.summary(),
                "leads": {
                    lead_id: asdict(ctx) 
                    for lead_id, ctx in result.results.items()
                }
            }
            output_file.write_text(json.dumps(output_data, indent=2))
            print(f"\n📁 Results saved to: {output_file}")
        
        elif cmd == "clear-cache":
            # Clear Iris cache
            iris = Iris()
            iris.clear_cache()
            print("Cache cleared.")
        
        elif cmd == "report":
            # Generate report from cached data
            cache_file = PROJECT_ROOT / "data" / "cache" / "iris" / "hot_leads_intelligence.json"
            if cache_file.exists():
                import json
                data = json.loads(cache_file.read_text())
                print(f"Intelligence Report (generated: {data['generated_at']})")
                print("=" * 70)
                print(f"Summary: {data['summary']}")
                print("\n" + "─" * 70)
                for lead_id, ctx in data['leads'].items():
                    confidence = ctx.get('confidence', 0)
                    company = ctx.get('company', lead_id)
                    hook = ctx.get('timely_opener', 'N/A')
                    print(f"  [{confidence:.0%}] {company}")
                    print(f"       → {hook[:70]}...")
            else:
                print("No cached report found. Run 'hot' command first.")
        
        # =====================================================================
        # SINGLE LEAD COMMAND
        # =====================================================================
        
        elif cmd not in ["batch", "hot", "top25", "clear-cache", "report"]:
            # Single lead enrichment (original behavior)
            company = cmd  # First arg is company name
            country = sys.argv[2] if len(sys.argv) > 2 else ""
            industries = sys.argv[3].split(",") if len(sys.argv) > 3 else []
            website = sys.argv[4] if len(sys.argv) > 4 else ""
            
            iris = Iris()
            context = iris.enrich_lead(
                lead_id="cli-test",
                company=company,
                country=country,
                industries=industries,
                website=website,
                force_refresh=True,
            )
            
            print(f"\n{'─'*60}")
            print(f"INTELLIGENCE REPORT: {company}")
            print(f"{'─'*60}")
            print(f"\n📰 NEWS:")
            print(f"   Hook: {context.news_hook or 'None found'}")
            print(f"   Source: {context.news_source or 'N/A'}")
            print(f"\n📈 INDUSTRY:")
            print(f"   Trend: {context.industry_trend or 'N/A'}")
            print(f"   Hook: {context.industry_hook or 'N/A'}")
            print(f"   Talking Points: {context.industry_talking_points or 'N/A'}")
            print(f"\n🌍 GEOPOLITICAL:")
            print(f"   Context: {context.geo_context or 'N/A'}")
            print(f"   Opportunity: {context.geo_opportunity or 'N/A'}")
            print(f"\n🏢 COMPANY:")
            print(f"   Insight: {context.company_insight or 'N/A'}")
            print(f"   Focus Areas: {context.company_focus_areas or 'N/A'}")
            print(f"\n{'─'*60}")
            print(f"📧 EMAIL-READY HOOKS:")
            print(f"{'─'*60}")
            for key, value in context.to_email_vars().items():
                if value:
                    print(f"   {key}: {value}")
            print(f"\n   Confidence: {context.confidence:.0%}")
            print(f"   Sources: {context.sources_checked}")
    
    else:
        print("Usage:")
        print("")
        print("  SINGLE LEAD:")
        print("    python agent.py <company> [country] [industries] [website]")
        print("")
        print("  BATCH COMMANDS:")
        print("    python agent.py hot              - Enrich top 25 hot leads (critical + high)")
        print("    python agent.py batch            - Enrich ALL European leads")
        print("    python agent.py batch --force    - Force refresh (bypass cache)")
        print("    python agent.py batch --workers=10  - Use 10 parallel workers")
        print("    python agent.py clear-cache      - Clear all cached intelligence")
        print("    python agent.py report           - View cached hot leads report")
        print("")
        print("  EXAMPLES:")
        print("    python agent.py 'TSN Kunststoffverarbeitung' 'Germany' 'automotive,vehicle'")
        print("    python agent.py 'Soplami' 'France' 'aerospace' 'https://soplami.com'")
        print("    python agent.py hot --force")
