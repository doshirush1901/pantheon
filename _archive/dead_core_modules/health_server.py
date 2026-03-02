#!/usr/bin/env python3
"""
HEALTH CHECK SERVER - FastAPI endpoint for system observability
===============================================================

Exposes health check endpoints for monitoring IRA agent status.

Endpoints:
    GET /health         - Quick health status
    GET /health/full    - Detailed health with latency checks
    GET /health/ready   - Kubernetes readiness probe
    GET /health/live    - Kubernetes liveness probe
    GET /metrics        - Prometheus-compatible metrics

Usage:
    # Start server
    python health_server.py
    
    # Or import and run programmatically
    from health_server import create_app, start_health_server
    app = create_app()
    start_health_server(port=8080)

    # Check health
    curl http://localhost:8080/health
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Setup path
CORE_DIR = Path(__file__).parent
AGENT_DIR = CORE_DIR.parent
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(CORE_DIR))

logger = logging.getLogger("ira.health_server")


def create_app():
    """Create FastAPI application with health endpoints."""
    try:
        from fastapi import FastAPI, HTTPException, Response
        from fastapi.responses import JSONResponse
    except ImportError:
        raise ImportError("FastAPI required: pip install fastapi uvicorn")
    
    app = FastAPI(
        title="IRA Health API",
        description="Health check and monitoring endpoints for IRA Agent",
        version="1.0.0",
    )
    
    # Import resilience module
    try:
        from resilience import (
            get_service_status,
            get_system_health_summary,
            check_all_services,
            get_all_circuit_status,
        )
        RESILIENCE_AVAILABLE = True
    except ImportError:
        RESILIENCE_AVAILABLE = False
        logger.warning("Resilience module not available")
    
    # Import error monitor
    try:
        from src.brain.error_monitor import get_monitor
        ERROR_MONITOR_AVAILABLE = True
    except ImportError:
        ERROR_MONITOR_AVAILABLE = False
    
    # Track startup time
    _startup_time = datetime.now()
    
    @app.get("/")
    async def root():
        """Root endpoint with API info."""
        return {
            "service": "IRA Health API",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "health_full": "/health/full",
                "ready": "/health/ready",
                "live": "/health/live",
                "metrics": "/metrics",
            }
        }
    
    @app.get("/health")
    async def health_check():
        """
        Quick health check endpoint.
        
        Returns service status based on circuit breaker states.
        No external API calls made - instant response.
        
        Response:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "services": {
                    "openai": "operational" | "degraded" | "down",
                    ...
                },
                "uptime_seconds": 12345.6
            }
        """
        if not RESILIENCE_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={"status": "error", "message": "Resilience module not available"}
            )
        
        summary = get_system_health_summary()
        uptime = (datetime.now() - _startup_time).total_seconds()
        
        response = {
            "status": summary["overall_status"],
            "health_score": summary["health_score"],
            "services": summary["services"],
            "uptime_seconds": round(uptime, 1),
            "timestamp": summary["timestamp"],
        }
        
        status_code = 200 if summary["overall_status"] == "healthy" else 503
        return JSONResponse(status_code=status_code, content=response)
    
    @app.get("/health/full")
    async def health_check_full():
        """
        Full health check with actual service connectivity tests.
        
        This endpoint performs real health checks against all external
        services (OpenAI, Qdrant, PostgreSQL, Voyage, Mem0).
        
        WARNING: This is slower as it makes actual API calls.
        Use /health for quick status based on circuit breakers.
        
        Response:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "services": {
                    "openai": {
                        "status": "operational",
                        "latency_ms": 123.4,
                        "error": null
                    },
                    ...
                }
            }
        """
        if not RESILIENCE_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={"status": "error", "message": "Resilience module not available"}
            )
        
        start_time = time.time()
        services = await check_all_services()
        check_duration = (time.time() - start_time) * 1000
        
        # Determine overall status
        statuses = [s.status.value for s in services.values()]
        if all(s == "operational" for s in statuses):
            overall = "healthy"
        elif any(s == "down" for s in statuses):
            overall = "unhealthy"
        else:
            overall = "degraded"
        
        response = {
            "status": overall,
            "check_duration_ms": round(check_duration, 1),
            "timestamp": datetime.now().isoformat(),
            "services": {
                name: health.to_dict()
                for name, health in services.items()
            },
        }
        
        status_code = 200 if overall == "healthy" else 503
        return JSONResponse(status_code=status_code, content=response)
    
    @app.get("/health/ready")
    async def readiness_probe():
        """
        Kubernetes readiness probe.
        
        Returns 200 if the service is ready to accept traffic.
        Returns 503 if critical services are down.
        """
        if not RESILIENCE_AVAILABLE:
            return Response(status_code=503)
        
        status = get_service_status()
        
        # Check critical services (openai and qdrant)
        critical_healthy = (
            status.get("openai", "down") != "down" and
            status.get("qdrant", "down") != "down"
        )
        
        if critical_healthy:
            return Response(status_code=200, content="ready")
        else:
            return Response(status_code=503, content="not ready")
    
    @app.get("/health/live")
    async def liveness_probe():
        """
        Kubernetes liveness probe.
        
        Returns 200 if the process is alive.
        This should always return 200 unless the process is dead.
        """
        return Response(status_code=200, content="alive")
    
    @app.get("/metrics")
    async def prometheus_metrics():
        """
        Prometheus-compatible metrics endpoint.
        
        Returns metrics in Prometheus text format.
        """
        if not RESILIENCE_AVAILABLE:
            return Response(
                status_code=503,
                content="# Resilience module not available\n",
                media_type="text/plain"
            )
        
        circuits = get_all_circuit_status()
        uptime = (datetime.now() - _startup_time).total_seconds()
        
        lines = [
            "# HELP ira_uptime_seconds Time since service started",
            "# TYPE ira_uptime_seconds gauge",
            f"ira_uptime_seconds {uptime:.1f}",
            "",
            "# HELP ira_circuit_breaker_state Circuit breaker state (0=closed, 1=half_open, 2=open)",
            "# TYPE ira_circuit_breaker_state gauge",
        ]
        
        state_map = {"closed": 0, "half_open": 1, "open": 2}
        for name, data in circuits.items():
            state_val = state_map.get(data.get("state", "closed"), 0)
            lines.append(f'ira_circuit_breaker_state{{service="{name}"}} {state_val}')
        
        lines.extend([
            "",
            "# HELP ira_circuit_breaker_failures Total failures per circuit",
            "# TYPE ira_circuit_breaker_failures counter",
        ])
        
        for name, data in circuits.items():
            lines.append(f'ira_circuit_breaker_failures{{service="{name}"}} {data.get("total_failures", 0)}')
        
        lines.extend([
            "",
            "# HELP ira_circuit_breaker_calls Total calls per circuit",
            "# TYPE ira_circuit_breaker_calls counter",
        ])
        
        for name, data in circuits.items():
            lines.append(f'ira_circuit_breaker_calls{{service="{name}"}} {data.get("total_calls", 0)}')
        
        # Add error monitor metrics if available
        if ERROR_MONITOR_AVAILABLE:
            try:
                monitor = get_monitor()
                summary = monitor.get_error_summary(hours=1)
                lines.extend([
                    "",
                    "# HELP ira_errors_total Total errors in last hour",
                    "# TYPE ira_errors_total gauge",
                    f"ira_errors_total {summary.get('total_errors', 0)}",
                ])
            except Exception:
                pass
        
        lines.append("")
        return Response(content="\n".join(lines), media_type="text/plain")
    
    @app.get("/circuits")
    async def circuit_breaker_status():
        """Get detailed circuit breaker status."""
        if not RESILIENCE_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={"error": "Resilience module not available"}
            )
        
        return get_all_circuit_status()
    
    @app.post("/circuits/{service}/reset")
    async def reset_circuit_breaker(service: str):
        """Manually reset a circuit breaker."""
        if not RESILIENCE_AVAILABLE:
            raise HTTPException(503, "Resilience module not available")
        
        try:
            from resilience import get_circuit_breaker
            cb = get_circuit_breaker(service)
            if cb:
                cb.reset()
                return {"message": f"Circuit breaker '{service}' reset", "service": service}
            else:
                raise HTTPException(404, f"Circuit breaker '{service}' not found")
        except Exception as e:
            raise HTTPException(500, str(e))
    
    @app.get("/errors")
    async def error_summary():
        """Get error summary from error monitor."""
        if not ERROR_MONITOR_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={"error": "Error monitor not available"}
            )
        
        try:
            monitor = get_monitor()
            return {
                "summary": monitor.get_error_summary(hours=24),
                "patterns": [
                    {
                        "component": p.component,
                        "error_type": p.error_type,
                        "count": p.count,
                        "last_seen": p.last_seen,
                    }
                    for p in monitor.detect_patterns()[:10]
                ]
            }
        except Exception as e:
            raise HTTPException(500, str(e))
    
    return app


def start_health_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    log_level: str = "info",
):
    """
    Start the health check server.
    
    Args:
        host: Host to bind to (default 0.0.0.0)
        port: Port to listen on (default 8080)
        log_level: Uvicorn log level
    """
    try:
        import uvicorn
    except ImportError:
        raise ImportError("uvicorn required: pip install uvicorn")
    
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="IRA Health Check Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--log-level", default="info", help="Log level")
    args = parser.parse_args()
    
    print(f"Starting IRA Health Server on {args.host}:{args.port}")
    start_health_server(host=args.host, port=args.port, log_level=args.log_level)
