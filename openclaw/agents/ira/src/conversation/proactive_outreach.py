"""
Proactive Outreach Scheduler
============================

Previously we detected who needs outreach but didn't actually send it.
This module schedules and triggers proactive messages.

Features:
1. Scheduled checks for outreach candidates
2. Rate limiting to avoid spamming
3. Time-based sending (respect user's active hours)
4. Integration with Telegram for actual sending

Usage:
    scheduler = OutreachScheduler()
    scheduler.start()  # Starts background checking
    
    # Or manually trigger check
    scheduler.check_and_send()
"""

import logging
import os
import json
import threading

logger = logging.getLogger(__name__)
import time
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from collections import defaultdict


@dataclass
class OutreachCandidate:
    """A contact that might benefit from proactive outreach."""
    contact_id: str
    name: str
    reasons: List[str]
    priority_score: float
    channel: str = "telegram"
    telegram_id: Optional[str] = None
    email: Optional[str] = None
    last_contacted: Optional[datetime] = None
    suggested_message: str = ""


@dataclass
class OutreachConfig:
    """Configuration for outreach scheduler."""
    enabled: bool = True
    check_interval_minutes: int = 60
    min_hours_between_outreach: int = 48
    max_outreach_per_day: int = 5
    active_hours_start: int = 9
    active_hours_end: int = 18
    priority_threshold: float = 2.0
    require_approval: bool = True


class OutreachScheduler:
    """
    Schedules and manages proactive outreach.
    
    Checks for candidates periodically and either:
    - Queues them for approval (if require_approval=True)
    - Sends them directly (if require_approval=False)
    """
    
    def __init__(
        self,
        config: OutreachConfig = None,
        storage_path: str = None,
        send_callback: Callable[[str, str, str], bool] = None,
    ):
        self.config = config or OutreachConfig()
        
        if storage_path is None:
            base_dir = Path(__file__).parent.parent.parent.parent.parent
            storage_path = str(base_dir / "data" / "outreach_state.json")
        
        self.storage_path = storage_path
        self.send_callback = send_callback  # (channel, recipient, message) -> bool
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Load state
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load scheduler state from disk."""
        try:
            with open(self.storage_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError, FileNotFoundError):
            return {
                "sent_today": [],
                "queued": [],
                "last_check": None,
                "daily_count": 0,
                "daily_reset_date": datetime.now().strftime("%Y-%m-%d"),
            }
    
    def _save_state(self):
        """Save state to disk."""
        Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def start(self):
        """Start the background scheduler."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Started background scheduler")
    
    def stop(self):
        """Stop the background scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Stopped")
    
    def _run_loop(self):
        """Background loop that checks for outreach candidates."""
        while self._running:
            try:
                # Check if within active hours
                now = datetime.now()
                if self.config.active_hours_start <= now.hour < self.config.active_hours_end:
                    self.check_and_queue()
                
                # Sleep until next check
                time.sleep(self.config.check_interval_minutes * 60)
            except Exception as e:
                logger.error("Error in loop: %s", e)
                time.sleep(300)  # Wait 5 min on error
    
    def check_and_queue(self) -> List[OutreachCandidate]:
        """
        Check for outreach candidates and queue them.
        
        Returns list of queued candidates.
        """
        # Reset daily counter if new day
        today = datetime.now().strftime("%Y-%m-%d")
        if self.state.get("daily_reset_date") != today:
            self.state["daily_count"] = 0
            self.state["sent_today"] = []
            self.state["daily_reset_date"] = today
        
        # Check if we've hit daily limit
        if self.state["daily_count"] >= self.config.max_outreach_per_day:
            return []
        
        # Get candidates
        candidates = self._get_candidates()
        
        # Filter already contacted recently
        filtered = []
        for candidate in candidates:
            if candidate.contact_id in self.state["sent_today"]:
                continue
            if self._recently_contacted(candidate.contact_id):
                continue
            if candidate.priority_score < self.config.priority_threshold:
                continue
            filtered.append(candidate)
        
        # Queue top candidates
        slots_available = self.config.max_outreach_per_day - self.state["daily_count"]
        to_queue = filtered[:slots_available]
        
        for candidate in to_queue:
            self._queue_candidate(candidate)
        
        self.state["last_check"] = datetime.now().isoformat()
        self._save_state()
        
        return to_queue
    
    def _get_candidates(self) -> List[OutreachCandidate]:
        """Get outreach candidates from the conversational enhancer."""
        try:
            from .replika_integration import create_enhancer
            enhancer = create_enhancer()
            raw_candidates = enhancer.get_proactive_outreach_candidates()
            
            candidates = []
            for raw in raw_candidates:
                # Get contact details
                contact_id = raw.get("contact_id", "")
                
                # Try to get telegram_id or email
                telegram_id = None
                email = None
                
                try:
                    from unified_identity import get_identity_service
                    identity_svc = get_identity_service()
                    contact = identity_svc.get_contact(contact_id)
                    if contact:
                        telegram_id = contact.telegram_id
                        email = contact.email
                except (ImportError, AttributeError):
                    pass
                
                # Generate suggested message
                suggested_message = self._generate_outreach_message(raw)
                
                candidates.append(OutreachCandidate(
                    contact_id=contact_id,
                    name=raw.get("name", contact_id),
                    reasons=raw.get("reasons", []),
                    priority_score=raw.get("priority_score", 0),
                    telegram_id=telegram_id,
                    email=email,
                    suggested_message=suggested_message,
                ))
            
            return sorted(candidates, key=lambda x: x.priority_score, reverse=True)
        except Exception as e:
            logger.error("Error getting candidates: %s", e)
            return []
    
    def _generate_outreach_message(self, candidate_data: Dict) -> str:
        """Generate a suggested outreach message."""
        reasons = candidate_data.get("reasons", [])
        name = candidate_data.get("name", "")
        
        if not reasons:
            return f"Hi{' ' + name if name else ''}! Just checking in - is there anything I can help with?"
        
        # Tailor message to reason
        reason = reasons[0].lower()
        
        if "follow-up" in reason or "followup" in reason:
            return f"Hi{' ' + name if name else ''}! I wanted to follow up on our earlier conversation. Is there anything else you need?"
        
        if "milestone" in reason:
            return f"Hi{' ' + name if name else ''}! I noticed we've been working together for a while. Thank you for your continued trust!"
        
        if "haven't connected" in reason or "stale" in reason:
            return f"Hi{' ' + name if name else ''}! It's been a while since we last spoke. How are things going?"
        
        if "at risk" in reason or "declining" in reason:
            return f"Hi{' ' + name if name else ''}! I wanted to check in and see if there's anything I can do better to help you."
        
        return f"Hi{' ' + name if name else ''}! Just reaching out to see if there's anything I can help with today."
    
    def _recently_contacted(self, contact_id: str) -> bool:
        """Check if we recently sent outreach to this contact."""
        try:
            from .relationship_store import get_relationship_store
            store = get_relationship_store()
            
            with store._get_conn() as conn:
                row = conn.execute("""
                    SELECT last_interaction FROM relationship_state
                    WHERE contact_id = ?
                """, (contact_id,)).fetchone()
                
                if row and row["last_interaction"]:
                    last = datetime.fromisoformat(row["last_interaction"])
                    hours_since = (datetime.now() - last).total_seconds() / 3600
                    return hours_since < self.config.min_hours_between_outreach
        except (ValueError, KeyError, TypeError):
            pass
        
        return False
    
    def _queue_candidate(self, candidate: OutreachCandidate):
        """Add candidate to outreach queue."""
        self.state["queued"].append({
            "contact_id": candidate.contact_id,
            "name": candidate.name,
            "reasons": candidate.reasons,
            "priority_score": candidate.priority_score,
            "telegram_id": candidate.telegram_id,
            "email": candidate.email,
            "suggested_message": candidate.suggested_message,
            "queued_at": datetime.now().isoformat(),
        })
        logger.info("Queued outreach for %s: %s", candidate.name, candidate.reasons)
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def get_queue(self) -> List[Dict]:
        """Get current outreach queue."""
        return self.state.get("queued", [])
    
    def approve_and_send(self, contact_id: str, custom_message: str = None) -> bool:
        """
        Approve and send outreach to a contact.
        
        Returns True if sent successfully.
        """
        # Find in queue
        queued_item = None
        for item in self.state["queued"]:
            if item["contact_id"] == contact_id:
                queued_item = item
                break
        
        if not queued_item:
            return False
        
        message = custom_message or queued_item["suggested_message"]
        
        # Determine channel and recipient
        if queued_item.get("telegram_id"):
            channel = "telegram"
            recipient = queued_item["telegram_id"]
        elif queued_item.get("email"):
            channel = "email"
            recipient = queued_item["email"]
        else:
            logger.warning("No channel for %s", contact_id)
            return False
        
        # Send via callback
        success = False
        if self.send_callback:
            try:
                success = self.send_callback(channel, recipient, message)
            except Exception as e:
                logger.error("Send failed: %s", e)
        
        if success:
            # Remove from queue
            self.state["queued"] = [
                q for q in self.state["queued"] 
                if q["contact_id"] != contact_id
            ]
            self.state["sent_today"].append(contact_id)
            self.state["daily_count"] += 1
            self._save_state()
            
            # Record the interaction
            self._record_outreach(contact_id, message)
        
        return success
    
    def dismiss(self, contact_id: str):
        """Dismiss a queued outreach without sending."""
        self.state["queued"] = [
            q for q in self.state["queued"]
            if q["contact_id"] != contact_id
        ]
        self._save_state()
    
    def _record_outreach(self, contact_id: str, message: str):
        """Record that we sent outreach."""
        try:
            from .relationship_store import get_relationship_store
            store = get_relationship_store()
            
            store.update_relationship_state(
                contact_id=contact_id,
                last_interaction=datetime.now().isoformat(),
            )
            
            store.record_pattern(
                contact_id=contact_id,
                pattern_type="outreach",
                pattern_key="proactive_sent",
                metadata={"message_preview": message[:100]}
            )
        except Exception as e:
            logger.error("Record failed: %s", e)
    
    def get_stats(self) -> Dict:
        """Get scheduler statistics."""
        return {
            "enabled": self.config.enabled,
            "running": self._running,
            "daily_count": self.state.get("daily_count", 0),
            "daily_limit": self.config.max_outreach_per_day,
            "queue_size": len(self.state.get("queued", [])),
            "last_check": self.state.get("last_check"),
        }


# Module-level singleton
_scheduler: Optional[OutreachScheduler] = None


def get_outreach_scheduler() -> OutreachScheduler:
    """Get or create the outreach scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = OutreachScheduler()
    return _scheduler


def start_outreach_scheduler():
    """Start the background outreach scheduler."""
    scheduler = get_outreach_scheduler()
    scheduler.start()


def get_outreach_queue() -> List[Dict]:
    """Get the current outreach queue."""
    return get_outreach_scheduler().get_queue()


def approve_outreach(contact_id: str, custom_message: str = None) -> bool:
    """Approve and send outreach."""
    return get_outreach_scheduler().approve_and_send(contact_id, custom_message)


# =============================================================================
# CLI for OpenClaw skill
# =============================================================================

if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Proactive Outreach Skill")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Run command - scan for candidates
    run_parser = subparsers.add_parser("run", help="Scan for outreach candidates")
    run_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Suggest command - get suggestions for a user
    suggest_parser = subparsers.add_parser("suggest", help="Get outreach suggestions")
    suggest_parser.add_argument("--user-id", required=True, help="User ID to get suggestions for")
    suggest_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Queue command - show current queue
    queue_parser = subparsers.add_parser("queue", help="Show outreach queue")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show scheduler stats")
    
    args = parser.parse_args()
    scheduler = get_outreach_scheduler()
    
    if args.command == "run":
        candidates = scheduler.find_outreach_candidates()
        if args.json:
            print(json.dumps({
                "candidates_found": len(candidates),
                "candidates": [{"contact_id": c.get("contact_id"), "reason": c.get("reason")} for c in candidates[:10]],
            }, indent=2))
        else:
            print(f"Found {len(candidates)} outreach candidates")
            for c in candidates[:5]:
                print(f"  - {c.get('contact_id')}: {c.get('reason', 'N/A')}")
    
    elif args.command == "suggest":
        queue = scheduler.get_queue()
        user_suggestions = [q for q in queue if q.get("contact_id") == args.user_id]
        if args.json:
            print(json.dumps({"user_id": args.user_id, "suggestions": user_suggestions}, indent=2))
        else:
            if user_suggestions:
                for s in user_suggestions:
                    print(f"Suggestion for {args.user_id}: {s.get('reason', 'Follow-up recommended')}")
            else:
                print(f"No pending outreach for {args.user_id}")
    
    elif args.command == "queue":
        queue = scheduler.get_queue()
        print(json.dumps({"queue_size": len(queue), "items": queue[:10]}, indent=2))
    
    elif args.command == "stats":
        stats = scheduler.get_stats()
        print(json.dumps(stats, indent=2))
