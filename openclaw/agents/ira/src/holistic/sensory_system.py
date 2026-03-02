#!/usr/bin/env python3
"""
SENSORY SYSTEM - Cross-Channel Integration and Unified Perception
==================================================================

Biological parallel:
    Multisensory integration (seeing + hearing + touching) creates richer
    neural representations. Each sense provides unique data; integration
    makes the whole greater than the sum of parts.

Ira parallel:
    Ira has multiple senses (Telegram, Email, Web search, Iris, document
    ingestion) but they operate in silos. A customer who emails and then
    messages on Telegram isn't recognized as the same conversation. Iris
    intelligence doesn't enrich the next customer interaction.

    This module creates a unified perception layer that integrates signals
    across all channels into a coherent picture.

Usage:
    from holistic.sensory_system import get_sensory_integrator

    sensory = get_sensory_integrator()
    sensory.record_perception("telegram", contact_id, message, metadata)
    sensory.record_perception("email", contact_id, message, metadata)
    context = sensory.get_integrated_context(contact_id)
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

try:
    from openclaw.agents.ira.config import atomic_write_json, append_jsonl
except ImportError:
    from config import atomic_write_json, append_jsonl

logger = logging.getLogger("ira.sensory_system")

HOLISTIC_DIR = Path(__file__).parent
SRC_DIR = HOLISTIC_DIR.parent
PROJECT_ROOT = SRC_DIR.parent.parent.parent.parent

SENSORY_STATE = PROJECT_ROOT / "data" / "holistic" / "sensory_state.json"
PERCEPTION_LOG = PROJECT_ROOT / "data" / "holistic" / "perception_log.jsonl"


CHANNEL_MODALITIES = {
    "telegram": {
        "type": "interactive",
        "richness": 0.7,
        "latency": "realtime",
        "strengths": ["quick_queries", "feedback", "commands", "approvals"],
    },
    "email": {
        "type": "asynchronous",
        "richness": 0.9,
        "latency": "minutes_to_hours",
        "strengths": ["formal_communication", "detailed_context", "thread_history"],
    },
    "web_search": {
        "type": "active_sensing",
        "richness": 0.6,
        "latency": "seconds",
        "strengths": ["market_data", "competitor_info", "news", "trends"],
    },
    "iris_intelligence": {
        "type": "active_sensing",
        "richness": 0.8,
        "latency": "seconds",
        "strengths": ["company_news", "industry_trends", "geopolitical_context"],
    },
    "document_ingestion": {
        "type": "passive_sensing",
        "richness": 1.0,
        "latency": "batch",
        "strengths": ["specs", "pricing", "manuals", "knowledge"],
    },
    "google_tools": {
        "type": "active_sensing",
        "richness": 0.5,
        "latency": "seconds",
        "strengths": ["calendar", "contacts", "spreadsheets", "drive"],
    },
}


@dataclass
class Perception:
    """A single sensory input from any channel."""
    channel: str
    contact_id: Optional[str]
    timestamp: str
    content_summary: str
    metadata: Dict = field(default_factory=dict)
    sentiment: Optional[str] = None  # positive, negative, neutral
    entities_mentioned: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)


@dataclass
class IntegratedContext:
    """Cross-channel context for a contact or topic."""
    contact_id: str
    channels_active: Set[str] = field(default_factory=set)
    recent_perceptions: List[Perception] = field(default_factory=list)
    sentiment_trajectory: List[str] = field(default_factory=list)
    topics_discussed: Set[str] = field(default_factory=set)
    last_interaction: Optional[str] = None
    interaction_count: int = 0
    cross_channel_notes: List[str] = field(default_factory=list)


class SensoryIntegrator:
    """
    Ira's sensory integration system: combines inputs from all channels
    into unified perception, detects cross-channel patterns, and enriches
    context for each interaction.
    """

    CONTEXT_WINDOW_HOURS = 72  # How far back to look for context

    def __init__(self):
        self._state = self._load_state()
        self._contact_contexts: Dict[str, IntegratedContext] = {}
        self._channel_stats: Dict[str, Dict] = defaultdict(lambda: {
            "total_perceptions": 0,
            "last_active": None,
        })
        self._load_contexts()

    def _load_state(self) -> Dict:
        SENSORY_STATE.parent.mkdir(parents=True, exist_ok=True)
        if SENSORY_STATE.exists():
            try:
                return json.loads(SENSORY_STATE.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "total_perceptions": 0,
            "channel_stats": {},
            "contact_summaries": {},
            "cross_channel_events": 0,
        }

    def _save_state(self):
        self._state["channel_stats"] = dict(self._channel_stats)
        contact_summaries = {}
        for cid, ctx in self._contact_contexts.items():
            contact_summaries[cid] = {
                "channels": list(ctx.channels_active),
                "interaction_count": ctx.interaction_count,
                "last_interaction": ctx.last_interaction,
                "topics": list(ctx.topics_discussed)[:20],
                "sentiment_trajectory": ctx.sentiment_trajectory[-10:],
            }
        self._state["contact_summaries"] = contact_summaries
        SENSORY_STATE.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(SENSORY_STATE, self._state)

    def _load_contexts(self):
        for cid, summary in self._state.get("contact_summaries", {}).items():
            self._contact_contexts[cid] = IntegratedContext(
                contact_id=cid,
                channels_active=set(summary.get("channels", [])),
                interaction_count=summary.get("interaction_count", 0),
                last_interaction=summary.get("last_interaction"),
                topics_discussed=set(summary.get("topics", [])),
                sentiment_trajectory=summary.get("sentiment_trajectory", []),
            )
        for channel, stats in self._state.get("channel_stats", {}).items():
            self._channel_stats[channel] = stats

    def record_perception(
        self,
        channel: str,
        contact_id: Optional[str],
        content_summary: str,
        metadata: Optional[Dict] = None,
        sentiment: Optional[str] = None,
        entities: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
    ) -> Optional[List[str]]:
        """
        Record a sensory input. Returns any cross-channel notes that
        should be surfaced to the current interaction.
        """
        now = datetime.now().isoformat()

        perception = Perception(
            channel=channel,
            contact_id=contact_id,
            timestamp=now,
            content_summary=content_summary[:500],
            metadata=metadata or {},
            sentiment=sentiment,
            entities_mentioned=entities or [],
            topics=topics or [],
        )

        self._state["total_perceptions"] = self._state.get("total_perceptions", 0) + 1
        self._channel_stats[channel]["total_perceptions"] = (
            self._channel_stats[channel].get("total_perceptions", 0) + 1
        )
        self._channel_stats[channel]["last_active"] = now

        entry = {
            "timestamp": now,
            "channel": channel,
            "contact_id": contact_id,
            "content_summary": content_summary[:500],
            "sentiment": sentiment,
            "entities": entities or [],
            "topics": topics or [],
        }
        PERCEPTION_LOG.parent.mkdir(parents=True, exist_ok=True)
        try:
            append_jsonl(PERCEPTION_LOG, entry)
        except Exception:
            pass

        cross_channel_notes = []
        if contact_id:
            cross_channel_notes = self._integrate_contact_perception(
                contact_id, perception
            )

        self._save_state()
        return cross_channel_notes

    def _integrate_contact_perception(
        self, contact_id: str, perception: Perception
    ) -> List[str]:
        """Integrate a perception into a contact's cross-channel context."""
        if contact_id not in self._contact_contexts:
            self._contact_contexts[contact_id] = IntegratedContext(
                contact_id=contact_id
            )

        ctx = self._contact_contexts[contact_id]
        notes = []

        previous_channels = set(ctx.channels_active)
        ctx.channels_active.add(perception.channel)

        if previous_channels and perception.channel not in previous_channels:
            notes.append(
                f"Cross-channel: {contact_id} previously on "
                f"{', '.join(previous_channels)}, now on {perception.channel}"
            )
            self._state["cross_channel_events"] = (
                self._state.get("cross_channel_events", 0) + 1
            )

        ctx.recent_perceptions.append(perception)
        ctx.recent_perceptions = ctx.recent_perceptions[-20:]

        ctx.interaction_count += 1
        ctx.last_interaction = perception.timestamp

        if perception.sentiment:
            ctx.sentiment_trajectory.append(perception.sentiment)
            ctx.sentiment_trajectory = ctx.sentiment_trajectory[-20:]

            if len(ctx.sentiment_trajectory) >= 3:
                recent = ctx.sentiment_trajectory[-3:]
                if all(s == "negative" for s in recent):
                    notes.append(
                        f"Sentiment alert: {contact_id} has been negative "
                        f"for 3 consecutive interactions"
                    )
                elif (
                    len(ctx.sentiment_trajectory) >= 4
                    and ctx.sentiment_trajectory[-4] == "negative"
                    and all(s == "positive" for s in recent)
                ):
                    notes.append(
                        f"Sentiment recovery: {contact_id} sentiment improving"
                    )

        if perception.topics:
            ctx.topics_discussed.update(perception.topics)

        return notes

    def get_integrated_context(self, contact_id: str) -> Dict:
        """
        Get the full cross-channel context for a contact.
        This is what makes Ira's perception richer than any single channel.
        """
        ctx = self._contact_contexts.get(contact_id)
        if not ctx:
            return {"contact_id": contact_id, "known": False}

        recent_by_channel = defaultdict(list)
        for p in ctx.recent_perceptions[-10:]:
            recent_by_channel[p.channel].append({
                "timestamp": p.timestamp,
                "summary": p.content_summary[:200],
                "sentiment": p.sentiment,
            })

        return {
            "contact_id": contact_id,
            "known": True,
            "channels_active": list(ctx.channels_active),
            "is_multi_channel": len(ctx.channels_active) > 1,
            "interaction_count": ctx.interaction_count,
            "last_interaction": ctx.last_interaction,
            "topics_discussed": list(ctx.topics_discussed)[:15],
            "sentiment_trajectory": ctx.sentiment_trajectory[-5:],
            "current_sentiment": (
                ctx.sentiment_trajectory[-1] if ctx.sentiment_trajectory else None
            ),
            "recent_by_channel": dict(recent_by_channel),
            "cross_channel_notes": ctx.cross_channel_notes[-5:],
        }

    def get_channel_health(self) -> Dict:
        """Get health status of each sensory channel."""
        now = datetime.now()
        channel_health = {}

        for channel, modality in CHANNEL_MODALITIES.items():
            stats = self._channel_stats.get(channel, {})
            total = stats.get("total_perceptions", 0)
            last_active = stats.get("last_active")

            if last_active:
                try:
                    gap = (now - datetime.fromisoformat(last_active)).total_seconds()
                    hours_since = gap / 3600
                except (ValueError, TypeError):
                    hours_since = None
            else:
                hours_since = None

            if total == 0:
                status = "dormant"
            elif hours_since and hours_since > 48:
                status = "inactive"
            elif hours_since and hours_since > 12:
                status = "idle"
            else:
                status = "active"

            channel_health[channel] = {
                "status": status,
                "total_perceptions": total,
                "last_active": last_active,
                "hours_since_active": round(hours_since, 1) if hours_since else None,
                "modality_type": modality["type"],
                "strengths": modality["strengths"],
            }

        return channel_health

    def get_sensory_report(self) -> Dict:
        """Get full sensory system report for vital signs."""
        channel_health = self.get_channel_health()

        active_channels = [
            ch for ch, h in channel_health.items() if h["status"] == "active"
        ]
        dormant_channels = [
            ch for ch, h in channel_health.items() if h["status"] == "dormant"
        ]
        multi_channel_contacts = [
            cid for cid, ctx in self._contact_contexts.items()
            if len(ctx.channels_active) > 1
        ]

        return {
            "total_perceptions": self._state.get("total_perceptions", 0),
            "active_channels": active_channels,
            "dormant_channels": dormant_channels,
            "channel_health": channel_health,
            "multi_channel_contacts": len(multi_channel_contacts),
            "cross_channel_events": self._state.get("cross_channel_events", 0),
            "total_contacts_tracked": len(self._contact_contexts),
            "sensory_richness": (
                "rich" if len(active_channels) >= 3 else
                "moderate" if len(active_channels) >= 2 else
                "monocular" if len(active_channels) == 1 else
                "blind"
            ),
        }


_instance: Optional[SensoryIntegrator] = None


def get_sensory_integrator() -> SensoryIntegrator:
    global _instance
    if _instance is None:
        _instance = SensoryIntegrator()
    return _instance
