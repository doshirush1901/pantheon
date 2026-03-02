#!/usr/bin/env python3
"""
Ira Quickstart — Minimal example of using Ira programmatically.

Prerequisites:
    1. pip install -r requirements.txt
    2. Copy .env.example to .env and fill in your API keys
    3. docker-compose up -d  (starts Qdrant)
    4. python scripts/ingest_all_imports.py  (first run only)

Usage:
    python examples/quickstart.py
    python examples/quickstart.py "What machine for 4mm ABS?"
"""

import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()


async def ask_ira(question: str) -> str:
    """Send a question to Ira's tool orchestrator and get a response."""
    from openclaw.agents.ira.src.core.tool_orchestrator import process_with_tools

    response = await process_with_tools(
        message=question,
        channel="api",
        user_id="quickstart@example.com",
    )
    return response


async def main():
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What machines does Machinecraft make?"

    print(f"\n  Question: {question}\n")
    print("  Thinking...\n")

    response = await ask_ira(question)

    print(f"  Ira: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())
