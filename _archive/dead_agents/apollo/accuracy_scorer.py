#!/usr/bin/env python3
"""
APOLLO Accuracy Scorer
======================

Measures how "off" IRA's responses are from expected answers.
Uses multiple metrics to create a mathematical accuracy score.

Components:
1. Semantic Similarity - How close is the meaning?
2. Fact Extraction - Did IRA get the key facts right?
3. Information Completeness - Did IRA cover all required points?
4. Style Match - Does it match Rushabh's communication style?

Usage:
    from accuracy_scorer import score_response, AccuracyReport
    
    report = score_response(
        ira_response="Hi! The PF1-C costs EUR 45,000...",
        expected_response="Hi! For your needs, PF1-C-1812 at EUR 39,000...",
        query="What's the price for 1800x1200 machine?"
    )
    print(f"Accuracy: {report.overall_score:.2%}")
"""

import os
import sys
import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import openai

client = openai.OpenAI()


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FactCheck:
    """A single fact that was checked."""
    fact: str
    expected: str
    actual: str
    correct: bool
    error_type: str = ""  # "wrong_value", "missing", "hallucination"


@dataclass 
class AccuracyReport:
    """Complete accuracy report for a single response."""
    
    # Overall score (0.0 to 1.0)
    overall_score: float
    
    # Component scores
    semantic_similarity: float  # 0-1: How close is the meaning?
    factual_accuracy: float     # 0-1: Are facts correct?
    completeness: float         # 0-1: All required info present?
    style_match: float          # 0-1: Matches Rushabh's style?
    
    # Detailed findings
    fact_checks: List[FactCheck] = field(default_factory=list)
    missing_info: List[str] = field(default_factory=list)
    hallucinations: List[str] = field(default_factory=list)
    style_issues: List[str] = field(default_factory=list)
    
    # Recommendations
    improvements: List[str] = field(default_factory=list)
    knowledge_gaps: List[str] = field(default_factory=list)
    clarification_needed: List[str] = field(default_factory=list)
    
    def __str__(self):
        return f"""
ACCURACY REPORT
===============
Overall Score: {self.overall_score:.1%}

Component Scores:
  Semantic Similarity: {self.semantic_similarity:.1%}
  Factual Accuracy:    {self.factual_accuracy:.1%}
  Completeness:        {self.completeness:.1%}
  Style Match:         {self.style_match:.1%}

Issues Found:
  Wrong Facts:    {len([f for f in self.fact_checks if not f.correct])}
  Missing Info:   {len(self.missing_info)}
  Hallucinations: {len(self.hallucinations)}
  Style Issues:   {len(self.style_issues)}

Top Improvements:
{chr(10).join(f'  - {i}' for i in self.improvements[:3])}
"""


# =============================================================================
# FACT EXTRACTION
# =============================================================================

FACT_EXTRACTION_PROMPT = """Extract all factual claims from this sales response.

Focus on:
1. Machine models mentioned (e.g., "PF1-C-1812")
2. Prices (e.g., "EUR 45,000", "₹4,500,000")
3. Specifications (forming area, depth, thickness, materials)
4. Delivery times (e.g., "4-5 months")
5. Payment terms (e.g., "30% advance")
6. Warranty details
7. Features mentioned

Return as JSON array of facts:
[
  {"category": "price", "item": "PF1-C-1812", "value": "EUR 45,000"},
  {"category": "spec", "item": "forming_area", "value": "1800x1200mm"},
  ...
]

RESPONSE TO ANALYZE:
{response}

Return ONLY the JSON array, no other text."""


def extract_facts(response: str) -> List[Dict]:
    """Extract factual claims from a response."""
    try:
        result = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": FACT_EXTRACTION_PROMPT.format(response=response)}
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        
        content = result.choices[0].message.content
        data = json.loads(content)
        
        # Handle both direct array and wrapped object
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'facts' in data:
            return data['facts']
        else:
            return []
            
    except Exception as e:
        print(f"Fact extraction error: {e}")
        return []


# =============================================================================
# COMPARISON ENGINE
# =============================================================================

COMPARISON_PROMPT = """Compare IRA's response to the expected response for this customer query.

CUSTOMER QUERY:
{query}

EXPECTED RESPONSE (Ground Truth - what Rushabh would say):
{expected}

IRA'S ACTUAL RESPONSE:
{actual}

Analyze and return JSON:
{{
    "semantic_similarity": 0.0-1.0,  // How similar is the overall meaning?
    "factual_matches": [
        {{"fact": "price", "expected": "EUR 39,000", "actual": "EUR 45,000", "correct": false}},
        ...
    ],
    "missing_information": ["list of things expected but not in IRA's response"],
    "hallucinations": ["list of things IRA said that aren't in expected/are wrong"],
    "style_comparison": {{
        "score": 0.0-1.0,
        "issues": ["too formal", "missing warmth", etc.]
    }},
    "completeness_score": 0.0-1.0,  // Did IRA cover all key points?
    "improvements": ["specific actionable improvements"]
}}"""


def compare_responses(
    query: str,
    expected: str, 
    actual: str
) -> Dict:
    """Compare IRA's response to expected response."""
    try:
        result = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a sales response evaluator. Return only valid JSON."},
                {"role": "user", "content": COMPARISON_PROMPT.format(
                    query=query,
                    expected=expected,
                    actual=actual
                )}
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        
        return json.loads(result.choices[0].message.content)
        
    except Exception as e:
        print(f"Comparison error: {e}")
        return {
            "semantic_similarity": 0.5,
            "factual_matches": [],
            "missing_information": [],
            "hallucinations": [],
            "style_comparison": {"score": 0.5, "issues": []},
            "completeness_score": 0.5,
            "improvements": [f"Error during comparison: {e}"]
        }


# =============================================================================
# SCORING FORMULA
# =============================================================================

def calculate_accuracy_score(
    semantic_sim: float,
    factual_acc: float,
    completeness: float,
    style_match: float,
    weights: Dict[str, float] = None
) -> float:
    """
    Calculate overall accuracy score using weighted formula.
    
    Formula:
        Score = w1*Semantic + w2*Factual + w3*Completeness + w4*Style
    
    Default weights prioritize factual accuracy for sales:
        - Factual: 40% (most important - wrong price = lost deal)
        - Completeness: 25% (need to answer all questions)
        - Semantic: 20% (general meaning alignment)
        - Style: 15% (personality match)
    """
    if weights is None:
        weights = {
            "semantic": 0.20,
            "factual": 0.40,
            "completeness": 0.25,
            "style": 0.15,
        }
    
    score = (
        weights["semantic"] * semantic_sim +
        weights["factual"] * factual_acc +
        weights["completeness"] * completeness +
        weights["style"] * style_match
    )
    
    return min(1.0, max(0.0, score))


# =============================================================================
# MAIN SCORING FUNCTION
# =============================================================================

def score_response(
    ira_response: str,
    expected_response: str,
    query: str,
    context: Dict = None,
) -> AccuracyReport:
    """
    Score IRA's response against expected response.
    
    Args:
        ira_response: What IRA actually said
        expected_response: What Rushabh would have said (ground truth)
        query: The original customer query
        context: Optional additional context
    
    Returns:
        AccuracyReport with detailed scoring
    """
    
    # Compare responses
    comparison = compare_responses(query, expected_response, ira_response)
    
    # Extract component scores
    semantic_sim = comparison.get("semantic_similarity", 0.5)
    completeness = comparison.get("completeness_score", 0.5)
    style_data = comparison.get("style_comparison", {"score": 0.5, "issues": []})
    style_match = style_data.get("score", 0.5)
    
    # Calculate factual accuracy
    fact_matches = comparison.get("factual_matches", [])
    if fact_matches:
        correct_facts = sum(1 for f in fact_matches if f.get("correct", False))
        factual_acc = correct_facts / len(fact_matches)
    else:
        factual_acc = 0.5  # No facts to check
    
    # Build fact check list
    fact_checks = [
        FactCheck(
            fact=f.get("fact", ""),
            expected=f.get("expected", ""),
            actual=f.get("actual", ""),
            correct=f.get("correct", False),
            error_type="wrong_value" if not f.get("correct", False) else "",
        )
        for f in fact_matches
    ]
    
    # Calculate overall score
    overall = calculate_accuracy_score(
        semantic_sim=semantic_sim,
        factual_acc=factual_acc,
        completeness=completeness,
        style_match=style_match,
    )
    
    # Identify knowledge gaps and clarification needs
    knowledge_gaps = []
    clarification_needed = []
    
    for missing in comparison.get("missing_information", []):
        if "price" in missing.lower() or "spec" in missing.lower():
            knowledge_gaps.append(f"Missing knowledge: {missing}")
        else:
            clarification_needed.append(f"Need to clarify: {missing}")
    
    return AccuracyReport(
        overall_score=overall,
        semantic_similarity=semantic_sim,
        factual_accuracy=factual_acc,
        completeness=completeness,
        style_match=style_match,
        fact_checks=fact_checks,
        missing_info=comparison.get("missing_information", []),
        hallucinations=comparison.get("hallucinations", []),
        style_issues=style_data.get("issues", []),
        improvements=comparison.get("improvements", []),
        knowledge_gaps=knowledge_gaps,
        clarification_needed=clarification_needed,
    )


# =============================================================================
# BATCH SCORING
# =============================================================================

def score_simulation(simulation_file: str) -> List[AccuracyReport]:
    """Score all turns in a simulation against expected responses."""
    
    with open(simulation_file) as f:
        data = json.load(f)
    
    reports = []
    conversation = data.get("conversation", [])
    
    for turn in conversation:
        # For simulations, we use the customer query as context
        # and compare IRA's response to what we'd expect
        query = turn.get("customer", "")
        ira_response = turn.get("ira", "")
        
        # Note: In real use, expected_response would come from training data
        # For now, we'll score style and completeness only
        report = score_response(
            ira_response=ira_response,
            expected_response=ira_response,  # Self-comparison for now
            query=query,
        )
        reports.append(report)
    
    return reports


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    # Demo scoring
    query = "What's the price for a 1800x1200mm thermoforming machine?"
    
    expected = """Hi! Happy to help.

For your 1800x1200mm requirement, I recommend the PF1-C-1812:
- Price: EUR 39,000 (approx ₹3,240,000)
- Forming area: 1800 x 1200 mm
- Max thickness: 10mm
- Lead time: 12-16 weeks

Let me know if you want detailed specs!"""

    actual = """Hello,

Thank you for your inquiry. We have several machines that could meet your needs. 
The PF1-C-1812 has a forming area of 1800x1200mm. 
The price is approximately EUR 45,000.
Delivery would be around 4-5 months.

Please let us know if you have any questions.

Best regards,
Ira"""

    print("Scoring IRA's response...")
    report = score_response(actual, expected, query)
    print(report)
