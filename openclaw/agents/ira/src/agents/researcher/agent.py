"""
Clio - The Researcher (OpenClaw Native)

The meticulous historian. Insatiably curious and rigorously thorough.
She retrieves all knowledge from every source (Qdrant, Mem0, Machine DB, Web)
and never misses a detail.

This module provides research functions that can be invoked by the LLM
through OpenClaw's native tool system.
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.clio")

# Knowledge base imports - these connect Clio to the real data
_qdrant_retrieve = None
_mem0_service = None
_neo4j_store = None
_knowledge_json_cache = None
_KNOWLEDGE_SOURCES_INITIALIZED = False

def _init_knowledge_sources():
    """Lazy-init connections to Qdrant, Mem0, and Neo4j."""
    global _qdrant_retrieve, _mem0_service, _neo4j_store, _KNOWLEDGE_SOURCES_INITIALIZED
    if _KNOWLEDGE_SOURCES_INITIALIZED:
        return
    _KNOWLEDGE_SOURCES_INITIALIZED = True

    try:
        from openclaw.agents.ira.src.brain.qdrant_retriever import retrieve
        _qdrant_retrieve = retrieve
        logger.info("Clio: Qdrant retriever connected")
    except ImportError:
        try:
            import sys
            agent_dir = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(agent_dir))
            from src.brain.qdrant_retriever import retrieve
            _qdrant_retrieve = retrieve
            logger.info("Clio: Qdrant retriever connected (relative import)")
        except ImportError:
            logger.warning("Clio: Qdrant retriever unavailable - using fallback")

    try:
        from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
        _mem0_service = get_mem0_service()
        logger.info("Clio: Mem0 memory connected")
    except ImportError:
        try:
            from src.memory.mem0_memory import get_mem0_service
            _mem0_service = get_mem0_service()
            logger.info("Clio: Mem0 memory connected (relative import)")
        except ImportError:
            logger.warning("Clio: Mem0 unavailable - using fallback")
    except Exception as e:
        logger.warning(f"Clio: Mem0 init failed: {e}")

    try:
        from openclaw.agents.ira.src.brain.neo4j_store import get_neo4j_store
        store = get_neo4j_store()
        if store.is_connected():
            _neo4j_store = store
            logger.info("Clio: Neo4j knowledge graph connected")
        else:
            logger.warning("Clio: Neo4j not reachable")
    except ImportError:
        try:
            from src.brain.neo4j_store import get_neo4j_store
            store = get_neo4j_store()
            if store.is_connected():
                _neo4j_store = store
                logger.info("Clio: Neo4j knowledge graph connected (relative import)")
        except ImportError:
            logger.warning("Clio: Neo4j store unavailable")
    except Exception as e:
        logger.warning(f"Clio: Neo4j init failed: {e}")

MEM0_KNOWLEDGE_USER_IDS = [
    "machinecraft_knowledge",
    "machinecraft_pricing",
    "machinecraft_customers",
    "machinecraft_processes",
    "machinecraft_applications",
    "machinecraft_general",
]


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ResearchResult:
    """Result from a research query."""
    query: str
    findings: List[Dict]
    sources: List[str]
    confidence: float
    processing_time: float


# =============================================================================
# PATTERN MATCHING
# =============================================================================

# Machine identification patterns
MACHINE_PATTERNS = [
    (r'(PF1)[-\s]?([A-Z])[-\s]?(\d{4})', lambda m: f"{m[0]}-{m[1]}-{m[2]}"),
    (r'(PF2)[-\s]?([A-Z])?[-\s]?(\d{4})', lambda m: f"{m[0]}-{m[1]}-{m[2]}"),
    (r'(AM)[-\s]?([A-Z])[-\s]?(\d{4})', lambda m: f"{m[0]}-{m[1]}-{m[2]}"),
    (r'(AM)[-\s]?(\d{4})', lambda m: f"{m[0]}-{m[1]}"),
    (r'(ATF)[-\s]?(\d+)', lambda m: f"{m[0]}-{m[1]}"),
    (r'(IMG)[-\s]?(\d{4})', lambda m: f"{m[0]}-{m[1]}"),
    (r'(FCS)[-\s]?(\d+)', lambda m: f"{m[0]}-{m[1]}"),
]

# Intent patterns
INTENT_PATTERNS = {
    "pricing": [r"price|cost|budget|quote|how much|₹|rs\.?|lakhs?|crores?"],
    "specs": [r"specification|spec|dimension|size|capacity|power|forming area"],
    "comparison": [r"compare|versus|vs\.?|difference|better|which one"],
    "recommendation": [r"recommend|suggest|suitable|best|ideal|right machine"],
}


# =============================================================================
# CORE RESEARCH FUNCTIONS
# =============================================================================

async def research(query: str, context: Optional[Dict] = None) -> str:
    """
    Main research function - can be called as an OpenClaw tool.
    
    Searches all available sources and synthesizes findings.
    
    Args:
        query: The search query or question
        context: Optional context including user_id, channel, intent
        
    Returns:
        Synthesized research findings as a string
    """
    context = context or {}
    start_time = time.time()
    
    logger.info({
        "agent": "Clio",
        "event": "research_started",
        "query_preview": query[:100]
    })
    
    # Extract what we're looking for
    clean_query = _extract_query(query)
    intent = _detect_intent(clean_query)
    machines = _extract_machines(clean_query)
    
    # Search all sources in parallel
    results = await _parallel_search(clean_query, intent, machines, context)
    
    # Synthesize findings
    response = _synthesize_findings(clean_query, results, intent)
    
    processing_time = time.time() - start_time
    
    logger.info({
        "agent": "Clio",
        "event": "research_complete",
        "results_found": len(results),
        "processing_time": round(processing_time, 2)
    })
    
    return response


def _extract_query(task: str) -> str:
    """Extract the actual query from a task description."""
    prefixes = ["Research:", "Recall memories for", "Find:", "Look up:", "Search for:"]
    query = task
    for prefix in prefixes:
        if task.startswith(prefix):
            query = task[len(prefix):].strip()
            break
    return query


def _detect_intent(query: str) -> str:
    """Detect the intent of the query."""
    query_lower = query.lower()
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                return intent
    return "general"


def _extract_machines(query: str) -> List[str]:
    """Extract machine model numbers from the query."""
    machines = []
    for pattern, formatter in MACHINE_PATTERNS:
        matches = re.findall(pattern, query, re.IGNORECASE)
        for match in matches:
            model = formatter(match).upper()
            if model not in machines:
                machines.append(model)
    return machines


async def _parallel_search(
    query: str,
    intent: str,
    machines: List[str],
    context: Dict
) -> List[Dict]:
    """Search all sources in parallel: Machine DB, Qdrant, Mem0, Neo4j."""
    results = []

    tasks = [
        _search_machine_db(machines, intent),
        _search_knowledge_base(query),
        _search_memories(query, context.get("user_id", "unknown")),
        _search_graph(query, machines),
    ]

    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for result in completed:
        if isinstance(result, Exception):
            logger.warning(f"Search task failed: {result}")
        elif result:
            if isinstance(result, list):
                results.extend(result)
            else:
                results.append(result)

    return results


# =============================================================================
# DATA SOURCES
# =============================================================================

_MACHINE_DATABASE: Optional[Dict] = None
_MACHINE_SPECS_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "brain" / "machine_specs.json"


def _get_machine_database() -> Dict:
    """Load machine specs from the canonical source of truth (machine_specs.json).

    Cached after first load. Falls back to an empty dict if the file is missing
    so callers never crash.
    """
    global _MACHINE_DATABASE
    if _MACHINE_DATABASE is not None:
        return _MACHINE_DATABASE

    try:
        raw = json.loads(_MACHINE_SPECS_PATH.read_text())
        db: Dict[str, Dict] = {}
        for model_key, spec in raw.items():
            entry: Dict[str, Any] = {
                "model": spec.get("model", model_key),
                "series": spec.get("series", ""),
                "variant": spec.get("variant", "standard"),
                "forming_area": spec.get("forming_area_mm", ""),
                "max_draw_depth_mm": spec.get("max_draw_depth_mm"),
                "max_sheet_thickness_mm": spec.get("max_sheet_thickness_mm"),
                "min_sheet_thickness_mm": spec.get("min_sheet_thickness_mm"),
                "heater_type": spec.get("heater_type", ""),
                "applications": spec.get("applications", []),
                "features": spec.get("features", []),
                "source": "Machine Database (machine_specs.json)",
            }
            price_inr = spec.get("price_inr", 0)
            if price_inr:
                entry["price_inr"] = price_inr
            price_usd = spec.get("price_usd", 0)
            if price_usd:
                entry["price_usd"] = price_usd

            if spec.get("series") == "AM":
                entry["note"] = "⚠️ AM series: materials ≤1.5mm thickness ONLY"

            db[model_key.upper()] = entry
        _MACHINE_DATABASE = db
        logger.info("Clio: Loaded %d machines from machine_specs.json", len(db))
    except FileNotFoundError:
        logger.warning("Clio: machine_specs.json not found at %s — machine DB empty", _MACHINE_SPECS_PATH)
        _MACHINE_DATABASE = {}
    except Exception as e:
        logger.error("Clio: Failed to load machine_specs.json: %s", e)
        _MACHINE_DATABASE = {}

    return _MACHINE_DATABASE


async def _search_machine_db(machines: List[str], intent: str) -> List[Dict]:
    """Search the machine database for specifications."""
    db = _get_machine_database()
    results = []

    for machine in machines:
        spec = db.get(machine.upper())
        if spec:
            results.append({
                "source": "Machine Database",
                "type": "machine_specs",
                "content": spec,
                "relevance": 0.95,
            })

    if not machines and intent in ["specs", "recommendation", "pricing"]:
        series_set = sorted({s.get("series", "?") for s in db.values() if s.get("series")})
        results.append({
            "source": "Machine Database",
            "type": "general_info",
            "content": {
                "total_models": len(db),
                "available_series": series_set,
                "series_notes": [
                    "PF1/PF2 - Positive Forming (1-10mm thickness)",
                    "AM - Multi-station Automatic (≤1.5mm ONLY)",
                    "ATF - Automatic Thermoforming",
                    "IMG - In-mold Graining",
                    "FCS - Form-Cut-Stack",
                ],
            },
            "relevance": 0.7,
        })

    return results


# In-memory cache with TTL and max-size eviction
_cache: Dict[str, tuple] = {}
_cache_ttl = 300  # 5 minutes
_CACHE_MAX_SIZE = 200


def _cache_evict():
    """Evict oldest entries when cache exceeds max size."""
    global _cache
    if len(_cache) <= _CACHE_MAX_SIZE:
        return
    sorted_keys = sorted(_cache, key=lambda k: _cache[k][1])
    for key in sorted_keys[:len(_cache) - _CACHE_MAX_SIZE]:
        del _cache[key]


def invalidate_cache(entity: str = "") -> None:
    """Clear research cache, optionally only for queries mentioning an entity."""
    global _cache
    if not entity:
        _cache.clear()
        return
    keys_to_remove = [k for k in _cache if entity.lower() in k.lower()]
    for k in keys_to_remove:
        del _cache[k]


async def _search_knowledge_base(query: str) -> List[Dict]:
    """Search the Qdrant vector knowledge base for ingested documents."""
    cache_key = f"kb:{hashlib.md5(query.encode()).hexdigest()}"
    if cache_key in _cache:
        cached, timestamp = _cache[cache_key]
        if time.time() - timestamp < _cache_ttl:
            return cached
        else:
            del _cache[cache_key]

    _init_knowledge_sources()
    results = []

    if _qdrant_retrieve is not None:
        try:
            retrieval = _qdrant_retrieve(query, top_k=15, min_score=0.15)
            for citation in retrieval.citations:
                results.append({
                    "source": f"Knowledge Base ({citation.filename})",
                    "type": "knowledge",
                    "content": citation.text,
                    "relevance": citation.score,
                    "doc_type": citation.doc_type,
                    "filename": citation.filename,
                    "machines": citation.machines,
                })
        except Exception as e:
            logger.warning(f"Clio: Qdrant search failed: {e}")

    if not results:
        results = _search_json_knowledge_fallback(query)

    _cache[cache_key] = (results, time.time())
    _cache_evict()
    return results


async def _search_memories(query: str, user_id: str) -> List[Dict]:
    """Search Mem0 for user-specific AND knowledge-base memories."""
    _init_knowledge_sources()
    results = []

    if _mem0_service is None:
        return results

    user_ids_to_search = [user_id] + MEM0_KNOWLEDGE_USER_IDS

    for uid in user_ids_to_search:
        try:
            memories = _mem0_service.search(query, user_id=uid, limit=5)
            for mem in memories:
                if mem.score < 0.3:
                    continue
                results.append({
                    "source": f"Memory ({uid})",
                    "type": "user_memory" if uid == user_id else "knowledge_memory",
                    "content": mem.memory,
                    "relevance": mem.score,
                    "memory_id": mem.id,
                })
        except Exception as e:
            logger.warning(f"Clio: Mem0 search failed for {uid}: {e}")

    results.sort(key=lambda r: r.get("relevance", 0), reverse=True)
    return results[:15]


async def _search_graph(query: str, machines: List[str]) -> List[Dict]:
    """Search Neo4j knowledge graph for entity relationships and context."""
    _init_knowledge_sources()
    results = []

    if _neo4j_store is None:
        return results

    entities_to_search = list(machines)
    entity_patterns = [
        (r'(PF1|PF2|AM|ATF|IMG|FCS)[-\s]?[A-Z]?[-\s]?\d+', lambda m: m.group(0).upper()),
        (r'\b(Machinecraft|FRIMO|Formpack|Motherson|Tata|Mahindra)\b', lambda m: m.group(0)),
    ]
    for pattern, extractor in entity_patterns:
        for match in re.finditer(pattern, query, re.IGNORECASE):
            entity = extractor(match)
            if entity not in entities_to_search:
                entities_to_search.append(entity)

    for entity in entities_to_search[:5]:
        try:
            related = _neo4j_store.get_related_entities(entity, depth=2, limit=10)
            for item in related:
                results.append({
                    "source": f"Knowledge Graph (related to {entity})",
                    "type": "graph_relationship",
                    "content": f"{entity} → {', '.join(item.get('relationship_types', []))} → {item['entity']} (distance: {item['distance']})",
                    "relevance": max(0.7 - (item.get("distance", 1) - 1) * 0.15, 0.3),
                    "entity": entity,
                    "related_entity": item["entity"],
                })
        except Exception as e:
            logger.warning(f"Clio: Neo4j related entities failed for {entity}: {e}")

        try:
            knowledge = _neo4j_store.get_entity_knowledge(entity)
            for item in knowledge[:5]:
                text = item.get("text") or item.get("summary") or ""
                if not text:
                    continue
                results.append({
                    "source": f"Knowledge Graph ({item.get('source_file', entity)})",
                    "type": "graph_knowledge",
                    "content": text[:1500],
                    "relevance": 0.85,
                    "entity": entity,
                    "knowledge_type": item.get("knowledge_type", "general"),
                })
        except Exception as e:
            logger.warning(f"Clio: Neo4j entity knowledge failed for {entity}: {e}")

    if entities_to_search:
        try:
            expanded = _neo4j_store.expand_query_with_graph(entities_to_search[:3], depth=1)
            new_entities = [e for e in expanded if e not in entities_to_search]
            if new_entities:
                results.append({
                    "source": "Knowledge Graph (expanded entities)",
                    "type": "graph_expansion",
                    "content": f"Related entities discovered: {', '.join(new_entities[:10])}",
                    "relevance": 0.6,
                })
        except Exception as e:
            logger.warning(f"Clio: Neo4j query expansion failed: {e}")

    return results


def _search_json_knowledge_fallback(query: str) -> List[Dict]:
    """Fallback: search local JSON knowledge files when Qdrant is unavailable."""
    global _knowledge_json_cache

    knowledge_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "knowledge"
    if not knowledge_dir.exists():
        return []

    if _knowledge_json_cache is None:
        _knowledge_json_cache = []
        for json_file in knowledge_dir.glob("*.json"):
            if json_file.name in ("ingested_hashes.json", "consolidation_log.json",
                                   "migration_log.json", "zenkai_log.json",
                                   "fusion_log.json", "transformations.json"):
                continue
            try:
                data = json.loads(json_file.read_text())
                if isinstance(data, list):
                    for item in data:
                        text = item.get("text", item.get("content", ""))
                        if text:
                            _knowledge_json_cache.append({
                                "text": text,
                                "source": json_file.name,
                                "entity": item.get("entity", ""),
                            })
                elif isinstance(data, dict):
                    for key, val in data.items():
                        if isinstance(val, str) and len(val) > 20:
                            _knowledge_json_cache.append({
                                "text": val,
                                "source": json_file.name,
                                "entity": key,
                            })
            except Exception:
                continue

    query_terms = set(query.lower().split())
    results = []
    for item in _knowledge_json_cache:
        text_lower = item["text"].lower()
        overlap = sum(1 for t in query_terms if t in text_lower)
        if overlap >= 2 or (len(query_terms) == 1 and overlap == 1):
            results.append({
                "source": f"Knowledge Base ({item['source']})",
                "type": "knowledge",
                "content": item["text"][:1500],
                "relevance": min(0.5 + overlap * 0.1, 0.9),
            })

    results.sort(key=lambda r: r["relevance"], reverse=True)
    return results[:10]


def _synthesize_findings(query: str, results: List[Dict], intent: str) -> str:
    """Synthesize research findings into a coherent response."""
    # Check for unknown product queries
    unknown_product_patterns = [
        r'x[-\s]?\d+',  # X-1, X-2, etc.
        r'prototype',
        r'unreleased',
        r'upcoming',
        r'new\s+model',
        r'(?:beta|alpha)\s+version',
    ]
    query_lower = query.lower()
    for pattern in unknown_product_patterns:
        if re.search(pattern, query_lower):
            return (
                "I don't have information about that product in my database. "
                "It may be unreleased, confidential, or not a Machinecraft product. "
                "I can only provide verified information about our current product lines:\n"
                "- **PF1/PF2 Series** - Positive Forming\n"
                "- **AM Series** - Multi-station Automatic (≤1.5mm)\n"
                "- **ATF Series** - Automatic Thermoforming\n"
                "- **IMG Series** - In-mold Graining\n"
                "- **FCS Series** - Form-Cut-Stack\n\n"
                "Would you like details about any of these instead?"
            )
    
    # Check for vague/general questions - provide an overview
    vague_patterns = ['tell me about', 'what do you', 'about your', 'your machine', 'show me']
    is_vague = any(p in query_lower for p in vague_patterns)
    
    if not results and is_vague:
        return (
            "## Machinecraft Thermoforming Machines\n\n"
            "We manufacture a complete range of thermoforming equipment:\n\n"
            "**PF1/PF2 Series** - Positive Forming machines for automotive interiors, "
            "door panels, and dashboards. Handles materials 1-10mm thick.\n\n"
            "**AM Series** - Multi-station automatic machines for thin gauge packaging "
            "and high-volume production (≤1.5mm materials ONLY).\n\n"
            "**ATF Series** - Automatic thermoforming for high-volume food containers "
            "and packaging applications.\n\n"
            "**IMG Series** - In-mold graining for premium textured surfaces and "
            "automotive interiors.\n\n"
            "**FCS Series** - Form-Cut-Stack systems for packaging and "
            "disposables.\n\n"
            "What specific application or requirement can I help you with?"
        )
    
    if not results:
        return f"I searched but couldn't find specific information about: {query}"
    
    machine_specs = [r for r in results if r.get("type") == "machine_specs"]
    knowledge = [r for r in results if r.get("type") in ("knowledge", "graph_knowledge")]
    memories = [r for r in results if r.get("type") in ("user_memory", "knowledge_memory")]
    general = [r for r in results if r.get("type") == "general_info"]
    graph_rels = [r for r in results if r.get("type") in ("graph_relationship", "graph_expansion")]
    
    parts = []
    
    # Machine specifications (highest priority)
    for spec in machine_specs:
        content = spec["content"]
        if isinstance(content, dict):
            model = content.get('model', 'Machine')
            parts.append(f"\n## {model} [SOURCE: Machine Database]")
            for key, value in content.items():
                if key not in ["model", "source"]:
                    label = key.replace('_', ' ').title()
                    if isinstance(value, list):
                        parts.append(f"- **{label}:** {', '.join(value)}")
                    else:
                        parts.append(f"- **{label}:** {value}")
    
    # General info
    for g in general:
        content = g["content"]
        if isinstance(content, dict) and "available_series" in content:
            parts.append("\n## Available Machine Series")
            for series in content["available_series"]:
                parts.append(f"- {series}")
    
    # Knowledge context (from Qdrant retrieval and JSON fallback)
    seen_content = set()
    for k in knowledge[:10]:
        content = k.get("content", "")
        content_key = content[:100]
        if content_key in seen_content:
            continue
        seen_content.add(content_key)
        parts.append(f"\n[{k['source']}] {content[:1500]}")

    # Graph relationships (from Neo4j)
    if graph_rels:
        parts.append("\n## Entity Relationships")
        for g in graph_rels[:8]:
            parts.append(f"- {g['content']}")

    # Memory context (from Mem0 - user and knowledge memories)
    for m in memories[:8]:
        parts.append(f"\n[{m.get('source', 'Memory')}] {m['content']}")

    if parts:
        return "\n".join(parts)

    return f"Research complete for: {query}"


# =============================================================================
# CONVENIENCE FUNCTIONS FOR OPENCLAW TOOLS
# =============================================================================

def get_machine_specs(model: str) -> Optional[Dict]:
    """
    Get specifications for a specific machine model.
    
    Can be exposed as an OpenClaw tool.
    
    Args:
        model: Machine model number (e.g., "PF1-C-2015")
        
    Returns:
        Machine specifications dict or None
    """
    model_upper = model.upper().strip()
    return _get_machine_database().get(model_upper)


def list_machines(series: Optional[str] = None) -> List[Dict]:
    """
    List available machines, optionally filtered by series.
    
    Args:
        series: Optional series filter (PF1, AM, ATF, etc.)
        
    Returns:
        List of machine summaries
    """
    db = _get_machine_database()
    machines = []
    for model, specs in db.items():
        if series is None or specs.get("series", "").upper() == series.upper():
            machines.append({
                "model": model,
                "series": specs.get("series"),
                "variant": specs.get("variant"),
                "forming_area": specs.get("forming_area"),
            })
    return machines


def check_thickness_compatibility(thickness_mm: float) -> Dict[str, Any]:
    """
    Check which machine series are compatible with a given material thickness.
    
    CRITICAL: This enforces the AM series ≤1.5mm rule.
    
    Args:
        thickness_mm: Material thickness in millimeters
        
    Returns:
        Compatibility information with recommendations
    """
    result = {
        "thickness_mm": thickness_mm,
        "compatible_series": [],
        "incompatible_series": [],
        "recommendation": "",
        "warnings": []
    }
    
    if thickness_mm <= 1.5:
        result["compatible_series"] = ["PF1", "PF2", "AM", "ATF", "IMG", "FCS"]
        result["recommendation"] = "All series are compatible with this thickness."
    elif thickness_mm <= 10:
        result["compatible_series"] = ["PF1", "PF2"]
        result["incompatible_series"] = ["AM"]
        result["warnings"].append(
            "⚠️ AM series is NOT suitable - it only handles materials ≤1.5mm thick."
        )
        result["recommendation"] = f"For {thickness_mm}mm thickness, use PF1 or PF2 series."
    else:
        result["compatible_series"] = ["PF2"]  # Large format only
        result["incompatible_series"] = ["AM"]
        result["warnings"].append(
            "⚠️ AM series is NOT suitable - it only handles materials ≤1.5mm thick."
        )
        result["recommendation"] = f"For {thickness_mm}mm thickness, consider PF2 large format series."
    
    return result
