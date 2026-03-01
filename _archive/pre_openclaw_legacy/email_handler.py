#!/usr/bin/env python3
"""
EMAIL CHANNEL HANDLER - Full Conversational Email Processing

╔════════════════════════════════════════════════════════════════════╗
║  Processes incoming emails with FULL conversational intelligence   ║
║  Cross-channel memory sharing with Telegram via identity linking   ║
║                                                                    ║
║  UPGRADED: Now matches Telegram's conversational capabilities      ║
║  - Coreference resolution ("it", "that machine")                   ║
║  - Entity extraction and tracking                                  ║
║  - Structured logging with tracing                                 ║
║  - Feedback learning from corrections                              ║
║  - Memory analytics integration                                    ║
╚════════════════════════════════════════════════════════════════════╝

Usage:
    from email_handler import EmailHandler
    handler = EmailHandler()
    response = handler.process_email(email_data)
"""

import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Setup paths
SKILL_DIR = Path(__file__).parent
SKILLS_DIR = SKILL_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
BRAIN_DIR = SKILLS_DIR / "brain"
MEMORY_DIR = SKILLS_DIR / "memory"
CONVERSATION_DIR = SKILLS_DIR / "conversation"

# Add paths for imports
sys.path.insert(0, str(AGENT_DIR))  # For config
sys.path.insert(0, str(BRAIN_DIR))
sys.path.insert(0, str(MEMORY_DIR))
sys.path.insert(0, str(CONVERSATION_DIR))
sys.path.insert(0, str(SKILL_DIR))  # For preprocessor/postprocessor

# Import centralized config
try:
    from config import DATABASE_URL, OPENAI_API_KEY
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    # Fallback: Load environment manually
    PROJECT_ROOT = AGENT_DIR.parent.parent.parent
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))

# BrainOrchestrator - Unified cognitive pipeline (NEW)
try:
    from brain_orchestrator import BrainOrchestrator, BrainState
    BRAIN_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    BRAIN_ORCHESTRATOR_AVAILABLE = False
    logger.warning("BrainOrchestrator not available - using legacy processing")

# Email Preprocessor (NEW)
try:
    from email_preprocessor import EmailPreprocessor, preprocess_email
    PREPROCESSOR_AVAILABLE = True
except ImportError:
    PREPROCESSOR_AVAILABLE = False
    logger.warning("EmailPreprocessor not available")

# Email Postprocessor (NEW)
try:
    from email_postprocessor import EmailPostprocessor, format_email_response, format_reply_subject
    POSTPROCESSOR_AVAILABLE = True
except ImportError:
    POSTPROCESSOR_AVAILABLE = False
    logger.warning("EmailPostprocessor not available")


# Mem0 - Modern AI Memory (Primary)
try:
    from mem0_memory import get_mem0_service, Mem0MemoryService
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    logger.warning("Mem0 memory not available")

# Memory Controller - Intelligent memory orchestration (NEW)
try:
    from memory_controller import remember_conversation, get_memory_controller
    MEMORY_CONTROLLER_AVAILABLE = True
except ImportError:
    MEMORY_CONTROLLER_AVAILABLE = False
    logger.warning("Memory controller not available")

# Persistent Memory integration (Fallback)
try:
    from persistent_memory import get_persistent_memory, PersistentMemory
    PERSISTENT_MEMORY_AVAILABLE = True
except ImportError:
    PERSISTENT_MEMORY_AVAILABLE = False
    logger.warning("Persistent memory not available")

# Memory Service integration
try:
    from memory_service import get_memory_service, MemoryService
    MEMORY_SERVICE_AVAILABLE = True
except ImportError:
    MEMORY_SERVICE_AVAILABLE = False
    logger.warning("Memory service not available")

# Real-time Indexer integration
try:
    sys.path.insert(0, str(BRAIN_DIR))
    from realtime_indexer import index_new_email
    REALTIME_INDEXER_AVAILABLE = True
except ImportError:
    REALTIME_INDEXER_AVAILABLE = False
    logger.warning("Real-time indexer not available")

# Structured Logging with Request Tracing
try:
    from structured_logger import (
        get_logger, start_trace, end_trace, log_event,
        log_error, PerformanceTimer, log_request
    )
    STRUCTURED_LOGGING_AVAILABLE = True
    _email_logger = get_logger("ira.email")
except ImportError:
    STRUCTURED_LOGGING_AVAILABLE = False
    _email_logger = None
    logger.warning("Structured logging not available")

# Feedback Learner for continuous improvement
try:
    from feedback_learner import (
        process_correction, enhance_response_with_learning, get_learning_stats
    )
    FEEDBACK_LEARNER_AVAILABLE = True
except ImportError:
    FEEDBACK_LEARNER_AVAILABLE = False
    logger.warning("Feedback learner not available")

# Coreference Resolution
try:
    from coreference import CoreferenceResolver
    COREFERENCE_AVAILABLE = True
except ImportError:
    COREFERENCE_AVAILABLE = False
    logger.warning("Coreference resolver not available")

# Entity Extraction
try:
    from entity_extractor import EntityExtractor
    ENTITY_EXTRACTOR_AVAILABLE = True
except ImportError:
    ENTITY_EXTRACTOR_AVAILABLE = False
    logger.warning("Entity extractor not available")

# Conversation State Management
try:
    from goal_manager import GoalManager
    from state_controller import StateController, Stage
    from proactive import ProactiveEngine
    from response_strategy import StrategyEngine
    CONVERSATION_MODULES_AVAILABLE = True
except ImportError:
    CONVERSATION_MODULES_AVAILABLE = False
    logger.warning("Conversation modules not available")

# Emotional Intelligence (Replika-style)
try:
    from replika_integration import ConversationalEnhancer, create_enhancer
    CONVERSATIONAL_ENHANCER_AVAILABLE = True
    _conversational_enhancer = None
except ImportError:
    CONVERSATIONAL_ENHANCER_AVAILABLE = False
    _conversational_enhancer = None
    logger.warning("Conversational enhancer not available")


def get_conversational_enhancer() -> Optional[ConversationalEnhancer]:
    """Get or create the conversational enhancer singleton."""
    global _conversational_enhancer
    if CONVERSATIONAL_ENHANCER_AVAILABLE and _conversational_enhancer is None:
        try:
            _conversational_enhancer = create_enhancer()
            logger.info("Initialized conversational enhancer")
        except Exception as e:
            logger.error("Failed to create enhancer: %s", e)
    return _conversational_enhancer


@dataclass
class EmailData:
    """Structured email data."""
    message_id: str
    thread_id: str
    from_email: str
    from_name: str
    to_email: str
    subject: str
    body: str
    date: datetime
    is_reply: bool = False
    in_reply_to: str = None


@dataclass
class EmailResponse:
    """Response to send."""
    to: str
    subject: str
    body: str
    thread_id: str = None
    in_reply_to: str = None


class EmailHandler:
    """
    Handles email processing with persistent memory integration.
    
    Now supports two processing modes:
    - Unified mode (NEW): Uses BrainOrchestrator for cognitive processing
    - Legacy mode: Uses manual 15-step process (fallback)
    """
    
    def __init__(self, use_brain_orchestrator: bool = True):
        self.internal_domains = ["machinecraft.in", "machinecraft.co"]
        self._last_response = ""
        
        # Initialize unified processing components (NEW)
        self.use_unified = use_brain_orchestrator and BRAIN_ORCHESTRATOR_AVAILABLE
        
        if self.use_unified:
            self.brain = BrainOrchestrator()
            self.preprocessor = EmailPreprocessor() if PREPROCESSOR_AVAILABLE else None
            self.postprocessor = EmailPostprocessor() if POSTPROCESSOR_AVAILABLE else None
            logger.info("Using unified BrainOrchestrator mode")
        else:
            self.brain = None
            self.preprocessor = None
            self.postprocessor = None
            logger.info("Using legacy processing mode")
        
    def is_internal(self, email: str) -> bool:
        """Check if email is internal."""
        if not email:
            return False
        domain = email.split("@")[-1].lower()
        return domain in self.internal_domains
    
    def extract_email_identity(self, email_data: EmailData) -> str:
        """Extract identity ID for the email sender."""
        from_email = email_data.from_email.lower()
        
        # Get or create identity
        identity_id = from_email  # Use email as default identity
        
        if MEMORY_SERVICE_AVAILABLE:
            try:
                memory = get_memory_service()
                existing_id = memory.get_identity_id("email", from_email)
                if existing_id:
                    identity_id = existing_id
                    logger.debug("Found existing identity: %s", identity_id)
            except Exception as e:
                logger.error("Identity lookup error: %s", e)
        
        return identity_id
    
    def process_email(
        self,
        email_data: EmailData,
        generate_response: bool = True
    ) -> Optional[EmailResponse]:
        """
        Process an incoming email with FULL conversational intelligence.
        
        Uses unified BrainOrchestrator mode when available (NEW),
        falls back to legacy 15-step processing otherwise.
        
        Returns EmailResponse or None.
        """
        # Route to unified processing if available
        if self.use_unified and self.brain:
            return self._process_email_unified(email_data, generate_response)
        
        # Legacy processing below
        return self._process_email_legacy(email_data, generate_response)
    
    def _process_email_unified(
        self,
        email_data: EmailData,
        generate_response: bool = True
    ) -> Optional[EmailResponse]:
        """
        Process email using unified BrainOrchestrator pipeline.
        
        This is the NEW streamlined processing that delegates cognitive work
        to BrainOrchestrator, keeping only email-specific logic here.
        """
        import time
        request_start_time = time.time()
        from_email = email_data.from_email.lower()
        is_internal = self.is_internal(from_email)
        
        # ===== STEP 1: START TRACE =====
        trace_id = None
        if STRUCTURED_LOGGING_AVAILABLE:
            trace_id = start_trace(
                channel="email",
                user_id=from_email,
                thread_id=email_data.thread_id
            )
            log_event("email", "unified_processing_started", {
                "from": from_email,
                "subject": email_data.subject[:50] if email_data.subject else "",
                "is_internal": is_internal
            })
        
        logger.info("Processing email (unified mode) from %s", from_email)
        
        # ===== STEP 2: GET IDENTITY =====
        identity_id = self.extract_email_identity(email_data)
        
        # ===== STEP 3: PREPROCESS EMAIL =====
        email_context = {}
        if self.preprocessor:
            email_context = self.preprocessor.prepare(email_data)
            logger.debug("Preprocessed: intent=%s", email_context.get('email_intent', {}).get('intent', 'unknown'))
        
        # ===== STEP 4: PROCESS THROUGH BRAIN ORCHESTRATOR =====
        brain_state = self.brain.process(
            message=email_context.get("cleaned_body", email_data.body),
            identity_id=identity_id,
            context={
                "thread_id": email_data.thread_id,
                "subject": email_data.subject,
                "from_email": from_email,
                "from_name": email_data.from_name,
                "is_reply": email_data.is_reply,
                "is_internal": is_internal,
                "thread_history": email_context.get("thread_history", []),
                "email_intent": email_context.get("email_intent", {}),
                "mentioned_entities": email_context.get("mentioned_entities", {}),
                "cc_list": email_context.get("cc_list", []),
            },
            channel="email"
        )
        
        logger.info("Brain processing complete: memories=%d, episodic=%s, phase=%s",
                    len(brain_state.user_memories), brain_state.episodes_retrieved, brain_state.phase.value)
        
        # ===== STEP 5: GENERATE RESPONSE =====
        response_text = None
        if generate_response:
            response_text = self._generate_response_from_brain_state(
                email_data=email_data,
                brain_state=brain_state,
                email_context=email_context
            )
            self._last_response = response_text or ""
        
        # ===== STEP 6: POST-PROCESSING (formatting) =====
        if response_text and self.postprocessor:
            # Get warmth from brain state context
            warmth = brain_state.context.get("warmth", "professional")
            response_text = self.postprocessor.format(
                response=response_text,
                email_data=email_data,
                brain_state=brain_state,
                warmth=warmth
            )
        
        # ===== STEP 7: STORE MEMORIES (via Memory Controller) =====
        if MEMORY_CONTROLLER_AVAILABLE and response_text:
            try:
                mem_result = remember_conversation(
                    user_message=f"Subject: {email_data.subject}\n\n{email_data.body}",
                    assistant_response=response_text,
                    user_id=identity_id,
                    channel="email",
                )
                mem_count = len(mem_result.added) + len(mem_result.updated)
                if mem_count > 0:
                    logger.info("MemController: +%d added, ~%d updated", len(mem_result.added), len(mem_result.updated))
                if mem_result.ignored > 0:
                    logger.debug("MemController: %d ignored", mem_result.ignored)
                if mem_result.conflicts > 0:
                    logger.warning("MemController: %d conflicts queued", mem_result.conflicts)
            except Exception as e:
                logger.error("MemController error: %s", e)
                # Fallback to Mem0
                if MEM0_AVAILABLE:
                    try:
                        mem0 = get_mem0_service()
                        mem0.remember_from_message(
                            user_message=f"Subject: {email_data.subject}\n\n{email_data.body}",
                            assistant_response=response_text,
                            user_id=identity_id,
                            channel="email",
                        )
                    except Exception:
                        pass
        elif MEM0_AVAILABLE and response_text:
            # Fallback: Direct Mem0
            try:
                mem0 = get_mem0_service()
                mem0_result = mem0.remember_from_message(
                    user_message=f"Subject: {email_data.subject}\n\n{email_data.body}",
                    assistant_response=response_text,
                    user_id=identity_id,
                    channel="email",
                )
                mem0_count = len(mem0_result.added) + len(mem0_result.updated)
                if mem0_count > 0:
                    logger.info("Mem0: +%d added, ~%d updated", len(mem0_result.added), len(mem0_result.updated))
            except Exception as e:
                logger.error("Mem0 storage error: %s", e)
        
        # ===== STEP 8: INDEX FOR RAG (same as legacy) =====
        if REALTIME_INDEXER_AVAILABLE:
            try:
                company_domain = from_email.split("@")[-1] if "@" in from_email else ""
                index_result = index_new_email(
                    email_id=hash(email_data.message_id) % (10**9),
                    subject=email_data.subject,
                    body=email_data.body,
                    from_email=from_email,
                    to_email=email_data.to_email,
                    date=email_data.date,
                    thread_key=email_data.thread_id,
                    company_domain=company_domain,
                    direction="inbound" if not is_internal else "internal",
                    is_reply=email_data.is_reply,
                )
                if index_result.get("status") == "indexed":
                    logger.info("Indexed %d chunks for RAG", index_result.get('chunks', 0))
            except Exception as e:
                logger.error("Real-time indexing error: %s", e)
        
        # ===== STEP 9: END TRACE AND RETURN =====
        request_duration_ms = (time.time() - request_start_time) * 1000
        
        if response_text:
            if STRUCTURED_LOGGING_AVAILABLE:
                log_event("email", "unified_response_generated", {
                    "duration_ms": round(request_duration_ms, 2),
                    "response_length": len(response_text),
                    "brain_phase": brain_state.phase.value,
                })
                end_trace(success=True)
            
            # Format subject
            subject = email_data.subject or "Your inquiry"
            if self.postprocessor:
                subject = self.postprocessor.format_subject(subject, is_reply=True)
            elif not subject.startswith("Re:"):
                subject = f"Re: {subject}"
            
            return EmailResponse(
                to=from_email,
                subject=subject,
                body=response_text,
                thread_id=email_data.thread_id,
                in_reply_to=email_data.message_id
            )
        
        if STRUCTURED_LOGGING_AVAILABLE:
            end_trace(success=False)
        
        return None
    
    def _generate_response_from_brain_state(
        self,
        email_data: EmailData,
        brain_state,  # BrainState - type hint omitted to avoid import errors
        email_context: Dict[str, Any]
    ) -> Optional[str]:
        """Generate response using brain state context."""
        try:
            from openai import OpenAI
            client = OpenAI()
            
            # Build prompt with brain state context
            system_prompt = self._build_email_system_prompt(email_data, brain_state)
            
            # Build user message with all context
            context_parts = []
            
            # Add cross-channel context (Telegram conversations with this contact)
            try:
                import sys
                sys.path.insert(0, str(SKILLS_DIR / "conversation"))
                from cross_channel_context import get_cross_channel_context
                
                xc_context = get_cross_channel_context(
                    channel="email",
                    identifier=email_data.from_email,
                    include_email=False,  # Don't need email context here
                    include_telegram=True  # Want to see Telegram conversations
                )
                
                if xc_context and xc_context.telegram_messages:
                    tg_parts = []
                    for msg in xc_context.telegram_messages[:5]:
                        tg_parts.append(f"- {msg.get('message', '')[:100]}")
                    if tg_parts:
                        context_parts.append(f"[Recent Telegram Messages from this contact]\n" + "\n".join(tg_parts))
            except Exception as xc_err:
                logger.debug("Cross-channel context error (non-fatal): %s", xc_err)
            
            # Add episodic context
            if brain_state.episodic_context:
                context_parts.append(f"[Previous Interactions]\n{brain_state.episodic_context}")
            
            # Add memory context
            if brain_state.user_memories:
                mem_texts = []
                for m in brain_state.user_memories[:5]:
                    text = m.memory_text if hasattr(m, 'memory_text') else str(m)
                    mem_texts.append(f"- {text}")
                if mem_texts:
                    context_parts.append(f"[User Memories]\n" + "\n".join(mem_texts))
            
            # Add entity memories
            if brain_state.entity_memories:
                ent_texts = []
                for m in brain_state.entity_memories[:5]:
                    text = m.memory_text if hasattr(m, 'memory_text') else str(m)
                    ent_texts.append(f"- {text}")
                if ent_texts:
                    context_parts.append(f"[Entity Context]\n" + "\n".join(ent_texts))
            
            # Add procedural guidance
            if brain_state.procedure_guidance:
                context_parts.append(f"[Suggested Approach]\n{brain_state.procedure_guidance}")
            
            # Add metacognitive guidance
            if brain_state.metacognitive_guidance:
                context_parts.append(f"[Confidence Note]\n{brain_state.metacognitive_guidance}")
            
            # Add competitor intelligence if available
            if hasattr(brain_state, 'competitor_context') and brain_state.competitor_context:
                context_parts.append(f"[COMPETITIVE INTELLIGENCE - Use for positioning]\n{brain_state.competitor_context}")
            
            context_block = "\n\n".join(context_parts) if context_parts else "No additional context available."
            
            user_message = f"""CONTEXT:
{context_block}

EMAIL FROM: {email_data.from_name or email_data.from_email}
SUBJECT: {email_data.subject}

EMAIL BODY:
{email_data.body}

Write a professional, helpful response to this email. Be specific and address their inquiry directly."""
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error("Response generation error: %s", e)
            return None
    
    def _build_email_system_prompt(self, email_data: EmailData, brain_state) -> str:
        """Build system prompt for email response generation."""
        is_internal = self.is_internal(email_data.from_email)
        
        base_prompt = """You are Ira, the AI sales assistant for Machinecraft Technologies, a manufacturer of vacuum forming and thermoforming machines.

Your role is to:
- Answer product inquiries with accurate technical information
- Provide pricing and lead time information when available
- Schedule calls and coordinate with the sales team
- Be professional, helpful, and efficient

Communication style:
- Professional but warm
- Concise and clear
- Use specific data when available
- If unsure, say so and offer to investigate"""
        
        if is_internal:
            base_prompt += "\n\nNote: This is an INTERNAL email from a Machinecraft team member. Be direct and casual."
        
        # Add competitor handling guidance if competitor comparison detected
        if hasattr(brain_state, 'is_competitor_comparison') and brain_state.is_competitor_comparison:
            base_prompt += """

COMPETITOR COMPARISON GUIDANCE:
When the customer mentions competitors, follow these principles:
- Be professional and factual - never disparage competitors directly
- Acknowledge the competitor's reputation where deserved
- Highlight Machinecraft's specific advantages that address the customer's needs
- Focus on value proposition: better price-to-performance, faster delivery, local support
- Emphasize our strengths: customization, application expertise, responsive service
- If asked directly about price comparison, be honest about our position in the market
- Offer to demonstrate our capabilities with a video call or reference visit"""
        
        return base_prompt
    
    def _process_email_legacy(
        self,
        email_data: EmailData,
        generate_response: bool = True
    ) -> Optional[EmailResponse]:
        """
        Legacy email processing with manual 15-step pipeline.
        
        This is the original implementation, kept for fallback.
        """
        request_start_time = time.time()
        from_email = email_data.from_email.lower()
        is_internal = self.is_internal(from_email)
        
        # ===== STEP 1: START TRACE =====
        trace_id = None
        if STRUCTURED_LOGGING_AVAILABLE:
            trace_id = start_trace(
                channel="email",
                user_id=from_email,
                thread_id=email_data.thread_id
            )
            log_event("email", "processing_started", {
                "from": from_email,
                "subject": email_data.subject[:50],
                "is_internal": is_internal
            })
        
        logger.info("Processing email from %s", from_email)
        logger.info("Subject: %s", email_data.subject)
        
        # ===== STEP 2: CHECK FOR CORRECTIONS =====
        if FEEDBACK_LEARNER_AVAILABLE:
            try:
                correction = process_correction(
                    user_message=email_data.body,
                    ira_previous=self._last_response if hasattr(self, '_last_response') else "",
                    context={"thread_id": email_data.thread_id, "from": from_email},
                    source=from_email,
                    channel="email"
                )
                if correction:
                    logger.info("Learned correction: %s", correction.id)
                    if STRUCTURED_LOGGING_AVAILABLE:
                        log_event("learning", "correction_detected", {
                            "correction_id": correction.id,
                            "type": correction.correction_type.value
                        })
            except Exception as e:
                logger.error("Correction check error: %s", e)
        
        # ===== STEP 3: GET IDENTITY =====
        identity_id = self.extract_email_identity(email_data)
        
        # ===== STEP 4: COREFERENCE RESOLUTION =====
        # Resolve pronouns like "it", "that machine" to specific entities
        resolved_body = email_data.body
        coreference_subs = []
        
        if COREFERENCE_AVAILABLE and MEMORY_SERVICE_AVAILABLE:
            try:
                # Get context from memory
                memory = get_memory_service()
                context = memory.get_context_pack("email", email_data.thread_id, email_data.body)
                
                resolver = CoreferenceResolver()
                coref_context = {
                    "key_entities": context.key_entities if context else {},
                    "recent_messages": context.recent_messages if context else []
                }
                
                resolved = resolver.resolve(email_data.body, coref_context)
                if resolved.confidence > 0.7 and resolved.substitutions:
                    resolved_body = resolved.resolved
                    coreference_subs = resolved.substitutions
                    logger.debug("Coreference: %s", coreference_subs)
                    
                    if STRUCTURED_LOGGING_AVAILABLE:
                        log_event("conversation", "coreference_resolved", {
                            "substitutions": len(coreference_subs)
                        })
            except Exception as e:
                logger.error("Coreference error: %s", e)
        
        # ===== STEP 5: ENTITY EXTRACTION =====
        extracted_entities = {}
        if ENTITY_EXTRACTOR_AVAILABLE:
            try:
                extractor = EntityExtractor()
                entities = extractor.extract(email_data.body)
                extracted_entities = entities.to_dict()
                
                if any(extracted_entities.values()):
                    logger.debug("Extracted entities: %s", list(extracted_entities.keys()))
            except Exception as e:
                logger.error("Entity extraction error: %s", e)
        
        # ===== STEP 6: RETRIEVE MEMORIES (Mem0 primary, PostgreSQL fallback) =====
        user_memories = []
        entity_memories = []
        mem0_context = ""
        
        # Use resolved body for better memory retrieval
        query = f"{email_data.subject} {resolved_body[:500]}"
        
        # PRIMARY: Mem0 AI Memory
        if MEM0_AVAILABLE:
            try:
                mem0 = get_mem0_service()
                mem0_results = mem0.search(
                    query=query,
                    user_id=identity_id,
                    limit=5,
                )
                
                if mem0_results:
                    # Convert to expected format
                    for m in mem0_results:
                        class Mem0Wrapper:
                            def __init__(self, mem):
                                self.id = mem.id
                                self.memory_text = mem.memory
                                self.identity_id = mem.user_id
                                self.confidence = mem.score
                                self.memory_type = "fact"
                            def to_dict(self):
                                return {"memory_text": self.memory_text, "confidence": self.confidence}
                        user_memories.append(Mem0Wrapper(m))
                    logger.info("Mem0: Retrieved %d memories", len(user_memories))
                
                # Also get formatted context for prompt
                mem0_context = mem0.get_relevant_context(query, identity_id, limit=5)
                    
            except Exception as e:
                logger.error("Mem0 error: %s", e)
        
        # FALLBACK: PostgreSQL memories
        if not user_memories and PERSISTENT_MEMORY_AVAILABLE:
            try:
                pm = get_persistent_memory()
                
                user_memories = pm.retrieve_for_prompt(
                    identity_id=identity_id,
                    query=query,
                    limit=5
                )
                
                if user_memories:
                    logger.info("PostgreSQL: Retrieved %d user memories", len(user_memories))
                
                entity_memories = pm.retrieve_entity_memories(
                    query=resolved_body[:500],
                    limit=5
                )
                
                if entity_memories:
                    logger.info("PostgreSQL: Retrieved %d entity memories", len(entity_memories))
                    
            except Exception as e:
                logger.error("PostgreSQL memory error: %s", e)
        
        # ===== STEP 6.5: REPLIKA-INSPIRED CONVERSATIONAL ENHANCEMENT =====
        # Process through emotional intelligence, relationship memory, adaptive style, etc.
        conversational_enhancement = None
        conv_enhancer = get_conversational_enhancer()
        
        if conv_enhancer:
            try:
                # Prepare memories for surfacing (combine user + entity memories)
                memories_for_surfacing = []
                if user_memories:
                    for m in user_memories:
                        memories_for_surfacing.append(m.to_dict() if hasattr(m, 'to_dict') else m)
                if entity_memories:
                    for m in entity_memories:
                        memories_for_surfacing.append(m.to_dict() if hasattr(m, 'to_dict') else m)
                
                # Extract topics for pattern tracking
                topics_detected = []
                if extracted_entities:
                    for entity_type, entities in extracted_entities.items():
                        if isinstance(entities, list):
                            topics_detected.extend(entities[:3])
                        elif isinstance(entities, str):
                            topics_detected.append(entities)
                
                # Process message through enhancer (with email for cross-channel linking)
                conversational_enhancement = conv_enhancer.process_message(
                    contact_id=from_email,
                    message=f"{email_data.subject}\n\n{resolved_body}",
                    name=email_data.from_name,
                    channel="email",
                    additional_context={
                        "thread_id": email_data.thread_id,
                        "is_reply": email_data.is_reply,
                        "is_internal": is_internal,
                    },
                    memories=memories_for_surfacing,
                    topics=topics_detected,
                    email=from_email,
                )
                
                # Log enhancement details
                health_status = ""
                if conversational_enhancement.conversation_health:
                    health_status = f", health={conversational_enhancement.conversation_health.health_score:.0f}"
                
                logger.info("Conversational enhancement: emotion=%s, warmth=%s%s",
                            conversational_enhancement.emotional_reading.primary_state.value,
                            conversational_enhancement.relationship_context.get('warmth', 'unknown'),
                            health_status)
                
                if STRUCTURED_LOGGING_AVAILABLE:
                    log_event("conversation", "enhancement_applied", {
                        "emotional_state": conversational_enhancement.emotional_reading.primary_state.value,
                        "warmth": conversational_enhancement.relationship_context.get("warmth", "unknown"),
                        "has_insights": len(conversational_enhancement.insights) > 0,
                    })
                
            except Exception as conv_err:
                logger.debug("Conversational enhancement error (non-fatal): %s", conv_err)
        
        # ===== STEP 7: CONVERSATION MODULES (Goal, Stage, Strategy) =====
        goal_result = None
        stage_guidance = None
        response_strategy = None
        
        if CONVERSATION_MODULES_AVAILABLE:
            try:
                # Goal Manager - track slot filling
                goal_manager = GoalManager()
                goal_result = goal_manager.process_turn(
                    message=resolved_body,
                    intent="email_inquiry",
                    context={"key_entities": extracted_entities}
                )
                
                if goal_result:
                    logger.debug("Goal completion: %.0f%%", goal_result.get('completion', 0))
                
                # State Controller - manage conversation stage
                state_controller = StateController()
                signals = state_controller.detect_signals(resolved_body, goal_result or {})
                state_controller.process_turn(signals)
                stage_guidance = state_controller.get_response_guidance()
                
                # Strategy Engine - determine response tone
                strategy_engine = StrategyEngine()
                response_strategy = strategy_engine.determine_strategy(
                    intent="email_inquiry",
                    stage=stage_guidance.get("stage", "discovery") if stage_guidance else "discovery",
                    channel="email",
                    is_internal=is_internal
                )
                
            except Exception as e:
                logger.error("Conversation modules error: %s", e)
        
        # ===== STEP 8: BUILD CONTEXT PACK =====
        context_pack = self._build_context_pack(
            email_data=email_data,
            identity_id=identity_id,
            is_internal=is_internal,
            user_memories=user_memories,
            entity_memories=entity_memories,
            extracted_entities=extracted_entities,
            coreference_subs=coreference_subs,
            goal_result=goal_result,
            stage_guidance=stage_guidance,
            response_strategy=response_strategy,
            conversational_enhancement=conversational_enhancement
        )
        
        # ===== STEP 9: GENERATE RESPONSE =====
        response_text = None
        if generate_response:
            response_text = self._generate_response(
                email_data=email_data,
                context_pack=context_pack,
                resolved_body=resolved_body
            )
            
            # Store for future correction detection
            self._last_response = response_text
        
        # ===== STEP 10: APPLY LEARNED CORRECTIONS =====
        if FEEDBACK_LEARNER_AVAILABLE and response_text:
            try:
                enhanced = enhance_response_with_learning(
                    f"{email_data.subject} {email_data.body}",
                    response_text
                )
                if enhanced != response_text:
                    response_text = enhanced
                    logger.info("Applied learned corrections to response")
            except Exception as e:
                logger.error("Learning enhancement error: %s", e)
        
        # ===== STEP 11: EXTRACT AND STORE NEW MEMORIES =====
        # PRIMARY: Memory Controller (intelligent routing and deduplication)
        if MEMORY_CONTROLLER_AVAILABLE and response_text:
            try:
                mem_result = remember_conversation(
                    user_message=f"Subject: {email_data.subject}\n\n{email_data.body}",
                    assistant_response=response_text,
                    user_id=identity_id,
                    channel="email",
                )
                
                mem_count = len(mem_result.added) + len(mem_result.updated)
                if mem_count > 0:
                    logger.info("MemController: +%d added, ~%d updated", len(mem_result.added), len(mem_result.updated))
                if mem_result.ignored > 0:
                    logger.debug("MemController: %d ignored", mem_result.ignored)
                    
            except Exception as e:
                logger.error("MemController error: %s", e)
                # Fallback to Mem0
                if MEM0_AVAILABLE:
                    try:
                        mem0 = get_mem0_service()
                        mem0.remember_from_message(
                            user_message=f"Subject: {email_data.subject}\n\n{email_data.body}",
                            assistant_response=response_text,
                            user_id=identity_id,
                            channel="email",
                        )
                    except Exception:
                        pass
        elif MEM0_AVAILABLE and response_text:
            # FALLBACK: Direct Mem0
            try:
                mem0 = get_mem0_service()
                mem0_result = mem0.remember_from_message(
                    user_message=f"Subject: {email_data.subject}\n\n{email_data.body}",
                    assistant_response=response_text,
                    user_id=identity_id,
                    channel="email",
                )
                
                mem0_count = len(mem0_result.added) + len(mem0_result.updated)
                if mem0_count > 0:
                    logger.info("Mem0: +%d added, ~%d updated", len(mem0_result.added), len(mem0_result.updated))
                    
            except Exception as e:
                logger.error("Mem0 storage error: %s", e)
        
        # FALLBACK: PostgreSQL (legacy)
        if PERSISTENT_MEMORY_AVAILABLE and response_text:
            try:
                pm = get_persistent_memory()
                
                created = pm.extract_and_store(
                    identity_id=identity_id,
                    user_message=f"Subject: {email_data.subject}\n\n{email_data.body}",
                    assistant_response=response_text,
                    source_channel="email",
                    source_conversation_id=email_data.thread_id
                )
                
                total = len(created.get("user", [])) + len(created.get("entity", []))
                if total > 0:
                    logger.info("PostgreSQL: Extracted %d memories", total)
                    
            except Exception as e:
                logger.error("PostgreSQL memory error: %s", e)
        
        # ===== STEP 12: UPDATE CONVERSATION STATE =====
        if MEMORY_SERVICE_AVAILABLE and response_text:
            try:
                memory = get_memory_service()
                memory.update_context_after_response(
                    channel="email",
                    identifier=email_data.thread_id,
                    user_message=email_data.body,
                    response_text=response_text,
                    mode="sales" if extracted_entities.get("machines") else "general",
                    intent="email_inquiry",
                    questions_asked=[],  # Could extract from response
                    entities_extracted=extracted_entities
                )
            except Exception as e:
                logger.error("State update error: %s", e)
        
        # ===== STEP 13: INDEX FOR RAG =====
        if REALTIME_INDEXER_AVAILABLE:
            try:
                company_domain = from_email.split("@")[-1] if "@" in from_email else ""
                index_result = index_new_email(
                    email_id=hash(email_data.message_id) % (10**9),  # Stable ID from message_id
                    subject=email_data.subject,
                    body=email_data.body,
                    from_email=from_email,
                    to_email=email_data.to_email,
                    date=email_data.date,
                    thread_key=email_data.thread_id,
                    company_domain=company_domain,
                    direction="inbound" if not is_internal else "internal",
                    is_reply=email_data.is_reply,
                )
                if index_result.get("status") == "indexed":
                    logger.info("Indexed %d chunks for RAG", index_result.get('chunks', 0))
            except Exception as e:
                logger.error("Real-time indexing error: %s", e)
        
        # ===== STEP 14: CHECK PROACTIVE SUGGESTIONS =====
        proactive_note = None
        if PERSISTENT_MEMORY_AVAILABLE and user_memories:
            try:
                pm = get_persistent_memory()
                suggestion = pm.get_proactive_suggestion(
                    identity_id=identity_id,
                    current_context=f"Replying to email about: {email_data.subject}",
                    recent_message=email_data.body[:500]
                )
                
                if suggestion:
                    proactive_note = suggestion.get("suggestion")
                    logger.debug("Proactive suggestion: %s", proactive_note)
            except Exception as e:
                logger.error("Proactive suggestion error: %s", e)
        
        # ===== STEP 15: UPDATE CONVERSATIONAL ENHANCER STATE =====
        # Score conversation quality and update relationship memory
        if conv_enhancer and conversational_enhancement and response_text:
            try:
                # Track which memories were surfaced (if any references made it to response)
                memories_surfaced = []
                if conversational_enhancement.memory_references:
                    for mem_ref in conversational_enhancement.memory_references:
                        if mem_ref.surfacing_text and mem_ref.surfacing_text.lower() in response_text.lower():
                            memories_surfaced.append(mem_ref.memory_id)
                
                # Determine if interaction was positive (email context - assume positive unless correction detected)
                was_positive = True
                if FEEDBACK_LEARNER_AVAILABLE:
                    # If a correction was detected earlier, mark as learning opportunity
                    was_positive = not hasattr(self, '_correction_detected') or not self._correction_detected
                
                # Score conversation quality and update all state
                turn_quality = conv_enhancer.post_response_update(
                    contact_id=from_email,
                    message=f"{email_data.subject}\n\n{email_data.body}",
                    response=response_text,
                    was_positive=was_positive,
                    memories_surfaced=memories_surfaced,
                    response_time_ms=int(request_duration_ms) if 'request_duration_ms' in dir() else 0,
                    had_citations=False,  # Email responses typically don't have inline citations
                )
                
                # Log quality score
                if turn_quality:
                    logger.debug("Turn quality: score=%.0f, signals=%d",
                                turn_quality.overall_score, len(turn_quality.signals))
                    
                    if STRUCTURED_LOGGING_AVAILABLE:
                        log_event("conversation", "quality_scored", {
                            "score": turn_quality.overall_score,
                            "signals_count": len(turn_quality.signals),
                        })
                
            except Exception as conv_update_err:
                logger.debug("Conversational enhancer update error (non-fatal): %s", conv_update_err)
        
        # ===== STEP 16: BUILD AND RETURN RESPONSE =====
        request_duration_ms = (time.time() - request_start_time) * 1000
        
        if response_text:
            # Optionally append proactive note to response
            if proactive_note:
                response_text += f"\n\n---\n💡 {proactive_note}"
            
            # End trace with success
            if STRUCTURED_LOGGING_AVAILABLE:
                log_event("email", "response_generated", {
                    "duration_ms": round(request_duration_ms, 2),
                    "response_length": len(response_text),
                    "coreference_applied": len(coreference_subs) > 0,
                    "entities_extracted": bool(extracted_entities)
                })
                
                log_request(
                    channel="email",
                    user_id=from_email,
                    message=f"{email_data.subject}: {email_data.body[:100]}",
                    response=response_text[:200],
                    duration_ms=request_duration_ms
                )
                
                end_trace(success=True)
            
            return EmailResponse(
                to=from_email,
                subject=f"Re: {email_data.subject}" if not email_data.subject.startswith("Re:") else email_data.subject,
                body=response_text,
                thread_id=email_data.thread_id,
                in_reply_to=email_data.message_id
            )
        
        # End trace with no response
        if STRUCTURED_LOGGING_AVAILABLE:
            log_event("email", "no_response_generated", {"duration_ms": round(request_duration_ms, 2)})
            end_trace(success=False)
        
        return None
    
    def _build_context_pack(
        self,
        email_data: EmailData,
        identity_id: str,
        is_internal: bool,
        user_memories: List,
        entity_memories: List,
        extracted_entities: Dict = None,
        coreference_subs: List = None,
        goal_result: Dict = None,
        stage_guidance: Dict = None,
        response_strategy: Any = None,
        conversational_enhancement: Any = None
    ) -> Dict:
        """Build context pack for response generation with full conversation context."""
        
        # Get conversation history if available
        recent_messages = []
        rolling_summary = ""
        
        if MEMORY_SERVICE_AVAILABLE:
            try:
                memory = get_memory_service()
                context = memory.get_context_pack("email", email_data.thread_id, email_data.body)
                recent_messages = context.recent_messages
                rolling_summary = context.rolling_summary
            except Exception:
                pass
        
        # Determine stage from guidance
        current_stage = "responding"
        if stage_guidance:
            current_stage = stage_guidance.get("stage", "responding")
        
        # Build conversational enhancement dict for context pack
        conv_enhancement_dict = None
        if conversational_enhancement:
            conv_enhancement_dict = {
                "emotional_state": conversational_enhancement.emotional_reading.primary_state.value,
                "emotional_intensity": conversational_enhancement.emotional_reading.intensity.value,
                "warmth": conversational_enhancement.relationship_context.get("warmth", "stranger"),
                "suggested_opener": conversational_enhancement.suggested_opener,
                "prompt_additions": conversational_enhancement.prompt_additions,
                "milestones": conversational_enhancement.milestones_to_celebrate,
                # Extended enhancement fields
                "memory_references": [m.to_dict() for m in conversational_enhancement.memory_references] if conversational_enhancement.memory_references else [],
                "style_guidance": conversational_enhancement.style_profile.get_response_guidance() if conversational_enhancement.style_profile and conversational_enhancement.style_profile.messages_analyzed >= 3 else {},
                "insights": [i.to_dict() for i in conversational_enhancement.insights[:2]] if conversational_enhancement.insights else [],
                "conversation_health": conversational_enhancement.conversation_health.to_dict() if conversational_enhancement.conversation_health else None,
            }
        
        return {
            "recent_messages": recent_messages,
            "rolling_summary": rolling_summary,
            "open_questions": [],
            "key_entities": extracted_entities or {},
            
            "rag_chunks": [],  # Will be populated by generate_answer
            "kg_facts": [],
            
            "identity": {
                "identity_id": identity_id,
                "email": email_data.from_email,
                "name": email_data.from_name
            },
            "is_internal": is_internal,
            "thread_id": email_data.thread_id,
            "current_mode": "email",
            "current_stage": current_stage,
            
            "user_memories": [m.to_dict() for m in user_memories] if user_memories else [],
            "entity_memories": [m.to_dict() for m in entity_memories] if entity_memories else [],
            
            # Conversation intelligence
            "coreference_applied": bool(coreference_subs),
            "coreference_subs": coreference_subs or [],
            "goal_result": goal_result or {},
            "stage_guidance": stage_guidance or {},
            "response_strategy": {
                "tone": response_strategy.tone.value if response_strategy else "professional",
                "length": response_strategy.length.value if response_strategy else "medium",
                "include_question": response_strategy.include_question if response_strategy else True
            } if response_strategy else None,
            
            "email_context": {
                "subject": email_data.subject,
                "from_name": email_data.from_name,
                "is_reply": email_data.is_reply
            },
            
            # Replika-inspired conversational enhancement
            "conversational_enhancement": conv_enhancement_dict,
        }
    
    def _generate_response(
        self,
        email_data: EmailData,
        context_pack: Dict,
        resolved_body: str = None
    ) -> str:
        """
        Generate email response using unified pipeline with conversation intelligence.
        
        Uses resolved_body (coreference-resolved) for better intent understanding.
        """
        # Use resolved body if available
        body_for_intent = resolved_body or email_data.body
        
        try:
            from generate_answer import generate_email_response, ContextPack
            
            # Build intent from email (use resolved body for better understanding)
            intent = f"Email about: {email_data.subject}\n\n{body_for_intent[:1000]}"
            
            # Convert to ContextPack
            ctx = ContextPack.from_dict(context_pack)
            
            # Generate response with email-specific styling and formatting
            response = generate_email_response(
                intent=intent,
                context_pack=ctx,
                thread_id=email_data.thread_id,
                sender_email=email_data.from_email,
                sender_name=email_data.from_name,
            )
            
            response_text = response.text
            
            # Log email styling debug info
            if response.debug_info.get("email_styled"):
                logger.debug("Email styled - quality: %s/100", response.debug_info.get('email_quality_score', 'N/A'))
            
            # Add goal-driven follow-up if slots are missing
            goal_result = context_pack.get("goal_result", {})
            if goal_result.get("should_ask") and goal_result.get("question"):
                response_text += f"\n\n{goal_result['question']}"
            
            return response_text
            
        except ImportError as e:
            logger.warning("generate_email_response not available: %s", e)
            return self._simple_response(email_data, context_pack)
        except Exception as e:
            logger.error("Response generation error: %s", e)
            return self._simple_response(email_data, context_pack)
    
    def _simple_response(self, email_data: EmailData, context_pack: Dict) -> str:
        """Generate a simple response when full pipeline unavailable."""
        
        # Format user memories if available
        memory_context = ""
        if context_pack.get("user_memories"):
            memory_context = "\n\nBased on our previous conversations, I remember:\n"
            for mem in context_pack["user_memories"][:3]:
                memory_context += f"- {mem.get('memory_text', '')}\n"
        
        return f"""Thank you for your email regarding "{email_data.subject}".

I've received your message and will get back to you shortly with more information.
{memory_context}
Best regards,
Ira
Machinecraft Technologies"""
    
    def link_to_telegram(self, email: str, telegram_chat_id: str) -> bool:
        """Link email identity to Telegram chat."""
        if not MEMORY_SERVICE_AVAILABLE:
            return False
        
        try:
            memory = get_memory_service()
            identity_id = memory.link_identities(
                channel1="email",
                id1=email.lower(),
                channel2="telegram",
                id2=telegram_chat_id,
                confidence=1.0
            )
            
            if identity_id:
                logger.info("Linked email:%s ↔ telegram:%s", email, telegram_chat_id)
                return True
            return False
            
        except Exception as e:
            logger.error("Link error: %s", e)
            return False


# Singleton
_handler: Optional[EmailHandler] = None


def get_email_handler() -> EmailHandler:
    """Get singleton EmailHandler."""
    global _handler
    if _handler is None:
        _handler = EmailHandler()
    return _handler


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Email Handler CLI")
    parser.add_argument("--test", action="store_true", help="Run test")
    args = parser.parse_args()
    
    if args.test:
        handler = EmailHandler()
        
        # Test email
        test_email = EmailData(
            message_id="test_001",
            thread_id="thread_001",
            from_email="john@abcmanufacturing.com",
            from_name="John Smith",
            to_email="sales@machinecraft.in",
            subject="Inquiry about PF1 Thermoforming Machine",
            body="""Hello,

I'm interested in your PF1 series thermoforming machines for our automotive parts production line.

We typically produce 500-600 parts per day and need a machine that can handle thick gauge ABS and HDPE materials.

Could you provide pricing and delivery information for the PF1-3020 model?

Thanks,
John Smith
Production Manager
ABC Manufacturing""",
            date=datetime.now()
        )
        
        print("=" * 60)
        print("EMAIL HANDLER TEST")
        print("=" * 60)
        
        print(f"\nProcessing email from: {test_email.from_name} <{test_email.from_email}>")
        print(f"Subject: {test_email.subject}")
        
        response = handler.process_email(test_email, generate_response=True)
        
        if response:
            print(f"\n--- RESPONSE ---")
            print(f"To: {response.to}")
            print(f"Subject: {response.subject}")
            print(f"\n{response.body}")
        else:
            print("No response generated")
        
        print("\n" + "=" * 60)
    else:
        parser.print_help()
