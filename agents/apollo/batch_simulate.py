#!/usr/bin/env python3
"""
APOLLO Batch Simulation Runner
===============================

Runs multiple sales simulations across different personas and generates
a comprehensive evaluation report.

Usage:
    python agents/apollo/batch_simulate.py                    # All personas, 4 turns each
    python agents/apollo/batch_simulate.py --turns 6          # 6 turns per simulation
    python agents/apollo/batch_simulate.py --personas european indian_auto  # Specific personas
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Import simulation components
from run_simulation import PERSONAS, generate_customer_email, get_ira_response, save_simulation
from evaluator import evaluate_simulation, generate_report, EvaluationResult


# =============================================================================
# BATCH SIMULATION
# =============================================================================

def run_batch_simulation(
    personas: List[str] = None,
    turns_per_simulation: int = 4,
    use_real_ira: bool = True,
    verbose: bool = True,
) -> Dict:
    """
    Run simulations for multiple personas and evaluate results.
    
    Args:
        personas: List of persona keys to simulate (default: all)
        turns_per_simulation: Number of conversation turns per simulation
        use_real_ira: Use real IRA vs GPT simulation
        verbose: Print progress
    
    Returns:
        Dict with simulation results and evaluation report
    """
    
    if personas is None:
        personas = list(PERSONAS.keys())
    
    results = {
        "started_at": datetime.now().isoformat(),
        "config": {
            "personas": personas,
            "turns": turns_per_simulation,
            "use_real_ira": use_real_ira,
        },
        "simulations": [],
        "evaluations": [],
    }
    
    if verbose:
        print("\n" + "="*70)
        print("🚀 APOLLO BATCH SIMULATION")
        print("="*70)
        print(f"   Personas: {len(personas)}")
        print(f"   Turns per simulation: {turns_per_simulation}")
        print(f"   Using: {'Real IRA' if use_real_ira else 'Simulated IRA'}")
        print("="*70 + "\n")
    
    for idx, persona_key in enumerate(personas, 1):
        if persona_key not in PERSONAS:
            print(f"⚠️  Unknown persona: {persona_key}, skipping...")
            continue
        
        persona = PERSONAS[persona_key]
        
        if verbose:
            print(f"\n{'─'*70}")
            print(f"🎭 SIMULATION {idx}/{len(personas)}: {persona['name']}")
            print(f"   Company: {persona['company']}")
            print(f"   Industry: {persona['industry']}")
            print(f"{'─'*70}")
        
        # Run simulation
        conversation = []
        
        for turn in range(1, turns_per_simulation + 1):
            if verbose:
                print(f"\n   Turn {turn}/{turns_per_simulation}...", end=" ", flush=True)
            
            # Generate customer email
            customer_email = generate_customer_email(persona, conversation, turn)
            
            # Get IRA's response
            ira_response = get_ira_response(customer_email, persona, use_real_ira=use_real_ira)
            
            # Store
            conversation.append({
                "turn": turn,
                "customer": customer_email,
                "ira": ira_response,
                "timestamp": datetime.now().isoformat(),
            })
            
            if verbose:
                print("✓")
        
        # Store simulation
        sim_data = {
            "persona": persona,
            "turns": len(conversation),
            "conversation": conversation,
            "generated_at": datetime.now().isoformat(),
        }
        results["simulations"].append(sim_data)
        
        # Save to file
        output_dir = PROJECT_ROOT / "data" / "simulations"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        persona_slug = persona["name"].replace(" ", "_").lower()
        output_file = output_dir / f"batch_{persona_slug}_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(sim_data, f, indent=2, ensure_ascii=False)
        
        if verbose:
            print(f"   💾 Saved: {output_file.name}")
        
        # Evaluate immediately
        if verbose:
            print(f"   📊 Evaluating...", end=" ", flush=True)
        
        sim_data["_file"] = str(output_file)
        eval_result = evaluate_simulation(sim_data)
        results["evaluations"].append(eval_result)
        
        if verbose:
            print(f"Score: {eval_result.overall_score}/5 | Deal: {eval_result.deal_likelihood}")
        
        # Brief pause between simulations
        time.sleep(1)
    
    # Generate summary report
    results["ended_at"] = datetime.now().isoformat()
    results["report"] = generate_report(results["evaluations"])
    
    if verbose:
        print(results["report"])
    
    # Save full results
    results_file = output_dir / f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Convert EvaluationResult to dict for JSON serialization
    results_export = {
        "started_at": results["started_at"],
        "ended_at": results["ended_at"],
        "config": results["config"],
        "summary": {
            "total_simulations": len(results["simulations"]),
            "avg_score": sum(e.overall_score for e in results["evaluations"]) / len(results["evaluations"]) if results["evaluations"] else 0,
            "high_likelihood": sum(1 for e in results["evaluations"] if e.deal_likelihood == "high"),
            "medium_likelihood": sum(1 for e in results["evaluations"] if e.deal_likelihood == "medium"),
            "low_likelihood": sum(1 for e in results["evaluations"] if e.deal_likelihood == "low"),
        },
        "evaluations": [
            {
                "persona": e.persona_name,
                "company": e.persona_company,
                "turns": e.total_turns,
                "scores": e.scores,
                "overall_score": e.overall_score,
                "strengths": e.strengths,
                "improvements": e.improvements,
                "deal_likelihood": e.deal_likelihood,
                "observations": e.key_observations,
            }
            for e in results["evaluations"]
        ],
    }
    
    with open(results_file, 'w') as f:
        json.dump(results_export, f, indent=2)
    
    if verbose:
        print(f"\n📁 Full results saved to: {results_file}")
    
    return results


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="APOLLO Batch Simulation")
    parser.add_argument("--personas", "-p", nargs="+",
                       choices=list(PERSONAS.keys()),
                       help="Personas to simulate (default: all)")
    parser.add_argument("--turns", "-t", type=int, default=4,
                       help="Turns per simulation (default: 4)")
    parser.add_argument("--simulate-ira", action="store_true",
                       help="Use GPT to simulate IRA responses")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Suppress detailed output")
    
    args = parser.parse_args()
    
    run_batch_simulation(
        personas=args.personas,
        turns_per_simulation=args.turns,
        use_real_ira=not args.simulate_ira,
        verbose=not args.quiet,
    )
