#!/usr/bin/env python3
"""
PRODUCTION RESILIENCE LAYER
============================

Centralized resilience infrastructure for IRA agent with:
- Circuit breakers for all external services
- Exponential backoff retry with tenacity
- Degraded mode fallbacks when services are down
- Health status tracking for observability

Usage:
    from core.resilience import (
        with_resilience, get_service_status,
        openai_breaker, qdrant_breaker, postgres_breaker
    )
    
    # Apply to API calls
    @with_resilience("openai")
    def call_openai_api():
        return client.chat.completions.create(...)
    
    # Check service status
    status = get_service_status()
    print(status["openai"])  # "operational" | "degraded" | "down"
"""

import functools
import logging
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Tuple
from pathlib import Path

T = TypeVar("T")

logger = logging.getLogger("ira.resilience")


class ServiceStatus(Enum):
    """Service health status levels."""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class CircuitState:
    """State tracking for circuit breaker."""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state: str = "closed"  # closed, open, half_open
    last_error: Optional[str] = None
    total_calls: int = 0
    total_failures: int = 0


@dataclass
class ServiceHealth:
    """Health information for a service."""
    name: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_check: Optional[datetime] = None
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    circuit_state: Optional[CircuitState] = None
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "latency_ms": round(self.latency_ms, 2) if self.latency_ms else None,
            "error": self.error_message,
            "circuit": {
                "state": self.circuit_state.state if self.circuit_state else None,
                "failures": self.circuit_state.failure_count if self.circuit_state else 0,
            }
        }


class ProductionCircuitBreaker:
    """
    Production-grade circuit breaker with degraded mode support.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is down, fail fast without calling
    - HALF_OPEN: Testing if service recovered
    
    Provides fallback mechanisms when service is unavailable.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
        fallback: Optional[Callable[..., Any]] = None,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.fallback = fallback
        
        self._state = CircuitState()
        self._lock = threading.Lock()
        
        # Register in global registry
        _circuit_registry[name] = self
    
    @property
    def is_open(self) -> bool:
        return self._state.state == "open"
    
    @property
    def is_closed(self) -> bool:
        return self._state.state == "closed"
    
    def get_state(self) -> CircuitState:
        return self._state
    
    def _should_allow_request(self) -> bool:
        """Determine if a request should be allowed."""
        with self._lock:
            if self._state.state == "closed":
                return True
            
            if self._state.state == "open":
                # Check if recovery timeout has passed
                if self._state.last_failure_time:
                    elapsed = time.time() - self._state.last_failure_time
                    if elapsed >= self.recovery_timeout:
                        self._state.state = "half_open"
                        self._state.success_count = 0
                        logger.info(f"[circuit:{self.name}] Transitioning to HALF_OPEN")
                        return True
                return False
            
            if self._state.state == "half_open":
                return True
            
            return False
    
    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            self._state.success_count += 1
            self._state.last_success_time = time.time()
            
            if self._state.state == "half_open":
                if self._state.success_count >= self.success_threshold:
                    self._state.state = "closed"
                    self._state.failure_count = 0
                    logger.info(f"[circuit:{self.name}] CLOSED - service recovered")
            elif self._state.state == "closed":
                # Reset failure count on success
                self._state.failure_count = max(0, self._state.failure_count - 1)
    
    def record_failure(self, error: Exception) -> None:
        """Record a failed call."""
        with self._lock:
            self._state.failure_count += 1
            self._state.total_failures += 1
            self._state.last_failure_time = time.time()
            self._state.last_error = str(error)[:200]
            
            if self._state.state == "half_open":
                # Recovery failed, back to open
                self._state.state = "open"
                logger.warning(f"[circuit:{self.name}] OPEN - recovery test failed: {error}")
            elif self._state.failure_count >= self.failure_threshold:
                self._state.state = "open"
                logger.warning(
                    f"[circuit:{self.name}] OPEN - {self._state.failure_count} failures: {error}"
                )
    
    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        with self._lock:
            self._state = CircuitState()
            logger.info(f"[circuit:{self.name}] Manually reset")
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Use as decorator."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            self._state.total_calls += 1
            
            if not self._should_allow_request():
                logger.warning(f"[circuit:{self.name}] Request blocked - circuit OPEN")
                if self.fallback:
                    logger.info(f"[circuit:{self.name}] Using fallback")
                    return self.fallback(*args, **kwargs)
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. Service unavailable.",
                    service=self.name,
                    state=self._state
                )
            
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure(e)
                
                # Try fallback on failure
                if self.fallback and self._state.state == "open":
                    logger.info(f"[circuit:{self.name}] Using fallback after failure")
                    return self.fallback(*args, **kwargs)
                raise
        
        return wrapper
    
    def execute(
        self,
        func: Callable[..., T],
        *args,
        fallback_result: Optional[T] = None,
        **kwargs
    ) -> Tuple[T, bool]:
        """
        Execute function with circuit breaker protection.
        
        Returns:
            Tuple of (result, used_fallback)
        """
        self._state.total_calls += 1
        
        if not self._should_allow_request():
            if self.fallback:
                return self.fallback(*args, **kwargs), True
            if fallback_result is not None:
                return fallback_result, True
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN.",
                service=self.name,
                state=self._state
            )
        
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result, False
        except Exception as e:
            self.record_failure(e)
            if self.fallback:
                return self.fallback(*args, **kwargs), True
            if fallback_result is not None:
                return fallback_result, True
            raise


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    def __init__(self, message: str, service: str = "", state: Optional[CircuitState] = None):
        super().__init__(message)
        self.service = service
        self.state = state


# Global circuit breaker registry
_circuit_registry: Dict[str, ProductionCircuitBreaker] = {}


def _degraded_openai_fallback(*args, **kwargs) -> Dict:
    """Fallback when OpenAI is unavailable."""
    return {
        "text": "I'm experiencing connectivity issues with my language model. "
                "Please try again in a few moments.",
        "degraded": True,
        "error": "OpenAI service unavailable"
    }


def _degraded_qdrant_fallback(*args, **kwargs) -> List:
    """Fallback when Qdrant is unavailable - return empty results."""
    logger.warning("[fallback] Qdrant unavailable, returning empty results")
    return []


def _degraded_postgres_fallback(*args, **kwargs) -> None:
    """Fallback when PostgreSQL is unavailable."""
    logger.warning("[fallback] PostgreSQL unavailable")
    return None


def _degraded_voyage_fallback(*args, **kwargs) -> List:
    """Fallback when Voyage is unavailable."""
    logger.warning("[fallback] Voyage unavailable, returning zero vector")
    return [[0.0] * 1024]  # Return zero vector for Voyage-3 dimension


def _degraded_mem0_fallback(*args, **kwargs) -> Dict:
    """Fallback when Mem0 is unavailable."""
    logger.warning("[fallback] Mem0 unavailable, returning empty memories")
    return {"memories": [], "degraded": True}


# Pre-configured circuit breakers for each service
openai_breaker = ProductionCircuitBreaker(
    name="openai",
    failure_threshold=5,
    recovery_timeout=60.0,
    success_threshold=2,
    fallback=_degraded_openai_fallback
)

qdrant_breaker = ProductionCircuitBreaker(
    name="qdrant",
    failure_threshold=3,
    recovery_timeout=30.0,
    success_threshold=2,
    fallback=_degraded_qdrant_fallback
)

postgres_breaker = ProductionCircuitBreaker(
    name="postgres",
    failure_threshold=5,
    recovery_timeout=60.0,
    success_threshold=2,
    fallback=_degraded_postgres_fallback
)

voyage_breaker = ProductionCircuitBreaker(
    name="voyage",
    failure_threshold=3,
    recovery_timeout=30.0,
    success_threshold=2,
    fallback=_degraded_voyage_fallback
)

mem0_breaker = ProductionCircuitBreaker(
    name="mem0",
    failure_threshold=3,
    recovery_timeout=45.0,
    success_threshold=2,
    fallback=_degraded_mem0_fallback
)


def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: float = 0.1,
    retry_on: Tuple[type, ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    Decorator for retrying with exponential backoff.
    
    Uses formula: delay = min(base_delay * (exponential_base ^ attempt), max_delay) + jitter
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential calculation (default 2 = double each time)
        jitter: Random jitter factor (0-1)
        retry_on: Tuple of exception types to retry on
        on_retry: Callback(exception, attempt) called before each retry
    
    Usage:
        @retry_with_exponential_backoff(max_retries=3, base_delay=2.0)
        def call_external_api():
            return requests.get(url)
    """
    import random
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"[retry] {func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise
                    
                    # Calculate delay: base * (2 ^ attempt)
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    # Add jitter
                    delay += delay * jitter * random.random()
                    
                    logger.warning(
                        f"[retry] {func.__name__} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    time.sleep(delay)
            
            raise last_exception
        return wrapper
    return decorator


def with_resilience(
    service: str,
    max_retries: int = 3,
    base_delay: float = 2.0,
    use_circuit_breaker: bool = True,
):
    """
    Unified resilience decorator combining retries and circuit breaker.
    
    Args:
        service: Service name ("openai", "qdrant", "postgres", "voyage", "mem0")
        max_retries: Maximum retry attempts
        base_delay: Base delay for exponential backoff
        use_circuit_breaker: Whether to use circuit breaker
    
    Usage:
        @with_resilience("openai", max_retries=3)
        def generate_response(prompt):
            return client.chat.completions.create(...)
    """
    breaker = _circuit_registry.get(service)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # First apply retry decorator
        @retry_with_exponential_backoff(
            max_retries=max_retries,
            base_delay=base_delay,
        )
        @functools.wraps(func)
        def with_retry(*args, **kwargs) -> T:
            return func(*args, **kwargs)
        
        # Then apply circuit breaker if available and enabled
        if use_circuit_breaker and breaker:
            return breaker(with_retry)
        
        return with_retry
    
    return decorator


def get_circuit_breaker(name: str) -> Optional[ProductionCircuitBreaker]:
    """Get a circuit breaker by name."""
    return _circuit_registry.get(name)


def get_all_circuit_status() -> Dict[str, Dict]:
    """Get status of all circuit breakers."""
    return {
        name: {
            "state": cb._state.state,
            "failure_count": cb._state.failure_count,
            "total_calls": cb._state.total_calls,
            "total_failures": cb._state.total_failures,
            "last_error": cb._state.last_error,
        }
        for name, cb in _circuit_registry.items()
    }


async def check_openai_health() -> ServiceHealth:
    """Check OpenAI API health."""
    health = ServiceHealth(name="openai")
    health.circuit_state = openai_breaker.get_state()
    
    try:
        import openai
        
        start = time.time()
        client = openai.OpenAI()
        # Quick model list call to verify connectivity
        client.models.list()
        health.latency_ms = (time.time() - start) * 1000
        health.status = ServiceStatus.OPERATIONAL
        health.last_check = datetime.now()
    except Exception as e:
        health.status = ServiceStatus.DOWN if openai_breaker.is_open else ServiceStatus.DEGRADED
        health.error_message = str(e)[:100]
        health.last_check = datetime.now()
    
    return health


async def check_qdrant_health() -> ServiceHealth:
    """Check Qdrant health."""
    health = ServiceHealth(name="qdrant")
    health.circuit_state = qdrant_breaker.get_state()
    
    try:
        from qdrant_client import QdrantClient
        import os
        
        start = time.time()
        client = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))
        # Quick health check
        info = client.get_collections()
        health.latency_ms = (time.time() - start) * 1000
        health.status = ServiceStatus.OPERATIONAL
        health.last_check = datetime.now()
    except Exception as e:
        health.status = ServiceStatus.DOWN if qdrant_breaker.is_open else ServiceStatus.DEGRADED
        health.error_message = str(e)[:100]
        health.last_check = datetime.now()
    
    return health


async def check_postgres_health() -> ServiceHealth:
    """Check PostgreSQL health."""
    health = ServiceHealth(name="postgres")
    health.circuit_state = postgres_breaker.get_state()
    
    try:
        import psycopg2
        import os
        
        start = time.time()
        conn = psycopg2.connect(
            os.environ.get("DATABASE_URL", "postgresql://localhost:5432/ira_db"),
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        health.latency_ms = (time.time() - start) * 1000
        health.status = ServiceStatus.OPERATIONAL
        health.last_check = datetime.now()
    except Exception as e:
        health.status = ServiceStatus.DOWN if postgres_breaker.is_open else ServiceStatus.DEGRADED
        health.error_message = str(e)[:100]
        health.last_check = datetime.now()
    
    return health


async def check_voyage_health() -> ServiceHealth:
    """Check Voyage AI health."""
    health = ServiceHealth(name="voyage")
    health.circuit_state = voyage_breaker.get_state()
    
    try:
        import voyageai
        import os
        
        api_key = os.environ.get("VOYAGE_API_KEY", "")
        if not api_key:
            health.status = ServiceStatus.DOWN
            health.error_message = "VOYAGE_API_KEY not configured"
            health.last_check = datetime.now()
            return health
        
        start = time.time()
        client = voyageai.Client(api_key=api_key)
        # Small test embedding
        client.embed(["test"], model="voyage-3")
        health.latency_ms = (time.time() - start) * 1000
        health.status = ServiceStatus.OPERATIONAL
        health.last_check = datetime.now()
    except Exception as e:
        health.status = ServiceStatus.DOWN if voyage_breaker.is_open else ServiceStatus.DEGRADED
        health.error_message = str(e)[:100]
        health.last_check = datetime.now()
    
    return health


async def check_mem0_health() -> ServiceHealth:
    """Check Mem0 health."""
    health = ServiceHealth(name="mem0")
    health.circuit_state = mem0_breaker.get_state()
    
    try:
        from mem0 import MemoryClient
        import os
        
        api_key = os.environ.get("MEM0_API_KEY", "")
        if not api_key:
            health.status = ServiceStatus.DOWN
            health.error_message = "MEM0_API_KEY not configured"
            health.last_check = datetime.now()
            return health
        
        start = time.time()
        client = MemoryClient(api_key=api_key)
        # Quick health check - get memories for test user
        client.get_all(user_id="health_check_test")
        health.latency_ms = (time.time() - start) * 1000
        health.status = ServiceStatus.OPERATIONAL
        health.last_check = datetime.now()
    except Exception as e:
        health.status = ServiceStatus.DOWN if mem0_breaker.is_open else ServiceStatus.DEGRADED
        health.error_message = str(e)[:100]
        health.last_check = datetime.now()
    
    return health


async def check_all_services() -> Dict[str, ServiceHealth]:
    """Check health of all external services."""
    import asyncio
    
    checks = await asyncio.gather(
        check_openai_health(),
        check_qdrant_health(),
        check_postgres_health(),
        check_voyage_health(),
        check_mem0_health(),
        return_exceptions=True,
    )
    
    services = ["openai", "qdrant", "postgres", "voyage", "mem0"]
    results = {}
    
    for service, check in zip(services, checks):
        if isinstance(check, Exception):
            results[service] = ServiceHealth(
                name=service,
                status=ServiceStatus.UNKNOWN,
                error_message=str(check)[:100],
                last_check=datetime.now(),
            )
        else:
            results[service] = check
    
    return results


def get_service_status() -> Dict[str, str]:
    """
    Get simple status string for each service based on circuit breaker state.
    
    Returns:
        Dict mapping service name to status ("operational", "degraded", "down")
    """
    status = {}
    
    for name, cb in _circuit_registry.items():
        state = cb._state
        if state.state == "open":
            status[name] = "down"
        elif state.failure_count > 0:
            status[name] = "degraded"
        else:
            status[name] = "operational"
    
    return status


def get_system_health_summary() -> Dict:
    """
    Get comprehensive system health summary.
    
    Returns JSON-serializable dict with all health information.
    """
    service_status = get_service_status()
    circuit_status = get_all_circuit_status()
    
    # Overall health score
    operational_count = sum(1 for s in service_status.values() if s == "operational")
    total_services = len(service_status)
    health_score = (operational_count / total_services * 100) if total_services > 0 else 0
    
    # Determine overall status
    if all(s == "operational" for s in service_status.values()):
        overall = "healthy"
    elif any(s == "down" for s in service_status.values()):
        overall = "unhealthy"
    else:
        overall = "degraded"
    
    return {
        "overall_status": overall,
        "health_score": round(health_score, 1),
        "timestamp": datetime.now().isoformat(),
        "services": service_status,
        "circuit_breakers": circuit_status,
    }


__all__ = [
    # Circuit breakers
    "ProductionCircuitBreaker",
    "CircuitBreakerOpenError",
    "CircuitState",
    "openai_breaker",
    "qdrant_breaker",
    "postgres_breaker",
    "voyage_breaker",
    "mem0_breaker",
    "get_circuit_breaker",
    "get_all_circuit_status",
    
    # Decorators
    "retry_with_exponential_backoff",
    "with_resilience",
    
    # Health checks
    "ServiceHealth",
    "ServiceStatus",
    "check_all_services",
    "check_openai_health",
    "check_qdrant_health",
    "check_postgres_health",
    "check_voyage_health",
    "check_mem0_health",
    "get_service_status",
    "get_system_health_summary",
]
