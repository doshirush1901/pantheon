#!/usr/bin/env python3
"""
ATHENA Response Evaluator
=========================

Evaluates IRA's responses against Rushabh's actual responses using
multiple criteria:

1. Style Match - Does IRA sound like Rushabh?
2. Content Accuracy - Are facts/specs correct?
3. Completeness - Does it answer all parts?
4. Sales Effectiveness - Does it move the conversation forward?
"""

import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent


@dataclass
class EvaluationResult:
    """Result of evaluating an IRA response."""
    question_id: str
    category: str
    
    # Scores (1-5)
    style_score: float
    accuracy_score: float
    completeness_score: float
    sales_effectiveness_score: float
    technical_conversation_score: float  # NEW: Technical conversation patterns
    overall_score: float
    
    # Detailed feedback
    style_feedback: str
    accuracy_feedback: str
    completeness_feedback: str
    sales_feedback: str
    technical_feedback: str  # NEW: Technical conversation feedback
    
    # Comparison
    key_differences: List[str]
    missing_elements: List[str]
    extra_elements: List[str]
    
    # Pass/Fail
    passed: bool
    critical_failures: List[str]


# Rushabh's style markers (extracted from real emails)
RUSHABH_STYLE_MARKERS = {
    'greetings': ['Hi', 'Hey', 'Hello', 'Dear'],
    'closings': ['Cheers', 'Best', 'Regards', 'Thanks'],
    'tone': ['happy to', 'glad to', 'sounds good', 'no problem', 'sure'],
    'direct_patterns': ['Let me', 'I will', "I'll", 'We can', 'Here is'],
    'action_oriented': ['send', 'share', 'provide', 'call', 'meet', 'visit'],
}

# Technical conversation patterns Rushabh uses
RUSHABH_TECHNICAL_PATTERNS = {
    'qualification_questions': [
        'what is your application',
        'what material',
        'max thickness',
        'max sheet size',
        'max depth',
        'what is your budget',
        'frame type',
        'heater type',
        'servo',
        'pneumatic',
    ],
    'structured_specs': [
        'config a', 'config b',  # Configuration options
        'max ', 'min ',          # Spec ranges
        'price:', 'cost:',       # Pricing structure
        'lead time',             # Delivery info
        'months',                # Timeline
    ],
    'service_breakdown': [
        'days',                  # Time breakdown
        'training',              # Service items
        'installation',
        'commissioning',
        'technician',
        'travel',
        'hotel',
    ],
    'reference_sites': [
        'sweden', 'denmark', 'uk', 'netherlands', 'belgium',
        'canada', 'russia', 'usa', 'uae', 'italy',
        'near', 'at', 'visit',   # Offer to show machine
        'customer', 'reference',
    ],
}

# Critical rules that must be followed
CRITICAL_RULES = {
    'AM_THICKNESS': {
        'pattern': r'AM.*(series|machine)',
        'rule': 'AM series is for ≤1.5mm thickness only',
        'violation_patterns': [r'AM.*(2|3|4|5|6)\s*mm', r'thick.*AM'],
    },
    'NO_FABRICATION': {
        'rule': 'Never fabricate specifications',
        'check_patterns': [r'\d{3,}\s*(kW|mm|kg)', r'model.*\d{4}'],
    },
    'PRICING_DISCLAIMER': {
        'pattern': r'(price|cost|quote|\$|€)',
        'rule': 'Pricing should mention "subject to configuration"',
    },
}


class ResponseEvaluator:
    """Evaluates IRA responses against ground truth (Rushabh's responses)."""
    
    def __init__(self):
        self.evaluation_count = 0
    
    def evaluate_style(self, ira_response: str, rushabh_response: str) -> Tuple[float, str]:
        """Evaluate how well IRA matches Rushabh's style."""
        score = 3.0  # Start neutral
        feedback_points = []
        
        ira_lower = ira_response.lower()
        rushabh_lower = rushabh_response.lower()
        
        # Check for greeting style match
        ira_greeting = any(g.lower() in ira_lower[:50] for g in RUSHABH_STYLE_MARKERS['greetings'])
        rushabh_greeting = any(g.lower() in rushabh_lower[:50] for g in RUSHABH_STYLE_MARKERS['greetings'])
        if ira_greeting == rushabh_greeting:
            score += 0.3
        
        # Check tone markers
        ira_tone = sum(1 for t in RUSHABH_STYLE_MARKERS['tone'] if t in ira_lower)
        rushabh_tone = sum(1 for t in RUSHABH_STYLE_MARKERS['tone'] if t in rushabh_lower)
        if abs(ira_tone - rushabh_tone) <= 1:
            score += 0.3
        else:
            feedback_points.append("Tone differs from Rushabh's style")
        
        # Check directness
        ira_direct = sum(1 for d in RUSHABH_STYLE_MARKERS['direct_patterns'] if d.lower() in ira_lower)
        if ira_direct >= 2:
            score += 0.2
        
        # Check action orientation
        ira_actions = sum(1 for a in RUSHABH_STYLE_MARKERS['action_oriented'] if a in ira_lower)
        if ira_actions >= 2:
            score += 0.2
        
        # Length comparison (Rushabh is typically concise)
        len_ratio = len(ira_response) / max(len(rushabh_response), 1)
        if 0.5 <= len_ratio <= 2.0:
            score += 0.3
        else:
            feedback_points.append(f"Response length differs significantly (ratio: {len_ratio:.1f})")
        
        # Check for overly formal language (Rushabh is direct)
        formal_markers = ['i would like to inform', 'please be advised', 'kindly note', 'we wish to']
        if any(f in ira_lower for f in formal_markers):
            score -= 0.5
            feedback_points.append("Too formal - Rushabh uses more direct language")
        
        # Ensure score is in range
        score = max(1.0, min(5.0, score))
        
        feedback = "; ".join(feedback_points) if feedback_points else "Good style match"
        return score, feedback
    
    def evaluate_accuracy(self, ira_response: str, rushabh_response: str, category: str) -> Tuple[float, str]:
        """Evaluate factual accuracy of the response."""
        score = 3.0
        feedback_points = []
        
        ira_lower = ira_response.lower()
        
        # Check for critical rule violations
        for rule_name, rule_info in CRITICAL_RULES.items():
            if 'violation_patterns' in rule_info:
                for pattern in rule_info['violation_patterns']:
                    if re.search(pattern, ira_lower, re.IGNORECASE):
                        score = 1.0
                        feedback_points.append(f"CRITICAL: Violated {rule_name} - {rule_info['rule']}")
                        return score, "; ".join(feedback_points)
        
        # Check if numbers/specs are mentioned - compare with Rushabh's
        ira_numbers = set(re.findall(r'\d+(?:\.\d+)?\s*(?:mm|kw|m³|kg|€|\$|%)', ira_lower))
        rushabh_numbers = set(re.findall(r'\d+(?:\.\d+)?\s*(?:mm|kw|m³|kg|€|\$|%)', rushabh_response.lower()))
        
        if rushabh_numbers:
            # Check how many specs match
            matching = ira_numbers.intersection(rushabh_numbers)
            match_ratio = len(matching) / len(rushabh_numbers)
            if match_ratio >= 0.5:
                score += 0.5
            elif match_ratio < 0.3:
                score -= 0.5
                feedback_points.append("Some specifications differ from Rushabh's response")
        
        # Check for machine model mentions
        ira_models = set(re.findall(r'PF1[-\s]?\w+|AM[-\s]?P?\s*\d*', ira_response, re.IGNORECASE))
        rushabh_models = set(re.findall(r'PF1[-\s]?\w+|AM[-\s]?P?\s*\d*', rushabh_response, re.IGNORECASE))
        
        if rushabh_models and ira_models:
            if ira_models.intersection(rushabh_models):
                score += 0.3
        
        score = max(1.0, min(5.0, score))
        feedback = "; ".join(feedback_points) if feedback_points else "Accurate response"
        return score, feedback
    
    def evaluate_completeness(self, ira_response: str, rushabh_response: str, question: str) -> Tuple[float, str]:
        """Evaluate if all parts of the question are addressed."""
        score = 3.0
        feedback_points = []
        missing = []
        
        question_lower = question.lower()
        ira_lower = ira_response.lower()
        rushabh_lower = rushabh_response.lower()
        
        # Check for question marks (multiple questions)
        question_count = question.count('?')
        if question_count > 1:
            # Multiple questions - check if response addresses them
            if len(ira_response) > len(question) * 2:
                score += 0.3
        
        # Check for key topics in question vs response
        key_topics = {
            'price': ['price', 'cost', 'quote', '€', '$'],
            'delivery': ['delivery', 'ship', 'timeline', 'when'],
            'specs': ['spec', 'dimension', 'size', 'thick', 'capacity'],
            'material': ['material', 'abs', 'hips', 'pp', 'pet'],
        }
        
        for topic, keywords in key_topics.items():
            if any(k in question_lower for k in keywords):
                # Topic mentioned in question - check if addressed
                if any(k in ira_lower for k in keywords):
                    score += 0.2
                elif any(k in rushabh_lower for k in keywords):
                    missing.append(topic)
                    score -= 0.2
        
        if missing:
            feedback_points.append(f"Missing topics: {', '.join(missing)}")
        
        # Compare paragraph count as completeness proxy
        ira_paras = len([p for p in ira_response.split('\n\n') if p.strip()])
        rushabh_paras = len([p for p in rushabh_response.split('\n\n') if p.strip()])
        
        if ira_paras >= rushabh_paras * 0.7:
            score += 0.2
        
        score = max(1.0, min(5.0, score))
        feedback = "; ".join(feedback_points) if feedback_points else "Complete response"
        return score, feedback
    
    def evaluate_technical_conversation(self, ira_response: str, rushabh_response: str, question: str) -> Tuple[float, str]:
        """
        Evaluate if IRA conducts technical sales conversations like Rushabh.
        
        This is NOT about style - it's about the SUBSTANCE of sales conversations:
        - Does IRA ask the right qualification questions?
        - Does IRA structure specs properly?
        - Does IRA break down services correctly?
        - Does IRA reference customer sites?
        """
        score = 3.0
        feedback_points = []
        
        ira_lower = ira_response.lower()
        rushabh_lower = rushabh_response.lower()
        question_lower = question.lower()
        
        # 1. Check if IRA asks qualification questions when appropriate
        # Rushabh often asks clarifying questions before giving final answers
        rushabh_asks = sum(1 for q in RUSHABH_TECHNICAL_PATTERNS['qualification_questions'] if q in rushabh_lower)
        ira_asks = sum(1 for q in RUSHABH_TECHNICAL_PATTERNS['qualification_questions'] if q in ira_lower)
        
        if rushabh_asks > 0:  # Rushabh asked questions
            if ira_asks >= rushabh_asks * 0.5:
                score += 0.4
            else:
                feedback_points.append("Rushabh asks qualification questions - IRA should too")
                score -= 0.3
        
        # 2. Check for structured specs (Config A vs Config B style)
        rushabh_structured = sum(1 for s in RUSHABH_TECHNICAL_PATTERNS['structured_specs'] if s in rushabh_lower)
        ira_structured = sum(1 for s in RUSHABH_TECHNICAL_PATTERNS['structured_specs'] if s in ira_lower)
        
        if rushabh_structured >= 3:  # Rushabh gave structured specs
            if ira_structured >= rushabh_structured * 0.5:
                score += 0.4
            else:
                feedback_points.append("Use structured format like Rushabh (Config A, Config B, price breakdown)")
                score -= 0.2
        
        # 3. Check for service breakdown (3 days dismantling, 3 days assembly, etc.)
        rushabh_service = sum(1 for s in RUSHABH_TECHNICAL_PATTERNS['service_breakdown'] if s in rushabh_lower)
        ira_service = sum(1 for s in RUSHABH_TECHNICAL_PATTERNS['service_breakdown'] if s in ira_lower)
        
        if rushabh_service >= 3:  # Rushabh broke down services
            if ira_service >= rushabh_service * 0.5:
                score += 0.3
            else:
                feedback_points.append("Break down services like Rushabh (X days for Y, total cost...)")
                score -= 0.2
        
        # 4. Check for reference site mentions
        if any(ref in rushabh_lower for ref in RUSHABH_TECHNICAL_PATTERNS['reference_sites']):
            if any(ref in ira_lower for ref in RUSHABH_TECHNICAL_PATTERNS['reference_sites']):
                score += 0.3
            else:
                feedback_points.append("Rushabh references customer sites - IRA should offer to show machines")
        
        # 5. Check if IRA provides numbers/specifics like Rushabh
        rushabh_numbers = len(re.findall(r'\d+', rushabh_response))
        ira_numbers = len(re.findall(r'\d+', ira_response))
        
        if rushabh_numbers >= 5:  # Rushabh provided specific numbers
            if ira_numbers >= rushabh_numbers * 0.5:
                score += 0.3
            else:
                feedback_points.append("Provide specific numbers like Rushabh does")
                score -= 0.2
        
        score = max(1.0, min(5.0, score))
        feedback = "; ".join(feedback_points) if feedback_points else "Good technical conversation patterns"
        return score, feedback
    
    def evaluate_sales_effectiveness(self, ira_response: str, rushabh_response: str) -> Tuple[float, str]:
        """Evaluate if the response moves the sale forward."""
        score = 3.0
        feedback_points = []
        
        ira_lower = ira_response.lower()
        
        # Check for call-to-action
        cta_patterns = [
            r'let me know',
            r'feel free to',
            r'call me',
            r'would you like',
            r'can we',
            r'shall we',
            r'happy to',
            r'send (you|me)',
        ]
        
        cta_count = sum(1 for p in cta_patterns if re.search(p, ira_lower))
        if cta_count >= 2:
            score += 0.5
            feedback_points.append("Good call-to-action")
        elif cta_count == 0:
            score -= 0.3
            feedback_points.append("Missing clear call-to-action")
        
        # Check for next steps
        next_step_patterns = ['next step', 'forward', 'follow up', 'schedule', 'arrange']
        if any(p in ira_lower for p in next_step_patterns):
            score += 0.3
        
        # Check for relationship building
        relationship_patterns = ['hope', 'looking forward', 'pleasure', 'thank you', 'appreciate']
        if any(p in ira_lower for p in relationship_patterns):
            score += 0.2
        
        # Penalize dead-end responses
        dead_end_patterns = ["i don't know", "not sure", "cannot help", "unfortunately"]
        if any(p in ira_lower for p in dead_end_patterns):
            score -= 0.5
            feedback_points.append("Response may close conversation prematurely")
        
        score = max(1.0, min(5.0, score))
        feedback = "; ".join(feedback_points) if feedback_points else "Sales-oriented response"
        return score, feedback
    
    def evaluate(
        self,
        question: str,
        ira_response: str,
        rushabh_response: str,
        question_id: str = "",
        category: str = "general"
    ) -> EvaluationResult:
        """Full evaluation of an IRA response."""
        self.evaluation_count += 1
        
        if not question_id:
            question_id = f"eval_{self.evaluation_count}"
        
        # Individual evaluations
        style_score, style_feedback = self.evaluate_style(ira_response, rushabh_response)
        accuracy_score, accuracy_feedback = self.evaluate_accuracy(ira_response, rushabh_response, category)
        completeness_score, completeness_feedback = self.evaluate_completeness(ira_response, rushabh_response, question)
        sales_score, sales_feedback = self.evaluate_sales_effectiveness(ira_response, rushabh_response)
        
        # NEW: Technical conversation evaluation (added 2026-02-28)
        tech_score, tech_feedback = self.evaluate_technical_conversation(ira_response, rushabh_response, question)
        
        # Overall score (weighted) - updated to include technical conversation
        # Style: 20% → 15%
        # Technical Conv: 30% (NEW)
        # Accuracy: 35% → 25%
        # Completeness: 25% → 15%
        # Sales: 20% → 15%
        overall = (
            style_score * 0.15 +
            tech_score * 0.30 +
            accuracy_score * 0.25 +
            completeness_score * 0.15 +
            sales_score * 0.15
        )
        
        # Identify differences
        key_differences = []
        missing_elements = []
        extra_elements = []
        
        # Check for topics in Rushabh's response not in IRA's
        rushabh_words = set(rushabh_response.lower().split())
        ira_words = set(ira_response.lower().split())
        
        important_words = ['pf1', 'am-p', 'price', 'cost', 'delivery', 'install', 'quote']
        for word in important_words:
            if word in rushabh_words and word not in ira_words:
                missing_elements.append(word)
            elif word in ira_words and word not in rushabh_words:
                extra_elements.append(word)
        
        # Critical failures
        critical_failures = []
        if accuracy_score <= 1.5:
            critical_failures.append("Accuracy failure - possible rule violation")
        if "CRITICAL" in accuracy_feedback:
            critical_failures.append(accuracy_feedback)
        
        # Pass/Fail (need overall >= 3.0 and no critical failures)
        passed = overall >= 3.0 and not critical_failures
        
        return EvaluationResult(
            question_id=question_id,
            category=category,
            style_score=style_score,
            accuracy_score=accuracy_score,
            completeness_score=completeness_score,
            sales_effectiveness_score=sales_score,
            technical_conversation_score=tech_score,
            overall_score=round(overall, 2),
            style_feedback=style_feedback,
            accuracy_feedback=accuracy_feedback,
            completeness_feedback=completeness_feedback,
            sales_feedback=sales_feedback,
            technical_feedback=tech_feedback,
            key_differences=key_differences,
            missing_elements=missing_elements,
            extra_elements=extra_elements,
            passed=passed,
            critical_failures=critical_failures,
        )


def main():
    """Test the evaluator with sample data."""
    print("="*70)
    print("  ATLAS EVALUATOR - TEST")
    print("="*70)
    
    evaluator = ResponseEvaluator()
    
    # Test case
    question = "What is the price for a PF1-1520 machine for food packaging?"
    
    rushabh_response = """Hi!

The PF1-1520 is a great choice for food packaging. Here's the pricing:

- PF1-1520 Base: €45,000
- With automatic feeding: €52,000

Let me know if you'd like a detailed quotation. Happy to arrange a call to discuss your specific requirements.

Cheers"""

    ira_response = """Hello,

Thank you for your inquiry about our PF1-1520 thermoforming machine.

The PF1-1520 has a forming area of 1500x2000mm and is suitable for food packaging applications. 

Pricing starts from approximately €45,000, subject to configuration and current pricing.

Would you like me to prepare a detailed quotation for your specific requirements?

Best regards"""

    result = evaluator.evaluate(
        question=question,
        ira_response=ira_response,
        rushabh_response=rushabh_response,
        category="pricing_inquiry"
    )
    
    print(f"\n--- Evaluation Result ---")
    print(f"Overall Score: {result.overall_score}/5.0")
    print(f"Passed: {result.passed}")
    print(f"\nScores:")
    print(f"  Style: {result.style_score}/5 - {result.style_feedback}")
    print(f"  Accuracy: {result.accuracy_score}/5 - {result.accuracy_feedback}")
    print(f"  Completeness: {result.completeness_score}/5 - {result.completeness_feedback}")
    print(f"  Sales: {result.sales_effectiveness_score}/5 - {result.sales_feedback}")
    
    if result.missing_elements:
        print(f"\nMissing: {result.missing_elements}")
    if result.critical_failures:
        print(f"\n⚠️  Critical: {result.critical_failures}")


if __name__ == "__main__":
    main()
