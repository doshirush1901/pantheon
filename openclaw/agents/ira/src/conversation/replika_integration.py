"""
Replika-Inspired Integration Layer
===================================

This module integrates all the Replika-inspired enhancements:
- Relationship Memory (warmth tracking, personal moments)
- Emotional Intelligence (state detection, calibration)
- Inner Voice (personality depth, observations)
- Progress Tracking (milestone celebration)
- Conversation Quality (health tracking, risk detection)
- Memory Surfacing (proactive memory references)
- Adaptive Style (per-user communication preferences)
- Insights Engine (pattern detection, actionable insights)

Usage:
    from conversation.replika_integration import ConversationalEnhancer
    
    enhancer = ConversationalEnhancer()
    
    # Process a message and get enhanced response guidance
    enhancement = enhancer.process_message(
        contact_id="john@acme.com",
        message="Thanks for the quick turnaround! Team's been stressed.",
        name="John"
    )
    
    # Apply enhancements to prompt
    enhanced_prompt = enhancer.apply_to_prompt(base_prompt, enhancement)
    
    # After response, update state
    enhancer.post_response_update(
        contact_id="john@acme.com",
        message="...",
        response="...",
        was_positive=True
    )
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

# Support both relative imports (when used as package) and direct imports (when loaded via sys.path)
try:
    from .relationship_memory import (
        RelationshipMemory,
        RelationshipWarmth,
        apply_relationship_to_prompt,
    )
except ImportError:
    from relationship_memory import (
        RelationshipMemory,
        RelationshipWarmth,
        apply_relationship_to_prompt,
    )

try:
    from .emotional_intelligence import (
        EmotionalIntelligence,
        EmotionalReading as EmotionalReadingOld,
        EmotionalState as EmotionalStateOld,
        get_emotional_opener,
        apply_emotional_calibration,
    )
except ImportError:
    from emotional_intelligence import (
        EmotionalIntelligence,
        EmotionalReading as EmotionalReadingOld,
        EmotionalState as EmotionalStateOld,
        get_emotional_opener,
        apply_emotional_calibration,
    )

try:
    from .inner_voice import (
        InnerVoice,
        ProgressTracker,
        generate_inner_voice_addition,
    )
except ImportError:
    from inner_voice import (
        InnerVoice,
        ProgressTracker,
        generate_inner_voice_addition,
    )

try:
    from .proactive import ProactiveEngine, ProactiveAction
except ImportError:
    from proactive import ProactiveEngine, ProactiveAction

try:
    from .conversation_quality import (
        ConversationQualityTracker,
        ConversationHealth,
        TurnQuality,
    )
except ImportError:
    from conversation_quality import (
        ConversationQualityTracker,
        ConversationHealth,
        TurnQuality,
    )

try:
    from .memory_surfacing import (
        MemorySurfacingEngine,
        MemoryReference,
        generate_memory_reference_prompt_addition,
    )
except ImportError:
    from memory_surfacing import (
        MemorySurfacingEngine,
        MemoryReference,
        generate_memory_reference_prompt_addition,
    )

try:
    from .adaptive_style import (
        AdaptiveStyleEngine,
        StyleProfile,
    )
except ImportError:
    from adaptive_style import (
        AdaptiveStyleEngine,
        StyleProfile,
    )

try:
    from .insights_engine import (
        InsightsEngine,
        Insight,
        Pattern,
    )
except ImportError:
    from insights_engine import (
        InsightsEngine,
        Insight,
        Pattern,
    )

# SQLite persistence and LLM emotion detection
try:
    from .relationship_store import (
        RelationshipStore,
        get_relationship_store,
    )
except ImportError:
    from relationship_store import (
        RelationshipStore,
        get_relationship_store,
    )

try:
    from .llm_emotion_detector import (
        LLMEmotionDetector,
        EmotionalReading,
        EmotionalState,
        EmotionalIntensity,
        get_emotion_detector,
        get_response_calibration,
    )
except ImportError:
    from llm_emotion_detector import (
        LLMEmotionDetector,
        EmotionalReading,
        EmotionalState,
        EmotionalIntensity,
        get_emotion_detector,
        get_response_calibration,
    )


@dataclass
class ConversationalEnhancement:
    """
    Complete enhancement package for a response.
    Contains all Replika-inspired guidance.
    """
    emotional_reading: EmotionalReading
    emotional_calibration: Dict
    relationship_context: Dict
    proactive_actions: List[ProactiveAction]
    inner_voice_addition: Optional[str]
    milestones_to_celebrate: List[Dict]
    suggested_opener: str
    
    # NEW: Extended enhancements
    conversation_health: Optional[ConversationHealth] = None
    memory_references: List[MemoryReference] = field(default_factory=list)
    style_profile: Optional[StyleProfile] = None
    insights: List[Insight] = field(default_factory=list)
    
    # Combined guidance for prompt
    prompt_additions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "emotional_reading": self.emotional_reading.to_dict(),
            "emotional_calibration": self.emotional_calibration,
            "relationship_context": self.relationship_context,
            "proactive_actions": [a.to_dict() for a in self.proactive_actions],
            "inner_voice_addition": self.inner_voice_addition,
            "milestones_to_celebrate": self.milestones_to_celebrate,
            "suggested_opener": self.suggested_opener,
            "prompt_additions": self.prompt_additions,
            # Extended data
            "conversation_health": self.conversation_health.to_dict() if self.conversation_health else None,
            "memory_references": [m.to_dict() for m in self.memory_references],
            "style_profile": self.style_profile.to_dict() if self.style_profile else None,
            "insights": [i.to_dict() for i in self.insights],
        }


class ConversationalEnhancer:
    """
    Central integration point for all Replika-inspired enhancements.
    
    This is the main interface for adding conversational depth to Ira.
    
    Capabilities:
    - Emotional Intelligence: Read and respond to user emotions (LLM-powered)
    - Relationship Memory: Track warmth, personal moments, preferences
    - Inner Voice: Add personality and observations
    - Progress Tracking: Celebrate milestones
    - Conversation Quality: Track health and detect declining relationships
    - Memory Surfacing: Proactively reference relevant memories
    - Adaptive Style: Learn and mirror individual communication styles
    - Insights Engine: Detect patterns and generate actionable insights
    
    All state is persisted to SQLite for cross-restart survival.
    Cross-channel identity linking (email + telegram = same person).
    """
    
    def __init__(self, state_path: Optional[str] = None, use_llm_emotion: bool = True):
        # NEW: SQLite persistence store
        self.store = get_relationship_store()
        
        # NEW: LLM-powered emotion detection
        self.emotion_detector = get_emotion_detector(use_llm=use_llm_emotion)
        
        # Core modules (original) - now backed by SQLite where appropriate
        self.relationship_memory = RelationshipMemory()
        self.emotional_intelligence = EmotionalIntelligence()  # Keep for backwards compat
        self.inner_voice = InnerVoice(store=self.store)  # Now evolves from feedback
        self.progress_tracker = ProgressTracker()
        self.proactive_engine = ProactiveEngine()
        
        # NEW: Extended modules
        self.quality_tracker = ConversationQualityTracker()
        self.memory_surfacer = MemorySurfacingEngine()
        self.style_engine = AdaptiveStyleEngine()
        self.insights_engine = InsightsEngine(store=self.store)
        
        self.state_path = state_path
        if state_path:
            self._load_state()
    
    def process_message(
        self,
        contact_id: str,
        message: str,
        name: str = "",
        channel: str = "telegram",
        additional_context: Dict = None,
        memories: List[Dict] = None,
        topics: List[str] = None,
        email: str = None,
        telegram_id: str = None,
    ) -> ConversationalEnhancement:
        """
        Process a message and generate complete enhancement guidance.
        
        This is the main entry point for each interaction.
        
        Args:
            contact_id: Unique identifier (email or chat ID)
            message: The user's message
            name: User's name if known
            channel: Communication channel
            additional_context: Any extra context (stage, mode, etc.)
            memories: List of stored memories about this contact (for surfacing)
            topics: List of topics detected in the message (for pattern tracking)
            email: Email address for cross-channel identity linking
            telegram_id: Telegram ID for cross-channel identity linking
        
        Returns:
            ConversationalEnhancement with all guidance
        """
        additional_context = additional_context or {}
        memories = memories or []
        topics = topics or []
        
        # === NEW: SQLite - Ensure contact exists and link identities ===
        self.store.get_or_create_contact(
            contact_id=contact_id,
            name=name,
            email=email or (contact_id if "@" in contact_id else None),
            telegram_id=telegram_id or (contact_id if channel == "telegram" and "@" not in contact_id else None),
        )
        
        # === UPGRADED: LLM-Powered Emotional Intelligence ===
        emotional_reading = self.emotion_detector.detect(message)
        
        # Persist to SQLite
        self.store.record_emotion(
            contact_id=contact_id,
            primary_state=emotional_reading.primary_state.value,
            intensity=emotional_reading.intensity.value,
            confidence=emotional_reading.confidence,
            signals=emotional_reading.signals
        )
        
        emotional_calibration = get_response_calibration(emotional_reading)
        
        # === CORE: Relationship Memory (in-memory + SQLite sync) ===
        rel_detected = self.relationship_memory.process_interaction(
            contact_id=contact_id,
            message=message,
            response="",
            name=name,
            is_positive=emotional_reading.primary_state != EmotionalState.FRUSTRATED
        )
        
        # Sync to SQLite
        rel = self.relationship_memory.get_or_create(contact_id, name)
        self.store.update_relationship_state(
            contact_id=contact_id,
            warmth=rel.warmth.value,
            warmth_score=rel.warmth_score,
            interaction_count=rel.interaction_count,
            positive_interactions=rel.positive_interactions,
        )
        
        relationship_context = self.relationship_memory.get_relationship_context(contact_id)
        warmth = relationship_context.get("warmth", "stranger")
        
        # === CORE: Proactive Actions ===
        care_actions = self.proactive_engine.get_relationship_based_actions(
            contact_id, self.relationship_memory
        )
        
        # === CORE: Inner Voice ===
        inner_addition = generate_inner_voice_addition(
            inner_voice=self.inner_voice,
            context=message,
            relationship_context=relationship_context,
            emotional_state=emotional_reading.primary_state.value,
            channel=channel
        )
        
        # === CORE: Progress Tracking ===
        rel = self.relationship_memory.get_or_create(contact_id, name)
        new_milestones = self.progress_tracker.check_for_milestones(
            contact_id=contact_id,
            interaction_count=rel.interaction_count,
            relationship_days=relationship_context.get("relationship_duration_days", 0),
            context=additional_context
        )
        uncelebrated = self.progress_tracker.get_uncelebrated(contact_id)
        
        # === NEW: Adaptive Style ===
        style_profile = self.style_engine.analyze_and_update(
            contact_id=contact_id,
            message=message,
        )
        
        # === NEW: Memory Surfacing ===
        memory_references = []
        is_first = relationship_context.get("interaction_count", 0) <= 1
        if self.memory_surfacer.should_surface_any(warmth, len(message), is_first):
            memory_references = self.memory_surfacer.find_surfacing_opportunities(
                user_message=message,
                memories=memories,
                relationship_warmth=warmth
            )
        
        # === NEW: Insights Engine ===
        self.insights_engine.record_interaction(
            contact_id=contact_id,
            message=message,
            topics=topics,
        )
        insights = self.insights_engine.get_insights(contact_id)
        
        # === NEW: Conversation Health (will be scored post-response) ===
        conversation_health = self.quality_tracker.get_health(contact_id)
        
        # === Suggested Opener ===
        suggested_opener = ""
        if emotional_reading.intensity.value in ["moderate", "strong"]:
            suggested_opener = get_emotional_opener(emotional_reading.primary_state)
        
        # === Build all prompt additions ===
        prompt_additions = self._build_prompt_additions(
            contact_id=contact_id,
            emotional_calibration=emotional_calibration,
            relationship_context=relationship_context,
            inner_addition=inner_addition,
            milestones=uncelebrated,
            care_actions=care_actions,
            style_profile=style_profile,
            memory_references=memory_references,
            insights=insights,
            conversation_health=conversation_health,
        )
        
        return ConversationalEnhancement(
            emotional_reading=emotional_reading,
            emotional_calibration=emotional_calibration,
            relationship_context=relationship_context,
            proactive_actions=care_actions,
            inner_voice_addition=inner_addition,
            milestones_to_celebrate=uncelebrated,
            suggested_opener=suggested_opener,
            prompt_additions=prompt_additions,
            # Extended fields
            conversation_health=conversation_health,
            memory_references=memory_references,
            style_profile=style_profile,
            insights=insights,
        )
    
    def _build_prompt_additions(
        self,
        contact_id: str,
        emotional_calibration: Dict,
        relationship_context: Dict,
        inner_addition: Optional[str],
        milestones: List[Dict],
        care_actions: List[ProactiveAction],
        style_profile: Optional[StyleProfile] = None,
        memory_references: List[MemoryReference] = None,
        insights: List[Insight] = None,
        conversation_health: Optional[ConversationHealth] = None,
    ) -> List[str]:
        """Build list of prompt additions based on all enhancements."""
        additions = []
        memory_references = memory_references or []
        insights = insights or []
        
        # === EMOTIONAL CALIBRATION ===
        if emotional_calibration.get("guidance"):
            additions.append(f"EMOTIONAL CONTEXT: {emotional_calibration['guidance']}")
        
        # === RELATIONSHIP CONTEXT ===
        warmth = relationship_context.get("warmth", "stranger")
        if warmth in ["trusted", "warm"]:
            additions.append(
                f"RELATIONSHIP: {warmth.upper()} - Be personable. "
                f"You've had {relationship_context.get('interaction_count', 0)} interactions."
            )
            
            moments = relationship_context.get("moments_to_reference", [])
            if moments:
                moment_texts = [m.get("content", "")[:60] for m in moments[-2:]]
                additions.append(f"PERSONAL CONTEXT: {'; '.join(moment_texts)}")
        
        # === ADAPTIVE STYLE ===
        if style_profile and style_profile.messages_analyzed >= 3:
            style_guidance = style_profile.get_response_guidance()
            key_guidance = []
            
            if style_profile.formality_score > 70:
                key_guidance.append("formal")
            elif style_profile.formality_score < 30:
                key_guidance.append("casual")
            
            if style_profile.detail_score > 70:
                key_guidance.append("detailed")
            elif style_profile.detail_score < 30:
                key_guidance.append("brief")
            
            if style_profile.pace_score > 70:
                key_guidance.append("direct")
            
            if key_guidance:
                additions.append(f"COMMUNICATION STYLE: This person prefers {', '.join(key_guidance)} responses.")
        
        # === MEMORY SURFACING ===
        if memory_references:
            ref_text = generate_memory_reference_prompt_addition(memory_references)
            if ref_text:
                additions.append(ref_text)
        
        # === INSIGHTS ===
        if insights:
            insight = insights[0]  # Top insight
            additions.append(f"INSIGHT: {insight.title}")
            if insight.action_suggestion:
                additions.append(f"  → {insight.action_suggestion}")
        
        # === CONVERSATION HEALTH ===
        if conversation_health and conversation_health.risk_level in ["medium", "high"]:
            additions.append(
                f"RELATIONSHIP HEALTH: {conversation_health.risk_level.upper()} risk "
                f"(trend: {conversation_health.trend}). Extra care advised."
            )
            if conversation_health.insights:
                additions.append(f"  → {conversation_health.insights[0]}")
        
        # === FEEDBACK LOOP: Learn from what works ===
        feedback = self._get_feedback_adjustments(contact_id)
        if feedback:
            additions.append(f"LEARNED: {feedback}")
        
        # === FOLLOW-UPS ===
        pending = relationship_context.get("pending_followups", [])
        if pending:
            followup_text = pending[0].get("content", "")[:80]
            additions.append(f"CONSIDER FOLLOWING UP: {followup_text}")
        
        # === CARE ACTIONS ===
        if care_actions:
            care_text = care_actions[0].content[:80]
            additions.append(f"CARE OPPORTUNITY: {care_text}")
        
        # === MILESTONES ===
        if milestones:
            milestone_type = milestones[0].get("type", "")
            additions.append(f"MILESTONE TO ACKNOWLEDGE: {milestone_type}")
        
        # === EVOLVED PERSONALITY ===
        personality_prompt = self.inner_voice.get_personality_prompt_addition()
        if personality_prompt:
            additions.append(personality_prompt)
        
        # === INNER VOICE ===
        if inner_addition:
            additions.append(f"INNER VOICE (optional to surface): {inner_addition}")
        
        return additions
    
    def _get_feedback_adjustments(self, contact_id: str) -> Optional[str]:
        """
        Analyze past quality scores to learn what works for this contact.
        
        This is the FEEDBACK LOOP that makes Ira smarter over time.
        Returns actionable guidance based on historical performance.
        """
        # Get recent quality history from SQLite
        turn_history = self.store.get_turn_history(contact_id, limit=10)
        
        if len(turn_history) < 3:
            return None  # Need enough data
        
        # Analyze trends
        engagement_scores = [t.get("engagement_score", 50) for t in turn_history]
        rapport_scores = [t.get("rapport_score", 50) for t in turn_history]
        satisfaction_scores = [t.get("satisfaction_score", 50) for t in turn_history]
        
        # Calculate recent trend
        recent = turn_history[:3]
        older = turn_history[3:6] if len(turn_history) >= 6 else turn_history[3:]
        
        if not older:
            return None
        
        recent_avg = sum(t.get("overall_score", 50) for t in recent) / len(recent)
        older_avg = sum(t.get("overall_score", 50) for t in older) / len(older)
        
        adjustments = []
        
        # Check for declining engagement
        if recent_avg < older_avg - 10:
            # Quality is dropping - find out why
            recent_engagement = sum(engagement_scores[:3]) / 3
            recent_rapport = sum(rapport_scores[:3]) / 3
            recent_satisfaction = sum(satisfaction_scores[:3]) / 3
            
            if recent_engagement < 40:
                adjustments.append("Be more engaging - ask questions, show curiosity")
            if recent_rapport < 40:
                adjustments.append("Build rapport - reference shared history, show warmth")
            if recent_satisfaction < 40:
                adjustments.append("Focus on being helpful - ensure you're addressing their needs")
        
        # Check what signals appeared in high-scoring turns
        high_scoring = [t for t in turn_history if t.get("overall_score", 0) >= 70]
        if high_scoring:
            # Look for patterns in signals
            all_signals = []
            for t in high_scoring:
                signals = t.get("signals")
                if signals:
                    if isinstance(signals, str):
                        all_signals.extend(signals.split(","))
                    elif isinstance(signals, list):
                        all_signals.extend(signals)
            
            # Count common successful signals
            from collections import Counter
            signal_counts = Counter(s.strip() for s in all_signals if s.strip())
            top_signals = signal_counts.most_common(2)
            
            for signal, count in top_signals:
                if count >= 2 and signal:
                    adjustments.append(f"Keep doing: {signal}")
        
        if adjustments:
            return " | ".join(adjustments[:2])  # Limit to 2 adjustments
        
        return None
    
    def apply_to_prompt(
        self,
        base_prompt: str,
        enhancement: ConversationalEnhancement
    ) -> str:
        """
        Apply all enhancements to a base prompt.
        
        Args:
            base_prompt: The original system/response prompt
            enhancement: ConversationalEnhancement from process_message
        
        Returns:
            Enhanced prompt with all conversational guidance
        """
        additions = enhancement.prompt_additions
        
        if not additions:
            return base_prompt
        
        enhanced = base_prompt + "\n\n" + "=" * 40
        enhanced += "\nCONVERSATIONAL ENHANCEMENT (Replika-inspired)\n"
        enhanced += "=" * 40 + "\n"
        enhanced += "\n".join(additions)
        enhanced += "\n" + "=" * 40
        
        return enhanced
    
    def post_response_update(
        self,
        contact_id: str,
        message: str,
        response: str,
        was_positive: bool = True,
        milestones_celebrated: List[str] = None,
        care_actions_taken: List[str] = None,
        memories_surfaced: List[str] = None,
        response_time_ms: int = 0,
        had_citations: bool = False,
    ) -> TurnQuality:
        """
        Update state after a response is sent.
        
        Args:
            contact_id: The contact identifier
            message: The user's original message
            response: Ira's response
            was_positive: Whether the interaction was positive
            milestones_celebrated: List of milestone types that were mentioned
            care_actions_taken: List of care action contents that were addressed
            memories_surfaced: List of memory IDs that were referenced
            response_time_ms: Response generation time
            had_citations: Whether response included citations
        
        Returns:
            TurnQuality score for this interaction
        """
        # === CORE: Update relationship memory ===
        self.relationship_memory.process_interaction(
            contact_id=contact_id,
            message=message,
            response=response,
            is_positive=was_positive
        )
        
        # === CORE: Mark milestones celebrated ===
        for milestone_type in (milestones_celebrated or []):
            self.progress_tracker.mark_celebrated(contact_id, milestone_type)
        
        # === CORE: Mark care actions taken ===
        for action_content in (care_actions_taken or []):
            self.proactive_engine.mark_action_taken(action_content)
        
        # === CORE: Update inner voice ===
        rel_context = self.relationship_memory.get_relationship_context(contact_id)
        self.inner_voice.analyze_conversation(
            messages=[
                {"role": "user", "content": message},
                {"role": "assistant", "content": response}
            ],
            relationship_context=rel_context
        )
        
        # === NEW: Score conversation quality (feeds back to inner voice) ===
        turn_quality = self.quality_tracker.score_turn(
            contact_id=contact_id,
            user_message=message,
            assistant_response=response,
            response_time_ms=response_time_ms,
            had_citations=had_citations,
        )
        
        # === NEW: Feed quality back to inner voice for evolution ===
        surfaced_reflections = [r for r in self.inner_voice.reflections if r.surfaced and not r.quality_score]
        for reflection in surfaced_reflections[-1:]:  # Only most recent
            self.inner_voice.record_feedback(
                reflection=reflection,
                quality_score=turn_quality.overall_score,
                contact_id=contact_id,
            )
        
        # === NEW: Mark memories as surfaced ===
        for memory_id in (memories_surfaced or []):
            self.memory_surfacer.mark_surfaced(memory_id)
            self.store.mark_memory_surfaced(memory_id, contact_id)
        
        # === NEW: Persist turn quality to SQLite ===
        self.store.add_turn_quality(
            contact_id=contact_id,
            turn_id=turn_quality.turn_id,
            overall_score=turn_quality.overall_score,
            engagement_score=turn_quality.scores.get("engagement", 50),
            rapport_score=turn_quality.scores.get("rapport", 50),
            satisfaction_score=turn_quality.scores.get("satisfaction", 50),
            effectiveness_score=turn_quality.scores.get("effectiveness", 50),
            signals=turn_quality.signals,
        )
        
        # === NEW: Update conversation health in SQLite ===
        health = self.quality_tracker.get_health(contact_id)
        if health:
            self.store.update_conversation_health(
                contact_id=contact_id,
                health_score=health.health_score,
                trend=health.trend,
                risk_level=health.risk_level,
            )
        
        # === NEW: Sync style profile to SQLite ===
        style = self.style_engine.profiles.get(contact_id)
        if style:
            self.store.update_style_profile(
                contact_id=contact_id,
                formality_score=style.formality_score,
                detail_score=style.detail_score,
                technical_score=style.technical_score,
                pace_score=style.pace_score,
                emoji_score=style.emoji_score,
                humor_score=style.humor_score,
                avg_message_length=style.avg_message_length,
                messages_analyzed=style.messages_analyzed,
            )
        
        # === Save state (legacy JSON backup) ===
        if self.state_path:
            self._save_state()
        
        return turn_quality
    
    def get_proactive_outreach_candidates(self) -> List[Dict]:
        """
        Get contacts that might benefit from proactive outreach.
        
        Returns list of contacts with:
        - Pending care follow-ups
        - Uncelebrated milestones
        - Stale relationships (warm but haven't talked recently)
        - At-risk relationships (declining quality)
        """
        candidates = []
        
        for contact_id, rel in self.relationship_memory.relationships.items():
            reasons = []
            priority_score = 0
            
            # Care follow-ups
            pending = rel.needs_followup()
            if pending:
                reasons.append(f"Care follow-up: {pending[0].content[:50]}")
                priority_score += 2
            
            # Milestones
            milestones = self.progress_tracker.get_uncelebrated(contact_id)
            if milestones:
                reasons.append(f"Milestone: {milestones[0].get('type', '')}")
                priority_score += 1
            
            # Stale relationship
            if rel.last_interaction:
                from datetime import timedelta
                days_since = (datetime.now() - rel.last_interaction).days
                if days_since > 14 and rel.warmth in [
                    RelationshipWarmth.WARM, 
                    RelationshipWarmth.TRUSTED
                ]:
                    reasons.append(f"Haven't connected in {days_since} days")
                    priority_score += 2
            
            # At-risk (declining conversation quality)
            health = self.quality_tracker.get_health(contact_id)
            if health and health.risk_level in ["medium", "high"]:
                reasons.append(f"Relationship at risk ({health.trend})")
                priority_score += 3
            
            # Actionable insights
            insights = self.insights_engine.get_insights(contact_id, actionable_only=True)
            if insights:
                reasons.append(f"Insight: {insights[0].title[:40]}")
                priority_score += 1
            
            if reasons:
                candidates.append({
                    "contact_id": contact_id,
                    "name": rel.name,
                    "warmth": rel.warmth.value,
                    "reasons": reasons,
                    "priority_score": priority_score,
                })
        
        candidates.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        return candidates[:10]
    
    def get_at_risk_relationships(self) -> List[Dict]:
        """
        Get relationships that are declining and need attention.
        
        Returns contacts with:
        - Low conversation health scores
        - Declining trends
        - Improvement suggestions
        """
        at_risk = self.quality_tracker.get_at_risk_contacts(threshold=45.0)
        
        results = []
        for health in at_risk:
            suggestions = self.quality_tracker.get_improvement_suggestions(health.contact_id)
            rel = self.relationship_memory.relationships.get(health.contact_id)
            
            results.append({
                "contact_id": health.contact_id,
                "name": rel.name if rel else health.contact_id,
                "health_score": health.health_score,
                "trend": health.trend,
                "risk_level": health.risk_level,
                "suggestions": suggestions,
                "insights": health.insights,
            })
        
        return results
    
    def get_relationship_dashboard(self) -> Dict:
        """
        Get a dashboard view of all relationship health.
        
        Returns aggregate statistics and highlights.
        """
        relationships = list(self.relationship_memory.relationships.values())
        
        if not relationships:
            return {"total": 0, "message": "No relationships tracked yet."}
        
        # Warmth distribution
        warmth_counts = {}
        for rel in relationships:
            w = rel.warmth.value
            warmth_counts[w] = warmth_counts.get(w, 0) + 1
        
        # Health distribution
        health_scores = []
        declining = []
        for contact_id in self.relationship_memory.relationships:
            health = self.quality_tracker.get_health(contact_id)
            if health:
                health_scores.append(health.health_score)
                if health.trend == "declining":
                    declining.append(contact_id)
        
        avg_health = sum(health_scores) / len(health_scores) if health_scores else 50.0
        
        # Pending actions
        outreach_candidates = self.get_proactive_outreach_candidates()
        
        return {
            "total_relationships": len(relationships),
            "warmth_distribution": warmth_counts,
            "average_health": round(avg_health, 1),
            "declining_relationships": len(declining),
            "pending_outreach": len(outreach_candidates),
            "top_priorities": outreach_candidates[:3],
            "at_risk": self.get_at_risk_relationships()[:3],
        }
    
    def _save_state(self) -> None:
        """Save all state to file."""
        if not self.state_path:
            return
        
        state = {
            "relationships": self.relationship_memory.to_dict(),
            "emotional_history": {
                k: [r.to_dict() for r in v]
                for k, v in self.emotional_intelligence.emotional_history.items()
            },
            "milestones": self.progress_tracker.milestones,
            "inner_reflections": [r.to_dict() for r in self.inner_voice.reflections],
        }
        
        path = Path(self.state_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2, default=str))
    
    def _load_state(self) -> None:
        """Load state from file."""
        if not self.state_path:
            return
        
        path = Path(self.state_path)
        if not path.exists():
            return
        
        try:
            state = json.loads(path.read_text())
            
            if state.get("relationships"):
                self.relationship_memory = RelationshipMemory.from_dict(
                    state["relationships"]
                )
            
            if state.get("milestones"):
                self.progress_tracker.milestones = state["milestones"]
                
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[ConversationalEnhancer] Failed to load state: {e}")


def create_enhancer(workspace_path: str = None) -> ConversationalEnhancer:
    """
    Factory function to create a ConversationalEnhancer with standard paths.
    
    Args:
        workspace_path: Path to workspace (defaults to Ira workspace)
    
    Returns:
        Configured ConversationalEnhancer
    """
    if workspace_path:
        state_path = f"{workspace_path}/conversational_state.json"
    else:
        from pathlib import Path
        agent_dir = Path(__file__).parent.parent.parent
        state_path = str(agent_dir / "workspace" / "conversational_state.json")
    
    return ConversationalEnhancer(state_path=state_path)
