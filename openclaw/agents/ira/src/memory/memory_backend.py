#!/usr/bin/env python3
"""
MEMORY BACKEND SELECTOR

Provides the correct memory implementation based on configuration.

Storage Backends:
  - "postgres": Full PostgreSQL (existing behavior, default)
  - "hybrid": Read both PostgreSQL + Mem0, write to Mem0 (transition period)
  - "mem0": Mem0 only (after migration complete)

Usage:
    from memory_backend import get_episodic_store, get_procedural_store
    
    episodes = get_episodic_store()
    procedures = get_procedural_store()
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Any, Tuple

# Load config
MEMORY_DIR = Path(__file__).parent
SKILLS_DIR = MEMORY_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
sys.path.insert(0, str(AGENT_DIR))

try:
    from config import FEATURES, STORAGE_BACKEND
except ImportError:
    FEATURES = {"use_postgres": True, "hybrid_mode": True}
    STORAGE_BACKEND = "hybrid"


def get_episodic_store():
    """
    Get the episodic memory store.
    
    Returns appropriate store based on STORAGE_BACKEND:
    - postgres: PostgreSQL only
    - hybrid: Reads both, writes to Mem0
    - mem0: Mem0 only
    """
    if STORAGE_BACKEND == "postgres":
        try:
            from .episodic_memory import get_episodic_memory
            return get_episodic_memory()
        except ImportError:
            from episodic_memory import get_episodic_memory
            return get_episodic_memory()
    
    elif STORAGE_BACKEND == "hybrid":
        # Hybrid: read from both, write to Mem0
        from .mem0_storage import get_mem0_storage
        storage = get_mem0_storage()
        mem0_store = Mem0EpisodicWrapper(storage.episodes)
        
        try:
            from .episodic_memory import get_episodic_memory
            pg_store = get_episodic_memory()
        except ImportError:
            pg_store = None
        
        return HybridEpisodicStore(pg_store, mem0_store)
    
    else:  # mem0
        from .mem0_storage import get_mem0_storage
        storage = get_mem0_storage()
        return Mem0EpisodicWrapper(storage.episodes)


def get_procedural_store():
    """
    Get the procedural memory store.
    
    Returns appropriate store based on STORAGE_BACKEND.
    """
    if STORAGE_BACKEND == "postgres":
        try:
            from .procedural_memory import get_procedural_memory
            return get_procedural_memory()
        except ImportError:
            from procedural_memory import get_procedural_memory
            return get_procedural_memory()
    
    elif STORAGE_BACKEND == "hybrid":
        from .mem0_storage import get_mem0_storage
        storage = get_mem0_storage()
        mem0_store = Mem0ProceduralWrapper(storage.procedures)
        
        try:
            from .procedural_memory import get_procedural_memory
            pg_store = get_procedural_memory()
        except ImportError:
            pg_store = None
        
        return HybridProceduralStore(pg_store, mem0_store)
    
    else:  # mem0
        from .mem0_storage import get_mem0_storage
        storage = get_mem0_storage()
        return Mem0ProceduralWrapper(storage.procedures)


def get_relationship_store():
    """
    Get the relationship store.
    
    Returns Mem0-backed relationship store.
    """
    from .mem0_storage import get_mem0_storage
    storage = get_mem0_storage()
    return storage.relationships


class Mem0EpisodicWrapper:
    """
    Wraps Mem0 episodic storage to match the PostgreSQL interface.
    
    Allows drop-in replacement without changing caller code.
    """
    
    def __init__(self, episodes_store):
        self._store = episodes_store
    
    def retrieve_for_prompt(
        self,
        identity_id: str,
        query: str,
        limit: int = 5,
    ) -> str:
        """Get episodes formatted for prompt injection."""
        # Try semantic search first
        episodes = self._store.search_episodes(identity_id, query, limit=limit)
        
        if not episodes:
            # Fall back to recent episodes
            episodes = self._store.get_episodes(identity_id, limit=limit)
        
        if not episodes:
            return ""
        
        lines = ["## Recent Episodes:"]
        for ep in episodes[:limit]:
            lines.append(f"- [{ep.timestamp[:10]}] {ep.summary}")
            if ep.outcome:
                lines.append(f"  Outcome: {ep.outcome}")
        
        return "\n".join(lines)
    
    def record_episode(
        self,
        identity_id: str,
        summary: str,
        topics: list = None,
        outcome: str = "",
        channel: str = "unknown",
        **kwargs
    ) -> str:
        """Record a new episode."""
        return self._store.store_episode(
            identity_id=identity_id,
            summary=summary,
            topics=topics or [],
            outcome=outcome,
            channel=channel,
            **kwargs
        )
    
    def get_recent(
        self,
        identity_id: str,
        limit: int = 10,
    ) -> list:
        """Get recent episodes."""
        return self._store.get_episodes(identity_id, limit=limit)


class Mem0ProceduralWrapper:
    """
    Wraps Mem0 procedural storage to match the PostgreSQL interface.
    """
    
    def __init__(self, procedures_store):
        self._store = procedures_store
    
    def match_procedure(self, query: str):
        """Find a procedure matching the query."""
        return self._store.find_procedure(query)
    
    def get_procedure_guidance(self, procedure) -> str:
        """Get formatted guidance for a procedure."""
        if not procedure:
            return ""
        
        lines = [
            f"## Procedure: {procedure.name}",
            f"Confidence: {procedure.confidence:.0%}",
            "",
            "Steps:"
        ]
        
        for i, step in enumerate(procedure.steps, 1):
            action = step.get('action', 'unknown')
            desc = step.get('description', '')
            lines.append(f"  {i}. {action}: {desc}")
        
        return "\n".join(lines)
    
    def learn_procedure(
        self,
        name: str,
        trigger_patterns: list,
        steps: list,
        description: str = "",
        source: str = "learned",
    ) -> str:
        """Learn a new procedure."""
        return self._store.store_procedure(
            name=name,
            trigger_patterns=trigger_patterns,
            steps=steps,
            description=description,
            source=source,
        )
    
    def record_outcome(self, procedure_id: str, success: bool):
        """Record procedure execution outcome."""
        if success:
            self._store.update_success(procedure_id)
        else:
            self._store.update_failure(procedure_id)
    
    def get_all(self) -> list:
        """Get all procedures."""
        return self._store.get_all()


# =============================================================================
# HYBRID STORES (Read from PostgreSQL + Mem0, Write to Mem0)
# =============================================================================

class HybridEpisodicStore:
    """
    Hybrid episodic store for migration period.
    
    - Reads from BOTH PostgreSQL and Mem0 (combines results)
    - Writes ONLY to Mem0 (gradual migration)
    """
    
    def __init__(self, pg_store, mem0_store):
        self._pg = pg_store
        self._mem0 = mem0_store
    
    def retrieve_for_prompt(
        self,
        identity_id: str,
        query: str,
        limit: int = 5,
    ) -> str:
        """Get episodes from both sources."""
        results = []
        
        # Get from PostgreSQL
        if self._pg:
            try:
                pg_result = self._pg.retrieve_for_prompt(identity_id, query, limit)
                if pg_result:
                    results.append(pg_result)
            except Exception as e:
                print(f"[hybrid] PostgreSQL episodic failed: {e}")
        
        # Get from Mem0
        try:
            mem0_result = self._mem0.retrieve_for_prompt(identity_id, query, limit)
            if mem0_result:
                results.append(mem0_result)
        except Exception as e:
            print(f"[hybrid] Mem0 episodic failed: {e}")
        
        if not results:
            return ""
        
        # Combine (dedupe would be nice but simple concat for now)
        return "\n\n".join(results)
    
    def record_episode(
        self,
        identity_id: str,
        summary: str,
        topics: list = None,
        outcome: str = "",
        channel: str = "unknown",
        **kwargs
    ) -> str:
        """Record to Mem0 only (migration path)."""
        return self._mem0.record_episode(
            identity_id=identity_id,
            summary=summary,
            topics=topics,
            outcome=outcome,
            channel=channel,
            **kwargs
        )
    
    def get_recent(self, identity_id: str, limit: int = 10) -> list:
        """Get recent from both sources."""
        results = []
        
        if self._pg:
            try:
                results.extend(self._pg.get_recent(identity_id, limit))
            except Exception:
                pass
        
        try:
            results.extend(self._mem0.get_recent(identity_id, limit))
        except Exception:
            pass
        
        # Sort by timestamp and return top N
        results.sort(key=lambda x: getattr(x, 'timestamp', ''), reverse=True)
        return results[:limit]


class HybridProceduralStore:
    """
    Hybrid procedural store for migration period.
    
    - Reads from BOTH PostgreSQL and Mem0
    - Writes ONLY to Mem0
    """
    
    def __init__(self, pg_store, mem0_store):
        self._pg = pg_store
        self._mem0 = mem0_store
    
    def match_procedure(self, query: str):
        """Find procedure from either source."""
        # Try PostgreSQL first (existing data)
        if self._pg:
            try:
                result = self._pg.match_procedure(query)
                if result:
                    return result
            except Exception:
                pass
        
        # Fall back to Mem0
        try:
            return self._mem0.match_procedure(query)
        except Exception:
            return None
    
    def get_procedure_guidance(self, procedure) -> str:
        """Get guidance - works with either source."""
        if not procedure:
            return ""
        
        # Try Mem0 wrapper format first
        if hasattr(self._mem0, 'get_procedure_guidance'):
            try:
                return self._mem0.get_procedure_guidance(procedure)
            except Exception:
                pass
        
        # Fall back to PostgreSQL format
        if self._pg and hasattr(self._pg, 'get_procedure_guidance'):
            try:
                return self._pg.get_procedure_guidance(procedure)
            except Exception:
                pass
        
        return ""
    
    def learn_procedure(
        self,
        name: str,
        trigger_patterns: list,
        steps: list,
        description: str = "",
        source: str = "learned",
    ) -> str:
        """Learn to Mem0 only."""
        return self._mem0.learn_procedure(
            name=name,
            trigger_patterns=trigger_patterns,
            steps=steps,
            description=description,
            source=source,
        )
    
    def record_outcome(self, procedure_id: str, success: bool):
        """Record to both if possible."""
        # Try Mem0
        try:
            self._mem0.record_outcome(procedure_id, success)
        except Exception:
            pass
        
        # Try PostgreSQL (for existing procedures)
        if self._pg:
            try:
                self._pg.record_outcome(procedure_id, success)
            except Exception:
                pass
    
    def get_all(self) -> list:
        """Get from both sources."""
        results = []
        
        if self._pg:
            try:
                results.extend(self._pg.get_all())
            except Exception:
                pass
        
        try:
            results.extend(self._mem0.get_all())
        except Exception:
            pass
        
        return results


# Convenience functions matching the original API
def get_episodic_memory():
    """Backward-compatible function."""
    return get_episodic_store()


def get_procedural_memory():
    """Backward-compatible function."""
    return get_procedural_store()


if __name__ == "__main__":
    print(f"Storage backend: {STORAGE_BACKEND}")
    print(f"PostgreSQL enabled: {FEATURES.get('use_postgres', False)}")
    
    episodes = get_episodic_store()
    procedures = get_procedural_store()
    
    print(f"Episodic store: {type(episodes).__name__}")
    print(f"Procedural store: {type(procedures).__name__}")
