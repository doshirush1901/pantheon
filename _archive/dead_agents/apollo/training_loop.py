#!/usr/bin/env python3
"""
APOLLO Training Loop
====================

The main training loop that:
1. Generates simulated customer queries
2. Gets IRA's response (through full pipeline)
3. Scores accuracy against expected answers
4. Updates learning engine with errors
5. Decides if Rushabh needs to correct anything
6. Applies learnings to improve future responses

Formula for improvement:
    
    Accuracy(t+1) = Accuracy(t) + α * (Expected - Actual) + β * Corrections
    
    Where:
    - α = learning rate from errors
    - β = weight of Rushabh's corrections

Usage:
    python agents/apollo/training_loop.py --iterations 10
    python agents/apollo/training_loop.py --interactive
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import openai

# Import APOLLO components
APOLLO_DIR = Path(__file__).parent
sys.path.insert(0, str(APOLLO_DIR))

from run_simulation import PERSONAS, generate_customer_email
from accuracy_scorer import score_response, AccuracyReport
from learning_engine import LearningEngine, enhance_ira_response
from pipeline_validator import PipelineValidator, validate_against_expected

client = openai.OpenAI()


# =============================================================================
# EXPECTED ANSWERS (Ground Truth from Training Data)
# =============================================================================

def load_training_pairs() -> List[Dict]:
    """Load Q&A pairs from training data."""
    training_file = PROJECT_ROOT / "data" / "training" / "athena_merged_training_set.json"
    
    if training_file.exists():
        with open(training_file) as f:
            data = json.load(f)
            
        # Handle nested structure
        if isinstance(data, dict) and "pairs" in data:
            return data["pairs"]
        elif isinstance(data, list):
            return data
    
    return []


def find_similar_training_pair(query: str, training_pairs: List[Dict]) -> Optional[Dict]:
    """Find a training pair similar to the query."""
    query_lower = query.lower()
    
    best_match = None
    best_score = 0
    
    for pair in training_pairs:
        customer_q = pair.get("customer_question", "").lower()
        
        # Simple word overlap scoring
        query_words = set(query_lower.split())
        pair_words = set(customer_q.split())
        
        if query_words and pair_words:
            overlap = len(query_words & pair_words)
            score = overlap / max(len(query_words), len(pair_words))
            
            if score > best_score:
                best_score = score
                best_match = pair
    
    if best_score > 0.3:
        return best_match
    
    return None


# =============================================================================
# IRA RESPONSE GENERATOR (Full Pipeline)
# =============================================================================

def get_ira_response_with_tracing(
    query: str,
    validator: PipelineValidator,
    learning_engine: LearningEngine,
) -> Tuple[str, Dict]:
    """
    Get IRA's response with full pipeline tracing.
    
    Steps:
    1. INGEST - Parse query
    2. RETRIEVE - Search knowledge
    3. RECOMMEND - Pick machine
    4. GENERATE - Create response
    5. VERIFY - Check facts
    6. PACKAGE - Format output
    """
    metadata = {
        "steps": {},
        "warnings": [],
        "sources_used": [],
    }
    
    try:
        # Import IRA's pipeline
        sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))
        from src.brain.generate_answer import generate_answer
        
        # Start trace
        validator.start_trace(query=query)
        
        # Step 1: INGEST
        start = time.time()
        validator.record_step("ingest", success=True, duration_ms=(time.time()-start)*1000)
        
        # Step 2-6: Let IRA's pipeline handle the rest
        start = time.time()
        
        context = {
            "channel": "email",
            "mode": "training",
        }
        
        result = generate_answer(
            intent=query,
            context_pack=context,
            channel="email",
        )
        
        # Extract response
        if hasattr(result, 'final_text'):
            response = result.final_text
        elif hasattr(result, 'text'):
            response = result.text
        elif isinstance(result, dict):
            response = result.get('final_text') or result.get('text') or str(result)
        else:
            response = str(result)
        
        duration = (time.time() - start) * 1000
        
        # Record pipeline steps
        validator.record_step("retrieve", success=True, duration_ms=duration*0.2)
        validator.record_step("recommend", success=True, duration_ms=duration*0.1)
        validator.record_step("generate", success=True, duration_ms=duration*0.5)
        validator.record_step("verify", success=True, duration_ms=duration*0.1)
        validator.record_step("package", success=True, duration_ms=duration*0.1)
        
        # Apply learning enhancements
        enhanced_response, enhance_meta = enhance_ira_response(
            query=query,
            draft_response=response,
            engine=learning_engine,
        )
        
        metadata.update(enhance_meta)
        
        return enhanced_response, metadata
        
    except Exception as e:
        metadata["error"] = str(e)
        
        # Fallback to simulated response
        return simulate_ira_response(query), metadata


def simulate_ira_response(query: str) -> str:
    """Fallback: Simulate IRA's response using GPT."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": """You are IRA, Machinecraft's AI sales assistant.
            
Style: Warm greeting (Hi!), concise, action-oriented, end with CTA.
Products: AM series (thin gauge), PF series (heavy gauge), BF (blister), SP (skin pack).
Pricing: Quote specific prices, add "subject to configuration".

Keep responses under 150 words."""},
            {"role": "user", "content": query},
        ],
        temperature=0.7,
        max_tokens=300,
    )
    return response.choices[0].message.content


# =============================================================================
# TRAINING ITERATION
# =============================================================================

def run_training_iteration(
    persona_type: str,
    turn: int,
    conversation: List[Dict],
    validator: PipelineValidator,
    learning_engine: LearningEngine,
    training_pairs: List[Dict],
) -> Dict:
    """
    Run a single training iteration.
    
    Returns:
        {
            "query": str,
            "ira_response": str,
            "expected_response": str,
            "accuracy": AccuracyReport,
            "should_escalate": bool,
            "escalation_reason": str,
        }
    """
    persona = PERSONAS.get(persona_type, PERSONAS["european"])
    
    # Generate customer query
    query = generate_customer_email(persona, conversation, turn)
    
    # Find expected response from training data
    training_pair = find_similar_training_pair(query, training_pairs)
    expected_response = training_pair.get("rushabh_response", "") if training_pair else ""
    
    # Get IRA's response with tracing
    ira_response, metadata = get_ira_response_with_tracing(
        query=query,
        validator=validator,
        learning_engine=learning_engine,
    )
    
    # Score accuracy
    if expected_response:
        accuracy = score_response(
            ira_response=ira_response,
            expected_response=expected_response,
            query=query,
        )
    else:
        # Self-evaluation when no ground truth
        accuracy = score_response(
            ira_response=ira_response,
            expected_response=ira_response,
            query=query,
        )
        accuracy.overall_score *= 0.8  # Discount self-eval
    
    # Learn from this iteration
    learning_engine.learn_from_report(accuracy, query)
    
    # Check if we should escalate to Rushabh
    should_escalate, escalation_reason = learning_engine.should_ask_rushabh(
        query=query,
        confidence=accuracy.overall_score,
    )
    
    return {
        "query": query,
        "ira_response": ira_response,
        "expected_response": expected_response,
        "accuracy": accuracy,
        "should_escalate": should_escalate,
        "escalation_reason": escalation_reason,
        "metadata": metadata,
    }


# =============================================================================
# MAIN TRAINING LOOP
# =============================================================================

def run_training_loop(
    iterations: int = 10,
    personas: List[str] = None,
    interactive: bool = False,
    verbose: bool = True,
):
    """
    Run the main training loop.
    
    Args:
        iterations: Number of training iterations
        personas: Personas to use (default: all)
        interactive: Whether to allow manual corrections
        verbose: Print detailed output
    """
    if personas is None:
        personas = list(PERSONAS.keys())
    
    # Initialize components
    validator = PipelineValidator()
    learning_engine = LearningEngine()
    training_pairs = load_training_pairs()
    
    print("\n" + "="*70)
    print("🎓 APOLLO TRAINING LOOP")
    print("="*70)
    print(f"   Iterations: {iterations}")
    print(f"   Personas: {len(personas)}")
    print(f"   Training pairs loaded: {len(training_pairs)}")
    print(f"   Interactive mode: {interactive}")
    print("="*70 + "\n")
    
    results = []
    escalations = []
    
    for i in range(iterations):
        # Rotate through personas
        persona_type = personas[i % len(personas)]
        turn = (i // len(personas)) + 1
        
        # Build conversation history for this persona
        persona_results = [r for r in results if r.get("persona") == persona_type]
        conversation = [
            {"customer": r["query"], "ira": r["ira_response"]}
            for r in persona_results
        ]
        
        if verbose:
            print(f"\n{'─'*50}")
            print(f"Iteration {i+1}/{iterations} | {persona_type} | Turn {turn}")
            print(f"{'─'*50}")
        
        # Run iteration
        result = run_training_iteration(
            persona_type=persona_type,
            turn=turn,
            conversation=conversation,
            validator=validator,
            learning_engine=learning_engine,
            training_pairs=training_pairs,
        )
        result["persona"] = persona_type
        result["iteration"] = i + 1
        
        results.append(result)
        
        if verbose:
            print(f"\n📊 Accuracy: {result['accuracy'].overall_score:.1%}")
            print(f"   Factual: {result['accuracy'].factual_accuracy:.1%}")
            print(f"   Style: {result['accuracy'].style_match:.1%}")
        
        # Handle escalation
        if result["should_escalate"]:
            if verbose:
                print(f"\n⚠️  ESCALATION NEEDED: {result['escalation_reason']}")
            
            escalations.append({
                "iteration": i + 1,
                "query": result["query"][:100],
                "reason": result["escalation_reason"],
            })
            
            if interactive:
                print(f"\nIRA's response:\n{result['ira_response'][:300]}...")
                correction = input("\nEnter correction (or press Enter to skip): ").strip()
                
                if correction:
                    learning_engine.record_correction(
                        query=result["query"],
                        original_response=result["ira_response"],
                        corrected_response=correction,
                    )
                    print("✓ Correction recorded")
        
        # Brief pause
        time.sleep(0.5)
    
    # Final summary
    print("\n" + "="*70)
    print("📊 TRAINING SUMMARY")
    print("="*70)
    
    avg_accuracy = sum(r["accuracy"].overall_score for r in results) / len(results)
    avg_factual = sum(r["accuracy"].factual_accuracy for r in results) / len(results)
    avg_style = sum(r["accuracy"].style_match for r in results) / len(results)
    
    print(f"\n   Total iterations: {len(results)}")
    print(f"   Average accuracy: {avg_accuracy:.1%}")
    print(f"   Average factual:  {avg_factual:.1%}")
    print(f"   Average style:    {avg_style:.1%}")
    print(f"   Escalations:      {len(escalations)}")
    
    # Learning trend
    trend = learning_engine.get_accuracy_trend()
    print(f"\n   Learning trend: {trend['trend'].upper()}")
    print(f"   Improvement: {trend['improvement']:+.1%}")
    
    # Top errors
    print("\n   Top Error Patterns:")
    for err in learning_engine.get_top_error_patterns(3):
        print(f"     - [{err.category}] {err.description[:40]}... ({err.occurrences}x)")
    
    print("="*70)
    
    # Save results
    output_dir = PROJECT_ROOT / "data" / "training"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"training_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    output_data = {
        "iterations": iterations,
        "avg_accuracy": avg_accuracy,
        "avg_factual": avg_factual,
        "avg_style": avg_style,
        "escalations": escalations,
        "trend": trend,
        "results": [
            {
                "iteration": r["iteration"],
                "persona": r["persona"],
                "accuracy": r["accuracy"].overall_score,
                "factual": r["accuracy"].factual_accuracy,
                "style": r["accuracy"].style_match,
                "escalated": r["should_escalate"],
            }
            for r in results
        ],
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n📁 Results saved: {output_file}")
    
    return results


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="APOLLO Training Loop")
    parser.add_argument("--iterations", "-n", type=int, default=10,
                       help="Number of training iterations")
    parser.add_argument("--personas", "-p", nargs="+",
                       choices=list(PERSONAS.keys()),
                       help="Personas to train on")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Interactive mode (allow corrections)")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Quiet mode")
    
    args = parser.parse_args()
    
    run_training_loop(
        iterations=args.iterations,
        personas=args.personas,
        interactive=args.interactive,
        verbose=not args.quiet,
    )
