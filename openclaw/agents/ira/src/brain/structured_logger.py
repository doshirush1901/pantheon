#!/usr/bin/env python3
"""
Structured Logger - Production-grade logging with request tracing

Features:
- JSON structured logs for production
- Request correlation IDs (trace through entire flow)
- Performance timing
- Error tracking with context
- Log levels per component
- Async-safe logging

Usage:
    from structured_logger import get_logger, start_trace, log_event
    
    # Start a new trace (typically at request entry)
    trace_id = start_trace(channel="telegram", user_id="123")
    
    # Log events with automatic trace context
    log_event("retrieval", "query_started", {"query": "PF1 specs", "top_k": 10})
    
    # Or use the logger directly
    logger = get_logger("ira.brain")
    logger.info("Processing query", extra={"query": text})
"""

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

# Configuration
LOG_LEVEL = os.environ.get("IRA_LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.environ.get("IRA_LOG_FORMAT", "json")  # "json" or "text"
LOG_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "crm" / "logs"

# Context variables for request tracing
_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_span_id: ContextVar[str] = ContextVar("span_id", default="")
_trace_context: ContextVar[Dict] = ContextVar("trace_context", default={})


@dataclass
class TraceContext:
    """Context for a single trace (request)."""
    trace_id: str
    channel: str = ""
    user_id: str = ""
    thread_id: str = ""
    started_at: float = field(default_factory=time.time)
    spans: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def elapsed_ms(self) -> float:
        return (time.time() - self.started_at) * 1000
    
    def to_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "channel": self.channel,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "elapsed_ms": round(self.elapsed_ms(), 2),
            "span_count": len(self.spans),
        }


@dataclass
class LogEvent:
    """Structured log event."""
    timestamp: str
    level: str
    component: str
    event: str
    trace_id: str
    span_id: str
    message: str
    duration_ms: Optional[float] = None
    data: Dict = field(default_factory=dict)
    error: Optional[str] = None
    stack_trace: Optional[str] = None


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log data
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
            "trace_id": _trace_id.get(""),
            "span_id": _span_id.get(""),
        }
        
        # Add extra fields
        if hasattr(record, "event"):
            log_data["event"] = record.event
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "data"):
            log_data["data"] = record.data
        
        # Add exception info
        if record.exc_info:
            import traceback
            log_data["error"] = str(record.exc_info[1])
            log_data["stack_trace"] = "".join(
                traceback.format_exception(*record.exc_info)
            )
        
        return json.dumps(log_data, default=str)


class PrettyFormatter(logging.Formatter):
    """Human-readable formatter for development."""
    
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        trace_id = _trace_id.get("")[:8] if _trace_id.get("") else "--------"
        
        # Base format
        base = f"{color}[{record.levelname:7}]{self.RESET} {trace_id} | {record.name} | {record.getMessage()}"
        
        # Add duration if present
        if hasattr(record, "duration_ms"):
            base += f" ({record.duration_ms:.1f}ms)"
        
        # Add data if present
        if hasattr(record, "data") and record.data:
            data_str = " | " + " ".join(f"{k}={v}" for k, v in record.data.items())
            base += f"\033[90m{data_str}\033[0m"
        
        return base


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger.
    
    Args:
        name: Logger name (e.g., "ira.brain", "ira.telegram")
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        if LOG_FORMAT == "json":
            handler.setFormatter(StructuredFormatter())
        else:
            handler.setFormatter(PrettyFormatter())
        
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, LOG_LEVEL))
        logger.propagate = False
    
    return logger


def start_trace(
    channel: str = "",
    user_id: str = "",
    thread_id: str = "",
    **metadata
) -> str:
    """
    Start a new trace for request tracking.
    
    Call this at the entry point of a request (e.g., telegram message received).
    
    Returns:
        trace_id for this trace
    """
    trace_id = str(uuid.uuid4())[:12]
    _trace_id.set(trace_id)
    _span_id.set(trace_id)  # Root span
    
    context = TraceContext(
        trace_id=trace_id,
        channel=channel,
        user_id=user_id,
        thread_id=thread_id,
        metadata=metadata
    )
    _trace_context.set(asdict(context))
    
    logger = get_logger("ira.trace")
    logger.info(
        f"Trace started",
        extra={
            "event": "trace_start",
            "data": {"channel": channel, "user_id": user_id[:8] if user_id else ""}
        }
    )
    
    return trace_id


def end_trace(success: bool = True, **metadata) -> Dict:
    """
    End the current trace.
    
    Returns:
        Trace summary
    """
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
    logger.info(
        f"Trace ended",
        extra={
            "event": "trace_end",
            "duration_ms": elapsed,
            "data": summary
        }
    )
    
    # Clear context
    _trace_id.set("")
    _span_id.set("")
    _trace_context.set({})
    
    return summary


def log_event(
    component: str,
    event: str,
    data: Optional[Dict] = None,
    level: str = "INFO",
    duration_ms: Optional[float] = None
) -> None:
    """
    Log a structured event.
    
    Args:
        component: Component name (e.g., "retrieval", "generation")
        event: Event name (e.g., "query_started", "cache_hit")
        data: Additional event data
        level: Log level
        duration_ms: Operation duration if applicable
    """
    logger = get_logger(f"ira.{component}")
    
    extra = {"event": event}
    if data:
        extra["data"] = data
    if duration_ms is not None:
        extra["duration_ms"] = duration_ms
    
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(f"{event}", extra=extra)


def log_error(
    component: str,
    error: Exception,
    context: Optional[Dict] = None,
    critical: bool = False
) -> None:
    """
    Log an error with full context.
    
    Args:
        component: Component where error occurred
        error: The exception
        context: Additional context data
        critical: Whether this is a critical error
    """
    logger = get_logger(f"ira.{component}")
    
    level = logging.CRITICAL if critical else logging.ERROR
    
    logger.log(
        level,
        f"Error in {component}: {str(error)}",
        exc_info=True,
        extra={
            "event": "error",
            "data": context or {}
        }
    )


T = TypeVar("T")


def traced(component: str, event: str = "operation"):
    """
    Decorator to automatically trace function execution.
    
    Usage:
        @traced("retrieval", "vector_search")
        def search_vectors(query: str) -> List[Dict]:
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            start = time.time()
            span_id = str(uuid.uuid4())[:8]
            old_span = _span_id.get("")
            _span_id.set(span_id)
            
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                
                log_event(
                    component,
                    f"{event}_completed",
                    duration_ms=duration
                )
                
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                log_error(component, e, {"event": event, "duration_ms": duration})
                raise
            finally:
                _span_id.set(old_span)
        
        return wrapper
    return decorator


class PerformanceTimer:
    """
    Context manager for timing operations.
    
    Usage:
        with PerformanceTimer("retrieval", "qdrant_query") as timer:
            results = qdrant.search(...)
        # Automatically logs duration
    """
    
    def __init__(self, component: str, event: str, data: Optional[Dict] = None):
        self.component = component
        self.event = event
        self.data = data or {}
        self.start_time = None
        self.duration_ms = None
    
    def __enter__(self) -> "PerformanceTimer":
        self.start_time = time.time()
        log_event(self.component, f"{self.event}_started", self.data)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.duration_ms = (time.time() - self.start_time) * 1000
        
        if exc_type:
            log_event(
                self.component,
                f"{self.event}_failed",
                {**self.data, "error": str(exc_val)},
                level="ERROR",
                duration_ms=self.duration_ms
            )
        else:
            log_event(
                self.component,
                f"{self.event}_completed",
                self.data,
                duration_ms=self.duration_ms
            )


# File-based logging for persistence
class FileLogger:
    """Append-only JSON log file for audit trail."""
    
    def __init__(self, name: str):
        self.log_path = LOG_DIR / f"{name}.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def write(self, event: Dict) -> None:
        """Write an event to the log file."""
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
        event["trace_id"] = _trace_id.get("")
        
        with open(self.log_path, "a") as f:
            f.write(json.dumps(event, default=str) + "\n")
    
    def read_recent(self, limit: int = 100) -> List[Dict]:
        """Read recent events from the log file."""
        if not self.log_path.exists():
            return []
        
        events = []
        with open(self.log_path, "r") as f:
            for line in f:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        
        return events[-limit:]


# Pre-configured loggers for common components
_request_logger = None
_performance_logger = None


def get_request_logger() -> FileLogger:
    """Get the request audit log."""
    global _request_logger
    if _request_logger is None:
        _request_logger = FileLogger("requests")
    return _request_logger


def get_performance_logger() -> FileLogger:
    """Get the performance metrics log."""
    global _performance_logger
    if _performance_logger is None:
        _performance_logger = FileLogger("performance")
    return _performance_logger


def log_request(
    channel: str,
    user_id: str,
    message: str,
    response: str,
    duration_ms: float,
    **metadata
) -> None:
    """Log a complete request for audit trail."""
    get_request_logger().write({
        "channel": channel,
        "user_id": user_id[:20] if user_id else "",
        "message_preview": message[:100],
        "response_preview": response[:200],
        "duration_ms": round(duration_ms, 2),
        **metadata
    })


def log_performance(
    component: str,
    operation: str,
    duration_ms: float,
    success: bool = True,
    **metadata
) -> None:
    """Log a performance metric."""
    get_performance_logger().write({
        "component": component,
        "operation": operation,
        "duration_ms": round(duration_ms, 2),
        "success": success,
        **metadata
    })


if __name__ == "__main__":
    # Test the logger
    print("Testing structured logger...\n")
    
    # Start a trace
    trace_id = start_trace(channel="telegram", user_id="test_user_123")
    print(f"Started trace: {trace_id}")
    
    # Log some events
    log_event("retrieval", "query_started", {"query": "PF1 specs", "top_k": 10})
    log_event("retrieval", "cache_hit", {"cache_tier": "L1"})
    log_event("retrieval", "query_completed", duration_ms=45.2)
    
    # Test performance timer
    with PerformanceTimer("generation", "llm_call", {"model": "gpt-4o-mini"}) as timer:
        time.sleep(0.1)  # Simulate work
    
    print(f"\nTimer recorded: {timer.duration_ms:.1f}ms")
    
    # Test traced decorator
    @traced("brain", "process_query")
    def dummy_operation():
        time.sleep(0.05)
        return "result"
    
    result = dummy_operation()
    
    # End trace
    summary = end_trace(success=True, messages_processed=1)
    print(f"\nTrace summary: {summary}")
    
    # Test file logging
    log_request(
        channel="telegram",
        user_id="test123",
        message="What is PF1?",
        response="The PF1 is...",
        duration_ms=150.5
    )
    
    print("\n✅ Structured logger working correctly")
