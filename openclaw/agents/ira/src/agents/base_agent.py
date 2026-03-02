"""
Base Agent Class for IRA Pantheon Agents

Provides common infrastructure: logging, metrics, and lifecycle.
Agents are invoked as direct function calls via invocation.py / ira_skills_tools.py.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """
    Base class for all agents in the IRA Pantheon.

    Each agent is a stateless service that:
    - Receives requests via direct function calls
    - Processes them through its handle() method
    - Returns results to the caller
    """

    def __init__(self, name: str, role: str = "agent"):
        self.name = name
        self.role = role
        self.logger = logging.getLogger(f"ira.agent.{self.name}")
        self._call_count = 0
        self._total_processing_time = 0.0

    @abstractmethod
    async def handle(self, request: Any, context: dict | None = None) -> Any:
        raise NotImplementedError("Agents must implement handle()")

    async def __call__(self, request: Any, context: dict | None = None) -> Any:
        start = time.time()
        self._call_count += 1
        try:
            return await self.handle(request, context)
        finally:
            elapsed = time.time() - start
            self._total_processing_time += elapsed
            self.logger.debug({
                "agent": self.name,
                "event": "call_complete",
                "elapsed_ms": round(elapsed * 1000),
            })

    def get_stats(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "calls": self._call_count,
            "total_time_s": round(self._total_processing_time, 2),
            "avg_time_ms": round(
                (self._total_processing_time / self._call_count * 1000)
                if self._call_count > 0 else 0,
                1,
            ),
        }
