#!/usr/bin/env python3
"""
UNIFIED DECAY MANAGER - Single Source of Truth for Memory Decay

╔════════════════════════════════════════════════════════════════════════════╗
║  FLAW 7 FIX: Consolidates duplicate decay logic from:                      ║
║  - memory_intelligence.py → apply_decay()                                  ║
║  - consolidation_job.py → run_decay()                                      ║
║  - memory_analytics.py → apply_memory_decay()                              ║
║                                                                            ║
║  Now there's ONE decay algorithm with configurable parameters.             ║
╚════════════════════════════════════════════════════════════════════════════╝

Usage:
    from unified_decay import UnifiedDecayManager, decay_memories
    
    manager = UnifiedDecayManager()
    result = manager.run_decay()
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Import from centralized config via brain_orchestrator
try:
    from config import DATABASE_URL
except ImportError:
    import os
    DATABASE_URL = os.environ.get("DATABASE_URL", "")


# =============================================================================
# DECAY CONFIGURATION
# =============================================================================

@dataclass
class DecayConfig:
    """Configurable decay parameters."""
    
    # Time thresholds
    inactivity_days_warning: int = 30      # When to start decay
    inactivity_days_archive: int = 90      # When to archive (not delete)
    inactivity_days_prune: int = 180       # When to consider for pruning
    
    # Decay rates (multiplier per period)
    base_decay_rate: float = 0.95          # 5% decay per period
    high_importance_decay: float = 0.98    # Important memories decay slower
    low_importance_decay: float = 0.90     # Unimportant decay faster
    
    # Importance thresholds
    importance_threshold_high: float = 0.8
    importance_threshold_low: float = 0.3
    
    # Recall boost
    recall_boost_factor: float = 1.1       # Boost when recalled
    max_importance: float = 1.0
    min_importance: float = 0.1
    
    # Prune settings
    prune_threshold: float = 0.15          # Below this = candidate for pruning
    max_memories_per_user: int = 1000      # Soft limit
    
    def to_dict(self) -> Dict:
        return {
            "inactivity_days_warning": self.inactivity_days_warning,
            "inactivity_days_archive": self.inactivity_days_archive,
            "inactivity_days_prune": self.inactivity_days_prune,
            "base_decay_rate": self.base_decay_rate,
            "high_importance_decay": self.high_importance_decay,
            "low_importance_decay": self.low_importance_decay,
            "prune_threshold": self.prune_threshold,
        }


@dataclass
class DecayResult:
    """Result of a decay operation."""
    memories_processed: int = 0
    memories_decayed: int = 0
    memories_boosted: int = 0
    memories_archived: int = 0
    memories_pruned: int = 0
    total_importance_reduced: float = 0.0
    duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "memories_processed": self.memories_processed,
            "memories_decayed": self.memories_decayed,
            "memories_boosted": self.memories_boosted,
            "memories_archived": self.memories_archived,
            "memories_pruned": self.memories_pruned,
            "total_importance_reduced": round(self.total_importance_reduced, 4),
            "duration_ms": round(self.duration_ms, 2),
            "errors": self.errors,
        }


# =============================================================================
# UNIFIED DECAY MANAGER
# =============================================================================

class UnifiedDecayManager:
    """
    Single source of truth for memory decay operations.
    
    Implements a biologically-inspired decay model:
    - Memories decay naturally over time
    - Recall strengthens memories (use it or lose it)
    - Important memories resist decay
    - Very old/unused memories can be pruned
    """
    
    def __init__(self, config: DecayConfig = None):
        self.config = config or DecayConfig()
        self._last_run: Optional[datetime] = None
        self._run_history: List[DecayResult] = []
    
    def _get_db_connection(self):
        """Get PostgreSQL connection."""
        if not DATABASE_URL:
            return None
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(DATABASE_URL)
            psycopg2.extras.register_uuid()
            return conn
        except Exception as e:
            print(f"[unified_decay] DB connection error: {e}")
            return None
    
    def run_decay(
        self,
        identity_id: Optional[str] = None,
        include_archive: bool = False,
        include_prune: bool = False,
        dry_run: bool = False
    ) -> DecayResult:
        """
        Run the unified decay algorithm.
        
        Args:
            identity_id: If provided, only decay this user's memories
            include_archive: Archive very old memories
            include_prune: Actually delete prunable memories
            dry_run: Don't commit changes, just report what would happen
        
        Returns:
            DecayResult with statistics
        """
        import time
        start = time.time()
        result = DecayResult()
        
        conn = self._get_db_connection()
        if not conn:
            result.errors.append("No database connection")
            return result
        
        try:
            now = datetime.now()
            warning_cutoff = now - timedelta(days=self.config.inactivity_days_warning)
            archive_cutoff = now - timedelta(days=self.config.inactivity_days_archive)
            prune_cutoff = now - timedelta(days=self.config.inactivity_days_prune)
            
            with conn.cursor() as cur:
                # Build query
                base_query = """
                    SELECT id, identity_id, importance, last_accessed, recalled_count
                    FROM ira_memory.user_memories
                    WHERE is_active = TRUE
                """
                params = []
                
                if identity_id:
                    base_query += " AND identity_id = %s"
                    params.append(identity_id)
                
                cur.execute(base_query, params)
                memories = cur.fetchall()
                result.memories_processed = len(memories)
                
                updates = []
                archives = []
                prunes = []
                
                for mem_id, mem_identity, importance, last_accessed, recalled_count in memories:
                    # Skip recently accessed
                    if last_accessed and last_accessed > warning_cutoff:
                        continue
                    
                    # Calculate decay rate based on importance
                    if importance >= self.config.importance_threshold_high:
                        decay_rate = self.config.high_importance_decay
                    elif importance <= self.config.importance_threshold_low:
                        decay_rate = self.config.low_importance_decay
                    else:
                        decay_rate = self.config.base_decay_rate
                    
                    # Calculate days since last access
                    if last_accessed:
                        days_inactive = (now - last_accessed).days
                    else:
                        days_inactive = self.config.inactivity_days_warning
                    
                    # Apply decay based on inactivity periods
                    periods = days_inactive // 30  # Decay per 30-day period
                    new_importance = importance * (decay_rate ** periods)
                    new_importance = max(self.config.min_importance, new_importance)
                    
                    importance_delta = importance - new_importance
                    
                    if importance_delta > 0.001:  # Only update if meaningful change
                        updates.append((new_importance, mem_id))
                        result.memories_decayed += 1
                        result.total_importance_reduced += importance_delta
                    
                    # Check for archive candidates
                    if include_archive and last_accessed and last_accessed < archive_cutoff:
                        archives.append(mem_id)
                        result.memories_archived += 1
                    
                    # Check for prune candidates
                    if include_prune and new_importance < self.config.prune_threshold:
                        if last_accessed and last_accessed < prune_cutoff:
                            prunes.append(mem_id)
                            result.memories_pruned += 1
                
                # Apply updates
                if not dry_run:
                    # Update importance
                    if updates:
                        cur.executemany("""
                            UPDATE ira_memory.user_memories
                            SET importance = %s, updated_at = NOW()
                            WHERE id = %s
                        """, updates)
                    
                    # Archive (mark as inactive)
                    if archives:
                        cur.execute("""
                            UPDATE ira_memory.user_memories
                            SET is_active = FALSE, metadata = 
                                COALESCE(metadata, '{}'::jsonb) || '{"archived_at": "%s"}'::jsonb
                            WHERE id = ANY(%s)
                        """, (now.isoformat(), archives))
                    
                    # Prune (delete)
                    if prunes:
                        # First backup to prune log
                        for mem_id in prunes:
                            cur.execute("""
                                INSERT INTO ira_memory.pruned_memories_log 
                                (original_id, identity_id, memory_text, pruned_at, reason)
                                SELECT id, identity_id, memory_text, NOW(), 'decay_threshold'
                                FROM ira_memory.user_memories WHERE id = %s
                            """, (mem_id,))
                        # Then delete
                        cur.execute("""
                            DELETE FROM ira_memory.user_memories
                            WHERE id = ANY(%s)
                        """, (prunes,))
                    
                    conn.commit()
                else:
                    conn.rollback()
                    
        except Exception as e:
            result.errors.append(str(e))
            conn.rollback()
        finally:
            conn.close()
        
        result.duration_ms = (time.time() - start) * 1000
        self._last_run = datetime.now()
        self._run_history.append(result)
        
        return result
    
    def boost_recalled(self, memory_id: str) -> bool:
        """
        Boost importance when a memory is recalled.
        
        Called when a memory is retrieved for use.
        """
        conn = self._get_db_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE ira_memory.user_memories
                    SET importance = LEAST(%s, importance * %s),
                        last_accessed = NOW(),
                        recalled_count = recalled_count + 1
                    WHERE id = %s
                """, (self.config.max_importance, self.config.recall_boost_factor, memory_id))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            print(f"[unified_decay] Boost error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def run_episodic_decay(self) -> DecayResult:
        """Apply decay to episodic memories."""
        import time
        start = time.time()
        result = DecayResult()
        
        conn = self._get_db_connection()
        if not conn:
            result.errors.append("No database connection")
            return result
        
        try:
            now = datetime.now()
            decay_cutoff = now - timedelta(days=self.config.inactivity_days_warning)
            
            with conn.cursor() as cur:
                # Decay episodic importance based on age and recall frequency
                cur.execute("""
                    UPDATE ira_memory.episodes
                    SET importance = GREATEST(%s, importance * %s)
                    WHERE timestamp < %s AND importance > %s
                    RETURNING id
                """, (
                    self.config.min_importance,
                    self.config.base_decay_rate,
                    decay_cutoff,
                    self.config.min_importance
                ))
                
                result.memories_decayed = cur.rowcount
                conn.commit()
                
        except Exception as e:
            result.errors.append(str(e))
            conn.rollback()
        finally:
            conn.close()
        
        result.duration_ms = (time.time() - start) * 1000
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get decay statistics."""
        return {
            "config": self.config.to_dict(),
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "recent_runs": [r.to_dict() for r in self._run_history[-5:]],
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_decay_manager: Optional[UnifiedDecayManager] = None


def get_decay_manager() -> UnifiedDecayManager:
    """Get singleton decay manager."""
    global _decay_manager
    if _decay_manager is None:
        _decay_manager = UnifiedDecayManager()
    return _decay_manager


def decay_memories(
    identity_id: Optional[str] = None,
    include_prune: bool = False
) -> DecayResult:
    """Run decay on memories."""
    return get_decay_manager().run_decay(
        identity_id=identity_id,
        include_prune=include_prune
    )


def boost_memory(memory_id: str) -> bool:
    """Boost a memory's importance when recalled."""
    return get_decay_manager().boost_recalled(memory_id)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Testing UnifiedDecayManager...")
    
    manager = UnifiedDecayManager()
    print(f"Config: {manager.config.to_dict()}")
    
    # Dry run
    result = manager.run_decay(dry_run=True)
    print(f"\nDry run result: {result.to_dict()}")
    
    # Get stats
    stats = manager.get_stats()
    print(f"\nStats: {json.dumps(stats, indent=2)}")
