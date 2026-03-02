#!/usr/bin/env python3
"""
MEMORY CONSOLIDATION JOB - Background Memory Maintenance

╔════════════════════════════════════════════════════════════════════╗
║  Run periodically (daily/weekly) to keep memory healthy:           ║
║  1. Apply decay to unused memories                                 ║
║  2. Merge duplicate/similar memories                               ║
║  3. Prune very low confidence memories                             ║
║  4. Promote high-confidence facts to semantic memory               ║
║  5. Generate memory statistics                                     ║
╚════════════════════════════════════════════════════════════════════╝

Usage:
    # Run full consolidation
    python consolidation_job.py
    
    # Run specific phase
    python consolidation_job.py --phase decay
    python consolidation_job.py --phase merge
    python consolidation_job.py --phase prune
    
    # Dry run (no changes)
    python consolidation_job.py --dry-run
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import from centralized config via brain_orchestrator
try:
    from config import DATABASE_URL, OPENAI_API_KEY
except ImportError:
    import os
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


@dataclass
class ConsolidationResult:
    """Results from a consolidation run."""
    phase: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    memories_processed: int = 0
    memories_decayed: int = 0
    memories_merged: int = 0
    memories_pruned: int = 0
    memories_promoted: int = 0
    errors: List[str] = None
    dry_run: bool = False
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    def to_dict(self) -> Dict:
        return {
            "phase": self.phase,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "memories_processed": self.memories_processed,
            "memories_decayed": self.memories_decayed,
            "memories_merged": self.memories_merged,
            "memories_pruned": self.memories_pruned,
            "memories_promoted": self.memories_promoted,
            "errors": self.errors,
            "dry_run": self.dry_run,
        }


class MemoryConsolidator:
    """
    Runs memory consolidation phases.
    
    Phases:
    1. DECAY - Reduce confidence of unused memories
    2. MERGE - Combine semantically similar memories
    3. PRUNE - Remove very low confidence memories
    4. PROMOTE - Elevate frequently-used facts
    5. STATS - Generate statistics report
    """
    
    # Configuration
    DECAY_RATE = 0.02  # 2% decay per run for unused memories
    DECAY_THRESHOLD_DAYS = 14  # Memories unused for 14+ days get decayed
    MERGE_SIMILARITY_THRESHOLD = 0.85  # Min similarity for auto-merge
    PRUNE_CONFIDENCE_THRESHOLD = 0.1  # Prune memories below this confidence
    PRUNE_MIN_AGE_DAYS = 30  # Only prune memories older than this
    PROMOTE_CONFIDENCE_THRESHOLD = 0.9  # Promote memories above this
    PROMOTE_MIN_USES = 5  # Promote memories used at least this many times
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._conn = None
    
    def _get_db_connection(self):
        """Get PostgreSQL connection."""
        if self._conn:
            return self._conn
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL not configured")
        try:
            import psycopg2
            import psycopg2.extras
            self._conn = psycopg2.connect(DATABASE_URL)
            psycopg2.extras.register_uuid()
            return self._conn
        except Exception as e:
            raise RuntimeError(f"Database connection failed: {e}")
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    # =========================================================================
    # PHASE 1: DECAY
    # =========================================================================
    
    def run_decay(self) -> ConsolidationResult:
        """
        Apply time-based decay to unused memories.
        
        Memories that haven't been used recently lose confidence.
        Frequently used memories gain confidence.
        """
        result = ConsolidationResult(phase="decay", started_at=datetime.now(), dry_run=self.dry_run)
        
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=self.DECAY_THRESHOLD_DAYS)
            
            # Get memories that need decay
            cur.execute("""
                SELECT id, memory_text, confidence, use_count, last_used_at
                FROM ira_memory.user_memories
                WHERE is_active = TRUE
                  AND (last_used_at IS NULL OR last_used_at < %s)
                  AND confidence > %s
            """, (cutoff_date, self.PRUNE_CONFIDENCE_THRESHOLD))
            
            memories_to_decay = cur.fetchall()
            result.memories_processed = len(memories_to_decay)
            
            for mem_id, text, confidence, use_count, last_used in memories_to_decay:
                # Calculate decay amount
                decay_amount = self.DECAY_RATE
                
                # Less decay for frequently used memories
                if use_count and use_count > 3:
                    decay_amount *= 0.5
                
                new_confidence = max(0.0, confidence - decay_amount)
                
                if not self.dry_run:
                    cur.execute("""
                        UPDATE ira_memory.user_memories
                        SET confidence = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (new_confidence, mem_id))
                
                result.memories_decayed += 1
                print(f"  [decay] '{text[:30]}...' {confidence:.2f} → {new_confidence:.2f}")
            
            # Also boost frequently used memories
            cur.execute("""
                SELECT id, memory_text, confidence, use_count
                FROM ira_memory.user_memories
                WHERE is_active = TRUE
                  AND use_count >= 3
                  AND confidence < 0.95
            """)
            
            for mem_id, text, confidence, use_count in cur.fetchall():
                boost = min(0.05, use_count * 0.01)
                new_confidence = min(0.95, confidence + boost)
                
                if not self.dry_run:
                    cur.execute("""
                        UPDATE ira_memory.user_memories
                        SET confidence = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (new_confidence, mem_id))
                
                print(f"  [boost] '{text[:30]}...' {confidence:.2f} → {new_confidence:.2f}")
            
            if not self.dry_run:
                conn.commit()
            
        except Exception as e:
            result.errors.append(str(e))
            print(f"  [error] Decay phase error: {e}")
        
        result.completed_at = datetime.now()
        return result
    
    # =========================================================================
    # PHASE 2: MERGE
    # =========================================================================
    
    def run_merge(self) -> ConsolidationResult:
        """
        Merge semantically similar memories.
        
        Groups similar memories and combines them using LLM.
        """
        result = ConsolidationResult(phase="merge", started_at=datetime.now(), dry_run=self.dry_run)
        
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            # Get all active memories grouped by identity
            cur.execute("""
                SELECT id, identity_id, memory_text, memory_type, confidence
                FROM ira_memory.user_memories
                WHERE is_active = TRUE
                ORDER BY identity_id, memory_type
            """)
            
            memories = cur.fetchall()
            result.memories_processed = len(memories)
            
            # Group by identity
            by_identity: Dict[str, List[Tuple]] = {}
            for row in memories:
                identity_id = row[1]
                if identity_id not in by_identity:
                    by_identity[identity_id] = []
                by_identity[identity_id].append(row)
            
            # Find similar pairs within each identity
            for identity_id, mems in by_identity.items():
                clusters = self._find_similar_clusters(mems)
                
                for cluster in clusters:
                    if len(cluster) < 2:
                        continue
                    
                    print(f"  [merge] Found cluster of {len(cluster)} similar memories")
                    
                    # Merge the cluster
                    merged_text = self._merge_memories_llm([m[2] for m in cluster])
                    if not merged_text:
                        continue
                    
                    # Keep the highest confidence one, update its text
                    cluster.sort(key=lambda x: x[4], reverse=True)
                    keeper = cluster[0]
                    to_deactivate = cluster[1:]
                    
                    if not self.dry_run:
                        # Update keeper with merged text
                        cur.execute("""
                            UPDATE ira_memory.user_memories
                            SET memory_text = %s, updated_at = NOW()
                            WHERE id = %s
                        """, (merged_text, keeper[0]))
                        
                        # Deactivate others
                        for mem in to_deactivate:
                            cur.execute("""
                                UPDATE ira_memory.user_memories
                                SET is_active = FALSE, updated_at = NOW()
                                WHERE id = %s
                            """, (mem[0],))
                    
                    result.memories_merged += len(to_deactivate)
                    print(f"    Merged into: '{merged_text[:50]}...'")
            
            if not self.dry_run:
                conn.commit()
            
        except Exception as e:
            result.errors.append(str(e))
            print(f"  [error] Merge phase error: {e}")
        
        result.completed_at = datetime.now()
        return result
    
    def _find_similar_clusters(self, memories: List[Tuple]) -> List[List[Tuple]]:
        """Find clusters of similar memories using word overlap."""
        def similarity(text1: str, text2: str) -> float:
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            if not words1 or not words2:
                return 0.0
            intersection = words1 & words2
            union = words1 | words2
            return len(intersection) / len(union)
        
        clusters = []
        used = set()
        
        for i, mem1 in enumerate(memories):
            if i in used:
                continue
            
            cluster = [mem1]
            used.add(i)
            
            for j, mem2 in enumerate(memories):
                if j in used or j <= i:
                    continue
                
                # Same type and high similarity
                if mem1[3] == mem2[3] and similarity(mem1[2], mem2[2]) > self.MERGE_SIMILARITY_THRESHOLD:
                    cluster.append(mem2)
                    used.add(j)
            
            if len(cluster) > 1:
                clusters.append(cluster)
        
        return clusters
    
    def _merge_memories_llm(self, texts: List[str]) -> Optional[str]:
        """Use LLM to merge similar memories into one."""
        if not OPENAI_API_KEY:
            # Fallback: just keep the longest one
            return max(texts, key=len)
        
        try:
            import httpx
            prompt = f"""Merge these similar facts about a user into a single, comprehensive statement:

{chr(10).join(f'- {t}' for t in texts)}

Output ONLY the merged statement, nothing else. Keep it concise."""
            
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 150,
                },
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"    [llm error] {e}")
            return max(texts, key=len)
    
    # =========================================================================
    # PHASE 3: PRUNE
    # =========================================================================
    
    def run_prune(self) -> ConsolidationResult:
        """
        Remove very low confidence memories.
        
        Only prunes memories that are old enough and have very low confidence.
        """
        result = ConsolidationResult(phase="prune", started_at=datetime.now(), dry_run=self.dry_run)
        
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            min_age = datetime.now() - timedelta(days=self.PRUNE_MIN_AGE_DAYS)
            
            # Find memories to prune
            cur.execute("""
                SELECT id, memory_text, confidence, created_at
                FROM ira_memory.user_memories
                WHERE is_active = TRUE
                  AND confidence < %s
                  AND created_at < %s
            """, (self.PRUNE_CONFIDENCE_THRESHOLD, min_age))
            
            memories_to_prune = cur.fetchall()
            result.memories_processed = len(memories_to_prune)
            
            for mem_id, text, confidence, created_at in memories_to_prune:
                if not self.dry_run:
                    cur.execute("""
                        UPDATE ira_memory.user_memories
                        SET is_active = FALSE, updated_at = NOW()
                        WHERE id = %s
                    """, (mem_id,))
                
                result.memories_pruned += 1
                print(f"  [prune] '{text[:40]}...' (confidence: {confidence:.2f})")
            
            if not self.dry_run:
                conn.commit()
            
        except Exception as e:
            result.errors.append(str(e))
            print(f"  [error] Prune phase error: {e}")
        
        result.completed_at = datetime.now()
        return result
    
    # =========================================================================
    # PHASE 4: PROMOTE
    # =========================================================================
    
    def run_promote(self) -> ConsolidationResult:
        """
        Promote high-confidence, frequently-used facts.
        
        These become "core memories" that are always considered.
        """
        result = ConsolidationResult(phase="promote", started_at=datetime.now(), dry_run=self.dry_run)
        
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            # Find high-confidence, frequently-used memories
            cur.execute("""
                SELECT id, identity_id, memory_text, memory_type, confidence, use_count
                FROM ira_memory.user_memories
                WHERE is_active = TRUE
                  AND confidence >= %s
                  AND use_count >= %s
                  AND memory_type != 'core'
            """, (self.PROMOTE_CONFIDENCE_THRESHOLD, self.PROMOTE_MIN_USES))
            
            memories_to_promote = cur.fetchall()
            result.memories_processed = len(memories_to_promote)
            
            for mem_id, identity_id, text, mem_type, confidence, use_count in memories_to_promote:
                if not self.dry_run:
                    # Mark as core memory type
                    cur.execute("""
                        UPDATE ira_memory.user_memories
                        SET memory_type = 'core', updated_at = NOW()
                        WHERE id = %s
                    """, (mem_id,))
                
                result.memories_promoted += 1
                print(f"  [promote] '{text[:40]}...' → CORE (uses: {use_count})")
            
            if not self.dry_run:
                conn.commit()
            
        except Exception as e:
            result.errors.append(str(e))
            print(f"  [error] Promote phase error: {e}")
        
        result.completed_at = datetime.now()
        return result
    
    # =========================================================================
    # PHASE 5: STATS
    # =========================================================================
    
    def generate_stats(self) -> Dict:
        """Generate memory statistics report."""
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            stats = {
                "generated_at": datetime.now().isoformat(),
                "user_memories": {},
                "entity_memories": {},
                "procedures": {},
            }
            
            # User memories stats
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE is_active) as active,
                    AVG(confidence) as avg_confidence,
                    SUM(use_count) as total_uses,
                    COUNT(DISTINCT identity_id) as unique_users
                FROM ira_memory.user_memories
            """)
            row = cur.fetchone()
            if row:
                stats["user_memories"] = {
                    "total": row[0],
                    "active": row[1],
                    "avg_confidence": float(row[2]) if row[2] else 0,
                    "total_uses": row[3] or 0,
                    "unique_users": row[4],
                }
            
            # By type breakdown
            cur.execute("""
                SELECT memory_type, COUNT(*)
                FROM ira_memory.user_memories
                WHERE is_active = TRUE
                GROUP BY memory_type
            """)
            stats["user_memories"]["by_type"] = {row[0]: row[1] for row in cur.fetchall()}
            
            # Entity memories stats
            try:
                cur.execute("""
                    SELECT COUNT(*), COUNT(DISTINCT entity_name)
                    FROM ira_memory.entity_memories
                    WHERE is_active = TRUE
                """)
                row = cur.fetchone()
                if row:
                    stats["entity_memories"] = {
                        "total": row[0],
                        "unique_entities": row[1],
                    }
            except Exception:
                stats["entity_memories"] = {"total": 0, "unique_entities": 0}
            
            # Procedures stats
            try:
                cur.execute("""
                    SELECT COUNT(*), SUM(success_count), SUM(failure_count)
                    FROM ira_memory.procedures
                    WHERE is_active = TRUE
                """)
                row = cur.fetchone()
                if row:
                    stats["procedures"] = {
                        "total": row[0],
                        "total_successes": row[1] or 0,
                        "total_failures": row[2] or 0,
                    }
            except Exception:
                stats["procedures"] = {"total": 0}
            
            return stats
            
        except Exception as e:
            return {"error": str(e)}
    
    # =========================================================================
    # FULL RUN
    # =========================================================================
    
    def run_all(self) -> Dict[str, ConsolidationResult]:
        """Run all consolidation phases."""
        print(f"\n{'='*60}")
        print(f"MEMORY CONSOLIDATION {'(DRY RUN)' if self.dry_run else ''}")
        print(f"Started: {datetime.now().isoformat()}")
        print(f"{'='*60}")
        
        results = {}
        
        print("\n📉 PHASE 1: DECAY")
        results["decay"] = self.run_decay()
        
        print("\n🔗 PHASE 2: MERGE")
        results["merge"] = self.run_merge()
        
        print("\n✂️ PHASE 3: PRUNE")
        results["prune"] = self.run_prune()
        
        print("\n⭐ PHASE 4: PROMOTE")
        results["promote"] = self.run_promote()
        
        print("\n📊 PHASE 5: STATS")
        stats = self.generate_stats()
        print(json.dumps(stats, indent=2))
        
        # Summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"  Decayed:  {results['decay'].memories_decayed}")
        print(f"  Merged:   {results['merge'].memories_merged}")
        print(f"  Pruned:   {results['prune'].memories_pruned}")
        print(f"  Promoted: {results['promote'].memories_promoted}")
        
        total_errors = sum(len(r.errors) for r in results.values())
        if total_errors > 0:
            print(f"  Errors:   {total_errors}")
        
        print(f"\nCompleted: {datetime.now().isoformat()}")
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Memory Consolidation Job")
    parser.add_argument("--phase", choices=["decay", "merge", "prune", "promote", "stats", "all"],
                        default="all", help="Which phase to run")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes, just report")
    
    args = parser.parse_args()
    
    consolidator = MemoryConsolidator(dry_run=args.dry_run)
    
    try:
        if args.phase == "all":
            consolidator.run_all()
        elif args.phase == "decay":
            result = consolidator.run_decay()
            print(f"Decayed: {result.memories_decayed}")
        elif args.phase == "merge":
            result = consolidator.run_merge()
            print(f"Merged: {result.memories_merged}")
        elif args.phase == "prune":
            result = consolidator.run_prune()
            print(f"Pruned: {result.memories_pruned}")
        elif args.phase == "promote":
            result = consolidator.run_promote()
            print(f"Promoted: {result.memories_promoted}")
        elif args.phase == "stats":
            stats = consolidator.generate_stats()
            print(json.dumps(stats, indent=2))
    finally:
        consolidator.close()


if __name__ == "__main__":
    main()
