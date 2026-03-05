"""
Conversation Management Skill

Provides conversational AI capabilities:
- Coreference resolution ("it", "that machine")
- Entity extraction and tracking
- Proactive engagement
- Relationship memory (Replika-inspired emotional layer)
- Conversation quality tracking
- Memory surfacing
- Adaptive communication style
- Proactive insights
"""

from .coreference import CoreferenceResolver, ResolvedQuery
from .entity_extractor import EntityExtractor, ExtractedEntities
from .proactive import ProactiveEngine, ProactiveAction, ActionType
from .relationship_memory import (
    RelationshipMemory,
    ContactRelationship,
    RelationshipWarmth,
    MemorableMoment,
    MomentType,
    LearnedPreference,
    apply_relationship_to_prompt,
)
from .emotional_intelligence import (
    EmotionalIntelligence,
    EmotionalReading,
    EmotionalState,
    EmotionalIntensity,
    get_emotional_opener,
    apply_emotional_calibration,
)
from .inner_voice import (
    InnerVoice,
    InnerReflection,
    ReflectionType,
    PersonalityTrait,
    ProgressTracker,
    generate_inner_voice_addition,
)
from .conversation_quality import (
    ConversationQualityTracker,
    ConversationHealth,
    TurnQuality,
    QualityDimension,
)
from .memory_surfacing import (
    MemorySurfacingEngine,
    MemoryReference,
    generate_memory_reference_prompt_addition,
)
from .adaptive_style import (
    AdaptiveStyleEngine,
    StyleProfile,
    StyleAnalyzer,
)
from .insights_engine import (
    InsightsEngine,
    Insight,
    Pattern,
    PatternTracker,
)
from .replika_integration import (
    ConversationalEnhancer,
    ConversationalEnhancement,
    create_enhancer,
)
from .relationship_store import (
    RelationshipStore,
    get_relationship_store,
    bootstrap_from_persistent_memory,
)
from .llm_emotion_detector import (
    LLMEmotionDetector,
    EmotionalReading as LLMEmotionalReading,
    EmotionalState as LLMEmotionalState,
    EmotionalIntensity,
    get_emotion_detector,
    detect_emotion,
    get_response_calibration,
)
from .proactive_outreach import (
    OutreachScheduler,
    OutreachCandidate,
    OutreachConfig,
    get_outreach_scheduler,
    start_outreach_scheduler,
    get_outreach_queue,
    approve_outreach,
)
from .goal_manager import (
    GoalManager,
    Goal,
    GoalStep,
    GoalStatus,
    GoalTemplate,
    GoalStore,
    get_goal_manager,
    get_active_goal,
    start_goal,
    update_goal,
    get_proactive_prompt,
    detect_goal,
)
__all__ = [
    # Coreference
    "CoreferenceResolver",
    "ResolvedQuery",
    # Entity extraction
    "EntityExtractor",
    "ExtractedEntities",
    # Proactive
    "ProactiveEngine",
    "ProactiveAction",
    "ActionType",
    # Relationship memory (Replika-inspired)
    "RelationshipMemory",
    "ContactRelationship",
    "RelationshipWarmth",
    "MemorableMoment",
    "MomentType",
    "LearnedPreference",
    "apply_relationship_to_prompt",
    # Emotional intelligence
    "EmotionalIntelligence",
    "EmotionalReading",
    "EmotionalState",
    "EmotionalIntensity",
    "get_emotional_opener",
    "apply_emotional_calibration",
    # Inner voice (now evolves from feedback)
    "InnerVoice",
    "InnerReflection",
    "ReflectionType",
    "PersonalityTrait",
    "ProgressTracker",
    "generate_inner_voice_addition",
    # Conversation quality
    "ConversationQualityTracker",
    "ConversationHealth",
    "TurnQuality",
    "QualityDimension",
    # Memory surfacing
    "MemorySurfacingEngine",
    "MemoryReference",
    "generate_memory_reference_prompt_addition",
    # Adaptive style
    "AdaptiveStyleEngine",
    "StyleProfile",
    "StyleAnalyzer",
    # Insights engine
    "InsightsEngine",
    "Insight",
    "Pattern",
    "PatternTracker",
    # Central integration
    "ConversationalEnhancer",
    "ConversationalEnhancement",
    "create_enhancer",
    # SQLite persistence
    "RelationshipStore",
    "get_relationship_store",
    "bootstrap_from_persistent_memory",
    # LLM emotion detection
    "LLMEmotionDetector",
    "LLMEmotionalReading",
    "LLMEmotionalState",
    "EmotionalIntensity",
    "get_emotion_detector",
    "detect_emotion",
    "get_response_calibration",
    # Proactive outreach scheduling
    "OutreachScheduler",
    "OutreachCandidate",
    "OutreachConfig",
    "get_outreach_scheduler",
    "start_outreach_scheduler",
    "get_outreach_queue",
    "approve_outreach",
    # Goal-Oriented Dialogue Management
    "GoalManager",
    "Goal",
    "GoalStep",
    "GoalStatus",
    "GoalTemplate",
    "GoalStore",
    "get_goal_manager",
    "get_active_goal",
    "start_goal",
    "update_goal",
    "get_proactive_prompt",
    "detect_goal",
]
