#!/usr/bin/env python3
"""
ATHENA Training Session
=======================

Runs a complete coaching session for IRA:
1. Load training data (Q&A pairs)
2. Present questions to IRA
3. Compare IRA's response to Rushabh's actual response
4. Score and provide coaching feedback
5. Generate learning report

Usage:
    python agents/athena/training_session.py
    python agents/athena/training_session.py --rounds 20
    python agents/athena/training_session.py --category pricing
"""

import argparse
import asyncio
import json
import random
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Use merged training set (European leads + Inquiry Form leads = 100 pairs)
TRAINING_DATA_FILE = PROJECT_ROOT / "data" / "training" / "athena_merged_training_set.json"
# Fallback to original if merged doesn't exist
if not TRAINING_DATA_FILE.exists():
    TRAINING_DATA_FILE = PROJECT_ROOT / "data" / "training" / "athena_training_set.json"
RESULTS_FILE = PROJECT_ROOT / "data" / "training" / "athena_session_results.json"


@dataclass
class CoachingFeedback:
    """Detailed coaching feedback for IRA."""
    overall_assessment: str
    style_coaching: str
    accuracy_coaching: str
    sales_coaching: str
    specific_improvements: List[str]
    exemplar_phrases: List[str]


@dataclass
class SessionResult:
    """Result of a single training round."""
    pair_id: str
    category: str
    company: str
    
    # Scores
    style_score: float
    accuracy_score: float
    completeness_score: float
    sales_score: float
    overall_score: float
    
    # Status
    passed: bool
    
    # Content
    question: str
    ira_response: str
    rushabh_response: str
    
    # Coaching
    feedback: CoachingFeedback


# Rushabh's signature style elements
RUSHABH_STYLE = {
    'greetings': ['Hi!', 'Hey', 'Hello', 'Hi there'],
    'closings': ['Cheers', 'Best', 'Thanks'],
    'warmth_phrases': ['happy to', 'glad to', 'no problem', 'sounds good', 'sure thing'],
    'action_phrases': ["Let me", "I'll", "I will", "Can we", "Let's"],
    'relationship_phrases': ['hope you are well', 'hope all is good', 'looking forward'],
}

# Critical rules IRA must follow
CRITICAL_RULES = {
    'AM_THICKNESS': {
        'description': 'AM series is for materials ≤1.5mm only',
        'violation_check': lambda q, r: ('am' in r.lower() and 
                                         any(f'{x}mm' in q.lower() for x in ['2', '3', '4', '5', '6', '8', '10'])),
    },
    'NO_FABRICATION': {
        'description': 'Never fabricate specifications',
        'violation_check': lambda q, r: False,  # Manual review needed
    },
    'PRICING_DISCLAIMER': {
        'description': 'Pricing should mention "subject to configuration"',
        'violation_check': lambda q, r: ('price' in q.lower() and 
                                         'subject to' not in r.lower() and
                                         '€' in r or '$' in r),
    },
}


class ATHENACoach:
    """ATHENA - IRA's personal coach."""
    
    def __init__(self):
        self.training_data = []
        self.session_results: List[SessionResult] = []
        self.round_count = 0
        
    def load_training_data(self, path: Path = TRAINING_DATA_FILE):
        """Load training data."""
        if not path.exists():
            print(f"[error] Training data not found: {path}")
            print("[hint] Run: python agents/athena/build_training_set.py")
            return False
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        self.training_data = data.get('pairs', [])
        print(f"[loaded] {len(self.training_data)} training pairs")
        return True
    
    async def get_ira_response(self, question: str) -> str:
        """Get IRA's response to a question."""
        try:
            # Try direct Python import
            from openclaw.agents.ira.src.agents import research, write, verify
            from openclaw.agents.ira.src.agents.chief_of_staff.agent import analyze_intent
            
            intent = analyze_intent(question)
            research_output = await research(question, {"intent": intent})
            context = {"intent": intent, "channel": "training", "research_output": research_output}
            draft = await write(question, context)
            verified = await verify(draft, question, context)
            
            return verified
            
        except ImportError:
            # Fallback: Return placeholder
            return "[IRA response would appear here - IRA modules not available]"
        except Exception as e:
            return f"[Error getting IRA response: {e}]"
    
    def evaluate_style(self, ira_response: str, rushabh_response: str) -> tuple[float, str]:
        """Evaluate style match."""
        score = 3.0
        feedback_parts = []
        
        ira = ira_response.lower()
        rush = rushabh_response.lower()
        
        # Check greeting
        has_greeting = any(g.lower() in ira[:50] for g in RUSHABH_STYLE['greetings'])
        if has_greeting:
            score += 0.3
        else:
            feedback_parts.append("Start with a warm greeting like Rushabh does ('Hi!', 'Hey')")
        
        # Check warmth
        warmth_count = sum(1 for p in RUSHABH_STYLE['warmth_phrases'] if p in ira)
        if warmth_count >= 1:
            score += 0.3
        else:
            feedback_parts.append("Add warmth phrases: 'happy to help', 'sounds good'")
        
        # Check action orientation
        action_count = sum(1 for p in RUSHABH_STYLE['action_phrases'] if p.lower() in ira)
        if action_count >= 1:
            score += 0.2
        else:
            feedback_parts.append("Be more action-oriented: 'Let me...', 'I will...'")
        
        # Check length (Rushabh is concise)
        len_ratio = len(ira_response) / max(len(rushabh_response), 1)
        if len_ratio > 2.5:
            score -= 0.3
            feedback_parts.append("Response too long - Rushabh is more concise")
        elif len_ratio < 0.3:
            score -= 0.2
            feedback_parts.append("Response too short - provide more detail")
        
        # Check for overly formal language
        formal_phrases = ['i would like to inform you', 'please be advised', 'kindly note']
        if any(f in ira for f in formal_phrases):
            score -= 0.4
            feedback_parts.append("Too formal! Rushabh uses casual, direct language")
        
        score = max(1.0, min(5.0, score))
        coaching = " | ".join(feedback_parts) if feedback_parts else "Good style match!"
        
        return score, coaching
    
    def evaluate_accuracy(self, ira_response: str, question: str, rushabh_response: str) -> tuple[float, str]:
        """Evaluate factual accuracy."""
        score = 3.5
        feedback_parts = []
        
        # Check critical rules
        for rule_name, rule_info in CRITICAL_RULES.items():
            if rule_info['violation_check'](question, ira_response):
                score = 1.0
                feedback_parts.append(f"CRITICAL VIOLATION: {rule_info['description']}")
                return score, " | ".join(feedback_parts)
        
        # Check if key specs mentioned in Rushabh's response are in IRA's
        rush_specs = set(ira_re for ira_re in [
            r'\d+\s*mm', r'\d+\s*kw', r'€\s*[\d,]+', r'\$\s*[\d,]+'
        ] if ira_re)  # Placeholder for actual regex matching
        
        # Check machine models
        rush_models = ['pf1', 'am-p', 'pf1-x', 'am series']
        for model in rush_models:
            if model in rushabh_response.lower() and model not in ira_response.lower():
                score -= 0.2
                feedback_parts.append(f"Rushabh mentioned {model.upper()} - consider including")
        
        score = max(1.0, min(5.0, score))
        coaching = " | ".join(feedback_parts) if feedback_parts else "Accurate response"
        
        return score, coaching
    
    def evaluate_completeness(self, ira_response: str, question: str) -> tuple[float, str]:
        """Evaluate if all parts of question are addressed."""
        score = 3.5
        feedback_parts = []
        
        # Count question marks (multiple questions?)
        q_count = question.count('?')
        if q_count > 1:
            # Check if response is substantial enough
            if len(ira_response) < 200:
                score -= 0.3
                feedback_parts.append("Multiple questions asked - provide fuller response")
        
        # Check for key topics
        topics = {
            'price': ['price', 'cost', 'quote', '€', '$'],
            'delivery': ['delivery', 'ship', 'timeline', 'when'],
            'specs': ['spec', 'dimension', 'thick', 'size'],
        }
        
        for topic, keywords in topics.items():
            if any(k in question.lower() for k in keywords):
                if not any(k in ira_response.lower() for k in keywords):
                    score -= 0.2
                    feedback_parts.append(f"Question asked about {topic} - address it")
        
        score = max(1.0, min(5.0, score))
        coaching = " | ".join(feedback_parts) if feedback_parts else "Complete response"
        
        return score, coaching
    
    def evaluate_sales_effectiveness(self, ira_response: str) -> tuple[float, str]:
        """Evaluate sales effectiveness."""
        score = 3.0
        feedback_parts = []
        
        ira = ira_response.lower()
        
        # Check for call-to-action
        cta_phrases = ['let me know', 'feel free', 'happy to', 'can we', 'shall we', 'would you like']
        cta_count = sum(1 for p in cta_phrases if p in ira)
        if cta_count >= 2:
            score += 0.5
        elif cta_count == 0:
            score -= 0.3
            feedback_parts.append("Add a call-to-action: 'Let me know if you need more details'")
        
        # Check for next steps
        next_step_phrases = ['next step', 'follow up', 'schedule', 'arrange', 'send you']
        if any(p in ira for p in next_step_phrases):
            score += 0.3
        
        # Penalize dead-ends
        dead_end_phrases = ["i don't know", "not sure", "cannot help", "unfortunately we"]
        if any(p in ira for p in dead_end_phrases):
            score -= 0.4
            feedback_parts.append("Avoid dead-end language - always offer an alternative")
        
        score = max(1.0, min(5.0, score))
        coaching = " | ".join(feedback_parts) if feedback_parts else "Good sales approach"
        
        return score, coaching
    
    def generate_coaching(self, 
                         style_score: float, style_feedback: str,
                         accuracy_score: float, accuracy_feedback: str,
                         completeness_score: float, completeness_feedback: str,
                         sales_score: float, sales_feedback: str,
                         rushabh_response: str) -> CoachingFeedback:
        """Generate comprehensive coaching feedback."""
        
        # Overall assessment
        avg_score = (style_score + accuracy_score + completeness_score + sales_score) / 4
        if avg_score >= 4.0:
            overall = "Excellent! You're communicating like Rushabh. Keep it up."
        elif avg_score >= 3.0:
            overall = "Good response, but there's room for improvement. Study the feedback."
        elif avg_score >= 2.0:
            overall = "This response needs work. Focus on the specific improvements below."
        else:
            overall = "Critical issues found. Review Rushabh's response carefully."
        
        # Extract exemplar phrases from Rushabh's response
        exemplars = []
        rush_lines = rushabh_response.split('\n')
        for line in rush_lines[:5]:
            line = line.strip()
            if 10 < len(line) < 100:
                exemplars.append(line)
        
        # Specific improvements
        improvements = []
        if style_feedback != "Good style match!":
            improvements.extend(style_feedback.split(' | '))
        if "CRITICAL" in accuracy_feedback:
            improvements.insert(0, accuracy_feedback)
        elif accuracy_feedback != "Accurate response":
            improvements.extend(accuracy_feedback.split(' | '))
        if completeness_feedback != "Complete response":
            improvements.extend(completeness_feedback.split(' | '))
        if sales_feedback != "Good sales approach":
            improvements.extend(sales_feedback.split(' | '))
        
        return CoachingFeedback(
            overall_assessment=overall,
            style_coaching=style_feedback,
            accuracy_coaching=accuracy_feedback,
            sales_coaching=sales_feedback,
            specific_improvements=improvements[:5],
            exemplar_phrases=exemplars[:3],
        )
    
    async def run_round(self, pair: Dict) -> SessionResult:
        """Run a single training round."""
        self.round_count += 1
        
        question = pair.get('customer_question', '')
        rushabh_response = pair.get('rushabh_response', '')
        
        # Get IRA's response
        ira_response = await self.get_ira_response(question)
        
        # Evaluate
        style_score, style_feedback = self.evaluate_style(ira_response, rushabh_response)
        accuracy_score, accuracy_feedback = self.evaluate_accuracy(ira_response, question, rushabh_response)
        completeness_score, completeness_feedback = self.evaluate_completeness(ira_response, question)
        sales_score, sales_feedback = self.evaluate_sales_effectiveness(ira_response)
        
        # Overall score
        overall_score = (
            style_score * 0.25 +
            accuracy_score * 0.35 +
            completeness_score * 0.20 +
            sales_score * 0.20
        )
        
        # Generate coaching
        feedback = self.generate_coaching(
            style_score, style_feedback,
            accuracy_score, accuracy_feedback,
            completeness_score, completeness_feedback,
            sales_score, sales_feedback,
            rushabh_response
        )
        
        passed = overall_score >= 3.0 and "CRITICAL" not in accuracy_feedback
        
        result = SessionResult(
            pair_id=pair.get('id', f'round_{self.round_count}'),
            category=pair.get('category', 'general'),
            company=pair.get('company', 'Unknown'),
            style_score=round(style_score, 2),
            accuracy_score=round(accuracy_score, 2),
            completeness_score=round(completeness_score, 2),
            sales_score=round(sales_score, 2),
            overall_score=round(overall_score, 2),
            passed=passed,
            question=question[:500],
            ira_response=ira_response[:500],
            rushabh_response=rushabh_response[:500],
            feedback=feedback,
        )
        
        self.session_results.append(result)
        return result
    
    async def run_session(self, rounds: int = 10, category: str = None):
        """Run a complete training session."""
        print(f"\n{'='*70}")
        print("  ATHENA TRAINING SESSION")
        print(f"{'='*70}")
        print(f"  'I don't just test you, IRA. I make you better.'")
        print(f"{'='*70}\n")
        
        # Filter by category if specified
        available = self.training_data
        if category:
            available = [p for p in available if p.get('category') == category]
            print(f"[filter] Category: {category} ({len(available)} pairs)")
        
        if not available:
            print("[error] No training pairs available")
            return
        
        # Select pairs for this session
        selected = random.sample(available, min(rounds, len(available)))
        print(f"[session] Running {len(selected)} training rounds...\n")
        
        # Run rounds
        for i, pair in enumerate(selected, 1):
            print(f"Round {i}/{len(selected)} [{pair.get('category')}]...", end=' ', flush=True)
            
            result = await self.run_round(pair)
            
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"{status} ({result.overall_score}/5.0)")
            
            if not result.passed:
                print(f"    Coach: {result.feedback.overall_assessment}")
        
        # Print session summary
        self._print_session_summary()
    
    def _print_session_summary(self):
        """Print session summary."""
        if not self.session_results:
            return
        
        passed = sum(1 for r in self.session_results if r.passed)
        total = len(self.session_results)
        pass_rate = passed / total * 100
        
        avg_overall = sum(r.overall_score for r in self.session_results) / total
        avg_style = sum(r.style_score for r in self.session_results) / total
        avg_accuracy = sum(r.accuracy_score for r in self.session_results) / total
        avg_sales = sum(r.sales_score for r in self.session_results) / total
        
        print(f"\n{'='*70}")
        print("  SESSION SUMMARY")
        print(f"{'='*70}")
        print(f"""
Rounds Completed:    {total}
Passed:              {passed} ({pass_rate:.0f}%)
Failed:              {total - passed}

Average Scores:
  Overall:           {avg_overall:.2f}/5.0
  Style:             {avg_style:.2f}/5.0
  Accuracy:          {avg_accuracy:.2f}/5.0
  Sales:             {avg_sales:.2f}/5.0
""")
        
        # Top coaching points
        all_improvements = []
        for r in self.session_results:
            all_improvements.extend(r.feedback.specific_improvements)
        
        if all_improvements:
            print("Top Coaching Points:")
            # Count frequency
            from collections import Counter
            common = Counter(all_improvements).most_common(5)
            for improvement, count in common:
                print(f"  • {improvement} ({count}x)")
    
    def save_results(self, path: Path = RESULTS_FILE):
        """Save session results."""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'session_timestamp': datetime.now().isoformat(),
            'total_rounds': len(self.session_results),
            'passed': sum(1 for r in self.session_results if r.passed),
            'results': [asdict(r) for r in self.session_results],
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"\n[saved] Session results → {path}")


async def main():
    parser = argparse.ArgumentParser(description="ATHENA Training Session")
    parser.add_argument('--rounds', type=int, default=10, help="Number of training rounds")
    parser.add_argument('--category', type=str, default=None, help="Filter by category")
    parser.add_argument('--data', type=str, default=str(TRAINING_DATA_FILE))
    args = parser.parse_args()
    
    coach = ATHENACoach()
    
    if not coach.load_training_data(Path(args.data)):
        return 1
    
    await coach.run_session(rounds=args.rounds, category=args.category)
    
    coach.save_results()
    
    return 0


if __name__ == "__main__":
    asyncio.run(main())
