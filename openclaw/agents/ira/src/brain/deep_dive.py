"""
Deep Dive - Conversational multi-topic research mode for Telegram.

Three-phase flow:
  Phase 1: CONVERSATION - Ira asks smart questions to expand the scope
  Phase 2: PLANNING - Athena breaks the request into parallel research tasks
  Phase 3: EXECUTION - Multiple research threads run, findings are cross-linked,
           and a long-form structured report is produced

Triggered by: /deepdive <topic> on Telegram
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("ira.deep_dive")


@dataclass
class DeepDiveSession:
    """Tracks a multi-turn deep dive session."""
    session_id: str
    original_query: str
    chat_id: str
    phase: str = "conversation"  # conversation, planning, researching, complete
    conversation: List[Dict[str, str]] = field(default_factory=list)
    research_plan: List[Dict[str, str]] = field(default_factory=list)
    findings: Dict[str, str] = field(default_factory=dict)
    final_report: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

_active_sessions: Dict[str, DeepDiveSession] = {}


def get_session(chat_id: str) -> Optional[DeepDiveSession]:
    return _active_sessions.get(chat_id)


def start_session(chat_id: str, query: str) -> str:
    """Start Phase 1: Ask smart questions to expand the scope."""
    session = DeepDiveSession(
        session_id=f"dd_{int(time.time())}",
        original_query=query,
        chat_id=chat_id,
        conversation=[{"role": "user", "content": query}],
    )
    _active_sessions[chat_id] = session

    questions = _generate_expansion_questions(query)
    session.conversation.append({"role": "assistant", "content": questions})

    return questions


def continue_conversation(chat_id: str, user_reply: str) -> Optional[str]:
    """Continue Phase 1 conversation, or transition to Phase 2 if ready."""
    session = _active_sessions.get(chat_id)
    if not session or session.phase != "conversation":
        return None

    session.conversation.append({"role": "user", "content": user_reply})

    go_keywords = ["go", "start", "do it", "yes", "let's go", "proceed", "research", "that's all", "enough", "ok go"]
    if any(kw in user_reply.lower().strip() for kw in go_keywords):
        session.phase = "planning"
        return None  # Signal to caller to start planning

    if len(session.conversation) >= 8:
        session.phase = "planning"
        return None

    follow_up = _generate_follow_up(session)
    session.conversation.append({"role": "assistant", "content": follow_up})
    return follow_up


def plan_research(chat_id: str) -> List[Dict[str, str]]:
    """Phase 2: Break the expanded request into parallel research tasks."""
    session = _active_sessions.get(chat_id)
    if not session:
        return []

    session.phase = "planning"
    plan = _generate_research_plan(session)
    session.research_plan = plan
    return plan


def execute_research(
    chat_id: str,
    on_progress: Optional[Callable[[str], None]] = None,
) -> str:
    """Phase 3: Execute all research tasks and produce a long-form report."""
    session = _active_sessions.get(chat_id)
    if not session:
        return "No active deep dive session."

    session.phase = "researching"

    try:
        from openclaw.agents.ira.src.brain.deep_research_engine import deep_research
    except ImportError:
        return "Deep research engine not available."

    all_findings = {}
    total_tasks = len(session.research_plan)

    for i, task in enumerate(session.research_plan):
        task_name = task.get("topic", f"Task {i+1}")
        task_query = task.get("query", task_name)

        if on_progress:
            on_progress(f"Researching ({i+1}/{total_tasks}): {task_name}")

        try:
            result = deep_research(
                query=task_query,
                max_iterations=4,
                max_time_seconds=90,
            )
            all_findings[task_name] = result.report
        except Exception as e:
            logger.warning(f"Research task failed: {task_name}: {e}")
            all_findings[task_name] = f"(Research failed: {e})"

    session.findings = all_findings

    if on_progress:
        on_progress("Synthesizing findings into report...")

    report = _synthesize_report(session)
    session.final_report = report
    session.phase = "complete"

    del _active_sessions[chat_id]

    return report


def cancel_session(chat_id: str) -> bool:
    if chat_id in _active_sessions:
        del _active_sessions[chat_id]
        return True
    return False


def _generate_expansion_questions(query: str) -> str:
    """Generate smart questions to expand the scope of the research."""
    try:
        import openai
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": (
                    "You are Athena, a strategic research planner for Machinecraft Technologies "
                    "(thermoforming machine manufacturer). The user wants a deep research dive.\n\n"
                    "Your job: ask 3-4 smart questions that will EXPAND the scope and make the "
                    "research more valuable. Think like a McKinsey consultant scoping an engagement.\n\n"
                    "Examples of good expansion questions:\n"
                    "- 'Should I also look at competitor activity in those regions?'\n"
                    "- 'Do you want me to include market size estimates?'\n"
                    "- 'Should I cross-reference with our order history to find patterns?'\n"
                    "- 'Want me to identify specific contacts at these companies?'\n\n"
                    "Be warm and direct. Start with 'Great topic!' or similar. "
                    "End with: 'Tell me what to include, or just say \"go\" and I\\'ll start researching!'"
                )},
                {"role": "user", "content": query},
            ],
            max_tokens=400,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Expansion question generation failed: {e}")
        return (
            f"Great topic! Before I dive deep into \"{query}\", a few questions:\n\n"
            "1. Any specific regions or markets to focus on?\n"
            "2. Should I include competitor analysis?\n"
            "3. Any time period to focus on (last year, last 5 years)?\n\n"
            "Tell me what to include, or just say \"go\" and I'll start researching!"
        )


def _generate_follow_up(session: DeepDiveSession) -> str:
    """Generate a follow-up question based on the conversation so far."""
    try:
        import openai
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

        messages = [
            {"role": "system", "content": (
                "You are Athena scoping a deep research project. Based on the conversation, "
                "ask ONE more focused question to refine the scope. Or if you have enough, "
                "say: 'Got it! I have a clear picture. Say \"go\" and I\\'ll start the deep dive.'"
            )},
        ]
        for turn in session.conversation:
            messages.append({"role": turn["role"], "content": turn["content"]})

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=200,
            temperature=0.5,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return "Got it! Say \"go\" and I'll start the deep dive."


def _generate_research_plan(session: DeepDiveSession) -> List[Dict[str, str]]:
    """Break the conversation into parallel research tasks."""
    try:
        import openai
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

        conv_text = "\n".join(
            f"{t['role'].upper()}: {t['content']}" for t in session.conversation
        )

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": (
                    "You are a research planner. Based on this conversation, create a research plan "
                    "with 3-6 parallel research tasks. Each task should be a specific, searchable topic.\n\n"
                    "Output as JSON array:\n"
                    '[{"topic": "Short name", "query": "Detailed search query", "rationale": "Why this matters"}]\n\n'
                    "Make tasks specific enough to search but broad enough to find useful data. "
                    "Include cross-cutting tasks like 'connections between X and Y' if relevant."
                )},
                {"role": "user", "content": f"CONVERSATION:\n{conv_text}"},
            ],
            max_tokens=800,
            temperature=0.3,
        )

        text = resp.choices[0].message.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        plan = json.loads(text)
        if isinstance(plan, list):
            return plan[:6]
    except Exception as e:
        logger.warning(f"Research plan generation failed: {e}")

    return [
        {"topic": "Main research", "query": session.original_query, "rationale": "Primary question"},
    ]


def _synthesize_report(session: DeepDiveSession) -> str:
    """Synthesize all findings into a long-form structured report."""
    try:
        import openai
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

        findings_text = ""
        for topic, report in session.findings.items():
            findings_text += f"\n\n## {topic}\n{report}"

        conv_text = "\n".join(
            f"{t['role'].upper()}: {t['content']}" for t in session.conversation
        )

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": (
                    "You are a senior consultant synthesizing research findings into a comprehensive report. "
                    "Create a well-structured, long-form report with:\n\n"
                    "1. Executive Summary (3-4 sentences)\n"
                    "2. Key Findings (organized by theme, not by research task)\n"
                    "3. Cross-connections (patterns across different findings)\n"
                    "4. Recommendations (actionable next steps)\n"
                    "5. Data Gaps (what we couldn't find)\n\n"
                    "Use markdown formatting. Be specific with data points. "
                    "Flag anything unverified. This should be a document worth reading, "
                    "not a summary of summaries.\n\n"
                    "IMPORTANT: Only include facts that appear in the research findings. "
                    "Do NOT fabricate data, company names, or statistics."
                )},
                {"role": "user", "content": (
                    f"ORIGINAL REQUEST:\n{conv_text}\n\n"
                    f"RESEARCH FINDINGS:\n{findings_text[:12000]}"
                )},
            ],
            max_tokens=4000,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Report synthesis failed: {e}")
        parts = ["# Deep Dive Report\n"]
        for topic, report in session.findings.items():
            parts.append(f"\n## {topic}\n{report}")
        return "\n".join(parts)
