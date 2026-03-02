#!/usr/bin/env python3
"""
APOLLO Pipeline Validator
=========================

Ensures IRA follows ALL the correct steps when generating a response:

1. INGEST - Parse and understand the email/query
2. RETRIEVE - Search the right knowledge sources
3. RECOMMEND - Select appropriate machine(s)
4. GENERATE - Create the response
5. VERIFY - Check facts against source of truth
6. PACKAGE - Format for the channel (email/telegram)

This validator:
- Tracks which steps IRA executed
- Identifies skipped or failed steps
- Measures retrieval quality
- Validates against ground truth
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from functools import wraps

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


# =============================================================================
# PIPELINE STEPS
# =============================================================================

@dataclass
class PipelineStep:
    """A single step in IRA's pipeline."""
    name: str
    executed: bool = False
    success: bool = False
    duration_ms: float = 0
    input_data: Dict = field(default_factory=dict)
    output_data: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class PipelineTrace:
    """Complete trace of IRA's processing pipeline."""
    query: str
    started_at: str
    ended_at: str = ""
    
    # Pipeline steps
    steps: Dict[str, PipelineStep] = field(default_factory=dict)
    
    # Quality metrics
    retrieval_quality: float = 0.0  # 0-1: How relevant were retrieved chunks?
    recommendation_match: bool = False  # Did IRA recommend the right machine?
    fact_accuracy: float = 0.0  # 0-1: Were facts correct?
    
    # Final outputs
    final_response: str = ""
    expected_response: str = ""
    accuracy_score: float = 0.0
    
    def get_summary(self) -> str:
        executed = [s for s in self.steps.values() if s.executed]
        failed = [s for s in self.steps.values() if s.executed and not s.success]
        
        total_time = sum(s.duration_ms for s in executed)
        
        return f"""
PIPELINE TRACE SUMMARY
======================
Query: {self.query[:50]}...
Started: {self.started_at}

STEPS EXECUTED: {len(executed)}/{len(self.steps)}
{chr(10).join(f"  {'✓' if s.success else '✗'} {name} ({s.duration_ms:.0f}ms)" for name, s in self.steps.items() if s.executed)}

FAILED STEPS: {len(failed)}
{chr(10).join(f"  - {s.name}: {', '.join(s.errors)}" for s in failed) if failed else "  None"}

QUALITY METRICS:
  Retrieval Quality:     {self.retrieval_quality:.1%}
  Recommendation Match:  {'✓' if self.recommendation_match else '✗'}
  Fact Accuracy:         {self.fact_accuracy:.1%}
  Overall Accuracy:      {self.accuracy_score:.1%}

Total Time: {total_time:.0f}ms
"""


# =============================================================================
# PIPELINE VALIDATOR
# =============================================================================

class PipelineValidator:
    """
    Validates IRA's response generation pipeline.
    
    Usage:
        validator = PipelineValidator()
        
        # Start trace
        trace = validator.start_trace(query="What's the price?")
        
        # Record steps
        validator.record_step("ingest", success=True, output={"intent": "pricing"})
        validator.record_step("retrieve", success=True, output={"chunks": [...]})
        ...
        
        # Finalize and get report
        report = validator.finalize_trace(response="Hi! The price is...")
    """
    
    EXPECTED_STEPS = [
        "ingest",      # Parse query, extract intent
        "retrieve",    # Search knowledge base
        "recommend",   # Machine recommendation
        "generate",    # Draft response
        "verify",      # Fact check
        "package",     # Final formatting
    ]
    
    def __init__(self):
        self.current_trace: Optional[PipelineTrace] = None
        self.traces: List[PipelineTrace] = []
    
    def start_trace(self, query: str, expected_response: str = "") -> PipelineTrace:
        """Start a new pipeline trace."""
        self.current_trace = PipelineTrace(
            query=query,
            started_at=datetime.now().isoformat(),
            expected_response=expected_response,
            steps={
                step: PipelineStep(name=step)
                for step in self.EXPECTED_STEPS
            },
        )
        return self.current_trace
    
    def record_step(
        self,
        step_name: str,
        success: bool = True,
        input_data: Dict = None,
        output_data: Dict = None,
        errors: List[str] = None,
        duration_ms: float = 0,
    ):
        """Record execution of a pipeline step."""
        if not self.current_trace:
            return
        
        if step_name not in self.current_trace.steps:
            self.current_trace.steps[step_name] = PipelineStep(name=step_name)
        
        step = self.current_trace.steps[step_name]
        step.executed = True
        step.success = success
        step.duration_ms = duration_ms
        step.input_data = input_data or {}
        step.output_data = output_data or {}
        step.errors = errors or []
    
    def finalize_trace(
        self,
        response: str,
        retrieval_chunks: List[Dict] = None,
        recommended_machine: str = None,
        expected_machine: str = None,
    ) -> PipelineTrace:
        """Finalize the trace and calculate metrics."""
        if not self.current_trace:
            return None
        
        self.current_trace.ended_at = datetime.now().isoformat()
        self.current_trace.final_response = response
        
        # Calculate retrieval quality
        if retrieval_chunks:
            self.current_trace.retrieval_quality = self._score_retrieval(
                self.current_trace.query,
                retrieval_chunks
            )
        
        # Check machine recommendation
        if recommended_machine and expected_machine:
            self.current_trace.recommendation_match = (
                recommended_machine.lower() == expected_machine.lower()
            )
        
        # Calculate fact accuracy (using scorer)
        if self.current_trace.expected_response:
            from accuracy_scorer import score_response
            report = score_response(
                ira_response=response,
                expected_response=self.current_trace.expected_response,
                query=self.current_trace.query,
            )
            self.current_trace.fact_accuracy = report.factual_accuracy
            self.current_trace.accuracy_score = report.overall_score
        
        # Store trace
        self.traces.append(self.current_trace)
        trace = self.current_trace
        self.current_trace = None
        
        return trace
    
    def _score_retrieval(self, query: str, chunks: List[Dict]) -> float:
        """Score how relevant the retrieved chunks are."""
        if not chunks:
            return 0.0
        
        # Simple relevance scoring based on query term overlap
        query_terms = set(query.lower().split())
        
        scores = []
        for chunk in chunks:
            text = chunk.get("text", chunk.get("content", "")).lower()
            chunk_terms = set(text.split())
            
            if not chunk_terms:
                scores.append(0.0)
                continue
            
            overlap = len(query_terms & chunk_terms)
            scores.append(min(1.0, overlap / len(query_terms)))
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def get_validation_report(self) -> Dict:
        """Get aggregated validation report."""
        if not self.traces:
            return {"error": "No traces recorded"}
        
        # Calculate aggregates
        total_traces = len(self.traces)
        
        step_success_rates = {}
        for step_name in self.EXPECTED_STEPS:
            executed = [t for t in self.traces if t.steps[step_name].executed]
            successful = [t for t in executed if t.steps[step_name].success]
            
            step_success_rates[step_name] = {
                "executed": len(executed),
                "successful": len(successful),
                "rate": len(successful) / len(executed) if executed else 0,
            }
        
        avg_retrieval = sum(t.retrieval_quality for t in self.traces) / total_traces
        recommendation_accuracy = sum(1 for t in self.traces if t.recommendation_match) / total_traces
        avg_fact_accuracy = sum(t.fact_accuracy for t in self.traces) / total_traces
        avg_overall = sum(t.accuracy_score for t in self.traces) / total_traces
        
        # Find problem areas
        problem_steps = [
            name for name, data in step_success_rates.items()
            if data["rate"] < 0.9 and data["executed"] > 0
        ]
        
        return {
            "total_traces": total_traces,
            "step_success_rates": step_success_rates,
            "avg_retrieval_quality": avg_retrieval,
            "recommendation_accuracy": recommendation_accuracy,
            "avg_fact_accuracy": avg_fact_accuracy,
            "avg_overall_accuracy": avg_overall,
            "problem_steps": problem_steps,
        }


# =============================================================================
# DECORATOR FOR PIPELINE INSTRUMENTATION
# =============================================================================

# Global validator instance
_validator = PipelineValidator()


def instrument_step(step_name: str):
    """Decorator to instrument a pipeline function."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            error = None
            result = None
            
            try:
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                error = str(e)
                success = False
                raise
            finally:
                duration = (time.time() - start) * 1000
                _validator.record_step(
                    step_name=step_name,
                    success=success,
                    duration_ms=duration,
                    errors=[error] if error else [],
                )
            
            return result
        return wrapper
    return decorator


def get_validator() -> PipelineValidator:
    """Get the global validator instance."""
    return _validator


# =============================================================================
# EXPECTED OUTPUTS FOR VALIDATION
# =============================================================================

EXPECTED_OUTPUTS = {
    "european_1800x1200_inquiry": {
        "machine": "PF1-C-1812",
        "price_eur_range": (35000, 45000),
        "lead_time_weeks": (12, 20),
        "key_specs": ["1800 x 1200 mm", "pneumatic", "10mm thickness"],
    },
    "indian_auto_1500x1200_inquiry": {
        "machine": "PF1-C-1812",  # Or PF1-X-1520
        "price_inr_range": (3000000, 5000000),
        "lead_time_weeks": (12, 20),
        "key_specs": ["ABS", "TPO", "automotive"],
    },
    "startup_small_machine": {
        "machine": "AM-1216",  # Entry level
        "price_usd_range": (40000, 80000),
        "key_specs": ["automatic", "roll-fed", "thin gauge"],
    },
}


def validate_against_expected(
    query_type: str,
    response: str,
    recommended_machine: str = None,
) -> Dict:
    """Validate response against expected outputs."""
    expected = EXPECTED_OUTPUTS.get(query_type)
    
    if not expected:
        return {"error": f"Unknown query type: {query_type}"}
    
    validations = {
        "machine_correct": False,
        "price_in_range": False,
        "key_specs_mentioned": 0,
        "issues": [],
    }
    
    # Check machine
    if recommended_machine:
        validations["machine_correct"] = (
            recommended_machine.upper() in expected["machine"].upper() or
            expected["machine"].upper() in recommended_machine.upper()
        )
        if not validations["machine_correct"]:
            validations["issues"].append(
                f"Wrong machine: expected {expected['machine']}, got {recommended_machine}"
            )
    
    # Check key specs mentioned
    response_lower = response.lower()
    for spec in expected.get("key_specs", []):
        if spec.lower() in response_lower:
            validations["key_specs_mentioned"] += 1
    
    return validations


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    # Demo validation
    validator = PipelineValidator()
    
    # Simulate a trace
    trace = validator.start_trace(
        query="What's the price for 1800x1200mm thermoformer?",
        expected_response="Hi! The PF1-C-1812 costs EUR 39,000..."
    )
    
    validator.record_step("ingest", success=True, duration_ms=50)
    validator.record_step("retrieve", success=True, duration_ms=200, 
                         output_data={"chunks_found": 5})
    validator.record_step("recommend", success=True, duration_ms=100,
                         output_data={"machine": "PF1-C-1812"})
    validator.record_step("generate", success=True, duration_ms=500)
    validator.record_step("verify", success=False, duration_ms=150,
                         errors=["Price mismatch detected"])
    validator.record_step("package", success=True, duration_ms=50)
    
    trace = validator.finalize_trace(
        response="Hi! The PF1-C-1812 costs EUR 45,000...",
        recommended_machine="PF1-C-1812",
        expected_machine="PF1-C-1812",
    )
    
    print(trace.get_summary())
    print("\nVALIDATION REPORT:")
    print(json.dumps(validator.get_validation_report(), indent=2))
