#!/usr/bin/env python3
"""
TELEGRAM FEEDBACK HANDLER
==========================

Process feedback from Telegram messages through the Feedback Processing Pipeline.

This script can be:
1. Called directly from Telegram bridge when feedback is detected
2. Used as a standalone CLI tool for testing
3. Integrated into OpenClaw agent workflows

Usage:
    python telegram_feedback_handler.py --feedback "No, the PF1-C-2015 is ₹60L" --user "123456789"
    python telegram_feedback_handler.py --test
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/src/brain"))

# Load environment
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("telegram_feedback")

# Import the pipeline
try:
    from feedback_processing_pipeline import (
        FeedbackProcessor,
        FeedbackResult,
        get_processor
    )
    PIPELINE_AVAILABLE = True
    logger.info("Feedback Processing Pipeline loaded")
except ImportError as e:
    PIPELINE_AVAILABLE = False
    logger.error(f"Failed to load pipeline: {e}")

# Telegram Bot
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_ENABLED = bool(TELEGRAM_TOKEN)


def process_telegram_feedback(
    feedback: str,
    user_id: str,
    original_response: str = "",
    chat_id: Optional[str] = None
) -> Optional[str]:
    """
    Process feedback from Telegram through the full pipeline.
    
    Args:
        feedback: The feedback message from user
        user_id: Telegram user ID
        original_response: IRA's original response being corrected
        chat_id: Optional chat ID for sending reply
    
    Returns:
        Confirmation message or None if failed
    """
    if not PIPELINE_AVAILABLE:
        return "Sorry, feedback processing is temporarily unavailable."
    
    logger.info(f"\n{'=' * 60}")
    logger.info("TELEGRAM FEEDBACK HANDLER")
    logger.info(f"{'=' * 60}")
    logger.info(f"User: {user_id}")
    logger.info(f"Feedback: {feedback[:100]}...")
    
    try:
        processor = get_processor()
        
        result = processor.process(
            feedback_message=feedback,
            original_response=original_response,
            from_user=f"telegram:{user_id}",
            channel="telegram",
            verbose=True
        )
        
        if result.success:
            logger.info(f"✅ Processed: {len(result.corrections_found)} corrections")
            logger.info(f"Updates: {result.updates_applied}")
            
            # Format for Telegram (shorter than email)
            confirmation = format_telegram_confirmation(result)
            
            # Send back to Telegram if enabled
            if chat_id and TELEGRAM_ENABLED:
                send_telegram_message(chat_id, confirmation)
            
            return confirmation
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        return None


def format_telegram_confirmation(result: FeedbackResult) -> str:
    """Format confirmation message for Telegram (shorter than email)."""
    
    if not result.corrections_found:
        return "Thanks for the feedback! I've noted it down. 📝"
    
    correction = result.corrections_found[0]  # Show first one
    
    if correction.feedback_type.value == "positive_feedback":
        return "Thanks! Glad I could help 😊"
    
    lines = ["Got it! I've learned:\n"]
    
    for c in result.corrections_found[:2]:  # Max 2 for Telegram
        lines.append(f"📝 *{c.topic}*")
        if c.incorrect_value and c.correct_value:
            lines.append(f"   ❌ {c.incorrect_value}")
            lines.append(f"   ✅ {c.correct_value}")
    
    lines.append("\nI won't make this mistake again! 🙏")
    
    return "\n".join(lines)


def send_telegram_message(chat_id: str, text: str) -> bool:
    """Send message to Telegram chat."""
    if not TELEGRAM_ENABLED:
        return False
    
    try:
        import requests
        
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def detect_feedback(message: str) -> bool:
    """Detect if a message is feedback/correction."""
    indicators = [
        "that's wrong", "that is wrong", "not correct",
        "no, it", "no that", "actually,", "should be",
        "fix this", "correct this", "wrong price",
        "wrong answer", "you made up", "is a competitor",
        "is our customer", "remember this", "don't ",
        "stop ", "always ", "never "
    ]
    
    message_lower = message.lower()
    return any(ind in message_lower for ind in indicators)


# =============================================================================
# TELEGRAM BRIDGE INTEGRATION
# =============================================================================

class TelegramFeedbackBridge:
    """
    Bridge for handling Telegram feedback.
    
    Can be integrated with existing Telegram handlers.
    """
    
    def __init__(self):
        self.processor = get_processor() if PIPELINE_AVAILABLE else None
        self.conversation_history = {}  # Track for context
    
    def handle_message(
        self,
        message: str,
        user_id: str,
        chat_id: str
    ) -> Optional[str]:
        """
        Handle incoming Telegram message.
        
        Returns feedback confirmation if it's feedback, None otherwise.
        """
        # Check if it's feedback
        if not detect_feedback(message):
            return None
        
        # Get previous response for context
        prev_response = self.conversation_history.get(
            f"{user_id}:{chat_id}", {}
        ).get("response", "")
        
        # Process feedback
        return process_telegram_feedback(
            feedback=message,
            user_id=user_id,
            original_response=prev_response,
            chat_id=chat_id
        )
    
    def record_response(
        self,
        user_id: str,
        chat_id: str,
        query: str,
        response: str
    ):
        """Record IRA's response for future feedback context."""
        key = f"{user_id}:{chat_id}"
        self.conversation_history[key] = {
            "query": query,
            "response": response
        }


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telegram Feedback Handler")
    parser.add_argument("--feedback", "-f", help="Feedback message to process")
    parser.add_argument("--original", "-o", default="", help="Original response")
    parser.add_argument("--user", "-u", default="telegram_user", help="User ID")
    parser.add_argument("--chat", "-c", default="", help="Chat ID for reply")
    parser.add_argument("--test", action="store_true", help="Run test cases")
    
    args = parser.parse_args()
    
    if args.test:
        # Test cases
        test_cases = [
            ("No, the PF1-C-2015 is ₹60 Lakhs not ₹65 Lakhs", "Price is ₹65 Lakhs"),
            ("Kiefel is a competitor", "Consider Kiefel"),
            ("Thanks, perfect answer!", "The machine costs ₹60L"),
        ]
        
        for feedback, original in test_cases:
            print(f"\n{'=' * 60}")
            print(f"FEEDBACK: {feedback}")
            result = process_telegram_feedback(
                feedback=feedback,
                user_id="test_user",
                original_response=original
            )
            print(f"\nRESULT:\n{result}")
            print("=" * 60)
    
    elif args.feedback:
        result = process_telegram_feedback(
            feedback=args.feedback,
            user_id=args.user,
            original_response=args.original,
            chat_id=args.chat if args.chat else None
        )
        print(f"\n{result}")
    
    else:
        parser.print_help()
