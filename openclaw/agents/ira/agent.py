#!/usr/bin/env python3
"""
Ira CLI — Talk to Ira from your terminal.

Usage:
    ira                          # Interactive REPL
    ira "What machine for 4mm ABS?"   # One-shot question
    ira --cli                    # Interactive REPL (explicit)
    ira --status                 # Health check (Qdrant, Postgres, OpenAI)
"""

import argparse
import asyncio
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

import logging

logging.disable(logging.CRITICAL)

import warnings

warnings.filterwarnings("ignore")

import atexit
import io


def _suppress_shutdown_warnings():
    sys.stderr = io.StringIO()


atexit.register(_suppress_shutdown_warnings)

from openclaw.agents.ira import __version__


def _print_banner():
    print()
    print("  ╔═══════════════════════════════════════╗")
    print(f"  ║         Ira CLI v{__version__:<21s}║")
    print("  ╚═══════════════════════════════════════╝")
    print()


def _color(text: str, code: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def _green(text: str) -> str:
    return _color(text, "0;32")


def _red(text: str) -> str:
    return _color(text, "0;31")


def _yellow(text: str) -> str:
    return _color(text, "1;33")


def _dim(text: str) -> str:
    return _color(text, "0;90")


# ---------------------------------------------------------------------------
# Status / health check
# ---------------------------------------------------------------------------

def _check_status():
    _print_banner()
    print("  Checking services...\n")

    checks = []

    # OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key and len(api_key) > 10:
        checks.append(("OpenAI API Key", True, "configured"))
    else:
        checks.append(("OpenAI API Key", False, "missing — set OPENAI_API_KEY in .env"))

    # Qdrant
    try:
        import requests
        qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        r = requests.get(f"{qdrant_url}/healthz", timeout=3)
        if r.status_code == 200:
            checks.append(("Qdrant", True, qdrant_url))
        else:
            checks.append(("Qdrant", False, f"status {r.status_code} at {qdrant_url}"))
    except Exception as e:
        checks.append(("Qdrant", False, f"unreachable — {e}"))

    # PostgreSQL
    try:
        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url:
            checks.append(("PostgreSQL", None, "DATABASE_URL not set (optional)"))
        else:
            import psycopg2
            conn = psycopg2.connect(db_url, connect_timeout=3)
            conn.close()
            checks.append(("PostgreSQL", True, "connected"))
    except Exception as e:
        checks.append(("PostgreSQL", False, f"connection failed — {e}"))

    # Mem0
    mem0_key = os.environ.get("MEM0_API_KEY", "")
    if mem0_key and len(mem0_key) > 5:
        checks.append(("Mem0", True, "API key configured"))
    else:
        checks.append(("Mem0", None, "MEM0_API_KEY not set (optional)"))

    for name, ok, detail in checks:
        if ok is True:
            icon = _green("✓")
        elif ok is False:
            icon = _red("✗")
        else:
            icon = _yellow("–")
        print(f"    {icon}  {name:<20s} {_dim(detail)}")

    print()
    all_critical = all(ok for name, ok, _ in checks if name in ("OpenAI API Key", "Qdrant"))
    if all_critical:
        print(f"  {_green('Ready.')} Run {_dim('ira')} to start chatting.\n")
    else:
        print(f"  {_red('Not ready.')} Fix the issues above first.\n")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Core: call process_with_tools
# ---------------------------------------------------------------------------

_AGENT_ICONS = {
    "Clio": "📚", "Iris": "🌐", "Calliope": "✍️", "Vera": "✅",
    "Sophia": "🪞", "Mnemosyne": "🗄️", "Hermes": "📧", "Plutus": "💰",
    "Hephaestus": "🔨", "Prometheus": "🔭", "Sphinx": "❓",
    "Nemesis": "⚖️", "Quotebuilder": "📄", "Delphi": "🔮", "Athena": "🧠",
}


def _cli_progress(event):
    """Print agent activations inline during pipeline execution."""
    if isinstance(event, dict):
        agent = event.get("agent", "")
        activity = event.get("activity", "")
        etype = event.get("type", "")
        icon = _AGENT_ICONS.get(agent, "▸")
        if etype == "agent_activate":
            print(f"    {icon} {_dim(f'{agent} — {activity}')}")
        elif etype == "merging":
            print(f"    ⚡ {_dim('Merging agent findings...')}")
        elif etype == "packaging":
            print(f"    📦 {_dim('Packaging reply...')}")
    elif isinstance(event, str):
        print(f"    ▸ {_dim(event)}")


async def _ask(message: str, conversation_history: str) -> str:
    from openclaw.agents.ira.src.core.tool_orchestrator import process_with_tools

    context = {
        "channel": "cli",
        "user_id": "rushabh@cli",
        "is_internal": True,
        "conversation_history": conversation_history,
        "mem0_context": "",
        "identity": None,
        "personality_context": "",
        "_progress_callback": _cli_progress,
    }

    response = await process_with_tools(
        message=message,
        channel="cli",
        user_id="rushabh@cli",
        context=context,
    )
    return response


# ---------------------------------------------------------------------------
# One-shot mode
# ---------------------------------------------------------------------------

def _one_shot(question: str):
    print(f"\n  {_dim('Question:')} {question}\n")

    t0 = time.time()
    response = asyncio.run(_ask(question, ""))
    elapsed = time.time() - t0

    print(f"  {response}\n")
    print(f"  {_dim(f'({elapsed:.1f}s)')}\n")


# ---------------------------------------------------------------------------
# Interactive REPL
# ---------------------------------------------------------------------------

def _repl():
    _print_banner()
    print("  Type your question, or:")
    print(f"    {_dim('/quit')}     — exit")
    print(f"    {_dim('/status')}   — health check")
    print(f"    {_dim('/clear')}    — reset conversation")
    print()

    conversation_history = ""
    turn = 0

    while True:
        try:
            user_input = input(f"  {_green('You:')} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\n  {_dim('Bye!')}\n")
            break

        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd in ("/quit", "/exit", "/q", "quit", "exit"):
            print(f"\n  {_dim('Bye!')}\n")
            break
        if cmd in ("/status",):
            _check_status()
            continue
        if cmd in ("/clear", "/reset"):
            conversation_history = ""
            turn = 0
            print(f"\n  {_dim('Conversation cleared.')}\n")
            continue

        turn += 1
        t0 = time.time()

        try:
            response = asyncio.run(_ask(user_input, conversation_history))
        except KeyboardInterrupt:
            print(f"\n  {_yellow('Cancelled.')}\n")
            continue
        except Exception as e:
            print(f"\n  {_red(f'Error: {e}')}\n")
            continue

        elapsed = time.time() - t0
        print(f"\n  {response}")
        print(f"\n  {_dim(f'({elapsed:.1f}s)')}\n")

        conversation_history += f"User: {user_input}\nIra: {response}\n\n"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="ira",
        description="Ira — Intelligent Revenue Assistant CLI",
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="Question to ask (omit for interactive mode)",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Interactive REPL mode",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check service health",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show debug logs from the pipeline",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.disable(logging.NOTSET)
        logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    if args.status:
        _check_status()
        return

    question = " ".join(args.question).strip() if args.question else ""

    if question and not args.cli:
        _one_shot(question)
    else:
        _repl()


if __name__ == "__main__":
    main()
