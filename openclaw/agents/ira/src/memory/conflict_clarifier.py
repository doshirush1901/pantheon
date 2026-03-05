#!/usr/bin/env python3
"""
CONFLICT CLARIFIER - Telegram-Based Memory Conflict Resolution

╔════════════════════════════════════════════════════════════════════╗
║  When conflicts are detected in Ira's memory, this system:         ║
║  1. Sends a Telegram message asking for clarification              ║
║  2. Parses your response (1, 2, or custom merge)                   ║
║  3. Updates memory based on your decision                          ║
╚════════════════════════════════════════════════════════════════════╝

Telegram Commands:
    /conflicts - Show all pending conflicts
    /resolve <id> <1|2|merge> - Resolve a specific conflict
    
Response Patterns:
    "1" or "keep first" → Keep existing fact
    "2" or "use new" → Use the new fact
    "merge: <your text>" → Use custom merged text
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# Import from centralized config via brain_orchestrator
try:
    from config import PROJECT_ROOT
except ImportError:
    from pathlib import Path
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent

# Telegram config (not in brain_orchestrator, load from env)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
CONFLICT_QUEUE_PATH = PROJECT_ROOT / "openclaw/agents/ira/workspace/conflict_queue.json"


# =============================================================================
# CONFLICT QUEUE MANAGEMENT
# =============================================================================

class ConflictQueue:
    """Manages the queue of pending conflicts."""
    
    def __init__(self, queue_path: Path = CONFLICT_QUEUE_PATH):
        self.queue_path = queue_path
        
    def _load_queue(self) -> List[Dict]:
        if not self.queue_path.exists():
            return []
        try:
            return json.loads(self.queue_path.read_text())
        except (json.JSONDecodeError, IOError, OSError):
            return []
    
    def _save_queue(self, queue: List[Dict]):
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self.queue_path.write_text(json.dumps(queue, indent=2))
    
    def get_pending(self) -> List[Dict]:
        """Get all unresolved conflicts."""
        queue = self._load_queue()
        return [c for c in queue if not c.get("resolved")]
    
    def get_conflict(self, conflict_id: str) -> Optional[Dict]:
        """Get a specific conflict by ID."""
        queue = self._load_queue()
        for c in queue:
            if c.get("conflict_id") == conflict_id:
                return c
        return None
    
    def resolve(self, conflict_id: str, resolution: str, merged_text: str = None) -> bool:
        """
        Resolve a conflict.
        
        Args:
            conflict_id: The conflict ID
            resolution: "keep_existing", "use_new", or "merge"
            merged_text: Custom text if resolution is "merge"
        """
        queue = self._load_queue()
        
        for conflict in queue:
            if conflict.get("conflict_id") == conflict_id:
                if conflict.get("resolved"):
                    return False  # Already resolved
                
                conflict["resolved"] = True
                conflict["resolution"] = resolution
                conflict["resolved_at"] = datetime.now().isoformat()
                
                if merged_text:
                    conflict["merged_text"] = merged_text
                
                # Apply to memory
                self._apply_resolution(conflict, resolution, merged_text)
                
                self._save_queue(queue)
                return True
        
        return False
    
    def _apply_resolution(self, conflict: Dict, resolution: str, merged_text: str = None):
        """Apply the resolution to persistent memory."""
        try:
            try:
                from .persistent_memory import PersistentMemory
            except ImportError:
                from persistent_memory import PersistentMemory
            pm = PersistentMemory()
            
            if resolution == "keep_existing":
                # No change needed
                pass
                
            elif resolution == "use_new":
                # Update existing memory with new fact
                pm.update_entity_memory(
                    conflict["existing_fact_id"],
                    conflict["new_fact"]
                )
                
            elif resolution == "merge" and merged_text:
                # Update with merged text
                pm.update_entity_memory(
                    conflict["existing_fact_id"],
                    merged_text
                )
                
        except Exception as e:
            logger.error("Error applying resolution: %s", e)
    
    def add_conflict(self, 
                     entity_name: str,
                     existing_fact: str,
                     existing_fact_id: int,
                     new_fact: str,
                     conflict_type: str,
                     source_document: str) -> str:
        """Add a new conflict to the queue."""
        import uuid
        
        conflict_id = str(uuid.uuid4())[:8]
        
        queue = self._load_queue()
        queue.append({
            "conflict_id": conflict_id,
            "entity_name": entity_name,
            "existing_fact": existing_fact,
            "existing_fact_id": existing_fact_id,
            "new_fact": new_fact,
            "conflict_type": conflict_type,
            "source_document": source_document,
            "created_at": datetime.now().isoformat(),
            "resolved": False
        })
        
        self._save_queue(queue)
        return conflict_id


# =============================================================================
# TELEGRAM INTEGRATION
# =============================================================================

class TelegramClarifier:
    """Sends conflict clarification requests via Telegram."""
    
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.queue = ConflictQueue()
        
        # Track which conflicts have been sent
        self._sent_conflicts_path = PROJECT_ROOT / "openclaw/agents/ira/workspace/sent_conflicts.json"
    
    def _send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send a message via Telegram."""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram not configured")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            resp = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode
            }, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error("Telegram send failed: %s", e)
            return False
    
    def send_conflict_for_clarification(self, conflict: Dict) -> bool:
        """Send a single conflict to Telegram for clarification."""
        conflict_id = conflict.get("conflict_id", "?")
        entity = conflict.get("entity_name", "Unknown")
        existing = conflict.get("existing_fact", "")
        new = conflict.get("new_fact", "")
        source = conflict.get("source_document", "document")
        conflict_type = conflict.get("conflict_type", "conflict")
        
        # Format message
        message = f"""⚠️ **MEMORY CONFLICT DETECTED**

**Entity:** {entity}
**Type:** {conflict_type}
**Source:** {source}

**[1] EXISTING FACT (in memory):**
_{existing}_

**[2] NEW FACT (from document):**
_{new}_

---
**Reply with:**
• `1` - Keep existing fact
• `2` - Use new fact  
• `merge: <your text>` - Custom merged version

**Conflict ID:** `{conflict_id}`"""
        
        success = self._send_message(message)
        
        if success:
            # Track that we've sent this
            self._mark_conflict_sent(conflict_id)
        
        return success
    
    def _mark_conflict_sent(self, conflict_id: str):
        """Mark a conflict as sent to avoid duplicates."""
        sent = self._get_sent_conflicts()
        if conflict_id not in sent:
            sent.append(conflict_id)
            self._sent_conflicts_path.parent.mkdir(parents=True, exist_ok=True)
            self._sent_conflicts_path.write_text(json.dumps(sent))
    
    def _get_sent_conflicts(self) -> List[str]:
        """Get list of already-sent conflict IDs."""
        if not self._sent_conflicts_path.exists():
            return []
        try:
            return json.loads(self._sent_conflicts_path.read_text())
        except (json.JSONDecodeError, IOError, OSError):
            return []
    
    def send_all_pending(self) -> int:
        """Send all pending conflicts that haven't been sent yet."""
        sent_ids = self._get_sent_conflicts()
        pending = self.queue.get_pending()
        
        count = 0
        for conflict in pending:
            if conflict.get("conflict_id") not in sent_ids:
                if self.send_conflict_for_clarification(conflict):
                    count += 1
        
        return count
    
    def format_conflicts_summary(self) -> str:
        """Format all pending conflicts as a summary message."""
        pending = self.queue.get_pending()
        
        if not pending:
            return "✅ No pending conflicts in memory."
        
        lines = [f"📋 **{len(pending)} PENDING CONFLICTS**\n"]
        
        for i, conflict in enumerate(pending, 1):
            conflict_id = conflict.get("conflict_id", "?")
            entity = conflict.get("entity_name", "Unknown")
            existing = conflict.get("existing_fact", "")[:50]
            new = conflict.get("new_fact", "")[:50]
            
            lines.append(f"**{i}. [{conflict_id}] {entity}**")
            lines.append(f"   Old: _{existing}..._")
            lines.append(f"   New: _{new}..._")
            lines.append("")
        
        lines.append("Use `/resolve <id> <1|2|merge>` to resolve")
        
        return "\n".join(lines)
    
    def parse_resolution_response(self, text: str, conflict_id: str = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Parse a user's resolution response.
        
        Returns: (conflict_id, resolution, merged_text)
        """
        text = text.strip().lower()
        
        # Direct responses: "1" or "2"
        if text in ["1", "keep", "keep existing", "first"]:
            return conflict_id, "keep_existing", None
        
        if text in ["2", "new", "use new", "second"]:
            return conflict_id, "use_new", None
        
        # Merge response: "merge: <text>"
        if text.startswith("merge:"):
            merged_text = text[6:].strip()
            return conflict_id, "merge", merged_text
        
        # Command format: /resolve <id> <decision>
        resolve_match = re.match(r'/resolve\s+(\w+)\s+(.+)', text, re.IGNORECASE)
        if resolve_match:
            cid = resolve_match.group(1)
            decision = resolve_match.group(2).strip()
            
            if decision in ["1", "keep"]:
                return cid, "keep_existing", None
            elif decision in ["2", "new"]:
                return cid, "use_new", None
            elif decision.startswith("merge:"):
                merged_text = decision[6:].strip()
                return cid, "merge", merged_text
        
        return None, None, None
    
    def handle_resolution(self, conflict_id: str, resolution: str, merged_text: str = None) -> str:
        """Handle a resolution and return confirmation message."""
        conflict = self.queue.get_conflict(conflict_id)
        
        if not conflict:
            return f"❌ Conflict `{conflict_id}` not found."
        
        if conflict.get("resolved"):
            return f"ℹ️ Conflict `{conflict_id}` was already resolved."
        
        success = self.queue.resolve(conflict_id, resolution, merged_text)
        
        if success:
            entity = conflict.get("entity_name", "Unknown")
            
            if resolution == "keep_existing":
                return f"✅ **Resolved:** Kept existing fact for *{entity}*"
            elif resolution == "use_new":
                return f"✅ **Resolved:** Updated *{entity}* with new fact"
            elif resolution == "merge":
                return f"✅ **Resolved:** Merged facts for *{entity}*"
        
        return f"❌ Failed to resolve conflict `{conflict_id}`"


# =============================================================================
# TELEGRAM COMMAND HANDLERS (for gateway integration)
# =============================================================================

def handle_conflicts_command() -> str:
    """Handle /conflicts command - show all pending conflicts."""
    clarifier = TelegramClarifier()
    return clarifier.format_conflicts_summary()


def handle_resolve_command(args: str) -> str:
    """Handle /resolve <id> <1|2|merge:text> command."""
    clarifier = TelegramClarifier()
    
    # Parse: /resolve abc123 2
    parts = args.strip().split(maxsplit=1)
    
    if len(parts) < 2:
        return "Usage: `/resolve <conflict_id> <1|2|merge:text>`"
    
    conflict_id = parts[0]
    decision = parts[1].lower()
    
    if decision in ["1", "keep"]:
        return clarifier.handle_resolution(conflict_id, "keep_existing")
    elif decision in ["2", "new"]:
        return clarifier.handle_resolution(conflict_id, "use_new")
    elif decision.startswith("merge:"):
        merged_text = decision[6:].strip()
        if not merged_text:
            return "Please provide merged text: `/resolve <id> merge: <your text>`"
        return clarifier.handle_resolution(conflict_id, "merge", merged_text)
    else:
        return "Invalid decision. Use `1`, `2`, or `merge: <text>`"


def handle_sendconflicts_command() -> str:
    """Handle /sendconflicts command - send all pending conflicts to Telegram."""
    clarifier = TelegramClarifier()
    count = clarifier.send_all_pending()
    
    if count == 0:
        return "ℹ️ No new conflicts to send (all pending conflicts have already been sent)."
    
    return f"📤 Sent {count} conflict(s) for clarification."


def check_if_conflict_response(text: str) -> Optional[str]:
    """
    Check if incoming message is a conflict resolution response.
    Returns the response message if it was a resolution, None otherwise.
    """
    text = text.strip()
    
    # Check for /resolve command
    if text.lower().startswith("/resolve"):
        args = text[8:].strip()
        return handle_resolve_command(args)
    
    # Check for quick response to most recent conflict
    clarifier = TelegramClarifier()
    pending = clarifier.queue.get_pending()
    
    if pending and text.lower() in ["1", "2"] or text.lower().startswith("merge:"):
        # Assume response to most recent conflict
        most_recent = pending[-1]
        conflict_id = most_recent.get("conflict_id")
        
        cid, resolution, merged = clarifier.parse_resolution_response(text, conflict_id)
        
        if resolution:
            return clarifier.handle_resolution(conflict_id, resolution, merged)
    
    return None


# =============================================================================
# AUTOMATIC CONFLICT NOTIFICATION
# =============================================================================

def notify_new_conflicts():
    """
    Check for new conflicts and send them to Telegram.
    Call this after document ingestion.
    """
    clarifier = TelegramClarifier()
    count = clarifier.send_all_pending()
    return count


# =============================================================================
# CLI
# =============================================================================

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python conflict_clarifier.py list         - Show pending conflicts")
        print("  python conflict_clarifier.py send         - Send conflicts to Telegram")
        print("  python conflict_clarifier.py resolve <id> <1|2|merge:text>")
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == "list":
        clarifier = TelegramClarifier()
        print(clarifier.format_conflicts_summary())
        
    elif cmd == "send":
        clarifier = TelegramClarifier()
        count = clarifier.send_all_pending()
        print(f"Sent {count} conflicts")
        
    elif cmd == "resolve" and len(sys.argv) >= 4:
        conflict_id = sys.argv[2]
        decision = " ".join(sys.argv[3:])
        result = handle_resolve_command(f"{conflict_id} {decision}")
        print(result)
    
    else:
        print("Unknown command")


if __name__ == "__main__":
    main()
