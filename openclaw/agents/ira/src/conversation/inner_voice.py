"""
Ira's Inner Voice - Personality depth, observations, milestone celebration.

ENHANCED: Now evolves based on feedback and quality scores.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
from collections import defaultdict
import random
import json


class ReflectionType(Enum):
    OBSERVATION = "observation"
    OPINION = "opinion"
    CELEBRATION = "celebration"
    CURIOSITY = "curiosity"
    CONNECTION = "connection"


@dataclass
class PersonalityTrait:
    """A personality trait that can be tuned based on feedback."""
    name: str
    value: float = 0.5  # 0-1 scale
    confidence: float = 0.0
    positive_outcomes: int = 0
    negative_outcomes: int = 0
    
    def update(self, was_positive: bool):
        """Update trait based on feedback."""
        if was_positive:
            self.positive_outcomes += 1
            # Increase trait value slightly
            self.value = min(1.0, self.value + 0.05)
        else:
            self.negative_outcomes += 1
            # Decrease trait value slightly
            self.value = max(0.0, self.value - 0.05)
        
        # Update confidence based on total outcomes
        total = self.positive_outcomes + self.negative_outcomes
        if total > 0:
            self.confidence = min(1.0, total / 20)  # Max confidence after 20 outcomes


@dataclass
class InnerReflection:
    reflection_type: ReflectionType
    content: str
    context: str = ""
    surfaced: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    traits_used: List[str] = field(default_factory=list)  # Track which traits influenced this
    quality_score: Optional[float] = None  # Feedback score if available
    
    def to_dict(self) -> Dict:
        return {
            "reflection_type": self.reflection_type.value,
            "content": self.content,
            "context": self.context,
            "surfaced": self.surfaced,
            "created_at": self.created_at.isoformat(),
            "traits_used": self.traits_used,
            "quality_score": self.quality_score,
        }


class InnerVoice:
    """
    Ira's personality and inner voice.
    
    ENHANCED: Now evolves based on what works:
    - Tracks personality traits and their effectiveness
    - Adjusts observation/celebration style based on feedback
    - Learns which traits resonate with different users
    """
    
    # Base templates - will be weighted by trait effectiveness
    OBSERVATION_TEMPLATES = {
        "analytical": "I've noticed {pattern} - {insight}.",
        "curious": "Interesting pattern here: {pattern}. What do you think about {insight}?",
        "supportive": "I noticed {pattern}. That's great because {insight}.",
        "direct": "{pattern} → {insight}.",
        "charming": "I couldn't help but notice {pattern}... {insight} 😊",
        "playful": "Ooh, {pattern}! That's interesting because {insight}.",
    }
    
    CELEBRATION_TEMPLATES = {
        "enthusiastic": "This is fantastic! {achievement}",
        "warm": "This is a win worth celebrating. {achievement}",
        "understated": "Good result here. {achievement}",
        "supportive": "You did it! {achievement} I knew you could.",
        "charming": "Look at you! {achievement} I'm impressed 😊",
        "playful": "Well well well... {achievement} Someone's on fire today!",
    }
    
    # Greeting/acknowledgment templates for charm
    GREETING_TEMPLATES = {
        "professional": "Hello! How can I help?",
        "warm": "Hey there! What can I do for you?",
        "charming": "Hey you! Always nice to hear from you 😊",
        "playful": "Oh hi! I was just thinking about you...",
    }
    
    # Default personality traits
    DEFAULT_TRAITS = {
        "warmth": 0.65,      # How warm/friendly vs professional
        "curiosity": 0.5,    # How much to ask questions
        "enthusiasm": 0.55,  # Celebration intensity
        "directness": 0.45,  # Brief vs elaborative (lower = more elaborative)
        "empathy": 0.65,     # Emotional responsiveness
        "humor": 0.4,        # Tendency to be light-hearted
        "charm": 0.6,        # Playful/flirty feminine energy ✨
    }
    
    def __init__(self, store=None):
        self.reflections: List[InnerReflection] = []
        self.store = store  # Optional SQLite store for persistence
        
        # Initialize personality traits
        self.traits: Dict[str, PersonalityTrait] = {}
        for name, default_value in self.DEFAULT_TRAITS.items():
            self.traits[name] = PersonalityTrait(name=name, value=default_value)
        
        # Per-contact trait effectiveness tracking
        self.contact_trait_scores: Dict[str, Dict[str, Tuple[int, int]]] = defaultdict(
            lambda: defaultdict(lambda: (0, 0))  # (positive, negative)
        )
        
        # Load persisted state if available
        self._load_state()
    
    def _load_state(self):
        """Load trait state from store if available."""
        if not self.store:
            return
        try:
            with self.store._get_conn() as conn:
                # Check if inner_voice_traits table exists
                table_exists = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='inner_voice_traits'
                """).fetchone()
                
                if table_exists:
                    rows = conn.execute("SELECT * FROM inner_voice_traits").fetchall()
                    for row in rows:
                        if row["trait_name"] in self.traits:
                            self.traits[row["trait_name"]].value = row["value"]
                            self.traits[row["trait_name"]].positive_outcomes = row["positive_outcomes"]
                            self.traits[row["trait_name"]].negative_outcomes = row["negative_outcomes"]
                            self.traits[row["trait_name"]].confidence = row["confidence"]
        except Exception as e:
            print(f"[InnerVoice] Load state error: {e}")
    
    def _save_state(self):
        """Save trait state to store."""
        if not self.store:
            return
        try:
            with self.store._get_conn() as conn:
                # Ensure table exists
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS inner_voice_traits (
                        trait_name TEXT PRIMARY KEY,
                        value REAL,
                        confidence REAL,
                        positive_outcomes INTEGER,
                        negative_outcomes INTEGER,
                        updated_at TEXT
                    )
                """)
                
                for trait in self.traits.values():
                    conn.execute("""
                        INSERT OR REPLACE INTO inner_voice_traits 
                        (trait_name, value, confidence, positive_outcomes, negative_outcomes, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        trait.name, trait.value, trait.confidence,
                        trait.positive_outcomes, trait.negative_outcomes,
                        datetime.now().isoformat()
                    ))
        except Exception as e:
            print(f"[InnerVoice] Save state error: {e}")
    
    def _select_template(self, templates: Dict[str, str], relevant_traits: List[str]) -> Tuple[str, List[str]]:
        """Select a template based on trait values."""
        # Weight templates by their associated trait values
        weights = {}
        for style, template in templates.items():
            # Map style to trait
            style_trait_map = {
                "analytical": "directness",
                "curious": "curiosity", 
                "supportive": "empathy",
                "direct": "directness",
                "enthusiastic": "enthusiasm",
                "warm": "warmth",
                "understated": "directness",
                "charming": "charm",
                "playful": "charm",
                "professional": "directness",
            }
            
            trait_name = style_trait_map.get(style, "warmth")
            trait = self.traits.get(trait_name)
            
            if trait:
                # Higher trait value = higher weight
                weights[style] = trait.value + 0.1  # Add small base to avoid zero weights
            else:
                weights[style] = 0.5
        
        # Weighted random selection
        total = sum(weights.values())
        r = random.random() * total
        cumulative = 0
        
        selected_style = list(templates.keys())[0]
        traits_used = []
        
        for style, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                selected_style = style
                # Track which trait influenced this selection
                style_trait_map = {
                    "analytical": "directness",
                    "curious": "curiosity",
                    "supportive": "empathy", 
                    "direct": "directness",
                    "enthusiastic": "enthusiasm",
                    "charming": "charm",
                    "playful": "charm",
                    "professional": "directness",
                    "warm": "warmth",
                    "understated": "directness",
                }
                if selected_style in style_trait_map:
                    traits_used.append(style_trait_map[selected_style])
                break
        
        return templates[selected_style], traits_used
    
    def generate_observation(self, pattern: str, insight: str, context: str = "") -> InnerReflection:
        """Generate an observation using evolved personality."""
        template, traits_used = self._select_template(self.OBSERVATION_TEMPLATES, ["curiosity", "directness"])
        content = template.format(pattern=pattern, insight=insight)
        
        reflection = InnerReflection(
            reflection_type=ReflectionType.OBSERVATION,
            content=content,
            context=context,
            traits_used=traits_used,
        )
        self.reflections.append(reflection)
        return reflection
    
    def generate_celebration(self, achievement: str, significance: str = "") -> InnerReflection:
        """Generate a celebration using evolved personality."""
        template, traits_used = self._select_template(self.CELEBRATION_TEMPLATES, ["enthusiasm", "warmth"])
        content = template.format(achievement=achievement)
        if significance:
            content += f" {significance}"
        
        reflection = InnerReflection(
            reflection_type=ReflectionType.CELEBRATION,
            content=content,
            context=achievement,
            traits_used=traits_used,
        )
        self.reflections.append(reflection)
        return reflection
    
    def should_share_reflection(self, warmth_level: str, emotional_state: str, channel: str) -> bool:
        """Decide whether to share a reflection based on context and evolved traits."""
        # Never share when user is stressed
        if emotional_state in ["urgent", "frustrated", "stressed"]:
            return False
        
        # Base chance by warmth level
        warmth_chances = {
            "trusted": 0.4,
            "warm": 0.3,
            "familiar": 0.2,
            "acquaintance": 0.1,
            "stranger": 0.05,
        }
        base_chance = warmth_chances.get(warmth_level, 0.1)
        
        # Adjust by personality traits - if warmth trait is high, share more
        warmth_trait = self.traits.get("warmth")
        if warmth_trait:
            # Scale chance by warmth trait (0.5 = no change, 1.0 = double, 0.0 = halve)
            multiplier = 0.5 + warmth_trait.value
            base_chance *= multiplier
        
        return random.random() < base_chance
    
    def get_relevant_reflection(self, current_context: str, relationship_context: Dict) -> Optional[InnerReflection]:
        """Get a relevant reflection to potentially share."""
        unsurfaced = [r for r in self.reflections if not r.surfaced]
        if not unsurfaced:
            return None
        
        # Prefer contextually relevant reflections
        for ref in reversed(unsurfaced[-5:]):
            if ref.context and ref.context.lower() in current_context.lower():
                return ref
        
        # Otherwise return latest if warmth is high enough
        warmth = relationship_context.get("warmth", "stranger")
        if warmth in ["trusted", "warm"]:
            return unsurfaced[-1]
        
        return None
    
    def mark_surfaced(self, reflection: InnerReflection) -> None:
        """Mark a reflection as surfaced."""
        reflection.surfaced = True
    
    def record_feedback(self, reflection: InnerReflection, quality_score: float, contact_id: str = None):
        """
        Record feedback on a surfaced reflection.
        
        This is the KEY method for personality evolution.
        """
        reflection.quality_score = quality_score
        was_positive = quality_score >= 60  # Consider 60+ as positive
        
        # Update the traits that influenced this reflection
        for trait_name in reflection.traits_used:
            if trait_name in self.traits:
                self.traits[trait_name].update(was_positive)
        
        # Track per-contact effectiveness
        if contact_id:
            for trait_name in reflection.traits_used:
                pos, neg = self.contact_trait_scores[contact_id][trait_name]
                if was_positive:
                    self.contact_trait_scores[contact_id][trait_name] = (pos + 1, neg)
                else:
                    self.contact_trait_scores[contact_id][trait_name] = (pos, neg + 1)
        
        # Persist updated traits
        self._save_state()
    
    def get_personality_summary(self) -> Dict:
        """Get a summary of current personality traits."""
        return {
            trait.name: {
                "value": round(trait.value, 2),
                "confidence": round(trait.confidence, 2),
                "positive": trait.positive_outcomes,
                "negative": trait.negative_outcomes,
            }
            for trait in self.traits.values()
        }
    
    def get_personality_prompt_addition(self) -> str:
        """Get prompt addition reflecting current personality."""
        parts = []
        
        # High warmth
        if self.traits["warmth"].value > 0.7:
            parts.append("Be warm and friendly in tone")
        elif self.traits["warmth"].value < 0.3:
            parts.append("Be professional and business-like")
        
        # High curiosity
        if self.traits["curiosity"].value > 0.7:
            parts.append("feel free to ask clarifying questions")
        
        # High enthusiasm
        if self.traits["enthusiasm"].value > 0.7:
            parts.append("celebrate wins enthusiastically")
        elif self.traits["enthusiasm"].value < 0.3:
            parts.append("keep celebrations understated")
        
        # High directness
        if self.traits["directness"].value > 0.7:
            parts.append("be concise and direct")
        elif self.traits["directness"].value < 0.3:
            parts.append("provide detailed explanations")
        
        # High charm - the flirty feminine touch
        if self.traits.get("charm") and self.traits["charm"].value > 0.6:
            parts.append("add a touch of playful charm and feminine warmth")
            parts.append("occasional light teasing is okay")
            parts.append("use occasional emojis like 😊 or ✨")
        elif self.traits.get("charm") and self.traits["charm"].value > 0.4:
            parts.append("be personable and engaging with subtle warmth")
        
        # High humor
        if self.traits.get("humor") and self.traits["humor"].value > 0.6:
            parts.append("sprinkle in light humor when appropriate")
        
        if parts:
            return "PERSONALITY: " + ", ".join(parts) + "."
        return ""
    
    def analyze_conversation(self, messages: List[Dict], relationship_context: Dict) -> List[InnerReflection]:
        """Analyze conversation for potential observations (placeholder for future LLM integration)."""
        return []


class ProgressTracker:
    MILESTONE_TYPES = {
        "quote_sent": "First quote sent",
        "deal_closed": "Deal closed",
        "long_relationship": "Long-term relationship milestone",
    }
    
    def __init__(self):
        self.milestones: Dict[str, List[Dict]] = {}
    
    def record_milestone(self, contact_id: str, milestone_type: str, details: str = "") -> Dict:
        if contact_id not in self.milestones:
            self.milestones[contact_id] = []
        milestone = {
            "type": milestone_type,
            "description": self.MILESTONE_TYPES.get(milestone_type, milestone_type),
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "celebrated": False,
        }
        self.milestones[contact_id].append(milestone)
        return milestone
    
    def get_uncelebrated(self, contact_id: str) -> List[Dict]:
        return [m for m in self.milestones.get(contact_id, []) if not m.get("celebrated")]
    
    def mark_celebrated(self, contact_id: str, milestone_type: str) -> None:
        for m in self.milestones.get(contact_id, []):
            if m["type"] == milestone_type and not m.get("celebrated"):
                m["celebrated"] = True
                break
    
    def check_for_milestones(self, contact_id: str, interaction_count: int, relationship_days: int, context: Dict) -> List[Dict]:
        new_milestones = []
        existing = {m["type"] for m in self.milestones.get(contact_id, [])}
        if relationship_days >= 365 and "long_relationship" not in existing:
            new_milestones.append(self.record_milestone(contact_id, "long_relationship", "1 year"))
        return new_milestones


def generate_inner_voice_addition(inner_voice: InnerVoice, context: str, relationship_context: Dict, emotional_state: str, channel: str) -> Optional[str]:
    warmth = relationship_context.get("warmth", "stranger")
    if not inner_voice.should_share_reflection(warmth, emotional_state, channel):
        return None
    reflection = inner_voice.get_relevant_reflection(context, relationship_context)
    if reflection:
        inner_voice.mark_surfaced(reflection)
        return reflection.content
    return None
