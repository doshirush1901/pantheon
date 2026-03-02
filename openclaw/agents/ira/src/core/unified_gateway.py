"""
Unified Gateway - Single entry point for the Ira pipeline.

Orchestrates: middleware -> identity -> intent -> research -> iris -> write -> verify -> reflection.
Uses shared skill invocation from src.skills.invocation (no duplication).
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict

logger = logging.getLogger("ira.gateway")

# Re-export for tests that import UNAVAILABLE from here
# P2: Tool-orchestrated mode (LLM chooses skills)
try:
    from openclaw.agents.ira.src.core.tool_orchestrator import process_with_tools
    TOOL_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    TOOL_ORCHESTRATOR_AVAILABLE = False

from openclaw.agents.ira.src.skills.invocation import (
    UNAVAILABLE,
    get_skill_availability,
    invoke_identity_resolve,
    invoke_iris_enrich,
    invoke_reflect,
    invoke_research,
    invoke_verify,
    invoke_write,
)


@dataclass
class GatewayRequest:
    """Incoming request to the gateway."""

    message: str
    channel: str = "api"
    user_id: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GatewayResponse:
    """Response from the gateway."""

    response: str
    intent: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)


class UnifiedGateway:
    """
    Unified gateway for all channels.
    Delegates skill execution to src.skills.invocation.
    """

    def _analyze_intent(self, message: str) -> str:
        try:
            from openclaw.agents.ira.src.agents.chief_of_staff.agent import analyze_intent
            return analyze_intent(message)
        except ImportError:
            return "general"

    async def process(self, request: GatewayRequest) -> GatewayResponse:
        """
        Execute the full pipeline: middleware -> identity -> intent -> research
        -> iris -> write -> verify -> reflection.
        """
        import asyncio
        import time
        import uuid

        _start_time = time.monotonic()
        _request_id = request.metadata.get("request_id") or str(uuid.uuid4())[:12]
        _phase_timings: Dict[str, float] = {}

        # Bind trace context for observability (correlates Athena→Clio→Vera logs)
        try:
            from openclaw.agents.ira.core.ira_logging import start_trace
            start_trace(channel=request.channel, user_id=request.user_id)
        except ImportError:
            pass

        # Sensory: record incoming perception
        try:
            from openclaw.agents.ira.src.holistic.sensory_system import get_sensory_integrator
            sensory = get_sensory_integrator()
            sensory.record_perception(
                channel=request.channel,
                contact_id=request.user_id,
                content_summary=request.message[:500],
            )
        except Exception:
            pass

        context: Dict[str, Any] = {
            "message": request.message,
            "channel": request.channel,
            "user_id": request.user_id,
            "metadata": request.metadata,
            "iris_context": {},
            "steering": None,
            "_request_id": _request_id,
        }

        # Identity (optional)
        try:
            resolved = invoke_identity_resolve(request.channel, request.user_id)
            if resolved is not None:
                context["identity"] = resolved
                context["lead_id"] = resolved
                # Phase 5: Populate company for Iris when we have contact identity
                try:
                    from openclaw.agents.ira.src.identity.unified_identity import get_identity_service
                    contact = get_identity_service().get_contact(resolved)
                    if contact and contact.company:
                        context["company"] = contact.company
                        context["lead_id"] = contact.contact_id
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Identity resolve skipped: {e}")

        # Intent
        context["intent"] = self._analyze_intent(request.message)
        request.metadata["intent"] = context["intent"]

        # Research
        context["research_output"] = await invoke_research(request.message, context)

        # Iris enrichment (Phase 5: Now gets company from identity when available)
        context["iris_context"] = await invoke_iris_enrich(context)

        # Write
        try:
            draft = await invoke_write(request.message, context)
        except RuntimeError as e:
            if "unavailable" in str(e).lower():
                return GatewayResponse(
                    response="Writing service unavailable.",
                    intent=context["intent"],
                )
            raise

        # Verify
        verified = await invoke_verify(draft, request.message, context)

        # Reflection (fire-and-forget)
        try:
            await invoke_reflect({
                "user_message": request.message,
                "response": verified,
                "intent": context["intent"],
                "results": context,
            })
        except Exception as e:
            logger.debug(f"Reflection skipped: {e}")

        # Holistic: record breath (pipeline timing) and check immune status
        try:
            _total_ms = (time.monotonic() - _start_time) * 1000
            from openclaw.agents.ira.src.holistic.respiratory_system import get_respiratory_system
            get_respiratory_system().record_breath(
                request_id=_request_id,
                total_latency_ms=_total_ms,
                phase_timings=_phase_timings,
                success=True,
                channel=request.channel,
            )
        except Exception:
            pass

        return GatewayResponse(
            response=verified,
            intent=context["intent"],
            metadata={"channel": request.channel, "request_id": _request_id},
        )

    async def process_telegram(self, message: str, user_id: str = "unknown") -> GatewayResponse:
        """Format a Telegram message and process through the pipeline."""
        req = GatewayRequest(
            message=message,
            channel="telegram",
            user_id=user_id,
            metadata={"source": "telegram"},
        )
        return await self.process(req)

    async def process_email(self, message: str, user_id: str = "unknown") -> GatewayResponse:
        """Format an email and process through the pipeline."""
        req = GatewayRequest(
            message=message,
            channel="email",
            user_id=user_id,
            metadata={"source": "email"},
        )
        return await self.process(req)


    async def process_tool_mode(self, request: GatewayRequest) -> GatewayResponse:
        """
        P2: LLM-driven pipeline using tool calls. Athena chooses skills.
        """
        try:
            from openclaw.agents.ira.src.core.tool_orchestrator import process_with_tools
            response = await process_with_tools(
                request.message, request.channel, request.user_id, dict(request.metadata)
            )
            return GatewayResponse(response=response, intent="tool_orchestrated", metadata={})
        except Exception as e:
            logger.warning("Tool orchestration failed, falling back: %s", e)
            return await self.process(request)

    async def health(self) -> Dict[str, Any]:
        """
        Report which skills are available. Mitigates lazy-loading uncertainty.
        """
        return {"status": "ok", "skills": get_skill_availability()}
