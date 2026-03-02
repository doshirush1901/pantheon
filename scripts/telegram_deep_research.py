#!/usr/bin/env python3
"""
TELEGRAM DEEP RESEARCH - Deep Research Pipeline for Telegram
==============================================================

Connects Telegram messages to the Deep Research Pipeline.
This ensures Telegram users get the same thorough, multi-source answers as email.

Usage:
    # Direct call
    python scripts/telegram_deep_research.py --message "What is the price of PF1-C-2015?" --chat-id YOUR_CHAT_ID
    
    # As imported module
    from telegram_deep_research import process_telegram_message
    response = process_telegram_message(message="...", chat_id="...")
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/src/brain"))

# Load environment
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ira.telegram_deep")

# Import Deep Research Pipeline
try:
    from deep_research_pipeline import get_pipeline, DeepResearchResult
    DEEP_RESEARCH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Deep Research Pipeline not available: {e}")
    DEEP_RESEARCH_AVAILABLE = False

# Import Telegram bot for sending replies
TELEGRAM_BOT_AVAILABLE = False
telegram_bot = None

try:
    import telegram
    from telegram import Bot
    
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if TELEGRAM_TOKEN:
        telegram_bot = Bot(token=TELEGRAM_TOKEN)
        TELEGRAM_BOT_AVAILABLE = True
except ImportError:
    pass


def process_telegram_message(
    message: str,
    chat_id: str,
    user_name: str = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Process a Telegram message through the Deep Research Pipeline.
    
    Args:
        message: The user's message
        chat_id: Telegram chat ID
        user_name: Optional user name for personalization
        verbose: Whether to log detailed progress
    
    Returns:
        Dict with response, questions, confidence, etc.
    """
    result = {
        "success": False,
        "response": None,
        "questions_for_rushabh": [],
        "confidence": 0.0,
        "processing_time": 0.0,
        "error": None
    }
    
    if not DEEP_RESEARCH_AVAILABLE:
        result["error"] = "Deep Research Pipeline not available"
        return result
    
    try:
        logger.info("=" * 60)
        logger.info("TELEGRAM DEEP RESEARCH")
        logger.info("=" * 60)
        logger.info(f"Chat ID: {chat_id}")
        logger.info(f"User: {user_name or 'Unknown'}")
        logger.info(f"Message: {message[:100]}...")
        
        # Get the pipeline
        pipeline = get_pipeline()
        
        # Run deep research
        research_result = pipeline.research(
            query=message,
            user_id=str(chat_id),
            channel="telegram",
            verbose=verbose
        )
        
        # Build result
        result["success"] = True
        result["response"] = research_result.draft_response
        result["confidence"] = research_result.confidence
        result["processing_time"] = research_result.processing_time_seconds
        result["questions_for_rushabh"] = [
            {
                "question": q.question,
                "purpose": q.purpose,
                "priority": q.priority
            }
            for q in research_result.follow_up_questions
        ]
        result["understanding"] = {
            "intent": research_result.understanding.intent,
            "complexity": research_result.understanding.complexity,
            "entities": research_result.understanding.entities
        }
        result["sources_count"] = len(research_result.sources_used)
        
        logger.info(f"\nDeep research complete in {result['processing_time']:.1f}s")
        logger.info(f"Confidence: {result['confidence']:.2f}")
        
    except Exception as e:
        logger.error(f"Error in deep research: {e}")
        import traceback
        logger.error(traceback.format_exc())
        result["error"] = str(e)
    
    return result


async def send_telegram_reply(chat_id: str, response: str) -> bool:
    """Send a reply to Telegram chat."""
    if not TELEGRAM_BOT_AVAILABLE:
        logger.warning("Telegram bot not available")
        return False
    
    try:
        await telegram_bot.send_message(
            chat_id=int(chat_id),
            text=response,
            parse_mode="Markdown"
        )
        return True
    except Exception as e:
        logger.error(f"Error sending Telegram reply: {e}")
        return False


def format_response_for_telegram(result: Dict[str, Any]) -> str:
    """Format the response nicely for Telegram."""
    if not result["success"]:
        return f"Sorry, I encountered an error: {result.get('error', 'Unknown error')}"
    
    response = result["response"]
    
    # Add confidence indicator if low
    if result["confidence"] < 0.6:
        response += "\n\n⚠️ _Note: I'm not fully confident in this answer. Please verify with the team._"
    
    # Add processing time as subtle indicator
    response += f"\n\n_Researched in {result['processing_time']:.1f}s_"
    
    return response


def main():
    parser = argparse.ArgumentParser(description="Telegram Deep Research")
    parser.add_argument("--message", "-m", required=True, help="Message to process")
    parser.add_argument("--chat-id", "-c", required=True, help="Telegram chat ID")
    parser.add_argument("--user", "-u", default=None, help="User name")
    parser.add_argument("--send", action="store_true", help="Actually send reply via Telegram")
    parser.add_argument("--quiet", "-q", action="store_true", help="Less verbose output")
    
    args = parser.parse_args()
    
    # Process the message
    result = process_telegram_message(
        message=args.message,
        chat_id=args.chat_id,
        user_name=args.user,
        verbose=not args.quiet
    )
    
    # Print response
    print("\n" + "=" * 60)
    print("RESPONSE FOR TELEGRAM:")
    print("=" * 60)
    print(format_response_for_telegram(result))
    
    # Print questions for Rushabh
    if result.get("questions_for_rushabh"):
        print("\n" + "-" * 60)
        print("QUESTIONS FOR RUSHABH:")
        print("-" * 60)
        for q in result["questions_for_rushabh"]:
            print(f"  [{q['priority']}] {q['question']}")
    
    # Send if requested
    if args.send and result["success"]:
        import asyncio
        response_text = format_response_for_telegram(result)
        success = asyncio.run(send_telegram_reply(args.chat_id, response_text))
        if success:
            print(f"\n✅ Reply sent to Telegram chat {args.chat_id}")
        else:
            print(f"\n❌ Failed to send reply to Telegram")
    
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
