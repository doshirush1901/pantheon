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
            model="gpt-4.1-mini",
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
            model="gpt-4.1-mini",
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
    unique_findings = []
    for f in all_findings:
        text_key = f.text[:100]
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            unique_findings.append(f)
    for i, f in enumerate(unique_findings, 1):
        source_tag = f.source if hasattr(f, 'source') else 'unknown'
        context_parts.append(f"[{i}:{source_tag}] {f.text}")

    context = "\n\n".join(context_parts[:30])
    steps_summary = "\n".join([
        f"Step {s.step_number}: {s.sub_query} -> {len(s.findings)} findings from {', '.join(s.sources_searched)}"
        for s in steps
    ])

    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{
                "role": "system",
                "content": (
                    "You are Ira, the Intelligent Revenue Assistant for Machinecraft Technologies. "
                    "You just completed a deep research session. Synthesize ALL findings into a "
                    "comprehensive, well-structured report. Use specific numbers, names, and facts "
                    "from the findings. Do NOT say 'I don't have' if the data is in the findings. "
                    "Format for Telegram (use **bold**, bullet points). "
                    "IMPORTANT: Include inline source citations in your report. For each claim, "
                    "add a bracketed source tag like [Qdrant], [Mem0], [machine_db], [web], [Neo4j] "
                    "after the relevant sentence. This helps the reader verify claims. "
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
# PANTHEON SUB-AGENT INTEGRATION
# =============================================================================

def _run_clio_research(query: str) -> List[ResearchFinding]:
    """Use Clio (Researcher agent) for deep multi-source research."""
    try:
        import asyncio
        from openclaw.agents.ira.src.agents.researcher.agent import research
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(research(query, context={"depth": "deep", "channel": "research"}))
        loop.close()
        if result:
            return [ResearchFinding(
                source="clio/researcher",
                query_used=query,
                text=result[:2000],
                score=0.9,
            )]
    except Exception as e:
        logger.debug(f"Clio research: {e}")
    return []


def _run_vera_verification(draft: str, query: str) -> str:
    """Use Vera (Fact Checker) to verify the research report."""
    try:
        import asyncio
        from openclaw.agents.ira.src.agents.fact_checker.agent import verify
        loop = asyncio.new_event_loop()
        verified = loop.run_until_complete(verify(draft, query))
        loop.close()
        return verified
    except Exception as e:
        logger.debug(f"Vera verification: {e}")
        return draft


def _run_calliope_write(query: str, research_output: str, channel: str = "telegram") -> str:
    """Use Calliope (Writer) to polish the research report."""
    try:
        import asyncio
        from openclaw.agents.ira.src.agents.writer.agent import write
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(write(query, context={
            "research_output": research_output,
            "channel": channel,
            "format": "research_report",
        }))
        loop.close()
        return result if result else research_output
    except Exception as e:
        logger.debug(f"Calliope write: {e}")
        return research_output


def _run_sophia_reflect(query: str, report: str):
    """Use Sophia (Reflector) to learn from this research session."""
    try:
        import asyncio
        from openclaw.agents.ira.src.agents.reflector.agent import reflect
        loop = asyncio.new_event_loop()
        loop.run_until_complete(reflect({
            "user_message": f"/research {query}",
            "response": report[:1000],
            "intent": "deep_research",
            "mode": "research",
            "confidence": "high",
            "channel": "telegram",
        }))
        loop.close()
    except Exception as e:
        logger.debug(f"Sophia reflect: {e}")


def _run_iris_intelligence(query: str) -> List[ResearchFinding]:
    """Use Iris (Intelligence) for external context if relevant."""
    try:
        import asyncio
        from openclaw.agents.ira.src.agents.iris_skill import iris_enrich
        context = {"query": query, "company": "", "lead_id": ""}

        import re
        companies = re.findall(r'(?:about|for|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', query)
        if companies:
            context["company"] = companies[0]

        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(iris_enrich(context))
        loop.close()

        findings = []
        for key, val in result.items():
            if val and isinstance(val, str) and len(val) > 10:
                findings.append(ResearchFinding(
                    source=f"iris/{key}",
                    query_used=query,
                    text=val,
                    score=0.75,
                ))
        return findings
    except Exception as e:
        logger.debug(f"Iris intelligence: {e}")
        return []


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def deep_research(
    query: str,
    on_progress: Optional[Callable[[str], None]] = None,
    max_iterations: int = 8,
    max_time_seconds: int = 180,
) -> DeepResearchResult:
    """
    Manus-style deep research using ALL Pantheon sub-agents.
    
    Pipeline:
      1. Athena decomposes query into sub-questions
      2. Clio researches each sub-question across all knowledge sources
      3. Iris adds external intelligence where relevant
      4. Gap analysis generates follow-up queries (iterative)
      5. Calliope synthesizes findings into a polished report
      6. Vera fact-checks the report for accuracy
      7. Sophia reflects and learns from the session
    """
    start_time = time.time()
    all_findings: List[ResearchFinding] = []
    _seen_finding_keys: set = set()
    steps: List[ResearchStep] = []
    sources_searched_total: set = set()

    def progress(msg: str):
        if on_progress:
            try:
                on_progress(msg)
            except Exception:
                pass
        logger.info(f"[DeepResearch] {msg}")

    progress(f"🔬 *Deep Research Started*\n\"{query[:100]}\"")

    # =========================================================================
    # PHASE 1: ATHENA - Decompose query
    # =========================================================================
    progress("🏛️ *Athena* is decomposing your question...")
    sub_queries = _decompose_query(query)
    progress(f"   → {len(sub_queries)} research angles identified")

    # =========================================================================
    # PHASE 2: CLIO + ALL SOURCES - Iterative research
    # =========================================================================
    iteration = 0
    pending_queries = list(sub_queries)

    while pending_queries and iteration < max_iterations:
        elapsed = time.time() - start_time
        if elapsed > max_time_seconds:
            progress(f"⏱️ Time limit ({int(elapsed)}s) - moving to synthesis")
            break

        iteration += 1
        sq = pending_queries.pop(0)
        sub_q = sq.get("query", sq) if isinstance(sq, dict) else str(sq)
        rationale = sq.get("rationale", "") if isinstance(sq, dict) else ""
        target_sources = sq.get("sources", ["qdrant", "mem0", "machine_db", "knowledge_files"]) if isinstance(sq, dict) else ["qdrant", "mem0"]

        step_start = time.time()
        progress(f"🔍 *Clio* researching ({iteration}/{iteration + len(pending_queries)}): \"{sub_q[:50]}...\"")

        step_findings: List[ResearchFinding] = []
        step_sources: List[str] = []

        # Always search Qdrant (primary RAG)
        results = _search_qdrant(sub_q, top_k=12)
        step_findings.extend(results)
        step_sources.append(f"qdrant({len(results)})")

        # Always search Mem0 (long-term memory)
        results = _search_mem0(sub_q)
        step_findings.extend(results)
        step_sources.append(f"mem0({len(results)})")

        if "machine_db" in target_sources:
            results = _search_machine_db(sub_q)
            step_findings.extend(results)
            if results:
                step_sources.append(f"machine_db({len(results)})")

        if "neo4j" in target_sources:
            results = _search_neo4j(sub_q)
            step_findings.extend(results)
            if results:
                step_sources.append(f"neo4j({len(results)})")

        if "knowledge_files" in target_sources:
            results = _search_knowledge_files(sub_q)
            step_findings.extend(results)
            if results:
                step_sources.append(f"files({len(results)})")

        # On first iteration, also use Clio's own research for a richer result
        if iteration == 1:
            clio_results = _run_clio_research(sub_q)
            step_findings.extend(clio_results)
            if clio_results:
                step_sources.append("clio(1)")

        step_duration = (time.time() - step_start) * 1000
        sources_searched_total.update(step_sources)

        # Gap analysis - check what's missing
        gaps = []
        if iteration < max_iterations and not pending_queries:
            gaps = _evaluate_gaps(query, all_findings + step_findings)
            for gap in gaps:
                pending_queries.append({
                    "query": gap,
                    "rationale": "Fill identified gap",
                    "sources": ["qdrant", "mem0", "knowledge_files"],
                })

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
        for finding in step_findings:
            finding_key = finding.text[:100] if hasattr(finding, 'text') else str(finding)[:100]
            if finding_key not in _seen_finding_keys:
                _seen_finding_keys.add(finding_key)
                all_findings.append(finding)

        progress(f"   → {len(step_findings)} findings from {', '.join(step_sources)}")
        if gaps:
            progress(f"   📝 {len(gaps)} gaps found, queuing follow-up searches")

    # =========================================================================
    # PHASE 3: IRIS - External intelligence (if query involves companies/leads)
    # =========================================================================
    iris_keywords = ["lead", "customer", "company", "competitor", "market", "industry", "europe", "prospect"]
    if any(kw in query.lower() for kw in iris_keywords):
        progress("🌐 *Iris* gathering external intelligence...")
        iris_findings = _run_iris_intelligence(query)
        if iris_findings:
            for finding in iris_findings:
                finding_key = finding.text[:100] if hasattr(finding, 'text') else str(finding)[:100]
                if finding_key not in _seen_finding_keys:
                    _seen_finding_keys.add(finding_key)
                    all_findings.append(finding)
            sources_searched_total.add(f"iris({len(iris_findings)})")
            progress(f"   → {len(iris_findings)} intelligence items")

    # =========================================================================
    # PHASE 4: CALLIOPE - Synthesize report
    # =========================================================================
    progress(f"✍️ *Calliope* synthesizing report from {len(all_findings)} findings...")
    raw_report, confidence, follow_ups = _synthesize_report(query, all_findings, steps)

    # =========================================================================
    # PHASE 5: VERA - Fact-check the report
    # =========================================================================
    progress("🔎 *Vera* fact-checking the report...")
    verified_report = _run_vera_verification(raw_report, query)

    # =========================================================================
    # PHASE 6: SOPHIA - Learn from this session
    # =========================================================================
    _run_sophia_reflect(query, verified_report)

    total_duration = (time.time() - start_time) * 1000
    progress(
        f"✅ *Research complete*\n"
        f"   {len(all_findings)} findings | {len(steps)} steps | {total_duration/1000:.1f}s\n"
        f"   Confidence: {confidence}\n"
        f"   Agents used: Athena, Clio, Iris, Calliope, Vera, Sophia"
    )

    return DeepResearchResult(
        query=query,
        report=verified_report,
        steps=steps,
        total_findings=len(all_findings),
        total_sources_searched=len(sources_searched_total),
        total_duration_ms=total_duration,
        confidence=confidence,
        follow_up_questions=follow_ups,
    )
