#!/usr/bin/env python3
"""
UNIFIED MEMORY SERVICE - Mem0 Primary with PostgreSQL Fallback

╔════════════════════════════════════════════════════════════════════╗
║  Single interface for all memory operations                        ║
║  - Primary: Mem0 (managed embeddings, semantic search)             ║
║  - Fallback: PostgreSQL (PersistentMemory)                         ║
║  - Automatic failover if Mem0 is unavailable                       ║
╚════════════════════════════════════════════════════════════════════╝

Usage:
    from unified_memory import get_unified_memory
    
    memory = get_unified_memory()
    memory.store("product", "PF1-X", "Price is $200K", user_id="rushabh")
    results = memory.search("PF1 price", user_id="rushabh")
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import from centralized config via brain_orchestrator
try:
    from config import DATABASE_URL, MEM0_API_KEY, OPENAI_API_KEY
except ImportError:
    import os
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    MEM0_API_KEY = os.environ.get("MEM0_API_KEY", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class UnifiedMemory:
    """A memory that can come from either Mem0 or PostgreSQL."""
    id: str
    text: str
    entity_type: Optional[str] = None
    entity_name: Optional[str] = None
    user_id: Optional[str] = None
    source: str = "unknown"  # "mem0" or "postgresql"
    score: float = 0.0
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StoreResult:
    """Result of storing a memory."""
    success: bool
    memory_id: Optional[str] = None
    source: str = "unknown"
    error: Optional[str] = None


# =============================================================================
# UNIFIED MEMORY SERVICE
# =============================================================================

class UnifiedMemoryService:
    """
    Unified memory service with Mem0 as primary and PostgreSQL as fallback.
    
    All operations try Mem0 first. If Mem0 fails or is unavailable,
    falls back to PostgreSQL automatically.
    """
    
    def __init__(self):
        self._mem0 = None
        self._postgres = None
        self._mem0_available = None  # None = not checked yet
        self._postgres_available = None
        
    # =========================================================================
    # LAZY INITIALIZATION
    # =========================================================================
    
    def _get_mem0(self):
        """Get Mem0 service (lazy init)."""
        if self._mem0 is None:
            try:
                from .mem0_memory import Mem0MemoryService
                self._mem0 = Mem0MemoryService()
                self._mem0_available = True
                print("[unified_memory] Mem0 initialized")
            except ImportError:
                try:
                    from mem0_memory import Mem0MemoryService
                    self._mem0 = Mem0MemoryService()
                    self._mem0_available = True
                    print("[unified_memory] Mem0 initialized")
                except Exception as e:
                    self._mem0_available = False
                    print(f"[unified_memory] Mem0 unavailable: {e}")
            except Exception as e:
                self._mem0_available = False
                print(f"[unified_memory] Mem0 unavailable: {e}")
        return self._mem0
    
    def _get_postgres(self):
        """Get PostgreSQL service (lazy init)."""
        if self._postgres is None:
            try:
                from .persistent_memory import PersistentMemory
                self._postgres = PersistentMemory()
                self._postgres_available = True
                print("[unified_memory] PostgreSQL initialized")
            except ImportError:
                try:
                    from persistent_memory import PersistentMemory
                    self._postgres = PersistentMemory()
                    self._postgres_available = True
                    print("[unified_memory] PostgreSQL initialized")
                except Exception as e:
                    self._postgres_available = False
                    print(f"[unified_memory] PostgreSQL unavailable: {e}")
            except Exception as e:
                self._postgres_available = False
                print(f"[unified_memory] PostgreSQL unavailable: {e}")
        return self._postgres
    
    # =========================================================================
    # STORE OPERATIONS
    # =========================================================================
    
    def store_entity_memory(
        self,
        entity_type: str,
        entity_name: str,
        memory_text: str,
        memory_type: str = "fact",
        user_id: str = "system",
        source_channel: str = "unified",
        confidence: float = 1.0,
    ) -> StoreResult:
        """
        Store a memory about an entity (company, contact, product).
        
        Tries Mem0 first, falls back to PostgreSQL if Mem0 fails.
        Stores in BOTH systems for redundancy.
        """
        mem0_result = None
        pg_result = None
        
        # Try Mem0 first
        mem0 = self._get_mem0()
        if mem0 and self._mem0_available:
            try:
                mem_id = mem0.add_entity_memory(
                    entity_type=entity_type,
                    entity_name=entity_name,
                    memory_text=memory_text,
                    source_user_id=user_id,
                )
                if mem_id:
                    mem0_result = StoreResult(
                        success=True,
                        memory_id=mem_id,
                        source="mem0"
                    )
                    print(f"[unified_memory] Stored in Mem0: {memory_text[:50]}...")
            except Exception as e:
                print(f"[unified_memory] Mem0 store failed: {e}")
        
        # Also store in PostgreSQL (fallback + backup)
        pg = self._get_postgres()
        if pg and self._postgres_available:
            try:
                pg_id = pg.store_entity_memory(
                    entity_type=entity_type,
                    entity_name=entity_name,
                    memory_text=memory_text,
                    memory_type=memory_type,
                    source_channel=source_channel,
                    source_identity_id=user_id,
                    confidence=confidence,
                    embed=False,  # Mem0 handles embeddings
                )
                if pg_id:
                    pg_result = StoreResult(
                        success=True,
                        memory_id=str(pg_id),
                        source="postgresql"
                    )
            except Exception as e:
                print(f"[unified_memory] PostgreSQL store failed: {e}")
        
        # Return primary result (Mem0) or fallback (PostgreSQL)
        if mem0_result and mem0_result.success:
            return mem0_result
        elif pg_result and pg_result.success:
            return pg_result
        else:
            return StoreResult(
                success=False,
                error="Both Mem0 and PostgreSQL failed"
            )
    
    def store_user_memory(
        self,
        user_id: str,
        memory_text: str,
        memory_type: str = "fact",
        source_channel: str = "unified",
        confidence: float = 1.0,
    ) -> StoreResult:
        """Store a memory about a user."""
        mem0_result = None
        pg_result = None
        
        # Try Mem0 first
        mem0 = self._get_mem0()
        if mem0 and self._mem0_available:
            try:
                mem_id = mem0.add_memory(
                    text=memory_text,
                    user_id=user_id,
                    metadata={
                        "memory_type": memory_type,
                        "source_channel": source_channel,
                    }
                )
                if mem_id:
                    mem0_result = StoreResult(
                        success=True,
                        memory_id=mem_id,
                        source="mem0"
                    )
            except Exception as e:
                print(f"[unified_memory] Mem0 store failed: {e}")
        
        # Also store in PostgreSQL
        pg = self._get_postgres()
        if pg and self._postgres_available:
            try:
                pg_id = pg.store_memory(
                    identity_id=user_id,
                    memory_text=memory_text,
                    memory_type=memory_type,
                    source_channel=source_channel,
                    confidence=confidence,
                    embed=False,
                )
                if pg_id:
                    pg_result = StoreResult(
                        success=True,
                        memory_id=str(pg_id),
                        source="postgresql"
                    )
            except Exception as e:
                print(f"[unified_memory] PostgreSQL store failed: {e}")
        
        if mem0_result and mem0_result.success:
            return mem0_result
        elif pg_result and pg_result.success:
            return pg_result
        else:
            return StoreResult(success=False, error="Both systems failed")
    
    # =========================================================================
    # SEARCH OPERATIONS
    # =========================================================================
    
    def search_entities(
        self,
        query: str,
        entity_type: Optional[str] = None,
        entity_name: Optional[str] = None,
        limit: int = 10,
    ) -> List[UnifiedMemory]:
        """
        Search for entity memories.
        
        Tries Mem0 first (better semantic search), falls back to PostgreSQL.
        """
        # Try Mem0 first
        mem0 = self._get_mem0()
        if mem0 and self._mem0_available:
            try:
                results = mem0.search_entity(
                    query=query,
                    entity_type=entity_type,
                    entity_name=entity_name,
                    limit=limit,
                )
                if results:
                    return [
                        UnifiedMemory(
                            id=r.id,
                            text=r.memory,
                            entity_type=r.metadata.get("entity_type"),
                            entity_name=r.metadata.get("entity_name"),
                            source="mem0",
                            score=r.score,
                            created_at=r.created_at,
                            metadata=r.metadata,
                        )
                        for r in results
                    ]
            except Exception as e:
                print(f"[unified_memory] Mem0 search failed: {e}")
        
        # Fallback to PostgreSQL
        pg = self._get_postgres()
        if pg and self._postgres_available:
            try:
                if entity_name:
                    results = pg.get_entity_memories(entity_name, limit=limit)
                else:
                    results = pg.retrieve_entity_memories(query, limit=limit)
                
                return [
                    UnifiedMemory(
                        id=str(r.id),
                        text=r.memory_text,
                        entity_type=r.entity_type,
                        entity_name=r.entity_name,
                        source="postgresql",
                        score=r.relevance_score,
                        created_at=r.created_at,
                    )
                    for r in results
                ]
            except Exception as e:
                print(f"[unified_memory] PostgreSQL search failed: {e}")
        
        return []
    
    def search_user_memories(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
    ) -> List[UnifiedMemory]:
        """Search for user memories."""
        # Try Mem0 first
        mem0 = self._get_mem0()
        if mem0 and self._mem0_available:
            try:
                results = mem0.search(query, user_id, limit=limit)
                if results:
                    return [
                        UnifiedMemory(
                            id=r.id,
                            text=r.memory,
                            user_id=user_id,
                            source="mem0",
                            score=r.score,
                            created_at=r.created_at,
                            metadata=r.metadata,
                        )
                        for r in results
                    ]
            except Exception as e:
                print(f"[unified_memory] Mem0 search failed: {e}")
        
        # Fallback to PostgreSQL
        pg = self._get_postgres()
        if pg and self._postgres_available:
            try:
                results = pg.retrieve_for_prompt(user_id, query, limit=limit)
                return [
                    UnifiedMemory(
                        id=str(r.id),
                        text=r.memory_text,
                        user_id=user_id,
                        source="postgresql",
                        score=r.relevance_score,
                        created_at=r.created_at,
                    )
                    for r in results
                ]
            except Exception as e:
                print(f"[unified_memory] PostgreSQL search failed: {e}")
        
        return []
    
    # =========================================================================
    # RETRIEVAL FOR PROMPTS
    # =========================================================================
    
    def get_context_for_prompt(
        self,
        query: str,
        user_id: str,
        entity_names: List[str] = None,
        limit: int = 10,
    ) -> str:
        """
        Get formatted context for LLM prompts.
        
        Combines user memories + entity memories relevant to the query.
        """
        lines = []
        
        # Get user memories
        user_memories = self.search_user_memories(query, user_id, limit=limit//2)
        if user_memories:
            lines.append("## What I Remember About You:")
            for m in user_memories:
                lines.append(f"- {m.text}")
            lines.append("")
        
        # Get entity memories
        entity_memories = self.search_entities(query, limit=limit//2)
        if entity_memories:
            lines.append("## Relevant Knowledge:")
            for m in entity_memories:
                prefix = f"[{m.entity_name}] " if m.entity_name else ""
                lines.append(f"- {prefix}{m.text}")
        
        return "\n".join(lines) if lines else ""
    
    # =========================================================================
    # STATS & DIAGNOSTICS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        stats = {
            "mem0_available": self._mem0_available,
            "postgresql_available": self._postgres_available,
            "mem0_count": 0,
            "postgresql_count": 0,
        }
        
        # PostgreSQL stats
        pg = self._get_postgres()
        if pg and self._postgres_available:
            try:
                import psycopg2
                conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM ira_memory.entity_memories WHERE is_active = TRUE")
                entity_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM ira_memory.user_memories WHERE is_active = TRUE")
                user_count = cur.fetchone()[0]
                stats["postgresql_count"] = entity_count + user_count
                stats["postgresql_entities"] = entity_count
                stats["postgresql_users"] = user_count
                conn.close()
            except Exception as e:
                stats["postgresql_error"] = str(e)
        
        return stats


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_unified_memory: Optional[UnifiedMemoryService] = None


def get_unified_memory() -> UnifiedMemoryService:
    """Get the global unified memory service."""
    global _unified_memory
    if _unified_memory is None:
        _unified_memory = UnifiedMemoryService()
    return _unified_memory


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    memory = get_unified_memory()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python unified_memory.py stats")
        print("  python unified_memory.py search <query>")
        print("  python unified_memory.py store <entity_type> <entity_name> <text>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "stats":
        stats = memory.get_stats()
        print("\n📊 UNIFIED MEMORY STATS")
        print("=" * 40)
        for k, v in stats.items():
            print(f"  {k}: {v}")
    
    elif cmd == "search" and len(sys.argv) >= 3:
        query = " ".join(sys.argv[2:])
        results = memory.search_entities(query, limit=10)
        print(f"\n🔍 Found {len(results)} results for '{query}':\n")
        for r in results:
            print(f"  [{r.source}] {r.entity_name or 'user'}: {r.text[:80]}...")
    
    elif cmd == "store" and len(sys.argv) >= 5:
        entity_type = sys.argv[2]
        entity_name = sys.argv[3]
        text = " ".join(sys.argv[4:])
        result = memory.store_entity_memory(entity_type, entity_name, text)
        print(f"✅ Stored via {result.source}: {result.memory_id}")
    
    else:
        print("Invalid command")
