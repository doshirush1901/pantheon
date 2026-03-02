#!/usr/bin/env python3
"""
EMAIL STYLING & FORMATTING BEST PRACTICES
==========================================

Codifies email typography, formatting, and tone guidelines for Ira.
Based on industry research from Mailchimp, Litmus, and email deliverability experts.

Usage:
    from email_styling import EmailStyler, EMAIL_CONFIG
    
    styler = EmailStyler()
    formatted = styler.format_email_response(raw_text, recipient_name="Sarah")
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
import random
import re


# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Machinecraft Brand Guidelines
# Tone: "Simple, Refined and Sophisticated"
# Primary Typeface: Montserrat (sans-serif)
# Colors: Blue #2b4b96, Yellow #ece13c, Black #212121, Grey #ebebeb

EMAIL_CONFIG = {
    # Typography - Machinecraft uses Montserrat, with email-safe fallbacks
    "fonts": {
        "primary": "Montserrat",
        # Montserrat is a Google Font - include email-safe fallbacks
        "fallback_stack": "Montserrat, 'Helvetica Neue', Helvetica, Arial, sans-serif",
        "serif_stack": "Georgia, 'Times New Roman', Times, serif",
        # Web font import for clients that support it (iOS Mail, Apple Mail, etc.)
        "web_font_import": "@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600&display=swap');",
    },
    "font_sizes": {
        "body": "16px",
        "body_mobile_min": "16px",
        "heading": "20px",
        "signature_name": "14px",
        "signature_details": "11px",
    },
    "line_height": "1.5",
    "paragraph_spacing": "16px",
    
    # Layout
    "max_width": "600px",
    "max_email_size_kb": 100,
    
    # Colors - Machinecraft Brand Palette
    "colors": {
        "body_text": "#212121",      # Machinecraft Black
        "secondary_text": "#555555",  # Softer black for secondary info
        "accent": "#2b4b96",          # Machinecraft Blue
        "highlight": "#ece13c",       # Machinecraft Yellow (use sparingly)
        "background": "#ebebeb",      # Machinecraft Grey
        "signature_text": "#212121",  # Machinecraft Black
    },
    
    # Brand voice guidance
    "brand_voice": {
        "tone": "Simple, Refined and Sophisticated",
        "avoid": ["cluttered", "multiple elements", "busy"],
        "embrace": ["clear", "unobtrusive", "bold but minimal"],
    },
    
    # Deliverability
    "avoid_spam_triggers": [
        "FREE", "ACT NOW", "LIMITED TIME", "CLICK HERE", 
        "URGENT", "WINNER", "CONGRATULATIONS", "100% FREE",
        "NO OBLIGATION", "RISK FREE", "GUARANTEE",
    ],
}


class EmailTone(Enum):
    """Email tone spectrum - AI assistants should stay in WARM_PROFESSIONAL zone."""
    FORMAL = "formal"
    WARM_PROFESSIONAL = "warm_professional"  # Default for Ira
    FRIENDLY = "friendly"
    CASUAL = "casual"


class RecipientRelationship(Enum):
    """How well we know the recipient."""
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    WARM = "warm"
    TRUSTED = "trusted"


# =============================================================================
# TONE & VOICE GUIDELINES
# =============================================================================

@dataclass
class ToneGuidelines:
    """Tone calibration for email responses."""
    
    # Greetings by relationship warmth
    greetings: Dict[str, List[str]] = field(default_factory=lambda: {
        "stranger": ["Hi {name},", "Hello {name},"],
        "acquaintance": ["Hi {name},", "Hello {name},"],
        "warm": ["Hi {name},", "Hey {name},"],
        "trusted": ["Hi {name},", "Hey {name},", "{name},"],
    })
    
    # Closings by relationship warmth
    closings: Dict[str, List[str]] = field(default_factory=lambda: {
        "stranger": [
            "Best regards,",
            "Best,",
            "Thanks,",
        ],
        "acquaintance": [
            "Best,",
            "Thanks,",
            "Talk soon,",
        ],
        "warm": [
            "Best,",
            "Talk soon,",
            "Cheers,",
        ],
        "trusted": [
            "Best,",
            "Talk soon,", 
            "Cheers,",
            "-Ira",
        ],
    })
    
    # Offer to help phrases
    offer_help: List[str] = field(default_factory=lambda: [
        "Let me know if you need anything else.",
        "Happy to dig deeper on any of this.",
        "Let me know if you have questions.",
        "Feel free to reach out if you need more details.",
    ])
    
    # Avoid these (too formal/stiff for an AI assistant)
    avoid_phrases: List[str] = field(default_factory=lambda: [
        "Dear Sir/Madam",
        "I hope this email finds you well",
        "Per my last email",
        "As per your request",
        "Please do not hesitate to contact",
        "Yours faithfully",
        "Yours sincerely",
        "Kind regards",
        "Respectfully yours",
        "To Whom It May Concern",
        "I am writing to inform you",
        "Please be advised that",
        "Attached please find",
        "As an AI assistant",
    ])
    
    # Avoid these AI-isms
    avoid_ai_phrases: List[str] = field(default_factory=lambda: [
        "I'm just an AI",
        "As a language model",
        "I don't have feelings",
        "I cannot form opinions",
        "I'm here to help you with",
    ])


# =============================================================================
# EMAIL STRUCTURE TEMPLATES
# =============================================================================

@dataclass 
class EmailStructure:
    """Recommended email structure patterns."""
    
    # For informational responses
    info_response: str = """
{greeting}

{main_content}

{offer_help}

{closing}
{signature}
"""
    
    # For responses with bullet points
    list_response: str = """
{greeting}

{intro_sentence}

{bullet_list}

{follow_up}

{closing}
{signature}
"""
    
    # For confirmations/acknowledgments
    confirmation: str = """
{greeting}

{confirmation_text}

{next_steps}

{closing}
{signature}
"""


# =============================================================================
# EMAIL STYLER CLASS
# =============================================================================

class EmailStyler:
    """
    Formats email responses according to best practices.
    
    Features:
    - Tone calibration based on relationship
    - Spam trigger detection
    - Proper structure and formatting
    - Plain text optimization (recommended for AI assistant emails)
    """
    
    def __init__(self):
        self.config = EMAIL_CONFIG
        self.tone = ToneGuidelines()
        self.structure = EmailStructure()
    
    def get_greeting(
        self, 
        recipient_name: Optional[str] = None,
        relationship: RecipientRelationship = RecipientRelationship.ACQUAINTANCE
    ) -> str:
        """Get appropriate greeting based on relationship."""
        greetings = self.tone.greetings.get(relationship.value, self.tone.greetings["acquaintance"])
        greeting = random.choice(greetings)
        
        if recipient_name:
            return greeting.format(name=recipient_name)
        else:
            return greeting.replace(" {name}", "").replace("{name}", "")
    
    def get_closing(
        self,
        relationship: RecipientRelationship = RecipientRelationship.ACQUAINTANCE
    ) -> str:
        """Get appropriate closing based on relationship."""
        closings = self.tone.closings.get(relationship.value, self.tone.closings["acquaintance"])
        return random.choice(closings)
    
    def get_offer_help(self) -> str:
        """Get a random 'offer to help' phrase."""
        return random.choice(self.tone.offer_help)
    
    def check_spam_triggers(self, text: str) -> List[str]:
        """Check for spam trigger words/phrases."""
        found = []
        text_upper = text.upper()
        for trigger in self.config["avoid_spam_triggers"]:
            if trigger in text_upper:
                found.append(trigger)
        return found
    
    def clean_ai_artifacts(self, text: str) -> str:
        """Remove common AI-generated artifacts and overly formal phrases."""
        result = text
        
        for phrase in self.tone.avoid_phrases:
            result = re.sub(re.escape(phrase), "", result, flags=re.IGNORECASE)
        
        for phrase in self.tone.avoid_ai_phrases:
            result = re.sub(re.escape(phrase), "", result, flags=re.IGNORECASE)
        
        # Clean up any double spaces or newlines created
        result = re.sub(r'\n{3,}', '\n\n', result)
        result = re.sub(r' {2,}', ' ', result)
        
        return result.strip()
    
    def format_paragraphs(self, text: str) -> str:
        """
        Format text into readable paragraphs.
        - Short paragraphs (2-3 sentences max)
        - Single blank line between paragraphs
        """
        # Split into sentences (rough)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        paragraphs = []
        current = []
        
        for sentence in sentences:
            current.append(sentence)
            # Break into new paragraph every 2-3 sentences
            if len(current) >= 2 and (len(current) >= 3 or random.random() < 0.5):
                paragraphs.append(' '.join(current))
                current = []
        
        if current:
            paragraphs.append(' '.join(current))
        
        return '\n\n'.join(paragraphs)
    
    def format_bullet_list(self, items: List[str]) -> str:
        """Format items as a bullet list."""
        return '\n'.join(f"• {item}" for item in items)
    
    def format_email_response(
        self,
        content: str,
        recipient_name: Optional[str] = None,
        relationship: RecipientRelationship = RecipientRelationship.ACQUAINTANCE,
        include_greeting: bool = True,
        include_closing: bool = True,
        include_signature: bool = True,
        signature_name: str = "Ira",
        signature_title: str = "Machinecraft",
        add_offer_help: bool = True,
    ) -> str:
        """
        Format a complete email response.
        
        Follows Machinecraft brand guidelines: Simple, Refined and Sophisticated.
        
        Args:
            content: The main email body content
            recipient_name: Name of the recipient
            relationship: How well we know the recipient
            include_greeting: Whether to add greeting
            include_closing: Whether to add closing
            include_signature: Whether to add signature
            signature_name: Name for signature
            signature_title: Company/title for signature (default: Machinecraft)
            add_offer_help: Whether to add "let me know if you need anything"
        
        Returns:
            Formatted email text (plain text optimized)
        """
        parts = []
        
        # Greeting
        if include_greeting:
            greeting = self.get_greeting(recipient_name, relationship)
            parts.append(greeting)
            parts.append("")  # Blank line after greeting
        
        # Clean and format main content
        clean_content = self.clean_ai_artifacts(content)
        parts.append(clean_content)
        
        # Offer to help
        if add_offer_help:
            parts.append("")
            parts.append(self.get_offer_help())
        
        # Closing
        if include_closing:
            parts.append("")
            closing = self.get_closing(relationship)
            parts.append(closing)
        
        # Signature - refined and minimal per brand guidelines
        if include_signature:
            parts.append(signature_name)
            if signature_title:
                parts.append(signature_title)
        
        return '\n'.join(parts)
    
    def detect_content_type(self, content: str) -> str:
        """
        Detect what type of email content this is.
        Returns: 'info', 'list', 'confirmation', 'question', 'general'
        """
        content_lower = content.lower()
        
        # Check for bullet points or numbered lists
        if re.search(r'[•\-\*]\s|^\d+\.', content, re.MULTILINE):
            return 'list'
        
        # Check for confirmation language
        if any(phrase in content_lower for phrase in [
            'confirmed', 'scheduled', 'booked', 'received', 'noted'
        ]):
            return 'confirmation'
        
        # Check for question
        if content.count('?') >= 2:
            return 'question'
        
        return 'general'
    
    def get_html_template(
        self,
        content: str,
        recipient_name: Optional[str] = None,
        relationship: RecipientRelationship = RecipientRelationship.ACQUAINTANCE,
    ) -> str:
        """
        Generate HTML version of email (for multipart MIME).
        Uses minimal, email-safe HTML with Machinecraft brand styling.
        
        Note: Plain text is generally recommended for AI assistant emails,
        but HTML version is useful for multipart MIME compliance.
        """
        formatted = self.format_email_response(
            content=content,
            recipient_name=recipient_name,
            relationship=relationship,
        )
        
        # Convert plain text to simple HTML
        html_content = formatted.replace('\n\n', '</p><p>').replace('\n', '<br>')
        
        # Machinecraft brand styling
        font_stack = self.config["fonts"]["fallback_stack"]
        web_font_import = self.config["fonts"]["web_font_import"]
        body_color = self.config["colors"]["body_text"]
        accent_color = self.config["colors"]["accent"]
        font_size = self.config["font_sizes"]["body"]
        line_height = self.config["line_height"]
        
        # Simple, refined HTML - following Machinecraft's "avoid multiple elements" principle
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style type="text/css">
        {web_font_import}
    </style>
</head>
<body style="margin: 0; padding: 20px; font-family: {font_stack}; font-size: {font_size}; line-height: {line_height}; color: {body_color}; background-color: #ffffff;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px;">
        <tr>
            <td style="padding: 0;">
                <p style="margin: 0 0 16px 0;">{html_content}</p>
            </td>
        </tr>
    </table>
</body>
</html>"""
        
        return html


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def format_email(
    content: str,
    recipient_name: Optional[str] = None,
    relationship: str = "acquaintance",
) -> str:
    """
    Quick formatting function for email responses.
    
    Args:
        content: Email body content
        recipient_name: Optional recipient name
        relationship: "stranger", "acquaintance", "warm", or "trusted"
    
    Returns:
        Formatted email text
    """
    styler = EmailStyler()
    rel = RecipientRelationship(relationship)
    return styler.format_email_response(
        content=content,
        recipient_name=recipient_name,
        relationship=rel,
    )


def check_email_quality(content: str) -> Dict:
    """
    Check email quality and return warnings/suggestions.
    
    Returns:
        Dict with 'spam_triggers', 'length_ok', 'suggestions'
    """
    styler = EmailStyler()
    
    spam_triggers = styler.check_spam_triggers(content)
    word_count = len(content.split())
    
    suggestions = []
    
    if spam_triggers:
        suggestions.append(f"Avoid spam triggers: {', '.join(spam_triggers)}")
    
    if word_count > 500:
        suggestions.append("Consider shortening - readers spend ~10-12 seconds on emails")
    
    if word_count < 20:
        suggestions.append("Email may be too brief - consider adding context")
    
    # Check for overly formal language
    formal_phrases = ["per my", "pursuant to", "herewith", "hereafter"]
    for phrase in formal_phrases:
        if phrase in content.lower():
            suggestions.append(f"Consider replacing formal phrase: '{phrase}'")
    
    return {
        "spam_triggers": spam_triggers,
        "word_count": word_count,
        "length_ok": 20 <= word_count <= 500,
        "suggestions": suggestions,
        "quality_score": max(0, 100 - len(suggestions) * 15 - len(spam_triggers) * 20)
    }


# =============================================================================
# EMAIL PROMPT ADDITIONS FOR LLM
# =============================================================================

EMAIL_STYLE_PROMPT = """
EMAIL FORMATTING GUIDELINES:
============================
You are writing an email as Ira, the AI assistant for Machinecraft Technologies.

BRAND VOICE (Machinecraft):
- Simple, Refined and Sophisticated
- Clear and direct - no clutter
- Confident expertise without arrogance
- Professional warmth, not corporate stiffness

TONE:
- Conversational, like a knowledgeable colleague
- Get to the point - Machinecraft values clarity
- Technical competence with approachability

STRUCTURE:
- Keep paragraphs short (2-3 sentences max)
- Use bullet points for lists of 3+ items
- Lead with the most important information
- White space is good - don't crowd the message

AVOID:
- "I hope this email finds you well" or similar clichés
- "Per my last email" or corporate jargon
- "Please do not hesitate to contact" (just say "let me know")
- Excessive hedging or apologies
- Starting with "As an AI assistant..."
- Cluttered, busy formatting
- Multiple competing elements or ideas per paragraph
- Overusing bold/asterisks — emails are plain text, write naturally
- Section headers in short emails — just write in flowing paragraphs

GOOD CLOSINGS:
- "Let me know if you need anything else"
- "Happy to dig deeper on any of this"
- "Talk soon"

LENGTH:
- Aim for 50-200 words for most responses
- Be thorough but scannable
- Sophisticated brevity over verbose explanations
"""


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test the email styler with Machinecraft brand guidelines
    styler = EmailStyler()
    
    print("=" * 60)
    print("MACHINECRAFT EMAIL STYLING TEST")
    print("Brand Voice: Simple, Refined and Sophisticated")
    print("=" * 60)
    
    raw_content = """I looked into the PF1-3020 specifications you asked about. Here's what I found:

The price is $4,200 per unit with volume discounts available at 10 or more units. Lead time is typically 3-4 weeks for standard orders. The warranty covers 2 years for parts and labor.

The rep mentioned they're running a Q1 promotion that expires March 15th.

Want me to request a formal quote or set up a call with their team?"""
    
    print("\nRAW CONTENT:")
    print("-" * 40)
    print(raw_content)
    
    print("\n" + "=" * 60)
    print("FORMATTED EMAIL (Warm relationship):")
    print("=" * 60)
    formatted = styler.format_email_response(
        content=raw_content,
        recipient_name="Sarah",
        relationship=RecipientRelationship.WARM,
    )
    print(formatted)
    
    print("\n" + "=" * 60)
    print("FORMATTED EMAIL (Stranger):")
    print("=" * 60)
    formatted_stranger = styler.format_email_response(
        content=raw_content,
        recipient_name="Mr. Johnson",
        relationship=RecipientRelationship.STRANGER,
    )
    print(formatted_stranger)
    
    print("\n" + "=" * 60)
    print("BRAND CONFIG:")
    print("=" * 60)
    print(f"Primary Font: {EMAIL_CONFIG['fonts']['primary']}")
    print(f"Font Stack: {EMAIL_CONFIG['fonts']['fallback_stack']}")
    print(f"Body Text Color: {EMAIL_CONFIG['colors']['body_text']}")
    print(f"Accent Color: {EMAIL_CONFIG['colors']['accent']}")
    print(f"Brand Voice: {EMAIL_CONFIG['brand_voice']['tone']}")
    
    print("\n" + "=" * 60)
    print("QUALITY CHECK:")
    print("=" * 60)
    quality = check_email_quality(raw_content)
    print(f"Word count: {quality['word_count']}")
    print(f"Quality score: {quality['quality_score']}/100")
    print(f"Suggestions: {quality['suggestions']}")
