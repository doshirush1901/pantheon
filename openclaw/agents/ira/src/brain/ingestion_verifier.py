#!/usr/bin/env python3
"""
INGESTION VERIFIER — Curiosity-Driven Pre-Storage Verification
================================================================

Sits between extraction and storage in the knowledge pipeline.
Before any knowledge item enters Qdrant/Mem0, this module:

1. Classifies entities (is "UZI" a person, company, machine, or project?)
2. Cross-references claims against email history in Qdrant
3. Assigns a confidence score based on evidence found
4. Flags ambiguous items for Telegram clarification
5. Downgrades or blocks items that contradict existing verified knowledge

The pipeline becomes:
  PDF → extract → VERIFY (this module) → store with confidence

Confidence tiers:
  0.9-1.0  VERIFIED    — cross-referenced against emails/existing knowledge
  0.7-0.89 LIKELY      — consistent with existing knowledge, no contradiction
  0.5-0.69 UNVERIFIED  — no supporting or contradicting evidence found
  0.3-0.49 UNCERTAIN   — ambiguous entity or weak evidence; queued for review
  0.0-0.29 REJECTED    — contradicts verified knowledge; blocked from storage
"""

import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ira.ingestion_verifier")

BRAIN_DIR = Path(__file__).parent
AGENT_DIR = BRAIN_DIR.parent.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(BRAIN_DIR))

VERIFICATION_LOG = PROJECT_ROOT / "data" / "knowledge" / "verification_log.jsonl"
REVIEW_QUEUE = PROJECT_ROOT / "data" / "brain" / "review_queue.json"

ENTITY_TYPES = {"person", "company", "machine", "project", "location", "event", "unknown"}

KNOWN_MACHINE_PREFIXES = {
    "PF1", "PF2", "AM", "IMG", "FCS", "ATF", "RT", "EFX", "AO",
    "SAM", "DUO", "UNO", "MC-4A",
}


@dataclass
class VerificationResult:
    """Result of verifying a single knowledge item before storage."""
    original_entity: str
    verified_entity: str
    entity_type: str
    confidence: float
    evidence: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    action: str = "store"  # store, store_with_flag, queue_for_review, reject
    review_reason: str = ""

    @property
    def tier(self) -> str:
        if self.confidence >= 0.9:
            return "VERIFIED"
        elif self.confidence >= 0.7:
            return "LIKELY"
        elif self.confidence >= 0.5:
            return "UNVERIFIED"
        elif self.confidence >= 0.3:
            return "UNCERTAIN"
        return "REJECTED"


# ---------------------------------------------------------------------------
# Entity classification
# ---------------------------------------------------------------------------

def _is_machine_model(entity: str) -> bool:
    """Check if an entity looks like a Machinecraft machine model."""
    upper = entity.upper().replace(" ", "-")
    for prefix in KNOWN_MACHINE_PREFIXES:
        if upper.startswith(prefix) and re.search(r'\d', upper):
            return True
    return False


def classify_entity(entity: str, text: str, source_file: str) -> str:
    """
    Classify what type of entity this is based on context clues.
    Returns one of: person, company, machine, project, location, event, unknown.
    """
    if not entity or len(entity.strip()) < 2:
        return "unknown"

    e_upper = entity.upper().strip()

    if _is_machine_model(entity):
        return "machine"

    company_suffixes = [
        "LTD", "INC", "CORP", "GMBH", "LLC", "PVT", "S.A.", "S.R.L.",
        "BV", "NV", "AG", "CO.", "TECHNOLOGIES", "INDUSTRIES", "GROUP",
        "PLASTICS", "ENGINEERING", "MANUFACTURING",
    ]
    for suffix in company_suffixes:
        if suffix in e_upper:
            return "company"

    person_indicators = [
        r'\b(?:Mr|Mrs|Ms|Dr|Prof)\.?\s',
        r'\b(?:Dear|Hi|Hello)\s+' + re.escape(entity),
        r'(?:from|by|to)\s+' + re.escape(entity) + r'\s',
    ]
    for pattern in person_indicators:
        if re.search(pattern, text[:2000], re.IGNORECASE):
            return "person"

    if entity.lower() in source_file.lower():
        fname_lower = source_file.lower()
        if any(w in fname_lower for w in ["offer", "quote", "for"]):
            # "Offer for X" — X could be a customer or project name
            return "unknown"

    # Short single-word capitalized names that don't match machine patterns
    # are inherently ambiguous (could be person, project, or codename)
    if len(entity.split()) == 1 and entity[0].isupper() and len(entity) <= 10:
        if not _is_machine_model(entity):
            return "unknown"

    return "unknown"


# ---------------------------------------------------------------------------
# Cross-reference against email history
# ---------------------------------------------------------------------------

def _search_emails(query: str, limit: int = 5) -> List[Dict]:
    """Search the email Qdrant collection for evidence about an entity."""
    try:
        import voyageai
        from qdrant_client import QdrantClient

        api_key = os.environ.get("VOYAGE_API_KEY", "")
        qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        if not api_key:
            return []

        voyage = voyageai.Client(api_key=api_key)
        qdrant = QdrantClient(url=qdrant_url, timeout=10)

        emb = voyage.embed([query], model="voyage-3", input_type="query").embeddings[0]

        results = []
        for collection in ["ira_emails_voyage_v2", "ira_chunks_v4_voyage"]:
            try:
                hits = qdrant.query_points(
                    collection_name=collection, query=emb, limit=limit,
                )
                for pt in hits.points:
                    p = pt.payload or {}
                    results.append({
                        "text": (p.get("text") or p.get("raw_text") or "")[:500],
                        "score": pt.score,
                        "source": p.get("filename") or p.get("subject") or collection,
                        "collection": collection,
                    })
            except Exception:
                continue

        results.sort(key=lambda x: -x["score"])
        return results[:limit]
    except Exception as e:
        logger.debug("Email cross-reference failed: %s", e)
        return []


def _search_existing_knowledge(query: str, limit: int = 5) -> List[Dict]:
    """Search existing knowledge base for corroborating or contradicting info."""
    try:
        import voyageai
        from qdrant_client import QdrantClient

        api_key = os.environ.get("VOYAGE_API_KEY", "")
        qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        if not api_key:
            return []

        voyage = voyageai.Client(api_key=api_key)
        qdrant = QdrantClient(url=qdrant_url, timeout=10)

        emb = voyage.embed([query], model="voyage-3", input_type="query").embeddings[0]

        hits = qdrant.query_points(
            collection_name="ira_discovered_knowledge", query=emb, limit=limit,
        )
        results = []
        for pt in hits.points:
            p = pt.payload or {}
            results.append({
                "text": (p.get("text") or "")[:500],
                "score": pt.score,
                "entity": p.get("entity", ""),
                "source": p.get("filename", ""),
                "confidence": p.get("confidence", 1.0),
            })
        return results
    except Exception as e:
        logger.debug("Knowledge cross-reference failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# LLM-powered verification (lightweight, gpt-4o-mini)
# ---------------------------------------------------------------------------

def _llm_verify_entity(
    entity: str,
    entity_type: str,
    text: str,
    source_file: str,
    email_evidence: List[Dict],
    knowledge_evidence: List[Dict],
) -> Dict[str, Any]:
    """
    Ask GPT-4o-mini to verify an entity given the evidence.
    Returns dict with: verified_entity, entity_type, confidence, reasoning.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {"confidence": 0.6, "entity_type": entity_type, "reasoning": "No LLM available"}

    email_ctx = ""
    if email_evidence:
        email_ctx = "EMAIL EVIDENCE:\n" + "\n".join(
            f"- [{e['source']}] (score {e['score']:.2f}): {e['text'][:200]}"
            for e in email_evidence[:5]
        )

    knowledge_ctx = ""
    if knowledge_evidence:
        knowledge_ctx = "EXISTING KNOWLEDGE:\n" + "\n".join(
            f"- [{e['source']}] entity={e.get('entity','')} conf={e.get('confidence',1.0)}: {e['text'][:200]}"
            for e in knowledge_evidence[:5]
        )

    prompt = f"""You are verifying data before it enters a knowledge base for Machinecraft Technologies (thermoforming machines).

ENTITY TO VERIFY: "{entity}"
CLASSIFIED AS: {entity_type}
SOURCE FILE: {source_file}

EXTRACTED TEXT (first 500 chars):
{text[:500]}

{email_ctx}

{knowledge_ctx}

Answer these questions as JSON:
{{
  "verified_entity": "corrected entity name if needed, or same as original",
  "entity_type": "one of: person, company, machine, project, location, unknown",
  "confidence": 0.0-1.0,
  "reasoning": "1-2 sentences explaining your assessment",
  "is_customer": true/false/null,
  "relationship_to_machinecraft": "customer/prospect/supplier/agent/partner/internal/unknown"
}}

Rules:
- If entity is a person's name (first name only like "Uzi", "Mikhail"), classify as person
- If entity is a machine model (PF1-X-2015, AM-5060), classify as machine and note the FULL model with variant letter
- If evidence shows this entity in a different role than the text implies, flag it
- Confidence 0.9+ only if email evidence directly confirms the claim
- Confidence 0.5-0.7 if no evidence either way
- Confidence <0.5 if evidence contradicts the claim"""

    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Verify entities for a knowledge base. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=400,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        return json.loads(raw)
    except Exception as e:
        logger.warning("LLM entity verification failed: %s", e)
        return {"confidence": 0.6, "entity_type": entity_type, "reasoning": f"LLM failed: {e}"}


# ---------------------------------------------------------------------------
# Review queue management
# ---------------------------------------------------------------------------

def _load_review_queue() -> List[Dict]:
    if REVIEW_QUEUE.exists():
        try:
            return json.loads(REVIEW_QUEUE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return []


def _save_review_queue(queue: List[Dict]):
    REVIEW_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_QUEUE.write_text(json.dumps(queue, indent=2, ensure_ascii=False))


def queue_for_review(
    entity: str,
    entity_type: str,
    source_file: str,
    text_excerpt: str,
    reason: str,
    confidence: float,
):
    """Add an item to the review queue for Rushabh to verify via Telegram."""
    queue = _load_review_queue()
    queue.append({
        "id": f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(queue)}",
        "entity": entity,
        "entity_type": entity_type,
        "source_file": source_file,
        "text_excerpt": text_excerpt[:300],
        "reason": reason,
        "confidence": confidence,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    })
    _save_review_queue(queue)
    logger.info("Queued for review: %s (%s) — %s", entity, entity_type, reason)


# ---------------------------------------------------------------------------
# Verification log
# ---------------------------------------------------------------------------

def _log_verification(result: VerificationResult, source_file: str):
    try:
        VERIFICATION_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "entity": result.original_entity,
            "verified_entity": result.verified_entity,
            "entity_type": result.entity_type,
            "confidence": result.confidence,
            "tier": result.tier,
            "action": result.action,
            "source_file": source_file,
            "evidence_count": len(result.evidence),
            "issues": result.issues,
        }
        with open(VERIFICATION_LOG, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main verification function
# ---------------------------------------------------------------------------

def verify_knowledge_item(
    entity: str,
    text: str,
    knowledge_type: str,
    source_file: str,
    confidence: float = 1.0,
    skip_llm: bool = False,
) -> VerificationResult:
    """
    Verify a knowledge item before it enters the knowledge base.

    Steps:
    1. Classify the entity type
    2. Search emails and existing knowledge for corroboration
    3. (Optional) LLM verification for ambiguous entities
    4. Assign confidence and decide action

    Returns VerificationResult with adjusted confidence and action.
    """
    result = VerificationResult(
        original_entity=entity,
        verified_entity=entity,
        entity_type="unknown",
        confidence=confidence,
    )

    if not entity or len(entity.strip()) < 2:
        result.confidence = min(confidence, 0.6)
        result.action = "store"
        return result

    # Step 1: Classify entity
    entity_type = classify_entity(entity, text, source_file)
    result.entity_type = entity_type

    # Machine models get high base confidence (regex is reliable)
    if entity_type == "machine":
        result.confidence = max(confidence, 0.85)
        result.action = "store"
        _log_verification(result, source_file)
        return result

    # Step 2: Cross-reference against emails and knowledge
    email_evidence = _search_emails(f"{entity} Machinecraft", limit=3)
    knowledge_evidence = _search_existing_knowledge(entity, limit=3)

    for ev in email_evidence:
        result.evidence.append(f"[email:{ev['source']}] score={ev['score']:.2f}")
    for ev in knowledge_evidence:
        result.evidence.append(f"[knowledge:{ev['source']}] score={ev['score']:.2f}")

    has_strong_email = any(e["score"] > 0.4 for e in email_evidence)
    has_strong_knowledge = any(e["score"] > 0.5 for e in knowledge_evidence)

    # Step 3: LLM verification for ambiguous or unknown entities
    if not skip_llm and entity_type == "unknown":
        llm_result = _llm_verify_entity(
            entity, entity_type, text, source_file,
            email_evidence, knowledge_evidence,
        )
        result.entity_type = llm_result.get("entity_type", entity_type)
        result.verified_entity = llm_result.get("verified_entity", entity)
        llm_confidence = llm_result.get("confidence", 0.6)
        reasoning = llm_result.get("reasoning", "")

        if reasoning:
            result.evidence.append(f"[llm] {reasoning}")

        # Use LLM confidence but cap it based on evidence
        if has_strong_email:
            result.confidence = min(max(llm_confidence, 0.8), 1.0)
        elif has_strong_knowledge:
            result.confidence = min(max(llm_confidence, 0.7), 0.95)
        else:
            result.confidence = min(llm_confidence, 0.75)
    else:
        # No LLM — use evidence-based scoring
        if has_strong_email and has_strong_knowledge:
            result.confidence = max(confidence, 0.85)
        elif has_strong_email or has_strong_knowledge:
            result.confidence = max(min(confidence, 0.8), 0.65)
        elif entity_type == "company":
            result.confidence = min(confidence, 0.7)
        else:
            result.confidence = min(confidence, 0.6)

    # Step 4: Decide action
    if result.confidence >= 0.7:
        result.action = "store"
    elif result.confidence >= 0.5:
        result.action = "store_with_flag"
        result.issues.append(f"Unverified entity '{entity}' (type={result.entity_type})")
    elif result.confidence >= 0.3:
        result.action = "queue_for_review"
        result.review_reason = (
            f"Ambiguous entity '{entity}' classified as {result.entity_type}. "
            f"Confidence {result.confidence:.2f}. Source: {source_file}"
        )
        queue_for_review(
            entity=entity,
            entity_type=result.entity_type,
            source_file=source_file,
            text_excerpt=text[:300],
            reason=result.review_reason,
            confidence=result.confidence,
        )
    else:
        result.action = "reject"
        result.issues.append(
            f"Rejected: entity '{entity}' contradicts existing knowledge"
        )

    _log_verification(result, source_file)
    return result


def verify_batch(
    items: List[Dict[str, Any]],
    skip_llm: bool = False,
) -> List[Tuple[Dict, VerificationResult]]:
    """
    Verify a batch of knowledge items.

    Args:
        items: List of dicts with keys: entity, text, knowledge_type, source_file, confidence
        skip_llm: Skip LLM verification (faster, less accurate)

    Returns:
        List of (item, VerificationResult) tuples
    """
    results = []
    for item in items:
        vr = verify_knowledge_item(
            entity=item.get("entity", ""),
            text=item.get("text", ""),
            knowledge_type=item.get("knowledge_type", "general"),
            source_file=item.get("source_file", ""),
            confidence=item.get("confidence", 1.0),
            skip_llm=skip_llm,
        )
        results.append((item, vr))
    return results


def get_review_queue_summary() -> str:
    """Get a human-readable summary of items pending review."""
    queue = _load_review_queue()
    pending = [q for q in queue if q.get("status") == "pending"]
    if not pending:
        return "No items pending review."

    lines = [f"{len(pending)} items pending review:\n"]
    for item in pending[:20]:
        lines.append(
            f"  [{item['id']}] {item['entity']} ({item['entity_type']}) "
            f"— conf={item['confidence']:.2f} — {item['reason'][:80]}"
        )
    if len(pending) > 20:
        lines.append(f"  ... and {len(pending) - 20} more")
    return "\n".join(lines)
