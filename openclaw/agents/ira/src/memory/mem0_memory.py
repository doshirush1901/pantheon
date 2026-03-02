#!/usr/bin/env python3
"""
MEM0 MEMORY SERVICE - Modern AI Memory Layer for Ira

╔════════════════════════════════════════════════════════════════════╗
║  Replaces PostgreSQL-based persistent memory with Mem0            ║
║  - Automatic fact extraction & deduplication                       ║
║  - Semantic search across all memories                             ║
║  - Temporal decay (old unused memories fade)                       ║
║  - Built-in conflict resolution                                    ║
╚════════════════════════════════════════════════════════════════════╝
"""

import logging
import os
import sys
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Production resilience layer
MEMORY_DIR = Path(__file__).parent
SKILLS_DIR = MEMORY_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(AGENT_DIR / "core"))

try:
    from core.resilience import mem0_breaker, retry_with_exponential_backoff
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False

try:
    from error_monitor import track_error, track_warning
except ImportError:
    def track_error(component, error, context=None, severity="error"): pass
    def track_warning(component, message, context=None): pass

# Load env
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip().strip('"')
            if not os.environ.get(key) or os.environ.get(key, "").startswith("your-"):
                os.environ[key] = value


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Memory:
    """A single memory from Mem0."""
    id: str
    memory: str  # The actual memory text
    user_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0  # Relevance score from search
    
    @classmethod
    def from_mem0(cls, data: Dict) -> "Memory":
        """Create from Mem0 API response."""
        return cls(
            id=data.get("id", ""),
            memory=data.get("memory", ""),
            user_id=data.get("user_id", ""),
            created_at=cls._parse_date(data.get("created_at")),
            updated_at=cls._parse_date(data.get("updated_at")),
            metadata=data.get("metadata", {}),
            score=data.get("score", 0.0),
        )
    
    @staticmethod
    def _parse_date(val) -> Optional[datetime]:
        if not val:
            return None
        if isinstance(val, datetime):
            return val
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None


@dataclass
class MemoryAddResult:
    """Result from adding memories."""
    added: List[str] = field(default_factory=list)
    updated: List[str] = field(default_factory=list)
    deleted: List[str] = field(default_factory=list)


# =============================================================================
# MEM0 MEMORY SERVICE
# =============================================================================

class Mem0MemoryService:
    """
    Modern memory service using Mem0 Platform.
    
    Features:
    - Automatic fact extraction from conversations
    - Semantic search across all memories
    - Deduplication and conflict resolution
    - User and entity memories
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Mem0 client."""
        self.api_key = api_key or os.environ.get("MEM0_API_KEY")
        
        if not self.api_key:
            raise ValueError("MEM0_API_KEY not found. Set it in environment or pass to constructor.")
        
        from mem0 import MemoryClient
        self.client = MemoryClient(api_key=self.api_key)
        self._initialized = True
    
    # =========================================================================
    # CORE OPERATIONS
    # =========================================================================
    
    def add_conversation(
        self,
        messages: List[Dict[str, str]],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryAddResult:
        """
        Extract and store memories from a conversation.
        
        Mem0 automatically:
        - Extracts facts from the conversation
        - Deduplicates against existing memories
        - Updates conflicting information
        
        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            user_id: Unique identifier for the user
            metadata: Optional metadata (channel, timestamp, etc.)
            
        Returns:
            MemoryAddResult with added/updated/deleted memory IDs
        """
        try:
            def do_add():
                return self.client.add(
                    messages=messages,
                    user_id=user_id,
                    metadata=metadata or {},
                )
            
            # Apply circuit breaker if available
            if RESILIENCE_AVAILABLE:
                result, used_fallback = mem0_breaker.execute(do_add, fallback_result={})
                if used_fallback:
                    track_warning("mem0_memory", "Mem0 unavailable, skipping memory add")
                    return MemoryAddResult()
            else:
                result = do_add()
            
            return MemoryAddResult(
                added=[m.get("id", "") for m in result.get("results", []) if m.get("event") == "ADD"],
                updated=[m.get("id", "") for m in result.get("results", []) if m.get("event") == "UPDATE"],
                deleted=[m.get("id", "") for m in result.get("results", []) if m.get("event") == "DELETE"],
            )
        except Exception as e:
            track_error("mem0_memory", e, {"operation": "add_conversation", "user_id": user_id})
            logger.error("Error adding conversation: %s", e)
            return MemoryAddResult()
    
    def add_memory(
        self,
        text: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Add a single memory directly.
        
        Args:
            text: The memory text to store
            user_id: User identifier
            metadata: Optional metadata
            
        Returns:
            Memory ID or event_id if queued (Mem0 processes async)
        """
        try:
            result = self.client.add(
                messages=[{"role": "user", "content": text}],
                user_id=user_id,
                metadata=metadata or {},
            )
            results = result.get("results", [])
            if results:
                # Mem0 may return immediate ID or queue for async processing
                first = results[0]
                return first.get("id") or first.get("event_id") or "queued"
            return None
        except Exception as e:
            logger.error("Error adding memory: %s", e)
            return None
    
    def search(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> List[Memory]:
        """
        Semantic search for relevant memories.
        
        Args:
            query: What to search for
            user_id: User to search memories for
            limit: Max results
            threshold: Min relevance score (0-1)
            
        Returns:
            List of relevant memories with scores
        """
        try:
            # Use v2 API with proper filters
            results = self.client.search(
                query=query,
                version="v2",
                filters={"user_id": user_id},
                top_k=limit,
                threshold=threshold if threshold > 0 else 0.3,
            )
            
            # v2 API returns 'memories' instead of 'results'
            memories_data = results.get("memories", results.get("results", []))
            
            memories = []
            for r in memories_data:
                mem = Memory.from_mem0(r)
                memories.append(mem)
            
            return memories
        except Exception as e:
            logger.error("Error searching: %s", e)
            return []
    
    def get_all(self, user_id: str) -> List[Memory]:
        """Get all memories for a user."""
        try:
            results = self.client.get_all(
                version="v2",
                filters={"user_id": user_id}
            )
            # Handle both v1 ('results') and v2 ('memories') response formats
            memories_data = results.get("memories", results.get("results", []))
            if isinstance(results, list):
                memories_data = results
            return [Memory.from_mem0(r) for r in memories_data]
        except Exception as e:
            logger.error("Error getting all: %s", e)
            return []
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a specific memory by ID."""
        try:
            result = self.client.get(memory_id=memory_id)
            if result:
                return Memory.from_mem0(result)
            return None
        except Exception as e:
            logger.error("Error getting memory: %s", e)
            return None
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory."""
        try:
            self.client.delete(memory_id=memory_id)
            return True
        except Exception as e:
            logger.error("Error deleting: %s", e)
            return False
    
    def delete_all(self, user_id: str) -> bool:
        """Delete all memories for a user."""
        try:
            self.client.delete_all(user_id=user_id)
            return True
        except Exception as e:
            logger.error("Error deleting all: %s", e)
            return False
    
    def update_memory(self, memory_id: str, text: str) -> bool:
        """Update a memory's text."""
        try:
            self.client.update(memory_id=memory_id, data=text)
            return True
        except Exception as e:
            logger.error("Error updating: %s", e)
            return False
    
    # =========================================================================
    # ENTITY MEMORIES (Companies, Contacts, etc.)
    # =========================================================================
    
    def add_entity_memory(
        self,
        entity_type: str,
        entity_name: str,
        memory_text: str,
        source_user_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Add a memory about an entity (company, contact, etc.)
        
        Uses agent_id for entity grouping in Mem0.
        """
        agent_id = f"{entity_type}:{entity_name.lower().replace(' ', '_')}"
        
        try:
            result = self.client.add(
                messages=[{"role": "user", "content": memory_text}],
                agent_id=agent_id,
                metadata={
                    "entity_type": entity_type,
                    "entity_name": entity_name,
                    "source_user_id": source_user_id,
                },
            )
            results = result.get("results", [])
            if results:
                # Mem0 may return immediate ID or queue for async processing
                first = results[0]
                return first.get("id") or first.get("event_id") or "queued"
            return None
        except Exception as e:
            logger.error("Error adding entity memory: %s", e)
            return None
    
    def search_entity(
        self,
        query: str,
        entity_type: Optional[str] = None,
        entity_name: Optional[str] = None,
        limit: int = 10,
    ) -> List[Memory]:
        """Search memories about entities."""
        try:
            if entity_name:
                agent_id = f"{entity_type or 'entity'}:{entity_name.lower().replace(' ', '_')}"
                results = self.client.search(
                    query=query,
                    version="v2",
                    filters={"agent_id": agent_id},
                    top_k=limit,
                )
            else:
                # Search across all - use wildcard
                results = self.client.search(
                    query=query,
                    version="v2",
                    filters={"agent_id": "*"},
                    top_k=limit,
                )
            
            memories_data = results.get("memories", results.get("results", []))
            return [Memory.from_mem0(r) for r in memories_data]
        except Exception as e:
            logger.error("Error searching entities: %s", e)
            return []
    
    # =========================================================================
    # CONVENIENCE METHODS FOR IRA
    # =========================================================================
    
    @staticmethod
    def _contains_suspect_claims(text: str) -> bool:
        """Check if user text contains pricing or spec claims that could
        pollute the knowledge base if Mem0 extracts them as facts.

        We don't block storage entirely — we just strip the user message
        so Mem0 only extracts facts from the assistant response (which has
        already been validated by knowledge_health).
        """
        import re
        suspect_patterns = [
            r"(?:your|the)\s+(?:price|cost)\s+(?:is|was|should be)\s+[\$₹€]?\s*[\d,]+",
            r"(?:PF\d|AM|IMG|FCS)\S*\s+(?:costs?|price[ds]?)\s+[\$₹€]?\s*[\d,]+",
            r"(?:i\s+(?:heard|read|think|saw)\s+(?:that\s+)?(?:it|the|your))\s+.*(?:price|cost|spec)",
        ]
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in suspect_patterns)

    def remember_from_message(
        self,
        user_message: str,
        assistant_response: str,
        user_id: str,
        channel: str = "telegram",
    ) -> MemoryAddResult:
        """
        Process a single exchange and extract memories.

        This is the main integration point - call after each message.

        If the user message contains suspect pricing/spec claims, we only
        feed the assistant response to Mem0 (which has been validated by
        knowledge_health). This prevents user-stated wrong facts from
        polluting the knowledge base.
        """
        if self._contains_suspect_claims(user_message):
            logger.info("Mem0: user message contains suspect claims, extracting only from assistant response")
            messages = [
                {"role": "assistant", "content": assistant_response},
            ]
        else:
            messages = [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response},
            ]

        return self.add_conversation(
            messages=messages,
            user_id=user_id,
            metadata={
                "channel": channel,
                "timestamp": datetime.now().isoformat(),
            },
        )
    
    KNOWLEDGE_USER_IDS = [
        "machinecraft_knowledge",
        "machinecraft_pricing",
        "machinecraft_customers",
        "machinecraft_processes",
        "machinecraft_applications",
        "machinecraft_general",
    ]

    def get_relevant_context(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
    ) -> str:
        """
        Get relevant memories formatted for LLM context.

        Searches both user-specific memories AND the ingested knowledge
        namespaces (machinecraft_knowledge, machinecraft_pricing, etc.)
        to ensure all ingested data is accessible.

        Returns a string ready to inject into prompts.
        """
        user_memories = self.search(query, user_id, limit=limit)

        knowledge_memories = []
        for kid in self.KNOWLEDGE_USER_IDS:
            if kid == user_id:
                continue
            try:
                results = self.search(query, user_id=kid, limit=3)
                knowledge_memories.extend(results)
            except Exception as e:
                logger.debug(f"Knowledge search for {kid} failed: {e}")

        knowledge_memories.sort(key=lambda m: m.score, reverse=True)
        knowledge_memories = knowledge_memories[:8]

        lines = []

        if user_memories:
            lines.append("## What I Remember About You:")
            for mem in user_memories:
                lines.append(f"- {mem.memory}")

        if knowledge_memories:
            lines.append("\n## Relevant Product & Business Knowledge:")
            seen = set()
            for mem in knowledge_memories:
                key = mem.memory[:80]
                if key in seen:
                    continue
                seen.add(key)
                lines.append(f"- {mem.memory}")

        return "\n".join(lines) if lines else ""
    
    def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a summary of what Ira knows about a user."""
        memories = self.get_all(user_id)
        
        return {
            "user_id": user_id,
            "total_memories": len(memories),
            "memories": [m.memory for m in memories[:20]],  # First 20
            "oldest": min((m.created_at for m in memories if m.created_at), default=None),
            "newest": max((m.created_at for m in memories if m.created_at), default=None),
        }


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_mem0_service: Optional[Mem0MemoryService] = None


def get_mem0_service() -> Mem0MemoryService:
    """Get or create the global Mem0 service."""
    global _mem0_service
    if _mem0_service is None:
        _mem0_service = Mem0MemoryService()
    return _mem0_service


# =============================================================================
# CLI FOR TESTING
# =============================================================================

if __name__ == "__main__":
    import sys
    
    service = get_mem0_service()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python mem0_memory.py add <user_id> <text>")
        print("  python mem0_memory.py search <user_id> <query>")
        print("  python mem0_memory.py list <user_id>")
        print("  python mem0_memory.py delete <memory_id>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "add" and len(sys.argv) >= 4:
        user_id = sys.argv[2]
        text = " ".join(sys.argv[3:])
        mem_id = service.add_memory(text, user_id)
        print(f"✅ Added memory: {mem_id}")
    
    elif cmd == "search" and len(sys.argv) >= 4:
        user_id = sys.argv[2]
        query = " ".join(sys.argv[3:])
        memories = service.search(query, user_id)
        print(f"\n🔍 Found {len(memories)} memories:\n")
        for m in memories:
            print(f"  [{m.score:.2f}] {m.memory}")
    
    elif cmd == "list" and len(sys.argv) >= 3:
        user_id = sys.argv[2]
        memories = service.get_all(user_id)
        print(f"\n📚 {len(memories)} memories for {user_id}:\n")
        for m in memories:
            print(f"  • {m.memory}")
    
    elif cmd == "delete" and len(sys.argv) >= 3:
        memory_id = sys.argv[2]
        if service.delete_memory(memory_id):
            print(f"✅ Deleted: {memory_id}")
        else:
            print(f"❌ Failed to delete: {memory_id}")
    
    else:
        print("Invalid command. Run without args for usage.")
