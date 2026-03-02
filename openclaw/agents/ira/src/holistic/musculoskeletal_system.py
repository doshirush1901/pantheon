#!/usr/bin/env python3
"""
MUSCULOSKELETAL SYSTEM - Action-to-Learning Feedback Loops
===========================================================

Biological parallel:
    Muscles secrete myokines (irisin, cathepsin B, BDNF) during contraction
    that cross the blood-brain barrier and enhance cognition. Embodied
    cognition: the body learns by doing, not just by reading.

Ira parallel:
    Ira's "muscles" are her action systems: CRM, outreach, email drafting,
    quote generation. Currently these are underexercised and don't feed
    back into learning. Every action should produce a learning signal.

Key principle: Ira learns best by DOING, not just by ingesting documents.

Usage:
    from holistic.musculoskeletal_system import get_musculoskeletal_system

    musculo = get_musculoskeletal_system()
    musculo.record_action("email_sent", {...})
    musculo.record_action_outcome("email_sent", request_id, "positive_reply")
    myokines = musculo.extract_learning_signals()
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("ira.musculoskeletal_system")

HOLISTIC_DIR = Path(__file__).parent
SRC_DIR = HOLISTIC_DIR.parent
PROJECT_ROOT = SRC_DIR.parent.parent.parent.parent

MUSCLE_STATE = PROJECT_ROOT / "data" / "holistic" / "muscle_state.json"
ACTION_LOG = PROJECT_ROOT / "data" / "holistic" / "action_log.jsonl"
MYOKINE_LOG = PROJECT_ROOT / "data" / "holistic" / "myokine_log.jsonl"


ACTION_TYPES = {
    "email_sent": {"muscle_group": "outreach", "learning_value": 0.8},
    "email_drafted": {"muscle_group": "outreach", "learning_value": 0.3},
    "email_approved": {"muscle_group": "outreach", "learning_value": 0.9},
    "quote_generated": {"muscle_group": "sales", "learning_value": 0.7},
    "quote_followed_up": {"muscle_group": "sales", "learning_value": 0.6},
    "lead_researched": {"muscle_group": "intelligence", "learning_value": 0.5},
    "drip_email_sent": {"muscle_group": "outreach", "learning_value": 0.4},
    "customer_replied": {"muscle_group": "relationship", "learning_value": 1.0},
    "knowledge_ingested": {"muscle_group": "learning", "learning_value": 0.3},
    "correction_applied": {"muscle_group": "learning", "learning_value": 0.9},
    "web_search_performed": {"muscle_group": "intelligence", "learning_value": 0.4},
    "calendar_checked": {"muscle_group": "operations", "learning_value": 0.1},
    "spreadsheet_read": {"muscle_group": "operations", "learning_value": 0.2},
}

OUTCOME_TYPES = {
    "positive_reply": {"signal_strength": 1.0, "hormone": "dopamine"},
    "negative_reply": {"signal_strength": 0.8, "hormone": "cortisol"},
    "no_reply": {"signal_strength": 0.2, "hormone": "neutral"},
    "quote_accepted": {"signal_strength": 1.0, "hormone": "dopamine"},
    "quote_rejected": {"signal_strength": 0.7, "hormone": "cortisol"},
    "meeting_scheduled": {"signal_strength": 0.9, "hormone": "dopamine"},
    "unsubscribed": {"signal_strength": 0.6, "hormone": "cortisol"},
    "correction_received": {"signal_strength": 0.8, "hormone": "cortisol"},
    "approval_received": {"signal_strength": 0.9, "hormone": "dopamine"},
}


@dataclass
class ActionRecord:
    """A recorded action (muscle contraction)."""
    action_type: str
    request_id: str
    timestamp: str
    context: Dict = field(default_factory=dict)
    outcome: Optional[str] = None
    outcome_timestamp: Optional[str] = None
    learning_extracted: bool = False


@dataclass
class Myokine:
    """A learning signal produced by an action (like a myokine from muscle)."""
    source_action: str
    signal_type: str  # "pattern", "preference", "correction", "relationship"
    content: str
    strength: float
    timestamp: str
    stored_to_memory: bool = False


class MusculoskeletalSystem:
    """
    Ira's musculoskeletal system: tracks actions, their outcomes,
    and extracts learning signals (myokines) from the action-outcome loop.
    """

    def __init__(self):
        self._state = self._load_state()
        self._pending_actions: Dict[str, ActionRecord] = {}
        self._load_pending()

    def _load_state(self) -> Dict:
        MUSCLE_STATE.parent.mkdir(parents=True, exist_ok=True)
        if MUSCLE_STATE.exists():
            try:
                return json.loads(MUSCLE_STATE.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "total_actions": 0,
            "actions_by_type": {},
            "actions_by_muscle_group": {},
            "total_myokines": 0,
            "muscle_fitness": {},
            "pending_outcomes": [],
            "last_exercise": None,
        }

    def _save_state(self):
        self._state["pending_outcomes"] = [
            {
                "action_type": a.action_type,
                "request_id": a.request_id,
                "timestamp": a.timestamp,
                "context": a.context,
            }
            for a in self._pending_actions.values()
        ]
        MUSCLE_STATE.parent.mkdir(parents=True, exist_ok=True)
        MUSCLE_STATE.write_text(json.dumps(self._state, indent=2))

    def _load_pending(self):
        for item in self._state.get("pending_outcomes", []):
            rid = item.get("request_id", "")
            if rid:
                self._pending_actions[rid] = ActionRecord(
                    action_type=item.get("action_type", "unknown"),
                    request_id=rid,
                    timestamp=item.get("timestamp", ""),
                    context=item.get("context", {}),
                )

    def record_action(
        self,
        action_type: str,
        context: Optional[Dict] = None,
        request_id: Optional[str] = None,
    ) -> str:
        """
        Record an action (muscle contraction). Returns a request_id
        that can be used later to record the outcome.
        """
        import uuid
        rid = request_id or str(uuid.uuid4())[:12]
        now = datetime.now().isoformat()

        record = ActionRecord(
            action_type=action_type,
            request_id=rid,
            timestamp=now,
            context=context or {},
        )

        self._pending_actions[rid] = record

        self._state["total_actions"] = self._state.get("total_actions", 0) + 1
        type_counts = self._state.get("actions_by_type", {})
        type_counts[action_type] = type_counts.get(action_type, 0) + 1
        self._state["actions_by_type"] = type_counts

        action_info = ACTION_TYPES.get(action_type, {})
        muscle_group = action_info.get("muscle_group", "general")
        group_counts = self._state.get("actions_by_muscle_group", {})
        group_counts[muscle_group] = group_counts.get(muscle_group, 0) + 1
        self._state["actions_by_muscle_group"] = group_counts

        self._state["last_exercise"] = now

        entry = {
            "timestamp": now,
            "action_type": action_type,
            "request_id": rid,
            "muscle_group": muscle_group,
            "context": context or {},
        }
        ACTION_LOG.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(ACTION_LOG, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

        self._save_state()
        logger.info(f"[MUSCULO] Action recorded: {action_type} (id={rid})")
        return rid

    def record_action_outcome(
        self,
        request_id: str,
        outcome: str,
        context: Optional[Dict] = None,
    ) -> Optional[Myokine]:
        """
        Record the outcome of a previous action. This is where
        the learning signal (myokine) is generated.
        """
        action = self._pending_actions.get(request_id)
        if not action:
            logger.warning(f"[MUSCULO] No pending action for {request_id}")
            return None

        action.outcome = outcome
        action.outcome_timestamp = datetime.now().isoformat()

        myokine = self._generate_myokine(action, outcome, context)

        if myokine:
            self._store_myokine(myokine)
            self._signal_endocrine(action, outcome)

        del self._pending_actions[request_id]

        self._update_muscle_fitness(action.action_type, outcome)
        self._save_state()

        return myokine

    def _generate_myokine(
        self,
        action: ActionRecord,
        outcome: str,
        context: Optional[Dict],
    ) -> Optional[Myokine]:
        """Generate a learning signal from an action-outcome pair."""
        outcome_info = OUTCOME_TYPES.get(outcome, {})
        action_info = ACTION_TYPES.get(action.action_type, {})

        strength = (
            outcome_info.get("signal_strength", 0.5)
            * action_info.get("learning_value", 0.5)
        )

        if strength < 0.1:
            return None

        if outcome in ("positive_reply", "quote_accepted", "meeting_scheduled", "approval_received"):
            signal_type = "pattern"
            content = (
                f"Successful {action.action_type}: "
                f"{json.dumps(action.context)[:200]} -> {outcome}"
            )
        elif outcome in ("negative_reply", "quote_rejected", "correction_received"):
            signal_type = "correction"
            content = (
                f"Failed {action.action_type}: "
                f"{json.dumps(action.context)[:200]} -> {outcome}. "
                f"Additional context: {json.dumps(context or {})[:200]}"
            )
        elif outcome == "unsubscribed":
            signal_type = "preference"
            content = (
                f"Contact opted out after {action.action_type}: "
                f"{json.dumps(action.context)[:200]}"
            )
        else:
            signal_type = "observation"
            content = (
                f"{action.action_type} -> {outcome}: "
                f"{json.dumps(action.context)[:200]}"
            )

        return Myokine(
            source_action=action.action_type,
            signal_type=signal_type,
            content=content,
            strength=strength,
            timestamp=datetime.now().isoformat(),
        )

    def _store_myokine(self, myokine: Myokine):
        """Store a myokine (learning signal) for dream mode to process."""
        entry = {
            "timestamp": myokine.timestamp,
            "source_action": myokine.source_action,
            "signal_type": myokine.signal_type,
            "content": myokine.content,
            "strength": myokine.strength,
        }
        MYOKINE_LOG.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(MYOKINE_LOG, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

        self._state["total_myokines"] = self._state.get("total_myokines", 0) + 1
        logger.info(
            f"[MUSCULO] Myokine generated: {myokine.signal_type} "
            f"(strength={myokine.strength:.2f})"
        )

    def _signal_endocrine(self, action: ActionRecord, outcome: str):
        """Forward the outcome signal to the endocrine system."""
        try:
            from openclaw.agents.ira.src.holistic.endocrine_system import get_endocrine_system
            endo = get_endocrine_system()

            outcome_info = OUTCOME_TYPES.get(outcome, {})
            hormone = outcome_info.get("hormone", "neutral")

            agents_involved = self._infer_agents(action.action_type)
            for agent in agents_involved:
                if hormone == "dopamine":
                    endo.signal_success(agent, context={"action": action.action_type, "outcome": outcome})
                elif hormone == "cortisol":
                    endo.signal_failure(agent, context={"action": action.action_type, "outcome": outcome})
        except Exception as e:
            logger.debug(f"[MUSCULO] Endocrine signal failed: {e}")

    def _infer_agents(self, action_type: str) -> List[str]:
        """Infer which agents were involved in an action."""
        mapping = {
            "email_sent": ["calliope", "athena"],
            "email_drafted": ["calliope"],
            "email_approved": ["calliope", "vera"],
            "quote_generated": ["clio", "calliope"],
            "lead_researched": ["iris", "clio"],
            "web_search_performed": ["iris"],
            "correction_applied": ["sophia"],
            "knowledge_ingested": ["clio"],
        }
        return mapping.get(action_type, ["athena"])

    def _update_muscle_fitness(self, action_type: str, outcome: str):
        """Update fitness score for the muscle group used."""
        action_info = ACTION_TYPES.get(action_type, {})
        muscle_group = action_info.get("muscle_group", "general")
        fitness = self._state.get("muscle_fitness", {})

        current = fitness.get(muscle_group, 0.5)
        outcome_info = OUTCOME_TYPES.get(outcome, {})
        hormone = outcome_info.get("hormone", "neutral")

        if hormone == "dopamine":
            current = min(current + 0.05, 1.0)
        elif hormone == "cortisol":
            current = max(current - 0.03, 0.0)

        fitness[muscle_group] = round(current, 3)
        self._state["muscle_fitness"] = fitness

    def get_exercise_report(self) -> Dict:
        """Get muscle system status for vital signs."""
        fitness = self._state.get("muscle_fitness", {})
        actions_by_group = self._state.get("actions_by_muscle_group", {})

        atrophied = [
            group for group, score in fitness.items() if score < 0.3
        ]
        strong = [
            group for group, score in fitness.items() if score > 0.7
        ]

        total_actions = self._state.get("total_actions", 0)
        total_myokines = self._state.get("total_myokines", 0)
        learning_rate = total_myokines / max(total_actions, 1)

        return {
            "total_actions": total_actions,
            "total_myokines": total_myokines,
            "learning_rate": round(learning_rate, 3),
            "muscle_fitness": fitness,
            "atrophied_groups": atrophied,
            "strong_groups": strong,
            "actions_by_type": self._state.get("actions_by_type", {}),
            "pending_outcomes": len(self._pending_actions),
            "last_exercise": self._state.get("last_exercise"),
        }

    def get_unprocessed_myokines(self, limit: int = 50) -> List[Dict]:
        """Get recent myokines for dream mode to process into long-term memory."""
        myokines = []
        if MYOKINE_LOG.exists():
            try:
                lines = MYOKINE_LOG.read_text().strip().split("\n")
                for line in lines[-limit:]:
                    if line.strip():
                        myokines.append(json.loads(line))
            except Exception:
                pass
        return myokines


_instance: Optional[MusculoskeletalSystem] = None


def get_musculoskeletal_system() -> MusculoskeletalSystem:
    global _instance
    if _instance is None:
        _instance = MusculoskeletalSystem()
    return _instance
