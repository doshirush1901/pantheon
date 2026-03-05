"""
RealTimeObserver — extracts learnings from the latest conversation turn.

Runs after every response from process_with_tools(). Uses a lightweight
LLM call (GPT-4o-mini) to detect facts, corrections, and preferences
in the user's message, then publishes them to the RealTimeHub for
immediate use on the next turn.

Design decisions:
  - GPT-4o-mini for cost: ~$0.0002 per observation call
  - Fire-and-forget: failures don't block the response pipeline
  - Conversation-scoped: patterns go to RealTimeHub, not Mem0/Qdrant
  - Nightly consolidation promotes durable patterns to long-term memory
"""

import asyncio
import json
import logging
import os
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.realtime_observer")

_TURN_LEARNING_PROMPT = (
    "You are observing a single turn in a conversation with an AI agent. "
    "The user said X, the agent said Y. Was there a correction, a new fact, "
    "a clarification, or a preference stated? If so, extract it as a concise, "
    "actionable learning. For example: 'User prefers metric units' or "
    "'Fact: The CEO of Walterpack is named Klaus.' If there is no learning, output null."
)


class RealTimeObserver:
    """
    Post-turn observer that extracts short-term learnings from conversations.

    Usage:
        observer = get_realtime_observer()
        patterns = await observer.run_observation(snippet, user_id, conversation_id)
    """

    def __init__(self):
        self._api_key: Optional[str] = None

    def _get_api_key(self) -> str:
        if not self._api_key:
            self._api_key = os.environ.get("OPENAI_API_KEY") or ""
            if not self._api_key:
                try:
                    from openclaw.agents.ira.config import OPENAI_API_KEY
                    self._api_key = OPENAI_API_KEY or ""
                except Exception:
                    pass
        return self._api_key

    async def run_observation(
        self,
        conversation_snippet: str,
        user_id: str,
        conversation_id: str = "",
    ) -> List["LearnedPattern"]:
        """
        Analyze the latest conversation turn and extract learnings.

        Returns the list of patterns published to the RealTimeHub.
        This is fire-and-forget safe — all exceptions are caught.
        """
        if not conversation_snippet or len(conversation_snippet.strip()) < 10:
            return []
        parts = conversation_snippet.split("\n")
        user_text = ""
        assistant_text = ""
        for line in parts:
            if line.lower().startswith("user:"):
                user_text = line.split(":", 1)[1].strip()
            elif line.lower().startswith("ira:") or line.lower().startswith("assistant:"):
                assistant_text = line.split(":", 1)[1].strip()

        await self.observe_turn(
            context={"user_id": user_id, "conversation_id": conversation_id},
            user_message=user_text or conversation_snippet,
            final_response=assistant_text or "",
            conversation_history=conversation_snippet,
        )
        return []

    async def observe_turn(
        self,
        context: Dict[str, Any],
        user_message: str,
        final_response: str,
        conversation_history: str,
    ) -> Optional[str]:
        """Analyze one turn and persist an extracted learning into LearningHub."""
        api_key = self._get_api_key()
        if not api_key:
            logger.warning("[RealTimeObserver] No API key — skipping observation")
            return None

        if not user_message or len(user_message.strip()) < 2:
            return None

        try:
            import openai
            from openclaw.agents.ira.src.learning.learning_hub import get_learning_hub

            client = openai.AsyncOpenAI(api_key=api_key)
            user_id = (context or {}).get("user_id", "unknown")
            conversation_id = (context or {}).get("conversation_id", "")

            prompt = (
                f"{_TURN_LEARNING_PROMPT}\n\n"
                f"X (user): {user_message.strip()}\n"
                f"Y (agent): {final_response.strip()}\n\n"
                f"Recent conversation history:\n{(conversation_history or '')[-2000:]}"
            )

            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {"role": "system", "content": "Return only the extracted learning as plain text, or null."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=120,
                    temperature=0.0,
                ),
                timeout=10.0,
            )

            learning = (response.choices[0].message.content or "").strip()
            if learning.startswith("```"):
                learning = learning.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            if not learning or learning.lower() in {"null", "none", "n/a"}:
                return None

            get_learning_hub().add_learning(
                learning,
                source="realtime_observer",
                metadata={
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                },
            )

            try:
                from openclaw.agents.ira.src.observers.realtime_hub import (
                    get_realtime_hub, LearnedPattern, PatternType,
                )
                ptype = PatternType.CORRECTION if "correct" in learning.lower() else (
                    PatternType.PREFERENCE if any(w in learning.lower() for w in ("prefer", "want", "like")) else PatternType.FACT
                )
                get_realtime_hub().publish(LearnedPattern(
                    pattern_type=ptype,
                    content=learning,
                    user_id=user_id,
                    conversation_id=conversation_id,
                ))
            except Exception as hub_err:
                logger.debug("[RealTimeObserver] Hub publish failed (non-fatal): %s", hub_err)

            logger.info("[RealTimeObserver] Added learning for user=%s: %s", user_id, learning[:140])
            return learning
        except asyncio.TimeoutError:
            logger.warning("[RealTimeObserver] LLM call timed out (10s)")
            return None
        except Exception as e:
            logger.warning("[RealTimeObserver] Observation failed (non-fatal): %s", e)
            return None


_observer_instance: Optional[RealTimeObserver] = None
_observer_lock = threading.Lock()


def get_realtime_observer() -> RealTimeObserver:
    global _observer_instance
    if _observer_instance is None:
        with _observer_lock:
            if _observer_instance is None:
                _observer_instance = RealTimeObserver()
    return _observer_instance
