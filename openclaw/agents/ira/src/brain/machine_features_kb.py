#!/usr/bin/env python3
"""
MACHINE FEATURES KNOWLEDGE BASE
================================

Reference knowledge for Ira to explain machine options to customers.
Source: Machinecraft Vacuum Forming Machines – Full Model List with Sizes & Descriptions

Usage:
    from machine_features_kb import get_feature_explanation, FEATURE_KB
    
    explanation = get_feature_explanation("autoloader")
"""

from typing import Dict, Optional

FEATURE_KB: Dict[str, dict] = {
    # ==========================================================================
    # AUTOLOADER
    # ==========================================================================
    "autoloader": {
        "name": "Automatic Sheet Loader",
        "short": "Servo-controlled pick & place system for automated sheet handling",
        "available_from": "PF1-X-1210",  # Autoloader starts from this model
        "how_it_works": """
The Machinecraft Automatic Sheet Loader automates loading of large thermoplastic sheets:

1. **Pallet-Based Input**: Sheets are pre-loaded onto a pallet in a staging zone
2. **Sheet Alignment**: 2 servo motors control X-Y centering of the top sheet
3. **Single Sheet Separation**: Pneumatic air-blow separator + mechanical dancing frame ensures only one sheet is picked
4. **Vacuum Pick-up**: Suction cups on servo-driven arm pick up the topmost sheet
5. **Transfer**: Sheet is placed onto forming area via servo gantry
6. **Double-Pick Protection**: Dual sensors verify single sheet pickup
7. **Simultaneous Unloading**: While next sheet loads, formed part is ejected
""",
        "benefits": [
            "Cycle Time Reduction – Simultaneous loading/unloading improves throughput",
            "Labor Saving – No manual intervention for heavy/large sheets",
            "Consistency – Eliminates sheet alignment errors, reduces scrap",
            "Clean Operation – Controlled movement reduces scratches"
        ],
        "when_to_recommend": "High volume production (>500 parts/day), heavy sheets (>5kg), consistent quality requirements",
        "price_impact": "Adds ~$30-50K to machine cost but saves 1-2 operators per shift"
    },
    
    # ==========================================================================
    # HEATER TYPES
    # ==========================================================================
    "heater_ceramic": {
        "name": "IR Ceramic Heaters",
        "short": "Standard option – reliable and robust for thick sheets",
        "how_it_works": "Ceramic elements heat up and radiate infrared energy slowly, delivering uniform heat over time",
        "pros": [
            "Excellent long-wave IR output – ideal for thick sheets (ABS, HDPE, PP)",
            "Stable and consistent heat – less prone to overshoot",
            "Low cost, long lifespan, rugged construction",
            "Performs well with textured sheet surfaces"
        ],
        "cons": [
            "Slower response time (30–60 sec to heat up)",
            "Not ideal for fast-cycle or ultra-thin applications",
            "Higher energy in idle cycles"
        ],
        "best_for": "General-purpose forming, thick gauge sheets, cost-sensitive projects, simple geometries",
        "price_impact": "Standard (included in base price)"
    },
    
    "heater_quartz": {
        "name": "IR Quartz Heaters",
        "short": "Mid-tier option – fast and efficient",
        "how_it_works": "Quartz tube heaters heat quickly and deliver medium to long-wave IR radiation",
        "pros": [
            "Faster response than ceramic (10–15 sec startup)",
            "Better energy efficiency with lower thermal inertia",
            "More uniform heat for medium-thickness sheets",
            "Good balance between performance and cost"
        ],
        "cons": [
            "More delicate than ceramic – needs careful handling",
            "Not as rapid as halogen",
            "Moderate upfront cost"
        ],
        "best_for": "General and technical thermoforming, mid-thickness materials (3–6 mm)",
        "price_impact": "Adds ~5-10% to machine cost"
    },
    
    "heater_halogen": {
        "name": "IR Halogen Heaters",
        "short": "Premium option – ultra-fast, high precision",
        "how_it_works": "Halogen lamps emit short-wave IR with very fast heat-up and cool-down",
        "pros": [
            "Fastest response time (<6 sec warmup)",
            "Can be turned off instantly = 30–50% energy savings",
            "Ideal for precise temperature zones",
            "Perfect for thin films, multi-layer sheets, high-speed lines"
        ],
        "cons": [
            "Requires specialized controllers (e.g., Heatronik)",
            "Higher cost – upfront and maintenance",
            "Sensitive to dust and handling errors",
            "Overkill for basic applications"
        ],
        "best_for": "Thin-wall, multi-cavity molds, clean-room, high-speed machines",
        "price_impact": "Adds ~20-30% to machine cost"
    },
    
    # ==========================================================================
    # VACUUM SYSTEM
    # ==========================================================================
    "vacuum_system": {
        "name": "Vacuuming System",
        "short": "Multi-stage automation for precision sheet forming",
        "components": {
            "vacuum_pump": {
                "name": "Oil-Lubricated Rotary Vane Vacuum Pump",
                "capacity": "Up to 300 m³/hr depending on machine size",
                "brands": "Busch, Becker, or equivalent",
                "features": "High flow rate, reliable, quiet operation"
            },
            "vacuum_tank": {
                "name": "Integrated Vacuum Tank",
                "capacity": "600 to 4000 liters depending on size",
                "purpose": "Stores vacuum for instant suction during forming"
            },
            "servo_valve": {
                "name": "Servo-Controlled Vacuum Valve (optional)",
                "brand": "Festo proportional servo valve",
                "capabilities": [
                    "Multi-step vacuum (30%, 60%, 100%)",
                    "Fine control over form-fill timing",
                    "Soft demolding or partial draw modes",
                    "Recipe-driven vacuum profiling"
                ]
            },
            "preblow": {
                "name": "Preblow and Sheet Release System",
                "purpose": "Pre-inflate heated sheet before mold contact (male tool forming)",
                "benefits": "Even wall thickness, reduces thinning at corners"
            }
        },
        "benefits": [
            "Faster cycles through vacuum tank buffering",
            "Flexible forming with programmable profiles",
            "Silent and efficient operation",
            "Precise preblow and release for complex geometry"
        ]
    },
    
    # ==========================================================================
    # TOOL CHANGE SYSTEM
    # ==========================================================================
    "quick_change": {
        "name": "Quick Change System with Ball Transfer Units",
        "short": "Rapid mold setup with minimal manual effort",
        "how_it_works": """
Ball transfer grid embedded in lower platen allows mold base to glide smoothly:
1. Air cylinders beneath platen lift the tool ~10-15mm with a switch
2. Operators slide mold into position with zero lifting
3. Tool clamping secures the mold
""",
        "benefits": [
            "Greatly reduces manpower and time for format changes",
            "Ideal for large or heavy tools",
            "Reduces operator strain and injury risk"
        ],
        "when_to_recommend": "Multiple product runs, heavy molds (>100kg), frequent changeovers"
    },
    
    "tool_clamping_manual": {
        "name": "Manual Tool Clamping",
        "short": "Standard through-bolts and guide bushings",
        "best_for": "Fixed-format applications, single product runs",
        "price_impact": "Standard (included)"
    },
    
    "tool_clamping_pneumatic": {
        "name": "Pneumatic Tool Clamping",
        "short": "Faster tool locking without manual bolts",
        "best_for": "Frequent tool changes, modular tooling, quick-release systems",
        "price_impact": "Optional upgrade"
    },
    
    # ==========================================================================
    # COOLING SYSTEMS
    # ==========================================================================
    "cooling_centrifugal": {
        "name": "Centrifugal Fan Cooling",
        "short": "Most common and cost-effective cooling method",
        "how_it_works": "High-volume fans directed toward mold face with adjustable louvers",
        "benefits": [
            "Simple setup and maintenance",
            "Easy to retrofit or adjust",
            "Suitable for moderate cycle times"
        ],
        "best_for": "Flat or shallow-draw parts, general-purpose production",
        "price_impact": "Standard (included)"
    },
    
    "cooling_ducted": {
        "name": "Central Ducted Cooling System",
        "short": "Premium cooling for complex molds and high volume",
        "how_it_works": "High-CFM blower delivers air through ducting manifold to precise tool locations",
        "benefits": [
            "Superior airflow control",
            "Targeted cooling for complex molds",
            "Reduced cycle time for high-output"
        ],
        "best_for": "Deep-draw molds, multi-zone parts, fast cycle requirements",
        "price_impact": "Optional upgrade (~$5-10K)"
    },
    
    # ==========================================================================
    # SHEET LOADING OPTIONS
    # ==========================================================================
    "sheet_loading_manual": {
        "name": "Manual Sheet Loading",
        "short": "Operator places sheets by hand",
        "when_to_use": [
            "Low volume production (<200 parts/day)",
            "Budget-conscious projects",
            "Prototype or sample runs",
            "Light sheets (<5kg)"
        ],
        "series": "PF1-C (standard)",
        "price_impact": "Base price (no extra cost)"
    },
    
    "sheet_loading_auto": {
        "name": "Automatic Sheet Loading",
        "short": "Servo-driven pick & place autoloader",
        "when_to_use": [
            "High volume production (>500 parts/day)",
            "Heavy sheets (>5kg)",
            "Consistent quality requirements",
            "Labor cost reduction needed"
        ],
        "series": "PF1-X (from model 1210 onwards)",
        "price_impact": "Adds ~$30-50K"
    },
    
    # ==========================================================================
    # SERIES COMPARISON (C vs X)
    # ==========================================================================
    "pf1_c_series": {
        "name": "PF1-C Series (Pneumatic)",
        "short": "Cost-effective solution for manual operations",
        "drive_type": "Air cylinder driven (pneumatic)",
        "sheet_loading": "Manual",
        "best_for": [
            "Budget-conscious buyers",
            "Low to medium volume",
            "Simple parts",
            "First-time thermoforming"
        ],
        "typical_price_range": "$40K - $120K USD",
        "key_advantage": "Lower upfront cost, simpler operation"
    },
    
    "pf1_x_series": {
        "name": "PF1-X Series (All-Servo)",
        "short": "Premium automation with servo precision",
        "drive_type": "All servo-controlled movements",
        "sheet_loading": "Automatic (from model 1210)",
        "best_for": [
            "High volume production",
            "Precision parts",
            "Reduced labor costs",
            "Tier 1 suppliers, OEMs"
        ],
        "typical_price_range": "$85K - $300K USD",
        "key_advantage": "Higher throughput, better consistency, lower labor cost"
    },
    
    # ==========================================================================
    # CONTROL SYSTEM
    # ==========================================================================
    "control_system": {
        "name": "Control System Architecture",
        "short": "Mitsubishi PLC & Servo platform with touchscreen HMI",
        "components": {
            "plc": "Mitsubishi PLC (Japan) – high-speed logic control",
            "servo": "Mitsubishi servo drives for all motion",
            "hmi": "10.1\" industrial touchscreen (upgradeable to 15\")",
            "pneumatics": "Festo / SMC",
            "sensors": "Keyence / Sick / P+F",
            "vacuum_pumps": "Busch / Becker",
            "heaters": "Elstein / TQS / Ceramicx"
        },
        "features": [
            "Multi-level password protection",
            "Recipe storage on SD card",
            "Real-time I/O visualization",
            "Alarm history and diagnostics",
            "Optional remote monitoring (IIoT)"
        ]
    }
}


def get_feature_explanation(feature_key: str, detail_level: str = "full") -> Optional[str]:
    """
    Get explanation for a machine feature.
    
    Args:
        feature_key: Key like "autoloader", "heater_ceramic", "pf1_x_series"
        detail_level: "short", "medium", or "full"
    
    Returns:
        Formatted explanation string
    """
    # Normalize the key
    key = feature_key.lower().replace(" ", "_").replace("-", "_")
    
    # Try exact match first
    feature = FEATURE_KB.get(key)
    
    # Try fuzzy match
    if not feature:
        for k, v in FEATURE_KB.items():
            if key in k or k in key:
                feature = v
                break
            if key in v.get("name", "").lower():
                feature = v
                break
    
    if not feature:
        return None
    
    name = feature.get("name", "")
    short = feature.get("short", "")
    
    if detail_level == "short":
        return f"**{name}**: {short}"
    
    # Build full explanation
    lines = [f"**{name}**", f"_{short}_", ""]
    
    if feature.get("how_it_works"):
        lines.append(feature["how_it_works"].strip())
        lines.append("")
    
    if feature.get("pros"):
        lines.append("**Pros:**")
        for p in feature["pros"]:
            lines.append(f"• {p}")
        lines.append("")
    
    if feature.get("cons"):
        lines.append("**Cons:**")
        for c in feature["cons"]:
            lines.append(f"• {c}")
        lines.append("")
    
    if feature.get("benefits"):
        lines.append("**Benefits:**")
        for b in feature["benefits"]:
            lines.append(f"• {b}")
        lines.append("")
    
    if feature.get("best_for"):
        best = feature["best_for"]
        if isinstance(best, list):
            lines.append("**Best For:** " + ", ".join(best))
        else:
            lines.append(f"**Best For:** {best}")
        lines.append("")
    
    if feature.get("when_to_recommend"):
        lines.append(f"**When to Recommend:** {feature['when_to_recommend']}")
        lines.append("")
    
    if feature.get("price_impact"):
        lines.append(f"**Price Impact:** {feature['price_impact']}")
    
    return "\n".join(lines).strip()


def get_series_comparison() -> str:
    """Get comparison between PF1-C and PF1-X series."""
    c = FEATURE_KB["pf1_c_series"]
    x = FEATURE_KB["pf1_x_series"]
    
    return f"""
**PF1-C Series (Pneumatic)** vs **PF1-X Series (All-Servo)**

| Feature | PF1-C | PF1-X |
|---------|-------|-------|
| Drive Type | {c['drive_type']} | {x['drive_type']} |
| Sheet Loading | {c['sheet_loading']} | {x['sheet_loading']} |
| Price Range | {c['typical_price_range']} | {x['typical_price_range']} |
| Best For | {', '.join(c['best_for'][:2])} | {', '.join(x['best_for'][:2])} |

**Choose PF1-C if:** Budget is priority, low-medium volume, simple parts
**Choose PF1-X if:** High volume, precision needed, want to reduce labor costs
"""


def answer_feature_question(question: str) -> Optional[str]:
    """
    Answer a question about machine features.
    
    Examples:
        "What does autoloader do?"
        "What's the difference between ceramic and quartz heaters?"
        "Should I choose PF1-C or PF1-X?"
    """
    q = question.lower()
    
    # Autoloader questions
    if "autoloader" in q or "auto loader" in q or "automatic loading" in q:
        return get_feature_explanation("autoloader")
    
    # Heater questions
    if "heater" in q:
        if "ceramic" in q:
            return get_feature_explanation("heater_ceramic")
        elif "quartz" in q:
            return get_feature_explanation("heater_quartz")
        elif "halogen" in q:
            return get_feature_explanation("heater_halogen")
        elif "difference" in q or "compare" in q or "which" in q:
            return (
                get_feature_explanation("heater_ceramic", "short") + "\n\n" +
                get_feature_explanation("heater_quartz", "short") + "\n\n" +
                get_feature_explanation("heater_halogen", "short")
            )
        else:
            return get_feature_explanation("heater_ceramic")
    
    # Series comparison
    if ("c" in q and "x" in q) or "which series" in q or "difference" in q:
        return get_series_comparison()
    
    # Vacuum questions
    if "vacuum" in q:
        return get_feature_explanation("vacuum_system")
    
    # Cooling questions
    if "cooling" in q or "cool" in q:
        if "ducted" in q or "central" in q:
            return get_feature_explanation("cooling_ducted")
        else:
            return get_feature_explanation("cooling_centrifugal")
    
    # Quick change
    if "quick change" in q or "tool change" in q or "ball transfer" in q:
        return get_feature_explanation("quick_change")
    
    # Control system
    if "control" in q or "plc" in q or "hmi" in q:
        return get_feature_explanation("control_system")
    
    return None


if __name__ == "__main__":
    # Test
    print("=== AUTOLOADER ===")
    print(get_feature_explanation("autoloader"))
    print()
    
    print("=== SERIES COMPARISON ===")
    print(get_series_comparison())
    print()
    
    print("=== HEATER QUESTION ===")
    print(answer_feature_question("What's the difference between ceramic and quartz heaters?"))
