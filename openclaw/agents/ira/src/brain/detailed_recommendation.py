#!/usr/bin/env python3
"""
DETAILED MACHINE RECOMMENDATION FORMATTER
==========================================

Generates comprehensive, professional machine recommendations
matching the level of detail in formal PDF quotes.

Includes:
- Machine overview paragraph
- Key features (bullet points)
- Full technical specifications
- Pricing with proper disclaimers
- Delivery and warranty terms
"""

from typing import Optional, Dict, List
from dataclasses import dataclass

# Import machine database
try:
    from machine_database import get_machine, MachineSpec, MACHINE_SPECS
    MACHINE_DB_AVAILABLE = True
except ImportError:
    MACHINE_DB_AVAILABLE = False


# =============================================================================
# SERIES DESCRIPTIONS
# =============================================================================

SERIES_DESCRIPTIONS = {
    "PF1": {
        "name": "PF1 Positive Forming Series",
        "tagline": "Heavy-Gauge Single-Station Cut-Sheet Thermoforming",
        "overview": (
            "The PF1 series represents Machinecraft's flagship heavy-gauge thermoforming machines. "
            "Featuring a robust closed-chamber, zero-sag design with sandwich heating (top & bottom IR heaters), "
            "these machines deliver precision forming for thermoplastic sheets from 1mm to 10mm thickness."
        ),
        "industries": ["Automotive interiors", "Aerospace components", "Industrial enclosures", 
                      "Sanitary-ware", "Refrigeration liners", "Commercial displays"],
    },
    "PF2": {
        "name": "PF2 Large Format Series",
        "tagline": "Extra-Large Positive Forming",
        "overview": (
            "The PF2 series extends our positive forming capability to larger forming areas. "
            "Built for demanding applications requiring parts over 2 meters, with the same precision "
            "and reliability as the PF1 series."
        ),
        "industries": ["Large automotive parts", "Bathtubs", "Commercial refrigeration", "Signage"],
    },
    "UNO": {
        "name": "UNO Entry Series",
        "tagline": "Compact Single-Heater Thermoforming",
        "overview": (
            "The UNO series offers a cost-effective entry into thermoforming with single-side heating. "
            "Ideal for startups and smaller production runs, these machines maintain Machinecraft's "
            "quality standards in a more accessible package."
        ),
        "industries": ["Prototyping", "Small batch production", "Packaging", "Educational"],
    },
    "DUO": {
        "name": "DUO Dual-Heater Series", 
        "tagline": "Double-Sided Heating for Thicker Materials",
        "overview": (
            "The DUO series features top and bottom heating for faster, more uniform forming of thicker sheets. "
            "Perfect for applications requiring consistent temperature distribution."
        ),
        "industries": ["Thick-gauge packaging", "Industrial parts", "Medical trays"],
    },
}

# =============================================================================
# KEY FEATURES BY SERIES/VARIANT
# =============================================================================

def get_key_features(machine: "MachineSpec") -> List[str]:
    """Get key features based on machine series and variant."""
    
    features = []
    
    # Common PF1/PF2 features
    if machine.series in ["PF1", "PF2"]:
        features.extend([
            "Closed-Chamber Zero-Sag Design",
            f"{machine.forming_area_mm} mm Forming Area",
            "Sandwich Heating Oven (Top & Bottom IR Heaters)",
        ])
        # Add heater details if available
        if machine.num_heaters and machine.heater_zones:
            features.append(f"{machine.num_heaters} Ceramic Heaters with {machine.heater_zones}-Zone Control")
        else:
            features.append("Multi-Zone Ceramic Heater Array")
        features.extend([
            "Pre-blow / Sag Compensation System with Light Sensors",
            "PLC Control with 7\" Color Touchscreen HMI",
        ])
        
        # Variant-specific features
        is_servo = 'X' in machine.model or 'servo' in (machine.variant or '').lower()
        if is_servo:
            features.extend([
                "All-Servo Drive System (Table, Platen, Clamp Frame)",
                "Universal Motorized Aperture Setting",
                "Recipe Memory for Quick Changeover",
            ])
        else:
            features.extend([
                "Pneumatic Forming System with Proportional Valves",
                "4-Pillar Guided Forming Press",
                "Manual Aperture Adjustment with Quick-Lock",
            ])
        
        features.extend([
            f"{machine.vacuum_pump_capacity} Vacuum Pump with {machine.vacuum_tank_size or '500L'} Tank",
            "Plug-Assist Compatibility",
            "Safety Interlocks & Light Curtains",
        ])
    
    elif machine.series == "UNO":
        features.extend([
            f"{machine.forming_area_mm} mm Forming Area",
            "Single-Side Ceramic Heating",
            "Compact Footprint Design",
            "PLC Control with Touchscreen",
            "Quick Tool Change System",
            f"{machine.vacuum_pump_capacity} Vacuum System",
        ])
    
    elif machine.series == "DUO":
        features.extend([
            f"{machine.forming_area_mm} mm Forming Area",
            "Double-Sided (Top & Bottom) Heating",
            "Faster Cycle Times for Thick Sheets",
            "PLC Control with Recipe Memory",
            f"{machine.vacuum_pump_capacity} Vacuum System",
        ])
    
    return features


# =============================================================================
# DETAILED RECOMMENDATION FORMATTER
# =============================================================================

def format_detailed_recommendation(
    machine_model: str,
    customer_name: str = None,
    application: str = None,
    materials: str = None,
    include_pricing: bool = True,
    include_terms: bool = True,
) -> str:
    """
    Generate a detailed, professional machine recommendation.
    
    Args:
        machine_model: Machine model code (e.g., "PF1-C-2015")
        customer_name: Customer's name for personalization
        application: Their intended application/industry
        materials: Materials they'll be forming
        include_pricing: Whether to include pricing details
        include_terms: Whether to include delivery/warranty terms
        
    Returns:
        Formatted recommendation text
    """
    if not MACHINE_DB_AVAILABLE:
        return f"I recommend the {machine_model}. Please contact sales for detailed specifications."
    
    machine = get_machine(machine_model)
    if not machine:
        return f"I recommend the {machine_model}. Please contact sales for detailed specifications."
    
    # Get series info
    series_info = SERIES_DESCRIPTIONS.get(machine.series, {
        "name": f"{machine.series} Series",
        "tagline": "Thermoforming Machine",
        "overview": "Professional thermoforming solution.",
        "industries": [],
    })
    
    # Build greeting
    greeting = f"Hi {customer_name}!" if customer_name else "Hi!"
    
    # Application context
    app_context = ""
    if application:
        app_context = f" for your {application.lower()} application"
    
    # Material context
    material_context = ""
    if materials:
        material_context = f" The {machine.model} handles {materials} excellently"
        if machine.max_sheet_thickness_mm:
            material_context += f" with sheets up to {machine.max_sheet_thickness_mm}mm thick."
        else:
            material_context += "."
    
    # Get features
    features = get_key_features(machine)
    features_text = "\n".join(f"• {f}" for f in features[:8])
    
    # Build technical specs table
    specs_lines = []
    if machine.forming_area_mm:
        specs_lines.append(f"• **Forming Area:** {machine.forming_area_mm} mm")
    if machine.max_draw_depth_mm:
        specs_lines.append(f"• **Max Draw Depth:** {machine.max_draw_depth_mm} mm")
    if machine.max_sheet_thickness_mm:
        specs_lines.append(f"• **Sheet Thickness Range:** {machine.min_sheet_thickness_mm or 1}-{machine.max_sheet_thickness_mm} mm")
    if machine.heater_power_kw:
        heater_detail = f"{machine.heater_power_kw} kW"
        if machine.num_heaters and machine.heater_zones:
            heater_detail += f" ({machine.num_heaters} heaters, {machine.heater_zones} zones)"
        specs_lines.append(f"• **Heater Power:** {heater_detail}")
    if machine.heater_type:
        specs_lines.append(f"• **Heater Type:** {machine.heater_type}")
    if machine.vacuum_pump_capacity:
        specs_lines.append(f"• **Vacuum Pump:** {machine.vacuum_pump_capacity}")
    if machine.vacuum_tank_size:
        specs_lines.append(f"• **Vacuum Tank:** {machine.vacuum_tank_size}")
    if machine.total_power_kw:
        specs_lines.append(f"• **Total Connected Load:** {machine.total_power_kw} kW")
    if machine.power_supply:
        specs_lines.append(f"• **Power Supply:** {machine.power_supply}")
    
    specs_text = "\n".join(specs_lines)
    
    # Pricing section
    pricing_text = ""
    if include_pricing and machine.price_inr:
        price_inr = machine.price_inr
        price_usd = machine.price_usd or (price_inr // 83)
        
        # Format nicely
        if price_inr >= 10000000:
            price_str = f"₹{price_inr/10000000:.2f} Crore"
        else:
            price_str = f"₹{price_inr/100000:.1f} Lakh"
        
        pricing_text = f"""
**INDICATIVE PRICING**
• **Base Machine Price:** {price_str} (~${price_usd:,} USD)
• Price is Ex-Works, excluding GST, freight, and installation
• Subject to current configuration and final specifications
"""
    
    # Terms section  
    terms_text = ""
    if include_terms:
        terms_text = """
**TERMS & CONDITIONS**
• **Lead Time:** 12-16 weeks from order confirmation
• **Payment Terms:** 30% advance, 60% before dispatch, 10% after installation
• **Warranty:** 12 months from installation or 18 months from dispatch (whichever earlier)
• **Installation:** Available at additional cost; includes commissioning and operator training
"""
    
    # Assemble full response
    response = f"""{greeting} Happy to help{app_context}.

Based on your requirements, I recommend the **{machine.model}** from our {series_info['name']}.

**MACHINE OVERVIEW**

{series_info['overview']}{material_context}

**KEY FEATURES**

{features_text}

**TECHNICAL SPECIFICATIONS**

{specs_text}
{pricing_text}{terms_text}
Would you like me to prepare a formal quotation, or do you have any questions about the machine specifications?"""
    
    return response


def format_comparison(
    primary_model: str,
    alternatives: List[str],
    customer_name: str = None,
) -> str:
    """
    Generate a comparison of multiple machines.
    """
    if not MACHINE_DB_AVAILABLE:
        return "I can compare multiple machines for you. Please contact sales for details."
    
    primary = get_machine(primary_model)
    if not primary:
        return f"Unable to find details for {primary_model}."
    
    greeting = f"Hi {customer_name}!" if customer_name else "Hi!"
    
    # Build comparison table
    lines = [f"{greeting} Here's a comparison of suitable machines for your requirements:\n"]
    
    # Primary recommendation
    lines.append(f"**Recommended: {primary.model}**")
    if primary.forming_area_mm:
        lines.append(f"• Forming Area: {primary.forming_area_mm} mm")
    if primary.max_sheet_thickness_mm:
        lines.append(f"• Max Thickness: {primary.max_sheet_thickness_mm} mm")
    if primary.price_inr:
        lines.append(f"• Price: ₹{primary.price_inr/100000:.1f}L (~${primary.price_usd or primary.price_inr//83:,})")
    lines.append("")
    
    # Alternatives
    if alternatives:
        lines.append("**Alternatives:**")
        for alt_model in alternatives[:3]:
            alt = get_machine(alt_model)
            if alt:
                price_str = f"₹{alt.price_inr/100000:.1f}L" if alt.price_inr else "Contact for price"
                lines.append(f"• {alt.model}: {alt.forming_area_mm} mm, {price_str}")
    
    lines.append("\nWould you like detailed specs on any of these options?")
    
    return "\n".join(lines)


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    # Test detailed recommendation
    print("=" * 70)
    print("TEST: Detailed PF1-C-1008 Recommendation")
    print("=" * 70)
    
    result = format_detailed_recommendation(
        machine_model="PF1-C-1008",
        customer_name="Yogesh",
        application="aerospace enclosures",
        materials="Kydex",
        include_pricing=True,
        include_terms=True,
    )
    
    print(result)
