#!/usr/bin/env python3
"""
MEMORY CONSOLIDATOR - Learn Generalized Knowledge from Conversational History

╔════════════════════════════════════════════════════════════════════════════╗
║  This module enables IRA to learn from its conversational experiences.     ║
║                                                                            ║
║  Like human memory consolidation during sleep, this system:                ║
║  1. Reviews recent episodic memories (conversations)                       ║
║  2. Extracts recurring patterns across multiple interactions               ║
║  3. Synthesizes generalized knowledge (facts, procedures, relationships)   ║
║  4. Stores the new knowledge for future retrieval                          ║
║                                                                            ║
║  Example outputs:                                                          ║
║  - Semantic Fact: "Automotive dashboards are a common PF1 application"     ║
║  - Procedural Memory: "handle_shipping_query" workflow                     ║
║  - Knowledge Graph: "PF1-Series" --used_for--> "Automotive Dashboards"     ║
╚════════════════════════════════════════════════════════════════════════════╝

Usage:
    from memory_consolidator import MemoryConsolidator, run_memory_consolidation
    
    consolidator = MemoryConsolidator()
    result = consolidator.consolidate_episodic_memories(days_to_review=7)
"""

import json
import logging
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

MEMORY_DIR = Path(__file__).parent
SKILLS_DIR = MEMORY_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent
sys.path.insert(0, str(AGENT_DIR))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ExtractedPattern:
    """A pattern extracted from multiple conversations."""
    pattern_type: str               # topic, intent, workflow, entity_usage
    description: str                # Human-readable pattern description
    evidence_count: int             # How many conversations support this
    example_queries: List[str]      # Sample queries that showed this pattern
    confidence: float               # Confidence score (0-1)
    entities_involved: List[str]    # Entities mentioned in pattern
    first_seen: datetime
    last_seen: datetime
    

@dataclass
class ConsolidatedKnowledge:
    """Knowledge synthesized from patterns."""
    knowledge_type: str             # semantic_fact, procedural, relationship
    content: str                    # The actual knowledge
    source_pattern: str             # Pattern this was derived from
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class ConsolidationResult:
    """Result of a memory consolidation run."""
    episodes_reviewed: int = 0
    patterns_identified: int = 0
    semantic_facts_created: int = 0
    procedures_created: int = 0
    relationships_created: int = 0
    knowledge_reinforced: int = 0
    patterns_pending_approval: int = 0
    duration_seconds: float = 0.0
    patterns: List[Dict] = field(default_factory=list)
    new_knowledge: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "episodes_reviewed": self.episodes_reviewed,
            "patterns_identified": self.patterns_identified,
            "semantic_facts_created": self.semantic_facts_created,
            "procedures_created": self.procedures_created,
            "relationships_created": self.relationships_created,
            "knowledge_reinforced": self.knowledge_reinforced,
            "patterns_pending_approval": self.patterns_pending_approval,
            "duration_seconds": round(self.duration_seconds, 2),
            "patterns": self.patterns,
            "new_knowledge": self.new_knowledge,
            "errors": self.errors,
        }


@dataclass
class PendingPattern:
    """A pattern awaiting approval before becoming knowledge."""
    id: str
    pattern_type: str
    description: str
    proposed_knowledge: str
    knowledge_type: str
    confidence: float
    evidence_count: int
    example_queries: List[str]
    entities_involved: List[str]
    created_at: str
    status: str = "pending"  # pending, approved, rejected
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "proposed_knowledge": self.proposed_knowledge,
            "knowledge_type": self.knowledge_type,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "example_queries": self.example_queries,
            "entities_involved": self.entities_involved,
            "created_at": self.created_at,
            "status": self.status,
            "reviewed_at": self.reviewed_at,
            "review_notes": self.review_notes,
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "PendingPattern":
        return cls(
            id=d.get("id", ""),
            pattern_type=d.get("pattern_type", ""),
            description=d.get("description", ""),
            proposed_knowledge=d.get("proposed_knowledge", ""),
            knowledge_type=d.get("knowledge_type", ""),
            confidence=d.get("confidence", 0.0),
            evidence_count=d.get("evidence_count", 0),
            example_queries=d.get("example_queries", []),
            entities_involved=d.get("entities_involved", []),
            created_at=d.get("created_at", ""),
            status=d.get("status", "pending"),
            reviewed_at=d.get("reviewed_at"),
            review_notes=d.get("review_notes"),
        )


@dataclass
class KnowledgeUsageStats:
    """Track how useful consolidated knowledge is."""
    knowledge_id: str
    content: str
    knowledge_type: str
    created_at: str
    times_retrieved: int = 0
    times_helpful: int = 0
    times_not_helpful: int = 0
    last_retrieved: Optional[str] = None
    
    @property
    def usefulness_score(self) -> float:
        """Calculate usefulness score (0-1)."""
        total = self.times_helpful + self.times_not_helpful
        if total == 0:
            return 0.5  # Neutral if no feedback
        return self.times_helpful / total
    
    def to_dict(self) -> Dict:
        return {
            "knowledge_id": self.knowledge_id,
            "content": self.content,
            "knowledge_type": self.knowledge_type,
            "created_at": self.created_at,
            "times_retrieved": self.times_retrieved,
            "times_helpful": self.times_helpful,
            "times_not_helpful": self.times_not_helpful,
            "last_retrieved": self.last_retrieved,
            "usefulness_score": self.usefulness_score,
        }


# =============================================================================
# MEMORY CONSOLIDATOR
# =============================================================================

class MemoryConsolidator:
    """
    Consolidates episodic memories into generalized knowledge.
    
    This is IRA's "learning engine" - it reviews past conversations
    and extracts patterns that become permanent knowledge.
    
    Features:
    - Pattern extraction from conversations
    - Knowledge synthesis (facts, procedures, relationships)
    - Pattern validation workflow (approve/reject before storing)
    - Quality scoring (track usefulness)
    - Export capabilities (CSV/Excel)
    """
    
    MIN_PATTERN_OCCURRENCES = 2    # Need at least N instances to form pattern
    MIN_CONFIDENCE = 0.6           # Minimum confidence to create knowledge
    AUTO_APPROVE_CONFIDENCE = 0.85 # Auto-approve patterns above this confidence
    
    # File paths
    AUDIT_FILE = PROJECT_ROOT / "data" / "knowledge" / "consolidation_log.json"
    PENDING_FILE = PROJECT_ROOT / "data" / "knowledge" / "pending_patterns.json"
    USAGE_STATS_FILE = PROJECT_ROOT / "data" / "knowledge" / "knowledge_usage_stats.json"
    EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
    
    def __init__(self, verbose: bool = False, require_approval: bool = False):
        """
        Initialize the MemoryConsolidator.
        
        Args:
            verbose: Enable verbose logging
            require_approval: If True, queue patterns for approval instead of auto-storing
        """
        self.verbose = verbose
        self.require_approval = require_approval
        self._openai = None
        self._mem0_storage = None
        self._memory_controller = None
        self._relationship_store = None
        self._procedural_store = None
        self._pending_patterns: Dict[str, PendingPattern] = {}
        self._usage_stats: Dict[str, KnowledgeUsageStats] = {}
        self._load_pending_patterns()
        self._load_usage_stats()
    
    def _log(self, msg: str):
        """Log if verbose mode."""
        if self.verbose:
            print(f"[MemoryConsolidator] {msg}")
        logger.info(msg)
    
    def _get_openai(self):
        """Get OpenAI client."""
        if self._openai is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                import openai
                self._openai = openai.OpenAI(api_key=api_key)
        return self._openai
    
    def _get_mem0_storage(self):
        """Get Mem0 storage service."""
        if self._mem0_storage is None:
            try:
                from .mem0_storage import get_mem0_storage
                self._mem0_storage = get_mem0_storage()
            except ImportError:
                from mem0_storage import get_mem0_storage
                self._mem0_storage = get_mem0_storage()
        return self._mem0_storage
    
    def _get_memory_controller(self):
        """Get memory controller for remember() function."""
        if self._memory_controller is None:
            try:
                from .memory_controller import get_memory_controller
                self._memory_controller = get_memory_controller()
            except ImportError:
                from memory_controller import get_memory_controller
                self._memory_controller = get_memory_controller()
        return self._memory_controller
    
    def _get_procedural_store(self):
        """Get procedural memory store."""
        if self._procedural_store is None:
            storage = self._get_mem0_storage()
            if storage:
                self._procedural_store = storage.procedures
        return self._procedural_store
    
    def _get_relationship_store(self):
        """Get relationship store."""
        if self._relationship_store is None:
            storage = self._get_mem0_storage()
            if storage:
                self._relationship_store = storage.relationships
        return self._relationship_store
    
    # =========================================================================
    # PENDING PATTERNS MANAGEMENT
    # =========================================================================
    
    def _load_pending_patterns(self):
        """Load pending patterns from file."""
        if self.PENDING_FILE.exists():
            try:
                data = json.loads(self.PENDING_FILE.read_text())
                self._pending_patterns = {
                    k: PendingPattern.from_dict(v) for k, v in data.items()
                }
            except (json.JSONDecodeError, IOError) as e:
                self._log(f"Error loading pending patterns: {e}")
                self._pending_patterns = {}
    
    def _save_pending_patterns(self):
        """Save pending patterns to file."""
        self.PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.to_dict() for k, v in self._pending_patterns.items()}
        self.PENDING_FILE.write_text(json.dumps(data, indent=2))
    
    def _queue_for_approval(self, pattern: ExtractedPattern, knowledge: ConsolidatedKnowledge) -> str:
        """Queue a pattern for human approval."""
        import hashlib
        
        pattern_id = hashlib.md5(
            f"{pattern.description}_{knowledge.content}".encode()
        ).hexdigest()[:12]
        
        pending = PendingPattern(
            id=pattern_id,
            pattern_type=pattern.pattern_type,
            description=pattern.description,
            proposed_knowledge=knowledge.content,
            knowledge_type=knowledge.knowledge_type,
            confidence=pattern.confidence,
            evidence_count=pattern.evidence_count,
            example_queries=pattern.example_queries[:5],
            entities_involved=pattern.entities_involved,
            created_at=datetime.now().isoformat(),
        )
        
        self._pending_patterns[pattern_id] = pending
        self._save_pending_patterns()
        
        return pattern_id
    
    def get_pending_patterns(self, status: str = "pending") -> List[PendingPattern]:
        """Get patterns awaiting approval."""
        return [p for p in self._pending_patterns.values() if p.status == status]
    
    def approve_pattern(self, pattern_id: str, notes: str = "") -> bool:
        """
        Approve a pending pattern and create the knowledge.
        
        Args:
            pattern_id: ID of the pattern to approve
            notes: Optional review notes
            
        Returns:
            True if approved and stored successfully
        """
        if pattern_id not in self._pending_patterns:
            self._log(f"Pattern {pattern_id} not found")
            return False
        
        pending = self._pending_patterns[pattern_id]
        
        # Create knowledge from pending pattern
        knowledge = ConsolidatedKnowledge(
            knowledge_type=pending.knowledge_type,
            content=pending.proposed_knowledge,
            source_pattern=pending.pattern_type,
            confidence=pending.confidence,
            metadata={
                "evidence_count": pending.evidence_count,
                "approved_at": datetime.now().isoformat(),
                "review_notes": notes,
            }
        )
        
        # Store the knowledge
        success = False
        if pending.knowledge_type == "semantic_fact":
            success = self._store_semantic_fact(knowledge)
        elif pending.knowledge_type == "procedural":
            knowledge.metadata["steps"] = pending.example_queries
            success = self._store_procedure(knowledge)
        elif pending.knowledge_type == "relationship":
            knowledge.metadata["entities"] = pending.entities_involved
            success = self._store_relationship(knowledge)
        
        if success:
            pending.status = "approved"
            pending.reviewed_at = datetime.now().isoformat()
            pending.review_notes = notes
            self._save_pending_patterns()
            
            # Track usage for this knowledge
            self._track_knowledge_created(knowledge, pattern_id)
            
            self._log(f"Approved pattern {pattern_id}: {pending.proposed_knowledge[:50]}...")
        
        return success
    
    def reject_pattern(self, pattern_id: str, reason: str = "") -> bool:
        """
        Reject a pending pattern.
        
        Args:
            pattern_id: ID of the pattern to reject
            reason: Reason for rejection
            
        Returns:
            True if rejected successfully
        """
        if pattern_id not in self._pending_patterns:
            self._log(f"Pattern {pattern_id} not found")
            return False
        
        pending = self._pending_patterns[pattern_id]
        pending.status = "rejected"
        pending.reviewed_at = datetime.now().isoformat()
        pending.review_notes = reason
        self._save_pending_patterns()
        
        self._log(f"Rejected pattern {pattern_id}: {reason}")
        return True
    
    def send_patterns_for_review(self) -> bool:
        """
        Send pending patterns to Rushabh via Telegram for review.
        
        Returns:
            True if notification sent successfully
        """
        pending = self.get_pending_patterns("pending")
        if not pending:
            self._log("No pending patterns to review")
            return False
        
        try:
            import requests
            
            telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            rushabh_chat_id = os.environ.get("RUSHABH_TELEGRAM_ID", "5700751574")
            
            if not telegram_token:
                self._log("Telegram token not configured")
                return False
            
            # Build message
            message = f"🧠 *Patterns Awaiting Review* ({len(pending)} items)\n\n"
            
            for i, p in enumerate(pending[:5], 1):
                message += f"*{i}. [{p.pattern_type}]* (confidence: {p.confidence:.0%})\n"
                message += f"   {p.description[:60]}...\n"
                message += f"   → {p.proposed_knowledge[:50]}...\n"
                message += f"   ID: `{p.id}`\n\n"
            
            if len(pending) > 5:
                message += f"_...and {len(pending) - 5} more_\n\n"
            
            message += "Reply with:\n"
            message += "• `/approve <id>` to approve\n"
            message += "• `/reject <id> <reason>` to reject\n"
            message += "• `/approve_all` to approve all\n"
            
            response = requests.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                json={
                    "chat_id": rushabh_chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
            
            return response.ok
            
        except Exception as e:
            self._log(f"Error sending patterns for review: {e}")
            return False
    
    # =========================================================================
    # QUALITY SCORING / USAGE TRACKING
    # =========================================================================
    
    def _load_usage_stats(self):
        """Load usage statistics from file."""
        if self.USAGE_STATS_FILE.exists():
            try:
                data = json.loads(self.USAGE_STATS_FILE.read_text())
                self._usage_stats = {}
                for k, v in data.items():
                    v.pop("usefulness_score", None)
                    self._usage_stats[k] = KnowledgeUsageStats(**v)
            except (json.JSONDecodeError, IOError, TypeError) as e:
                self._log(f"Error loading usage stats: {e}")
                self._usage_stats = {}
    
    def _save_usage_stats(self):
        """Save usage statistics to file."""
        self.USAGE_STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.to_dict() for k, v in self._usage_stats.items()}
        self.USAGE_STATS_FILE.write_text(json.dumps(data, indent=2))
    
    def _track_knowledge_created(self, knowledge: ConsolidatedKnowledge, knowledge_id: str):
        """Track a newly created piece of knowledge."""
        stats = KnowledgeUsageStats(
            knowledge_id=knowledge_id,
            content=knowledge.content,
            knowledge_type=knowledge.knowledge_type,
            created_at=datetime.now().isoformat(),
        )
        self._usage_stats[knowledge_id] = stats
        self._save_usage_stats()
    
    def record_knowledge_retrieval(self, knowledge_id: str, was_helpful: Optional[bool] = None):
        """
        Record that a piece of knowledge was retrieved.
        
        Args:
            knowledge_id: ID of the knowledge
            was_helpful: True if helpful, False if not, None if unknown
        """
        if knowledge_id not in self._usage_stats:
            return
        
        stats = self._usage_stats[knowledge_id]
        stats.times_retrieved += 1
        stats.last_retrieved = datetime.now().isoformat()
        
        if was_helpful is True:
            stats.times_helpful += 1
        elif was_helpful is False:
            stats.times_not_helpful += 1
        
        self._save_usage_stats()
    
    def get_quality_report(self) -> Dict[str, Any]:
        """
        Get a report on knowledge quality/usefulness.
        
        Returns:
            Dict with quality metrics
        """
        if not self._usage_stats:
            return {"total_knowledge": 0, "message": "No usage data yet"}
        
        stats_list = list(self._usage_stats.values())
        
        # Calculate metrics
        total = len(stats_list)
        total_retrievals = sum(s.times_retrieved for s in stats_list)
        total_helpful = sum(s.times_helpful for s in stats_list)
        total_not_helpful = sum(s.times_not_helpful for s in stats_list)
        
        # Find most/least useful
        with_feedback = [s for s in stats_list if s.times_helpful + s.times_not_helpful > 0]
        most_useful = sorted(with_feedback, key=lambda x: x.usefulness_score, reverse=True)[:5]
        least_useful = sorted(with_feedback, key=lambda x: x.usefulness_score)[:5]
        
        # Never retrieved
        never_retrieved = [s for s in stats_list if s.times_retrieved == 0]
        
        return {
            "total_knowledge": total,
            "total_retrievals": total_retrievals,
            "total_helpful_feedback": total_helpful,
            "total_not_helpful_feedback": total_not_helpful,
            "overall_usefulness": total_helpful / (total_helpful + total_not_helpful) if (total_helpful + total_not_helpful) > 0 else 0.5,
            "knowledge_with_feedback": len(with_feedback),
            "never_retrieved_count": len(never_retrieved),
            "most_useful": [{"content": s.content[:50], "score": s.usefulness_score} for s in most_useful],
            "least_useful": [{"content": s.content[:50], "score": s.usefulness_score} for s in least_useful],
        }
    
    # =========================================================================
    # EXPORT CAPABILITIES
    # =========================================================================
    
    def export_to_csv(self, filename: str = None) -> Path:
        """
        Export consolidated knowledge to CSV.
        
        Args:
            filename: Optional filename (default: knowledge_export_YYYYMMDD.csv)
            
        Returns:
            Path to the exported file
        """
        import csv
        
        self.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        
        if filename is None:
            filename = f"knowledge_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = self.EXPORTS_DIR / filename
        
        # Collect all knowledge sources
        rows = []
        
        # From usage stats
        for stats in self._usage_stats.values():
            rows.append({
                "id": stats.knowledge_id,
                "type": stats.knowledge_type,
                "content": stats.content,
                "created_at": stats.created_at,
                "times_retrieved": stats.times_retrieved,
                "times_helpful": stats.times_helpful,
                "times_not_helpful": stats.times_not_helpful,
                "usefulness_score": f"{stats.usefulness_score:.2f}",
                "status": "active",
            })
        
        # From pending patterns
        for pending in self._pending_patterns.values():
            rows.append({
                "id": pending.id,
                "type": pending.knowledge_type,
                "content": pending.proposed_knowledge,
                "created_at": pending.created_at,
                "times_retrieved": 0,
                "times_helpful": 0,
                "times_not_helpful": 0,
                "usefulness_score": "N/A",
                "status": pending.status,
            })
        
        # Write CSV
        if rows:
            fieldnames = ["id", "type", "content", "created_at", "times_retrieved", 
                         "times_helpful", "times_not_helpful", "usefulness_score", "status"]
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        
        self._log(f"Exported {len(rows)} items to {filepath}")
        return filepath
    
    def export_to_excel(self, filename: str = None) -> Path:
        """
        Export consolidated knowledge to Excel with multiple sheets.
        
        Args:
            filename: Optional filename (default: knowledge_export_YYYYMMDD.xlsx)
            
        Returns:
            Path to the exported file
        """
        try:
            import pandas as pd
        except ImportError:
            self._log("pandas not installed, falling back to CSV")
            return self.export_to_csv(filename.replace('.xlsx', '.csv') if filename else None)
        
        self.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        
        if filename is None:
            filename = f"knowledge_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        filepath = self.EXPORTS_DIR / filename
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Sheet 1: Active Knowledge
            active_data = []
            for stats in self._usage_stats.values():
                active_data.append({
                    "ID": stats.knowledge_id,
                    "Type": stats.knowledge_type,
                    "Content": stats.content,
                    "Created": stats.created_at[:10] if stats.created_at else "",
                    "Retrievals": stats.times_retrieved,
                    "Helpful": stats.times_helpful,
                    "Not Helpful": stats.times_not_helpful,
                    "Usefulness %": f"{stats.usefulness_score * 100:.0f}%",
                })
            
            if active_data:
                df_active = pd.DataFrame(active_data)
                df_active.to_excel(writer, sheet_name="Active Knowledge", index=False)
            
            # Sheet 2: Pending Patterns
            pending_data = []
            for pending in self._pending_patterns.values():
                pending_data.append({
                    "ID": pending.id,
                    "Pattern Type": pending.pattern_type,
                    "Description": pending.description,
                    "Proposed Knowledge": pending.proposed_knowledge,
                    "Knowledge Type": pending.knowledge_type,
                    "Confidence %": f"{pending.confidence * 100:.0f}%",
                    "Evidence Count": pending.evidence_count,
                    "Status": pending.status,
                    "Created": pending.created_at[:10] if pending.created_at else "",
                    "Review Notes": pending.review_notes or "",
                })
            
            if pending_data:
                df_pending = pd.DataFrame(pending_data)
                df_pending.to_excel(writer, sheet_name="Pending Patterns", index=False)
            
            # Sheet 3: Consolidation History
            history = []
            if self.AUDIT_FILE.exists():
                try:
                    history = json.loads(self.AUDIT_FILE.read_text())
                except (json.JSONDecodeError, IOError):
                    pass
            
            if history:
                history_data = []
                for h in history[-50:]:  # Last 50 runs
                    history_data.append({
                        "Timestamp": h.get("timestamp", "")[:16],
                        "Episodes Reviewed": h.get("episodes_reviewed", 0),
                        "Patterns Found": h.get("patterns_identified", 0),
                        "Facts Created": h.get("semantic_facts_created", 0),
                        "Procedures Created": h.get("procedures_created", 0),
                        "Relationships Created": h.get("relationships_created", 0),
                        "Duration (s)": h.get("duration_seconds", 0),
                    })
                df_history = pd.DataFrame(history_data)
                df_history.to_excel(writer, sheet_name="Consolidation History", index=False)
            
            # Sheet 4: Quality Report
            quality = self.get_quality_report()
            quality_data = [{
                "Metric": k.replace("_", " ").title(),
                "Value": str(v) if not isinstance(v, (int, float)) else v,
            } for k, v in quality.items() if not isinstance(v, list)]
            
            if quality_data:
                df_quality = pd.DataFrame(quality_data)
                df_quality.to_excel(writer, sheet_name="Quality Report", index=False)
        
        self._log(f"Exported to Excel: {filepath}")
        return filepath
    
    # =========================================================================
    # EPISODE FETCHING
    # =========================================================================
    
    def _fetch_episodes(self, days: int) -> List[Dict]:
        """
        Fetch all episodic memories from the last N days.
        
        Sources:
        1. Local JSON backup (data/mem0_storage/episodes.json)
        2. Request log (crm/logs/requests.jsonl)
        """
        episodes = []
        cutoff = datetime.now() - timedelta(days=days)
        
        storage = self._get_mem0_storage()
        if storage:
            for identity_id, user_episodes in storage.episodes._local_cache.items():
                for ep in user_episodes.values():
                    try:
                        ts = datetime.fromisoformat(ep.timestamp)
                        if ts >= cutoff:
                            episodes.append({
                                "id": ep.id,
                                "identity_id": identity_id,
                                "timestamp": ep.timestamp,
                                "summary": ep.summary,
                                "topics": ep.topics,
                                "outcome": ep.outcome,
                                "channel": ep.channel,
                                "importance": ep.importance,
                            })
                    except (ValueError, AttributeError):
                        continue
        
        requests_log = PROJECT_ROOT / "crm" / "logs" / "requests.jsonl"
        if requests_log.exists():
            try:
                with open(requests_log, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            record = json.loads(line)
                            ts_str = record.get("timestamp", "")
                            if ts_str:
                                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                if ts.replace(tzinfo=None) >= cutoff:
                                    episodes.append({
                                        "id": record.get("request_id", ""),
                                        "identity_id": record.get("user_id", record.get("identity_id", "")),
                                        "timestamp": ts_str,
                                        "summary": record.get("query", record.get("message_preview", ""))[:500],
                                        "topics": record.get("topics", []),
                                        "outcome": record.get("outcome", ""),
                                        "channel": record.get("channel", "unknown"),
                                        "response_preview": record.get("response_preview", "")[:500],
                                        "citations": record.get("citations", []),
                                    })
                        except (json.JSONDecodeError, ValueError):
                            continue
            except Exception as e:
                self._log(f"Error reading requests log: {e}")
        
        self._log(f"Fetched {len(episodes)} episodes from last {days} days")
        return episodes
    
    # =========================================================================
    # PATTERN EXTRACTION
    # =========================================================================
    
    def _extract_patterns_with_llm(self, episodes: List[Dict]) -> List[ExtractedPattern]:
        """
        Use LLM to extract patterns across all episodes.
        
        Identifies:
        - Recurring topics (what users ask about most)
        - Common intents (what users want to accomplish)
        - Workflow patterns (sequences of actions)
        - Entity usage patterns (which products/entities are discussed together)
        """
        client = self._get_openai()
        if not client:
            self._log("OpenAI client not available, using heuristic extraction")
            return self._extract_patterns_heuristic(episodes)
        
        episode_summaries = []
        for ep in episodes[:100]:
            summary = ep.get("summary", "")
            outcome = ep.get("outcome", "")
            channel = ep.get("channel", "")
            topics = ep.get("topics", [])
            
            if summary:
                entry = f"- [{channel}] {summary}"
                if outcome:
                    entry += f" (Outcome: {outcome})"
                if topics:
                    entry += f" [Topics: {', '.join(topics)}]"
                episode_summaries.append(entry)
        
        if not episode_summaries:
            return []
        
        prompt = f"""Analyze these {len(episode_summaries)} conversation summaries from Ira (AI sales assistant for Machinecraft thermoforming machines).

CONVERSATIONS:
{chr(10).join(episode_summaries[:50])}

Identify RECURRING PATTERNS that appear across multiple conversations:

1. **TOPIC PATTERNS**: What subjects come up repeatedly?
   - Which machine models are frequently discussed?
   - What specifications are commonly asked about?
   - What applications/industries appear often?

2. **INTENT PATTERNS**: What are users trying to accomplish?
   - Common request types (quotes, specs, comparisons)
   - Typical customer journey stages
   - Frequently asked questions

3. **WORKFLOW PATTERNS**: Are there sequences of actions that happen together?
   - E.g., "Users who ask about PF1 often follow up about pricing"
   - E.g., "Shipping questions usually come after quote acceptance"

4. **ENTITY RELATIONSHIPS**: What entities are mentioned together?
   - E.g., "PF1 is often discussed with automotive applications"
   - E.g., "European customers often ask about CE certification"

Return JSON:
{{
  "topic_patterns": [
    {{"topic": "...", "frequency": N, "examples": ["query1", "query2"]}}
  ],
  "intent_patterns": [
    {{"intent": "...", "frequency": N, "typical_resolution": "..."}}
  ],
  "workflow_patterns": [
    {{"name": "...", "trigger": "...", "steps": ["step1", "step2"], "frequency": N}}
  ],
  "entity_relationships": [
    {{"entity1": "...", "relation": "...", "entity2": "...", "frequency": N}}
  ],
  "generalized_facts": [
    {{"fact": "...", "confidence": 0.8, "evidence_count": N}}
  ]
}}

Only include patterns that appear at least 2 times. Be specific to Machinecraft's domain."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract patterns from conversation data. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000,
                temperature=0.3,
            )
            
            text = response.choices[0].message.content
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            result = json.loads(text)
            patterns = self._convert_llm_result_to_patterns(result)
            
            self._log(f"LLM extracted {len(patterns)} patterns")
            return patterns
            
        except Exception as e:
            self._log(f"LLM extraction error: {e}")
            return self._extract_patterns_heuristic(episodes)
    
    def _convert_llm_result_to_patterns(self, result: Dict) -> List[ExtractedPattern]:
        """Convert LLM result to ExtractedPattern objects."""
        patterns = []
        now = datetime.now()
        
        for tp in result.get("topic_patterns", []):
            if tp.get("frequency", 0) >= self.MIN_PATTERN_OCCURRENCES:
                patterns.append(ExtractedPattern(
                    pattern_type="topic",
                    description=f"Users frequently ask about {tp.get('topic', '')}",
                    evidence_count=tp.get("frequency", 0),
                    example_queries=tp.get("examples", [])[:3],
                    confidence=min(0.9, 0.5 + tp.get("frequency", 0) * 0.1),
                    entities_involved=[tp.get("topic", "")],
                    first_seen=now,
                    last_seen=now,
                ))
        
        for ip in result.get("intent_patterns", []):
            if ip.get("frequency", 0) >= self.MIN_PATTERN_OCCURRENCES:
                patterns.append(ExtractedPattern(
                    pattern_type="intent",
                    description=f"Common user intent: {ip.get('intent', '')}",
                    evidence_count=ip.get("frequency", 0),
                    example_queries=[ip.get("typical_resolution", "")],
                    confidence=min(0.85, 0.5 + ip.get("frequency", 0) * 0.1),
                    entities_involved=[],
                    first_seen=now,
                    last_seen=now,
                ))
        
        for wp in result.get("workflow_patterns", []):
            if wp.get("frequency", 0) >= self.MIN_PATTERN_OCCURRENCES:
                patterns.append(ExtractedPattern(
                    pattern_type="workflow",
                    description=f"Workflow pattern: {wp.get('name', '')} - triggered by '{wp.get('trigger', '')}'",
                    evidence_count=wp.get("frequency", 0),
                    example_queries=wp.get("steps", []),
                    confidence=min(0.8, 0.4 + wp.get("frequency", 0) * 0.15),
                    entities_involved=[],
                    first_seen=now,
                    last_seen=now,
                ))
        
        for er in result.get("entity_relationships", []):
            if er.get("frequency", 0) >= self.MIN_PATTERN_OCCURRENCES:
                patterns.append(ExtractedPattern(
                    pattern_type="entity_relationship",
                    description=f"{er.get('entity1', '')} {er.get('relation', '')} {er.get('entity2', '')}",
                    evidence_count=er.get("frequency", 0),
                    example_queries=[],
                    confidence=min(0.85, 0.5 + er.get("frequency", 0) * 0.1),
                    entities_involved=[er.get("entity1", ""), er.get("entity2", "")],
                    first_seen=now,
                    last_seen=now,
                ))
        
        for gf in result.get("generalized_facts", []):
            if gf.get("evidence_count", 0) >= self.MIN_PATTERN_OCCURRENCES:
                patterns.append(ExtractedPattern(
                    pattern_type="fact",
                    description=gf.get("fact", ""),
                    evidence_count=gf.get("evidence_count", 0),
                    example_queries=[],
                    confidence=gf.get("confidence", 0.7),
                    entities_involved=[],
                    first_seen=now,
                    last_seen=now,
                ))
        
        return patterns
    
    def _extract_patterns_heuristic(self, episodes: List[Dict]) -> List[ExtractedPattern]:
        """
        Extract patterns using heuristics (fallback when LLM unavailable).
        """
        patterns = []
        now = datetime.now()
        
        topic_counts = Counter()
        topic_examples = defaultdict(list)
        
        for ep in episodes:
            summary = ep.get("summary", "").lower()
            
            machine_patterns = [
                r'pf1', r'pf2', r'am[-\s]?\d', r'fcs', r'img', r'thermoform'
            ]
            import re
            for pattern in machine_patterns:
                if re.search(pattern, summary):
                    topic = re.search(pattern, summary).group(0).upper()
                    topic_counts[topic] += 1
                    topic_examples[topic].append(ep.get("summary", "")[:100])
            
            application_keywords = [
                "automotive", "packaging", "medical", "aerospace", "signage",
                "dashboard", "interior", "tray", "container", "enclosure"
            ]
            for kw in application_keywords:
                if kw in summary:
                    topic_counts[kw] += 1
                    topic_examples[kw].append(ep.get("summary", "")[:100])
        
        for topic, count in topic_counts.most_common(10):
            if count >= self.MIN_PATTERN_OCCURRENCES:
                patterns.append(ExtractedPattern(
                    pattern_type="topic",
                    description=f"Users frequently ask about {topic}",
                    evidence_count=count,
                    example_queries=topic_examples[topic][:3],
                    confidence=min(0.8, 0.4 + count * 0.1),
                    entities_involved=[topic],
                    first_seen=now,
                    last_seen=now,
                ))
        
        return patterns
    
    # =========================================================================
    # KNOWLEDGE SYNTHESIS
    # =========================================================================
    
    def _synthesize_knowledge(self, patterns: List[ExtractedPattern]) -> List[ConsolidatedKnowledge]:
        """
        Synthesize patterns into actionable knowledge.
        
        Converts patterns into:
        1. Semantic facts (for remember())
        2. Procedural memories (workflows)
        3. Knowledge graph relationships
        """
        knowledge = []
        
        for pattern in patterns:
            if pattern.confidence < self.MIN_CONFIDENCE:
                continue
            
            if pattern.pattern_type == "topic":
                knowledge.append(ConsolidatedKnowledge(
                    knowledge_type="semantic_fact",
                    content=pattern.description,
                    source_pattern=pattern.pattern_type,
                    confidence=pattern.confidence,
                    metadata={
                        "evidence_count": pattern.evidence_count,
                        "examples": pattern.example_queries,
                        "entities": pattern.entities_involved,
                    }
                ))
            
            elif pattern.pattern_type == "fact":
                knowledge.append(ConsolidatedKnowledge(
                    knowledge_type="semantic_fact",
                    content=pattern.description,
                    source_pattern=pattern.pattern_type,
                    confidence=pattern.confidence,
                    metadata={
                        "evidence_count": pattern.evidence_count,
                    }
                ))
            
            elif pattern.pattern_type == "workflow":
                steps = pattern.example_queries
                if steps:
                    knowledge.append(ConsolidatedKnowledge(
                        knowledge_type="procedural",
                        content=pattern.description,
                        source_pattern=pattern.pattern_type,
                        confidence=pattern.confidence,
                        metadata={
                            "steps": steps,
                            "evidence_count": pattern.evidence_count,
                        }
                    ))
            
            elif pattern.pattern_type == "entity_relationship":
                parts = pattern.description.split()
                if len(parts) >= 3:
                    knowledge.append(ConsolidatedKnowledge(
                        knowledge_type="relationship",
                        content=pattern.description,
                        source_pattern=pattern.pattern_type,
                        confidence=pattern.confidence,
                        metadata={
                            "entities": pattern.entities_involved,
                            "evidence_count": pattern.evidence_count,
                        }
                    ))
            
            elif pattern.pattern_type == "intent":
                knowledge.append(ConsolidatedKnowledge(
                    knowledge_type="semantic_fact",
                    content=pattern.description,
                    source_pattern=pattern.pattern_type,
                    confidence=pattern.confidence,
                    metadata={
                        "evidence_count": pattern.evidence_count,
                    }
                ))
        
        self._log(f"Synthesized {len(knowledge)} knowledge items from {len(patterns)} patterns")
        return knowledge
    
    # =========================================================================
    # KNOWLEDGE STORAGE
    # =========================================================================
    
    def _store_semantic_fact(self, knowledge: ConsolidatedKnowledge) -> bool:
        """Store a semantic fact using remember()."""
        try:
            controller = self._get_memory_controller()
            if not controller:
                self._log("Memory controller unavailable")
                return False
            
            result = controller.process(
                content=knowledge.content,
                source="consolidation",
                entity_name=knowledge.metadata.get("entities", [None])[0] if knowledge.metadata.get("entities") else None,
                context={
                    "is_consolidated": True,
                    "source_pattern": knowledge.source_pattern,
                    "confidence": knowledge.confidence,
                    "evidence_count": knowledge.metadata.get("evidence_count", 0),
                }
            )
            
            success = result.get("action") in ["create", "reinforce", "update"]
            if success:
                self._log(f"Stored fact: {knowledge.content[:60]}...")
            return success
            
        except Exception as e:
            self._log(f"Error storing fact: {e}")
            return False
    
    def _store_procedure(self, knowledge: ConsolidatedKnowledge) -> bool:
        """Store a procedural memory."""
        try:
            proc_store = self._get_procedural_store()
            if not proc_store:
                self._log("Procedural store unavailable")
                return False
            
            steps = knowledge.metadata.get("steps", [])
            if not steps:
                return False
            
            import re
            name_match = re.search(r'Workflow pattern: (\w+)', knowledge.content)
            name = name_match.group(1) if name_match else f"consolidated_workflow_{datetime.now().strftime('%Y%m%d')}"
            
            trigger_match = re.search(r"triggered by '([^']+)'", knowledge.content)
            trigger = trigger_match.group(1) if trigger_match else ""
            
            proc_steps = [
                {"action": f"step_{i+1}", "description": step}
                for i, step in enumerate(steps)
            ]
            
            proc_id = proc_store.store_procedure(
                name=name,
                trigger_patterns=[trigger] if trigger else [name],
                steps=proc_steps,
                description=knowledge.content,
                source="consolidation",
            )
            
            self._log(f"Stored procedure: {name}")
            return bool(proc_id)
            
        except Exception as e:
            self._log(f"Error storing procedure: {e}")
            return False
    
    def _store_relationship(self, knowledge: ConsolidatedKnowledge) -> bool:
        """Store a knowledge graph relationship."""
        try:
            rel_store = self._get_relationship_store()
            if not rel_store:
                self._log("Relationship store unavailable")
                return False
            
            entities = knowledge.metadata.get("entities", [])
            if len(entities) < 2:
                import re
                parts = knowledge.content.split()
                if len(parts) >= 3:
                    entities = [parts[0], parts[-1]]
                else:
                    return False
            
            relation_patterns = {
                "used_for": ["used for", "used in", "application"],
                "related_to": ["related to", "associated with"],
                "requires": ["requires", "needs"],
                "is_a": ["is a", "type of"],
                "has": ["has", "includes", "contains"],
            }
            
            relation = "related_to"
            content_lower = knowledge.content.lower()
            for rel_type, patterns in relation_patterns.items():
                if any(p in content_lower for p in patterns):
                    relation = rel_type
                    break
            
            success = rel_store.add_relationship(
                source=entities[0],
                relation=relation,
                target=entities[1],
                confidence=knowledge.confidence,
                learned_from="consolidation",
            )
            
            if success:
                self._log(f"Stored relationship: {entities[0]} --{relation}--> {entities[1]}")
            return success
            
        except Exception as e:
            self._log(f"Error storing relationship: {e}")
            return False
    
    def _store_knowledge(
        self, 
        knowledge_items: List[ConsolidatedKnowledge], 
        patterns: List[ExtractedPattern],
        result: ConsolidationResult
    ):
        """
        Store all synthesized knowledge.
        
        If require_approval is True, patterns below AUTO_APPROVE_CONFIDENCE
        will be queued for human approval instead of stored directly.
        """
        for i, knowledge in enumerate(knowledge_items):
            try:
                # Get corresponding pattern
                pattern = patterns[i] if i < len(patterns) else None
                
                # Check if we need approval
                should_queue = (
                    self.require_approval and 
                    pattern is not None and 
                    pattern.confidence < self.AUTO_APPROVE_CONFIDENCE
                )
                
                if should_queue:
                    # Queue for approval
                    pattern_id = self._queue_for_approval(pattern, knowledge)
                    result.patterns_pending_approval += 1
                    result.new_knowledge.append({
                        "type": knowledge.knowledge_type,
                        "content": knowledge.content,
                        "status": "pending_approval",
                        "pattern_id": pattern_id,
                    })
                    continue
                
                # Store directly
                import hashlib
                knowledge_id = hashlib.md5(knowledge.content.encode()).hexdigest()[:12]
                
                if knowledge.knowledge_type == "semantic_fact":
                    if self._store_semantic_fact(knowledge):
                        result.semantic_facts_created += 1
                        result.new_knowledge.append({
                            "type": "semantic_fact",
                            "content": knowledge.content,
                            "confidence": knowledge.confidence,
                        })
                        self._track_knowledge_created(knowledge, knowledge_id)
                
                elif knowledge.knowledge_type == "procedural":
                    if self._store_procedure(knowledge):
                        result.procedures_created += 1
                        result.new_knowledge.append({
                            "type": "procedural",
                            "content": knowledge.content,
                            "steps": knowledge.metadata.get("steps", []),
                        })
                        self._track_knowledge_created(knowledge, knowledge_id)
                
                elif knowledge.knowledge_type == "relationship":
                    if self._store_relationship(knowledge):
                        result.relationships_created += 1
                        result.new_knowledge.append({
                            "type": "relationship",
                            "content": knowledge.content,
                            "entities": knowledge.metadata.get("entities", []),
                        })
                        self._track_knowledge_created(knowledge, knowledge_id)
                        
            except Exception as e:
                result.errors.append(f"Storage error: {str(e)}")
    
    def _log_consolidation(self, result: ConsolidationResult, patterns: List[ExtractedPattern]):
        """
        Log consolidation results to audit file for tracking over time.
        
        This creates a history of what IRA has learned, enabling:
        - Debugging consolidation issues
        - Understanding learning trends
        - Reviewing what patterns were found
        """
        try:
            self.AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            history = []
            if self.AUDIT_FILE.exists():
                try:
                    history = json.loads(self.AUDIT_FILE.read_text())
                except (json.JSONDecodeError, IOError):
                    history = []
            
            entry = {
                "timestamp": datetime.now().isoformat(),
                "episodes_reviewed": result.episodes_reviewed,
                "patterns_identified": result.patterns_identified,
                "semantic_facts_created": result.semantic_facts_created,
                "procedures_created": result.procedures_created,
                "relationships_created": result.relationships_created,
                "knowledge_reinforced": result.knowledge_reinforced,
                "duration_seconds": result.duration_seconds,
                "errors": result.errors[:5] if result.errors else [],
                "top_patterns": [
                    {
                        "type": p.pattern_type,
                        "description": p.description[:100],
                        "confidence": p.confidence,
                        "evidence_count": p.evidence_count,
                    }
                    for p in sorted(patterns, key=lambda x: x.confidence, reverse=True)[:5]
                ],
            }
            
            history.append(entry)
            
            history = history[-100:]
            
            self.AUDIT_FILE.write_text(json.dumps(history, indent=2))
            self._log(f"Logged consolidation to {self.AUDIT_FILE}")
            
        except Exception as e:
            self._log(f"Failed to log consolidation: {e}")
    
    # =========================================================================
    # MAIN CONSOLIDATION METHOD
    # =========================================================================
    
    def consolidate_episodic_memories(self, days_to_review: int = 7) -> ConsolidationResult:
        """
        Main consolidation method - learns from recent conversations.
        
        Args:
            days_to_review: How many days of history to analyze
            
        Returns:
            ConsolidationResult with statistics and new knowledge
        """
        import time
        start_time = time.time()
        
        result = ConsolidationResult()
        self._log(f"Starting memory consolidation (reviewing {days_to_review} days)")
        
        episodes = self._fetch_episodes(days_to_review)
        result.episodes_reviewed = len(episodes)
        
        if len(episodes) < 3:
            self._log(f"Not enough episodes ({len(episodes)}) for meaningful consolidation")
            result.duration_seconds = time.time() - start_time
            return result
        
        self._log(f"Extracting patterns from {len(episodes)} episodes...")
        patterns = self._extract_patterns_with_llm(episodes)
        result.patterns_identified = len(patterns)
        result.patterns = [
            {
                "type": p.pattern_type,
                "description": p.description,
                "evidence_count": p.evidence_count,
                "confidence": p.confidence,
            }
            for p in patterns
        ]
        
        if not patterns:
            self._log("No significant patterns found")
            result.duration_seconds = time.time() - start_time
            return result
        
        self._log(f"Synthesizing knowledge from {len(patterns)} patterns...")
        knowledge_items = self._synthesize_knowledge(patterns)
        
        self._log(f"Storing {len(knowledge_items)} knowledge items...")
        self._store_knowledge(knowledge_items, patterns, result)
        
        # Send notification if patterns are pending approval
        if result.patterns_pending_approval > 0:
            self._log(f"{result.patterns_pending_approval} patterns queued for approval")
            self.send_patterns_for_review()
        
        result.duration_seconds = time.time() - start_time
        
        self._log_consolidation(result, patterns)
        
        self._log(f"Consolidation complete: {result.semantic_facts_created} facts, "
                  f"{result.procedures_created} procedures, "
                  f"{result.relationships_created} relationships"
                  + (f", {result.patterns_pending_approval} pending approval" if result.patterns_pending_approval > 0 else ""))
        
        return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_consolidator: Optional[MemoryConsolidator] = None


def get_memory_consolidator(verbose: bool = False) -> MemoryConsolidator:
    """Get or create the memory consolidator."""
    global _consolidator
    if _consolidator is None:
        _consolidator = MemoryConsolidator(verbose=verbose)
    return _consolidator


def run_memory_consolidation(days: int = 7, verbose: bool = False) -> ConsolidationResult:
    """
    Run memory consolidation.
    
    Usage:
        from memory_consolidator import run_memory_consolidation
        result = run_memory_consolidation(days=7)
    """
    consolidator = MemoryConsolidator(verbose=verbose)
    return consolidator.consolidate_episodic_memories(days_to_review=days)


# =============================================================================
# CLI
# =============================================================================

def show_consolidation_history(limit: int = 10):
    """Show recent consolidation history."""
    audit_file = PROJECT_ROOT / "data" / "knowledge" / "consolidation_log.json"
    
    if not audit_file.exists():
        print("No consolidation history found.")
        return
    
    try:
        history = json.loads(audit_file.read_text())
    except (json.JSONDecodeError, IOError):
        print("Error reading consolidation history.")
        return
    
    print(f"\n📜 CONSOLIDATION HISTORY (last {min(limit, len(history))} runs)")
    print("=" * 70)
    
    total_facts = 0
    total_procedures = 0
    total_relationships = 0
    
    for entry in history[-limit:]:
        ts = entry.get("timestamp", "")[:16]
        episodes = entry.get("episodes_reviewed", 0)
        patterns = entry.get("patterns_identified", 0)
        facts = entry.get("semantic_facts_created", 0)
        procs = entry.get("procedures_created", 0)
        rels = entry.get("relationships_created", 0)
        
        total_facts += facts
        total_procedures += procs
        total_relationships += rels
        
        print(f"\n  {ts}")
        print(f"    Episodes: {episodes} → Patterns: {patterns}")
        print(f"    Created: {facts} facts, {procs} procedures, {rels} relationships")
        
        top_patterns = entry.get("top_patterns", [])
        if top_patterns:
            print(f"    Top patterns:")
            for p in top_patterns[:2]:
                print(f"      • [{p['type']}] {p['description'][:50]}...")
    
    print(f"\n  📊 TOTALS:")
    print(f"     Facts: {total_facts}")
    print(f"     Procedures: {total_procedures}")
    print(f"     Relationships: {total_relationships}")


def get_consolidation_stats() -> Dict[str, Any]:
    """Get overall consolidation statistics."""
    audit_file = PROJECT_ROOT / "data" / "knowledge" / "consolidation_log.json"
    
    if not audit_file.exists():
        return {"total_runs": 0}
    
    try:
        history = json.loads(audit_file.read_text())
    except (json.JSONDecodeError, IOError):
        return {"total_runs": 0, "error": "Failed to read history"}
    
    if not history:
        return {"total_runs": 0}
    
    return {
        "total_runs": len(history),
        "total_episodes_reviewed": sum(e.get("episodes_reviewed", 0) for e in history),
        "total_patterns_found": sum(e.get("patterns_identified", 0) for e in history),
        "total_facts_created": sum(e.get("semantic_facts_created", 0) for e in history),
        "total_procedures_created": sum(e.get("procedures_created", 0) for e in history),
        "total_relationships_created": sum(e.get("relationships_created", 0) for e in history),
        "first_run": history[0].get("timestamp", "")[:10] if history else None,
        "last_run": history[-1].get("timestamp", "")[:16] if history else None,
        "avg_patterns_per_run": sum(e.get("patterns_identified", 0) for e in history) / len(history) if history else 0,
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Memory Consolidation System")
    parser.add_argument("--days", type=int, default=7, help="Days of history to review")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Don't store, just show patterns")
    parser.add_argument("--require-approval", action="store_true", help="Queue patterns for approval")
    parser.add_argument("--history", action="store_true", help="Show consolidation history")
    parser.add_argument("--stats", action="store_true", help="Show consolidation statistics")
    parser.add_argument("--pending", action="store_true", help="Show pending patterns awaiting approval")
    parser.add_argument("--approve", type=str, help="Approve a pattern by ID")
    parser.add_argument("--approve-all", action="store_true", help="Approve all pending patterns")
    parser.add_argument("--reject", type=str, help="Reject a pattern by ID")
    parser.add_argument("--reject-reason", type=str, default="", help="Reason for rejection")
    parser.add_argument("--export-csv", action="store_true", help="Export knowledge to CSV")
    parser.add_argument("--export-excel", action="store_true", help="Export knowledge to Excel")
    parser.add_argument("--quality", action="store_true", help="Show quality report")
    args = parser.parse_args()
    
    print("=" * 60)
    print("IRA MEMORY CONSOLIDATION")
    print("=" * 60)
    
    consolidator = MemoryConsolidator(verbose=True, require_approval=args.require_approval)
    
    if args.history:
        show_consolidation_history(limit=10)
    
    elif args.stats:
        stats = get_consolidation_stats()
        print(f"\n📊 CONSOLIDATION STATISTICS")
        print("-" * 40)
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"   {key}: {value:.1f}")
            else:
                print(f"   {key}: {value}")
    
    elif args.pending:
        pending = consolidator.get_pending_patterns("pending")
        print(f"\n📋 PENDING PATTERNS ({len(pending)} items)")
        print("-" * 60)
        for p in pending:
            print(f"\n  ID: {p.id}")
            print(f"  Type: {p.pattern_type}")
            print(f"  Description: {p.description[:70]}...")
            print(f"  Proposed: {p.proposed_knowledge[:70]}...")
            print(f"  Confidence: {p.confidence:.0%}")
            print(f"  Evidence: {p.evidence_count} occurrences")
        
        if not pending:
            print("   No pending patterns.")
    
    elif args.approve:
        if consolidator.approve_pattern(args.approve):
            print(f"✅ Approved pattern {args.approve}")
        else:
            print(f"❌ Failed to approve pattern {args.approve}")
    
    elif args.approve_all:
        pending = consolidator.get_pending_patterns("pending")
        approved = 0
        for p in pending:
            if consolidator.approve_pattern(p.id):
                approved += 1
        print(f"✅ Approved {approved}/{len(pending)} patterns")
    
    elif args.reject:
        if consolidator.reject_pattern(args.reject, args.reject_reason):
            print(f"❌ Rejected pattern {args.reject}")
        else:
            print(f"Failed to reject pattern {args.reject}")
    
    elif args.export_csv:
        filepath = consolidator.export_to_csv()
        print(f"📄 Exported to: {filepath}")
    
    elif args.export_excel:
        filepath = consolidator.export_to_excel()
        print(f"📊 Exported to: {filepath}")
    
    elif args.quality:
        report = consolidator.get_quality_report()
        print(f"\n📈 QUALITY REPORT")
        print("-" * 40)
        print(f"   Total knowledge items: {report.get('total_knowledge', 0)}")
        print(f"   Total retrievals: {report.get('total_retrievals', 0)}")
        print(f"   Helpful feedback: {report.get('total_helpful_feedback', 0)}")
        print(f"   Not helpful feedback: {report.get('total_not_helpful_feedback', 0)}")
        print(f"   Overall usefulness: {report.get('overall_usefulness', 0):.0%}")
        print(f"   Never retrieved: {report.get('never_retrieved_count', 0)}")
        
        if report.get("most_useful"):
            print(f"\n   🌟 Most Useful:")
            for item in report["most_useful"][:3]:
                print(f"      {item['score']:.0%} - {item['content']}...")
        
        if report.get("least_useful"):
            print(f"\n   ⚠ Least Useful:")
            for item in report["least_useful"][:3]:
                print(f"      {item['score']:.0%} - {item['content']}...")
    
    elif args.dry_run:
        episodes = consolidator._fetch_episodes(args.days)
        print(f"\nEpisodes found: {len(episodes)}")
        
        patterns = consolidator._extract_patterns_with_llm(episodes)
        print(f"\nPatterns identified: {len(patterns)}")
        for p in patterns:
            print(f"  [{p.pattern_type}] {p.description[:60]}... (confidence: {p.confidence:.0%})")
        
        knowledge = consolidator._synthesize_knowledge(patterns)
        print(f"\nKnowledge to be created: {len(knowledge)}")
        for k in knowledge:
            print(f"  [{k.knowledge_type}] {k.content[:60]}...")
    
    else:
        result = consolidator.consolidate_episodic_memories(days_to_review=args.days)
        
        print(f"\n📊 CONSOLIDATION RESULTS:")
        print(f"   Episodes reviewed: {result.episodes_reviewed}")
        print(f"   Patterns identified: {result.patterns_identified}")
        print(f"   Semantic facts created: {result.semantic_facts_created}")
        print(f"   Procedures created: {result.procedures_created}")
        print(f"   Relationships created: {result.relationships_created}")
        if result.patterns_pending_approval > 0:
            print(f"   Patterns pending approval: {result.patterns_pending_approval}")
        print(f"   Duration: {result.duration_seconds:.1f}s")
        
        if result.errors:
            print(f"\n⚠ Errors: {len(result.errors)}")
            for err in result.errors[:3]:
                print(f"   - {err}")
        
        if result.new_knowledge:
            print(f"\n🧠 NEW KNOWLEDGE:")
            for k in result.new_knowledge[:5]:
                status = k.get('status', 'stored')
                print(f"   [{k['type']}] {k['content'][:50]}... ({status})")
