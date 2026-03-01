#!/usr/bin/env python3
"""
DEEP RESEARCH ENGINE - Manus-style Multi-Step Research
======================================================

Iterative research loop that:
1. Decomposes complex questions into sub-queries
2. Searches ALL knowledge sources in parallel (Qdrant, Mem0, Neo4j, Machine DB)
3. Evaluates what's missing after each step
4. Generates follow-up queries to fill gaps
5. Synthesizes a comprehensive research report

Triggered by: /research <query> or /deep <query> on Telegram

Usage:
    from deep_research_engine import deep_research, DeepResearchResult
    
    result = deep_research(
        query="Full analysis of our European customer pipeline",
        on_progress=lambda msg: send_telegram(chat_id, msg),
        max_iterations=5,
    )
    print(result.report)
"""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("ira.deep_research")

SKILL_DIR = Path(__file__).parent
SRC_DIR = SKILL_DIR.parent
AGENT_DIR = SRC_DIR.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(SKILL_DIR))

try:
    from config import get_openai_client, get_logger, OPENAI_API_KEY, setup_import_paths
    setup_import_paths()
    logger = get_logger("ira.deep_research")
except ImportError:
    pass


@dataclass
class ResearchFinding:
    """A single finding from one search step."""
    source: str
    query_used: str
    text: str
    score: float = 0.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class ResearchStep:
    """One iteration of the research loop."""
    step_number: int
    sub_query: str
    rationale: str
    sources_searched: List[str] = field(default_factory=list)
    findings: List[ResearchFinding] = field(default_factory=list)
    gaps_identified: List[str] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class DeepResearchResult:
    """Final output of a deep research session."""
    query: str
    report: str
    steps: List[ResearchStep] = field(default_factory=list)
    total_findings: int = 0
    total_sources_searched: int = 0
    total_duration_ms: float = 0.0
    confidence: str = "medium"
    follow_up_questions: List[str] = field(default_factory=list)


# =============================================================================
# KNOWLEDGE SOURCE CONNECTORS
# =============================================================================

def _search_qdrant(query: str, top_k: int = 10) -> List[ResearchFinding]:
    """Search all Qdrant collections via the unified retriever."""
    try:
        from qdrant_retriever import retrieve
        result = retrieve(query, top_k=top_k)
        return [
            ResearchFinding(
                source="qdrant",
                query_used=query,
                text=c.text,
                score=c.score,
            )
            for c in result.citations
        ]
    except Exception as e:
        logger.warning(f"Qdrant search failed: {e}")
        return []


def _search_mem0(query: str, user_ids: Optional[List[str]] = None) -> List[ResearchFinding]:
    """Search Mem0 long-term memory across multiple knowledge stores."""
    findings = []
    if not user_ids:
        user_ids = [
            "machinecraft_knowledge", "machinecraft_pricing",
            "machinecraft_customers", "machinecraft_processes",
            "machinecraft_general", "system_ira_corrections",
        ]
    try:
        from mem0 import MemoryClient
        mc = MemoryClient(api_key=os.environ.get("MEM0_API_KEY", ""))
        for uid in user_ids:
            try:
                results = mc.search(
                    query, user_id=uid, limit=5,
                    filters={"AND": [{"user_id": uid}]}
                )
                if results:
                    for r in results:
                        mem_text = r.get("memory", "") if isinstance(r, dict) else str(r)
                        if mem_text:
                            findings.append(ResearchFinding(
                                source=f"mem0/{uid}",
                                query_used=query,
                                text=mem_text,
                                score=r.get("score", 0.5) if isinstance(r, dict) else 0.5,
                            ))
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Mem0 search failed: {e}")
    return findings


def _search_neo4j(query: str) -> List[ResearchFinding]:
    """Search Neo4j knowledge graph for relationships and entities."""
    try:
        from neo4j_store import Neo4jStore
        ns = Neo4jStore()
        results = ns.search(query, limit=10)
        return [
            ResearchFinding(
                source="neo4j",
                query_used=query,
                text=str(r),
                score=0.7,
            )
            for r in results
        ] if results else []
    except Exception as e:
        logger.debug(f"Neo4j search: {e}")
        return []


def _search_machine_db(query: str) -> List[ResearchFinding]:
    """Search the machine specs database."""
    try:
        from machine_database import MACHINE_SPECS, get_machine, find_machines_by_size
        findings = []
        q_lower = query.lower()

        for model, spec in MACHINE_SPECS.items():
            if model.lower() in q_lower or spec.series.lower() in q_lower:
                spec_text = (
                    f"{model}: {spec.series} series. "
                    f"Forming area: {spec.forming_area}. "
                    f"Max depth: {spec.max_depth}mm. "
                    f"Thickness: {spec.thickness_range}. "
                    f"Price: {spec.base_price}. "
                    f"Applications: {', '.join(spec.applications[:5])}."
                )
                findings.append(ResearchFinding(
                    source="machine_db",
                    query_used=query,
                    text=spec_text,
                    score=0.95,
                ))

        if not findings:
            for model, spec in list(MACHINE_SPECS.items())[:3]:
                for keyword in ["pf1", "pf2", "am", "img", "fcs", "atf"]:
                    if keyword in q_lower and keyword in model.lower():
                        spec_text = f"{model}: {spec.series}. Area: {spec.forming_area}. Price: {spec.base_price}."
                        findings.append(ResearchFinding(
                            source="machine_db", query_used=query,
                            text=spec_text, score=0.8,
                        ))
        return findings
    except Exception as e:
        logger.debug(f"Machine DB search: {e}")
        return []


def _search_knowledge_files(query: str) -> List[ResearchFinding]:
    """Search JSON knowledge backup files in data/knowledge/."""
    findings = []
    knowledge_dir = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "knowledge"
    if not knowledge_dir.exists():
        return findings

    q_lower = query.lower()
    keywords = [w for w in q_lower.split() if len(w) > 3]

    for json_file in knowledge_dir.glob("*.json"):
        try:
            data = json.loads(json_file.read_text())
            items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            for item in items[:50]:
                text = json.dumps(item) if isinstance(item, dict) else str(item)
                if any(kw in text.lower() for kw in keywords):
                    findings.append(ResearchFinding(
                        source=f"knowledge/{json_file.name}",
                        query_used=query,
                        text=text[:500],
                        score=0.6,
                    ))
                    if len(findings) >= 5:
                        return findings
        except Exception:
            continue
    return findings


# =============================================================================
# CORE RESEARCH LOOP
# =============================================================================

def _decompose_query(query: str) -> List[Dict[str, str]]:
    """Use LLM to break a complex query into sub-queries."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": (
                    "You are a research planner for Machinecraft Technologies (thermoforming machines). "
                    "Break the user's question into 3-6 specific sub-queries that can be searched independently. "
                    "Each sub-query should target a different aspect or knowledge source. "
                    "Return JSON array: [{\"query\": \"...\", \"rationale\": \"...\", \"sources\": [\"qdrant\", \"mem0\", \"machine_db\", \"neo4j\", \"knowledge_files\"]}]"
                ),
            }, {
                "role": "user",
                "content": query,
            }],
            max_tokens=800,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)
        sub_queries = parsed.get("sub_queries", parsed.get("queries", []))
        if isinstance(sub_queries, list) and sub_queries:
            return sub_queries
    except Exception as e:
        logger.warning(f"Query decomposition failed: {e}")

    return [
        {"query": query, "rationale": "Direct search", "sources": ["qdrant", "mem0", "machine_db"]},
    ]


def _evaluate_gaps(query: str, findings: List[ResearchFinding]) -> List[str]:
    """Use LLM to identify what's still missing from the research."""
    if not findings:
        return [query]

    context = "\n".join([f"- [{f.source}] {f.text[:200]}" for f in findings[:15]])
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": (
                    "You are evaluating research completeness for Machinecraft Technologies. "
                    "Given the original question and findings so far, identify 0-3 specific gaps "
                    "that need more research. Return JSON: {\"gaps\": [\"specific query to fill gap\"], \"sufficient\": true/false}"
                ),
            }, {
                "role": "user",
                "content": f"Question: {query}\n\nFindings so far:\n{context}",
            }],
            max_tokens=300,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.choices[0].message.content)
        if parsed.get("sufficient", False):
            return []
        return parsed.get("gaps", [])
    except Exception as e:
        logger.warning(f"Gap evaluation failed: {e}")
        return []


def _synthesize_report(query: str, all_findings: List[ResearchFinding], steps: List[ResearchStep]) -> Tuple[str, str, List[str]]:
    """Synthesize all findings into a comprehensive research report."""
    context_parts = []
    seen_texts = set()
    for f in all_findings:
        text_key = f.text[:100]
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            context_parts.append(f"[{f.source}] {f.text}")

    context = "\n\n".join(context_parts[:30])
    steps_summary = "\n".join([
        f"Step {s.step_number}: {s.sub_query} -> {len(s.findings)} findings from {', '.join(s.sources_searched)}"
        for s in steps
    ])

    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": (
                    "You are Ira, the Intelligent Revenue Assistant for Machinecraft Technologies. "
                    "You just completed a deep research session. Synthesize ALL findings into a "
                    "comprehensive, well-structured report. Use specific numbers, names, and facts "
                    "from the findings. Do NOT say 'I don't have' if the data is in the findings. "
                    "Format for Telegram (use **bold**, bullet points). "
                    "End with 2-3 follow-up questions. "
                    "Also assess confidence: high/medium/low."
                ),
            }, {
                "role": "user",
                "content": (
                    f"Original question: {query}\n\n"
                    f"Research steps:\n{steps_summary}\n\n"
                    f"All findings ({len(context_parts)} unique sources):\n{context}"
                ),
            }],
            max_tokens=2000,
            temperature=0.3,
        )
        report = response.choices[0].message.content

        confidence = "high" if len(all_findings) > 10 else "medium" if len(all_findings) > 3 else "low"
        follow_ups = []
        if "?" in report:
            lines = report.split("\n")
            for line in lines[-5:]:
                if "?" in line:
                    follow_ups.append(line.strip().lstrip("•-* "))

        return report, confidence, follow_ups
    except Exception as e:
        logger.error(f"Report synthesis failed: {e}")
        plain = "\n".join([f"• {f.text[:200]}" for f in all_findings[:10]])
        return f"Research findings for: {query}\n\n{plain}", "low", []


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def deep_research(
    query: str,
    on_progress: Optional[Callable[[str], None]] = None,
    max_iterations: int = 5,
    max_time_seconds: int = 120,
) -> DeepResearchResult:
    """
    Run a Manus-style deep research session.
    
    Args:
        query: The research question
        on_progress: Callback for progress updates (e.g., Telegram message sender)
        max_iterations: Max research iterations (each searches multiple sources)
        max_time_seconds: Hard time limit
    """
    start_time = time.time()
    all_findings: List[ResearchFinding] = []
    steps: List[ResearchStep] = []
    sources_searched_total: set = set()

    def progress(msg: str):
        if on_progress:
            try:
                on_progress(msg)
            except Exception:
                pass
        logger.info(f"[DeepResearch] {msg}")

    progress(f"🔬 Starting deep research: \"{query[:80]}...\"")

    # Step 1: Decompose the query
    progress("📋 Step 1: Decomposing query into sub-questions...")
    sub_queries = _decompose_query(query)
    progress(f"   Found {len(sub_queries)} research angles")

    # Step 2: Execute research iterations
    iteration = 0
    pending_queries = list(sub_queries)

    while pending_queries and iteration < max_iterations:
        elapsed = time.time() - start_time
        if elapsed > max_time_seconds:
            progress(f"⏱️ Time limit reached ({int(elapsed)}s)")
            break

        iteration += 1
        sq = pending_queries.pop(0)
        sub_q = sq.get("query", sq) if isinstance(sq, dict) else str(sq)
        rationale = sq.get("rationale", "") if isinstance(sq, dict) else ""
        target_sources = sq.get("sources", ["qdrant", "mem0", "machine_db"]) if isinstance(sq, dict) else ["qdrant", "mem0"]

        step_start = time.time()
        progress(f"🔍 Step {iteration + 1}: Searching \"{sub_q[:60]}...\"")

        step_findings: List[ResearchFinding] = []
        step_sources: List[str] = []

        if "qdrant" in target_sources:
            results = _search_qdrant(sub_q, top_k=8)
            step_findings.extend(results)
            step_sources.append(f"qdrant({len(results)})")

        if "mem0" in target_sources:
            results = _search_mem0(sub_q)
            step_findings.extend(results)
            step_sources.append(f"mem0({len(results)})")

        if "machine_db" in target_sources:
            results = _search_machine_db(sub_q)
            step_findings.extend(results)
            step_sources.append(f"machine_db({len(results)})")

        if "neo4j" in target_sources:
            results = _search_neo4j(sub_q)
            step_findings.extend(results)
            step_sources.append(f"neo4j({len(results)})")

        if "knowledge_files" in target_sources:
            results = _search_knowledge_files(sub_q)
            step_findings.extend(results)
            step_sources.append(f"files({len(results)})")

        step_duration = (time.time() - step_start) * 1000
        sources_searched_total.update(step_sources)

        gaps = []
        if iteration < max_iterations and not pending_queries:
            gaps = _evaluate_gaps(query, all_findings + step_findings)
            for gap in gaps:
                pending_queries.append({"query": gap, "rationale": "Fill gap", "sources": ["qdrant", "mem0"]})

        step = ResearchStep(
            step_number=iteration,
            sub_query=sub_q,
            rationale=rationale,
            sources_searched=step_sources,
            findings=step_findings,
            gaps_identified=gaps,
            duration_ms=step_duration,
        )
        steps.append(step)
        all_findings.extend(step_findings)

        progress(f"   Found {len(step_findings)} results from {', '.join(step_sources)}")
        if gaps:
            progress(f"   📝 {len(gaps)} gaps identified, queuing follow-up searches")

    # Step 3: Synthesize report
    elapsed = time.time() - start_time
    progress(f"📝 Synthesizing report from {len(all_findings)} findings across {iteration} steps...")

    report, confidence, follow_ups = _synthesize_report(query, all_findings, steps)

    total_duration = (time.time() - start_time) * 1000
    progress(f"✅ Research complete ({total_duration/1000:.1f}s, {len(all_findings)} findings, confidence: {confidence})")

    return DeepResearchResult(
        query=query,
        report=report,
        steps=steps,
        total_findings=len(all_findings),
        total_sources_searched=len(sources_searched_total),
        total_duration_ms=total_duration,
        confidence=confidence,
        follow_up_questions=follow_ups,
    )
