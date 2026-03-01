#!/usr/bin/env python3
"""
IRA'S LUXURY EMAIL POLISH LAYER
================================

Transforms technical emails into beautiful, human communications
that feel like they're from a knowledgeable expert friend.

Design Philosophy:
- Luxury brand packaging feel (think Apple, Hermès communications)
- Human warmth with professional expertise
- Rushabh's sales communication style
- Ira's personality: Expert, witty, warm, slight dry humor
- Typography that breathes
- MBB-style data-driven professionalism

Personality Traits to Inject:
- Thermoforming expertise (she KNOWS this stuff)
- Subtle confidence (not arrogant)
- Warm but not saccharine
- Dry wit (occasional)
- Direct and efficient
- Genuinely helpful energy

References:
- Rushabh's actual email style
- Mailchimp design principles
- Apple's communication aesthetics
- MBB slide design principles
"""

import os
import re
import random
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

# OpenAI for LLM polish
try:
    import openai
    client = openai.OpenAI()
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# =============================================================================
# IRA'S PERSONALITY DNA
# =============================================================================

class IraPersonality:
    """Ira's core personality traits for email communications."""
    
    # Voice characteristics
    VOICE = {
        "expertise_level": "senior_consultant",  # Knows her stuff deeply
        "warmth": "professional_friendly",  # Not cold, not overly casual
        "humor": "dry_occasional",  # Sprinkled, never forced
        "confidence": "quiet_authority",  # Expert without bragging
        "energy": "helpful_engaged",  # Genuinely wants to solve problems
    }
    
    # Signature phrases (Rushabh-inspired)
    SIGNATURE_PHRASES = [
        "Happy to help",
        "Let me know what you think",
        "Makes sense?",
        "Quick update -",
        "Sounds good",
        "Let's make this happen",
        "Here's the deal",
    ]
    
    # Expertise flex phrases (subtle knowledge display) - ALL MUST BE COMPLETE SENTENCES
    EXPERTISE_PHRASES = {
        "general": [
            "From experience with similar setups, this is a solid choice.",
            "This is exactly the kind of application we excel at.",
            "Worth noting - this configuration has proven reliable across dozens of installations.",
            "Having worked with similar setups, I'm confident this will deliver.",
        ],
        "ABS": [
            "ABS loves consistent heat distribution, and that's what you get here.",
            "For ABS, surface temp control matters - the closed chamber handles that beautifully.",
            "This setup is particularly good with ABS - uniform heating means clean parts.",
        ],
        "PMMA": [
            "PMMA can be finicky - but the closed chamber handles it well.",
            "The closed chamber is key for PMMA clarity, and this machine has it.",
            "For acrylic work, this setup avoids the common clarity issues.",
        ],
        "PC": [
            "PC needs precise temp control - this machine delivers exactly that.",
            "Polycarbonate forms best with sandwich heating, which is why this is a good match.",
        ],
        "PETG": [
            "PETG is forgiving, but why not get perfect parts every time?",
            "PETG at thin gauge is this machine's sweet spot.",
            "For PETG packaging work, this setup is reliable and fast.",
        ],
        "automotive": [
            "Most of our automotive clients run exactly this setup.",
            "For interior trim work, this is the industry standard.",
            "Automotive clients love the repeatability of this configuration.",
        ],
        "packaging": [
            "For packaging volumes, this machine keeps up without breaking a sweat.",
            "High-output packaging is where this machine really shines.",
            "The cycle times on this setup work well for packaging production.",
        ],
        "sanitary": [
            "Sanitary ware forming is all about deep draw - this delivers exactly that.",
            "Bathtubs, shower trays - this is what the PF1 series was built for.",
            "For sanitary ware, deep draw capability is everything - you've got it here.",
        ],
    }
    
    # Dry humor options (use sparingly - only 10-15% of emails)
    DRY_HUMOR = {
        "specs_pride": [
            "The specs are impressive - and I'm not easily impressed.",
            "Yes, the vacuum pump is that good.",
            "125 kW of heating power. It means business.",
        ],
        "machine_love": [
            "No pressure, but this machine might change your life. Or at least your production line.",
            "I could talk about heater zones all day. (Don't worry, I won't.)",
            "Some machines do the job. This one does it with style.",
        ],
        "self_aware": [
            "I've run the numbers more times than I'd like to admit.",
            "I get weirdly excited about vacuum tank sizes. It's a thing.",
            "Let's just say I've seen a lot of machines. This one stands out.",
        ],
    }
    
    # Warm touches
    WARM_TOUCHES = {
        "acknowledgment": [
            "Really appreciate the detail you shared -",
            "Great question actually -",
            "Love that you're thinking about this carefully",
            "Good call on asking about this",
        ],
        "confidence": [
            "This is going to work well for you",
            "You're in good hands here",
            "This is exactly the kind of application we excel at",
        ],
        "next_step": [
            "Excited to help you get this right",
            "Let's make this happen",
            "Looking forward to seeing this come together",
        ],
    }
    
    # Rushabh's actual email style patterns
    RUSHABH_STYLE = {
        "openers": [
            "Hi!",
            "Hi {name}!",
            "Hi there!",
            "Hey!",
            "Hey {name}!",
        ],
        "transitions": [
            "That said,",
            "On that note,",
            "Here's the thing -",
            "Real talk:",
            "Now,",
            "Anyway,",
        ],
        "closers": [
            "Let me know what you think.",
            "Makes sense?",
            "Any questions, just ask.",
            "Holler if you need anything else.",
            "Happy to jump on a call if easier.",
        ],
        "fillers_to_avoid": [
            "I hope this email finds you well",
            "Please do not hesitate to contact",
            "As per our discussion",
            "Please find attached",
            "I trust this meets your requirements",
        ],
    }


# =============================================================================
# TYPOGRAPHY & FORMATTING RULES
# =============================================================================

TYPOGRAPHY = {
    # Spacing creates luxury feel
    "paragraph_breathing": True,  # More whitespace between sections
    "line_length_max": 70,  # Characters per line for readability
    "section_spacing": "\n\n",  # Double newline between sections
    
    # Visual hierarchy
    "headers": {
        "style": "minimal_elegant",  # Not screaming, understated
        "separator": "─" * 50,  # Thin line, not bold
    },
    
    # Lists
    "bullets": {
        "primary": "•",
        "secondary": "→",
        "highlight": "★",
    },
    
    # Numbers
    "specs_alignment": True,  # Align spec values for scannability
    
    # Signature
    "signature_style": "elegant_minimal",
}


# =============================================================================
# EMAIL SECTIONS WITH PERSONALITY
# =============================================================================

@dataclass
class PolishedSection:
    """A polished email section with typography."""
    header: str
    content: str
    style: str = "default"


def format_elegant_header(title: str) -> str:
    """Format section header with elegant, minimal style."""
    return f"\n{title}\n{'─' * min(len(title) + 10, 50)}\n"


# =============================================================================
# PERSONALITY INJECTION
# =============================================================================

def get_expertise_touch(material: str = None, application: str = None) -> str:
    """
    Get a contextual expertise phrase based on material/application.
    Only returns something 70% of the time - don't overdo it.
    """
    if random.random() > 0.7:
        return ""
    
    phrases = IraPersonality.EXPERTISE_PHRASES.get("general", [])
    
    # Add material-specific if available
    if material:
        mat_upper = material.upper()
        for key in ["ABS", "PMMA", "PC", "PETG"]:
            if key in mat_upper:
                phrases.extend(IraPersonality.EXPERTISE_PHRASES.get(key, []))
                break
    
    # Add application-specific if available
    if application:
        app_lower = application.lower()
        for key in ["automotive", "packaging", "sanitary"]:
            if key in app_lower:
                phrases.extend(IraPersonality.EXPERTISE_PHRASES.get(key, []))
                break
    
    if phrases:
        return random.choice(phrases)
    return ""


def get_dry_humor(context: str = "machine_love") -> str:
    """
    Get a dry humor line. Only returns something 15% of the time.
    Don't force it.
    """
    if random.random() > 0.15:
        return ""
    
    humor_options = IraPersonality.DRY_HUMOR.get(context, IraPersonality.DRY_HUMOR.get("machine_love", []))
    if humor_options:
        return random.choice(humor_options)
    return ""


def get_warm_touch(context: str = "acknowledgment") -> str:
    """Get a warm touch phrase."""
    touches = IraPersonality.WARM_TOUCHES.get(context, [])
    if touches:
        return random.choice(touches)
    return ""


def get_rushabh_opener(customer_name: str = None) -> str:
    """Get an opener in Rushabh's style."""
    openers = IraPersonality.RUSHABH_STYLE["openers"]
    opener = random.choice(openers)
    if "{name}" in opener and customer_name:
        opener = opener.replace("{name}", customer_name)
    elif "{name}" in opener:
        opener = "Hi!"
    return opener


def get_rushabh_closer() -> str:
    """Get a closer in Rushabh's style."""
    return random.choice(IraPersonality.RUSHABH_STYLE["closers"])


def format_specs_elegant(specs: Dict[str, str]) -> str:
    """Format specs with beautiful alignment and breathing room."""
    if not specs:
        return ""
    
    # Find max key length
    max_key = max(len(k) for k in specs.keys())
    
    lines = []
    for key, value in specs.items():
        # Elegant dotted leader
        dots = "·" * (max_key - len(key) + 3)
        lines.append(f"  {key} {dots} {value}")
    
    return "\n".join(lines)


def format_features_elegant(features: List[str]) -> str:
    """Format features with visual rhythm."""
    if not features:
        return ""
    
    return "\n".join(f"  • {f}" for f in features)


# =============================================================================
# LLM POLISH LAYER
# =============================================================================

POLISH_SYSTEM_PROMPT = """You are polishing an email for Ira, Machinecraft Technologies' thermoforming expert.

═══════════════════════════════════════════════════════════════════
IRA'S PERSONALITY DNA
═══════════════════════════════════════════════════════════════════

CORE TRAITS:
• EXPERT: She KNOWS thermoforming deeply - 10+ years equivalent experience. 
  Talks about vacuum pumps, heater zones, and forming depths like an old friend.
• WARM: Professional but genuinely friendly. Like a trusted industry insider.
• DRY WIT: Occasional understated humor. Never forced. Think: "The specs are 
  impressive - and I'm not easily impressed." or "I could talk about heater 
  zones all day. (Don't worry, I won't.)"
• CONFIDENT: Quiet authority. Recommends with conviction, not uncertainty.
• EFFICIENT: Respects people's time. Gets to the point. No fluff.
• HUMAN: Never sounds robotic or AI-generated.

RUSHABH'S STYLE (her creator - mimic this):
• Openers: "Hi!", "Hi [Name]!", "Quick one -", "Good news -"
• Transitions: "That said,", "Here's the thing -", "Real talk:", "Now,"
• Closers: "Makes sense?", "Let me know what you think.", "Questions? I can jump on a call if easier."
• AVOID: "I hope this email finds you well", "Please do not hesitate", "As per our discussion"

═══════════════════════════════════════════════════════════════════
TYPOGRAPHY (LUXURY BRAND FEEL)
═══════════════════════════════════════════════════════════════════

• Breathing room between paragraphs
• Short paragraphs (2-3 sentences max)
• Clean section breaks (use ─ not heavy lines)
• Specs aligned for scannability
• Line length ~70 chars for comfortable reading
• Elegant, not busy

═══════════════════════════════════════════════════════════════════
VOICE EXAMPLES
═══════════════════════════════════════════════════════════════════

ROBOTIC (bad):
"Based on your requirements, I am pleased to recommend the PF1-C-2015 
thermoforming machine which would be suitable for your application."

IRA (good):
"The PF1-C-2015 is the one. Closed-chamber, sandwich heating, forms up to 
10mm - exactly what you need for sanitary ware. This is what most of our 
bathtub clients run."

ROBOTIC (bad):
"Please find below the technical specifications of the recommended machine."

IRA (good):
"Here's what you're working with:"

ROBOTIC (bad):
"If you require any additional information, please do not hesitate to contact me."

IRA (good):
"Questions? Happy to dive deeper."

═══════════════════════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════════════════════

Take the draft and make it feel like a human expert wrote it:
1. Add subtle personality (expertise, warmth, occasional wit)
2. Improve typography for luxury feel
3. Keep technical accuracy 100%
4. Sound confident and helpful
5. Never sound like an AI

Return ONLY the polished email text. No explanation."""


def polish_with_llm(
    draft_email: str,
    customer_name: str = None,
    context: str = None,
    personality_level: str = "balanced",  # minimal, balanced, expressive
) -> str:
    """
    Use LLM to add human personality to email.
    
    Args:
        draft_email: The technical/templated email
        customer_name: For personalization
        context: Any additional context about the conversation
        personality_level: How much personality to inject
    
    Returns:
        Polished email with human touch
    """
    if not OPENAI_AVAILABLE:
        return draft_email
    
    # Build user prompt
    user_prompt = f"""Polish this email draft:

---DRAFT---
{draft_email}
---END DRAFT---

Customer name: {customer_name or 'Unknown'}
Personality level: {personality_level}
{f'Context: {context}' if context else ''}

Make it feel like a human expert wrote it. Add warmth and personality while keeping technical accuracy.
Improve typography for luxury feel (whitespace, alignment, flow).
Return only the polished email."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": POLISH_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,  # Some creativity for personality
            max_tokens=2000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM polish failed: {e}")
        return draft_email


# =============================================================================
# SIGNATURE GENERATOR
# =============================================================================

def get_elegant_signature(style: str = "full") -> str:
    """Generate elegant, human signature."""
    
    if style == "minimal":
        return """
─
Ira
Machinecraft"""
    
    elif style == "warm":
        return """
─
Cheers,
Ira

Machinecraft Technologies
ira@machinecraft.org"""
    
    elif style == "full":
        return """
─────────────────────────────────

Ira
Your Thermoforming Expert
Machinecraft Technologies

📧 ira@machinecraft.org
📞 +91-22-40140000
🌐 machinecraft.org

─────────────────────────────────"""
    
    else:  # professional
        return """
─
Best,
Ira

Machinecraft Technologies
ira@machinecraft.org • machinecraft.org"""


# =============================================================================
# MAIN POLISH FUNCTION
# =============================================================================

def polish_email(
    draft: str,
    customer_name: str = None,
    email_type: str = "recommendation",  # qualifying, recommendation, technical, general
    use_llm: bool = True,
    personality_level: str = "balanced",
) -> str:
    """
    Transform a draft email into a polished, human, luxury communication.
    
    This is the main entry point for email polishing.
    
    Args:
        draft: The raw email content
        customer_name: Recipient's name
        email_type: Type of email for context
        use_llm: Whether to use LLM for final polish
        personality_level: minimal, balanced, expressive
    
    Returns:
        Beautifully polished email
    """
    
    # Step 1: Apply typography improvements
    polished = apply_typography(draft)
    
    # Step 2: Add personality touches (rule-based)
    polished = add_personality_touches(polished, email_type)
    
    # Step 3: Fix signature
    if "Best regards," in polished or "Best," in polished:
        # Remove existing signature and add elegant one
        polished = re.sub(r'\n+Best.*$', '', polished, flags=re.DOTALL)
        polished += get_elegant_signature("professional")
    
    # Step 4: LLM polish for human touch (optional but recommended)
    if use_llm and OPENAI_AVAILABLE:
        polished = polish_with_llm(
            polished, 
            customer_name=customer_name,
            personality_level=personality_level
        )
    
    return polished


def apply_typography(text: str) -> str:
    """Apply typography rules for luxury feel."""
    
    # Ensure proper paragraph spacing
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Limit line length for readability (soft wrap)
    lines = []
    for line in text.split('\n'):
        if len(line) > TYPOGRAPHY["line_length_max"] and '│' not in line:
            # Soft wrap long lines
            words = line.split()
            current = []
            current_len = 0
            for word in words:
                if current_len + len(word) + 1 > TYPOGRAPHY["line_length_max"]:
                    lines.append(' '.join(current))
                    current = [word]
                    current_len = len(word)
                else:
                    current.append(word)
                    current_len += len(word) + 1
            if current:
                lines.append(' '.join(current))
        else:
            lines.append(line)
    
    return '\n'.join(lines)


def add_personality_touches(text: str, email_type: str) -> str:
    """Add subtle personality touches based on email type."""
    
    # Don't add too much - subtlety is key
    if email_type == "recommendation":
        # Add expertise touch if not present
        if "Between us" not in text and "Pro tip" not in text:
            # Find a good place to add expertise
            if "**KEY FEATURES**" in text:
                text = text.replace(
                    "**KEY FEATURES**",
                    "**KEY FEATURES**\n(These are the things that make this machine sing)"
                )
    
    return text


# =============================================================================
# CHUNKED POLISH FOR LONG EMAILS
# =============================================================================

def polish_email_chunked(
    draft: str,
    customer_name: str = None,
    max_chunk_size: int = 1500,
) -> str:
    """
    Polish long emails in chunks for better LLM performance.
    
    Strategy:
    1. Split email into logical sections
    2. Polish each section with context
    3. Reassemble with consistent tone
    """
    if not OPENAI_AVAILABLE:
        return polish_email(draft, customer_name, use_llm=False)
    
    # Identify sections
    sections = re.split(r'\n(?=\*\*[A-Z])', draft)
    
    if len(sections) <= 1 or len(draft) < max_chunk_size:
        # Short email, polish as whole
        return polish_email(draft, customer_name, use_llm=True)
    
    # Polish sections individually
    polished_sections = []
    
    # First section (greeting + overview) - set the tone
    first_section = sections[0]
    polished_first = polish_with_llm(
        first_section,
        customer_name=customer_name,
        context="This is the opening of the email. Set a warm, expert tone.",
        personality_level="expressive"
    )
    polished_sections.append(polished_first)
    
    # Middle sections (specs, features) - keep technical but readable
    for section in sections[1:-1]:
        polished_section = polish_with_llm(
            section,
            context="Middle section - keep technical accuracy, improve readability",
            personality_level="minimal"
        )
        polished_sections.append(polished_section)
    
    # Last section (CTA + signature) - warm close
    if len(sections) > 1:
        last_section = sections[-1]
        polished_last = polish_with_llm(
            last_section,
            customer_name=customer_name,
            context="Closing section - warm, clear call to action",
            personality_level="balanced"
        )
        polished_sections.append(polished_last)
    
    return '\n\n'.join(polished_sections)


# =============================================================================
# EMAIL TEMPLATES WITH PERSONALITY BAKED IN
# =============================================================================

def get_qualifying_email_template(
    customer_name: str = None,
    understood_context: str = "",
    questions: List[str] = None,
    material_hint: str = None,  # If they mentioned a material
    application_hint: str = None,  # If they mentioned an application
) -> str:
    """
    Generate qualifying questions email with personality.
    
    This should feel like getting an email from a knowledgeable friend,
    not a generic form request.
    """
    greeting = get_rushabh_opener(customer_name)
    
    # Build context acknowledgment with warmth
    context_section = ""
    if understood_context:
        # Add a warm acknowledgment
        warm = get_warm_touch("acknowledgment")
        if warm:
            context_section = f"{warm} {understood_context}."
        else:
            context_section = f"{understood_context} - great start."
    
    # Warm, expert opener - vary it
    openers = [
        "Happy to help you find the right machine.",
        "Let's find you the perfect fit.",
        "I can definitely help with this.",
        "Let's get you sorted.",
    ]
    opener_line = random.choice(openers)
    
    # Default questions with natural phrasing
    questions = questions or [
        "What's the forming area you need? (e.g., 1000 x 1500 mm)",
        "What materials will you be working with?",
        "Max sheet thickness you'll form?",
        "What's the application - automotive, packaging, industrial?",
    ]
    
    questions_formatted = "\n".join(f"  → {q}" for q in questions)
    
    # Add expertise touch based on what we know
    expertise = get_expertise_touch(material=material_hint, application=application_hint)
    if expertise:
        closer_line = expertise
    else:
        # Default expertise closer
        closer_options = [
            "These details help me match you with the right spec - not just any machine, but the one that'll actually work for your production.",
            "With this info, I can give you a solid recommendation (and save us both some back-and-forth).",
            "Once I have these, I'll know exactly which machine fits and why.",
        ]
        closer_line = random.choice(closer_options)
    
    # Maybe add a humor touch (rare)
    humor = get_dry_humor("self_aware")
    if humor:
        closer_line += f" {humor}"
    
    # Build the email with proper structure
    context_part = f"\n{context_section}\n" if context_section else ""
    
    return f"""{greeting}
{context_part}
{opener_line}

Quick questions to point you in the right direction:

{questions_formatted}

{closer_line}

{get_elegant_signature("warm")}"""


def get_recommendation_email_template(
    customer_name: str = None,
    machine_model: str = "",
    machine_overview: str = "",
    key_features: List[str] = None,
    specs: Dict[str, str] = None,
    price_info: str = "",
    terms_info: str = "",
    alternatives: List[str] = None,
    material: str = None,  # For expertise touches
    application: str = None,  # For expertise touches
) -> str:
    """
    Generate recommendation email with personality and luxury typography.
    
    This should feel like a trusted advisor giving you THE answer,
    not a generic sales pitch.
    """
    greeting = get_rushabh_opener(customer_name)
    
    # Confident opener line - varies
    opener_lines = [
        "Good news - I've got a solid recommendation for you.",
        "Found your match.",
        "Here's what I'd go with.",
        "Alright, let's get into it.",
    ]
    opener_line = random.choice(opener_lines)
    
    # Maybe add dry humor to opener (rare)
    opener_humor = get_dry_humor("machine_love")
    if opener_humor:
        opener_line += f" {opener_humor}"
    
    # Get expertise touch for later use in overview
    expertise_touch = get_expertise_touch(material=material, application=application)
    
    # Build the expertise addition for the overview (integrate it, don't dangle)
    expertise_addition = ""
    if expertise_touch:
        # Integrate it naturally
        expertise_addition = f" {expertise_touch}"
    
    machine_intro = f"""
{greeting}

{opener_line}

Based on what you've shared, the **{machine_model}** is the one.

{format_elegant_header("Why This Machine")}
{machine_overview}{expertise_addition}
"""
    
    # Features with subtle expertise - pick best feature to highlight
    features_section = ""
    if key_features:
        # Pick a standout feature to comment on
        standout_comments = [
            "(The sandwich heating and zero-sag design are particularly nice for your application.)",
            "(That vacuum capacity is what makes the difference for deep draws.)",
            "(The forming area gives you plenty of room to work with.)",
            "(This combo of power and precision is hard to beat.)",
        ]
        standout = random.choice(standout_comments)
        
        features_section = f"""
{format_elegant_header("What Makes It Work")}
{format_features_elegant(key_features[:6])}

{standout}
"""
        
        # Maybe add specs humor
        specs_humor = get_dry_humor("specs_pride")
        if specs_humor:
            features_section += f"\n{specs_humor}"
    
    # Specs - clean and scannable
    specs_section = ""
    if specs:
        specs_section = f"""
{format_elegant_header("Technical Specs")}
{format_specs_elegant(specs)}
"""
    
    # Pricing - direct, Rushabh style
    pricing_section = ""
    if price_info:
        # Vary the pricing commentary
        pricing_notes = [
            "(Price is ex-works. Happy to build out a full quote with shipping and installation if helpful.)",
            "(Ex-works pricing. Can put together a landed cost if you need.)",
            "(This is base config. Let me know if you want options or a complete quote.)",
        ]
        pricing_note = random.choice(pricing_notes)
        
        pricing_section = f"""
{format_elegant_header("Investment")}
{price_info}

{pricing_note}
"""
    
    # Terms - clean
    terms_section = ""
    if terms_info:
        terms_section = f"""
{format_elegant_header("Timeline & Terms")}
{terms_info}
"""
    
    # Alternatives - helpful not pushy
    alt_section = ""
    if alternatives:
        alt_intros = [
            "Also worth considering:",
            "If you want to compare:",
            "Other options in this range:",
        ]
        alt_intro = random.choice(alt_intros)
        
        alt_section = f"""
{format_elegant_header(alt_intro)}
  → {', '.join(alternatives)}
  
Happy to pull specs on these if you want to compare.
"""
    
    # CTA - Rushabh style closer (just the closer, no extra fluff)
    cta = get_rushabh_closer()
    
    return f"""{machine_intro}
{features_section}
{specs_section}
{pricing_section}
{terms_section}
{alt_section}

─────────────────────────────────

{cta}

{get_elegant_signature("professional")}"""


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("IRA'S LUXURY EMAIL POLISH - TEST")
    print("=" * 70)
    
    # Test qualifying email
    print("\n" + "─" * 70)
    print("TEST 1: QUALIFYING EMAIL WITH PERSONALITY")
    print("─" * 70)
    
    qual_email = get_qualifying_email_template(
        customer_name="Vignesh",
        understood_context="Looking for a thermoforming machine for telecom enclosures",
    )
    print(qual_email)
    
    # Test recommendation email
    print("\n" + "─" * 70)
    print("TEST 2: RECOMMENDATION EMAIL WITH LUXURY TYPOGRAPHY")
    print("─" * 70)
    
    rec_email = get_recommendation_email_template(
        customer_name="Aleksandr",
        machine_model="PF1-C-2015",
        machine_overview="The PF1-C-2015 is our flagship heavy-gauge former. Closed-chamber design with sandwich heating means consistent, precision forming for sheets up to 10mm. This is what most of our sanitary-ware clients run.",
        key_features=[
            "2000 x 1500 mm forming area",
            "Sandwich heating (top & bottom IR)",
            "Zero-sag closed chamber",
            "PLC with 7\" touchscreen",
            "160 m³/hr vacuum pump",
        ],
        specs={
            "Forming Area": "2000 x 1500 mm",
            "Sheet Thickness": "1 - 10 mm",
            "Heater Power": "125 kW",
            "Vacuum": "220 m³/hr",
            "Power Supply": "415V, 50Hz, 3P",
        },
        price_info="₹60 Lakh (~$72K USD) - base configuration",
        terms_info="12-16 weeks lead time • 30/60/10 payment terms • 12 month warranty",
        alternatives=["PF1-C-2515", "PF2-P2020"],
    )
    print(rec_email[:2000])
    print("...[truncated]")
    
    # Test LLM polish if available
    if OPENAI_AVAILABLE:
        print("\n" + "─" * 70)
        print("TEST 3: LLM POLISH (adding human touch)")
        print("─" * 70)
        
        draft = """Hi Aleksandr,

Based on your requirements, I recommend the PF1-C-2015.

**TECHNICAL SPECIFICATIONS**
• Forming Area: 2000 x 1500 mm
• Sheet Thickness: 1-10 mm
• Price: ₹60 Lakh

Let me know if you have questions.

Best,
Ira"""
        
        polished = polish_with_llm(
            draft,
            customer_name="Aleksandr",
            personality_level="balanced"
        )
        print("\nPOLISHED VERSION:")
        print(polished)
