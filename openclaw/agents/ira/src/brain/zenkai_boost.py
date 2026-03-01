#!/usr/bin/env python3
"""
ZENKAI BOOST - Anti-Fragile Learning System
============================================

In Dragon Ball Z, Saiyans get dramatically stronger after recovering from
near-death experiences. This "Zenkai Boost" makes them anti-fragile - they
become stronger from adversity.

For our agents, we implement the same concept:
- Failures give MORE XP than successes (2-3x multiplier)
- Errors that are analyzed and fixed give massive boosts
- Near-failures (recovered errors) are the best learning opportunities
- Patterns of failures are tracked to prevent repeated mistakes

The philosophy: "What doesn't kill you makes you stronger"

Usage:
    from zenkai_boost import ZenkaiTracker, get_zenkai_tracker
    
    tracker = get_zenkai_tracker()
    
    # Record a failure (triggers Zenkai analysis)
    tracker.record_failure(
        agent_id="researcher",
        error_type="knowledge_gap",
        context="Could not find PF1 pricing data",
        severity="medium"
    )
    
    # Record recovery from failure
    tracker.record_recovery(
        agent_id="researcher", 
        failure_id="...",
        lesson_learned="Need to check pricing database first"
    )
    
    # Check if agent is in Zenkai state (recently recovered)
    if tracker.is_in_zenkai_state("researcher"):
        # Agent has temporary power boost!
        pass
"""

import json
import logging
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger("ira.zenkai")

BRAIN_DIR = Path(__file__).parent
PROJECT_ROOT = BRAIN_DIR.parent.parent.parent.parent.parent
ZENKAI_FILE = PROJECT_ROOT / "data" / "knowledge" / "zenkai_log.json"

# Import power levels for XP boosting
try:
    from .power_levels import get_power_tracker
    POWER_LEVELS_AVAILABLE = True
except ImportError:
    try:
        from power_levels import get_power_tracker
        POWER_LEVELS_AVAILABLE = True
    except ImportError:
        POWER_LEVELS_AVAILABLE = False


class FailureSeverity(Enum):
    """Severity levels for failures - higher severity = bigger Zenkai boost."""
    LOW = "low"           # Minor issue, small boost
    MEDIUM = "medium"     # Moderate issue, good boost  
    HIGH = "high"         # Major issue, big boost
    CRITICAL = "critical" # Near-death, massive boost (OVER 9000 potential!)


class FailureType(Enum):
    """Types of failures agents can experience."""
    KNOWLEDGE_GAP = "knowledge_gap"       # Didn't know something
    REASONING_ERROR = "reasoning_error"   # Logic mistake
    COMMUNICATION = "communication"       # Misunderstood request
    HALLUCINATION = "hallucination"       # Made something up
    TIMEOUT = "timeout"                   # Took too long
    VALIDATION_FAIL = "validation_fail"   # Output didn't pass checks
    COLLABORATION_FAIL = "collaboration_fail"  # Agent teamwork broke down


# XP multipliers for Zenkai boost based on severity
ZENKAI_XP_MULTIPLIERS = {
    FailureSeverity.LOW: 1.5,
    FailureSeverity.MEDIUM: 2.0,
    FailureSeverity.HIGH: 2.5,
    FailureSeverity.CRITICAL: 3.0,  # Near-death = massive boost!
}

# Base XP for different failure types
FAILURE_BASE_XP = {
    FailureType.KNOWLEDGE_GAP: 30,
    FailureType.REASONING_ERROR: 40,
    FailureType.COMMUNICATION: 25,
    FailureType.HALLUCINATION: 50,  # Serious - needs big learning
    FailureType.TIMEOUT: 20,
    FailureType.VALIDATION_FAIL: 35,
    FailureType.COLLABORATION_FAIL: 45,
}

# Recovery bonus (on top of failure XP)
RECOVERY_BONUS_XP = 50

# Zenkai state duration (temporary power boost after recovery)
ZENKAI_STATE_DURATION = timedelta(hours=24)


@dataclass
class FailureRecord:
    """Record of an agent failure."""
    failure_id: str
    agent_id: str
    timestamp: str
    failure_type: str
    severity: str
    context: str
    error_message: str = ""
    recovered: bool = False
    recovery_timestamp: str = ""
    lesson_learned: str = ""
    xp_awarded: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass 
class ZenkaiState:
    """Tracks an agent's current Zenkai state."""
    agent_id: str
    active: bool = False
    boost_multiplier: float = 1.0
    activated_at: str = ""
    expires_at: str = ""
    trigger_failure_id: str = ""
    consecutive_recoveries: int = 0


class ZenkaiTracker:
    """
    Tracks failures and applies Zenkai boosts to agents.
    
    Like Vegeta after his fight with Goku, agents emerge from failures
    stronger than before - IF they learn from them.
    """
    
    def __init__(self):
        self._failures: Dict[str, FailureRecord] = {}
        self._agent_states: Dict[str, ZenkaiState] = {}
        self._failure_patterns: Dict[str, List[str]] = {}  # agent -> failure types
        self._load()
    
    def _load(self):
        """Load Zenkai data from file."""
        ZENKAI_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        if ZENKAI_FILE.exists():
            try:
                data = json.loads(ZENKAI_FILE.read_text())
                
                for fid, fdata in data.get("failures", {}).items():
                    self._failures[fid] = FailureRecord(**fdata)
                
                for aid, sdata in data.get("states", {}).items():
                    self._agent_states[aid] = ZenkaiState(**sdata)
                
                self._failure_patterns = data.get("patterns", {})
                
            except Exception as e:
                logger.warning(f"Failed to load Zenkai data: {e}")
    
    def _save(self):
        """Save Zenkai data to file."""
        try:
            # Keep only recent failures (last 500)
            recent_failures = dict(
                sorted(self._failures.items(), 
                       key=lambda x: x[1].timestamp, 
                       reverse=True)[:500]
            )
            
            data = {
                "failures": {fid: f.to_dict() for fid, f in recent_failures.items()},
                "states": {aid: asdict(s) for aid, s in self._agent_states.items()},
                "patterns": self._failure_patterns,
                "last_updated": datetime.now().isoformat(),
            }
            ZENKAI_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save Zenkai data: {e}")
    
    def _generate_failure_id(self, agent_id: str, context: str) -> str:
        """Generate unique failure ID."""
        data = f"{agent_id}:{context}:{datetime.now().isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()[:12]
    
    def _get_power_tracker(self):
        """Get power tracker if available."""
        if POWER_LEVELS_AVAILABLE:
            return get_power_tracker()
        return None
    
    # =========================================================================
    # RECORD FAILURES
    # =========================================================================
    
    def record_failure(
        self,
        agent_id: str,
        failure_type: str,
        context: str,
        severity: str = "medium",
        error_message: str = ""
    ) -> str:
        """
        Record an agent failure - the first step to a Zenkai boost!
        
        Returns:
            failure_id: Use this to record recovery later
        """
        failure_id = self._generate_failure_id(agent_id, context)
        
        # Convert string to enum if needed
        try:
            f_type = FailureType(failure_type)
        except ValueError:
            f_type = FailureType.REASONING_ERROR
        
        try:
            f_severity = FailureSeverity(severity)
        except ValueError:
            f_severity = FailureSeverity.MEDIUM
        
        # Create failure record
        failure = FailureRecord(
            failure_id=failure_id,
            agent_id=agent_id,
            timestamp=datetime.now().isoformat(),
            failure_type=f_type.value,
            severity=f_severity.value,
            context=context,
            error_message=error_message,
        )
        
        self._failures[failure_id] = failure
        
        # Track failure patterns
        if agent_id not in self._failure_patterns:
            self._failure_patterns[agent_id] = []
        self._failure_patterns[agent_id].append(f_type.value)
        self._failure_patterns[agent_id] = self._failure_patterns[agent_id][-50:]
        
        logger.info(f"⚠️ Failure recorded for {agent_id}: {f_type.value} ({f_severity.value})")
        
        self._save()
        return failure_id
    
    def record_recovery(
        self,
        agent_id: str,
        failure_id: str,
        lesson_learned: str
    ) -> int:
        """
        Record recovery from a failure - THIS triggers the Zenkai boost!
        
        Args:
            agent_id: The agent that recovered
            failure_id: The failure being recovered from
            lesson_learned: What the agent learned (important for growth!)
            
        Returns:
            xp_awarded: The XP boost from Zenkai
        """
        if failure_id not in self._failures:
            logger.warning(f"Unknown failure ID: {failure_id}")
            return 0
        
        failure = self._failures[failure_id]
        
        if failure.recovered:
            logger.debug(f"Failure {failure_id} already recovered")
            return 0
        
        # Mark as recovered
        failure.recovered = True
        failure.recovery_timestamp = datetime.now().isoformat()
        failure.lesson_learned = lesson_learned
        
        # Calculate Zenkai XP boost
        f_type = FailureType(failure.failure_type)
        f_severity = FailureSeverity(failure.severity)
        
        base_xp = FAILURE_BASE_XP.get(f_type, 30)
        multiplier = ZENKAI_XP_MULTIPLIERS.get(f_severity, 2.0)
        
        zenkai_xp = int(base_xp * multiplier) + RECOVERY_BONUS_XP
        failure.xp_awarded = zenkai_xp
        
        # Apply XP to power levels
        power_tracker = self._get_power_tracker()
        if power_tracker:
            # Use knowledge XP since this is learned wisdom
            power_tracker.record_knowledge_learned(
                agent_id, 
                knowledge_count=int(zenkai_xp / 15),  # Convert to knowledge units
                source=f"Zenkai recovery: {failure.failure_type}"
            )
        
        # Activate Zenkai state (temporary boost)
        self._activate_zenkai_state(agent_id, failure_id, f_severity)
        
        logger.info(f"💥 ZENKAI BOOST! {agent_id} recovered and gained {zenkai_xp} XP!")
        
        self._save()
        return zenkai_xp
    
    def _activate_zenkai_state(
        self, 
        agent_id: str, 
        failure_id: str,
        severity: FailureSeverity
    ):
        """Activate temporary Zenkai power boost state."""
        now = datetime.now()
        
        # Get or create state
        if agent_id not in self._agent_states:
            self._agent_states[agent_id] = ZenkaiState(agent_id=agent_id)
        
        state = self._agent_states[agent_id]
        
        # If already in Zenkai state, increase consecutive counter
        if state.active:
            state.consecutive_recoveries += 1
        else:
            state.consecutive_recoveries = 1
        
        # Calculate boost multiplier based on severity and consecutive recoveries
        base_multiplier = ZENKAI_XP_MULTIPLIERS.get(severity, 2.0)
        consecutive_bonus = min(state.consecutive_recoveries * 0.1, 0.5)
        
        state.active = True
        state.boost_multiplier = base_multiplier + consecutive_bonus
        state.activated_at = now.isoformat()
        state.expires_at = (now + ZENKAI_STATE_DURATION).isoformat()
        state.trigger_failure_id = failure_id
        
        logger.info(f"⚡ {agent_id} entered Zenkai state! Boost: {state.boost_multiplier:.1f}x")
    
    # =========================================================================
    # QUERY ZENKAI STATE
    # =========================================================================
    
    def is_in_zenkai_state(self, agent_id: str) -> bool:
        """Check if an agent is currently in Zenkai boost state."""
        if agent_id not in self._agent_states:
            return False
        
        state = self._agent_states[agent_id]
        
        if not state.active:
            return False
        
        # Check if expired
        if state.expires_at:
            expires = datetime.fromisoformat(state.expires_at)
            if datetime.now() > expires:
                state.active = False
                self._save()
                return False
        
        return True
    
    def get_zenkai_multiplier(self, agent_id: str) -> float:
        """Get current Zenkai boost multiplier for an agent."""
        if not self.is_in_zenkai_state(agent_id):
            return 1.0
        return self._agent_states[agent_id].boost_multiplier
    
    def get_failure_patterns(self, agent_id: str) -> Dict[str, int]:
        """Get failure pattern analysis for an agent."""
        if agent_id not in self._failure_patterns:
            return {}
        
        patterns = {}
        for f_type in self._failure_patterns[agent_id]:
            patterns[f_type] = patterns.get(f_type, 0) + 1
        
        return dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True))
    
    def get_unrecovered_failures(self, agent_id: str) -> List[FailureRecord]:
        """Get failures that haven't been recovered from yet."""
        return [
            f for f in self._failures.values()
            if f.agent_id == agent_id and not f.recovered
        ]
    
    def get_agent_zenkai_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get Zenkai statistics for an agent."""
        agent_failures = [f for f in self._failures.values() if f.agent_id == agent_id]
        recovered = [f for f in agent_failures if f.recovered]
        
        total_zenkai_xp = sum(f.xp_awarded for f in recovered)
        
        return {
            "agent_id": agent_id,
            "total_failures": len(agent_failures),
            "recovered_failures": len(recovered),
            "recovery_rate": len(recovered) / len(agent_failures) if agent_failures else 0,
            "total_zenkai_xp": total_zenkai_xp,
            "in_zenkai_state": self.is_in_zenkai_state(agent_id),
            "current_multiplier": self.get_zenkai_multiplier(agent_id),
            "failure_patterns": self.get_failure_patterns(agent_id),
            "unrecovered": len(self.get_unrecovered_failures(agent_id)),
        }
    
    def display_zenkai_status(self) -> str:
        """Display Zenkai status for all agents."""
        lines = []
        lines.append("╔════════════════════════════════════════════════════════════════╗")
        lines.append("║              💥 ZENKAI BOOST STATUS 💥                         ║")
        lines.append("╠════════════════════════════════════════════════════════════════╣")
        
        agents = ["chief_of_staff", "researcher", "writer", "fact_checker", "reflector"]
        agent_names = {
            "chief_of_staff": "Athena",
            "researcher": "Clio", 
            "writer": "Calliope",
            "fact_checker": "Vera",
            "reflector": "Sophia",
        }
        
        for agent_id in agents:
            stats = self.get_agent_zenkai_stats(agent_id)
            name = agent_names.get(agent_id, agent_id)
            
            status = "⚡ ZENKAI ACTIVE" if stats["in_zenkai_state"] else "○ Normal"
            mult = f"{stats['current_multiplier']:.1f}x" if stats["in_zenkai_state"] else "1.0x"
            
            lines.append(f"║ {name:12} │ {status:16} │ Boost: {mult:5} │ XP: {stats['total_zenkai_xp']:>5} ║")
            
            if stats["failure_patterns"]:
                top_pattern = list(stats["failure_patterns"].keys())[0]
                lines.append(f"║              │ Common: {top_pattern:20}  │ Unrecovered: {stats['unrecovered']:>2} ║")
            
            lines.append("╟────────────────────────────────────────────────────────────────╢")
        
        lines.append("╚════════════════════════════════════════════════════════════════╝")
        
        return "\n".join(lines)


# Singleton instance
_zenkai_tracker: Optional[ZenkaiTracker] = None


def get_zenkai_tracker() -> ZenkaiTracker:
    """Get the singleton Zenkai tracker."""
    global _zenkai_tracker
    if _zenkai_tracker is None:
        _zenkai_tracker = ZenkaiTracker()
    return _zenkai_tracker


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Zenkai Boost System")
    parser.add_argument("--status", action="store_true", help="Show Zenkai status")
    parser.add_argument("--fail", nargs=3, metavar=("AGENT", "TYPE", "CONTEXT"),
                       help="Record a failure")
    parser.add_argument("--recover", nargs=3, metavar=("AGENT", "FAILURE_ID", "LESSON"),
                       help="Record recovery")
    parser.add_argument("--stats", type=str, help="Show stats for agent")
    
    args = parser.parse_args()
    
    tracker = get_zenkai_tracker()
    
    if args.status:
        print(tracker.display_zenkai_status())
    
    elif args.fail:
        agent, f_type, context = args.fail
        fid = tracker.record_failure(agent, f_type, context, severity="medium")
        print(f"Failure recorded: {fid}")
    
    elif args.recover:
        agent, fid, lesson = args.recover
        xp = tracker.record_recovery(agent, fid, lesson)
        print(f"Recovery recorded! Zenkai XP: {xp}")
    
    elif args.stats:
        stats = tracker.get_agent_zenkai_stats(args.stats)
        print(json.dumps(stats, indent=2))
    
    else:
        print(tracker.display_zenkai_status())
