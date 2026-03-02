#!/usr/bin/env python3
"""
SALES FLOW TRAINING LOOP

Complete training pipeline that:
1. Creative Agent generates realistic "customer" emails (learning from real patterns)
2. Ira responds through her full cognitive pipeline
3. Evaluator scores the response quality
4. Both sides learn - creating training data for the sales flow

This creates a self-improving loop where Ira learns the exact sales patterns
that work in European B2B machine sales.

Usage:
    # Single simulation with creative agent
    python agents/apollo/sales_flow_training.py --persona dutch_hydroponics
    
    # Batch training across all personas
    python agents/apollo/sales_flow_training.py --batch --iterations 3
    
    # Generate training dataset
    python agents/apollo/sales_flow_training.py --generate-dataset --size 50
"""

import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.apollo.creative_customer_agent import (
    CreativeCustomerAgent,
    ENHANCED_PERSONAS,
    STAGE_PROGRESSIONS,
    load_sales_patterns,
    load_action_training,
)


# =============================================================================
# TRAINING DATA STRUCTURES
# =============================================================================

@dataclass
class TrainingExample:
    """A single training example from the simulation."""
    stage: str
    customer_input: str
    expected_response_type: str
    ira_response: str
    key_questions: List[str]
    objections_handled: List[str]
    quality_score: float = 0.0
    feedback: str = ""


@dataclass
class SalesFlowTrainingSet:
    """Complete training set for sales flow learning."""
    examples: List[TrainingExample]
    personas_used: List[str]
    stages_covered: List[str]
    total_simulations: int
    generated_at: str


# =============================================================================
# RESPONSE EVALUATOR
# =============================================================================

class ResponseEvaluator:
    """Evaluates IRA's responses against expected behaviors."""
    
    def __init__(self):
        self.action_training = load_action_training()
        
        # Load expected actions for each stage
        self.stage_actions = {}
        for action in self.action_training.get("actions", []):
            self.stage_actions[action["stage"]] = {
                "recommended_action": action["recommended_action"],
                "example_response": action["example_response"],
                "next_stages": action["next_stages"],
            }
    
    def evaluate(
        self,
        stage: str,
        customer_email: str,
        ira_response: str,
        key_questions: List[str],
        objections: List[str]
    ) -> Dict:
        """Evaluate IRA's response quality."""
        
        score = 0.0
        feedback = []
        
        # 1. Check if response addresses key questions
        questions_addressed = 0
        for q in key_questions:
            q_lower = q.lower()
            if any(word in ira_response.lower() for word in q_lower.split()[:3]):
                questions_addressed += 1
        
        if key_questions:
            question_score = questions_addressed / len(key_questions)
            score += question_score * 0.3
            if question_score < 1.0:
                feedback.append(f"Missed {len(key_questions) - questions_addressed} questions")
        
        # 2. Check stage-appropriate behavior
        expected = self.stage_actions.get(stage, {})
        if expected:
            # Check for key action elements
            action_keywords = expected.get("recommended_action", "").lower().split()[:5]
            action_match = sum(1 for kw in action_keywords if kw in ira_response.lower())
            action_score = min(action_match / max(len(action_keywords), 1), 1.0)
            score += action_score * 0.25
        
        # 3. Check objection handling
        if objections:
            objections_addressed = 0
            for obj in objections:
                obj_words = obj.lower().split()[:3]
                if any(word in ira_response.lower() for word in obj_words):
                    objections_addressed += 1
            objection_score = objections_addressed / len(objections)
            score += objection_score * 0.25
            if objection_score < 1.0:
                feedback.append(f"Didn't fully address {len(objections) - objections_addressed} objections")
        else:
            score += 0.25  # No objections to handle
        
        # 4. Response quality checks
        quality_score = 0.0
        
        # Appropriate length (not too short, not too long)
        word_count = len(ira_response.split())
        if 50 <= word_count <= 300:
            quality_score += 0.5
        elif 30 <= word_count < 50 or 300 < word_count <= 400:
            quality_score += 0.25
        else:
            feedback.append("Response length not optimal")
        
        # Has a call to action
        cta_keywords = ["let me know", "please", "would you", "shall we", "happy to", "call", "schedule"]
        if any(kw in ira_response.lower() for kw in cta_keywords):
            quality_score += 0.5
        else:
            feedback.append("Missing clear call-to-action")
        
        score += quality_score * 0.2
        
        return {
            "score": round(score, 2),
            "feedback": feedback,
            "questions_addressed": questions_addressed,
            "total_questions": len(key_questions),
        }


# =============================================================================
# SALES FLOW TRAINER
# =============================================================================

class SalesFlowTrainer:
    """
    Main training orchestrator that runs simulations and generates training data.
    """
    
    def __init__(self):
        self.evaluator = ResponseEvaluator()
        self.training_examples: List[TrainingExample] = []
        self.simulation_results: List[Dict] = []
    
    async def run_single_simulation(
        self,
        persona_key: str,
        max_turns: int = 6,
        verbose: bool = True
    ) -> Dict:
        """Run a single training simulation."""
        
        # Import IRA components
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))
            from src.agents import research, write, verify
            from src.agents.chief_of_staff.agent import analyze_intent
            IRA_AVAILABLE = True
        except ImportError:
            IRA_AVAILABLE = False
            if verbose:
                print("Warning: IRA not available")
        
        # Initialize creative agent
        creative_agent = CreativeCustomerAgent(persona_key)
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"SALES FLOW TRAINING - {persona_key}")
            print(f"{'='*60}")
            print(f"Persona: {creative_agent.persona['name']}")
            print(f"Progression: {creative_agent.progression['description']}")
        
        simulation = {
            "persona": persona_key,
            "started_at": datetime.now().isoformat(),
            "turns": [],
            "training_examples": [],
        }
        
        ira_last_response = None
        
        while creative_agent.should_continue() and creative_agent.turn_count < max_turns:
            # Generate customer email
            customer_email = creative_agent.generate_customer_email(ira_last_response)
            
            if verbose:
                print(f"\n{'─'*40}")
                print(f"Turn {creative_agent.turn_count + 1}: {customer_email.stage}")
                print(f"{'─'*40}")
                print(f"📧 Customer: {customer_email.body[:150]}...")
            
            # Get IRA's response
            if IRA_AVAILABLE:
                try:
                    intent = analyze_intent(customer_email.body)
                    research_output = await research(customer_email.body, {
                        "intent": intent,
                        "customer_name": creative_agent.persona["name"],
                    })
                    context = {
                        "intent": intent,
                        "channel": "email",
                        "research_output": research_output,
                    }
                    draft = await write(customer_email.body, context)
                    ira_response = await verify(draft, customer_email.body, context)
                except Exception as e:
                    ira_response = f"[IRA Error: {e}]"
            else:
                ira_response = f"[Mock response for {customer_email.stage}]"
            
            if verbose:
                print(f"🤖 IRA: {ira_response[:150]}...")
            
            # Evaluate response
            evaluation = self.evaluator.evaluate(
                stage=customer_email.stage,
                customer_email=customer_email.body,
                ira_response=ira_response,
                key_questions=customer_email.key_questions,
                objections=customer_email.objections_raised,
            )
            
            if verbose:
                print(f"📊 Score: {evaluation['score']:.2f}")
                if evaluation['feedback']:
                    print(f"   Feedback: {', '.join(evaluation['feedback'])}")
            
            # Create training example
            example = TrainingExample(
                stage=customer_email.stage,
                customer_input=customer_email.body,
                expected_response_type=customer_email.expected_response_type,
                ira_response=ira_response,
                key_questions=customer_email.key_questions,
                objections_handled=customer_email.objections_raised,
                quality_score=evaluation["score"],
                feedback="; ".join(evaluation["feedback"]),
            )
            self.training_examples.append(example)
            simulation["training_examples"].append({
                "stage": example.stage,
                "customer_input": example.customer_input,
                "ira_response": example.ira_response,
                "score": example.quality_score,
                "feedback": example.feedback,
            })
            
            # Record and advance
            creative_agent.record_ira_response(ira_response)
            ira_last_response = ira_response
            creative_agent.advance_stage(ira_response)
        
        # Finalize
        outcome = creative_agent.determine_outcome()
        simulation["outcome"] = outcome
        simulation["ended_at"] = datetime.now().isoformat()
        simulation["total_turns"] = len(simulation["turns"])
        simulation["avg_score"] = sum(
            ex["score"] for ex in simulation["training_examples"]
        ) / max(len(simulation["training_examples"]), 1)
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"COMPLETE - Outcome: {outcome.upper()}")
            print(f"Avg Score: {simulation['avg_score']:.2f}")
            print(f"{'='*60}")
        
        self.simulation_results.append(simulation)
        return simulation
    
    async def run_batch_training(
        self,
        personas: List[str] = None,
        iterations: int = 1,
        max_turns: int = 6,
        verbose: bool = True
    ) -> Dict:
        """Run batch training across multiple personas."""
        
        if personas is None:
            personas = list(ENHANCED_PERSONAS.keys())
        
        print(f"\n{'='*70}")
        print(f"BATCH SALES FLOW TRAINING")
        print(f"{'='*70}")
        print(f"Personas: {len(personas)}")
        print(f"Iterations per persona: {iterations}")
        print(f"Max turns: {max_turns}")
        print(f"{'='*70}\n")
        
        all_results = []
        
        for iteration in range(iterations):
            print(f"\n--- Iteration {iteration + 1}/{iterations} ---")
            
            for persona in personas:
                result = await self.run_single_simulation(
                    persona_key=persona,
                    max_turns=max_turns,
                    verbose=verbose,
                )
                all_results.append(result)
        
        # Summary
        total_examples = len(self.training_examples)
        avg_score = sum(ex.quality_score for ex in self.training_examples) / max(total_examples, 1)
        stages_covered = list(set(ex.stage for ex in self.training_examples))
        
        print(f"\n{'='*70}")
        print(f"BATCH TRAINING COMPLETE")
        print(f"{'='*70}")
        print(f"Total simulations: {len(all_results)}")
        print(f"Total training examples: {total_examples}")
        print(f"Average score: {avg_score:.2f}")
        print(f"Stages covered: {len(stages_covered)}")
        print(f"{'='*70}")
        
        return {
            "total_simulations": len(all_results),
            "total_examples": total_examples,
            "avg_score": avg_score,
            "stages_covered": stages_covered,
            "results": all_results,
        }
    
    def export_training_set(self, output_path: Path = None) -> Path:
        """Export training examples to JSON for IRA ingestion."""
        
        if output_path is None:
            output_path = PROJECT_ROOT / "data" / "training" / "sales_flow_training_set.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        training_set = {
            "generated_at": datetime.now().isoformat(),
            "total_examples": len(self.training_examples),
            "stages_covered": list(set(ex.stage for ex in self.training_examples)),
            "avg_quality_score": sum(ex.quality_score for ex in self.training_examples) / max(len(self.training_examples), 1),
            "examples": [
                {
                    "stage": ex.stage,
                    "customer_input": ex.customer_input,
                    "expected_response_type": ex.expected_response_type,
                    "ira_response": ex.ira_response,
                    "key_questions": ex.key_questions,
                    "objections_handled": ex.objections_handled,
                    "quality_score": ex.quality_score,
                    "feedback": ex.feedback,
                }
                for ex in self.training_examples
            ],
        }
        
        with open(output_path, 'w') as f:
            json.dump(training_set, f, indent=2)
        
        print(f"Exported {len(self.training_examples)} training examples to {output_path}")
        return output_path


# =============================================================================
# MAIN
# =============================================================================

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Sales Flow Training")
    parser.add_argument("--persona", type=str, default="dutch_hydroponics",
                       choices=list(ENHANCED_PERSONAS.keys()),
                       help="Customer persona for single simulation")
    parser.add_argument("--turns", type=int, default=6, help="Max turns per simulation")
    parser.add_argument("--batch", action="store_true", help="Run batch training")
    parser.add_argument("--iterations", type=int, default=1, help="Iterations per persona")
    parser.add_argument("--generate-dataset", action="store_true", help="Generate training dataset")
    parser.add_argument("--size", type=int, default=20, help="Dataset size (simulations)")
    parser.add_argument("--quiet", action="store_true", help="Less verbose output")
    
    args = parser.parse_args()
    
    trainer = SalesFlowTrainer()
    
    if args.generate_dataset:
        # Generate a full training dataset
        iterations = args.size // len(ENHANCED_PERSONAS)
        await trainer.run_batch_training(
            iterations=max(iterations, 1),
            max_turns=args.turns,
            verbose=not args.quiet,
        )
        trainer.export_training_set()
        
    elif args.batch:
        # Batch training
        await trainer.run_batch_training(
            iterations=args.iterations,
            max_turns=args.turns,
            verbose=not args.quiet,
        )
        trainer.export_training_set()
        
    else:
        # Single simulation
        await trainer.run_single_simulation(
            persona_key=args.persona,
            max_turns=args.turns,
            verbose=not args.quiet,
        )
        trainer.export_training_set()


if __name__ == "__main__":
    asyncio.run(main())
