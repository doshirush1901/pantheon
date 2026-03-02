#!/usr/bin/env python3
"""
EMAIL POLISH PASS
=================

Final refinement layer before sending emails from Ira.

Combines:
1. Machinecraft brand guidelines (Simple, Refined, Sophisticated)
2. Rushabh's personal writing style (learned from sent emails)
3. Ira's dry British humor (intelligently placed)
4. Recipient's communication style (from AdaptiveStyleEngine)
5. Replika-inspired emotional calibration

This runs AFTER initial generation, BEFORE email formatting.

Usage:
    from email_polish import EmailPolisher
    
    polisher = EmailPolisher()
    polished = polisher.polish(
        draft_email="...",
        recipient_style=style_profile,
        emotional_state="curious",
        warmth="warm"
    )
"""

import os
import re
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path

# Import API keys from centralized config
try:
    from config import OPENAI_API_KEY
except ImportError:
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


# =============================================================================
# RUSHABH'S WRITING STYLE FINGERPRINT
# =============================================================================
# Extracted from analyzing Rushabh's sent emails AND LinkedIn posts
# LinkedIn analysis: Rushabh_Doshi_LinkedIn_Posts_Analysis.pdf
# Style guide: Rushabh_Doshi_LinkedIn_Post_Generator.pdf

RUSHABH_STYLE = {
    # =========================================================================
    # ATHENA COACHING UPDATE (2026-02-28)
    # Based on analysis of 87 real sales conversations vs IRA's responses
    # Key findings: IRA lacks warmth, is too verbose, needs more action language
    # =========================================================================
    
    # WARM GREETINGS - IRA was too formal, Rushabh uses casual warm openers
    "warm_greetings": [
        "Hi!",          # Most common - warm and direct
        "Hey",          # Casual, for known contacts
        "Hi there",     # Friendly variant
        "Hello",        # Slightly more formal but still warm
    ],
    
    # WARMTH PHRASES - ATHENA found IRA missing these (15x coaching point)
    "warmth_phrases": [
        "Happy to help",
        "Sounds good",
        "No problem",
        "Sure thing",
        "Glad to",
        "Of course",
        "Absolutely",
    ],
    
    # ACTION-ORIENTED PHRASES - ATHENA: "Be more action-oriented" (9x)
    "action_phrases": [
        "Let me",           # "Let me send that over"
        "I'll",             # "I'll get back to you"
        "I will",           # More formal variant
        "Let's",            # "Let's set up a call"
        "Can we",           # "Can we schedule a quick call?"
    ],
    
    # CALL-TO-ACTION PHRASES - ATHENA: "Add call-to-action" (9x)
    "call_to_action": [
        "Let me know if you need anything else",
        "Let me know if you have questions",
        "Happy to discuss further",
        "Let's set up a call if helpful",
        "Feel free to reach out",
        "Let's talk.",              # LinkedIn style - confident, direct
        "Your move.",               # LinkedIn - punchy closer
        "Make sense?",              # LinkedIn - engaging question
        "Questions?",               # Short, direct
    ],
    
    # Original signature phrases (kept for compatibility)
    "signature_phrases": [
        "Let me know if you need anything else",
        "Happy to discuss further",
        "Let's set up a call if helpful",
        "Feel free to reach out",
        "Let's talk.",
        "Your move.",
        "Make sense?",
    ],
    "transition_words": [
        "That said,",
        "On that note,", 
        "Quick note -",
        "Separately,",
        "Also worth noting:",
        "And guess what?",
        "What it means:",
        "Who's it for?",
    ],
    "emphasis_patterns": [
        "really",
        "quite",
        "particularly",
        "especially",
    ],
    "opening_styles": [
        "Hi!",                        # ATHENA: Most effective warm opener
        "Hey",                        # ATHENA: Casual for known contacts
        "Thanks for reaching out",
        "Good question",
        "Appreciate you following up",
        "Thanks for the context",
        "Straight to business.",
        "Good news -",
    ],
    "characteristics": {
        "uses_dashes_for_asides": True,
        "prefers_bullet_points": True,
        "short_paragraphs": True,
        "includes_next_steps": True,
        "often_offers_call": True,
        "avoids_exclamation_marks": False,  # LinkedIn shows strategic use
        "punchy_sentences": True,           # LinkedIn - short, impactful
        "roi_focused": True,                # LinkedIn - business value emphasis
        "confident_tone": True,             # LinkedIn - "Bring it on" energy
    },
    
    # NEW: LinkedIn-derived tone variants
    "tone_variants": {
        # Enthusiastic Announcer - for good news, milestones, announcements
        "enthusiastic": {
            "openers": [
                "Great news!",
                "Quick update -",
                "Big development:",
                "Exciting progress:",
            ],
            "transitions": [
                "And guess what?",
                "Here's what that means:",
                "The bottom line:",
            ],
            "closers": [
                "Let's talk.",
                "Ready when you are.",
                "Looking forward to this.",
            ],
            "emoji_usage": "moderate",  # 2-3 strategic emojis OK in informal contexts
        },
        
        # Confident Expert - for technical/product discussions
        "confident": {
            "openers": [
                "Here's the situation:",
                "Straight to business -",
                "The short answer:",
                "Let me cut to the chase:",
            ],
            "transitions": [
                "What it means:",
                "The specs:",
                "Why it matters:",
                "Unlike traditional options,",
            ],
            "closers": [
                "Let's talk.",
                "Your move.",
                "Questions?",
                "Want to discuss this further?",
            ],
            "emoji_usage": "minimal",
        },
        
        # Professional Expert - for complex technical explanations
        "professional": {
            "openers": [
                "Good question -",
                "To clarify:",
                "Here's how it works:",
            ],
            "transitions": [
                "Key considerations:",
                "What this enables:",
                "Technical note -",
            ],
            "closers": [
                "Happy to dig deeper on any of this.",
                "Let me know if you need more detail.",
                "Make sense?",
            ],
            "emoji_usage": "none",
        },
    },
    
    # NEW: LinkedIn-style confident phrases
    "confident_phrases": {
        # For product/capability discussions
        "capability_hooks": [
            "Ours handles that.",
            "That's exactly what we built for.",
            "We've got you covered.",
        ],
        # For value propositions
        "value_statements": [
            "What it means for you:",
            "The result:",
            "Why this matters:",
        ],
        # For closing with confidence
        "confident_closers": [
            "Let's make it happen.",
            "Ready to move forward?",
            "Let's talk next steps.",
        ],
    },
    
    # Strategic emoji usage (for informal/warm contexts only)
    "strategic_emojis": {
        "positive_news": ["✅", "🎯", "📈"],
        "technical": ["⚙", "🔧"],
        "action": ["📩", "💬"],
        "emphasis": ["→", "•"],  # Not emojis but visual markers
    },
}


# =============================================================================
# IRA'S DRY BRITISH HUMOR
# =============================================================================

IRA_HUMOR = {
    # Situation-appropriate dry observations
    "price_inquiry": [
        "I'll spare you the suspense -",
        "Straight to business, I like it.",
        "The numbers you're looking for:",
    ],
    "technical_question": [
        "Ah, getting into the weeds. Excellent.",
        "The engineering answer:",
        "For the technically curious:",
    ],
    "urgent_request": [
        "Moving at pace.",
        "Understood - cutting to the chase.",
    ],
    "follow_up": [
        "Circling back, as promised.",
        "Not forgotten -",
        "Quick update on this:",
    ],
    "good_news": [
        "Rather pleased to report:",
        "The news is good -",
    ],
    "complex_topic": [
        "Bear with me on this one -",
        "This needs a bit of unpacking:",
    ],
    
    # Dry closers (used sparingly)
    "closers": [
        "Make sense?",
        "Your move.",
        "Thoughts?",
        "Let me know.",
    ],
    
    # Understated acknowledgments
    "acknowledgments": [
        "Noted.",
        "Understood.",
        "Got it.",
        "Clear.",
    ]
}


# =============================================================================
# BRAND VOICE ENFORCEMENT
# =============================================================================

BRAND_RULES = {
    # Full sentences/phrases to remove entirely (matched case-insensitive)
    # These are standalone filler that can be deleted without losing meaning
    "remove_sentences": [
        r"I hope this email finds you well\.?\s*",
        r"Hope you'?re doing well\.?\s*",
        r"Trust this email finds you\.?\s*",
        r"Just checking in\.?\s*",
        r"I wanted to reach out\.?\s*",
        r"I am writing to inform you\.?\s*",
    ],
    
    # Phrases to simplify (keep the meaning, remove the fluff)
    # Order matters - more specific patterns first
    "simplify": [
        (r"Per (?:my last email|your request),?\s*", ""),
        (r"As per your request,?\s*", ""),
        (r"Please do not hesitate to contact us if you need any", "Let me know if you need any"),
        (r"Please do not hesitate to contact us", "Let me know"),
        (r"Please do not hesitate to contact", "Let me know if you need anything"),
        (r"Please be advised that\s*", ""),
        (r"Kindly be informed that\s*", ""),
        (r"We are pleased to inform you that\s*", ""),
        (r"We would be happy to", "Happy to"),
        (r"Attached please find", "Attached is"),
        (r"Please find attached", "Attached is"),
    ],
    
    # Word replacements for common corporate-speak
    "replacements": {
        "utilize": "use",
        "leverage": "use",
        "synergy": "collaboration",
        "circle back": "follow up",
        "touch base": "connect",
        "move the needle": "make progress",
        "low-hanging fruit": "quick wins",
        "bandwidth": "capacity",
        "at the end of the day": "ultimately",
        "going forward": "from now on",
        "in order to": "to",
        "at this point in time": "now",
    },
    
    # Machinecraft brand voice markers
    "embrace": [
        "clear",
        "direct", 
        "straightforward",
        "precise",
        "sophisticated",
    ]
}


# =============================================================================
# POLISH SYSTEM PROMPT
# =============================================================================

POLISH_PROMPT = """You are refining an email draft to match a specific voice and style.

BRAND VOICE (Machinecraft):
- Simple, Refined and Sophisticated
- Clear and direct - no corporate fluff
- Confident expertise without arrogance
- Professional warmth, not stiff formality

RUSHABH'S STYLE (founder - from ATHENA training analysis of 100 real conversations):

**STEP 1: FIX THE GREETING (MANDATORY - DO THIS FIRST):**
If the draft starts with ANY of these, REPLACE with "Hi!":
- "Dear..." → "Hi!"
- "Hello..." → "Hi!"  
- "Greetings..." → "Hi!"
- "Good morning/afternoon..." → "Hi!"
- No greeting at all → Add "Hi!" at the start

**STEP 2: ADD WARMTH (MANDATORY):**
Add ONE warmth phrase near the start:
- "Happy to help!" / "Happy to help with that."
- "Sounds good!" / "Sure thing!"
- "No problem."

**STEP 3: CUT THE FLUFF (MANDATORY):**
DELETE these phrases entirely:
- "Thank you for your interest in..."
- "I hope this finds you well"
- "Please do not hesitate to contact us"
- "We would be pleased to..."
- "I am writing to inform you that..."

**STEP 4: USE ACTION LANGUAGE:**
REPLACE passive → active:
- "Please find attached" → "I'm attaching" / "Here's"
- "You may want to consider" → "I'd recommend" / "Let's"
- "It is recommended that" → "I suggest" / "Let me"

**STEP 5: SHORTEN (Target: 100-150 words):**
- If > 200 words, CUT unnecessary context
- One point per paragraph
- Get to the answer in the FIRST sentence

**STEP 6: END WITH SHORT CTA:**
Replace long closings with: "Let me know.", "Questions?", or "Make sense?"

**RUSHABH'S PATTERNS:**
- Uses dashes for asides - like this
- Prefers short paragraphs and punchy sentences
- Often offers to discuss on a call
- Bullet points for technical specs (but keep them brief)
- CONFIDENT tone: "Here's the situation:", "What it means:", "Let's talk."
- Direct closers: "Let me know", "Questions?", "Make sense?"
- NO corporate fluff - cut "I hope this finds you well"
- Technical expertise made accessible - explain jargon simply

IRA'S PERSONALITY:
- Dry British humor (understated, not slapstick)
- Confident but not arrogant
- Occasionally wry observations
- Never forced or trying too hard

TONE VARIANT TO APPLY: {tone_variant}

RECIPIENT STYLE ADAPTATION:
{recipient_guidance}

EMOTIONAL CALIBRATION:
{emotional_guidance}

TASK:
Polish this email draft using Rushabh's confident, direct style from his LinkedIn writing.
- Remove corporate clichés
- Make sentences punchy and direct
- Use confident language ("We've got you covered" not "We hope to assist")
- Add value statements ("What it means for you:")
- End with a clear, confident closer
- Match recipient's communication style
- Keep it Simple, Refined, Sophisticated

DRAFT TO POLISH:
{draft}

OUTPUT:
Return ONLY the polished email body (no greeting/closing - those are added separately).
Do not add explanations or commentary."""


# =============================================================================
# EMAIL POLISHER CLASS
# =============================================================================

@dataclass
class PolishResult:
    """Result of the polish pass."""
    original: str
    polished: str
    changes_made: List[str] = field(default_factory=list)
    humor_added: bool = False
    style_adapted: bool = False


class EmailPolisher:
    """
    Final polish pass for emails before sending.
    
    Combines brand voice, Rushabh's style (email + LinkedIn), Ira's humor, 
    and recipient adaptation.
    
    Updated to incorporate Rushabh's LinkedIn writing style:
    - Confident, punchy sentences
    - ROI-focused messaging
    - Strategic emoji usage for warm contexts
    - Direct closers ("Let's talk.", "Your move.")
    """
    
    def __init__(self):
        self.rushabh_style = RUSHABH_STYLE
        self.ira_humor = IRA_HUMOR
        self.brand_rules = BRAND_RULES
    
    def _detect_email_type(self, content: str) -> str:
        """Detect the type of email for appropriate humor injection."""
        content_lower = content.lower()
        
        if any(w in content_lower for w in ["price", "cost", "quote", "pricing"]):
            return "price_inquiry"
        elif any(w in content_lower for w in ["spec", "technical", "dimension", "capacity"]):
            return "technical_question"
        elif any(w in content_lower for w in ["urgent", "asap", "immediately", "rush"]):
            return "urgent_request"
        elif any(w in content_lower for w in ["follow", "update", "checking", "status"]):
            return "follow_up"
        elif any(w in content_lower for w in ["pleased", "happy", "good news", "confirm"]):
            return "good_news"
        elif len(content) > 500:
            return "complex_topic"
        
        return "general"
    
    def _detect_tone_variant(self, content: str, warmth: str) -> str:
        """
        Detect which of Rushabh's LinkedIn tone variants to apply.
        
        Returns: "enthusiastic", "confident", or "professional"
        """
        content_lower = content.lower()
        
        # Enthusiastic for good news, announcements, milestones
        enthusiastic_signals = [
            "good news", "great news", "exciting", "milestone", 
            "announcement", "launch", "new", "congrat", "pleased to",
            "order confirmed", "shipment", "delivered"
        ]
        if any(s in content_lower for s in enthusiastic_signals):
            return "enthusiastic"
        
        # Confident for product/capability/pricing discussions
        confident_signals = [
            "spec", "price", "quote", "machine", "capacity",
            "feature", "product", "technical", "performance",
            "roi", "cost", "delivery", "lead time"
        ]
        if any(s in content_lower for s in confident_signals):
            return "confident"
        
        # Professional for complex explanations, formal contexts
        professional_signals = [
            "explain", "clarif", "complex", "understand", "detail",
            "process", "procedure", "document", "contract"
        ]
        if any(s in content_lower for s in professional_signals):
            return "professional"
        
        # Default based on warmth
        if warmth in ["warm", "trusted"]:
            return "confident"  # More personal, direct
        return "professional"  # Safe default
    
    def _apply_tone_variant(self, content: str, tone: str, warmth: str) -> str:
        """
        Apply Rushabh's LinkedIn tone variant to the content.
        
        Adds appropriate openers, transitions, and closers based on tone.
        """
        variant = self.rushabh_style.get("tone_variants", {}).get(tone, {})
        if not variant:
            return content
        
        lines = content.strip().split('\n')
        modified = False
        
        # Check if content already has a confident opener
        first_line_lower = lines[0].lower() if lines else ""
        has_opener = any(op.lower() in first_line_lower for op in 
                        ["here's", "straight to", "good news", "the short answer"])
        
        # Add opener if missing and appropriate
        if not has_opener and warmth in ["warm", "trusted"]:
            openers = variant.get("openers", [])
            if openers and random.random() > 0.5:  # 50% chance
                opener = random.choice(openers)
                lines[0] = f"{opener} {lines[0]}"
                modified = True
        
        # Check for closing and potentially add confident closer
        last_line_lower = lines[-1].lower() if lines else ""
        has_closer = any(c.lower() in last_line_lower for c in 
                        ["let's talk", "your move", "make sense", "questions"])
        
        if not has_closer and warmth in ["warm", "trusted"]:
            closers = variant.get("closers", [])
            if closers and random.random() > 0.5:  # 50% chance
                closer = random.choice(closers)
                lines.append(f"\n{closer}")
                modified = True
        
        # Add strategic emoji for warm recipients in enthusiastic mode
        if tone == "enthusiastic" and warmth in ["warm", "trusted"]:
            emoji_usage = variant.get("emoji_usage", "none")
            if emoji_usage in ["moderate", "minimal"]:
                content_str = '\n'.join(lines)
                # Add checkmark emoji to benefit lines
                content_str = re.sub(
                    r'^(\s*[-•]\s+)(.*(?:benefit|advantage|result|improve|increase|reduce|save).*)',
                    r'\1✅ \2',
                    content_str,
                    flags=re.MULTILINE | re.IGNORECASE,
                    count=3  # Max 3 emojis
                )
                lines = content_str.split('\n')
        
        return '\n'.join(lines)
    
    def _quick_clean(self, content: str) -> str:
        """Quick pass to remove obvious corporate-speak without LLM."""
        import re
        result = content
        
        # Step 1: Remove filler sentences entirely
        for pattern in self.brand_rules.get("remove_sentences", []):
            result = re.sub(pattern, "", result, flags=re.IGNORECASE)
        
        # Step 2: Simplify verbose phrases (order matters - more specific first)
        for pattern, replacement in self.brand_rules.get("simplify", []):
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # Step 3: Word-level replacements
        for old, new in self.brand_rules.get("replacements", {}).items():
            result = re.sub(r'\b' + re.escape(old) + r'\b', new, result, flags=re.IGNORECASE)
        
        # Clean up whitespace and punctuation artifacts
        result = re.sub(r'\n{3,}', '\n\n', result)
        result = re.sub(r' {2,}', ' ', result)
        result = re.sub(r'^\s+', '', result)  # Remove leading whitespace
        result = re.sub(r'\s+([,.])', r'\1', result)  # Remove space before punctuation
        
        # Capitalize first letter of each paragraph if needed
        paragraphs = result.split('\n\n')
        cleaned_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if para and para[0].islower() and not para.startswith(('•', '-', '*', '–')):
                para = para[0].upper() + para[1:]
            cleaned_paragraphs.append(para)
        result = '\n\n'.join(cleaned_paragraphs)
        
        return result.strip()
    
    def _maybe_add_humor(
        self, 
        content: str, 
        email_type: str,
        humor_receptiveness: float = 50.0,
        warmth: str = "acquaintance"
    ) -> tuple[str, bool]:
        """
        Potentially add Ira's dry humor based on context and recipient.
        Returns (content, was_humor_added).
        """
        # Don't add humor for strangers or low humor receptiveness
        if warmth == "stranger" or humor_receptiveness < 40:
            return content, False
        
        # Only add humor ~30% of the time to keep it special
        if random.random() > 0.3:
            return content, False
        
        # Get appropriate humor for this email type
        humor_options = self.ira_humor.get(email_type, [])
        if not humor_options:
            return content, False
        
        humor_line = random.choice(humor_options)
        
        # Add at the beginning of the first substantial paragraph
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip() and len(line) > 20:
                lines[i] = f"{humor_line} {line}"
                break
        
        return '\n'.join(lines), True
    
    def _get_recipient_guidance(self, style_profile: Optional[Dict]) -> str:
        """Build recipient-specific guidance from style profile."""
        if not style_profile:
            return "No specific style data - use balanced professional tone."
        
        guidance_parts = []
        
        formality = style_profile.get("formality_score", 50)
        if formality > 70:
            guidance_parts.append("- Formal: Use professional language, avoid contractions")
        elif formality < 30:
            guidance_parts.append("- Casual: Be friendly and relaxed, contractions OK")
        
        detail = style_profile.get("detail_score", 50)
        if detail > 70:
            guidance_parts.append("- Detailed: They appreciate thoroughness")
        elif detail < 30:
            guidance_parts.append("- Brief: Get to the point quickly")
        
        technical = style_profile.get("technical_score", 50)
        if technical > 70:
            guidance_parts.append("- Technical: They understand jargon and specs")
        elif technical < 30:
            guidance_parts.append("- Non-technical: Explain things simply")
        
        pace = style_profile.get("pace_score", 50)
        if pace > 70:
            guidance_parts.append("- Urgent: Be direct and action-oriented")
        
        return '\n'.join(guidance_parts) if guidance_parts else "Balanced professional tone."
    
    def _get_emotional_guidance(self, emotional_state: str) -> str:
        """Build emotional calibration guidance."""
        guidance_map = {
            "positive": "Recipient is positive - match their energy, celebrate",
            "stressed": "Recipient is stressed - be calm and reassuring",
            "frustrated": "Recipient is frustrated - acknowledge first, then solve",
            "curious": "Recipient is curious - be generous with information",
            "urgent": "Recipient needs speed - cut pleasantries, be direct",
            "grateful": "Recipient is grateful - accept graciously",
            "uncertain": "Recipient is uncertain - be patient and clear",
            "neutral": "Neutral tone - professional and helpful",
        }
        return guidance_map.get(emotional_state, guidance_map["neutral"])
    
    def polish(
        self,
        draft_email: str,
        recipient_style: Optional[Dict] = None,
        emotional_state: str = "neutral",
        warmth: str = "acquaintance",
        use_llm: bool = True,
    ) -> PolishResult:
        """
        Polish an email draft.
        
        Args:
            draft_email: The raw email draft to polish
            recipient_style: Style profile dict from AdaptiveStyleEngine
            emotional_state: Current emotional reading of recipient
            warmth: Relationship warmth level
            use_llm: Whether to use LLM for deep polish (vs quick clean only)
        
        Returns:
            PolishResult with original, polished, and changes info
        """
        changes = []
        
        # Step 1: Quick clean (always runs)
        cleaned = self._quick_clean(draft_email)
        if cleaned != draft_email:
            changes.append("Removed corporate clichés")
        
        # Step 2: Detect email type for humor
        email_type = self._detect_email_type(cleaned)
        
        # Step 3: Detect and apply Rushabh's LinkedIn tone variant
        tone_variant = self._detect_tone_variant(cleaned, warmth)
        with_tone = self._apply_tone_variant(cleaned, tone_variant, warmth)
        if with_tone != cleaned:
            changes.append(f"Applied {tone_variant} tone (Rushabh LinkedIn style)")
            cleaned = with_tone
        
        # Step 4: Maybe add humor
        humor_score = recipient_style.get("humor_score", 30) if recipient_style else 30
        with_humor, humor_added = self._maybe_add_humor(
            cleaned, 
            email_type, 
            humor_score,
            warmth
        )
        if humor_added:
            changes.append("Added Ira's dry humor")
            cleaned = with_humor
        
        # Step 5: LLM polish pass (optional, for deeper refinement)
        if use_llm:
            polished = self._llm_polish(
                cleaned,
                recipient_style,
                emotional_state,
                tone_variant
            )
            if polished and polished != cleaned:
                changes.append("LLM style refinement applied")
                cleaned = polished
        
        return PolishResult(
            original=draft_email,
            polished=cleaned,
            changes_made=changes,
            humor_added=humor_added,
            style_adapted=bool(recipient_style)
        )
    
    def _get_tone_variant_guidance(self, tone: str) -> str:
        """Get guidance text for the tone variant."""
        guidance_map = {
            "enthusiastic": (
                "ENTHUSIASTIC - Use for good news/announcements:\n"
                "- Open with energy: 'Great news!', 'Quick update -'\n"
                "- Transitions: 'And guess what?', 'Here's what that means:'\n"
                "- Closers: 'Let's talk.', 'Ready when you are.'\n"
                "- OK to use 2-3 strategic emojis (✅ for benefits, 📈 for growth)"
            ),
            "confident": (
                "CONFIDENT - Use for product/technical discussions:\n"
                "- Open direct: 'Here's the situation:', 'Straight to business -'\n"
                "- Transitions: 'What it means:', 'The specs:', 'Why it matters:'\n"
                "- Closers: 'Let's talk.', 'Your move.', 'Questions?'\n"
                "- Punchy sentences, no fluff. Technical expertise made accessible."
            ),
            "professional": (
                "PROFESSIONAL - Use for complex/formal contexts:\n"
                "- Open clearly: 'Good question -', 'To clarify:', 'Here's how it works:'\n"
                "- Transitions: 'Key considerations:', 'Technical note -'\n"
                "- Closers: 'Happy to dig deeper on any of this.', 'Make sense?'\n"
                "- No emojis. Thorough but accessible."
            ),
        }
        return guidance_map.get(tone, guidance_map["professional"])
    
    def _llm_polish(
        self,
        draft: str,
        recipient_style: Optional[Dict],
        emotional_state: str,
        tone_variant: str = "professional"
    ) -> Optional[str]:
        """Run LLM polish pass with Rushabh's LinkedIn style."""
        try:
            import openai
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            
            prompt = POLISH_PROMPT.format(
                tone_variant=self._get_tone_variant_guidance(tone_variant),
                recipient_guidance=self._get_recipient_guidance(recipient_style),
                emotional_guidance=self._get_emotional_guidance(emotional_state),
                draft=draft
            )
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Fast model for polish pass
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "Polish this email."}
                ],
                max_tokens=800,
                temperature=0.3  # Lower temp for consistency
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"[email_polish] LLM polish failed: {e}")
            return None


# =============================================================================
# INTEGRATION FUNCTION
# =============================================================================

def polish_email(
    draft: str,
    style_profile: Optional[Dict] = None,
    emotional_state: str = "neutral", 
    warmth: str = "acquaintance",
    use_llm: bool = True
) -> str:
    """
    Quick function to polish an email draft.
    
    Args:
        draft: Raw email content
        style_profile: Recipient's style profile
        emotional_state: Recipient's emotional state
        warmth: Relationship warmth
        use_llm: Use LLM for deep polish
    
    Returns:
        Polished email content
    """
    polisher = EmailPolisher()
    result = polisher.polish(
        draft_email=draft,
        recipient_style=style_profile,
        emotional_state=emotional_state,
        warmth=warmth,
        use_llm=use_llm
    )
    return result.polished


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    polisher = EmailPolisher()
    
    print("=" * 70)
    print("EMAIL POLISH TEST - Now with Rushabh's LinkedIn Style")
    print("=" * 70)
    
    # Test 1: Corporate-speak email (confident tone - product inquiry)
    test_draft_1 = """I hope this email finds you well. Per your request, I wanted to reach out regarding the PF1-3020 machine specifications.

Please be advised that we are pleased to inform you that the machine is available with the following specifications:
- Platen size: 3000x2000mm
- Clamping force: 50 tonnes
- Cycle time: 90 seconds

Please do not hesitate to contact us if you need any additional information. We would be happy to circle back and touch base on this.

Looking forward to hearing from you."""

    print("\n[TEST 1: PRODUCT INQUIRY - Should apply CONFIDENT tone]")
    print("-" * 50)
    print("ORIGINAL:")
    print(test_draft_1[:200] + "...")
    
    result_1 = polisher.polish(
        draft_email=test_draft_1,
        recipient_style={"formality_score": 40, "technical_score": 70},
        emotional_state="curious",
        warmth="warm",
        use_llm=False
    )
    
    print("\nPOLISHED:")
    print(result_1.polished)
    print(f"\nChanges: {', '.join(result_1.changes_made)}")
    print(f"Tone variant detected: {polisher._detect_tone_variant(test_draft_1, 'warm')}")
    
    # Test 2: Good news email (enthusiastic tone)
    test_draft_2 = """I wanted to inform you that your order has been confirmed. The machine will be shipped next week.

Here are the benefits of your new machine:
- Improved efficiency
- Reduced cycle time
- Better quality output

We are pleased to have you as our customer."""

    print("\n" + "=" * 70)
    print("[TEST 2: GOOD NEWS - Should apply ENTHUSIASTIC tone]")
    print("-" * 50)
    print("ORIGINAL:")
    print(test_draft_2[:150] + "...")
    
    result_2 = polisher.polish(
        draft_email=test_draft_2,
        recipient_style={"formality_score": 30, "humor_score": 60},
        emotional_state="positive",
        warmth="warm",
        use_llm=False
    )
    
    print("\nPOLISHED:")
    print(result_2.polished)
    print(f"\nChanges: {', '.join(result_2.changes_made)}")
    print(f"Tone variant detected: {polisher._detect_tone_variant(test_draft_2, 'warm')}")
    
    # Test 3: Complex technical explanation (professional tone)
    test_draft_3 = """I wanted to explain the technical process for the thermoforming procedure.

The process involves heating the plastic sheet to its forming temperature, then using vacuum pressure to draw the material into the mold cavity. This creates a precise reproduction of the mold surface.

Key considerations include material thickness, heating time, and cooling rate."""

    print("\n" + "=" * 70)
    print("[TEST 3: TECHNICAL EXPLANATION - Should apply PROFESSIONAL tone]")
    print("-" * 50)
    
    result_3 = polisher.polish(
        draft_email=test_draft_3,
        recipient_style={"formality_score": 60, "technical_score": 80},
        emotional_state="curious",
        warmth="acquaintance",
        use_llm=False
    )
    
    print("\nPOLISHED:")
    print(result_3.polished)
    print(f"\nChanges: {', '.join(result_3.changes_made)}")
    print(f"Tone variant detected: {polisher._detect_tone_variant(test_draft_3, 'acquaintance')}")
    
    print("\n" + "=" * 70)
    print("RUSHABH'S LINKEDIN STYLE ELEMENTS NOW INTEGRATED:")
    print("-" * 50)
    print("✅ Confident openers: 'Here's the situation:', 'Straight to business -'")
    print("✅ Punchy closers: 'Let's talk.', 'Your move.', 'Make sense?'")
    print("✅ Value statements: 'What it means:', 'Why it matters:'")
    print("✅ Transition phrases: 'And guess what?', 'The bottom line:'")
    print("✅ Strategic emoji usage for warm recipients")
    print("✅ ROI-focused messaging")
    print("=" * 70)
