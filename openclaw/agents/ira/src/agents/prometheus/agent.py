#!/usr/bin/env python3
"""
PROMETHEUS — The Market Discovery Agent
========================================

Named after the Titan who brought fire to humanity — Prometheus brings
new market knowledge to Machinecraft.

Prometheus scans the world for products and industries where vacuum forming
can be applied, with a focus on emerging sectors:
  - Battery storage enclosures & EV components
  - Renewable energy (solar panel frames, wind turbine fairings)
  - Drone / UAV body shells
  - Medical device housings (post-COVID growth)
  - Modular construction & prefab panels
  - Cold chain / insulated packaging
  - Agricultural tech enclosures
  - Data center cooling shrouds

Architecture:
    Athena → delegates to → Prometheus → returns OpportunityReport
    Prometheus uses: Iris (web intelligence), Qdrant (existing knowledge),
                     Machine DB (product fit), LLM (analysis)

Usage:
    from openclaw.agents.ira.src.agents.prometheus.agent import Prometheus, get_prometheus

    prometheus = get_prometheus()
    report = await prometheus.scan_industry("battery storage")
    full = await prometheus.run_discovery_sweep()
    opp = await prometheus.evaluate_opportunity("EV battery enclosures", "Germany")
"""

import json
import logging
import os
import sys
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

logger = logging.getLogger("ira.prometheus")

AGENT_DIR = Path(__file__).parent
SRC_DIR = AGENT_DIR.parent.parent
PROJECT_ROOT = SRC_DIR.parent.parent.parent

sys.path.insert(0, str(SRC_DIR / "brain"))
sys.path.insert(0, str(PROJECT_ROOT / "agents" / "iris"))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

# ─── Imports with graceful fallbacks ─────────────────────────────────────────

try:
    import openai
    _openai_client = openai.AsyncOpenAI()
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    from agent import Iris
    IRIS_AVAILABLE = True
except ImportError:
    IRIS_AVAILABLE = False

try:
    from qdrant_retriever import retrieve as qdrant_retrieve
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

try:
    from machine_database import MACHINE_DATABASE
    MACHINE_DB_AVAILABLE = True
except ImportError:
    MACHINE_DB_AVAILABLE = False

JINA_API_KEY = os.getenv("JINA_API_KEY", "")

DATA_DIR = PROJECT_ROOT / "data" / "discovery"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OPPORTUNITIES_FILE = DATA_DIR / "opportunities.json"
SCAN_LOG_FILE = DATA_DIR / "scan_log.jsonl"
INDUSTRY_MAP_FILE = DATA_DIR / "industry_taxonomy.json"

LLM_MODEL = os.getenv("PROMETHEUS_MODEL", "gpt-4o")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class FitScore(Enum):
    """How well vacuum forming fits this product/application."""
    PERFECT = "perfect"       # vacuum forming is the standard process
    STRONG = "strong"         # vacuum forming is a top-2 choice
    VIABLE = "viable"         # vacuum forming works, but competes with injection/blow molding
    STRETCH = "stretch"       # possible but not typical — needs validation
    POOR = "poor"             # wrong process entirely


class MarketMaturity(Enum):
    """How mature is this market for thermoforming?"""
    ESTABLISHED = "established"   # automotive interiors, packaging — we're already here
    GROWING = "growing"           # EV, medical — adoption accelerating
    EMERGING = "emerging"         # battery storage, drones — early movers win
    NASCENT = "nascent"           # speculative — needs R&D validation


@dataclass
class DiscoveredProduct:
    """A product or component that could be made via vacuum forming."""
    name: str
    description: str
    industry: str
    sub_industry: str = ""
    materials: List[str] = field(default_factory=list)
    typical_thickness_mm: str = ""
    typical_size_mm: str = ""
    fit_score: str = "viable"
    why_vacuum_forming: str = ""
    competing_processes: List[str] = field(default_factory=list)
    example_companies: List[str] = field(default_factory=list)
    regions_of_demand: List[str] = field(default_factory=list)
    estimated_volume: str = ""  # "low", "medium", "high", "very_high"
    source_urls: List[str] = field(default_factory=list)


@dataclass
class MarketOpportunity:
    """A scored market opportunity combining product + market intelligence."""
    id: str
    product: DiscoveredProduct
    market_maturity: str = "emerging"
    machinecraft_fit: str = ""         # which MC machine series fits
    recommended_machines: List[str] = field(default_factory=list)
    estimated_price_range_usd: str = ""
    competitive_landscape: str = ""
    entry_strategy: str = ""
    reference_customers: List[str] = field(default_factory=list)
    score: float = 0.0                 # 0-100 composite score
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    discovered_at: str = ""
    last_updated: str = ""
    iris_intelligence: Dict[str, str] = field(default_factory=dict)


@dataclass
class IndustryScanResult:
    """Result of scanning a single industry vertical."""
    industry: str
    scan_date: str
    products_found: List[DiscoveredProduct] = field(default_factory=list)
    opportunities: List[MarketOpportunity] = field(default_factory=list)
    market_size_estimate: str = ""
    growth_rate: str = ""
    key_trends: List[str] = field(default_factory=list)
    key_players: List[str] = field(default_factory=list)
    raw_intelligence: str = ""


# =============================================================================
# SEED INDUSTRIES — Prometheus's starting knowledge
# =============================================================================

EMERGING_INDUSTRIES = {
    "battery_storage": {
        "name": "Battery Storage & EV Components",
        "search_queries": [
            "battery enclosure thermoforming",
            "EV battery cover vacuum formed",
            "lithium battery housing plastic",
            "energy storage enclosure manufacturing",
            "battery pack protective covers thermoformed",
        ],
        "products_to_find": [
            "battery module covers", "cell holder trays", "thermal barrier sheets",
            "BMS enclosures", "battery pack housings", "EV under-body shields",
        ],
        "materials": ["ABS", "PC", "PP", "HDPE", "FR-rated ABS", "Polycarbonate"],
        "why_thermoforming": "Large, lightweight covers with fire-retardant properties. Lower tooling cost than injection molding for medium volumes typical of battery OEMs.",
        "regions": ["Germany", "China", "USA", "South Korea", "India"],
    },
    "renewable_energy": {
        "name": "Renewable Energy",
        "search_queries": [
            "solar panel frame thermoforming",
            "wind turbine nacelle cover vacuum forming",
            "solar inverter enclosure plastic forming",
            "renewable energy plastic housings",
        ],
        "products_to_find": [
            "solar panel back sheets", "inverter housings", "wind turbine fairings",
            "nacelle covers", "junction box covers", "cable management trays",
        ],
        "materials": ["ABS", "ASA", "PMMA", "PC", "HDPE"],
        "why_thermoforming": "Large-format parts (nacelle covers, panel frames) at volumes too low for injection molding. UV-stable materials needed.",
        "regions": ["Germany", "India", "USA", "China", "Denmark"],
    },
    "drone_uav": {
        "name": "Drone & UAV Manufacturing",
        "search_queries": [
            "drone body shell thermoforming",
            "UAV fuselage vacuum forming",
            "drone enclosure manufacturing plastic",
            "delivery drone housing production",
        ],
        "products_to_find": [
            "drone body shells", "UAV fuselage halves", "payload bay covers",
            "sensor housings", "propeller guards", "landing gear fairings",
        ],
        "materials": ["ABS", "Polycarbonate", "PETG", "Carbon-fiber reinforced"],
        "why_thermoforming": "Lightweight, aerodynamic shells. Rapid prototyping and low-to-medium volume production. Design iteration speed.",
        "regions": ["USA", "China", "Israel", "Germany", "India"],
    },
    "medical_devices": {
        "name": "Medical Device Housings",
        "search_queries": [
            "medical device enclosure thermoforming",
            "diagnostic equipment housing vacuum formed",
            "medical cart covers thermoformed",
            "hospital equipment plastic housing",
        ],
        "products_to_find": [
            "diagnostic machine housings", "medical cart covers", "imaging equipment shrouds",
            "patient bed panels", "surgical light covers", "lab equipment enclosures",
        ],
        "materials": ["ABS", "HIPS", "Polycarbonate", "PETG", "Acrylic"],
        "why_thermoforming": "Clean, smooth surfaces for hygiene. Medium volumes. Custom shapes for ergonomic designs. FDA-compliant materials available.",
        "regions": ["USA", "Germany", "Japan", "India", "Netherlands"],
    },
    "modular_construction": {
        "name": "Modular Construction & Prefab",
        "search_queries": [
            "prefab wall panel thermoforming",
            "modular bathroom pod vacuum forming",
            "construction panel plastic forming",
            "prefabricated building components thermoformed",
        ],
        "products_to_find": [
            "bathroom wall panels", "shower trays", "modular ceiling panels",
            "facade cladding", "window surrounds", "HVAC duct sections",
        ],
        "materials": ["ABS", "PMMA", "PVC", "Acrylic", "HDPE"],
        "why_thermoforming": "Large panels (up to 3m). Consistent quality for modular assembly. Lower cost than fiberglass for medium runs.",
        "regions": ["UK", "Germany", "Netherlands", "Scandinavia", "USA"],
    },
    "cold_chain": {
        "name": "Cold Chain & Insulated Packaging",
        "search_queries": [
            "insulated shipping container thermoforming",
            "cold chain packaging vacuum formed",
            "pharmaceutical cold chain enclosure",
            "temperature controlled packaging thermoformed",
        ],
        "products_to_find": [
            "insulated shipping containers", "vaccine transport boxes",
            "frozen food packaging", "pharmaceutical cold boxes",
            "reusable cold chain containers", "insulated pallet covers",
        ],
        "materials": ["EPS", "EPP", "HDPE", "PP", "Multilayer films"],
        "why_thermoforming": "Deep-draw capability for insulated containers. Reusable designs replacing single-use. Growing pharma cold chain demand.",
        "regions": ["USA", "EU", "India", "Middle East", "Southeast Asia"],
    },
    "agritech": {
        "name": "Agricultural Technology",
        "search_queries": [
            "agricultural machinery cover thermoforming",
            "tractor fender vacuum forming",
            "farm equipment enclosure plastic",
            "precision agriculture housing",
        ],
        "products_to_find": [
            "tractor fenders", "combine harvester covers", "seed drill housings",
            "irrigation controller enclosures", "drone sprayer bodies",
            "livestock equipment panels",
        ],
        "materials": ["ABS", "HDPE", "PP", "ASA"],
        "why_thermoforming": "Rugged, UV-stable parts. Large fenders and covers. Low-to-medium volumes typical of ag equipment.",
        "regions": ["India", "Brazil", "USA", "Germany", "Australia"],
    },
    "data_centers": {
        "name": "Data Center & IT Infrastructure",
        "search_queries": [
            "server rack cover thermoforming",
            "data center airflow panel vacuum formed",
            "IT equipment enclosure plastic forming",
            "cooling shroud thermoformed",
        ],
        "products_to_find": [
            "server rack panels", "airflow management shrouds", "cable management trays",
            "cooling duct covers", "UPS enclosures", "edge computing housings",
        ],
        "materials": ["ABS", "Polycarbonate", "HIPS", "FR-ABS"],
        "why_thermoforming": "Fire-retardant enclosures. Custom airflow management. Rapid design changes as server architectures evolve.",
        "regions": ["USA", "Ireland", "Singapore", "Germany", "India"],
    },
    "marine_watercraft": {
        "name": "Marine & Watercraft",
        "search_queries": [
            "boat hull thermoforming",
            "marine dashboard vacuum forming",
            "kayak shell thermoformed",
            "watercraft component plastic forming",
        ],
        "products_to_find": [
            "small boat hulls", "kayak/canoe shells", "marine dashboards",
            "hatch covers", "seat shells", "storage compartments",
        ],
        "materials": ["HDPE", "ABS", "Polycarbonate", "Acrylic"],
        "why_thermoforming": "Twin-sheet forming for hollow hulls. UV and water resistant. Cost-effective for small-to-medium boat runs.",
        "regions": ["USA", "Australia", "Scandinavia", "UK", "Turkey"],
    },
    "ev_charging": {
        "name": "EV Charging Infrastructure",
        "search_queries": [
            "EV charger enclosure thermoforming",
            "charging station housing vacuum formed",
            "electric vehicle charger cover plastic",
            "EVSE enclosure manufacturing",
        ],
        "products_to_find": [
            "charger pedestal housings", "wall-mount charger covers",
            "cable management shrouds", "display bezels", "weather shields",
        ],
        "materials": ["ASA", "ABS", "Polycarbonate", "PC/ABS blend"],
        "why_thermoforming": "Outdoor-rated UV-stable enclosures. Thousands of units needed (sweet spot for thermoforming vs injection). Rapid iteration as standards evolve.",
        "regions": ["USA", "EU", "China", "India", "UK"],
    },
}


# =============================================================================
# WEB INTELLIGENCE (uses Jina like Iris)
# =============================================================================

class WebScanner:
    """Searches the web for vacuum forming opportunities in target industries."""

    def __init__(self):
        self._cache: Dict[str, Tuple[str, datetime]] = {}
        self._cache_ttl_hours = 24

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        cache_key = hashlib.md5(query.encode()).hexdigest()
        if cache_key in self._cache:
            cached, ts = self._cache[cache_key]
            age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            if age_h < self._cache_ttl_hours:
                return json.loads(cached)

        if not AIOHTTP_AVAILABLE or not JINA_API_KEY:
            logger.warning("Web search unavailable (aiohttp=%s, jina=%s)", AIOHTTP_AVAILABLE, bool(JINA_API_KEY))
            return []

        url = f"https://s.jina.ai/{query}"
        headers = {
            "Authorization": f"Bearer {JINA_API_KEY}",
            "Accept": "application/json",
            "X-Retain-Images": "none",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        logger.warning("Jina search returned %d for: %s", resp.status, query)
                        return []
                    data = await resp.json()
                    results = []
                    for item in (data.get("data", []) or [])[:max_results]:
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "content": item.get("content", "")[:2000],
                        })
                    self._cache[cache_key] = (json.dumps(results), datetime.now(timezone.utc))
                    return results
        except Exception as e:
            logger.error("Web search failed for '%s': %s", query, e)
            return []

    async def scrape_page(self, url: str) -> str:
        if not AIOHTTP_AVAILABLE or not JINA_API_KEY:
            return ""
        reader_url = f"https://r.jina.ai/{url}"
        headers = {
            "Authorization": f"Bearer {JINA_API_KEY}",
            "Accept": "text/plain",
            "X-Retain-Images": "none",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(reader_url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        return text[:5000]
        except Exception as e:
            logger.error("Page scrape failed for '%s': %s", url, e)
        return ""


# =============================================================================
# LLM ANALYSIS ENGINE
# =============================================================================

class AnalysisEngine:
    """Uses LLM to analyze web results and score opportunities."""

    PRODUCT_DISCOVERY_PROMPT = """You are a market research analyst specializing in vacuum forming / thermoforming applications.

Given web search results about "{industry}", identify specific PRODUCTS or COMPONENTS that can be manufactured using vacuum forming (thermoforming).

For each product found, provide:
1. product_name: Specific name (e.g., "EV battery module cover" not just "battery parts")
2. description: What it is and how it's used (1-2 sentences)
3. materials: Likely plastic materials (ABS, PC, HDPE, PP, PETG, etc.)
4. typical_thickness_mm: Range like "2-4" or "1-3"
5. typical_size_mm: Approximate dimensions like "600x400" or "1200x800"
6. fit_score: One of: perfect, strong, viable, stretch
7. why_vacuum_forming: Why thermoforming specifically suits this product
8. competing_processes: What other manufacturing methods compete (injection molding, blow molding, rotomolding, etc.)
9. example_companies: Companies making or needing these products
10. estimated_volume: "low" (<100/yr), "medium" (100-1000/yr), "high" (1000-10000/yr), "very_high" (>10000/yr)

Focus on products where vacuum forming has a genuine advantage:
- Large parts (>300mm) where injection mold tooling is prohibitive
- Medium production volumes (100-10,000 units/year)
- Parts needing deep draw or complex contours
- Applications where tooling cost matters (startups, prototyping)
- Thick gauge (1-8mm) structural parts

IGNORE products better suited to injection molding (small, high-volume, tight tolerances).

Web search results:
{search_results}

Existing knowledge about this industry:
{existing_knowledge}

Return valid JSON array of products. Return at least 3, up to 8 products."""

    OPPORTUNITY_SCORING_PROMPT = """You are a strategic advisor for Machinecraft Technologies, a vacuum forming machine manufacturer.

Score this market opportunity for Machinecraft:

Product: {product_name}
Description: {product_description}
Industry: {industry}
Materials: {materials}
Fit Score: {fit_score}
Market Maturity: {market_maturity}

Machinecraft's machine lineup:
{machine_lineup}

Score these dimensions (0-100 each):
1. technical_fit: How well do MC machines handle this product? (size, thickness, materials)
2. market_timing: Is the market ready? (emerging = higher score for first-mover advantage)
3. volume_match: Does typical production volume match thermoforming sweet spot?
4. competitive_gap: How underserved is this market by existing thermoforming suppliers?
5. revenue_potential: What's the revenue opportunity for MC? (machine sales + repeat business)
6. strategic_value: Does this open a new vertical or strengthen an existing one?

Also provide:
- recommended_machines: Which MC machine series/models fit (e.g., "PF1-X-2015", "PF1-C-3020")
- estimated_price_range_usd: Machine price range for this application
- entry_strategy: 1-2 sentence go-to-market recommendation
- competitive_landscape: Who else serves this market?

Return valid JSON with scores and recommendations."""

    async def discover_products(
        self, industry: str, search_results: List[Dict], existing_knowledge: str
    ) -> List[DiscoveredProduct]:
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI unavailable — cannot analyze products")
            return []

        formatted_results = "\n\n".join(
            f"Source: {r.get('title', 'Unknown')}\nURL: {r.get('url', '')}\n{r.get('content', '')}"
            for r in search_results
        )

        prompt = self.PRODUCT_DISCOVERY_PROMPT.format(
            industry=industry,
            search_results=formatted_results or "(no web results available)",
            existing_knowledge=existing_knowledge or "(none)",
        )

        try:
            resp = await _openai_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            raw = resp.choices[0].message.content
            data = json.loads(raw)
            products_raw = data if isinstance(data, list) else data.get("products", [])

            products = []
            for p in products_raw:
                products.append(DiscoveredProduct(
                    name=p.get("product_name", p.get("name", "Unknown")),
                    description=p.get("description", ""),
                    industry=industry,
                    materials=p.get("materials", []),
                    typical_thickness_mm=str(p.get("typical_thickness_mm", "")),
                    typical_size_mm=str(p.get("typical_size_mm", "")),
                    fit_score=p.get("fit_score", "viable"),
                    why_vacuum_forming=p.get("why_vacuum_forming", ""),
                    competing_processes=p.get("competing_processes", []),
                    example_companies=p.get("example_companies", []),
                    estimated_volume=p.get("estimated_volume", "medium"),
                    source_urls=[r.get("url", "") for r in search_results if r.get("url")],
                ))
            return products

        except Exception as e:
            logger.error("Product discovery LLM call failed: %s", e)
            return []

    async def score_opportunity(
        self, product: DiscoveredProduct, machine_lineup: str
    ) -> Dict[str, Any]:
        if not OPENAI_AVAILABLE:
            return {"score": 0, "error": "OpenAI unavailable"}

        prompt = self.OPPORTUNITY_SCORING_PROMPT.format(
            product_name=product.name,
            product_description=product.description,
            industry=product.industry,
            materials=", ".join(product.materials),
            fit_score=product.fit_score,
            market_maturity="emerging",
            machine_lineup=machine_lineup,
        )

        try:
            resp = await _openai_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            logger.error("Opportunity scoring failed: %s", e)
            return {"score": 0, "error": str(e)}


# =============================================================================
# MACHINE FIT ANALYZER
# =============================================================================

class MachineFitAnalyzer:
    """Maps discovered products to Machinecraft machines."""

    SERIES_CAPABILITIES = {
        "PF1-X": {
            "type": "Servo positive forming",
            "thickness": "1-8mm",
            "strengths": "Precision, repeatability, automotive-grade",
            "best_for": "Automotive, medical, high-precision parts",
        },
        "PF1-C": {
            "type": "Pneumatic positive forming",
            "thickness": "1-8mm",
            "strengths": "Cost-effective, reliable, large format available",
            "best_for": "Industrial covers, agricultural, general purpose",
        },
        "PF2": {
            "type": "Open-bath positive forming",
            "thickness": "3-8mm",
            "strengths": "Very large parts, deep draw",
            "best_for": "Bath/sanitary, large panels",
        },
        "AM": {
            "type": "Multi-station thin gauge",
            "thickness": "0.2-1.5mm",
            "strengths": "High speed, multi-station, automated",
            "best_for": "Packaging, trays, thin-wall containers",
        },
        "FCS": {
            "type": "Form-cut-stack",
            "thickness": "0.2-1.5mm",
            "strengths": "Inline forming+cutting+stacking",
            "best_for": "High-volume packaging, food trays",
        },
        "IMG": {
            "type": "In-mold graining",
            "thickness": "1-4mm",
            "strengths": "Textured surfaces, Class-A finish",
            "best_for": "Automotive interiors, premium surfaces",
        },
    }

    def recommend_machines(self, product: DiscoveredProduct) -> List[str]:
        thickness = self._parse_thickness(product.typical_thickness_mm)
        size = self._parse_size(product.typical_size_mm)
        recommendations = []

        if thickness and thickness[1] <= 1.5 and product.estimated_volume in ("high", "very_high"):
            recommendations.extend(["AM series", "FCS series"])

        if thickness and thickness[1] > 1.5:
            if any(kw in product.description.lower() for kw in ("precision", "automotive", "medical", "ev", "battery")):
                recommendations.append("PF1-X series (servo)")
            recommendations.append("PF1-C series (pneumatic)")

        if size and max(size) > 2000:
            recommendations.append("PF2 series (large format)")

        if any(kw in product.description.lower() for kw in ("texture", "grain", "class-a", "interior")):
            recommendations.append("IMG series")

        if not recommendations:
            recommendations.append("PF1-C series (versatile)")

        return recommendations

    def get_machine_lineup_summary(self) -> str:
        lines = []
        for series, info in self.SERIES_CAPABILITIES.items():
            lines.append(f"- {series}: {info['type']} | Thickness: {info['thickness']} | Best for: {info['best_for']}")
        return "\n".join(lines)

    def _parse_thickness(self, s: str) -> Optional[Tuple[float, float]]:
        if not s:
            return None
        try:
            parts = s.replace("mm", "").strip().split("-")
            if len(parts) == 2:
                return (float(parts[0]), float(parts[1]))
            return (float(parts[0]), float(parts[0]))
        except (ValueError, IndexError):
            return None

    def _parse_size(self, s: str) -> Optional[Tuple[float, float]]:
        if not s:
            return None
        try:
            s_clean = s.replace("mm", "").strip()
            for sep in ("x", "X", "×"):
                if sep in s_clean:
                    parts = s_clean.split(sep)
                    return (float(parts[0].strip()), float(parts[1].strip()))
        except (ValueError, IndexError):
            pass
        return None


# =============================================================================
# PROMETHEUS — THE DISCOVERY AGENT
# =============================================================================

class Prometheus:
    """Market discovery agent that finds new vacuum forming opportunities worldwide."""

    def __init__(self):
        self.scanner = WebScanner()
        self.analyzer = AnalysisEngine()
        self.machine_fit = MachineFitAnalyzer()
        self._opportunities: Dict[str, MarketOpportunity] = {}
        self._load_existing_opportunities()

    def _load_existing_opportunities(self):
        if OPPORTUNITIES_FILE.exists():
            try:
                data = json.loads(OPPORTUNITIES_FILE.read_text())
                for opp_data in data.get("opportunities", []):
                    prod_data = opp_data.pop("product", {})
                    product = DiscoveredProduct(**prod_data)
                    opp = MarketOpportunity(product=product, **opp_data)
                    self._opportunities[opp.id] = opp
                logger.info("Loaded %d existing opportunities", len(self._opportunities))
            except Exception as e:
                logger.warning("Could not load opportunities: %s", e)

    def _save_opportunities(self):
        data = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "total": len(self._opportunities),
            "opportunities": [
                {**asdict(opp)} for opp in sorted(
                    self._opportunities.values(),
                    key=lambda o: o.score,
                    reverse=True,
                )
            ],
        }
        OPPORTUNITIES_FILE.write_text(json.dumps(data, indent=2, default=str))

    def _log_scan(self, industry: str, products_found: int, duration_s: float):
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "industry": industry,
            "products_found": products_found,
            "duration_s": round(duration_s, 2),
        }
        with open(SCAN_LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _get_existing_knowledge(self, industry: str) -> str:
        if not QDRANT_AVAILABLE:
            return ""
        try:
            result = qdrant_retrieve(f"vacuum forming applications in {industry}", top_k=3)
            if hasattr(result, "citations") and result.citations:
                return "\n".join(c.text[:500] for c in result.citations[:3])
        except Exception as e:
            logger.warning("Qdrant lookup failed: %s", e)
        return ""

    async def scan_industry(self, industry_key: str) -> IndustryScanResult:
        """Scan a single industry vertical for vacuum forming opportunities."""
        import time
        start = time.time()

        industry_info = EMERGING_INDUSTRIES.get(industry_key, {})
        industry_name = industry_info.get("name", industry_key)
        logger.info("Prometheus scanning: %s", industry_name)

        all_search_results = []
        queries = industry_info.get("search_queries", [f"{industry_key} thermoforming applications"])
        for query in queries[:3]:
            results = await self.scanner.search(query)
            all_search_results.extend(results)

        existing_knowledge = self._get_existing_knowledge(industry_name)

        products = await self.analyzer.discover_products(
            industry_name, all_search_results, existing_knowledge
        )

        for p in products:
            if not p.regions_of_demand:
                p.regions_of_demand = industry_info.get("regions", [])

        machine_lineup = self.machine_fit.get_machine_lineup_summary()
        opportunities = []
        for product in products:
            scoring = await self.analyzer.score_opportunity(product, machine_lineup)

            mc_machines = self.machine_fit.recommend_machines(product)

            scores = {
                k: scoring.get(k, 50)
                for k in ("technical_fit", "market_timing", "volume_match",
                          "competitive_gap", "revenue_potential", "strategic_value")
            }
            composite = sum(scores.values()) / len(scores) if scores else 0

            opp_id = hashlib.md5(
                f"{product.name}:{product.industry}".encode()
            ).hexdigest()[:12]

            opp = MarketOpportunity(
                id=opp_id,
                product=product,
                market_maturity=scoring.get("market_maturity", "emerging"),
                machinecraft_fit=", ".join(mc_machines),
                recommended_machines=scoring.get("recommended_machines", mc_machines),
                estimated_price_range_usd=scoring.get("estimated_price_range_usd", ""),
                competitive_landscape=scoring.get("competitive_landscape", ""),
                entry_strategy=scoring.get("entry_strategy", ""),
                score=round(composite, 1),
                score_breakdown=scores,
                discovered_at=datetime.now(timezone.utc).isoformat(),
                last_updated=datetime.now(timezone.utc).isoformat(),
            )
            opportunities.append(opp)
            self._opportunities[opp.id] = opp

        self._save_opportunities()

        duration = time.time() - start
        self._log_scan(industry_name, len(products), duration)

        return IndustryScanResult(
            industry=industry_name,
            scan_date=datetime.now(timezone.utc).isoformat(),
            products_found=products,
            opportunities=sorted(opportunities, key=lambda o: o.score, reverse=True),
            key_trends=industry_info.get("search_queries", [])[:3],
            key_players=[
                c for p in products for c in p.example_companies[:2]
            ][:10],
            raw_intelligence=f"Scanned {len(all_search_results)} web sources in {duration:.1f}s",
        )

    async def run_discovery_sweep(
        self, industries: Optional[List[str]] = None, top_n: int = 20
    ) -> Dict[str, Any]:
        """Run a full sweep across multiple industries. Returns top opportunities."""
        target_industries = industries or list(EMERGING_INDUSTRIES.keys())
        all_opportunities = []
        industry_summaries = []

        for industry_key in target_industries:
            try:
                result = await self.scan_industry(industry_key)
                all_opportunities.extend(result.opportunities)
                industry_summaries.append({
                    "industry": result.industry,
                    "products_found": len(result.products_found),
                    "top_score": result.opportunities[0].score if result.opportunities else 0,
                    "key_players": result.key_players[:5],
                })
            except Exception as e:
                logger.error("Scan failed for %s: %s", industry_key, e)
                industry_summaries.append({
                    "industry": industry_key,
                    "error": str(e),
                })

        ranked = sorted(all_opportunities, key=lambda o: o.score, reverse=True)[:top_n]

        report = {
            "sweep_date": datetime.now(timezone.utc).isoformat(),
            "industries_scanned": len(target_industries),
            "total_products_found": len(all_opportunities),
            "top_opportunities": [
                {
                    "rank": i + 1,
                    "product": opp.product.name,
                    "industry": opp.product.industry,
                    "score": opp.score,
                    "fit": opp.machinecraft_fit,
                    "machines": opp.recommended_machines,
                    "entry_strategy": opp.entry_strategy,
                }
                for i, opp in enumerate(ranked)
            ],
            "industry_summaries": industry_summaries,
        }

        report_file = DATA_DIR / f"sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.write_text(json.dumps(report, indent=2, default=str))
        logger.info("Discovery sweep complete: %d opportunities across %d industries",
                     len(all_opportunities), len(target_industries))

        return report

    async def evaluate_opportunity(
        self, product_description: str, target_region: str = ""
    ) -> MarketOpportunity:
        """Evaluate a single product idea for vacuum forming viability."""
        search_results = await self.scanner.search(
            f"{product_description} thermoforming vacuum forming"
        )

        products = await self.analyzer.discover_products(
            product_description, search_results, ""
        )

        if not products:
            products = [DiscoveredProduct(
                name=product_description,
                description=f"User-submitted idea: {product_description}",
                industry="custom",
                regions_of_demand=[target_region] if target_region else [],
            )]

        product = products[0]
        if target_region:
            product.regions_of_demand = [target_region]

        machine_lineup = self.machine_fit.get_machine_lineup_summary()
        scoring = await self.analyzer.score_opportunity(product, machine_lineup)
        mc_machines = self.machine_fit.recommend_machines(product)

        scores = {
            k: scoring.get(k, 50)
            for k in ("technical_fit", "market_timing", "volume_match",
                      "competitive_gap", "revenue_potential", "strategic_value")
        }
        composite = sum(scores.values()) / len(scores) if scores else 0

        opp_id = hashlib.md5(
            f"{product.name}:{product.industry}:{target_region}".encode()
        ).hexdigest()[:12]

        opp = MarketOpportunity(
            id=opp_id,
            product=product,
            machinecraft_fit=", ".join(mc_machines),
            recommended_machines=scoring.get("recommended_machines", mc_machines),
            estimated_price_range_usd=scoring.get("estimated_price_range_usd", ""),
            competitive_landscape=scoring.get("competitive_landscape", ""),
            entry_strategy=scoring.get("entry_strategy", ""),
            score=round(composite, 1),
            score_breakdown=scores,
            discovered_at=datetime.now(timezone.utc).isoformat(),
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

        self._opportunities[opp.id] = opp
        self._save_opportunities()
        return opp

    def get_top_opportunities(self, n: int = 10, industry: str = "") -> List[MarketOpportunity]:
        """Get top-scored opportunities, optionally filtered by industry."""
        opps = list(self._opportunities.values())
        if industry:
            opps = [o for o in opps if industry.lower() in o.product.industry.lower()]
        return sorted(opps, key=lambda o: o.score, reverse=True)[:n]

    def format_report(self, opportunities: List[MarketOpportunity]) -> str:
        """Format opportunities as a readable report for Telegram/chat."""
        if not opportunities:
            return "No opportunities found yet. Run a discovery sweep first."

        lines = ["**Prometheus Discovery Report**", f"_{len(opportunities)} opportunities ranked by score_\n"]

        for i, opp in enumerate(opportunities, 1):
            p = opp.product
            lines.append(f"**{i}. {p.name}** (Score: {opp.score}/100)")
            lines.append(f"   Industry: {p.industry}")
            lines.append(f"   Fit: {p.fit_score} | Materials: {', '.join(p.materials[:3])}")
            lines.append(f"   Why thermoforming: {p.why_vacuum_forming[:120]}")
            lines.append(f"   MC Machines: {opp.machinecraft_fit}")
            if opp.entry_strategy:
                lines.append(f"   Strategy: {opp.entry_strategy[:150]}")
            if p.example_companies:
                lines.append(f"   Target companies: {', '.join(p.example_companies[:3])}")
            lines.append("")

        return "\n".join(lines)


# =============================================================================
# SINGLETON
# =============================================================================

_prometheus_instance: Optional[Prometheus] = None


def get_prometheus() -> Prometheus:
    global _prometheus_instance
    if _prometheus_instance is None:
        _prometheus_instance = Prometheus()
    return _prometheus_instance


# =============================================================================
# SKILL ENTRY POINTS (for invocation.py)
# =============================================================================

async def discovery_scan(query: str, context: Dict[str, Any] = None) -> str:
    """Skill entry point: scan an industry or evaluate an opportunity."""
    prometheus = get_prometheus()
    context = context or {}

    query_lower = query.lower()

    if "sweep" in query_lower or "all industries" in query_lower:
        report = await prometheus.run_discovery_sweep()
        return json.dumps(report, indent=2, default=str)

    if "top" in query_lower or "best" in query_lower or "opportunities" in query_lower:
        n = 10
        industry_filter = ""
        for ind_key, ind_info in EMERGING_INDUSTRIES.items():
            if ind_key in query_lower or ind_info["name"].lower() in query_lower:
                industry_filter = ind_info["name"]
                break
        opps = prometheus.get_top_opportunities(n=n, industry=industry_filter)
        return prometheus.format_report(opps)

    matched_industry = None
    for ind_key, ind_info in EMERGING_INDUSTRIES.items():
        if ind_key in query_lower or ind_info["name"].lower() in query_lower:
            matched_industry = ind_key
            break

    if matched_industry:
        result = await prometheus.scan_industry(matched_industry)
        return prometheus.format_report(result.opportunities)

    opp = await prometheus.evaluate_opportunity(query)
    return prometheus.format_report([opp])


async def discovery_sweep(industries: Optional[List[str]] = None) -> str:
    """Run a full discovery sweep. Called by scheduler or manually."""
    prometheus = get_prometheus()
    report = await prometheus.run_discovery_sweep(industries=industries)
    return json.dumps(report, indent=2, default=str)
