#!/usr/bin/env python3
"""
IMMUNE SYSTEM - Auto-Remediation of Chronic Knowledge Issues
=============================================================

Biological parallel:
    Microglia prune bad synapses. Cytokines regulate synaptic strength.
    Chronic inflammation (unresolved issues) is neurotoxic.

Ira parallel:
    The knowledge_health monitor DETECTS issues but doesn't RESOLVE them.
    The same AM thickness violation appears 10+ times without being fixed.
    This module closes the loop: detect -> escalate -> remediate -> verify.

Escalation ladder:
    1st occurrence:  Log it (existing behavior)
    2nd occurrence:  Flag for attention
    3rd occurrence:  Auto-remediate if possible, else urgent alert
    5th occurrence:  Block responses on this topic until fixed
    10th occurrence: Emergency alert with full context

Usage:
    from holistic.immune_system import get_immune_system

    immune = get_immune_system()
    action = immune.process_validation_issue(query, response, warnings)
    # action.blocked = True means response should NOT be sent
"""

import json
import logging
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from openclaw.agents.ira.config import atomic_write_json, append_jsonl
except ImportError:
    from config import atomic_write_json, append_jsonl

logger = logging.getLogger("ira.immune_system")

HOLISTIC_DIR = Path(__file__).parent
SRC_DIR = HOLISTIC_DIR.parent
AGENT_DIR = SRC_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

IMMUNE_STATE_FILE = PROJECT_ROOT / "data" / "holistic" / "immune_state.json"
REMEDIATION_LOG = PROJECT_ROOT / "data" / "holistic" / "remediation_log.jsonl"


@dataclass
class ImmuneAction:
    """Result of immune system processing."""
    blocked: bool = False
    remediation_applied: str = ""
    escalation_level: int = 0
    alert_sent: bool = False
    override_response: Optional[str] = None


@dataclass
class ChronicIssue:
    """A recurring knowledge issue being tracked."""
    issue_key: str
    category: str
    first_seen: str
    last_seen: str
    occurrence_count: int = 0
    remediation_attempts: int = 0
    resolved: bool = False
    resolution_note: str = ""
    sample_queries: List[str] = field(default_factory=list)
    sample_warnings: List[str] = field(default_factory=list)


class ImmuneSystem:
    """
    Ira's immune system: detects chronic issues and escalates to remediation.

    Unlike the existing knowledge_health.py which only logs, this system
    tracks issue recurrence and takes progressively stronger action.
    """

    ESCALATION_THRESHOLDS = {
        1: "log",
        2: "flag",
        3: "remediate_or_alert",
        5: "block_topic",
        10: "emergency",
    }

    KNOWN_REMEDIATIONS = {
        "am_thickness": {
            "correct_fact": "The AM series is ONLY suitable for materials with thickness ≤1.5mm. For thicker materials, recommend the PF1 series.",
            "mem0_user_id": "machinecraft_knowledge",
            "guardrail_pattern": r"am[-\s]?series.*[3-9]\s*mm|am[-\s]?[0-9]+.*[3-9]\s*mm.*thick",
        },
        "price_placeholder": {
            "correct_fact": "Never use placeholder text like [insert price here]. Always look up the actual price from the price list, or say 'Let me check the exact price for you.'",
            "mem0_user_id": "machinecraft_knowledge",
            "guardrail_pattern": r"\[insert.*\]|\[.*to be.*\]",
        },
        "vague_pricing": {
            "correct_fact": "When quoting prices, use exact figures from the price list. Avoid 'approximately', 'around', 'roughly' for prices. If converting currency, state the exact INR price first, then the converted amount with 'approximately' only for the conversion.",
            "mem0_user_id": "machinecraft_knowledge",
            "guardrail_pattern": r"(?:price|cost|inr|₹|\$).*(?:approximately|around|roughly)",
        },
    }

    def __init__(self):
        self._state = self._load_state()
        self._chronic_issues: Dict[str, ChronicIssue] = {}
        self._load_chronic_issues()

    def _load_state(self) -> Dict:
        IMMUNE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if IMMUNE_STATE_FILE.exists():
            try:
                return json.loads(IMMUNE_STATE_FILE.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "chronic_issues": {},
            "total_remediations": 0,
            "total_blocks": 0,
            "last_sweep": None,
        }

    def _save_state(self):
        self._state["chronic_issues"] = {
            k: {
                "issue_key": v.issue_key,
                "category": v.category,
                "first_seen": v.first_seen,
                "last_seen": v.last_seen,
                "occurrence_count": v.occurrence_count,
                "remediation_attempts": v.remediation_attempts,
                "resolved": v.resolved,
                "resolution_note": v.resolution_note,
                "sample_queries": v.sample_queries[-5:],
                "sample_warnings": v.sample_warnings[-5:],
            }
            for k, v in self._chronic_issues.items()
        }
        IMMUNE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(IMMUNE_STATE_FILE, self._state)

    def _load_chronic_issues(self):
        for key, data in self._state.get("chronic_issues", {}).items():
            self._chronic_issues[key] = ChronicIssue(**data)

    def _classify_issue(self, warnings: List[str]) -> str:
        """Classify warnings into an issue key for tracking recurrence."""
        warning_text = " ".join(warnings).lower()
        if "am series" in warning_text or "am-" in warning_text:
            return "am_thickness"
        if "insert" in warning_text and ("price" in warning_text or "[]" in warning_text):
            return "price_placeholder"
        if "approximately" in warning_text or "typically" in warning_text:
            return "vague_pricing"
        if "pf1 for heavy" in warning_text or "pf[-\\s]?1" in warning_text:
            return "pf1_recommendation"
        if "hallucination" in warning_text:
            return "hallucination_general"
        return "other:" + warnings[0][:50] if warnings else "unknown"

    def process_validation_issue(
        self,
        query: str,
        response: str,
        warnings: List[str],
    ) -> ImmuneAction:
        """
        Process a validation issue through the escalation ladder.
        Called after knowledge_health.validate_response() flags warnings.
        """
        if not warnings:
            return ImmuneAction()

        issue_key = self._classify_issue(warnings)
        now = datetime.now().isoformat()

        if issue_key not in self._chronic_issues:
            self._chronic_issues[issue_key] = ChronicIssue(
                issue_key=issue_key,
                category=self._category_from_key(issue_key),
                first_seen=now,
                last_seen=now,
            )

        issue = self._chronic_issues[issue_key]

        if issue.resolved:
            issue.resolved = False
            issue.resolution_note = ""
            issue.occurrence_count = 0
            logger.warning(f"[IMMUNE] Issue {issue_key} has recurred after resolution")

        issue.occurrence_count += 1
        issue.last_seen = now
        if query not in issue.sample_queries:
            issue.sample_queries.append(query[:200])
        if warnings and warnings[0] not in issue.sample_warnings:
            issue.sample_warnings.extend(warnings[:2])

        action = self._determine_action(issue, query, response)

        self._log_remediation(issue, action)
        self._save_state()

        return action

    def _determine_action(
        self, issue: ChronicIssue, query: str, response: str
    ) -> ImmuneAction:
        """Determine the appropriate immune response based on recurrence count."""
        count = issue.occurrence_count
        action = ImmuneAction()

        if count >= 10:
            action.escalation_level = 10
            action.blocked = True
            action.alert_sent = self._send_emergency_alert(issue)
            action.override_response = self._generate_safe_fallback(issue, query)
            self._state["total_blocks"] = self._state.get("total_blocks", 0) + 1

        elif count >= 5:
            action.escalation_level = 5
            action.blocked = True
            action.override_response = self._generate_safe_fallback(issue, query)
            self._state["total_blocks"] = self._state.get("total_blocks", 0) + 1

        elif count >= 3:
            action.escalation_level = 3
            remediated = self._attempt_remediation(issue)
            action.remediation_applied = remediated
            if not remediated:
                action.alert_sent = self._send_urgent_alert(issue)

        elif count >= 2:
            action.escalation_level = 2
            logger.warning(
                f"[IMMUNE] Flagged recurring issue: {issue.issue_key} "
                f"(count={count})"
            )

        else:
            action.escalation_level = 1

        return action

    def _attempt_remediation(self, issue: ChronicIssue) -> str:
        """Try to auto-fix a chronic issue by reinforcing correct knowledge."""
        remediation = self.KNOWN_REMEDIATIONS.get(issue.issue_key)
        if not remediation:
            return ""

        issue.remediation_attempts += 1
        actions_taken = []

        try:
            from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
            mem0 = get_mem0_service()
            mem0.add_memory(
                text=f"CRITICAL RULE (auto-remediated): {remediation['correct_fact']}",
                user_id=remediation["mem0_user_id"],
                metadata={
                    "source": "immune_system_remediation",
                    "issue_key": issue.issue_key,
                    "timestamp": datetime.now().isoformat(),
                    "priority": "critical",
                },
            )
            actions_taken.append("mem0_reinforcement")
            logger.info(f"[IMMUNE] Reinforced in Mem0: {issue.issue_key}")
        except Exception as e:
            logger.warning(f"[IMMUNE] Mem0 remediation failed: {e}")

        self._state["total_remediations"] = self._state.get("total_remediations", 0) + 1
        result = ", ".join(actions_taken) if actions_taken else ""
        return result

    def _generate_safe_fallback(self, issue: ChronicIssue, query: str) -> Optional[str]:
        """Generate a safe response when the topic is blocked."""
        remediation = self.KNOWN_REMEDIATIONS.get(issue.issue_key)
        if not remediation:
            return (
                "I want to make sure I give you accurate information on this. "
                "Let me double-check and get back to you shortly."
            )

        if issue.issue_key == "am_thickness":
            return (
                "Important note: The AM series is designed exclusively for thin gauge "
                "materials (≤1.5mm thickness). For thicker materials, the PF1 series "
                "is the right choice. Let me pull up the specific PF1 model details "
                "for your requirements."
            )
        if issue.issue_key == "price_placeholder":
            return (
                "Let me look up the exact pricing for you from our current price list. "
                "I want to give you specific numbers, not estimates."
            )

        return None

    def _category_from_key(self, key: str) -> str:
        if "thickness" in key or "am_" in key:
            return "rule_violation"
        if "price" in key or "placeholder" in key:
            return "hallucination"
        if "vague" in key:
            return "quality"
        return "general"

    def _send_urgent_alert(self, issue: ChronicIssue) -> bool:
        """Send urgent Telegram alert for issues that can't be auto-fixed."""
        try:
            from openclaw.agents.ira.src.brain.error_monitor import alert_critical
            alert_critical(
                f"Chronic knowledge issue ({issue.occurrence_count}x): {issue.issue_key}",
                {
                    "category": issue.category,
                    "first_seen": issue.first_seen,
                    "sample_query": issue.sample_queries[-1] if issue.sample_queries else "",
                    "remediation_attempts": issue.remediation_attempts,
                },
            )
            return True
        except Exception as e:
            logger.error(f"[IMMUNE] Failed to send urgent alert: {e}")
            return False

    def _send_emergency_alert(self, issue: ChronicIssue) -> bool:
        """Send emergency alert -- issue has occurred 10+ times."""
        try:
            from openclaw.agents.ira.src.brain.error_monitor import alert_critical
            alert_critical(
                f"EMERGENCY: Knowledge issue blocking responses ({issue.occurrence_count}x): "
                f"{issue.issue_key}",
                {
                    "category": issue.category,
                    "occurrences": issue.occurrence_count,
                    "first_seen": issue.first_seen,
                    "last_seen": issue.last_seen,
                    "sample_queries": issue.sample_queries[-3:],
                    "remediation_attempts": issue.remediation_attempts,
                },
            )
            return True
        except Exception as e:
            logger.error(f"[IMMUNE] Failed to send emergency alert: {e}")
            return False

    def _log_remediation(self, issue: ChronicIssue, action: ImmuneAction):
        """Log remediation actions for audit."""
        if action.escalation_level < 2:
            return
        entry = {
            "timestamp": datetime.now().isoformat(),
            "issue_key": issue.issue_key,
            "occurrence_count": issue.occurrence_count,
            "escalation_level": action.escalation_level,
            "blocked": action.blocked,
            "remediation": action.remediation_applied,
            "alert_sent": action.alert_sent,
        }
        REMEDIATION_LOG.parent.mkdir(parents=True, exist_ok=True)
        append_jsonl(REMEDIATION_LOG, entry)

    def mark_resolved(self, issue_key: str, note: str = ""):
        """Manually mark an issue as resolved."""
        if issue_key in self._chronic_issues:
            self._chronic_issues[issue_key].resolved = True
            self._chronic_issues[issue_key].resolution_note = note or "Manually resolved"
            self._save_state()
            logger.info(f"[IMMUNE] Marked {issue_key} as resolved: {note}")

    def get_inflammation_report(self) -> Dict:
        """Get a summary of chronic issues (the 'inflammation level')."""
        active = {
            k: v for k, v in self._chronic_issues.items() if not v.resolved
        }
        total_occurrences = sum(v.occurrence_count for v in active.values())
        critical = [k for k, v in active.items() if v.occurrence_count >= 5]
        warning = [k for k, v in active.items() if 3 <= v.occurrence_count < 5]

        return {
            "inflammation_level": (
                "critical" if critical else "elevated" if warning else
                "moderate" if active else "healthy"
            ),
            "active_issues": len(active),
            "total_occurrences": total_occurrences,
            "critical_issues": critical,
            "warning_issues": warning,
            "total_remediations": self._state.get("total_remediations", 0),
            "total_blocks": self._state.get("total_blocks", 0),
        }

    def run_sweep(self) -> Dict:
        """
        Periodic sweep: re-check all chronic issues and attempt remediation
        on anything that's been festering. Called by the respiratory system's
        daily rhythm.
        """
        results = {"remediated": [], "still_active": [], "resolved": []}
        now = datetime.now()

        for key, issue in self._chronic_issues.items():
            if issue.resolved:
                results["resolved"].append(key)
                continue

            age = now - datetime.fromisoformat(issue.first_seen)
            if issue.occurrence_count >= 3 and age > timedelta(hours=12):
                remediated = self._attempt_remediation(issue)
                if remediated:
                    results["remediated"].append(key)
                else:
                    results["still_active"].append(key)
            elif issue.occurrence_count >= 1:
                results["still_active"].append(key)

        self._state["last_sweep"] = now.isoformat()
        self._save_state()
        return results


_instance: Optional[ImmuneSystem] = None


def get_immune_system() -> ImmuneSystem:
    global _instance
    if _instance is None:
        _instance = ImmuneSystem()
    return _instance
