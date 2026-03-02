#!/usr/bin/env python3
"""
VOICE SYSTEM — Adaptive Tone, Length, and Format Shaping
=========================================================

Biological parallel:
    The larynx doesn't decide *what* to say — the brain does that. The larynx
    controls *how* it's said: volume, pitch, speed, timbre. A whisper in a
    library, a shout across a factory floor, a warm tone with a friend.

Ira parallel:
    Ira's brain (generate_answer, tool_orchestrator) decides the content.
    The voice system sits at the very end of the pipeline and reshapes the
    delivery: trimming verbose answers for quick lookups, expanding terse
    ones for complex asks, matching the user's communication style, and
    adapting to channel constraints.

    It applies deterministic rules for trimming, formatting, and length
    enforcement based on channel and message complexity.

Usage:
    from openclaw.agents.ira.src.holistic.voice_system import get_voice_system

    voice = get_voice_system()
    shaped = voice.reshape(response_text, channel="telegram", message=user_msg)

Integration points:
    - generate_answer.py: after _apply_personality(), before business rules
    - tool_orchestrator.py: before returning final response
    - unified_gateway.py: after invoke_verify(), before GatewayResponse
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("ira.voice_system")

HOLISTIC_DIR = Path(__file__).parent
SRC_DIR = HOLISTIC_DIR.parent
PROJECT_ROOT = SRC_DIR.parent.parent.parent.parent

VOICE_STATE_FILE = PROJECT_ROOT / "data" / "holistic" / "voice_state.json"
VOICE_LOG = PROJECT_ROOT / "data" / "holistic" / "voice_log.jsonl"


# ---------------------------------------------------------------------------
# Channel voice profiles — how Ira "speaks" on each channel
# ---------------------------------------------------------------------------

CHANNEL_PROFILES = {
    "telegram": {
        "max_length": 2000,
        "prefer_short": True,
        "use_markdown": True,
        "use_emoji_sparingly": True,
        "default_style": "conversational",
    },
    "email": {
        "max_length": 8000,
        "prefer_short": False,
        "use_markdown": False,
        "use_emoji_sparingly": False,
        "default_style": "professional",
    },
    "api": {
        "max_length": 4000,
        "prefer_short": False,
        "use_markdown": True,
        "use_emoji_sparingly": False,
        "default_style": "neutral",
    },
    "cli": {
        "max_length": 4000,
        "prefer_short": False,
        "use_markdown": True,
        "use_emoji_sparingly": False,
        "default_style": "neutral",
    },
}


# ---------------------------------------------------------------------------
# Message complexity classification
# ---------------------------------------------------------------------------

_QUICK_LOOKUP_PATTERNS = [
    r"^(?:what(?:'s| is) the )?price",
    r"^(?:what(?:'s| is) the )?cost",
    r"^how much",
    r"^(?:what(?:'s| is) the )?lead time",
    r"^(?:what(?:'s| is) the )?delivery",
    r"^(?:what(?:'s| is) the )?spec",
    r"^(?:what(?:'s| is) the )?max(?:imum)?",
    r"^(?:what(?:'s| is) the )?min(?:imum)?",
    r"^(?:what(?:'s| is) the )?weight",
    r"^(?:what(?:'s| is) the )?dimension",
    r"^(?:what(?:'s| is) the )?forming area",
    r"^(?:what(?:'s| is) the )?thickness",
    r"^(?:do (?:you|we) have)",
    r"^(?:is there|are there)",
    r"^(?:can (?:you|it|the))",
    r"^(?:does (?:it|the))",
    r"^(?:yes|no|ok|okay|sure|got it|thanks|thank you)",
]

_COMPLEX_PATTERNS = [
    r"compare|comparison|versus|vs\.?",
    r"recommend|suggest|advise|which (?:machine|model|series)",
    r"draft|write|compose|email",
    r"research|investigate|find out|look into",
    r"explain|walk me through|how does",
    r"multiple|several|all|every|list all",
    r"customer.*in.*(?:germany|india|usa|europe|asia)",
]


@dataclass
class MessageProfile:
    """Analysis of an incoming message to guide voice shaping."""
    complexity: str  # "quick", "moderate", "complex"
    word_count: int
    is_question: bool
    is_command: bool
    is_multi_part: bool
    sub_requests: int
    estimated_ideal_length: int  # target response word count
    tone: str  # "casual", "professional", "urgent"


@dataclass
class VoiceAction:
    """Result of voice reshaping."""
    original_length: int
    shaped_length: int
    actions_taken: List[str]
    complexity: str
    channel: str


# ---------------------------------------------------------------------------
# Core voice system
# ---------------------------------------------------------------------------

class VoiceSystem:
    """
    Adaptive voice that reshapes Ira's responses based on message complexity,
    channel constraints, user preferences, and time of day.
    """

    def __init__(self):
        self._state = self._load_state()
        self._quick_patterns = [re.compile(p, re.IGNORECASE) for p in _QUICK_LOOKUP_PATTERNS]
        self._complex_patterns = [re.compile(p, re.IGNORECASE) for p in _COMPLEX_PATTERNS]

    # -- State persistence --------------------------------------------------

    def _load_state(self) -> Dict:
        try:
            if VOICE_STATE_FILE.exists():
                return json.loads(VOICE_STATE_FILE.read_text())
        except Exception as e:
            logger.debug(f"Voice state load failed: {e}")
        return {
            "total_reshapes": 0,
            "total_trims": 0,
            "total_expansions": 0,
            "avg_compression_ratio": 1.0,
            "channel_stats": {},
            "last_updated": datetime.now().isoformat(),
        }

    def _save_state(self):
        try:
            VOICE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self._state["last_updated"] = datetime.now().isoformat()
            VOICE_STATE_FILE.write_text(json.dumps(self._state, indent=2, default=str))
        except Exception as e:
            logger.debug(f"Voice state save failed: {e}")

    def _log_event(self, event: Dict):
        try:
            VOICE_LOG.parent.mkdir(parents=True, exist_ok=True)
            event["timestamp"] = datetime.now().isoformat()
            with open(VOICE_LOG, "a") as f:
                f.write(json.dumps(event, default=str) + "\n")
        except Exception:
            pass

    # -- Message analysis ---------------------------------------------------

    def analyze_message(self, message: str, channel: str = "telegram") -> MessageProfile:
        """Classify the incoming message to determine voice parameters."""
        msg_lower = message.lower().strip()
        words = message.split()
        word_count = len(words)

        is_command = msg_lower.startswith("/")
        is_question = msg_lower.rstrip().endswith("?") or any(
            msg_lower.startswith(w) for w in ["what", "how", "when", "where", "why", "who", "can", "does", "is", "are", "do"]
        )

        # Count sub-requests (numbered items, "also", "and also", line breaks with questions)
        sub_requests = max(1, len(re.findall(r"(?:^\d+[.)]\s|\balso\b|\badditionally\b|\bplus\b)", message, re.MULTILINE | re.IGNORECASE)))
        is_multi_part = sub_requests > 1 or word_count > 80

        # Complexity classification
        if is_command or word_count <= 8:
            complexity = "quick"
        elif any(p.search(msg_lower) for p in self._quick_patterns):
            complexity = "quick"
        elif any(p.search(msg_lower) for p in self._complex_patterns) or is_multi_part:
            complexity = "complex"
        else:
            complexity = "moderate"

        # Tone detection
        if any(w in msg_lower for w in ["asap", "urgent", "immediately", "now", "quick"]):
            tone = "urgent"
        elif channel == "email" or word_count > 50:
            tone = "professional"
        else:
            tone = "casual"

        # Ideal response length (in words)
        ideal_lengths = {
            "quick": 40,
            "moderate": 120,
            "complex": 300,
        }
        ideal = ideal_lengths[complexity]
        if is_multi_part:
            ideal = max(ideal, sub_requests * 80)

        return MessageProfile(
            complexity=complexity,
            word_count=word_count,
            is_question=is_question,
            is_command=is_command,
            is_multi_part=is_multi_part,
            sub_requests=sub_requests,
            estimated_ideal_length=ideal,
            tone=tone,
        )

    # -- Core reshape -------------------------------------------------------

    def reshape(
        self,
        response: str,
        channel: str = "telegram",
        message: str = "",
        user_id: str = "",
    ) -> str:
        """
        Reshape a response based on message complexity and channel.

        This is the main entry point — called from generate_answer,
        tool_orchestrator, and unified_gateway right before the response
        is returned to the user.
        """
        if not response or not response.strip():
            return response

        original_len = len(response)
        profile = self.analyze_message(message, channel) if message else MessageProfile(
            complexity="moderate", word_count=0, is_question=False,
            is_command=False, is_multi_part=False, sub_requests=1,
            estimated_ideal_length=120, tone="casual",
        )

        channel_profile = CHANNEL_PROFILES.get(channel, CHANNEL_PROFILES["telegram"])
        actions_taken = []

        shaped = response

        # 1. Trim verbose responses for quick lookups
        if profile.complexity == "quick" and len(shaped.split()) > profile.estimated_ideal_length * 2:
            shaped = self._trim_for_quick(shaped, profile)
            actions_taken.append("trimmed_for_quick_lookup")

        # 2. Enforce channel max length
        if len(shaped) > channel_profile["max_length"]:
            shaped = self._enforce_max_length(shaped, channel_profile["max_length"])
            actions_taken.append("enforced_max_length")

        # 3. Clean up formatting artifacts
        shaped = self._clean_formatting(shaped, channel_profile)
        if shaped != response:
            actions_taken.append("cleaned_formatting")

        # 4. Trim trailing filler for urgent tone
        if profile.tone == "urgent":
            shaped = self._trim_filler(shaped)
            if shaped != response:
                actions_taken.append("trimmed_filler_urgent")

        # Track stats
        self._record_reshape(
            original_len=original_len,
            shaped_len=len(shaped),
            actions=actions_taken,
            complexity=profile.complexity,
            channel=channel,
            user_id=user_id,
        )

        return shaped

    # -- Shaping strategies -------------------------------------------------

    def _trim_for_quick(self, text: str, profile: MessageProfile) -> str:
        """For quick lookups, keep only the substantive answer."""
        lines = text.strip().split("\n")
        if len(lines) <= 3:
            return text

        # Keep lines that contain actual data (numbers, specs, prices)
        data_lines = []
        context_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            has_data = bool(re.search(
                r'\d+[,.]?\d*\s*(?:mm|cm|m|kg|kw|INR|USD|EUR|GBP|₹|\$|€|£|%|months?|weeks?|days?)',
                stripped, re.IGNORECASE
            ))
            has_bullet = stripped.startswith(("-", "*", "•", "1.", "2.", "3."))
            has_bold = "**" in stripped
            if has_data or has_bullet or has_bold:
                data_lines.append(line)
            else:
                context_lines.append(line)

        # For quick lookups: prioritize data lines, add minimal context
        if data_lines:
            result_lines = []
            if context_lines:
                result_lines.append(context_lines[0])
            result_lines.extend(data_lines[:10])
            # Keep a closing CTA if present
            last_line = lines[-1].strip().lower()
            if any(cta in last_line for cta in ["let me know", "questions?", "make sense?", "want me to", "shall i"]):
                result_lines.append(lines[-1])
            return "\n".join(result_lines)

        return text

    def _enforce_max_length(self, text: str, max_len: int) -> str:
        """Truncate intelligently at paragraph/sentence boundaries."""
        if len(text) <= max_len:
            return text

        # Try to cut at a paragraph boundary
        truncated = text[:max_len]
        last_para = truncated.rfind("\n\n")
        if last_para > max_len * 0.6:
            return truncated[:last_para].rstrip()

        # Try sentence boundary
        last_sentence = max(truncated.rfind(". "), truncated.rfind(".\n"))
        if last_sentence > max_len * 0.6:
            return truncated[:last_sentence + 1]

        return truncated.rstrip()

    def _clean_formatting(self, text: str, channel_profile: Dict) -> str:
        """Remove formatting artifacts and normalize whitespace."""
        # Collapse 3+ consecutive blank lines to 2
        text = re.sub(r"\n{4,}", "\n\n\n", text)

        # Remove trailing whitespace on each line
        text = "\n".join(line.rstrip() for line in text.split("\n"))

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def _trim_filler(self, text: str) -> str:
        """Remove filler phrases that add no value, especially for urgent messages."""
        filler_patterns = [
            r"(?:^|\n)(?:I hope this helps|Hope that helps|Let me know if you (?:need|have) (?:anything|any)(?:thing)? else)[.!]*\s*$",
            r"(?:^|\n)(?:Feel free to reach out|Don't hesitate to (?:ask|reach out))[.!]*\s*$",
            r"(?:^|\n)(?:Is there anything else (?:I can help|you'd like))[^?]*\?\s*$",
        ]
        for pattern in filler_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)
        return text.rstrip()

    # -- Tracking -----------------------------------------------------------

    def _record_reshape(
        self,
        original_len: int,
        shaped_len: int,
        actions: List[str],
        complexity: str,
        channel: str,
        user_id: str,
    ):
        """Track reshape statistics for learning."""
        self._state["total_reshapes"] = self._state.get("total_reshapes", 0) + 1
        if shaped_len < original_len:
            self._state["total_trims"] = self._state.get("total_trims", 0) + 1
        elif shaped_len > original_len:
            self._state["total_expansions"] = self._state.get("total_expansions", 0) + 1

        # Rolling average compression ratio
        if original_len > 0:
            ratio = shaped_len / original_len
            prev = self._state.get("avg_compression_ratio", 1.0)
            n = self._state["total_reshapes"]
            self._state["avg_compression_ratio"] = round(prev + (ratio - prev) / n, 4)

        # Per-channel stats
        ch_stats = self._state.setdefault("channel_stats", {})
        ch = ch_stats.setdefault(channel, {"reshapes": 0, "trims": 0})
        ch["reshapes"] = ch.get("reshapes", 0) + 1
        if shaped_len < original_len:
            ch["trims"] = ch.get("trims", 0) + 1

        if actions:
            self._log_event({
                "type": "reshape",
                "channel": channel,
                "user_id": user_id,
                "complexity": complexity,
                "original_len": original_len,
                "shaped_len": shaped_len,
                "actions": actions,
            })

        # Periodic save (every 10 reshapes)
        if self._state["total_reshapes"] % 10 == 0:
            self._save_state()

    # -- Reports for vital signs --------------------------------------------

    def get_voice_report(self) -> Dict:
        """Produce a health report for the vital signs dashboard."""
        total = self._state.get("total_reshapes", 0)
        trims = self._state.get("total_trims", 0)
        expansions = self._state.get("total_expansions", 0)
        ratio = self._state.get("avg_compression_ratio", 1.0)

        status = "healthy"
        if total > 0 and trims / total > 0.8:
            status = "over_trimming"
        elif total > 0 and ratio > 1.3:
            status = "verbose"

        return {
            "status": status,
            "total_reshapes": total,
            "total_trims": trims,
            "total_expansions": expansions,
            "avg_compression_ratio": ratio,
            "channel_stats": self._state.get("channel_stats", {}),
        }

    # -- Dream mode maintenance ---------------------------------------------

    def run_voice_maintenance(self) -> Dict:
        """Called during dream mode Phase 10.5.

        Analyzes voice patterns and adjusts the Telegram max_length threshold
        based on observed trimming rates. If >80% of reshapes are trims, the
        limit is too tight. If avg compression ratio > 1.3, responses are
        expanding and the limit should tighten.
        """
        report = self.get_voice_report()
        adjustments = []

        tg = CHANNEL_PROFILES.get("telegram", {})
        current_max = tg.get("max_length", 2000)

        if report["status"] == "over_trimming" and current_max < 3000:
            new_max = min(current_max + 200, 3000)
            tg["max_length"] = new_max
            adjustments.append(f"Raised Telegram max_length {current_max} → {new_max}")
            logger.info("[Voice] Over-trimming: raised Telegram max_length to %d", new_max)

        if report["status"] == "verbose" and current_max > 1500:
            new_max = max(current_max - 200, 1500)
            tg["max_length"] = new_max
            adjustments.append(f"Lowered Telegram max_length {current_max} → {new_max}")
            logger.info("[Voice] Verbose: lowered Telegram max_length to %d", new_max)

        self._save_state()

        return {
            "voice_status": report["status"],
            "total_reshapes": report["total_reshapes"],
            "adjustments": adjustments,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_instance: Optional[VoiceSystem] = None


def get_voice_system() -> VoiceSystem:
    """Get the singleton VoiceSystem instance."""
    global _instance
    if _instance is None:
        _instance = VoiceSystem()
    return _instance
