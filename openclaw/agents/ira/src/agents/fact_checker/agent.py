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
    Retrieval-augmented fact-checker. Verifies ALL factual claims in a draft
    by extracting them, searching the knowledge base for evidence, and then
    rewriting the draft to remove or flag anything unsupported.
    
    Two-pass system:
      Pass 1: Rule-based checks (AM thickness, pricing, spec ranges)
      Pass 2: LLM-powered claim extraction + retrieval verification
    """
    context = context or {}
    
    logger.info({"agent": "Vera", "event": "verification_started", "draft_length": len(draft)})
    
    issues = []
    corrections_made = []
    verified_draft = draft
    
    # ── PASS 1: Rule-based checks (fast, deterministic) ──────────────
    
    am_check = _check_am_series_rule(draft, original_query)
    if am_check["violation"]:
        issues.append(am_check["issue"])
        if am_check["correction"]:
            verified_draft = _add_am_warning(verified_draft, original_query)
            corrections_made.append("Added AM series thickness warning")
    
    if _needs_pricing_disclaimer(verified_draft, original_query):
        verified_draft = _add_pricing_disclaimer(verified_draft)
        corrections_made.append("Added pricing disclaimer")
    
    hallucinations = _detect_hallucinations(verified_draft)
    if hallucinations:
        for h in hallucinations:
            issues.append(f"Potential hallucination: '{h}'")
        verified_draft = _flag_hallucinations(verified_draft, hallucinations)
    
    spec_issues = _validate_specifications(verified_draft)
    issues.extend(spec_issues)
    
    price_warnings = _verify_prices(verified_draft)
    if price_warnings:
        issues.extend(price_warnings)
    
    # ── PASS 2: Retrieval-augmented claim verification (LLM) ─────────
    # Skip only trivial acks/greetings (< 30 chars)
    if len(verified_draft) > 30:
        rav_result = await _retrieval_augmented_verify(verified_draft, original_query, context)
        if rav_result:
            verified_draft = rav_result["verified_draft"]
            corrections_made.extend(rav_result.get("corrections", []))
            issues.extend(rav_result.get("issues", []))

    # ── PASS 3: Entity cross-reference ────────────────────────────────
    # Verify company names and roles against source data
    if len(verified_draft) > 100:
        xref_result = await _cross_reference_entities(verified_draft, original_query, context)
        if xref_result and xref_result["corrections"]:
            verified_draft = xref_result["corrected_draft"]
            corrections_made.extend(xref_result["corrections"])
            issues.extend(xref_result["issues"])

    logger.info({
        "agent": "Vera",
        "event": "verification_complete",
        "issues_found": len(issues),
        "corrections_made": len(corrections_made),
    })
    if issues:
        logger.warning({"agent": "Vera", "event": "issues_detected", "issues": issues})
    
    return verified_draft


async def _retrieval_augmented_verify(
    draft: str,
    original_query: str,
    context: Dict,
) -> Optional[Dict]:
    """Extract claims from draft, search for evidence, rewrite to remove unsupported claims."""
    import os
    
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None
    
    # Step 1: Gather evidence from all available sources
    evidence_parts = []
    
    # From pipeline context (research output already fetched)
    research = context.get("research_output", "")
    if research:
        evidence_parts.append(f"RESEARCH OUTPUT:\n{research[:3000]}")
    
    # From Mem0
    try:
        from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
        mem0 = get_mem0_service()
        for uid in ["machinecraft_customers", "machinecraft_knowledge", "machinecraft_pricing"]:
            memories = mem0.search(original_query, uid, limit=8)
            if memories:
                evidence_parts.append(f"MEM0 [{uid}]:\n" + "\n".join(f"- {m.memory}" for m in memories))
    except Exception as e:
        logger.debug(f"Vera: Mem0 evidence fetch failed: {e}")
    
    # From Qdrant
    try:
        from openclaw.agents.ira.src.brain.qdrant_retriever import retrieve as qdrant_retrieve
        rag_result = qdrant_retrieve(original_query, top_k=5)
        if hasattr(rag_result, 'citations') and rag_result.citations:
            rag_text = "\n".join(
                f"- [{c.filename}] {c.text[:300]}" for c in rag_result.citations[:5]
            )
            evidence_parts.append(f"DOCUMENTS:\n{rag_text}")
    except Exception as e:
        logger.debug(f"Vera: Qdrant evidence fetch failed: {e}")
    
    if not evidence_parts:
        return None
    
    evidence = "\n\n".join(evidence_parts)
    
    # Step 2: Ask LLM to verify the draft against the evidence
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """You are Vera, a rigorous fact-checker for Machinecraft Technologies.

Given a DRAFT response and EVIDENCE from our databases, verify every factual claim.

Your job:
1. Check each specific claim (company names, machine models, specs, prices, relationships, dates, regions)
2. If a claim is SUPPORTED by the evidence, keep it
3. If a claim is CONTRADICTED by the evidence, REMOVE it or correct it
4. If a claim has NO evidence either way, add "(unverified)" after it
5. If a company is called a "customer" but evidence doesn't confirm they bought a machine, change to "contact" or remove

Output the CORRECTED draft. Keep the same tone and structure. Only change factual claims.
If everything checks out, return the draft unchanged.

At the end, add a line: [Vera: X claims verified, Y corrected, Z flagged as unverified]"""},
                {"role": "user", "content": f"DRAFT:\n{draft}\n\nEVIDENCE:\n{evidence[:6000]}"},
            ],
            max_tokens=2048,
            temperature=0.1,
        )
        
        result_text = resp.choices[0].message.content.strip()
        
        # Extract Vera's summary line
        vera_corrections = []
        vera_issues = []
        if "[Vera:" in result_text:
            summary_start = result_text.rfind("[Vera:")
            summary = result_text[summary_start:]
            result_text = result_text[:summary_start].strip()
            if "corrected" in summary.lower():
                vera_corrections.append(summary.strip("[]"))
            if "unverified" in summary.lower():
                vera_issues.append(summary.strip("[]"))
        
        if result_text and len(result_text) > 50:
            return {
                "verified_draft": result_text,
                "corrections": vera_corrections,
                "issues": vera_issues,
            }
    except Exception as e:
        logger.warning(f"Vera: Retrieval-augmented verification failed: {e}")
    
    return None


def _verify_prices(draft: str) -> List[str]:
    """Check prices mentioned in draft against machine_specs.json canonical prices."""
    import json
    from pathlib import Path
    warnings: List[str] = []
    specs_file = Path(__file__).parent.parent.parent.parent.parent / "data" / "brain" / "machine_specs.json"
    if not specs_file.exists():
        return warnings
    try:
        specs = json.loads(specs_file.read_text())
    except Exception:
        return warnings

    price_pattern = re.compile(r'(?:INR|₹|Rs\.?)\s*([\d,]+(?:\.\d+)?)', re.IGNORECASE)
    model_pattern = re.compile(
        r'(PF\d-[CXR]-\d{4}|AM[P]?-\d{4}|IMG-\d{4}|FCS-\d{4}|PF2-P\d{4}|UNO-\d{4}|DUO-\d{4})',
        re.IGNORECASE,
    )

    models_in_draft = model_pattern.findall(draft)
    prices_in_draft = price_pattern.findall(draft)

    if not models_in_draft or not prices_in_draft:
        return warnings

    for model in models_in_draft:
        model_upper = model.upper()
        spec = specs.get(model_upper) or specs.get(model)
        if not spec:
            continue
        canonical_price = spec.get("price_inr") or spec.get("base_price_inr")
        if not canonical_price:
            continue
        canonical_num = int(str(canonical_price).replace(",", "").replace(".", ""))
        for price_str in prices_in_draft:
            try:
                mentioned_num = int(price_str.replace(",", "").split(".")[0])
                if mentioned_num > 0 and canonical_num > 0:
                    ratio = mentioned_num / canonical_num
                    if ratio < 0.7 or ratio > 1.3:
                        warnings.append(
                            f"Price mismatch: {model} mentioned at INR {price_str} "
                            f"but canonical price is INR {canonical_price:,} (>{30}% deviation)"
                        )
            except (ValueError, ZeroDivisionError):
                continue
    return warnings


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


def _needs_pricing_disclaimer(draft: str, original_query: str = "") -> bool:
    """Check if draft mentions pricing and needs disclaimer.
    
    Skips non-sales contexts (dream summaries, status checks, training) to
    avoid false positives.
    """
    if original_query:
        query_lower = original_query.lower()
        non_sales_indicators = [
            "dream", "summary", "journal", "status", "memories", "teach",
            "train", "/", "self-test", "self test", "error", "lesson",
            "health", "score", "debug",
        ]
        if any(ind in query_lower for ind in non_sales_indicators):
            return False

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


async def _cross_reference_entities(
    draft: str,
    original_query: str,
    context: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Cross-reference company names and factual claims in the draft against source data.
    
    Uses an LLM to compare the draft against the raw data that was used to generate it,
    flagging any claims that aren't supported by the evidence.
    """
    result = {"corrected_draft": draft, "corrections": [], "issues": []}
    
    company_pattern = re.compile(
        r'\*\*([A-Z][A-Za-z\s&\-\.]+?)\*\*|'
        r'(?:^|\d+\.\s+)([A-Z][A-Za-z\s&\-\.]{2,}?)(?:\s*[-–(]|\s*$)',
        re.MULTILINE,
    )
    matches = company_pattern.findall(draft)
    company_names = [m[0] or m[1] for m in matches if (m[0] or m[1]).strip()]
    
    if not company_names or len(company_names) < 2:
        return result
    
    source_data = ""
    if context:
        research = context.get("research_output", "")
        if research:
            source_data = research[:3000]
    
    if not source_data:
        try:
            from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
            mem0 = get_mem0_service()
            memories = mem0.search(original_query, "machinecraft_customers", limit=15)
            source_data = "\n".join(f"- {m.memory}" for m in memories)
        except Exception:
            pass
    
    if not source_data:
        return result
    
    try:
        import openai
        import os
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return result
        
        client = openai.OpenAI(api_key=api_key)
        companies_str = ", ".join(company_names[:15])
        
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "You are Vera, a fact-checker. Given a draft response and the SOURCE DATA it was based on, "
                    "check if each company listed in the draft is actually supported by the source data.\n\n"
                    "For each company, output ONE line:\n"
                    "VERIFIED: [Company] - reason\n"
                    "UNVERIFIED: [Company] - not found in source data\n"
                    "WRONG_ROLE: [Company] - listed as customer but source says agent/partner/prospect\n\n"
                    "Only flag issues. If everything checks out, say ALL_VERIFIED."
                )},
                {"role": "user", "content": (
                    f"DRAFT mentions these companies: {companies_str}\n\n"
                    f"SOURCE DATA:\n{source_data[:4000]}\n\n"
                    f"Check each company against the source data."
                )},
            ],
            max_tokens=500,
            temperature=0.1,
        )
        
        analysis = resp.choices[0].message.content.strip()
        
        if "ALL_VERIFIED" in analysis:
            return result
        
        unverified = []
        wrong_role = []
        for line in analysis.split("\n"):
            line = line.strip()
            if line.startswith("UNVERIFIED:"):
                company = line.split(":", 1)[1].split("-")[0].strip()
                unverified.append(company)
            elif line.startswith("WRONG_ROLE:"):
                company = line.split(":", 1)[1].split("-")[0].strip()
                wrong_role.append(company)
        
        if unverified or wrong_role:
            disclaimer_parts = []
            if unverified:
                disclaimer_parts.append(
                    f"Could not verify from our records: {', '.join(unverified)}"
                )
            if wrong_role:
                disclaimer_parts.append(
                    f"May not be customers (could be agents/partners): {', '.join(wrong_role)}"
                )
            disclaimer = "\n\nNote: " + ". ".join(disclaimer_parts) + "."
            result["corrected_draft"] = draft + disclaimer
            result["corrections"].append(f"Added entity verification note ({len(unverified)} unverified, {len(wrong_role)} wrong role)")
            result["issues"].extend([f"Unverified entity: {c}" for c in unverified])
            result["issues"].extend([f"Wrong role: {c}" for c in wrong_role])
            logger.info(f"[Vera] Entity cross-reference: {len(unverified)} unverified, {len(wrong_role)} wrong role")
    
    except Exception as e:
        logger.warning(f"[Vera] Entity cross-reference failed: {e}")
    
    return result


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
    
    price_warnings = _verify_prices(verified_draft)
    if price_warnings:
        issues.extend(price_warnings)
    
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


# =============================================================================
# BACKWARD-COMPATIBLE ALIASES
# =============================================================================
# brain/__init__.py and generate_answer.py import these names

FactIssue = str  # Issues are plain strings in this implementation

class FactChecker:
    """Wrapper class for backward compatibility with brain imports."""

    @staticmethod
    async def verify_draft(draft: str, query: str, context: Optional[Dict] = None) -> VerificationReport:
        return generate_verification_report(draft, query, context)

    @staticmethod
    async def check(draft: str, query: str, context: Optional[Dict] = None) -> str:
        return await verify(draft, query, context)


async def verify_reply(draft: str, original_query: str, context: Optional[Dict] = None) -> str:
    """Alias for verify() - used by brain/__init__.py and generate_answer.py."""
    return await verify(draft, original_query, context)
