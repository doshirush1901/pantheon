#!/usr/bin/env python3
"""
MEMORY INTELLIGENCE - Advanced Memory Management

╔════════════════════════════════════════════════════════════════════╗
║  Makes Ira's memory more human-like:                               ║
║  • Consolidation: Merge similar memories                           ║
║  • Decay: Fade unused memories over time                           ║
║  • Importance: Score memories by usefulness                        ║
║  • Themes: Group memories into high-level categories               ║
║  • Relationships: Connect related memories                         ║
╚════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import from centralized config via brain_orchestrator
try:
    from config import DATABASE_URL, OPENAI_API_KEY
except ImportError:
    import os
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


# =============================================================================
# MEMORY THEMES
# =============================================================================

MEMORY_THEMES = {
    "personal": {
        "keywords": ["childhood", "family", "father", "mother", "grew up", "personal", "dream", "feel", "emotion"],
        "label": "Personal & Background",
        "emoji": "👤"
    },
    "business": {
        "keywords": ["company", "business", "revenue", "turnover", "profit", "sales", "customer", "market"],
        "label": "Business & Strategy",
        "emoji": "💼"
    },
    "goals": {
        "keywords": ["goal", "vision", "want", "plan", "by 2024", "by 2025", "by 2026", "by 2027", "by 2028", "by 2030", "launch", "achieve"],
        "label": "Goals & Aspirations",
        "emoji": "🎯"
    },
    "preferences": {
        "keywords": ["prefer", "like", "don't like", "hate", "love", "style", "approach"],
        "label": "Preferences",
        "emoji": "⭐"
    },
    "relationships": {
        "keywords": ["works with", "reports to", "manages", "partner", "colleague", "team", "palak", "father"],
        "label": "Relationships",
        "emoji": "👥"
    },
    "technical": {
        "keywords": ["machine", "pf1", "thermoform", "technology", "product", "spec", "feature"],
        "label": "Technical Knowledge",
        "emoji": "⚙️"
    },
    "context": {
        "keywords": ["creator", "boss", "internal", "trust", "respect"],
        "label": "Relationship with Ira",
        "emoji": "🤖"
    }
}


@dataclass
class MemoryWithScore:
    """Memory with intelligence scoring."""
    id: int
    memory_text: str
    memory_type: str
    confidence: float
    use_count: int
    created_at: datetime
    last_used_at: Optional[datetime]
    
    # Computed scores
    importance_score: float = 0.0
    decay_factor: float = 1.0
    theme: str = "general"
    theme_confidence: float = 0.0
    related_memory_ids: List[int] = None
    
    def __post_init__(self):
        if self.related_memory_ids is None:
            self.related_memory_ids = []


class MemoryIntelligence:
    """
    Advanced memory management - consolidation, decay, importance scoring.
    """
    
    def __init__(self):
        self._conn = None
        self._openai = None
    
    def _get_db(self):
        if self._conn is None or self._conn.closed:
            import psycopg2
            self._conn = psycopg2.connect(DATABASE_URL)
        return self._conn
    
    def _get_openai(self):
        if self._openai is None:
            from openai import OpenAI
            self._openai = OpenAI(api_key=OPENAI_API_KEY)
        return self._openai
    
    # =========================================================================
    # MEMORY DECAY
    # =========================================================================
    
    def apply_decay(self, identity_id: str = None, decay_rate: float = 0.95) -> int:
        """
        Apply time-based decay to memories.
        
        Memories lose confidence over time if not used.
        Well-used memories resist decay.
        
        Returns: Number of memories affected
        """
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            # Decay formula: confidence *= decay_rate ^ (days_since_use)
            # But cap minimum at 0.3 so old memories don't completely vanish
            
            if identity_id:
                cursor.execute("""
                    UPDATE ira_memory.user_memories
                    SET confidence = GREATEST(0.3, confidence * POWER(%s, 
                        EXTRACT(DAY FROM NOW() - COALESCE(last_used_at, created_at)) / 30.0
                    ))
                    WHERE identity_id = %s AND is_active = TRUE
                    RETURNING id
                """, (decay_rate, identity_id))
            else:
                cursor.execute("""
                    UPDATE ira_memory.user_memories
                    SET confidence = GREATEST(0.3, confidence * POWER(%s, 
                        EXTRACT(DAY FROM NOW() - COALESCE(last_used_at, created_at)) / 30.0
                    ))
                    WHERE is_active = TRUE
                    RETURNING id
                """, (decay_rate,))
            
            affected = len(cursor.fetchall())
            conn.commit()
            
            # Boost frequently-used memories back up
            cursor.execute("""
                UPDATE ira_memory.user_memories
                SET confidence = LEAST(1.0, confidence + (use_count * 0.05))
                WHERE use_count > 3 AND is_active = TRUE
            """)
            conn.commit()
            
            print(f"[memory_intelligence] Applied decay to {affected} memories")
            return affected
            
        except Exception as e:
            print(f"[memory_intelligence] Decay error: {e}")
            return 0
    
    # =========================================================================
    # IMPORTANCE SCORING
    # =========================================================================
    
    def score_importance(self, identity_id: str) -> List[MemoryWithScore]:
        """
        Score memories by importance.
        
        Factors:
        - Use frequency (more used = more important)
        - Recency (recently created/used = more relevant)
        - Type (facts > context > preferences)
        - Confidence level
        - Theme relevance
        """
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, memory_text, memory_type, confidence, use_count,
                       created_at, last_used_at
                FROM ira_memory.user_memories
                WHERE identity_id = %s AND is_active = TRUE
                ORDER BY created_at DESC
            """, (identity_id,))
            
            memories = []
            for row in cursor.fetchall():
                mem = MemoryWithScore(
                    id=row[0],
                    memory_text=row[1],
                    memory_type=row[2],
                    confidence=row[3] or 1.0,
                    use_count=row[4] or 0,
                    created_at=row[5],
                    last_used_at=row[6]
                )
                
                # Calculate importance score
                mem.importance_score = self._calculate_importance(mem)
                
                # Assign theme
                mem.theme, mem.theme_confidence = self._assign_theme(mem.memory_text)
                
                memories.append(mem)
            
            # Sort by importance
            memories.sort(key=lambda m: m.importance_score, reverse=True)
            
            return memories
            
        except Exception as e:
            print(f"[memory_intelligence] Scoring error: {e}")
            return []
    
    def _calculate_importance(self, mem: MemoryWithScore) -> float:
        """Calculate importance score (0-1)."""
        score = 0.0
        
        # Base confidence (0-0.3)
        score += mem.confidence * 0.3
        
        # Usage frequency (0-0.25)
        usage_score = min(mem.use_count / 10, 1.0) * 0.25
        score += usage_score
        
        # Recency (0-0.2)
        days_old = (datetime.now() - mem.created_at).days if mem.created_at else 30
        recency_score = max(0, 1 - (days_old / 90)) * 0.2  # Decay over 90 days
        score += recency_score
        
        # Type bonus (0-0.15)
        type_weights = {
            "fact": 0.15,
            "correction": 0.15,  # Corrections are high value
            "preference": 0.12,
            "context": 0.10,
            "relationship": 0.08
        }
        score += type_weights.get(mem.memory_type, 0.05)
        
        # Content quality (0-0.1) - longer, more specific memories are better
        if len(mem.memory_text) > 50:
            score += 0.05
        if any(c.isdigit() for c in mem.memory_text):  # Contains numbers (specific)
            score += 0.05
        
        return min(score, 1.0)
    
    def _assign_theme(self, memory_text: str) -> Tuple[str, float]:
        """Assign a theme to a memory based on keywords."""
        text_lower = memory_text.lower()
        
        best_theme = "general"
        best_score = 0.0
        
        for theme_id, theme_data in MEMORY_THEMES.items():
            matches = sum(1 for kw in theme_data["keywords"] if kw in text_lower)
            score = matches / len(theme_data["keywords"])
            
            if score > best_score:
                best_score = score
                best_theme = theme_id
        
        return best_theme, best_score
    
    # =========================================================================
    # MEMORY CONSOLIDATION
    # =========================================================================
    
    def consolidate_memories(self, identity_id: str, similarity_threshold: float = 0.75) -> int:
        """
        Merge similar memories into consolidated versions.
        
        Uses LLM to identify and merge semantically similar memories.
        Returns number of memories consolidated.
        """
        try:
            conn = self._get_db()
            cursor = conn.cursor()
            
            # Get all active memories
            cursor.execute("""
                SELECT id, memory_text, memory_type, confidence, use_count
                FROM ira_memory.user_memories
                WHERE identity_id = %s AND is_active = TRUE
                ORDER BY created_at
            """, (identity_id,))
            
            memories = cursor.fetchall()
            if len(memories) < 2:
                return 0
            
            # Find similar memory clusters using simple text similarity
            clusters = self._find_similar_clusters(memories)
            
            consolidated = 0
            for cluster in clusters:
                if len(cluster) < 2:
                    continue
                
                # Use LLM to merge the cluster
                merged_text = self._merge_memories_llm(cluster)
                if not merged_text:
                    continue
                
                # Keep the first memory, update its text, deactivate others
                primary_id = cluster[0][0]
                other_ids = [m[0] for m in cluster[1:]]
                
                # Sum up use counts
                total_use_count = sum(m[4] for m in cluster)
                max_confidence = max(m[3] for m in cluster)
                
                # Update primary
                cursor.execute("""
                    UPDATE ira_memory.user_memories
                    SET memory_text = %s, 
                        confidence = %s,
                        use_count = %s,
                        memory_type = 'fact'
                    WHERE id = %s
                """, (merged_text, max_confidence, total_use_count, primary_id))
                
                # Deactivate others
                for oid in other_ids:
                    cursor.execute("""
                        UPDATE ira_memory.user_memories
                        SET is_active = FALSE
                        WHERE id = %s
                    """, (oid,))
                
                consolidated += len(cluster) - 1
                print(f"[memory_intelligence] Consolidated {len(cluster)} memories → '{merged_text[:50]}...'")
            
            conn.commit()
            return consolidated
            
        except Exception as e:
            print(f"[memory_intelligence] Consolidation error: {e}")
            if self._conn:
                self._conn.rollback()
            return 0
    
    def _find_similar_clusters(self, memories: List[tuple]) -> List[List[tuple]]:
        """Find clusters of similar memories using word overlap."""
        clusters = []
        used = set()
        
        for i, mem1 in enumerate(memories):
            if i in used:
                continue
            
            cluster = [mem1]
            words1 = set(mem1[1].lower().split())
            
            for j, mem2 in enumerate(memories[i+1:], i+1):
                if j in used:
                    continue
                
                words2 = set(mem2[1].lower().split())
                
                # Calculate Jaccard similarity
                intersection = len(words1 & words2)
                union = len(words1 | words2)
                similarity = intersection / union if union > 0 else 0
                
                if similarity > 0.4:  # 40% word overlap
                    cluster.append(mem2)
                    used.add(j)
            
            if len(cluster) > 1:
                clusters.append(cluster)
                used.add(i)
        
        return clusters
    
    def _merge_memories_llm(self, cluster: List[tuple]) -> Optional[str]:
        """Use LLM to merge similar memories into one."""
        memory_texts = [m[1] for m in cluster]
        
        prompt = f"""Merge these related memories into ONE clear, comprehensive statement.
Keep all important details. Be concise but complete.

Memories to merge:
{chr(10).join(f'- {t}' for t in memory_texts)}

Merged memory (one sentence):"""

        try:
            client = self._get_openai()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150
            )
            
            merged = response.choices[0].message.content.strip()
            # Remove quotes if present
            merged = merged.strip('"').strip("'")
            
            return merged if len(merged) > 20 else None
            
        except Exception as e:
            print(f"[memory_intelligence] LLM merge error: {e}")
            return None
    
    # =========================================================================
    # MEMORY THEMES SUMMARY
    # =========================================================================
    
    def get_themed_summary(self, identity_id: str) -> Dict:
        """
        Get memories organized by theme with a summary for each.
        
        Returns structured data for rich display.
        """
        scored = self.score_importance(identity_id)
        
        # Group by theme
        by_theme = {}
        for mem in scored:
            theme = mem.theme
            if theme not in by_theme:
                by_theme[theme] = []
            by_theme[theme].append(mem)
        
        # Build summary
        summary = {
            "total_memories": len(scored),
            "themes": {},
            "top_memories": [
                {"text": m.memory_text, "importance": m.importance_score}
                for m in scored[:5]
            ]
        }
        
        for theme_id, memories in by_theme.items():
            theme_info = MEMORY_THEMES.get(theme_id, {"label": theme_id.title(), "emoji": "📝"})
            
            # Sort by importance within theme
            memories.sort(key=lambda m: m.importance_score, reverse=True)
            
            summary["themes"][theme_id] = {
                "label": theme_info["label"],
                "emoji": theme_info["emoji"],
                "count": len(memories),
                "avg_importance": sum(m.importance_score for m in memories) / len(memories),
                "top_memories": [m.memory_text for m in memories[:3]]
            }
        
        return summary
    
    def format_themed_display(self, identity_id: str) -> str:
        """Format memories with themes for Telegram display."""
        summary = self.get_themed_summary(identity_id)
        
        lines = [f"**What I Know About You** ({summary['total_memories']} memories)\n"]
        
        # Sort themes by count
        sorted_themes = sorted(
            summary["themes"].items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        for theme_id, theme_data in sorted_themes:
            emoji = theme_data["emoji"]
            label = theme_data["label"]
            count = theme_data["count"]
            
            lines.append(f"\n{emoji} **{label}** ({count})")
            
            for mem in theme_data["top_memories"]:
                # Truncate long memories
                display = mem[:80] + "..." if len(mem) > 80 else mem
                lines.append(f"  • {display}")
        
        lines.append("\n_Use `/memories full` for complete list_")
        
        return "\n".join(lines)
    
    # =========================================================================
    # MAINTENANCE
    # =========================================================================
    
    def decay_old_memories(self, days: int = 30) -> int:
        """
        Decay memories that haven't been used in N days.
        
        This is a convenience wrapper for the nightly dream script.
        
        Args:
            days: Memories unused for this many days get decayed
            
        Returns:
            Number of memories decayed
        """
        try:
            conn = self._get_db()
            if not conn:
                print("[memory_intelligence] No DB connection for decay")
                return 0
            
            cursor = conn.cursor()
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Decay memories not used since cutoff
            # Reduce confidence by 10% for each decay cycle
            cursor.execute("""
                UPDATE persistent_memory
                SET confidence = GREATEST(0.1, confidence * 0.9),
                    updated_at = NOW()
                WHERE (last_used_at IS NULL OR last_used_at < %s)
                AND confidence > 0.1
                RETURNING id
            """, (cutoff_date,))
            
            decayed = cursor.fetchall()
            conn.commit()
            
            count = len(decayed)
            if count > 0:
                print(f"[memory_intelligence] Decayed {count} old memories")
            return count
            
        except Exception as e:
            print(f"[memory_intelligence] Decay error: {e}")
            return 0
    
    def archive_memories(self, days: int = 180) -> int:
        """
        Archive very old, low-confidence memories.
        
        Moves memories older than N days with low confidence to an archive table
        (or marks them as archived if no archive table exists).
        
        Args:
            days: Memories older than this get archived
            
        Returns:
            Number of memories archived
        """
        try:
            conn = self._get_db()
            if not conn:
                print("[memory_intelligence] No DB connection for archive")
                return 0
            
            cursor = conn.cursor()
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Mark very old, low-confidence memories as archived
            # (We use a soft delete approach - set is_active = false)
            cursor.execute("""
                UPDATE persistent_memory
                SET is_active = FALSE,
                    updated_at = NOW()
                WHERE created_at < %s
                AND confidence < 0.3
                AND is_active = TRUE
                RETURNING id
            """, (cutoff_date,))
            
            archived = cursor.fetchall()
            conn.commit()
            
            count = len(archived)
            if count > 0:
                print(f"[memory_intelligence] Archived {count} old memories")
            return count
            
        except Exception as e:
            print(f"[memory_intelligence] Archive error: {e}")
            return 0
    
    def run_maintenance(self, identity_id: str = None) -> Dict:
        """
        Run full memory maintenance:
        - Apply decay
        - Consolidate similar memories
        - Re-score importance
        """
        results = {
            "decayed": 0,
            "consolidated": 0,
            "rescored": 0
        }
        
        print("[memory_intelligence] Running maintenance...")
        
        # Apply decay
        results["decayed"] = self.apply_decay(identity_id)
        
        # Consolidate if we have an identity
        if identity_id:
            results["consolidated"] = self.consolidate_memories(identity_id)
            
            # Re-score
            scored = self.score_importance(identity_id)
            results["rescored"] = len(scored)
        
        print(f"[memory_intelligence] Maintenance complete: {results}")
        return results


# Singleton
_intelligence: Optional[MemoryIntelligence] = None


def get_memory_intelligence() -> MemoryIntelligence:
    global _intelligence
    if _intelligence is None:
        _intelligence = MemoryIntelligence()
    return _intelligence


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Memory Intelligence CLI")
    parser.add_argument("--identity", type=str, help="Identity ID to operate on")
    parser.add_argument("--decay", action="store_true", help="Apply memory decay")
    parser.add_argument("--consolidate", action="store_true", help="Consolidate similar memories")
    parser.add_argument("--score", action="store_true", help="Score and display memories")
    parser.add_argument("--themes", action="store_true", help="Show themed summary")
    parser.add_argument("--maintenance", action="store_true", help="Run full maintenance")
    
    args = parser.parse_args()
    
    mi = MemoryIntelligence()
    
    if args.decay:
        mi.apply_decay(args.identity)
    
    elif args.consolidate and args.identity:
        mi.consolidate_memories(args.identity)
    
    elif args.score and args.identity:
        scored = mi.score_importance(args.identity)
        print(f"\n{'='*60}")
        print(f"MEMORY IMPORTANCE SCORES ({len(scored)} memories)")
        print('='*60)
        for mem in scored[:15]:
            print(f"\n[{mem.importance_score:.2f}] [{mem.theme}] {mem.memory_text[:70]}...")
    
    elif args.themes and args.identity:
        print(mi.format_themed_display(args.identity))
    
    elif args.maintenance:
        mi.run_maintenance(args.identity)
    
    else:
        parser.print_help()
