#!/usr/bin/env python3
"""
EPISODIC CONSOLIDATOR - Episode → Semantic Memory Transfer

╔════════════════════════════════════════════════════════════════════════════╗
║  FLAW 9 FIX: Missing Episode-to-Semantic Consolidation                     ║
║                                                                            ║
║  Neuroscience: During sleep, hippocampus (episodic) transfers repeated    ║
║  patterns to cortex (semantic) for long-term storage.                      ║
║                                                                            ║
║  Implementation: Periodically analyze episodes, find patterns, and        ║
║  create/update semantic memories from them.                                ║
║                                                                            ║
║  Examples:                                                                 ║
║  - "John always asks about pricing on Mondays" → semantic fact             ║
║  - "User prefers email over Telegram" → user preference                    ║
║  - "ABC Corp usually orders in Q4" → entity pattern                        ║
╚════════════════════════════════════════════════════════════════════════════╝

Usage:
    from episodic_consolidator import EpisodicConsolidator, run_consolidation
    
    consolidator = EpisodicConsolidator()
    result = consolidator.consolidate()
"""

import json
import os
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Import from centralized config via brain_orchestrator
try:
    from config import DATABASE_URL, OPENAI_API_KEY
except ImportError:
    import os
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://ira:ira_password@localhost:5432/ira_db")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class DetectedPattern:
    """A pattern detected in episodes."""
    pattern_type: str              # temporal, behavioral, preference, entity
    description: str               # Human-readable description
    identity_id: str               # User this pattern applies to
    evidence: List[str]            # Episode IDs that support this
    confidence: float              # How confident we are (0-1)
    times_observed: int            # How many times seen
    first_seen: datetime
    last_seen: datetime
    
    def to_memory_text(self) -> str:
        """Convert pattern to a memory fact."""
        return self.description


@dataclass
class ConsolidationResult:
    """Result of a consolidation run."""
    episodes_analyzed: int = 0
    patterns_found: int = 0
    memories_created: int = 0
    memories_updated: int = 0
    memories_skipped: int = 0
    duration_ms: float = 0.0
    patterns: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "episodes_analyzed": self.episodes_analyzed,
            "patterns_found": self.patterns_found,
            "memories_created": self.memories_created,
            "memories_updated": self.memories_updated,
            "memories_skipped": self.memories_skipped,
            "duration_ms": round(self.duration_ms, 2),
            "patterns": self.patterns,
            "errors": self.errors,
        }


# =============================================================================
# PATTERN DETECTORS
# =============================================================================

class TemporalPatternDetector:
    """Detect time-based patterns in episodes."""
    
    def detect(
        self,
        episodes: List[Dict],
        identity_id: str
    ) -> List[DetectedPattern]:
        """Find temporal patterns."""
        patterns = []
        
        # Group by day of week
        day_counts = Counter()
        day_episodes = defaultdict(list)
        for ep in episodes:
            day = ep.get("day_of_week", "")
            if day:
                day_counts[day] += 1
                day_episodes[day].append(ep["id"])
        
        # Detect preferred days (>40% of interactions on one day)
        total = sum(day_counts.values())
        if total >= 5:  # Need enough data
            for day, count in day_counts.most_common(1):
                ratio = count / total
                if ratio > 0.4:
                    patterns.append(DetectedPattern(
                        pattern_type="temporal",
                        description=f"This user typically contacts us on {day}s ({count}/{total} interactions)",
                        identity_id=identity_id,
                        evidence=day_episodes[day][:5],
                        confidence=min(0.9, ratio),
                        times_observed=count,
                        first_seen=datetime.now(),
                        last_seen=datetime.now(),
                    ))
        
        # Group by time of day
        time_counts = Counter()
        time_episodes = defaultdict(list)
        for ep in episodes:
            tod = ep.get("time_of_day", "")
            if tod:
                time_counts[tod] += 1
                time_episodes[tod].append(ep["id"])
        
        if total >= 5:
            for tod, count in time_counts.most_common(1):
                ratio = count / total
                if ratio > 0.5:
                    patterns.append(DetectedPattern(
                        pattern_type="temporal",
                        description=f"This user is most active in the {tod} ({count}/{total} interactions)",
                        identity_id=identity_id,
                        evidence=time_episodes[tod][:5],
                        confidence=min(0.9, ratio),
                        times_observed=count,
                        first_seen=datetime.now(),
                        last_seen=datetime.now(),
                    ))
        
        return patterns


class BehavioralPatternDetector:
    """Detect behavioral patterns in episodes."""
    
    def detect(
        self,
        episodes: List[Dict],
        identity_id: str
    ) -> List[DetectedPattern]:
        """Find behavioral patterns."""
        patterns = []
        
        # Group by episode type
        type_counts = Counter()
        type_episodes = defaultdict(list)
        for ep in episodes:
            ep_type = ep.get("episode_type", "")
            if ep_type:
                type_counts[ep_type] += 1
                type_episodes[ep_type].append(ep["id"])
        
        # Detect dominant interaction types
        total = sum(type_counts.values())
        if total >= 5:
            for ep_type, count in type_counts.most_common(2):
                ratio = count / total
                if ratio > 0.3:
                    desc_map = {
                        "inquiry": "frequently asks questions/inquiries",
                        "complaint": "often has complaints or issues to resolve",
                        "transaction": "regularly makes transactions/purchases",
                        "followup": "typically follows up on previous conversations",
                    }
                    desc = desc_map.get(ep_type, f"often engages in {ep_type} interactions")
                    patterns.append(DetectedPattern(
                        pattern_type="behavioral",
                        description=f"This user {desc} ({count}/{total} interactions)",
                        identity_id=identity_id,
                        evidence=type_episodes[ep_type][:5],
                        confidence=min(0.85, ratio),
                        times_observed=count,
                        first_seen=datetime.now(),
                        last_seen=datetime.now(),
                    ))
        
        # Detect emotional patterns
        valence_scores = []
        for ep in episodes:
            valence = ep.get("emotional_valence", 0)
            if isinstance(valence, int):
                valence_scores.append(valence)
        
        if len(valence_scores) >= 5:
            avg_valence = sum(valence_scores) / len(valence_scores)
            if avg_valence > 0.5:
                patterns.append(DetectedPattern(
                    pattern_type="behavioral",
                    description="This user generally has positive interactions with us",
                    identity_id=identity_id,
                    evidence=[],
                    confidence=0.7,
                    times_observed=len(valence_scores),
                    first_seen=datetime.now(),
                    last_seen=datetime.now(),
                ))
            elif avg_valence < -0.3:
                patterns.append(DetectedPattern(
                    pattern_type="behavioral",
                    description="This user has had some challenging interactions - be extra careful and supportive",
                    identity_id=identity_id,
                    evidence=[],
                    confidence=0.7,
                    times_observed=len(valence_scores),
                    first_seen=datetime.now(),
                    last_seen=datetime.now(),
                ))
        
        return patterns


class TopicPatternDetector:
    """Detect topic/interest patterns in episodes."""
    
    def detect(
        self,
        episodes: List[Dict],
        identity_id: str
    ) -> List[DetectedPattern]:
        """Find topic patterns."""
        patterns = []
        
        # Aggregate topics
        topic_counts = Counter()
        topic_episodes = defaultdict(list)
        for ep in episodes:
            topics = ep.get("key_topics", [])
            if isinstance(topics, list):
                for topic in topics:
                    topic_lower = topic.lower() if isinstance(topic, str) else str(topic)
                    topic_counts[topic_lower] += 1
                    topic_episodes[topic_lower].append(ep["id"])
        
        # Find recurring topics
        for topic, count in topic_counts.most_common(3):
            if count >= 3:  # Topic mentioned at least 3 times
                patterns.append(DetectedPattern(
                    pattern_type="interest",
                    description=f"This user frequently asks about '{topic}'",
                    identity_id=identity_id,
                    evidence=topic_episodes[topic][:5],
                    confidence=min(0.8, 0.5 + count * 0.1),
                    times_observed=count,
                    first_seen=datetime.now(),
                    last_seen=datetime.now(),
                ))
        
        # Aggregate entities
        entity_counts = Counter()
        entity_episodes = defaultdict(list)
        for ep in episodes:
            entities = ep.get("entities_mentioned", [])
            if isinstance(entities, list):
                for entity in entities:
                    entity_lower = entity.lower() if isinstance(entity, str) else str(entity)
                    entity_counts[entity_lower] += 1
                    entity_episodes[entity_lower].append(ep["id"])
        
        # Find recurring entities
        for entity, count in entity_counts.most_common(2):
            if count >= 2:
                patterns.append(DetectedPattern(
                    pattern_type="entity_interest",
                    description=f"This user often discusses '{entity}'",
                    identity_id=identity_id,
                    evidence=entity_episodes[entity][:5],
                    confidence=min(0.8, 0.4 + count * 0.15),
                    times_observed=count,
                    first_seen=datetime.now(),
                    last_seen=datetime.now(),
                ))
        
        return patterns


# =============================================================================
# EPISODIC CONSOLIDATOR
# =============================================================================

class EpisodicConsolidator:
    """
    Consolidates episodic memories into semantic facts.
    
    Like the brain during sleep, this finds patterns in episodes
    and creates stable semantic memories from them.
    """
    
    def __init__(self):
        self.temporal_detector = TemporalPatternDetector()
        self.behavioral_detector = BehavioralPatternDetector()
        self.topic_detector = TopicPatternDetector()
        
        self._min_episodes = 5          # Need at least this many episodes
        self._min_confidence = 0.6      # Minimum confidence to create memory
        self._lookback_days = 90        # How far back to look
    
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
            print(f"[consolidator] DB connection error: {e}")
            return None
    
    def _load_episodes_from_json(self) -> Dict[str, List[Dict]]:
        """Load episodes from JSON file (fallback when no PostgreSQL)."""
        episodes_file = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "mem0_storage" / "episodes.json"
        if not episodes_file.exists():
            return {}
        
        try:
            data = json.loads(episodes_file.read_text())
            
            # Convert to format expected by pattern detectors
            result = {}
            for identity_id, episodes_dict in data.items():
                episodes = []
                for ep_id, ep_data in episodes_dict.items():
                    # Parse timestamp
                    ts_str = ep_data.get("timestamp", "")
                    try:
                        ts = datetime.fromisoformat(ts_str)
                    except:
                        ts = datetime.now()
                    
                    episodes.append({
                        "id": ep_id,
                        "timestamp": ts,
                        "episode_type": ep_data.get("channel", "unknown"),
                        "summary": ep_data.get("summary", ""),
                        "day_of_week": ts.strftime("%A"),
                        "time_of_day": "morning" if ts.hour < 12 else ("afternoon" if ts.hour < 17 else "evening"),
                        "key_topics": ep_data.get("topics", []),
                        "entities_mentioned": [],
                        "emotional_valence": ep_data.get("emotional_valence", 0),
                    })
                
                if episodes:
                    result[identity_id] = episodes
            
            return result
        except Exception as e:
            print(f"[consolidator] JSON load error: {e}")
            return {}
    
    def consolidate(
        self,
        identity_id: Optional[str] = None,
        dry_run: bool = False
    ) -> ConsolidationResult:
        """
        Run consolidation for one user or all users.
        
        Args:
            identity_id: If provided, only consolidate for this user
            dry_run: If True, don't create memories, just report patterns
        
        Returns:
            ConsolidationResult with statistics
        """
        import time
        start = time.time()
        result = ConsolidationResult()
        
        conn = self._get_db_connection()
        
        # Try PostgreSQL first
        if conn:
            try:
                with conn.cursor() as cur:
                    # Get users to process
                    if identity_id:
                        users = [identity_id]
                    else:
                        cutoff = datetime.now() - timedelta(days=self._lookback_days)
                        cur.execute("""
                            SELECT DISTINCT identity_id
                            FROM ira_memory.episodes
                            WHERE timestamp > %s
                            GROUP BY identity_id
                            HAVING COUNT(*) >= %s
                        """, (cutoff, self._min_episodes))
                        users = [row[0] for row in cur.fetchall()]
                    
                    # Process each user
                    for uid in users:
                        user_result = self._consolidate_user(conn, uid, dry_run)
                        result.episodes_analyzed += user_result["episodes"]
                        result.patterns_found += user_result["patterns_found"]
                        result.memories_created += user_result["created"]
                        result.memories_updated += user_result["updated"]
                        result.memories_skipped += user_result["skipped"]
                        result.patterns.extend(user_result["patterns"])
                        
                if not dry_run:
                    conn.commit()
                    
            except Exception as e:
                result.errors.append(str(e))
                conn.rollback()
            finally:
                conn.close()
        else:
            # Fall back to JSON episodes file
            print("[consolidator] No DB, trying JSON episodes file...")
            json_episodes = self._load_episodes_from_json()
            
            if not json_episodes:
                print("[consolidator] No episodes found in JSON either")
                result.errors.append("No episodes available (no DB or JSON)")
            else:
                # Process JSON episodes
                cutoff = datetime.now() - timedelta(days=self._lookback_days)
                
                for uid, episodes in json_episodes.items():
                    if identity_id and uid != identity_id:
                        continue
                    
                    # Filter by date
                    recent_episodes = [
                        ep for ep in episodes 
                        if ep.get("timestamp", datetime.min) > cutoff
                    ]
                    
                    if len(recent_episodes) < self._min_episodes:
                        continue
                    
                    result.episodes_analyzed += len(recent_episodes)
                    
                    # Detect patterns
                    all_patterns = []
                    all_patterns.extend(self.temporal_detector.detect(recent_episodes, uid))
                    all_patterns.extend(self.behavioral_detector.detect(recent_episodes, uid))
                    all_patterns.extend(self.topic_detector.detect(recent_episodes, uid))
                    
                    result.patterns_found += len(all_patterns)
                    
                    # Filter by confidence and add to result
                    confident_patterns = [p for p in all_patterns if p.confidence >= self._min_confidence]
                    for pattern in confident_patterns:
                        result.patterns.append({
                            "type": pattern.pattern_type,
                            "description": pattern.description,
                            "confidence": pattern.confidence,
                        })
                    
                    # If not dry run, store patterns in Mem0
                    if not dry_run and confident_patterns:
                        self._store_patterns_mem0(uid, confident_patterns)
                        result.memories_created += len(confident_patterns)
                
                print(f"[consolidator] Processed {result.episodes_analyzed} episodes from JSON")
        
        result.duration_ms = (time.time() - start) * 1000
        return result
    
    def _store_patterns_mem0(self, identity_id: str, patterns: List[DetectedPattern]):
        """Store detected patterns to Mem0 (when no PostgreSQL available)."""
        try:
            from mem0 import MemoryClient
            api_key = os.environ.get("MEM0_API_KEY")
            if not api_key:
                return
            
            client = MemoryClient(api_key=api_key)
            
            for pattern in patterns:
                client.add(
                    messages=[{"role": "assistant", "content": pattern.to_memory_text()}],
                    user_id=identity_id,
                    metadata={
                        "type": "consolidated_pattern",
                        "pattern_type": pattern.pattern_type,
                        "confidence": pattern.confidence,
                        "source": "episodic_consolidation",
                    }
                )
        except Exception as e:
            print(f"[consolidator] Mem0 store error: {e}")
    
    def _consolidate_user(
        self,
        conn,
        identity_id: str,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Consolidate episodes for a single user."""
        result = {
            "episodes": 0,
            "patterns_found": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "patterns": [],
        }
        
        # Load episodes
        cutoff = datetime.now() - timedelta(days=self._lookback_days)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, timestamp, episode_type, summary,
                       day_of_week, time_of_day, key_topics,
                       entities_mentioned, emotional_valence
                FROM ira_memory.episodes
                WHERE identity_id = %s AND timestamp > %s
                ORDER BY timestamp DESC
            """, (identity_id, cutoff))
            
            episodes = []
            for row in cur.fetchall():
                episodes.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "episode_type": row[2],
                    "summary": row[3],
                    "day_of_week": row[4],
                    "time_of_day": row[5],
                    "key_topics": row[6] or [],
                    "entities_mentioned": row[7] or [],
                    "emotional_valence": row[8] or 0,
                })
        
        result["episodes"] = len(episodes)
        
        if len(episodes) < self._min_episodes:
            return result
        
        # Detect patterns
        all_patterns = []
        all_patterns.extend(self.temporal_detector.detect(episodes, identity_id))
        all_patterns.extend(self.behavioral_detector.detect(episodes, identity_id))
        all_patterns.extend(self.topic_detector.detect(episodes, identity_id))
        
        result["patterns_found"] = len(all_patterns)
        
        # Filter by confidence
        confident_patterns = [p for p in all_patterns if p.confidence >= self._min_confidence]
        
        # Create/update memories
        for pattern in confident_patterns:
            pattern_dict = {
                "type": pattern.pattern_type,
                "description": pattern.description,
                "confidence": pattern.confidence,
                "times_observed": pattern.times_observed,
            }
            result["patterns"].append(pattern_dict)
            
            if dry_run:
                continue
            
            # Check if similar memory exists
            existing = self._find_similar_memory(conn, identity_id, pattern)
            
            if existing:
                # Update existing
                self._update_memory_from_pattern(conn, existing, pattern)
                result["updated"] += 1
            else:
                # Create new
                self._create_memory_from_pattern(conn, identity_id, pattern)
                result["created"] += 1
        
        return result
    
    def _find_similar_memory(
        self,
        conn,
        identity_id: str,
        pattern: DetectedPattern
    ) -> Optional[str]:
        """Check if a similar memory already exists."""
        with conn.cursor() as cur:
            # Look for memories with similar text
            cur.execute("""
                SELECT id
                FROM ira_memory.user_memories
                WHERE identity_id = %s
                  AND is_active = TRUE
                  AND (
                      memory_text ILIKE %s
                      OR metadata->>'pattern_type' = %s
                  )
                LIMIT 1
            """, (identity_id, f'%{pattern.description[:50]}%', pattern.pattern_type))
            
            row = cur.fetchone()
            return row[0] if row else None
    
    def _create_memory_from_pattern(
        self,
        conn,
        identity_id: str,
        pattern: DetectedPattern
    ):
        """Create a new semantic memory from a pattern."""
        import hashlib
        
        memory_id = hashlib.md5(
            f"{identity_id}_{pattern.pattern_type}_{pattern.description[:50]}".encode()
        ).hexdigest()[:16]
        
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ira_memory.user_memories
                (id, identity_id, memory_text, category, importance, source,
                 confidence, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """, (
                memory_id,
                identity_id,
                pattern.to_memory_text(),
                pattern.pattern_type,
                min(0.8, pattern.confidence),
                "episodic_consolidation",
                pattern.confidence,
                json.dumps({
                    "pattern_type": pattern.pattern_type,
                    "evidence_count": len(pattern.evidence),
                    "times_observed": pattern.times_observed,
                    "consolidated_at": datetime.now().isoformat(),
                }),
            ))
    
    def _update_memory_from_pattern(
        self,
        conn,
        memory_id: str,
        pattern: DetectedPattern
    ):
        """Update an existing memory with new pattern evidence."""
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE ira_memory.user_memories
                SET confidence = GREATEST(confidence, %s),
                    importance = GREATEST(importance, %s),
                    recalled_count = recalled_count + 1,
                    last_accessed = NOW(),
                    updated_at = NOW(),
                    metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb
                WHERE id = %s
            """, (
                pattern.confidence,
                min(0.8, pattern.confidence),
                json.dumps({
                    "last_consolidated": datetime.now().isoformat(),
                    "times_observed": pattern.times_observed,
                }),
                memory_id,
            ))


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_consolidator: Optional[EpisodicConsolidator] = None


def get_consolidator() -> EpisodicConsolidator:
    """Get singleton consolidator instance."""
    global _consolidator
    if _consolidator is None:
        _consolidator = EpisodicConsolidator()
    return _consolidator


def run_consolidation(
    identity_id: Optional[str] = None,
    dry_run: bool = False
) -> ConsolidationResult:
    """Run episodic consolidation."""
    return get_consolidator().consolidate(identity_id, dry_run)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Testing EpisodicConsolidator...")
    
    consolidator = EpisodicConsolidator()
    
    # Dry run to see what patterns would be detected
    result = consolidator.consolidate(dry_run=True)
    
    print(f"\nConsolidation result: {json.dumps(result.to_dict(), indent=2)}")
