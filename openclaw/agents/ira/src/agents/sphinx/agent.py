"""
Sphinx — The Gatekeeper of Clarity
===================================

Sphinx is the mythical guardian who poses questions before granting passage.
She intercepts complex but vague requests before they enter Athena's tool loop,
asks a batch of numbered clarifying questions, and only releases an enriched
brief to Athena once the user has answered.

Usage:
    from openclaw.agents.ira.src.agents.sphinx import (
        should_clarify,
        generate_questions,
        merge_brief,
        detect_task_type,
    )

    if await should_clarify(message, conversation_history):
        questions = await generate_questions(message, detect_task_type(message))
        # Send formatted questions to user; on reply, merge_brief(original, questions, reply)
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.sphinx")

try:
    from openclaw.agents.ira.config import get_openai_client, FAST_LLM_MODEL, get_logger
    logger = get_logger("ira.sphinx")
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    FAST_LLM_MODEL = "gpt-4o-mini"

# Task types for question generation checklists
TASK_TYPES = [
    "sales",       # machine recommendation, quote, application
    "email",       # draft email, outreach, follow-up
    "research",    # research company, market, topic
    "finance",     # order book, cashflow, revenue
    "crm",         # leads, pipeline, customers
    "general",     # other
]

CLARIFY_SYSTEM = """You are a classifier for a B2B assistant (Ira at Machinecraft Technologies).
Given the user's message, decide if it is TOO VAGUE to act on well — i.e. critical details are missing for the implied task.

Return ONLY a JSON object: {"needs_clarification": true or false, "task_type": "sales"|"email"|"research"|"finance"|"crm"|"general"}

Rules:
- If the message already has enough specifics (company name, machine model, material, recipient, time period, etc.) to act on, return needs_clarification: false.
- If the message is ambiguous (e.g. "research that German company", "send a follow-up to the packaging lead", "what's our financial position" without time scope), return needs_clarification: true.
- task_type: sales = machine recommendation/quote/application; email = draft/send/follow-up; research = research company/topic; finance = order book/cashflow/revenue; crm = leads/pipeline/customers; general = other."""

QUESTIONS_SYSTEM = """You are Sphinx, the gatekeeper of clarity for Ira (Machinecraft Technologies).
Given the user's message and its task type, generate 3-8 SHORT clarifying questions. Only ask about what is genuinely MISSING — do not repeat info the user already gave.

Rules:
- Maximum 8 questions. Prefer 4-6.
- Each question must be one line, concise, no preamble.
- Return ONLY a JSON array of question strings, e.g. ["Question 1?", "Question 2?"]
- For sales: application, material, thickness, sheet size, depth, budget.
- For email: recipient (who), purpose/context, key points, tone.
- For research: which company/topic, what to find, purpose.
- For finance: time period, which metric, comparison basis.
- For crm: which leads/region/stage, what action.
- Do not ask generic questions like "Can you tell me more?" — be specific."""

MERGE_SYSTEM = """You are assembling a brief for an AI assistant (Athena). The user originally asked something vague; they then answered numbered clarifying questions. Merge the original request with the Q&A into a single, structured brief that Athena can act on without re-reading the conversation.

Format the brief as clear sections, e.g.:
TASK: [one line summary]
[RELEVANT SECTION]: [answer from user]
...

Include every answered question as a section. Keep it concise but complete. Output ONLY the brief, no meta-commentary."""


def _get_client():
    if CONFIG_AVAILABLE:
        return get_openai_client()
    try:
        from openai import OpenAI
        return OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    except Exception:
        return None


def detect_task_type(message: str) -> str:
    """Heuristic detection of task type from message content (no LLM). Used when we already know we need to clarify."""
    m = message.lower().strip()
    if any(w in m for w in ["draft", "email", "send to", "follow-up", "follow up", "outreach", "write to"]):
        return "email"
    if any(w in m for w in ["research", "find out", "look up", "intel", "what do we know"]):
        return "research"
    if any(w in m for w in ["order book", "cashflow", "revenue", "financial", "outstanding", "receivables"]):
        return "finance"
    if any(w in m for w in ["lead", "pipeline", "crm", "customer list", "drip", "follow up"]):
        return "crm"
    if any(w in m for w in ["machine", "recommend", "quote", "price", "thermoform", "material", "thickness", "pf1", "pf2", "am-"]):
        return "sales"
    return "general"


async def should_clarify(message: str, conversation_history: str = "") -> bool:
    """Fast GPT-4o-mini call: is this request too vague to act on well?"""
    client = _get_client()
    if not client:
        return False
    try:
        user_content = f"User message:\n{message}\n"
        if conversation_history:
            user_content += f"\nRecent conversation (for context only):\n{conversation_history[:800]}"
        response = client.chat.completions.create(
            model=FAST_LLM_MODEL,
            messages=[
                {"role": "system", "content": CLARIFY_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=80,
            temperature=0,
        )
        text = (response.choices[0].message.content or "").strip()
        # Handle markdown code block
        if "```" in text:
            text = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
        data = json.loads(text)
        return bool(data.get("needs_clarification", False))
    except Exception as e:
        logger.warning("[Sphinx] should_clarify failed: %s", e)
        return False


async def generate_questions(message: str, task_type: str) -> List[str]:
    """Generate 3-8 numbered clarifying questions based on what's missing for the task type."""
    client = _get_client()
    if not client:
        return []
    try:
        user_content = f"Task type: {task_type}\n\nUser message:\n{message}"
        response = client.chat.completions.create(
            model=FAST_LLM_MODEL,
            messages=[
                {"role": "system", "content": QUESTIONS_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=400,
            temperature=0.3,
        )
        text = (response.choices[0].message.content or "").strip()
        if "```" in text:
            text = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
        questions = json.loads(text)
        if not isinstance(questions, list):
            return []
        # Cap at 8, ensure strings
        out = [str(q).strip() for q in questions[:8] if q]
        return out
    except Exception as e:
        logger.warning("[Sphinx] generate_questions failed: %s", e)
        return []


def merge_brief(original_message: str, questions: List[str], answers: str) -> str:
    """Merge original request + Q&A into a clean enriched brief for Athena."""
    client = _get_client()
    if not client:
        return _merge_brief_fallback(original_message, questions, answers)
    try:
        user_content = f"Original request:\n{original_message}\n\nQuestions we asked:\n" + "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions)) + f"\n\nUser's reply (numbered answers):\n{answers}"
        response = client.chat.completions.create(
            model=FAST_LLM_MODEL,
            messages=[
                {"role": "system", "content": MERGE_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1024,
            temperature=0.2,
        )
        brief = (response.choices[0].message.content or "").strip()
        if brief:
            return brief
    except Exception as e:
        logger.warning("[Sphinx] merge_brief LLM failed: %s", e)
    return _merge_brief_fallback(original_message, questions, answers)


def _merge_brief_fallback(original_message: str, questions: List[str], answers: str) -> str:
    """Fallback: simple concatenation when LLM merge is unavailable."""
    lines = [f"TASK: {original_message}", "", "USER ANSWERS (from clarification):"]
    # Parse loose numbered lines from answers (e.g. "1. ABS 2. 4mm" or "1. ABS\n2. 4mm")
    answer_lines = []
    for part in re.split(r"\s*(?=\d+[.)]\s*)", answers):
        part = part.strip()
        if part:
            answer_lines.append(part)
    for i, q in enumerate(questions):
        ans = answer_lines[i] if i < len(answer_lines) else "(not answered)"
        lines.append(f"Q{i+1}. {q}\nA: {ans}")
    return "\n".join(lines)


def format_questions_for_user(questions: List[str]) -> str:
    """Format the question list as a single message with intro and reply instruction."""
    if not questions:
        return ""
    intro = "Before I dig in, I need a few details. Answer whichever apply:\n\n"
    numbered = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    outro = "\n\nReply with numbered answers (e.g. '1. ABS, 2. 4mm') and I'll get to work."
    return intro + numbered + outro
