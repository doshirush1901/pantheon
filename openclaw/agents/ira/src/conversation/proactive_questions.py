#!/usr/bin/env python3
"""
PROACTIVE QUESTION ENGINE - Smarter Follow-ups for Ira
=======================================================

Makes Ira ask intelligent follow-up questions based on:
1. Conversation topic/intent
2. Information gaps (what's missing)
3. Conversation stage (early vs deep)
4. User's communication style
5. Business context (sales qualification)

Integrates with:
- InquiryQualifier (machine-specific questions)
- ConversationGoals (slot filling)
- EmotionalIntelligence (tone calibration)

Usage:
    from proactive_questions import get_proactive_questions
    
    questions = get_proactive_questions(
        message="I need a thermoforming machine",
        context={"topic": "machine_inquiry"},
        conversation_history=[...],
    )
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class QuestionType(Enum):
    CLARIFYING = "clarifying"      # Need more info to understand
    QUALIFYING = "qualifying"       # Sales qualification
    EXPLORATORY = "exploratory"     # Dig deeper
    CONFIRMING = "confirming"       # Verify understanding
    NEXT_STEPS = "next_steps"       # Move conversation forward
    CARE = "care"                   # Relationship building


class ConversationTopic(Enum):
    MACHINE_INQUIRY = "machine_inquiry"
    QUOTE_REQUEST = "quote_request"
    TECHNICAL_QUESTION = "technical_question"
    MARKET_RESEARCH = "market_research"
    FOLLOW_UP = "follow_up"
    GENERAL = "general"
    SUPPORT = "support"


@dataclass
class ProactiveQuestion:
    """A proactive question to ask."""
    question: str
    question_type: QuestionType
    priority: int  # 1 = highest
    context_trigger: str  # What triggered this question
    slot_to_fill: Optional[str] = None  # If for slot filling
    
    def to_dict(self) -> Dict:
        return {
            "question": self.question,
            "type": self.question_type.value,
            "priority": self.priority,
            "trigger": self.context_trigger,
        }


# Question templates organized by topic and stage
QUESTION_TEMPLATES = {
    ConversationTopic.MACHINE_INQUIRY: {
        "early": [
            ProactiveQuestion(
                question="What size parts will you be forming?",
                question_type=QuestionType.QUALIFYING,
                priority=1,
                context_trigger="machine inquiry without size",
                slot_to_fill="forming_size"
            ),
            ProactiveQuestion(
                question="What materials will you be processing?",
                question_type=QuestionType.QUALIFYING,
                priority=1,
                context_trigger="machine inquiry without material",
                slot_to_fill="material"
            ),
            ProactiveQuestion(
                question="What production volume are you targeting?",
                question_type=QuestionType.QUALIFYING,
                priority=2,
                context_trigger="machine inquiry without volume",
                slot_to_fill="volume"
            ),
        ],
        "mid": [
            ProactiveQuestion(
                question="Do you need automatic sheet loading, or is manual operation acceptable?",
                question_type=QuestionType.QUALIFYING,
                priority=1,
                context_trigger="volume clarified, automation unclear",
                slot_to_fill="automation_level"
            ),
            ProactiveQuestion(
                question="What's your timeline for getting operational?",
                question_type=QuestionType.QUALIFYING,
                priority=2,
                context_trigger="requirements clear, timeline unclear",
                slot_to_fill="timeline"
            ),
        ],
        "late": [
            ProactiveQuestion(
                question="Would you like me to prepare a detailed quotation?",
                question_type=QuestionType.NEXT_STEPS,
                priority=1,
                context_trigger="requirements qualified"
            ),
            ProactiveQuestion(
                question="Do you have any questions about installation or training?",
                question_type=QuestionType.EXPLORATORY,
                priority=2,
                context_trigger="quote discussed"
            ),
        ],
    },
    
    ConversationTopic.QUOTE_REQUEST: {
        "early": [
            ProactiveQuestion(
                question="Which machine model are you interested in?",
                question_type=QuestionType.CLARIFYING,
                priority=1,
                context_trigger="quote request without model"
            ),
            ProactiveQuestion(
                question="Do you need any additional options or accessories?",
                question_type=QuestionType.EXPLORATORY,
                priority=2,
                context_trigger="model specified"
            ),
        ],
        "late": [
            ProactiveQuestion(
                question="Would you like me to include shipping costs to your location?",
                question_type=QuestionType.NEXT_STEPS,
                priority=1,
                context_trigger="quote being prepared"
            ),
        ],
    },
    
    ConversationTopic.TECHNICAL_QUESTION: {
        "any": [
            ProactiveQuestion(
                question="Is this for a specific application you're working on?",
                question_type=QuestionType.EXPLORATORY,
                priority=2,
                context_trigger="technical question asked"
            ),
            ProactiveQuestion(
                question="Would it help if I explained the practical implications?",
                question_type=QuestionType.CLARIFYING,
                priority=3,
                context_trigger="complex technical topic"
            ),
        ],
    },
    
    ConversationTopic.MARKET_RESEARCH: {
        "early": [
            ProactiveQuestion(
                question="What region or market are you most interested in?",
                question_type=QuestionType.CLARIFYING,
                priority=1,
                context_trigger="market research without region"
            ),
            ProactiveQuestion(
                question="Are you looking at specific competitors or the market overall?",
                question_type=QuestionType.CLARIFYING,
                priority=2,
                context_trigger="market research"
            ),
        ],
    },
    
    ConversationTopic.GENERAL: {
        "any": [
            ProactiveQuestion(
                question="Is there anything specific I can help you with?",
                question_type=QuestionType.EXPLORATORY,
                priority=3,
                context_trigger="unclear intent"
            ),
        ],
    },
}


# Information extraction patterns
INFO_PATTERNS = {
    "forming_size": [
        r"(\d+)\s*[xX×]\s*(\d+)",  # 1500 x 2000
        r"(\d+)\s*mm",  # Dimension mentioned
        r"(small|medium|large)\s*(?:size|part)",
    ],
    "material": [
        r"(HDPE|ABS|PP|PS|PVC|PMMA|PC|PET|PETG|TPO|HIPS|acrylic|polycarbonate)",
    ],
    "volume": [
        r"(high|medium|low)\s*volume",
        r"(\d+)\s*(?:parts?|pieces?|units?)\s*(?:per|a|\/)\s*(?:day|week|month)",
        r"(mass production|prototype|pilot)",
    ],
    "automation_level": [
        r"(auto|automatic|manual)\s*(?:load|loading)?",
        r"(servo|pick.?place|autoloader)",
    ],
    "timeline": [
        r"(urgent|asap|immediately|this (?:week|month|quarter|year))",
        r"(Q[1-4]|H[12])\s*\d{4}",
        r"by\s+(?:end of\s+)?(january|february|march|april|may|june|july|august|september|october|november|december)",
    ],
    "budget": [
        r"\$[\d,]+",
        r"(?:INR|USD|EUR|₹|\$)\s*[\d,]+",
        r"budget\s*(?:is|of|around)?\s*[\d,]+",
    ],
}


class ProactiveQuestionEngine:
    """
    Generates intelligent follow-up questions based on conversation context.
    """
    
    def __init__(self):
        self.asked_questions: List[str] = []
        self.known_slots: Dict[str, str] = {}
    
    def detect_topic(self, message: str, context: Optional[Dict] = None) -> ConversationTopic:
        """Detect the conversation topic from message and context."""
        message_lower = message.lower()
        
        # Check context first
        if context:
            if context.get("topic"):
                try:
                    return ConversationTopic(context["topic"])
                except ValueError:
                    pass
            
            if context.get("intent"):
                intent = context["intent"].lower()
                if "quote" in intent:
                    return ConversationTopic.QUOTE_REQUEST
                if "machine" in intent or "inquiry" in intent:
                    return ConversationTopic.MACHINE_INQUIRY
        
        # Detect from message
        if any(word in message_lower for word in ["quote", "price", "cost", "pricing"]):
            return ConversationTopic.QUOTE_REQUEST
        
        if any(word in message_lower for word in ["machine", "thermoform", "vacuum form", "pf1", "forming"]):
            return ConversationTopic.MACHINE_INQUIRY
        
        if any(word in message_lower for word in ["spec", "technical", "how does", "what is the"]):
            return ConversationTopic.TECHNICAL_QUESTION
        
        if any(word in message_lower for word in ["market", "competitor", "industry", "trend"]):
            return ConversationTopic.MARKET_RESEARCH
        
        if any(word in message_lower for word in ["follow", "update", "status", "where are we"]):
            return ConversationTopic.FOLLOW_UP
        
        return ConversationTopic.GENERAL
    
    def extract_known_info(self, message: str, history: Optional[List[str]] = None) -> Dict[str, str]:
        """Extract what information we already have."""
        all_text = message
        if history:
            all_text = " ".join(history + [message])
        
        known = {}
        
        for slot, patterns in INFO_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, all_text, re.IGNORECASE)
                if match:
                    known[slot] = match.group(0)
                    break
        
        return known
    
    def detect_stage(
        self,
        topic: ConversationTopic,
        known_info: Dict[str, str],
        turn_count: int = 1,
    ) -> str:
        """Detect conversation stage (early, mid, late)."""
        if topic == ConversationTopic.MACHINE_INQUIRY:
            # Based on how much we know
            slots_filled = len(known_info)
            if slots_filled >= 4:
                return "late"
            elif slots_filled >= 2:
                return "mid"
            return "early"
        
        if topic == ConversationTopic.QUOTE_REQUEST:
            if "model" in str(known_info).lower() or turn_count > 2:
                return "late"
            return "early"
        
        # Default based on turn count
        if turn_count >= 5:
            return "late"
        elif turn_count >= 2:
            return "mid"
        return "early"
    
    def get_missing_slots(
        self,
        topic: ConversationTopic,
        known_info: Dict[str, str],
    ) -> List[str]:
        """Get which slots are still missing."""
        if topic == ConversationTopic.MACHINE_INQUIRY:
            required_slots = ["forming_size", "material", "volume"]
            optional_slots = ["automation_level", "timeline", "budget"]
            
            missing = []
            for slot in required_slots:
                if slot not in known_info:
                    missing.append(slot)
            
            # Add optional slots if we have the required ones
            if len(missing) == 0:
                for slot in optional_slots:
                    if slot not in known_info:
                        missing.append(slot)
            
            return missing
        
        return []
    
    def generate_questions(
        self,
        message: str,
        context: Optional[Dict] = None,
        history: Optional[List[str]] = None,
        max_questions: int = 2,
        emotional_state: str = "neutral",
    ) -> List[ProactiveQuestion]:
        """
        Generate proactive questions based on context.
        
        Args:
            message: Current user message
            context: Additional context dict
            history: Previous messages in conversation
            max_questions: Maximum questions to return
            emotional_state: User's emotional state
        
        Returns:
            List of ProactiveQuestion objects, prioritized
        """
        # Don't ask questions if user seems frustrated or urgent
        if emotional_state in ["frustrated", "urgent", "stressed"]:
            return []
        
        topic = self.detect_topic(message, context)
        known_info = self.extract_known_info(message, history)
        turn_count = len(history) if history else 1
        stage = self.detect_stage(topic, known_info, turn_count)
        missing_slots = self.get_missing_slots(topic, known_info)
        
        # Get applicable question templates
        templates = QUESTION_TEMPLATES.get(topic, {})
        candidates = []
        
        # Stage-specific questions
        if stage in templates:
            candidates.extend(templates[stage])
        
        # Any-stage questions
        if "any" in templates:
            candidates.extend(templates["any"])
        
        # Filter out already-asked questions
        candidates = [
            q for q in candidates 
            if q.question not in self.asked_questions
        ]
        
        # Filter by missing slots (if slot-based)
        slot_based = [q for q in candidates if q.slot_to_fill]
        non_slot = [q for q in candidates if not q.slot_to_fill]
        
        prioritized = []
        
        # First, add questions for missing slots
        for slot in missing_slots:
            for q in slot_based:
                if q.slot_to_fill == slot:
                    prioritized.append(q)
                    break
        
        # Then add non-slot questions
        prioritized.extend(non_slot)
        
        # Sort by priority
        prioritized.sort(key=lambda x: x.priority)
        
        # Return top N
        return prioritized[:max_questions]
    
    def format_questions_for_response(
        self,
        questions: List[ProactiveQuestion],
        style: str = "conversational",
    ) -> str:
        """
        Format questions for inclusion in a response.
        
        Args:
            questions: List of ProactiveQuestion objects
            style: "conversational", "list", or "embedded"
        
        Returns:
            Formatted string to append to response
        """
        if not questions:
            return ""
        
        if style == "list":
            lines = ["\n\nA few questions:"]
            for q in questions:
                lines.append(f"• {q.question}")
            return "\n".join(lines)
        
        elif style == "embedded":
            # Return just the first question as a natural continuation
            return f" {questions[0].question}"
        
        else:  # conversational
            if len(questions) == 1:
                return f"\n\n{questions[0].question}"
            else:
                intro = "\n\nQuick questions to help me assist you better:"
                qs = "\n".join(f"• {q.question}" for q in questions)
                return f"{intro}\n{qs}"
    
    def mark_asked(self, question: str) -> None:
        """Mark a question as asked."""
        self.asked_questions.append(question)
    
    def reset(self) -> None:
        """Reset for new conversation."""
        self.asked_questions = []
        self.known_slots = {}


# Singleton instance
_engine: Optional[ProactiveQuestionEngine] = None


def get_proactive_engine() -> ProactiveQuestionEngine:
    """Get the proactive question engine instance."""
    global _engine
    if _engine is None:
        _engine = ProactiveQuestionEngine()
    return _engine


def get_proactive_questions(
    message: str,
    context: Optional[Dict] = None,
    history: Optional[List[str]] = None,
    max_questions: int = 2,
    emotional_state: str = "neutral",
) -> List[ProactiveQuestion]:
    """
    Convenience function to get proactive questions.
    
    Returns:
        List of ProactiveQuestion objects
    """
    engine = get_proactive_engine()
    return engine.generate_questions(
        message=message,
        context=context,
        history=history,
        max_questions=max_questions,
        emotional_state=emotional_state,
    )


def format_proactive_questions(
    questions: List[ProactiveQuestion],
    style: str = "conversational",
) -> str:
    """Format questions for response."""
    engine = get_proactive_engine()
    return engine.format_questions_for_response(questions, style)


# CLI for testing
if __name__ == "__main__":
    print("=" * 60)
    print("PROACTIVE QUESTION ENGINE TEST")
    print("=" * 60)
    
    engine = ProactiveQuestionEngine()
    
    # Test 1: Machine inquiry without details
    print("\n[Test 1] Machine inquiry without details")
    msg1 = "I'm looking for a thermoforming machine"
    questions = engine.generate_questions(msg1)
    print(f"Message: {msg1}")
    print(f"Questions: {[q.question for q in questions]}")
    
    # Test 2: Machine inquiry with some details
    print("\n[Test 2] Machine inquiry with partial details")
    msg2 = "I need a machine for 1500x2000mm HDPE parts"
    questions = engine.generate_questions(msg2)
    print(f"Message: {msg2}")
    print(f"Questions: {[q.question for q in questions]}")
    
    # Test 3: Quote request
    print("\n[Test 3] Quote request")
    msg3 = "Can you send me a quote for a PF1-3020?"
    questions = engine.generate_questions(msg3, context={"intent": "quote"})
    print(f"Message: {msg3}")
    print(f"Questions: {[q.question for q in questions]}")
    
    # Test 4: Technical question
    print("\n[Test 4] Technical question")
    msg4 = "What's the difference between ceramic and quartz heaters?"
    questions = engine.generate_questions(msg4)
    print(f"Message: {msg4}")
    print(f"Questions: {[q.question for q in questions]}")
    
    # Test 5: Frustrated user (should return no questions)
    print("\n[Test 5] Frustrated user")
    msg5 = "I've been waiting for a week for this quote"
    questions = engine.generate_questions(msg5, emotional_state="frustrated")
    print(f"Message: {msg5}")
    print(f"Questions: {[q.question for q in questions]} (should be empty)")
    
    print("\n" + "=" * 60)
    print("✅ Proactive Question Engine ready")
    print("=" * 60)
