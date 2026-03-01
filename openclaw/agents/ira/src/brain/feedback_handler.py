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


def detect_feedback(message: str) -> Tuple[Optional[str], float]:
    """Detect if a message is positive or negative feedback.
    
    Returns: (feedback_type, confidence) where feedback_type is 'positive', 'negative', or None.
    """
    msg_lower = message.lower().strip()

    if len(msg_lower) < 3:
        return None, 0.0

    pos_hits = sum(1 for p in POSITIVE_PATTERNS if p in msg_lower)
    neg_hits = sum(1 for p in NEGATIVE_PATTERNS if p in msg_lower)

    if pos_hits == 0 and neg_hits == 0:
        return None, 0.0

    if pos_hits > neg_hits:
        confidence = min(0.5 + pos_hits * 0.15, 0.95)
        return "positive", confidence
    elif neg_hits > pos_hits:
        confidence = min(0.5 + neg_hits * 0.15, 0.95)
        return "negative", confidence
    else:
        return None, 0.0


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

    return "Glad that helped! I'll keep doing more of this."


def handle_negative_feedback(
    user_message: str,
    previous_response: str,
    generation_path: str,
    chat_id: str = "",
) -> str:
    """Handle negative feedback: log mistake, get coach analysis, queue for dream learning.
    
    Returns an acknowledgment with what Ira learned.
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

    # Get coach analysis
    coach_analysis = _get_coach_analysis(user_message, previous_response)
    if coach_analysis:
        feedback_entry["coach_analysis"] = coach_analysis

    _append_jsonl(FEEDBACK_LOG, feedback_entry)

    # Queue for dream-mode learning
    dream_entry = {
        "timestamp": datetime.now().isoformat(),
        "source": "telegram_negative_feedback",
        "user_feedback": user_message[:1000],
        "ira_response": previous_response[:1000],
        "coach_analysis": coach_analysis or "",
        "status": "pending",
    }
    _append_jsonl(DREAM_BACKLOG, dream_entry)

    # Log to mistake log for brain_rewire
    _log_mistake(user_message, previous_response, coach_analysis)

    # Reduce agent scores
    scores = _load_agent_scores()
    agents_used = _identify_agents_used(generation_path)
    for agent_name in agents_used:
        if agent_name in scores:
            old = scores[agent_name]["score"]
            scores[agent_name]["failures"] += 1
            scores[agent_name]["score"] = max(old - 0.03, 0.1)
            logger.info(f"[FEEDBACK] Reduced {agent_name}: {old:.2f} -> {scores[agent_name]['score']:.2f}")
    _save_agent_scores(scores)

    ack = "I hear you. I've logged this and will learn from it."
    if coach_analysis:
        ack += f"\n\nMy coach says: {coach_analysis[:200]}"
    ack += "\n\nI'll work on this during my next dream cycle."
    return ack


def _identify_agents_used(generation_path: str) -> List[str]:
    """Identify which agents were involved based on the generation path."""
    path_lower = (generation_path or "").lower()
    agents = ["athena"]
    if "research" in path_lower or "clio" in path_lower:
        agents.append("clio")
    if "write" in path_lower or "calliope" in path_lower:
        agents.append("calliope")
    if "verify" in path_lower or "vera" in path_lower or "fact" in path_lower:
        agents.append("vera")
    if "iris" in path_lower or "web" in path_lower:
        agents.append("iris")
    if "agent" in path_lower or "tool" in path_lower:
        agents.extend(["clio", "calliope", "vera"])
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
