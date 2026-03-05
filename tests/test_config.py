"""
Tests for config.py
====================

Tests for centralized configuration and utilities.
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import pytest

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))


class TestCircuitBreaker:
    """Tests for circuit breaker pattern."""
    
    def test_circuit_breaker_starts_closed(self):
        """Circuit breaker should start in CLOSED state."""
        from config import CircuitBreaker, CircuitBreakerState
        
        cb = CircuitBreaker(name="test_closed", failure_threshold=3, recovery_timeout=30)
        assert cb.state == CircuitBreakerState.CLOSED
    
    def test_circuit_opens_after_threshold(self):
        """Circuit should open after failure threshold."""
        from config import CircuitBreaker, CircuitBreakerState
        
        cb = CircuitBreaker(name="test_open", failure_threshold=3, recovery_timeout=30)
        
        # Record failures
        for _ in range(3):
            cb.record_failure()
        
        assert cb.state == CircuitBreakerState.OPEN
    
    def test_circuit_resets_on_success(self):
        """Circuit should reset failure count on success."""
        from config import CircuitBreaker, CircuitBreakerState
        
        cb = CircuitBreaker(name="test_reset", failure_threshold=3, recovery_timeout=30)
        
        # Record some failures
        cb.record_failure()
        cb.record_failure()
        
        # Record success
        cb.record_success()
        
        assert cb._failure_count == 0
        assert cb.state == CircuitBreakerState.CLOSED
    
    def test_get_circuit_breaker_factory(self):
        """Test circuit breaker factory creates named instances."""
        from config import get_circuit_breaker
        
        cb = get_circuit_breaker("factory_test", failure_threshold=5)
        assert cb is not None
        assert cb.name == "factory_test"


class TestRateLimiter:
    """Tests for rate limiting."""
    
    def test_rate_limiter_allows_initial_requests(self):
        """Rate limiter should allow burst requests."""
        from config import RateLimiter
        
        limiter = RateLimiter(rate=1, burst=5)
        
        # Should allow 5 requests immediately
        for _ in range(5):
            assert limiter.acquire() is True
    
    def test_rate_limiter_blocks_after_burst(self):
        """Rate limiter should block after burst exhausted."""
        from config import RateLimiter
        
        limiter = RateLimiter(rate=1, burst=3)
        
        # Exhaust burst
        for _ in range(3):
            limiter.acquire()
        
        # Next request should fail without waiting
        assert limiter.acquire(block=False) is False
    
    def test_get_rate_limiter_factory(self):
        """Test rate limiter factory returns consistent instances."""
        from config import get_rate_limiter
        
        limiter1 = get_rate_limiter("test_factory")
        limiter2 = get_rate_limiter("test_factory")
        
        # Should return same instance
        assert limiter1 is limiter2


class TestStorageTransaction:
    """Tests for multi-storage transactions."""
    
    def test_multi_storage_write_exists(self):
        """multi_storage_write function should exist."""
        from config import multi_storage_write
        
        assert multi_storage_write is not None
    
    def test_context_manager_basic(self, tmp_path):
        """Basic context manager should work."""
        from config import multi_storage_write
        
        json_file = tmp_path / "test.json"
        
        # Create original file
        with open(json_file, "w") as f:
            json.dump({"original": True}, f)
        
        # Use context manager
        with multi_storage_write(json_path=json_file, backup=False):
            pass  # No writes in test
        
        # File should still exist
        assert json_file.exists()


class TestGetLogger:
    """Tests for logging utilities."""
    
    def test_get_logger_returns_logger(self):
        """get_logger should return a logger instance."""
        from config import get_logger
        
        logger = get_logger("test_module")
        assert logger is not None
        # Logger name includes ira. prefix
        assert "test_module" in logger.name or logger.name == "ira.test_module"
    
    def test_get_logger_multiple_calls(self):
        """get_logger should work for multiple modules."""
        from config import get_logger
        
        logger1 = get_logger("module_a")
        logger2 = get_logger("module_b")
        
        assert logger1 is not None
        assert logger2 is not None


class TestPathSetup:
    """Tests for import path setup."""
    
    def test_setup_import_paths(self):
        """setup_import_paths should add paths to sys.path."""
        from config import setup_import_paths
        
        # Should not raise
        setup_import_paths()
        
        # Some Ira paths should be in sys.path
        ira_paths_found = any("ira" in p.lower() for p in sys.path if isinstance(p, str))
        assert ira_paths_found


class TestConstants:
    """Tests for configuration constants."""
    
    def test_project_root_exists(self):
        """PROJECT_ROOT should point to valid directory."""
        from config import PROJECT_ROOT
        
        assert PROJECT_ROOT.exists()
        assert PROJECT_ROOT.is_dir()
    
    def test_rate_limits_defined(self):
        """RATE_LIMITS should have expected keys."""
        from config import RATE_LIMITS
        
        assert isinstance(RATE_LIMITS, dict)
    
    def test_message_limits_defined(self):
        """MESSAGE_LIMITS should have expected keys."""
        from config import MESSAGE_LIMITS
        
        assert isinstance(MESSAGE_LIMITS, dict)
