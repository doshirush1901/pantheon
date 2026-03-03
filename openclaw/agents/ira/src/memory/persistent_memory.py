#!/usr/bin/env python3
"""
PERSISTENT MEMORY - ChatGPT-Style User Memory System

╔════════════════════════════════════════════════════════════════════╗
║  Enables Ira to remember facts about users across ALL conversations║
║  Unlike conversation memory, this persists forever until deleted   ║
╚════════════════════════════════════════════════════════════════════╝

Features:
- Automatic extraction of memorable facts from conversations
- Semantic retrieval of relevant memories for personalization
- User can view/delete their memories
- Cross-channel memory (Telegram + Email share same memories)
- Entity memory (facts about companies/contacts)

Memory Types:
- FACT: Concrete information ("Works at ABC Corp as Production Manager")
- PREFERENCE: User preferences ("Prefers detailed technical specs")
- CONTEXT: Business context ("Typically orders 2-3 machines/year")
- RELATIONSHIP: Connections ("Reports to John Smith, CEO")
- ENTITY: Facts about third parties ("ABC Corp uses PF1 series")
- CORRECTION: User corrections ("Actually, the price is X not Y")
"""

import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import from centralized config
try:
    from config import DATABASE_URL, OPENAI_API_KEY, VOYAGE_API_KEY, QDRANT_URL, COLLECTIONS
except ImportError:
    import os
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    COLLECTIONS = {
        "chunks": "ira_chunks_v4_voyage",
        "emails": "ira_emails_voyage_v2",
        "dream": "ira_dream_knowledge_v1",
        "customers": "ira_customers",
    }

# Embedding configuration - Use Voyage-3 for consistency with retrieval
EMBEDDING_MODEL = "voyage-3"
EMBEDDING_DIMENSION = 1024


# =============================================================================
# SCHEMA
# =============================================================================

PERSISTENT_MEMORY_SCHEMA = """
-- User persistent memories (ChatGPT-style)
CREATE TABLE IF NOT EXISTS ira_memory.user_memories (
    id SERIAL PRIMARY KEY,
    identity_id TEXT NOT NULL,
    memory_text TEXT NOT NULL,
    memory_type TEXT DEFAULT 'fact',
    source_channel TEXT,
    source_conversation_id TEXT,
    confidence REAL DEFAULT 1.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    use_count INTEGER DEFAULT 0,
    embedding_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_user_memories_identity 
ON ira_memory.user_memories(identity_id);

CREATE INDEX IF NOT EXISTS idx_user_memories_active 
ON ira_memory.user_memories(identity_id, is_active);

CREATE INDEX IF NOT EXISTS idx_user_memories_type 
ON ira_memory.user_memories(memory_type);

-- Entity memories (facts about companies/contacts)
CREATE TABLE IF NOT EXISTS ira_memory.entity_memories (
    id SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    memory_text TEXT NOT NULL,
    memory_type TEXT DEFAULT 'fact',
    source_channel TEXT,
    source_identity_id TEXT,
    confidence REAL DEFAULT 1.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    use_count INTEGER DEFAULT 0,
    embedding_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_entity_memories_name 
ON ira_memory.entity_memories(normalized_name);

CREATE INDEX IF NOT EXISTS idx_entity_memories_type 
ON ira_memory.entity_memories(entity_type);

CREATE INDEX IF NOT EXISTS idx_entity_memories_active 
ON ira_memory.entity_memories(is_active);
"""


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class UserMemory:
    """A single persistent memory about a user."""
    id: Optional[int] = None
    identity_id: str = ""
    memory_text: str = ""
    memory_type: str = "fact"
    source_channel: Optional[str] = None
    source_conversation_id: Optional[str] = None
    confidence: float = 1.0
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    use_count: int = 0
    embedding_id: Optional[str] = None
    relevance_score: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "identity_id": self.identity_id,
            "memory_text": self.memory_text,
            "memory_type": self.memory_type,
            "source_channel": self.source_channel,
            "confidence": self.confidence,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "use_count": self.use_count
        }
    
    @classmethod
    def from_row(cls, row: tuple) -> "UserMemory":
        return cls(
            id=row[0],
            identity_id=row[1],
            memory_text=row[2],
            memory_type=row[3],
            source_channel=row[4],
            source_conversation_id=row[5],
            confidence=row[6],
            is_active=row[7],
            created_at=row[8],
            last_used_at=row[9],
            use_count=row[10],
            embedding_id=row[11] if len(row) > 11 else None
        )


@dataclass
class EntityMemory:
    """A memory about a company, contact, or other entity."""
    id: Optional[int] = None
    entity_type: str = "company"  # company, contact, product
    entity_name: str = ""
    normalized_name: str = ""
    memory_text: str = ""
    memory_type: str = "fact"
    source_channel: Optional[str] = None
    source_identity_id: Optional[str] = None
    confidence: float = 1.0
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    use_count: int = 0
    embedding_id: Optional[str] = None
    relevance_score: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_name": self.entity_name,
            "memory_text": self.memory_text,
            "memory_type": self.memory_type,
            "confidence": self.confidence,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "use_count": self.use_count
        }
    
    @classmethod
    def from_row(cls, row: tuple) -> "EntityMemory":
        return cls(
            id=row[0],
            entity_type=row[1],
            entity_name=row[2],
            normalized_name=row[3],
            memory_text=row[4],
            memory_type=row[5],
            source_channel=row[6],
            source_identity_id=row[7],
            confidence=row[8],
            is_active=row[9],
            created_at=row[10],
            last_used_at=row[11],
            use_count=row[12],
            embedding_id=row[13] if len(row) > 13 else None
        )


# =============================================================================
# EXTRACTION PROMPTS
# =============================================================================

MEMORY_EXTRACTION_PROMPT = """Analyze this conversation and extract facts worth remembering.

USER MESSAGE:
{user_message}

ASSISTANT RESPONSE:
{assistant_response}

EXISTING MEMORIES (don't duplicate):
{existing_memories}

Extract NEW memorable facts in these categories:

1. USER FACTS - About the person talking:
   - Personal/professional details (name, role, company, location)
   - Preferences (communication style, technical level)
   - Business context (industry, typical needs, order patterns)

2. ENTITY FACTS - About third parties mentioned:
   - Company info (what machines they use, their industry)
   - Contact info (who works where, their role)
   - Relationships (who is whose customer/supplier)

3. CORRECTIONS - If user corrected something:
   - "Actually, the price is X" → correction
   - "No, I meant Y not Z" → correction

Rules:
- Only extract concrete, lasting facts
- Skip temporary states ("is busy today")
- Each memory should be self-contained
- Maximum 3 user memories + 3 entity memories per conversation
- If nothing memorable, return empty arrays

Output JSON:
{{
  "user_memories": [
    {{"memory": "Works at ABC Corp as Production Manager", "type": "fact"}}
  ],
  "entity_memories": [
    {{"entity_type": "company", "entity_name": "ABC Corp", "memory": "Uses PF1 series for automotive parts", "type": "fact"}}
  ],
  "corrections": [
    {{"original": "price was $50k", "corrected": "price is actually $45k", "memory": "PF1-3020 price is $45k not $50k"}}
  ]
}}

JSON:"""


PROACTIVE_SUGGESTION_PROMPT = """Based on these memories about the user and the current conversation, suggest ONE helpful proactive action.

USER MEMORIES:
{user_memories}

ENTITY MEMORIES:
{entity_memories}

CURRENT CONTEXT:
{current_context}

RECENT MESSAGE:
{recent_message}

Consider suggesting:
- Follow-up reminders ("You mentioned following up with X...")
- Relevant info from past conversations ("Last time you asked about Y...")
- Connections ("You work with Z who also uses...")
- Helpful context ("Based on your preference for detailed specs...")

Rules:
- Only suggest if genuinely helpful
- Be natural, not creepy
- If nothing useful to suggest, return null

Output JSON (or null):
{{
  "suggestion": "Based on what I remember, you might want to...",
  "reason": "Why this is relevant",
  "memory_refs": [1, 2]
}}

JSON:"""


# =============================================================================
# MAIN CLASS
# =============================================================================

class PersistentMemory:
    """
    Manages ChatGPT-style persistent user memories and entity memories.
    
    MIGRATION NOTE (Feb 2026):
    - Switched from OpenAI text-embedding-3-small (1536d) to Voyage-3 (1024d)
    - New collections: ira_user_memories_v2, ira_entity_memories_v2
    - Legacy collections (ira_user_memories, ira_entity_memories) contain OpenAI embeddings
    - To migrate: Re-embed existing memories using scripts/migrate_memories_to_voyage.py
    """
    
    # New Voyage-3 collections (1024d)
    QDRANT_COLLECTION = "ira_user_memories_v2"
    ENTITY_COLLECTION = "ira_entity_memories_v2"
    
    # Legacy collections (OpenAI 1536d) - kept for migration reference
    LEGACY_USER_COLLECTION = "ira_user_memories"
    LEGACY_ENTITY_COLLECTION = "ira_entity_memories"
    
    def __init__(self):
        self._conn = None
        self._qdrant = None
        self._openai = None
        self._voyage = None
        self._schema_initialized = False
    
    # =========================================================================
    # DATABASE
    # =========================================================================
    
    def _get_db(self):
        """Get PostgreSQL connection."""
        if self._conn is None or self._conn.closed:
            import psycopg2
            self._conn = psycopg2.connect(DATABASE_URL)
        return self._conn
    
    def _get_qdrant(self):
        """Get Qdrant client for semantic search."""
        if self._qdrant is None:
            from qdrant_client import QdrantClient
            self._qdrant = QdrantClient(url=QDRANT_URL)
        return self._qdrant
    
    def _get_openai(self):
        """Get OpenAI client (for LLM calls, not embeddings)."""
        if self._openai is None:
            from openai import OpenAI
            self._openai = OpenAI(api_key=OPENAI_API_KEY)
        return self._openai
    
    def _get_voyage(self):
        """Get Voyage client for embeddings."""
        if self._voyage is None:
            import voyageai
            self._voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
        return self._voyage
    
    def ensure_schema(self) -> bool:
        """Initialize database schema."""
        if self._schema_initialized:
            return True
        
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            cursor.execute("CREATE SCHEMA IF NOT EXISTS ira_memory;")
            
            for stmt in PERSISTENT_MEMORY_SCHEMA.split(';'):
                stmt = stmt.strip()
                if stmt and not stmt.startswith('--'):
                    try:
                        cursor.execute(stmt)
                    except Exception as e:
                        if 'already exists' not in str(e).lower():
                            print(f"[persistent_memory] Schema warning: {e}")
            
            conn.commit()
            self._schema_initialized = True
            print("[persistent_memory] Schema initialized")
            return True
            
        except Exception as e:
            print(f"[persistent_memory] Schema error: {e}")
            return False
    
    def _ensure_qdrant_collection(self, collection_name: str):
        """Ensure Qdrant collection exists with Voyage-3 dimensions (1024d)."""
        try:
            qdrant = self._get_qdrant()
            from qdrant_client.models import Distance, VectorParams
            
            collections = [c.name for c in qdrant.get_collections().collections]
            if collection_name not in collections:
                qdrant.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE)
                )
                print(f"[persistent_memory] Created Qdrant collection: {collection_name} (Voyage-3, {EMBEDDING_DIMENSION}d)")
        except Exception as e:
            print(f"[persistent_memory] Qdrant setup warning: {e}")
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using Voyage-3 (consistent with retrieval)."""
        client = self._get_voyage()
        result = client.embed(
            [text[:8000]],  # Voyage has input limits
            model=EMBEDDING_MODEL,
            input_type="document"
        )
        return result.embeddings[0]
    
    # =========================================================================
    # USER MEMORY STORAGE
    # =========================================================================
    
    def store_memory(
        self,
        identity_id: str,
        memory_text: str,
        memory_type: str = "fact",
        source_channel: str = None,
        source_conversation_id: str = None,
        confidence: float = 1.0,
        embed: bool = True
    ) -> Optional[int]:
        """Store a new persistent memory for a user."""
        self.ensure_schema()
        
        if self._is_duplicate(identity_id, memory_text):
            print(f"[persistent_memory] Skipping duplicate: {memory_text[:50]}...")
            return None
        
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO ira_memory.user_memories
                (identity_id, memory_text, memory_type, source_channel, 
                 source_conversation_id, confidence, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (
                identity_id, memory_text, memory_type, source_channel,
                source_conversation_id, confidence
            ))
            
            memory_id = cursor.fetchone()[0]
            conn.commit()
            
            if embed:
                try:
                    self._embed_memory(memory_id, identity_id, memory_text)
                except Exception as e:
                    print(f"[persistent_memory] Embedding failed (non-fatal): {e}")
            
            print(f"[persistent_memory] Stored [{memory_type}]: {memory_text[:50]}...")
            return memory_id
            
        except Exception as e:
            print(f"[persistent_memory] Store error: {e}")
            if self._conn:
                self._conn.rollback()
            return None
    
    def _embed_memory(self, memory_id: int, identity_id: str, memory_text: str):
        """Create and store embedding for a memory."""
        self._ensure_qdrant_collection(self.QDRANT_COLLECTION)
        
        embedding = self._get_embedding(memory_text)
        point_id = str(uuid.uuid4())
        
        qdrant = self._get_qdrant()
        from qdrant_client.models import PointStruct
        
        qdrant.upsert(
            collection_name=self.QDRANT_COLLECTION,
            points=[PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "memory_id": memory_id,
                    "identity_id": identity_id,
                    "memory_text": memory_text
                }
            )]
        )
        
        conn = self._get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE ira_memory.user_memories 
            SET embedding_id = %s 
            WHERE id = %s
        """, (point_id, memory_id))
        conn.commit()
    
    def _is_duplicate(self, identity_id: str, memory_text: str) -> bool:
        """Check if a very similar memory already exists."""
        existing = self.list_memories(identity_id, include_inactive=False)
        
        memory_lower = memory_text.lower().strip()
        
        for mem in existing:
            existing_lower = mem.memory_text.lower().strip()
            
            if existing_lower == memory_lower:
                return True
            
            mem_words = set(memory_lower.split())
            existing_words = set(existing_lower.split())
            
            if mem_words and existing_words:
                overlap = len(mem_words & existing_words) / max(len(mem_words), len(existing_words))
                if overlap > 0.8:
                    return True
        
        return False
    
    # =========================================================================
    # ENTITY MEMORY STORAGE
    # =========================================================================
    
    def store_entity_memory(
        self,
        entity_type: str,
        entity_name: str,
        memory_text: str,
        memory_type: str = "fact",
        source_channel: str = None,
        source_identity_id: str = None,
        confidence: float = 1.0,
        embed: bool = True
    ) -> Optional[int]:
        """Store a memory about an entity (company/contact)."""
        self.ensure_schema()
        
        normalized_name = self._normalize_entity_name(entity_name)
        
        if self._is_entity_duplicate(normalized_name, memory_text):
            print(f"[persistent_memory] Skipping duplicate entity memory: {memory_text[:50]}...")
            return None
        
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO ira_memory.entity_memories
                (entity_type, entity_name, normalized_name, memory_text, memory_type,
                 source_channel, source_identity_id, confidence, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (
                entity_type, entity_name, normalized_name, memory_text, memory_type,
                source_channel, source_identity_id, confidence
            ))
            
            memory_id = cursor.fetchone()[0]
            conn.commit()
            
            if embed:
                try:
                    self._embed_entity_memory(memory_id, entity_type, normalized_name, memory_text)
                except Exception as e:
                    print(f"[persistent_memory] Entity embedding failed (non-fatal): {e}")
            
            print(f"[persistent_memory] Stored entity [{entity_type}:{entity_name}]: {memory_text[:50]}...")
            return memory_id
            
        except Exception as e:
            print(f"[persistent_memory] Entity store error: {e}")
            if self._conn:
                self._conn.rollback()
            return None
    
    def _normalize_entity_name(self, name: str) -> str:
        """Normalize entity name for matching."""
        name = name.lower().strip()
        name = re.sub(r'\s+(inc|corp|ltd|llc|gmbh|co|company)\.?$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', ' ', name)
        return name.strip()
    
    def _embed_entity_memory(self, memory_id: int, entity_type: str, normalized_name: str, memory_text: str):
        """Create embedding for entity memory."""
        self._ensure_qdrant_collection(self.ENTITY_COLLECTION)
        
        embedding = self._get_embedding(f"{entity_type}: {normalized_name} - {memory_text}")
        point_id = str(uuid.uuid4())
        
        qdrant = self._get_qdrant()
        from qdrant_client.models import PointStruct
        
        qdrant.upsert(
            collection_name=self.ENTITY_COLLECTION,
            points=[PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "memory_id": memory_id,
                    "entity_type": entity_type,
                    "normalized_name": normalized_name,
                    "memory_text": memory_text
                }
            )]
        )
        
        conn = self._get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE ira_memory.entity_memories 
            SET embedding_id = %s 
            WHERE id = %s
        """, (point_id, memory_id))
        conn.commit()
    
    def _is_entity_duplicate(self, normalized_name: str, memory_text: str) -> bool:
        """Check if entity memory is duplicate."""
        existing = self.get_entity_memories(normalized_name)
        memory_lower = memory_text.lower().strip()
        
        for mem in existing:
            existing_lower = mem.memory_text.lower().strip()
            if existing_lower == memory_lower:
                return True
            
            mem_words = set(memory_lower.split())
            existing_words = set(existing_lower.split())
            if mem_words and existing_words:
                overlap = len(mem_words & existing_words) / max(len(mem_words), len(existing_words))
                if overlap > 0.8:
                    return True
        
        return False
    
    def update_entity_memory(
        self,
        memory_id: int,
        new_memory_text: str,
        re_embed: bool = True
    ) -> bool:
        """
        Update an existing entity memory with new text.
        Used for conflict resolution when user chooses new/merged text.
        
        Args:
            memory_id: ID of the memory to update
            new_memory_text: The new text to replace the old
            re_embed: Whether to regenerate the embedding
            
        Returns:
            True if successful, False otherwise
        """
        self.ensure_schema()
        
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            # Get existing memory for entity info
            cursor.execute("""
                SELECT entity_type, entity_name, normalized_name, embedding_id
                FROM ira_memory.entity_memories
                WHERE id = %s
            """, (memory_id,))
            
            row = cursor.fetchone()
            if not row:
                print(f"[persistent_memory] Memory {memory_id} not found")
                return False
            
            entity_type, entity_name, normalized_name, old_embedding_id = row
            
            # Update the memory text
            cursor.execute("""
                UPDATE ira_memory.entity_memories
                SET memory_text = %s,
                    last_used_at = NOW()
                WHERE id = %s
            """, (new_memory_text, memory_id))
            
            conn.commit()
            
            # Re-embed if requested
            if re_embed:
                try:
                    # Delete old embedding from Qdrant if exists
                    if old_embedding_id:
                        try:
                            qdrant = self._get_qdrant()
                            qdrant.delete(
                                collection_name=self.ENTITY_COLLECTION,
                                points_selector=[old_embedding_id]
                            )
                        except Exception:
                            pass
                    
                    # Create new embedding
                    self._embed_entity_memory(memory_id, entity_type, normalized_name, new_memory_text)
                except Exception as e:
                    print(f"[persistent_memory] Re-embedding failed (non-fatal): {e}")
            
            print(f"[persistent_memory] Updated memory {memory_id}: {new_memory_text[:50]}...")
            return True
            
        except Exception as e:
            print(f"[persistent_memory] Update error: {e}")
            if self._conn:
                self._conn.rollback()
            return False
    
    def delete_entity_memory(self, memory_id: int) -> bool:
        """Delete an entity memory (soft delete - marks inactive)."""
        self.ensure_schema()
        
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE ira_memory.entity_memories
                SET is_active = FALSE
                WHERE id = %s
            """, (memory_id,))
            
            conn.commit()
            print(f"[persistent_memory] Deleted memory {memory_id}")
            return True
            
        except Exception as e:
            print(f"[persistent_memory] Delete error: {e}")
            return False
    
    # =========================================================================
    # RETRIEVAL
    # =========================================================================
    
    def retrieve_for_prompt(
        self,
        identity_id: str,
        query: str = None,
        limit: int = 5,
        min_relevance: float = 0.3
    ) -> List[UserMemory]:
        """
        Retrieve relevant user memories for prompt.
        
        Scoring combines:
        - Semantic similarity (how relevant to query)
        - Importance score (how valuable the memory is)
        - Confidence (has it decayed?)
        - Usage (frequently used = more important)
        """
        self.ensure_schema()
        
        all_memories = self.list_memories(identity_id, include_inactive=False)
        
        if not all_memories:
            return []
        
        # Calculate importance scores for all memories
        importance_map = {}
        for mem in all_memories:
            # Base importance from confidence and usage
            base_importance = mem.confidence * 0.4
            usage_boost = min(mem.use_count / 10, 1.0) * 0.2
            
            # Type bonus
            type_bonus = {
                "fact": 0.15, "correction": 0.2, "preference": 0.12,
                "context": 0.1, "relationship": 0.08
            }.get(mem.memory_type, 0.05)
            
            # Specificity bonus (numbers, names = more specific)
            specificity = 0.1 if any(c.isdigit() for c in mem.memory_text) else 0.0
            specificity += 0.05 if len(mem.memory_text) > 60 else 0.0
            
            importance_map[mem.id] = base_importance + usage_boost + type_bonus + specificity
        
        if not query:
            # No query - return most important memories
            for mem in all_memories:
                mem.relevance_score = importance_map.get(mem.id, 0.5)
            all_memories.sort(key=lambda m: m.relevance_score, reverse=True)
            return all_memories[:limit]
        
        try:
            self._ensure_qdrant_collection(self.QDRANT_COLLECTION)
            query_embedding = self._get_embedding(query)
            
            qdrant = self._get_qdrant()
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            results = qdrant.query_points(
                collection_name=self.QDRANT_COLLECTION,
                query=query_embedding,
                query_filter=Filter(
                    must=[FieldCondition(
                        key="identity_id",
                        match=MatchValue(value=identity_id)
                    )]
                ),
                limit=limit * 3,
                with_payload=True
            )
            
            semantic_map = {}
            for r in results.points:
                mem_id = r.payload.get("memory_id")
                if mem_id:
                    semantic_map[mem_id] = r.score
            
            scored_memories = []
            for mem in all_memories:
                # Combined score: 50% semantic, 50% importance
                semantic_score = semantic_map.get(mem.id, 0.0)
                importance_score = importance_map.get(mem.id, 0.5)
                
                # If semantically relevant, weight semantic more
                if semantic_score > 0.5:
                    mem.relevance_score = semantic_score * 0.6 + importance_score * 0.4
                else:
                    # Low semantic match - rely more on importance
                    mem.relevance_score = semantic_score * 0.3 + importance_score * 0.7
                
                # Always include high-importance memories even with low semantic match
                if mem.relevance_score >= min_relevance or importance_score > 0.6:
                    scored_memories.append(mem)
            
            scored_memories.sort(key=lambda m: m.relevance_score, reverse=True)
            memories = scored_memories[:limit]
            
        except Exception as e:
            print(f"[persistent_memory] Semantic search failed: {e}")
            for mem in all_memories:
                mem.relevance_score = importance_map.get(mem.id, 0.5)
            all_memories.sort(key=lambda m: m.relevance_score, reverse=True)
            memories = all_memories[:limit]
        
        self._update_usage(memories)
        return memories
    
    def retrieve_entity_memories(
        self,
        query: str,
        entity_names: List[str] = None,
        limit: int = 5
    ) -> List[EntityMemory]:
        """Retrieve relevant entity memories."""
        self.ensure_schema()
        
        memories = []
        
        # Direct lookup if entity names provided
        if entity_names:
            for name in entity_names:
                mems = self.get_entity_memories(name)
                memories.extend(mems)
        
        # Semantic search
        if query:
            try:
                self._ensure_qdrant_collection(self.ENTITY_COLLECTION)
                query_embedding = self._get_embedding(query)
                
                qdrant = self._get_qdrant()
                results = qdrant.query_points(
                    collection_name=self.ENTITY_COLLECTION,
                    query=query_embedding,
                    limit=limit,
                    with_payload=True
                )
                
                for r in results.points:
                    mem_id = r.payload.get("memory_id")
                    if mem_id and not any(m.id == mem_id for m in memories):
                        # Fetch full memory from DB
                        entity_mem = self._get_entity_memory_by_id(mem_id)
                        if entity_mem:
                            entity_mem.relevance_score = r.score
                            memories.append(entity_mem)
                            
            except Exception as e:
                print(f"[persistent_memory] Entity search failed: {e}")
        
        return memories[:limit]
    
    def _get_entity_memory_by_id(self, memory_id: int) -> Optional[EntityMemory]:
        """Get entity memory by ID."""
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, entity_type, entity_name, normalized_name, memory_text,
                       memory_type, source_channel, source_identity_id, confidence,
                       is_active, created_at, last_used_at, use_count, embedding_id
                FROM ira_memory.entity_memories
                WHERE id = %s AND is_active = TRUE
            """, (memory_id,))
            
            row = cursor.fetchone()
            if row:
                return EntityMemory.from_row(row)
            return None
            
        except Exception as e:
            print(f"[persistent_memory] Entity lookup error: {e}")
            return None
    
    def _update_usage(self, memories: List[UserMemory]):
        """Update usage stats for retrieved memories."""
        if not memories:
            return
        
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            ids = [m.id for m in memories if m.id]
            if ids:
                cursor.execute("""
                    UPDATE ira_memory.user_memories
                    SET last_used_at = NOW(), use_count = use_count + 1
                    WHERE id = ANY(%s)
                """, (ids,))
                conn.commit()
        except Exception as e:
            print(f"[persistent_memory] Usage update failed: {e}")
    
    def list_memories(
        self,
        identity_id: str,
        include_inactive: bool = False,
        limit: int = 50
    ) -> List[UserMemory]:
        """List all memories for a user."""
        self.ensure_schema()
        
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            if include_inactive:
                cursor.execute("""
                    SELECT id, identity_id, memory_text, memory_type, source_channel,
                           source_conversation_id, confidence, is_active,
                           created_at, last_used_at, use_count, embedding_id
                    FROM ira_memory.user_memories
                    WHERE identity_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (identity_id, limit))
            else:
                cursor.execute("""
                    SELECT id, identity_id, memory_text, memory_type, source_channel,
                           source_conversation_id, confidence, is_active,
                           created_at, last_used_at, use_count, embedding_id
                    FROM ira_memory.user_memories
                    WHERE identity_id = %s AND is_active = TRUE
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (identity_id, limit))
            
            return [UserMemory.from_row(row) for row in cursor.fetchall()]
            
        except Exception as e:
            print(f"[persistent_memory] List error: {e}")
            return []
    
    def get_entity_memories(self, entity_name: str, limit: int = 20) -> List[EntityMemory]:
        """Get all memories about an entity."""
        self.ensure_schema()
        
        normalized = self._normalize_entity_name(entity_name)
        
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, entity_type, entity_name, normalized_name, memory_text,
                       memory_type, source_channel, source_identity_id, confidence,
                       is_active, created_at, last_used_at, use_count, embedding_id
                FROM ira_memory.entity_memories
                WHERE normalized_name = %s AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT %s
            """, (normalized, limit))
            
            return [EntityMemory.from_row(row) for row in cursor.fetchall()]
            
        except Exception as e:
            print(f"[persistent_memory] Entity list error: {e}")
            return []
    
    # =========================================================================
    # EXTRACTION
    # =========================================================================
    
    def extract_and_store(
        self,
        identity_id: str,
        user_message: str,
        assistant_response: str,
        source_channel: str = "telegram",
        source_conversation_id: str = None
    ) -> Dict[str, List[int]]:
        """
        Extract all types of memories from a conversation.
        
        Returns dict with created memory IDs by type.
        """
        if not identity_id:
            return {"user": [], "entity": [], "correction": []}
        
        existing = self.list_memories(identity_id, include_inactive=False)
        existing_text = "\n".join([f"- {m.memory_text}" for m in existing[:10]])
        if not existing_text:
            existing_text = "(No existing memories)"
        
        prompt = MEMORY_EXTRACTION_PROMPT.format(
            user_message=user_message[:1000],
            assistant_response=assistant_response[:1000],
            existing_memories=existing_text
        )
        
        result = {"user": [], "entity": [], "correction": []}
        
        try:
            client = self._get_openai()
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You extract memorable facts from conversations. Output valid JSON only."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            response_text = response.choices[0].message.content.strip()
            
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            data = json.loads(response_text)
            
            # Store user memories
            for mem_data in data.get("user_memories", [])[:3]:
                memory_text = mem_data.get("memory", "").strip()
                memory_type = mem_data.get("type", "fact")
                
                if memory_text and len(memory_text) > 10:
                    memory_id = self.store_memory(
                        identity_id=identity_id,
                        memory_text=memory_text,
                        memory_type=memory_type,
                        source_channel=source_channel,
                        source_conversation_id=source_conversation_id,
                        confidence=0.9
                    )
                    if memory_id:
                        result["user"].append(memory_id)
            
            # Store entity memories
            for mem_data in data.get("entity_memories", [])[:3]:
                entity_type = mem_data.get("entity_type", "company")
                entity_name = mem_data.get("entity_name", "").strip()
                memory_text = mem_data.get("memory", "").strip()
                
                if entity_name and memory_text and len(memory_text) > 10:
                    memory_id = self.store_entity_memory(
                        entity_type=entity_type,
                        entity_name=entity_name,
                        memory_text=memory_text,
                        source_channel=source_channel,
                        source_identity_id=identity_id,
                        confidence=0.85
                    )
                    if memory_id:
                        result["entity"].append(memory_id)
            
            # Store corrections as high-confidence memories
            for corr_data in data.get("corrections", [])[:2]:
                memory_text = corr_data.get("memory", "").strip()
                
                if memory_text and len(memory_text) > 10:
                    memory_id = self.store_memory(
                        identity_id=identity_id,
                        memory_text=f"[CORRECTION] {memory_text}",
                        memory_type="correction",
                        source_channel=source_channel,
                        source_conversation_id=source_conversation_id,
                        confidence=1.0  # High confidence for explicit corrections
                    )
                    if memory_id:
                        result["correction"].append(memory_id)
            
            total = len(result["user"]) + len(result["entity"]) + len(result["correction"])
            if total > 0:
                print(f"[persistent_memory] Extracted {total} memories for {identity_id}")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"[persistent_memory] JSON parse error: {e}")
            return result
        except Exception as e:
            print(f"[persistent_memory] Extraction error: {e}")
            return result
    
    # =========================================================================
    # PROACTIVE SUGGESTIONS
    # =========================================================================
    
    def get_proactive_suggestion(
        self,
        identity_id: str,
        current_context: str,
        recent_message: str
    ) -> Optional[Dict]:
        """
        Generate a proactive suggestion based on memories.
        
        Returns suggestion dict or None if nothing useful.
        """
        user_memories = self.list_memories(identity_id, include_inactive=False)
        if not user_memories:
            return None
        
        # Get entity memories mentioned in recent message
        entity_memories = self.retrieve_entity_memories(recent_message, limit=5)
        
        user_mem_text = "\n".join([f"- [{m.memory_type}] {m.memory_text}" for m in user_memories[:8]])
        entity_mem_text = "\n".join([f"- [{m.entity_name}] {m.memory_text}" for m in entity_memories[:5]])
        
        prompt = PROACTIVE_SUGGESTION_PROMPT.format(
            user_memories=user_mem_text or "(none)",
            entity_memories=entity_mem_text or "(none)",
            current_context=current_context[:500],
            recent_message=recent_message[:500]
        )
        
        try:
            client = self._get_openai()
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You suggest helpful proactive actions based on user memories. Be natural and helpful, not creepy. Return valid JSON or null."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if result_text.lower() == "null" or not result_text:
                return None
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            suggestion = json.loads(result_text)
            
            if suggestion and suggestion.get("suggestion"):
                return suggestion
            return None
            
        except Exception as e:
            print(f"[persistent_memory] Proactive suggestion error: {e}")
            return None
    
    # =========================================================================
    # USER COMMANDS
    # =========================================================================
    
    def delete_memory(self, identity_id: str, memory_id: int) -> bool:
        """Delete (deactivate) a memory."""
        self.ensure_schema()
        
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE ira_memory.user_memories
                SET is_active = FALSE
                WHERE id = %s AND identity_id = %s
                RETURNING id
            """, (memory_id, identity_id))
            
            result = cursor.fetchone()
            conn.commit()
            
            if result:
                print(f"[persistent_memory] Deleted memory {memory_id}")
                return True
            return False
            
        except Exception as e:
            print(f"[persistent_memory] Delete error: {e}")
            return False
    
    def handle_explicit_remember(
        self,
        identity_id: str,
        message: str,
        source_channel: str = "telegram"
    ) -> Tuple[bool, str]:
        """Handle explicit 'remember that...' commands."""
        patterns = [
            r"remember\s+that\s+(.+)",
            r"remember:\s*(.+)",
            r"note\s+that\s+(.+)",
            r"keep\s+in\s+mind\s+that\s+(.+)",
        ]
        
        message_lower = message.lower().strip()
        
        for pattern in patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                memory_text = match.group(1).strip()
                memory_text = memory_text[0].upper() + memory_text[1:] if memory_text else memory_text
                
                if len(memory_text) < 5:
                    return False, "That's too short to remember. Please be more specific."
                
                memory_id = self.store_memory(
                    identity_id=identity_id,
                    memory_text=memory_text,
                    memory_type="preference",
                    source_channel=source_channel,
                    confidence=1.0
                )
                
                if memory_id:
                    return True, f"Got it! I'll remember: \"{memory_text}\""
                else:
                    return False, "I already know that, or something very similar."
        
        return False, None
    
    def handle_forget_command(
        self,
        identity_id: str,
        message: str
    ) -> Tuple[bool, str]:
        """Handle 'forget' commands."""
        message_lower = message.lower().strip()
        
        id_match = re.search(r"forget\s+(?:#|memory\s*)?(\d+)", message_lower)
        if id_match:
            memory_id = int(id_match.group(1))
            if self.delete_memory(identity_id, memory_id):
                return True, f"Done! I've forgotten memory #{memory_id}."
            return False, f"Couldn't find memory #{memory_id} or it doesn't belong to you."
        
        text_match = re.search(r"forget\s+that\s+(.+)", message_lower, re.IGNORECASE)
        if text_match:
            search_text = text_match.group(1).strip()
            memories = self.list_memories(identity_id)
            
            for mem in memories:
                if search_text.lower() in mem.memory_text.lower():
                    if self.delete_memory(identity_id, mem.id):
                        return True, f"Done! I've forgotten: \"{mem.memory_text}\""
            
            return False, f"I couldn't find a memory matching '{search_text}'."
        
        return False, None
    
    def format_memories_for_display(self, identity_id: str) -> str:
        """Format all memories for display to user."""
        memories = self.list_memories(identity_id, include_inactive=False)
        
        if not memories:
            return "I don't have any memories about you yet. As we chat, I'll remember important things!"
        
        lines = ["**What I Remember About You:**\n"]
        
        by_type = {}
        for mem in memories:
            t = mem.memory_type
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(mem)
        
        type_labels = {
            "fact": "📋 Facts",
            "preference": "⭐ Preferences",
            "context": "💼 Context",
            "relationship": "👥 Relationships",
            "correction": "✏️ Corrections"
        }
        
        for mem_type, mems in by_type.items():
            label = type_labels.get(mem_type, mem_type.title())
            lines.append(f"\n{label}:")
            for mem in mems:
                lines.append(f"  #{mem.id}: {mem.memory_text}")
        
        lines.append(f"\n_Total: {len(memories)} memories_")
        lines.append("_To delete: say 'forget #N' where N is the memory number_")
        
        return "\n".join(lines)
    
    def format_memories_for_prompt(self, memories: List[UserMemory]) -> str:
        """Format memories for inclusion in LLM system prompt."""
        if not memories:
            return ""
        
        lines = ["## What I Remember About This User"]
        
        for mem in memories:
            lines.append(f"- {mem.memory_text}")
        
        lines.append("")
        lines.append("Use these memories to personalize your response. Reference relevant facts naturally.")
        
        return "\n".join(lines)
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def get_stats(self, identity_id: str = None) -> Dict:
        """Get memory statistics."""
        self.ensure_schema()
        
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            # User memories
            if identity_id:
                cursor.execute("""
                    SELECT memory_type, COUNT(*) 
                    FROM ira_memory.user_memories
                    WHERE identity_id = %s AND is_active = TRUE
                    GROUP BY memory_type
                """, (identity_id,))
            else:
                cursor.execute("""
                    SELECT memory_type, COUNT(*) 
                    FROM ira_memory.user_memories
                    WHERE is_active = TRUE
                    GROUP BY memory_type
                """)
            
            user_type_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            cursor.execute("SELECT COUNT(*) FROM ira_memory.user_memories WHERE is_active = TRUE")
            total_user = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT identity_id) FROM ira_memory.user_memories WHERE is_active = TRUE")
            users_with_memories = cursor.fetchone()[0]
            
            # Entity memories
            cursor.execute("SELECT COUNT(*) FROM ira_memory.entity_memories WHERE is_active = TRUE")
            total_entity = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT entity_type, COUNT(*) 
                FROM ira_memory.entity_memories
                WHERE is_active = TRUE
                GROUP BY entity_type
            """)
            entity_type_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                "user_memories": {
                    "total": total_user,
                    "users_with_memories": users_with_memories,
                    "by_type": user_type_counts
                },
                "entity_memories": {
                    "total": total_entity,
                    "by_type": entity_type_counts
                }
            }
            
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# SINGLETON
# =============================================================================

_persistent_memory: Optional[PersistentMemory] = None


def get_persistent_memory() -> PersistentMemory:
    """Get singleton PersistentMemory instance."""
    global _persistent_memory
    if _persistent_memory is None:
        _persistent_memory = PersistentMemory()
    return _persistent_memory


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Persistent Memory CLI")
    parser.add_argument("--init", action="store_true", help="Initialize schema")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--list", type=str, metavar="IDENTITY_ID", help="List memories for user")
    parser.add_argument("--entities", type=str, metavar="ENTITY_NAME", help="List entity memories")
    parser.add_argument("--test", action="store_true", help="Run test extraction")
    
    args = parser.parse_args()
    
    pm = PersistentMemory()
    
    if args.init:
        pm.ensure_schema()
        print("Schema initialized")
    
    elif args.stats:
        print(json.dumps(pm.get_stats(), indent=2))
    
    elif args.list:
        memories = pm.list_memories(args.list)
        for m in memories:
            print(f"#{m.id} [{m.memory_type}] {m.memory_text}")
    
    elif args.entities:
        memories = pm.get_entity_memories(args.entities)
        for m in memories:
            print(f"#{m.id} [{m.entity_type}:{m.entity_name}] {m.memory_text}")
    
    elif args.test:
        print("=" * 60)
        print("PERSISTENT MEMORY - TEST")
        print("=" * 60)
        
        test_identity = "test_user_001"
        
        print("\n1. Testing memory extraction...")
        created = pm.extract_and_store(
            identity_id=test_identity,
            user_message="Hi, I'm John from ABC Manufacturing. We're looking for thermoforming machines for automotive interior parts. We typically order 2-3 machines per year. Actually, the PF1-3020 price should be $45k not $50k.",
            assistant_response="Hello John! Great to hear from ABC Manufacturing. For automotive interior parts, our PF1 series would be ideal. What forming areas are you typically working with?",
            source_channel="telegram"
        )
        print(f"   Created: {created}")
        
        print("\n2. Testing memory retrieval...")
        memories = pm.retrieve_for_prompt(
            identity_id=test_identity,
            query="What machines for automotive?",
            limit=5
        )
        print(f"   Retrieved {len(memories)} user memories:")
        for m in memories:
            print(f"   - [{m.memory_type}] {m.memory_text}")
        
        print("\n3. Testing entity memories...")
        entity_mems = pm.get_entity_memories("ABC Manufacturing")
        print(f"   Found {len(entity_mems)} entity memories:")
        for m in entity_mems:
            print(f"   - [{m.entity_type}] {m.memory_text}")
        
        print("\n4. Testing proactive suggestion...")
        suggestion = pm.get_proactive_suggestion(
            identity_id=test_identity,
            current_context="Discussing machine options",
            recent_message="What about pricing?"
        )
        if suggestion:
            print(f"   Suggestion: {suggestion.get('suggestion')}")
        else:
            print("   No suggestion generated")
        
        print("\n5. Display format:")
        print(pm.format_memories_for_display(test_identity))
        
        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
    
    else:
        parser.print_help()
