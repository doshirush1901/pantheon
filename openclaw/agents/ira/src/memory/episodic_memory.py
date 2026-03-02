#!/usr/bin/env python3
"""
EPISODIC MEMORY - Events with Temporal Context

╔════════════════════════════════════════════════════════════════════╗
║  Semantic Memory = FACTS ("John works at ABC Corp")                ║
║  Episodic Memory = EVENTS ("Tuesday 3pm - John called frustrated   ║
║                    about shipping delay, resolved with expedited") ║
╚════════════════════════════════════════════════════════════════════╝

This is the missing temporal layer that enables:
- "When did we last discuss this?"
- "What happened in our last conversation?"
- "What did we talk about last week?"
- Learning from conversation patterns over time

Based on neuroscience:
- Hippocampus binds what/where/when into episodes
- Episodes later consolidate into semantic facts
- Retrieval uses temporal and contextual cues
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import hashlib

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

class EpisodeType(Enum):
    CONVERSATION = "conversation"      # A conversation/interaction
    TRANSACTION = "transaction"        # A business transaction
    INQUIRY = "inquiry"               # A question/inquiry
    COMPLAINT = "complaint"           # A complaint or issue
    MILESTONE = "milestone"           # A significant event
    FOLLOWUP = "followup"             # A follow-up interaction
    CORRECTION = "correction"         # A correction or update


class EmotionalValence(Enum):
    VERY_NEGATIVE = -2
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    VERY_POSITIVE = 2


@dataclass
class Episode:
    """
    A single episode - a bounded event in time.
    
    Think of it as: "What happened? When? Who was involved? How did it end?"
    """
    id: str
    timestamp: datetime
    identity_id: str                    # Who was involved
    channel: str                        # Where it happened (telegram, email, etc.)
    episode_type: EpisodeType
    summary: str                        # What happened (1-2 sentences)
    
    # Temporal context
    duration_minutes: int = 0
    day_of_week: str = ""              # Monday, Tuesday, etc.
    time_of_day: str = ""              # morning, afternoon, evening, night
    
    # Content
    key_topics: List[str] = field(default_factory=list)
    entities_mentioned: List[str] = field(default_factory=list)
    user_intent: str = ""
    outcome: str = ""                  # How it resolved
    
    # Emotional context
    emotional_valence: EmotionalValence = EmotionalValence.NEUTRAL
    user_emotional_state: str = ""
    
    # Linking
    related_episodes: List[str] = field(default_factory=list)  # IDs of related episodes
    triggered_memories: List[str] = field(default_factory=list)  # Memory IDs that were used
    created_memories: List[str] = field(default_factory=list)   # Memory IDs that were created
    
    # Retrieval
    retrieval_cues: List[str] = field(default_factory=list)  # Keywords for retrieval
    importance: float = 0.5           # 0-1 scale
    recalled_count: int = 0
    last_recalled: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "identity_id": self.identity_id,
            "channel": self.channel,
            "episode_type": self.episode_type.value,
            "summary": self.summary,
            "duration_minutes": self.duration_minutes,
            "day_of_week": self.day_of_week,
            "time_of_day": self.time_of_day,
            "key_topics": self.key_topics,
            "entities_mentioned": self.entities_mentioned,
            "user_intent": self.user_intent,
            "outcome": self.outcome,
            "emotional_valence": self.emotional_valence.value,
            "user_emotional_state": self.user_emotional_state,
            "related_episodes": self.related_episodes,
            "triggered_memories": self.triggered_memories,
            "created_memories": self.created_memories,
            "retrieval_cues": self.retrieval_cues,
            "importance": self.importance,
            "recalled_count": self.recalled_count,
            "last_recalled": self.last_recalled.isoformat() if self.last_recalled else None,
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "Episode":
        return cls(
            id=d.get("id", ""),
            timestamp=datetime.fromisoformat(d["timestamp"]) if d.get("timestamp") else datetime.now(),
            identity_id=d.get("identity_id", ""),
            channel=d.get("channel", ""),
            episode_type=EpisodeType(d.get("episode_type", "conversation")),
            summary=d.get("summary", ""),
            duration_minutes=d.get("duration_minutes", 0),
            day_of_week=d.get("day_of_week", ""),
            time_of_day=d.get("time_of_day", ""),
            key_topics=d.get("key_topics", []),
            entities_mentioned=d.get("entities_mentioned", []),
            user_intent=d.get("user_intent", ""),
            outcome=d.get("outcome", ""),
            emotional_valence=EmotionalValence(d.get("emotional_valence", 0)),
            user_emotional_state=d.get("user_emotional_state", ""),
            related_episodes=d.get("related_episodes", []),
            triggered_memories=d.get("triggered_memories", []),
            created_memories=d.get("created_memories", []),
            retrieval_cues=d.get("retrieval_cues", []),
            importance=d.get("importance", 0.5),
            recalled_count=d.get("recalled_count", 0),
            last_recalled=datetime.fromisoformat(d["last_recalled"]) if d.get("last_recalled") else None,
        )
    
    def format_for_display(self) -> str:
        """Human-readable format."""
        date_str = self.timestamp.strftime("%A %B %d, %Y at %I:%M %p")
        return f"[{date_str}] {self.summary}"
    
    def format_for_prompt(self) -> str:
        """Format for LLM context."""
        relative = self._relative_time()
        return f"[{relative}] {self.summary} (outcome: {self.outcome or 'ongoing'})"
    
    def _relative_time(self) -> str:
        """Get relative time description."""
        now = datetime.now()
        diff = now - self.timestamp
        
        if diff.days == 0:
            if diff.seconds < 3600:
                return "earlier today"
            return "today"
        elif diff.days == 1:
            return "yesterday"
        elif diff.days < 7:
            return f"last {self.day_of_week}"
        elif diff.days < 14:
            return "last week"
        elif diff.days < 30:
            return f"{diff.days // 7} weeks ago"
        elif diff.days < 60:
            return "last month"
        else:
            return f"{diff.days // 30} months ago"


# =============================================================================
# SCHEMA
# =============================================================================

EPISODIC_MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS ira_memory.episodes (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    identity_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    episode_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    
    duration_minutes INTEGER DEFAULT 0,
    day_of_week TEXT,
    time_of_day TEXT,
    
    key_topics JSONB DEFAULT '[]',
    entities_mentioned JSONB DEFAULT '[]',
    user_intent TEXT,
    outcome TEXT,
    
    emotional_valence INTEGER DEFAULT 0,
    user_emotional_state TEXT,
    
    related_episodes JSONB DEFAULT '[]',
    triggered_memories JSONB DEFAULT '[]',
    created_memories JSONB DEFAULT '[]',
    
    retrieval_cues JSONB DEFAULT '[]',
    importance REAL DEFAULT 0.5,
    recalled_count INTEGER DEFAULT 0,
    last_recalled TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episodes_identity ON ira_memory.episodes(identity_id);
CREATE INDEX IF NOT EXISTS idx_episodes_timestamp ON ira_memory.episodes(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_episodes_type ON ira_memory.episodes(episode_type);
CREATE INDEX IF NOT EXISTS idx_episodes_importance ON ira_memory.episodes(importance DESC);
"""


# =============================================================================
# EPISODIC MEMORY MANAGER
# =============================================================================

class EpisodicMemory:
    """
    Manages episodic memories - events with temporal context.
    
    Key capabilities:
    - Record conversation episodes as they happen
    - Retrieve by time ("last week", "on Tuesday")
    - Retrieve by topic/entity
    - Link related episodes
    - Track what was discussed when
    """
    
    def __init__(self):
        self._schema_ensured = False
        self._current_episode: Optional[Episode] = None
    
    def _get_db_connection(self):
        """Get PostgreSQL connection."""
        if not DATABASE_URL:
            return None
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        except Exception as e:
            print(f"[episodic_memory] DB connection error: {e}")
            return None
    
    def ensure_schema(self):
        """Ensure the database schema exists."""
        if self._schema_ensured:
            return
        
        conn = self._get_db_connection()
        if not conn:
            return
        
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE SCHEMA IF NOT EXISTS ira_memory")
                cur.execute(EPISODIC_MEMORY_SCHEMA)
                conn.commit()
            self._schema_ensured = True
        except Exception as e:
            print(f"[episodic_memory] Schema error: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _get_time_context(self, dt: datetime) -> Tuple[str, str]:
        """Get day of week and time of day."""
        day_of_week = dt.strftime("%A")
        hour = dt.hour
        
        if 5 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 17:
            time_of_day = "afternoon"
        elif 17 <= hour < 21:
            time_of_day = "evening"
        else:
            time_of_day = "night"
        
        return day_of_week, time_of_day
    
    # =========================================================================
    # RECORDING
    # =========================================================================
    
    def start_episode(
        self,
        identity_id: str,
        channel: str,
        user_message: str,
        episode_type: EpisodeType = EpisodeType.CONVERSATION
    ) -> Episode:
        """
        Start recording a new episode.
        
        Call this when a conversation/interaction starts.
        """
        self.ensure_schema()
        
        now = datetime.now()
        day_of_week, time_of_day = self._get_time_context(now)
        
        episode_id = hashlib.md5(
            f"{identity_id}_{now.isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Extract initial cues from message
        retrieval_cues = self._extract_cues(user_message)
        
        self._current_episode = Episode(
            id=episode_id,
            timestamp=now,
            identity_id=identity_id,
            channel=channel,
            episode_type=episode_type,
            summary="",  # Will be generated at end
            day_of_week=day_of_week,
            time_of_day=time_of_day,
            retrieval_cues=retrieval_cues,
            user_intent=user_message[:200],
        )
        
        return self._current_episode
    
    def end_episode(
        self,
        summary: str,
        outcome: str = "",
        key_topics: List[str] = None,
        entities_mentioned: List[str] = None,
        emotional_valence: EmotionalValence = EmotionalValence.NEUTRAL,
        user_emotional_state: str = "",
        importance: float = 0.5,
        triggered_memories: List[str] = None,
        created_memories: List[str] = None
    ) -> Optional[Episode]:
        """
        End and save the current episode.
        
        Call this when a conversation/interaction ends.
        """
        if not self._current_episode:
            return None
        
        episode = self._current_episode
        
        # Calculate duration
        duration = datetime.now() - episode.timestamp
        episode.duration_minutes = int(duration.total_seconds() / 60)
        
        # Fill in details
        episode.summary = summary
        episode.outcome = outcome
        episode.key_topics = key_topics or []
        episode.entities_mentioned = entities_mentioned or []
        episode.emotional_valence = emotional_valence
        episode.user_emotional_state = user_emotional_state
        episode.importance = importance
        episode.triggered_memories = triggered_memories or []
        episode.created_memories = created_memories or []
        
        # Add more retrieval cues
        episode.retrieval_cues.extend(key_topics or [])
        episode.retrieval_cues.extend(entities_mentioned or [])
        episode.retrieval_cues = list(set(episode.retrieval_cues))[:20]
        
        # Save to database
        self._save_episode(episode)
        
        self._current_episode = None
        return episode
    
    def record_episode(
        self,
        identity_id: str,
        channel: str,
        summary: str,
        episode_type: EpisodeType = EpisodeType.CONVERSATION,
        timestamp: datetime = None,
        **kwargs
    ) -> Episode:
        """
        Record a complete episode in one call.
        
        Use this for recording past events or simple interactions.
        """
        self.ensure_schema()
        
        ts = timestamp or datetime.now()
        day_of_week, time_of_day = self._get_time_context(ts)
        
        episode_id = hashlib.md5(
            f"{identity_id}_{ts.isoformat()}".encode()
        ).hexdigest()[:16]
        
        episode = Episode(
            id=episode_id,
            timestamp=ts,
            identity_id=identity_id,
            channel=channel,
            episode_type=episode_type,
            summary=summary,
            day_of_week=day_of_week,
            time_of_day=time_of_day,
            **kwargs
        )
        
        # Extract retrieval cues
        episode.retrieval_cues = self._extract_cues(summary)
        episode.retrieval_cues.extend(kwargs.get("key_topics", []))
        episode.retrieval_cues.extend(kwargs.get("entities_mentioned", []))
        episode.retrieval_cues = list(set(episode.retrieval_cues))[:20]
        
        self._save_episode(episode)
        return episode
    
    def _extract_cues(self, text: str) -> List[str]:
        """Extract retrieval cues from text."""
        cues = []
        
        # Extract significant words (4+ chars, not common)
        words = re.findall(r'\b[A-Za-z]{4,}\b', text.lower())
        stop_words = {'that', 'this', 'with', 'from', 'have', 'been', 'were', 'what', 'when', 'where', 'which'}
        cues = [w for w in words if w not in stop_words][:10]
        
        # Extract numbers (might be prices, quantities)
        numbers = re.findall(r'\b\d+\b', text)
        cues.extend(numbers[:3])
        
        return cues
    
    def _save_episode(self, episode: Episode):
        """Save episode to database."""
        conn = self._get_db_connection()
        if not conn:
            return
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ira_memory.episodes 
                    (id, timestamp, identity_id, channel, episode_type, summary,
                     duration_minutes, day_of_week, time_of_day,
                     key_topics, entities_mentioned, user_intent, outcome,
                     emotional_valence, user_emotional_state,
                     related_episodes, triggered_memories, created_memories,
                     retrieval_cues, importance, recalled_count, last_recalled)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        summary = EXCLUDED.summary,
                        outcome = EXCLUDED.outcome,
                        key_topics = EXCLUDED.key_topics,
                        entities_mentioned = EXCLUDED.entities_mentioned,
                        emotional_valence = EXCLUDED.emotional_valence,
                        importance = EXCLUDED.importance,
                        recalled_count = EXCLUDED.recalled_count,
                        last_recalled = EXCLUDED.last_recalled
                """, (
                    episode.id,
                    episode.timestamp,
                    episode.identity_id,
                    episode.channel,
                    episode.episode_type.value,
                    episode.summary,
                    episode.duration_minutes,
                    episode.day_of_week,
                    episode.time_of_day,
                    json.dumps(episode.key_topics),
                    json.dumps(episode.entities_mentioned),
                    episode.user_intent,
                    episode.outcome,
                    episode.emotional_valence.value,
                    episode.user_emotional_state,
                    json.dumps(episode.related_episodes),
                    json.dumps(episode.triggered_memories),
                    json.dumps(episode.created_memories),
                    json.dumps(episode.retrieval_cues),
                    episode.importance,
                    episode.recalled_count,
                    episode.last_recalled,
                ))
                conn.commit()
        except Exception as e:
            print(f"[episodic_memory] Save error: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    # =========================================================================
    # RETRIEVAL
    # =========================================================================
    
    def retrieve_recent(
        self,
        identity_id: str,
        limit: int = 5,
        days_back: int = 30
    ) -> List[Episode]:
        """
        Retrieve recent episodes for a user.
        """
        self.ensure_schema()
        
        conn = self._get_db_connection()
        if not conn:
            return []
        
        try:
            with conn.cursor() as cur:
                cutoff = datetime.now() - timedelta(days=days_back)
                cur.execute("""
                    SELECT id, timestamp, identity_id, channel, episode_type, summary,
                           duration_minutes, day_of_week, time_of_day,
                           key_topics, entities_mentioned, user_intent, outcome,
                           emotional_valence, user_emotional_state,
                           related_episodes, triggered_memories, created_memories,
                           retrieval_cues, importance, recalled_count, last_recalled
                    FROM ira_memory.episodes
                    WHERE identity_id = %s AND timestamp > %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (identity_id, cutoff, limit))
                
                episodes = []
                for row in cur.fetchall():
                    episodes.append(self._row_to_episode(row))
                
                return episodes
        except Exception as e:
            print(f"[episodic_memory] Retrieve error: {e}")
            return []
        finally:
            conn.close()
    
    def retrieve_by_time(
        self,
        identity_id: str,
        time_reference: str,
        limit: int = 5
    ) -> List[Episode]:
        """
        Retrieve episodes by temporal reference.
        
        Supports: "yesterday", "last week", "last Tuesday", "last month", etc.
        """
        self.ensure_schema()
        
        now = datetime.now()
        start_date = None
        end_date = None
        day_filter = None
        
        time_ref = time_reference.lower().strip()
        
        # Parse temporal reference
        if time_ref in ["today", "earlier today"]:
            start_date = now.replace(hour=0, minute=0, second=0)
            end_date = now
        elif time_ref == "yesterday":
            yesterday = now - timedelta(days=1)
            start_date = yesterday.replace(hour=0, minute=0, second=0)
            end_date = yesterday.replace(hour=23, minute=59, second=59)
        elif time_ref == "last week":
            start_date = now - timedelta(days=7)
            end_date = now
        elif time_ref == "last month":
            start_date = now - timedelta(days=30)
            end_date = now
        elif "last" in time_ref:
            # "last Tuesday", "last Monday", etc.
            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            for i, day in enumerate(days):
                if day in time_ref:
                    day_filter = day.capitalize()
                    start_date = now - timedelta(days=14)  # Look back 2 weeks
                    end_date = now
                    break
        else:
            # Default: last 7 days
            start_date = now - timedelta(days=7)
            end_date = now
        
        if not start_date:
            return []
        
        conn = self._get_db_connection()
        if not conn:
            return []
        
        try:
            with conn.cursor() as cur:
                if day_filter:
                    cur.execute("""
                        SELECT id, timestamp, identity_id, channel, episode_type, summary,
                               duration_minutes, day_of_week, time_of_day,
                               key_topics, entities_mentioned, user_intent, outcome,
                               emotional_valence, user_emotional_state,
                               related_episodes, triggered_memories, created_memories,
                               retrieval_cues, importance, recalled_count, last_recalled
                        FROM ira_memory.episodes
                        WHERE identity_id = %s 
                          AND timestamp BETWEEN %s AND %s
                          AND day_of_week = %s
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, (identity_id, start_date, end_date, day_filter, limit))
                else:
                    cur.execute("""
                        SELECT id, timestamp, identity_id, channel, episode_type, summary,
                               duration_minutes, day_of_week, time_of_day,
                               key_topics, entities_mentioned, user_intent, outcome,
                               emotional_valence, user_emotional_state,
                               related_episodes, triggered_memories, created_memories,
                               retrieval_cues, importance, recalled_count, last_recalled
                        FROM ira_memory.episodes
                        WHERE identity_id = %s 
                          AND timestamp BETWEEN %s AND %s
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, (identity_id, start_date, end_date, limit))
                
                episodes = []
                for row in cur.fetchall():
                    ep = self._row_to_episode(row)
                    self._mark_recalled(ep.id)
                    episodes.append(ep)
                
                return episodes
        except Exception as e:
            print(f"[episodic_memory] Time retrieval error: {e}")
            return []
        finally:
            conn.close()
    
    def retrieve_by_topic(
        self,
        identity_id: str,
        topic: str,
        limit: int = 5
    ) -> List[Episode]:
        """
        Retrieve episodes by topic/entity.
        """
        self.ensure_schema()
        
        conn = self._get_db_connection()
        if not conn:
            return []
        
        try:
            with conn.cursor() as cur:
                # Search in key_topics, entities_mentioned, and retrieval_cues
                topic_pattern = f'%{topic.lower()}%'
                cur.execute("""
                    SELECT id, timestamp, identity_id, channel, episode_type, summary,
                           duration_minutes, day_of_week, time_of_day,
                           key_topics, entities_mentioned, user_intent, outcome,
                           emotional_valence, user_emotional_state,
                           related_episodes, triggered_memories, created_memories,
                           retrieval_cues, importance, recalled_count, last_recalled
                    FROM ira_memory.episodes
                    WHERE identity_id = %s 
                      AND (
                          LOWER(summary) LIKE %s
                          OR key_topics::text ILIKE %s
                          OR entities_mentioned::text ILIKE %s
                          OR retrieval_cues::text ILIKE %s
                      )
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (identity_id, topic_pattern, topic_pattern, topic_pattern, topic_pattern, limit))
                
                episodes = []
                for row in cur.fetchall():
                    ep = self._row_to_episode(row)
                    self._mark_recalled(ep.id)
                    episodes.append(ep)
                
                return episodes
        except Exception as e:
            print(f"[episodic_memory] Topic retrieval error: {e}")
            return []
        finally:
            conn.close()
    
    def retrieve_for_prompt(
        self,
        identity_id: str,
        query: str,
        limit: int = 3
    ) -> str:
        """
        Retrieve episodes formatted for LLM prompt.
        """
        # Try to detect temporal reference
        time_refs = ["yesterday", "last week", "last month", "today", "earlier"]
        for ref in time_refs:
            if ref in query.lower():
                episodes = self.retrieve_by_time(identity_id, ref, limit)
                if episodes:
                    return self._format_episodes_for_prompt(episodes)
        
        # Try topic-based retrieval
        episodes = self.retrieve_by_topic(identity_id, query, limit)
        if not episodes:
            # Fallback to recent
            episodes = self.retrieve_recent(identity_id, limit)
        
        return self._format_episodes_for_prompt(episodes)
    
    def _format_episodes_for_prompt(self, episodes: List[Episode]) -> str:
        """Format episodes for LLM context."""
        if not episodes:
            return ""
        
        lines = ["CONVERSATION HISTORY (what happened before):"]
        for ep in episodes:
            lines.append(f"• {ep.format_for_prompt()}")
        
        return "\n".join(lines)
    
    def _row_to_episode(self, row: tuple) -> Episode:
        """Convert database row to Episode."""
        return Episode(
            id=row[0],
            timestamp=row[1],
            identity_id=row[2],
            channel=row[3],
            episode_type=EpisodeType(row[4]),
            summary=row[5],
            duration_minutes=row[6] or 0,
            day_of_week=row[7] or "",
            time_of_day=row[8] or "",
            key_topics=row[9] or [],
            entities_mentioned=row[10] or [],
            user_intent=row[11] or "",
            outcome=row[12] or "",
            emotional_valence=EmotionalValence(row[13] or 0),
            user_emotional_state=row[14] or "",
            related_episodes=row[15] or [],
            triggered_memories=row[16] or [],
            created_memories=row[17] or [],
            retrieval_cues=row[18] or [],
            importance=row[19] or 0.5,
            recalled_count=row[20] or 0,
            last_recalled=row[21],
        )
    
    def _mark_recalled(self, episode_id: str):
        """Mark an episode as recalled."""
        conn = self._get_db_connection()
        if not conn:
            return
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE ira_memory.episodes
                    SET recalled_count = recalled_count + 1,
                        last_recalled = NOW()
                    WHERE id = %s
                """, (episode_id,))
                conn.commit()
        except Exception as e:
            print(f"[episodic_memory] Mark recalled error: {e}")
        finally:
            conn.close()
    
    # =========================================================================
    # ANALYSIS
    # =========================================================================
    
    def get_conversation_patterns(self, identity_id: str) -> Dict:
        """
        Analyze conversation patterns for a user.
        
        Returns insights like:
        - Most active days/times
        - Common topics
        - Typical emotional states
        """
        self.ensure_schema()
        
        conn = self._get_db_connection()
        if not conn:
            return {}
        
        try:
            with conn.cursor() as cur:
                # Get all episodes for analysis
                cur.execute("""
                    SELECT day_of_week, time_of_day, episode_type, 
                           key_topics, emotional_valence
                    FROM ira_memory.episodes
                    WHERE identity_id = %s
                """, (identity_id,))
                
                rows = cur.fetchall()
                if not rows:
                    return {}
                
                # Analyze patterns
                day_counts = {}
                time_counts = {}
                topic_counts = {}
                
                for day, time, etype, topics, emotion in rows:
                    day_counts[day] = day_counts.get(day, 0) + 1
                    time_counts[time] = time_counts.get(time, 0) + 1
                    for topic in (topics or []):
                        topic_counts[topic] = topic_counts.get(topic, 0) + 1
                
                return {
                    "total_episodes": len(rows),
                    "most_active_day": max(day_counts, key=day_counts.get) if day_counts else None,
                    "most_active_time": max(time_counts, key=time_counts.get) if time_counts else None,
                    "top_topics": sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5],
                    "by_day": day_counts,
                    "by_time": time_counts,
                }
        except Exception as e:
            print(f"[episodic_memory] Pattern analysis error: {e}")
            return {}
        finally:
            conn.close()
    
    def get_stats(self) -> Dict:
        """Get episodic memory statistics."""
        conn = self._get_db_connection()
        if not conn:
            return {}
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(DISTINCT identity_id) as unique_users,
                        AVG(importance) as avg_importance,
                        SUM(recalled_count) as total_recalls
                    FROM ira_memory.episodes
                """)
                row = cur.fetchone()
                
                return {
                    "total_episodes": row[0] or 0,
                    "unique_users": row[1] or 0,
                    "avg_importance": float(row[2]) if row[2] else 0,
                    "total_recalls": row[3] or 0,
                }
        except Exception as e:
            print(f"[episodic_memory] Stats error: {e}")
            return {}
        finally:
            conn.close()


# Singleton
_episodic_memory: Optional[EpisodicMemory] = None


def get_episodic_memory() -> EpisodicMemory:
    global _episodic_memory
    if _episodic_memory is None:
        _episodic_memory = EpisodicMemory()
    return _episodic_memory


# =============================================================================
# CLI / TESTING
# =============================================================================

if __name__ == "__main__":
    em = get_episodic_memory()
    
    print("=" * 60)
    print("EPISODIC MEMORY TEST")
    print("=" * 60)
    
    # Record a test episode
    print("\n📝 Recording test episode...")
    episode = em.record_episode(
        identity_id="test_user_123",
        channel="telegram",
        summary="User asked about PF1 pricing and availability. Provided quote for 3 units.",
        episode_type=EpisodeType.INQUIRY,
        key_topics=["PF1", "pricing", "quote"],
        entities_mentioned=["PF1", "ABC Manufacturing"],
        outcome="Quote provided, user said they'll discuss with team",
        emotional_valence=EmotionalValence.POSITIVE,
        importance=0.7,
    )
    print(f"  Created: {episode.id}")
    print(f"  {episode.format_for_display()}")
    
    # Retrieve
    print("\n🔍 Retrieving recent episodes...")
    recent = em.retrieve_recent("test_user_123", limit=3)
    for ep in recent:
        print(f"  • {ep.format_for_prompt()}")
    
    # Stats
    print("\n📊 Stats:")
    stats = em.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    # Patterns
    print("\n📈 Patterns:")
    patterns = em.get_conversation_patterns("test_user_123")
    print(f"  Most active day: {patterns.get('most_active_day')}")
    print(f"  Most active time: {patterns.get('most_active_time')}")
    
    print("\n" + "=" * 60)
