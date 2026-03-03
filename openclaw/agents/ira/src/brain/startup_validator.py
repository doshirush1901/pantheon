#!/usr/bin/env python3
"""
STARTUP VALIDATOR - Pre-flight checks for Ira
==============================================

Validates all required configuration, connections, and dependencies
before Ira starts processing messages.

Checks:
1. Required environment variables
2. API connections (OpenAI, Voyage, Qdrant)
3. Database connections (PostgreSQL)
4. Telegram API access
5. Required files and directories
6. Memory system health
7. Feature flags consistency

Usage:
    from startup_validator import validate_startup, StartupReport
    
    # Run all checks
    report = validate_startup()
    
    if not report.can_start:
        print("Critical issues found - cannot start")
        for issue in report.critical_issues:
            print(f"  ❌ {issue}")
        sys.exit(1)
    
    if report.warnings:
        print("Warnings (non-blocking):")
        for warning in report.warnings:
            print(f"  ⚠️ {warning}")
"""

import logging
import os
import sys
import time

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SKILL_DIR = Path(__file__).parent  # brain/
SRC_DIR = SKILL_DIR.parent         # src/
AGENT_DIR = SRC_DIR.parent         # ira/
PROJECT_ROOT = AGENT_DIR.parent.parent.parent
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(SKILL_DIR))

# Try to import error monitor (lives in brain/)
try:
    from error_monitor import alert_critical, track_warning
except ImportError:
    def alert_critical(message, context=None): pass
    def track_warning(component, message, context=None): pass


@dataclass
class CheckResult:
    """Result of a single check."""
    name: str
    passed: bool
    message: str
    is_critical: bool = False
    details: Dict = field(default_factory=dict)


@dataclass
class StartupReport:
    """Complete startup validation report."""
    timestamp: str
    checks_total: int
    checks_passed: int
    checks_failed: int
    can_start: bool
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    all_results: List[CheckResult] = field(default_factory=list)
    startup_time_ms: float = 0
    
    def summary(self) -> str:
        """Generate summary string."""
        status = "✅ READY" if self.can_start else "❌ BLOCKED"
        return (
            f"{status} | "
            f"Checks: {self.checks_passed}/{self.checks_total} passed | "
            f"Critical: {len(self.critical_issues)} | "
            f"Warnings: {len(self.warnings)} | "
            f"Time: {self.startup_time_ms:.0f}ms"
        )


class StartupValidator:
    """
    Validates Ira's startup requirements.
    
    Run before starting any message processing to ensure
    all required services and configuration are available.
    """
    
    # Required environment variables with descriptions
    REQUIRED_ENV_VARS = {
        "OPENAI_API_KEY": "Required for LLM responses",
        "TELEGRAM_BOT_TOKEN": "Required for Telegram messaging",
        "TELEGRAM_CHAT_ID": "Required for Telegram messaging",
    }
    
    # Optional but recommended environment variables
    RECOMMENDED_ENV_VARS = {
        "VOYAGE_API_KEY": "Recommended for embeddings",
        "QDRANT_URL": "Recommended for vector search",
        "DATABASE_URL": "Recommended for PostgreSQL storage",
        "MEM0_API_KEY": "Recommended for memory layer",
        "ANTHROPIC_API_KEY": "Optional for Claude models",
    }
    
    # Required directories
    REQUIRED_DIRS = [
        PROJECT_ROOT / "logs",
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "crm",
    ]
    
    def __init__(self):
        self.results: List[CheckResult] = []
        self.start_time = time.time()
    
    def _add_result(self, result: CheckResult) -> None:
        """Add a check result."""
        self.results.append(result)
    
    def check_env_vars(self) -> List[CheckResult]:
        """Check required environment variables."""
        results = []
        
        # Required vars
        for var, description in self.REQUIRED_ENV_VARS.items():
            value = os.environ.get(var, "")
            passed = bool(value and len(value) > 5)
            
            result = CheckResult(
                name=f"env:{var}",
                passed=passed,
                message=f"{var}: {'✓ set' if passed else '✗ missing or invalid'} - {description}",
                is_critical=True,
            )
            results.append(result)
        
        # Recommended vars
        for var, description in self.RECOMMENDED_ENV_VARS.items():
            value = os.environ.get(var, "")
            passed = bool(value and len(value) > 5)
            
            result = CheckResult(
                name=f"env:{var}",
                passed=passed,
                message=f"{var}: {'✓ set' if passed else '⚠ not set'} - {description}",
                is_critical=False,
            )
            results.append(result)
        
        return results
    
    def check_openai_connection(self) -> CheckResult:
        """Test OpenAI API connection."""
        try:
            import openai
            
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                return CheckResult(
                    name="api:openai",
                    passed=False,
                    message="OpenAI API key not configured",
                    is_critical=True,
                )
            
            client = openai.OpenAI(api_key=api_key)
            
            # Quick test call
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": "Say 'ok'"}],
                max_tokens=5,
            )
            
            return CheckResult(
                name="api:openai",
                passed=True,
                message="OpenAI API connection successful",
                is_critical=True,
                details={"model": "gpt-4.1-mini"},
            )
            
        except Exception as e:
            return CheckResult(
                name="api:openai",
                passed=False,
                message=f"OpenAI API connection failed: {str(e)[:100]}",
                is_critical=True,
            )
    
    def check_qdrant_connection(self) -> CheckResult:
        """Test Qdrant vector database connection."""
        try:
            qdrant_url = os.environ.get("QDRANT_URL", "")
            if not qdrant_url:
                return CheckResult(
                    name="api:qdrant",
                    passed=False,
                    message="Qdrant URL not configured",
                    is_critical=False,
                )
            
            from qdrant_client import QdrantClient
            
            client = QdrantClient(url=qdrant_url)
            collections = client.get_collections()
            
            return CheckResult(
                name="api:qdrant",
                passed=True,
                message=f"Qdrant connection successful ({len(collections.collections)} collections)",
                is_critical=False,
                details={"collections": len(collections.collections)},
            )
            
        except Exception as e:
            return CheckResult(
                name="api:qdrant",
                passed=False,
                message=f"Qdrant connection failed: {str(e)[:100]}",
                is_critical=False,
            )
    
    def check_telegram_connection(self) -> CheckResult:
        """Test Telegram Bot API connection."""
        try:
            import requests
            
            token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            if not token:
                return CheckResult(
                    name="api:telegram",
                    passed=False,
                    message="Telegram bot token not configured",
                    is_critical=True,
                )
            
            response = requests.get(
                f"https://api.telegram.org/bot{token}/getMe",
                timeout=10,
            )
            
            if response.ok:
                data = response.json()
                bot_name = data.get("result", {}).get("username", "unknown")
                return CheckResult(
                    name="api:telegram",
                    passed=True,
                    message=f"Telegram API connected as @{bot_name}",
                    is_critical=True,
                    details={"bot_username": bot_name},
                )
            else:
                return CheckResult(
                    name="api:telegram",
                    passed=False,
                    message=f"Telegram API returned error: {response.status_code}",
                    is_critical=True,
                )
            
        except Exception as e:
            return CheckResult(
                name="api:telegram",
                passed=False,
                message=f"Telegram API connection failed: {str(e)[:100]}",
                is_critical=True,
            )
    
    def check_postgres_connection(self) -> CheckResult:
        """Test PostgreSQL connection."""
        try:
            db_url = os.environ.get("DATABASE_URL", "")
            if not db_url:
                return CheckResult(
                    name="db:postgres",
                    passed=False,
                    message="PostgreSQL DATABASE_URL not configured",
                    is_critical=False,
                )
            
            import psycopg2
            
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            
            return CheckResult(
                name="db:postgres",
                passed=True,
                message="PostgreSQL connection successful",
                is_critical=False,
            )
            
        except ImportError:
            return CheckResult(
                name="db:postgres",
                passed=False,
                message="psycopg2 not installed",
                is_critical=False,
            )
        except Exception as e:
            return CheckResult(
                name="db:postgres",
                passed=False,
                message=f"PostgreSQL connection failed: {str(e)[:100]}",
                is_critical=False,
            )
    
    def check_directories(self) -> List[CheckResult]:
        """Check required directories exist."""
        results = []
        
        for dir_path in self.REQUIRED_DIRS:
            exists = dir_path.exists()
            
            # Try to create if doesn't exist
            if not exists:
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    exists = True
                    message = f"Created directory: {dir_path.name}"
                except Exception as e:
                    message = f"Cannot create directory: {dir_path.name} - {e}"
            else:
                message = f"Directory exists: {dir_path.name}"
            
            result = CheckResult(
                name=f"dir:{dir_path.name}",
                passed=exists,
                message=message,
                is_critical=False,
            )
            results.append(result)
        
        return results
    
    def check_memory_system(self) -> CheckResult:
        """Check if memory system is available."""
        try:
            from mem0_memory import get_mem0_service
            mem0 = get_mem0_service()
            
            if mem0:
                return CheckResult(
                    name="memory:mem0",
                    passed=True,
                    message="Mem0 memory system available",
                    is_critical=False,
                )
            else:
                return CheckResult(
                    name="memory:mem0",
                    passed=False,
                    message="Mem0 service not initialized",
                    is_critical=False,
                )
        except ImportError:
            return CheckResult(
                name="memory:mem0",
                passed=False,
                message="Mem0 module not available",
                is_critical=False,
            )
        except Exception as e:
            return CheckResult(
                name="memory:mem0",
                passed=False,
                message=f"Memory system error: {str(e)[:100]}",
                is_critical=False,
            )
    
    def _check_brain_orchestrator(self) -> CheckResult:
        """Check if brain orchestrator is available."""
        try:
            from brain_orchestrator import BrainOrchestrator
            return CheckResult(
                name="brain:orchestrator",
                passed=True,
                message="Brain orchestrator available",
                is_critical=False,
            )
        except ImportError:
            return CheckResult(
                name="brain:orchestrator",
                passed=False,
                message="Brain orchestrator not available (non-critical)",
                is_critical=False,
            )
        except Exception as e:
            return CheckResult(
                name="brain:orchestrator",
                passed=False,
                message=f"Brain orchestrator error: {str(e)[:100]}",
                is_critical=False,
            )

    def check_brain_state(self) -> CheckResult:
        """Check if brain state classes are available."""
        try:
            from src.core.brain_state import BrainState, ProcessingPhase, AttentionManager
            
            state = BrainState(message="test", identity_id="validator")
            
            return CheckResult(
                name="brain:state_classes",
                passed=True,
                message="Brain state classes available",
                is_critical=False,
            )
        except ImportError as e:
            return CheckResult(
                name="brain:state_classes",
                passed=False,
                message=f"Brain state classes not available: {str(e)[:50]}",
                is_critical=False,
            )
        except Exception as e:
            return CheckResult(
                name="brain:state_classes",
                passed=False,
                message=f"Brain state error: {str(e)[:100]}",
                is_critical=False,
            )
    
    def run_all_checks(self, quick: bool = False) -> StartupReport:
        """
        Run all startup validation checks.
        
        Args:
            quick: If True, skip slow connection checks
        
        Returns:
            StartupReport with all results
        """
        self.results = []
        self.start_time = time.time()
        
        # Environment variables (always run)
        self.results.extend(self.check_env_vars())
        
        # Directory checks (always run)
        self.results.extend(self.check_directories())
        
        if not quick:
            # API connection checks
            self.results.append(self.check_openai_connection())
            self.results.append(self.check_telegram_connection())
            self.results.append(self.check_qdrant_connection())
            self.results.append(self.check_postgres_connection())
            
            # System checks
            self.results.append(self.check_memory_system())
            self.results.append(self._check_brain_orchestrator())
        
        # Compile report
        elapsed_ms = (time.time() - self.start_time) * 1000
        
        passed = [r for r in self.results if r.passed]
        failed = [r for r in self.results if not r.passed]
        critical_failed = [r for r in failed if r.is_critical]
        warnings = [r for r in failed if not r.is_critical]
        
        report = StartupReport(
            timestamp=datetime.now().isoformat(),
            checks_total=len(self.results),
            checks_passed=len(passed),
            checks_failed=len(failed),
            can_start=len(critical_failed) == 0,
            critical_issues=[r.message for r in critical_failed],
            warnings=[r.message for r in warnings],
            all_results=self.results,
            startup_time_ms=elapsed_ms,
        )
        
        # Alert if critical issues found
        if critical_failed:
            alert_critical(
                f"Startup validation failed: {len(critical_failed)} critical issues",
                {"issues": [r.name for r in critical_failed]}
            )
        
        return report


def validate_startup(quick: bool = False) -> StartupReport:
    """
    Run startup validation and return report.
    
    Args:
        quick: If True, skip slow connection checks
    
    Returns:
        StartupReport with validation results
    """
    validator = StartupValidator()
    return validator.run_all_checks(quick=quick)


def print_startup_report(report: StartupReport) -> None:
    """Print a formatted startup report."""
    logger.info("\n" + "=" * 60)
    logger.info("IRA STARTUP VALIDATION")
    logger.info("=" * 60)
    
    if report.can_start:
        logger.info("\n✅ READY TO START")
    else:
        logger.error("\n❌ CANNOT START - CRITICAL ISSUES FOUND")
    
    logger.info(f"\nChecks: {report.checks_passed}/{report.checks_total} passed")
    logger.info(f"Time: {report.startup_time_ms:.0f}ms")
    
    if report.critical_issues:
        logger.error(f"\n🚨 CRITICAL ISSUES ({len(report.critical_issues)}):")
        for issue in report.critical_issues:
            logger.error(f"   ❌ {issue}")
    
    if report.warnings:
        logger.warning(f"\n⚠️  WARNINGS ({len(report.warnings)}):")
        for warning in report.warnings:
            logger.warning(f"   ⚠ {warning}")
    
    logger.info("\n" + "=" * 60)


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ira Startup Validator")
    parser.add_argument("--quick", action="store_true", help="Quick check (skip slow API tests)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    report = validate_startup(quick=args.quick)
    
    if args.json:
        import json
        print(json.dumps({
            "timestamp": report.timestamp,
            "can_start": report.can_start,
            "checks_total": report.checks_total,
            "checks_passed": report.checks_passed,
            "critical_issues": report.critical_issues,
            "warnings": report.warnings,
            "startup_time_ms": report.startup_time_ms,
        }, indent=2))
    else:
        print_startup_report(report)
    
    sys.exit(0 if report.can_start else 1)
