#!/usr/bin/env python3
"""
MEMORY CONSOLIDATION SCHEDULER
==============================

Schedules and runs memory consolidation jobs:
1. As a daemon with APScheduler
2. As a cron-compatible one-shot
3. As a background thread in the main application

Consolidation Phases (from consolidation_job.py):
- DECAY: Reduce confidence of unused memories
- MERGE: Combine semantically similar memories
- PRUNE: Remove very low confidence memories
- PROMOTE: Elevate frequently-used facts
- STATS: Generate statistics report

Usage:
    # Run as daemon
    python consolidation_scheduler.py --daemon
    
    # Run once (for cron)
    python consolidation_scheduler.py --once
    
    # Run specific phase
    python consolidation_scheduler.py --once --phase decay
    
    # Dry run
    python consolidation_scheduler.py --once --dry-run

Cron Example (daily at 3 AM):
    0 3 * * * cd /path/to/Ira && python -m openclaw.agents.ira.src.memory.consolidation_scheduler --once

Environment Variables:
    CONSOLIDATION_ENABLED: Set to "true" to enable (default: true)
    CONSOLIDATION_HOUR: Hour to run daily (default: 3)
    CONSOLIDATION_MINUTE: Minute to run (default: 0)
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from threading import Thread, Event

# Setup paths
MEMORY_DIR = Path(__file__).parent
SKILLS_DIR = MEMORY_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(MEMORY_DIR))

# Import from centralized config
try:
    from config import get_logger, FEATURES
    logger = get_logger("consolidation_scheduler")
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("consolidation_scheduler")
    FEATURES = {}
    # Load .env fallback
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))

# Scheduler state file
SCHEDULER_STATE_FILE = PROJECT_ROOT / "data" / "consolidation_state.json"


class ConsolidationScheduler:
    """
    Schedules and manages memory consolidation jobs.
    
    Can run as:
    - Daemon with APScheduler
    - One-shot for cron
    - Background thread
    """
    
    def __init__(self):
        self.enabled = os.environ.get("CONSOLIDATION_ENABLED", "true").lower() == "true"
        self.hour = int(os.environ.get("CONSOLIDATION_HOUR", "3"))
        self.minute = int(os.environ.get("CONSOLIDATION_MINUTE", "0"))
        
        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._last_run: Optional[datetime] = None
        self._load_state()
    
    def _load_state(self):
        """Load scheduler state from file."""
        if SCHEDULER_STATE_FILE.exists():
            try:
                state = json.loads(SCHEDULER_STATE_FILE.read_text())
                if state.get("last_run"):
                    self._last_run = datetime.fromisoformat(state["last_run"])
            except (json.JSONDecodeError, IOError):
                pass
    
    def _save_state(self):
        """Save scheduler state to file."""
        SCHEDULER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "enabled": self.enabled,
            "schedule": f"{self.hour:02d}:{self.minute:02d}",
            "updated_at": datetime.now().isoformat(),
        }
        SCHEDULER_STATE_FILE.write_text(json.dumps(state, indent=2))
    
    def run_consolidation(self, 
                          phase: Optional[str] = None, 
                          dry_run: bool = False) -> Dict[str, Any]:
        """
        Run memory consolidation.
        
        Args:
            phase: Specific phase to run (decay, merge, prune, promote, stats)
                   or None for full consolidation
            dry_run: If True, don't make changes
            
        Returns:
            Consolidation result dict
        """
        logger.info(f"Starting consolidation (phase={phase or 'all'}, dry_run={dry_run})")
        
        start_time = datetime.now()
        result = {
            "success": False,
            "phase": phase or "all",
            "dry_run": dry_run,
            "started_at": start_time.isoformat(),
            "completed_at": None,
            "stats": {},
            "errors": [],
        }
        
        try:
            # Import consolidation job
            from consolidation_job import MemoryConsolidator
            
            consolidator = MemoryConsolidator(dry_run=dry_run)
            
            if phase:
                # Run specific phase
                phase_result = self._run_phase(consolidator, phase)
                result["stats"][phase] = phase_result.to_dict() if hasattr(phase_result, 'to_dict') else str(phase_result)
            else:
                # Run all phases
                for p in ["decay", "merge", "prune", "promote", "stats"]:
                    try:
                        phase_result = self._run_phase(consolidator, p)
                        result["stats"][p] = phase_result.to_dict() if hasattr(phase_result, 'to_dict') else str(phase_result)
                    except Exception as e:
                        logger.error(f"Phase {p} failed: {e}")
                        result["errors"].append(f"{p}: {str(e)}")
            
            result["success"] = len(result["errors"]) == 0
            
        except ImportError as e:
            logger.error(f"Failed to import consolidation_job: {e}")
            result["errors"].append(str(e))
        except Exception as e:
            logger.error(f"Consolidation failed: {e}")
            result["errors"].append(str(e))
        
        result["completed_at"] = datetime.now().isoformat()
        result["duration_seconds"] = (datetime.now() - start_time).total_seconds()
        
        # Update state
        if not dry_run:
            self._last_run = datetime.now()
            self._save_state()
        
        # Log result
        self._log_result(result)
        
        return result
    
    def _run_phase(self, consolidator, phase: str):
        """Run a specific consolidation phase."""
        phase_methods = {
            "decay": lambda: consolidator.run_decay(),
            "merge": lambda: consolidator.run_merge(),
            "prune": lambda: consolidator.run_prune(),
            "promote": lambda: consolidator.run_promote(),
            "stats": lambda: consolidator.run_stats(),
        }
        
        method = phase_methods.get(phase)
        if method:
            return method()
        else:
            raise ValueError(f"Unknown phase: {phase}")
    
    def _log_result(self, result: Dict[str, Any]):
        """Log consolidation result to file."""
        log_file = PROJECT_ROOT / "logs" / "consolidation.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_file, "a") as f:
            f.write(json.dumps(result) + "\n")
    
    def should_run_today(self) -> bool:
        """Check if consolidation should run today."""
        if not self._last_run:
            return True
        
        # Run if last run was not today
        today = datetime.now().date()
        return self._last_run.date() < today
    
    def start_daemon(self):
        """Start the scheduler as a daemon process."""
        logger.info(f"Starting consolidation daemon (schedule: {self.hour:02d}:{self.minute:02d})")
        
        # Try to use APScheduler if available
        try:
            from apscheduler.schedulers.blocking import BlockingScheduler
            from apscheduler.triggers.cron import CronTrigger
            
            scheduler = BlockingScheduler()
            scheduler.add_job(
                lambda: self.run_consolidation(),
                CronTrigger(hour=self.hour, minute=self.minute),
                id="memory_consolidation",
                name="Memory Consolidation Job",
                replace_existing=True,
            )
            
            logger.info("Using APScheduler for cron-like scheduling")
            
            # Handle signals
            def shutdown(signum, frame):
                logger.info("Shutting down scheduler...")
                scheduler.shutdown(wait=False)
            
            signal.signal(signal.SIGTERM, shutdown)
            signal.signal(signal.SIGINT, shutdown)
            
            scheduler.start()
            
        except ImportError:
            logger.warning("APScheduler not available, using simple loop")
            self._run_simple_daemon()
    
    def _run_simple_daemon(self):
        """Run daemon with simple sleep loop (fallback)."""
        while not self._stop_event.is_set():
            now = datetime.now()
            
            # Check if it's time to run
            if now.hour == self.hour and now.minute == self.minute:
                if self.should_run_today():
                    self.run_consolidation()
            
            # Sleep for 60 seconds
            self._stop_event.wait(60)
    
    def start_background(self, callback: Optional[Callable] = None):
        """Start consolidation in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Background thread already running")
            return
        
        def _run():
            result = self.run_consolidation()
            if callback:
                callback(result)
        
        self._thread = Thread(target=_run, name="consolidation_worker", daemon=True)
        self._thread.start()
        logger.info("Started background consolidation thread")
    
    def stop(self):
        """Stop the scheduler."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "enabled": self.enabled,
            "schedule": f"{self.hour:02d}:{self.minute:02d}",
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "should_run_today": self.should_run_today(),
            "running": self._thread.is_alive() if self._thread else False,
        }


# Global scheduler instance
_scheduler: Optional[ConsolidationScheduler] = None


def get_scheduler() -> ConsolidationScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = ConsolidationScheduler()
    return _scheduler


def run_consolidation(phase: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Convenience function to run consolidation."""
    return get_scheduler().run_consolidation(phase=phase, dry_run=dry_run)


def start_background_consolidation(callback: Optional[Callable] = None):
    """Start consolidation in background."""
    return get_scheduler().start_background(callback=callback)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Memory Consolidation Scheduler")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--phase", choices=["decay", "merge", "prune", "promote", "stats"],
                        help="Run specific phase only")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes")
    parser.add_argument("--status", action="store_true", help="Show scheduler status")
    args = parser.parse_args()
    
    scheduler = get_scheduler()
    
    if args.status:
        status = scheduler.get_status()
        print(json.dumps(status, indent=2))
        return
    
    if args.daemon:
        if not scheduler.enabled:
            print("Consolidation is disabled. Set CONSOLIDATION_ENABLED=true to enable.")
            sys.exit(1)
        scheduler.start_daemon()
    
    elif args.once:
        result = scheduler.run_consolidation(phase=args.phase, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["success"] else 1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
