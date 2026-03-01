#!/usr/bin/env python3
"""
MEMORY CONTROLLER - Intelligent Memory Update Orchestrator

╔════════════════════════════════════════════════════════════════════════════╗
║  This agent decides:                                                       ║
║  1. WHAT gets stored (filter noise, extract signal)                        ║
║  2. WHERE it gets stored (Mem0, Qdrant, JSON)                             ║
║  3. WHEN to update vs create (detect duplicates, contradictions)          ║
║  4. HOW to consolidate (episodic → semantic facts)                        ║
╚════════════════════════════════════════════════════════════════════════════╝

Memory Types & Destinations:
┌─────────────────────────┬───────────────┬───────────────┬─────────────────┐
│ Memory Type             │ Mem0 (Cloud)  │ Qdrant        │ JSON (Backup)   │
├─────────────────────────┼───────────────┼───────────────┼─────────────────┤
│ User facts (personal)   │ ✓ user_id     │ -             │ -               │
│ Entity facts (products) │ ✓ agent_id    │ ✓ chunks      │ -               │
│ Episodes (conversations)│ ✓ user_id     │ -             │ ✓ episodes.json │
│ Procedures (workflows)  │ ✓ agent_id    │ -             │ ✓ procedures.json│
│ Dream knowledge         │ ✓ system_ira  │ ✓ dream coll  │ -               │
│ Relationships           │ ✓ agent_id    │ -             │ ✓ relations.json│
│ Corrections             │ ✓ UPDATE      │ ✓ UPDATE      │ -               │
└─────────────────────────┴───────────────┴───────────────┴─────────────────┘

Triggers for Memory Updates:
1. LEARN - New information from conversation/document
2. CORRECT - User explicitly corrects a fact
3. REINFORCE - Same fact seen again (boost confidence)
4. DECAY - Fact not used in long time (reduce importance)
5. CONFLICT - New fact contradicts existing (needs resolution)
6. CONSOLIDATE - Multiple episodes → single semantic fact
"""

import logging
import os
import sys
import json
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

# Setup paths
MEMORY_DIR = Path(__file__).parent
SKILLS_DIR = MEMORY_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent
sys.path.insert(0, str(AGENT_DIR))

# Import centralized config
try:
    from config import (
        OPENAI_API_KEY, MEM0_API_KEY, QDRANT_URL,
        setup_import_paths, get_logger as get_config_logger
    )
    setup_import_paths()
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    # Fallback: Load env
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    MEM0_API_KEY = os.environ.get("MEM0_API_KEY", "")
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")


# =============================================================================
# MEMORY TYPES
# =============================================================================

class MemoryType(Enum):
    """Types of memories Ira can store."""
    USER_FACT = "user_fact"           # Personal info about a user
    ENTITY_FACT = "entity_fact"       # Info about products, companies
    EPISODE = "episode"               # Timestamped conversation event
    PROCEDURE = "procedure"           # Learned workflow
    RELATIONSHIP = "relationship"     # Connection between entities
    DREAM_INSIGHT = "dream_insight"   # Knowledge from document learning
    CORRECTION = "correction"         # Explicit user correction


class UpdateAction(Enum):
    """Actions the controller can take."""
    CREATE = "create"       # New memory
    UPDATE = "update"       # Modify existing
    REINFORCE = "reinforce" # Boost confidence
    CONFLICT = "conflict"   # Queue for resolution
    IGNORE = "ignore"       # Too noisy/redundant
    CONSOLIDATE = "consolidate"  # Merge into existing


class StorageTarget(Enum):
    """Where to store memory."""
    MEM0_USER = "mem0_user"       # Mem0 with user_id
    MEM0_AGENT = "mem0_agent"     # Mem0 with agent_id
    QDRANT = "qdrant"             # Vector search
    JSON_BACKUP = "json_backup"   # Local JSON file
    ALL = "all"                   # Multiple targets


@dataclass
class MemoryUpdate:
    """A memory update request."""
    content: str
    memory_type: MemoryType
    source: str  # telegram, email, dream, correction
    identity_id: Optional[str] = None
    entity_name: Optional[str] = None
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Controller fills these
    action: Optional[UpdateAction] = None
    targets: List[StorageTarget] = field(default_factory=list)
    existing_memory_id: Optional[str] = None
    conflict_with: Optional[str] = None


@dataclass
class ControllerDecision:
    """Decision made by the controller."""
    action: UpdateAction
    targets: List[StorageTarget]
    reason: str
    existing_memory_id: Optional[str] = None
    conflict_detected: bool = False
    confidence_adjustment: float = 0.0


# =============================================================================
# MEMORY CONTROLLER
# =============================================================================

class MemoryController:
    """
    Intelligent agent that orchestrates all memory updates.
    
    Responsibilities:
    1. Classify incoming information
    2. Check for duplicates/conflicts
    3. Decide storage targets
    4. Execute updates
    5. Trigger consolidation when appropriate
    """
    
    # Thresholds
    DUPLICATE_THRESHOLD = 0.85  # Similarity score to consider duplicate
    CONFLICT_THRESHOLD = 0.7   # Score to flag as potential conflict
    NOISE_PATTERNS = [
        r'^(ok|okay|thanks|thank you|got it|sure|yes|no)\.?$',
        r'^(hi|hello|hey|bye|goodbye)\.?$',
        r'^\W+$',  # Just punctuation
    ]
    
    def __init__(self):
        self._mem0 = None
        self._qdrant = None
        self._openai = None
        self._decision_log: List[Dict] = []
    
    def _get_mem0(self):
        """Get Mem0 client."""
        if self._mem0 is None:
            api_key = os.environ.get("MEM0_API_KEY")
            if api_key:
                try:
                    from mem0 import MemoryClient
                    self._mem0 = MemoryClient(api_key=api_key)
                except Exception as e:
                    logger.warning(f"Mem0 unavailable: {e}")
        return self._mem0
    
    def _get_qdrant(self):
        """Get Qdrant client."""
        if self._qdrant is None:
            try:
                from qdrant_client import QdrantClient
                url = os.environ.get("QDRANT_URL", "http://localhost:6333")
                self._qdrant = QdrantClient(url=url, timeout=30)
            except Exception as e:
                logger.warning(f"Qdrant unavailable: {e}")
        return self._qdrant
    
    def _get_openai(self):
        """Get OpenAI client for LLM decisions."""
        if self._openai is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                import openai
                self._openai = openai.OpenAI(api_key=api_key)
        return self._openai
    
    # =========================================================================
    # CLASSIFICATION
    # =========================================================================
    
    def classify(self, content: str, context: Dict[str, Any] = None) -> MemoryType:
        """
        Classify content into memory type.
        
        Uses heuristics first, then LLM if ambiguous.
        """
        content_lower = content.lower()
        context = context or {}
        
        # Explicit correction
        if any(p in content_lower for p in ["actually", "correction:", "that's wrong", "no, it's"]):
            return MemoryType.CORRECTION
        
        # Relationship patterns
        if any(p in content_lower for p in ["works at", "works for", "is from", "knows"]):
            return MemoryType.RELATIONSHIP
        
        # Procedure patterns
        if any(p in content_lower for p in ["how to", "steps to", "process for", "workflow"]):
            return MemoryType.PROCEDURE
        
        # Entity vs User fact
        if context.get("has_entity"):
            return MemoryType.ENTITY_FACT
        
        if context.get("is_about_user"):
            return MemoryType.USER_FACT
        
        # Dream source
        if context.get("source") == "dream":
            return MemoryType.DREAM_INSIGHT
        
        # Default to episode if from conversation
        if context.get("source") in ["telegram", "email"]:
            return MemoryType.EPISODE
        
        return MemoryType.USER_FACT
    
    def is_noise(self, content: str) -> bool:
        """Check if content is just noise (greetings, confirmations)."""
        import re
        
        content = content.strip()
        if len(content) < 10:
            return True
        
        for pattern in self.NOISE_PATTERNS:
            if re.match(pattern, content, re.IGNORECASE):
                return True
        
        return False
    
    # =========================================================================
    # DUPLICATE & CONFLICT DETECTION
    # =========================================================================
    
    def check_existing(
        self,
        content: str,
        identity_id: Optional[str] = None,
        entity_name: Optional[str] = None,
    ) -> Tuple[Optional[str], float, bool]:
        """
        Check for existing similar memories.
        
        Returns: (existing_id, similarity_score, is_conflict)
        """
        mem0 = self._get_mem0()
        if not mem0:
            return None, 0.0, False
        
        try:
            # Build filters - mem0 v2 API requires non-empty filters
            filters = {}
            if identity_id:
                filters["user_id"] = identity_id
            elif entity_name:
                filters["agent_id"] = f"entity_{entity_name.lower().replace(' ', '_')}"
            
            # Cannot search without a filter scope - return early
            if not filters:
                return None, 0.0, False
            
            results = mem0.search(
                query=content,
                version="v2",
                filters=filters,
                top_k=3,
            )
            
            memories = results.get("results", results.get("memories", []))
            
            if not memories:
                return None, 0.0, False
            
            top = memories[0]
            score = top.get("score", 0)
            existing_text = top.get("memory", "")
            existing_id = top.get("id")
            
            # Check for conflict (high similarity but different content)
            is_conflict = self._detect_conflict(content, existing_text)
            
            return existing_id, score, is_conflict
            
        except Exception as e:
            logger.error(f"Existing check error: {e}")
            return None, 0.0, False
    
    def _detect_conflict(self, new_content: str, existing_content: str) -> bool:
        """
        Detect if new content conflicts with existing.
        
        Uses simple heuristics, could use LLM for complex cases.
        """
        # Negation detection
        negations = ["not", "isn't", "wasn't", "don't", "doesn't", "never", "no longer"]
        
        new_lower = new_content.lower()
        existing_lower = existing_content.lower()
        
        # Check if one negates the other
        for neg in negations:
            if neg in new_lower and neg not in existing_lower:
                return True
            if neg in existing_lower and neg not in new_lower:
                return True
        
        # Check for contradictory numbers
        import re
        new_numbers = set(re.findall(r'\d+', new_content))
        existing_numbers = set(re.findall(r'\d+', existing_content))
        
        if new_numbers and existing_numbers and new_numbers != existing_numbers:
            # Same topic but different numbers = potential conflict
            return True
        
        return False
    
    # =========================================================================
    # DECISION MAKING
    # =========================================================================
    
    def decide(self, update: MemoryUpdate) -> ControllerDecision:
        """
        Make decision about how to handle a memory update.
        
        This is the core logic of the controller.
        """
        # Check for noise
        if self.is_noise(update.content):
            return ControllerDecision(
                action=UpdateAction.IGNORE,
                targets=[],
                reason="Content is noise (too short or just greeting/confirmation)"
            )
        
        # Check for existing
        existing_id, similarity, is_conflict = self.check_existing(
            update.content,
            identity_id=update.identity_id,
            entity_name=update.entity_name,
        )
        
        # Duplicate detection
        if similarity >= self.DUPLICATE_THRESHOLD and not is_conflict:
            return ControllerDecision(
                action=UpdateAction.REINFORCE,
                targets=[StorageTarget.MEM0_USER if update.identity_id else StorageTarget.MEM0_AGENT],
                reason=f"Similar memory exists (score={similarity:.2f}), reinforcing",
                existing_memory_id=existing_id,
                confidence_adjustment=0.1,  # Boost confidence
            )
        
        # Conflict detection
        if is_conflict and similarity >= self.CONFLICT_THRESHOLD:
            return ControllerDecision(
                action=UpdateAction.CONFLICT,
                targets=[],  # Don't store yet
                reason=f"Conflicts with existing memory (score={similarity:.2f})",
                existing_memory_id=existing_id,
                conflict_detected=True,
            )
        
        # Correction handling
        if update.memory_type == MemoryType.CORRECTION:
            return ControllerDecision(
                action=UpdateAction.UPDATE,
                targets=self._get_targets(update.memory_type),
                reason="Explicit correction - updating existing memory",
                existing_memory_id=existing_id,
            )
        
        # New memory
        return ControllerDecision(
            action=UpdateAction.CREATE,
            targets=self._get_targets(update.memory_type),
            reason="New information, creating memory",
        )
    
    def _get_targets(self, memory_type: MemoryType) -> List[StorageTarget]:
        """Get storage targets for a memory type."""
        targets = {
            MemoryType.USER_FACT: [StorageTarget.MEM0_USER],
            MemoryType.ENTITY_FACT: [StorageTarget.MEM0_AGENT, StorageTarget.QDRANT],
            MemoryType.EPISODE: [StorageTarget.MEM0_USER, StorageTarget.JSON_BACKUP],
            MemoryType.PROCEDURE: [StorageTarget.MEM0_AGENT, StorageTarget.JSON_BACKUP],
            MemoryType.RELATIONSHIP: [StorageTarget.MEM0_AGENT, StorageTarget.JSON_BACKUP],
            MemoryType.DREAM_INSIGHT: [StorageTarget.MEM0_AGENT, StorageTarget.QDRANT],
            MemoryType.CORRECTION: [StorageTarget.MEM0_USER, StorageTarget.MEM0_AGENT],
        }
        return targets.get(memory_type, [StorageTarget.MEM0_USER])
    
    # =========================================================================
    # EXECUTION
    # =========================================================================
    
    def execute(self, update: MemoryUpdate, decision: ControllerDecision) -> Dict[str, Any]:
        """
        Execute the memory update based on decision.
        
        Returns execution results.
        """
        results = {
            "action": decision.action.value,
            "targets_updated": [],
            "errors": [],
        }
        
        if decision.action == UpdateAction.IGNORE:
            return results
        
        if decision.action == UpdateAction.CONFLICT:
            # Queue for human resolution
            self._queue_conflict(update, decision)
            results["conflict_queued"] = True
            return results
        
        # Execute updates
        for target in decision.targets:
            try:
                if target == StorageTarget.MEM0_USER:
                    self._store_mem0_user(update, decision)
                    results["targets_updated"].append("mem0_user")
                
                elif target == StorageTarget.MEM0_AGENT:
                    self._store_mem0_agent(update, decision)
                    results["targets_updated"].append("mem0_agent")
                
                elif target == StorageTarget.QDRANT:
                    self._store_qdrant(update, decision)
                    results["targets_updated"].append("qdrant")
                
                elif target == StorageTarget.JSON_BACKUP:
                    self._store_json(update, decision)
                    results["targets_updated"].append("json_backup")
                    
            except Exception as e:
                results["errors"].append(f"{target.value}: {str(e)}")
        
        # Log decision
        self._log_decision(update, decision, results)
        
        return results
    
    def _store_mem0_user(self, update: MemoryUpdate, decision: ControllerDecision):
        """Store to Mem0 with user_id."""
        mem0 = self._get_mem0()
        if not mem0 or not update.identity_id:
            return
        
        if decision.action == UpdateAction.UPDATE and decision.existing_memory_id:
            # Update existing
            mem0.update(
                memory_id=decision.existing_memory_id,
                data=update.content,
            )
        else:
            # Create new
            mem0.add(
                messages=[{"role": "user", "content": update.content}],
                user_id=update.identity_id,
                metadata={
                    "type": update.memory_type.value,
                    "source": update.source,
                    "confidence": update.confidence,
                    "created_at": datetime.now().isoformat(),
                    **update.metadata,
                }
            )
    
    def _store_mem0_agent(self, update: MemoryUpdate, decision: ControllerDecision):
        """Store to Mem0 with agent_id."""
        mem0 = self._get_mem0()
        if not mem0:
            return
        
        agent_id = f"ira_{update.memory_type.value}"
        if update.entity_name:
            agent_id = f"entity_{update.entity_name.lower().replace(' ', '_')}"[:50]
        
        mem0.add(
            messages=[{"role": "user", "content": update.content}],
            agent_id=agent_id,
            metadata={
                "type": update.memory_type.value,
                "source": update.source,
                "confidence": update.confidence,
                "created_at": datetime.now().isoformat(),
                **update.metadata,
            }
        )
    
    def _store_qdrant(self, update: MemoryUpdate, decision: ControllerDecision):
        """Store to Qdrant for vector search."""
        qdrant = self._get_qdrant()
        if not qdrant:
            return
        
        # Get embedding
        try:
            import voyageai
            voyage = voyageai.Client(api_key=os.environ.get("VOYAGE_API_KEY"))
            embedding = voyage.embed([update.content], model="voyage-3", input_type="document").embeddings[0]
        except Exception as e:
            logger.error(f"Voyage embedding failed: {e}")
            return
        
        # Store
        import uuid
        from qdrant_client.models import PointStruct
        
        collection = {
            MemoryType.ENTITY_FACT: "ira_chunks_v4_voyage",
            MemoryType.DREAM_INSIGHT: "ira_dream_knowledge_v1",
        }.get(update.memory_type, "ira_memories")
        
        qdrant.upsert(
            collection_name=collection,
            points=[PointStruct(
                id=uuid.uuid4().hex,
                vector=embedding,
                payload={
                    "text": update.content,
                    "raw_text": update.content,
                    "type": update.memory_type.value,
                    "source": update.source,
                    "confidence": update.confidence,
                    "indexed_at": datetime.now().isoformat(),
                    **update.metadata,
                }
            )]
        )
    
    def _store_json(self, update: MemoryUpdate, decision: ControllerDecision):
        """Store to local JSON backup."""
        from .mem0_storage import DATA_DIR
        
        file_map = {
            MemoryType.EPISODE: "episodes.json",
            MemoryType.PROCEDURE: "procedures.json",
            MemoryType.RELATIONSHIP: "relationships.json",
        }
        
        filename = file_map.get(update.memory_type)
        if not filename:
            return
        
        filepath = DATA_DIR / filename
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load existing
        data = {}
        if filepath.exists():
            try:
                data = json.loads(filepath.read_text())
            except (json.JSONDecodeError, IOError, OSError):
                pass
        
        # Add new entry
        entry_id = hashlib.md5(update.content.encode()).hexdigest()[:12]
        
        if update.memory_type == MemoryType.EPISODE:
            user_id = update.identity_id or "unknown"
            if user_id not in data:
                data[user_id] = {}
            data[user_id][entry_id] = {
                "id": entry_id,
                "content": update.content,
                "timestamp": datetime.now().isoformat(),
                "source": update.source,
                **update.metadata,
            }
        else:
            data[entry_id] = {
                "id": entry_id,
                "content": update.content,
                "created_at": datetime.now().isoformat(),
                "source": update.source,
                **update.metadata,
            }
        
        filepath.write_text(json.dumps(data, indent=2, default=str))
    
    def _queue_conflict(self, update: MemoryUpdate, decision: ControllerDecision):
        """Queue conflict for human resolution."""
        conflict_file = PROJECT_ROOT / "data" / "conflicts.json"
        conflict_file.parent.mkdir(parents=True, exist_ok=True)
        
        conflicts = []
        if conflict_file.exists():
            try:
                conflicts = json.loads(conflict_file.read_text())
            except (json.JSONDecodeError, IOError, OSError):
                pass
        
        conflicts.append({
            "id": hashlib.md5(update.content.encode()).hexdigest()[:12],
            "new_content": update.content,
            "existing_id": decision.existing_memory_id,
            "identity_id": update.identity_id,
            "source": update.source,
            "timestamp": datetime.now().isoformat(),
            "resolved": False,
        })
        
        conflict_file.write_text(json.dumps(conflicts, indent=2))
    
    def _log_decision(self, update: MemoryUpdate, decision: ControllerDecision, results: Dict):
        """Log decision for debugging/auditing."""
        self._decision_log.append({
            "timestamp": datetime.now().isoformat(),
            "content_preview": update.content[:100],
            "memory_type": update.memory_type.value,
            "action": decision.action.value,
            "targets": [t.value for t in decision.targets],
            "reason": decision.reason,
            "success": len(results.get("errors", [])) == 0,
        })
        
        # Keep only last 100 decisions in memory
        self._decision_log = self._decision_log[-100:]
    
    # =========================================================================
    # HIGH-LEVEL API
    # =========================================================================
    
    def process(
        self,
        content: str,
        source: str,
        identity_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Process a memory update end-to-end.
        
        This is the main entry point for all memory updates.
        
        Args:
            content: The content to store
            source: Where it came from (telegram, email, dream, correction)
            identity_id: User identifier (for user memories)
            entity_name: Entity name (for entity memories)
            context: Additional context for classification
            
        Returns:
            Results dict with action taken and targets updated
        """
        context = context or {}
        context["source"] = source
        
        # Resolve identity if needed
        if identity_id:
            try:
                from .unified_mem0 import get_unified_mem0
                service = get_unified_mem0()
                identity_id = service.identity.resolve(identity_id)
            except (ImportError, AttributeError):
                pass
        
        # Classify
        memory_type = self.classify(content, context)
        
        # Create update object
        update = MemoryUpdate(
            content=content,
            memory_type=memory_type,
            source=source,
            identity_id=identity_id,
            entity_name=entity_name,
            metadata=context.get("metadata", {}),
        )
        
        # Decide
        decision = self.decide(update)
        
        # Execute
        results = self.execute(update, decision)
        results["memory_type"] = memory_type.value
        results["decision_reason"] = decision.reason
        
        return results
    
    def get_decision_log(self) -> List[Dict]:
        """Get recent decisions for debugging."""
        return self._decision_log


# =============================================================================
# SINGLETON
# =============================================================================

_controller: Optional[MemoryController] = None


def get_memory_controller() -> MemoryController:
    """Get or create the memory controller."""
    global _controller
    if _controller is None:
        _controller = MemoryController()
    return _controller


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def remember(
    content: str,
    source: str,
    identity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    **context
) -> Dict[str, Any]:
    """
    Convenience function to store a memory.
    
    Usage:
        from memory_controller import remember
        
        # User fact
        remember("John prefers email over phone", "telegram", identity_id="john@example.com")
        
        # Entity fact
        remember("EcoForm 3220 has 3200mm forming width", "dream", entity_name="EcoForm 3220")
        
        # Correction
        remember("Actually, EcoForm has 3500mm width", "telegram", is_correction=True)
    """
    controller = get_memory_controller()
    return controller.process(
        content=content,
        source=source,
        identity_id=identity_id,
        entity_name=entity_name,
        context=context,
    )


def correct(
    content: str,
    identity_id: Optional[str] = None,
    source: str = "telegram",
) -> Dict[str, Any]:
    """
    Convenience function for corrections.
    
    Usage:
        correct("The price is $50,000, not $45,000", identity_id="john@example.com")
    """
    controller = get_memory_controller()
    return controller.process(
        content=content,
        source=source,
        identity_id=identity_id,
        context={"is_correction": True},
    )


@dataclass
class RememberResult:
    """Result of remember_conversation, compatible with old MemoryAddResult."""
    added: List[str] = field(default_factory=list)
    updated: List[str] = field(default_factory=list)
    ignored: int = 0
    conflicts: int = 0
    

def remember_conversation(
    user_message: str,
    assistant_response: str,
    user_id: str,
    channel: str = "telegram",
) -> RememberResult:
    """
    Process a conversation exchange through the Memory Controller.
    
    This is the DROP-IN REPLACEMENT for mem0.remember_from_message().
    
    Instead of directly calling Mem0, this:
    1. Extracts facts from both messages
    2. Checks for duplicates/conflicts
    3. Routes to appropriate storage
    
    Usage (in telegram_gateway.py or email_handler.py):
        # OLD:
        # mem0_result = mem0.remember_from_message(user_msg, response, user_id, channel)
        
        # NEW:
        from memory_controller import remember_conversation
        result = remember_conversation(user_msg, response, user_id, channel)
    """
    controller = get_memory_controller()
    result = RememberResult()
    
    # Process user message
    if user_message and len(user_message.strip()) > 10:
        user_result = controller.process(
            content=user_message,
            source=channel,
            identity_id=user_id,
            context={"role": "user", "is_about_user": True},
        )
        
        if user_result["action"] == "create":
            result.added.append(user_result.get("memory_type", "unknown"))
        elif user_result["action"] == "reinforce":
            result.updated.append(user_result.get("memory_type", "unknown"))
        elif user_result["action"] == "ignore":
            result.ignored += 1
        elif user_result["action"] == "conflict":
            result.conflicts += 1
    
    # Process assistant response (may contain entity facts)
    if assistant_response and len(assistant_response.strip()) > 20:
        # Extract any entity mentions from response
        import re
        entity_patterns = [
            r'(EcoForm|ThermoLine|PF\d+|Machinecraft)\s+(\w+)',
            r'(\d+(?:mm|cm|m|kg|kW))',  # Specifications
        ]
        
        has_entity = any(re.search(p, assistant_response) for p in entity_patterns)
        
        if has_entity:
            response_result = controller.process(
                content=assistant_response[:500],  # Limit length
                source=channel,
                identity_id=user_id,
                context={"role": "assistant", "has_entity": True},
            )
            
            if response_result["action"] == "create":
                result.added.append(response_result.get("memory_type", "unknown"))
    
    return result


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    controller = get_memory_controller()
    
    if len(sys.argv) < 2:
        print("Memory Controller")
        print("=" * 40)
        print("Usage:")
        print("  python memory_controller.py test")
        print("  python memory_controller.py log")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "test":
        # Test the controller
        test_cases = [
            ("John works at ABC Corp", "telegram", "john@example.com", None),
            ("EcoForm 3220 has 3200mm forming width", "dream", None, "EcoForm 3220"),
            ("ok", "telegram", "john@example.com", None),  # Should be ignored
            ("Actually, EcoForm has 3500mm width", "telegram", None, "EcoForm 3220"),  # Correction
        ]
        
        for content, source, identity, entity in test_cases:
            print(f"\nProcessing: '{content[:50]}...'")
            result = controller.process(content, source, identity, entity)
            print(f"  Type: {result['memory_type']}")
            print(f"  Action: {result['action']}")
            print(f"  Reason: {result['decision_reason']}")
            print(f"  Targets: {result.get('targets_updated', [])}")
    
    elif cmd == "log":
        log = controller.get_decision_log()
        print(f"Recent decisions: {len(log)}")
        for entry in log[-10:]:
            print(f"  [{entry['timestamp'][:16]}] {entry['action']}: {entry['content_preview'][:40]}...")
