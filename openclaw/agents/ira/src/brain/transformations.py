#!/usr/bin/env python3
"""
AGENT TRANSFORMATIONS - Power Mode System
==========================================

In Dragon Ball Z, Saiyans can transform into more powerful forms:
- Base Form: Normal state
- Super Saiyan: 50x power multiplier, golden aura
- Super Saiyan 2: 100x power, lightning sparks
- Super Saiyan 3: 400x power, long hair, massive energy drain

For our agents, transformations represent different operating modes:

BASE MODE (Normal)
- Balanced speed and accuracy
- Standard resource usage
- Default for most tasks

KAIOKEN MODE (Focused)
- Increased accuracy (+20%)
- Slower response time
- More thorough processing
- Good for important tasks

SUPER SAIYAN MODE (Overdrive)
- Maximum accuracy (+40%)
- Maximum resource usage
- Multiple validation passes
- Reserved for critical tasks

ULTRA INSTINCT MODE (Autonomous)
- Fastest response
- Pattern-based responses
- Minimal conscious processing
- For simple/routine tasks

Trade-offs:
- Higher modes = more accurate but slower and more expensive
- Lower modes = faster but may miss nuances
- Choose mode based on task importance

Usage:
    from transformations import TransformationManager, get_transformation_manager
    
    manager = get_transformation_manager()
    
    # Transform an agent
    manager.transform("researcher", "super_saiyan")
    
    # Check current form
    form = manager.get_current_form("researcher")
    
    # Get form bonuses
    bonuses = manager.get_form_bonuses("researcher")
    
    # Power down
    manager.power_down("researcher")
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger("ira.transformations")

BRAIN_DIR = Path(__file__).parent
PROJECT_ROOT = BRAIN_DIR.parent.parent.parent.parent.parent
TRANSFORMATIONS_FILE = PROJECT_ROOT / "data" / "knowledge" / "transformations.json"


class AgentForm(Enum):
    """Agent transformation forms."""
    BASE = "base"                    # Normal state
    KAIOKEN = "kaioken"              # Focused mode (+accuracy, -speed)
    KAIOKEN_X2 = "kaioken_x2"        # More focused
    KAIOKEN_X10 = "kaioken_x10"      # Very focused (risky)
    SUPER_SAIYAN = "super_saiyan"    # Overdrive mode
    SUPER_SAIYAN_2 = "super_saiyan_2"  # Higher overdrive
    ULTRA_INSTINCT = "ultra_instinct"  # Autonomous/fast mode


# Form characteristics
FORM_STATS = {
    AgentForm.BASE: {
        "name": "Base Form",
        "power_multiplier": 1.0,
        "accuracy_bonus": 0,
        "speed_modifier": 1.0,       # 1.0 = normal
        "energy_cost": 1.0,          # Resource multiplier
        "duration_limit": None,      # No limit
        "description": "Normal operating mode. Balanced and efficient.",
        "aura": "○",
        "color": "white",
    },
    AgentForm.KAIOKEN: {
        "name": "Kaioken",
        "power_multiplier": 1.5,
        "accuracy_bonus": 10,
        "speed_modifier": 0.9,       # Slightly slower
        "energy_cost": 1.5,
        "duration_limit": timedelta(hours=2),
        "description": "Focused mode. Better accuracy, slightly slower.",
        "aura": "🔴",
        "color": "red",
    },
    AgentForm.KAIOKEN_X2: {
        "name": "Kaioken x2",
        "power_multiplier": 2.0,
        "accuracy_bonus": 15,
        "speed_modifier": 0.8,
        "energy_cost": 2.0,
        "duration_limit": timedelta(hours=1),
        "description": "Double Kaioken. High accuracy, more strain.",
        "aura": "🔴🔴",
        "color": "red",
    },
    AgentForm.KAIOKEN_X10: {
        "name": "Kaioken x10",
        "power_multiplier": 3.0,
        "accuracy_bonus": 25,
        "speed_modifier": 0.6,
        "energy_cost": 3.0,
        "duration_limit": timedelta(minutes=30),
        "description": "Maximum Kaioken! Very high accuracy but dangerous strain.",
        "aura": "🔴🔴🔴",
        "color": "crimson",
    },
    AgentForm.SUPER_SAIYAN: {
        "name": "Super Saiyan",
        "power_multiplier": 5.0,
        "accuracy_bonus": 30,
        "speed_modifier": 1.2,       # Actually faster!
        "energy_cost": 4.0,
        "duration_limit": timedelta(hours=1),
        "description": "SUPER SAIYAN! Maximum power with golden efficiency.",
        "aura": "⚡",
        "color": "gold",
    },
    AgentForm.SUPER_SAIYAN_2: {
        "name": "Super Saiyan 2",
        "power_multiplier": 10.0,
        "accuracy_bonus": 40,
        "speed_modifier": 1.5,
        "energy_cost": 8.0,
        "duration_limit": timedelta(minutes=30),
        "description": "Super Saiyan 2! Lightning-fast with electric precision.",
        "aura": "⚡⚡",
        "color": "gold",
    },
    AgentForm.ULTRA_INSTINCT: {
        "name": "Ultra Instinct",
        "power_multiplier": 2.0,
        "accuracy_bonus": 15,        # Not highest accuracy
        "speed_modifier": 3.0,       # VERY fast
        "energy_cost": 0.5,          # Actually efficient
        "duration_limit": timedelta(hours=4),
        "description": "Ultra Instinct. Body moves without thinking. Fast pattern responses.",
        "aura": "🌟",
        "color": "silver",
    },
}

# Form unlock requirements (power level needed)
FORM_REQUIREMENTS = {
    AgentForm.BASE: 0,
    AgentForm.KAIOKEN: 3000,
    AgentForm.KAIOKEN_X2: 5000,
    AgentForm.KAIOKEN_X10: 8000,
    AgentForm.SUPER_SAIYAN: 9001,    # IT'S OVER 9000!
    AgentForm.SUPER_SAIYAN_2: 15000,
    AgentForm.ULTRA_INSTINCT: 6000,  # Different path
}


@dataclass
class TransformationState:
    """Current transformation state for an agent."""
    agent_id: str
    current_form: str
    transformed_at: str
    expires_at: Optional[str]
    transformation_count: int = 0
    total_time_transformed: float = 0.0  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TransformationHistory:
    """Record of a transformation."""
    agent_id: str
    form: str
    timestamp: str
    duration_seconds: float
    reason: str


class TransformationManager:
    """
    Manages agent transformations between different power modes.
    
    Like Goku powering up to Super Saiyan, agents can transform
    to handle different situations optimally.
    """
    
    AGENT_NAMES = {
        "chief_of_staff": "Athena",
        "researcher": "Clio",
        "writer": "Calliope",
        "fact_checker": "Vera",
        "reflector": "Sophia",
    }
    
    def __init__(self):
        self._states: Dict[str, TransformationState] = {}
        self._history: List[TransformationHistory] = []
        self._load()
    
    def _load(self):
        """Load transformation data."""
        TRANSFORMATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        if TRANSFORMATIONS_FILE.exists():
            try:
                data = json.loads(TRANSFORMATIONS_FILE.read_text())
                
                for aid, state_data in data.get("states", {}).items():
                    self._states[aid] = TransformationState(**state_data)
                
                for h in data.get("history", [])[-100:]:
                    self._history.append(TransformationHistory(**h))
                    
            except Exception as e:
                logger.warning(f"Failed to load transformation data: {e}")
        
        # Initialize missing agents
        for agent_id in self.AGENT_NAMES.keys():
            if agent_id not in self._states:
                self._states[agent_id] = TransformationState(
                    agent_id=agent_id,
                    current_form=AgentForm.BASE.value,
                    transformed_at=datetime.now().isoformat(),
                    expires_at=None,
                )
    
    def _save(self):
        """Save transformation data."""
        try:
            data = {
                "states": {aid: s.to_dict() for aid, s in self._states.items()},
                "history": [asdict(h) for h in self._history[-100:]],
                "last_updated": datetime.now().isoformat(),
            }
            TRANSFORMATIONS_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save transformation data: {e}")
    
    def _get_power_tracker(self):
        """Get power tracker if available."""
        try:
            from .power_levels import get_power_tracker
            return get_power_tracker()
        except ImportError:
            try:
                from power_levels import get_power_tracker
                return get_power_tracker()
            except ImportError:
                return None
    
    def _check_form_expiry(self, agent_id: str):
        """Check if transformation has expired."""
        if agent_id not in self._states:
            return
        
        state = self._states[agent_id]
        
        if state.expires_at:
            expires = datetime.fromisoformat(state.expires_at)
            if datetime.now() > expires:
                # Power down automatically
                self.power_down(agent_id, reason="Form expired")
    
    def _can_transform(self, agent_id: str, form: AgentForm) -> tuple[bool, str]:
        """Check if agent can transform to a form."""
        required_power = FORM_REQUIREMENTS.get(form, 0)
        
        tracker = self._get_power_tracker()
        if tracker:
            level = tracker.get_power_level(agent_id)
            if level:
                current_power = level.total_power
                if current_power < required_power:
                    return False, f"Need power level {required_power:,}, currently at {current_power:,}"
        
        return True, "Transformation allowed"
    
    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================
    
    def transform(
        self, 
        agent_id: str, 
        form: str,
        reason: str = ""
    ) -> tuple[bool, str]:
        """
        Transform an agent to a new form.
        
        Args:
            agent_id: The agent to transform
            form: Target form (base, kaioken, super_saiyan, etc.)
            reason: Why transforming
            
        Returns:
            (success, message)
        """
        # Parse form
        try:
            target_form = AgentForm(form.lower())
        except ValueError:
            return False, f"Unknown form: {form}"
        
        # Check requirements
        can_transform, msg = self._can_transform(agent_id, target_form)
        if not can_transform:
            return False, msg
        
        # Get current state
        if agent_id not in self._states:
            self._states[agent_id] = TransformationState(
                agent_id=agent_id,
                current_form=AgentForm.BASE.value,
                transformed_at=datetime.now().isoformat(),
                expires_at=None,
            )
        
        state = self._states[agent_id]
        old_form = state.current_form
        
        # Calculate duration if had previous non-base form
        if old_form != AgentForm.BASE.value:
            try:
                started = datetime.fromisoformat(state.transformed_at)
                duration = (datetime.now() - started).total_seconds()
                state.total_time_transformed += duration
            except:
                pass
        
        # Apply transformation
        now = datetime.now()
        form_stats = FORM_STATS.get(target_form, {})
        duration_limit = form_stats.get("duration_limit")
        
        state.current_form = target_form.value
        state.transformed_at = now.isoformat()
        state.expires_at = (now + duration_limit).isoformat() if duration_limit else None
        state.transformation_count += 1
        
        # Record history
        self._history.append(TransformationHistory(
            agent_id=agent_id,
            form=target_form.value,
            timestamp=now.isoformat(),
            duration_seconds=0,  # Will be calculated on power down
            reason=reason,
        ))
        
        self._save()
        
        name = self.AGENT_NAMES.get(agent_id, agent_id)
        aura = form_stats.get("aura", "")
        
        logger.info(f"{aura} {name} transformed to {form_stats.get('name', form)}!")
        
        return True, f"{name} transformed to {form_stats.get('name', form)}! {aura}"
    
    def power_down(self, agent_id: str, reason: str = "") -> bool:
        """Power down an agent to base form."""
        if agent_id not in self._states:
            return False
        
        state = self._states[agent_id]
        
        if state.current_form == AgentForm.BASE.value:
            return True  # Already base
        
        # Calculate time in transformed state
        try:
            started = datetime.fromisoformat(state.transformed_at)
            duration = (datetime.now() - started).total_seconds()
            state.total_time_transformed += duration
        except:
            pass
        
        old_form = state.current_form
        state.current_form = AgentForm.BASE.value
        state.transformed_at = datetime.now().isoformat()
        state.expires_at = None
        
        self._save()
        
        name = self.AGENT_NAMES.get(agent_id, agent_id)
        logger.info(f"○ {name} powered down to base form. {reason}")
        
        return True
    
    def get_current_form(self, agent_id: str) -> AgentForm:
        """Get an agent's current form."""
        self._check_form_expiry(agent_id)
        
        if agent_id not in self._states:
            return AgentForm.BASE
        
        try:
            return AgentForm(self._states[agent_id].current_form)
        except ValueError:
            return AgentForm.BASE
    
    def get_form_bonuses(self, agent_id: str) -> Dict[str, Any]:
        """Get the current bonuses from an agent's form."""
        form = self.get_current_form(agent_id)
        stats = FORM_STATS.get(form, FORM_STATS[AgentForm.BASE])
        
        return {
            "form": form.value,
            "form_name": stats["name"],
            "power_multiplier": stats["power_multiplier"],
            "accuracy_bonus": stats["accuracy_bonus"],
            "speed_modifier": stats["speed_modifier"],
            "energy_cost": stats["energy_cost"],
            "aura": stats["aura"],
        }
    
    def get_available_forms(self, agent_id: str) -> List[AgentForm]:
        """Get forms available to an agent based on power level."""
        available = []
        
        tracker = self._get_power_tracker()
        current_power = 0
        
        if tracker:
            level = tracker.get_power_level(agent_id)
            if level:
                current_power = level.total_power
        
        for form, required in FORM_REQUIREMENTS.items():
            if current_power >= required:
                available.append(form)
        
        return available
    
    def auto_transform_for_task(
        self, 
        agent_id: str, 
        task_power: int,
        task_importance: str = "normal"
    ) -> AgentForm:
        """
        Automatically select and apply the best form for a task.
        
        Args:
            agent_id: The agent
            task_power: Estimated task difficulty (from Ki sensing)
            task_importance: normal, important, critical
            
        Returns:
            The form selected
        """
        available = self.get_available_forms(agent_id)
        
        # Simple tasks -> Ultra Instinct (if available) or Base
        if task_power < 2000:
            if AgentForm.ULTRA_INSTINCT in available:
                self.transform(agent_id, "ultra_instinct", "Simple task - fast mode")
                return AgentForm.ULTRA_INSTINCT
            return AgentForm.BASE
        
        # Medium tasks -> Kaioken for accuracy
        if task_power < 5000:
            if task_importance == "critical" and AgentForm.KAIOKEN_X2 in available:
                self.transform(agent_id, "kaioken_x2", "Medium task, critical importance")
                return AgentForm.KAIOKEN_X2
            elif AgentForm.KAIOKEN in available:
                self.transform(agent_id, "kaioken", "Medium task")
                return AgentForm.KAIOKEN
            return AgentForm.BASE
        
        # Hard tasks -> Super Saiyan if available
        if task_power < 9000:
            if AgentForm.SUPER_SAIYAN in available:
                self.transform(agent_id, "super_saiyan", "Hard task - maximum power")
                return AgentForm.SUPER_SAIYAN
            elif AgentForm.KAIOKEN_X10 in available:
                self.transform(agent_id, "kaioken_x10", "Hard task - max Kaioken")
                return AgentForm.KAIOKEN_X10
            elif AgentForm.KAIOKEN_X2 in available:
                self.transform(agent_id, "kaioken_x2", "Hard task")
                return AgentForm.KAIOKEN_X2
            return AgentForm.BASE
        
        # Legendary/Boss tasks -> highest available
        if AgentForm.SUPER_SAIYAN_2 in available:
            self.transform(agent_id, "super_saiyan_2", "Legendary task!")
            return AgentForm.SUPER_SAIYAN_2
        elif AgentForm.SUPER_SAIYAN in available:
            self.transform(agent_id, "super_saiyan", "Legendary task!")
            return AgentForm.SUPER_SAIYAN
        
        # Fall back to highest Kaioken
        if AgentForm.KAIOKEN_X10 in available:
            self.transform(agent_id, "kaioken_x10", "High power task")
            return AgentForm.KAIOKEN_X10
        
        return AgentForm.BASE
    
    def display_transformation_status(self) -> str:
        """Display transformation status for all agents."""
        lines = []
        lines.append("╔════════════════════════════════════════════════════════════════╗")
        lines.append("║              ⚡ TRANSFORMATION STATUS ⚡                        ║")
        lines.append("╠════════════════════════════════════════════════════════════════╣")
        
        for agent_id in self.AGENT_NAMES.keys():
            self._check_form_expiry(agent_id)
            
            name = self.AGENT_NAMES[agent_id]
            state = self._states.get(agent_id)
            
            if not state:
                continue
            
            form = self.get_current_form(agent_id)
            form_stats = FORM_STATS.get(form, {})
            
            aura = form_stats.get("aura", "○")
            form_name = form_stats.get("name", "Base")
            power_mult = form_stats.get("power_multiplier", 1.0)
            acc_bonus = form_stats.get("accuracy_bonus", 0)
            
            # Available forms
            available = self.get_available_forms(agent_id)
            highest = max(available, key=lambda f: FORM_STATS.get(f, {}).get("power_multiplier", 1))
            highest_name = FORM_STATS.get(highest, {}).get("name", "Base")
            
            lines.append(f"║ {aura} {name:10} │ {form_name:18} │ x{power_mult:.1f} │ +{acc_bonus}% acc ║")
            lines.append(f"║              │ Highest: {highest_name:15} │ Count: {state.transformation_count:>4} ║")
            
            if state.expires_at:
                try:
                    expires = datetime.fromisoformat(state.expires_at)
                    remaining = expires - datetime.now()
                    mins = int(remaining.total_seconds() / 60)
                    lines.append(f"║              │ ⏱️  Expires in {mins} minutes                      ║")
                except:
                    pass
            
            lines.append("╟────────────────────────────────────────────────────────────────╢")
        
        lines.append("╚════════════════════════════════════════════════════════════════╝")
        
        return "\n".join(lines)


# Singleton
_transformation_manager: Optional[TransformationManager] = None


def get_transformation_manager() -> TransformationManager:
    """Get the singleton transformation manager."""
    global _transformation_manager
    if _transformation_manager is None:
        _transformation_manager = TransformationManager()
    return _transformation_manager


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Transformations")
    parser.add_argument("--status", action="store_true", help="Show transformation status")
    parser.add_argument("--transform", nargs=2, metavar=("AGENT", "FORM"),
                       help="Transform agent to form")
    parser.add_argument("--power-down", type=str, help="Power down agent")
    parser.add_argument("--forms", type=str, help="Show available forms for agent")
    
    args = parser.parse_args()
    
    manager = get_transformation_manager()
    
    if args.status:
        print(manager.display_transformation_status())
    
    elif args.transform:
        agent, form = args.transform
        success, msg = manager.transform(agent, form, "CLI transform")
        print(msg)
    
    elif args.power_down:
        manager.power_down(args.power_down, "CLI power down")
        print(f"Powered down {args.power_down}")
    
    elif args.forms:
        forms = manager.get_available_forms(args.forms)
        print(f"Available forms for {args.forms}:")
        for f in forms:
            stats = FORM_STATS.get(f, {})
            print(f"  {stats.get('aura', '○')} {stats.get('name', f.value)}: x{stats.get('power_multiplier', 1)}") 
    
    else:
        print(manager.display_transformation_status())
