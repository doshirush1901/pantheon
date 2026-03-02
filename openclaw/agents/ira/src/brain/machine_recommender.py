#!/usr/bin/env python3
"""
MACHINE RECOMMENDER
===================

Intelligent machine recommendation based on customer requirements.
Uses the structured MACHINE_SPECS database as the SOURCE OF TRUTH.

This replaces the RAG-only approach for machine recommendations,
ensuring accurate, verifiable suggestions.

Usage:
    from machine_recommender import recommend_machines, MachineRecommendation
    
    recommendations = recommend_machines(
        min_width=1000,
        min_height=2000,
        material_thickness=4.0,
        budget_preference="low",
    )
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# Import machine database
try:
    from .machine_database import (
        MACHINE_SPECS, MachineSpec, get_machine,
        find_machines_by_size, get_machines_by_series,
        normalize_model_alias
    )
    MACHINE_DB_AVAILABLE = True
except ImportError:
    try:
        from machine_database import (
            MACHINE_SPECS, MachineSpec, get_machine,
            find_machines_by_size, get_machines_by_series,
            normalize_model_alias
        )
        MACHINE_DB_AVAILABLE = True
    except ImportError:
        MACHINE_DB_AVAILABLE = False
        logger.warning("Machine database not available")


@dataclass
class MachineRecommendation:
    """A single machine recommendation with reasoning."""
    model: str
    series: str
    forming_area: str
    forming_area_raw: Tuple[int, int]
    price_inr: int
    price_usd: Optional[int] = None
    
    # Match quality
    fit_score: float = 0.0  # 0-1, higher = better fit
    excess_area_mm: int = 0  # How much larger than needed
    
    # Why this machine
    match_reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Full specs for response
    max_sheet_thickness: float = 0
    heater_power_kw: float = 0
    vacuum_pump: str = ""
    features: List[str] = field(default_factory=list)
    applications: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "model": self.model,
            "series": self.series,
            "forming_area": self.forming_area,
            "price_inr": self.price_inr,
            "price_usd": self.price_usd,
            "fit_score": self.fit_score,
            "match_reasons": self.match_reasons,
            "warnings": self.warnings,
            "max_sheet_thickness": self.max_sheet_thickness,
            "heater_power_kw": self.heater_power_kw,
        }


@dataclass
class RecommendationResult:
    """Complete recommendation result with context."""
    query_understood: Dict[str, Any]
    recommendations: List[MachineRecommendation]
    best_match: Optional[MachineRecommendation] = None
    alternative_matches: List[MachineRecommendation] = field(default_factory=list)
    
    # For response generation
    formatted_response: str = ""
    confidence: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "query_understood": self.query_understood,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "best_match": self.best_match.to_dict() if self.best_match else None,
            "confidence": self.confidence,
        }


def parse_dimensions_from_text(text: str) -> Optional[Tuple[int, int]]:
    """
    Extract dimensions from natural language text.
    
    Handles formats like:
    - "1x2m", "1 x 2 m", "1m x 2m"
    - "1000x2000mm", "1000 x 2000 mm"
    - "1000mm x 2000mm"
    - "size 1 by 2 meters"
    
    Returns (width_mm, height_mm) or None if not found.
    """
    patterns = [
        # Meters: 1x2m, 1 x 2 m, 1m x 2m
        r'(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*m(?:eter)?s?\b',
        r'(\d+(?:\.\d+)?)\s*m\s*[xX×]\s*(\d+(?:\.\d+)?)\s*m(?:eter)?s?\b',
        # Millimeters: 1000x2000mm, 1000 x 2000 mm
        r'(\d{3,4})\s*[xX×]\s*(\d{3,4})\s*mm\b',
        r'(\d{3,4})\s*mm\s*[xX×]\s*(\d{3,4})\s*mm\b',
        # Natural language: size 1 by 2 meters
        r'size\s*(\d+(?:\.\d+)?)\s*(?:by|x)\s*(\d+(?:\.\d+)?)\s*m(?:eter)?s?',
        # Just numbers with x: 1x2 (assume meters if small, mm if large)
        r'\b(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\b',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val1 = float(match.group(1))
            val2 = float(match.group(2))
            
            # Determine if meters or millimeters
            if val1 < 10 and val2 < 10:
                # Likely meters, convert to mm
                width_mm = int(val1 * 1000)
                height_mm = int(val2 * 1000)
            else:
                # Already in mm
                width_mm = int(val1)
                height_mm = int(val2)
            
            return (width_mm, height_mm)
    
    return None


def parse_thickness_from_text(text: str) -> Optional[float]:
    """
    Extract material thickness from text.
    
    Handles: "4mm ABS", "4 mm thick", "thickness 4mm", "4mm sheet"
    """
    patterns = [
        r'(\d+(?:\.\d+)?)\s*mm\s*(?:ABS|HIPS|PP|PE|PET|PETG|PVC|PC|PMMA|HDPE|thick)',
        r'(?:thickness|sheet)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*mm',
        r'(\d+(?:\.\d+)?)\s*mm\s*(?:sheet|material|thick)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    
    return None


def parse_budget_preference(text: str) -> str:
    """
    Detect budget preference from text.
    
    Returns: "low", "medium", "high", or "any"
    """
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["low budget", "cheap", "affordable", "budget", "cost-effective", "economical", "startup"]):
        return "low"
    if any(word in text_lower for word in ["premium", "high-end", "best quality", "top", "no budget"]):
        return "high"
    if any(word in text_lower for word in ["mid-range", "moderate", "reasonable"]):
        return "medium"
    
    return "any"


def parse_budget_amount(text: str) -> Optional[int]:
    """
    Extract budget amount from text and convert to INR.
    
    Handles formats like:
    - "$60,000 USD", "$60K USD", "USD 60,000"
    - "€200,000", "EUR 200K"
    - "₹50 lakh", "₹5 Cr", "INR 10000000"
    - "budget of 60000 dollars"
    
    Returns amount in INR (rounded).
    """
    text_lower = text.lower()
    
    # Exchange rates (approximate)
    USD_TO_INR = 83
    EUR_TO_INR = 90
    GBP_TO_INR = 105
    
    # USD patterns
    usd_patterns = [
        r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:k|K)\s*(?:USD|usd)?',  # $60K USD
        r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:USD|usd)?',  # $60,000 USD
        r'USD\s*([\d,]+(?:\.\d+)?)\s*(?:k|K)?',  # USD 60K
        r'([\d,]+(?:\.\d+)?)\s*(?:k|K)?\s*(?:USD|usd|dollars?)',  # 60K USD / 60000 dollars
        r'budget\s*(?:of\s*)?\$?\s*([\d,]+(?:\.\d+)?)\s*(?:k|K)?',  # budget of 60000
    ]
    
    for pattern in usd_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            amount = float(amount_str)
            
            # Check if it's in K (thousands)
            if 'k' in text_lower[match.start():match.end()].lower() or amount < 1000:
                amount *= 1000
            
            return int(amount * USD_TO_INR)
    
    # EUR patterns
    eur_patterns = [
        r'€\s*([\d,]+(?:\.\d+)?)\s*(?:k|K)?',  # €200K
        r'EUR\s*([\d,]+(?:\.\d+)?)\s*(?:k|K)?',  # EUR 200000
        r'([\d,]+(?:\.\d+)?)\s*(?:k|K)?\s*(?:EUR|euros?)',  # 200K EUR
    ]
    
    for pattern in eur_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            amount = float(amount_str)
            
            if 'k' in text_lower[match.start():match.end()].lower() or amount < 1000:
                amount *= 1000
            
            return int(amount * EUR_TO_INR)
    
    # INR patterns
    inr_patterns = [
        r'₹\s*([\d,]+(?:\.\d+)?)\s*(?:lakh|lac|L)\b',  # ₹50 lakh
        r'₹\s*([\d,]+(?:\.\d+)?)\s*(?:crore|cr)\b',  # ₹1 Cr
        r'₹\s*([\d,]+(?:\.\d+)?)',  # ₹5000000
        r'INR\s*([\d,]+(?:\.\d+)?)\s*(?:lakh|lac|L|crore|cr)?',  # INR 50 lakh
        r'([\d,]+(?:\.\d+)?)\s*(?:lakh|lac)\b',  # 50 lakh
        r'([\d,]+(?:\.\d+)?)\s*(?:crore|cr)\b',  # 1 crore
    ]
    
    for pattern in inr_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            amount = float(amount_str)
            
            matched_text = text_lower[match.start():match.end()]
            if 'crore' in matched_text or 'cr' in matched_text:
                amount *= 10000000  # 1 crore = 10 million
            elif 'lakh' in matched_text or 'lac' in matched_text or 'l' in matched_text:
                amount *= 100000  # 1 lakh = 100,000
            
            return int(amount)
    
    return None


def recommend_machines(
    min_width: int = 0,
    min_height: int = 0,
    material_thickness: Optional[float] = None,
    budget_preference: str = "any",
    max_price_inr: Optional[int] = None,
    material_type: Optional[str] = None,
    series_preference: Optional[str] = None,
    exclude_series: Optional[List[str]] = None,
) -> RecommendationResult:
    """
    Recommend machines based on customer requirements.
    
    Args:
        min_width: Minimum forming width in mm
        min_height: Minimum forming height in mm
        material_thickness: Required sheet thickness in mm
        budget_preference: "low", "medium", "high", or "any"
        max_price_inr: Maximum budget in INR
        material_type: Material type (ABS, HIPS, PP, etc.)
        series_preference: Preferred series (PF1, AM, etc.)
        exclude_series: Series to exclude (e.g., AM for thick materials)
    
    Returns:
        RecommendationResult with ranked recommendations
    """
    if not MACHINE_DB_AVAILABLE:
        logger.error("Machine database not available")
        return RecommendationResult(
            query_understood={"error": "Machine database not available"},
            recommendations=[],
            confidence=0.0,
        )
    
    query_understood = {
        "min_width_mm": min_width,
        "min_height_mm": min_height,
        "material_thickness_mm": material_thickness,
        "budget_preference": budget_preference,
        "max_price_inr": max_price_inr,
        "material_type": material_type,
    }
    
    # Get machines that fit the size requirement
    candidates = find_machines_by_size(min_width, min_height, max_price_inr)
    
    if not candidates:
        logger.warning(f"No machines found for size {min_width}x{min_height}mm")
        return RecommendationResult(
            query_understood=query_understood,
            recommendations=[],
            confidence=0.0,
            formatted_response=f"No machines found for forming area {min_width}x{min_height}mm.",
        )
    
    # Filter and score candidates
    recommendations = []
    
    for machine in candidates:
        rec = _score_machine(
            machine=machine,
            min_width=min_width,
            min_height=min_height,
            material_thickness=material_thickness,
            budget_preference=budget_preference,
            material_type=material_type,
            exclude_series=exclude_series or [],
            max_price_inr=max_price_inr,
        )
        
        if rec:
            recommendations.append(rec)
    
    # Sort by fit score (higher = better), then by price (lower = better)
    recommendations.sort(key=lambda r: (-r.fit_score, r.price_inr or 999999999))
    
    # Determine best match and alternatives
    best_match = recommendations[0] if recommendations else None
    alternatives = recommendations[1:4] if len(recommendations) > 1 else []
    
    # Calculate confidence
    confidence = 0.0
    if best_match:
        confidence = best_match.fit_score
        if best_match.warnings:
            confidence -= 0.1 * len(best_match.warnings)
        confidence = max(0.0, min(1.0, confidence))
    
    # Format response
    formatted = _format_recommendation_response(
        best_match=best_match,
        alternatives=alternatives,
        query_understood=query_understood,
    )
    
    return RecommendationResult(
        query_understood=query_understood,
        recommendations=recommendations,
        best_match=best_match,
        alternative_matches=alternatives,
        formatted_response=formatted,
        confidence=confidence,
    )


def _score_machine(
    machine: MachineSpec,
    min_width: int,
    min_height: int,
    material_thickness: Optional[float],
    budget_preference: str,
    material_type: Optional[str],
    exclude_series: List[str],
    max_price_inr: Optional[int] = None,
) -> Optional[MachineRecommendation]:
    """Score a machine against requirements."""
    
    # Check exclusions
    if machine.series in exclude_series:
        return None
    
    # AM series can't handle thick materials (>1.5mm per AGENTS.md rule)
    if machine.series == "AM" and material_thickness and material_thickness > 1.5:
        return None
    
    # Calculate fit
    w, h = machine.forming_area_raw if machine.forming_area_raw else (0, 0)
    
    # Check if it fits (allowing rotation)
    fits_normal = w >= min_width and h >= min_height
    fits_rotated = w >= min_height and h >= min_width
    
    if not (fits_normal or fits_rotated):
        return None
    
    # Calculate excess area
    if fits_normal:
        excess = (w - min_width) + (h - min_height)
    else:
        excess = (w - min_height) + (h - min_width)
    
    # Check material thickness compatibility
    thickness_ok = True
    if material_thickness:
        max_thick = machine.max_sheet_thickness_mm or 10
        thickness_ok = max_thick >= material_thickness
    
    if not thickness_ok:
        return None
    
    # Build recommendation
    rec = MachineRecommendation(
        model=machine.model,
        series=machine.series,
        forming_area=machine.forming_area_mm,
        forming_area_raw=machine.forming_area_raw,
        price_inr=machine.price_inr or 0,
        price_usd=machine.price_usd,
        excess_area_mm=excess,
        max_sheet_thickness=machine.max_sheet_thickness_mm or 0,
        heater_power_kw=machine.heater_power_kw or 0,
        vacuum_pump=machine.vacuum_pump_capacity or "",
        features=machine.features or [],
        applications=machine.applications or [],
    )
    
    # Calculate fit score (0-1)
    score = 1.0
    
    # Perfect size match bonus
    if excess == 0:
        score += 0.2
        rec.match_reasons.append("Exact size match")
    elif excess < 500:
        score += 0.1
        rec.match_reasons.append("Close size match")
    else:
        # Penalize oversized machines
        score -= min(0.3, excess / 5000)
        if excess > 1000:
            rec.match_reasons.append(f"Larger than needed (+{excess}mm)")
    
    # Material thickness compatibility
    if material_thickness:
        if machine.max_sheet_thickness_mm and machine.max_sheet_thickness_mm >= material_thickness:
            rec.match_reasons.append(f"Handles {material_thickness}mm material")
        else:
            rec.warnings.append("Material thickness compatibility unverified")
    
    # Budget scoring with explicit max price
    price = machine.price_inr or 0
    
    if max_price_inr:
        # Strong penalty for over-budget machines
        if price > max_price_inr:
            overage_pct = (price - max_price_inr) / max_price_inr
            score -= 0.4 + (overage_pct * 0.2)  # Heavy penalty for exceeding budget
            rec.warnings.append(f"⚠️ Over budget by ₹{price - max_price_inr:,} ({overage_pct*100:.0f}%)")
        elif price <= max_price_inr * 0.8:  # Under 80% of budget
            score += 0.15
            rec.match_reasons.append(f"Within budget (₹{price:,})")
        else:  # 80-100% of budget
            score += 0.05
            rec.match_reasons.append("Fits budget")
    
    if budget_preference == "low":
        # Prefer cheaper machines
        if price <= 4000000:
            score += 0.15
            rec.match_reasons.append("Budget-friendly (entry-level)")
        elif price <= 6000000:
            score += 0.05
        else:
            score -= 0.1
            rec.warnings.append("Higher price point")
    elif budget_preference == "high":
        # Prefer premium machines (servo, more features)
        if machine.variant and "servo" in machine.variant.lower():
            score += 0.15
            rec.match_reasons.append("Premium servo-driven")
    
    # Series-specific adjustments
    if machine.series == "PF1":
        variant = (machine.variant or "").lower()
        if "x" in variant or "servo" in variant:
            rec.match_reasons.append("All-servo drives for precision")
        elif "c" in variant or "pneumatic" in variant:
            rec.match_reasons.append("Pneumatic - cost-effective")
    
    rec.fit_score = max(0.0, min(1.0, score))
    
    return rec


def _format_recommendation_response(
    best_match: Optional[MachineRecommendation],
    alternatives: List[MachineRecommendation],
    query_understood: Dict,
) -> str:
    """Format a human-readable recommendation response."""
    
    if not best_match:
        return "I couldn't find a suitable machine for your requirements. Please provide more details."
    
    lines = []
    
    # Best recommendation
    lines.append(f"**Recommended Machine: {best_match.model}**")
    lines.append("")
    lines.append(f"**Forming Area:** {best_match.forming_area}")
    lines.append(f"**Price:** ₹{best_match.price_inr:,}" + (f" (~${best_match.price_usd:,})" if best_match.price_usd else ""))
    
    if best_match.max_sheet_thickness:
        lines.append(f"**Max Sheet Thickness:** {best_match.max_sheet_thickness}mm")
    if best_match.heater_power_kw:
        lines.append(f"**Heater Power:** {best_match.heater_power_kw} kW")
    if best_match.vacuum_pump:
        lines.append(f"**Vacuum Pump:** {best_match.vacuum_pump}")
    
    # Why this machine
    if best_match.match_reasons:
        lines.append("")
        lines.append("**Why this machine:**")
        for reason in best_match.match_reasons[:4]:
            lines.append(f"- {reason}")
    
    # Warnings
    if best_match.warnings:
        lines.append("")
        for warning in best_match.warnings:
            lines.append(f"⚠️ {warning}")
    
    # Alternatives
    if alternatives:
        lines.append("")
        lines.append("**Alternatives:**")
        for alt in alternatives[:2]:
            price_str = f"₹{alt.price_inr:,}" if alt.price_inr else "Contact for price"
            lines.append(f"- {alt.model} ({alt.forming_area}) - {price_str}")
    
    return "\n".join(lines)


def recommend_from_query(query: str, nlu_result: Optional[Any] = None) -> RecommendationResult:
    """
    Main entry point: recommend machines from a natural language query.
    
    Args:
        query: The user's question
        nlu_result: Optional NLU result with pre-extracted entities
    
    Returns:
        RecommendationResult with best machine recommendations
    """
    # Extract dimensions
    dimensions = None
    if nlu_result:
        # Try to get dimensions from NLU result
        try:
            dims = nlu_result.get_dimensions()
            if dims:
                dimensions = dims[0]  # (width, height)
        except (AttributeError, IndexError):
            pass
    
    if not dimensions:
        dimensions = parse_dimensions_from_text(query)
    
    if not dimensions:
        logger.warning(f"Could not extract dimensions from query: {query}")
        return RecommendationResult(
            query_understood={"error": "Could not extract size requirements"},
            recommendations=[],
            confidence=0.0,
            formatted_response="Please specify the part size you need (e.g., '1m x 2m' or '1000mm x 2000mm').",
        )
    
    min_width, min_height = dimensions
    
    # Extract material thickness
    material_thickness = None
    if nlu_result:
        try:
            thicknesses = nlu_result.get_thicknesses()
            if thicknesses:
                material_thickness = thicknesses[0]
        except (AttributeError, IndexError):
            pass
    
    if not material_thickness:
        material_thickness = parse_thickness_from_text(query)
    
    # Detect budget preference and amount
    budget_preference = parse_budget_preference(query)
    max_price_inr = parse_budget_amount(query)
    
    # If explicit budget given, make preference low/medium based on amount
    # Add 10% tolerance to budget (customer saying $60K should match $60K machine)
    if max_price_inr:
        max_price_inr = int(max_price_inr * 1.10)  # 10% tolerance
        if max_price_inr < 5500000:  # < 55L INR (~$66K)
            budget_preference = "low"
        elif max_price_inr < 15000000:  # < 1.5Cr INR
            budget_preference = "medium"
    
    # Detect material type
    material_type = None
    material_patterns = [
        r'\b(ABS|HIPS|PP|PE|PET|PETG|PVC|PC|PMMA|HDPE|LDPE|TPO)\b',
    ]
    for pattern in material_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            material_type = match.group(1).upper()
            break
    
    # Exclude AM series for thick materials
    exclude_series = []
    if material_thickness and material_thickness > 1.5:
        exclude_series.append("AM")
    
    logger.info(
        f"Machine recommendation: size={min_width}x{min_height}mm, "
        f"thickness={material_thickness}mm, budget={budget_preference}, "
        f"max_price_inr={max_price_inr}, material={material_type}"
    )
    
    return recommend_machines(
        min_width=min_width,
        min_height=min_height,
        material_thickness=material_thickness,
        budget_preference=budget_preference,
        max_price_inr=max_price_inr,
        material_type=material_type,
        exclude_series=exclude_series,
    )


# =============================================================================
# CLI Testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="Test machine recommender")
    parser.add_argument("query", nargs="?", default="which machine for 4mm ABS, 1x2m size, low budget")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    result = recommend_from_query(args.query)
    
    if args.json:
        import json
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"Query: {args.query}")
        print(f"{'='*60}")
        print(f"\nUnderstood:")
        for k, v in result.query_understood.items():
            if v:
                print(f"  {k}: {v}")
        print(f"\nConfidence: {result.confidence:.2f}")
        print(f"\n{result.formatted_response}")
