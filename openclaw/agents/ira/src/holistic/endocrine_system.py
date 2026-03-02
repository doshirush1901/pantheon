#!/usr/bin/env python3
"""
ENDOCRINE SYSTEM - Agent Scoring with Bidirectional Reinforcement
==================================================================

Biological parallel:
    Hormones modulate learning. Cortisol helps memory acutely but destroys
    it chronically. Dopamine drives reward-based learning. The endocrine
    system's power is in its dual nature.

Ira parallel:
    agent_scores.json exists but is barely active. Iris and Sophia have
    never been scored. There's no positive reinforcement signal. Scores
    don't influence behavior. This module makes the endocrine system
    actually regulate Ira's cognitive behavior.

Key improvements over existing feedback_handler.py:
    1. Bidirectional: both positive AND negative signals are strong
    2. Scores influence behavior: agent selection, confidence thresholds
    3. Decay: unused agents' scores drift toward baseline (use it or lose it)
    4. Cortisol model: acute stress (single failure) is a learning signal,
       chronic stress (repeated failures) triggers protective measures

Usage:
    from holistic.endocrine_system import get_endocrine_system

    endo = get_endocrine_system()
    endo.signal_success("clio", context={"query_type": "pricing"})
    endo.signal_failure("calliope", context={"issue": "wrong tone"})
    confidence = endo.get_agent_confidence("vera")
    preferred = endo.select_preferred_agent(["clio", "iris"], task="research")
"""

import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("ira.endocrine_system")

HOLISTIC_DIR = Path(__file__).parent
SRC_DIR = HOLISTIC_DIR.parent
PROJECT_ROOT = SRC_DIR.parent.parent.parent.parent

ENDOCRINE_STATE = PROJECT_ROOT / "data" / "holistic" / "endocrine_state.json"
HORMONE_LOG = PROJECT_ROOT / "data" / "holistic" / "hormone_log.jsonl"

LEGACY_SCORES_FILE = PROJECT_ROOT / "openclaw" / "data" / "learned_lessons" / "agent_scores.json"


@dataclass
class AgentProfile:
    """Extended agent profile with endocrine-style regulation."""
    name: str
    score: float = 0.7
    successes: int = 0
    failures: int = 0
    total_invocations: int = 0
    last_invoked: Optional[str] = None
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    streak: int = 0  # positive = success streak, negative = failure streak
    stress_level: float = 0.0  # 0-1, chronic failure accumulation
    specialties: Dict[str, float] = field(default_factory=dict)


class EndocrineSystem:
    """
    Ira's endocrine system: regulates agent behavior through
    bidirectional scoring, stress modeling, and preference selection.
    """

    BASELINE_SCORE = 0.7
    MIN_SCORE = 0.1
    MAX_SCORE = 1.0

    SUCCESS_BOOST = 0.03
    FAILURE_PENALTY = 0.04
    STREAK_MULTIPLIER = 0.01  # additional per streak length

    STRESS_ACCUMULATION = 0.15  # per failure
    STRESS_DECAY = 0.05  # per success or per day
    STRESS_THRESHOLD = 0.6  # above this, agent is "chronically stressed"

    INACTIVITY_DECAY_DAYS = 7
    INACTIVITY_DECAY_RATE = 0.01  # per day toward baseline

    def __init__(self):
        self._profiles: Dict[str, AgentProfile] = {}
        self._load_state()

    def _load_state(self):
        ENDOCRINE_STATE.parent.mkdir(parents=True, exist_ok=True)

        if ENDOCRINE_STATE.exists():
            try:
                data = json.loads(ENDOCRINE_STATE.read_text())
                for name, pdata in data.get("profiles", {}).items():
                    self._profiles[name] = AgentProfile(
                        name=name,
                        score=pdata.get("score", self.BASELINE_SCORE),
                        successes=pdata.get("successes", 0),
                        failures=pdata.get("failures", 0),
                        total_invocations=pdata.get("total_invocations", 0),
                        last_invoked=pdata.get("last_invoked"),
                        last_success=pdata.get("last_success"),
                        last_failure=pdata.get("last_failure"),
                        streak=pdata.get("streak", 0),
                        stress_level=pdata.get("stress_level", 0.0),
                        specialties=pdata.get("specialties", {}),
                    )
                return
            except (json.JSONDecodeError, IOError):
                pass

        if LEGACY_SCORES_FILE.exists():
            try:
                legacy = json.loads(LEGACY_SCORES_FILE.read_text())
                for name, data in legacy.items():
                    self._profiles[name] = AgentProfile(
                        name=name,
                        score=data.get("score", self.BASELINE_SCORE),
                        successes=data.get("successes", 0),
                        failures=data.get("failures", 0),
                        total_invocations=data.get("successes", 0) + data.get("failures", 0),
                    )
                logger.info(f"[ENDOCRINE] Migrated {len(self._profiles)} agents from legacy scores")
            except (json.JSONDecodeError, IOError):
                pass

        for name in ["athena", "clio", "calliope", "vera", "iris", "sophia"]:
            if name not in self._profiles:
                self._profiles[name] = AgentProfile(name=name)

    def _save_state(self):
        data = {
            "profiles": {
                name: {
                    "score": round(p.score, 4),
                    "successes": p.successes,
                    "failures": p.failures,
                    "total_invocations": p.total_invocations,
                    "last_invoked": p.last_invoked,
                    "last_success": p.last_success,
                    "last_failure": p.last_failure,
                    "streak": p.streak,
                    "stress_level": round(p.stress_level, 4),
                    "specialties": {k: round(v, 3) for k, v in p.specialties.items()},
                }
                for name, p in self._profiles.items()
            },
            "last_updated": datetime.now().isoformat(),
        }
        ENDOCRINE_STATE.parent.mkdir(parents=True, exist_ok=True)
        ENDOCRINE_STATE.write_text(json.dumps(data, indent=2))

        self._sync_legacy_scores()

    def _sync_legacy_scores(self):
        """Keep legacy agent_scores.json in sync for backward compatibility."""
        legacy = {}
        for name, p in self._profiles.items():
            legacy[name] = {
                "score": round(p.score, 2),
                "successes": p.successes,
                "failures": p.failures,
            }
        try:
            LEGACY_SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
            LEGACY_SCORES_FILE.write_text(json.dumps(legacy, indent=2))
        except Exception as e:
            logger.warning(f"[ENDOCRINE] Failed to sync legacy scores: {e}")

    def signal_success(
        self,
        agent_name: str,
        context: Optional[Dict] = None,
        specialty: Optional[str] = None,
    ):
        """
        Dopamine signal: agent performed well.
        Boosts score, extends streak, reduces stress, updates specialty.
        """
        profile = self._ensure_profile(agent_name)
        now = datetime.now().isoformat()

        profile.successes += 1
        profile.total_invocations += 1
        profile.last_invoked = now
        profile.last_success = now

        if profile.streak >= 0:
            profile.streak += 1
        else:
            profile.streak = 1

        streak_bonus = min(abs(profile.streak) * self.STREAK_MULTIPLIER, 0.05)
        boost = self.SUCCESS_BOOST + streak_bonus
        profile.score = min(profile.score + boost, self.MAX_SCORE)

        profile.stress_level = max(profile.stress_level - self.STRESS_DECAY, 0)

        if specialty:
            old = profile.specialties.get(specialty, 0.5)
            profile.specialties[specialty] = min(old + 0.05, 1.0)

        self._log_hormone("dopamine", agent_name, boost, context)
        self._save_state()

        logger.info(
            f"[ENDOCRINE] {agent_name} success: score={profile.score:.3f} "
            f"streak={profile.streak} stress={profile.stress_level:.2f}"
        )

    def signal_failure(
        self,
        agent_name: str,
        context: Optional[Dict] = None,
        specialty: Optional[str] = None,
    ):
        """
        Cortisol signal: agent performed poorly.
        Acute failure is a learning signal. Chronic failure triggers protection.
        """
        profile = self._ensure_profile(agent_name)
        now = datetime.now().isoformat()

        profile.failures += 1
        profile.total_invocations += 1
        profile.last_invoked = now
        profile.last_failure = now

        if profile.streak <= 0:
            profile.streak -= 1
        else:
            profile.streak = -1

        streak_penalty = min(abs(profile.streak) * self.STREAK_MULTIPLIER, 0.05)
        penalty = self.FAILURE_PENALTY + streak_penalty
        profile.score = max(profile.score - penalty, self.MIN_SCORE)

        profile.stress_level = min(
            profile.stress_level + self.STRESS_ACCUMULATION, 1.0
        )

        if specialty:
            old = profile.specialties.get(specialty, 0.5)
            profile.specialties[specialty] = max(old - 0.08, 0.0)

        if profile.stress_level >= self.STRESS_THRESHOLD:
            logger.warning(
                f"[ENDOCRINE] {agent_name} is chronically stressed "
                f"(stress={profile.stress_level:.2f}). Consider intervention."
            )

        self._log_hormone("cortisol", agent_name, -penalty, context)
        self._save_state()

        logger.info(
            f"[ENDOCRINE] {agent_name} failure: score={profile.score:.3f} "
            f"streak={profile.streak} stress={profile.stress_level:.2f}"
        )

    def signal_invocation(self, agent_name: str):
        """Record that an agent was invoked (regardless of outcome)."""
        profile = self._ensure_profile(agent_name)
        profile.total_invocations += 1
        profile.last_invoked = datetime.now().isoformat()
        self._save_state()

    def get_agent_confidence(self, agent_name: str) -> float:
        """
        Get effective confidence for an agent, factoring in stress.
        Chronically stressed agents have reduced effective confidence.
        """
        profile = self._ensure_profile(agent_name)
        stress_penalty = profile.stress_level * 0.2
        return max(profile.score - stress_penalty, self.MIN_SCORE)

    def select_preferred_agent(
        self,
        candidates: List[str],
        task: Optional[str] = None,
    ) -> str:
        """
        Select the best agent for a task based on scores and specialties.
        This is how scores actually influence behavior.
        """
        if not candidates:
            return "athena"

        best_agent = candidates[0]
        best_score = -1.0

        for name in candidates:
            profile = self._ensure_profile(name)
            effective = self.get_agent_confidence(name)

            if task and task in profile.specialties:
                effective += profile.specialties[task] * 0.2

            if effective > best_score:
                best_score = effective
                best_agent = name

        return best_agent

    def is_agent_stressed(self, agent_name: str) -> bool:
        """Check if an agent is chronically stressed."""
        profile = self._ensure_profile(agent_name)
        return profile.stress_level >= self.STRESS_THRESHOLD

    def apply_inactivity_decay(self):
        """
        Apply decay to agents that haven't been used recently.
        Scores drift toward baseline -- use it or lose it.
        Called by the respiratory system's daily rhythm.
        """
        now = datetime.now()
        decayed = []

        for name, profile in self._profiles.items():
            if not profile.last_invoked:
                continue
            try:
                last = datetime.fromisoformat(profile.last_invoked)
                days_inactive = (now - last).days
                if days_inactive >= self.INACTIVITY_DECAY_DAYS:
                    decay_amount = (days_inactive - self.INACTIVITY_DECAY_DAYS + 1) * self.INACTIVITY_DECAY_RATE
                    if profile.score > self.BASELINE_SCORE:
                        profile.score = max(profile.score - decay_amount, self.BASELINE_SCORE)
                        decayed.append(f"{name}: -{decay_amount:.3f}")
                    elif profile.score < self.BASELINE_SCORE:
                        profile.score = min(profile.score + decay_amount * 0.5, self.BASELINE_SCORE)
                        decayed.append(f"{name}: +{decay_amount * 0.5:.3f}")

                    profile.stress_level = max(profile.stress_level - self.STRESS_DECAY, 0)
            except (ValueError, TypeError):
                continue

        if decayed:
            logger.info(f"[ENDOCRINE] Inactivity decay applied: {', '.join(decayed)}")
            self._save_state()

        return decayed

    def get_endocrine_report(self) -> Dict:
        """Get full endocrine system status for vital signs."""
        profiles_summary = {}
        for name, p in self._profiles.items():
            profiles_summary[name] = {
                "score": round(p.score, 3),
                "effective_confidence": round(self.get_agent_confidence(name), 3),
                "stress_level": round(p.stress_level, 3),
                "streak": p.streak,
                "total_invocations": p.total_invocations,
                "success_rate": (
                    round(p.successes / max(p.total_invocations, 1), 3)
                ),
                "last_invoked": p.last_invoked,
                "chronically_stressed": self.is_agent_stressed(name),
                "top_specialties": dict(
                    sorted(p.specialties.items(), key=lambda x: -x[1])[:3]
                ),
            }

        stressed_agents = [
            name for name, p in self._profiles.items()
            if self.is_agent_stressed(name)
        ]
        avg_score = (
            sum(p.score for p in self._profiles.values()) / len(self._profiles)
            if self._profiles else 0
        )

        return {
            "overall_health": (
                "critical" if len(stressed_agents) >= 3 else
                "stressed" if stressed_agents else
                "healthy"
            ),
            "avg_score": round(avg_score, 3),
            "stressed_agents": stressed_agents,
            "profiles": profiles_summary,
        }

    def _ensure_profile(self, name: str) -> AgentProfile:
        if name not in self._profiles:
            self._profiles[name] = AgentProfile(name=name)
        return self._profiles[name]

    def _log_hormone(
        self, hormone: str, agent: str, delta: float, context: Optional[Dict]
    ):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "hormone": hormone,
            "agent": agent,
            "delta": round(delta, 4),
            "context": context or {},
        }
        HORMONE_LOG.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(HORMONE_LOG, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass


_instance: Optional[EndocrineSystem] = None


def get_endocrine_system() -> EndocrineSystem:
    global _instance
    if _instance is None:
        _instance = EndocrineSystem()
    return _instance
