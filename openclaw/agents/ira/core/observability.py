#!/usr/bin/env python3
"""
PRODUCTION OBSERVABILITY
========================

Structlog-based production logging with OpenTelemetry integration.

Features:
- Structured JSON logs for production
- Pretty console logs for development
- Request tracing with correlation IDs
- Automatic LLM call instrumentation
- Performance timing with spans
- Error tracking with full context

Usage:
    from core.observability import (
        configure_logging,
        get_logger,
        bind_trace_context,
        traced,
        PerformanceSpan
    )
    
    # Configure at app startup
    configure_logging(environment="production")
    
    # Get a logger
    logger = get_logger("ira.brain")
    logger.info("Processing query", query=text, top_k=10)
    
    # Trace a function
    @traced("retrieval", "vector_search")
    def search_vectors(query: str):
        ...
    
    # Time an operation
    with PerformanceSpan("generation", "llm_call"):
        response = client.chat.completions.create(...)
"""

import functools
import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

LOG_LEVEL = os.environ.get("IRA_LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.environ.get("IRA_LOG_FORMAT", "auto")
ENVIRONMENT = os.environ.get("IRA_ENVIRONMENT", "development")

_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_span_id: ContextVar[str] = ContextVar("span_id", default="")
_trace_context: ContextVar[Dict] = ContextVar("trace_context", default={})

T = TypeVar("T")

_STRUCTLOG_AVAILABLE = False
_OPENTELEMETRY_AVAILABLE = False

try:
    import structlog
    from structlog.processors import JSONRenderer, TimeStamper, add_log_level
    from structlog.contextvars import merge_contextvars
    _STRUCTLOG_AVAILABLE = True
except ImportError as e:
    logger.debug(f"structlog not available: {e}")

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    _OPENTELEMETRY_AVAILABLE = True
except ImportError as e:
    logger.debug(f"opentelemetry not available: {e}")


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class TraceContext:
    """Context for request tracing."""
    trace_id: str
    channel: str = ""
    user_id: str = ""
    thread_id: str = ""
    started_at: float = field(default_factory=time.time)
    spans: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1000


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": _trace_id.get(""),
            "span_id": _span_id.get(""),
        }
        
        if hasattr(record, "event_data"):
            log_data.update(record.event_data)
        
        if record.exc_info:
            import traceback
            log_data["error"] = str(record.exc_info[1])
            log_data["stack_trace"] = "".join(
                traceback.format_exception(*record.exc_info)
            )
        
        return json.dumps(log_data, default=str)


class PrettyFormatter(logging.Formatter):
    """Human-readable colored formatter for development."""
    
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"
    GRAY = "\033[90m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        trace_id = _trace_id.get("")[:8] if _trace_id.get("") else "--------"
        
        base = f"{color}[{record.levelname:7}]{self.RESET} {trace_id} | {record.name} | {record.getMessage()}"
        
        if hasattr(record, "event_data") and record.event_data:
            data_str = " | " + " ".join(f"{k}={v}" for k, v in record.event_data.items())
            base += f"{self.GRAY}{data_str}{self.RESET}"
        
        return base


_configured = False
_structlog_configured = False


def configure_logging(
    environment: str = None,
    log_level: str = None,
    log_format: str = None
):
    """Configure logging for the application."""
    global _configured, _structlog_configured
    
    if _configured:
        return
    
    env = environment or ENVIRONMENT
    level = log_level or LOG_LEVEL
    fmt = log_format or LOG_FORMAT
    
    if fmt == "auto":
        fmt = "json" if env == "production" else "pretty"
    
    if _STRUCTLOG_AVAILABLE and not _structlog_configured:
        processors = [
            merge_contextvars,
            add_log_level,
            TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]
        
        if fmt == "json":
            processors.append(JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer(colors=True))
        
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, level)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
        _structlog_configured = True
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level))
    
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            JSONFormatter() if fmt == "json" else PrettyFormatter()
        )
        root_logger.addHandler(handler)
    
    _configured = True


def get_logger(name: str):
    """Get a configured logger."""
    configure_logging()
    
    if _STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    
    return logging.getLogger(name)


def bind_trace_context(
    trace_id: str = None,
    channel: str = "",
    user_id: str = "",
    **kwargs
):
    """Bind trace context to all subsequent logs."""
    tid = trace_id or str(uuid.uuid4())[:12]
    _trace_id.set(tid)
    _span_id.set(tid)
    
    _trace_context.set({
        "trace_id": tid,
        "channel": channel,
        "user_id": user_id,
        "started_at": time.time(),
        **kwargs
    })
    
    if _STRUCTLOG_AVAILABLE:
        structlog.contextvars.bind_contextvars(
            trace_id=tid,
            channel=channel,
            user_id=user_id[:8] if user_id else ""
        )
    
    return tid


def start_trace(channel: str = "", user_id: str = "", **metadata) -> str:
    """Start a new trace for request tracking."""
    return bind_trace_context(channel=channel, user_id=user_id, **metadata)


def end_trace(success: bool = True, **metadata) -> Dict:
    """End the current trace."""
    context = _trace_context.get({})
    if not context:
        return {}
    
    elapsed = (time.time() - context.get("started_at", time.time())) * 1000
    
    summary = {
        "trace_id": context.get("trace_id"),
        "channel": context.get("channel"),
        "elapsed_ms": round(elapsed, 2),
        "success": success,
        **metadata
    }
    
    logger = get_logger("ira.trace")
    logger.info("trace_ended", **summary)
    
    _trace_id.set("")
    _span_id.set("")
    _trace_context.set({})
    
    if _STRUCTLOG_AVAILABLE:
        structlog.contextvars.clear_contextvars()
    
    return summary


def get_trace_id() -> str:
    """Get the current trace ID."""
    return _trace_id.get("")


class PerformanceSpan:
    """Context manager for timing operations."""
    
    def __init__(self, component: str, operation: str, **attributes):
        self.component = component
        self.operation = operation
        self.attributes = attributes
        self.start_time: Optional[float] = None
        self.duration_ms: Optional[float] = None
        self._parent_span = None
        self._otel_span = None
    
    def __enter__(self) -> "PerformanceSpan":
        self.start_time = time.time()
        self._parent_span = _span_id.get("")
        
        span_id = str(uuid.uuid4())[:8]
        _span_id.set(span_id)
        
        if _OPENTELEMETRY_AVAILABLE:
            tracer = trace.get_tracer(f"ira.{self.component}")
            self._otel_span = tracer.start_span(f"{self.component}.{self.operation}")
            for key, value in self.attributes.items():
                self._otel_span.set_attribute(key, str(value))
        
        logger = get_logger(f"ira.{self.component}")
        logger.debug(f"{self.operation}_started", **self.attributes)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration_ms = (time.time() - self.start_time) * 1000
        logger = get_logger(f"ira.{self.component}")
        
        if exc_type:
            logger.error(
                f"{self.operation}_failed",
                error=str(exc_val),
                duration_ms=self.duration_ms,
                **self.attributes
            )
        else:
            logger.info(
                f"{self.operation}_completed",
                duration_ms=self.duration_ms,
                **self.attributes
            )
        
        if self._otel_span:
            self._otel_span.end()
        
        _span_id.set(self._parent_span or "")


def traced(component: str, operation: str = "operation"):
    """Decorator to automatically trace function execution."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            with PerformanceSpan(component, operation):
                return func(*args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            with PerformanceSpan(component, operation):
                return await func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def log_event(component: str, event: str, level: str = "INFO", **data):
    """Log a structured event."""
    logger = get_logger(f"ira.{component}")
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(event, **data)


def log_error(component: str, error: Exception, context: Optional[Dict] = None, critical: bool = False):
    """Log an error with full context."""
    logger = get_logger(f"ira.{component}")
    
    if critical:
        logger.critical(
            "critical_error",
            error=str(error),
            error_type=type(error).__name__,
            **(context or {}),
            exc_info=True
        )
    else:
        logger.error(
            "error",
            error=str(error),
            error_type=type(error).__name__,
            **(context or {}),
            exc_info=True
        )


configure_logging()
