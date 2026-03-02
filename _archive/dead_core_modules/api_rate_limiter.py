#!/usr/bin/env python3
"""
API RATE LIMITER - Graceful handling of API rate limits
========================================================

Provides rate limiting and retry logic for external API calls,
specifically designed for:
- OpenAI API (GPT models)
- Voyage AI (embeddings)
- Qdrant (vector search)

Features:
1. Token bucket rate limiting
2. Exponential backoff with jitter
3. Automatic rate limit error detection
4. Circuit breaker for repeated failures
5. Logging and alerting for rate limit events

Usage:
    from api_rate_limiter import openai_with_retry, rate_limited_openai
    
    # As decorator
    @openai_with_retry(max_retries=3)
    def my_api_call():
        return client.chat.completions.create(...)
    
    # Or use the wrapper directly
    response = rate_limited_openai(
        lambda: client.chat.completions.create(...),
        operation="chat_completion"
    )
"""

import os
import time
import random
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from threading import Lock
from typing import Any, Callable, Dict, Optional, TypeVar

# Try to import error monitor
try:
    from error_monitor import track_error, track_warning, alert_critical
except ImportError:
    def track_error(component, error, context=None, severity="error"): pass
    def track_warning(component, message, context=None): pass
    def alert_critical(message, context=None): pass

logger = logging.getLogger("ira.rate_limiter")

T = TypeVar("T")


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 60
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: float = 0.1  # Random jitter factor
    circuit_breaker_threshold: int = 10  # Failures before circuit opens
    circuit_breaker_reset_seconds: int = 300  # Time before circuit resets


# Default configs for different APIs
OPENAI_CONFIG = RateLimitConfig(
    requests_per_minute=60,
    max_retries=5,
    base_delay=1.0,
    max_delay=60.0,
)

VOYAGE_CONFIG = RateLimitConfig(
    requests_per_minute=100,
    max_retries=3,
    base_delay=0.5,
    max_delay=30.0,
)

QDRANT_CONFIG = RateLimitConfig(
    requests_per_minute=1000,
    max_retries=3,
    base_delay=0.2,
    max_delay=10.0,
)


@dataclass
class CircuitBreaker:
    """Circuit breaker to prevent repeated failed calls."""
    failures: int = 0
    last_failure: Optional[datetime] = None
    is_open: bool = False
    threshold: int = 10
    reset_seconds: int = 300
    
    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failures += 1
        self.last_failure = datetime.now()
        
        if self.failures >= self.threshold:
            self.is_open = True
            logger.warning(f"Circuit breaker OPEN after {self.failures} failures")
    
    def record_success(self) -> None:
        """Record a success and reset the circuit."""
        if self.failures > 0:
            logger.info(f"Circuit breaker reset after success (was at {self.failures} failures)")
        self.failures = 0
        self.is_open = False
    
    def can_attempt(self) -> bool:
        """Check if we can attempt a call."""
        if not self.is_open:
            return True
        
        # Check if reset time has passed
        if self.last_failure:
            elapsed = (datetime.now() - self.last_failure).total_seconds()
            if elapsed >= self.reset_seconds:
                self.is_open = False
                self.failures = 0
                logger.info("Circuit breaker reset (timeout)")
                return True
        
        return False


class TokenBucket:
    """Token bucket rate limiter."""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = Lock()
    
    def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens, returning wait time if needed.
        
        Returns:
            Time to wait before tokens are available (0 if available now)
        """
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Add tokens based on elapsed time
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0.0
            
            # Calculate wait time
            needed = tokens - self.tokens
            wait_time = needed / self.rate
            return wait_time


class APIRateLimiter:
    """
    Centralized rate limiter for all API calls.
    
    Manages:
    - Per-API rate limiting
    - Circuit breakers
    - Retry logic with exponential backoff
    """
    
    def __init__(self):
        self._lock = Lock()
        self._buckets: Dict[str, TokenBucket] = {}
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._configs: Dict[str, RateLimitConfig] = {
            "openai": OPENAI_CONFIG,
            "voyage": VOYAGE_CONFIG,
            "qdrant": QDRANT_CONFIG,
        }
        
        # Statistics
        self._stats: Dict[str, Dict] = defaultdict(lambda: {
            "requests": 0,
            "retries": 0,
            "rate_limits": 0,
            "failures": 0,
        })
    
    def _get_bucket(self, api: str) -> TokenBucket:
        """Get or create token bucket for an API."""
        if api not in self._buckets:
            config = self._configs.get(api, OPENAI_CONFIG)
            rate = config.requests_per_minute / 60.0
            self._buckets[api] = TokenBucket(rate, config.requests_per_minute)
        return self._buckets[api]
    
    def _get_circuit(self, api: str) -> CircuitBreaker:
        """Get or create circuit breaker for an API."""
        if api not in self._circuits:
            config = self._configs.get(api, OPENAI_CONFIG)
            self._circuits[api] = CircuitBreaker(
                threshold=config.circuit_breaker_threshold,
                reset_seconds=config.circuit_breaker_reset_seconds,
            )
        return self._circuits[api]
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if an error is a rate limit error."""
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        rate_limit_indicators = [
            "rate_limit",
            "ratelimit",
            "rate limit",
            "429",
            "too many requests",
            "quota exceeded",
            "requests per minute",
            "rpm",
            "tpm",
        ]
        
        return any(indicator in error_str or indicator in error_type.lower() 
                  for indicator in rate_limit_indicators)
    
    def execute(
        self,
        api: str,
        operation: str,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """
        Execute an API call with rate limiting and retry logic.
        
        Args:
            api: API name ("openai", "voyage", "qdrant")
            operation: Operation name for logging
            func: Function to execute
            *args, **kwargs: Arguments to pass to func
        
        Returns:
            Result of func
        
        Raises:
            Exception: If all retries exhausted
        """
        config = self._configs.get(api, OPENAI_CONFIG)
        bucket = self._get_bucket(api)
        circuit = self._get_circuit(api)
        
        # Check circuit breaker
        if not circuit.can_attempt():
            raise Exception(f"Circuit breaker open for {api} - too many recent failures")
        
        # Wait for rate limit
        wait_time = bucket.acquire()
        if wait_time > 0:
            logger.debug(f"[{api}] Rate limiting: waiting {wait_time:.2f}s")
            time.sleep(wait_time)
        
        self._stats[api]["requests"] += 1
        last_error = None
        
        for attempt in range(config.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                circuit.record_success()
                return result
                
            except Exception as e:
                last_error = e
                
                # Check if this is a rate limit error
                if self._is_rate_limit_error(e):
                    self._stats[api]["rate_limits"] += 1
                    
                    # Calculate backoff delay
                    delay = min(
                        config.base_delay * (2 ** attempt),
                        config.max_delay
                    )
                    # Add jitter
                    jitter = delay * config.jitter * random.random()
                    delay += jitter
                    
                    logger.warning(
                        f"[{api}] Rate limit hit on {operation}, "
                        f"attempt {attempt + 1}/{config.max_retries + 1}, "
                        f"waiting {delay:.2f}s"
                    )
                    
                    track_warning(
                        "rate_limiter",
                        f"{api} rate limit on {operation}",
                        {"attempt": attempt + 1, "delay": delay}
                    )
                    
                    if attempt < config.max_retries:
                        self._stats[api]["retries"] += 1
                        time.sleep(delay)
                        continue
                
                # Not a rate limit error or final attempt
                circuit.record_failure()
                
                if attempt < config.max_retries:
                    self._stats[api]["retries"] += 1
                    delay = config.base_delay * (2 ** attempt)
                    logger.warning(f"[{api}] Error on {operation}: {e}, retrying in {delay:.1f}s")
                    time.sleep(delay)
                    continue
                
                # Final failure
                self._stats[api]["failures"] += 1
                track_error(
                    "rate_limiter",
                    e,
                    {"api": api, "operation": operation, "attempts": attempt + 1},
                    severity="error"
                )
                raise
        
        raise last_error
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        return dict(self._stats)


# Global rate limiter instance
_rate_limiter: Optional[APIRateLimiter] = None


def get_rate_limiter() -> APIRateLimiter:
    """Get the global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = APIRateLimiter()
    return _rate_limiter


def rate_limited_openai(
    func: Callable[..., T],
    operation: str = "api_call",
    *args,
    **kwargs
) -> T:
    """Execute an OpenAI API call with rate limiting."""
    return get_rate_limiter().execute("openai", operation, func, *args, **kwargs)


def rate_limited_voyage(
    func: Callable[..., T],
    operation: str = "embedding",
    *args,
    **kwargs
) -> T:
    """Execute a Voyage AI API call with rate limiting."""
    return get_rate_limiter().execute("voyage", operation, func, *args, **kwargs)


def rate_limited_qdrant(
    func: Callable[..., T],
    operation: str = "search",
    *args,
    **kwargs
) -> T:
    """Execute a Qdrant API call with rate limiting."""
    return get_rate_limiter().execute("qdrant", operation, func, *args, **kwargs)


def openai_with_retry(
    max_retries: int = 5,
    operation: str = "api_call",
):
    """
    Decorator for OpenAI API calls with rate limiting.
    
    Usage:
        @openai_with_retry(max_retries=3, operation="chat_completion")
        def generate_response(prompt):
            return client.chat.completions.create(...)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return get_rate_limiter().execute(
                "openai",
                operation,
                lambda: func(*args, **kwargs)
            )
        return wrapper
    return decorator


def voyage_with_retry(
    max_retries: int = 3,
    operation: str = "embedding",
):
    """Decorator for Voyage AI API calls with rate limiting."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return get_rate_limiter().execute(
                "voyage",
                operation,
                lambda: func(*args, **kwargs)
            )
        return wrapper
    return decorator


# CLI for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="API Rate Limiter CLI")
    parser.add_argument("--stats", action="store_true", help="Show rate limiter stats")
    parser.add_argument("--test", action="store_true", help="Run rate limiter test")
    args = parser.parse_args()
    
    limiter = get_rate_limiter()
    
    if args.stats:
        print("\n📊 RATE LIMITER STATS")
        print("=" * 40)
        stats = limiter.get_stats()
        for api, data in stats.items():
            print(f"\n{api}:")
            for key, value in data.items():
                print(f"  {key}: {value}")
    
    elif args.test:
        print("\n🧪 RATE LIMITER TEST")
        print("=" * 40)
        
        def test_func():
            return "success"
        
        # Test normal execution
        result = limiter.execute("openai", "test", test_func)
        print(f"✅ Normal execution: {result}")
        
        # Test with simulated rate limit
        call_count = 0
        def rate_limit_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Rate limit exceeded (429)")
            return "success after retries"
        
        try:
            result = limiter.execute("openai", "retry_test", rate_limit_func)
            print(f"✅ Retry test passed: {result} (took {call_count} attempts)")
        except Exception as e:
            print(f"❌ Retry test failed: {e}")
        
        print(f"\nStats after test: {limiter.get_stats()}")
    
    else:
        print("Use --stats or --test")
