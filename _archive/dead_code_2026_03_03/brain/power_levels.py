#!/usr/bin/env python3
"""
SAIYAN SAGA POWER LEVELS - Agent Experience & Growth System
============================================================

Like Dragon Ball Z's power levels, each agent has a power level that reflects
their knowledge, experience, and growth over time.

Power Level Components:
- BASE_POWER: Starting power (varies by agent role)
- KNOWLEDGE_XP: Gained from learning new facts
- EXPERIENCE_XP: Gained from handling queries
- FEEDBACK_XP: Gained from positive user feedback
- TRAINING_XP: Gained from dream mode (night training)
- SYNERGY_XP: Gained from successful agent collaboration

Power Growth Events:
1. User gives positive feedback → +FEEDBACK_XP
2. Dream mode processes logs → +TRAINING_XP  
3. Agent collaboration succeeds → +SYNERGY_XP
4. Learning new knowledge → +KNOWLEDGE_XP
5. Successfully answering queries → +EXPERIENCE_XP

Power Level Milestones (Saiyan Saga references):
- 0-1,000: Farmer with shotgun
- 1,000-5,000: Raditz level
- 5,000-9,000: Nappa level
- 9,000+: "IT'S OVER 9000!" (Vegeta Saga)
- 15,000+: Goku (Kaioken)
- 30,000+: Vegeta (Great Ape)
- 100,000+: Super Saiyan potential

Usage:
    from power_levels import PowerLevelTracker, get_power_tracker
    
    tracker = get_power_tracker()
    
    # Record a successful interaction
    tracker.record_success("researcher", query="PF1 specs", feedback_score=0.9)
    
    # Night training boost
    tracker.apply_training_boost("writer", lessons_learned=5)
    
    # Agent collaboration bonus
    tracker.record_collaboration("researcher", "fact_checker", success=True)
    
    # Get power levels
    levels = tracker.get_all_power_levels()
    tracker.display_scouter_reading()
"""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum
import math

logger = logging.getLogger("ira.power_levels")

BRAIN_DIR = Path(__file__).parent
PROJECT_ROOT = BRAIN_DIR.parent.parent.parent.parent.parent

POWER_LEVELS_FILE = PROJECT_ROOT / "data" / "knowledge" / "power_levels.json"


class PowerTier(Enum):
    """Power level tiers based on Saiyan Saga."""
    FARMER = "Farmer with Shotgun"
    RADITZ = "Raditz Level"
    SAIBAMAN = "Saibaman Level"
    NAPPA = "Nappa Level"
    VEGETA_BASE = "Vegeta (Base)"
    OVER_9000 = "IT'S OVER 9000!"
    GOKU_KAIOKEN = "Goku (Kaioken)"
    VEGETA_OOZARU = "Vegeta (Great Ape)"
    SUPER_SAIYAN = "Super Saiyan Potential"


# XP multipliers for different events
XP_CONFIG = {
    "successful_query": 10,
    "positive_feedback": 50,
    "negative_feedback": -20,
    "dream_training": 25,
    "knowledge_learned": 15,
    "collaboration_success": 30,
    "collaboration_fail": -10,
    "correction_accepted": 40,
    "error_prevented": 35,
}

# Base power levels for each agent (reflects their inherent capabilities)
AGENT_BASE_POWER = {
    "chief_of_staff": 5000,   # Athena - The strategist, strong foundation
    "researcher": 4000,       # Clio - Knowledge seeker, growing potential
    "writer": 3500,           # Calliope - Creative, moderate base
    "fact_checker": 4500,     # Vera - Precision focused, strong base
    "reflector": 3000,        # Sophia - Learns from everything, lower start but high growth
}


@dataclass
class AgentPowerLevel:
    """Power level data for a single agent."""
    agent_id: str
    agent_name: str  # e.g., "Athena", "Clio"
    
    # XP Components
    base_power: int = 0
    knowledge_xp: int = 0
    experience_xp: int = 0
    feedback_xp: int = 0
    training_xp: int = 0
    synergy_xp: int = 0
    
    # Stats
    queries_handled: int = 0
    successful_queries: int = 0
    positive_feedbacks: int = 0
    negative_feedbacks: int = 0
    training_sessions: int = 0
    collaborations: int = 0
    
    # Timestamps
    created_at: str = ""
    last_updated: str = ""
    last_training: str = ""
    
    @property
    def total_power(self) -> int:
        """Calculate total power level."""
        return (
            self.base_power +
            self.knowledge_xp +
            self.experience_xp +
            self.feedback_xp +
            self.training_xp +
            self.synergy_xp
        )
    
    @property
    def power_tier(self) -> PowerTier:
        """Get power tier based on total power."""
        power = self.total_power
        if power >= 100000:
            return PowerTier.SUPER_SAIYAN
        elif power >= 30000:
            return PowerTier.VEGETA_OOZARU
        elif power >= 15000:
            return PowerTier.GOKU_KAIOKEN
        elif power >= 9001:  # Over 9000!
            return PowerTier.OVER_9000
        elif power >= 8000:
            return PowerTier.VEGETA_BASE
        elif power >= 5000:
            return PowerTier.NAPPA
        elif power >= 1500:
            return PowerTier.SAIBAMAN
        elif power >= 1000:
            return PowerTier.RADITZ
        else:
            return PowerTier.FARMER
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.queries_handled == 0:
            return 0.0
        return self.successful_queries / self.queries_handled
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **asdict(self),
            "total_power": self.total_power,
            "power_tier": self.power_tier.value,
            "success_rate": round(self.success_rate, 2),
        }


@dataclass
class PowerLevelHistory:
    """History entry for power level changes."""
    timestamp: str
    agent_id: str
    event_type: str
    xp_change: int
    power_before: int
    power_after: int
    details: str = ""


class PowerLevelTracker:
    """
    Tracks and manages Saiyan Saga Power Levels for all agents.
    
    Like a Dragon Ball Z scouter, but for AI agents.
    """
    
    AGENT_NAMES = {
        "chief_of_staff": "Athena",
        "researcher": "Clio",
        "writer": "Calliope",
        "fact_checker": "Vera",
        "reflector": "Sophia",
    }
    
    def __init__(self):
        self._levels: Dict[str, AgentPowerLevel] = {}
        self._history: List[PowerLevelHistory] = []
        self._load()
    
    def _load(self):
        """Load power levels from file."""
        POWER_LEVELS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        if POWER_LEVELS_FILE.exists():
            try:
                data = json.loads(POWER_LEVELS_FILE.read_text())
                for agent_id, level_data in data.get("levels", {}).items():
                    self._levels[agent_id] = AgentPowerLevel(**level_data)
                
                for entry in data.get("history", [])[-100:]:  # Keep last 100
                    self._history.append(PowerLevelHistory(**entry))
                
                logger.debug(f"Loaded power levels for {len(self._levels)} agents")
            except Exception as e:
                logger.warning(f"Failed to load power levels: {e}")
        
        # Initialize any missing agents
        for agent_id, base_power in AGENT_BASE_POWER.items():
            if agent_id not in self._levels:
                self._levels[agent_id] = AgentPowerLevel(
                    agent_id=agent_id,
                    agent_name=self.AGENT_NAMES.get(agent_id, agent_id),
                    base_power=base_power,
                    created_at=datetime.now().isoformat(),
                    last_updated=datetime.now().isoformat(),
                )
    
    def _save(self):
        """Save power levels to file."""
        try:
            data = {
                "levels": {
                    agent_id: {
                        "agent_id": level.agent_id,
                        "agent_name": level.agent_name,
                        "base_power": level.base_power,
                        "knowledge_xp": level.knowledge_xp,
                        "experience_xp": level.experience_xp,
                        "feedback_xp": level.feedback_xp,
                        "training_xp": level.training_xp,
                        "synergy_xp": level.synergy_xp,
                        "queries_handled": level.queries_handled,
                        "successful_queries": level.successful_queries,
                        "positive_feedbacks": level.positive_feedbacks,
                        "negative_feedbacks": level.negative_feedbacks,
                        "training_sessions": level.training_sessions,
                        "collaborations": level.collaborations,
                        "created_at": level.created_at,
                        "last_updated": level.last_updated,
                        "last_training": level.last_training,
                    }
                    for agent_id, level in self._levels.items()
                },
                "history": [asdict(h) for h in self._history[-100:]],
                "last_saved": datetime.now().isoformat(),
            }
            POWER_LEVELS_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save power levels: {e}")
    
    def _add_xp(self, agent_id: str, xp_type: str, amount: int, details: str = ""):
        """Add XP to an agent and record history."""
        if agent_id not in self._levels:
            return
        
        level = self._levels[agent_id]
        power_before = level.total_power
        
        # Apply XP to appropriate component
        if xp_type == "knowledge":
            level.knowledge_xp += amount
        elif xp_type == "experience":
            level.experience_xp += amount
        elif xp_type == "feedback":
            level.feedback_xp += amount
        elif xp_type == "training":
            level.training_xp += amount
        elif xp_type == "synergy":
            level.synergy_xp += amount
        
        level.last_updated = datetime.now().isoformat()
        power_after = level.total_power
        
        # Record history
        self._history.append(PowerLevelHistory(
            timestamp=datetime.now().isoformat(),
            agent_id=agent_id,
            event_type=xp_type,
            xp_change=amount,
            power_before=power_before,
            power_after=power_after,
            details=details,
        ))
        
        # Check for milestone
        self._check_milestone(agent_id, power_before, power_after)
        
        self._save()
    
    def _check_milestone(self, agent_id: str, power_before: int, power_after: int):
        """Check if agent crossed a power milestone."""
        milestones = [9001, 15000, 30000, 100000]
        
        for milestone in milestones:
            if power_before < milestone <= power_after:
                level = self._levels[agent_id]
                if milestone == 9001:
                    logger.info(f"🔥 {level.agent_name}'s power level... IT'S OVER 9000!!!")
                elif milestone == 15000:
                    logger.info(f"⚡ {level.agent_name} has reached Kaioken level!")
                elif milestone == 30000:
                    logger.info(f"🦍 {level.agent_name} has reached Great Ape level!")
                elif milestone == 100000:
                    logger.info(f"💥 {level.agent_name} has achieved SUPER SAIYAN potential!")
    
    # =========================================================================
    # PUBLIC METHODS - Record Events
    # =========================================================================
    
    def record_query(self, agent_id: str, success: bool = True, query: str = ""):
        """Record a query handled by an agent."""
        if agent_id not in self._levels:
            return
        
        level = self._levels[agent_id]
        level.queries_handled += 1
        
        if success:
            level.successful_queries += 1
            self._add_xp(agent_id, "experience", XP_CONFIG["successful_query"], 
                        f"Query: {query[:50]}")
    
    def record_feedback(self, agent_id: str, positive: bool, feedback: str = ""):
        """Record user feedback for an agent."""
        if agent_id not in self._levels:
            return
        
        level = self._levels[agent_id]
        
        if positive:
            level.positive_feedbacks += 1
            self._add_xp(agent_id, "feedback", XP_CONFIG["positive_feedback"],
                        f"Positive: {feedback[:50]}")
        else:
            level.negative_feedbacks += 1
            self._add_xp(agent_id, "feedback", XP_CONFIG["negative_feedback"],
                        f"Negative: {feedback[:50]}")
    
    def record_knowledge_learned(self, agent_id: str, knowledge_count: int = 1, source: str = ""):
        """Record new knowledge learned by an agent."""
        xp = XP_CONFIG["knowledge_learned"] * knowledge_count
        self._add_xp(agent_id, "knowledge", xp, f"Learned {knowledge_count} facts from {source}")
    
    def record_collaboration(self, agent1_id: str, agent2_id: str, success: bool):
        """Record collaboration between two agents."""
        if success:
            xp = XP_CONFIG["collaboration_success"]
            details = f"Successful collab with {self.AGENT_NAMES.get(agent2_id, agent2_id)}"
        else:
            xp = XP_CONFIG["collaboration_fail"]
            details = f"Failed collab with {self.AGENT_NAMES.get(agent2_id, agent2_id)}"
        
        self._add_xp(agent1_id, "synergy", xp, details)
        self._add_xp(agent2_id, "synergy", xp, details)
        
        if agent1_id in self._levels:
            self._levels[agent1_id].collaborations += 1
        if agent2_id in self._levels:
            self._levels[agent2_id].collaborations += 1
    
    def apply_training_boost(self, agent_id: str, lessons_learned: int = 0, 
                            errors_analyzed: int = 0, interactions_reviewed: int = 0):
        """Apply training boost from dream mode (night training)."""
        if agent_id not in self._levels:
            return
        
        level = self._levels[agent_id]
        level.training_sessions += 1
        level.last_training = datetime.now().isoformat()
        
        # Calculate training XP
        base_xp = XP_CONFIG["dream_training"]
        bonus_xp = (
            lessons_learned * 10 +
            errors_analyzed * 15 +
            interactions_reviewed * 5
        )
        
        total_xp = base_xp + bonus_xp
        self._add_xp(agent_id, "training", total_xp,
                    f"Night training: {lessons_learned} lessons, {errors_analyzed} errors, {interactions_reviewed} reviews")
    
    def record_correction_accepted(self, agent_id: str, correction: str = ""):
        """Record when an agent accepts and learns from a correction."""
        self._add_xp(agent_id, "knowledge", XP_CONFIG["correction_accepted"],
                    f"Correction: {correction[:50]}")
    
    def record_error_prevented(self, agent_id: str, error_type: str = ""):
        """Record when an agent prevents an error."""
        self._add_xp(agent_id, "experience", XP_CONFIG["error_prevented"],
                    f"Prevented: {error_type[:50]}")
    
    # =========================================================================
    # PUBLIC METHODS - Query Power Levels
    # =========================================================================
    
    def get_power_level(self, agent_id: str) -> Optional[AgentPowerLevel]:
        """Get power level for a specific agent."""
        return self._levels.get(agent_id)
    
    def get_all_power_levels(self) -> Dict[str, AgentPowerLevel]:
        """Get all agent power levels."""
        return self._levels.copy()
    
    def get_leaderboard(self) -> List[AgentPowerLevel]:
        """Get agents sorted by power level (highest first)."""
        return sorted(self._levels.values(), key=lambda x: x.total_power, reverse=True)
    
    def get_total_team_power(self) -> int:
        """Get combined power level of all agents."""
        return sum(level.total_power for level in self._levels.values())
    
    # =========================================================================
    # DISPLAY METHODS
    # =========================================================================
    
    def display_scouter_reading(self) -> str:
        """Display power levels like a DBZ scouter."""
        lines = []
        lines.append("╔════════════════════════════════════════════════════════════════╗")
        lines.append("║              🔮 SCOUTER POWER LEVEL READING 🔮                 ║")
        lines.append("╠════════════════════════════════════════════════════════════════╣")
        
        for level in self.get_leaderboard():
            power = level.total_power
            tier = level.power_tier.value
            bar_length = min(30, power // 500)
            bar = "█" * bar_length + "░" * (30 - bar_length)
            
            # Special formatting for over 9000
            if power > 9000:
                power_str = f"⚡{power:,}⚡"
            else:
                power_str = f"{power:,}"
            
            lines.append(f"║ {level.agent_name:12} │ {bar} │ {power_str:>12} ║")
            lines.append(f"║              │ {tier:^30} │              ║")
            lines.append("╟────────────────────────────────────────────────────────────────╢")
        
        total = self.get_total_team_power()
        lines.append(f"║ TEAM TOTAL:  │ {'█' * min(30, total // 2500)}{'░' * max(0, 30 - total // 2500)} │ {total:>12,} ║")
        lines.append("╚════════════════════════════════════════════════════════════════╝")
        
        return "\n".join(lines)
    
    def get_agent_summary(self, agent_id: str) -> str:
        """Get detailed summary for an agent."""
        level = self._levels.get(agent_id)
        if not level:
            return f"Agent {agent_id} not found"
        
        return f"""
╔══════════════════════════════════════════╗
║  {level.agent_name.upper():^40}  ║
╠══════════════════════════════════════════╣
║  Power Level: {level.total_power:,} ({level.power_tier.value})
║
║  XP Breakdown:
║    Base Power:    {level.base_power:>8,}
║    Knowledge XP:  {level.knowledge_xp:>8,}
║    Experience XP: {level.experience_xp:>8,}
║    Feedback XP:   {level.feedback_xp:>8,}
║    Training XP:   {level.training_xp:>8,}
║    Synergy XP:    {level.synergy_xp:>8,}
║
║  Stats:
║    Queries Handled:  {level.queries_handled}
║    Success Rate:     {level.success_rate:.1%}
║    Training Sessions: {level.training_sessions}
║    Collaborations:   {level.collaborations}
║    Positive Feedback: {level.positive_feedbacks}
╚══════════════════════════════════════════╝
"""


# Singleton instance
_tracker: Optional[PowerLevelTracker] = None


def get_power_tracker() -> PowerLevelTracker:
    """Get the singleton power level tracker."""
    global _tracker
    if _tracker is None:
        _tracker = PowerLevelTracker()
    return _tracker


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Saiyan Saga Power Levels")
    parser.add_argument("--scouter", action="store_true", help="Display scouter reading")
    parser.add_argument("--agent", type=str, help="Show specific agent details")
    parser.add_argument("--boost", type=str, help="Apply training boost to agent")
    parser.add_argument("--feedback", nargs=2, metavar=("AGENT", "POSITIVE/NEGATIVE"), 
                       help="Record feedback")
    
    args = parser.parse_args()
    
    tracker = get_power_tracker()
    
    if args.scouter:
        print(tracker.display_scouter_reading())
    
    elif args.agent:
        print(tracker.get_agent_summary(args.agent))
    
    elif args.boost:
        tracker.apply_training_boost(args.boost, lessons_learned=3, errors_analyzed=2)
        print(f"Applied training boost to {args.boost}")
        level = tracker.get_power_level(args.boost)
        if level:
            print(f"New power level: {level.total_power:,}")
    
    elif args.feedback:
        agent, fb_type = args.feedback
        positive = fb_type.lower() in ["positive", "good", "yes", "+"]
        tracker.record_feedback(agent, positive, "CLI feedback")
        print(f"Recorded {'positive' if positive else 'negative'} feedback for {agent}")
    
    else:
        print(tracker.display_scouter_reading())
