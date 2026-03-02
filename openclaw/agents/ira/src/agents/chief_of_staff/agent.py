"""
Intent Helpers (formerly "Chief of Staff")

Advisory utilities for the Tool Orchestrator LLM:
- Intent analysis (keyword-based quick classification)
- Plan creation (recommended skill sequences)
- Response synthesis (priority-based output merging)

The actual orchestration is done by tool_orchestrator.py — these are helpers only.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.athena")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Plan:
    """An execution plan for processing a request."""
    plan_id: str
    intent: str
    steps: List[str]
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "intent": self.intent,
            "steps": self.steps,
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Plan":
        created = d.get("created_at")
        if isinstance(created, str):
            from datetime import datetime
            created = datetime.fromisoformat(created) if created else datetime.now()
        return cls(
            plan_id=d.get("plan_id", ""),
            intent=d.get("intent", "general"),
            steps=d.get("steps", []),
            context=d.get("context", {}),
            created_at=created or datetime.now(),
        )


@dataclass
class OrchestrationResult:
    """Result of an orchestration request."""
    success: bool
    response: str
    intent: str
    plan: Optional[Plan] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "response": self.response,
            "intent": self.intent,
            "plan": self.plan.to_dict() if self.plan else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "OrchestrationResult":
        plan_data = d.get("plan")
        plan = Plan.from_dict(plan_data) if plan_data else None
        return cls(
            success=d.get("success", False),
            response=d.get("response", ""),
            intent=d.get("intent", "general"),
            plan=plan,
            metadata=d.get("metadata", {}),
        )


# =============================================================================
# INTENT ANALYSIS
# =============================================================================

# Intent patterns for quick classification
INTENT_PATTERNS = {
    "pricing": ["price", "cost", "budget", "quote", "how much", "₹", "rs", "lakh", "crore"],
    "specs": ["specification", "spec", "dimension", "forming area", "capacity", "thickness"],
    "email": ["email", "draft", "write to", "follow up", "reply", "compose", "send"],
    "recommendation": ["recommend", "suggest", "suitable", "best", "which machine", "for"],
    "comparison": ["compare", "versus", "vs", "difference", "better"],
    "memory": ["remember", "recall", "last time", "previously", "our conversation"],
    "feedback": ["wrong", "incorrect", "actually", "that's not right", "correction"],
}

# Common typos mapping
TYPO_CORRECTIONS = {
    "emial": "email",
    "emal": "email",
    "dratf": "draft",
    "darft": "draft",
    "wirte": "write",
    "wriet": "write",
    "pric": "price",
    "priice": "price",
    "recomend": "recommend",
    "reccomend": "recommend",
    "spce": "spec",
    "sepc": "spec",
    "qoute": "quote",
    "quoet": "quote",
}

# Intent priority order (higher priority intents checked first when multiple match)
INTENT_PRIORITY = ["feedback", "email", "pricing", "specs", "recommendation", "comparison", "memory"]


def _fix_typos(message: str) -> str:
    """Fix common typos in the message."""
    message_lower = message.lower()
    for typo, correction in TYPO_CORRECTIONS.items():
        message_lower = message_lower.replace(typo, correction)
    return message_lower


def analyze_intent(message: str) -> str:
    """
    Analyze the user's intent from their message.
    
    This is a helper for the LLM - it can use this for quick classification
    before deciding which skills to invoke.
    
    Args:
        message: User's message text
        
    Returns:
        Intent category (pricing, specs, email, recommendation, etc.)
    """
    # Fix typos first
    message_lower = _fix_typos(message)
    
    # Collect all matching intents
    matched_intents = []
    
    # Collect all matching intents
    for intent, keywords in INTENT_PATTERNS.items():
        for keyword in keywords:
            if keyword in message_lower:
                if intent not in matched_intents:
                    matched_intents.append(intent)
                break  # Found a match for this intent, move to next
    
    # If no matches, return general
    if not matched_intents:
        return "general"
    
    # If only one match, return it
    if len(matched_intents) == 1:
        return matched_intents[0]
    
    # Multiple matches - use priority order
    for priority_intent in INTENT_PRIORITY:
        if priority_intent in matched_intents:
            return priority_intent
    
    # Fallback to first match
    return matched_intents[0]


def get_recommended_skills(intent: str) -> List[str]:
    """
    Get the recommended skill sequence for a given intent.
    
    This helps the LLM know which skills to invoke in what order.
    
    Args:
        intent: The analyzed intent
        
    Returns:
        List of skill names to invoke in order
    """
    skill_sequences = {
        "pricing": ["research_skill", "fact_checking_skill", "writing_skill"],
        "specs": ["research_skill", "writing_skill", "fact_checking_skill"],
        "email": ["research_skill", "writing_skill", "fact_checking_skill"],
        "recommendation": ["research_skill", "writing_skill", "fact_checking_skill"],
        "comparison": ["research_skill", "writing_skill", "fact_checking_skill"],
        "memory": ["recall_memory", "writing_skill"],
        "feedback": ["feedback_handler"],
        "general": ["research_skill", "writing_skill", "fact_checking_skill"],
    }
    
    return skill_sequences.get(intent, skill_sequences["general"])


def create_plan(message: str, intent: str, user_id: str = "unknown") -> Plan:
    """
    Create an execution plan for processing a request.
    
    This is advisory - the LLM uses this as guidance, not as a rigid script.
    
    Args:
        message: User's message
        intent: Analyzed intent
        user_id: User identifier
        
    Returns:
        Plan with recommended steps
    """
    import uuid
    
    plan_id = str(uuid.uuid4())[:8]
    skills = get_recommended_skills(intent)
    
    steps = []
    for skill in skills:
        if skill == "research_skill":
            steps.append(f"[RESEARCH] Search for: {message[:100]}")
        elif skill == "writing_skill":
            steps.append(f"[WRITE] Draft {intent} response")
        elif skill == "fact_checking_skill":
            steps.append("[VERIFY] Check accuracy and compliance")
        elif skill == "recall_memory":
            steps.append(f"[MEMORY] Recall context for {user_id}")
        elif skill == "feedback_handler":
            steps.append("[FEEDBACK] Process correction and learn")
        else:
            steps.append(f"[{skill.upper()}] Execute {skill}")
    
    # Always add reflection as final step
    steps.append("[REFLECT] Trigger background reflection")
    
    return Plan(
        plan_id=plan_id,
        intent=intent,
        steps=steps,
        context={
            "user_id": user_id,
            "original_message": message,
            "skills": skills
        }
    )


# =============================================================================
# RESPONSE SYNTHESIS
# =============================================================================

def synthesize_response(
    research_output: Optional[str] = None,
    writing_output: Optional[str] = None,
    verification_output: Optional[str] = None
) -> str:
    """
    Synthesize a final response from skill outputs.
    
    Priority order:
    1. Verification output (if it made corrections)
    2. Writing output (the crafted response)
    3. Research output (raw findings)
    
    Args:
        research_output: Output from research_skill
        writing_output: Output from writing_skill
        verification_output: Output from fact_checking_skill
        
    Returns:
        Final synthesized response
    """
    # Verification output takes priority if it exists and is substantive
    if verification_output and len(verification_output) > 50:
        return verification_output
    
    # Writing output is preferred for most responses
    if writing_output and len(writing_output) > 30:
        return writing_output
    
    # Fall back to research if nothing else
    if research_output and len(research_output) > 20:
        return f"Based on my research: {research_output}"
    
    return "I apologize, but I wasn't able to fully process your request. Could you please rephrase?"


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_intent(message: str) -> Dict[str, Any]:
    """
    Get intent analysis as a dictionary (for JSON serialization).
    
    This can be exposed as an OpenClaw tool.
    """
    intent = analyze_intent(message)
    skills = get_recommended_skills(intent)
    
    return {
        "intent": intent,
        "recommended_skills": skills,
        "description": _get_intent_description(intent)
    }


def _get_intent_description(intent: str) -> str:
    """Get a human-readable description of the intent."""
    descriptions = {
        "pricing": "User is asking about prices, costs, or requesting a quote",
        "specs": "User wants technical specifications or machine details",
        "email": "User wants to draft or compose an email",
        "recommendation": "User is seeking advice on which machine to choose",
        "comparison": "User wants to compare different machines or options",
        "memory": "User is referring to a previous conversation or stored information",
        "feedback": "User is providing a correction or feedback",
        "general": "General inquiry that needs research and response"
    }
    return descriptions.get(intent, "Unknown intent type")
