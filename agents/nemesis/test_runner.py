#!/usr/bin/env python3
"""
NEMESIS - Autonomous Test Agent for IRA

My purpose is to make IRA stronger through relentless, methodical testing.
I test, evaluate, and generate actionable feedback to improve the system.
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add IRA to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))

# --- CONFIGURATION ---
NEMESIS_DIR = Path(__file__).parent
TEST_CASES_FILE = NEMESIS_DIR / "test_cases.json"
SCORING_RUBRIC_FILE = NEMESIS_DIR / "scoring_rubric.md"
RESULTS_FILE = PROJECT_ROOT / "test_results.md"
LESSONS_FILE = PROJECT_ROOT / "generated_lessons.md"

# Scoring thresholds
PASS_THRESHOLD = 3.5
EXCELLENT_THRESHOLD = 4.5


class NemesisJudge:
    """LLM-as-judge for evaluating IRA responses."""
    
    def __init__(self, rubric: str):
        self.rubric = rubric
    
    def evaluate(
        self,
        test_case: Dict,
        response: str,
        response_time: float
    ) -> Dict[str, Any]:
        """
        Evaluate IRA's response against the scoring rubric.
        
        Uses rule-based evaluation for critical rules and heuristics
        for other dimensions.
        """
        scores = {
            "accuracy": 5,
            "completeness": 5,
            "clarity": 5,
            "rule_adherence": 5
        }
        reasoning_parts = []
        improvement_suggestion = None
        critical_rule_violated = None
        
        response_lower = response.lower()
        question_lower = test_case["question"].lower()
        expected = test_case.get("expected_keywords", [])
        critical_rule = test_case.get("critical_rule")
        
        # --- Rule Adherence (Check Critical Rules First) ---
        
        # AM_THICKNESS Rule
        if critical_rule == "AM_THICKNESS" or "thick" in question_lower or re.search(r'\d+\s*mm', question_lower):
            thickness_match = re.search(r'(\d+(?:\.\d+)?)\s*mm', question_lower)
            if thickness_match:
                thickness = float(thickness_match.group(1))
                if thickness > 1.5:
                    # Must warn about AM series
                    has_warning = any([
                        "1.5mm" in response_lower,
                        "1.5 mm" in response_lower,
                        "≤1.5" in response,
                        "not suitable" in response_lower and "am" in response_lower,
                        "am series was not" in response_lower,
                    ])
                    if not has_warning:
                        scores["rule_adherence"] = 1
                        critical_rule_violated = "AM_THICKNESS"
                        reasoning_parts.append(f"CRITICAL: Failed to warn about AM series {thickness}mm thickness limit.")
                        improvement_suggestion = "Always include AM series warning for materials >1.5mm thick."
                    else:
                        reasoning_parts.append("Correctly warned about AM series thickness limit.")
        
        # PRICING_DISCLAIMER Rule
        if critical_rule == "PRICING_DISCLAIMER" or "price" in question_lower or "cost" in question_lower:
            has_price = any(x in response for x in ["₹", "Rs", "lakh", "crore"])
            if has_price:
                has_disclaimer = "subject to" in response_lower
                if not has_disclaimer:
                    scores["rule_adherence"] = 1
                    critical_rule_violated = "PRICING_DISCLAIMER"
                    reasoning_parts.append("CRITICAL: Price mentioned without required disclaimer.")
                    improvement_suggestion = "Always add 'subject to configuration and current pricing' to prices."
                else:
                    reasoning_parts.append("Correctly included pricing disclaimer.")
        
        # NO_FABRICATION Rule
        if critical_rule == "NO_FABRICATION":
            # Check if response fabricates information about non-existent machines
            fabrication_indicators = [
                "x-1" in response_lower,
                "prototype" in response_lower and "spec" in response_lower,
                len(response) > 200 and "don't" not in response_lower and "cannot" not in response_lower,
            ]
            if any(fabrication_indicators):
                scores["rule_adherence"] = 1
                critical_rule_violated = "NO_FABRICATION"
                reasoning_parts.append("CRITICAL: Response appears to fabricate information about unknown product.")
                improvement_suggestion = "When asked about unknown products, clearly state that information is not available."
            elif any(x in response_lower for x in ["don't", "cannot", "no information", "not available"]):
                reasoning_parts.append("Correctly declined to fabricate information.")
        
        # --- Accuracy (keyword matching) ---
        keywords_found = sum(1 for kw in expected if kw.lower() in response_lower)
        keyword_ratio = keywords_found / len(expected) if expected else 1.0
        
        if keyword_ratio >= 0.8:
            scores["accuracy"] = 5
            reasoning_parts.append(f"Found {keywords_found}/{len(expected)} expected keywords.")
        elif keyword_ratio >= 0.6:
            scores["accuracy"] = 4
            reasoning_parts.append(f"Found {keywords_found}/{len(expected)} expected keywords.")
        elif keyword_ratio >= 0.4:
            scores["accuracy"] = 3
            reasoning_parts.append(f"Missing some expected keywords ({keywords_found}/{len(expected)}).")
        elif keyword_ratio >= 0.2:
            scores["accuracy"] = 2
            reasoning_parts.append(f"Missing many expected keywords ({keywords_found}/{len(expected)}).")
            if not improvement_suggestion:
                improvement_suggestion = f"Include more relevant details about: {', '.join(expected)}"
        else:
            scores["accuracy"] = 1
            reasoning_parts.append(f"Failed to address expected topics ({keywords_found}/{len(expected)}).")
            if not improvement_suggestion:
                improvement_suggestion = f"Response should address: {', '.join(expected)}"
        
        # --- Completeness ---
        if len(response) > 300:
            scores["completeness"] = 5
        elif len(response) > 200:
            scores["completeness"] = 4
        elif len(response) > 100:
            scores["completeness"] = 3
        elif len(response) > 50:
            scores["completeness"] = 2
        else:
            scores["completeness"] = 1
            if not improvement_suggestion:
                improvement_suggestion = "Provide more comprehensive responses."
        
        # --- Clarity ---
        has_structure = any([
            "**" in response,  # Bold text
            "##" in response,  # Headers
            "\n-" in response or "\n•" in response,  # Bullet points
        ])
        
        if has_structure and len(response) > 100:
            scores["clarity"] = 5
        elif has_structure or len(response) > 150:
            scores["clarity"] = 4
        elif len(response) > 50:
            scores["clarity"] = 3
        else:
            scores["clarity"] = 2
        
        # --- Calculate Final Score ---
        if critical_rule_violated:
            # Cap score at 2.0 for critical rule violations
            final_score = min(2.0, sum(scores.values()) / 4)
        else:
            final_score = sum(scores.values()) / 4
        
        # Default improvement suggestion
        if not improvement_suggestion:
            if final_score >= EXCELLENT_THRESHOLD:
                improvement_suggestion = "Response is excellent. Consider adding more specific use cases."
            else:
                improvement_suggestion = "Continue improving knowledge retrieval and response structure."
        
        return {
            "scores": scores,
            "final_score": round(final_score, 2),
            "critical_rule_violated": critical_rule_violated,
            "reasoning": " ".join(reasoning_parts),
            "improvement_suggestion": improvement_suggestion,
            "response_time_ms": round(response_time * 1000, 2),
            "keywords_found": keywords_found,
            "keywords_expected": len(expected)
        }


class Nemesis:
    """
    Autonomous Test Agent for IRA.
    
    I am Nemesis. My purpose is to make IRA stronger.
    """
    
    def __init__(self):
        self.test_cases = self._load_test_cases()
        self.rubric = self._load_rubric()
        self.judge = NemesisJudge(self.rubric)
        self.results: List[Dict] = []
        
    def _load_test_cases(self) -> List[Dict]:
        """Load test cases from JSON file."""
        with open(TEST_CASES_FILE, 'r') as f:
            return json.load(f)
    
    def _load_rubric(self) -> str:
        """Load scoring rubric from markdown file."""
        with open(SCORING_RUBRIC_FILE, 'r') as f:
            return f.read()
    
    async def _invoke_ira(self, question: str) -> tuple[str, float]:
        """
        Send a question to IRA and get the response.
        
        Returns (response_text, response_time_seconds)
        """
        import time
        
        # Import IRA's pipeline
        from src.agents import research, write, verify
        from src.agents.chief_of_staff.agent import analyze_intent
        
        start_time = time.time()
        
        try:
            # Run through IRA's pipeline
            intent = analyze_intent(question)
            
            # Research
            research_output = await research(question, {"intent": intent})
            
            # Write
            context = {
                "intent": intent,
                "channel": "cli",
                "research_output": research_output
            }
            draft = await write(question, context)
            
            # Verify
            verified = await verify(draft, question, context)
            
            response_time = time.time() - start_time
            return verified, response_time
            
        except Exception as e:
            response_time = time.time() - start_time
            return f"Error: {str(e)}", response_time
    
    async def run_test(self, test_case: Dict) -> Dict:
        """Run a single test case and return results."""
        print(f"  📨 Sending: \"{test_case['question'][:60]}...\"")
        
        # Get IRA's response
        response, response_time = await self._invoke_ira(test_case["question"])
        
        print(f"  ⏱️  Response time: {response_time*1000:.0f}ms")
        print(f"  📝 Response length: {len(response)} chars")
        
        # Evaluate the response
        evaluation = self.judge.evaluate(test_case, response, response_time)
        
        return {
            "test_id": test_case["id"],
            "category": test_case["category"],
            "question": test_case["question"],
            "response": response,
            "evaluation": evaluation
        }
    
    async def run_all_tests(self) -> None:
        """Execute the complete test cycle."""
        start_time = datetime.now()
        
        print("=" * 60)
        print("  NEMESIS TEST CYCLE")
        print(f"  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        self.results = []
        
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\n--- Test {i}/{len(self.test_cases)}: {test_case['category']} ---")
            
            result = await self.run_test(test_case)
            self.results.append(result)
            
            score = result["evaluation"]["final_score"]
            status = "✓ PASS" if score >= PASS_THRESHOLD else "✗ FAIL"
            
            if result["evaluation"]["critical_rule_violated"]:
                status = f"✗ CRITICAL ({result['evaluation']['critical_rule_violated']})"
            
            print(f"  📊 Score: {score}/5.0 {status}")
            
            # Small delay between tests
            await asyncio.sleep(0.1)
        
        # Calculate summary statistics
        total_score = sum(r["evaluation"]["final_score"] for r in self.results)
        average_score = total_score / len(self.results) if self.results else 0
        passed = sum(1 for r in self.results if r["evaluation"]["final_score"] >= PASS_THRESHOLD)
        failed = len(self.results) - passed
        critical_violations = sum(1 for r in self.results if r["evaluation"]["critical_rule_violated"])
        
        print("\n" + "=" * 60)
        print("  TEST CYCLE COMPLETE")
        print("=" * 60)
        print(f"  Average Score: {average_score:.2f}/5.0")
        print(f"  Passed: {passed}/{len(self.results)}")
        print(f"  Failed: {failed}/{len(self.results)}")
        print(f"  Critical Violations: {critical_violations}")
        print("=" * 60)
        
        # Generate output files
        self._write_results(start_time, average_score)
        self._write_lessons(start_time)
        
        print(f"\n📄 Results written to: {RESULTS_FILE}")
        print(f"📚 Lessons written to: {LESSONS_FILE}")
    
    def _write_results(self, start_time: datetime, average_score: float) -> None:
        """Write detailed test results to markdown file."""
        with open(RESULTS_FILE, "w") as f:
            f.write(f"# IRA Test Cycle Results\n\n")
            f.write(f"**Date:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Summary
            passed = sum(1 for r in self.results if r["evaluation"]["final_score"] >= PASS_THRESHOLD)
            critical = sum(1 for r in self.results if r["evaluation"]["critical_rule_violated"])
            
            f.write("## Summary\n\n")
            f.write(f"| Metric | Value |\n")
            f.write(f"|--------|-------|\n")
            f.write(f"| **Average Score** | {average_score:.2f}/5.0 |\n")
            f.write(f"| **Tests Passed** | {passed}/{len(self.results)} |\n")
            f.write(f"| **Critical Violations** | {critical} |\n\n")
            
            # Results table
            f.write("## Detailed Results\n\n")
            f.write("| # | Category | Score | Status | Suggestion |\n")
            f.write("|---|----------|-------|--------|------------|\n")
            
            for r in sorted(self.results, key=lambda x: x["evaluation"]["final_score"]):
                score = r["evaluation"]["final_score"]
                if r["evaluation"]["critical_rule_violated"]:
                    status = f"⛔ {r['evaluation']['critical_rule_violated']}"
                elif score >= EXCELLENT_THRESHOLD:
                    status = "✅ Excellent"
                elif score >= PASS_THRESHOLD:
                    status = "✓ Pass"
                else:
                    status = "✗ Fail"
                
                suggestion = r["evaluation"]["improvement_suggestion"][:80] + "..." if len(r["evaluation"]["improvement_suggestion"]) > 80 else r["evaluation"]["improvement_suggestion"]
                
                f.write(f"| {r['test_id']} | {r['category']} | {score} | {status} | {suggestion} |\n")
            
            # Detailed breakdowns
            f.write("\n## Test Details\n\n")
            for r in self.results:
                f.write(f"### Test {r['test_id']}: {r['category']}\n\n")
                f.write(f"**Question:** {r['question']}\n\n")
                f.write(f"**Scores:**\n")
                for dim, score in r["evaluation"]["scores"].items():
                    f.write(f"- {dim.title()}: {score}/5\n")
                f.write(f"- **Final Score:** {r['evaluation']['final_score']}/5.0\n\n")
                f.write(f"**Reasoning:** {r['evaluation']['reasoning']}\n\n")
                f.write(f"**Response Preview:**\n```\n{r['response'][:500]}{'...' if len(r['response']) > 500 else ''}\n```\n\n")
                f.write("---\n\n")
    
    def _write_lessons(self, start_time: datetime) -> None:
        """Generate actionable lessons from test failures."""
        with open(LESSONS_FILE, "w") as f:
            f.write(f"# Generated Lessons from Test Cycle\n\n")
            f.write(f"**Generated:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("The following improvements are recommended based on test analysis. ")
            f.write("Review and integrate these into IRA's knowledge base.\n\n")
            f.write("---\n\n")
            
            # Group by failure type
            critical_failures = [r for r in self.results if r["evaluation"]["critical_rule_violated"]]
            score_failures = [r for r in self.results if not r["evaluation"]["critical_rule_violated"] and r["evaluation"]["final_score"] < PASS_THRESHOLD]
            
            if critical_failures:
                f.write("## 🚨 Critical Rule Violations\n\n")
                f.write("These are the highest priority fixes:\n\n")
                for r in critical_failures:
                    f.write(f"### {r['category']} (Test {r['test_id']})\n\n")
                    f.write(f"- **Rule Violated:** `{r['evaluation']['critical_rule_violated']}`\n")
                    f.write(f"- **Score:** {r['evaluation']['final_score']}/5.0\n")
                    f.write(f"- **Action Required:** {r['evaluation']['improvement_suggestion']}\n")
                    f.write(f"- **Analysis:** {r['evaluation']['reasoning']}\n\n")
            
            if score_failures:
                f.write("## ⚠️ Quality Improvements Needed\n\n")
                for r in score_failures:
                    f.write(f"### {r['category']} (Test {r['test_id']})\n\n")
                    f.write(f"- **Score:** {r['evaluation']['final_score']}/5.0\n")
                    f.write(f"- **Suggestion:** {r['evaluation']['improvement_suggestion']}\n\n")
            
            # General recommendations
            f.write("## 📋 General Recommendations\n\n")
            
            # Analyze patterns
            low_accuracy = [r for r in self.results if r["evaluation"]["scores"]["accuracy"] < 4]
            low_completeness = [r for r in self.results if r["evaluation"]["scores"]["completeness"] < 4]
            low_clarity = [r for r in self.results if r["evaluation"]["scores"]["clarity"] < 4]
            
            if low_accuracy:
                f.write("### Improve Knowledge Retrieval\n\n")
                f.write(f"- {len(low_accuracy)} tests had accuracy scores below 4\n")
                f.write("- Consider expanding the machine database with more details\n")
                f.write("- Improve keyword matching in research phase\n\n")
            
            if low_completeness:
                f.write("### Enhance Response Comprehensiveness\n\n")
                f.write(f"- {len(low_completeness)} tests had completeness scores below 4\n")
                f.write("- Provide more context and detail in responses\n")
                f.write("- Include related information proactively\n\n")
            
            if low_clarity:
                f.write("### Improve Response Structure\n\n")
                f.write(f"- {len(low_clarity)} tests had clarity scores below 4\n")
                f.write("- Use more formatting (headers, bullets)\n")
                f.write("- Apply Pyramid Principle consistently\n\n")
            
            # Final summary
            avg_score = sum(r["evaluation"]["final_score"] for r in self.results) / len(self.results)
            f.write("---\n\n")
            f.write(f"**Overall Assessment:** Average score {avg_score:.2f}/5.0\n\n")
            
            if avg_score >= EXCELLENT_THRESHOLD:
                f.write("🌟 IRA is performing excellently. Focus on edge cases and advanced scenarios.\n")
            elif avg_score >= PASS_THRESHOLD:
                f.write("✓ IRA is performing adequately. Address the suggestions above to improve.\n")
            else:
                f.write("⚠️ IRA needs significant improvement. Prioritize critical rule violations first.\n")


async def main():
    """Main entry point for Nemesis."""
    nemesis = Nemesis()
    await nemesis.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
