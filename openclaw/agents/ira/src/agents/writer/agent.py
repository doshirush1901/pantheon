"""
Calliope - The Writer (OpenClaw Native)

The eloquent wordsmith. Empathetic, persuasive, and a master of tone.
She crafts every email, quote, and response to be clear, compelling,
and perfectly branded.

This module provides writing functions that can be invoked by the LLM
through OpenClaw's native tool system.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger("ira.calliope")


# =============================================================================
# STYLE PATTERNS
# =============================================================================
# ATHENA COACHING UPDATE (2026-02-28)
# Based on analysis of 87 real sales conversations
# Key improvements: More warmth, more concise, more action-oriented

# Rushabh's WARM greetings (ATHENA: "Start with warm greeting" - 14x)
STYLE_GREETINGS = [
    "Hi!",                    # Most effective - warm and direct
    "Hey",                    # For known contacts
    "Hi there",               # Friendly variant
]

# Rushabh's characteristic openers
STYLE_OPENERS = [
    "Hi! ",                   # ATHENA: Warm greeting first
    "Hey - ",                 # ATHENA: Casual for known contacts  
    "Good question -",
    "Here's the situation:",
    "Thanks for reaching out.",
]

STYLE_TRANSITIONS = [
    "That said,",
    "What it means:",
    "Why it matters:",
    "The key takeaway:",
]

# ATHENA: "Add call-to-action" (9x coaching point)
STYLE_CLOSERS = [
    "Let me know if you need anything else.",
    "Happy to discuss further.",
    "Questions?",             # ATHENA: Short, direct
    "Let me know.",           # ATHENA: Concise
    "Make sense?",            # ATHENA: Engaging
]

# ATHENA: "Add warmth phrases" (15x coaching point)
WARMTH_PHRASES = [
    "Happy to help!",
    "Sounds good -",
    "No problem.",
    "Sure thing -",
    "Of course!",
]

# ATHENA: "Be more action-oriented" (9x coaching point)
ACTION_PHRASES = [
    "Let me",                 # "Let me send that over"
    "I'll",                   # "I'll get back to you"
    "Let's",                  # "Let's set up a call"
]

# IRA personality phrases (use sparingly)
IRA_PERSONALITY = [
    "(not that I'm biased, of course)",
    "– if you'll pardon the technical dive",
    "(the engineering equivalent of a Swiss Army knife)",
]

# ATHENA: "Response too long" (10x coaching point) - Target lengths
# Rushabh's emails: 3-5 sentences (50-150 words depending on complexity)
MAX_RESPONSE_WORDS = {
    "email": 120,             # Balanced for emails
    "telegram": 80,           # Short for messaging
    "cli": 150,               # CLI slightly longer
    "training": 120,          # Training mode - balanced
}


# =============================================================================
# CORE WRITING FUNCTIONS
# =============================================================================

async def write(query: str, context: Optional[Dict] = None) -> str:
    """
    Main writing function - can be called as an OpenClaw tool.
    
    Crafts a professional, well-structured response based on the input.
    
    Args:
        query: The original user query
        context: Context including research_output, intent, channel
        
    Returns:
        Crafted response text
    """
    context = context or {}
    
    logger.info({
        "agent": "Calliope",
        "event": "writing_started",
        "intent": context.get("intent", "general"),
        "channel": context.get("channel", "unknown")
    })
    
    intent = context.get("intent", "general")
    channel = context.get("channel", "cli")
    research_output = context.get("research_output", "")
    iris_context = context.get("iris_context") or {}
    steering = context.get("steering")
    context["iris_context"] = iris_context
    context["steering"] = steering

    # Route to appropriate writer
    if intent == "email" or "draft" in query.lower() and "email" in query.lower():
        response = _draft_email(query, research_output, context)
    elif intent == "pricing" and "quote" in query.lower():
        response = _draft_quote(query, research_output, context)
    else:
        response = _draft_response(query, research_output, context)
    
    logger.info({
        "agent": "Calliope",
        "event": "writing_complete",
        "response_length": len(response)
    })
    
    return response


def _draft_response(query: str, research: str, context: Dict) -> str:
    """
    Draft a general response using the Pyramid Principle.
    
    ATHENA COACHING (2026-02-28):
    - START with "Hi!" (MANDATORY - 10x coaching point)
    - Add warmth: "Happy to help", "Sounds good"
    - Be concise: Rushabh's responses are SHORT
    - Use action language: "Let me...", "I'll..."
    - Always include call-to-action
    """
    channel = context.get("channel", "cli")
    intent = context.get("intent", "general")
    
    # ATHENA: ALWAYS start with warm greeting (10x coaching point)
    greeting = "Hi! "  # MANDATORY per ATHENA
    
    # ATHENA: Add warmth phrase after greeting (6x coaching point)
    import random
    warmth_phrases = ["Happy to help. ", "Sounds good. ", "Sure thing. ", "No problem. ", ""]
    warmth = random.choice(warmth_phrases[:3])  # Weighted to ensure warmth
    
    # ATHENA: Select follow-up based on context
    if "thank" in query.lower():
        opener = greeting + "Happy to help! "  # Extra warm for thanks
    elif "?" in query:
        opener = greeting + warmth  # Greeting + warmth for questions
    else:
        opener = greeting + warmth  # Greeting + warmth for statements
    
    # Build response using Pyramid Principle (BLUF)
    parts = [opener]
    
    # Extract key information from research
    if research:
        # Bottom Line Up Front - give the answer first, skip filler
        # ATHENA: "Responses too long" (10x) - be direct
        formatted_research = _format_research(research)
        
        # ATHENA: Enforce conciseness
        max_words = MAX_RESPONSE_WORDS.get(channel, 200)
        words = formatted_research.split()
        if len(words) > max_words:
            formatted_research = " ".join(words[:max_words - 20])
            formatted_research += "\n\nLet me know if you want more details."
        
        parts.append("\n" + formatted_research)
    else:
        # ATHENA: Action language (5x coaching point)
        action_responses = [
            "\nLet me look into that for you.",
            "\nI'll check on this and get back to you.",
            "\nLet me find the details.",
        ]
        parts.append(random.choice(action_responses))
    
    # ATHENA: Short CTA (2x coaching point) - Rushabh uses SHORT closers
    ctas = ["Let me know.", "Questions?", "Make sense?"]
    parts.append(f"\n\n{random.choice(ctas)}")
    
    return "".join(parts)


def _draft_email(query: str, research: str, context: Dict) -> str:
    """
    Draft a professional email.

    ATHENA COACHING (2026-02-28):
    - Start with warm greeting ("Hi!" not "Dear")
    - Keep it SHORT (Rushabh's emails are 3-5 sentences)
    - Use action language ("Let me...", "I'll...")
    - End with clear call-to-action

    Incorporates iris_context (news_hook, timely_opener) and steering when present.
    """
    iris_context = context.get("iris_context") or {}
    steering = context.get("steering")

    # Extract recipient name if mentioned
    recipient = ""  # ATHENA: Rushabh often skips name in greeting
    name_match = re.search(r'to\s+(\w+)', query, re.IGNORECASE)
    if name_match:
        recipient = " " + name_match.group(1).title()

    # Determine subject
    subject = "Re: Your Inquiry"  # ATHENA: More natural subject lines
    if "quote" in query.lower() or "pricing" in query.lower():
        subject = "Pricing Info - Machinecraft"
    elif "followup" in query.lower() or "follow up" in query.lower():
        subject = "Following Up"

    # Build email - ATHENA: Start warm, stay concise
    # Iris: use news_hook or timely_opener as opener when available
    opener_line = f"Hi{recipient}!"
    if iris_context.get("timely_opener"):
        opener_line += f"\n\n{iris_context['timely_opener']}"
    elif iris_context.get("news_hook"):
        opener_line += f"\n\n{iris_context['news_hook']}"

    email_parts = [
        f"**Subject:** {subject}",
        "",
        opener_line,  # ATHENA: Warm greeting (14x coaching point)
        "",
    ]
    if steering:
        email_parts.append(f"([User feedback: {steering}])")
        email_parts.append("")

    # ATHENA: No fluff opener - get to the point
    if "follow" in query.lower() and not iris_context:
        email_parts.append("Quick follow-up on our conversation -")
    # Skip generic "thank you for interest" - ATHENA: "Responses too long"
    
    email_parts.append("")
    
    # Add research content - keep it brief
    if research:
        # ATHENA: Truncate if too long (10x "too verbose" feedback)
        formatted = _format_research(research)
        words = formatted.split()
        if len(words) > MAX_RESPONSE_WORDS.get("email", 150):
            formatted = " ".join(words[:120]) + "\n\nHappy to share more details if needed."
        email_parts.append(formatted)
    else:
        email_parts.append("Let me look into this and get back to you.")  # ATHENA: Action language
    
    # ATHENA: Short, warm closer with call-to-action (9x coaching point)
    email_parts.extend([
        "",
        "Let me know if you have questions.",  # ATHENA: Concise CTA
        "",
        "Best,",  # ATHENA: Rushabh uses short sign-offs
        "Ira",
    ])
    
    return "\n".join(email_parts)


def _draft_quote(query: str, research: str, context: Dict) -> str:
    """Draft a formal quotation document."""
    today = datetime.now().strftime("%d %B %Y")
    
    # Extract machine from query or research
    machine_match = re.search(r'(PF[12]|AM|ATF|IMG|FCS)[-\s]?[A-Z]?[-\s]?\d+', query + " " + research, re.IGNORECASE)
    machine = machine_match.group(0).upper() if machine_match else "[MACHINE MODEL]"
    
    # Try to extract price from research
    price = "[PRICE]"
    price_match = re.search(r'₹?([\d.]+)\s*(lakhs?|crores?)', research, re.IGNORECASE)
    if price_match:
        price = f"₹{price_match.group(1)} {price_match.group(2)}"
    
    quote_parts = [
        "# QUOTATION",
        "",
        f"**Date:** {today}",
        "**Validity:** 30 days",
        "**Reference:** QT-" + datetime.now().strftime("%Y%m%d"),
        "",
        "---",
        "",
        "## Machine Details",
        "",
        f"**Model:** {machine}",
        "",
    ]
    
    # Add specifications from research
    if research:
        quote_parts.append("**Specifications:**")
        for line in research.split("\n"):
            if "forming_area" in line.lower() or "thickness" in line.lower() or "depth" in line.lower():
                quote_parts.append(line)
    
    quote_parts.extend([
        "",
        "## Pricing",
        "",
        f"**Base Price:** {price}",
        "",
        "*All prices are subject to configuration and current pricing.*",
        "",
        "---",
        "",
        "## Terms & Conditions",
        "",
        "- Delivery: Ex-works, timeline subject to confirmation",
        "- Payment: As per mutually agreed terms",
        "- Warranty: 12 months from commissioning",
        "",
        "---",
        "",
        "For any questions, please contact us at sales@machinecraft.in",
    ])
    
    return "\n".join(quote_parts)


def _format_research(research: str) -> str:
    """Format research output for readability."""
    # Clean up the research output
    lines = research.strip().split("\n")
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Convert markdown-style headers
        if line.startswith("##"):
            formatted_lines.append("\n" + line)
        # Convert list items to cleaner format
        elif line.startswith("- **"):
            formatted_lines.append(line)
        elif line.startswith("-"):
            formatted_lines.append(line)
        else:
            formatted_lines.append(line)
    
    return "\n".join(formatted_lines)


# =============================================================================
# CHANNEL-SPECIFIC FORMATTERS
# =============================================================================

def format_for_channel(response: str, channel: str) -> str:
    """
    Format response for specific channel requirements.
    
    Args:
        response: The draft response
        channel: Target channel (telegram, email, whatsapp, etc.)
        
    Returns:
        Channel-optimized response
    """
    if channel == "telegram":
        # Telegram supports markdown but has length limits
        if len(response) > 4000:
            response = response[:3950] + "\n\n[Message truncated. Reply for more details.]"
        return response
    
    elif channel == "whatsapp":
        # WhatsApp has simpler formatting
        response = response.replace("**", "*")  # Bold syntax
        response = response.replace("##", "")   # Remove headers
        if len(response) > 4000:
            response = response[:3950] + "\n\n[Continued...]"
        return response
    
    elif channel == "email":
        # Email can be longer and more formal
        return response
    
    else:
        return response


def add_brand_voice(response: str) -> str:
    """
    Ensure response matches Machinecraft brand voice.

    Brand Voice: Simple, Refined, Sophisticated
    """
    # Remove excessive exclamation marks (keep max 1)
    exclaim_count = response.count("!")
    if exclaim_count > 1:
        response = response.replace("!", ".", exclaim_count - 1)

    # Ensure proper capitalization of brand terms
    brand_terms = {
        "machinecraft": "Machinecraft",
        "MACHINECRAFT": "Machinecraft",
        "Pf1": "PF1",
        "Pf2": "PF2",
    }
    for wrong, correct in brand_terms.items():
        response = response.replace(wrong, correct)

    return response


# =============================================================================
# STREAMING (Task 1.2 - True LLM Streaming)
# =============================================================================

async def write_streaming(message: str, context: Optional[Dict] = None) -> AsyncGenerator[str, None]:
    """
    Async generator that yields tokens from the OpenAI API in real time.

    Uses stream=True for true token-by-token streaming instead of simulated
    chunking. Incorporates iris_context and steering from context.

    Args:
        message: The user query or draft request
        context: Dict with research_output, iris_context, steering, intent, channel

    Yields:
        str: Each token as it arrives from the LLM
    """
    context = context or {}
    research = context.get("research_output", "")
    iris_ctx = context.get("iris_context") or {}
    steering = context.get("steering")
    intent = context.get("intent", "general")
    channel = context.get("channel", "cli")

    system_parts = [
        "You are Ira, the Intelligent Revenue Assistant for Machinecraft Technologies.",
        "Write in a warm, concise, professional tone. Start with 'Hi!' for greetings.",
        "Keep responses SHORT (3-5 sentences for emails). Use action language: 'Let me...', 'I'll...'.",
    ]
    if iris_ctx:
        hooks = []
        if iris_ctx.get("news_hook"):
            hooks.append(f"News hook for opener: {iris_ctx['news_hook']}")
        if iris_ctx.get("industry_hook"):
            hooks.append(f"Industry angle: {iris_ctx['industry_hook']}")
        if iris_ctx.get("timely_opener"):
            hooks.append(f"Timely opener: {iris_ctx['timely_opener']}")
        if hooks:
            system_parts.append("Use this intelligence in your response: " + " | ".join(hooks))
    if steering:
        system_parts.append(f"User feedback to apply: {steering}")

    user_content = f"Query: {message}\n\nResearch: {research[:2000]}" if research else message

    try:
        import openai
        client = openai.AsyncOpenAI()
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "\n".join(system_parts)},
                {"role": "user", "content": user_content},
            ],
            max_tokens=500,
            temperature=0.4,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.warning(f"Streaming LLM failed: {e}, falling back to template")
        # Fallback: use sync write and yield as single chunk
        draft = await write(message, context)
        yield draft
