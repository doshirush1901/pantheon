#!/usr/bin/env python3
"""
QUOTE EMAIL FORMATTER - Format quotes in Machinecraft style
============================================================

Takes a GeneratedQuote and formats it as a professional email
matching Machinecraft's actual quotation format.

Format learned from actual quotes in data/imports/Quotes/

Usage:
    from quote_email_formatter import format_quote_email
    
    email_body = format_quote_email(quote, recipient_name="John")
"""

from typing import Optional
from datetime import datetime

try:
    from .quote_generator import GeneratedQuote
except ImportError:
    from quote_generator import GeneratedQuote

try:
    from .email_styling import EmailStyler, RecipientRelationship
    STYLING_AVAILABLE = True
except ImportError:
    STYLING_AVAILABLE = False


def format_quote_email(
    quote: GeneratedQuote,
    recipient_name: Optional[str] = None,
    include_intro: bool = True,
    include_detailed_specs: bool = False,
    tone: str = "professional",  # professional, friendly, formal
) -> str:
    """
    Format a quote as a professional email with Ira's voice.
    
    Args:
        quote: GeneratedQuote object
        recipient_name: Name for personalization
        include_intro: Whether to include intro paragraph
        include_detailed_specs: Whether to include full technical specs
        tone: "professional", "friendly", or "formal"
    
    Returns:
        Formatted email body
    """
    recipient = recipient_name or quote.customer_name.split()[0] if quote.customer_name else None
    
    sections = []
    
    # Intro
    if include_intro:
        if tone == "friendly":
            intro = "Here's the quotation you asked for! I've put together what I think is the best configuration for your needs."
        elif tone == "formal":
            intro = f"Please find attached our quotation reference {quote.quote_id} as per your requirements."
        else:
            intro = f"Here's the quotation for your thermoforming requirements (ref: {quote.quote_id})."
        sections.append(intro)
    
    # Machine recommendation
    machine_section = [
        "",
        "**RECOMMENDED MACHINE**",
        "",
        f"**Model:** {quote.recommended_model}",
        f"**Forming Area:** {quote.forming_area_mm[0]} x {quote.forming_area_mm[1]} mm ({quote.forming_area_sqm} sq.m)",
    ]
    
    if quote.machine_variant == "X":
        machine_section.append("**Type:** All-Servo (PF1-X) - Precision forming with automatic features")
    else:
        machine_section.append("**Type:** Pneumatic (PF1-C) - Reliable and cost-effective")
    
    sections.append("\n".join(machine_section))
    
    # Key features
    if quote.key_features:
        features_section = [
            "",
            "**KEY FEATURES**",
            "",
        ]
        for feature in quote.key_features[:6]:
            features_section.append(f"• {feature}")
        sections.append("\n".join(features_section))
    
    # Pricing breakdown
    pricing_section = [
        "",
        "**PRICING**",
        "",
    ]
    
    # Line items
    for item in quote.line_items:
        price_str = f"₹{item.total_price_inr:,}"
        pricing_section.append(f"• {item.description}: {price_str}")
    
    pricing_section.append("")
    pricing_section.append(f"**Subtotal:** ₹{quote.subtotal_inr:,}")
    
    if quote.gst_inr > 0:
        pricing_section.append(f"GST (18%): ₹{quote.gst_inr:,}")
        pricing_section.append(f"**Total:** ₹{quote.total_inr:,} (approx. ${quote.total_usd:,} USD)")
    else:
        pricing_section.append(f"**Total:** ₹{quote.subtotal_inr:,} (approx. ${quote.total_usd:,} USD)")
        pricing_section.append("*(Export pricing - GST exempt)*")
    
    sections.append("\n".join(pricing_section))
    
    # Terms
    terms_section = [
        "",
        "**TERMS**",
        "",
        f"• **Delivery:** {quote.delivery_time}",
        f"• **Payment:** {quote.payment_terms}",
        f"• **Warranty:** {quote.warranty}",
        f"• **Validity:** This quote is valid until {quote.valid_until}",
    ]
    sections.append("\n".join(terms_section))
    
    # Notes/recommendations
    if quote.notes:
        notes_section = [
            "",
            "**NOTES**",
            "",
        ]
        for note in quote.notes[:4]:
            notes_section.append(f"• {note}")
        sections.append("\n".join(notes_section))
    
    # Closing
    if tone == "friendly":
        closing = "\n\nLet me know if you have any questions or if you'd like to discuss the options! I'm happy to adjust the configuration based on your specific needs."
    elif tone == "formal":
        closing = "\n\nPlease do not hesitate to contact us should you require any clarification or wish to discuss alternative configurations."
    else:
        closing = "\n\nLet me know if you have any questions or would like to explore different options. I can adjust the configuration based on your specific requirements."
    
    sections.append(closing)
    
    # Combine
    body = "\n".join(sections)
    
    # Apply styling if available
    if STYLING_AVAILABLE:
        styler = EmailStyler()
        relationship = RecipientRelationship.ACQUAINTANCE
        if recipient and any(name in recipient.lower() for name in ["rushabh", "raghav"]):
            relationship = RecipientRelationship.TRUSTED
        
        body = styler.format_email_response(
            content=body,
            recipient_name=recipient,
            relationship=relationship,
            include_greeting=True,
            include_closing=True,
            include_signature=True,
            signature_name="Ira",
            signature_title="Machinecraft",
            add_offer_help=False,  # Already included in closing
        )
    else:
        # Manual formatting
        if recipient:
            body = f"{recipient},\n\n{body}\n\n- Ira\nMachinecraft"
        else:
            body = f"{body}\n\n- Ira\nMachinecraft"
    
    return body


def format_quote_telegram(
    quote: GeneratedQuote,
    compact: bool = True,
) -> str:
    """
    Format a quote for Telegram (markdown) - Machinecraft style.
    
    Args:
        quote: GeneratedQuote object
        compact: Whether to use compact format
    
    Returns:
        Formatted Telegram message
    """
    w, h = quote.forming_area_mm
    is_servo = quote.machine_variant in ["X", "S"]
    variant_desc = "All-Servo" if is_servo else "Pneumatic"
    
    def fmt_lakhs(amt: int) -> str:
        if amt >= 10000000:
            return f"₹{amt/10000000:.2f} Cr"
        elif amt >= 100000:
            return f"₹{amt/100000:.1f}L"
        return f"₹{amt:,}"
    
    if compact:
        lines = [
            f"📋 **Quote {quote.quote_id}**",
            "",
            f"🏭 **{quote.recommended_model}** ({variant_desc})",
            f"📐 Forming Area: {w} × {h} mm",
            "",
            "💰 **Pricing:**",
            f"   Base Machine: {fmt_lakhs(quote.base_price_inr)}",
        ]
        
        if quote.options_total_inr > 0:
            lines.append(f"   Options: +{fmt_lakhs(quote.options_total_inr)}")
        
        if quote.gst_inr > 0:
            lines.append(f"   GST (18%): +{fmt_lakhs(quote.gst_inr)}")
            lines.append(f"   **Total: {fmt_lakhs(quote.total_inr)}**")
        else:
            lines.append(f"   **Total (Ex-Works): {fmt_lakhs(quote.subtotal_inr)}**")
        
        lines.append(f"   _(${quote.total_usd:,} USD approx.)_")
        
        lines.extend([
            "",
            "📝 **Key Specs:**",
            "   • Closed-chamber zero-sag design",
            "   • Sandwich heating (top & bottom)",
        ])
        
        if is_servo:
            lines.append("   • All-servo drives with auto sheet loading")
        else:
            lines.append("   • Pneumatic drives, manual loading")
        
        lines.extend([
            "",
            f"⏱ Lead Time: {quote.delivery_time}",
            "📅 Valid: 30 days",
            "",
            "_Price Ex-Works Umargam, Gujarat. GST & freight extra._",
        ])
        
        return "\n".join(lines)
    
    # Detailed format
    lines = [
        "═" * 40,
        f"📋 **MACHINECRAFT QUOTATION**",
        f"Quote No: {quote.quote_id}",
        "═" * 40,
        "",
        f"**Machine:** {quote.recommended_model}",
        f"**Type:** {variant_desc} (PF1-{quote.machine_variant} Series)",
        f"**Forming Area:** {w} × {h} mm ({quote.forming_area_sqm} sq.m)",
        "",
        "**KEY FEATURES:**",
        "• Closed-chamber zero-sag design",
        "• Sandwich heating oven (top & bottom IR)",
        "• PLC control with 7\" touchscreen HMI",
    ]
    
    if is_servo:
        lines.extend([
            "• All-servo drives (platen, heaters, clamps)",
            "• Universal motorized aperture setting",
            "• Automatic sheet loading system",
        ])
    else:
        lines.extend([
            "• Pneumatic forming system",
            "• Fixed clamp frames (1 included)",
            "• Manual sheet loading",
        ])
    
    lines.extend([
        "",
        "─" * 40,
        "**PRICING**",
        "─" * 40,
    ])
    
    for item in quote.line_items:
        lines.append(f"• {item.description}: {fmt_lakhs(item.total_price_inr)}")
    
    lines.append("")
    lines.append(f"Subtotal: {fmt_lakhs(quote.subtotal_inr)}")
    
    if quote.gst_inr > 0:
        lines.append(f"GST (18%): {fmt_lakhs(quote.gst_inr)}")
        lines.append(f"**TOTAL: {fmt_lakhs(quote.total_inr)}**")
    else:
        lines.append(f"**TOTAL (Ex-Works): {fmt_lakhs(quote.subtotal_inr)}**")
    
    lines.extend([
        f"_(${quote.total_usd:,} USD approx.)_",
        "",
        "_Price Ex-Works Machinecraft plant, Umargam, Gujarat._",
        "",
        "─" * 40,
        "**TERMS:**",
        f"• Lead Time: {quote.delivery_time}",
        f"• Payment: {quote.payment_terms}",
        f"• Warranty: {quote.warranty}",
        "• Validity: 30 days",
        "─" * 40,
        "",
        "_Packing, freight, insurance & installation extra._",
    ])
    
    return "\n".join(lines)


def format_quote_whatsapp(quote: GeneratedQuote) -> str:
    """
    Format a quote for WhatsApp (plain text, simple formatting).
    
    Args:
        quote: GeneratedQuote object
    
    Returns:
        WhatsApp-friendly message
    """
    lines = [
        f"*MACHINECRAFT QUOTE*",
        f"Ref: {quote.quote_id}",
        "",
        f"*Machine:* {quote.recommended_model}",
        f"*Size:* {quote.forming_area_mm[0]} x {quote.forming_area_mm[1]} mm",
        "",
        "*Pricing:*",
        f"Base: ₹{quote.base_price_inr:,}",
    ]
    
    if quote.options_total_inr > 0:
        lines.append(f"Options: ₹{quote.options_total_inr:,}")
    
    if quote.gst_inr > 0:
        lines.append(f"GST: ₹{quote.gst_inr:,}")
    
    lines.extend([
        f"*Total: ₹{quote.total_inr:,}*",
        f"(${quote.total_usd:,} USD)",
        "",
        f"Delivery: {quote.delivery_time}",
        f"Valid: {quote.valid_until}",
        "",
        "Reply for full details or to discuss options.",
    ])
    
    return "\n".join(lines)


# CLI test
if __name__ == "__main__":
    from quote_generator import generate_quote
    
    print("\n" + "=" * 60)
    print("QUOTE EMAIL FORMATTER TEST")
    print("=" * 60)
    
    # Generate test quote
    quote = generate_quote(
        forming_size=(2000, 1500),
        variant="X",
        customer_name="John Smith",
        company_name="Acme Plastics",
    )
    
    print("\n--- EMAIL FORMAT (Professional) ---")
    print(format_quote_email(quote, recipient_name="John", tone="professional"))
    
    print("\n--- TELEGRAM FORMAT (Compact) ---")
    print(format_quote_telegram(quote, compact=True))
    
    print("\n--- WHATSAPP FORMAT ---")
    print(format_quote_whatsapp(quote))
