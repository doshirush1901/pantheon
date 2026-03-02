#!/usr/bin/env python3
"""
FUSION DANCE - Agent Combination System
========================================

In Dragon Ball Z, two warriors can perform the Fusion Dance to combine
into a single, more powerful fighter:
- Goku + Vegeta = Gogeta (Fusion Dance) or Vegito (Potara Earrings)
- Power is multiplied, not just added
- Fusion has a time limit (30 minutes for Fusion Dance)
- Failed fusion creates a weak/fat version

For our agents, Fusion enables:
- Combining two agents' expertise for boss-level tasks
- Multiplied effective power (not just added)
- Temporary fusion state with time limit
- Combined knowledge access from both agents
- Unified response that leverages both skill sets

Fusion Combinations:
- Athena + Clio = "Athlio" (Strategy + Research)
- Clio + Vera = "Clira" (Research + Verification) 
- Calliope + Vera = "Callira" (Writing + Fact-Checking)
- Athena + Sophia = "Sophena" (Strategy + Reflection)

Usage:
    from fusion import FusionManager, get_fusion_manager
    
    manager = get_fusion_manager()
    
    # Perform fusion
    fusion = manager.fuse("researcher", "fact_checker", task="Verify complex claims")
    
    # Check fusion state
    if manager.is_fused("researcher"):
        fusion_id = manager.get_active_fusion("researcher")
        
    # Defuse
    manager.defuse(fusion_id)
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import hashlib

logger = logging.getLogger("ira.fusion")

BRAIN_DIR = Path(__file__).parent
PROJECT_ROOT = BRAIN_DIR.parent.parent.parent.parent.parent
FUSION_FILE = PROJECT_ROOT / "data" / "knowledge" / "fusion_log.json"

# Import power levels
try:
    from .power_levels import get_power_tracker
    POWER_LEVELS_AVAILABLE = True
except ImportError:
    try:
        from power_levels import get_power_tracker
        POWER_LEVELS_AVAILABLE = True
    except ImportError:
        POWER_LEVELS_AVAILABLE = False


class FusionType(Enum):
    """Types of fusion available."""
    FUSION_DANCE = "fusion_dance"      # Standard 30-min fusion
    POTARA = "potara"                   # Longer fusion (1 hour)
    METAMORAN = "metamoran"             # Quick fusion (15 min, easier)


# Fusion duration limits
FUSION_DURATIONS = {
    FusionType.FUSION_DANCE: timedelta(minutes=30),
    FusionType.POTARA: timedelta(hours=1),
    FusionType.METAMORAN: timedelta(minutes=15),
}

# Power multipliers for fusion types
FUSION_POWER_MULTIPLIERS = {
    FusionType.FUSION_DANCE: 10.0,    # 10x combined power
    FusionType.POTARA: 15.0,          # 15x combined power (stronger)
    FusionType.METAMORAN: 5.0,        # 5x combined power (weaker but quick)
}

# Agent names
AGENT_NAMES = {
    "chief_of_staff": "Athena",
    "researcher": "Clio",
    "writer": "Calliope",
    "fact_checker": "Vera",
    "reflector": "Sophia",
}

# Fusion names (combined agent names)
FUSION_NAMES = {
    frozenset(["chief_of_staff", "researcher"]): "Athlio",
    frozenset(["chief_of_staff", "writer"]): "Athiope",
    frozenset(["chief_of_staff", "fact_checker"]): "Athera",
    frozenset(["chief_of_staff", "reflector"]): "Sophena",
    frozenset(["researcher", "writer"]): "Cliope",
    frozenset(["researcher", "fact_checker"]): "Clira",
    frozenset(["researcher", "reflector"]): "Cliphia",
    frozenset(["writer", "fact_checker"]): "Callira",
    frozenset(["writer", "reflector"]): "Calliphia",
    frozenset(["fact_checker", "reflector"]): "Veraphia",
}

# Synergy bonuses for certain combinations
FUSION_SYNERGIES = {
    frozenset(["researcher", "fact_checker"]): {
        "bonus": 2.0,  # Extra multiplier
        "description": "Research + Verification = Perfect accuracy",
        "special_ability": "claim_validation",
    },
    frozenset(["writer", "fact_checker"]): {
        "bonus": 1.8,
        "description": "Writing + Fact-checking = Bulletproof content",
        "special_ability": "verified_writing",
    },
    frozenset(["chief_of_staff", "reflector"]): {
        "bonus": 1.5,
        "description": "Strategy + Reflection = Adaptive planning",
        "special_ability": "learning_strategy",
    },
    frozenset(["researcher", "writer"]): {
        "bonus": 1.6,
        "description": "Research + Writing = Expert content creation",
        "special_ability": "informed_drafting",
    },
}


@dataclass
class FusionState:
    """Active fusion state."""
    fusion_id: str
    agent1_id: str
    agent2_id: str
    fusion_name: str
    fusion_type: str
    combined_power: int
    power_multiplier: float
    synergy_bonus: float
    special_ability: Optional[str]
    created_at: str
    expires_at: str
    task: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.now() > datetime.fromisoformat(self.expires_at)
    
    @property
    def time_remaining(self) -> timedelta:
        if not self.expires_at:
            return timedelta(hours=1)
        expires = datetime.fromisoformat(self.expires_at)
        remaining = expires - datetime.now()
        return max(remaining, timedelta(0))


@dataclass
class FusionHistory:
    """Record of a completed fusion."""
    fusion_id: str
    agent1_id: str
    agent2_id: str
    fusion_name: str
    fusion_type: str
    duration_seconds: float
    task: str
    success: bool
    timestamp: str


class FusionManager:
    """
    Manages agent fusion for boss-level tasks.
    
    Like the Fusion Dance in DBZ, two agents can combine their powers
    to handle tasks that would overwhelm either alone.
    """
    
    def __init__(self):
        self._active_fusions: Dict[str, FusionState] = {}
        self._history: List[FusionHistory] = []
        self._load()
    
    def _load(self):
        """Load fusion data."""
        FUSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        if FUSION_FILE.exists():
            try:
                data = json.loads(FUSION_FILE.read_text())
                
                for fid, fdata in data.get("active", {}).items():
                    state = FusionState(**fdata)
                    if not state.is_expired:
                        self._active_fusions[fid] = state
                
                for h in data.get("history", [])[-100:]:
                    self._history.append(FusionHistory(**h))
                    
            except Exception as e:
                logger.warning(f"Failed to load fusion data: {e}")
    
    def _save(self):
        """Save fusion data."""
        try:
            # Clean expired fusions
            self._active_fusions = {
                fid: f for fid, f in self._active_fusions.items()
                if not f.is_expired
            }
            
            data = {
                "active": {fid: f.to_dict() for fid, f in self._active_fusions.items()},
                "history": [asdict(h) for h in self._history[-100:]],
                "last_updated": datetime.now().isoformat(),
            }
            FUSION_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save fusion data: {e}")
    
    def _generate_fusion_id(self, agent1: str, agent2: str) -> str:
        """Generate unique fusion ID."""
        data = f"{agent1}:{agent2}:{datetime.now().isoformat()}"
        return f"fusion_{hashlib.md5(data.encode()).hexdigest()[:8]}"
    
    def _get_agent_power(self, agent_id: str) -> int:
        """Get agent's current power level."""
        if POWER_LEVELS_AVAILABLE:
            tracker = get_power_tracker()
            level = tracker.get_power_level(agent_id)
            if level:
                return level.total_power
        return 5000  # Default
    
    def _get_fusion_name(self, agent1: str, agent2: str) -> str:
        """Get the fusion name for two agents."""
        key = frozenset([agent1, agent2])
        return FUSION_NAMES.get(key, f"{AGENT_NAMES.get(agent1, agent1)[:3]}{AGENT_NAMES.get(agent2, agent2)[:3]}")
    
    def _get_synergy(self, agent1: str, agent2: str) -> Dict[str, Any]:
        """Get synergy bonus for a fusion combination."""
        key = frozenset([agent1, agent2])
        return FUSION_SYNERGIES.get(key, {"bonus": 1.0, "description": "Standard fusion", "special_ability": None})
    
    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================
    
    def can_fuse(self, agent1_id: str, agent2_id: str) -> Tuple[bool, str]:
        """
        Check if two agents can fuse.
        
        Returns:
            (can_fuse, reason)
        """
        # Check if either is already fused
        if self.is_fused(agent1_id):
            return False, f"{AGENT_NAMES.get(agent1_id)} is already fused"
        if self.is_fused(agent2_id):
            return False, f"{AGENT_NAMES.get(agent2_id)} is already fused"
        
        # Can't fuse with self
        if agent1_id == agent2_id:
            return False, "Cannot fuse with self"
        
        # Check if agents exist
        if agent1_id not in AGENT_NAMES or agent2_id not in AGENT_NAMES:
            return False, "Unknown agent"
        
        return True, "Fusion possible!"
    
    def fuse(
        self,
        agent1_id: str,
        agent2_id: str,
        fusion_type: str = "fusion_dance",
        task: str = ""
    ) -> Optional[FusionState]:
        """
        Perform fusion between two agents.
        
        FUUUU-SION-HA!
        
        Args:
            agent1_id: First agent
            agent2_id: Second agent
            fusion_type: Type of fusion (fusion_dance, potara, metamoran)
            task: The task this fusion is for
            
        Returns:
            FusionState if successful, None if failed
        """
        # Check if fusion is possible
        can, reason = self.can_fuse(agent1_id, agent2_id)
        if not can:
            logger.warning(f"Fusion failed: {reason}")
            return None
        
        # Parse fusion type
        try:
            f_type = FusionType(fusion_type.lower())
        except ValueError:
            f_type = FusionType.FUSION_DANCE
        
        # Calculate combined power
        power1 = self._get_agent_power(agent1_id)
        power2 = self._get_agent_power(agent2_id)
        
        base_multiplier = FUSION_POWER_MULTIPLIERS.get(f_type, 10.0)
        synergy = self._get_synergy(agent1_id, agent2_id)
        synergy_bonus = synergy.get("bonus", 1.0)
        
        # Fusion power = (power1 + power2) * multiplier * synergy
        combined_power = int((power1 + power2) * base_multiplier * synergy_bonus)
        
        # Calculate expiration
        duration = FUSION_DURATIONS.get(f_type, timedelta(minutes=30))
        now = datetime.now()
        expires = now + duration
        
        # Create fusion state
        fusion_id = self._generate_fusion_id(agent1_id, agent2_id)
        fusion_name = self._get_fusion_name(agent1_id, agent2_id)
        
        fusion = FusionState(
            fusion_id=fusion_id,
            agent1_id=agent1_id,
            agent2_id=agent2_id,
            fusion_name=fusion_name,
            fusion_type=f_type.value,
            combined_power=combined_power,
            power_multiplier=base_multiplier,
            synergy_bonus=synergy_bonus,
            special_ability=synergy.get("special_ability"),
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
            task=task,
        )
        
        self._active_fusions[fusion_id] = fusion
        self._save()
        
        name1 = AGENT_NAMES.get(agent1_id, agent1_id)
        name2 = AGENT_NAMES.get(agent2_id, agent2_id)
        
        logger.info(f"💫 FUSION! {name1} + {name2} = {fusion_name}! Power: {combined_power:,}")
        
        return fusion
    
    def defuse(self, fusion_id: str, success: bool = True) -> bool:
        """
        End a fusion and return agents to normal.
        
        Args:
            fusion_id: The fusion to end
            success: Whether the fusion task was successful
            
        Returns:
            True if defused successfully
        """
        if fusion_id not in self._active_fusions:
            return False
        
        fusion = self._active_fusions.pop(fusion_id)
        
        # Calculate duration
        created = datetime.fromisoformat(fusion.created_at)
        duration = (datetime.now() - created).total_seconds()
        
        # Record history
        self._history.append(FusionHistory(
            fusion_id=fusion_id,
            agent1_id=fusion.agent1_id,
            agent2_id=fusion.agent2_id,
            fusion_name=fusion.fusion_name,
            fusion_type=fusion.fusion_type,
            duration_seconds=duration,
            task=fusion.task,
            success=success,
            timestamp=datetime.now().isoformat(),
        ))
        
        self._save()
        
        logger.info(f"💨 {fusion.fusion_name} defused! Duration: {duration/60:.1f} minutes")
        
        return True
    
    def is_fused(self, agent_id: str) -> bool:
        """Check if an agent is currently fused."""
        for fusion in self._active_fusions.values():
            if fusion.is_expired:
                continue
            if fusion.agent1_id == agent_id or fusion.agent2_id == agent_id:
                return True
        return False
    
    def get_active_fusion(self, agent_id: str) -> Optional[FusionState]:
        """Get the active fusion for an agent."""
        for fusion in self._active_fusions.values():
            if fusion.is_expired:
                continue
            if fusion.agent1_id == agent_id or fusion.agent2_id == agent_id:
                return fusion
        return None
    
    def get_fusion_power(self, agent_id: str) -> int:
        """Get the effective power level when fused."""
        fusion = self.get_active_fusion(agent_id)
        if fusion:
            return fusion.combined_power
        return self._get_agent_power(agent_id)
    
    def get_all_active_fusions(self) -> List[FusionState]:
        """Get all active fusions."""
        # Clean expired
        self._active_fusions = {
            fid: f for fid, f in self._active_fusions.items()
            if not f.is_expired
        }
        return list(self._active_fusions.values())
    
    def get_best_fusion_for_task(self, task_power: int) -> Optional[Tuple[str, str]]:
        """
        Recommend the best fusion combination for a task.
        
        Args:
            task_power: The estimated power level of the task
            
        Returns:
            (agent1_id, agent2_id) or None if fusion not needed
        """
        # Find available agents (not already fused)
        available = [a for a in AGENT_NAMES.keys() if not self.is_fused(a)]
        
        if len(available) < 2:
            return None
        
        # Score all possible fusions
        best_fusion = None
        best_score = 0
        
        for i, agent1 in enumerate(available):
            for agent2 in available[i+1:]:
                # Calculate potential fusion power
                power1 = self._get_agent_power(agent1)
                power2 = self._get_agent_power(agent2)
                synergy = self._get_synergy(agent1, agent2)
                
                fusion_power = (power1 + power2) * 10.0 * synergy.get("bonus", 1.0)
                
                # Score based on how well fusion matches task
                if fusion_power >= task_power:
                    # Prefer smaller excess power (efficiency)
                    score = fusion_power - (fusion_power - task_power) * 0.1
                    score *= synergy.get("bonus", 1.0)  # Synergy bonus
                    
                    if score > best_score:
                        best_score = score
                        best_fusion = (agent1, agent2)
        
        return best_fusion
    
    def display_fusion_status(self) -> str:
        """Display current fusion status."""
        lines = []
        lines.append("╔════════════════════════════════════════════════════════════════╗")
        lines.append("║                   💫 FUSION STATUS 💫                          ║")
        lines.append("╠════════════════════════════════════════════════════════════════╣")
        
        active = self.get_all_active_fusions()
        
        if not active:
            lines.append("║   No active fusions. All agents operating independently.      ║")
        else:
            for fusion in active:
                name1 = AGENT_NAMES.get(fusion.agent1_id, fusion.agent1_id)
                name2 = AGENT_NAMES.get(fusion.agent2_id, fusion.agent2_id)
                remaining = fusion.time_remaining
                mins = int(remaining.total_seconds() / 60)
                
                lines.append(f"║ 💫 {fusion.fusion_name:12} │ {name1} + {name2:12}                ║")
                lines.append(f"║    Power: {fusion.combined_power:>10,} │ Type: {fusion.fusion_type:15}   ║")
                lines.append(f"║    Time remaining: {mins} minutes                              ║")
                if fusion.special_ability:
                    lines.append(f"║    Special: {fusion.special_ability:40}       ║")
                lines.append("╟────────────────────────────────────────────────────────────────╢")
        
        # Show possible fusions
        lines.append("║ Available Fusion Combinations:                                 ║")
        synergies = sorted(FUSION_SYNERGIES.items(), key=lambda x: x[1]["bonus"], reverse=True)
        for agents, synergy in synergies[:3]:
            agent_list = list(agents)
            name1 = AGENT_NAMES.get(agent_list[0], agent_list[0])
            name2 = AGENT_NAMES.get(agent_list[1], agent_list[1])
            fusion_name = self._get_fusion_name(agent_list[0], agent_list[1])
            bonus = synergy["bonus"]
            lines.append(f"║   {name1} + {name2} = {fusion_name} (x{bonus:.1f} synergy)           ║")
        
        lines.append("╚════════════════════════════════════════════════════════════════╝")
        
        return "\n".join(lines)


# Singleton
_fusion_manager: Optional[FusionManager] = None


def get_fusion_manager() -> FusionManager:
    """Get the singleton fusion manager."""
    global _fusion_manager
    if _fusion_manager is None:
        _fusion_manager = FusionManager()
    return _fusion_manager


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Fusion System")
    parser.add_argument("--status", action="store_true", help="Show fusion status")
    parser.add_argument("--fuse", nargs=2, metavar=("AGENT1", "AGENT2"),
                       help="Fuse two agents")
    parser.add_argument("--defuse", type=str, help="Defuse by fusion ID")
    parser.add_argument("--task", type=str, default="", help="Task for fusion")
    parser.add_argument("--recommend", type=int, help="Recommend fusion for task power")
    
    args = parser.parse_args()
    
    manager = get_fusion_manager()
    
    if args.status:
        print(manager.display_fusion_status())
    
    elif args.fuse:
        agent1, agent2 = args.fuse
        fusion = manager.fuse(agent1, agent2, task=args.task)
        if fusion:
            print(f"💫 FUSION SUCCESS!")
            print(f"   Name: {fusion.fusion_name}")
            print(f"   Power: {fusion.combined_power:,}")
            print(f"   Expires: {fusion.time_remaining.total_seconds()/60:.0f} minutes")
        else:
            print("❌ Fusion failed!")
    
    elif args.defuse:
        if manager.defuse(args.defuse):
            print("💨 Defused successfully!")
        else:
            print("❌ Fusion not found")
    
    elif args.recommend:
        result = manager.get_best_fusion_for_task(args.recommend)
        if result:
            agent1, agent2 = result
            name1 = AGENT_NAMES.get(agent1, agent1)
            name2 = AGENT_NAMES.get(agent2, agent2)
            print(f"Recommended fusion: {name1} + {name2}")
        else:
            print("No fusion recommended for this power level")
    
    else:
        print(manager.display_fusion_status())
