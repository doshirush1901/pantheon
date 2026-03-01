#!/usr/bin/env python3
"""
IRA AGENT - Unified Agent Coordinator

╔════════════════════════════════════════════════════════════════════════════╗
║  ⚠️  DEPRECATED - KEPT FOR BACKWARD COMPATIBILITY ONLY                     ║
║                                                                            ║
║  This agent class has been REPLACED by the 4-Pipeline System:              ║
║    1. query_analysis_pipeline.py    - Intent & entity extraction          ║
║    2. deep_research_pipeline.py     - Multi-source answer generation      ║
║    3. reply_packaging_pipeline.py   - MBB-quality reply formatting        ║
║    4. feedback_processing_pipeline.py - Learning from corrections         ║
║                                                                            ║
║  Master orchestrator: ira_pipeline_orchestrator.py                        ║
║                                                                            ║
║  This file is kept because:                                                ║
║    - openclaw/agents/ira/__init__.py imports IraAgent                     ║
║    - tools/query.py uses get_agent()                                      ║
║                                                                            ║
║  For new integrations, use ira_pipeline_orchestrator.py directly.         ║
║  DO NOT ADD NEW FEATURES HERE. Use the pipeline system instead.           ║
╚════════════════════════════════════════════════════════════════════════════╝

HISTORICAL: Unified Agent Coordinator for IRA

╔════════════════════════════════════════════════════════════════════════════╗
║                         INTELLIGENT REVENUE ASSISTANT                       ║
║                                                                            ║
║  This was the central coordinator for all Ira capabilities:                ║
║                                                                            ║
║  CHANNELS:                                                                 ║
║    - Telegram (primary interactive)                                        ║
║    - Email (async, formal)                                                 ║
║    - API (programmatic access)                                             ║
║                                                                            ║
║  BRAIN:                                                                    ║
║    - BrainOrchestrator (unified cognitive pipeline)                        ║
║    - Memory (semantic, episodic, procedural)                               ║
║    - RAG (knowledge retrieval)                                             ║
║    - Conversation (coreference, entities, emotion)                         ║
║                                                                            ║
║  IDENTITY:                                                                 ║
║    - Cross-channel identity resolution                                     ║
║    - Unified contact management                                            ║
║                                                                            ║
║  STATE:                                                                    ║
║    - Agent-level configuration                                             ║
║    - Session management                                                    ║
║    - Health monitoring                                                     ║
╚════════════════════════════════════════════════════════════════════════════╝

Usage:
    from openclaw.agents.ira.agent import IraAgent, get_agent
    
    agent = get_agent()
    response = agent.process("What's the price for PF1?", 
                             channel="telegram", 
                             user_id="123456")
"""

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
import threading

# Setup paths
AGENT_DIR = Path(__file__).parent
SRC_DIR = AGENT_DIR / "src"  # Renamed from "skills" to "src" during OpenClaw migration
CORE_DIR = AGENT_DIR / "core"
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

# Add all source directories to path
for src_subdir in ["brain", "memory", "conversation", "identity", "common"]:
    sys.path.insert(0, str(SRC_DIR / src_subdir))
sys.path.insert(0, str(CORE_DIR))
sys.path.insert(0, str(AGENT_DIR))

# Import centralized config (loads .env automatically)
try:
    from config import (
        DATABASE_URL, QDRANT_URL, OPENAI_API_KEY, VOYAGE_API_KEY,
        load_soul, get_soul_excerpt, FEATURES, validate_config,
        get_logger
    )
    CONFIG_AVAILABLE = True
    _logger = get_logger("ira.agent")
except ImportError:
    import logging
    CONFIG_AVAILABLE = False
    _logger = logging.getLogger("ira.agent")
    if not _logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
        _logger.addHandler(handler)
        _logger.setLevel(logging.INFO)
    # Fallback: Load environment manually (override to ensure fresh values)
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip('"')
                os.environ[key] = value


# =============================================================================
# MODULE IMPORTS WITH AVAILABILITY FLAGS
# =============================================================================

# State Manager (unified state persistence)
try:
    from state import get_state_manager, record_request, record_error
    STATE_AVAILABLE = True
except ImportError:
    STATE_AVAILABLE = False
    _logger.warning("State manager not available")

# Production Resilience Layer
try:
    from resilience import (
        get_system_health_summary, get_service_status, check_all_services,
        with_resilience, openai_breaker, qdrant_breaker, 
        CircuitBreakerOpenError
    )
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False
    # Define placeholder exception
    class CircuitBreakerOpenError(Exception):
        def __init__(self, message="", service="", state=None):
            super().__init__(message)
            self.service = service
            self.state = state
    _logger.warning("Resilience layer not available")

# Centralized Error Monitoring
try:
    from error_monitor import (
        track_error, track_warning, alert_critical, 
        with_error_tracking, get_monitor as get_error_monitor
    )
    ERROR_MONITOR_AVAILABLE = True
except ImportError:
    ERROR_MONITOR_AVAILABLE = False
    def track_error(component, error, context=None, severity="error"): pass
    def track_warning(component, message, context=None): pass
    def alert_critical(message, context=None): pass
    _logger.warning("Error monitor not available")

# Brain State Classes and Orchestrator (from centralized location)
try:
    from src.core.brain_state import BrainState, ProcessingPhase, AttentionManager
    from src.core.brain_orchestrator import get_brain
    BRAIN_AVAILABLE = True
except ImportError as e:
    BRAIN_AVAILABLE = False
    BrainState = None
    get_brain = None
    _logger.warning(f"Brain modules not available: {e}")

# Unified Identity
try:
    from unified_identity import UnifiedIdentityService, Contact
    IDENTITY_AVAILABLE = True
except ImportError:
    IDENTITY_AVAILABLE = False
    _logger.warning("Identity service not available")

# Memory Service
try:
    from memory_service import MemoryService, get_memory_service
    MEMORY_SERVICE_AVAILABLE = True
except ImportError:
    MEMORY_SERVICE_AVAILABLE = False
    _logger.warning("Memory service not available")

# Persistent Memory
try:
    from persistent_memory import get_persistent_memory, PersistentMemory
    PERSISTENT_MEMORY_AVAILABLE = True
except ImportError:
    PERSISTENT_MEMORY_AVAILABLE = False

# Episodic Memory
try:
    from episodic_memory import get_episodic_memory, EpisodeType
    EPISODIC_AVAILABLE = True
except ImportError:
    EPISODIC_AVAILABLE = False

# Conversational Enhancer
try:
    from replika_integration import ConversationalEnhancer, create_enhancer
    CONVERSATION_AVAILABLE = True
except ImportError as e:
    CONVERSATION_AVAILABLE = False
    _logger.warning(f"Conversational enhancer not available: {e}")

# Coreference Resolution
try:
    from coreference import CoreferenceResolver
    COREFERENCE_AVAILABLE = True
except ImportError:
    COREFERENCE_AVAILABLE = False

# Entity Extraction
try:
    from entity_extractor import EntityExtractor
    ENTITY_AVAILABLE = True
except ImportError:
    ENTITY_AVAILABLE = False

# Response Generation
try:
    from generate_answer import generate_answer, ContextPack
    GENERATOR_AVAILABLE = True
except ImportError:
    GENERATOR_AVAILABLE = False
    _logger.warning("Response generator not available")

# RAG Retrieval
try:
    # Use qdrant_retriever which has a standalone retrieve() function
    from qdrant_retriever import retrieve as rag_retrieve, RetrievalResult
    RAG_AVAILABLE = True
except ImportError:
    try:
        # Fallback to unified_retriever class
        from unified_retriever import UnifiedRetriever
        _unified_retriever = UnifiedRetriever()
        def rag_retrieve(query: str, limit: int = 10, **kwargs):
            result = _unified_retriever.retrieve(query, top_k=limit)
            return {"citations": [r.__dict__ for r in result.results]}
        RAG_AVAILABLE = True
    except ImportError:
        RAG_AVAILABLE = False
        _logger.warning("RAG retrieval not available")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class Channel(Enum):
    """Supported communication channels."""
    TELEGRAM = "telegram"
    EMAIL = "email"
    API = "api"
    CLI = "cli"


class AgentState(Enum):
    """Agent operational states."""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    DEGRADED = "degraded"
    SHUTDOWN = "shutdown"


@dataclass
class AgentConfig:
    """Agent configuration."""
    name: str = "Ira"
    version: str = "2.0.0"
    
    # Feature flags
    enable_brain: bool = True
    enable_memory: bool = True
    enable_conversation: bool = True
    enable_rag: bool = True
    enable_proactive: bool = True
    
    # Limits
    max_response_length: int = 4000
    max_context_items: int = 10
    response_timeout_sec: int = 30
    
    # Channels
    default_channel: Channel = Channel.TELEGRAM
    enabled_channels: List[Channel] = field(default_factory=lambda: [
        Channel.TELEGRAM, Channel.EMAIL, Channel.API
    ])
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "enable_brain": self.enable_brain,
            "enable_memory": self.enable_memory,
            "enable_conversation": self.enable_conversation,
            "enable_rag": self.enable_rag,
            "max_response_length": self.max_response_length,
        }


@dataclass
class AgentRequest:
    """Unified request to the agent."""
    message: str
    channel: Channel
    user_id: str
    thread_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Channel-specific fields
    reply_to_message_id: Optional[str] = None  # Telegram
    email_subject: Optional[str] = None        # Email
    email_thread_id: Optional[str] = None      # Email


@dataclass
class AgentResponse:
    """Unified response from the agent."""
    message: str
    channel: Channel
    success: bool = True
    
    # Processing metadata
    brain_state: Optional[BrainState] = None
    processing_time_ms: float = 0.0
    tokens_used: int = 0
    
    # Context used
    memories_used: int = 0
    rag_chunks_used: int = 0
    procedure_used: Optional[str] = None
    
    # Actions triggered
    actions: List[Dict] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    # Errors
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "message": self.message,
            "channel": self.channel.value,
            "success": self.success,
            "processing_time_ms": self.processing_time_ms,
            "memories_used": self.memories_used,
            "rag_chunks_used": self.rag_chunks_used,
            "procedure_used": self.procedure_used,
            "errors": self.errors,
        }


@dataclass
class AgentHealth:
    """Agent health status."""
    state: AgentState = AgentState.INITIALIZING
    uptime_seconds: float = 0.0
    requests_processed: int = 0
    errors_count: int = 0
    last_request_time: Optional[datetime] = None
    
    # Module health
    brain_healthy: bool = True
    memory_healthy: bool = True
    rag_healthy: bool = True
    
    # Performance metrics
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "state": self.state.value,
            "uptime_seconds": self.uptime_seconds,
            "requests_processed": self.requests_processed,
            "errors_count": self.errors_count,
            "brain_healthy": self.brain_healthy,
            "memory_healthy": self.memory_healthy,
            "rag_healthy": self.rag_healthy,
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
        }


# =============================================================================
# IRA AGENT
# =============================================================================

class IraAgent:
    """
    Unified Ira Agent - Central Coordinator.
    
    This class coordinates all Ira capabilities across channels,
    providing a single interface for intelligent interactions.
    """
    
    def __init__(self, config: AgentConfig = None, strict: bool = False):
        """
        Initialize the IRA agent.
        
        Args:
            config: Agent configuration
            strict: If True, raise RuntimeError if critical modules fail to initialize.
                   If False (default), continue with degraded functionality.
        """
        self.config = config or AgentConfig()
        self.health = AgentHealth()
        self._start_time = datetime.now()
        self._response_times: List[float] = []
        self._lock = threading.Lock()
        self._init_errors: List[str] = []
        
        # Initialize modules
        self._init_modules()
        
        # Validate initialization
        self._validate_initialization(strict=strict)
        
        self.health.state = AgentState.READY
        _logger.info(f"{self.config.name} v{self.config.version} initialized")
    
    def _validate_initialization(self, strict: bool = False):
        """
        Validate that critical modules initialized successfully.
        
        Args:
            strict: If True, raise RuntimeError on critical failures
        """
        critical_failures = []
        warnings = []
        
        # Check critical modules (required for basic operation)
        if self.config.enable_brain:
            if not BRAIN_AVAILABLE:
                critical_failures.append("Brain module not available (import failed)")
            elif not self.health.brain_healthy:
                critical_failures.append("Brain module failed to initialize")
            elif self._brain is None:
                critical_failures.append("Brain module is None after initialization")
        
        # Check important modules (degraded without them)
        if self.config.enable_memory and not self.health.memory_healthy:
            warnings.append("Memory module unhealthy - memory features disabled")
        
        if not IDENTITY_AVAILABLE or self._identity is None:
            warnings.append("Identity service unavailable - cross-channel linking disabled")
        
        # Check config validity
        if CONFIG_AVAILABLE:
            config_status = validate_config()
            missing_keys = [k for k, v in config_status.items() if not v]
            if missing_keys:
                warnings.append(f"Missing config: {', '.join(missing_keys)}")
        
        # Report warnings
        for warning in warnings:
            _logger.warning(warning)
        
        # Handle critical failures
        if critical_failures:
            self._init_errors = critical_failures
            error_msg = "Critical initialization failures:\n" + "\n".join(f"  - {f}" for f in critical_failures)
            
            if strict:
                raise RuntimeError(error_msg)
            else:
                _logger.error(error_msg)
                _logger.warning("Continuing with degraded functionality. Use strict=True to fail fast.")
    
    def _init_modules(self):
        """Initialize all agent modules."""
        # Brain orchestrator
        self._brain = None
        if BRAIN_AVAILABLE and self.config.enable_brain:
            try:
                self._brain = get_brain()
                _logger.info(f"Brain modules: {self._brain.modules}")
            except Exception as e:
                self.health.brain_healthy = False
                _logger.error(f"Brain init error: {e}")
        
        # Identity service
        self._identity = None
        if IDENTITY_AVAILABLE:
            try:
                self._identity = UnifiedIdentityService()
            except Exception as e:
                _logger.error(f"Identity init error: {e}")
        
        # Memory service
        self._memory = None
        if MEMORY_SERVICE_AVAILABLE and self.config.enable_memory:
            try:
                self._memory = get_memory_service()
            except Exception as e:
                self.health.memory_healthy = False
                _logger.error(f"Memory init error: {e}")
        
        # Conversational enhancer
        self._enhancer = None
        if CONVERSATION_AVAILABLE and self.config.enable_conversation:
            try:
                self._enhancer = create_enhancer()
            except Exception as e:
                _logger.error(f"Enhancer init error: {e}")
        
        # Coreference resolver
        self._coreference = None
        if COREFERENCE_AVAILABLE:
            try:
                self._coreference = CoreferenceResolver()
            except Exception as e:
                _logger.error(f"Coreference init error: {e}")
        
        # Entity extractor
        self._entity_extractor = None
        if ENTITY_AVAILABLE:
            try:
                self._entity_extractor = EntityExtractor()
            except Exception as e:
                _logger.error(f"Entity extractor init error: {e}")
    
    # =========================================================================
    # CORE PROCESSING
    # =========================================================================
    
    def process(
        self,
        message: str,
        channel: str = "telegram",
        user_id: str = "unknown",
        thread_id: Optional[str] = None,
        **kwargs
    ) -> AgentResponse:
        """
        Process a message through the unified agent pipeline.
        
        This is the main entry point for all channels.
        
        Args:
            message: User message
            channel: Channel name (telegram, email, api)
            user_id: User identifier (chat_id, email, etc.)
            thread_id: Conversation thread ID
            **kwargs: Channel-specific parameters
        
        Returns:
            AgentResponse with the generated response
        """
        start_time = time.time()

        # Bind trace context for observability (correlates Athena→Clio→Vera logs)
        try:
            from openclaw.agents.ira.core.ira_logging import start_trace
            start_trace(channel=channel, user_id=user_id)
        except ImportError:
            pass

        # Build request
        request = AgentRequest(
            message=message,
            channel=Channel(channel) if isinstance(channel, str) else channel,
            user_id=user_id,
            thread_id=thread_id or user_id,
            metadata=kwargs
        )
        
        self.health.state = AgentState.PROCESSING
        
        try:
            response = self._process_request(request)
            
            # Record successful request
            if STATE_AVAILABLE:
                record_request(request.channel.value)
                
        except CircuitBreakerOpenError as e:
            # Circuit breaker is open - service unavailable
            response = AgentResponse(
                message="I'm experiencing connectivity issues with some of my services. "
                        "Please try again in a few moments.",
                channel=request.channel,
                success=False,
                errors=[f"Service unavailable: {e.service}"]
            )
            self.health.errors_count += 1
            track_warning("agent", f"Circuit breaker open: {e.service}", {"request": message[:100]})
            
        except Exception as e:
            response = AgentResponse(
                message=f"I encountered an error processing your request. Please try again.",
                channel=request.channel,
                success=False,
                errors=[str(e)]
            )
            self.health.errors_count += 1
            
            # Centralized error monitoring
            track_error(
                "agent.process",
                e,
                {
                    "channel": request.channel.value,
                    "user_id": request.user_id[:50] if request.user_id else "unknown",
                    "message_preview": message[:100] if message else "",
                },
                severity="error"
            )
            
            # Record error in state
            if STATE_AVAILABLE:
                record_error(request.channel.value, str(e))
        
        # Update stats
        processing_time = (time.time() - start_time) * 1000
        response.processing_time_ms = processing_time
        
        with self._lock:
            self._response_times.append(processing_time)
            if len(self._response_times) > 100:
                self._response_times = self._response_times[-100:]
            self.health.requests_processed += 1
            self.health.last_request_time = datetime.now()
            self.health.avg_response_time_ms = sum(self._response_times) / len(self._response_times)
        
        self.health.state = AgentState.READY
        return response
    
    def _process_request(self, request: AgentRequest) -> AgentResponse:
        """Internal request processing pipeline."""
        
        # Step 1: Resolve identity
        identity_id = self._resolve_identity(request)
        
        # Step 2: Get conversation context
        context = self._get_conversation_context(request, identity_id)
        
        # Step 3: Resolve coreferences
        resolved_message, coreference_subs = self._resolve_coreferences(
            request.message, context
        )
        
        # Step 4: Extract entities
        entities = self._extract_entities(resolved_message)
        
        # Step 5: Process through brain
        brain_state = self._process_brain(
            message=resolved_message,
            identity_id=identity_id,
            context={
                "channel": request.channel.value,
                "thread_id": request.thread_id,
                "entities": entities,
                "coreference_subs": coreference_subs,
                **context
            }
        )
        
        # Step 6: Retrieve RAG context
        rag_chunks = self._retrieve_rag(resolved_message)
        
        # Step 7: Generate response
        response_text, tokens = self._generate_response(
            request=request,
            brain_state=brain_state,
            rag_chunks=rag_chunks,
            identity_id=identity_id,
            context=context
        )
        
        # Step 8: Apply conversational enhancements
        enhanced_response = self._enhance_response(
            response_text, request, identity_id, context
        )
        
        # Step 9: Record episodic memory
        self._record_episode(request, enhanced_response, identity_id, entities)
        
        # Step 10: Get proactive suggestions
        suggestions = self._get_suggestions(request, identity_id, brain_state)
        
        return AgentResponse(
            message=enhanced_response,
            channel=request.channel,
            success=True,
            brain_state=brain_state,
            tokens_used=tokens,
            memories_used=len(brain_state.user_memories) if brain_state else 0,
            rag_chunks_used=len(rag_chunks),
            procedure_used=brain_state.matched_procedure.name if brain_state and brain_state.matched_procedure else None,
            suggestions=suggestions
        )
    
    # =========================================================================
    # PIPELINE STEPS
    # =========================================================================
    
    def _resolve_identity(self, request: AgentRequest) -> str:
        """Resolve user identity across channels."""
        if not self._identity:
            return request.user_id
        
        try:
            # UnifiedIdentityService.resolve() returns contact_id directly (string)
            contact_id = self._identity.resolve(
                channel=request.channel.value,
                identifier=request.user_id,
                create_if_missing=True
            )
            if contact_id:
                return contact_id
        except Exception as e:
            _logger.error(f"Identity resolution error: {e}")
        
        return request.user_id
    
    def _get_conversation_context(
        self,
        request: AgentRequest,
        identity_id: str
    ) -> Dict[str, Any]:
        """Get conversation context from memory service.
        
        Propagates all fields from the memory service context pack so that
        downstream consumers (generate_answer, etc.) have full context
        including is_internal, identity, open_questions, and current_stage.
        """
        context = {
            "recent_messages": [],
            "rolling_summary": "",
            "current_mode": "general",
            "key_entities": {},
            "is_internal": False,
            "identity": None,
            "open_questions": [],
            "current_stage": "new",
            "kg_facts": [],
        }
        
        if not self._memory:
            return context
        
        try:
            context_pack = self._memory.get_context_pack(
                request.channel.value,
                request.thread_id or identity_id,
                request.message
            )
            if context_pack:
                context["recent_messages"] = context_pack.recent_messages or []
                context["rolling_summary"] = context_pack.rolling_summary or ""
                context["current_mode"] = getattr(context_pack, 'current_mode', None) or "general"
                context["key_entities"] = context_pack.key_entities or {}
                context["is_internal"] = getattr(context_pack, 'is_internal', False)
                context["identity"] = getattr(context_pack, 'identity', None)
                context["open_questions"] = getattr(context_pack, 'open_questions', []) or []
                context["current_stage"] = getattr(context_pack, 'current_stage', "new") or "new"
                context["kg_facts"] = getattr(context_pack, 'kg_facts', []) or []
        except Exception as e:
            _logger.error(f"Context retrieval error: {e}")
        
        return context
    
    def _resolve_coreferences(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Tuple[str, List[Dict]]:
        """Resolve pronouns and references in message."""
        if not self._coreference:
            return message, []
        
        try:
            # CoreferenceResolver.resolve(query, context)
            resolved = self._coreference.resolve(
                query=message,
                context={
                    "recent_messages": context.get("recent_messages", []),
                    "key_entities": context.get("key_entities", {}),
                    "last_topic": context.get("current_mode", ""),
                }
            )
            # Returns ResolvedQuery with .resolved and .substitutions
            return resolved.resolved, resolved.substitutions
        except Exception as e:
            _logger.error(f"Coreference error: {e}")
        
        return message, []
    
    def _extract_entities(self, message: str) -> Dict[str, List[str]]:
        """Extract entities from message."""
        if not self._entity_extractor:
            return {}
        
        try:
            # ExtractedEntities has machines, applications, materials, dimensions
            extracted = self._entity_extractor.extract(message)
            return {
                "machines": extracted.machines,
                "applications": extracted.applications,
                "materials": extracted.materials,
                "dimensions": extracted.dimensions,
            }
        except Exception as e:
            _logger.error(f"Entity extraction error: {e}")
        
        return {}
    
    def _process_brain(
        self,
        message: str,
        identity_id: str,
        context: Dict[str, Any]
    ) -> Optional[BrainState]:
        """Process through brain orchestrator."""
        if not self._brain:
            return None
        
        try:
            return self._brain.process(
                message=message,
                identity_id=identity_id,
                context=context,
                channel=context.get("channel", "telegram")
            )
        except Exception as e:
            _logger.error(f"Brain processing error: {e}")
            self.health.brain_healthy = False
        
        return None
    
    def _retrieve_rag(self, query: str, limit: int = 8) -> List[Dict]:
        """Retrieve RAG context."""
        if not RAG_AVAILABLE or not self.config.enable_rag:
            return []
        
        try:
            results = rag_retrieve(query, top_k=limit)
            
            # Handle both RetrievalResult object and dict formats
            if hasattr(results, 'citations'):
                # RetrievalResult from qdrant_retriever
                citations = results.citations[:limit]
                return [c.to_dict() if hasattr(c, 'to_dict') else c for c in citations]
            elif isinstance(results, dict):
                # Dict format from unified_retriever fallback
                return results.get("citations", [])[:limit]
            else:
                return []
        except Exception as e:
            _logger.error(f"RAG retrieval error: {e}")
            self.health.rag_healthy = False
        
        return []
    
    def _generate_response(
        self,
        request: AgentRequest,
        brain_state: Optional[BrainState],
        rag_chunks: List[Dict],
        identity_id: str,
        context: Dict[str, Any]
    ) -> Tuple[str, int]:
        """Generate response using the answer generator.
        
        Builds a full context pack matching the Telegram gateway's richness:
        memory service fields, Mem0, cross-channel context, soul context, and
        conversational enhancement are all included so email and Telegram
        replies go through identical data paths.
        """
        if not GENERATOR_AVAILABLE:
            return "I'm unable to generate a response at the moment.", 0
        
        try:
            # Load soul/identity if available
            soul_context = ""
            if CONFIG_AVAILABLE:
                try:
                    soul_context = get_soul_excerpt(1500)
                except Exception as e:
                    _logger.warning("Soul context load failed: %s", e, exc_info=True)
            
            # Merge identity dict with the identity_id
            identity_info = context.get("identity") or {}
            if not identity_info:
                identity_info = {"identity_id": identity_id}
            elif "identity_id" not in identity_info:
                identity_info["identity_id"] = identity_id
            
            # Build context pack with ALL fields (matching Telegram gateway)
            context_pack = {
                "recent_messages": context.get("recent_messages", []),
                "rolling_summary": context.get("rolling_summary", ""),
                "current_mode": context.get("current_mode", "general"),
                "current_stage": context.get("current_stage", "new"),
                "key_entities": context.get("key_entities", {}),
                "open_questions": context.get("open_questions", []),
                "kg_facts": context.get("kg_facts", []),
                "rag_chunks": [
                    {
                        "text": (c.get("text", "") if isinstance(c, dict) else getattr(c, "text", ""))[:500],
                        "filename": c.get("citation", "unknown") if isinstance(c, dict) else getattr(c, "filename", "unknown"),
                        "score": c.get("score", 0.5) if isinstance(c, dict) else getattr(c, "score", 0.5)
                    }
                    for c in rag_chunks
                ],
                "identity": identity_info,
                "is_internal": context.get("is_internal", False),
                "thread_id": request.thread_id,
                "soul_context": soul_context,
            }
            
            # Add brain state context
            if brain_state:
                context_pack["user_memories"] = [
                    m.to_dict() if hasattr(m, 'to_dict') else m 
                    for m in brain_state.user_memories
                ]
                context_pack["entity_memories"] = [
                    m.to_dict() if hasattr(m, 'to_dict') else m 
                    for m in brain_state.entity_memories
                ]
                context_pack["memory_guidance"] = brain_state.memory_guidance
                context_pack["reasoning_context"] = brain_state.reasoning_context
                context_pack["metacognitive_guidance"] = brain_state.metacognitive_guidance
                context_pack["episodic_context"] = brain_state.episodic_context
                context_pack["procedure_guidance"] = brain_state.procedure_guidance
            
            # Mem0 semantic memory retrieval
            mem0_context = ""
            try:
                from mem0_service import get_mem0_service
                mem0_svc = get_mem0_service()
                if mem0_svc:
                    mem0_context = mem0_svc.get_relevant_context(
                        query=request.message,
                        user_id=identity_id or "unknown",
                        limit=5,
                    )
            except ImportError:
                pass
            except Exception as e:
                _logger.warning(f"Mem0 retrieval error (non-fatal): {e}")
            context_pack["mem0_context"] = mem0_context
            
            # Cross-channel context
            cross_channel_context = ""
            try:
                from cross_channel_context import get_cross_channel_context
                cc_data = get_cross_channel_context(
                    channel=request.channel.value,
                    identifier=request.thread_id or identity_id or "",
                    include_email=(request.channel.value != "email"),
                    include_telegram=(request.channel.value != "telegram"),
                )
                if cc_data:
                    cross_channel_context = cc_data.to_context_string()
            except ImportError:
                pass
            except Exception as e:
                _logger.warning(f"Cross-channel context error (non-fatal): {e}")
            context_pack["cross_channel_context"] = cross_channel_context
            
            # Conversational enhancement (Replika-style)
            if self._enhancer:
                try:
                    user_name = ""
                    if identity_info:
                        user_name = identity_info.get("name", "")
                    
                    enhancement = self._enhancer.process_message(
                        contact_id=identity_id,
                        message=request.message,
                        name=user_name,
                        channel=request.channel.value,
                        additional_context={
                            "stage": context.get("current_stage", "new"),
                            "mode": context.get("current_mode", "general"),
                        },
                    )
                    if enhancement:
                        context_pack["conversational_enhancement"] = {
                            "emotional_state": getattr(
                                getattr(enhancement, 'emotional_reading', None),
                                'primary_state', None
                            ),
                            "warmth": (enhancement.relationship_context or {}).get("warmth", "stranger")
                                if hasattr(enhancement, 'relationship_context') else "stranger",
                            "suggested_opener": getattr(enhancement, 'suggested_opener', ""),
                            "prompt_additions": getattr(enhancement, 'prompt_additions', []),
                            "milestones": getattr(enhancement, 'milestones_to_celebrate', []),
                        }
                        # Normalize emotional_state to string
                        es = context_pack["conversational_enhancement"]["emotional_state"]
                        if hasattr(es, 'value'):
                            context_pack["conversational_enhancement"]["emotional_state"] = es.value
                except Exception as e:
                    _logger.warning(f"Conversational enhancement error (non-fatal): {e}")
            
            result = generate_answer(
                intent=request.message,
                context_pack=context_pack,
                channel=request.channel.value
            )
            
            tokens = result.debug_info.get("tokens_used", 0) if result.debug_info else 0
            return result.text, tokens
            
        except Exception as e:
            _logger.error(f"Generation error: {e}")
        
        return "I encountered an issue generating a response.", 0
    
    def _enhance_response(
        self,
        response: str,
        request: AgentRequest,
        identity_id: str,
        context: Dict[str, Any]
    ) -> str:
        """Apply conversational enhancements."""
        if not self._enhancer:
            return response
        
        try:
            enhancement = self._enhancer.process_message(
                contact_id=identity_id,
                message=request.message,
                channel=request.channel.value
            )
            
            # Apply emotional calibration
            # ConversationalEnhancement is a dataclass, use attribute access
            emotional_state = getattr(enhancement, 'emotional_state', None)
            if emotional_state and emotional_state != "neutral":
                # The enhancer already provides calibration guidance
                pass
            
            return response
            
        except Exception as e:
            _logger.error(f"Enhancement error: {e}")
        
        return response
    
    def _record_episode(
        self,
        request: AgentRequest,
        response: str,
        identity_id: str,
        entities: Dict[str, List[str]]
    ):
        """Record interaction as episodic memory."""
        if not EPISODIC_AVAILABLE:
            return
        
        try:
            em = get_episodic_memory()
            # Use machine names and applications as key topics
            key_topics = entities.get("machines", [])[:3]
            entities_mentioned = entities.get("applications", [])[:3] + entities.get("materials", [])[:3]
            
            em.record_episode(
                identity_id=identity_id,
                channel=request.channel.value,
                summary=f"User asked: {request.message[:100]}",
                episode_type=EpisodeType.CONVERSATION,
                key_topics=key_topics,
                entities_mentioned=entities_mentioned,
                user_intent=request.message[:200]
            )
        except Exception as e:
            _logger.error(f"Episode recording error: {e}")
    
    def _get_suggestions(
        self,
        request: AgentRequest,
        identity_id: str,
        brain_state: Optional[BrainState]
    ) -> List[str]:
        """Get proactive suggestions for follow-up."""
        suggestions = []
        
        # Add procedure-based suggestions
        if brain_state and brain_state.matched_procedure:
            suggestions.append(f"Following {brain_state.matched_procedure.name} workflow")
        
        # Add knowledge gap suggestions
        if brain_state and brain_state.knowledge_assessment:
            if brain_state.knowledge_assessment.gaps:
                for gap in brain_state.knowledge_assessment.gaps[:2]:
                    suggestions.append(f"Need more info: {gap}")
        
        return suggestions
    
    # =========================================================================
    # CHANNEL-SPECIFIC HELPERS
    # =========================================================================
    
    def process_telegram(
        self,
        message: str,
        chat_id: str,
        **kwargs
    ) -> AgentResponse:
        """Process a Telegram message."""
        return self.process(
            message=message,
            channel="telegram",
            user_id=str(chat_id),
            **kwargs
        )
    
    def process_email(
        self,
        body: str,
        from_email: str,
        subject: str = "",
        thread_id: Optional[str] = None,
        **kwargs
    ) -> AgentResponse:
        """Process an email."""
        return self.process(
            message=body,
            channel="email",
            user_id=from_email.lower(),
            thread_id=thread_id,
            email_subject=subject,
            **kwargs
        )
    
    def process_api(
        self,
        message: str,
        api_key: str,
        **kwargs
    ) -> AgentResponse:
        """Process an API request."""
        return self.process(
            message=message,
            channel="api",
            user_id=api_key,
            **kwargs
        )
    
    # =========================================================================
    # MANAGEMENT
    # =========================================================================
    
    def get_health(self) -> AgentHealth:
        """Get agent health status."""
        self.health.uptime_seconds = (datetime.now() - self._start_time).total_seconds()
        return self.health
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive health status of all external dependencies.
        
        Checks status of:
        - OpenAI API
        - Voyage API
        - Mem0
        - Qdrant
        - PostgreSQL
        
        Returns:
            JSON object with status of each service:
            {
                "overall_status": "healthy" | "degraded" | "unhealthy",
                "health_score": 80.0,
                "services": {
                    "openai": "operational" | "degraded" | "down",
                    "voyage": "operational",
                    "mem0": "operational",
                    "qdrant": "operational",
                    "postgres": "degraded"
                },
                "agent": {
                    "state": "ready",
                    "uptime_seconds": 12345.6,
                    "requests_processed": 100,
                    "error_rate": 0.02
                }
            }
        """
        result = {
            "overall_status": "unknown",
            "health_score": 0.0,
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "agent": {},
        }
        
        # Get service status from resilience layer
        if RESILIENCE_AVAILABLE:
            try:
                health_summary = get_system_health_summary()
                result["overall_status"] = health_summary.get("overall_status", "unknown")
                result["health_score"] = health_summary.get("health_score", 0.0)
                result["services"] = health_summary.get("services", {})
                result["circuit_breakers"] = health_summary.get("circuit_breakers", {})
            except Exception as e:
                _logger.error(f"Error getting system health: {e}")
                result["services"]["resilience"] = "error"
        else:
            # Fallback: Check basic connectivity
            result["services"] = {
                "openai": self._check_openai_basic(),
                "qdrant": self._check_qdrant_basic(),
                "postgres": self._check_postgres_basic(),
                "voyage": "unknown",
                "mem0": "unknown",
            }
            
            # Calculate health score
            operational = sum(1 for s in result["services"].values() if s == "operational")
            total = len(result["services"])
            result["health_score"] = (operational / total * 100) if total > 0 else 0
            
            if all(s == "operational" for s in result["services"].values()):
                result["overall_status"] = "healthy"
            elif any(s == "down" for s in result["services"].values()):
                result["overall_status"] = "unhealthy"
            else:
                result["overall_status"] = "degraded"
        
        # Add agent-specific health metrics
        agent_health = self.get_health()
        error_rate = (
            agent_health.errors_count / agent_health.requests_processed
            if agent_health.requests_processed > 0 else 0.0
        )
        
        result["agent"] = {
            "state": agent_health.state.value,
            "uptime_seconds": round(agent_health.uptime_seconds, 1),
            "requests_processed": agent_health.requests_processed,
            "errors_count": agent_health.errors_count,
            "error_rate": round(error_rate, 4),
            "avg_response_time_ms": round(agent_health.avg_response_time_ms, 1),
            "brain_healthy": agent_health.brain_healthy,
            "memory_healthy": agent_health.memory_healthy,
            "rag_healthy": agent_health.rag_healthy,
        }
        
        return result
    
    def _check_openai_basic(self) -> str:
        """Basic OpenAI connectivity check."""
        try:
            if not OPENAI_API_KEY:
                return "down"
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            client.models.list()
            return "operational"
        except Exception:
            return "down"
    
    def _check_qdrant_basic(self) -> str:
        """Basic Qdrant connectivity check."""
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(url=QDRANT_URL if CONFIG_AVAILABLE else "http://localhost:6333")
            client.get_collections()
            return "operational"
        except Exception:
            return "down"
    
    def _check_postgres_basic(self) -> str:
        """Basic PostgreSQL connectivity check."""
        try:
            import psycopg2
            db_url = DATABASE_URL if CONFIG_AVAILABLE else "postgresql://localhost:5432/ira_db"
            conn = psycopg2.connect(db_url, connect_timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            return "operational"
        except Exception:
            return "degraded"  # PostgreSQL is optional
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed agent status."""
        health = self.get_health()
        
        # Get persistent state
        persistent_state = {}
        if STATE_AVAILABLE:
            try:
                state_manager = get_state_manager()
                persistent_state = state_manager.to_dict()
            except Exception as e:
                persistent_state = {"error": str(e)}
        
        return {
            "agent": {
                "name": self.config.name,
                "version": self.config.version,
                "state": health.state.value,
            },
            "health": health.to_dict(),
            "system_health": self.get_system_health(),
            "modules": {
                "brain": BRAIN_AVAILABLE and self.health.brain_healthy,
                "memory": MEMORY_SERVICE_AVAILABLE and self.health.memory_healthy,
                "rag": RAG_AVAILABLE and self.health.rag_healthy,
                "conversation": CONVERSATION_AVAILABLE,
                "identity": IDENTITY_AVAILABLE,
                "coreference": COREFERENCE_AVAILABLE,
                "entity_extraction": ENTITY_AVAILABLE,
                "state_manager": STATE_AVAILABLE,
                "resilience": RESILIENCE_AVAILABLE,
                "error_monitor": ERROR_MONITOR_AVAILABLE,
            },
            "brain_modules": self._brain.modules if self._brain else {},
            "persistent_state": persistent_state,
            "config": self.config.to_dict(),
        }
    
    def link_identity(
        self,
        channel1: str,
        id1: str,
        channel2: str,
        id2: str,
        confidence: float = 0.9
    ) -> bool:
        """Link identities across channels."""
        if not self._identity:
            return False
        
        try:
            self._identity.link(channel1, id1, channel2, id2, confidence)
            return True
        except Exception as e:
            print(f"[agent] Identity linking error: {e}")
        
        return False


# =============================================================================
# SINGLETON AND CONVENIENCE
# =============================================================================

_agent: Optional[IraAgent] = None


def get_agent(config: AgentConfig = None) -> IraAgent:
    """Get singleton agent instance."""
    global _agent
    if _agent is None:
        _agent = IraAgent(config)
    return _agent


def process(
    message: str,
    channel: str = "telegram",
    user_id: str = "unknown",
    **kwargs
) -> AgentResponse:
    """Process a message through the agent."""
    return get_agent().process(message, channel, user_id, **kwargs)


# =============================================================================
# CLI
# =============================================================================

def main():
    """Run agent in CLI mode for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ira Agent CLI")
    parser.add_argument("--status", action="store_true", help="Show agent status")
    parser.add_argument("--message", "-m", type=str, help="Message to process")
    parser.add_argument("--channel", "-c", type=str, default="cli", help="Channel")
    parser.add_argument("--user", "-u", type=str, default="cli_user", help="User ID")
    args = parser.parse_args()
    
    agent = get_agent()
    
    if args.status:
        status = agent.get_status()
        print(json.dumps(status, indent=2))
        return
    
    if args.message:
        response = agent.process(
            message=args.message,
            channel=args.channel,
            user_id=args.user
        )
        print(f"\n{response.message}")
        print(f"\n[{response.processing_time_ms:.0f}ms | {response.memories_used} memories | {response.rag_chunks_used} chunks]")
        return
    
    # Interactive mode
    print(f"\n{'='*60}")
    print(f"  {agent.config.name} v{agent.config.version} - Interactive CLI")
    print(f"{'='*60}")
    print("Type 'quit' to exit, 'status' for agent status\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == "quit":
                print("Goodbye!")
                break
            
            if user_input.lower() == "status":
                status = agent.get_status()
                print(json.dumps(status, indent=2))
                continue
            
            response = agent.process(
                message=user_input,
                channel="cli",
                user_id="cli_user"
            )
            
            print(f"\nIra: {response.message}")
            print(f"[{response.processing_time_ms:.0f}ms]")
            print()
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
