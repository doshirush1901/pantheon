"""
Centralized Regex Patterns for Ira
===================================

Single source of truth for all machine model, price, and entity patterns
used across the codebase. Import from here to ensure consistency.

Usage:
    from common.patterns import (
        extract_machine_models,
        extract_prices,
        MACHINE_PATTERNS,
        PRICE_PATTERNS,
    )
    
    machines = extract_machine_models("Looking for PF1-C-3020 price")
    prices = extract_prices("Price is ₹65,00,000 or USD 78,000")
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# =============================================================================
# MACHINE MODEL PATTERNS
# =============================================================================

MACHINE_PATTERNS: Dict[str, re.Pattern] = {
    # PF1/PF2 Series - Vacuum Forming Machines
    # Matches: PF1-C-3020, PF1C3020, PF1-X-2520, PF2-3000x2000
    "pf1": re.compile(
        r'\bPF[-\s]?[12][-\s]?([XCSPRA])[-\s]?(\d{2,4})(?:[xX](\d{2,4}))?\b',
        re.IGNORECASE
    ),
    
    # ATF Series - Automatic Thermoforming
    # Matches: ATF-1218, ATF1218, ATF-1515
    "atf": re.compile(
        r'\bATF[-\s]?(\d{3,4})\b',
        re.IGNORECASE
    ),
    
    # IMG Series - In-Mold Grain
    # Matches: IMG-1350, IMG1350
    "img": re.compile(
        r'\bIMG[-\s]?(\d{3,4})\b',
        re.IGNORECASE
    ),
    
    # AM Series - AM Machines
    # Matches: AM-V-5060, AM-M-4050, AM-P-5060
    "am": re.compile(
        r'\bAM[-\s]?([MVP])[-\s]?(\d{4})\b',
        re.IGNORECASE
    ),
    
    # FCS Series - FCS Machines
    # Matches: FCS-6070, FCS6070
    "fcs": re.compile(
        r'\bFCS[-\s]?(\d{4})\b',
        re.IGNORECASE
    ),
    
    # RT Series - Rotational Machines
    # Matches: RT-5A-3020, RT-3-2015
    "rt": re.compile(
        r'\bRT[-\s]?(\d+[A-Z]?)[-\s]?(\d{4})\b',
        re.IGNORECASE
    ),
    
    # UNO/DUO Series
    # Matches: UNO-1515, DUO-2020
    "uno_duo": re.compile(
        r'\b(UNO|DUO)[-\s]?(\d{4})\b',
        re.IGNORECASE
    ),
}

# Simplified patterns for quick matching (any machine mention)
MACHINE_QUICK_PATTERNS: List[re.Pattern] = [
    re.compile(r'\bPF[-\s]?[12][-\s]?[XCSPRA]?[-\s]?\d*', re.IGNORECASE),
    re.compile(r'\bAM[-\s]?[MVP][-\s]?\d*', re.IGNORECASE),
    re.compile(r'\bFCS[-\s]?\d+', re.IGNORECASE),
    re.compile(r'\bATF[-\s]?\d+', re.IGNORECASE),
    re.compile(r'\bIMG[-\s]?\d+', re.IGNORECASE),
    re.compile(r'\bRT[-\s]?\d+[A-Z]?[-\s]?\d*', re.IGNORECASE),
    re.compile(r'\b(UNO|DUO)[-\s]?\d+', re.IGNORECASE),
]


# =============================================================================
# PRICE PATTERNS
# =============================================================================

@dataclass
class ExtractedPrice:
    """Extracted price with currency info."""
    amount: float
    currency: str  # INR, USD, EUR
    original: str  # Original matched string
    amount_inr: float  # Normalized to INR


# Currency conversion rates (for normalization)
# Note: These should be updated periodically or fetched from config
USD_TO_INR = 83.0
EUR_TO_INR = 90.0

PRICE_PATTERNS: List[re.Pattern] = [
    # Symbol prefix: $1,234.56, €1,234, ₹65,00,000
    re.compile(r'([\$€₹])\s*([\d,]+(?:\.\d{1,2})?)', re.IGNORECASE),
    
    # Currency suffix: 1,234 USD, 1234 EUR, 65,00,000 INR
    re.compile(r'([\d,]+(?:\.\d{1,2})?)\s*(USD|EUR|INR|Rs\.?)', re.IGNORECASE),
    
    # Indian style with lakhs/crores: 65 lakh, 1.5 crore
    re.compile(r'([\d.]+)\s*(lakh|lac|crore|cr)\b', re.IGNORECASE),
    
    # Plain large numbers likely to be prices (Indian format: 65,00,000)
    re.compile(r'\b(\d{1,2},\d{2},\d{3})\b'),  # Indian: 65,00,000
    re.compile(r'\b(\d{1,3}(?:,\d{3}){2,})\b'),  # Western: 6,500,000
]


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

def extract_machine_models(text: str) -> List[str]:
    """
    Extract all machine model references from text.
    
    Returns normalized model names (e.g., "PF1-C-3020").
    
    Args:
        text: Text to search
    
    Returns:
        List of unique machine model strings
    """
    machines = []
    seen = set()
    
    for pattern in MACHINE_QUICK_PATTERNS:
        for match in pattern.finditer(text):
            # Normalize: uppercase, standardize hyphens
            model = match.group(0).upper()
            model = re.sub(r'[\s]+', '-', model)  # Spaces to hyphens
            model = re.sub(r'-+', '-', model)  # Multiple hyphens to one
            
            if model not in seen:
                seen.add(model)
                machines.append(model)
    
    return machines


def extract_machine_details(text: str) -> List[Dict]:
    """
    Extract machine models with detailed parsing.
    
    Returns structured info including series, variant, and size.
    
    Args:
        text: Text to search
    
    Returns:
        List of dicts with model details
    """
    results = []
    
    # PF1/PF2 series
    for match in MACHINE_PATTERNS["pf1"].finditer(text):
        variant = match.group(1).upper() if match.group(1) else ""
        size = match.group(2)
        height = match.group(3) if match.lastindex >= 3 and match.group(3) else None
        
        model = f"PF1-{variant}-{size}" if variant else f"PF1-{size}"
        if height:
            model += f"x{height}"
        
        results.append({
            "model": model,
            "series": "PF1",
            "variant": variant,
            "size": size,
            "forming_area": f"{size[:2]}00 x {size[2:]}00 mm" if len(size) == 4 else None,
        })
    
    # ATF series
    for match in MACHINE_PATTERNS["atf"].finditer(text):
        size = match.group(1)
        results.append({
            "model": f"ATF-{size}",
            "series": "ATF",
            "size": size,
        })
    
    # IMG series
    for match in MACHINE_PATTERNS["img"].finditer(text):
        size = match.group(1)
        results.append({
            "model": f"IMG-{size}",
            "series": "IMG",
            "size": size,
        })
    
    # AM series
    for match in MACHINE_PATTERNS["am"].finditer(text):
        variant = match.group(1).upper()
        size = match.group(2)
        results.append({
            "model": f"AM-{variant}-{size}",
            "series": "AM",
            "variant": variant,
            "size": size,
        })
    
    return results


def extract_prices(text: str) -> List[ExtractedPrice]:
    """
    Extract all prices from text with currency detection.
    
    Args:
        text: Text to search
    
    Returns:
        List of ExtractedPrice objects
    """
    prices = []
    
    # Symbol prefix patterns
    for match in re.finditer(r'([\$€₹])\s*([\d,]+(?:\.\d{1,2})?)', text):
        symbol = match.group(1)
        amount_str = match.group(2).replace(',', '')
        
        try:
            amount = float(amount_str)
        except ValueError:
            continue
        
        if symbol == '$':
            currency = 'USD'
            amount_inr = amount * USD_TO_INR
        elif symbol == '€':
            currency = 'EUR'
            amount_inr = amount * EUR_TO_INR
        else:
            currency = 'INR'
            amount_inr = amount
        
        prices.append(ExtractedPrice(
            amount=amount,
            currency=currency,
            original=match.group(0),
            amount_inr=amount_inr
        ))
    
    # Currency suffix patterns
    for match in re.finditer(r'([\d,]+(?:\.\d{1,2})?)\s*(USD|EUR|INR|Rs\.?)', text, re.IGNORECASE):
        amount_str = match.group(1).replace(',', '')
        currency = match.group(2).upper()
        
        if currency.startswith('RS'):
            currency = 'INR'
        
        try:
            amount = float(amount_str)
        except ValueError:
            continue
        
        if currency == 'USD':
            amount_inr = amount * USD_TO_INR
        elif currency == 'EUR':
            amount_inr = amount * EUR_TO_INR
        else:
            amount_inr = amount
        
        prices.append(ExtractedPrice(
            amount=amount,
            currency=currency,
            original=match.group(0),
            amount_inr=amount_inr
        ))
    
    # Lakh/Crore patterns
    for match in re.finditer(r'([\d.]+)\s*(lakh|lac|crore|cr)\b', text, re.IGNORECASE):
        amount_str = match.group(1)
        unit = match.group(2).lower()
        
        try:
            amount = float(amount_str)
        except ValueError:
            continue
        
        if unit in ('lakh', 'lac'):
            amount_inr = amount * 100000
        else:  # crore
            amount_inr = amount * 10000000
        
        prices.append(ExtractedPrice(
            amount=amount_inr,
            currency='INR',
            original=match.group(0),
            amount_inr=amount_inr
        ))
    
    return prices


def has_price_info(text: str) -> bool:
    """Quick check if text contains any price information."""
    quick_pattern = re.compile(
        r'[\$€₹]\s*[\d,]+|'
        r'[\d,]+\s*(?:USD|EUR|INR|Rs)|'
        r'\d+\s*(?:lakh|lac|crore)',
        re.IGNORECASE
    )
    return bool(quick_pattern.search(text))


def normalize_model_name(model: str) -> str:
    """
    Normalize a machine model name to canonical format.
    
    Examples:
        "PF1 C 3020" -> "PF1-C-3020"
        "pf1c3020" -> "PF1-C-3020"
        "ATF1218" -> "ATF-1218"
    """
    model = model.upper().strip()
    
    # PF1/PF2 normalization
    pf_match = re.match(r'PF[-\s]?([12])[-\s]?([XCSPRA])[-\s]?(\d{4})', model)
    if pf_match:
        return f"PF{pf_match.group(1)}-{pf_match.group(2)}-{pf_match.group(3)}"
    
    # Simple model normalization (ATF, IMG, etc.)
    simple_match = re.match(r'(ATF|IMG|FCS|AM|RT)[-\s]?(.+)', model)
    if simple_match:
        return f"{simple_match.group(1)}-{simple_match.group(2)}"
    
    return model


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Patterns
    "MACHINE_PATTERNS",
    "MACHINE_QUICK_PATTERNS",
    "PRICE_PATTERNS",
    
    # Functions
    "extract_machine_models",
    "extract_machine_details",
    "extract_prices",
    "has_price_info",
    "normalize_model_name",
    
    # Data classes
    "ExtractedPrice",
    
    # Constants
    "USD_TO_INR",
    "EUR_TO_INR",
]
