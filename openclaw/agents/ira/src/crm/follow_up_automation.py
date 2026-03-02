#!/usr/bin/env python3
"""
PROACTIVE FOLLOW-UP AUTOMATION
===============================

Automatically identifies stale quotes and generates follow-up suggestions.
Integrates with dream mode for nightly review.

Usage:
    from follow_up_automation import FollowUpEngine, get_engine
    
    engine = get_engine()
    
    # Get follow-up suggestions
    suggestions = engine.generate_suggestions()
    
    # Queue for morning review
    engine.queue_for_review(suggestions)
    
    # Send via Telegram for approval
    engine.send_daily_digest()
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from enum import Enum

SKILL_DIR = Path(__file__).parent
SKILLS_DIR = SKILL_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

# Load env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

sys.path.insert(0, str(SKILL_DIR))

from quote_lifecycle import get_tracker, Quote, QuoteStatus


class FollowUpPriority(Enum):
    """Priority level for follow-ups."""
    HIGH = "high"      # High-value quote, long silence
    MEDIUM = "medium"  # Regular quote, needs attention
    LOW = "low"        # Recent or low-value


class FollowUpReason(Enum):
    """Reason for suggesting follow-up."""
    STALE = "stale"                    # No response for a while
    HIGH_VALUE = "high_value"          # Large deal worth pursuing
    MULTIPLE_FOLLOW_UPS = "multi_fu"   # Already followed up, still no response
    COMPETITOR_RISK = "competitor"     # May be comparing options
    DECISION_TIMELINE = "timeline"     # Near their decision date


@dataclass
class FollowUpSuggestion:
    """A suggested follow-up action."""
    quote_id: str
    customer_email: str
    customer_name: Optional[str]
    company: Optional[str]
    product: str
    quote_amount: float
    currency: str
    
    # Follow-up details
    priority: FollowUpPriority
    reason: FollowUpReason
    days_since_activity: int
    follow_up_count: int
    
    # Suggested action
    suggested_action: str
    suggested_message: str
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "quote_id": self.quote_id,
            "customer_email": self.customer_email,
            "customer_name": self.customer_name,
            "company": self.company,
            "product": self.product,
            "quote_amount": self.quote_amount,
            "currency": self.currency,
            "priority": self.priority.value,
            "reason": self.reason.value,
            "days_since_activity": self.days_since_activity,
            "follow_up_count": self.follow_up_count,
            "suggested_action": self.suggested_action,
            "suggested_message": self.suggested_message,
            "created_at": self.created_at.isoformat(),
        }
    
    def to_telegram_message(self) -> str:
        """Format for Telegram notification."""
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[self.priority.value]
        
        msg = f"{priority_emoji} *{self.quote_id}*\n"
        msg += f"   {self.customer_name or self.customer_email}"
        if self.company:
            msg += f" ({self.company})"
        msg += f"\n   {self.product} - ${self.quote_amount:,.0f}\n"
        msg += f"   📅 {self.days_since_activity}d inactive"
        if self.follow_up_count > 0:
            msg += f", {self.follow_up_count} follow-ups"
        msg += f"\n   💡 {self.suggested_action}"
        
        return msg


class FollowUpEngine:
    """
    Generates smart follow-up suggestions based on quote lifecycle data.
    """
    
    # Thresholds
    STALE_DAYS = 7           # Days without activity to consider stale
    HIGH_VALUE_USD = 30000   # Quotes above this get priority
    MAX_FOLLOW_UPS = 5       # Stop suggesting after this many
    
    # Message templates
    TEMPLATES = {
        "initial_check": [
            "Hi {name}, just checking in on the {product} quote I sent last week. Do you have any questions or need any clarifications?",
            "Hi {name}, wanted to follow up on the {product} quotation. Happy to discuss any aspects or arrange a call if that would help.",
        ],
        "second_follow_up": [
            "Hi {name}, following up on our {product} discussion. I'm available to address any concerns or provide additional information.",
            "Hi {name}, just a gentle nudge on the {product} quote. If timing has changed, let me know and I can adjust accordingly.",
        ],
        "high_value": [
            "Hi {name}, I wanted to personally follow up on the {product} project. Given the scope, I'd be happy to arrange a call with our technical team.",
            "Hi {name}, checking in on your {product} requirements. We're holding a favorable pricing window and wanted to ensure you had all the information needed.",
        ],
        "re_engagement": [
            "Hi {name}, it's been a while since we discussed {product}. If your requirements have changed, I'd be happy to revise the proposal.",
            "Hi {name}, just touching base on the {product} inquiry. If you're still evaluating options, I'd welcome the chance to address any concerns.",
        ],
    }
    
    def __init__(self):
        self.tracker = get_tracker()
        self._suggestions_queue: List[FollowUpSuggestion] = []
    
    def generate_suggestions(self, max_suggestions: int = 10) -> List[FollowUpSuggestion]:
        """
        Analyze quotes and generate follow-up suggestions.
        
        Returns prioritized list of suggested follow-ups.
        """
        suggestions = []
        
        # Get stale quotes
        stale_quotes = self.tracker.get_stale_quotes(days=self.STALE_DAYS)
        
        for quote in stale_quotes:
            # Skip if already too many follow-ups
            if quote.follow_up_count >= self.MAX_FOLLOW_UPS:
                continue
            
            suggestion = self._create_suggestion(quote)
            if suggestion:
                suggestions.append(suggestion)
        
        # Sort by priority and value
        suggestions.sort(
            key=lambda s: (
                {"high": 0, "medium": 1, "low": 2}[s.priority.value],
                -s.quote_amount,
            )
        )
        
        return suggestions[:max_suggestions]
    
    def _create_suggestion(self, quote: Quote) -> Optional[FollowUpSuggestion]:
        """Create a follow-up suggestion for a quote."""
        days_inactive = quote.days_since_follow_up() or 0
        
        # Determine priority
        priority = self._calculate_priority(quote, days_inactive)
        
        # Determine reason
        reason = self._determine_reason(quote, days_inactive)
        
        # Generate suggested message
        action, message = self._generate_suggestion(quote, reason)
        
        return FollowUpSuggestion(
            quote_id=quote.quote_id,
            customer_email=quote.customer_email,
            customer_name=quote.customer_name,
            company=quote.company,
            product=quote.product,
            quote_amount=quote.amount,
            currency=quote.currency,
            priority=priority,
            reason=reason,
            days_since_activity=days_inactive,
            follow_up_count=quote.follow_up_count,
            suggested_action=action,
            suggested_message=message,
        )
    
    def _calculate_priority(self, quote: Quote, days_inactive: int) -> FollowUpPriority:
        """Calculate follow-up priority."""
        # High value quotes are always high priority
        if quote.amount >= self.HIGH_VALUE_USD:
            return FollowUpPriority.HIGH
        
        # Long silence with previous follow-ups is concerning
        if days_inactive >= 14 and quote.follow_up_count >= 2:
            return FollowUpPriority.HIGH
        
        # Moderate delay
        if days_inactive >= 10 or quote.follow_up_count >= 1:
            return FollowUpPriority.MEDIUM
        
        return FollowUpPriority.LOW
    
    def _determine_reason(self, quote: Quote, days_inactive: int) -> FollowUpReason:
        """Determine the main reason for follow-up."""
        if quote.amount >= self.HIGH_VALUE_USD:
            return FollowUpReason.HIGH_VALUE
        
        if quote.follow_up_count >= 2:
            return FollowUpReason.MULTIPLE_FOLLOW_UPS
        
        if days_inactive >= 21:
            return FollowUpReason.COMPETITOR_RISK
        
        return FollowUpReason.STALE
    
    def _generate_suggestion(
        self, 
        quote: Quote, 
        reason: FollowUpReason
    ) -> tuple[str, str]:
        """Generate action and message suggestion."""
        import random
        
        name = (quote.customer_name or "").split()[0] if quote.customer_name else "there"
        product = quote.product
        
        # Select template based on situation
        if reason == FollowUpReason.HIGH_VALUE:
            templates = self.TEMPLATES["high_value"]
            action = "Send personalized high-value follow-up"
        elif quote.follow_up_count == 0:
            templates = self.TEMPLATES["initial_check"]
            action = "Send initial check-in"
        elif quote.follow_up_count == 1:
            templates = self.TEMPLATES["second_follow_up"]
            action = "Send second follow-up"
        else:
            templates = self.TEMPLATES["re_engagement"]
            action = "Attempt re-engagement"
        
        message = random.choice(templates).format(name=name, product=product)
        
        return action, message
    
    def queue_for_review(self, suggestions: List[FollowUpSuggestion]) -> None:
        """Queue suggestions for morning review."""
        self._suggestions_queue = suggestions
    
    def get_queued_suggestions(self) -> List[FollowUpSuggestion]:
        """Get queued suggestions."""
        return self._suggestions_queue
    
    def clear_queue(self) -> None:
        """Clear the suggestions queue."""
        self._suggestions_queue = []
    
    def send_daily_digest(self) -> bool:
        """
        Send daily follow-up digest via Telegram.
        Called by dream mode in the morning.
        """
        suggestions = self.generate_suggestions(max_suggestions=5)
        
        if not suggestions:
            return True  # Nothing to report
        
        try:
            import requests
            
            telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            chat_id = os.environ.get("ADMIN_TELEGRAM_ID", os.environ.get("RUSHABH_TELEGRAM_ID", ""))
            
            if not telegram_token:
                return False
            
            # Build message
            high = sum(1 for s in suggestions if s.priority == FollowUpPriority.HIGH)
            med = sum(1 for s in suggestions if s.priority == FollowUpPriority.MEDIUM)
            
            message = f"📋 *Follow-Up Digest*\n"
            message += f"━━━━━━━━━━━━━━━\n"
            message += f"🔴 {high} high priority, 🟡 {med} medium\n\n"
            
            for suggestion in suggestions[:5]:
                message += suggestion.to_telegram_message() + "\n\n"
            
            message += "_Reply with quote ID to see details or draft a follow-up_"
            
            response = requests.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
            
            return response.ok
            
        except Exception as e:
            print(f"[follow_up] Telegram send error: {e}")
            return False
    
    def record_follow_up_sent(
        self, 
        quote_id: str, 
        channel: str = "email",
        notes: str = ""
    ) -> bool:
        """Record that a follow-up was sent."""
        result = self.tracker.record_follow_up(quote_id, channel, notes)
        return result is not None


# Singleton
_engine: Optional[FollowUpEngine] = None


def get_engine() -> FollowUpEngine:
    """Get singleton follow-up engine."""
    global _engine
    if _engine is None:
        _engine = FollowUpEngine()
    return _engine


def run_daily_follow_up_check() -> Dict[str, Any]:
    """
    Run daily follow-up check (called by dream mode).
    
    Returns summary of suggestions generated.
    """
    engine = get_engine()
    suggestions = engine.generate_suggestions()
    
    result = {
        "suggestions_generated": len(suggestions),
        "high_priority": sum(1 for s in suggestions if s.priority == FollowUpPriority.HIGH),
        "medium_priority": sum(1 for s in suggestions if s.priority == FollowUpPriority.MEDIUM),
        "low_priority": sum(1 for s in suggestions if s.priority == FollowUpPriority.LOW),
        "digest_sent": False,
    }
    
    if suggestions:
        result["digest_sent"] = engine.send_daily_digest()
    
    return result


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Follow-Up Automation")
    parser.add_argument("--suggestions", action="store_true", help="Generate suggestions")
    parser.add_argument("--digest", action="store_true", help="Send daily digest")
    parser.add_argument("--max", type=int, default=10, help="Max suggestions")
    args = parser.parse_args()
    
    engine = get_engine()
    
    if args.suggestions:
        suggestions = engine.generate_suggestions(max_suggestions=args.max)
        print(f"\n📋 Follow-Up Suggestions ({len(suggestions)})")
        print("=" * 50)
        
        for s in suggestions:
            print(s.to_telegram_message())
            print(f"   📝 Message: {s.suggested_message[:60]}...")
            print()
    
    elif args.digest:
        print("Sending daily digest...")
        success = engine.send_daily_digest()
        print(f"Digest sent: {'✅' if success else '❌'}")
    
    else:
        parser.print_help()
