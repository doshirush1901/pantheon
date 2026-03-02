#!/usr/bin/env python3
"""
IRA ORCHESTRATOR - Unified Service Manager

╔════════════════════════════════════════════════════════════════════════════╗
║                         IRA SERVICE ORCHESTRATOR                            ║
║                                                                            ║
║  Starts and manages all Ira services:                                      ║
║                                                                            ║
║  CORE SERVICES:                                                            ║
║    - IraAgent (unified cognitive processing)                               ║
║    - Telegram Gateway (interactive channel)                                ║
║    - Email Watcher (async channel)                                         ║
║                                                                            ║
║  BACKGROUND JOBS:                                                          ║
║    - Memory consolidation (episodic → semantic)                            ║
║    - Memory decay (importance fading)                                      ║
║    - Proactive outreach scheduler                                          ║
║                                                                            ║
║  Usage:                                                                    ║
║    python orchestrator.py              # Start all services                ║
║    python orchestrator.py --telegram   # Telegram only                     ║
║    python orchestrator.py --email      # Email only                        ║
║    python orchestrator.py --status     # Check status                      ║
║    python orchestrator.py --cli        # Interactive CLI                   ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import os
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Setup paths
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/skills/telegram_channel"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/skills/email_channel"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/skills/memory"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/skills/brain"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw/agents/ira/skills/conversation"))

# Load environment (override existing values to ensure .env takes precedence)
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip().strip('"')
            os.environ[key] = value  # Override to ensure fresh .env values are used


# =============================================================================
# SERVICE DEFINITIONS
# =============================================================================

class ServiceStatus:
    """Track service status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    STOPPING = "stopping"


class Service:
    """Base service class."""
    
    def __init__(self, name: str):
        self.name = name
        self.status = ServiceStatus.STOPPED
        self.thread: Optional[threading.Thread] = None
        self.error: Optional[str] = None
        self._stop_event = threading.Event()
    
    def start(self):
        """Start the service."""
        if self.status == ServiceStatus.RUNNING:
            return
        
        self.status = ServiceStatus.STARTING
        self._stop_event.clear()
        
        self.thread = threading.Thread(target=self._run_wrapper, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the service."""
        self.status = ServiceStatus.STOPPING
        self._stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        self.status = ServiceStatus.STOPPED
    
    def _run_wrapper(self):
        """Wrapper for run method with error handling."""
        try:
            self.status = ServiceStatus.RUNNING
            self.run()
        except Exception as e:
            self.status = ServiceStatus.ERROR
            self.error = str(e)
            print(f"[{self.name}] Error: {e}")
    
    def run(self):
        """Override this method in subclasses."""
        raise NotImplementedError


class TelegramService(Service):
    """Telegram gateway service."""
    
    def __init__(self, poll_interval: int = 2):
        super().__init__("telegram")
        self.poll_interval = poll_interval
        self._gateway = None
    
    def run(self):
        """Run telegram polling loop."""
        try:
            from src.telegram_channel.telegram_gateway import TelegramGateway
            self._gateway = TelegramGateway()
            
            print(f"[telegram] Starting polling (interval={self.poll_interval}s)", flush=True)
            
            while not self._stop_event.is_set():
                try:
                    self._gateway.poll_once()
                except Exception as e:
                    print(f"[telegram] Poll error: {e}", flush=True)
                
                self._stop_event.wait(self.poll_interval)
                
        except Exception as e:
            print(f"[telegram] Fatal error: {e}", flush=True)
            raise e


class EmailService(Service):
    """Email watcher service."""
    
    def __init__(self, poll_interval: int = 60):
        super().__init__("email")
        self.poll_interval = poll_interval
    
    def run(self):
        """Run email watching loop."""
        try:
            from email_handler import EmailHandler
            handler = EmailHandler()
            
            print(f"[email] Starting watcher (interval={self.poll_interval}s)")
            
            while not self._stop_event.is_set():
                try:
                    # Email watching logic would go here
                    # For now, just wait - actual implementation
                    # uses Gmail push notifications
                    pass
                except Exception as e:
                    print(f"[email] Watch error: {e}")
                
                self._stop_event.wait(self.poll_interval)
                
        except Exception as e:
            raise e


class ConsolidationService(Service):
    """Memory consolidation background job."""
    
    def __init__(self, interval_hours: int = 6):
        super().__init__("consolidation")
        self.interval_seconds = interval_hours * 3600
    
    def run(self):
        """Run periodic consolidation."""
        try:
            from episodic_consolidator import run_consolidation
            from unified_decay import decay_memories
            
            print(f"[consolidation] Starting (interval={self.interval_seconds/3600}h)")
            
            while not self._stop_event.is_set():
                try:
                    # Run episodic → semantic consolidation
                    result = run_consolidation()
                    if result.memories_created > 0:
                        print(f"[consolidation] Created {result.memories_created} semantic memories from episodes")
                    
                    # Run memory decay
                    decay_result = decay_memories()
                    if decay_result.memories_decayed > 0:
                        print(f"[consolidation] Decayed {decay_result.memories_decayed} memories")
                        
                except Exception as e:
                    print(f"[consolidation] Error: {e}")
                
                self._stop_event.wait(self.interval_seconds)
                
        except ImportError as e:
            print(f"[consolidation] Module not available: {e}")
        except Exception as e:
            raise e


class ProactiveService(Service):
    """Proactive outreach scheduler."""
    
    def __init__(self, interval_minutes: int = 30):
        super().__init__("proactive")
        self.interval_seconds = interval_minutes * 60
    
    def run(self):
        """Run proactive outreach scheduling."""
        try:
            from proactive_outreach import get_outreach_scheduler
            
            scheduler = get_outreach_scheduler()
            print(f"[proactive] Starting (interval={self.interval_seconds/60}m)")
            
            while not self._stop_event.is_set():
                try:
                    # Check for outreach candidates
                    candidates = scheduler.get_candidates()
                    if candidates:
                        print(f"[proactive] {len(candidates)} outreach candidates")
                        
                except Exception as e:
                    print(f"[proactive] Error: {e}")
                
                self._stop_event.wait(self.interval_seconds)
                
        except ImportError as e:
            print(f"[proactive] Module not available: {e}")
        except Exception as e:
            raise e


# =============================================================================
# ORCHESTRATOR
# =============================================================================

class IraOrchestrator:
    """
    Main orchestrator that manages all Ira services.
    """
    
    def __init__(self):
        self.services: Dict[str, Service] = {}
        self._running = False
        self._start_time: Optional[datetime] = None
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n[orchestrator] Shutdown signal received")
        self.stop()
    
    def add_service(self, service: Service):
        """Add a service to manage."""
        self.services[service.name] = service
    
    def start(self, services: List[str] = None):
        """Start specified services (or all if none specified)."""
        self._running = True
        self._start_time = datetime.now()
        
        # Initialize agent first
        try:
            from agent import get_agent
            agent = get_agent()
            print(f"[orchestrator] Agent initialized: {agent.config.name} v{agent.config.version}")
        except Exception as e:
            print(f"[orchestrator] Agent init error: {e}")
        
        # Start services
        service_names = services or list(self.services.keys())
        
        for name in service_names:
            if name in self.services:
                print(f"[orchestrator] Starting {name}...")
                self.services[name].start()
                time.sleep(0.5)  # Stagger startup
    
    def stop(self):
        """Stop all services."""
        self._running = False
        
        for name, service in self.services.items():
            if service.status == ServiceStatus.RUNNING:
                print(f"[orchestrator] Stopping {name}...")
                service.stop()
        
        print("[orchestrator] All services stopped")
    
    def get_status(self) -> Dict:
        """Get orchestrator status."""
        uptime = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
        
        return {
            "running": self._running,
            "uptime_seconds": uptime,
            "services": {
                name: {
                    "status": service.status,
                    "error": service.error
                }
                for name, service in self.services.items()
            }
        }
    
    def wait(self):
        """Wait for shutdown."""
        try:
            while self._running:
                time.sleep(1)
                
                # Check service health
                for name, service in self.services.items():
                    if service.status == ServiceStatus.ERROR:
                        print(f"[orchestrator] Service {name} in error state")
                        
        except KeyboardInterrupt:
            self.stop()


# =============================================================================
# CLI
# =============================================================================

def run_cli():
    """Run interactive CLI mode."""
    try:
        from agent import get_agent
        
        agent = get_agent()
        
        print(f"\n{'='*60}")
        print(f"  {agent.config.name} v{agent.config.version} - Interactive CLI")
        print(f"{'='*60}")
        print("Commands: /status, /health, /quit")
        print()
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ["/quit", "/exit", "quit", "exit"]:
                    print("Goodbye!")
                    break
                
                if user_input.lower() in ["/status", "status"]:
                    status = agent.get_status()
                    print(json.dumps(status, indent=2))
                    continue
                
                if user_input.lower() in ["/health", "health"]:
                    health = agent.get_health()
                    print(json.dumps(health.to_dict(), indent=2))
                    continue
                
                # Process message
                response = agent.process(
                    message=user_input,
                    channel="cli",
                    user_id="cli_user"
                )
                
                print(f"\nIra: {response.message}")
                
                if response.procedure_used:
                    print(f"[procedure: {response.procedure_used}]")
                if response.suggestions:
                    print(f"[suggestions: {', '.join(response.suggestions[:2])}]")
                    
                print(f"[{response.processing_time_ms:.0f}ms | {response.memories_used} memories | {response.rag_chunks_used} chunks]")
                print()
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
                
    except Exception as e:
        print(f"Failed to start CLI: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Ira Service Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python orchestrator.py              # Start all services
  python orchestrator.py --telegram   # Telegram only
  python orchestrator.py --cli        # Interactive CLI
  python orchestrator.py --status     # Show status
        """
    )
    
    parser.add_argument("--telegram", action="store_true", help="Run Telegram gateway")
    parser.add_argument("--email", action="store_true", help="Run email watcher")
    parser.add_argument("--consolidation", action="store_true", help="Run consolidation job")
    parser.add_argument("--proactive", action="store_true", help="Run proactive scheduler")
    parser.add_argument("--all", action="store_true", help="Run all services")
    parser.add_argument("--cli", action="store_true", help="Interactive CLI mode")
    parser.add_argument("--status", action="store_true", help="Show agent status")
    parser.add_argument("--interval", type=int, default=2, help="Poll interval (seconds)")
    
    args = parser.parse_args()
    
    # CLI mode
    if args.cli:
        run_cli()
        return
    
    # Status mode
    if args.status:
        try:
            from agent import get_agent
            agent = get_agent()
            status = agent.get_status()
            print(json.dumps(status, indent=2))
        except Exception as e:
            print(f"Error: {e}")
        return
    
    # Create orchestrator
    orchestrator = IraOrchestrator()
    
    # Determine which services to run
    services_to_run = []
    
    if args.all or not any([args.telegram, args.email, args.consolidation, args.proactive]):
        # Default: run telegram + consolidation
        services_to_run = ["telegram", "consolidation"]
    else:
        if args.telegram:
            services_to_run.append("telegram")
        if args.email:
            services_to_run.append("email")
        if args.consolidation:
            services_to_run.append("consolidation")
        if args.proactive:
            services_to_run.append("proactive")
    
    # Add services
    if "telegram" in services_to_run:
        orchestrator.add_service(TelegramService(poll_interval=args.interval))
    if "email" in services_to_run:
        orchestrator.add_service(EmailService())
    if "consolidation" in services_to_run:
        orchestrator.add_service(ConsolidationService())
    if "proactive" in services_to_run:
        orchestrator.add_service(ProactiveService())
    
    # Start
    print(f"\n{'='*60}")
    print(f"  IRA ORCHESTRATOR - Starting {len(services_to_run)} services")
    print(f"  Services: {', '.join(services_to_run)}")
    print(f"{'='*60}\n")
    
    orchestrator.start()
    orchestrator.wait()


if __name__ == "__main__":
    main()
