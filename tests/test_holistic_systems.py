#!/usr/bin/env python3
"""
Acceptance Tests for Holistic Body Systems
============================================

Maps to the Manus AI roadmap acceptance criteria:

Phase 1 (Immune):
    1.1 - Issue frequency tracking with count and last_seen
    1.2 - Auto-remediation module with reingest, guardrail, alert functions
    1.3 - Remediation triggers at count >= 3
    1.4 - AM thickness specifically remediated

Phase 2 (Respiratory):
    2.1 - Heartbeat recording
    2.2 - Dream mode health logging
    2.3 - Vital signs report generation
    2.4 - Telegram-formatted output

Phase 3 (Endocrine):
    3.1 - All agents scoreable (including Iris, Sophia)
    3.2 - Positive reinforcement works
    3.3 - Scores influence agent selection

Phase 4 (Musculoskeletal):
    4.1 - Action recording
    4.2 - Learning events from actions (myokines)
    4.3 - Myokines available for dream mode

Phase 5 (Sensory):
    5.1 - Cross-channel perception recording
    5.2 - Contact context integration
    5.3 - Channel health reporting

Phase 6 (Metabolic):
    6.1 - Knowledge base scanning (Qdrant + files)
    6.2 - Active cleanup cycle
    6.3 - Integration into dream mode
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# PHASE 1: IMMUNE SYSTEM
# =============================================================================

class TestImmuneSystem:
    """Acceptance criteria for Phase 1 (Immune System)."""

    def setup_method(self):
        """Fresh immune system for each test."""
        from openclaw.agents.ira.src.holistic.immune_system import ImmuneSystem
        self.immune = ImmuneSystem()
        self.immune._chronic_issues = {}
        self.immune._state = {
            "chronic_issues": {},
            "total_remediations": 0,
            "total_blocks": 0,
            "last_sweep": None,
        }

    def test_1_1_issue_frequency_tracking(self):
        """1.1: Issues must track count and last_seen."""
        warnings = ["Business rule violation: AM Series Thickness Limit"]

        self.immune.process_validation_issue("test query", "test response", warnings)
        self.immune.process_validation_issue("test query 2", "test response 2", warnings)

        assert "am_thickness" in self.immune._chronic_issues
        issue = self.immune._chronic_issues["am_thickness"]
        assert issue.occurrence_count == 2
        assert issue.last_seen is not None
        assert issue.first_seen is not None
        assert len(issue.sample_queries) >= 1

    def test_1_2_remediation_module_exists(self):
        """1.2: Auto-remediation module has known remediations."""
        assert "am_thickness" in self.immune.KNOWN_REMEDIATIONS
        assert "price_placeholder" in self.immune.KNOWN_REMEDIATIONS
        assert "vague_pricing" in self.immune.KNOWN_REMEDIATIONS

        for key, rem in self.immune.KNOWN_REMEDIATIONS.items():
            assert "correct_fact" in rem
            assert "mem0_user_id" in rem
            assert "guardrail_pattern" in rem

    def test_1_3_remediation_triggers_at_count_3(self):
        """1.3: Auto-remediation triggers when count >= 3."""
        warnings = ["Business rule violation: AM Series Thickness Limit"]

        action1 = self.immune.process_validation_issue("q1", "r1", warnings)
        assert action1.escalation_level == 1

        action2 = self.immune.process_validation_issue("q2", "r2", warnings)
        assert action2.escalation_level == 2

        with patch("openclaw.agents.ira.src.holistic.immune_system.ImmuneSystem._attempt_remediation", return_value="mem0_reinforcement"):
            action3 = self.immune.process_validation_issue("q3", "r3", warnings)
        assert action3.escalation_level == 3

    def test_1_3_blocking_at_count_5(self):
        """1.3 extended: Responses blocked at count >= 5."""
        warnings = ["Business rule violation: AM Series Thickness Limit"]

        for i in range(5):
            action = self.immune.process_validation_issue(f"q{i}", f"r{i}", warnings)

        assert action.blocked is True
        assert action.escalation_level == 5
        assert action.override_response is not None

    def test_1_4_am_thickness_specific_remediation(self):
        """1.4: AM thickness has a specific remediation rule."""
        rem = self.immune.KNOWN_REMEDIATIONS["am_thickness"]
        assert "1.5mm" in rem["correct_fact"]
        assert "PF1" in rem["correct_fact"]
        assert rem["mem0_user_id"] == "machinecraft_knowledge"

    def test_inflammation_report(self):
        """Inflammation report correctly summarizes chronic issues."""
        warnings = ["Business rule violation: AM Series Thickness Limit"]
        for i in range(6):
            self.immune.process_validation_issue(f"q{i}", f"r{i}", warnings)

        report = self.immune.get_inflammation_report()
        assert report["inflammation_level"] == "critical"
        assert report["active_issues"] >= 1
        assert "am_thickness" in report["critical_issues"]


# =============================================================================
# PHASE 2: RESPIRATORY SYSTEM
# =============================================================================

class TestRespiratorySystem:
    """Acceptance criteria for Phase 2 (Respiratory System)."""

    def setup_method(self):
        from openclaw.agents.ira.src.holistic.respiratory_system import RespiratorySystem
        self.resp = RespiratorySystem()
        self.resp._state = {
            "last_heartbeat": None,
            "heartbeat_count": 0,
            "today": None,
            "daily_rhythms": {},
            "consecutive_heartbeats": 0,
            "longest_gap_s": 0,
        }

    def test_2_1_heartbeat_recording(self):
        """2.1: Heartbeat records alive status."""
        result = self.resp.record_heartbeat()
        assert result["alive"] is True
        assert self.resp._state["heartbeat_count"] == 1
        assert self.resp._state["last_heartbeat"] is not None

    def test_2_1_heartbeat_gap_detection(self):
        """2.1: Heartbeat detects gaps."""
        from datetime import datetime, timedelta
        old_time = (datetime.now() - timedelta(hours=1)).isoformat()
        self.resp._state["last_heartbeat"] = old_time

        result = self.resp.record_heartbeat()
        assert result["gap_detected"] is True
        assert result["gap_seconds"] > 3000

    def test_2_2_dream_mode_health_logging(self):
        """2.2: Dream mode completion is recorded."""
        self.resp.record_heartbeat()  # ensure daily rhythm exists
        self.resp.record_dream_mode(completed=True, duration_s=120.5)

        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        rhythm = self.resp._state["daily_rhythms"].get(today, {})
        assert rhythm["dream_mode_ran"] is True
        assert rhythm["dream_mode_completed"] is True
        assert rhythm["dream_mode_duration_s"] == 120.5

    def test_2_3_vital_signs_report(self):
        """2.3: Vital signs report has all required fields."""
        report = self.resp.get_rhythm_report()
        assert "heartbeat" in report
        assert "today" in report
        assert "hrv" in report
        assert "dream_streak" in report

    def test_2_3_breath_recording_and_hrv(self):
        """2.3: Breath recording feeds HRV calculation."""
        for i in range(10):
            self.resp.record_breath(
                request_id=f"req_{i}",
                total_latency_ms=500 + (i * 50),
                success=True,
                channel="telegram",
            )

        hrv = self.resp.calculate_hrv()
        assert hrv["hrv"] is not None
        assert hrv["sample_size"] == 10
        assert hrv["status"] in ("very_stable", "healthy", "variable", "unstable")

    def test_arrhythmia_detection(self):
        """Arrhythmia detection catches missing dream mode."""
        from datetime import datetime
        yesterday = (datetime.now() - __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%d")
        self.resp._state["daily_rhythms"] = {
            yesterday: {"dream_mode_completed": False}
        }

        issues = self.resp.check_arrhythmia()
        assert any("Dream mode" in i for i in issues)


# =============================================================================
# PHASE 3: ENDOCRINE SYSTEM
# =============================================================================

class TestEndocrineSystem:
    """Acceptance criteria for Phase 3 (Endocrine System)."""

    def setup_method(self):
        from openclaw.agents.ira.src.holistic.endocrine_system import EndocrineSystem
        self.endo = EndocrineSystem()
        self.endo._profiles = {}
        for name in ["athena", "clio", "calliope", "vera", "iris", "sophia"]:
            from openclaw.agents.ira.src.holistic.endocrine_system import AgentProfile
            self.endo._profiles[name] = AgentProfile(name=name)

    def test_3_1_all_agents_scoreable(self):
        """3.1: All agents including Iris and Sophia can be scored."""
        for name in ["athena", "clio", "calliope", "vera", "iris", "sophia"]:
            self.endo.signal_success(name)
            profile = self.endo._profiles[name]
            assert profile.successes == 1
            assert profile.score > 0.7

    def test_3_1_iris_sophia_scoring(self):
        """3.1: Iris and Sophia specifically get scored."""
        self.endo.signal_success("iris", specialty="lead_research")
        self.endo.signal_failure("sophia", context={"issue": "weak reflection"})

        assert self.endo._profiles["iris"].successes == 1
        assert self.endo._profiles["iris"].score > 0.7
        assert self.endo._profiles["sophia"].failures == 1
        assert self.endo._profiles["sophia"].score < 0.7

    def test_3_2_positive_reinforcement(self):
        """3.2: Positive feedback increases scores with streak bonus."""
        initial = self.endo._profiles["clio"].score
        for _ in range(5):
            self.endo.signal_success("clio")

        assert self.endo._profiles["clio"].score > initial
        assert self.endo._profiles["clio"].streak == 5
        assert self.endo._profiles["clio"].stress_level == 0.0

    def test_3_2_negative_reinforcement_with_stress(self):
        """3.2: Negative feedback decreases scores and accumulates stress."""
        initial = self.endo._profiles["calliope"].score
        for _ in range(4):
            self.endo.signal_failure("calliope")

        assert self.endo._profiles["calliope"].score < initial
        assert self.endo._profiles["calliope"].streak == -4
        assert self.endo._profiles["calliope"].stress_level > 0

    def test_3_3_scores_influence_selection(self):
        """3.3: Higher-scoring agents are preferred for tasks."""
        self.endo._profiles["clio"].score = 0.9
        self.endo._profiles["iris"].score = 0.6

        preferred = self.endo.select_preferred_agent(["clio", "iris"], task="research")
        assert preferred == "clio"

    def test_3_3_specialty_bonus_in_selection(self):
        """3.3: Specialty bonus can override raw score."""
        self.endo._profiles["iris"].score = 0.65
        self.endo._profiles["iris"].specialties = {"lead_research": 0.95}
        self.endo._profiles["clio"].score = 0.7

        preferred = self.endo.select_preferred_agent(
            ["clio", "iris"], task="lead_research"
        )
        assert preferred == "iris"

    def test_chronic_stress_detection(self):
        """Chronic stress is detected after repeated failures."""
        for _ in range(5):
            self.endo.signal_failure("vera")

        assert self.endo.is_agent_stressed("vera") is True
        report = self.endo.get_endocrine_report()
        assert "vera" in report["stressed_agents"]


# =============================================================================
# PHASE 4: MUSCULOSKELETAL SYSTEM
# =============================================================================

class TestMusculoskeletalSystem:
    """Acceptance criteria for Phase 4 (Musculoskeletal System)."""

    def setup_method(self):
        from openclaw.agents.ira.src.holistic.musculoskeletal_system import MusculoskeletalSystem
        self.musculo = MusculoskeletalSystem()
        self.musculo._state = {
            "total_actions": 0,
            "actions_by_type": {},
            "actions_by_muscle_group": {},
            "total_myokines": 0,
            "muscle_fitness": {},
            "pending_outcomes": [],
            "last_exercise": None,
        }
        self.musculo._pending_actions = {}

    def test_4_1_action_recording(self):
        """4.1: Actions are recorded with type and context."""
        rid = self.musculo.record_action(
            "email_sent",
            context={"to": "customer@example.com", "subject": "Quote"},
        )
        assert rid is not None
        assert self.musculo._state["total_actions"] == 1
        assert "email_sent" in self.musculo._state["actions_by_type"]
        assert rid in self.musculo._pending_actions

    def test_4_2_learning_events_from_outcomes(self):
        """4.2: Action outcomes generate myokines (learning signals)."""
        rid = self.musculo.record_action("email_sent", context={"to": "test"})

        with patch("openclaw.agents.ira.src.holistic.musculoskeletal_system.MusculoskeletalSystem._signal_endocrine"):
            myokine = self.musculo.record_action_outcome(
                rid, "positive_reply", context={"reply": "Interested!"}
            )

        assert myokine is not None
        assert myokine.signal_type == "pattern"
        assert myokine.strength > 0
        assert self.musculo._state["total_myokines"] == 1

    def test_4_2_negative_outcome_generates_correction(self):
        """4.2: Negative outcomes generate correction-type myokines."""
        rid = self.musculo.record_action("email_sent", context={"to": "test"})

        with patch("openclaw.agents.ira.src.holistic.musculoskeletal_system.MusculoskeletalSystem._signal_endocrine"):
            myokine = self.musculo.record_action_outcome(
                rid, "negative_reply", context={"reply": "Not interested"}
            )

        assert myokine is not None
        assert myokine.signal_type == "correction"

    def test_4_3_myokines_available_for_dream(self):
        """4.3: Unprocessed myokines can be retrieved for dream mode."""
        myokines = self.musculo.get_unprocessed_myokines(limit=10)
        assert isinstance(myokines, list)

    def test_exercise_report(self):
        """Exercise report shows muscle fitness."""
        self.musculo.record_action("email_sent")
        self.musculo.record_action("lead_researched")

        report = self.musculo.get_exercise_report()
        assert report["total_actions"] == 2
        assert "actions_by_type" in report
        assert "muscle_fitness" in report


# =============================================================================
# PHASE 5: SENSORY SYSTEM
# =============================================================================

class TestSensorySystem:
    """Acceptance criteria for Phase 5 (Sensory System)."""

    def setup_method(self):
        from openclaw.agents.ira.src.holistic.sensory_system import SensoryIntegrator
        self.sensory = SensoryIntegrator()
        self.sensory._state = {
            "total_perceptions": 0,
            "channel_stats": {},
            "contact_summaries": {},
            "cross_channel_events": 0,
        }
        self.sensory._contact_contexts = {}
        from collections import defaultdict
        self.sensory._channel_stats = defaultdict(lambda: {
            "total_perceptions": 0,
            "last_active": None,
        })

    def test_5_1_cross_channel_perception(self):
        """5.1: Perceptions from different channels are recorded."""
        self.sensory.record_perception(
            "telegram", "user_123", "Hello from Telegram"
        )
        self.sensory.record_perception(
            "email", "user_123", "Hello from Email"
        )

        assert self.sensory._state["total_perceptions"] == 2
        assert self.sensory._channel_stats["telegram"]["total_perceptions"] == 1
        assert self.sensory._channel_stats["email"]["total_perceptions"] == 1

    def test_5_2_contact_context_integration(self):
        """5.2: Same contact across channels is integrated."""
        self.sensory.record_perception(
            "telegram", "mike_chen", "Interested in PF1"
        )
        notes = self.sensory.record_perception(
            "email", "mike_chen", "Formal quote request"
        )

        assert notes is not None
        assert any("Cross-channel" in n for n in notes)

        context = self.sensory.get_integrated_context("mike_chen")
        assert context["known"] is True
        assert context["is_multi_channel"] is True
        assert "telegram" in context["channels_active"]
        assert "email" in context["channels_active"]

    def test_5_3_channel_health(self):
        """5.3: Channel health is reported correctly."""
        self.sensory.record_perception("telegram", None, "test")

        health = self.sensory.get_channel_health()
        assert "telegram" in health
        assert health["telegram"]["status"] == "active"
        assert health["iris_intelligence"]["status"] == "dormant"

    def test_sentiment_tracking(self):
        """Sentiment trajectory is tracked across interactions."""
        for sentiment in ["positive", "positive", "negative", "negative", "negative"]:
            self.sensory.record_perception(
                "telegram", "user_x", "msg", sentiment=sentiment
            )

        context = self.sensory.get_integrated_context("user_x")
        assert context["sentiment_trajectory"] == [
            "positive", "positive", "negative", "negative", "negative"
        ]


# =============================================================================
# PHASE 6: METABOLIC SYSTEM
# =============================================================================

class TestMetabolicSystem:
    """Acceptance criteria for Phase 6 (Metabolic System)."""

    def setup_method(self):
        from openclaw.agents.ira.src.holistic.metabolic_system import MetabolicSystem
        self.metabolic = MetabolicSystem()
        self.metabolic._state = {
            "last_cleanup": None,
            "total_cleanups": 0,
            "total_items_cleaned": 0,
            "total_contradictions_found": 0,
            "knowledge_stats": {},
        }

    def test_6_1_contradiction_detection(self):
        """6.1: Contradictions in knowledge texts are detected."""
        texts = [
            "The AM series handles materials ≤1.5mm thickness",
            "The AM series can handle materials ≤2mm thickness",
            "Batelaan is closed permanently",
            "Batelaan is operational and a key customer",
        ]

        contradictions = self.metabolic.detect_contradictions(texts)
        assert len(contradictions) >= 2

    def test_6_2_cleanup_cycle_runs(self):
        """6.2: Cleanup cycle executes all operations."""
        results = self.metabolic.run_cleanup_cycle()

        assert "validation_cleanup" in results
        assert "knowledge_audit" in results
        assert "feedback_hygiene" in results
        assert "state_consistency" in results
        assert "qdrant_hygiene" in results

        assert self.metabolic._state["total_cleanups"] == 1
        assert self.metabolic._state["last_cleanup"] is not None

    def test_6_2_metabolic_report(self):
        """6.2: Metabolic report shows health status."""
        report = self.metabolic.get_metabolic_report()
        assert "health" in report
        assert "last_cleanup" in report
        assert "cleanup_overdue" in report


# =============================================================================
# VITAL SIGNS (Cross-system integration)
# =============================================================================

class TestVitalSigns:
    """Test the unified vital signs collection."""

    def test_vital_signs_format(self):
        """Vital signs report has all system sections."""
        from openclaw.agents.ira.src.holistic.vital_signs import collect_vital_signs
        report = collect_vital_signs()

        assert "overall_health" in report
        assert "overall_score" in report
        assert "system_scores" in report
        assert "immune" in report
        assert "respiratory" in report
        assert "endocrine" in report
        assert "musculoskeletal" in report
        assert "sensory" in report
        assert "metabolic" in report
        assert "alerts" in report
        assert "recommendations" in report

    def test_telegram_formatting(self):
        """Telegram format produces readable output."""
        from openclaw.agents.ira.src.holistic.vital_signs import (
            collect_vital_signs,
            format_vitals_telegram,
        )
        report = collect_vital_signs()
        formatted = format_vitals_telegram(report)

        assert "VITAL SIGNS" in formatted
        assert "Immune" in formatted
        assert "Respiratory" in formatted
        assert len(formatted) > 100
