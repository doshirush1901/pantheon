"""
Nightly consolidation of real-time learnings.

Reviews all patterns collected during the day from the RealTimeHub's
persisted JSONL file. Uses an LLM to decide which patterns represent
durable, long-term knowledge worth promoting to Mem0 and truth hints.
Clears the temporary hub after processing.

Called from nap.py as run_phase_realtime_consolidation().
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from openclaw.agents.ira.src.observers.realtime_hub import LearnedPattern

logger = logging.getLogger("ira.realtime_consolidator")

_CONSOLIDATION_PROMPT = """You are reviewing patterns that Ira (an AI sales assistant) learned during today's conversations. Each pattern was extracted in real-time from user messages.

Your job: decide which patterns represent DURABLE, long-term knowledge that should be permanently stored, vs. which are transient/conversational and should be discarded.

Criteria for PROMOTION (keep permanently):
- Factual information about a customer, company, or project that will be relevant in future conversations
- Corrections to Ira's knowledge (wrong specs, prices, names, etc.)
- Persistent user preferences (communication style, format preferences)
- Business relationships, deadlines, or commitments

Criteria for DISCARD:
- One-time conversational context ("I'm in a meeting right now")
- Vague or ambiguous statements
- Information Ira already knows (duplicates of existing knowledge)
- Temporary states ("I'll call you back in 5 minutes")

For each pattern, respond with:
- "PROMOTE" if it should be stored permanently
- "DISCARD" if it's transient

Also, for promoted patterns, rewrite the content to be clear and self-contained
(it will be stored without conversation context).

Respond with a JSON array. Each element:
{{"id": <index>, "decision": "PROMOTE"|"DISCARD", "rewritten": "..." (only if PROMOTE)}}

Patterns to review:
{patterns}"""


async def consolidate_realtime_patterns(dry_run: bool = False) -> Dict[str, Any]:
    """
    Review today's real-time patterns and promote durable ones to Mem0.

    Returns a summary dict with counts for the nap journal.
    """
    from openclaw.agents.ira.src.observers.realtime_hub import (
        RealTimeHub,
        LearnedPattern,
        PatternType,
    )

    patterns = RealTimeHub.load_persisted()
    if not patterns:
        logger.info("[Consolidator] No real-time patterns to consolidate")
        return {"total": 0, "promoted": 0, "discarded": 0}

    logger.info("[Consolidator] Reviewing %d real-time patterns from today", len(patterns))

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.warning("[Consolidator] No API key — skipping consolidation")
        return {"total": len(patterns), "promoted": 0, "discarded": 0, "error": "no_api_key"}

    patterns_text = "\n".join(
        f"{i}. [{p.pattern_type.value.upper()}] (user={p.user_id}) {p.content}"
        for i, p in enumerate(patterns)
    )

    try:
        import openai
        client = openai.AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You review learned patterns and decide which to keep permanently. Respond only with valid JSON."},
                {"role": "user", "content": _CONSOLIDATION_PROMPT.format(patterns=patterns_text)},
            ],
            max_tokens=2048,
            temperature=0.1,
        )

        raw = (response.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        decisions = json.loads(raw)
        if not isinstance(decisions, list):
            decisions = []

    except Exception as e:
        logger.error("[Consolidator] LLM review failed: %s", e)
        return {"total": len(patterns), "promoted": 0, "discarded": 0, "error": str(e)}

    promoted = 0
    discarded = 0

    for decision in decisions:
        idx = decision.get("id")
        if idx is None or idx >= len(patterns):
            continue

        pattern = patterns[idx]

        if decision.get("decision") == "PROMOTE":
            rewritten = decision.get("rewritten", pattern.content)

            if not dry_run:
                await _promote_to_mem0(pattern, rewritten)

                if pattern.pattern_type == PatternType.CORRECTION:
                    await _promote_to_nemesis(pattern, rewritten)

            promoted += 1
            logger.info("[Consolidator] PROMOTED: %s", rewritten[:100])
        else:
            discarded += 1
            logger.debug("[Consolidator] DISCARDED: %s", pattern.content[:100])

    if not dry_run:
        RealTimeHub.clear_persisted()
        logger.info("[Consolidator] Cleared persisted patterns file")

    result = {
        "total": len(patterns),
        "promoted": promoted,
        "discarded": discarded,
    }
    logger.info("[Consolidator] Done: %s", result)
    return result


async def _promote_to_mem0(pattern: LearnedPattern, rewritten: str) -> None:
    """Store a promoted pattern in Mem0 for long-term retrieval."""
    try:
        from openclaw.agents.ira.src.memory.mem0_memory import Mem0Memory
        mem0 = Mem0Memory()

        category_map = {
            "fact": "machinecraft_customers",
            "correction": "machinecraft_knowledge",
            "preference": "machinecraft_customers",
        }
        mem0_user = category_map.get(pattern.pattern_type.value, "machinecraft_general")

        await asyncio.to_thread(
            mem0.add_memory,
            text=f"[REALTIME LEARNING] {rewritten}",
            user_id=mem0_user,
            metadata={
                "source": "realtime_observer",
                "original_user": pattern.user_id,
                "pattern_type": pattern.pattern_type.value,
                "timestamp": pattern.timestamp,
            },
        )
        logger.info("[Consolidator] Stored in Mem0 (%s): %s", mem0_user, rewritten[:80])
    except Exception as e:
        logger.warning("[Consolidator] Mem0 storage failed: %s", e)


async def _promote_to_nemesis(pattern: LearnedPattern, rewritten: str) -> None:
    """Feed corrections to Nemesis for deeper integration (truth hints, Qdrant, etc.)."""
    try:
        from openclaw.agents.ira.src.agents.nemesis import ingest_correction
        await asyncio.to_thread(
            ingest_correction,
            wrong_info="(detected via real-time observation)",
            correct_info=rewritten,
            source="realtime_observer",
            entity=pattern.user_id,
            category="fact",
            severity="important",
        )
        logger.info("[Consolidator] Fed correction to Nemesis: %s", rewritten[:80])
    except Exception as e:
        logger.warning("[Consolidator] Nemesis ingestion failed: %s", e)
