"""
Feedback Handler - Processes positive and negative feedback from Telegram.

Positive feedback: logs success, boosts agent confidence for the pipeline that worked.
Negative feedback: logs mistake with context, asks the coach (Grounded Coach) for analysis,
                   queues the lesson for dream-mode learning.

Invoked from the Telegram gateway when feedback is detected in a user message.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("ira.feedback_handler")

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
FEEDBACK_LOG = PROJECT_ROOT / "data" / "feedback_log.jsonl"
DREAM_BACKLOG = PROJECT_ROOT / "data" / "feedback_backlog.jsonl"
AGENT_SCORES_FILE = PROJECT_ROOT / "data" / "learned_lessons" / "agent_scores.json"
MISTAKE_LOG = PROJECT_ROOT / "data" / "training" / "mistake_log.json"

POSITIVE_PATTERNS = [
    "good", "great", "nice", "well done", "perfect", "excellent", "awesome",
    "correct", "right", "exactly", "spot on", "that's it", "love it",
    "thanks", "thank you", "helpful", "brilliant", "impressive", "nailed it",
    "yes!", "yes!!", "yes!!!", "bingo", "bravo", "superb", "fantastic",
    "good job", "good work", "nice work", "great work", "keep it up",
    "much better", "way better", "improved", "this is what i wanted",
]

NEGATIVE_PATTERNS = [
    "wrong", "incorrect", "not right", "that's not", "no,", "nope",
    "bad", "terrible", "useless", "fix this", "fix it", "you're wrong",
    "hallucinating", "made up", "fabricated", "fake", "not true",
    "drunk", "sober up", "pull yourself together", "what are you doing",
    "that's not what i asked", "not what i meant", "off topic",
    "disappointing", "worse", "garbage", "nonsense", "rubbish",
    "you forgot", "you missed", "you ignored", "didn't answer",
    "actually,", "correction:", "should be", "instead of",
]


def detect_feedback(message: str, previous_response: str = "") -> Tuple[Optional[str], float]:
    """Detect if a message is positive or negative feedback.
    
    Uses pattern matching for clear-cut cases and an LLM for ambiguous ones
    (e.g. "actually, can you tell me about PF2?" is NOT feedback despite
    containing "actually,").
    
    Returns: (feedback_type, confidence) where feedback_type is 'positive', 'negative', or None.
    """
    msg_lower = message.lower().strip()

    if len(msg_lower) < 3:
        return None, 0.0

    # Long substantive messages are queries, not feedback.
    # Feedback is short: "great!", "that's wrong", "thanks", "fix this".
    if len(msg_lower) > 200:
        return None, 0.0

    # Messages with numbered lists or multiple questions are queries, not feedback.
    if msg_lower.count("\n") > 3 or sum(1 for c in msg_lower if c in "12345") >= 3:
        return None, 0.0

    pos_hits = sum(1 for p in POSITIVE_PATTERNS if p in msg_lower)
    neg_hits = sum(1 for p in NEGATIVE_PATTERNS if p in msg_lower)

    if pos_hits == 0 and neg_hits == 0:
        return None, 0.0

    # Require stronger signal: at least 2 pattern hits, or 1 hit in a short message
    total_hits = pos_hits + neg_hits
    if total_hits == 1 and len(msg_lower) > 80:
        return None, 0.0

    # High-confidence cases: skip LLM
    if pos_hits >= 3 and neg_hits == 0:
        return "positive", 0.9
    if neg_hits >= 3 and pos_hits == 0:
        return "negative", 0.9

    # Ambiguous cases (mixed signals or low hit count): use LLM to disambiguate
    if (pos_hits > 0 and neg_hits > 0) or max(pos_hits, neg_hits) <= 1:
        llm_result = _llm_classify_feedback(message, previous_response)
        if llm_result:
            return llm_result, 0.75

    if pos_hits > neg_hits:
        return "positive", min(0.5 + pos_hits * 0.15, 0.7)
    elif neg_hits > pos_hits:
        return "negative", min(0.5 + neg_hits * 0.15, 0.7)
    return None, 0.0


def _llm_classify_feedback(message: str, previous_response: str) -> Optional[str]:
    """Use gpt-4o-mini to classify ambiguous messages as feedback or not."""
    try:
        import openai
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return None

        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "Classify this message. Is it:\n"
                    "A) POSITIVE feedback about the previous response (praise, thanks, confirmation)\n"
                    "B) NEGATIVE feedback about the previous response (correction, complaint, disagreement)\n"
                    "C) NOT feedback (new question, topic change, continuation of conversation)\n\n"
                    "Output ONLY one word: POSITIVE, NEGATIVE, or NONE"
                )},
                {"role": "user", "content": (
                    f"PREVIOUS RESPONSE: {previous_response[:300]}\n\n"
                    f"USER MESSAGE: {message}"
                )},
            ],
            max_tokens=10,
            temperature=0.0,
        )
        result = resp.choices[0].message.content.strip().upper()
        if "POSITIVE" in result:
            return "positive"
        if "NEGATIVE" in result:
            return "negative"
        return None
    except Exception as e:
        logger.debug(f"LLM feedback classification failed: {e}")
        return None


def _load_agent_scores() -> Dict:
    """Load agent confidence scores."""
    if AGENT_SCORES_FILE.exists():
        try:
            return json.loads(AGENT_SCORES_FILE.read_text())
        except Exception:
            pass
    return {
        "clio": {"score": 0.7, "successes": 0, "failures": 0},
        "calliope": {"score": 0.7, "successes": 0, "failures": 0},
        "vera": {"score": 0.7, "successes": 0, "failures": 0},
        "iris": {"score": 0.5, "successes": 0, "failures": 0},
        "sophia": {"score": 0.7, "successes": 0, "failures": 0},
        "athena": {"score": 0.7, "successes": 0, "failures": 0},
    }


def _save_agent_scores(scores: Dict):
    """Save agent confidence scores."""
    AGENT_SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
    AGENT_SCORES_FILE.write_text(json.dumps(scores, indent=2))


def _append_jsonl(filepath: Path, entry: Dict):
    """Append a JSON entry to a JSONL file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "a") as f:
        f.write(json.dumps(entry) + "\n")


def handle_positive_feedback(
    user_message: str,
    previous_response: str,
    generation_path: str,
    chat_id: str = "",
) -> str:
    """Handle positive feedback: log success and boost agent scores.
    
    Returns an acknowledgment message.
    """
    logger.info(f"[FEEDBACK] Positive feedback detected: {user_message[:50]}")

    _append_jsonl(FEEDBACK_LOG, {
        "timestamp": datetime.now().isoformat(),
        "type": "positive",
        "user_message": user_message[:500],
        "previous_response": previous_response[:500],
        "generation_path": generation_path,
        "chat_id": chat_id,
    })

    scores = _load_agent_scores()
    agents_to_boost = _identify_agents_used(generation_path)
    for agent_name in agents_to_boost:
        if agent_name in scores:
            scores[agent_name]["successes"] += 1
            old = scores[agent_name]["score"]
            scores[agent_name]["score"] = min(old + 0.02, 1.0)
            logger.info(f"[FEEDBACK] Boosted {agent_name}: {old:.2f} -> {scores[agent_name]['score']:.2f}")
    _save_agent_scores(scores)

    # Signal endocrine system (bidirectional reinforcement)
    try:
        from openclaw.agents.ira.src.holistic.endocrine_system import get_endocrine_system
        endo = get_endocrine_system()
        for agent_name in agents_to_boost:
            endo.signal_success(agent_name, context={"source": "telegram_feedback"})
    except Exception:
        pass

    # Record as muscle action with positive outcome
    try:
        from openclaw.agents.ira.src.holistic.musculoskeletal_system import get_musculoskeletal_system
        musculo = get_musculoskeletal_system()
        musculo.record_action_outcome(
            request_id=chat_id or "unknown",
            outcome="approval_received",
            context={"feedback": user_message[:200]},
        )
    except Exception:
        pass

    # Store confirmed facts from the approved response in Mem0
    _store_confirmed_facts(previous_response)

    return "Glad that helped! I've reinforced this in my memory."


def _store_confirmed_facts(response: str):
    """When the user confirms a response is good, store key facts from it
    in Mem0 as verified/confirmed data."""
    if not response or len(response) < 50:
        return
    try:
        import openai
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return
        
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "Extract key facts from this response that was confirmed as correct by the user. "
                    "Output each fact as a standalone declarative statement, one per line. "
                    "Focus on: customer names + machines, prices, dates, relationships. "
                    "Prefix each with 'CONFIRMED: '. Max 5 facts. "
                    "If no specific facts worth storing, output: NOTHING_TO_STORE"
                )},
                {"role": "user", "content": response[:1000]},
            ],
            max_tokens=300,
            temperature=0.1,
        )
        result = resp.choices[0].message.content.strip()
        if "NOTHING_TO_STORE" in result:
            return
        
        facts = [l.strip() for l in result.split("\n") if l.strip().startswith("CONFIRMED:")]
        if not facts:
            return
        
        from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
        mem0 = get_mem0_service()
        for fact in facts[:5]:
            try:
                mem0.add_memory(
                    text=fact,
                    user_id="machinecraft_customers",
                    metadata={"source": "rushabh_confirmed", "timestamp": datetime.now().isoformat()},
                )
                logger.info(f"[FEEDBACK] Stored confirmed fact: {fact[:80]}")
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"[FEEDBACK] Confirmed fact storage failed: {e}")


def handle_negative_feedback(
    user_message: str,
    previous_response: str,
    generation_path: str,
    chat_id: str = "",
) -> str:
    """Handle negative feedback: extract corrections, store in Mem0 IMMEDIATELY,
    log mistake, ask coach for analysis, and queue for dream learning.
    
    The key difference from before: corrections are applied RIGHT NOW in Mem0,
    not deferred to dream mode. This means the very next question will use
    the corrected data.
    """
    logger.info(f"[FEEDBACK] Negative feedback detected: {user_message[:50]}")

    feedback_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "negative",
        "user_message": user_message[:1000],
        "previous_response": previous_response[:1000],
        "generation_path": generation_path,
        "chat_id": chat_id,
    }

    # STEP 1: Extract specific corrections and store in Mem0 IMMEDIATELY
    corrections_stored = _extract_and_store_corrections(user_message, previous_response)

    # STEP 2: Get coach analysis
    coach_analysis = _get_coach_analysis(user_message, previous_response)
    if coach_analysis:
        feedback_entry["coach_analysis"] = coach_analysis

    _append_jsonl(FEEDBACK_LOG, feedback_entry)

    # STEP 3: Queue for dream-mode deeper learning
    dream_entry = {
        "timestamp": datetime.now().isoformat(),
        "source": "telegram_negative_feedback",
        "user_feedback": user_message[:1000],
        "ira_response": previous_response[:1000],
        "coach_analysis": coach_analysis or "",
        "corrections_stored": corrections_stored,
        "status": "pending",
    }
    _append_jsonl(DREAM_BACKLOG, dream_entry)

    _log_mistake(user_message, previous_response, coach_analysis)

    # STEP 4: Reduce agent scores + signal endocrine system
    scores = _load_agent_scores()
    agents_used = _identify_agents_used(generation_path)
    for agent_name in agents_used:
        if agent_name in scores:
            old = scores[agent_name]["score"]
            scores[agent_name]["failures"] += 1
            scores[agent_name]["score"] = max(old - 0.03, 0.1)
    _save_agent_scores(scores)

    try:
        from openclaw.agents.ira.src.holistic.endocrine_system import get_endocrine_system
        endo = get_endocrine_system()
        for agent_name in agents_used:
            endo.signal_failure(agent_name, context={
                "source": "telegram_feedback",
                "corrections": corrections_stored[:3],
            })
    except Exception:
        pass

    try:
        from openclaw.agents.ira.src.holistic.musculoskeletal_system import get_musculoskeletal_system
        musculo = get_musculoskeletal_system()
        musculo.record_action_outcome(
            request_id=chat_id or "unknown",
            outcome="correction_received",
            context={"feedback": user_message[:200]},
        )
    except Exception:
        pass

    # Build acknowledgment showing what was learned RIGHT NOW
    ack = "Got it. I've updated my memory immediately with your corrections."
    if corrections_stored:
        ack += "\n\nStored right now:"
        for c in corrections_stored[:5]:
            ack += f"\n  - {c}"
    if coach_analysis:
        ack += f"\n\nCoach analysis: {coach_analysis[:200]}"
    ack += "\n\nThese corrections are live — ask me again and I'll use the updated data."
    return ack


def _extract_and_store_corrections(user_message: str, previous_response: str) -> List[str]:
    """Extract specific factual corrections from the user's message and store them
    in Mem0 immediately so they're available for the next query.
    
    Returns list of corrections that were stored.
    """
    stored = []
    
    try:
        import openai
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return stored
        
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "Extract specific factual corrections from the user's feedback. "
                    "Output each correction as a standalone fact that can be stored in memory.\n\n"
                    "Format: one fact per line, written as a declarative statement.\n"
                    "Example input: 'Batelaan is shut, they are not a customer anymore. Dezet has PF1-X-1310'\n"
                    "Example output:\n"
                    "Batelaan Kunststoffen is permanently closed and no longer operational\n"
                    "Batelaan is NOT a current Machinecraft customer\n"
                    "Dezet (Netherlands) has machine PF1-X-1310\n"
                    "Dezet is a confirmed Machinecraft customer\n\n"
                    "If the message is just general displeasure with no specific facts, output: NO_SPECIFIC_CORRECTIONS\n"
                    "Be precise. Include company names, machine models, dates, and relationships."
                )},
                {"role": "user", "content": (
                    f"USER'S CORRECTION:\n{user_message}\n\n"
                    f"IRA'S PREVIOUS RESPONSE (what was wrong):\n{previous_response[:800]}"
                )},
            ],
            max_tokens=500,
            temperature=0.1,
        )
        
        result = resp.choices[0].message.content.strip()
        
        if "NO_SPECIFIC_CORRECTIONS" in result:
            return stored
        
        facts = [line.strip() for line in result.split("\n") if line.strip() and len(line.strip()) > 5]
        
        if not facts:
            return stored
        
        # Store each fact in Mem0 immediately
        try:
            from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
            mem0 = get_mem0_service()
            
            for fact in facts[:10]:
                try:
                    mem0.add_memory(
                        text=fact,
                        user_id="machinecraft_customers",
                        metadata={"source": "rushabh_correction", "timestamp": datetime.now().isoformat()},
                    )
                    stored.append(fact)
                    logger.info(f"[FEEDBACK] Stored correction in Mem0: {fact[:80]}")
                except Exception as e:
                    logger.warning(f"[FEEDBACK] Failed to store correction: {e}")
                    
        except ImportError:
            logger.warning("[FEEDBACK] Mem0 not available for immediate correction storage")
        except Exception as e:
            logger.warning(f"[FEEDBACK] Mem0 storage error: {e}")
    
    except Exception as e:
        logger.warning(f"[FEEDBACK] Correction extraction failed: {e}")
    
    return stored


def _identify_agents_used(generation_path: str, agents_used: Optional[List[str]] = None) -> List[str]:
    """Identify which agents were involved.
    
    Prefers the explicit agents_used list (populated by tool_orchestrator) over
    string-matching on generation_path (legacy fallback).
    Phase 3 (Endocrine): Ensure Iris and Sophia get scored when used.
    """
    if agents_used:
        return list(set(["athena"] + agents_used))

    path_lower = (generation_path or "").lower()
    agents = ["athena"]
    if "research" in path_lower or "clio" in path_lower:
        agents.append("clio")
    if "write" in path_lower or "calliope" in path_lower:
        agents.append("calliope")
    if "verify" in path_lower or "vera" in path_lower or "fact" in path_lower:
        agents.append("vera")
    if "iris" in path_lower or "web" in path_lower or "lead" in path_lower or "enrich" in path_lower:
        agents.append("iris")
    if "reflect" in path_lower or "sophia" in path_lower or "lesson" in path_lower:
        agents.append("sophia")
    if "agent" in path_lower or "tool" in path_lower or "pipeline" in path_lower:
        agents.extend(["clio", "calliope", "vera", "iris", "sophia"])
    return list(set(agents))


def _get_coach_analysis(user_feedback: str, ira_response: str) -> Optional[str]:
    """Ask the Grounded Coach to analyze what went wrong."""
    try:
        import openai
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return None

        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "You are Ira's coach. The user gave negative feedback on Ira's response. "
                    "Analyze what went wrong in 2-3 sentences. Be specific: was it a wrong fact, "
                    "wrong tone, irrelevant answer, hallucination, or something else? "
                    "Then give one concrete lesson Ira should learn."
                )},
                {"role": "user", "content": (
                    f"USER FEEDBACK: {user_feedback}\n\n"
                    f"IRA'S RESPONSE: {ira_response[:800]}"
                )},
            ],
            max_tokens=200,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Coach analysis failed: {e}")
        return None


def _log_mistake(user_feedback: str, ira_response: str, coach_analysis: Optional[str]):
    """Log mistake for brain_rewire to process."""
    MISTAKE_LOG.parent.mkdir(parents=True, exist_ok=True)

    mistakes = []
    if MISTAKE_LOG.exists():
        try:
            mistakes = json.loads(MISTAKE_LOG.read_text())
        except Exception:
            mistakes = []

    mistakes.append({
        "timestamp": datetime.now().isoformat(),
        "user_feedback": user_feedback[:500],
        "ira_response": ira_response[:500],
        "coach_analysis": coach_analysis or "",
        "source": "telegram_live",
    })

    MISTAKE_LOG.write_text(json.dumps(mistakes, indent=2))


# =============================================================================
# CUSTOMER POSITIVE FEEDBACK (Beyond the Brain Phase 9)
# =============================================================================

CUSTOMER_POSITIVE_PATTERNS = [
    "thank you", "thanks", "looks good", "sounds good", "perfect",
    "great", "excellent", "let's proceed", "let's go ahead", "we accept",
    "we agree", "approved", "go ahead", "confirmed", "we'll take it",
    "place the order", "send the quote", "send the invoice",
    "interested", "very helpful", "impressive", "well done",
    "good job", "nice work", "exactly what we need",
]


def detect_customer_positive(message: str, from_email: str = "") -> bool:
    """Detect if a customer (non-Rushabh) reply is positive."""
    if not message or len(message) < 3:
        return False
    # Skip internal emails
    if from_email and ("machinecraft" in from_email.lower() or "rushabh" in from_email.lower()):
        return False
    msg_lower = message.lower()
    hits = sum(1 for p in CUSTOMER_POSITIVE_PATTERNS if p in msg_lower)
    return hits >= 1


def handle_customer_positive_feedback(
    customer_message: str,
    ira_previous_response: str,
    from_email: str = "",
    generation_path: str = "",
) -> None:
    """
    When a customer replies positively, boost agent scores.
    This is the external feedback loop - customers validating Ira's work.
    """
    if not detect_customer_positive(customer_message, from_email):
        return

    logger.info(f"[FEEDBACK] Customer positive signal from {from_email[:30]}: {customer_message[:50]}")

    _append_jsonl(FEEDBACK_LOG, {
        "timestamp": datetime.now().isoformat(),
        "type": "customer_positive",
        "from": from_email[:100],
        "user_message": customer_message[:500],
        "previous_response": ira_previous_response[:500],
        "generation_path": generation_path,
    })

    scores = _load_agent_scores()
    # Customer positive = moderate boost to all pipeline agents
    for agent_name in ["athena", "clio", "calliope", "vera"]:
        if agent_name in scores:
            old = scores[agent_name]["score"]
            scores[agent_name]["successes"] += 1
            scores[agent_name]["score"] = min(old + 0.01, 1.0)
    # If Iris was used (lead enrichment), boost Iris too
    if generation_path and ("iris" in generation_path.lower() or "enrich" in generation_path.lower()):
        if "iris" in scores:
            scores["iris"]["successes"] += 1
            scores["iris"]["score"] = min(scores["iris"]["score"] + 0.01, 1.0)
    _save_agent_scores(scores)
