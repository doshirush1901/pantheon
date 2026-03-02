#!/usr/bin/env python3
"""
IRA EMAIL CONVERSATION LOOP - Startup Script
============================================

Automated email conversation system with closed-loop learning.

CRITICAL RULE: Ira must ALWAYS be the LAST one to send a message in any thread.

When Rushabh replies, Ira will:
1. LEARN - Extract and store learnings from the reply
2. INTROSPECT - Consider alternative perspectives
3. ADD VALUE - Share insights and knowledge
4. ASK COUNTER-QUESTIONS - Continue the dialogue

Architecture:
┌─────────────────────────────────────────────────────────────────────┐
│                    EMAIL CONVERSATION LOOP                         │
│            (Ira ALWAYS replies - never leaves a thread)            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │ Gmail Inbox  │───▶│  Gmail Watcher   │───▶│ Incoming Email   │  │
│  │  (Rushabh)   │    │  (polls inbox)   │    │   Parsed         │  │
│  └──────────────┘    └──────────────────┘    └────────┬─────────┘  │
│                                                        │            │
│                                                        ▼            │
│                                             ┌──────────────────┐   │
│                                             │ Feedback Learner │   │
│                                             │ - Learn from msg │   │
│                                             │ - Extract facts  │   │
│                                             │ - Find questions │   │
│                                             │ - Note strategy  │   │
│                                             └────────┬─────────┘   │
│                                                       │            │
│     ┌─────────────────────────────────────────────────┼───────┐    │
│     │                                                 ▼       │    │
│     │  MEM0 MEMORY                     ┌──────────────────┐  │    │
│     │  ┌────────────────┐              │  Store Learnings │  │    │
│     │  │ Past learnings │◀────────────│  (persistent)    │  │    │
│     │  │ Preferences    │              └──────────────────┘  │    │
│     │  │ Corrections    │                                    │    │
│     │  └────────────────┘                                    │    │
│     └────────────────────────────────────────────────────────┘    │
│                                                        │            │
│                                                        ▼            │
│                                             ┌──────────────────┐   │
│                                             │ Response Gen     │   │
│                                             │ - Acknowledge    │   │
│                                             │ - Add insight    │   │
│                                             │ - Ask questions  │   │
│                                             └────────┬─────────┘   │
│                                                       │            │
│                                                       ▼            │
│                                             ┌──────────────────┐   │
│                                             │ Email Polish     │   │
│                                             │ - Brand voice    │   │
│                                             │ - Ira personality│   │
│                                             │ - Remove clichés │   │
│                                             └────────┬─────────┘   │
│                                                       │            │
│                                                       ▼            │
│  ┌──────────────┐    ┌──────────────────┐   ┌──────────────────┐  │
│  │ Rushabh gets │◀───│   Gmail Send     │◀──│   Final Reply    │  │
│  │    reply     │    │  (ALWAYS sends)  │   │ (NEVER skipped)  │  │
│  └──────────────┘    └──────────────────┘   └──────────────────┘  │
│                              │                                     │
│                              ▼                                     │
│                    [Loop continues when                            │
│                     Rushabh replies]                               │
└────────────────────────────────────────────────────────────────────┘

Usage:
    # Check once
    python scripts/start_email_loop.py --once
    
    # Run continuously (every 60s)
    python scripts/start_email_loop.py --loop
    
    # Run with custom interval
    python scripts/start_email_loop.py --loop --interval 120
    
    # Dry run (don't send replies)
    python scripts/start_email_loop.py --once --dry-run
"""

import os
import sys
from pathlib import Path

# Setup project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ[key.strip()] = value.strip().strip('"')

# Import the conversation loop
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/src/email_channel"))

if __name__ == "__main__":
    from email_conversation_loop import EmailConversationLoop, main
    
    import argparse
    parser = argparse.ArgumentParser(
        description="Ira Email Conversation Loop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--once", action="store_true", help="Check once and exit")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Don't send replies")
    
    args = parser.parse_args()
    
    print("""
╔════════════════════════════════════════════════════════════════════╗
║              IRA EMAIL CONVERSATION LOOP                           ║
║                                                                    ║
║  Automated replies with closed-loop learning                       ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    loop = EmailConversationLoop()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - replies will not be sent\n")
    
    if args.loop:
        loop.run_loop(interval_seconds=args.interval)
    else:
        loop.check_and_process()
        loop.print_stats()
