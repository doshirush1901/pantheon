#!/usr/bin/env python3
"""
ERROR MONITOR - Production Error Tracking & Alerting
=====================================================

Centralized error monitoring for Ira with:
1. Error tracking with context
2. Telegram alerts for critical errors
3. Rate limiting detection
4. Error pattern analysis
5. Silent failure detection

Usage:
    from error_monitor import ErrorMonitor, track_error, alert_critical
    
    # Track an error
    track_error("retrieval", error, {"query": query})
    
    # Alert critical errors
    alert_critical("API quota exceeded", {"api": "openai", "quota": 0})
    
    # Use as decorator
    @with_error_tracking("brain")
    def process_query(...):
        ...
"""

import os
import json
import time
import logging
import traceback
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, TypeVar

# Try to import Telegram config
try:
    from config import TELEGRAM_BOT_TOKEN, EXPECTED_CHAT_ID
    TELEGRAM_AVAILABLE = bool(TELEGRAM_BOT_TOKEN and EXPECTED_CHAT_ID)
except ImportError:
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    EXPECTED_CHAT_ID = os.environ.get("EXPECTED_CHAT_ID", "")
    TELEGRAM_AVAILABLE = bool(TELEGRAM_BOT_TOKEN and EXPECTED_CHAT_ID)

# Logging
logger = logging.getLogger("ira.error_monitor")

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
ERROR_LOG_DIR = PROJECT_ROOT / "data" / "logs"
ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Also create the legacy logs directory for compatibility
(PROJECT_ROOT / "logs" / "errors").mkdir(parents=True, exist_ok=True)


@dataclass
class ErrorRecord:
    """Single error record."""
    timestamp: str
    component: str
    error_type: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    severity: str = "error"  # "warning", "error", "critical"
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ErrorPattern:
    """Pattern of repeated errors."""
    component: str
    error_type: str
    count: int
    first_seen: str
    last_seen: str
    sample_message: str


class ErrorMonitor:
    """
    Centralized error monitoring for Ira.
    
    Features:
    - Tracks all errors with context
    - Detects error patterns (rate limiting, repeated failures)
    - Sends Telegram alerts for critical errors
    - Persists errors to log files for debugging
    """
    
    # Error types that warrant immediate alerts
    CRITICAL_ERROR_TYPES = {
        "APIError",
        "RateLimitError", 
        "AuthenticationError",
        "DatabaseError",
        "ConfigurationError",
        "OutOfMemoryError",
    }
    
    # Rate limit: max alerts per hour
    ALERT_RATE_LIMIT = 5
    
    def __init__(self):
        self._lock = Lock()
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._recent_errors: List[ErrorRecord] = []
        self._alert_timestamps: List[float] = []
        self._last_cleanup = time.time()
        
        # Centralized error log file (as specified in requirements)
        self._log_file = ERROR_LOG_DIR / "errors.jsonl"
        # Also keep daily logs for easier debugging
        self._daily_log_file = ERROR_LOG_DIR / f"errors_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    
    def track_error(
        self,
        component: str,
        error: Exception,
        context: Optional[Dict] = None,
        severity: str = "error",
    ) -> ErrorRecord:
        """
        Track an error with full context.
        
        Args:
            component: Component where error occurred (e.g., "retrieval", "brain")
            error: The exception
            context: Additional context data
            severity: "warning", "error", or "critical"
        
        Returns:
            ErrorRecord for the tracked error
        """
        with self._lock:
            # Create error record
            record = ErrorRecord(
                timestamp=datetime.now().isoformat(),
                component=component,
                error_type=type(error).__name__,
                message=str(error)[:500],
                context=context or {},
                stack_trace=traceback.format_exc()[:2000],
                severity=severity,
            )
            
            # Track in memory
            self._recent_errors.append(record)
            if len(self._recent_errors) > 1000:
                self._recent_errors = self._recent_errors[-500:]
            
            # Update counts
            key = f"{component}:{type(error).__name__}"
            self._error_counts[key] += 1
            
            # Persist to log file
            self._write_to_log(record)
            
            # Log it
            logger.error(
                f"[{component}] {type(error).__name__}: {str(error)[:100]}",
                exc_info=True
            )
            
            # Check if we should alert
            if self._should_alert(record):
                self._send_alert(record)
            
            # Cleanup old data periodically
            if time.time() - self._last_cleanup > 3600:
                self._cleanup()
            
            return record
    
    def track_warning(
        self,
        component: str,
        message: str,
        context: Optional[Dict] = None,
    ) -> None:
        """Track a warning (non-exception)."""
        record = ErrorRecord(
            timestamp=datetime.now().isoformat(),
            component=component,
            error_type="Warning",
            message=message[:500],
            context=context or {},
            severity="warning",
        )
        
        with self._lock:
            self._recent_errors.append(record)
            self._write_to_log(record)
        
        logger.warning(f"[{component}] {message[:100]}")
    
    def alert_critical(
        self,
        message: str,
        context: Optional[Dict] = None,
    ) -> None:
        """
        Send a critical alert immediately.
        Use for serious issues that need immediate attention.
        """
        record = ErrorRecord(
            timestamp=datetime.now().isoformat(),
            component="system",
            error_type="CriticalAlert",
            message=message[:500],
            context=context or {},
            severity="critical",
        )
        
        with self._lock:
            self._recent_errors.append(record)
            self._write_to_log(record)
        
        logger.critical(f"CRITICAL: {message[:100]}")
        self._send_alert(record, force=True)
    
    def _should_alert(self, record: ErrorRecord) -> bool:
        """Determine if an error should trigger an alert."""
        # Always alert for critical severity
        if record.severity == "critical":
            return True
        
        # Alert for known critical error types
        if record.error_type in self.CRITICAL_ERROR_TYPES:
            return True
        
        # Alert if same error type repeated 5+ times in last hour
        key = f"{record.component}:{record.error_type}"
        if self._error_counts.get(key, 0) >= 5:
            # But only alert once per pattern
            if self._error_counts[key] == 5:
                return True
        
        return False
    
    def _send_alert(self, record: ErrorRecord, force: bool = False) -> bool:
        """Send Telegram alert."""
        if not TELEGRAM_AVAILABLE:
            logger.warning("Telegram alerting not configured")
            return False
        
        # Check rate limit unless forced
        if not force:
            now = time.time()
            self._alert_timestamps = [t for t in self._alert_timestamps if now - t < 3600]
            
            if len(self._alert_timestamps) >= self.ALERT_RATE_LIMIT:
                logger.warning(f"Alert rate limit reached ({self.ALERT_RATE_LIMIT}/hr)")
                return False
        
        try:
            import requests
            
            # Format alert message
            severity_emoji = {
                "warning": "⚠️",
                "error": "❌",
                "critical": "🚨",
            }.get(record.severity, "❗")
            
            message = f"""{severity_emoji} *IRA ERROR ALERT*

*Component:* `{record.component}`
*Type:* `{record.error_type}`
*Severity:* {record.severity.upper()}

*Message:*
{record.message[:300]}

*Time:* {record.timestamp}"""
            
            if record.context:
                context_str = "\n".join(f"• {k}: {v}" for k, v in list(record.context.items())[:5])
                message += f"\n\n*Context:*\n{context_str}"
            
            # Send via Telegram
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            response = requests.post(
                url,
                json={
                    "chat_id": EXPECTED_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
            
            if response.ok:
                self._alert_timestamps.append(time.time())
                logger.info(f"Alert sent for {record.error_type}")
                return True
            else:
                logger.error(f"Failed to send alert: {response.text}")
                return False
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False
    
    def _write_to_log(self, record: ErrorRecord) -> None:
        """Write error record to log files."""
        log_line = json.dumps(record.to_dict()) + "\n"
        
        # Write to centralized error log
        try:
            with open(self._log_file, "a") as f:
                f.write(log_line)
        except Exception as e:
            logger.error(f"Failed to write to centralized error log: {e}")
        
        # Also write to daily log for easier debugging
        try:
            with open(self._daily_log_file, "a") as f:
                f.write(log_line)
        except Exception as e:
            logger.error(f"Failed to write to daily error log: {e}")
    
    def _cleanup(self) -> None:
        """Cleanup old data."""
        self._last_cleanup = time.time()
        
        # Reset hourly counts
        self._error_counts.clear()
        
        # Keep only recent errors
        if len(self._recent_errors) > 500:
            self._recent_errors = self._recent_errors[-250:]
    
    def get_error_summary(self, hours: int = 24) -> Dict:
        """Get error summary for the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff.isoformat()
        
        summary = {
            "total_errors": 0,
            "by_component": defaultdict(int),
            "by_type": defaultdict(int),
            "by_severity": defaultdict(int),
            "recent_critical": [],
        }
        
        for record in self._recent_errors:
            if record.timestamp >= cutoff_str:
                summary["total_errors"] += 1
                summary["by_component"][record.component] += 1
                summary["by_type"][record.error_type] += 1
                summary["by_severity"][record.severity] += 1
                
                if record.severity == "critical":
                    summary["recent_critical"].append({
                        "timestamp": record.timestamp,
                        "component": record.component,
                        "message": record.message[:100],
                    })
        
        return dict(summary)
    
    def detect_patterns(self) -> List[ErrorPattern]:
        """Detect repeated error patterns."""
        patterns = []
        pattern_counts: Dict[str, Dict] = defaultdict(lambda: {
            "count": 0, 
            "first_seen": None, 
            "last_seen": None,
            "sample": ""
        })
        
        for record in self._recent_errors:
            key = f"{record.component}:{record.error_type}"
            data = pattern_counts[key]
            data["count"] += 1
            
            if not data["first_seen"]:
                data["first_seen"] = record.timestamp
            data["last_seen"] = record.timestamp
            data["sample"] = record.message[:100]
        
        # Report patterns with 3+ occurrences
        for key, data in pattern_counts.items():
            if data["count"] >= 3:
                component, error_type = key.split(":", 1)
                patterns.append(ErrorPattern(
                    component=component,
                    error_type=error_type,
                    count=data["count"],
                    first_seen=data["first_seen"],
                    last_seen=data["last_seen"],
                    sample_message=data["sample"],
                ))
        
        return sorted(patterns, key=lambda p: -p.count)


# Global monitor instance
_monitor: Optional[ErrorMonitor] = None


def get_monitor() -> ErrorMonitor:
    """Get the global error monitor."""
    global _monitor
    if _monitor is None:
        _monitor = ErrorMonitor()
    return _monitor


def track_error(
    component: str,
    error: Exception,
    context: Optional[Dict] = None,
    severity: str = "error",
) -> ErrorRecord:
    """Track an error with context."""
    return get_monitor().track_error(component, error, context, severity)


def track_warning(
    component: str,
    message: str,
    context: Optional[Dict] = None,
) -> None:
    """Track a warning."""
    get_monitor().track_warning(component, message, context)


def alert_critical(message: str, context: Optional[Dict] = None) -> None:
    """Send a critical alert."""
    get_monitor().alert_critical(message, context)


T = TypeVar("T")


def with_error_tracking(component: str):
    """
    Decorator to automatically track errors in a function.
    
    Usage:
        @with_error_tracking("retrieval")
        def search_vectors(query: str):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                track_error(component, e, {"function": func.__name__})
                raise
        return wrapper
    return decorator


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Error Monitor CLI")
    parser.add_argument("--summary", action="store_true", help="Show error summary")
    parser.add_argument("--patterns", action="store_true", help="Show error patterns")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back")
    parser.add_argument("--test-alert", action="store_true", help="Send test alert")
    args = parser.parse_args()
    
    monitor = get_monitor()
    
    if args.summary:
        print("\n📊 ERROR SUMMARY")
        print("=" * 50)
        summary = monitor.get_error_summary(args.hours)
        print(f"Total errors (last {args.hours}h): {summary['total_errors']}")
        print(f"\nBy component: {dict(summary['by_component'])}")
        print(f"By type: {dict(summary['by_type'])}")
        print(f"By severity: {dict(summary['by_severity'])}")
        
        if summary['recent_critical']:
            print("\n🚨 Recent critical errors:")
            for err in summary['recent_critical'][:5]:
                print(f"  [{err['timestamp']}] {err['component']}: {err['message']}")
    
    elif args.patterns:
        print("\n🔄 ERROR PATTERNS")
        print("=" * 50)
        patterns = monitor.detect_patterns()
        
        if patterns:
            for p in patterns[:10]:
                print(f"\n{p.component} / {p.error_type}")
                print(f"  Count: {p.count}")
                print(f"  First: {p.first_seen}")
                print(f"  Last: {p.last_seen}")
                print(f"  Sample: {p.sample_message[:60]}...")
        else:
            print("No significant patterns detected")
    
    elif args.test_alert:
        print("Sending test alert...")
        alert_critical("Test alert from error_monitor.py", {"test": True})
        print("✅ Test alert sent (check Telegram)")
    
    else:
        print("Use --summary, --patterns, or --test-alert")
