#!/usr/bin/env python3
"""
DETAILED TECH SPECS GENERATOR
==============================

Generates comprehensive technical specifications for PF1-X machines
based on the Machinecraft PF1 Thermoformer Configurator Design document.

Usage:
    from detailed_specs_generator import generate_detailed_specs
    specs = generate_detailed_specs("PF1-X-1520")
"""

from typing import Optional
from machine_database import MACHINE_SPECS, get_machine


def normalize_model_name(model: str) -> str:
    """Normalize model names for external communication."""
    if model.startswith("PF1-A-"):
        return model.replace("PF1-A-", "PF1-C-")
    if model.startswith("PF1-S-"):
        return model.replace("PF1-S-", "PF1-X-")
    return model

# Comprehensive spec templates based on Configurator Design document
PF1_X_DETAILED_SPECS = {
    "forming_system": {
        "title": "Forming System",
        "specs": [
            "Closed-chamber vacuum forming with full enclosure",
            "Preblow bubble capability for male tools",
            "Sheet sag control with sensor feedback",
            "Multi-stage vacuum application (programmable 30%, 60%, 100%)",
            "Servo-controlled vacuum valve for precise forming"
        ]
    },
    "frame_system": {
        "title": "Frame & Sheet Clamping",
        "specs": [
            "Servo-driven universal aperture frames (X-Y motorized adjustment)",
            "Quick frame changeover: <5 minutes via touchscreen vs 1-2 hours manual",
            "Automatic sheet centering with 2 servo motors",
            "Robust steel/aluminum construction"
        ]
    },
    "sheet_loading": {
        "title": "Automatic Sheet Loading System",
        "specs": [
            "Pallet-based sheet stack input",
            "Vacuum suction cup pick-up with servo-driven gantry",
            "Pneumatic air-blow sheet separator (single-sheet detection)",
            "Dual sensor redundancy (double-pick protection)",
            "Simultaneous part unloading during loading",
            "Cycle time: 15-30 seconds load/unload vs 2-4 minutes manual"
        ]
    },
    "heater_system": {
        "title": "Heating System",
        "variants": {
            "ceramic": {
                "type": "IR Ceramic Heaters (Long-Wave)",
                "response_time": "30-60 seconds to operating temp",
                "pros": ["Rugged and long-lasting", "Wide material acceptance", "Lower cost"],
                "cons": ["Slower response time", "Higher energy in idle"],
                "best_for": "General-purpose, thick gauge sheets, budget-conscious"
            },
            "quartz": {
                "type": "IR Quartz Heaters (Medium-Wave)", 
                "response_time": "10-15 seconds to operating temp",
                "pros": ["Faster response than ceramic", "~25% energy savings", "Better zone control"],
                "cons": ["Slightly shorter lifespan", "More fragile"],
                "best_for": "Technical thermoforming, mid-thickness materials (3-6mm)"
            },
            "halogen": {
                "type": "IR Halogen Heaters (Short-Wave)",
                "response_time": "2-3 seconds to operating temp",
                "pros": ["Ultra-fast heating", "Up to 50% energy savings (on/off capability)", "Highest precision"],
                "cons": ["Highest cost", "Requires Heatronik controller", "Not for PMMA/PC/PET"],
                "best_for": "High-speed production, thin-wall parts, energy-conscious operations"
            }
        },
        "zones": "Independently controlled top and bottom heaters with programmable zone-wise heating"
    },
    "heater_control": {
        "title": "Heater Control Options",
        "standard": {
            "name": "SSR Control (Standard)",
            "description": "Solid State Relay control with PLC and PID loops per zone",
            "features": ["Zone-wise power control", "Thermocouple/pyrometer feedback", "Reliable and proven"]
        },
        "advanced": {
            "name": "Heatronik Controller (Advanced)",
            "description": "Closed-loop control with automatic fault detection",
            "features": ["Auto-detects failed heaters", "Soft start for halogen", "Compact panel design", "REQUIRED for halogen heaters"]
        }
    },
    "motion_system": {
        "title": "Machine Motion (All-Servo)",
        "specs": [
            "Servo-driven clamp frame (X-Y axes)",
            "Servo-driven lower platen (Z-axis) for smooth mold rise/descent",
            "Servo-driven plug assist (optional) for deep draw support",
            "Programmable acceleration/deceleration profiles",
            "Precision positioning with encoder feedback",
            "Benefits: Faster cycles, quieter operation, precise repeatability"
        ]
    },
    "tool_change": {
        "title": "Quick Tool Change System",
        "specs": [
            "Ball transfer units on lower platen for easy tool sliding",
            "Pneumatic lift cylinders (10-15mm lift) for zero-effort positioning",
            "Tool change time: <10 minutes by single operator vs 30-60 minutes with forklift",
            "Quick pneumatic clamping (optional) vs manual bolting",
            "Vacuum locking for rapid tool securing"
        ]
    },
    "cooling_system": {
        "title": "Cooling System",
        "options": {
            "centrifugal": {
                "name": "Centrifugal Fan Cooling (Standard)",
                "description": "Multiple fans directed at mold face with adjustable louvers",
                "pros": ["Simple and modular", "Easy maintenance", "Included in base price"]
            },
            "ducted": {
                "name": "Central Ducted Cooling (Optional)",
                "description": "High-capacity blower with ductwork for uniform airflow",
                "pros": ["Higher airflow and pressure", "Faster cooling", "More uniform temperature"],
                "benefits": "Reduces cooling time by 20-40%"
            }
        }
    },
    "vacuum_system": {
        "title": "Vacuum System",
        "specs": [
            "Oil-lubricated rotary vane vacuum pump (Busch/Becker)",
            "High-capacity vacuum tank (600-4000L depending on size)",
            "Rapid evacuation for fast cycle times",
            "Preblow system for male tool forming",
            "Air ejection for clean part release"
        ],
        "optional": "Proportional vacuum valve for multi-stage vacuum control"
    },
    "control_system": {
        "title": "Control System",
        "specs": [
            "Mitsubishi PLC (Japan) - high-speed logic control",
            "Mitsubishi servo drives for all motion axes",
            "10.1\" industrial touchscreen HMI (upgradeable to 15\")",
            "Multi-level password protection (Operator/Engineer/Manager)",
            "Recipe storage on SD card with real-time visualization",
            "Alarm history, diagnostic logs, maintenance prompts"
        ],
        "brands": {
            "PLC & Servos": "Mitsubishi Electric (Japan)",
            "Pneumatics": "Festo / SMC",
            "Sensors": "Keyence / Sick / P+F", 
            "Vacuum Pumps": "Busch / Becker",
            "Heaters": "Elstein / TQS / Ceramicx",
            "Switchgear": "Eaton / Siemens"
        }
    },
    "safety": {
        "title": "Safety Features",
        "specs": [
            "Full perimeter safety guards with interlocked doors",
            "Light curtains in sheet loading area (Sick/Keyence)",
            "2-level safety on upper platen (mechanical + electronic)",
            "Emergency stops at operator station and control panel",
            "Safety PLC for controlled stops",
            "CE compliance standard"
        ]
    },
    "electrical": {
        "title": "Electrical System",
        "specs": [
            "Rittal/Hoffman-style enclosed, ventilated control cabinet",
            "Labeled, segregated wiring for easy fault tracing",
            "Solid State Relays (SSRs) for heater zones",
            "PID logic for precise thermal control",
            "Load visualization via ammeter/voltmeter per zone"
        ]
    }
}


def generate_detailed_specs(model: str, include_all: bool = True) -> str:
    """
    Generate comprehensive technical specifications for a PF1-X machine.
    
    Args:
        model: Machine model (e.g., "PF1-X-1520")
        include_all: Include all spec sections
    
    Returns:
        Formatted technical specification string
    """
    # Get base machine specs
    machine = get_machine(model)
    if not machine:
        # Try normalized name
        for m in MACHINE_SPECS.keys():
            if normalize_model_name(m) == model or m == model:
                machine = MACHINE_SPECS[m]
                break
    
    if not machine:
        return f"Machine {model} not found in database."
    
    # Determine if it's an X series (all-servo with autoloader)
    is_x_series = "-X-" in model or "-XL-" in model or machine.variant and "servo" in machine.variant.lower()
    
    lines = []
    lines.append(f"**{normalize_model_name(model)} - Detailed Technical Specifications**")
    lines.append("")
    
    # Basic specs from database
    lines.append("**1. Machine Overview**")
    lines.append(f"• Model: {normalize_model_name(model)}")
    lines.append(f"• Series: {machine.series} ({'All-Servo with Autoloader' if is_x_series else 'Pneumatic'})")
    lines.append(f"• Maximum Forming Area: {machine.forming_area_mm} mm")
    if machine.max_tool_height_mm:
        lines.append(f"• Maximum Tool Height: {machine.max_tool_height_mm} mm")
    if machine.max_draw_depth_mm:
        lines.append(f"• Maximum Draw Depth: {machine.max_draw_depth_mm} mm")
    if machine.max_sheet_thickness_mm:
        lines.append(f"• Sheet Thickness Range: {machine.min_sheet_thickness_mm or 1}-{machine.max_sheet_thickness_mm} mm")
    lines.append("")
    
    # Heating system
    lines.append("**2. Heating System**")
    lines.append(f"• Heater Power: {machine.heater_power_kw} kW")
    if machine.total_power_kw:
        lines.append(f"• Total Connected Power: {machine.total_power_kw} kW")
    lines.append(f"• Heater Type: {machine.heater_type or 'IR Ceramic/Quartz (configurable)'}")
    if machine.num_heaters:
        lines.append(f"• Number of Heater Banks: {machine.num_heaters} (top and bottom)")
    if machine.heater_zones:
        lines.append(f"• Heater Zones: {machine.heater_zones} independently controlled zones")
    lines.append("• Zone-wise temperature control with programmable profiles")
    lines.append("• Sag control with optional sensor feedback")
    lines.append("")
    
    # Vacuum system
    lines.append("**3. Vacuum System**")
    lines.append(f"• Vacuum Pump: Oil-lubricated rotary vane ({machine.vacuum_pump_capacity})")
    if machine.vacuum_tank_size:
        lines.append(f"• Vacuum Tank: {machine.vacuum_tank_size}")
    lines.append("• Brands: Busch, Becker, or equivalent")
    lines.append("• Features: Rapid evacuation, preblow for male tools, air ejection")
    lines.append("• Optional: Servo-controlled proportional valve for multi-stage vacuum")
    lines.append("")
    
    # Motion system (differs for X vs C series)
    lines.append("**4. Motion System**")
    if is_x_series:
        lines.append("• Drive Type: All-Servo (Mitsubishi servo motors)")
        lines.append("• Clamp Frame: Servo-driven X-Y positioning")
        lines.append("• Lower Platen: Servo-driven Z-axis with smooth acceleration")
        lines.append("• Benefits: Faster cycles, quieter operation, programmable profiles")
    else:
        lines.append("• Drive Type: Pneumatic (air cylinder driven)")
        lines.append("• Clamp Frame: Pneumatic actuation")
        lines.append("• Lower Platen: Pneumatic with cushioned stops")
    lines.append("")
    
    # Sheet loading
    lines.append("**5. Sheet Loading System**")
    if is_x_series:
        lines.append("• Type: Automatic Sheet Loader (standard on X series)")
        lines.append("• Mechanism: Servo-driven pick & place with vacuum suction cups")
        lines.append("• Sheet Separation: Pneumatic air-blow + mechanical dancing frame")
        lines.append("• Safety: Dual sensors for double-pick protection")
        lines.append("• Part Unloading: Simultaneous with loading (pneumatic pusher)")
        lines.append("• Cycle Time: 15-30 seconds vs 2-4 minutes manual")
    else:
        lines.append("• Type: Manual sheet loading")
        lines.append("• Optional: Automatic loader available as upgrade")
    lines.append("")
    
    # Frame system
    lines.append("**6. Frame & Clamping System**")
    if is_x_series:
        lines.append("• Frame Type: Servo-driven universal aperture (motorized X-Y adjustment)")
        lines.append("• Changeover Time: <5 minutes via touchscreen")
    else:
        lines.append("• Frame Type: Fixed window frames (manual adjustment)")
        lines.append("• Changeover Time: 1-2 hours with manual swap")
    lines.append("• Construction: Robust steel/aluminum")
    lines.append("")
    
    # Tool change
    lines.append("**7. Tool Change System**")
    lines.append("• Ball transfer units on lower platen for easy tool sliding")
    lines.append("• Pneumatic lift cylinders for zero-effort positioning")
    lines.append("• Tool change time: <10 minutes by single operator")
    lines.append("• Clamping: Manual bolting (standard) or pneumatic quick-clamps (optional)")
    lines.append("")
    
    # Cooling
    lines.append("**8. Cooling System**")
    lines.append("• Standard: Centrifugal fans with adjustable louvers")
    lines.append("• Optional: Central ducted cooling (high-flow blower)")
    lines.append("• Water mist spray available for rapid cooling")
    lines.append("")
    
    # Control system
    lines.append("**9. Control System**")
    lines.append("• PLC: Mitsubishi Electric (Japan)")
    lines.append("• HMI: 10.1\" industrial touchscreen (upgradeable to 15\")")
    lines.append("• Servo Drives: Mitsubishi for all motion axes")
    lines.append("• Features: Recipe storage, alarm history, diagnostic logs")
    lines.append("• Remote Monitoring: Optional IIoT connectivity")
    lines.append("")
    
    # Electrical
    lines.append("**10. Electrical Specifications**")
    lines.append(f"• Power Supply: {machine.power_supply or '415V, 50Hz, 3P+N+PE'}")
    lines.append("• Control Cabinet: Rittal/Hoffman enclosed, ventilated")
    lines.append("• Heater Control: SSR with PID (standard) or Heatronik (optional)")
    lines.append("")
    
    # Safety
    lines.append("**11. Safety Features**")
    lines.append("• Full perimeter guards with interlocked doors")
    lines.append("• Light curtains in loading area (Sick/Keyence)")
    lines.append("• 2-level safety on upper platen")
    lines.append("• Emergency stops at multiple locations")
    lines.append("• CE compliant")
    lines.append("")
    
    # Pricing
    lines.append("**12. Pricing**")
    if machine.price_usd:
        lines.append(f"• Price: ${machine.price_usd:,} USD")
    elif machine.price_inr:
        lines.append(f"• Price: ₹{machine.price_inr:,} (~${machine.price_inr // 83:,} USD)")
    lines.append("• Includes: Base machine with standard features")
    lines.append("• Optional upgrades quoted separately")
    lines.append("")
    
    # Applications
    if machine.applications:
        lines.append("**13. Typical Applications**")
        for app in machine.applications[:5]:
            lines.append(f"• {app}")
        lines.append("")
    
    # Features
    if machine.features:
        lines.append("**14. Key Features**")
        for feat in machine.features[:6]:
            lines.append(f"• {feat}")
    
    return "\n".join(lines)


def get_spec_comparison(model1: str, model2: str) -> str:
    """Generate side-by-side comparison of two machines."""
    m1 = get_machine(model1)
    m2 = get_machine(model2)
    
    if not m1 or not m2:
        return "One or both machines not found."
    
    lines = [
        f"**Comparison: {model1} vs {model2}**",
        "",
        f"| Specification | {model1} | {model2} |",
        "|--------------|----------|----------|",
        f"| Forming Area | {m1.forming_area_mm} | {m2.forming_area_mm} |",
        f"| Tool Height | {m1.max_tool_height_mm}mm | {m2.max_tool_height_mm}mm |",
        f"| Heater Power | {m1.heater_power_kw}kW | {m2.heater_power_kw}kW |",
        f"| Vacuum | {m1.vacuum_pump_capacity} | {m2.vacuum_pump_capacity} |",
    ]
    
    if m1.price_usd and m2.price_usd:
        lines.append(f"| Price (USD) | ${m1.price_usd:,} | ${m2.price_usd:,} |")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test
    print(generate_detailed_specs("PF1-X-1520"))
