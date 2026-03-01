#!/usr/bin/env python3
"""
Tests for Production Resilience Layer

Run with:
    pytest tests/test_resilience.py -v
"""

import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

# Add paths
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent
AGENT_DIR = PROJECT_ROOT / "openclaw" / "agents" / "ira"
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(AGENT_DIR / "core"))

import pytest


class TestCircuitBreaker:
    """Test ProductionCircuitBreaker functionality."""
    
    def test_circuit_starts_closed(self):
        """Circuit breaker should start in closed state."""
        from resilience import ProductionCircuitBreaker
        
        cb = ProductionCircuitBreaker(name="test_closed", failure_threshold=3)
        assert cb.is_closed
        assert not cb.is_open
    
    def test_circuit_opens_after_failures(self):
        """Circuit should open after failure threshold is reached."""
        from resilience import ProductionCircuitBreaker
        
        cb = ProductionCircuitBreaker(name="test_open", failure_threshold=3, recovery_timeout=60)
        
        # Simulate failures
        for i in range(3):
            cb.record_failure(Exception(f"Test error {i}"))
        
        assert cb.is_open
        assert not cb.is_closed
    
    def test_circuit_breaker_blocks_requests_when_open(self):
        """Open circuit should block requests."""
        from resilience import ProductionCircuitBreaker, CircuitBreakerOpenError
        
        cb = ProductionCircuitBreaker(name="test_block", failure_threshold=2)
        
        # Open the circuit
        for _ in range(2):
            cb.record_failure(Exception("Error"))
        
        @cb
        def should_fail():
            return "success"
        
        with pytest.raises(CircuitBreakerOpenError):
            should_fail()
    
    def test_circuit_allows_requests_when_closed(self):
        """Closed circuit should allow requests through."""
        from resilience import ProductionCircuitBreaker
        
        cb = ProductionCircuitBreaker(name="test_allow", failure_threshold=5)
        
        @cb
        def should_succeed():
            return "success"
        
        result = should_succeed()
        assert result == "success"
    
    def test_fallback_used_when_circuit_open(self):
        """Fallback should be used when circuit is open."""
        from resilience import ProductionCircuitBreaker
        
        fallback_called = False
        
        def fallback(*args, **kwargs):
            nonlocal fallback_called
            fallback_called = True
            return "fallback_result"
        
        cb = ProductionCircuitBreaker(
            name="test_fallback",
            failure_threshold=2,
            fallback=fallback
        )
        
        # Open the circuit
        for _ in range(2):
            cb.record_failure(Exception("Error"))
        
        @cb
        def should_use_fallback():
            return "success"
        
        result = should_use_fallback()
        assert fallback_called
        assert result == "fallback_result"
    
    def test_circuit_recovery(self):
        """Circuit should transition to half-open after recovery timeout."""
        from resilience import ProductionCircuitBreaker
        
        cb = ProductionCircuitBreaker(
            name="test_recovery",
            failure_threshold=2,
            recovery_timeout=0.1,  # 100ms for fast test
            success_threshold=1
        )
        
        # Open the circuit
        for _ in range(2):
            cb.record_failure(Exception("Error"))
        
        assert cb.is_open
        
        # Wait for recovery timeout
        time.sleep(0.15)
        
        # Make a successful call through the decorator - this triggers half-open check
        @cb
        def recovery_test():
            return "recovered"
        
        result = recovery_test()
        
        assert result == "recovered"
        assert cb.is_closed


class TestRetryDecorator:
    """Test retry_with_exponential_backoff decorator."""
    
    def test_retry_succeeds_first_try(self):
        """Function should return immediately on success."""
        from resilience import retry_with_exponential_backoff
        
        call_count = 0
        
        @retry_with_exponential_backoff(max_retries=3, base_delay=0.01)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = success_func()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_failure(self):
        """Function should retry on failure."""
        from resilience import retry_with_exponential_backoff
        
        call_count = 0
        
        @retry_with_exponential_backoff(max_retries=3, base_delay=0.01)
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = fail_twice()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausted(self):
        """Should raise exception after retries exhausted."""
        from resilience import retry_with_exponential_backoff
        
        @retry_with_exponential_backoff(max_retries=2, base_delay=0.01)
        def always_fail():
            raise ValueError("Permanent error")
        
        with pytest.raises(ValueError):
            always_fail()


class TestServiceHealth:
    """Test service health check functionality."""
    
    def test_get_service_status(self):
        """Should return status for all services."""
        from resilience import get_service_status
        
        status = get_service_status()
        
        assert "openai" in status
        assert "qdrant" in status
        assert "postgres" in status
        assert "voyage" in status
        assert "mem0" in status
    
    def test_get_system_health_summary(self):
        """Should return comprehensive health summary."""
        from resilience import get_system_health_summary
        
        summary = get_system_health_summary()
        
        assert "overall_status" in summary
        assert "health_score" in summary
        assert "services" in summary
        assert "timestamp" in summary
        assert summary["overall_status"] in ["healthy", "degraded", "unhealthy"]
        assert 0 <= summary["health_score"] <= 100


class TestWithResilienceDecorator:
    """Test the unified with_resilience decorator."""
    
    def test_with_resilience_success(self):
        """Should allow successful calls through."""
        from resilience import with_resilience
        
        @with_resilience("openai", max_retries=1, use_circuit_breaker=False)
        def success_func():
            return "success"
        
        result = success_func()
        assert result == "success"
    
    def test_with_resilience_retry(self):
        """Should retry on failure."""
        from resilience import with_resilience
        
        call_count = 0
        
        @with_resilience("qdrant", max_retries=2, base_delay=0.01, use_circuit_breaker=False)
        def fail_once():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection lost")
            return "success"
        
        result = fail_once()
        assert result == "success"
        assert call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
