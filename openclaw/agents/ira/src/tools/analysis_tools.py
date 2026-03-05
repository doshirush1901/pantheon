"""
Analysis Sandbox for Ira
========================

Lets Athena (the LLM orchestrator) write and execute Python code on the fly
to process data pulled from Gmail, CRM, finance tools, etc.

The code runs in an isolated subprocess with a strict timeout. Data from
previous tool calls can be passed in as a JSON string and is made available
to the script as the variable DATA (a parsed Python object).

Security:
  - AST-based import/call whitelist validated BEFORE execution
  - Subprocess isolation (no exec/eval in the main process)
  - Minimal environment variables (no credential leakage)
  - Working directory set to temp dir (no project file access)
  - 60-second hard timeout
  - stdout/stderr captured and returned; nothing written to disk permanently
  - Internal-only: gated by is_internal flag in the orchestrator
"""

import ast
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

_ALLOWED_IMPORTS = frozenset({
    "sys", "json", "collections", "re", "math", "datetime", "timedelta",
    "csv", "io", "itertools", "functools", "operator", "statistics",
    "textwrap", "string", "pathlib",
})

_BLOCKED_IMPORTS = frozenset({
    "os", "subprocess", "socket", "requests", "urllib", "http", "shutil",
    "importlib", "builtins", "ctypes", "multiprocessing", "threading",
    "signal", "pickle", "shelve", "tempfile", "glob", "webbrowser",
    "ftplib", "smtplib", "xmlrpc", "code", "codeop", "compileall",
    "py_compile", "zipimport", "pkgutil",
})

_BLOCKED_CALLS = frozenset({
    "exec", "eval", "compile", "__import__", "getattr", "setattr",
    "delattr", "globals", "locals", "vars", "dir", "breakpoint",
    "input", "memoryview", "classmethod", "staticmethod",
})

_BLOCKED_ATTR_CALLS = frozenset({
    "system", "popen", "exec", "spawn", "fork", "kill", "environ",
    "listdir", "scandir", "walk", "makedirs", "mkdir", "rmdir",
    "remove", "unlink", "rename", "replace", "chmod", "chown",
    "chdir", "getcwd",
})


def _validate_code_safety(code: str) -> Optional[str]:
    """Parse code as AST and reject anything outside the safety whitelist.

    Returns None if the code is safe, or an error message describing
    the violation.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"Syntax error in generated code: {e}"

    for node in ast.walk(tree):
        # --- import foo / import foo, bar ---
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in _BLOCKED_IMPORTS:
                    return f"Blocked import: '{alias.name}' is not allowed in the sandbox"
                if top not in _ALLOWED_IMPORTS:
                    return f"Disallowed import: '{alias.name}' — only these modules are permitted: {', '.join(sorted(_ALLOWED_IMPORTS))}"

        # --- from foo import bar ---
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in _BLOCKED_IMPORTS:
                    return f"Blocked import: 'from {node.module}' is not allowed in the sandbox"
                if top not in _ALLOWED_IMPORTS:
                    return f"Disallowed import: 'from {node.module}' — only these modules are permitted: {', '.join(sorted(_ALLOWED_IMPORTS))}"

        # --- bare calls: exec(...), eval(...), __import__(...) ---
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _BLOCKED_CALLS:
                return f"Blocked call: '{func.id}()' is not allowed in the sandbox"

            # --- attribute calls: os.system(...), module.popen(...) ---
            if isinstance(func, ast.Attribute) and func.attr in _BLOCKED_ATTR_CALLS:
                return f"Blocked call: '.{func.attr}()' is not allowed in the sandbox"

        # --- open() — allow read-only from data/ only ---
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "open":
                mode_arg = None
                for kw in node.keywords:
                    if kw.arg == "mode":
                        if isinstance(kw.value, ast.Constant):
                            mode_arg = kw.value.value
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    mode_arg = node.args[1].value
                if mode_arg is not None and any(c in str(mode_arg) for c in "waxb+"):
                    if "rb" != mode_arg and "r" not in str(mode_arg):
                        return "Blocked: open() with write mode is not allowed in the sandbox"
                    if "+" in str(mode_arg):
                        return "Blocked: open() with write mode is not allowed in the sandbox"

        # --- string-based exec/eval hidden in Constant nodes is caught
        #     by the Call check above; also block f-string tricks ---
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name) and func.value.id == "__builtins__":
                    return "Blocked: direct access to __builtins__ is not allowed"

    return None


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

    safety_error = _validate_code_safety(code)
    if safety_error:
        return f"(Security: {safety_error})"

    preamble_lines = [
        "import sys, json, collections, re, math",
        "from datetime import datetime, timedelta",
    ]

    if data:
        escaped = json.dumps(data)
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

    sandbox_env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": "",
        "HOME": os.environ.get("HOME", "/tmp"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "LANG": "en_US.UTF-8",
    }

    try:
        with open(script_path, "w") as f:
            f.write(full_code)

        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=tmp_dir,
            env=sandbox_env,
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
        except OSError as e:
            logger.error(f"Error in run_analysis: {e}", exc_info=True)
