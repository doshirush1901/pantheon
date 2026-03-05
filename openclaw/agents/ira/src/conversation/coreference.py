#!/usr/bin/env python3
"""
Coreference Resolution for Conversational Context
==================================================

Resolves pronouns and references to entities mentioned in previous turns.
Handles cases like:
- "What about it?" -> "What about PF1-1510?"
- "How much does that cost?" -> "How much does PF1-1510 cost?"
- "Tell me more" -> "Tell me more about PF1-1510"

This is a lightweight rule-based approach optimized for Machinecraft's
product-focused conversations.
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Use centralized patterns
SKILLS_DIR = Path(__file__).parent.parent
AGENT_DIR = SKILLS_DIR.parent

try:
    sys.path.insert(0, str(AGENT_DIR))
    from config import setup_import_paths
    setup_import_paths()
    from patterns import MACHINE_QUICK_PATTERNS, extract_machine_models
    PATTERNS_AVAILABLE = True
except ImportError:
    PATTERNS_AVAILABLE = False
    MACHINE_QUICK_PATTERNS = None


@dataclass
class ResolvedQuery:
    """Result of coreference resolution."""
    original: str
    resolved: str
    confidence: float
    substitutions: List[Dict] = field(default_factory=list)
    
    def was_resolved(self) -> bool:
        return self.original != self.resolved and self.confidence > 0.5


# Pronouns and references that need resolution
PRONOUN_PATTERNS = [
    (r'\b(it|this|that)\b', 'singular_thing'),
    (r'\b(they|these|those|them)\b', 'plural_thing'),
    (r'\b(this machine|that machine|the machine)\b', 'machine_ref'),
    (r'\b(this model|that model|the model)\b', 'model_ref'),
    (r'\b(its|their)\b', 'possessive'),
]

# Follow-up patterns that need context
FOLLOWUP_PATTERNS = [
    r'^(what about|how about|and the|also)\b',
    r'^(more|details|explain|why|how)\b',
    r'^(tell me more|go on|continue)\b',
    r'^(price|cost|specs?|dimensions?|size)\?*$',
    r'^(yes|no|ok|sure|thanks)\b',
    r'^(in\s+\w+)\b',  # "In Europe", "In Germany"
    r'^(from\s+\w+)\b',  # "From our list"
    r'^(name\s+\w+|names?)\b',  # "Name a few", "Names"
]

# Short affirmative responses that confirm previous bot question
AFFIRMATIVE_PATTERNS = [
    r'^(yes|yeah|yep|yup|sure|ok|okay|correct|right|exactly)[\s!.]*$',
]

# Location/filter refinements
REFINEMENT_PATTERNS = [
    (r'^in\s+(europe|germany|france|uk|usa|asia|india|china)$', 'location'),
    (r'^from\s+(our\s+list|the\s+list|database|crm)$', 'source'),
    (r'^(name\s+a\s+few|name\s+some|names?)$', 'request_names'),
]


class CoreferenceResolver:
    """
    Resolves pronouns and references in follow-up questions.
    
    Uses conversation context to replace pronouns with actual entities.
    """
    
    def __init__(self):
        self._pronoun_re = [(re.compile(p, re.IGNORECASE), t) for p, t in PRONOUN_PATTERNS]
        self._followup_re = [re.compile(p, re.IGNORECASE) for p in FOLLOWUP_PATTERNS]
        self._affirmative_re = [re.compile(p, re.IGNORECASE) for p in AFFIRMATIVE_PATTERNS]
        self._refinement_re = [(re.compile(p, re.IGNORECASE), t) for p, t in REFINEMENT_PATTERNS]
    
    def resolve(
        self,
        query: str,
        context: Dict,
    ) -> ResolvedQuery:
        """
        Resolve pronouns and references in a query.
        
        Args:
            query: The user's message
            context: Dict with 'key_entities', 'recent_messages', 'last_bot_question'
            
        Returns:
            ResolvedQuery with resolved text and confidence
        """
        key_entities = context.get("key_entities", {})
        recent_messages = context.get("recent_messages", [])
        last_bot_question = context.get("last_bot_question", "")
        last_topic = context.get("last_topic", "")
        
        # Extract most recent entity mentions
        recent_machine = self._get_recent_machine(key_entities, recent_messages)
        recent_topic = self._get_recent_topic(recent_messages) or last_topic
        
        query_lower = query.lower().strip()
        resolved = query
        substitutions = []
        confidence = 0.0
        
        # Handle affirmative responses to bot questions ("Yes" -> expand to what bot asked)
        if self._is_affirmative(query_lower) and last_bot_question:
            resolved = self._expand_affirmative(query, last_bot_question, recent_topic)
            if resolved != query:
                substitutions.append({
                    "type": "affirmative_expansion",
                    "from": query,
                    "to": resolved,
                    "bot_question": last_bot_question
                })
                return ResolvedQuery(
                    original=query,
                    resolved=resolved,
                    confidence=0.9,
                    substitutions=substitutions
                )
        
        # Handle refinement patterns ("In Europe", "From our list")
        for pattern, refine_type in self._refinement_re:
            match = pattern.match(query_lower)
            if match:
                resolved = self._expand_refinement(query, refine_type, match.group(0), recent_topic, recent_machine)
                if resolved != query:
                    substitutions.append({
                        "type": f"refinement_{refine_type}",
                        "from": query,
                        "to": resolved
                    })
                    return ResolvedQuery(
                        original=query,
                        resolved=resolved,
                        confidence=0.85,
                        substitutions=substitutions
                    )
        
        # Check if this is a follow-up that needs context
        is_followup = self._is_followup_question(query_lower)
        has_pronouns = self._has_pronouns(query_lower)
        
        if not is_followup and not has_pronouns:
            return ResolvedQuery(
                original=query,
                resolved=query,
                confidence=0.0,
                substitutions=[]
            )
        
        # Resolve pronouns to recent machine
        if recent_machine:
            for pattern, ptype in self._pronoun_re:
                if pattern.search(query_lower):
                    # Replace pronoun with machine name
                    if ptype in ['singular_thing', 'machine_ref', 'model_ref']:
                        resolved = pattern.sub(recent_machine, resolved)
                        substitutions.append({
                            "type": ptype,
                            "from": pattern.pattern,
                            "to": recent_machine
                        })
                        confidence = 0.85
        
        # Handle bare follow-ups like "price?" or "specs?"
        if is_followup and recent_machine and len(query.split()) <= 2:
            bare_topic = query_lower.rstrip('?').strip()
            if bare_topic in ['price', 'cost', 'specs', 'specifications', 'size', 'dimensions']:
                resolved = f"What is the {bare_topic} of {recent_machine}?"
                substitutions.append({
                    "type": "bare_followup",
                    "from": query,
                    "to": resolved
                })
                confidence = 0.9
        
        # Handle "what about X" patterns
        what_about_match = re.match(r'^(what about|how about)\s+(.+)$', query_lower, re.IGNORECASE)
        if what_about_match and recent_topic:
            topic = what_about_match.group(2).rstrip('?')
            resolved = f"Tell me about {topic} for {recent_machine or recent_topic}"
            substitutions.append({
                "type": "what_about",
                "from": query,
                "to": resolved
            })
            confidence = 0.8
        
        # Handle "tell me more" 
        if re.match(r'^(tell me more|more details|explain more)', query_lower, re.IGNORECASE):
            if recent_machine:
                resolved = f"Tell me more about {recent_machine}"
                substitutions.append({
                    "type": "tell_more",
                    "from": query,
                    "to": resolved
                })
                confidence = 0.85
        
        return ResolvedQuery(
            original=query,
            resolved=resolved,
            confidence=confidence,
            substitutions=substitutions
        )
    
    def _is_affirmative(self, query: str) -> bool:
        """Check if query is a simple affirmative response."""
        for pattern in self._affirmative_re:
            if pattern.match(query):
                return True
        return False
    
    def _expand_affirmative(
        self,
        query: str,
        last_bot_question: str,
        recent_topic: str
    ) -> str:
        """Expand affirmative response based on what bot asked."""
        question_lower = last_bot_question.lower()
        
        # Bot asked about application
        if "application" in question_lower or "looking at" in question_lower:
            return f"Yes, tell me more about {recent_topic}" if recent_topic else query
        
        # Bot asked about specific details
        if "would you like" in question_lower:
            # Extract what bot offered
            if "more" in question_lower:
                return f"Yes, tell me more"
            return f"Yes, please proceed with that"
        
        # Bot asked a clarifying question
        if "?" in last_bot_question:
            return f"Yes, {recent_topic}" if recent_topic else query
        
        return query
    
    def _expand_refinement(
        self,
        query: str,
        refine_type: str,
        matched: str,
        recent_topic: str,
        recent_machine: str
    ) -> str:
        """Expand refinement queries like 'In Europe', 'From our list'."""
        
        if refine_type == "location":
            # "In Europe" -> "Companies in Europe interested in thermoforming"
            location = matched.replace("in ", "").strip()
            if recent_topic and "compan" in recent_topic.lower():
                return f"Companies in {location} that might be interested in thermoforming machines"
            elif recent_machine:
                return f"Customers for {recent_machine} in {location}"
            return f"Thermoforming prospects in {location}"
        
        elif refine_type == "source":
            # "From our list" -> "Show companies from our CRM/database"
            return f"Show me companies from our internal database/CRM that are prospects for thermoforming machines"
        
        elif refine_type == "request_names":
            # "Name a few" -> "List specific company names"
            if recent_topic:
                return f"List specific company names for {recent_topic}"
            return "List specific company names of thermoforming prospects"
        
        return query
    
    def _get_recent_machine(
        self,
        key_entities: Dict,
        recent_messages: List[Dict]
    ) -> Optional[str]:
        """Get the most recently mentioned machine."""
        # First check key_entities
        machines = key_entities.get("machines", [])
        if machines:
            return machines[-1]  # Most recent
        
        # Fallback: scan recent messages for machine patterns
        # Use centralized patterns if available
        if PATTERNS_AVAILABLE and MACHINE_QUICK_PATTERNS:
            for msg in reversed(recent_messages[-5:]):
                content = msg.get("content", "")
                found = extract_machine_models(content)
                if found:
                    return found[-1]
        else:
            # Fallback to local pattern
            machine_pattern = re.compile(r'\b(PF[-\s]?[12][-\s]?\d*[A-Z]?|AM[-\s]?\d+|RE[-\s]?\d+)\b', re.IGNORECASE)
            for msg in reversed(recent_messages[-5:]):
                content = msg.get("content", "")
                matches = machine_pattern.findall(content)
                if matches:
                    return matches[-1].upper().replace(" ", "-")
        
        return None
    
    def _get_recent_topic(self, recent_messages: List[Dict]) -> Optional[str]:
        """Get the recent topic of conversation."""
        if not recent_messages:
            return None
        
        # Get last user message
        for msg in reversed(recent_messages[-3:]):
            if msg.get("role") == "user":
                return msg.get("content", "")[:100]
        
        return None
    
    def _is_followup_question(self, query: str) -> bool:
        """Check if query is a follow-up needing context."""
        for pattern in self._followup_re:
            if pattern.search(query):
                return True
        
        # Very short queries are likely follow-ups
        if len(query.split()) <= 3:
            return True
        
        return False
    
    def _has_pronouns(self, query: str) -> bool:
        """Check if query contains pronouns that need resolution."""
        for pattern, _ in self._pronoun_re:
            if pattern.search(query):
                return True
        return False


# Singleton
_resolver = None


def get_resolver() -> CoreferenceResolver:
    global _resolver
    if _resolver is None:
        _resolver = CoreferenceResolver()
    return _resolver


def resolve_coreference(query: str, context: Dict) -> ResolvedQuery:
    """Resolve coreferences in a query."""
    return get_resolver().resolve(query, context)


if __name__ == "__main__":
    # Test
    resolver = CoreferenceResolver()
    
    # Simulate conversation context
    context = {
        "key_entities": {"machines": ["PF1-1510"]},
        "recent_messages": [
            {"role": "user", "content": "Tell me about PF1-1510"},
            {"role": "assistant", "content": "The PF1-1510 is our entry-level pressure forming machine..."},
        ]
    }
    
    test_queries = [
        "What about it?",
        "How much does it cost?",
        "price?",
        "Tell me more",
        "What about the specs?",
        "Is that machine good for automotive?",
    ]
    
    print("Coreference Resolution Test")
    print("=" * 50)
    print(f"Context: machines={context['key_entities']['machines']}")
    print()
    
    for q in test_queries:
        result = resolver.resolve(q, context)
        if result.was_resolved():
            print(f'"{q}" -> "{result.resolved}"')
            print(f"  confidence: {result.confidence:.2f}")
        else:
            print(f'"{q}" -> (no resolution needed)')
        print()
