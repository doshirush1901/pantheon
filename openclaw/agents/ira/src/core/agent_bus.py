"""
Agent Bus — Manus-style agent-to-agent communication.

Enables agents to collaborate autonomously without Athena mediating every step.
Agents post messages to the bus; other agents subscribe to relevant topics and
can spawn sub-tasks, pass results, or request help from peers.

Architecture:
    AgentBus (singleton)
      ├── dispatch(sender, target, task, data) → result
      ├── broadcast(sender, topic, data) → list of results
      └── chain(steps) → final result (sequential agent pipeline)

    Each agent registers capabilities. When Clio needs intelligence, she calls
    bus.dispatch("clio", "iris", "enrich_company", {...}) directly — no LLM round-trip.

Usage from any agent:
    from openclaw.agents.ira.src.core.agent_bus import get_bus
    bus = get_bus()
    intel = await bus.dispatch("hermes", "iris", "enrich_company", {"company": "TSN", "country": "Germany"})
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

logger = logging.getLogger("ira.agent_bus")


@dataclass
class BusMessage:
    sender: str
    target: str
    task: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    trace_id: str = ""


@dataclass
class BusResult:
    sender: str
    target: str
    task: str
    result: Any
    elapsed_ms: float = 0.0
    success: bool = True
    error: str = ""


AgentHandler = Callable[..., Coroutine[Any, Any, Any]]


class AgentBus:
    """Central message bus for agent-to-agent communication."""

    def __init__(self):
        self._handlers: Dict[str, Dict[str, AgentHandler]] = {}
        self._trace_log: List[Dict] = []
        self._max_trace = 200

    def register(self, agent_name: str, task: str, handler: AgentHandler):
        """Register an agent's capability on the bus."""
        if agent_name not in self._handlers:
            self._handlers[agent_name] = {}
        self._handlers[agent_name][task] = handler
        logger.debug(f"[Bus] Registered {agent_name}.{task}")

    def registered_agents(self) -> Dict[str, List[str]]:
        """Return map of agent -> list of registered tasks."""
        return {agent: list(tasks.keys()) for agent, tasks in self._handlers.items()}

    async def dispatch(
        self,
        sender: str,
        target: str,
        task: str,
        data: Dict[str, Any] = None,
        timeout: float = 60.0,
    ) -> BusResult:
        """Send a task from one agent to another. Returns the result."""
        data = data or {}
        msg = BusMessage(sender=sender, target=target, task=task, data=data)

        handler = self._handlers.get(target, {}).get(task)
        if not handler:
            err = f"No handler for {target}.{task}"
            logger.warning(f"[Bus] {sender} -> {target}.{task}: {err}")
            return BusResult(sender=sender, target=target, task=task,
                             result=None, success=False, error=err)

        t0 = time.time()
        try:
            result = await asyncio.wait_for(handler(**data), timeout=timeout)
            elapsed = (time.time() - t0) * 1000
            logger.info(f"[Bus] {sender} -> {target}.{task} OK ({elapsed:.0f}ms)")
            self._log_trace(msg, elapsed, True)

            self._signal_endocrine(target, success=True)

            return BusResult(sender=sender, target=target, task=task,
                             result=result, elapsed_ms=elapsed)
        except asyncio.TimeoutError:
            elapsed = (time.time() - t0) * 1000
            err = f"Timeout after {timeout}s"
            logger.error(f"[Bus] {sender} -> {target}.{task}: {err}")
            self._log_trace(msg, elapsed, False, err)
            self._signal_endocrine(target, success=False)
            return BusResult(sender=sender, target=target, task=task,
                             result=None, elapsed_ms=elapsed, success=False, error=err)
        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            err = f"{type(e).__name__}: {e}"
            logger.error(f"[Bus] {sender} -> {target}.{task}: {err}")
            self._log_trace(msg, elapsed, False, err)
            self._signal_endocrine(target, success=False)
            return BusResult(sender=sender, target=target, task=task,
                             result=None, elapsed_ms=elapsed, success=False, error=err)

    async def parallel_dispatch(
        self,
        sender: str,
        tasks: List[Tuple[str, str, Dict[str, Any]]],
        timeout: float = 60.0,
    ) -> List[BusResult]:
        """Fire multiple agent tasks concurrently. Each tuple is (target, task, data)."""
        coros = [
            self.dispatch(sender, target, task, data, timeout=timeout)
            for target, task, data in tasks
        ]
        return await asyncio.gather(*coros, return_exceptions=False)

    async def chain(
        self,
        sender: str,
        steps: List[Tuple[str, str]],
        initial_data: Dict[str, Any] = None,
        timeout_per_step: float = 60.0,
    ) -> BusResult:
        """Execute a sequential agent chain. Each step's output feeds the next.

        steps: list of (target_agent, task_name) tuples
        The result of each step is merged into the data dict for the next step.
        """
        data = dict(initial_data or {})
        last_result = None

        for i, (target, task) in enumerate(steps):
            result = await self.dispatch(sender, target, task, data, timeout=timeout_per_step)
            if not result.success:
                logger.warning(f"[Bus] Chain broke at step {i+1}/{len(steps)}: "
                               f"{target}.{task} — {result.error}")
                return result
            if isinstance(result.result, dict):
                data.update(result.result)
            else:
                data["_prev_result"] = result.result
            data["_chain_step"] = i + 1
            last_result = result

        return last_result

    async def research_deep(
        self,
        query: str,
        context: Dict[str, Any] = None,
        max_hops: int = 3,
    ) -> Dict[str, Any]:
        """Multi-hop research mode — agents collaborate autonomously.

        Hop 1: Clio researches + Iris gathers intelligence (parallel)
        Hop 2: If gaps found, Mnemosyne checks CRM + Plutus checks finance (parallel)
        Hop 3: Vera fact-checks the combined findings
        """
        context = context or {}
        findings: Dict[str, Any] = {"query": query, "hops": [], "sources": []}

        # Hop 1: Parallel research + intelligence
        hop1_tasks = []
        if "clio" in self._handlers and "research" in self._handlers.get("clio", {}):
            hop1_tasks.append(("clio", "research", {"query": query, "context": context}))
        if "iris" in self._handlers and "enrich_company" in self._handlers.get("iris", {}):
            company = context.get("company", "")
            if company:
                hop1_tasks.append(("iris", "enrich_company", {
                    "company": company,
                    "country": context.get("country", ""),
                }))

        if hop1_tasks:
            results = await self.parallel_dispatch("athena", hop1_tasks, timeout=45.0)
            hop1_data = {}
            for r in results:
                if r.success and r.result:
                    hop1_data[r.target] = r.result
                    findings["sources"].append(f"{r.target}.{r.task}")
            findings["hops"].append({"hop": 1, "agents": [t[0] for t in hop1_tasks], "data": hop1_data})

            # Hop 2: Fill gaps — CRM and finance if relevant
            if max_hops >= 2:
                hop2_tasks = []
                combined_text = str(hop1_data)
                needs_crm = any(w in query.lower() for w in
                                ["customer", "lead", "contact", "crm", "pipeline", "who"])
                needs_finance = any(w in query.lower() for w in
                                    ["order", "revenue", "payment", "cashflow", "financial", "money"])

                if needs_crm and "mnemosyne" in self._handlers:
                    if "lookup" in self._handlers.get("mnemosyne", {}):
                        hop2_tasks.append(("mnemosyne", "lookup", {"query": query, "context": context}))
                    if "pipeline" in self._handlers.get("mnemosyne", {}):
                        hop2_tasks.append(("mnemosyne", "pipeline", {"context": context}))

                if needs_finance and "plutus" in self._handlers:
                    if "order_book" in self._handlers.get("plutus", {}):
                        hop2_tasks.append(("plutus", "order_book", {"context": context}))

                if hop2_tasks:
                    results2 = await self.parallel_dispatch("athena", hop2_tasks, timeout=30.0)
                    hop2_data = {}
                    for r in results2:
                        if r.success and r.result:
                            hop2_data[r.target] = r.result
                            findings["sources"].append(f"{r.target}.{r.task}")
                    findings["hops"].append({"hop": 2, "agents": [t[0] for t in hop2_tasks], "data": hop2_data})

        # Hop 3: Vera fact-checks if we have substantial findings
        if max_hops >= 3 and "vera" in self._handlers and "verify" in self._handlers.get("vera", {}):
            all_text = "\n".join(
                str(hop.get("data", "")) for hop in findings["hops"]
            )
            if len(all_text) > 100:
                verify_result = await self.dispatch(
                    "athena", "vera", "verify",
                    {"draft": all_text[:8000], "query": query, "context": context},
                    timeout=30.0,
                )
                if verify_result.success:
                    findings["verified"] = True
                    findings["sources"].append("vera.verify")

        return findings

    def _signal_endocrine(self, agent_name: str, success: bool):
        """Signal the endocrine system about agent performance."""
        try:
            from openclaw.agents.ira.src.holistic.endocrine_system import get_endocrine_system
            endo = get_endocrine_system()
            if success:
                endo.signal_success(agent_name)
            else:
                endo.signal_failure(agent_name)
        except Exception:
            pass

    def _log_trace(self, msg: BusMessage, elapsed_ms: float, success: bool, error: str = ""):
        entry = {
            "sender": msg.sender, "target": msg.target, "task": msg.task,
            "elapsed_ms": round(elapsed_ms, 1), "success": success,
            "error": error, "ts": msg.timestamp,
        }
        self._trace_log.append(entry)
        if len(self._trace_log) > self._max_trace:
            self._trace_log = self._trace_log[-self._max_trace:]

    def get_trace(self, last_n: int = 20) -> List[Dict]:
        return self._trace_log[-last_n:]


_bus_instance: Optional[AgentBus] = None


def get_bus() -> AgentBus:
    """Get or create the singleton AgentBus."""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = AgentBus()
        _register_all_agents(_bus_instance)
    return _bus_instance


def _register_all_agents(bus: AgentBus):
    """Register all Pantheon agents on the bus with their capabilities."""

    # --- Clio (Researcher) ---
    async def _clio_research(query: str = "", context: Dict = None, **kw) -> str:
        from openclaw.agents.ira.src.skills.invocation import invoke_research
        return await invoke_research(query, context or {})

    bus.register("clio", "research", _clio_research)

    # --- Iris (Intelligence) ---
    async def _iris_enrich(company: str = "", country: str = "", **kw) -> Dict:
        try:
            from agents.iris.agent import Iris
            iris = Iris()
            return await iris.enrich_lead_async(company=company, country=country)
        except ImportError:
            try:
                from openclaw.agents.ira.src.skills.invocation import invoke_iris_enrich
                return await invoke_iris_enrich({"company": company, "country": country})
            except Exception:
                return {"error": "Iris unavailable"}

    bus.register("iris", "enrich_company", _iris_enrich)

    # --- Mnemosyne (CRM) ---
    async def _mnemosyne_lookup(query: str = "", context: Dict = None, **kw) -> str:
        from openclaw.agents.ira.src.skills.invocation import invoke_crm_lookup
        return await invoke_crm_lookup(query, context)

    async def _mnemosyne_pipeline(context: Dict = None, **kw) -> str:
        from openclaw.agents.ira.src.skills.invocation import invoke_crm_pipeline
        return await invoke_crm_pipeline(context)

    async def _mnemosyne_drip(context: Dict = None, **kw) -> str:
        from openclaw.agents.ira.src.skills.invocation import invoke_crm_drip
        return await invoke_crm_drip(context)

    bus.register("mnemosyne", "lookup", _mnemosyne_lookup)
    bus.register("mnemosyne", "pipeline", _mnemosyne_pipeline)
    bus.register("mnemosyne", "drip_candidates", _mnemosyne_drip)

    # --- Plutus (Finance) ---
    async def _plutus_overview(query: str = "", context: Dict = None, **kw) -> str:
        from openclaw.agents.ira.src.skills.invocation import invoke_finance_overview
        return await invoke_finance_overview(query, context)

    async def _plutus_order_book(context: Dict = None, **kw) -> str:
        from openclaw.agents.ira.src.skills.invocation import invoke_order_book_status
        return await invoke_order_book_status(context)

    async def _plutus_cashflow(context: Dict = None, **kw) -> str:
        from openclaw.agents.ira.src.skills.invocation import invoke_cashflow_forecast
        return await invoke_cashflow_forecast(context)

    bus.register("plutus", "overview", _plutus_overview)
    bus.register("plutus", "order_book", _plutus_order_book)
    bus.register("plutus", "cashflow", _plutus_cashflow)

    # --- Vera (Fact Checker) ---
    async def _vera_verify(draft: str = "", query: str = "", context: Dict = None, **kw) -> str:
        from openclaw.agents.ira.src.skills.invocation import invoke_verify
        return await invoke_verify(draft, query, context or {})

    bus.register("vera", "verify", _vera_verify)

    # --- Calliope (Writer) ---
    async def _calliope_write(message: str = "", context: Dict = None, **kw) -> str:
        from openclaw.agents.ira.src.skills.invocation import invoke_write
        return await invoke_write(message, context or {})

    bus.register("calliope", "write", _calliope_write)

    # --- Sophia (Reflector) ---
    async def _sophia_reflect(interaction_data: Dict = None, **kw) -> None:
        from openclaw.agents.ira.src.skills.invocation import invoke_reflect
        await invoke_reflect(interaction_data or {})

    bus.register("sophia", "reflect", _sophia_reflect)

    # --- Hephaestus (Forge) ---
    async def _hephaestus_forge(task: str = "", code: str = "", data: str = "",
                                 context: Dict = None, **kw) -> str:
        from openclaw.agents.ira.src.skills.invocation import invoke_hephaestus
        return await invoke_hephaestus(task=task, code=code, data=data, context=context)

    bus.register("hephaestus", "forge", _hephaestus_forge)

    # --- Prometheus (Discovery) ---
    async def _prometheus_scan(query: str = "", context: Dict = None, **kw) -> str:
        from openclaw.agents.ira.src.skills.invocation import invoke_discovery_scan
        return await invoke_discovery_scan(query, context)

    bus.register("prometheus", "scan", _prometheus_scan)

    logger.info(f"[Bus] Registered {len(bus._handlers)} agents: "
                f"{list(bus._handlers.keys())}")
