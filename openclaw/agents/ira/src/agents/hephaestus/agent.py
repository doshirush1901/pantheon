"""
Hephaestus — The Divine Forge
=============================

God of the forge, craftsman of the gods. When Athena needed a shield,
when Hermes needed winged sandals, when Achilles needed armor — they
went to Hephaestus. He builds things.

In Ira's pantheon, Hephaestus is the program-builder. When any agent
needs to compute, transform, aggregate, or analyze data that can't be
done in a single tool call, Athena delegates to Hephaestus. He:

  1. Takes a task description + raw data from previous tool calls
  2. Writes a Python program to accomplish the task
  3. Executes it in a sandboxed subprocess (60s timeout)
  4. Returns the computed result

He can also be called directly with pre-written code when Athena
already knows what program to run.

Usage:
    from openclaw.agents.ira.src.agents.hephaestus.agent import forge

    # Mode 1: Athena provides a task, Hephaestus writes the code
    result = await forge(
        task="Group these emails by sender domain, count per company, rank top 10",
        data=raw_email_output,
        context={"user_id": "rushabh", "channel": "telegram"},
    )

    # Mode 2: Athena provides the code directly
    result = await forge(
        code="for item in sorted(DATA, key=...): print(...)",
        data=json_string,
        context={},
    )
"""

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("ira.agents.hephaestus")


async def forge(
    task: str = "",
    code: str = "",
    data: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Hephaestus forges a program and executes it.

    Args:
        task: Natural-language description of what to compute. Hephaestus
              will use an LLM to generate the Python code. Mutually
              exclusive with `code` (if both provided, `code` wins).
        code: Pre-written Python code to execute directly.
        data: Raw data string (JSON or plain text) from previous tool calls.
              Made available as the variable DATA in the script.
        context: Execution context (user_id, channel, etc.).

    Returns:
        The stdout of the executed program, or an error message.
    """
    context = context or {}

    if not code and not task:
        return "(Hephaestus needs either a task description or code to execute.)"

    if not code:
        code = await _generate_code(task, data)
        if not code:
            return "(Hephaestus could not generate code for this task.)"
        logger.info(f"[Hephaestus] Generated {len(code)} chars of code for: {task[:80]}")

    from openclaw.agents.ira.src.tools.analysis_tools import run_analysis
    result = run_analysis(code=code, data=data)

    if result.startswith("(Script failed"):
        logger.warning(f"[Hephaestus] First attempt failed, retrying with fix...")
        fixed_code = await _fix_code(code, result, task or "execute the provided code", data)
        if fixed_code and fixed_code != code:
            result = run_analysis(code=fixed_code, data=data)

    return result


async def _generate_code(task: str, data: str) -> str:
    """Use LLM to generate Python code for a task.

    Hephaestus is a craftsman, not a chatbot. He generates clean,
    focused Python that prints its results to stdout.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return ""

    try:
        import openai
        client = openai.AsyncOpenAI(api_key=api_key)

        data_preview = data[:3000] if data else "(no data provided)"

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _FORGE_SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"TASK:\n{task}\n\n"
                    f"DATA PREVIEW (first 3000 chars):\n{data_preview}"
                )},
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        raw = response.choices[0].message.content.strip()
        return _extract_code(raw)
    except Exception as e:
        logger.error(f"[Hephaestus] Code generation failed: {e}")
        return ""


async def _fix_code(code: str, error: str, task: str, data: str) -> str:
    """Attempt to fix broken code based on the error message."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return ""

    try:
        import openai
        client = openai.AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _FORGE_SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"TASK:\n{task}\n\n"
                    f"BROKEN CODE:\n```python\n{code}\n```\n\n"
                    f"ERROR:\n{error[-1500:]}\n\n"
                    f"DATA PREVIEW:\n{data[:1500] if data else '(none)'}\n\n"
                    f"Fix the code. Return ONLY the corrected Python."
                )},
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        raw = response.choices[0].message.content.strip()
        return _extract_code(raw)
    except Exception as e:
        logger.error(f"[Hephaestus] Code fix failed: {e}")
        return ""


def _extract_code(raw: str) -> str:
    """Extract Python code from LLM response, stripping markdown fences."""
    if "```python" in raw:
        parts = raw.split("```python")
        if len(parts) > 1:
            code_block = parts[1].split("```")[0]
            return code_block.strip()
    if "```" in raw:
        parts = raw.split("```")
        if len(parts) > 1:
            return parts[1].strip()
    return raw


_FORGE_SYSTEM_PROMPT = """You are Hephaestus, the program-builder for Ira (Machinecraft's AI assistant).

Your job: write a Python script that accomplishes the given TASK using the given DATA.

RULES:
- Write ONLY Python code. No explanations, no markdown (unless wrapping in ```python).
- The variable DATA is pre-loaded with the input data (parsed JSON if valid, raw string otherwise).
- Use print() to output results. The stdout IS the result.
- Available imports (pre-loaded): sys, json, os, collections, re, math, datetime, timedelta
- You can import standard library modules (csv, statistics, itertools, etc.)
- Do NOT import external packages (no pandas, numpy, requests, etc.)
- Handle edge cases: DATA might be None, empty, or malformed.
- Format output for readability: use aligned columns, separators, numbered lists.
- Keep code concise. No classes unless needed. Prefer functions for clarity.
- If DATA is a string with structured text (like email listings), parse it with regex or string splitting.
- For rankings/tables, include a header and separator line.
- Always handle the case where DATA has fewer items than expected."""
