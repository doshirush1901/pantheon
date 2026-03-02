#!/usr/bin/env python3
"""
PF1 PRICING ESTIMATOR - Intelligent Quote Generation
=====================================================

Learns pricing patterns from:
1. Historical quotes in memory
2. Machine database specs
3. Option configurations

Usage:
    from pricing_estimator import PricingEstimator
    
    estimator = PricingEstimator()
    quote = estimator.estimate_price(
        forming_area=(2000, 1500),  # mm
        model_variant="X",  # C=pneumatic, X/S=servo
        options={
            "heater_type": "quartz",
            "frame_type": "universal",
            "loading": "manual",
        }
    )
"""

import os
import re
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import machine database
try:
    from .machine_database import (
        MACHINE_SPECS, MachineSpec, get_machine, 
        find_machines_by_size, get_machines_by_series
    )
except ImportError:
    from machine_database import (
        MACHINE_SPECS, MachineSpec, get_machine,
        find_machines_by_size, get_machines_by_series
    )

# =============================================================================
# PRICING CONSTANTS (learned from quotes)
# =============================================================================

# Base prices by forming area (INR) - PF1-C series (pneumatic)
BASE_PRICE_PER_SQ_METER_INR = {
    "small": 2_200_000,    # < 1 sq.m
    "medium": 1_800_000,   # 1-2 sq.m
    "large": 1_500_000,    # 2-4 sq.m
    "xlarge": 1_300_000,   # > 4 sq.m
}

# Variant multipliers (relative to PF1-C base)
VARIANT_MULTIPLIERS = {
    "C": 1.0,      # Pneumatic - base
    "A": 1.0,      # Air cylinder - same as C
    "X": 1.35,     # Servo/Pro - 35% premium
    "S": 1.35,     # Servo (same as X)
    "P": 0.85,     # Budget pneumatic
    "R": 1.15,     # With roll feeder
}

# Option pricing (INR additions)
OPTION_PRICES_INR = {
    # Frame Type
    "frame_fixed": 0,
    "frame_universal": 350_000,  # Auto XY adjustment
    
    # Sheet Loading
    "loading_manual": 0,
    "loading_roll_feeder": 450_000,
    "loading_robotic": 1_200_000,
    
    # Tool Clamping
    "clamp_bolts": 0,
    "clamp_pneumatic": 150_000,
    "clamp_auto_align": 300_000,
    
    # Tool Loading
    "tool_forklift": 0,
    "tool_ball_transfer": 120_000,
    
    # Heater Movement
    "heater_move_pneumatic": 0,
    "heater_move_servo": 250_000,
    
    # Heater Type
    "heater_ceramic": 0,
    "heater_quartz": 100_000,  # Per sq.m forming area
    "heater_halogen": 200_000,  # Per sq.m
    
    # Bottom Table
    "bottom_pneumatic": 0,
    "bottom_servo": 400_000,
    
    # Upper Table
    "upper_pneumatic": 0,
    "upper_servo": 350_000,
    
    # Heater Controller
    "controller_ssr": 0,
    "controller_heatronik": 180_000,
    
    # Cooling
    "cooling_centrifugal": 0,
    "cooling_ducted": 250_000,
    
    # Special Options
    "plug_assist": 200_000,
    "pressure_forming": 800_000,
    "twin_sheet": 1_500_000,
    "sag_control": 0,  # Included in PF1
}

# USD/INR exchange rate for international quotes
USD_INR_RATE = 83

# Margin percentages
MARGINS = {
    "domestic_india": 0.0,      # Base price
    "export_standard": 0.15,    # 15% export margin
    "export_premium": 0.25,     # 25% for complex configs
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class PriceEstimate:
    """Complete price estimate for a machine configuration."""
    model_suggested: str
    forming_area_mm: Tuple[int, int]
    forming_area_sqm: float
    variant: str
    
    # Price breakdown
    base_price_inr: int
    options_price_inr: int
    total_price_inr: int
    total_price_usd: int
    
    # Options selected
    options: Dict[str, str] = field(default_factory=dict)
    options_breakdown: Dict[str, int] = field(default_factory=dict)
    
    # Confidence & notes
    confidence: float = 0.85
    notes: List[str] = field(default_factory=list)
    comparable_models: List[str] = field(default_factory=list)
    
    # Metadata
    estimated_at: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "model": self.model_suggested,
            "forming_area": f"{self.forming_area_mm[0]} x {self.forming_area_mm[1]} mm",
            "variant": self.variant,
            "base_price_inr": self.base_price_inr,
            "options_price_inr": self.options_price_inr,
            "total_price_inr": self.total_price_inr,
            "total_price_usd": self.total_price_usd,
            "options": self.options,
            "confidence": self.confidence,
            "notes": self.notes,
        }


@dataclass
class QuoteRequest:
    """Structured quote request from customer."""
    # Required
    forming_width_mm: int
    forming_height_mm: int
    
    # Optional
    variant: str = "C"  # C, X, S, A, P, R
    max_sheet_thickness_mm: float = 8.0
    max_draw_depth_mm: int = 500
    
    # Materials
    materials: List[str] = field(default_factory=list)  # ABS, PC, PMMA, etc.
    
    # Options
    frame_type: str = "fixed"  # fixed, universal
    loading: str = "manual"  # manual, roll_feeder, robotic
    heater_type: str = "ceramic"  # ceramic, quartz, halogen
    drive_type: str = "pneumatic"  # pneumatic, servo
    
    # Special
    plug_assist: bool = False
    pressure_forming: bool = False
    twin_sheet: bool = False
    
    # Customer context
    industry: str = ""
    application: str = ""
    country: str = "India"


# =============================================================================
# PRICING ESTIMATOR
# =============================================================================

class PricingEstimator:
    """
    Intelligent pricing estimator for PF1 machines.
    
    Combines:
    1. Machine database lookup
    2. Option pricing rules
    3. Learned patterns from historical quotes
    """
    
    def __init__(self):
        self.learned_patterns: Dict[str, Any] = {}
        self._load_learned_patterns()
    
    def _load_learned_patterns(self):
        """Load learned pricing patterns from memory."""
        # TODO: Load from Qdrant/memory system
        pass
    
    def estimate_price(
        self,
        forming_area: Tuple[int, int],
        variant: str = "C",
        options: Dict[str, str] = None,
        country: str = "India",
        **kwargs
    ) -> PriceEstimate:
        """
        Estimate price for a machine configuration.
        
        Args:
            forming_area: (width_mm, height_mm)
            variant: C (pneumatic), X/S (servo), A (air), P (budget), R (roll)
            options: Dict of option selections
            country: For export margin calculation
            
        Returns:
            PriceEstimate with full breakdown
        """
        options = options or {}
        width_mm, height_mm = forming_area
        sqm = (width_mm * height_mm) / 1_000_000
        
        # 1. Find closest standard model
        model_suggested = self._suggest_model(width_mm, height_mm, variant)
        
        # 2. Calculate base price
        base_price = self._calculate_base_price(width_mm, height_mm, variant)
        
        # 3. Calculate options price
        options_price, options_breakdown = self._calculate_options_price(
            sqm, options, variant
        )
        
        # 4. Apply export margin if needed
        margin = 0.0
        if country.lower() != "india":
            margin = MARGINS["export_standard"]
            if options.get("loading") == "robotic" or variant in ["X", "S"]:
                margin = MARGINS["export_premium"]
        
        subtotal = base_price + options_price
        total_inr = int(subtotal * (1 + margin))
        total_usd = total_inr // USD_INR_RATE
        
        # 5. Build estimate
        estimate = PriceEstimate(
            model_suggested=model_suggested,
            forming_area_mm=forming_area,
            forming_area_sqm=round(sqm, 2),
            variant=variant.upper(),
            base_price_inr=base_price,
            options_price_inr=options_price,
            total_price_inr=total_inr,
            total_price_usd=total_usd,
            options=options,
            options_breakdown=options_breakdown,
            confidence=self._calculate_confidence(forming_area, variant),
            notes=self._generate_notes(forming_area, variant, options, margin),
            comparable_models=self._find_comparable_models(width_mm, height_mm),
            estimated_at=datetime.now().isoformat(),
        )
        
        return estimate
    
    def _suggest_model(self, width_mm: int, height_mm: int, variant: str) -> str:
        """Suggest the closest standard model name."""
        # Convert to cm for model naming
        w_cm = width_mm // 10
        h_cm = height_mm // 10
        
        # Standard sizes (in cm, smaller dimension first)
        standard_sizes = [
            (80, 60), (100, 80), (120, 80), (120, 120),
            (130, 90), (150, 100), (180, 120), (200, 100),
            (200, 150), (200, 200), (250, 150), (250, 200),
            (300, 150), (300, 200), (350, 200), (350, 250),
            (400, 250), (500, 280),
        ]
        
        # Find closest
        best_match = None
        min_diff = float('inf')
        
        for sw, sh in standard_sizes:
            # Check both orientations
            diff1 = abs(w_cm - sw) + abs(h_cm - sh)
            diff2 = abs(w_cm - sh) + abs(h_cm - sw)
            diff = min(diff1, diff2)
            
            if diff < min_diff:
                min_diff = diff
                if diff1 <= diff2:
                    best_match = (max(sw, sh), min(sw, sh))
                else:
                    best_match = (max(sw, sh), min(sw, sh))
        
        if best_match:
            # Format: PF1-{variant}-{width}{height} (e.g., PF1-C-2015 for 2000x1500mm)
            w, h = best_match
            # Use single digits for <1000, double for >=1000 (e.g., 20 for 2000, 15 for 1500)
            w_str = str(w // 10) if w >= 100 else str(w)
            h_str = str(h // 10) if h >= 100 else str(h)
            return f"PF1-{variant.upper()}-{w_str}{h_str}"
        
        # Custom size - format like standard models
        w_str = str(w_cm // 10) if w_cm >= 100 else str(w_cm)
        h_str = str(h_cm // 10) if h_cm >= 100 else str(h_cm)
        return f"PF1-{variant.upper()}-{w_str}{h_str} (custom)"
    
    def _calculate_base_price(self, width_mm: int, height_mm: int, variant: str) -> int:
        """Calculate base machine price."""
        sqm = (width_mm * height_mm) / 1_000_000
        
        # Get price per sqm based on size category
        if sqm < 1:
            price_per_sqm = BASE_PRICE_PER_SQ_METER_INR["small"]
        elif sqm < 2:
            price_per_sqm = BASE_PRICE_PER_SQ_METER_INR["medium"]
        elif sqm < 4:
            price_per_sqm = BASE_PRICE_PER_SQ_METER_INR["large"]
        else:
            price_per_sqm = BASE_PRICE_PER_SQ_METER_INR["xlarge"]
        
        # Calculate raw base price
        base = int(sqm * price_per_sqm)
        
        # Apply minimum price
        min_price = 3_000_000  # 30 lakh minimum
        base = max(base, min_price)
        
        # Apply variant multiplier
        multiplier = VARIANT_MULTIPLIERS.get(variant.upper(), 1.0)
        
        return int(base * multiplier)
    
    def _calculate_options_price(
        self, 
        sqm: float, 
        options: Dict[str, str],
        variant: str
    ) -> Tuple[int, Dict[str, int]]:
        """Calculate total options price with breakdown."""
        total = 0
        breakdown = {}
        
        # Frame type
        frame = options.get("frame_type", "fixed")
        if frame == "universal":
            price = OPTION_PRICES_INR["frame_universal"]
            breakdown["Universal Frames"] = price
            total += price
        
        # Loading
        loading = options.get("loading", "manual")
        if loading == "roll_feeder":
            price = OPTION_PRICES_INR["loading_roll_feeder"]
            breakdown["Roll Feeder"] = price
            total += price
        elif loading == "robotic":
            price = OPTION_PRICES_INR["loading_robotic"]
            breakdown["Robotic Autoloader"] = price
            total += price
        
        # Clamping
        clamp = options.get("clamping", "bolts")
        if clamp == "pneumatic":
            price = OPTION_PRICES_INR["clamp_pneumatic"]
            breakdown["Pneumatic Clamps"] = price
            total += price
        elif clamp == "auto_align":
            price = OPTION_PRICES_INR["clamp_auto_align"]
            breakdown["Auto-Align Clamps"] = price
            total += price
        
        # Tool loading
        tool = options.get("tool_loading", "forklift")
        if tool == "ball_transfer":
            price = OPTION_PRICES_INR["tool_ball_transfer"]
            breakdown["Ball Transfer Units"] = price
            total += price
        
        # Heater type (price scales with area)
        heater = options.get("heater_type", "ceramic")
        if heater == "quartz":
            price = int(OPTION_PRICES_INR["heater_quartz"] * sqm)
            breakdown["IR Quartz Heaters"] = price
            total += price
        elif heater == "halogen":
            price = int(OPTION_PRICES_INR["heater_halogen"] * sqm)
            breakdown["IR Halogen Heaters"] = price
            total += price
        
        # Drive systems (if not already servo variant)
        if variant.upper() not in ["X", "S"]:
            if options.get("heater_drive") == "servo":
                price = OPTION_PRICES_INR["heater_move_servo"]
                breakdown["Servo Heater Drive"] = price
                total += price
            
            if options.get("bottom_drive") == "servo":
                price = OPTION_PRICES_INR["bottom_servo"]
                breakdown["Servo Bottom Table"] = price
                total += price
            
            if options.get("upper_drive") == "servo":
                price = OPTION_PRICES_INR["upper_servo"]
                breakdown["Servo Upper Table"] = price
                total += price
        
        # Controller
        if options.get("controller") == "heatronik":
            price = OPTION_PRICES_INR["controller_heatronik"]
            breakdown["Heatronik Controller"] = price
            total += price
        
        # Cooling
        if options.get("cooling") == "ducted":
            price = OPTION_PRICES_INR["cooling_ducted"]
            breakdown["Ducted Cooling"] = price
            total += price
        
        # Special options
        if options.get("plug_assist"):
            price = OPTION_PRICES_INR["plug_assist"]
            breakdown["Plug Assist System"] = price
            total += price
        
        if options.get("pressure_forming"):
            price = OPTION_PRICES_INR["pressure_forming"]
            breakdown["Pressure Forming"] = price
            total += price
        
        if options.get("twin_sheet"):
            price = OPTION_PRICES_INR["twin_sheet"]
            breakdown["Twin Sheet Capability"] = price
            total += price
        
        return total, breakdown
    
    def _calculate_confidence(self, forming_area: Tuple[int, int], variant: str) -> float:
        """Calculate confidence level based on how standard the config is."""
        width, height = forming_area
        
        # Check if it's a standard size
        standard_sizes = [
            (1000, 800), (1200, 800), (1500, 1000), (1800, 1200),
            (2000, 1000), (2000, 1500), (2000, 2000), (2500, 1500),
            (3000, 1500), (3000, 2000), (3500, 2000), (3500, 2500),
        ]
        
        is_standard = any(
            (width == w and height == h) or (width == h and height == w)
            for w, h in standard_sizes
        )
        
        if is_standard and variant in ["C", "X", "S"]:
            return 0.95
        elif is_standard:
            return 0.90
        else:
            return 0.80
    
    def _generate_notes(
        self, 
        forming_area: Tuple[int, int], 
        variant: str,
        options: Dict[str, str],
        margin: float
    ) -> List[str]:
        """Generate helpful notes for the estimate."""
        notes = []
        width, height = forming_area
        sqm = (width * height) / 1_000_000
        
        # Size notes
        if sqm > 4:
            notes.append("Large format machine - consider split shipment")
        
        # Variant notes
        if variant.upper() in ["X", "S"]:
            notes.append("Servo variant includes all-servo drives (heater, upper, lower tables)")
        
        # Option recommendations
        if options.get("loading") == "manual" and sqm > 2:
            notes.append("Consider robotic loading for large format - improves cycle time")
        
        if options.get("heater_type") != "quartz":
            notes.append("IR Quartz heaters recommended for energy savings (most popular)")
        
        if options.get("frame_type") != "universal" and sqm > 1.5:
            notes.append("Universal frames recommended for flexibility with multiple products")
        
        # Export notes
        if margin > 0:
            notes.append(f"Export pricing includes {int(margin*100)}% margin")
        
        return notes
    
    def _find_comparable_models(self, width_mm: int, height_mm: int) -> List[str]:
        """Find comparable models from database."""
        comparable = []
        
        for model, spec in MACHINE_SPECS.items():
            if not spec.forming_area_raw:
                continue
            
            sw, sh = spec.forming_area_raw
            # Within 20% of requested size
            w_match = 0.8 <= sw / width_mm <= 1.2
            h_match = 0.8 <= sh / height_mm <= 1.2
            
            if w_match and h_match:
                comparable.append(model)
        
        return comparable[:5]  # Top 5
    
    def estimate_from_request(self, request: QuoteRequest) -> PriceEstimate:
        """Estimate price from a structured quote request."""
        # Determine variant from drive type if not specified
        variant = request.variant
        if request.drive_type == "servo" and variant == "C":
            variant = "X"
        
        # Build options dict
        options = {
            "frame_type": request.frame_type,
            "loading": request.loading,
            "heater_type": request.heater_type,
            "plug_assist": request.plug_assist,
            "pressure_forming": request.pressure_forming,
            "twin_sheet": request.twin_sheet,
        }
        
        return self.estimate_price(
            forming_area=(request.forming_width_mm, request.forming_height_mm),
            variant=variant,
            options=options,
            country=request.country,
        )
    
    def format_quote(self, estimate: PriceEstimate, currency: str = "INR") -> str:
        """Format estimate as a readable quote."""
        lines = []
        lines.append("=" * 60)
        lines.append("MACHINECRAFT PF1 PRICE ESTIMATE")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Machine Model:    {estimate.model_suggested}")
        lines.append(f"Forming Area:     {estimate.forming_area_mm[0]} x {estimate.forming_area_mm[1]} mm")
        lines.append(f"                  ({estimate.forming_area_sqm} sq.m)")
        lines.append(f"Variant:          PF1-{estimate.variant}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("PRICING BREAKDOWN")
        lines.append("-" * 60)
        lines.append(f"Base Machine:     ₹{estimate.base_price_inr:,}")
        
        if estimate.options_breakdown:
            lines.append("")
            lines.append("Options:")
            for opt_name, opt_price in estimate.options_breakdown.items():
                lines.append(f"  + {opt_name:25} ₹{opt_price:,}")
            lines.append(f"  {'─' * 35}")
            lines.append(f"  Options Subtotal:           ₹{estimate.options_price_inr:,}")
        
        lines.append("")
        lines.append("-" * 60)
        
        if currency.upper() == "USD":
            lines.append(f"TOTAL PRICE:      ${estimate.total_price_usd:,} USD")
            lines.append(f"                  (₹{estimate.total_price_inr:,} INR)")
        else:
            lines.append(f"TOTAL PRICE:      ₹{estimate.total_price_inr:,} INR")
            lines.append(f"                  (${estimate.total_price_usd:,} USD)")
        
        lines.append("-" * 60)
        lines.append(f"Estimate Confidence: {estimate.confidence*100:.0f}%")
        
        if estimate.notes:
            lines.append("")
            lines.append("Notes:")
            for note in estimate.notes:
                lines.append(f"  • {note}")
        
        if estimate.comparable_models:
            lines.append("")
            lines.append(f"Comparable Models: {', '.join(estimate.comparable_models[:3])}")
        
        lines.append("")
        lines.append("=" * 60)
        lines.append("This is an estimate. Final quote subject to detailed requirements.")
        lines.append("=" * 60)
        
        return "\n".join(lines)


# =============================================================================
# QUICK LOOKUP FUNCTIONS
# =============================================================================

def quick_estimate(width_mm: int, height_mm: int, variant: str = "C") -> str:
    """Quick price estimate for a size."""
    estimator = PricingEstimator()
    estimate = estimator.estimate_price(
        forming_area=(width_mm, height_mm),
        variant=variant,
    )
    return estimator.format_quote(estimate)


def compare_variants(width_mm: int, height_mm: int) -> str:
    """Compare C vs X variant pricing."""
    estimator = PricingEstimator()
    
    est_c = estimator.estimate_price(
        forming_area=(width_mm, height_mm),
        variant="C",
    )
    
    est_x = estimator.estimate_price(
        forming_area=(width_mm, height_mm),
        variant="X",
    )
    
    lines = [
        f"Comparison: {width_mm}x{height_mm}mm",
        "=" * 50,
        f"PF1-C (Pneumatic):  ₹{est_c.total_price_inr:,}  (${est_c.total_price_usd:,})",
        f"PF1-X (Servo):      ₹{est_x.total_price_inr:,}  (${est_x.total_price_usd:,})",
        f"Servo Premium:      ₹{est_x.total_price_inr - est_c.total_price_inr:,} (+{((est_x.total_price_inr/est_c.total_price_inr)-1)*100:.0f}%)",
    ]
    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 60)
    print("PF1 PRICING ESTIMATOR")
    print("=" * 60)
    
    # Example estimates
    print("\n--- Example 1: PF1-C-2015 ---")
    print(quick_estimate(2000, 1500, "C"))
    
    print("\n--- Example 2: PF1-X-3020 with options ---")
    estimator = PricingEstimator()
    estimate = estimator.estimate_price(
        forming_area=(3000, 2000),
        variant="X",
        options={
            "frame_type": "universal",
            "loading": "robotic",
            "heater_type": "quartz",
            "clamping": "auto_align",
            "tool_loading": "ball_transfer",
            "controller": "heatronik",
            "cooling": "ducted",
        },
        country="USA",
    )
    print(estimator.format_quote(estimate, "USD"))
    
    print("\n--- Variant Comparison: 2000x1500mm ---")
    print(compare_variants(2000, 1500))
