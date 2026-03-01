"""
Vera - The Fact-Checker (OpenClaw Native)

The incorruptible auditor. Skeptical, precise, and bound by truth.
She verifies every claim, checks every number, and ensures no error
or hallucination ever reaches the user.

This module provides verification functions that can be invoked by the LLM
through OpenClaw's native tool system.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.vera")


# =============================================================================
# CRITICAL BUSINESS RULES
# =============================================================================

# AM Series thickness rule - MOST IMPORTANT
AM_SERIES_MAX_THICKNESS = 1.5  # mm

# Required disclaimers
PRICING_DISCLAIMER = "subject to configuration and current pricing"
DELIVERY_DISCLAIMER = "subject to confirmation"

# Hallucination patterns to flag
HALLUCINATION_PATTERNS = [
    r"world(?:'?s)?\s+(?:leading|largest|best)",  # world's, worlds, world leading
    r"#\s*1\s+in",
    r"(?:9[89]|100)\s*%\s+(?:satisfaction|success|accuracy)",
    r"over\s+\d{3,}\s+(?:years|decades)",
    r"\d{5,}\s+(?:customers|clients|machines)",
]


# =============================================================================
# CORE VERIFICATION FUNCTIONS
# =============================================================================

async def verify(
    draft: str,
    original_query: str,
    context: Optional[Dict] = None
) -> str:
    """
    Main verification function - can be called as an OpenClaw tool.
    
    Verifies a draft response for accuracy and compliance.
    
    Args:
        draft: The draft response to verify
        original_query: The original user query
        context: Additional context
        
    Returns:
        Verified (and possibly corrected) response
    """
    context = context or {}
    
    logger.info({
        "agent": "Vera",
        "event": "verification_started",
        "draft_length": len(draft)
    })
    
    issues = []
    warnings = []
    corrections_made = []
    verified_draft = draft
    
    # Check 1: AM Series Thickness Rule (CRITICAL)
    am_check = _check_am_series_rule(draft, original_query)
    if am_check["violation"]:
        issues.append(am_check["issue"])
        if am_check["correction"]:
            verified_draft = _add_am_warning(verified_draft, original_query)
            corrections_made.append("Added AM series thickness warning")
    
    # Check 2: Pricing Disclaimer
    if _needs_pricing_disclaimer(verified_draft):
        verified_draft = _add_pricing_disclaimer(verified_draft)
        corrections_made.append("Added pricing disclaimer")
    
    # Check 3: Hallucination Detection
    hallucinations = _detect_hallucinations(verified_draft)
    if hallucinations:
        for h in hallucinations:
            issues.append(f"Potential hallucination: '{h}'")
        verified_draft = _flag_hallucinations(verified_draft, hallucinations)
    
    # Check 4: Validate Specifications
    spec_issues = _validate_specifications(verified_draft)
    issues.extend(spec_issues)
    
    # Log results
    logger.info({
        "agent": "Vera",
        "event": "verification_complete",
        "issues_found": len(issues),
        "corrections_made": len(corrections_made)
    })
    
    # If issues were found, log them
    if issues:
        logger.warning({
            "agent": "Vera",
            "event": "issues_detected",
            "issues": issues
        })
    
    return verified_draft


def _check_am_series_rule(draft: str, query: str) -> Dict[str, Any]:
    """
    Check for AM series thickness rule violation.
    
    CRITICAL RULE: AM series is ONLY for materials ≤1.5mm thick.
    """
    result = {
        "violation": False,
        "issue": None,
        "correction": None
    }
    
    # Check if query mentions thick materials (>1.5mm)
    thickness_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:mm|millimeter)', query, re.IGNORECASE)
    if thickness_match:
        thickness = float(thickness_match.group(1))
        
        # If thickness > 1.5mm and response doesn't mention AM limitation
        if thickness > AM_SERIES_MAX_THICKNESS:
            # Check if AM series is mentioned without proper warning
            if re.search(r'\bAM[-\s]?\d', draft, re.IGNORECASE):
                if "1.5mm" not in draft.lower() and "1.5 mm" not in draft.lower():
                    result["violation"] = True
                    result["issue"] = f"AM series mentioned for {thickness}mm material without thickness warning"
                    result["correction"] = "add_am_warning"
            
            # Check if ANY recommendation is made without AM warning
            if not re.search(r'AM\s+series.*(?:not|only|≤1\.5)', draft, re.IGNORECASE):
                result["violation"] = True
                result["issue"] = f"Response for {thickness}mm material missing AM series warning"
                result["correction"] = "add_am_warning"
    
    return result


def _add_am_warning(draft: str, query: str) -> str:
    """Add the AM series thickness warning to the response."""
    warning = (
        "\n\n**Note:** The AM series was not recommended as it is only suitable "
        "for materials with a thickness of 1.5mm or less."
    )
    
    # Don't add if warning already exists
    if "1.5mm" in draft.lower() or "1.5 mm" in draft.lower() or "≤1.5" in draft:
        return draft
    
    # Add warning at the end
    return draft + warning


def _needs_pricing_disclaimer(draft: str) -> bool:
    """Check if draft mentions pricing and needs disclaimer."""
    # Check for price indicators
    price_patterns = [
        r'₹\s*[\d.]+',
        r'Rs\.?\s*[\d.]+',
        r'\d+\s*(?:lakhs?|crores?)',
        r'price[d]?\s+(?:at|around|approximately)',
    ]
    
    for pattern in price_patterns:
        if re.search(pattern, draft, re.IGNORECASE):
            # Check if disclaimer already present
            if PRICING_DISCLAIMER.lower() not in draft.lower():
                return True
    
    return False


def _add_pricing_disclaimer(draft: str) -> str:
    """Add pricing disclaimer to the response."""
    # Check if disclaimer already exists
    if PRICING_DISCLAIMER.lower() in draft.lower():
        return draft
    
    # Find the price mention and add disclaimer after it
    price_pattern = r'(₹\s*[\d.]+\s*(?:lakhs?|crores?)?|Rs\.?\s*[\d.]+\s*(?:lakhs?|crores?)?|\d+\s*(?:lakhs?|crores?))'
    
    def add_disclaimer(match):
        return f"{match.group(1)} ({PRICING_DISCLAIMER})"
    
    # Only add disclaimer to first price mention
    modified = re.sub(price_pattern, add_disclaimer, draft, count=1, flags=re.IGNORECASE)
    
    if modified == draft:
        # If no price pattern matched, add general disclaimer
        modified += f"\n\n*All pricing information is {PRICING_DISCLAIMER}.*"
    
    return modified


def _detect_hallucinations(draft: str) -> List[str]:
    """Detect potential hallucinations in the response."""
    hallucinations = []
    
    for pattern in HALLUCINATION_PATTERNS:
        matches = re.findall(pattern, draft, re.IGNORECASE)
        hallucinations.extend(matches)
    
    return hallucinations


def _flag_hallucinations(draft: str, hallucinations: List[str]) -> str:
    """Flag detected hallucinations with [UNVERIFIED] tag."""
    for h in hallucinations:
        draft = draft.replace(h, f"[UNVERIFIED: {h}]")
    return draft


def _validate_specifications(draft: str) -> List[str]:
    """Validate any specifications mentioned in the draft."""
    issues = []
    
    # Check for unrealistic forming areas (should be in reasonable range)
    area_match = re.search(r'(\d{3,})\s*x\s*(\d{3,})\s*mm', draft)
    if area_match:
        width = int(area_match.group(1))
        height = int(area_match.group(2))
        
        # Reasonable range: 500-10000mm per dimension
        if width < 500 or width > 10000 or height < 500 or height > 10000:
            issues.append(f"Unusual forming area dimension: {width}x{height}mm")
    
    # Check for unrealistic thickness values
    thickness_match = re.search(r'thickness[:\s]+(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*mm', draft, re.IGNORECASE)
    if thickness_match:
        min_t = float(thickness_match.group(1))
        max_t = float(thickness_match.group(2))
        
        if min_t > max_t:
            issues.append(f"Invalid thickness range: {min_t}-{max_t}mm (min > max)")
        if max_t > 20:  # Thermoforming typically doesn't go beyond 20mm
            issues.append(f"Unusually high max thickness: {max_t}mm")
    
    return issues


# =============================================================================
# VERIFICATION REPORT
# =============================================================================

@dataclass
class VerificationReport:
    """Detailed verification report."""
    passed: bool
    confidence: float
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    corrections_made: List[str] = field(default_factory=list)
    original_draft: str = ""
    verified_draft: str = ""


def generate_verification_report(
    draft: str,
    original_query: str,
    context: Optional[Dict] = None
) -> VerificationReport:
    """
    Generate a detailed verification report.
    
    Args:
        draft: The draft to verify
        original_query: Original user query
        context: Additional context
        
    Returns:
        Detailed VerificationReport
    """
    issues = []
    warnings = []
    corrections = []
    verified_draft = draft
    
    # Run all checks
    am_check = _check_am_series_rule(draft, original_query)
    if am_check["violation"]:
        issues.append(am_check["issue"])
        verified_draft = _add_am_warning(verified_draft, original_query)
        corrections.append("Added AM series warning")
    
    if _needs_pricing_disclaimer(verified_draft):
        verified_draft = _add_pricing_disclaimer(verified_draft)
        corrections.append("Added pricing disclaimer")
    
    hallucinations = _detect_hallucinations(verified_draft)
    for h in hallucinations:
        warnings.append(f"Potential hallucination flagged: {h}")
    if hallucinations:
        verified_draft = _flag_hallucinations(verified_draft, hallucinations)
    
    spec_issues = _validate_specifications(verified_draft)
    issues.extend(spec_issues)
    
    # Calculate confidence
    confidence = 1.0
    confidence -= 0.1 * len(issues)
    confidence -= 0.05 * len(warnings)
    confidence = max(0.0, min(1.0, confidence))
    
    return VerificationReport(
        passed=len(issues) == 0,
        confidence=confidence,
        issues=issues,
        warnings=warnings,
        corrections_made=corrections,
        original_draft=draft,
        verified_draft=verified_draft
    )
