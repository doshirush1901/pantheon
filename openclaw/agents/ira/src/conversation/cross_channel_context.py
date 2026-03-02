#!/usr/bin/env python3
"""
CROSS-CHANNEL CONTEXT SERVICE
==============================

Provides unified conversation context across Email and Telegram channels.

When a customer messages on Telegram, Ira can see their recent email conversations.
When drafting emails, Ira can see recent Telegram chats with the same contact.

Usage:
    from cross_channel_context import get_cross_channel_context, CrossChannelService
    
    # Get context for a Telegram user
    context = get_cross_channel_context(
        channel="telegram",
        identifier="YOUR_CHAT_ID"  # Telegram chat ID
    )
    
    # Returns recent emails, conversations, and interaction summary
    print(context.email_threads)
    print(context.summary)
"""

import logging
import os
import sys
import json

logger = logging.getLogger(__name__)
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager

SKILL_DIR = Path(__file__).parent
SKILLS_DIR = SKILL_DIR.parent
AGENT_DIR = SKILLS_DIR.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(SKILLS_DIR / "identity"))
sys.path.insert(0, str(SKILLS_DIR / "memory"))

PROJECT_ROOT = AGENT_DIR.parent.parent.parent

# Load env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

# Import identity service
try:
    from unified_identity import get_identity_service, Contact
    IDENTITY_AVAILABLE = True
except ImportError:
    IDENTITY_AVAILABLE = False
    Contact = None

# Paths
CRM_DIR = PROJECT_ROOT / "crm"
RELATIONSHIPS_DB = CRM_DIR / "relationships.db"
EMAIL_LOG = CRM_DIR / "logs" / "requests.jsonl"
TELEGRAM_LOG = CRM_DIR / "logs" / "telegram_activity_log.json"

# Context configuration
MAX_EMAIL_THREADS = 5
MAX_TELEGRAM_MESSAGES = 10
LOOKBACK_DAYS = 14


@dataclass
class EmailThread:
    """Summary of an email conversation."""
    thread_id: str
    subject: str
    last_date: datetime
    message_count: int
    summary: str
    last_message_preview: str
    from_email: str


@dataclass
class TelegramConversation:
    """Summary of Telegram messages."""
    chat_id: str
    last_date: datetime
    message_count: int
    topics: List[str]
    last_messages: List[Dict]


@dataclass
class CrossChannelContext:
    """Unified context from all channels for a contact."""
    contact_id: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_company: Optional[str] = None
    
    # Recent activity
    email_threads: List[EmailThread] = field(default_factory=list)
    telegram_messages: List[Dict] = field(default_factory=list)
    
    # Aggregated insights
    total_interactions: int = 0
    first_contact: Optional[datetime] = None
    last_contact: Optional[datetime] = None
    primary_channel: str = "unknown"
    topics_discussed: List[str] = field(default_factory=list)
    
    # Summary for LLM context
    summary: str = ""
    
    def to_context_string(self) -> str:
        """Format context for injection into LLM prompt."""
        if not self.email_threads and not self.telegram_messages:
            return ""
        
        parts = []
        
        if self.contact_name:
            parts.append(f"📇 Contact: {self.contact_name}")
            if self.contact_company:
                parts.append(f"   Company: {self.contact_company}")
            if self.contact_email:
                parts.append(f"   Email: {self.contact_email}")
        
        if self.email_threads:
            parts.append(f"\n📧 Recent Email Conversations ({len(self.email_threads)}):")
            for thread in self.email_threads[:3]:
                age = (datetime.now() - thread.last_date).days
                age_str = f"{age}d ago" if age > 0 else "today"
                parts.append(f"   • {thread.subject[:50]} ({age_str})")
                parts.append(f"     Last: {thread.last_message_preview[:80]}...")
        
        if self.topics_discussed:
            parts.append(f"\n🏷️ Topics discussed: {', '.join(self.topics_discussed[:5])}")
        
        if self.summary:
            parts.append(f"\n💡 {self.summary}")
        
        return "\n".join(parts)


class CrossChannelService:
    """
    Service to retrieve and combine context from multiple channels.
    
    Links contacts across:
    - Email (from address)
    - Telegram (chat ID)
    - Phone (if available)
    """
    
    def __init__(self):
        self._identity_service = None
        self._db_conn = None
    
    def _get_identity_service(self):
        """Get identity service (lazy init)."""
        if self._identity_service is None and IDENTITY_AVAILABLE:
            self._identity_service = get_identity_service()
        return self._identity_service
    
    @contextmanager
    def _get_db(self):
        """Get database connection."""
        if not RELATIONSHIPS_DB.exists():
            yield None
            return
        
        conn = sqlite3.connect(str(RELATIONSHIPS_DB))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def resolve_contact(self, channel: str, identifier: str) -> Optional[Contact]:
        """
        Resolve a channel identifier to a unified contact.
        
        Args:
            channel: "telegram", "email", or "phone"
            identifier: The channel-specific ID (chat_id, email address, phone)
        
        Returns:
            Contact object if found
        """
        identity_svc = self._get_identity_service()
        if not identity_svc:
            return None
        
        try:
            contact_id = identity_svc.resolve(channel, identifier)
            if contact_id:
                return identity_svc.get_contact(contact_id)
        except Exception as e:
            logger.error("Contact resolution error: %s", e)
        
        return None
    
    def get_email_threads_for_contact(
        self, 
        email: str, 
        limit: int = MAX_EMAIL_THREADS,
        days: int = LOOKBACK_DAYS
    ) -> List[EmailThread]:
        """Get recent email threads for a contact."""
        threads = []
        
        # Try to read from email logs
        if EMAIL_LOG.exists():
            try:
                cutoff = datetime.now() - timedelta(days=days)
                email_lower = email.lower()
                
                thread_data = {}  # thread_id -> messages
                
                with open(EMAIL_LOG, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            record = json.loads(line)
                            
                            # Check if this record involves the contact
                            record_email = record.get("from_email", "").lower()
                            record_to = record.get("to_email", "").lower()
                            
                            if email_lower not in (record_email, record_to):
                                continue
                            
                            # Parse timestamp
                            ts_str = record.get("timestamp", "")
                            if ts_str:
                                try:
                                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                    if ts.replace(tzinfo=None) < cutoff:
                                        continue
                                except (ValueError, TypeError):
                                    pass
                            
                            thread_id = record.get("thread_id", record.get("message_id", ""))
                            if thread_id:
                                if thread_id not in thread_data:
                                    thread_data[thread_id] = []
                                thread_data[thread_id].append(record)
                                
                        except json.JSONDecodeError:
                            continue
                
                # Convert to EmailThread objects
                for thread_id, messages in thread_data.items():
                    if not messages:
                        continue
                    
                    # Sort by timestamp
                    messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                    latest = messages[0]
                    
                    threads.append(EmailThread(
                        thread_id=thread_id,
                        subject=latest.get("subject", "No subject")[:100],
                        last_date=datetime.fromisoformat(
                            latest.get("timestamp", datetime.now().isoformat()).replace("Z", "+00:00")
                        ).replace(tzinfo=None),
                        message_count=len(messages),
                        summary=latest.get("summary", ""),
                        last_message_preview=latest.get("message_preview", latest.get("body", ""))[:150],
                        from_email=latest.get("from_email", email),
                    ))
                
                # Sort by recency
                threads.sort(key=lambda x: x.last_date, reverse=True)
                
            except Exception as e:
                logger.error("Error reading email logs: %s", e)
        
        # Also check relationships database for email history
        with self._get_db() as conn:
            if conn:
                try:
                    cursor = conn.execute("""
                        SELECT DISTINCT 
                            thread_id, subject, MAX(timestamp) as last_ts,
                            COUNT(*) as msg_count
                        FROM email_history
                        WHERE (from_email = ? OR to_email = ?)
                          AND timestamp > datetime('now', ?)
                        GROUP BY thread_id
                        ORDER BY last_ts DESC
                        LIMIT ?
                    """, (email, email, f'-{days} days', limit))
                    
                    for row in cursor:
                        # Don't duplicate threads we already have
                        if any(t.thread_id == row['thread_id'] for t in threads):
                            continue
                        
                        threads.append(EmailThread(
                            thread_id=row['thread_id'],
                            subject=row['subject'] or "No subject",
                            last_date=datetime.fromisoformat(row['last_ts']) if row['last_ts'] else datetime.now(),
                            message_count=row['msg_count'],
                            summary="",
                            last_message_preview="",
                            from_email=email,
                        ))
                except sqlite3.OperationalError:
                    # Table might not exist
                    pass
        
        return threads[:limit]
    
    def get_telegram_messages_for_chat(
        self,
        chat_id: str,
        limit: int = MAX_TELEGRAM_MESSAGES,
        days: int = LOOKBACK_DAYS
    ) -> List[Dict]:
        """Get recent Telegram messages for a chat."""
        messages = []
        
        if TELEGRAM_LOG.exists():
            try:
                cutoff = datetime.now() - timedelta(days=days)
                
                with open(TELEGRAM_LOG, 'r') as f:
                    data = json.load(f)
                
                for entry in data:
                    if str(entry.get("chat_id", "")) != str(chat_id):
                        continue
                    
                    ts_str = entry.get("timestamp", "")
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str)
                            if ts < cutoff:
                                continue
                        except (ValueError, TypeError):
                            pass
                    
                    messages.append({
                        "timestamp": ts_str,
                        "message": entry.get("message", "")[:200],
                        "from_user": entry.get("from_user", ""),
                        "response_type": entry.get("type", "message"),
                    })
                
                # Sort by recency
                messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                
            except Exception as e:
                logger.error("Error reading Telegram logs: %s", e)
        
        return messages[:limit]
    
    def extract_topics(self, texts: List[str]) -> List[str]:
        """Extract key topics from a list of texts."""
        topics = set()
        
        # Simple keyword extraction
        topic_keywords = {
            "pricing": ["price", "cost", "budget", "quote", "₹", "$", "inr", "usd", "eur"],
            "PF1 machines": ["pf1", "pf-1"],
            "PF2 machines": ["pf2", "pf-2"],
            "AM machines": ["am-", "am machine"],
            "FCS machines": ["fcs", "inline"],
            "IMG machines": ["img", "in-mold"],
            "specifications": ["spec", "dimension", "size", "capacity", "power", "kw"],
            "delivery": ["delivery", "lead time", "shipping", "timeline", "when"],
            "warranty": ["warranty", "guarantee", "support", "service"],
            "installation": ["install", "commission", "training", "setup"],
            "materials": ["abs", "hdpe", "pp", "tpo", "acrylic", "petg"],
            "applications": ["automotive", "packaging", "signage", "industrial"],
        }
        
        combined_text = " ".join(texts).lower()
        
        for topic, keywords in topic_keywords.items():
            if any(kw in combined_text for kw in keywords):
                topics.add(topic)
        
        return list(topics)[:10]
    
    def generate_summary(self, context: CrossChannelContext) -> str:
        """Generate a brief summary of the cross-channel context."""
        parts = []
        
        if context.email_threads:
            recent_thread = context.email_threads[0]
            age = (datetime.now() - recent_thread.last_date).days
            if age == 0:
                parts.append(f"Active email thread today: \"{recent_thread.subject[:40]}\"")
            elif age <= 3:
                parts.append(f"Recent email ({age}d ago): \"{recent_thread.subject[:40]}\"")
            else:
                parts.append(f"Last email {age} days ago about \"{recent_thread.subject[:40]}\"")
        
        if context.topics_discussed:
            parts.append(f"Interested in: {', '.join(context.topics_discussed[:3])}")
        
        if context.total_interactions > 5:
            parts.append(f"Engaged customer ({context.total_interactions} interactions)")
        
        return ". ".join(parts)
    
    def get_context(
        self,
        channel: str,
        identifier: str,
        include_email: bool = True,
        include_telegram: bool = True,
    ) -> CrossChannelContext:
        """
        Get unified cross-channel context for a contact.
        
        Args:
            channel: Source channel ("telegram" or "email")
            identifier: Channel identifier (chat_id or email address)
            include_email: Include email thread context
            include_telegram: Include Telegram message context
        
        Returns:
            CrossChannelContext with all available context
        """
        context = CrossChannelContext()
        
        # Resolve contact identity
        contact = self.resolve_contact(channel, identifier)
        if contact:
            context.contact_id = contact.contact_id
            context.contact_name = contact.name
            context.contact_email = contact.email
            context.contact_company = contact.company
        
        # Get email context
        email_to_check = None
        if include_email:
            if channel == "email":
                email_to_check = identifier
            elif contact and contact.email:
                email_to_check = contact.email
            
            if email_to_check:
                context.email_threads = self.get_email_threads_for_contact(email_to_check)
        
        # Get Telegram context
        chat_id_to_check = None
        if include_telegram:
            if channel == "telegram":
                chat_id_to_check = identifier
            elif contact and contact.telegram_id:
                chat_id_to_check = contact.telegram_id
            
            if chat_id_to_check:
                context.telegram_messages = self.get_telegram_messages_for_chat(chat_id_to_check)
        
        # Aggregate insights
        all_texts = []
        
        for thread in context.email_threads:
            all_texts.append(thread.subject)
            all_texts.append(thread.last_message_preview)
        
        for msg in context.telegram_messages:
            all_texts.append(msg.get("message", ""))
        
        context.topics_discussed = self.extract_topics(all_texts)
        context.total_interactions = len(context.email_threads) + len(context.telegram_messages)
        
        # Determine primary channel
        if context.email_threads and not context.telegram_messages:
            context.primary_channel = "email"
        elif context.telegram_messages and not context.email_threads:
            context.primary_channel = "telegram"
        elif context.email_threads and context.telegram_messages:
            # Compare recency
            email_latest = context.email_threads[0].last_date if context.email_threads else datetime.min
            tg_latest = datetime.fromisoformat(context.telegram_messages[0]["timestamp"]) if context.telegram_messages else datetime.min
            context.primary_channel = "email" if email_latest > tg_latest else "telegram"
        
        # Generate summary
        context.summary = self.generate_summary(context)
        
        return context


# Singleton instance
_service: Optional[CrossChannelService] = None


def get_cross_channel_service() -> CrossChannelService:
    """Get singleton cross-channel service."""
    global _service
    if _service is None:
        _service = CrossChannelService()
    return _service


def get_cross_channel_context(
    channel: str,
    identifier: str,
    **kwargs
) -> CrossChannelContext:
    """Convenience function to get cross-channel context."""
    return get_cross_channel_service().get_context(channel, identifier, **kwargs)


# =============================================================================
# CLI FOR TESTING
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Cross-Channel Context Service")
    parser.add_argument("--telegram", help="Get context for Telegram chat ID")
    parser.add_argument("--email", help="Get context for email address")
    args = parser.parse_args()
    
    service = CrossChannelService()
    
    if args.telegram:
        print(f"\n📱 Getting context for Telegram: {args.telegram}")
        ctx = service.get_context("telegram", args.telegram)
        print(ctx.to_context_string())
        print(f"\n📊 Stats:")
        print(f"   Email threads: {len(ctx.email_threads)}")
        print(f"   Telegram messages: {len(ctx.telegram_messages)}")
        print(f"   Topics: {ctx.topics_discussed}")
        
    elif args.email:
        print(f"\n📧 Getting context for Email: {args.email}")
        ctx = service.get_context("email", args.email)
        print(ctx.to_context_string())
        print(f"\n📊 Stats:")
        print(f"   Email threads: {len(ctx.email_threads)}")
        print(f"   Topics: {ctx.topics_discussed}")
    
    else:
        print("Usage:")
        print("  python cross_channel_context.py --telegram YOUR_CHAT_ID")
        print("  python cross_channel_context.py --email john@example.com")
