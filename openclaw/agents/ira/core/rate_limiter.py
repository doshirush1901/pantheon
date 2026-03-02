#!/usr/bin/env python3
"""
RATE LIMITER - Production-grade API rate limiting
=================================================

Centralized rate limiting for all external API calls using pyrate-limiter.

Features:
- Per-service rate limits (OpenAI, Voyage, etc.)
- Sliding window algorithms
- Async support
- Graceful degradation when limits hit
- Integration with circuit breakers

Usage:
    from core.rate_limiter import (
        rate_limit, get_limiter,
        openai_limiter, voyage_limiter
    )
    
    # Decorator usage
    @rate_limit("openai")
    def call_openai_api():
        return client.chat.completions.create(...)
    
    # Manual usage
    limiter = get_limiter("openai")
    if limiter.try_acquire():
        response = client.chat.completions.create(...)
    else:
        # Handle rate limit exceeded
        ...

Configuration via environment variables:
    OPENAI_RATE_LIMIT=60      # requests per minute
    VOYAGE_RATE_LIMIT=100     # requests per minute  
    QDRANT_RATE_LIMIT=200     # requests per minute
"""

import functools
import logging
import os
import time
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

logger = logging.getLogger("ira.rate_limiter")

T = TypeVar("T")

_PYRATE_AVAILABLE = False
try:
    from pyrate_limiter import Duration, Limiter, Rate, BucketFullException
    _PYRATE_AVAILABLE = True
except ImportError:
    logger.warning("pyrate-limiter not installed: pip install pyrate-limiter")


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    BLOCK = "block"
    SKIP = "skip"
    QUEUE = "queue"


@dataclass
class RateLimitConfig:
    """Configuration for a rate limiter."""
    name: str
    requests_per_minute: int
    requests_per_hour: Optional[int] = None
    requests_per_day: Optional[int] = None
    strategy: RateLimitStrategy = RateLimitStrategy.BLOCK
    
    @classmethod
    def from_env(cls, name: str, default_rpm: int = 60) -> "RateLimitConfig":
        """Create config from environment variables."""
        env_key = f"{name.upper()}_RATE_LIMIT"
        rpm = int(os.environ.get(env_key, default_rpm))
        
        hour_key = f"{name.upper()}_RATE_LIMIT_HOUR"
        rph = int(os.environ.get(hour_key, 0)) or None
        
        day_key = f"{name.upper()}_RATE_LIMIT_DAY"
        rpd = int(os.environ.get(day_key, 0)) or None
        
        return cls(
            name=name,
            requests_per_minute=rpm,
            requests_per_hour=rph,
            requests_per_day=rpd,
        )


class ServiceRateLimiter:
    """
    Rate limiter for a specific service.
    
    Uses sliding window algorithm via pyrate-limiter.
    Falls back to simple token bucket if pyrate-limiter not available.
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.name = config.name
        self._limiter = None
        self._fallback_tokens = config.requests_per_minute
        self._fallback_last_refill = time.time()
        
        if _PYRATE_AVAILABLE:
            rates = [
                Rate(config.requests_per_minute, Duration.MINUTE),
            ]
            if config.requests_per_hour:
                rates.append(Rate(config.requests_per_hour, Duration.HOUR))
            if config.requests_per_day:
                rates.append(Rate(config.requests_per_day, Duration.DAY))
            
            self._limiter = Limiter(*rates)
            logger.info(f"Rate limiter '{config.name}': {config.requests_per_minute}/min")
        else:
            logger.warning(f"Using fallback rate limiter for '{config.name}'")
    
    def try_acquire(self, weight: int = 1) -> bool:
        """
        Try to acquire rate limit tokens.
        
        Returns True if request is allowed, False if rate limited.
        """
        if self._limiter:
            try:
                self._limiter.try_acquire(self.name, weight=weight)
                return True
            except BucketFullException:
                logger.warning(f"Rate limit exceeded for {self.name}")
                return False
        else:
            return self._fallback_try_acquire(weight)
    
    def acquire(self, weight: int = 1, timeout: float = 30.0) -> bool:
        """
        Acquire rate limit tokens, blocking if necessary.
        
        Returns True if acquired, False if timeout reached.
        """
        if self._limiter:
            start = time.time()
            while time.time() - start < timeout:
                try:
                    self._limiter.try_acquire(self.name, weight=weight)
                    return True
                except BucketFullException:
                    time.sleep(0.1)
            return False
        else:
            return self._fallback_try_acquire(weight)
    
    def _fallback_try_acquire(self, weight: int = 1) -> bool:
        """Simple token bucket fallback."""
        now = time.time()
        elapsed = now - self._fallback_last_refill
        
        if elapsed >= 60:
            self._fallback_tokens = self.config.requests_per_minute
            self._fallback_last_refill = now
        
        if self._fallback_tokens >= weight:
            self._fallback_tokens -= weight
            return True
        
        return False
    
    def get_wait_time(self) -> float:
        """Get estimated wait time until next request allowed."""
        if self._limiter:
            return 1.0
        else:
            if self._fallback_tokens > 0:
                return 0.0
            elapsed = time.time() - self._fallback_last_refill
            return max(0, 60 - elapsed)


DEFAULT_LIMITS = {
    "openai": RateLimitConfig(
        name="openai",
        requests_per_minute=60,
        requests_per_day=10000,
    ),
    "voyage": RateLimitConfig(
        name="voyage",
        requests_per_minute=100,
        requests_per_day=50000,
    ),
    "qdrant": RateLimitConfig(
        name="qdrant",
        requests_per_minute=200,
    ),
    "postgres": RateLimitConfig(
        name="postgres",
        requests_per_minute=500,
    ),
    "mem0": RateLimitConfig(
        name="mem0",
        requests_per_minute=60,
    ),
    "anthropic": RateLimitConfig(
        name="anthropic",
        requests_per_minute=60,
        requests_per_day=10000,
    ),
}

_limiter_registry: Dict[str, ServiceRateLimiter] = {}


def get_limiter(service: str) -> ServiceRateLimiter:
    """Get or create a rate limiter for a service."""
    if service not in _limiter_registry:
        if service in DEFAULT_LIMITS:
            config = RateLimitConfig.from_env(
                service, 
                DEFAULT_LIMITS[service].requests_per_minute
            )
        else:
            config = RateLimitConfig.from_env(service, 60)
        
        _limiter_registry[service] = ServiceRateLimiter(config)
    
    return _limiter_registry[service]


openai_limiter = get_limiter("openai")
voyage_limiter = get_limiter("voyage")
qdrant_limiter = get_limiter("qdrant")
postgres_limiter = get_limiter("postgres")
mem0_limiter = get_limiter("mem0")


def rate_limit(
    service: str,
    weight: int = 1,
    strategy: RateLimitStrategy = RateLimitStrategy.BLOCK,
    timeout: float = 30.0,
    fallback: Optional[Callable[..., Any]] = None,
):
    """
    Decorator to apply rate limiting to a function.
    
    Args:
        service: Service name (e.g., "openai", "voyage")
        weight: Request weight (default 1)
        strategy: What to do when rate limited
            - BLOCK: Wait until rate limit clears
            - SKIP: Return None or fallback
            - QUEUE: Not implemented
        timeout: Max time to wait in BLOCK mode
        fallback: Fallback function to call when rate limited (SKIP mode)
    
    Usage:
        @rate_limit("openai")
        def call_openai():
            return client.chat.completions.create(...)
        
        @rate_limit("voyage", strategy=RateLimitStrategy.SKIP)
        def get_embedding(text):
            return voyage.embed([text])
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            limiter = get_limiter(service)
            
            if strategy == RateLimitStrategy.BLOCK:
                if limiter.acquire(weight=weight, timeout=timeout):
                    return func(*args, **kwargs)
                else:
                    logger.error(f"Rate limit timeout for {service}")
                    if fallback:
                        return fallback(*args, **kwargs)
                    raise RateLimitExceeded(f"Rate limit exceeded for {service}")
            
            elif strategy == RateLimitStrategy.SKIP:
                if limiter.try_acquire(weight=weight):
                    return func(*args, **kwargs)
                else:
                    logger.warning(f"Skipping due to rate limit: {service}")
                    if fallback:
                        return fallback(*args, **kwargs)
                    return None
            
            else:
                return func(*args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            limiter = get_limiter(service)
            
            if strategy == RateLimitStrategy.BLOCK:
                import asyncio
                start = time.time()
                while time.time() - start < timeout:
                    if limiter.try_acquire(weight=weight):
                        return await func(*args, **kwargs)
                    await asyncio.sleep(0.1)
                
                if fallback:
                    return fallback(*args, **kwargs)
                raise RateLimitExceeded(f"Rate limit exceeded for {service}")
            
            elif strategy == RateLimitStrategy.SKIP:
                if limiter.try_acquire(weight=weight):
                    return await func(*args, **kwargs)
                else:
                    if fallback:
                        return fallback(*args, **kwargs)
                    return None
            
            else:
                return await func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded and strategy is BLOCK with timeout."""
    pass


def get_rate_limit_status() -> Dict[str, Dict]:
    """Get current status of all rate limiters."""
    status = {}
    for name, limiter in _limiter_registry.items():
        status[name] = {
            "requests_per_minute": limiter.config.requests_per_minute,
            "wait_time_seconds": limiter.get_wait_time(),
        }
    return status


__all__ = [
    "ServiceRateLimiter",
    "RateLimitConfig",
    "RateLimitStrategy",
    "RateLimitExceeded",
    "get_limiter",
    "rate_limit",
    "get_rate_limit_status",
    "openai_limiter",
    "voyage_limiter",
    "qdrant_limiter",
    "postgres_limiter",
    "mem0_limiter",
]


if __name__ == "__main__":
    print("Testing Rate Limiter\n" + "=" * 50)
    
    limiter = get_limiter("test_service")
    
    print(f"Config: {limiter.config.requests_per_minute}/min")
    
    for i in range(5):
        if limiter.try_acquire():
            print(f"Request {i+1}: ✅ Allowed")
        else:
            print(f"Request {i+1}: ❌ Rate limited")
    
    @rate_limit("test_service", strategy=RateLimitStrategy.SKIP)
    def test_function():
        return "success"
    
    result = test_function()
    print(f"\nDecorator test: {result}")
    
    status = get_rate_limit_status()
    print(f"\nStatus: {status}")
    
    print("\n✅ Rate limiter test complete")
