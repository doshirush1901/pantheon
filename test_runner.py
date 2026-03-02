#!/usr/bin/env python3
"""
Ira Test Runner - Execute test cases from ira_test_suite.md

Usage:
    python test_runner.py RAG-01              # Run single test
    python test_runner.py RAG-01 RAG-02       # Run multiple tests
    python test_runner.py --all               # Run all tests
    python test_runner.py --list              # List all test IDs
    python test_runner.py --category RAG      # Run all RAG tests
    python test_runner.py --channel telegram  # Run all telegram tests
"""

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class TestCase:
    """Represents a single test case from the test suite."""
    test_id: str
    channel: str
    message: str
    expected_outcome: str
    subject: Optional[str] = None  # For email tests


@dataclass
class TestResult:
    """Result of executing a test case."""
    test_case: TestCase
    actual_response: str
    success: bool
    processing_time_ms: float
    error: Optional[str] = None


class TestSuiteParser:
    """Parse test cases from the markdown test suite file."""
    
    def __init__(self, filepath: str = "ira_test_suite.md"):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            # Try relative to script location
            self.filepath = PROJECT_ROOT / filepath
        
        if not self.filepath.exists():
            raise FileNotFoundError(f"Test suite not found: {filepath}")
        
        self.test_cases: Dict[str, TestCase] = {}
        self._parse()
    
    def _parse(self):
        """Parse the markdown file to extract test cases."""
        content = self.filepath.read_text()
        
        # Pattern to match test case blocks
        # Matches ### TEST-ID followed by bullet points
        test_pattern = re.compile(
            r'###\s+([A-Z]+-\d+)\s*\n'  # Test ID header
            r'(?:.*?\n)*?'  # Optional content
            r'-\s+\*\*Channel\*\*:\s*(\w+)\s*\n'  # Channel
            r'-\s+\*\*Message\*\*:\s*(.*?)(?=\n-\s+\*\*Expected)'  # Message (multiline)
            r'\s*-\s+\*\*Expected Outcome\*\*:\s*(.*?)(?=\n\n---|\n\n###|\n\n##|\Z)',  # Expected
            re.DOTALL | re.MULTILINE
        )
        
        for match in test_pattern.finditer(content):
            test_id = match.group(1).strip()
            channel = match.group(2).strip().lower()
            raw_message = match.group(3).strip()
            expected = match.group(4).strip()
            
            # Parse email subject if present
            subject = None
            message = raw_message
            
            # Handle special [EMPTY] placeholder for empty message tests
            if message == "[EMPTY]":
                message = ""
            
            if channel == "email" and raw_message.startswith("Subject:"):
                lines = raw_message.split('\n', 1)
                subject_line = lines[0]
                subject = subject_line.replace("Subject:", "").strip()
                message = lines[1].strip() if len(lines) > 1 else ""
            
            self.test_cases[test_id] = TestCase(
                test_id=test_id,
                channel=channel,
                message=message,
                expected_outcome=expected,
                subject=subject
            )
    
    def get_test(self, test_id: str) -> Optional[TestCase]:
        """Get a specific test case by ID."""
        return self.test_cases.get(test_id.upper())
    
    def get_all_tests(self) -> List[TestCase]:
        """Get all test cases."""
        return list(self.test_cases.values())
    
    def get_tests_by_category(self, category: str) -> List[TestCase]:
        """Get tests matching a category prefix (e.g., 'RAG', 'MEM')."""
        category = category.upper()
        return [tc for tc in self.test_cases.values() 
                if tc.test_id.startswith(category)]
    
    def get_tests_by_channel(self, channel: str) -> List[TestCase]:
        """Get tests for a specific channel."""
        channel = channel.lower()
        return [tc for tc in self.test_cases.values() 
                if tc.channel == channel]
    
    def list_test_ids(self) -> List[str]:
        """List all available test IDs."""
        return sorted(self.test_cases.keys())


class TestRunner:
    """Execute tests against the Ira agent."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.agent = None
        self._init_agent()
    
    def _init_agent(self):
        """Initialize the Ira agent."""
        try:
            from openclaw.agents.ira import get_agent
            self.agent = get_agent()
            if self.verbose:
                print(f"[✓] Agent initialized: {self.agent.config.name} v{self.agent.config.version}")
        except Exception as e:
            print(f"[✗] Failed to initialize agent: {e}")
            sys.exit(1)
    
    def run_test(self, test_case: TestCase) -> TestResult:
        """Execute a single test case."""
        start_time = time.time()
        error = None
        actual_response = ""
        
        try:
            if test_case.channel == "email":
                # Use process_email for email channel
                response = self.agent.process_email(
                    body=test_case.message,
                    from_email="test_user_email@example.com",
                    subject=test_case.subject or "Test Email",
                    thread_id=f"test_thread_{test_case.test_id}"
                )
            else:
                # Use process for telegram/other channels
                response = self.agent.process(
                    message=test_case.message,
                    channel=test_case.channel,
                    user_id=f"test_user_{test_case.channel}",
                    thread_id=f"test_thread_{test_case.test_id}"
                )
            
            actual_response = response.message
            success = response.success
            processing_time = response.processing_time_ms
            
        except Exception as e:
            error = str(e)
            success = False
            processing_time = (time.time() - start_time) * 1000
        
        return TestResult(
            test_case=test_case,
            actual_response=actual_response,
            success=success,
            processing_time_ms=processing_time,
            error=error
        )
    
    def run_tests(self, test_cases: List[TestCase]) -> List[TestResult]:
        """Execute multiple test cases."""
        results = []
        for i, tc in enumerate(test_cases, 1):
            if self.verbose:
                print(f"\n[{i}/{len(test_cases)}] Running {tc.test_id}...")
            result = self.run_test(tc)
            results.append(result)
        return results


def format_result(result: TestResult, show_full: bool = True) -> str:
    """Format a test result for display."""
    tc = result.test_case
    
    # Status indicator
    status = "✓ PASS" if result.success and not result.error else "✗ FAIL"
    if result.error:
        status = "✗ ERROR"
    
    lines = [
        "=" * 70,
        f"Test ID: {tc.test_id}",
        f"Status:  {status}",
        f"Channel: {tc.channel}",
        f"Time:    {result.processing_time_ms:.0f}ms",
        "-" * 70,
    ]
    
    # Message sent
    if tc.subject:
        lines.append(f"Subject: {tc.subject}")
    
    msg_preview = tc.message[:200] + "..." if len(tc.message) > 200 else tc.message
    lines.append(f"Message Sent:\n{msg_preview}")
    
    lines.append("-" * 70)
    
    # Actual response
    if result.error:
        lines.append(f"ERROR: {result.error}")
    else:
        if show_full:
            lines.append(f"Actual Response:\n{result.actual_response}")
        else:
            resp_preview = result.actual_response[:300] + "..." if len(result.actual_response) > 300 else result.actual_response
            lines.append(f"Actual Response:\n{resp_preview}")
    
    lines.append("-" * 70)
    
    # Expected outcome
    lines.append(f"Expected Outcome:\n{tc.expected_outcome}")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)


def format_summary(results: List[TestResult]) -> str:
    """Format a summary of all test results."""
    total = len(results)
    passed = sum(1 for r in results if r.success and not r.error)
    failed = sum(1 for r in results if not r.success or r.error)
    avg_time = sum(r.processing_time_ms for r in results) / total if total > 0 else 0
    
    lines = [
        "",
        "=" * 70,
        "SUMMARY",
        "=" * 70,
        f"Total Tests:  {total}",
        f"Passed:       {passed}",
        f"Failed:       {failed}",
        f"Pass Rate:    {(passed/total*100):.1f}%" if total > 0 else "N/A",
        f"Avg Time:     {avg_time:.0f}ms",
        "=" * 70,
    ]
    
    if failed > 0:
        lines.append("\nFailed Tests:")
        for r in results:
            if not r.success or r.error:
                lines.append(f"  - {r.test_case.test_id}: {r.error or 'Response failure'}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Ira Test Runner - Execute tests from ira_test_suite.md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_runner.py RAG-01              # Run single test
  python test_runner.py RAG-01 MEM-01       # Run multiple tests
  python test_runner.py --all               # Run all tests
  python test_runner.py --list              # List all test IDs
  python test_runner.py --category RAG      # Run all RAG tests
  python test_runner.py --channel telegram  # Run all telegram tests
        """
    )
    
    parser.add_argument(
        "test_ids",
        nargs="*",
        help="Test IDs to run (e.g., RAG-01 MEM-02)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run all tests"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available test IDs"
    )
    parser.add_argument(
        "--category", "-c",
        type=str,
        help="Run all tests in a category (e.g., RAG, MEM, CONV)"
    )
    parser.add_argument(
        "--channel",
        type=str,
        choices=["telegram", "email"],
        help="Run all tests for a specific channel"
    )
    parser.add_argument(
        "--suite", "-s",
        type=str,
        default="ira_test_suite.md",
        help="Path to test suite markdown file"
    )
    parser.add_argument(
        "--brief", "-b",
        action="store_true",
        help="Show brief output (truncate long responses)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output (summary only)"
    )
    
    args = parser.parse_args()
    
    # Parse test suite
    try:
        suite = TestSuiteParser(args.suite)
        print(f"[✓] Loaded test suite: {suite.filepath}")
        print(f"[✓] Found {len(suite.test_cases)} test cases")
    except FileNotFoundError as e:
        print(f"[✗] {e}")
        sys.exit(1)
    
    # List mode
    if args.list:
        print("\nAvailable Test IDs:")
        print("-" * 40)
        for test_id in suite.list_test_ids():
            tc = suite.get_test(test_id)
            print(f"  {test_id:12} [{tc.channel:8}] {tc.message[:40]}...")
        sys.exit(0)
    
    # Determine which tests to run
    test_cases: List[TestCase] = []
    
    if args.all:
        test_cases = suite.get_all_tests()
    elif args.category:
        test_cases = suite.get_tests_by_category(args.category)
        if not test_cases:
            print(f"[✗] No tests found for category: {args.category}")
            sys.exit(1)
    elif args.channel:
        test_cases = suite.get_tests_by_channel(args.channel)
        if not test_cases:
            print(f"[✗] No tests found for channel: {args.channel}")
            sys.exit(1)
    elif args.test_ids:
        for test_id in args.test_ids:
            tc = suite.get_test(test_id)
            if tc:
                test_cases.append(tc)
            else:
                print(f"[!] Warning: Test ID not found: {test_id}")
    else:
        parser.print_help()
        print("\n[!] Please specify test IDs or use --all, --category, or --channel")
        sys.exit(1)
    
    if not test_cases:
        print("[✗] No tests to run")
        sys.exit(1)
    
    print(f"\n[→] Running {len(test_cases)} test(s)...\n")
    
    # Run tests
    runner = TestRunner(verbose=not args.quiet)
    results = runner.run_tests(test_cases)
    
    # Display results
    if not args.quiet:
        for result in results:
            print(format_result(result, show_full=not args.brief))
    
    # Summary
    print(format_summary(results))
    
    # Exit code based on results
    failed = sum(1 for r in results if not r.success or r.error)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
