#!/usr/bin/env python3
"""CLI interface for Mem0 memory operations, used by OpenClaw skills."""

import argparse
import json
import sys
import os

# Ensure the project root is in the Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from src.memory.unified_mem0 import get_unified_mem0


def main():
    parser = argparse.ArgumentParser(description="Mem0 Memory CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Recall command
    recall_parser = subparsers.add_parser("recall", help="Recall memories by query")
    recall_parser.add_argument("--query", required=True, help="Search query")
    recall_parser.add_argument("--user-id", required=True, help="User identifier")

    # Search command (alias for recall)
    search_parser = subparsers.add_parser("search", help="Search memories by query")
    search_parser.add_argument("--query", required=True, help="Search query")
    search_parser.add_argument("--user-id", required=True, help="User identifier")

    # Store command
    store_parser = subparsers.add_parser("store", help="Store a new memory")
    store_parser.add_argument("--text", required=True, help="Text to store")
    store_parser.add_argument("--user-id", required=True, help="User identifier")

    args = parser.parse_args()

    try:
        mem0 = get_unified_mem0()
    except Exception as e:
        print(json.dumps({"error": f"Failed to initialize Mem0: {str(e)}"}))
        sys.exit(1)

    if args.command in ("recall", "search"):
        results = mem0.search(query=args.query, user_id=args.user_id)
        print(json.dumps(results, indent=2, default=str))

    elif args.command == "store":
        user_message = f"Please remember: {args.text}"
        assistant_response = "Noted and stored."
        mem0.remember(
            user_message=user_message,
            assistant_response=assistant_response,
            user_id=args.user_id
        )
        print(json.dumps({"status": "stored", "text": args.text}))


if __name__ == "__main__":
    main()
