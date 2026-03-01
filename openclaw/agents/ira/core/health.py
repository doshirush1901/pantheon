#!/usr/bin/env python3
"""
HEALTH CHECK - System health monitoring endpoint
=================================================

Comprehensive health check system for monitoring IRA status.

Features:
- Component health checks (DB, Redis, Qdrant, APIs)
- Dependency verification
- Performance metrics
- Configurable checks
- FastAPI integration ready

Usage:
    from core.health import (
        health_check,
        get_health_status,
        HealthStatus
    )
    
    # Quick health check
    status = await health_check()
    print(status.is_healthy)
    
    # Detailed status
    status = await get_health_status(include_details=True)
    print(status.to_dict())

FastAPI Integration:
    from core.health import create_health_router
    
    app = FastAPI()
    app.include_router(create_health_router())
    # Adds /health and /health/ready endpoints
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("ira.health")


class ComponentStatus(Enum):
    """Status of a component."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a single component."""
    name: str
    status: ComponentStatus
    latency_ms: float = 0.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_healthy(self) -> bool:
        return self.status == ComponentStatus.HEALTHY
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 2),
            "message": self.message,
            "details": self.details,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass
class HealthStatus:
    """Overall system health status."""
    status: ComponentStatus
    components: List[ComponentHealth] = field(default_factory=list)
    version: str = "1.0.0"
    uptime_seconds: float = 0.0
    checked_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_healthy(self) -> bool:
        return self.status == ComponentStatus.HEALTHY
    
    @property
    def is_ready(self) -> bool:
        return self.status in (ComponentStatus.HEALTHY, ComponentStatus.DEGRADED)
    
    def to_dict(self, include_details: bool = True) -> Dict:
        result = {
            "status": self.status.value,
            "healthy": self.is_healthy,
            "ready": self.is_ready,
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 0),
            "checked_at": self.checked_at.isoformat(),
        }
        
        if include_details:
            result["components"] = [c.to_dict() for c in self.components]
        
        return result


_start_time = time.time()


async def check_postgres() -> ComponentHealth:
    """Check PostgreSQL connection."""
    start = time.time()
    
    try:
        import asyncpg
        
        database_url = os.environ.get("DATABASE_URL", "")
        if not database_url:
            return ComponentHealth(
                name="postgres",
                status=ComponentStatus.UNKNOWN,
                message="DATABASE_URL not configured",
            )
        
        conn = await asyncio.wait_for(
            asyncpg.connect(database_url),
            timeout=5.0
        )
        
        await conn.fetchval("SELECT 1")
        await conn.close()
        
        return ComponentHealth(
            name="postgres",
            status=ComponentStatus.HEALTHY,
            latency_ms=(time.time() - start) * 1000,
            message="Connected",
        )
        
    except asyncio.TimeoutError:
        return ComponentHealth(
            name="postgres",
            status=ComponentStatus.UNHEALTHY,
            latency_ms=(time.time() - start) * 1000,
            message="Connection timeout",
        )
    except ImportError:
        return ComponentHealth(
            name="postgres",
            status=ComponentStatus.UNKNOWN,
            message="asyncpg not installed",
        )
    except Exception as e:
        return ComponentHealth(
            name="postgres",
            status=ComponentStatus.UNHEALTHY,
            latency_ms=(time.time() - start) * 1000,
            message=str(e),
        )


async def check_redis() -> ComponentHealth:
    """Check Redis connection."""
    start = time.time()
    
    try:
        import redis.asyncio as aioredis
        
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        
        client = aioredis.from_url(redis_url)
        await asyncio.wait_for(client.ping(), timeout=3.0)
        await client.close()
        
        return ComponentHealth(
            name="redis",
            status=ComponentStatus.HEALTHY,
            latency_ms=(time.time() - start) * 1000,
            message="Connected",
        )
        
    except asyncio.TimeoutError:
        return ComponentHealth(
            name="redis",
            status=ComponentStatus.DEGRADED,
            latency_ms=(time.time() - start) * 1000,
            message="Connection timeout (using memory cache fallback)",
        )
    except ImportError:
        return ComponentHealth(
            name="redis",
            status=ComponentStatus.DEGRADED,
            message="redis not installed (using memory cache)",
        )
    except Exception as e:
        return ComponentHealth(
            name="redis",
            status=ComponentStatus.DEGRADED,
            latency_ms=(time.time() - start) * 1000,
            message=f"Unavailable: {e} (using memory cache)",
        )


async def check_qdrant() -> ComponentHealth:
    """Check Qdrant vector database."""
    start = time.time()
    
    try:
        from qdrant_client import QdrantClient
        
        qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        
        client = QdrantClient(url=qdrant_url, timeout=5.0)
        collections = client.get_collections()
        
        return ComponentHealth(
            name="qdrant",
            status=ComponentStatus.HEALTHY,
            latency_ms=(time.time() - start) * 1000,
            message="Connected",
            details={"collections": len(collections.collections)},
        )
        
    except ImportError:
        return ComponentHealth(
            name="qdrant",
            status=ComponentStatus.UNKNOWN,
            message="qdrant-client not installed",
        )
    except Exception as e:
        return ComponentHealth(
            name="qdrant",
            status=ComponentStatus.UNHEALTHY,
            latency_ms=(time.time() - start) * 1000,
            message=str(e),
        )


async def check_openai() -> ComponentHealth:
    """Check OpenAI API availability."""
    start = time.time()
    
    api_key = os.environ.get("OPENAI_API_KEY", "")
    
    if not api_key:
        return ComponentHealth(
            name="openai",
            status=ComponentStatus.UNKNOWN,
            message="OPENAI_API_KEY not configured",
        )
    
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key, timeout=5.0)
        client.models.list()
        
        return ComponentHealth(
            name="openai",
            status=ComponentStatus.HEALTHY,
            latency_ms=(time.time() - start) * 1000,
            message="API accessible",
        )
        
    except ImportError:
        return ComponentHealth(
            name="openai",
            status=ComponentStatus.UNKNOWN,
            message="openai not installed",
        )
    except Exception as e:
        return ComponentHealth(
            name="openai",
            status=ComponentStatus.UNHEALTHY,
            latency_ms=(time.time() - start) * 1000,
            message=str(e),
        )


async def check_voyage() -> ComponentHealth:
    """Check Voyage AI API availability."""
    start = time.time()
    
    api_key = os.environ.get("VOYAGE_API_KEY", "")
    
    if not api_key:
        return ComponentHealth(
            name="voyage",
            status=ComponentStatus.UNKNOWN,
            message="VOYAGE_API_KEY not configured",
        )
    
    try:
        import voyageai
        
        client = voyageai.Client(api_key=api_key)
        client.embed(["test"], model="voyage-3")
        
        return ComponentHealth(
            name="voyage",
            status=ComponentStatus.HEALTHY,
            latency_ms=(time.time() - start) * 1000,
            message="API accessible",
        )
        
    except ImportError:
        return ComponentHealth(
            name="voyage",
            status=ComponentStatus.UNKNOWN,
            message="voyageai not installed",
        )
    except Exception as e:
        return ComponentHealth(
            name="voyage",
            status=ComponentStatus.DEGRADED,
            latency_ms=(time.time() - start) * 1000,
            message=str(e),
        )


async def check_mem0() -> ComponentHealth:
    """Check Mem0 memory service."""
    start = time.time()
    
    api_key = os.environ.get("MEM0_API_KEY", "")
    
    if not api_key:
        return ComponentHealth(
            name="mem0",
            status=ComponentStatus.UNKNOWN,
            message="MEM0_API_KEY not configured",
        )
    
    try:
        from mem0 import MemoryClient
        
        client = MemoryClient(api_key=api_key)
        
        return ComponentHealth(
            name="mem0",
            status=ComponentStatus.HEALTHY,
            latency_ms=(time.time() - start) * 1000,
            message="Client initialized",
        )
        
    except ImportError:
        return ComponentHealth(
            name="mem0",
            status=ComponentStatus.UNKNOWN,
            message="mem0 not installed",
        )
    except Exception as e:
        return ComponentHealth(
            name="mem0",
            status=ComponentStatus.DEGRADED,
            latency_ms=(time.time() - start) * 1000,
            message=str(e),
        )


async def check_cache() -> ComponentHealth:
    """Check cache layer health."""
    start = time.time()
    
    try:
        from .cache import get_cache, get_all_cache_stats
        
        cache = get_cache()
        
        test_key = "_health_check_"
        cache.set(test_key, "ok", ttl=10)
        result = cache.get(test_key)
        cache.delete(test_key)
        
        stats = get_all_cache_stats()
        
        return ComponentHealth(
            name="cache",
            status=ComponentStatus.HEALTHY if result == "ok" else ComponentStatus.DEGRADED,
            latency_ms=(time.time() - start) * 1000,
            message="Working",
            details={
                "backend": stats.get("main_cache", {}).get("backend", "unknown"),
                "hit_rate": stats.get("main_cache", {}).get("hit_rate", 0),
            },
        )
        
    except ImportError:
        return ComponentHealth(
            name="cache",
            status=ComponentStatus.UNKNOWN,
            message="Cache module not available",
        )
    except Exception as e:
        return ComponentHealth(
            name="cache",
            status=ComponentStatus.DEGRADED,
            latency_ms=(time.time() - start) * 1000,
            message=str(e),
        )


async def check_nlu() -> ComponentHealth:
    """Check NLU processor health."""
    start = time.time()
    
    try:
        import sys
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        from src.brain.nlu_processor import get_nlu_processor
        
        nlu = get_nlu_processor()
        result = nlu.process("test query")
        
        return ComponentHealth(
            name="nlu",
            status=ComponentStatus.HEALTHY,
            latency_ms=(time.time() - start) * 1000,
            message="spaCy model loaded",
            details={"model": nlu.model_name},
        )
        
    except ImportError as e:
        return ComponentHealth(
            name="nlu",
            status=ComponentStatus.DEGRADED,
            message=f"NLU not available: {e}",
        )
    except Exception as e:
        return ComponentHealth(
            name="nlu",
            status=ComponentStatus.DEGRADED,
            latency_ms=(time.time() - start) * 1000,
            message=str(e),
        )


DEFAULT_CHECKS = [
    check_qdrant,
    check_redis,
    check_cache,
    check_openai,
    check_voyage,
]

FULL_CHECKS = DEFAULT_CHECKS + [
    check_postgres,
    check_mem0,
    check_nlu,
]


async def health_check(
    checks: List[Callable] = None,
    timeout: float = 10.0,
) -> HealthStatus:
    """
    Run health checks on system components.
    
    Args:
        checks: List of check functions (defaults to DEFAULT_CHECKS)
        timeout: Maximum time to wait for all checks
        
    Returns:
        HealthStatus with component details
    """
    checks = checks or DEFAULT_CHECKS
    
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*[check() for check in checks], return_exceptions=True),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        return HealthStatus(
            status=ComponentStatus.DEGRADED,
            components=[],
            uptime_seconds=time.time() - _start_time,
        )
    
    components = []
    for result in results:
        if isinstance(result, Exception):
            components.append(ComponentHealth(
                name="unknown",
                status=ComponentStatus.UNHEALTHY,
                message=str(result),
            ))
        else:
            components.append(result)
    
    unhealthy_count = sum(1 for c in components if c.status == ComponentStatus.UNHEALTHY)
    degraded_count = sum(1 for c in components if c.status == ComponentStatus.DEGRADED)
    
    if unhealthy_count > 0:
        overall_status = ComponentStatus.UNHEALTHY
    elif degraded_count > 0:
        overall_status = ComponentStatus.DEGRADED
    else:
        overall_status = ComponentStatus.HEALTHY
    
    return HealthStatus(
        status=overall_status,
        components=components,
        uptime_seconds=time.time() - _start_time,
    )


async def get_health_status(
    include_details: bool = True,
    full_check: bool = False,
) -> Dict:
    """
    Get system health status as dictionary.
    
    Args:
        include_details: Include component details
        full_check: Run all checks including slower ones
        
    Returns:
        Health status dictionary
    """
    checks = FULL_CHECKS if full_check else DEFAULT_CHECKS
    status = await health_check(checks=checks)
    return status.to_dict(include_details=include_details)


def create_health_router():
    """
    Create FastAPI router for health endpoints.
    
    Returns:
        FastAPI APIRouter with /health and /health/ready endpoints
    """
    try:
        from fastapi import APIRouter
        from fastapi.responses import JSONResponse
    except ImportError:
        logger.warning("FastAPI not installed, health router not available")
        return None
    
    router = APIRouter(tags=["health"])
    
    @router.get("/health")
    async def health():
        """Basic health check endpoint."""
        status = await get_health_status(include_details=True, full_check=False)
        status_code = 200 if status["healthy"] else 503
        return JSONResponse(content=status, status_code=status_code)
    
    @router.get("/health/ready")
    async def ready():
        """Readiness probe endpoint."""
        status = await get_health_status(include_details=False, full_check=False)
        status_code = 200 if status["ready"] else 503
        return JSONResponse(content=status, status_code=status_code)
    
    @router.get("/health/live")
    async def live():
        """Liveness probe endpoint."""
        return {"status": "alive", "uptime_seconds": round(time.time() - _start_time, 0)}
    
    @router.get("/health/full")
    async def full():
        """Full health check with all components."""
        status = await get_health_status(include_details=True, full_check=True)
        status_code = 200 if status["healthy"] else 503
        return JSONResponse(content=status, status_code=status_code)
    
    return router


__all__ = [
    "ComponentStatus",
    "ComponentHealth",
    "HealthStatus",
    "health_check",
    "get_health_status",
    "create_health_router",
    "check_postgres",
    "check_redis",
    "check_qdrant",
    "check_openai",
    "check_voyage",
    "check_mem0",
    "check_cache",
    "check_nlu",
]


if __name__ == "__main__":
    import asyncio
    import json
    
    async def main():
        print("Running Health Checks\n" + "=" * 50)
        
        status = await health_check()
        
        print(f"\nOverall Status: {status.status.value}")
        print(f"Healthy: {status.is_healthy}")
        print(f"Ready: {status.is_ready}")
        print(f"Uptime: {status.uptime_seconds:.0f}s")
        
        print("\nComponent Status:")
        for comp in status.components:
            icon = "✅" if comp.is_healthy else "⚠️" if comp.status == ComponentStatus.DEGRADED else "❌"
            print(f"  {icon} {comp.name}: {comp.status.value} ({comp.latency_ms:.0f}ms)")
            if comp.message:
                print(f"     {comp.message}")
        
        print("\nFull JSON:")
        print(json.dumps(status.to_dict(), indent=2))
    
    asyncio.run(main())
