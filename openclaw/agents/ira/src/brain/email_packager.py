#!/usr/bin/env python3
"""
MACHINECRAFT EMAIL PACKAGER
============================

Combines content generation with professional email styling
to produce beautiful, branded emails that match Machinecraft's
identity: "Simple, Refined and Sophisticated"

Inspired by:
- Mailchimp email design best practices
- Litmus deliverability guidelines  
- Machinecraft brand standards

Features:
- Beautiful visual hierarchy
- Scannable structure with clear sections
- Professional technical specs formatting
- Warm yet sophisticated tone
- Mobile-friendly formatting
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum

# Import existing modules
try:
    from email_styling import EmailStyler, RecipientRelationship, EMAIL_CONFIG
    EMAIL_STYLING_AVAILABLE = True
except ImportError:
    EMAIL_STYLING_AVAILABLE = False

try:
    from detailed_recommendation import (
        format_detailed_recommendation, 
        get_key_features,
        SERIES_DESCRIPTIONS
    )
    DETAILED_REC_AVAILABLE = True
except ImportError:
    DETAILED_REC_AVAILABLE = False

try:
    from machine_database import get_machine, MachineSpec
    MACHINE_DB_AVAILABLE = True
except ImportError:
    MACHINE_DB_AVAILABLE = False

# Import luxury polish layer
try:
    from email_polish_luxury import (
        polish_email, polish_with_llm, 
        get_qualifying_email_template,
        get_recommendation_email_template,
        get_elegant_signature,
        format_elegant_header,
        format_specs_elegant,
        format_features_elegant,
        OPENAI_AVAILABLE as LLM_POLISH_AVAILABLE
    )
    LUXURY_POLISH_AVAILABLE = True
except ImportError:
    LUXURY_POLISH_AVAILABLE = False
    LLM_POLISH_AVAILABLE = False


# =============================================================================
# MACHINECRAFT BRAND ELEMENTS
# =============================================================================

BRAND = {
    "voice": "Simple, Refined and Sophisticated",
    "colors": {
        "blue": "#2b4b96",
        "yellow": "#ece13c", 
        "black": "#212121",
        "grey": "#ebebeb",
    },
    "company_tagline": "Precision Thermoforming Solutions",
    "signature": {
        "name": "Ira",
        "title": "Your Machinecraft Assistant",
        "company": "Machinecraft Technologies",
        "phone": "+91-22-40140000",
        "email": "ira@machinecraft.org",
        "website": "www.machinecraft.org",
    }
}


# =============================================================================
# EMAIL TEMPLATES
# =============================================================================

class EmailTemplate(Enum):
    """Pre-designed email templates for common scenarios."""
    QUALIFYING_QUESTIONS = "qualifying"
    MACHINE_RECOMMENDATION = "recommendation"
    QUOTATION_FOLLOWUP = "quote_followup"
    TECHNICAL_INFO = "technical"
    GENERAL_RESPONSE = "general"


# =============================================================================
# EMAIL SECTION FORMATTERS
# =============================================================================

def format_section_header(title: str) -> str:
    """Format a section header - clean, sophisticated style."""
    return f"\n━━━ {title.upper()} ━━━\n"


def format_specs_table(specs: Dict[str, str]) -> str:
    """
    Format specifications as a clean, readable table.
    Uses consistent spacing for visual alignment.
    """
    if not specs:
        return ""
    
    # Find max key length for alignment
    max_key_len = max(len(k) for k in specs.keys())
    
    lines = []
    for key, value in specs.items():
        # Right-pad key for alignment
        padded_key = key.ljust(max_key_len)
        lines.append(f"  {padded_key}  │  {value}")
    
    return "\n".join(lines)


def format_features_list(features: List[str], style: str = "bullet") -> str:
    """Format features as an elegant list."""
    if not features:
        return ""
    
    if style == "bullet":
        return "\n".join(f"  • {f}" for f in features)
    elif style == "check":
        return "\n".join(f"  ✓ {f}" for f in features)
    elif style == "arrow":
        return "\n".join(f"  → {f}" for f in features)
    else:
        return "\n".join(f"  • {f}" for f in features)


def format_price(price_inr: int, price_usd: int = None) -> str:
    """Format price in a sophisticated way."""
    if price_inr >= 10000000:
        inr_str = f"₹{price_inr/10000000:.2f} Crore"
    elif price_inr >= 100000:
        inr_str = f"₹{price_inr/100000:.1f} Lakh"
    else:
        inr_str = f"₹{price_inr:,}"
    
    if price_usd:
        return f"{inr_str} (approximately ${price_usd:,} USD)"
    return inr_str


# =============================================================================
# EMAIL PACKAGER CLASS
# =============================================================================

@dataclass
class PackagedEmail:
    """A fully packaged email ready to send."""
    subject: str
    body_plain: str
    body_html: Optional[str] = None
    recipient_name: Optional[str] = None
    template_used: EmailTemplate = EmailTemplate.GENERAL_RESPONSE
    word_count: int = 0
    sections: List[str] = field(default_factory=list)


class MachinecraftEmailPackager:
    """
    Packages IRA's responses into beautiful, branded emails.
    
    Design Philosophy (from Machinecraft brand):
    - Clean, uncluttered layouts
    - Clear visual hierarchy
    - Sophisticated simplicity
    - Data-driven but warm
    """
    
    def __init__(self):
        self.brand = BRAND
        if EMAIL_STYLING_AVAILABLE:
            self.styler = EmailStyler()
        else:
            self.styler = None
    
    # =========================================================================
    # MAIN PACKAGING METHODS
    # =========================================================================
    
    def package_qualifying_questions(
        self,
        customer_name: Optional[str] = None,
        understood_context: str = "",
        questions: List[str] = None,
        use_luxury_polish: bool = True,
    ) -> PackagedEmail:
        """
        Package qualifying questions email with personality.
        
        Style: Warm, helpful, expert - feels human
        """
        # Use luxury template if available
        if LUXURY_POLISH_AVAILABLE and use_luxury_polish:
            body = get_qualifying_email_template(
                customer_name=customer_name,
                understood_context=understood_context,
                questions=questions,
            )
        else:
            # Fallback to basic template
            greeting = f"Hi {customer_name}!" if customer_name else "Hi!"
            
            context_line = ""
            if understood_context:
                context_line = f"I understand you're {understood_context}.\n\n"
            
            questions = questions or [
                "What forming area (size) do you require?",
                "What materials will you be forming?",
                "What is the maximum sheet thickness?",
                "What is your intended application?",
            ]
            
            questions_formatted = format_features_list(questions, style="arrow")
            
            body = f"""{greeting} Happy to help you find the right thermoforming machine.

{context_line}To recommend the best solution for your needs, could you share a few details?

{questions_formatted}

Once I have these, I can suggest the most suitable machine from our range with accurate specs and pricing.

Looking forward to your response!

{self._get_signature()}"""
        
        return PackagedEmail(
            subject="RE: Thermoforming Machine Inquiry",
            body_plain=body,
            recipient_name=customer_name,
            template_used=EmailTemplate.QUALIFYING_QUESTIONS,
            word_count=len(body.split()),
            sections=["greeting", "context", "questions", "cta", "signature"],
        )
    
    def package_machine_recommendation(
        self,
        machine_model: str,
        customer_name: Optional[str] = None,
        application: Optional[str] = None,
        materials: Optional[str] = None,
        alternatives: List[str] = None,
        use_luxury_polish: bool = True,
        use_llm_polish: bool = False,  # Set True for extra human touch
    ) -> PackagedEmail:
        """
        Package a detailed machine recommendation email with personality.
        
        Style: Expert, warm, luxury typography - feels human
        """
        if not MACHINE_DB_AVAILABLE:
            return self._fallback_recommendation(machine_model, customer_name)
        
        machine = get_machine(machine_model)
        if not machine:
            return self._fallback_recommendation(machine_model, customer_name)
        
        # Use luxury template if available
        if LUXURY_POLISH_AVAILABLE and use_luxury_polish:
            # Build overview with personality
            series_info = SERIES_DESCRIPTIONS.get(machine.series, {})
            overview_base = series_info.get("overview", "")
            
            # Add application-specific touch
            if application:
                overview = f"{overview_base} This is a great fit for {application.lower()} work."
            else:
                overview = overview_base
            
            # Add material mention
            if materials and machine.max_sheet_thickness_mm:
                overview += f" Handles {materials} beautifully up to {machine.max_sheet_thickness_mm}mm."
            
            # Build features list
            features = []
            if machine.forming_area_mm:
                features.append(f"{machine.forming_area_mm} mm forming area")
            features.extend([
                "Sandwich heating (top & bottom IR)",
                "Zero-sag closed chamber design",
                "PLC with touchscreen HMI",
            ])
            if machine.vacuum_pump_capacity:
                features.append(f"{machine.vacuum_pump_capacity} vacuum pump")
            
            # Build specs dict
            specs = {}
            if machine.forming_area_mm:
                specs["Forming Area"] = f"{machine.forming_area_mm} mm"
            if machine.max_sheet_thickness_mm:
                specs["Sheet Thickness"] = f"{machine.min_sheet_thickness_mm or 1} - {machine.max_sheet_thickness_mm} mm"
            if machine.heater_power_kw:
                specs["Heater Power"] = f"{machine.heater_power_kw} kW"
            if machine.vacuum_pump_capacity:
                specs["Vacuum"] = machine.vacuum_pump_capacity
            if machine.power_supply:
                specs["Power Supply"] = machine.power_supply
            
            # Price string
            price_info = ""
            if machine.price_inr:
                price_usd = machine.price_usd or (machine.price_inr // 83)
                if machine.price_inr >= 10000000:
                    price_info = f"₹{machine.price_inr/10000000:.2f} Cr (~${price_usd:,} USD) - base configuration"
                else:
                    price_info = f"₹{machine.price_inr/100000:.1f} Lakh (~${price_usd:,} USD) - base configuration"
            
            # Terms string
            terms_info = "12-16 weeks lead time • 30/60/10 payment terms • 12 month warranty"
            
            body = get_recommendation_email_template(
                customer_name=customer_name,
                machine_model=machine.model,
                machine_overview=overview,
                key_features=features,
                specs=specs,
                price_info=price_info,
                terms_info=terms_info,
                alternatives=alternatives,
            )
            
            # Optional LLM polish for extra human touch
            if use_llm_polish and LLM_POLISH_AVAILABLE:
                body = polish_with_llm(body, customer_name=customer_name, personality_level="balanced")
        
        else:
            # Fallback to basic template (original code)
            greeting = f"Hi {customer_name}!" if customer_name else "Hi!"
            app_context = f" for your {application.lower()} application" if application else ""
            series_info = SERIES_DESCRIPTIONS.get(machine.series, {})
            series_overview = series_info.get("overview", "")
            
            material_line = ""
            if materials:
                material_line = f"\nThis machine handles {materials} excellently"
                if machine.max_sheet_thickness_mm:
                    material_line += f" with sheets up to {machine.max_sheet_thickness_mm}mm thick."
                else:
                    material_line += "."
            
            specs = {}
            if machine.forming_area_mm:
                specs["Forming Area"] = f"{machine.forming_area_mm} mm"
            if machine.max_sheet_thickness_mm:
                specs["Sheet Thickness"] = f"{machine.min_sheet_thickness_mm or 1} - {machine.max_sheet_thickness_mm} mm"
            if machine.heater_power_kw:
                specs["Heater Power"] = f"{machine.heater_power_kw} kW"
            if machine.vacuum_pump_capacity:
                specs["Vacuum Pump"] = machine.vacuum_pump_capacity
            if machine.power_supply:
                specs["Power Supply"] = machine.power_supply
            
            specs_formatted = format_specs_table(specs)
            features = get_key_features(machine) if DETAILED_REC_AVAILABLE else []
            features_formatted = format_features_list(features[:6], style="check")
            
            price_section = ""
            if machine.price_inr:
                price_str = format_price(machine.price_inr, machine.price_usd)
                price_section = f"\n\n**Indicative Pricing**\nBase Machine Price: {price_str}\n(Ex-Works, excludes GST)"
            
            body = f"""{greeting} Happy to help{app_context}.

Based on your requirements, I recommend the **{machine.model}**.

**Overview**
{series_overview}{material_line}

**Key Features**
{features_formatted}

**Technical Specs**
{specs_formatted}
{price_section}

Let me know if you have questions!

{self._get_signature()}"""
        
        return PackagedEmail(
            subject=f"Machine Recommendation: {machine.model}",
            body_plain=body,
            recipient_name=customer_name,
            template_used=EmailTemplate.MACHINE_RECOMMENDATION,
            word_count=len(body.split()),
            sections=["greeting", "overview", "features", "specs", "pricing", "terms", "cta", "signature"],
        )
    
    def package_technical_response(
        self,
        content: str,
        customer_name: Optional[str] = None,
        machine_model: Optional[str] = None,
    ) -> PackagedEmail:
        """
        Package a technical Q&A response.
        
        Style: Expert, helpful, clear
        """
        greeting = f"Hi {customer_name}!" if customer_name else "Hi!"
        
        body = f"""{greeting}

{content}

Let me know if you need any clarification or have more questions about the technical details.

{self._get_signature()}"""
        
        return PackagedEmail(
            subject=f"RE: Technical Question{f' - {machine_model}' if machine_model else ''}",
            body_plain=body,
            recipient_name=customer_name,
            template_used=EmailTemplate.TECHNICAL_INFO,
            word_count=len(body.split()),
        )
    
    def package_general_response(
        self,
        content: str,
        customer_name: Optional[str] = None,
        subject: str = "RE: Your Inquiry",
    ) -> PackagedEmail:
        """
        Package a general response email.
        
        Style: Professional, warm, clear
        """
        # Clean up content
        content = self._clean_content(content)
        
        greeting = f"Hi {customer_name}!" if customer_name else "Hi!"
        
        body = f"""{greeting}

{content}

Let me know if you need anything else.

{self._get_signature()}"""
        
        return PackagedEmail(
            subject=subject,
            body_plain=body,
            recipient_name=customer_name,
            template_used=EmailTemplate.GENERAL_RESPONSE,
            word_count=len(body.split()),
        )
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_signature(self, style: str = "full") -> str:
        """Get email signature based on style."""
        sig = self.brand["signature"]
        
        if style == "minimal":
            return f"""Best,
{sig['name']}
{sig['company']}"""
        
        elif style == "full":
            return f"""Best regards,

{sig['name']}
{sig['title']}
{sig['company']}
📧 {sig['email']}
🌐 {sig['website']}"""
        
        else:  # standard
            return f"""Best,
{sig['name']}
{sig['company']}"""
    
    def _clean_content(self, content: str) -> str:
        """Clean up content - remove artifacts, fix formatting."""
        # Remove excessive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Remove AI-isms
        ai_phrases = [
            "As an AI assistant",
            "I'm just an AI",
            "I don't have personal feelings",
        ]
        for phrase in ai_phrases:
            content = content.replace(phrase, "")
        
        # Remove overly formal phrases
        formal_phrases = [
            "I hope this email finds you well",
            "Per my last email",
            "Please do not hesitate to contact",
        ]
        for phrase in formal_phrases:
            content = re.sub(re.escape(phrase), "", content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def _fallback_recommendation(
        self,
        machine_model: str,
        customer_name: Optional[str] = None,
    ) -> PackagedEmail:
        """Fallback when machine database isn't available."""
        greeting = f"Hi {customer_name}!" if customer_name else "Hi!"
        
        body = f"""{greeting}

Based on your requirements, I recommend the **{machine_model}**.

For detailed specifications and pricing, I'll connect you with our sales team who can provide a comprehensive quote.

{self._get_signature()}"""
        
        return PackagedEmail(
            subject=f"Machine Recommendation: {machine_model}",
            body_plain=body,
            recipient_name=customer_name,
            template_used=EmailTemplate.MACHINE_RECOMMENDATION,
            word_count=len(body.split()),
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_packager = None

def get_packager() -> MachinecraftEmailPackager:
    """Get singleton email packager instance."""
    global _packager
    if _packager is None:
        _packager = MachinecraftEmailPackager()
    return _packager


def package_email(
    content: str,
    email_type: str = "general",
    customer_name: Optional[str] = None,
    **kwargs
) -> PackagedEmail:
    """
    Quick packaging function.
    
    Args:
        content: Email content or context
        email_type: "qualifying", "recommendation", "technical", "general"
        customer_name: Recipient name
        **kwargs: Additional args for specific templates
    
    Returns:
        PackagedEmail ready to send
    """
    packager = get_packager()
    
    if email_type == "qualifying":
        return packager.package_qualifying_questions(
            customer_name=customer_name,
            understood_context=kwargs.get("understood_context", ""),
            questions=kwargs.get("questions"),
        )
    
    elif email_type == "recommendation":
        return packager.package_machine_recommendation(
            machine_model=kwargs.get("machine_model", ""),
            customer_name=customer_name,
            application=kwargs.get("application"),
            materials=kwargs.get("materials"),
            alternatives=kwargs.get("alternatives"),
        )
    
    elif email_type == "technical":
        return packager.package_technical_response(
            content=content,
            customer_name=customer_name,
            machine_model=kwargs.get("machine_model"),
        )
    
    else:
        return packager.package_general_response(
            content=content,
            customer_name=customer_name,
            subject=kwargs.get("subject", "RE: Your Inquiry"),
        )


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MACHINECRAFT EMAIL PACKAGER TEST")
    print("Brand: Simple, Refined and Sophisticated")
    print("=" * 70)
    
    packager = MachinecraftEmailPackager()
    
    # Test 1: Qualifying Questions
    print("\n" + "─" * 70)
    print("TEST 1: QUALIFYING QUESTIONS EMAIL")
    print("─" * 70)
    
    email1 = packager.package_qualifying_questions(
        customer_name="Vignesh",
        understood_context="looking for a thermoforming machine for telecom applications",
    )
    print(email1.body_plain)
    
    # Test 2: Machine Recommendation
    print("\n" + "─" * 70)
    print("TEST 2: MACHINE RECOMMENDATION EMAIL")
    print("─" * 70)
    
    email2 = packager.package_machine_recommendation(
        machine_model="PF1-C-2015",
        customer_name="Aleksandr",
        application="sanitary-ware",
        materials="ABS+PMMA",
        alternatives=["PF1-C-2515", "PF2-P2020"],
    )
    print(email2.body_plain[:2000])
    print("...[truncated]")
    
    print(f"\nWord count: {email2.word_count}")
    print(f"Sections: {email2.sections}")
