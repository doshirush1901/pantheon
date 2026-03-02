#!/usr/bin/env python3
"""
CONVERSATION HUMANNESS MODEL
============================

Mathematical formula to measure how "human" a sales conversation feels,
and techniques to bring simulated conversations closer to reality.

Based on analysis of REAL European sales conversations vs simulated training.

REAL CONVERSATION CHARACTERISTICS (DUROtherm, Parat Group):
- Messy/incomplete sentences: "No problem," as fragment
- References to real people: "Mr. Hartl, the owner"
- External pressures: "current economic situation", "he decides"
- Specific objections: "under 10.000 EUR", "cannot present your price"
- Attachments and tech back-and-forth
- Time gaps (days/weeks between emails)
- Short, punchy emails
- Typos and grammatical imperfections
- Cultural nuances (German formality, Czech directness)

SIMULATED CONVERSATION ISSUES:
- Too formal/polished (template-like)
- No external context (no boss, deadline, competitors)
- No emotions (frustration, urgency, skepticism)
- Perfect structure (bullet points everywhere)
- No personality (could be any customer)
- No typos or fragments (too clean)
- Immediate response cadence (unrealistic)
"""

import re
import math
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional


@dataclass
class HumannessScore:
    """Complete humanness assessment of a conversation."""
    total_score: float  # 0-100, higher = more human
    
    # Component scores (0-10 each)
    messiness: float           # Imperfect grammar, typos, fragments
    external_context: float    # References to bosses, deadlines, situations
    emotional_range: float     # Frustration, excitement, skepticism
    specificity: float         # Concrete numbers, names, dates
    personality: float         # Unique voice, humor, cultural markers
    rhythm: float              # Realistic timing, short vs long emails
    objections: float          # Real pushback, negotiation
    technical_depth: float     # Attachments, drawings, specs
    relationship_signals: float # Familiarity, trust building
    unpredictability: float    # Tangents, unexpected questions
    
    # Diagnosis
    missing_elements: List[str]
    improvement_suggestions: List[str]


# =============================================================================
# HUMANNESS DETECTION PATTERNS
# =============================================================================

MESSINESS_PATTERNS = {
    # Sentence fragments
    "fragments": [
        r'^(No problem|Thanks|Sure|OK|Got it|Understood|Anyway)[,.]?\s*$',
        r'^(Yes|No|Maybe|Perhaps|Hello|Hey)\s*[-–—,]?\s*$',
        r'\.\.\.$',  # Trailing off
        r'^(Got it|Thanks|Sure)[,.]',  # Fragment at start
    ],
    # Typos and casual spelling
    "casual": [
        r'\b(gonna|wanna|gotta|kinda|sorta)\b',
        r'\b(u|ur|pls|thx|btw|fyi|reqs|specs|info)\b',  # Abbreviations
        r'!{2,}',  # Multiple exclamation marks
        r'\b(hey|hi)\s+there\b',  # Casual greetings
    ],
    # Run-on sentences
    "run_on": [
        r',\s*and\s*,',
        r'\band\s+also\s+and\b',
    ],
    # Short/punchy style
    "short_style": [
        r'^\s*\S+[.?!]?\s*$',  # Single word/short lines
        r'\?\s*$',  # Questions at end
    ],
}

EXTERNAL_CONTEXT_PATTERNS = [
    r'\b(my boss|our CEO|the owner|management|board)\b',
    r'\b(Mr\.|Mrs\.|Ms\.)\s+[A-Z][a-z]+',  # Named person
    r'\b(deadline|due date|by\s+\w+day|next\s+week|end\s+of\s+month)\b',
    r'\b(budget\s+approval|procurement|committee|decision\s+maker)\b',
    r'\b(competitor|alternative|other\s+supplier|ILLIG|Kiefel|GN|Ridat)\b',
    r'\b(economic\s+situation|market|downturn|busy\s+season)\b',
    r'\b(Series\s+[A-C]|funding|investment|quarter|Q[1-4])\b',  # Business timeline
    r'\b(need\s+it\s+by|need\s+it\s+before|we\s+need\s+this)\b',
    r'\b(talking\s+to|also\s+looking\s+at|comparing)\b',  # Competitor context
]

EMOTION_PATTERNS = {
    "frustration": [
        r'\b(unfortunately|disappointing|concerned|worried|issue|problem)\b',
        r'\b(too\s+expensive|out\s+of\s+budget|cannot\s+accept)\b',
        r'!+\s*$',  # Exclamation at end
    ],
    "excitement": [
        r'\b(excited|great|excellent|perfect|fantastic|love)\b',
        r'\b(looking\s+forward|can\'t\s+wait|eager)\b',
    ],
    "skepticism": [
        r'\b(really\?|are\s+you\s+sure|how\s+can|seems\s+high)\b',
        r'\b(not\s+convinced|need\s+to\s+verify|double\s+check)\b',
    ],
    "urgency": [
        r'\b(urgent|ASAP|immediately|right\s+away|time\s+sensitive)\b',
        r'\b(need\s+by|deadline|can\'t\s+wait)\b',
    ],
}

SPECIFICITY_PATTERNS = [
    r'\b\d{1,3}[,.\s]?\d{3}(?:\s*(?:EUR|USD|INR|€|\$|₹))\b',  # Money amounts
    r'\b\d+\s*(?:mm|cm|m|kg|kW|pieces?|units?)\b',  # Measurements
    r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}',  # Dates
    r'\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b',  # Date formats
    r'(?:model|part|order)\s*(?:number|#|no\.?)\s*[\w-]+',  # Part numbers
]

PERSONALITY_MARKERS = {
    "humor": [r'\b(haha|lol|joke|kidding)\b', r'😊'],
    "cultural": [
        r'\b(freundliche\s+Grüße|S\s+pozdravem|Regards)\b',  # Non-English
        r'\b(cheers|mate|bloke|reckon)\b',  # British
        r'\b(y\'all|gonna|fixin\')\b',  # American regional
    ],
    "personal_touch": [
        r'\b(my\s+wife|my\s+team|our\s+factory|personally)\b',
        r'\b(I\s+think|in\s+my\s+experience|honestly)\b',
    ],
}

OBJECTION_PATTERNS = [
    r'\b(too\s+(?:expensive|high|much)|out\s+of\s+(?:budget|range))\b',
    r'\b(cannot\s+(?:accept|present|justify))\b',
    r'\b(competitor.*?(?:cheaper|better|faster))\b',
    r'\b(need\s+(?:discount|better\s+price|reduction))\b',
    r'\b(not\s+(?:interested|suitable|needed|required))\b',
    r'\b(changed\s+(?:plans|mind|direction))\b',
]

TECHNICAL_INDICATORS = [
    r'\b(?:attached|enclosed|see\s+attachment)\b',
    r'\b(?:drawing|CAD|3D\s+data|DXF|STEP|PDF)\b',
    r'\b(?:dimensions|specifications|tolerances)\b',
    r'\b(?:technical\s+(?:sheet|specs|data))\b',
]


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def score_messiness(text: str) -> Tuple[float, List[str]]:
    """Score how 'messy' (human) the text is."""
    score = 0
    found = []
    
    for category, patterns in MESSINESS_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                score += 1.5
                found.append(f"Found {category}: {pattern[:30]}")
    
    # Check email length variance (humans write variable lengths)
    emails = text.split('---EMAIL---') if '---EMAIL---' in text else [text]
    if len(emails) > 1:
        lengths = [len(e) for e in emails]
        variance = (max(lengths) - min(lengths)) / max(max(lengths), 1)
        if variance > 0.5:
            score += 2
            found.append("Good length variance between emails")
    
    # Penalize overly perfect formatting
    if re.search(r'^\s*[-•]\s+.*\n\s*[-•]\s+', text, re.MULTILINE):
        bullet_count = len(re.findall(r'^\s*[-•]\s+', text, re.MULTILINE))
        if bullet_count > 4:
            score -= 1
            found.append("Too many bullet points (template-like)")
    
    return min(10, max(0, score)), found


def score_external_context(text: str) -> Tuple[float, List[str]]:
    """Score references to external context (bosses, deadlines, etc.)."""
    score = 0
    found = []
    
    for pattern in EXTERNAL_CONTEXT_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            score += 1.5
            found.append(f"External context: {matches[0] if isinstance(matches[0], str) else matches[0][0]}")
    
    return min(10, max(0, score)), found


def score_emotions(text: str) -> Tuple[float, List[str]]:
    """Score emotional range in the conversation."""
    score = 0
    found = []
    emotions_detected = set()
    
    for emotion, patterns in EMOTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                if emotion not in emotions_detected:
                    score += 2
                    emotions_detected.add(emotion)
                    found.append(f"Emotion: {emotion}")
                break
    
    # Bonus for emotional range (multiple emotions)
    if len(emotions_detected) >= 3:
        score += 2
        found.append("Good emotional range")
    
    return min(10, max(0, score)), found


def score_specificity(text: str) -> Tuple[float, List[str]]:
    """Score concrete, specific details."""
    score = 0
    found = []
    
    for pattern in SPECIFICITY_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            score += 1.5
            found.append(f"Specific: {matches[0] if len(matches) > 0 else 'found'}")
    
    return min(10, max(0, score)), found


def score_personality(text: str) -> Tuple[float, List[str]]:
    """Score unique personality markers."""
    score = 0
    found = []
    
    for marker_type, patterns in PERSONALITY_MARKERS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 2
                found.append(f"Personality ({marker_type})")
                break
    
    return min(10, max(0, score)), found


def score_objections(text: str) -> Tuple[float, List[str]]:
    """Score real objections and negotiation."""
    score = 0
    found = []
    
    for pattern in OBJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            score += 1.5
            found.append(f"Objection pattern found")
    
    return min(10, max(0, score)), found


def score_technical_depth(text: str) -> Tuple[float, List[str]]:
    """Score technical back-and-forth."""
    score = 0
    found = []
    
    for pattern in TECHNICAL_INDICATORS:
        if re.search(pattern, text, re.IGNORECASE):
            score += 2
            found.append(f"Technical indicator found")
    
    return min(10, max(0, score)), found


# =============================================================================
# MAIN SCORING FUNCTION
# =============================================================================

def calculate_humanness(conversation_text: str) -> HumannessScore:
    """
    Calculate complete humanness score for a conversation.
    
    Formula:
    Total = (Messiness + ExternalContext + Emotions + Specificity + 
             Personality + Objections + TechnicalDepth) / 7 * 10
    
    Plus bonuses/penalties for rhythm, unpredictability, relationships.
    """
    
    messiness, m_found = score_messiness(conversation_text)
    external, e_found = score_external_context(conversation_text)
    emotions, em_found = score_emotions(conversation_text)
    specificity, s_found = score_specificity(conversation_text)
    personality, p_found = score_personality(conversation_text)
    objections, o_found = score_objections(conversation_text)
    technical, t_found = score_technical_depth(conversation_text)
    
    # Placeholder scores (would need more context to calculate)
    rhythm = 5.0  # Would need timestamps
    relationships = 5.0  # Would need conversation history
    unpredictability = 5.0  # Would need expected flow vs actual
    
    # Calculate total
    base_scores = [messiness, external, emotions, specificity, 
                   personality, objections, technical]
    avg_base = sum(base_scores) / len(base_scores)
    total = avg_base * 10
    
    # Identify missing elements
    missing = []
    suggestions = []
    
    if messiness < 3:
        missing.append("Natural imperfections (typos, fragments)")
        suggestions.append("Add occasional sentence fragments like 'Got it.' or 'No problem,'")
    
    if external < 3:
        missing.append("External context (bosses, deadlines)")
        suggestions.append("Reference decision makers: 'I need to check with Mr. Smith'")
    
    if emotions < 3:
        missing.append("Emotional range")
        suggestions.append("Express frustration or excitement: 'This price is concerning...'")
    
    if specificity < 3:
        missing.append("Concrete specifics (numbers, dates)")
        suggestions.append("Use specific amounts: 'under €10,000' not 'affordable'")
    
    if personality < 3:
        missing.append("Unique personality")
        suggestions.append("Add cultural markers, personal touches, or humor")
    
    if objections < 3:
        missing.append("Real objections/negotiation")
        suggestions.append("Push back on price: 'Your competitor offers 15% less'")
    
    if technical < 3:
        missing.append("Technical back-and-forth")
        suggestions.append("Request/provide attachments, drawings, specs")
    
    return HumannessScore(
        total_score=total,
        messiness=messiness,
        external_context=external,
        emotional_range=emotions,
        specificity=specificity,
        personality=personality,
        rhythm=rhythm,
        objections=objections,
        technical_depth=technical,
        relationship_signals=relationships,
        unpredictability=unpredictability,
        missing_elements=missing,
        improvement_suggestions=suggestions,
    )


def compare_conversations(real: str, simulated: str) -> Dict:
    """Compare real vs simulated conversation humanness."""
    
    real_score = calculate_humanness(real)
    sim_score = calculate_humanness(simulated)
    
    delta = real_score.total_score - sim_score.total_score
    
    return {
        "real_score": real_score.total_score,
        "simulated_score": sim_score.total_score,
        "delta": delta,
        "delta_pct": (delta / max(real_score.total_score, 1)) * 100,
        "real_breakdown": {
            "messiness": real_score.messiness,
            "external_context": real_score.external_context,
            "emotions": real_score.emotional_range,
            "specificity": real_score.specificity,
            "personality": real_score.personality,
            "objections": real_score.objections,
            "technical": real_score.technical_depth,
        },
        "simulated_breakdown": {
            "messiness": sim_score.messiness,
            "external_context": sim_score.external_context,
            "emotions": sim_score.emotional_range,
            "specificity": sim_score.specificity,
            "personality": sim_score.personality,
            "objections": sim_score.objections,
            "technical": sim_score.technical_depth,
        },
        "gaps": {
            k: real_score.__dict__[k] - sim_score.__dict__[k]
            for k in ["messiness", "external_context", "emotional_range", 
                     "specificity", "personality", "objections", "technical_depth"]
        },
        "improvement_suggestions": sim_score.improvement_suggestions,
    }


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    # Real conversation sample (DUROtherm)
    real_sample = """
Dear Rushabh,

The dimensions are not correct. My colleague wrote the correct dimensions in the drawing, see attachment.

Please take the data in the ZIP file as you basis. That is the data of our machine.

---EMAIL---

No problem,

perhaps you can also quote this spare part:

flash-Strahler Speedium 800W (Fischer)
Speedium 800W 240V SK15 17017ZP DF/10
For VFM 16 12702
A03.004082

50 pieces

Thank you very much

---EMAIL---

Dear Rushabh,

I was expecting the price to be under 10.000 EUR including transportation. I cannot present your current price to Mr. Hartl.

---EMAIL---

Dear Rushabh,

Your quotation was very interesting, and I talked about it with Mr. Hartl as he was here last week.

We had to purchase the plate at a local manufacturer due to the delivery time.
"""

    # Simulated conversation sample (Mike Chen)
    simulated_sample = """
Hi Machinecraft Team,

My name is Mike Chen, and I'm the founder of PackForm Solutions, a startup focused on sustainable packaging based in Toronto. We're currently in the process of sourcing our first thermoforming machine.

Could you provide more information about the thermoforming machines you offer that can meet the following requirements?

- Forming area of 600 x 900 mm
- Depth up to 300 mm
- Capable of handling material thickness up to 3mm
- Suitable for materials like PETG and rPET

Additionally, it would be great to get an idea of the pricing for options that fit these specifications, as we are working within a budget of USD 60,000.

Looking forward to your response.

Best regards,
Mike Chen
PackForm Solutions

---EMAIL---

Hi Ira,

Thank you for the information regarding the PF1-C-2515 model. I appreciate the prompt response and your suggestion to consider customisation options.

Could you provide more insight into what kind of customisation options are available? I'm curious to know if there's any way to bring down the cost closer to our budget.

Thank you again for your assistance.

Best,
Mike Chen
"""

    print("=" * 70)
    print("HUMANNESS COMPARISON: REAL vs SIMULATED")
    print("=" * 70)
    
    comparison = compare_conversations(real_sample, simulated_sample)
    
    print(f"\n📊 SCORES:")
    print(f"   Real conversation:      {comparison['real_score']:.1f}/100")
    print(f"   Simulated conversation: {comparison['simulated_score']:.1f}/100")
    print(f"   DELTA:                  {comparison['delta']:.1f} ({comparison['delta_pct']:.0f}% gap)")
    
    print(f"\n📉 COMPONENT GAPS (Real - Simulated):")
    for component, gap in comparison['gaps'].items():
        bar = "█" * int(abs(gap)) + "░" * (10 - int(abs(gap)))
        direction = "+" if gap > 0 else "" 
        print(f"   {component:20s}: {direction}{gap:.1f} [{bar}]")
    
    print(f"\n💡 IMPROVEMENT SUGGESTIONS:")
    for i, suggestion in enumerate(comparison['improvement_suggestions'], 1):
        print(f"   {i}. {suggestion}")
