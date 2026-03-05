"""
Nemesis — The Correction-Hungry Learning Agent
================================================

Nemesis is the goddess of retribution and balance. In Ira's pantheon she
serves a singular obsession: **no mistake goes unlearned**.

She sits at every junction where Ira can fail:
  1. Telegram corrections — Rushabh says "that's wrong, it should be X"
  2. Sophia reflections — post-response quality checks flag issues
  3. Immune system — recurring validation failures
  4. Knowledge health — hallucination / business-rule violations

For each failure she:
  - Extracts the structured correction (wrong → right, entity, category)
  - Records it in her SQLite correction store
  - Stores it immediately in Mem0 (so the next query benefits)
  - Queues it for deep training during sleep/nap mode

During sleep, her trainer:
  - Generates new truth hints from repeated corrections
  - Indexes correction facts into Qdrant for semantic retrieval
  - Produces a training guidance block for the system prompt
  - Reports what she learned to Telegram

Usage:
    from openclaw.agents.ira.src.agents.nemesis import ingest_correction, ingest_failure

    # From Telegram feedback
    ingest_correction(
        wrong_info="[Customer A] owes ₹X.XX Cr",
        correct_info="[Customer A] only has ₹X Cr pending, rest is paid",
        source="telegram_feedback",
        entity="[Customer A]",
        category="customer",
        severity="critical",
        query="What's our order book?",
        bad_response="Outstanding: ₹XX Cr...",
    )

    # From Sophia reflection
    ingest_failure(
        query="Give me the CFO dashboard",
        response="Here's the dashboard...",
        issues=["PRICING_DISCLAIMER_MISSING"],
        quality_score=0.6,
        source="sophia_reflection",
    )
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.nemesis")

try:
    from openclaw.agents.ira.config import get_openai_client, FAST_LLM_MODEL, get_logger
    logger = get_logger("ira.nemesis")
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    FAST_LLM_MODEL = "gpt-4.1-mini"

from . import correction_store as store


class Nemesis:
    """The correction-hungry learning agent.
    
    Nemesis intercepts every failure signal in the system, structures it,
    stores it for immediate use (Mem0) and queues it for deep training
    (correction_store → sleep trainer).
    """

    def __init__(self):
        self._client = None
        self._mem0 = None

    @property
    def client(self):
        if self._client is None:
            if CONFIG_AVAILABLE:
                self._client = get_openai_client()
            else:
                try:
                    from openai import OpenAI
                    self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
                except Exception as e:
                    logger.error(f"Error in client: {e}", exc_info=True)
        return self._client

    @property
    def mem0(self):
        if self._mem0 is None:
            try:
                from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
                self._mem0 = get_mem0_service()
            except Exception as e:
                logger.error(f"Error in mem0: {e}", exc_info=True)
        return self._mem0

    # -----------------------------------------------------------------
    # PUBLIC: Ingest a correction (wrong → right)
    # -----------------------------------------------------------------

    def ingest_correction(
        self,
        *,
        wrong_info: str,
        correct_info: str,
        source: str = "telegram_feedback",
        entity: Optional[str] = None,
        category: Optional[str] = None,
        severity: str = "important",
        query: Optional[str] = None,
        bad_response: Optional[str] = None,
        coach_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ingest a correction: store it, learn from it immediately, queue for sleep training.
        
        Returns a dict with correction_id and what was stored.
        """
        if not category:
            category = self._classify_category(wrong_info, correct_info, entity)
        if not entity:
            entity = self._extract_entity(wrong_info, correct_info)

        cid = store.record_correction(
            wrong_info=wrong_info,
            correct_info=correct_info,
            source=source,
            entity=entity,
            category=category,
            severity=severity,
            query=query,
            bad_response=bad_response,
            coach_note=coach_note,
        )

        mem0_stored = self._store_in_mem0(correct_info, entity, category, source)

        try:
            from openclaw.agents.ira.src.agents.researcher.agent import invalidate_cache
            invalidate_cache(entity=entity or "")
        except Exception as e:
            logger.error(f"Error in ingest_correction: {e}", exc_info=True)

        self._flag_qdrant_contradictions(entity or "", correct_info)

        logger.info(
            f"[NEMESIS] Ingested correction {cid}: "
            f"{entity or 'general'}/{category} ({severity}) — mem0={'yes' if mem0_stored else 'no'}"
        )

        return {
            "correction_id": cid,
            "entity": entity,
            "category": category,
            "severity": severity,
            "mem0_stored": mem0_stored,
        }

    # -----------------------------------------------------------------
    # PUBLIC: Ingest a failure (bad response)
    # -----------------------------------------------------------------

    def ingest_failure(
        self,
        *,
        query: str,
        response: str,
        source: str = "sophia_reflection",
        issues: Optional[List[str]] = None,
        quality_score: Optional[float] = None,
        coach_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ingest a response failure. Extracts corrections if possible."""
        fid = store.record_failure(
            query=query,
            response=response,
            source=source,
            issues=issues,
            quality_score=quality_score,
            coach_note=coach_note,
        )

        corrections_extracted = 0
        if issues:
            corrections_extracted = self._extract_corrections_from_issues(
                query, response, issues
            )

        logger.info(
            f"[NEMESIS] Ingested failure {fid}: {len(issues or [])} issues, "
            f"{corrections_extracted} corrections extracted"
        )

        return {
            "failure_id": fid,
            "issues": issues or [],
            "corrections_extracted": corrections_extracted,
        }

    # -----------------------------------------------------------------
    # PUBLIC: Ingest raw Telegram feedback (natural language)
    # -----------------------------------------------------------------

    def ingest_telegram_feedback(
        self,
        *,
        user_message: str,
        previous_response: str,
        coach_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ingest natural-language feedback from Telegram.
        
        Uses LLM to extract structured corrections, then ingests each one.
        """
        corrections = self._extract_corrections_from_feedback(
            user_message, previous_response
        )

        results = []
        for corr in corrections:
            result = self.ingest_correction(
                wrong_info=corr.get("wrong_info", ""),
                correct_info=corr.get("correct_info", ""),
                source="telegram_feedback",
                entity=corr.get("entity"),
                category=corr.get("category"),
                severity=corr.get("severity", "important"),
                query=None,
                bad_response=previous_response[:1000],
                coach_note=coach_note,
            )
            results.append(result)

        return {
            "corrections_count": len(results),
            "corrections": results,
        }

    # -----------------------------------------------------------------
    # PUBLIC: Stats and reporting
    # -----------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return store.get_correction_stats()

    def get_hungry_report(self) -> str:
        """Generate a report of what Nemesis is hungry to fix."""
        stats = self.get_stats()
        unapplied = store.get_unapplied_corrections(limit=10)

        lines = [
            f"Nemesis Correction Report",
            f"Total corrections: {stats['total_corrections']}",
            f"Awaiting training: {stats['unapplied']}",
            f"Training runs: {stats['training_runs']}",
        ]

        if stats["repeat_offenders"]:
            lines.append("\nRepeat offenders:")
            for ro in stats["repeat_offenders"][:5]:
                lines.append(f"  {ro['entity']} ({ro['category']}): {ro['total_occ']}x")

        if unapplied:
            lines.append("\nPending corrections (top 10):")
            for c in unapplied:
                sev = c["severity"]
                ent = c["entity"] or "general"
                lines.append(f"  [{sev}] {ent}: {c['correct_info'][:80]}")

        return "\n".join(lines)

    # -----------------------------------------------------------------
    # PRIVATE: LLM extraction
    # -----------------------------------------------------------------

    def _extract_corrections_from_feedback(
        self, user_message: str, previous_response: str
    ) -> List[Dict[str, Any]]:
        """Use LLM to extract structured corrections from natural language feedback."""
        if not self.client:
            return [self._fallback_extraction(user_message, previous_response)]

        try:
            resp = self.client.chat.completions.create(
                model=FAST_LLM_MODEL,
                messages=[
                    {"role": "system", "content": (
                        "You are Nemesis, a correction extraction engine. "
                        "Extract every factual correction from the user's feedback about Ira's response.\n\n"
                        "Return a JSON array of corrections. Each correction:\n"
                        "{\n"
                        '  "wrong_info": "what Ira said that was wrong",\n'
                        '  "correct_info": "what the correct information is",\n'
                        '  "entity": "entity name (company, machine model, person) or null",\n'
                        '  "category": "spec|price|fact|customer|process|tone",\n'
                        '  "severity": "critical|important|minor|style"\n'
                        "}\n\n"
                        "Rules:\n"
                        "- Be precise: extract the specific wrong fact and the specific correct fact\n"
                        "- If the user says 'that's wrong' without giving the correct answer, "
                        "set correct_info to 'USER FLAGGED AS WRONG — needs investigation'\n"
                        "- Price/customer/spec errors are always 'critical' or 'important'\n"
                        "- Tone/style feedback is 'style'\n"
                        "- If no specific corrections, return empty array []\n"
                    )},
                    {"role": "user", "content": (
                        f"IRA'S RESPONSE:\n{previous_response[:1500]}\n\n"
                        f"USER'S FEEDBACK:\n{user_message}"
                    )},
                ],
                max_tokens=800,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            raw = resp.choices[0].message.content.strip()
            parsed = json.loads(raw)

            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "corrections" in parsed:
                return parsed["corrections"]
            if isinstance(parsed, dict) and "wrong_info" in parsed:
                return [parsed]
            return []

        except Exception as e:
            logger.warning(f"[NEMESIS] LLM extraction failed: {e}")
            return [self._fallback_extraction(user_message, previous_response)]

    def _fallback_extraction(
        self, user_message: str, previous_response: str
    ) -> Dict[str, Any]:
        """Rule-based fallback when LLM is unavailable."""
        return {
            "wrong_info": previous_response[:200],
            "correct_info": user_message[:500],
            "entity": None,
            "category": "fact",
            "severity": "important",
        }

    def _extract_corrections_from_issues(
        self, query: str, response: str, issues: List[str]
    ) -> int:
        """Extract corrections from Sophia/Vera issue codes."""
        count = 0
        for issue in issues:
            if "PRICING_DISCLAIMER_MISSING" in issue:
                self.ingest_correction(
                    wrong_info="Response contained price without disclaimer",
                    correct_info="All prices MUST include 'subject to configuration and current pricing'",
                    source="sophia_reflection",
                    category="price",
                    severity="important",
                    query=query,
                    bad_response=response[:500],
                )
                count += 1
            elif "AM_SERIES" in issue:
                self.ingest_correction(
                    wrong_info="AM series recommended for thick material",
                    correct_info="AM series is ONLY for materials ≤1.5mm. For >1.5mm use PF1/PF2.",
                    source="sophia_reflection",
                    entity="AM Series",
                    category="spec",
                    severity="critical",
                    query=query,
                    bad_response=response[:500],
                )
                count += 1
            elif "HALLUCINATION" in issue or "UNKNOWN_MODEL" in issue:
                self.ingest_correction(
                    wrong_info=f"Response may contain hallucinated information: {issue}",
                    correct_info="Only use verified data from machine_specs.json and Qdrant",
                    source="sophia_reflection",
                    category="fact",
                    severity="critical",
                    query=query,
                    bad_response=response[:500],
                )
                count += 1
        return count

    def _flag_qdrant_contradictions(self, entity: str, correct_info: str) -> None:
        """Search Qdrant for chunks that contradict the correction and flag them."""
        if not entity:
            return
        try:
            from openclaw.agents.ira.src.brain.qdrant_retriever import retrieve as qdrant_retrieve
            results = qdrant_retrieve(entity, top_k=5)
            if not hasattr(results, 'citations') or not results.citations:
                return
            from qdrant_client import QdrantClient
            client = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))
            for citation in results.citations:
                if entity.lower() in (citation.text or "").lower():
                    try:
                        client.set_payload(
                            collection_name="ira_chunks_v4_voyage",
                            payload={
                                "_correction_flag": correct_info,
                                "_flagged_at": datetime.now().isoformat(),
                            },
                            points=[citation.id] if hasattr(citation, 'id') and citation.id else [],
                        )
                        logger.info("[Nemesis] Flagged Qdrant chunk %s as potentially contradicted by correction", citation.id)
                    except Exception as e:
                        logger.debug("[Nemesis] Could not flag Qdrant chunk: %s", e)
        except Exception as e:
            logger.debug("[Nemesis] Qdrant contradiction flagging failed: %s", e)

    def _classify_category(
        self, wrong_info: str, correct_info: str, entity: Optional[str]
    ) -> str:
        """Classify the correction category from content."""
        combined = f"{wrong_info} {correct_info}".lower()
        if any(w in combined for w in ["price", "cost", "$", "₹", "€", "usd", "inr", "eur", "cr", "lakh"]):
            return "price"
        if any(w in combined for w in ["mm", "kw", "spec", "dimension", "thickness", "heater", "servo"]):
            return "spec"
        if any(w in combined for w in ["customer", "company", "ordered", "bought", "shut", "closed"]):
            return "customer"
        if any(w in combined for w in ["process", "forming", "vacuum", "heating"]):
            return "process"
        if any(w in combined for w in ["tone", "formal", "casual", "rude", "polite"]):
            return "tone"
        return "fact"

    def _extract_entity(self, wrong_info: str, correct_info: str) -> Optional[str]:
        """Try to extract entity name from correction text."""
        import re
        combined = f"{wrong_info} {correct_info}"
        model_match = re.search(r'\b(PF[12]-[A-Z]*-?\d{4}|AM[P]?-\d{4}|IMG-\d{4}|FCS-\d{4}|ATF-\d{4})\b', combined)
        if model_match:
            return model_match.group(1)
        return None

    def _store_in_mem0(
        self, correct_info: str, entity: Optional[str],
        category: Optional[str], source: str,
    ) -> bool:
        """Store the correction in Mem0 for immediate retrieval."""
        if not self.mem0:
            return False

        user_id_map = {
            "spec": "machinecraft_knowledge",
            "price": "machinecraft_pricing",
            "customer": "machinecraft_customers",
            "process": "machinecraft_processes",
        }
        user_id = user_id_map.get(category, "machinecraft_general")

        try:
            self.mem0.add_memory(
                text=f"CORRECTION ({source}): {correct_info}",
                user_id=user_id,
                metadata={
                    "source": f"nemesis_{source}",
                    "entity": entity,
                    "category": category,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            return True
        except Exception as e:
            logger.warning(f"[NEMESIS] Mem0 storage failed: {e}")
            return False


# =====================================================================
# Singleton + convenience functions
# =====================================================================

_nemesis: Optional[Nemesis] = None


def get_nemesis() -> Nemesis:
    global _nemesis
    if _nemesis is None:
        _nemesis = Nemesis()
    return _nemesis


def ingest_correction(**kwargs) -> Dict[str, Any]:
    """Convenience: ingest a correction."""
    return get_nemesis().ingest_correction(**kwargs)


def ingest_failure(**kwargs) -> Dict[str, Any]:
    """Convenience: ingest a failure."""
    return get_nemesis().ingest_failure(**kwargs)
