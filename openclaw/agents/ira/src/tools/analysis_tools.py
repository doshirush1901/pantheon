"""
Analysis Sandbox for Ira
========================

Lets Athena (the LLM orchestrator) write and execute Python code on the fly
to process data pulled from Gmail, CRM, finance tools, etc.

The code runs in an isolated subprocess with a strict timeout. Data from
previous tool calls can be passed in as a JSON string and is made available
to the script as the variable DATA (a parsed Python object).

Security:
  - Subprocess isolation (no exec/eval in the main process)
  - 60-second hard timeout
  - stdout/stderr captured and returned; nothing written to disk permanently
  - Internal-only: gated by is_internal flag in the orchestrator
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ira.analysis_tools")

TIMEOUT_SECONDS = 60
MAX_OUTPUT_CHARS = 8000
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent


def run_analysis(code: str, data: str = "") -> str:
    """Execute a Python script in a subprocess and return its stdout.

    Args:
        code: Python source code to execute.
        data: Optional JSON string injected as the variable DATA.

    Returns:
        Script stdout (truncated to 8000 chars), or error message.
    """
    if not code or not code.strip():
        return "(Error: no code provided)"

    preamble_lines = [
        "import sys, json, os, collections, re, math",
        "from datetime import datetime, timedelta",
    ]

    if data:
        escaped = json.dumps(data)
        # Try JSON parse first; fall back to raw string if it's not valid JSON
        preamble_lines.append(f"_raw_data = {escaped}")
        preamble_lines.append("try:")
        preamble_lines.append("    DATA = json.loads(_raw_data)")
        preamble_lines.append("except (json.JSONDecodeError, TypeError):")
        preamble_lines.append("    DATA = _raw_data")
    else:
        preamble_lines.append("DATA = None")

    preamble = "\n".join(preamble_lines) + "\n\n"
    full_code = preamble + code

    tmp_dir = tempfile.mkdtemp(prefix="ira_analysis_")
    script_path = os.path.join(tmp_dir, "analysis.py")

    try:
        with open(script_path, "w") as f:
            f.write(full_code)

        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=str(PROJECT_ROOT),
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            error_msg = stderr[-2000:] if stderr else "(no error output)"
            return f"(Script failed with exit code {result.returncode})\n{error_msg}"

        if not stdout:
            return "(Script produced no output. Add print() statements.)"

        if len(stdout) > MAX_OUTPUT_CHARS:
            return stdout[:MAX_OUTPUT_CHARS] + f"\n\n... (truncated, {len(stdout)} total chars)"

        return stdout

    except subprocess.TimeoutExpired:
        return f"(Script timed out after {TIMEOUT_SECONDS}s. Simplify the analysis or reduce data size.)"
    except Exception as e:
        logger.error(f"Analysis sandbox error: {e}")
        return f"(Analysis error: {e})"
    finally:
        try:
            os.unlink(script_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass
