"""
Memory System - Cognitive Architecture for Ira

╔════════════════════════════════════════════════════════════════════╗
║  COGNITIVE MEMORY ARCHITECTURE v2.0                                ║
║                                                                    ║
║  Declarative Memory:                                               ║
║  - persistent_memory: Semantic facts (WHAT)                        ║
║  - episodic_memory: Events with time (WHEN/WHERE)                  ║
║                                                                    ║
║  Procedural Memory:                                                ║
║  - procedural_memory: Learned skills/workflows (HOW)               ║
║                                                                    ║
║  Executive Functions:                                              ║
║  - metacognition: Knowing what you know (CONFIDENCE)               ║
║  - memory_trigger: Attention gating (WHEN to retrieve)             ║
║  - memory_weaver: Context formatting (FORMAT)                      ║
║  - memory_reasoning: Inner monologue (THINK)                       ║
║                                                                    ║
║  Orchestration (NEW - Brain Engineering Fixes):                    ║
║  - brain_orchestrator: Unified cognitive pipeline                  ║
║  - async_brain: Parallel processing for speed                      ║
║  - unified_decay: Single source of truth for decay                 ║
║  - episodic_consolidator: Episode → Semantic transfer              ║
║                                                                    ║
║  Maintenance:                                                      ║
║  - memory_intelligence: Scoring, themes                            ║
║  - consolidation_job: Background maintenance                       ║
╚════════════════════════════════════════════════════════════════════╝
"""
from .persistent_memory import PersistentMemory, UserMemory, EntityMemory, get_persistent_memory
from .memory_service import MemoryService, ConversationState, ContextPack, get_memory_service
from .memory_trigger import MemoryTrigger, TriggerDecision, should_retrieve_memory, get_memory_trigger
from .memory_intelligence import MemoryIntelligence, MemoryWithScore, get_memory_intelligence
from .memory_weaver import MemoryWeaver, WovenContext, WeaveStrategy, get_memory_weaver
from .memory_reasoning import MemoryReasoner, ReasoningTrace, reason_with_memories, get_memory_reasoner
from .procedural_memory import ProceduralMemory, Procedure, ProcedureStep, get_procedural_memory
from .episodic_memory import EpisodicMemory, Episode, EpisodeType, get_episodic_memory
from .metacognition import MetaCognition, KnowledgeAssessment, KnowledgeState, assess_knowledge, get_metacognition
from .document_ingestor import DocumentIngestor, IngestionResult
from .conflict_clarifier import ConflictQueue, TelegramClarifier
from .unified_memory import UnifiedMemoryService, get_unified_memory

# Mem0 - Modern AI Memory Layer (replaces PostgreSQL for user memories)
from .mem0_memory import Mem0MemoryService, Memory as Mem0Memory, get_mem0_service

# Note: BrainOrchestrator has been deprecated. Use ChiefOfStaffAgent instead:
#   from src.agents.chief_of_staff import get_chief_of_staff
#   response = await get_chief_of_staff().process_message(message, identity_id)

from .unified_decay import UnifiedDecayManager, DecayConfig, DecayResult, decay_memories, boost_memory, get_decay_manager
from .episodic_consolidator import EpisodicConsolidator, ConsolidationResult, run_consolidation, get_consolidator

# Unified Architecture (NEW - PostgreSQL Replacement)
from .unified_mem0 import UnifiedMem0Service, IdentityResolver, get_unified_mem0
from .mem0_storage import Mem0Storage, EpisodicMem0Store, ProceduralMem0Store, RelationshipMem0Store, get_mem0_storage
from .memory_backend import get_episodic_store, get_procedural_store, get_relationship_store

# Memory Controller (NEW - Intelligent Update Orchestration)
from .memory_controller import (
    MemoryController, MemoryType, UpdateAction, StorageTarget,
    MemoryUpdate, ControllerDecision, RememberResult,
    get_memory_controller, remember, correct, remember_conversation
)

__all__ = [
    # Semantic memory (WHAT - facts)
    "PersistentMemory",
    "UserMemory", 
    "EntityMemory",
    "get_persistent_memory",
    # Episodic memory (WHEN/WHERE - events with time)
    "EpisodicMemory",
    "Episode",
    "EpisodeType",
    "get_episodic_memory",
    # Procedural memory (HOW - skills/workflows)
    "ProceduralMemory",
    "Procedure",
    "ProcedureStep",
    "get_procedural_memory",
    # Meta-cognition (knowing what you know)
    "MetaCognition",
    "KnowledgeAssessment",
    "KnowledgeState",
    "assess_knowledge",
    "get_metacognition",
    # Conversation state
    "MemoryService",
    "ConversationState",
    "ContextPack",
    "get_memory_service",
    # Attention gating (WHEN to retrieve)
    "MemoryTrigger",
    "TriggerDecision",
    "should_retrieve_memory",
    "get_memory_trigger",
    # Context formatting (HOW to format)
    "MemoryWeaver",
    "WovenContext",
    "WeaveStrategy",
    "get_memory_weaver",
    # Inner monologue (THINK)
    "MemoryReasoner",
    "ReasoningTrace",
    "reason_with_memories",
    "get_memory_reasoner",
    # Advanced operations
    "MemoryIntelligence",
    "MemoryWithScore",
    "get_memory_intelligence",
    # Document ingestion
    "DocumentIngestor",
    "IngestionResult",
    # Conflict resolution
    "ConflictQueue",
    "TelegramClarifier",
    # Mem0 - Modern AI Memory (replaces PostgreSQL)
    "Mem0MemoryService",
    "Mem0Memory",
    "get_mem0_service",
    # Unified Memory (Mem0 primary + PostgreSQL fallback)
    "UnifiedMemoryService",
    "get_unified_memory",
    # Unified Decay (NEW - single source of truth)
    "UnifiedDecayManager",
    "DecayConfig",
    "DecayResult",
    "decay_memories",
    "boost_memory",
    "get_decay_manager",
    # Episodic Consolidation (NEW - episode → semantic)
    "EpisodicConsolidator",
    "ConsolidationResult",
    "run_consolidation",
    "get_consolidator",
    # Unified Architecture (NEW - PostgreSQL Replacement)
    "UnifiedMem0Service",
    "IdentityResolver",
    "get_unified_mem0",
    "Mem0Storage",
    "EpisodicMem0Store",
    "ProceduralMem0Store",
    "RelationshipMem0Store",
    "get_mem0_storage",
    "get_episodic_store",
    "get_procedural_store",
    "get_relationship_store",
    # Memory Controller (intelligent update orchestration)
    "MemoryController",
    "MemoryType",
    "UpdateAction",
    "StorageTarget",
    "MemoryUpdate",
    "ControllerDecision",
    "RememberResult",
    "get_memory_controller",
    "remember",
    "correct",
    "remember_conversation",
]
