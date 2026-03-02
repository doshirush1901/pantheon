#!/usr/bin/env python3
"""
HALLUCINATION GUARD - Multi-layer protection against LLM hallucinations
========================================================================

Strategies:
1. Pre-generation: Validate we have data before generating
2. Structured output: Force LLM to cite sources
3. Post-generation: Verify all claims against database
4. Confidence scoring: Detect uncertain responses
5. Grounding enforcement: Ensure every fact has a source

Usage:
    from hallucination_guard import HallucinationGuard
    guard = HallucinationGuard()
    safe_reply = guard.generate_safe_reply(query, machines, context)
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import openai

# Import our database
from machine_database import get_machine, MACHINE_SPECS, MachineSpec, format_spec_table


@dataclass
class GroundedFact:
    """A fact with its source."""
    claim: str
    source: str  # "database", "document", "discovered"
    confidence: float
    verified: bool = False


@dataclass
class SafetyReport:
    """Report on reply safety."""
    is_safe: bool
    hallucination_risk: float  # 0.0 - 1.0
    ungrounded_claims: List[str]
    warnings: List[str]


class HallucinationGuard:
    """
    Multi-layer protection against hallucinations.
    """
    
    def __init__(self):
        self.openai = openai.OpenAI()
        self.valid_series = {"PF1", "PF2", "IMG", "IMGS", "AM", "FCS", "UNO", "DUO", "PLAY", "ATF"}
        self.valid_models = set(MACHINE_SPECS.keys())
        
        # Fake name patterns to block (but NOT our valid model numbers)
        self.fake_patterns = [
            r'(?:Thermo|Vac|Form|Heat|Press|Mold)(?:Master|Pro|Max|Plus|X|Elite|Ultra|Tech|Force)\s*\d*',
            # Don't match patterns that look like our models (PF1, PF2, IMG, AM, etc.)
            r'(?:TF|VF|HF|MF|TM|VM)-?\d{3,4}[A-Z]*',  # Generic alphanumeric (removed PF)
            # "Model XYZ-1234" but NOT "Model PF1-C-2020"
            r'Model\s+(?!PF|IMG|AM|FCS|UNO|DUO)[A-Z0-9-]+\d{4}',
            r'(?:Super|Mega|Ultra|Pro|Max)\s*(?:Former|Vac|Form|Press)',
        ]
    
    # =========================================================================
    # STRATEGY 1: Pre-generation validation
    # =========================================================================
    
    def validate_can_answer(self, query: str, machines: List[MachineSpec]) -> Tuple[bool, str]:
        """
        Check if we have enough data to answer without hallucinating.
        
        Returns:
            (can_answer, reason)
        """
        # Check if we found any machines
        if not machines:
            return False, "No machines found in database for this query"
        
        # Check if machines have the necessary data
        missing_critical = []
        for m in machines:
            if not m.price_inr and not m.price_usd:
                missing_critical.append(f"{m.model}: no price")
            if not m.forming_area_mm:
                missing_critical.append(f"{m.model}: no forming area")
        
        if len(missing_critical) == len(machines):
            return False, f"All machines missing critical data: {missing_critical}"
        
        return True, "Sufficient data available"
    
    # =========================================================================
    # STRATEGY 2: Structured output with source citations
    # =========================================================================
    
    def generate_with_citations(self, query: str, machines: List[MachineSpec], 
                                context: List[Dict]) -> Dict:
        """
        Generate a response with explicit source citations.
        
        Forces the LLM to cite where each fact comes from.
        """
        # Build source reference
        sources = {}
        for i, m in enumerate(machines):
            sources[f"DB_{m.model}"] = {
                "type": "database",
                "model": m.model,
                "price_inr": m.price_inr,
                "forming_area": m.forming_area_mm,
                "heater_power": m.heater_power_kw,
                "vacuum": m.vacuum_pump_capacity,
            }
        
        for i, c in enumerate(context[:5]):
            sources[f"DOC_{i}"] = {
                "type": "document",
                "text": c.get("text", "")[:200],
            }
        
        prompt = f"""Generate a response to this query. You MUST cite sources for EVERY fact.

QUERY: {query}

AVAILABLE SOURCES:
{json.dumps(sources, indent=2)}

Return JSON with this structure:
{{
    "response_text": "Your response here with [SOURCE_ID] citations inline",
    "facts_used": [
        {{"fact": "The PF1-C-2015 costs ₹60,00,000", "source_id": "DB_PF1-C-2015"}},
        ...
    ],
    "machines_mentioned": ["PF1-C-2015", ...],
    "confidence": 0.0-1.0
}}

RULES:
- ONLY use facts from the sources provided
- Every number MUST have a [SOURCE_ID] citation
- If you can't find data in sources, say "specification not available"
- Do NOT invent any machine names or specs
"""

        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Generate cited responses. Never invent facts."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3  # Lower temperature = less hallucination
            )
            
            text = response.choices[0].message.content
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text)
            
        except Exception as e:
            return {"error": str(e), "response_text": "", "confidence": 0}
    
    # =========================================================================
    # STRATEGY 3: Post-generation verification
    # =========================================================================
    
    def verify_all_claims(self, reply: str, machines: List[MachineSpec]) -> SafetyReport:
        """
        Verify every factual claim in the reply.
        """
        warnings = []
        ungrounded = []
        risk_score = 0.0
        
        # Check for fake machine names
        for pattern in self.fake_patterns:
            matches = re.findall(pattern, reply, re.IGNORECASE)
            for match in matches:
                ungrounded.append(f"Fake machine name: {match}")
                risk_score += 0.5
        
        # Check mentioned models exist
        mentioned_models = self._extract_model_mentions(reply)
        for model in mentioned_models:
            if model not in self.valid_models:
                # Check if it's close to a valid model (typo)
                close_match = self._find_close_match(model)
                if close_match:
                    warnings.append(f"Model '{model}' might be typo for '{close_match}'")
                    risk_score += 0.1
                else:
                    ungrounded.append(f"Unknown model: {model}")
                    risk_score += 0.3
        
        # Check prices match database
        machine_lookup = {m.model: m for m in machines}
        price_pattern = r'₹\s*([\d,]+)'
        for match in re.finditer(price_pattern, reply):
            price_str = match.group(1).replace(',', '')
            try:
                price = int(price_str)
                # Find which machine this might refer to
                context = reply[max(0, match.start()-100):match.end()+50]
                found_match = False
                for model, machine in machine_lookup.items():
                    if model in context and machine.price_inr:
                        if abs(price - machine.price_inr) / machine.price_inr > 0.1:
                            warnings.append(f"Price ₹{price:,} doesn't match {model} (₹{machine.price_inr:,})")
                            risk_score += 0.2
                        found_match = True
                        break
                if not found_match and price > 100000:  # Significant price mentioned
                    warnings.append(f"Price ₹{price:,} not verified against database")
                    risk_score += 0.1
            except (ValueError, TypeError):
                pass  # Skip invalid price formats
        
        # Check for vague/uncertain language (might indicate hallucination)
        uncertainty_phrases = [
            "I believe", "I think", "possibly", "might be", "could be",
            "approximately", "around", "roughly", "estimated"
        ]
        for phrase in uncertainty_phrases:
            if phrase.lower() in reply.lower():
                warnings.append(f"Uncertain language detected: '{phrase}'")
                risk_score += 0.05
        
        is_safe = risk_score < 0.3 and len(ungrounded) == 0
        
        return SafetyReport(
            is_safe=is_safe,
            hallucination_risk=min(risk_score, 1.0),
            ungrounded_claims=ungrounded,
            warnings=warnings
        )
    
    def _extract_model_mentions(self, text: str) -> List[str]:
        """Extract all model number mentions from text."""
        patterns = [
            r'PF1-[A-Z]-\d{4}',
            r'PF2-[A-Z]\d{4}',
            r'AM-[A-Z]?-?\d{4}',
            r'IMG[S]?-\d{4}',
            r'FCS-\d{4}-\d[A-Z]{2}',
            r'UNO-\d{4}',
            r'DUO-\d{4}',
            r'PLAY-\d{4}',
            r'ATF-\d{4}',
        ]
        
        models = []
        for pattern in patterns:
            models.extend(re.findall(pattern, text))
        return list(set(models))
    
    def _find_close_match(self, model: str) -> Optional[str]:
        """Find a close match in valid models (for typos)."""
        model_clean = model.replace("-", "").upper()
        for valid in self.valid_models:
            valid_clean = valid.replace("-", "").upper()
            # Simple edit distance check
            if len(model_clean) == len(valid_clean):
                diff = sum(1 for a, b in zip(model_clean, valid_clean) if a != b)
                if diff <= 2:  # Allow 2 character differences
                    return valid
        return None
    
    # =========================================================================
    # STRATEGY 4: Confidence scoring
    # =========================================================================
    
    def score_response_confidence(self, reply: str, machines: List[MachineSpec]) -> float:
        """
        Score how confident we are that the response is accurate.
        
        Returns 0.0 (no confidence) to 1.0 (high confidence)
        """
        score = 1.0
        
        # Penalize for no machines
        if not machines:
            score -= 0.5
        
        # Penalize for uncertainty language
        uncertainty_count = sum(1 for phrase in 
            ["I believe", "I think", "possibly", "might", "could be", "approximately"]
            if phrase.lower() in reply.lower())
        score -= uncertainty_count * 0.1
        
        # Penalize for very long responses (more room for error)
        word_count = len(reply.split())
        if word_count > 800:
            score -= 0.1
        
        # Bonus for using exact model numbers from our database
        mentioned = self._extract_model_mentions(reply)
        valid_mentions = sum(1 for m in mentioned if m in self.valid_models)
        if mentioned:
            score += (valid_mentions / len(mentioned)) * 0.2
        
        # Bonus for including specific numbers
        has_specific_numbers = bool(re.search(r'\d{2,4}\s*(?:mm|kW|m³/hr)', reply))
        if has_specific_numbers:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    # =========================================================================
    # STRATEGY 5: Safe generation with guardrails
    # =========================================================================
    
    def generate_safe_reply(self, query: str, machines: List[MachineSpec], 
                           context: List[Dict]) -> Tuple[str, SafetyReport]:
        """
        Generate a reply with all safety guardrails.
        
        1. Validate we can answer
        2. Generate with low temperature
        3. Verify all claims
        4. Score confidence
        5. Reject if unsafe
        """
        # Step 1: Can we answer?
        can_answer, reason = self.validate_can_answer(query, machines)
        if not can_answer:
            return self._generate_safe_fallback(query, reason), SafetyReport(
                is_safe=True,
                hallucination_risk=0.0,
                ungrounded_claims=[],
                warnings=[f"Used fallback: {reason}"]
            )
        
        # Step 2: Generate with citations
        cited_response = self.generate_with_citations(query, machines, context)
        
        if "error" in cited_response:
            return self._generate_safe_fallback(query, "Generation error"), SafetyReport(
                is_safe=True,
                hallucination_risk=0.0,
                ungrounded_claims=[],
                warnings=["Used fallback due to generation error"]
            )
        
        reply = cited_response.get("response_text", "")
        
        # Remove citation markers for final output
        reply = re.sub(r'\[DB_[^\]]+\]', '', reply)
        reply = re.sub(r'\[DOC_\d+\]', '', reply)
        
        # Step 3: Verify all claims
        safety = self.verify_all_claims(reply, machines)
        
        # Step 4: Score confidence
        confidence = self.score_response_confidence(reply, machines)
        
        # Step 5: Reject if unsafe
        if not safety.is_safe or confidence < 0.5:
            return self._generate_safe_fallback(
                query, 
                f"Safety check failed (risk={safety.hallucination_risk:.2f}, confidence={confidence:.2f})"
            ), safety
        
        return reply, safety
    
    def _generate_safe_fallback(self, query: str, reason: str) -> str:
        """Generate a safe fallback response."""
        return f"""Hello,

Thank you for your enquiry. I want to ensure I provide you with accurate information.

I'm currently reviewing our technical documentation to find the best match for your requirements. Rather than risk providing incorrect specifications, I'll compile verified data from our catalogue and get back to you shortly.

In the meantime, could you confirm:
1. The exact forming area dimensions required?
2. Material type and thickness?
3. Production volume expectations?

This will help me recommend the most suitable machine from our PF1, PF2, IMG, or AM series.

Best regards,
Ira
Technical Sales Expert
Machinecraft

---
[Internal note: {reason}]
"""


def guard_reply(reply: str, machines: List[MachineSpec]) -> Tuple[str, bool, str]:
    """
    Quick function to guard a reply.
    
    Returns:
        (reply, is_safe, report)
    """
    guard = HallucinationGuard()
    safety = guard.verify_all_claims(reply, machines)
    
    report = f"Risk: {safety.hallucination_risk:.2f}\n"
    if safety.ungrounded_claims:
        report += f"Ungrounded: {safety.ungrounded_claims}\n"
    if safety.warnings:
        report += f"Warnings: {safety.warnings}\n"
    
    return reply, safety.is_safe, report


if __name__ == "__main__":
    # Test
    guard = HallucinationGuard()
    
    # Test with bad reply
    bad_reply = """
    The ThermoMaster 2000 is perfect for your needs. It has a forming area of 
    2000 x 1500 mm and costs approximately ₹75,00,000. I believe this should work.
    """
    
    machines = [get_machine("PF1-C-2015")]
    safety = guard.verify_all_claims(bad_reply, machines)
    
    print("BAD REPLY SAFETY CHECK:")
    print(f"  Safe: {safety.is_safe}")
    print(f"  Risk: {safety.hallucination_risk}")
    print(f"  Ungrounded: {safety.ungrounded_claims}")
    print(f"  Warnings: {safety.warnings}")
    
    # Test with good reply  
    good_reply = """
    The PF1-C-2015 is perfect for your needs. It has a forming area of 
    2000 x 1500 mm and costs ₹60,00,000. The heater power is 125 kW.
    """
    
    safety = guard.verify_all_claims(good_reply, machines)
    
    print("\nGOOD REPLY SAFETY CHECK:")
    print(f"  Safe: {safety.is_safe}")
    print(f"  Risk: {safety.hallucination_risk}")
    print(f"  Warnings: {safety.warnings}")
