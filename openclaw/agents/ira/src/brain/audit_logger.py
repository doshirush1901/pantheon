#!/usr/bin/env python3
"""
AUDIT LOGGER FOR IRA
====================

Comprehensive logging system for debugging Ira's responses.
Tracks every email processed, sources used, validation results,
and final replies sent.

Usage:
    from audit_logger import AuditLogger
    
    audit = AuditLogger()
    audit.start_request(thread_id, query)
    audit.log_source("qdrant", chunks)
    audit.log_validation("model_check", passed=True)
    audit.log_reply(reply_text)
    audit.end_request()
    
    # View logs
    audit.get_recent_logs(10)
    audit.search_logs("PF1-X-1520")
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import threading

# Audit log directory - use project root data folder
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
AUDIT_DIR = PROJECT_ROOT / "data" / "audit_logs"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class AuditEntry:
    """Single audit log entry."""
    timestamp: str
    event_type: str
    data: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RequestAudit:
    """Complete audit for a single request."""
    request_id: str
    thread_id: str
    started_at: str
    ended_at: Optional[str] = None
    
    # Input
    query: str = ""
    parsed_intent: str = ""
    parsed_series: str = ""
    parsed_model: str = ""
    parsed_size: str = ""
    
    # Sources used
    machines_found: List[str] = None
    qdrant_chunks: List[Dict] = None
    context_filtered: int = 0
    
    # Validation
    validations: List[Dict] = None
    regeneration_attempts: int = 0
    
    # Output
    reply_word_count: int = 0
    reply_preview: str = ""
    fallback_used: bool = False
    
    # Status
    status: str = "in_progress"
    error: Optional[str] = None
    duration_ms: Optional[int] = None
    
    def __post_init__(self):
        if self.machines_found is None:
            self.machines_found = []
        if self.qdrant_chunks is None:
            self.qdrant_chunks = []
        if self.validations is None:
            self.validations = []


class AuditLogger:
    """
    Comprehensive audit logger for Ira.
    Thread-safe with file-based persistence.
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._lock = threading.Lock()
        self._current_request: Optional[RequestAudit] = None
        self._start_time: Optional[datetime] = None
        
        # Daily log file
        self._log_file = AUDIT_DIR / f"audit_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    
    def _generate_request_id(self, thread_id: str) -> str:
        """Generate unique request ID."""
        timestamp = datetime.now().isoformat()
        unique = f"{thread_id}_{timestamp}"
        return hashlib.md5(unique.encode()).hexdigest()[:12]
    
    def start_request(self, thread_id: str, query: str) -> str:
        """Start auditing a new request."""
        if not self.enabled:
            return ""
        
        with self._lock:
            request_id = self._generate_request_id(thread_id)
            self._start_time = datetime.now()
            
            self._current_request = RequestAudit(
                request_id=request_id,
                thread_id=thread_id,
                started_at=self._start_time.isoformat(),
                query=query[:500]  # Truncate for storage
            )
            
            self._write_event("request_started", {
                "request_id": request_id,
                "thread_id": thread_id,
                "query_preview": query[:200]
            })
            
            return request_id
    
    def log_parsed(self, intent: str, series: str = "", model: str = "", size: str = ""):
        """Log parsed query information."""
        if not self.enabled or not self._current_request:
            return
        
        with self._lock:
            self._current_request.parsed_intent = intent
            self._current_request.parsed_series = series or ""
            self._current_request.parsed_model = model or ""
            self._current_request.parsed_size = str(size) if size else ""
    
    def log_machines(self, machines: List[Any]):
        """Log machines found from database."""
        if not self.enabled or not self._current_request:
            return
        
        with self._lock:
            machine_list = []
            for m in machines:
                if hasattr(m, 'model'):
                    machine_list.append({
                        "model": m.model,
                        "series": getattr(m, 'series', ''),
                        "forming_area": getattr(m, 'forming_area_mm', ''),
                        "price_usd": getattr(m, 'price_usd', None)
                    })
            
            self._current_request.machines_found = [m.get('model', str(m)) for m in machine_list]
            
            self._write_event("machines_found", {
                "count": len(machines),
                "machines": machine_list
            })
    
    def log_qdrant_search(self, query: str, results: List[Dict], filtered_count: int = 0):
        """Log Qdrant search results."""
        if not self.enabled or not self._current_request:
            return
        
        with self._lock:
            chunks = []
            for r in results[:10]:  # Max 10 for storage
                chunks.append({
                    "source": r.get("source", "unknown")[:100],
                    "score": round(r.get("score", 0), 3),
                    "preview": r.get("text", "")[:150]
                })
            
            self._current_request.qdrant_chunks = chunks
            self._current_request.context_filtered = filtered_count
            
            self._write_event("qdrant_search", {
                "query_preview": query[:100],
                "results_count": len(results),
                "filtered_count": filtered_count,
                "top_sources": [c["source"] for c in chunks[:5]]
            })
    
    def log_validation(self, check_name: str, passed: bool, details: str = ""):
        """Log a validation check result."""
        if not self.enabled or not self._current_request:
            return
        
        with self._lock:
            validation = {
                "check": check_name,
                "passed": passed,
                "details": details[:200],
                "timestamp": datetime.now().isoformat()
            }
            self._current_request.validations.append(validation)
            
            if not passed:
                self._write_event("validation_failed", validation)
    
    def log_regeneration(self, attempt: int, reason: str):
        """Log a reply regeneration attempt."""
        if not self.enabled or not self._current_request:
            return
        
        with self._lock:
            self._current_request.regeneration_attempts = attempt
            
            self._write_event("regeneration", {
                "attempt": attempt,
                "reason": reason[:200]
            })
    
    def log_reply(self, reply: str, fallback: bool = False):
        """Log the final reply generated."""
        if not self.enabled or not self._current_request:
            return
        
        with self._lock:
            self._current_request.reply_word_count = len(reply.split())
            self._current_request.reply_preview = reply[:500]
            self._current_request.fallback_used = fallback
    
    def log_error(self, error: str):
        """Log an error."""
        if not self.enabled or not self._current_request:
            return
        
        with self._lock:
            self._current_request.error = error[:500]
            self._current_request.status = "error"
            
            self._write_event("error", {"error": error[:500]})
    
    def end_request(self, success: bool = True):
        """End the current request audit."""
        if not self.enabled or not self._current_request:
            return
        
        with self._lock:
            end_time = datetime.now()
            self._current_request.ended_at = end_time.isoformat()
            self._current_request.status = "success" if success else "failed"
            
            if self._start_time:
                self._current_request.duration_ms = int(
                    (end_time - self._start_time).total_seconds() * 1000
                )
            
            # Write full request summary
            self._write_event("request_completed", {
                "request_id": self._current_request.request_id,
                "status": self._current_request.status,
                "duration_ms": self._current_request.duration_ms,
                "machines_used": self._current_request.machines_found,
                "qdrant_chunks_count": len(self._current_request.qdrant_chunks),
                "validations_passed": sum(1 for v in self._current_request.validations if v.get("passed")),
                "validations_failed": sum(1 for v in self._current_request.validations if not v.get("passed")),
                "regeneration_attempts": self._current_request.regeneration_attempts,
                "reply_word_count": self._current_request.reply_word_count,
                "fallback_used": self._current_request.fallback_used
            })
            
            # Write full audit record to daily file
            self._write_full_audit()
            
            # Reset
            self._current_request = None
            self._start_time = None
    
    def _write_event(self, event_type: str, data: Dict):
        """Write a single event to the log."""
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            data=data
        )
        
        try:
            with open(self._log_file, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as e:
            print(f"[AUDIT] Failed to write event: {e}")
    
    def _write_full_audit(self):
        """Write full audit record."""
        if not self._current_request:
            return
        
        # Write to separate full audit file
        full_audit_file = AUDIT_DIR / f"full_audit_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        
        try:
            audit_data = {
                "request_id": self._current_request.request_id,
                "thread_id": self._current_request.thread_id,
                "started_at": self._current_request.started_at,
                "ended_at": self._current_request.ended_at,
                "duration_ms": self._current_request.duration_ms,
                "status": self._current_request.status,
                "query": self._current_request.query,
                "parsed": {
                    "intent": self._current_request.parsed_intent,
                    "series": self._current_request.parsed_series,
                    "model": self._current_request.parsed_model,
                    "size": self._current_request.parsed_size
                },
                "machines_found": self._current_request.machines_found,
                "qdrant_chunks": self._current_request.qdrant_chunks,
                "context_filtered": self._current_request.context_filtered,
                "validations": self._current_request.validations,
                "regeneration_attempts": self._current_request.regeneration_attempts,
                "reply_word_count": self._current_request.reply_word_count,
                "reply_preview": self._current_request.reply_preview,
                "fallback_used": self._current_request.fallback_used,
                "error": self._current_request.error
            }
            
            with open(full_audit_file, "a") as f:
                f.write(json.dumps(audit_data) + "\n")
        except Exception as e:
            print(f"[AUDIT] Failed to write full audit: {e}")
    
    # =========================================================================
    # Query methods for debugging
    # =========================================================================
    
    def get_recent_logs(self, count: int = 10) -> List[Dict]:
        """Get recent audit logs."""
        logs = []
        
        # Read from today's full audit file
        full_audit_file = AUDIT_DIR / f"full_audit_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        
        if full_audit_file.exists():
            try:
                with open(full_audit_file, "r") as f:
                    lines = f.readlines()
                    for line in lines[-count:]:
                        logs.append(json.loads(line.strip()))
            except Exception as e:
                print(f"[AUDIT] Failed to read logs: {e}")
        
        return logs
    
    def get_request(self, request_id: str) -> Optional[Dict]:
        """Get a specific request by ID."""
        # Search today's logs first
        full_audit_file = AUDIT_DIR / f"full_audit_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        
        if full_audit_file.exists():
            try:
                with open(full_audit_file, "r") as f:
                    for line in f:
                        data = json.loads(line.strip())
                        if data.get("request_id") == request_id:
                            return data
            except Exception:
                pass
        
        return None
    
    def search_logs(self, term: str, days: int = 7) -> List[Dict]:
        """Search logs for a term."""
        results = []
        term_lower = term.lower()
        
        # Search recent days
        from datetime import timedelta
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            full_audit_file = AUDIT_DIR / f"full_audit_{date}.jsonl"
            
            if full_audit_file.exists():
                try:
                    with open(full_audit_file, "r") as f:
                        for line in f:
                            if term_lower in line.lower():
                                results.append(json.loads(line.strip()))
                except Exception:
                    pass
        
        return results
    
    def get_stats(self, days: int = 1) -> Dict:
        """Get aggregate statistics."""
        from datetime import timedelta
        
        stats = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "avg_duration_ms": 0,
            "fallback_used": 0,
            "regenerations": 0,
            "validation_failures": 0,
            "machines_mentioned": {},
            "intents": {}
        }
        
        durations = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            full_audit_file = AUDIT_DIR / f"full_audit_{date}.jsonl"
            
            if full_audit_file.exists():
                try:
                    with open(full_audit_file, "r") as f:
                        for line in f:
                            data = json.loads(line.strip())
                            stats["total_requests"] += 1
                            
                            if data.get("status") == "success":
                                stats["successful"] += 1
                            else:
                                stats["failed"] += 1
                            
                            if data.get("duration_ms"):
                                durations.append(data["duration_ms"])
                            
                            if data.get("fallback_used"):
                                stats["fallback_used"] += 1
                            
                            stats["regenerations"] += data.get("regeneration_attempts", 0)
                            
                            for v in data.get("validations", []):
                                if not v.get("passed"):
                                    stats["validation_failures"] += 1
                            
                            for m in data.get("machines_found", []):
                                stats["machines_mentioned"][m] = stats["machines_mentioned"].get(m, 0) + 1
                            
                            intent = data.get("parsed", {}).get("intent", "unknown")
                            stats["intents"][intent] = stats["intents"].get(intent, 0) + 1
                            
                except Exception:
                    pass
        
        if durations:
            stats["avg_duration_ms"] = int(sum(durations) / len(durations))
        
        return stats


# Global audit logger instance
audit_logger = AuditLogger()


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger."""
    return audit_logger


# CLI for viewing logs
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="View Ira audit logs")
    parser.add_argument("--recent", type=int, default=5, help="Show N recent requests")
    parser.add_argument("--search", type=str, help="Search for term in logs")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--request", type=str, help="Get specific request by ID")
    args = parser.parse_args()
    
    logger = AuditLogger()
    
    if args.stats:
        print("\n📊 AUDIT STATISTICS (Last 24 hours)")
        print("=" * 50)
        stats = logger.get_stats(1)
        print(f"Total requests: {stats['total_requests']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Avg duration: {stats['avg_duration_ms']}ms")
        print(f"Fallbacks used: {stats['fallback_used']}")
        print(f"Regenerations: {stats['regenerations']}")
        print(f"Validation failures: {stats['validation_failures']}")
        print(f"\nIntents: {stats['intents']}")
        print(f"\nTop machines: {dict(sorted(stats['machines_mentioned'].items(), key=lambda x: -x[1])[:5])}")
    
    elif args.search:
        print(f"\n🔍 Searching for: {args.search}")
        print("=" * 50)
        results = logger.search_logs(args.search)
        for r in results[:10]:
            print(f"\n[{r.get('started_at', 'unknown')}] {r.get('request_id', 'unknown')}")
            print(f"  Query: {r.get('query', '')[:80]}...")
            print(f"  Status: {r.get('status', 'unknown')}, Duration: {r.get('duration_ms', 0)}ms")
            print(f"  Machines: {r.get('machines_found', [])}")
    
    elif args.request:
        print(f"\n📋 Request: {args.request}")
        print("=" * 50)
        req = logger.get_request(args.request)
        if req:
            print(json.dumps(req, indent=2))
        else:
            print("Request not found")
    
    else:
        print(f"\n📜 RECENT REQUESTS (Last {args.recent})")
        print("=" * 50)
        logs = logger.get_recent_logs(args.recent)
        for log in logs:
            print(f"\n[{log.get('started_at', 'unknown')}]")
            print(f"  ID: {log.get('request_id', 'unknown')}")
            print(f"  Query: {log.get('query', '')[:60]}...")
            print(f"  Intent: {log.get('parsed', {}).get('intent', 'unknown')}")
            print(f"  Machines: {log.get('machines_found', [])}")
            print(f"  Status: {log.get('status', 'unknown')}, Duration: {log.get('duration_ms', 0)}ms")
            if log.get('fallback_used'):
                print(f"  ⚠️  FALLBACK USED")
            if log.get('regeneration_attempts', 0) > 0:
                print(f"  🔄 Regenerations: {log.get('regeneration_attempts')}")
