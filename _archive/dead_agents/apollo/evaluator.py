#!/usr/bin/env python3
"""
APOLLO Simulation Evaluator
============================

Evaluates IRA's performance in sales simulations using LLM-as-judge.

Usage:
    python agents/apollo/evaluator.py --file data/simulations/sim_*.json
"""

import os
import sys
import json
import glob
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import openai

client = openai.OpenAI()


# =============================================================================
# EVALUATION CRITERIA
# =============================================================================

EVALUATION_PROMPT = """You are an expert sales trainer evaluating AI sales conversations.

Review this sales conversation between a customer and IRA (an AI sales assistant for Machinecraft Technologies, a thermoforming machine manufacturer).

EVALUATION CRITERIA (Score 1-5 for each):

1. **RESPONSE RELEVANCE** (Does IRA answer what the customer asked?)
   - 5: Directly answers all questions with specific details
   - 3: Answers most questions but misses some points
   - 1: Off-topic or misses the main question

2. **TECHNICAL ACCURACY** (Is the information correct?)
   - 5: All specs, prices, features are accurate
   - 3: Mostly accurate with minor issues
   - 1: Contains significant errors or hallucinations

3. **SALES EFFECTIVENESS** (Does IRA move the deal forward?)
   - 5: Excellent - asks qualifying questions, creates urgency, proposes next steps
   - 3: Adequate - provides info but passive
   - 1: Poor - missed opportunities, no call-to-action

4. **TONE & PROFESSIONALISM** (Does IRA sound like a helpful salesperson?)
   - 5: Warm, professional, confident, consultative
   - 3: Professional but robotic or overly formal
   - 1: Cold, impersonal, or inappropriate

5. **CONCISENESS** (Is the response appropriately sized?)
   - 5: Perfect length - complete but not verbose
   - 3: Slightly too long or too short
   - 1: Way too long/short, misses key info or overwhelms

CUSTOMER PROFILE:
{customer_profile}

CONVERSATION:
{conversation}

Provide your evaluation in this JSON format:
{{
    "scores": {{
        "relevance": <1-5>,
        "technical_accuracy": <1-5>,
        "sales_effectiveness": <1-5>,
        "tone": <1-5>,
        "conciseness": <1-5>
    }},
    "overall_score": <1-5>,
    "strengths": ["..."],
    "improvements": ["..."],
    "deal_likelihood": "<high/medium/low>",
    "key_observations": "..."
}}"""


# =============================================================================
# EVALUATOR
# =============================================================================

@dataclass
class EvaluationResult:
    """Result of evaluating a single simulation."""
    simulation_file: str
    persona_name: str
    persona_company: str
    total_turns: int
    scores: Dict[str, float]
    overall_score: float
    strengths: List[str]
    improvements: List[str]
    deal_likelihood: str
    key_observations: str
    evaluated_at: str


def evaluate_simulation(simulation_data: Dict) -> EvaluationResult:
    """Evaluate a single simulation using LLM-as-judge."""
    
    persona = simulation_data.get("persona", {})
    conversation = simulation_data.get("conversation", [])
    
    # Format customer profile
    customer_profile = f"""
Name: {persona.get('name', 'Unknown')}
Company: {persona.get('company', 'Unknown')}
Industry: {persona.get('industry', 'Unknown')}
Location: {persona.get('location', 'Unknown')}
Budget: {persona.get('currency', '')} {persona.get('budget', 'Unknown')}
Requirements: {json.dumps(persona.get('requirements', {}), indent=2)}
"""
    
    # Format conversation
    conv_text = ""
    for turn in conversation:
        conv_text += f"\n--- Turn {turn.get('turn', '?')} ---\n"
        conv_text += f"CUSTOMER:\n{turn.get('customer', '')}\n\n"
        conv_text += f"IRA:\n{turn.get('ira', '')}\n"
    
    # Get evaluation from GPT
    prompt = EVALUATION_PROMPT.format(
        customer_profile=customer_profile,
        conversation=conv_text,
    )
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert sales trainer. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    
    # Parse evaluation
    try:
        eval_data = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        eval_data = {
            "scores": {"relevance": 3, "technical_accuracy": 3, "sales_effectiveness": 3, "tone": 3, "conciseness": 3},
            "overall_score": 3,
            "strengths": [],
            "improvements": [],
            "deal_likelihood": "medium",
            "key_observations": "Evaluation parsing failed",
        }
    
    return EvaluationResult(
        simulation_file=simulation_data.get("_file", "unknown"),
        persona_name=persona.get("name", "Unknown"),
        persona_company=persona.get("company", "Unknown"),
        total_turns=len(conversation),
        scores=eval_data.get("scores", {}),
        overall_score=eval_data.get("overall_score", 3.0),
        strengths=eval_data.get("strengths", []),
        improvements=eval_data.get("improvements", []),
        deal_likelihood=eval_data.get("deal_likelihood", "medium"),
        key_observations=eval_data.get("key_observations", ""),
        evaluated_at=datetime.now().isoformat(),
    )


def evaluate_all_simulations(pattern: str = "data/simulations/sim_*.json") -> List[EvaluationResult]:
    """Evaluate all simulations matching the pattern."""
    
    results = []
    files = glob.glob(str(PROJECT_ROOT / pattern))
    
    print(f"\n🔍 Found {len(files)} simulation(s) to evaluate\n")
    
    for filepath in files:
        print(f"📊 Evaluating: {Path(filepath).name}...")
        
        with open(filepath) as f:
            data = json.load(f)
            data["_file"] = filepath
        
        result = evaluate_simulation(data)
        results.append(result)
        
        # Quick summary
        print(f"   Overall Score: {result.overall_score}/5")
        print(f"   Deal Likelihood: {result.deal_likelihood}")
    
    return results


def generate_report(results: List[EvaluationResult]) -> str:
    """Generate a summary report of all evaluations."""
    
    if not results:
        return "No simulations to evaluate."
    
    # Calculate averages
    avg_overall = sum(r.overall_score for r in results) / len(results)
    avg_scores = {}
    for key in ["relevance", "technical_accuracy", "sales_effectiveness", "tone", "conciseness"]:
        avg_scores[key] = sum(r.scores.get(key, 3) for r in results) / len(results)
    
    # Collect common improvements
    all_improvements = []
    for r in results:
        all_improvements.extend(r.improvements)
    
    # Build report
    report = f"""
================================================================================
                        APOLLO SIMULATION EVALUATION REPORT
                        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
================================================================================

📊 SUMMARY
   Simulations Evaluated: {len(results)}
   Average Overall Score: {avg_overall:.2f}/5

📈 CATEGORY SCORES (Average)
   Relevance:           {avg_scores.get('relevance', 0):.2f}/5
   Technical Accuracy:  {avg_scores.get('technical_accuracy', 0):.2f}/5
   Sales Effectiveness: {avg_scores.get('sales_effectiveness', 0):.2f}/5
   Tone & Professionalism: {avg_scores.get('tone', 0):.2f}/5
   Conciseness:         {avg_scores.get('conciseness', 0):.2f}/5

🎯 DEAL OUTCOMES
   High Likelihood:  {sum(1 for r in results if r.deal_likelihood == 'high')}
   Medium Likelihood: {sum(1 for r in results if r.deal_likelihood == 'medium')}
   Low Likelihood:   {sum(1 for r in results if r.deal_likelihood == 'low')}

📝 INDIVIDUAL RESULTS
"""
    
    for i, r in enumerate(results, 1):
        report += f"""
   {i}. {r.persona_name} ({r.persona_company})
      Turns: {r.total_turns} | Score: {r.overall_score}/5 | Deal: {r.deal_likelihood}
      Strengths: {', '.join(r.strengths[:2]) if r.strengths else 'N/A'}
      Improvements: {', '.join(r.improvements[:2]) if r.improvements else 'N/A'}
"""
    
    # Common improvements
    if all_improvements:
        from collections import Counter
        common = Counter(all_improvements).most_common(5)
        report += "\n🔧 TOP AREAS FOR IMPROVEMENT\n"
        for item, count in common:
            report += f"   - {item} (mentioned {count}x)\n"
    
    report += """
================================================================================
"""
    
    return report


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="APOLLO Simulation Evaluator")
    parser.add_argument("--pattern", "-p", type=str, 
                       default="data/simulations/sim_*.json",
                       help="Glob pattern for simulation files")
    parser.add_argument("--output", "-o", type=str,
                       help="Output file for report (default: stdout)")
    
    args = parser.parse_args()
    
    # Run evaluation
    results = evaluate_all_simulations(args.pattern)
    
    if results:
        report = generate_report(results)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"\n📄 Report saved to: {args.output}")
        else:
            print(report)
        
        # Save detailed results
        output_dir = PROJECT_ROOT / "data" / "simulations"
        results_file = output_dir / f"evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        results_data = [
            {
                "file": r.simulation_file,
                "persona": r.persona_name,
                "company": r.persona_company,
                "turns": r.total_turns,
                "scores": r.scores,
                "overall_score": r.overall_score,
                "strengths": r.strengths,
                "improvements": r.improvements,
                "deal_likelihood": r.deal_likelihood,
                "observations": r.key_observations,
            }
            for r in results
        ]
        
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"📊 Detailed results saved to: {results_file}")
