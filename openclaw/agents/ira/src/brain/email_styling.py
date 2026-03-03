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
        """Generate HTML version of email. Delegates to plain_to_html()."""
        return plain_to_html(content)


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
    
    if word_count > 800:
        suggestions.append("Consider shortening - very long emails may lose reader attention")
    
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
        "length_ok": 20 <= word_count <= 800,
        "suggestions": suggestions,
        "quality_score": max(0, 100 - len(suggestions) * 15 - len(spam_triggers) * 20)
    }


# =============================================================================
# PLAIN TEXT -> HTML CONVERSION
# =============================================================================

_FONT_STACK = EMAIL_CONFIG["fonts"]["fallback_stack"]
_FONT_IMPORT = EMAIL_CONFIG["fonts"]["web_font_import"]
_COLOR_BODY = EMAIL_CONFIG["colors"]["body_text"]
_COLOR_ACCENT = EMAIL_CONFIG["colors"]["accent"]
_COLOR_SECONDARY = EMAIL_CONFIG["colors"]["secondary_text"]

_SIGNATURE_HTML = (
    '<table role="presentation" cellpadding="0" cellspacing="0" '
    f'style="border-top:1px solid #ddd; margin-top:24px; padding-top:16px; font-family:{_FONT_STACK};">'
    "<tr><td>"
    f'<span style="font-size:14px; font-weight:600; color:{_COLOR_BODY};">Ira</span><br>'
    f'<span style="font-size:12px; color:{_COLOR_SECONDARY};">Your Machinecraft Assistant</span><br>'
    f'<span style="font-size:12px; color:{_COLOR_SECONDARY};">Machinecraft Technologies</span><br>'
    f'<span style="font-size:12px; color:{_COLOR_SECONDARY};">'
    f'<a href="mailto:ira@machinecraft.org" style="color:{_COLOR_ACCENT}; text-decoration:none;">ira@machinecraft.org</a>'
    f' &middot; <a href="https://www.machinecraft.org" style="color:{_COLOR_ACCENT}; text-decoration:none;">machinecraft.org</a>'
    "</span>"
    "</td></tr></table>"
)

_P_STYLE = f"margin:0 0 16px 0; font-size:16px; line-height:1.5; color:{_COLOR_BODY};"
_H3_STYLE = f"margin:24px 0 8px 0; font-size:18px; font-weight:600; color:{_COLOR_ACCENT};"
_LI_STYLE = f"margin:0 0 6px 0; font-size:16px; line-height:1.5; color:{_COLOR_BODY};"
_TABLE_STYLE = "width:100%; border-collapse:collapse; margin:12px 0 16px 0;"
_TD_KEY_STYLE = (
    f"padding:6px 12px 6px 0; font-size:14px; color:{_COLOR_SECONDARY}; "
    "border-bottom:1px solid #eee; white-space:nowrap; vertical-align:top;"
)
_TD_VAL_STYLE = (
    f"padding:6px 0; font-size:14px; color:{_COLOR_BODY}; "
    "border-bottom:1px solid #eee; vertical-align:top;"
)


def _escape_html(text: str) -> str:
    """Escape HTML special characters while preserving already-converted tags."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def _convert_inline(text: str) -> str:
    """Convert inline markdown: **bold** and *italic*."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', text)
    return text


def _is_section_header(line: str) -> bool:
    """Detect section headers: all-caps lines, lines with ━━━ dividers, or **Header** alone."""
    stripped = line.strip()
    if not stripped:
        return False
    if "━" in stripped:
        return True
    clean = re.sub(r'[^A-Za-z\s]', '', stripped)
    if clean.strip() and clean.strip().isupper() and len(clean.strip()) > 3:
        return True
    if re.match(r'^\*\*[^*]+\*\*$', stripped):
        return True
    return False


def _extract_header_text(line: str) -> str:
    """Pull the display text from a header line."""
    stripped = line.strip()
    stripped = re.sub(r'━+\s*', '', stripped).strip()
    stripped = re.sub(r'^\*\*(.+)\*\*$', r'\1', stripped)
    return stripped


def _is_kv_line(line: str) -> bool:
    """Detect key-value spec lines like 'Forming Area: 2000x1500mm' or 'Key  |  Value'."""
    stripped = line.strip()
    if not stripped or len(stripped) < 5:
        return False
    if re.match(r'^[\s•\-\*\d]', stripped):
        return False
    if '│' in stripped or '|' in stripped:
        parts = re.split(r'\s*[│|]\s*', stripped, maxsplit=1)
        return len(parts) == 2 and len(parts[0].strip()) > 1 and len(parts[1].strip()) > 1
    if ':' in stripped:
        parts = stripped.split(':', 1)
        key = parts[0].strip()
        val = parts[1].strip()
        if 2 < len(key) < 40 and len(val) > 1 and not key[0].islower():
            return True
    return False


def _parse_kv(line: str) -> tuple:
    """Split a key-value line into (key, value)."""
    stripped = line.strip()
    if '│' in stripped or '|' in stripped:
        parts = re.split(r'\s*[│|]\s*', stripped, maxsplit=1)
        return (parts[0].strip(), parts[1].strip())
    parts = stripped.split(':', 1)
    return (parts[0].strip(), parts[1].strip())


def _is_bullet(line: str) -> bool:
    return bool(re.match(r'^\s*[•\-\*✓→]\s+', line))


def _is_numbered(line: str) -> bool:
    return bool(re.match(r'^\s*\d+[.)]\s+', line))


def _bullet_text(line: str) -> str:
    return re.sub(r'^\s*[•\-\*✓→]\s+', '', line).strip()


def _numbered_text(line: str) -> str:
    return re.sub(r'^\s*\d+[.)]\s+', '', line).strip()


def _convert_body_blocks(plain_body: str) -> str:
    """Convert the plain-text body into HTML blocks (paragraphs, lists, tables, headers)."""
    lines = plain_body.split('\n')
    html_parts: List[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if _is_section_header(line):
            header_text = _escape_html(_extract_header_text(line))
            if header_text:
                html_parts.append(f'<h3 style="{_H3_STYLE}">{header_text}</h3>')
            i += 1
            continue

        if _is_kv_line(line):
            rows: List[tuple] = []
            while i < len(lines) and _is_kv_line(lines[i]):
                k, v = _parse_kv(lines[i])
                rows.append((_escape_html(k), _convert_inline(_escape_html(v))))
                i += 1
            table_html = f'<table role="presentation" style="{_TABLE_STYLE}">'
            for k, v in rows:
                table_html += (
                    f'<tr><td style="{_TD_KEY_STYLE}">{k}</td>'
                    f'<td style="{_TD_VAL_STYLE}">{v}</td></tr>'
                )
            table_html += '</table>'
            html_parts.append(table_html)
            continue

        if _is_bullet(line):
            items: List[str] = []
            while i < len(lines) and _is_bullet(lines[i]):
                items.append(_convert_inline(_escape_html(_bullet_text(lines[i]))))
                i += 1
            list_html = '<ul style="margin:8px 0 16px 0; padding-left:24px;">'
            for item in items:
                list_html += f'<li style="{_LI_STYLE}">{item}</li>'
            list_html += '</ul>'
            html_parts.append(list_html)
            continue

        if _is_numbered(line):
            items = []
            while i < len(lines) and _is_numbered(lines[i]):
                items.append(_convert_inline(_escape_html(_numbered_text(lines[i]))))
                i += 1
            list_html = '<ol style="margin:8px 0 16px 0; padding-left:24px;">'
            for item in items:
                list_html += f'<li style="{_LI_STYLE}">{item}</li>'
            list_html += '</ol>'
            html_parts.append(list_html)
            continue

        para_lines: List[str] = []
        while i < len(lines) and lines[i].strip() and not _is_section_header(lines[i]) and not _is_kv_line(lines[i]) and not _is_bullet(lines[i]) and not _is_numbered(lines[i]):
            para_lines.append(lines[i])
            i += 1
        all_short = all(len(l.strip()) < 40 for l in para_lines)
        if all_short and len(para_lines) > 1:
            joined = '<br>'.join(_convert_inline(_escape_html(l.strip())) for l in para_lines)
        else:
            joined = _convert_inline(_escape_html(' '.join(l.strip() for l in para_lines)))
        html_parts.append(f'<p style="{_P_STYLE}">{joined}</p>')

    return '\n'.join(html_parts)


def plain_to_html(body: str) -> str:
    """Convert a plain-text email body into a branded Machinecraft HTML email.

    Handles markdown-style formatting (**bold**, bullets, numbered lists,
    key-value spec lines, section headers) and wraps everything in a clean,
    email-safe HTML shell with Montserrat typography and brand colors.

    This is the single entry-point used by gmail_send() to auto-generate
    the text/html MIME part from the plain-text draft.
    """
    inner_html = _convert_body_blocks(body)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>Machinecraft</title>
<!--[if mso]><style>body,table,td{{font-family:Helvetica,Arial,sans-serif !important;}}</style><![endif]-->
<style type="text/css">
{_FONT_IMPORT}
</style>
</head>
<body style="margin:0; padding:0; background-color:#f7f7f7; -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f7f7f7;">
<tr><td align="center" style="padding:24px 16px;">
<table role="presentation" cellpadding="0" cellspacing="0" style="max-width:600px; width:100%; background-color:#ffffff; border-radius:4px;">
<tr><td style="padding:32px 32px 24px 32px; font-family:{_FONT_STACK}; font-size:16px; line-height:1.5; color:{_COLOR_BODY};">
{inner_html}
{_SIGNATURE_HTML}
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


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
- Default: detailed and thorough — 200-500 words, 6-10 paragraphs
- Use section headers (**Overview**, **Specifications**) for structured emails
- Use bullet points (- item) for feature lists, "Key: Value" for specs
- Be comprehensive but scannable — white space and structure help readability
- For simple replies or follow-ups, shorter is fine (50-150 words)
"""


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MACHINECRAFT EMAIL STYLING TEST")
    print("Brand Voice: Simple, Refined and Sophisticated")
    print("=" * 60)

    sample = """Hi Sarah,

Here are the specs for the **PF1-C-2015**:

**Technical Specifications**
Forming Area: 2000 x 1500 mm
Max Thickness: 8 mm
Heater Power: 120 kW
Vacuum: 250 m3/hr

Key features:
- Sandwich heating (top & bottom IR)
- Zero-sag closed chamber design
- PLC with touchscreen HMI
- Servo-driven frame movement

1. Base price: $85,000 USD (subject to configuration and current pricing)
2. Lead time: 12-16 weeks from order confirmation
3. Warranty: 12 months parts and labour

Let me know if you need anything else!

Best,
Ira
Machinecraft Technologies"""

    print("\nPLAIN TEXT INPUT:")
    print("-" * 40)
    print(sample)

    html = plain_to_html(sample)
    print("\n" + "=" * 60)
    print("HTML OUTPUT (first 2000 chars):")
    print("=" * 60)
    print(html[:2000])

    out_path = "/tmp/machinecraft_email_test.html"
    with open(out_path, "w") as f:
        f.write(html)
    print(f"\nFull HTML written to {out_path} — open in a browser to preview.")
