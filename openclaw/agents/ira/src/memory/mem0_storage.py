#!/usr/bin/env python3
"""
MEM0 STORAGE - PostgreSQL Replacement Layer

╔════════════════════════════════════════════════════════════════════════════╗
║  This module provides PostgreSQL-like storage using Mem0.                  ║
║  Use this when you want to eliminate PostgreSQL dependency.                ║
║                                                                            ║
║  Storage Strategy:                                                         ║
║  - Episodic memories → Mem0 with user_id = identity + metadata             ║
║  - Procedural memories → Mem0 with agent_id = "procedures"                 ║
║  - Relationships → Mem0 with metadata linking                              ║
║  - JSON file backup for critical data                                      ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

import json
import hashlib
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Load environment
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    import os
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


# =============================================================================
# CONFIGURATION
# =============================================================================

DATA_DIR = PROJECT_ROOT / "data" / "mem0_storage"
EPISODES_FILE = DATA_DIR / "episodes.json"
PROCEDURES_FILE = DATA_DIR / "procedures.json"


# =============================================================================
# EPISODIC MEMORY STORAGE (was PostgreSQL)
# =============================================================================

@dataclass
class StoredEpisode:
    """An episode stored in Mem0."""
    id: str
    identity_id: str
    timestamp: str
    summary: str
    topics: List[str] = field(default_factory=list)
    outcome: str = ""
    channel: str = "unknown"
    emotional_valence: int = 0
    importance: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_mem0_format(self) -> str:
        """Convert to Mem0-storable text."""
        return f"""Episode {self.timestamp} ({self.channel}):
{self.summary}
Topics: {', '.join(self.topics)}
Outcome: {self.outcome}
Importance: {self.importance}"""


class EpisodicMem0Store:
    """
    Stores episodic memories in Mem0 + local JSON backup.
    
    Replaces PostgreSQL ira_memory.episodes table.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        import os
        self.api_key = api_key or os.environ.get("MEM0_API_KEY")
        self._client = None
        self._local_cache: Dict[str, Dict[str, StoredEpisode]] = {}
        self._load_local()
    
    def _get_client(self):
        if self._client is None and self.api_key:
            try:
                from mem0 import MemoryClient
                self._client = MemoryClient(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Episodic Mem0 unavailable: {e}")
        return self._client
    
    def _load_local(self):
        """Load local backup."""
        if EPISODES_FILE.exists():
            try:
                data = json.loads(EPISODES_FILE.read_text())
                for identity_id, episodes in data.items():
                    self._local_cache[identity_id] = {
                        ep_id: StoredEpisode(**ep) 
                        for ep_id, ep in episodes.items()
                    }
            except Exception as e:
                logger.error(f"Episodic load error: {e}")
    
    def _save_local(self):
        """Save to local backup."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            identity_id: {ep_id: ep.__dict__ for ep_id, ep in episodes.items()}
            for identity_id, episodes in self._local_cache.items()
        }
        EPISODES_FILE.write_text(json.dumps(data, indent=2, default=str))
    
    def store_episode(
        self,
        identity_id: str,
        summary: str,
        topics: List[str],
        outcome: str = "",
        channel: str = "unknown",
        emotional_valence: int = 0,
        importance: float = 0.5,
        **kwargs
    ) -> str:
        """Store a new episode."""
        episode = StoredEpisode(
            id=f"ep_{uuid.uuid4().hex[:12]}",
            identity_id=identity_id,
            timestamp=datetime.now().isoformat(),
            summary=summary,
            topics=topics,
            outcome=outcome,
            channel=channel,
            emotional_valence=emotional_valence,
            importance=importance,
            metadata=kwargs,
        )
        
        # Store in local cache
        if identity_id not in self._local_cache:
            self._local_cache[identity_id] = {}
        self._local_cache[identity_id][episode.id] = episode
        self._save_local()
        
        # Store in Mem0
        client = self._get_client()
        if client:
            try:
                client.add(
                    messages=[{"role": "user", "content": episode.to_mem0_format()}],
                    user_id=identity_id,
                    metadata={
                        "type": "episode",
                        "episode_id": episode.id,
                        "channel": channel,
                        "importance": importance,
                        "topics": topics,
                    }
                )
            except Exception as e:
                logger.error(f"Episodic Mem0 store error: {e}")
        
        return episode.id
    
    def get_episodes(
        self,
        identity_id: str,
        limit: int = 10,
        since: Optional[datetime] = None,
    ) -> List[StoredEpisode]:
        """Get recent episodes for a user."""
        episodes = list(self._local_cache.get(identity_id, {}).values())
        
        if since:
            episodes = [
                ep for ep in episodes 
                if datetime.fromisoformat(ep.timestamp) >= since
            ]
        
        episodes.sort(key=lambda x: x.timestamp, reverse=True)
        return episodes[:limit]
    
    def search_episodes(
        self,
        identity_id: str,
        query: str,
        limit: int = 5,
    ) -> List[StoredEpisode]:
        """Search episodes by content (uses Mem0 semantic search)."""
        client = self._get_client()
        if not client:
            # Fall back to local search
            episodes = self._local_cache.get(identity_id, {}).values()
            query_lower = query.lower()
            matched = [
                ep for ep in episodes
                if query_lower in ep.summary.lower() or 
                any(query_lower in t.lower() for t in ep.topics)
            ]
            return matched[:limit]
        
        try:
            results = client.search(
                query=query,
                version="v2",
                filters={"user_id": identity_id, "type": "episode"},
                top_k=limit,
            )
            
            # Convert back to StoredEpisode
            episodes = []
            for mem in results.get("results", results.get("memories", [])):
                episode_id = mem.get("metadata", {}).get("episode_id")
                if episode_id and episode_id in self._local_cache.get(identity_id, {}):
                    episodes.append(self._local_cache[identity_id][episode_id])
            
            return episodes
        except Exception as e:
            logger.error(f"Episodic search error: {e}")
            return []


# =============================================================================
# PROCEDURAL MEMORY STORAGE (was PostgreSQL)
# =============================================================================

@dataclass
class StoredProcedure:
    """A procedure stored in Mem0."""
    id: str
    name: str
    trigger_patterns: List[str]
    steps: List[Dict[str, Any]]
    description: str = ""
    success_count: int = 0
    failure_count: int = 0
    confidence: float = 0.5
    source: str = "learned"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_mem0_format(self) -> str:
        """Convert to searchable text."""
        steps_text = "\n".join([
            f"  {i+1}. {s.get('action', '')}: {s.get('description', '')}"
            for i, s in enumerate(self.steps)
        ])
        return f"""Procedure: {self.name}
Triggers: {', '.join(self.trigger_patterns)}
Description: {self.description}
Steps:
{steps_text}
Confidence: {self.confidence:.0%}"""


class ProceduralMem0Store:
    """
    Stores procedural memories in Mem0 + local JSON backup.
    
    Replaces PostgreSQL ira_memory.procedures table.
    """
    
    AGENT_ID = "ira_procedures"
    
    def __init__(self, api_key: Optional[str] = None):
        import os
        self.api_key = api_key or os.environ.get("MEM0_API_KEY")
        self._client = None
        self._procedures: Dict[str, StoredProcedure] = {}
        self._load_local()
    
    def _get_client(self):
        if self._client is None and self.api_key:
            try:
                from mem0 import MemoryClient
                self._client = MemoryClient(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Procedural Mem0 unavailable: {e}")
        return self._client
    
    def _load_local(self):
        """Load local backup."""
        if PROCEDURES_FILE.exists():
            try:
                data = json.loads(PROCEDURES_FILE.read_text())
                self._procedures = {
                    proc_id: StoredProcedure(**proc)
                    for proc_id, proc in data.items()
                }
            except Exception as e:
                logger.error(f"Procedural load error: {e}")
    
    def _save_local(self):
        """Save to local backup."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = {proc_id: proc.__dict__ for proc_id, proc in self._procedures.items()}
        PROCEDURES_FILE.write_text(json.dumps(data, indent=2, default=str))
    
    def store_procedure(
        self,
        name: str,
        trigger_patterns: List[str],
        steps: List[Dict[str, Any]],
        description: str = "",
        source: str = "learned",
    ) -> str:
        """Store a new procedure."""
        proc = StoredProcedure(
            id=f"proc_{hashlib.md5(name.encode()).hexdigest()[:10]}",
            name=name,
            trigger_patterns=trigger_patterns,
            steps=steps,
            description=description,
            source=source,
        )
        
        self._procedures[proc.id] = proc
        self._save_local()
        
        # Store in Mem0
        client = self._get_client()
        if client:
            try:
                client.add(
                    messages=[{"role": "user", "content": proc.to_mem0_format()}],
                    agent_id=self.AGENT_ID,
                    metadata={
                        "type": "procedure",
                        "procedure_id": proc.id,
                        "name": name,
                        "triggers": trigger_patterns,
                    }
                )
            except Exception as e:
                logger.error(f"Procedural Mem0 store error: {e}")
        
        return proc.id
    
    def find_procedure(self, query: str) -> Optional[StoredProcedure]:
        """Find a procedure matching the query."""
        import re
        
        query_lower = query.lower()
        
        for proc in self._procedures.values():
            for pattern in proc.trigger_patterns:
                try:
                    if re.search(pattern, query_lower):
                        return proc
                except re.error:
                    if pattern.lower() in query_lower:
                        return proc
        
        return None
    
    def get_all(self) -> List[StoredProcedure]:
        """Get all procedures."""
        return list(self._procedures.values())
    
    def update_success(self, procedure_id: str):
        """Record successful use."""
        if procedure_id in self._procedures:
            proc = self._procedures[procedure_id]
            proc.success_count += 1
            total = proc.success_count + proc.failure_count
            proc.confidence = proc.success_count / total if total > 0 else 0.5
            self._save_local()
    
    def update_failure(self, procedure_id: str):
        """Record failed use."""
        if procedure_id in self._procedures:
            proc = self._procedures[procedure_id]
            proc.failure_count += 1
            total = proc.success_count + proc.failure_count
            proc.confidence = proc.success_count / total if total > 0 else 0.5
            self._save_local()


# =============================================================================
# RELATIONSHIP STORAGE (enhanced with Mem0)
# =============================================================================

@dataclass
class StoredRelationship:
    """A relationship between entities."""
    source: str
    relation: str
    target: str
    confidence: float = 1.0
    learned_from: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class RelationshipMem0Store:
    """
    Stores entity relationships in Mem0.
    
    This provides graph-like querying without Neo4j.
    """
    
    AGENT_ID = "ira_relationships"
    
    def __init__(self, api_key: Optional[str] = None):
        import os
        self.api_key = api_key or os.environ.get("MEM0_API_KEY")
        self._client = None
        self._relationships: List[StoredRelationship] = []
        self._load_local()
    
    def _get_client(self):
        if self._client is None and self.api_key:
            try:
                from mem0 import MemoryClient
                self._client = MemoryClient(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Relationship Mem0 unavailable: {e}")
        return self._client
    
    def _load_local(self):
        """Load from local file."""
        rel_file = DATA_DIR / "relationships.json"
        if rel_file.exists():
            try:
                data = json.loads(rel_file.read_text())
                self._relationships = [StoredRelationship(**r) for r in data]
            except Exception as e:
                logger.error(f"Relationship load error: {e}")
    
    def _save_local(self):
        """Save to local file."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        rel_file = DATA_DIR / "relationships.json"
        data = [r.__dict__ for r in self._relationships]
        rel_file.write_text(json.dumps(data, indent=2))
    
    def add_relationship(
        self,
        source: str,
        relation: str,
        target: str,
        confidence: float = 1.0,
        learned_from: str = "",
    ) -> bool:
        """Add a relationship."""
        rel = StoredRelationship(
            source=source,
            relation=relation,
            target=target,
            confidence=confidence,
            learned_from=learned_from,
        )
        
        # Check for duplicates
        for existing in self._relationships:
            if (existing.source == source and 
                existing.relation == relation and 
                existing.target == target):
                return False
        
        self._relationships.append(rel)
        self._save_local()
        
        # Store in Mem0
        client = self._get_client()
        if client:
            try:
                fact = f"{source} {relation.replace('_', ' ')} {target}"
                client.add(
                    messages=[{"role": "user", "content": fact}],
                    agent_id=self.AGENT_ID,
                    metadata={
                        "type": "relationship",
                        "source": source,
                        "relation": relation,
                        "target": target,
                        "confidence": confidence,
                    }
                )
            except Exception as e:
                logger.error(f"Relationship Mem0 store error: {e}")
        
        return True
    
    def get_relationships(
        self,
        entity: str,
        relation: Optional[str] = None,
    ) -> List[StoredRelationship]:
        """Get relationships for an entity."""
        entity_lower = entity.lower()
        results = []
        
        for rel in self._relationships:
            if rel.source.lower() == entity_lower or rel.target.lower() == entity_lower:
                if relation is None or rel.relation == relation:
                    results.append(rel)
        
        return results
    
    def search_relationships(self, query: str, limit: int = 10) -> List[StoredRelationship]:
        """Search relationships by semantic similarity."""
        client = self._get_client()
        if not client:
            # Local search
            query_lower = query.lower()
            return [
                r for r in self._relationships
                if query_lower in r.source.lower() or 
                query_lower in r.target.lower() or
                query_lower in r.relation.lower()
            ][:limit]
        
        try:
            results = client.search(
                query=query,
                version="v2",
                filters={"agent_id": self.AGENT_ID},
                top_k=limit,
            )
            
            # Match back to local relationships
            matched = []
            for mem in results.get("results", results.get("memories", [])):
                meta = mem.get("metadata", {})
                source = meta.get("source", "")
                relation = meta.get("relation", "")
                target = meta.get("target", "")
                
                for r in self._relationships:
                    if r.source == source and r.relation == relation and r.target == target:
                        matched.append(r)
                        break
            
            return matched
        except Exception as e:
            logger.error(f"Relationship search error: {e}")
            return []


# =============================================================================
# UNIFIED INTERFACE
# =============================================================================

class Mem0Storage:
    """
    Unified storage interface replacing PostgreSQL.
    
    Usage:
        storage = Mem0Storage()
        storage.episodes.store_episode(...)
        storage.procedures.store_procedure(...)
        storage.relationships.add_relationship(...)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        import os
        api_key = api_key or os.environ.get("MEM0_API_KEY")
        
        self.episodes = EpisodicMem0Store(api_key)
        self.procedures = ProceduralMem0Store(api_key)
        self.relationships = RelationshipMem0Store(api_key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return {
            "episodes": sum(len(eps) for eps in self.episodes._local_cache.values()),
            "procedures": len(self.procedures._procedures),
            "relationships": len(self.relationships._relationships),
            "backend": "mem0",
        }


_storage: Optional[Mem0Storage] = None


def get_mem0_storage() -> Mem0Storage:
    """Get or create the unified storage."""
    global _storage
    if _storage is None:
        _storage = Mem0Storage()
    return _storage


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    storage = get_mem0_storage()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python mem0_storage.py stats")
        print("  python mem0_storage.py episodes <identity_id>")
        print("  python mem0_storage.py procedures")
        print("  python mem0_storage.py relationships <entity>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "stats":
        print(json.dumps(storage.get_stats(), indent=2))
    
    elif cmd == "episodes" and len(sys.argv) >= 3:
        episodes = storage.episodes.get_episodes(sys.argv[2])
        for ep in episodes:
            print(f"[{ep.timestamp}] {ep.summary[:80]}")
    
    elif cmd == "procedures":
        for proc in storage.procedures.get_all():
            print(f"[{proc.confidence:.0%}] {proc.name}: {proc.trigger_patterns}")
    
    elif cmd == "relationships" and len(sys.argv) >= 3:
        rels = storage.relationships.get_relationships(sys.argv[2])
        for r in rels:
            print(f"{r.source} --{r.relation}--> {r.target}")
