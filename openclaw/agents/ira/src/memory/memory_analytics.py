#!/usr/bin/env python3
"""
MEMORY ANALYTICS - Track, Decay, Search, and Export IRA's Knowledge
====================================================================

Features:
1. Analytics Dashboard - What does IRA remember most?
2. Memory Decay - Old unused memories fade over time
3. Memory Search - Find what IRA knows about any topic
4. Backup/Restore - Export and import all learned knowledge

Usage:
    from memory_analytics import (
        get_memory_analytics,
        search_memories,
        export_all_knowledge,
        import_knowledge,
        apply_memory_decay
    )
    
    # Search
    results = search_memories("PF1 machine")
    
    # Analytics
    stats = get_memory_analytics()
    
    # Export
    export_all_knowledge("/path/to/backup.json")
    
    # Decay
    decayed = apply_memory_decay(days_threshold=90)
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)
import sqlite3
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Paths
SKILL_DIR = Path(__file__).parent
BRAIN_DIR = SKILL_DIR.parent / "brain"
DATA_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "crm"
ANALYTICS_DB = DATA_DIR / "memory_analytics.db"

# Add brain to path for feedback_learner
import sys
sys.path.insert(0, str(BRAIN_DIR))


@dataclass
class MemoryStats:
    """Statistics about IRA's memory."""
    total_memories: int = 0
    active_memories: int = 0
    decayed_memories: int = 0
    total_uses: int = 0
    
    # By type
    by_type: Dict[str, int] = field(default_factory=dict)
    
    # By source
    by_channel: Dict[str, int] = field(default_factory=dict)
    
    # Top entities
    top_entities: List[Tuple[str, int]] = field(default_factory=list)
    top_topics: List[Tuple[str, int]] = field(default_factory=list)
    
    # Usage patterns
    most_used: List[Dict] = field(default_factory=list)
    recently_added: List[Dict] = field(default_factory=list)
    never_used: List[Dict] = field(default_factory=list)
    
    # Health
    avg_confidence: float = 0.0
    decay_candidates: int = 0  # Memories that might be decayed soon
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass 
class SearchResult:
    """A memory search result."""
    source: str  # "conversation", "persistent", "learned", "entity"
    text: str
    relevance: float
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)


class MemoryAnalytics:
    """
    Analytics engine for IRA's memory systems.
    
    Aggregates data from:
    - ConversationState (memory_service.py)
    - PersistentMemory (persistent_memory.py)
    - LearnedCorrections (feedback_learner.py)
    """
    
    def __init__(self):
        self._init_analytics_db()
        self._pg_conn = None
    
    def _get_sqlite_conn(self, db_path: str = None) -> sqlite3.Connection:
        """Get SQLite connection with WAL mode enabled."""
        path = db_path or str(ANALYTICS_DB)
        conn = sqlite3.connect(path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn
    
    def _init_analytics_db(self) -> None:
        """Initialize local analytics tracking database."""
        ANALYTICS_DB.parent.mkdir(parents=True, exist_ok=True)
        
        with self._get_sqlite_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_type TEXT,
                    memory_id TEXT,
                    action TEXT,
                    query TEXT,
                    timestamp TEXT,
                    channel TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decay_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_type TEXT,
                    memory_id TEXT,
                    old_confidence REAL,
                    new_confidence REAL,
                    reason TEXT,
                    timestamp TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS topic_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    memory_type TEXT,
                    memory_id TEXT,
                    weight REAL DEFAULT 1.0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_topic ON topic_index(topic)
            """)
            conn.commit()
    
    def _get_pg_conn(self):
        """Get PostgreSQL connection for persistent memory."""
        if self._pg_conn is None:
            try:
                import psycopg2
                db_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
                if db_url:
                    self._pg_conn = psycopg2.connect(db_url)
            except Exception as e:
                logger.warning("Postgres not available: %s", e)
        return self._pg_conn
    
    def get_stats(self) -> MemoryStats:
        """
        Get comprehensive memory statistics.
        
        Aggregates across all memory sources.
        """
        stats = MemoryStats()
        
        # 1. Conversation Memory Stats
        conv_stats = self._get_conversation_stats()
        
        # 2. Mem0 Stats (Primary AI Memory)
        mem0_stats = self._get_mem0_stats()
        
        # 3. Persistent Memory Stats (PostgreSQL - Legacy)
        persist_stats = self._get_persistent_stats()
        
        # 4. Learned Corrections Stats (SQLite)
        learned_stats = self._get_learned_stats()
        
        # Aggregate
        stats.total_memories = (
            conv_stats.get("total", 0) +
            mem0_stats.get("total", 0) +
            persist_stats.get("total", 0) +
            learned_stats.get("total", 0)
        )
        stats.active_memories = (
            mem0_stats.get("total", 0) +
            persist_stats.get("active", 0) +
            learned_stats.get("active", 0)
        )
        stats.total_uses = (
            persist_stats.get("uses", 0) +
            learned_stats.get("uses", 0)
        )
        
        # By type
        stats.by_type = {
            "conversation_context": conv_stats.get("total", 0),
            "mem0_memory": mem0_stats.get("total", 0),
            "persistent_memory": persist_stats.get("total", 0),
            "learned_correction": learned_stats.get("total", 0),
            **persist_stats.get("by_type", {}),
            **learned_stats.get("by_type", {})
        }
        
        # By channel
        stats.by_channel = {
            **persist_stats.get("by_channel", {}),
            **conv_stats.get("by_channel", {})
        }
        
        # Top entities and topics
        stats.top_entities = self._extract_top_entities()
        stats.top_topics = self._extract_top_topics()
        
        # Most/least used
        stats.most_used = persist_stats.get("most_used", [])
        stats.recently_added = persist_stats.get("recent", [])
        stats.never_used = persist_stats.get("never_used", [])
        
        # Health metrics
        stats.avg_confidence = persist_stats.get("avg_confidence", 0.0)
        stats.decay_candidates = self._count_decay_candidates()
        
        return stats
    
    def _get_conversation_stats(self) -> Dict:
        """Get stats from conversation memory (file-based)."""
        state_dir = SKILL_DIR / "state"
        if not state_dir.exists():
            return {"total": 0, "by_channel": {}}
        
        total = 0
        by_channel = defaultdict(int)
        
        for state_file in state_dir.glob("*.json"):
            try:
                data = json.loads(state_file.read_text())
                msg_count = len(data.get("recent_messages", []))
                total += msg_count
                
                channel = data.get("channel", "unknown")
                by_channel[channel] += msg_count
            except Exception:
                pass
        
        return {
            "total": total,
            "by_channel": dict(by_channel)
        }
    
    def _get_mem0_stats(self) -> Dict:
        """Get stats from Mem0 AI memory."""
        try:
            try:
                from mem0_memory import get_mem0_service
            except ImportError:
                from .mem0_memory import get_mem0_service
            
            mem0 = get_mem0_service()
            
            # Get total memories - this requires iterating users
            # For now, return minimal stats
            return {
                "total": 0,  # Would need to aggregate across users
                "status": "connected"
            }
        except Exception as e:
            return {"total": 0, "status": f"unavailable: {e}"}
    
    def _get_persistent_stats(self) -> Dict:
        """Get stats from PostgreSQL persistent memory."""
        conn = self._get_pg_conn()
        if not conn:
            return {"total": 0, "active": 0, "uses": 0}
        
        stats = {"by_type": {}, "by_channel": {}}
        
        try:
            cursor = conn.cursor()
            
            # Total and active
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active,
                    SUM(use_count) as uses,
                    AVG(confidence) as avg_conf
                FROM ira_memory.user_memories
            """)
            row = cursor.fetchone()
            if row:
                stats["total"] = row[0] or 0
                stats["active"] = row[1] or 0
                stats["uses"] = row[2] or 0
                stats["avg_confidence"] = float(row[3] or 0)
            
            # By type
            cursor.execute("""
                SELECT memory_type, COUNT(*) 
                FROM ira_memory.user_memories 
                GROUP BY memory_type
            """)
            for row in cursor:
                stats["by_type"][row[0]] = row[1]
            
            # By channel
            cursor.execute("""
                SELECT source_channel, COUNT(*) 
                FROM ira_memory.user_memories 
                WHERE source_channel IS NOT NULL
                GROUP BY source_channel
            """)
            for row in cursor:
                stats["by_channel"][row[0]] = row[1]
            
            # Most used
            cursor.execute("""
                SELECT memory_text, use_count, memory_type
                FROM ira_memory.user_memories
                WHERE is_active = TRUE
                ORDER BY use_count DESC
                LIMIT 5
            """)
            stats["most_used"] = [
                {"text": r[0][:100], "uses": r[1], "type": r[2]}
                for r in cursor
            ]
            
            # Recent
            cursor.execute("""
                SELECT memory_text, created_at, memory_type
                FROM ira_memory.user_memories
                WHERE is_active = TRUE
                ORDER BY created_at DESC
                LIMIT 5
            """)
            stats["recent"] = [
                {"text": r[0][:100], "created": str(r[1]), "type": r[2]}
                for r in cursor
            ]
            
            # Never used
            cursor.execute("""
                SELECT memory_text, created_at, memory_type
                FROM ira_memory.user_memories
                WHERE is_active = TRUE AND use_count = 0
                ORDER BY created_at ASC
                LIMIT 5
            """)
            stats["never_used"] = [
                {"text": r[0][:100], "created": str(r[1]), "type": r[2]}
                for r in cursor
            ]
            
        except Exception as e:
            logger.error("Persistent stats error: %s", e)
        
        return stats
    
    def _get_learned_stats(self) -> Dict:
        """Get stats from learned corrections (SQLite)."""
        try:
            from feedback_learner import LearningDatabase
            db = LearningDatabase()
            stats = db.get_stats()
            
            return {
                "total": stats.get("total_corrections", 0),
                "active": stats.get("high_confidence", 0),
                "uses": stats.get("total_uses", 0),
                "by_type": {"learned_correction": stats.get("total_corrections", 0)}
            }
        except ImportError:
            return {"total": 0, "active": 0, "uses": 0}
        except Exception as e:
            logger.error("Learned stats error: %s", e)
            return {"total": 0, "active": 0, "uses": 0}
    
    def _extract_top_entities(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Extract most mentioned entities across all memories."""
        entity_counts = Counter()
        
        # From persistent memory
        conn = self._get_pg_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT memory_text FROM ira_memory.user_memories
                    WHERE is_active = TRUE
                """)
                for row in cursor:
                    # Extract machine models
                    models = re.findall(
                        r'(PF1[-\s]?[A-Z][-\s]?\d+[-\s]?\d*|AM[-\s]?[MVP]\d*|ATF[-\s]?\d+)',
                        row[0], re.IGNORECASE
                    )
                    entity_counts.update(m.upper() for m in models)
                    
                    # Extract companies
                    companies = re.findall(
                        r'(?:at|from|with)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+(?:Corp|Inc|GmbH|Ltd)?',
                        row[0]
                    )
                    entity_counts.update(companies)
            except Exception:
                pass
        
        # From learned corrections
        try:
            learned_db = DATA_DIR / "learned_knowledge.db"
            if learned_db.exists():
                with self._get_sqlite_conn(str(learned_db)) as lconn:
                    cursor = lconn.execute("SELECT keywords FROM corrections")
                    for row in cursor:
                        if row[0]:
                            keywords = json.loads(row[0])
                            entity_counts.update(keywords)
        except Exception:
            pass
        
        return entity_counts.most_common(limit)
    
    def _extract_top_topics(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Extract most common topics across memories."""
        topic_keywords = [
            "price", "specification", "delivery", "warranty", "installation",
            "thermoforming", "packaging", "automotive", "medical", "food",
            "forming", "cutting", "heating", "cooling", "maintenance",
            "quote", "order", "lead time", "technical", "support"
        ]
        
        topic_counts = Counter()
        
        # Scan persistent memories
        conn = self._get_pg_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT memory_text FROM ira_memory.user_memories
                    WHERE is_active = TRUE
                """)
                for row in cursor:
                    text_lower = row[0].lower()
                    for topic in topic_keywords:
                        if topic in text_lower:
                            topic_counts[topic] += 1
            except Exception:
                pass
        
        return topic_counts.most_common(limit)
    
    def _count_decay_candidates(self, days: int = 90) -> int:
        """Count memories that are candidates for decay."""
        threshold = datetime.now() - timedelta(days=days)
        count = 0
        
        conn = self._get_pg_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM ira_memory.user_memories
                    WHERE is_active = TRUE 
                    AND use_count = 0
                    AND created_at < %s
                """, (threshold,))
                row = cursor.fetchone()
                count += row[0] if row else 0
            except Exception:
                pass
        
        return count
    
    def search(
        self,
        query: str,
        limit: int = 20,
        sources: List[str] = None
    ) -> List[SearchResult]:
        """
        Search across all memory sources.
        
        Args:
            query: Search query
            limit: Max results
            sources: Filter to specific sources ("conversation", "persistent", "learned")
        
        Returns:
            List of SearchResult objects
        """
        sources = sources or ["conversation", "persistent", "learned"]
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # 1. Search conversation memories
        if "conversation" in sources:
            conv_results = self._search_conversation(query_lower, query_words, limit)
            results.extend(conv_results)
        
        # 2. Search persistent memories
        if "persistent" in sources:
            persist_results = self._search_persistent(query_lower, query_words, limit)
            results.extend(persist_results)
        
        # 3. Search learned corrections
        if "learned" in sources:
            learned_results = self._search_learned(query_lower, query_words, limit)
            results.extend(learned_results)
        
        # Sort by relevance and limit
        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:limit]
    
    def _search_conversation(
        self,
        query_lower: str,
        query_words: set,
        limit: int
    ) -> List[SearchResult]:
        """Search conversation state files."""
        results = []
        state_dir = SKILL_DIR / "state"
        
        if not state_dir.exists():
            return results
        
        for state_file in state_dir.glob("*.json"):
            try:
                data = json.loads(state_file.read_text())
                
                # Search recent messages
                for msg in data.get("recent_messages", []):
                    content = msg.get("content", "").lower()
                    relevance = self._calculate_relevance(content, query_lower, query_words)
                    
                    if relevance > 0.1:
                        results.append(SearchResult(
                            source="conversation",
                            text=msg.get("content", "")[:200],
                            relevance=relevance,
                            metadata={
                                "channel": data.get("channel"),
                                "role": msg.get("role"),
                                "identifier": data.get("identifier", "")[:20]
                            }
                        ))
                
                # Search key entities
                entities = data.get("key_entities", {})
                for key, value in entities.items():
                    if isinstance(value, list):
                        value_str = ", ".join(str(v) for v in value)
                    else:
                        value_str = str(value)
                    
                    relevance = self._calculate_relevance(
                        f"{key}: {value_str}".lower(),
                        query_lower,
                        query_words
                    )
                    
                    if relevance > 0.1:
                        results.append(SearchResult(
                            source="conversation",
                            text=f"{key}: {value_str}",
                            relevance=relevance,
                            metadata={
                                "type": "key_entity",
                                "channel": data.get("channel")
                            }
                        ))
            except Exception:
                pass
        
        return results
    
    def _search_persistent(
        self,
        query_lower: str,
        query_words: set,
        limit: int
    ) -> List[SearchResult]:
        """Search PostgreSQL persistent memories."""
        results = []
        conn = self._get_pg_conn()
        
        if not conn:
            return results
        
        try:
            cursor = conn.cursor()
            
            # Use ILIKE for case-insensitive search
            search_pattern = f"%{query_lower}%"
            cursor.execute("""
                SELECT memory_text, memory_type, confidence, use_count, created_at, identity_id
                FROM ira_memory.user_memories
                WHERE is_active = TRUE 
                AND LOWER(memory_text) LIKE %s
                ORDER BY use_count DESC, confidence DESC
                LIMIT %s
            """, (search_pattern, limit * 2))
            
            for row in cursor:
                text = row[0]
                relevance = self._calculate_relevance(text.lower(), query_lower, query_words)
                
                # Boost by use count and confidence
                relevance *= (1 + row[3] * 0.1)  # use_count boost
                relevance *= row[2]  # confidence
                
                results.append(SearchResult(
                    source="persistent",
                    text=text[:300],
                    relevance=min(relevance, 1.0),
                    metadata={
                        "type": row[1],
                        "confidence": row[2],
                        "uses": row[3],
                        "created": str(row[4]) if row[4] else None,
                        "identity": row[5][:20] if row[5] else None
                    }
                ))
            
            # Also search entity memories
            cursor.execute("""
                SELECT memory_text, entity_name, entity_type, confidence
                FROM ira_memory.entity_memories
                WHERE is_active = TRUE
                AND (LOWER(memory_text) LIKE %s OR LOWER(entity_name) LIKE %s)
                LIMIT %s
            """, (search_pattern, search_pattern, limit))
            
            for row in cursor:
                text = f"{row[1]} ({row[2]}): {row[0]}"
                relevance = self._calculate_relevance(text.lower(), query_lower, query_words)
                
                results.append(SearchResult(
                    source="entity",
                    text=text[:300],
                    relevance=min(relevance * 1.2, 1.0),  # Slight boost for entity
                    metadata={
                        "entity_name": row[1],
                        "entity_type": row[2],
                        "confidence": row[3]
                    }
                ))
                
        except Exception as e:
            logger.error("Persistent search error: %s", e)
        
        return results
    
    def _search_learned(
        self,
        query_lower: str,
        query_words: set,
        limit: int
    ) -> List[SearchResult]:
        """Search learned corrections."""
        results = []
        
        try:
            from feedback_learner import LearningDatabase
            db = LearningDatabase()
            corrections = db.find_relevant_corrections(query_lower, limit=limit)
            
            for corr in corrections:
                text = f"Learned: {corr.correct_info}"
                if corr.wrong_info:
                    text = f"Correction: '{corr.wrong_info}' → '{corr.correct_info}'"
                
                relevance = self._calculate_relevance(
                    text.lower(),
                    query_lower,
                    query_words
                )
                
                # Boost by confidence
                if corr.confidence.value == "high":
                    relevance *= 1.3
                elif corr.confidence.value == "medium":
                    relevance *= 1.1
                
                results.append(SearchResult(
                    source="learned",
                    text=text[:300],
                    relevance=min(relevance, 1.0),
                    metadata={
                        "type": corr.correction_type.value,
                        "confidence": corr.confidence.value,
                        "uses": corr.use_count,
                        "keywords": corr.keywords
                    }
                ))
        except ImportError:
            pass
        except Exception as e:
            logger.error("Learned search error: %s", e)
        
        return results
    
    def _calculate_relevance(
        self,
        text: str,
        query_lower: str,
        query_words: set
    ) -> float:
        """Calculate relevance score."""
        score = 0.0
        
        # Exact match
        if query_lower in text:
            score += 0.5
        
        # Word matches
        text_words = set(text.split())
        matching_words = query_words & text_words
        if query_words:
            word_match_ratio = len(matching_words) / len(query_words)
            score += word_match_ratio * 0.5
        
        return min(score, 1.0)
    
    def apply_decay(
        self,
        days_threshold: int = 90,
        decay_factor: float = 0.1,
        min_confidence: float = 0.2,
        dry_run: bool = False
    ) -> Dict:
        """
        Apply decay to old unused memories.
        
        Args:
            days_threshold: Memories unused for this many days get decayed
            decay_factor: How much to reduce confidence (0.1 = 10% reduction)
            min_confidence: Minimum confidence before deactivation
            dry_run: If True, just report what would happen
        
        Returns:
            Summary of decay actions
        """
        summary = {
            "decayed": 0,
            "deactivated": 0,
            "preserved": 0,
            "details": []
        }
        
        threshold = datetime.now() - timedelta(days=days_threshold)
        
        # Decay persistent memories
        conn = self._get_pg_conn()
        if conn:
            try:
                cursor = conn.cursor()
                
                # Find decay candidates
                cursor.execute("""
                    SELECT id, memory_text, confidence, use_count, created_at, last_used_at
                    FROM ira_memory.user_memories
                    WHERE is_active = TRUE
                    AND use_count = 0
                    AND created_at < %s
                """, (threshold,))
                
                for row in cursor:
                    mem_id, text, conf, uses, created, last_used = row
                    new_conf = max(conf - decay_factor, 0)
                    
                    if new_conf < min_confidence:
                        # Deactivate
                        if not dry_run:
                            cursor.execute("""
                                UPDATE ira_memory.user_memories
                                SET is_active = FALSE, confidence = %s
                                WHERE id = %s
                            """, (new_conf, mem_id))
                        summary["deactivated"] += 1
                        action = "deactivated"
                    else:
                        # Decay confidence
                        if not dry_run:
                            cursor.execute("""
                                UPDATE ira_memory.user_memories
                                SET confidence = %s
                                WHERE id = %s
                            """, (new_conf, mem_id))
                        summary["decayed"] += 1
                        action = "decayed"
                    
                    summary["details"].append({
                        "id": mem_id,
                        "text": text[:50],
                        "old_confidence": conf,
                        "new_confidence": new_conf,
                        "action": action
                    })
                    
                    # Log decay
                    self._log_decay(
                        "persistent",
                        str(mem_id),
                        conf,
                        new_conf,
                        f"unused for {days_threshold}+ days"
                    )
                
                if not dry_run:
                    conn.commit()
                    
            except Exception as e:
                logger.error("Decay error: %s", e)
        
        # Count preserved (used memories)
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM ira_memory.user_memories
                    WHERE is_active = TRUE AND use_count > 0
                """)
                row = cursor.fetchone()
                summary["preserved"] = row[0] if row else 0
            except Exception:
                pass
        
        return summary
    
    def _log_decay(
        self,
        memory_type: str,
        memory_id: str,
        old_conf: float,
        new_conf: float,
        reason: str
    ) -> None:
        """Log a decay action."""
        with self._get_sqlite_conn() as conn:
            conn.execute("""
                INSERT INTO decay_log (memory_type, memory_id, old_confidence, new_confidence, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (memory_type, memory_id, old_conf, new_conf, reason, datetime.now(timezone.utc).isoformat()))
            conn.commit()
    
    def export_all(self, output_path: str) -> Dict:
        """
        Export all memory to a JSON file.
        
        Args:
            output_path: Path to output JSON file
        
        Returns:
            Summary of exported data
        """
        export_data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
            "conversation_states": [],
            "persistent_memories": [],
            "entity_memories": [],
            "learned_corrections": [],
            "identity_links": {}
        }
        
        summary = {"conversation": 0, "persistent": 0, "entity": 0, "learned": 0}
        
        # 1. Export conversation states
        state_dir = SKILL_DIR / "state"
        if state_dir.exists():
            for state_file in state_dir.glob("*.json"):
                try:
                    data = json.loads(state_file.read_text())
                    export_data["conversation_states"].append(data)
                    summary["conversation"] += 1
                except Exception:
                    pass
        
        # Export identity links
        links_file = state_dir / "identity_links.json"
        if links_file.exists():
            try:
                export_data["identity_links"] = json.loads(links_file.read_text())
            except Exception:
                pass
        
        # 2. Export persistent memories (PostgreSQL)
        conn = self._get_pg_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, identity_id, memory_text, memory_type, source_channel,
                           confidence, is_active, created_at, use_count
                    FROM ira_memory.user_memories
                """)
                for row in cursor:
                    export_data["persistent_memories"].append({
                        "id": row[0],
                        "identity_id": row[1],
                        "memory_text": row[2],
                        "memory_type": row[3],
                        "source_channel": row[4],
                        "confidence": row[5],
                        "is_active": row[6],
                        "created_at": str(row[7]) if row[7] else None,
                        "use_count": row[8]
                    })
                    summary["persistent"] += 1
                
                # Entity memories
                cursor.execute("""
                    SELECT id, entity_type, entity_name, memory_text, confidence, is_active
                    FROM ira_memory.entity_memories
                """)
                for row in cursor:
                    export_data["entity_memories"].append({
                        "id": row[0],
                        "entity_type": row[1],
                        "entity_name": row[2],
                        "memory_text": row[3],
                        "confidence": row[4],
                        "is_active": row[5]
                    })
                    summary["entity"] += 1
                    
            except Exception as e:
                logger.error("Export persistent error: %s", e)
        
        # 3. Export learned corrections (SQLite)
        try:
            learned_db = DATA_DIR / "learned_knowledge.db"
            if learned_db.exists():
                with self._get_sqlite_conn(str(learned_db)) as lconn:
                    cursor = lconn.execute("""
                        SELECT id, correction_type, wrong_info, correct_info, context,
                               source, confidence, confirmations, created_at, keywords
                        FROM corrections
                    """)
                    for row in cursor:
                        export_data["learned_corrections"].append({
                            "id": row[0],
                            "correction_type": row[1],
                            "wrong_info": row[2],
                            "correct_info": row[3],
                            "context": json.loads(row[4]) if row[4] else {},
                            "source": row[5],
                            "confidence": row[6],
                            "confirmations": row[7],
                            "created_at": row[8],
                            "keywords": json.loads(row[9]) if row[9] else []
                        })
                        summary["learned"] += 1
        except Exception as e:
            logger.error("Export learned error: %s", e)
        
        # Write to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(export_data, indent=2, default=str))
        
        logger.info("Exported to %s", output_path)
        return summary
    
    def import_backup(self, input_path: str, merge: bool = True) -> Dict:
        """
        Import memory from a backup file.
        
        Args:
            input_path: Path to backup JSON file
            merge: If True, merge with existing. If False, replace.
        
        Returns:
            Summary of imported data
        """
        summary = {"conversation": 0, "persistent": 0, "entity": 0, "learned": 0, "skipped": 0}
        
        try:
            data = json.loads(Path(input_path).read_text())
        except Exception as e:
            logger.error("Import error: %s", e)
            return summary
        
        # 1. Import conversation states
        state_dir = SKILL_DIR / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        
        for state in data.get("conversation_states", []):
            try:
                channel = state.get("channel", "unknown")
                identifier = state.get("identifier", "unknown")
                filename = f"{channel}_{identifier}.json".replace(":", "_")
                state_file = state_dir / filename
                
                if state_file.exists() and merge:
                    # Merge: keep existing, add new messages
                    existing = json.loads(state_file.read_text())
                    existing_msgs = {m.get("content", "") for m in existing.get("recent_messages", [])}
                    for msg in state.get("recent_messages", []):
                        if msg.get("content", "") not in existing_msgs:
                            existing.setdefault("recent_messages", []).append(msg)
                    state_file.write_text(json.dumps(existing, indent=2))
                else:
                    state_file.write_text(json.dumps(state, indent=2))
                
                summary["conversation"] += 1
            except Exception:
                summary["skipped"] += 1
        
        # Import identity links
        if data.get("identity_links"):
            links_file = state_dir / "identity_links.json"
            links_file.write_text(json.dumps(data["identity_links"], indent=2))
        
        # 2. Import persistent memories (PostgreSQL)
        conn = self._get_pg_conn()
        if conn:
            try:
                cursor = conn.cursor()
                
                for mem in data.get("persistent_memories", []):
                    if merge:
                        # Check if exists
                        cursor.execute("""
                            SELECT id FROM ira_memory.user_memories
                            WHERE identity_id = %s AND memory_text = %s
                        """, (mem.get("identity_id"), mem.get("memory_text")))
                        if cursor.fetchone():
                            summary["skipped"] += 1
                            continue
                    
                    cursor.execute("""
                        INSERT INTO ira_memory.user_memories
                        (identity_id, memory_text, memory_type, source_channel, confidence, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        mem.get("identity_id"),
                        mem.get("memory_text"),
                        mem.get("memory_type", "fact"),
                        mem.get("source_channel"),
                        mem.get("confidence", 1.0),
                        mem.get("is_active", True)
                    ))
                    summary["persistent"] += 1
                
                conn.commit()
            except Exception as e:
                logger.error("Import persistent error: %s", e)
        
        # 3. Import learned corrections
        try:
            from feedback_learner import LearnedCorrection, LearningDatabase, CorrectionType, ConfidenceLevel
            db = LearningDatabase()
            
            for corr in data.get("learned_corrections", []):
                try:
                    correction = LearnedCorrection(
                        id=corr.get("id"),
                        correction_type=CorrectionType(corr.get("correction_type", "factual")),
                        wrong_info=corr.get("wrong_info", ""),
                        correct_info=corr.get("correct_info", ""),
                        context=corr.get("context", {}),
                        source=corr.get("source", "import"),
                        confidence=ConfidenceLevel(corr.get("confidence", "low")),
                        confirmations=corr.get("confirmations", 1),
                        created_at=corr.get("created_at", datetime.now(timezone.utc).isoformat()),
                        keywords=corr.get("keywords", [])
                    )
                    db.save_correction(correction)
                    summary["learned"] += 1
                except Exception:
                    summary["skipped"] += 1
        except ImportError:
            pass
        
        logger.info("Imported: %s", summary)
        return summary


# Singleton
_analytics: Optional[MemoryAnalytics] = None


def get_analytics() -> MemoryAnalytics:
    """Get analytics singleton."""
    global _analytics
    if _analytics is None:
        _analytics = MemoryAnalytics()
    return _analytics


# Convenience functions
def get_memory_analytics() -> Dict:
    """Get memory statistics as a dict."""
    return get_analytics().get_stats().to_dict()


def search_memories(query: str, limit: int = 20) -> List[Dict]:
    """Search all memory sources."""
    results = get_analytics().search(query, limit=limit)
    return [r.to_dict() for r in results]


def apply_memory_decay(days: int = 90, dry_run: bool = False) -> Dict:
    """Apply decay to old unused memories."""
    return get_analytics().apply_decay(days_threshold=days, dry_run=dry_run)


def export_all_knowledge(output_path: str) -> Dict:
    """Export all memory to a file."""
    return get_analytics().export_all(output_path)


def import_knowledge(input_path: str, merge: bool = True) -> Dict:
    """Import memory from a backup file."""
    return get_analytics().import_backup(input_path, merge=merge)


def format_stats_for_telegram() -> str:
    """Format stats for Telegram display."""
    stats = get_memory_analytics()
    
    lines = [
        "📊 **IRA MEMORY ANALYTICS**\n",
        f"**Total Memories:** {stats.get('total_memories', 0)}",
        f"**Active:** {stats.get('active_memories', 0)}",
        f"**Total Uses:** {stats.get('total_uses', 0)}",
        f"**Decay Candidates:** {stats.get('decay_candidates', 0)}",
        "",
        "**By Type:**"
    ]
    
    for mtype, count in stats.get("by_type", {}).items():
        lines.append(f"  • {mtype}: {count}")
    
    lines.append("")
    lines.append("**Top Entities:**")
    for entity, count in stats.get("top_entities", [])[:5]:
        lines.append(f"  • {entity}: {count} mentions")
    
    lines.append("")
    lines.append("**Top Topics:**")
    for topic, count in stats.get("top_topics", [])[:5]:
        lines.append(f"  • {topic}: {count}")
    
    if stats.get("most_used"):
        lines.append("")
        lines.append("**Most Used Memories:**")
        for mem in stats.get("most_used", [])[:3]:
            lines.append(f"  • {mem['text'][:50]}... ({mem['uses']} uses)")
    
    return "\n".join(lines)


def format_search_for_telegram(query: str, results: List[Dict]) -> str:
    """Format search results for Telegram."""
    if not results:
        return f"🔍 No memories found for: **{query}**"
    
    lines = [f"🔍 **Memory Search: {query}**\n"]
    
    for i, r in enumerate(results[:10], 1):
        source_emoji = {
            "conversation": "💬",
            "persistent": "🧠",
            "learned": "📚",
            "entity": "🏢"
        }.get(r["source"], "📌")
        
        relevance_pct = int(r["relevance"] * 100)
        lines.append(f"{source_emoji} [{relevance_pct}%] {r['text'][:100]}")
        
        if r.get("metadata"):
            meta = r["metadata"]
            meta_parts = []
            if meta.get("type"):
                meta_parts.append(f"type:{meta['type']}")
            if meta.get("uses"):
                meta_parts.append(f"uses:{meta['uses']}")
            if meta_parts:
                lines.append(f"   _({', '.join(meta_parts)})_")
        
        lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    print("Testing Memory Analytics...")
    
    # Test stats
    stats = get_memory_analytics()
    print(f"\nStats: {json.dumps(stats, indent=2)}")
    
    # Test search
    results = search_memories("PF1")
    print(f"\nSearch 'PF1': {len(results)} results")
    
    # Test formatted output
    print("\n" + format_stats_for_telegram())
    
    print("\n✅ Memory Analytics working")
