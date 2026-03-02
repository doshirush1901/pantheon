#!/usr/bin/env python3
"""
SALES QUALIFICATION CHECKER
===========================

Checks if a customer inquiry has enough information to make a machine recommendation.
If not, generates appropriate qualifying questions.

This follows Rushabh's sales approach:
1. NEVER recommend a machine without knowing:
   - Forming area required
   - Material type
   - Sheet thickness
   - Application/industry
   - Budget (optional but helpful)

2. If any essential info is missing, ASK FIRST, don't guess.

Usage:
    from sales_qualifier import qualify_inquiry, QualificationResult
    
    result = qualify_inquiry("We need a vacuum forming machine")
    if not result.is_qualified:
        return result.qualifying_questions
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set
from enum import Enum


class RequiredInfo(Enum):
    """Essential information needed for machine recommendation."""
    FORMING_AREA = "forming_area"
    MATERIAL = "material"
    THICKNESS = "thickness"
    APPLICATION = "application"
    BUDGET = "budget"  # Nice to have, not required


@dataclass
class QualificationResult:
    """Result of qualifying an inquiry."""
    is_qualified: bool
    missing_info: List[RequiredInfo]
    extracted_info: Dict[str, str]
    qualifying_questions: List[str]
    qualification_score: float  # 0.0 to 1.0
    
    @property
    def should_ask_questions(self) -> bool:
        """Returns True if IRA should ask questions before recommending."""
        # Ask if missing critical info (forming area OR material OR thickness)
        critical_missing = {RequiredInfo.FORMING_AREA, RequiredInfo.MATERIAL, RequiredInfo.THICKNESS}
        return bool(critical_missing & set(self.missing_info))


# =============================================================================
# EXTRACTION PATTERNS
# =============================================================================

# Forming area patterns (e.g., "800 x 1000 mm", "1000x1500", "2000 x 2000")
FORMING_AREA_PATTERNS = [
    r'(\d{3,4})\s*[xX×]\s*(\d{3,4})\s*(?:mm)?',  # 800 x 1000 mm
    r'forming\s+area[:\s]+(\d{3,4})\s*[xX×]\s*(\d{3,4})',
    r'size[:\s]+(\d{3,4})\s*[xX×]\s*(\d{3,4})',
    r'(\d{3,4})mm\s*[xX×]\s*(\d{3,4})mm',
]

# Material patterns
MATERIAL_PATTERNS = [
    r'\b(ABS|PC|PMMA|HIPS|PP|PE|TPO|HDPE|LDPE|PET|PETG|PS|PVC|acrylic|kydex|polycarbonate|polypropylene)\b',
]

# Thickness patterns (e.g., "up to 6mm", "6mm thick", "thickness: 8mm")
THICKNESS_PATTERNS = [
    r'(?:up\s*to\s*)?(\d+(?:\.\d+)?)\s*mm\s*(?:thick|thickness)?',
    r'thickness[:\s]+(?:up\s*to\s*)?(\d+(?:\.\d+)?)\s*mm',
    r'(\d+(?:\.\d+)?)\s*mm\s+sheet',
]

# Application/industry patterns
APPLICATION_PATTERNS = [
    r'\b(automotive|aerospace|packaging|sanitary|luggage|telecom|medical|refrigerat|signage|enclosure|panel)\w*\b',
]

# IMG (In-Mold Graining) process indicators - requires IMG series machine
IMG_PROCESS_PATTERNS = [
    r'\bIMG\b',                           # Explicit IMG mention
    r'in[-\s]?mold[-\s]?grain',           # In-mold graining
    r'grain\s*retention',                  # Grain retention requirement
    r'TPO\s*(?:form|sheet|material)',     # TPO forming (typically IMG)
    r'class[-\s]?A\s*surface',            # Class-A surface finish
    r'interior.*(?:grain|texture)',        # Interior with grain/texture
    r'(?:grain|texture).*interior',        # grain/texture for interior
]

# Impossible/unrealistic request patterns
# These combinations are red flags that need expectation management
IMPOSSIBLE_REQUEST_INDICATORS = {
    'budget_too_low_for_size': {
        'large_size': r'(?:2500|3000|3500|4000)\s*[xX×]\s*(?:2000|2500|3000|3500|4000)',
        'low_budget': r'(?:20|25|30)\s*(?:lakh|lac)',  # <30 lakh for large format
    },
    'unrealistic_delivery': {
        'patterns': [r'(?:1|2|3|4)\s*weeks?', r'immediate', r'urgent.*(?:1|2)\s*weeks?', r'this\s*week'],
    },
    'extreme_thickness': {
        'patterns': [r'(?:12|13|14|15|16|17|18|19|20)\s*mm\s*(?:thick|sheet)'],
    },
}

# Budget patterns
BUDGET_PATTERNS = [
    r'budget[:\s]+(?:(?:Rs\.?|₹|INR|USD|\$|€)\s*)?(\d[\d,\.]*)\s*(?:lakh|lac|cr|crore|k|K|lakhs)?',
    r'(\d[\d,\.]*)\s*(?:lakh|lac|cr|crore)\s*(?:budget|rupee|inr)?',
    r'(?:USD|\$)\s*(\d[\d,\.]*)\s*(?:k|K|thousand|million)?',
]


# =============================================================================
# QUALIFYING QUESTIONS
# =============================================================================

QUALIFYING_QUESTIONS = {
    RequiredInfo.FORMING_AREA: [
        "What forming area do you require? (e.g., 800 x 1000 mm, 1500 x 2000 mm)",
        "What is the maximum part size you'll be forming?",
    ],
    RequiredInfo.MATERIAL: [
        "What materials will you be forming? (e.g., ABS, PMMA, PC, HIPS)",
        "What type of plastic sheets will you be processing?",
    ],
    RequiredInfo.THICKNESS: [
        "What is the maximum sheet thickness you'll be working with?",
        "What thickness range do you need? (e.g., up to 6mm, up to 10mm)",
    ],
    RequiredInfo.APPLICATION: [
        "What industry/application is this for?",
        "What type of products will you be manufacturing?",
    ],
    RequiredInfo.BUDGET: [
        "Do you have a target budget in mind?",
    ],
}


# =============================================================================
# MAIN QUALIFICATION LOGIC
# =============================================================================

def qualify_inquiry(query: str) -> QualificationResult:
    """
    Check if an inquiry has enough information for machine recommendation.
    
    Args:
        query: Customer's inquiry text
        
    Returns:
        QualificationResult with extracted info and any missing requirements
    """
    query_lower = query.lower()
    extracted = {}
    present_info: Set[RequiredInfo] = set()
    
    # Check for forming area
    for pattern in FORMING_AREA_PATTERNS:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            extracted['forming_area'] = f"{match.group(1)} x {match.group(2)} mm"
            present_info.add(RequiredInfo.FORMING_AREA)
            break
    
    # Check for material
    for pattern in MATERIAL_PATTERNS:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            extracted['material'] = match.group(1).upper()
            present_info.add(RequiredInfo.MATERIAL)
            break
    
    # Check for thickness
    for pattern in THICKNESS_PATTERNS:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            extracted['thickness'] = f"{match.group(1)}mm"
            present_info.add(RequiredInfo.THICKNESS)
            break
    
    # Check for application/industry
    for pattern in APPLICATION_PATTERNS:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            extracted['application'] = match.group(1).capitalize()
            present_info.add(RequiredInfo.APPLICATION)
            break
    
    # Check for budget
    for pattern in BUDGET_PATTERNS:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            extracted['budget'] = match.group(1)
            present_info.add(RequiredInfo.BUDGET)
            break
    
    # Determine what's missing
    # Required: forming_area, material, thickness
    # Optional: application, budget
    required = {RequiredInfo.FORMING_AREA, RequiredInfo.MATERIAL, RequiredInfo.THICKNESS}
    missing = list(required - present_info)
    
    # Add application if missing (helpful but not blocking)
    if RequiredInfo.APPLICATION not in present_info:
        missing.append(RequiredInfo.APPLICATION)
    
    # Calculate qualification score
    required_present = len(required & present_info)
    total_required = len(required)
    score = required_present / total_required if total_required > 0 else 0.0
    
    # Generate qualifying questions for missing info
    questions = []
    for info in missing[:3]:  # Max 3 questions
        qs = QUALIFYING_QUESTIONS.get(info, [])
        if qs:
            questions.append(qs[0])
    
    is_qualified = score >= 0.66  # At least 2 of 3 required fields
    
    return QualificationResult(
        is_qualified=is_qualified,
        missing_info=missing,
        extracted_info=extracted,
        qualifying_questions=questions,
        qualification_score=score,
    )


def is_vague_inquiry(query: str) -> bool:
    """
    Quick check if query is too vague for machine recommendation.
    
    Examples of vague queries:
    - "We need a vacuum forming machine"
    - "Looking for thermoforming equipment"
    - "Please share machine details"
    
    Examples of specific queries:
    - "Need machine for 1000x1500mm ABS sheets up to 6mm"
    - "What's the price for PF1-C-2015?"
    """
    query_lower = query.lower()
    
    # If asking about a specific model, not vague
    specific_models = ['pf1-c', 'pf1-x', 'pf2-', 'uno-', 'duo-', 'atf-', 'fcs-', 'am-', 'img-']
    if any(m in query_lower for m in specific_models):
        return False
    
    # Check if has at least one concrete spec
    result = qualify_inquiry(query)
    
    # Vague if no required info present
    return result.qualification_score < 0.33


def is_specific_model_query(query: str) -> bool:
    """Check if query is about a specific machine model."""
    query_lower = query.lower()
    specific_models = ['pf1-c-', 'pf1-x-', 'pf2-p', 'uno-', 'duo-', 'atf-', 'fcs-', 'am-', 'img-']
    return any(m in query_lower for m in specific_models)


def detect_img_requirement(query: str) -> bool:
    """
    Detect if the query requires IMG (In-Mold Graining) series machine.
    
    IMG series is needed for:
    - TPO forming with grain retention
    - Class-A surface finish requirements
    - Automotive interior components with texture
    
    Returns True if IMG series should be recommended instead of PF1/PF2.
    """
    query_lower = query.lower()
    
    for pattern in IMG_PROCESS_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return True
    
    # Also check for TPO + automotive combination
    if 'tpo' in query_lower and 'automotive' in query_lower:
        return True
    
    # Check for grain + interior combination
    if ('grain' in query_lower or 'texture' in query_lower) and 'interior' in query_lower:
        return True
    
    return False


@dataclass
class ImpossibleRequestResult:
    """Result of checking for impossible/unrealistic requests."""
    is_impossible: bool
    reasons: List[str]
    suggestions: List[str]
    
    
def detect_impossible_request(query: str) -> ImpossibleRequestResult:
    """
    Detect if the request has unrealistic/impossible combinations.
    
    Examples:
    - 3000x3000mm forming area with 25 lakh budget (too low)
    - Delivery in 4 weeks (standard is 12-16 weeks)
    - 15mm sheet thickness (max is typically 10mm)
    
    Returns suggestions for managing expectations.
    """
    query_lower = query.lower()
    reasons = []
    suggestions = []
    
    # Check for unrealistic delivery times
    for pattern in IMPOSSIBLE_REQUEST_INDICATORS['unrealistic_delivery']['patterns']:
        if re.search(pattern, query_lower, re.IGNORECASE):
            reasons.append("Delivery time requested is unrealistic")
            suggestions.append("Standard lead time is 12-16 weeks from order confirmation. We can discuss expedited options, but immediate delivery is not possible for custom manufacturing.")
            break
    
    # Check for extreme thickness
    for pattern in IMPOSSIBLE_REQUEST_INDICATORS['extreme_thickness']['patterns']:
        if re.search(pattern, query_lower, re.IGNORECASE):
            reasons.append("Sheet thickness exceeds standard machine capabilities")
            suggestions.append("Our heavy-gauge machines handle up to 10mm thickness. For thicker materials, please share more details about your application so we can discuss alternatives.")
            break
    
    # Check for large size + low budget
    large_size_match = re.search(
        IMPOSSIBLE_REQUEST_INDICATORS['budget_too_low_for_size']['large_size'], 
        query_lower
    )
    low_budget_match = re.search(
        IMPOSSIBLE_REQUEST_INDICATORS['budget_too_low_for_size']['low_budget'], 
        query_lower
    )
    
    if large_size_match and low_budget_match:
        reasons.append("Budget may be insufficient for the requested forming area")
        suggestions.append("Large-format machines (2500mm+) typically start around ₹60-80 lakhs. We can discuss options that fit your budget, or explore financing.")
    
    is_impossible = len(reasons) > 0
    
    return ImpossibleRequestResult(
        is_impossible=is_impossible,
        reasons=reasons,
        suggestions=suggestions,
    )


def format_qualifying_response(result: QualificationResult, customer_name: str = None) -> str:
    """
    Format a professional response asking for missing information.
    """
    greeting = f"Hi {customer_name}!" if customer_name else "Hi!"
    
    # Acknowledge what we understood
    understood = []
    if result.extracted_info.get('application'):
        understood.append(f"for {result.extracted_info['application'].lower()} applications")
    if result.extracted_info.get('material'):
        understood.append(f"working with {result.extracted_info['material']}")
    
    understood_text = ""
    if understood:
        understood_text = f" I understand you're looking for a machine {' and '.join(understood)}."
    
    # Questions
    questions_text = "\n".join(f"• {q}" for q in result.qualifying_questions)
    
    response = f"""{greeting} Happy to help you find the right thermoforming machine.{understood_text}

To recommend the best machine for your needs, I'd like to understand a few things:

{questions_text}

Once I have these details, I can suggest the most suitable machine from our PF1/PF2 range with accurate specifications and pricing."""
    
    return response


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    test_queries = [
        "We need a vacuum forming machine. Please share details.",
        "Hi team, need a quote for a thermoforming machine.",
        "Looking for PF1-C-2015 price",
        "Need machine for 1000x1500mm PMMA sheets up to 6mm for telecom enclosures",
        "Budget is 50 lakh, need ABS forming machine",
        "What machine do you recommend for automotive parts?",
    ]
    
    print("=" * 70)
    print("SALES QUALIFICATION CHECKER TEST")
    print("=" * 70)
    
    for query in test_queries:
        print(f"\nQuery: {query[:60]}...")
        result = qualify_inquiry(query)
        print(f"  Qualified: {result.is_qualified}")
        print(f"  Score: {result.qualification_score:.2f}")
        print(f"  Extracted: {result.extracted_info}")
        if result.qualifying_questions:
            print(f"  Questions: {result.qualifying_questions[0][:50]}...")
        print("-" * 50)
