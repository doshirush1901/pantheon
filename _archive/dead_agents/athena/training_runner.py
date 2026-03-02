#!/usr/bin/env python3
"""
ATLAS Training Runner
=====================

Orchestrates the full training loop:
1. Load training data (genuine Q&A pairs)
2. Generate questions (from real data or templates)
3. Send to IRA, collect responses
4. Evaluate against Rushabh's actual responses
5. Generate feedback and store for learning
6. Repeat for iterative improvement

Usage:
    python agents/atlas/training_runner.py
    python agents/atlas/training_runner.py --iterations 10 --batch-size 20
"""

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.atlas.question_generator import QuestionGenerator, GeneratedQuestion
from agents.atlas.evaluator import ResponseEvaluator, EvaluationResult


@dataclass
class TrainingRun:
    """Record of a training run."""
    run_id: str
    timestamp: str
    total_questions: int
    passed: int
    failed: int
    avg_overall_score: float
    avg_style_score: float
    avg_accuracy_score: float
    category_scores: Dict[str, float]
    critical_failures: List[str]
    top_improvements: List[str]


@dataclass
class TrainingResult:
    """Result of training on a single Q&A pair."""
    question_id: str
    category: str
    question: str
    ira_response: str
    rushabh_response: str
    evaluation: EvaluationResult
    feedback_generated: str


class IRAInvoker:
    """Invokes IRA to get responses."""
    
    def __init__(self, use_direct: bool = True):
        self.use_direct = use_direct
        self._initialized = False
    
    async def _init_ira(self):
        """Initialize IRA components."""
        if self._initialized:
            return
        
        try:
            # Import IRA components
            from openclaw.agents.ira.src.agents import research, write, verify
            from openclaw.agents.ira.src.agents.chief_of_staff.agent import analyze_intent
            
            self.research = research
            self.write = write
            self.verify = verify
            self.analyze_intent = analyze_intent
            self._initialized = True
            
        except ImportError as e:
            print(f"[warn] Could not import IRA components: {e}")
            self._initialized = False
    
    async def get_response(self, question: str) -> str:
        """Get IRA's response to a question."""
        if self.use_direct:
            return await self._invoke_direct(question)
        else:
            return await self._invoke_cli(question)
    
    async def _invoke_direct(self, question: str) -> str:
        """Invoke IRA directly using Python functions."""
        await self._init_ira()
        
        if not self._initialized:
            return "[ERROR: IRA not initialized]"
        
        try:
            # Analyze intent
            intent = self.analyze_intent(question)
            
            # Research
            research_output = await self.research(question, {"intent": intent})
            
            # Write
            context = {
                "intent": intent,
                "channel": "training",
                "research_output": research_output
            }
            draft = await self.write(question, context)
            
            # Verify
            verified = await self.verify(draft, question, context)
            
            return verified
            
        except Exception as e:
            return f"[ERROR: {str(e)}]"
    
    async def _invoke_cli(self, question: str) -> str:
        """Invoke IRA using CLI (fallback)."""
        try:
            import subprocess
            
            result = subprocess.run(
                ["openclaw", "agent", "--agent", "ira", "--message", question],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(PROJECT_ROOT)
            )
            
            return result.stdout or result.stderr or "[No response]"
            
        except Exception as e:
            return f"[CLI ERROR: {str(e)}]"


class ATLASTrainer:
    """Main training orchestrator."""
    
    def __init__(self, training_data_path: Path = None):
        self.training_data = None
        self.qa_pairs = []
        
        if training_data_path and training_data_path.exists():
            with open(training_data_path, 'r') as f:
                self.training_data = json.load(f)
                self.qa_pairs = self.training_data.get('qa_pairs', [])
        
        self.question_generator = QuestionGenerator(training_data_path)
        self.evaluator = ResponseEvaluator()
        self.ira = IRAInvoker(use_direct=True)
        
        self.results: List[TrainingResult] = []
        self.run_count = 0
    
    async def train_single(self, qa_pair: Dict) -> TrainingResult:
        """Train on a single Q&A pair."""
        question = qa_pair.get('customer_question', '')
        rushabh_response = qa_pair.get('rushabh_response', '')
        category = qa_pair.get('category', 'general')
        question_id = qa_pair.get('id', f'qa_{len(self.results)+1}')
        
        # Get IRA's response
        ira_response = await self.ira.get_response(question)
        
        # Evaluate
        evaluation = self.evaluator.evaluate(
            question=question,
            ira_response=ira_response,
            rushabh_response=rushabh_response,
            question_id=question_id,
            category=category
        )
        
        # Generate feedback
        feedback = self._generate_feedback(evaluation, question, ira_response, rushabh_response)
        
        result = TrainingResult(
            question_id=question_id,
            category=category,
            question=question[:500],
            ira_response=ira_response[:500],
            rushabh_response=rushabh_response[:500],
            evaluation=evaluation,
            feedback_generated=feedback,
        )
        
        self.results.append(result)
        return result
    
    def _generate_feedback(
        self,
        evaluation: EvaluationResult,
        question: str,
        ira_response: str,
        rushabh_response: str
    ) -> str:
        """Generate actionable feedback from evaluation."""
        feedback_parts = []
        
        if evaluation.style_score < 3:
            feedback_parts.append(
                f"Style improvement needed: {evaluation.style_feedback}. "
                f"Rushabh's style is more direct and warm."
            )
        
        if evaluation.accuracy_score < 3:
            feedback_parts.append(
                f"Accuracy issue: {evaluation.accuracy_feedback}. "
                f"Verify specifications before responding."
            )
        
        if evaluation.completeness_score < 3:
            feedback_parts.append(
                f"Completeness issue: {evaluation.completeness_feedback}. "
                f"Address all parts of the customer's question."
            )
        
        if evaluation.sales_effectiveness_score < 3:
            feedback_parts.append(
                f"Sales improvement: {evaluation.sales_feedback}. "
                f"Include a clear call-to-action."
            )
        
        if evaluation.missing_elements:
            feedback_parts.append(
                f"Missing elements from Rushabh's response: {', '.join(evaluation.missing_elements)}"
            )
        
        if evaluation.critical_failures:
            feedback_parts.append(
                f"CRITICAL: {'; '.join(evaluation.critical_failures)}"
            )
        
        return "\n".join(feedback_parts) if feedback_parts else "Good response - no major issues."
    
    async def run_training_batch(self, batch_size: int = 20) -> TrainingRun:
        """Run training on a batch of Q&A pairs."""
        self.run_count += 1
        run_id = f"run_{self.run_count}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"\n{'='*70}")
        print(f"  ATLAS TRAINING RUN: {run_id}")
        print(f"{'='*70}\n")
        
        # Select Q&A pairs for this batch
        if self.qa_pairs:
            import random
            batch = random.sample(self.qa_pairs, min(batch_size, len(self.qa_pairs)))
        else:
            # Generate questions if no training data
            print("[info] No training data - using generated questions")
            generated = self.question_generator.generate_batch(batch_size, mix_real=False)
            batch = [
                {
                    'id': q.id,
                    'category': q.category,
                    'customer_question': q.question,
                    'rushabh_response': '',  # No ground truth
                }
                for q in generated
            ]
        
        print(f"[info] Training on {len(batch)} Q&A pairs...")
        
        # Train on each pair
        batch_results = []
        for i, qa_pair in enumerate(batch, 1):
            print(f"[{i}/{len(batch)}] {qa_pair.get('category', 'unknown')}...", end=' ', flush=True)
            
            result = await self.train_single(qa_pair)
            batch_results.append(result)
            
            status = "✓" if result.evaluation.passed else "✗"
            print(f"{status} ({result.evaluation.overall_score:.1f})")
        
        # Aggregate results
        passed = sum(1 for r in batch_results if r.evaluation.passed)
        failed = len(batch_results) - passed
        
        avg_overall = sum(r.evaluation.overall_score for r in batch_results) / len(batch_results)
        avg_style = sum(r.evaluation.style_score for r in batch_results) / len(batch_results)
        avg_accuracy = sum(r.evaluation.accuracy_score for r in batch_results) / len(batch_results)
        
        # Category scores
        category_scores = {}
        category_counts = {}
        for r in batch_results:
            cat = r.category
            if cat not in category_scores:
                category_scores[cat] = 0
                category_counts[cat] = 0
            category_scores[cat] += r.evaluation.overall_score
            category_counts[cat] += 1
        
        for cat in category_scores:
            category_scores[cat] /= category_counts[cat]
        
        # Collect critical failures
        critical_failures = []
        for r in batch_results:
            critical_failures.extend(r.evaluation.critical_failures)
        
        # Top improvements needed
        top_improvements = []
        style_issues = sum(1 for r in batch_results if r.evaluation.style_score < 3)
        accuracy_issues = sum(1 for r in batch_results if r.evaluation.accuracy_score < 3)
        completeness_issues = sum(1 for r in batch_results if r.evaluation.completeness_score < 3)
        sales_issues = sum(1 for r in batch_results if r.evaluation.sales_effectiveness_score < 3)
        
        if style_issues > len(batch_results) * 0.3:
            top_improvements.append(f"Style matching ({style_issues} issues)")
        if accuracy_issues > len(batch_results) * 0.2:
            top_improvements.append(f"Accuracy ({accuracy_issues} issues)")
        if completeness_issues > len(batch_results) * 0.3:
            top_improvements.append(f"Completeness ({completeness_issues} issues)")
        if sales_issues > len(batch_results) * 0.3:
            top_improvements.append(f"Sales effectiveness ({sales_issues} issues)")
        
        run_result = TrainingRun(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            total_questions=len(batch_results),
            passed=passed,
            failed=failed,
            avg_overall_score=round(avg_overall, 2),
            avg_style_score=round(avg_style, 2),
            avg_accuracy_score=round(avg_accuracy, 2),
            category_scores={k: round(v, 2) for k, v in category_scores.items()},
            critical_failures=list(set(critical_failures)),
            top_improvements=top_improvements,
        )
        
        return run_result
    
    def print_run_summary(self, run: TrainingRun):
        """Print summary of a training run."""
        print(f"\n{'='*70}")
        print(f"  TRAINING RUN SUMMARY: {run.run_id}")
        print(f"{'='*70}")
        
        pass_rate = run.passed / run.total_questions * 100
        
        print(f"""
Total Questions:     {run.total_questions}
Passed:              {run.passed} ({pass_rate:.0f}%)
Failed:              {run.failed}

Average Scores:
  Overall:           {run.avg_overall_score}/5.0
  Style:             {run.avg_style_score}/5.0
  Accuracy:          {run.avg_accuracy_score}/5.0
""")
        
        print("Category Scores:")
        for cat, score in sorted(run.category_scores.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {score}/5.0")
        
        if run.critical_failures:
            print(f"\n⚠️  Critical Failures:")
            for failure in run.critical_failures[:5]:
                print(f"  - {failure}")
        
        if run.top_improvements:
            print(f"\n📈 Top Improvements Needed:")
            for improvement in run.top_improvements:
                print(f"  - {improvement}")
    
    def save_results(self, output_path: Path):
        """Save all training results."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        results_data = {
            'metadata': {
                'total_results': len(self.results),
                'saved_at': datetime.now().isoformat(),
            },
            'results': [
                {
                    'question_id': r.question_id,
                    'category': r.category,
                    'question': r.question,
                    'ira_response': r.ira_response,
                    'rushabh_response': r.rushabh_response,
                    'evaluation': asdict(r.evaluation),
                    'feedback': r.feedback_generated,
                }
                for r in self.results
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        print(f"\n[saved] {len(self.results)} results → {output_path}")


async def main():
    parser = argparse.ArgumentParser(description="ATLAS Training Runner")
    parser.add_argument('--training-data', type=str, default='data/training/atlas_training_data.json')
    parser.add_argument('--output', type=str, default='data/training/atlas_evaluation_results.json')
    parser.add_argument('--batch-size', type=int, default=20)
    parser.add_argument('--iterations', type=int, default=1)
    args = parser.parse_args()
    
    training_data_path = PROJECT_ROOT / args.training_data
    output_path = PROJECT_ROOT / args.output
    
    trainer = ATLASTrainer(training_data_path)
    
    print(f"[info] Training data: {training_data_path}")
    print(f"[info] Q&A pairs available: {len(trainer.qa_pairs)}")
    
    all_runs = []
    for i in range(args.iterations):
        if args.iterations > 1:
            print(f"\n{'#'*70}")
            print(f"  ITERATION {i+1}/{args.iterations}")
            print(f"{'#'*70}")
        
        run = await trainer.run_training_batch(batch_size=args.batch_size)
        trainer.print_run_summary(run)
        all_runs.append(run)
    
    # Save results
    trainer.save_results(output_path)
    
    # Print overall summary
    if args.iterations > 1:
        print(f"\n{'='*70}")
        print("  OVERALL TRAINING SUMMARY")
        print(f"{'='*70}")
        
        total_passed = sum(r.passed for r in all_runs)
        total_questions = sum(r.total_questions for r in all_runs)
        avg_score = sum(r.avg_overall_score for r in all_runs) / len(all_runs)
        
        print(f"""
Iterations:          {len(all_runs)}
Total Questions:     {total_questions}
Total Passed:        {total_passed} ({total_passed/total_questions*100:.0f}%)
Avg Overall Score:   {avg_score:.2f}/5.0
""")
    
    return 0


if __name__ == "__main__":
    asyncio.run(main())
