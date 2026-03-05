"""
Unified Skill Invocation - Single source of truth for skill execution.

Per The Covenant: no duplication. All skill invocation logic lives here.
Used by UnifiedGateway, StreamingGateway, and any future BusOrchestrator.
"""

import logging
from typing import Any, AsyncGenerator, Dict, Optional

logger = logging.getLogger("ira.skills.invocation")

# Sentinel for unavailable skills
UNAVAILABLE = object()


def _load_research() -> Any:
    """Lazy-load research skill."""
    try:
        from openclaw.agents.ira.src.agents.researcher.agent import research
        return research
    except ImportError as e:
        logger.warning(f"Research skill unavailable: {e}")
        return UNAVAILABLE


def _load_write() -> Any:
    """Lazy-load write skill."""
    try:
        from openclaw.agents.ira.src.agents.writer.agent import write
        return write
    except ImportError as e:
        logger.warning(f"Write skill unavailable: {e}")
        return UNAVAILABLE


def _load_write_streaming() -> Any:
    """Lazy-load write_streaming skill."""
    try:
        from openclaw.agents.ira.src.agents.writer.agent import write_streaming
        return write_streaming
    except ImportError as e:
        logger.warning(f"Write streaming skill unavailable: {e}")
        return UNAVAILABLE


def _load_verify() -> Any:
    """Lazy-load verify skill."""
    try:
        from openclaw.agents.ira.src.agents.fact_checker.agent import verify
        return verify
    except ImportError as e:
        logger.warning(f"Verify skill unavailable: {e}")
        return UNAVAILABLE


def _load_iris_enrich() -> Any:
    """Lazy-load iris_enrich skill."""
    try:
        from openclaw.agents.ira.src.agents.iris_skill import iris_enrich
        return iris_enrich
    except ImportError as e:
        logger.warning(f"Iris enrich skill unavailable: {e}")
        return UNAVAILABLE


def _load_reflect() -> Any:
    """Lazy-load reflect skill."""
    try:
        from openclaw.agents.ira.src.agents.reflector.agent import reflect
        return reflect
    except ImportError as e:
        logger.warning(f"Reflect skill unavailable: {e}")
        return UNAVAILABLE


def _load_crm_lookup() -> Any:
    """Lazy-load Mnemosyne CRM lookup skill."""
    try:
        from openclaw.agents.ira.src.agents.crm_agent.agent import lookup_contact
        return lookup_contact
    except ImportError as e:
        logger.warning(f"CRM lookup skill unavailable: {e}")
        return UNAVAILABLE


def _load_crm_list_customers() -> Any:
    """Lazy-load Mnemosyne list all customers skill."""
    try:
        from openclaw.agents.ira.src.agents.crm_agent.agent import list_all_customers
        return list_all_customers
    except ImportError as e:
        logger.warning(f"CRM list customers skill unavailable: {e}")
        return UNAVAILABLE


def _load_crm_pipeline() -> Any:
    """Lazy-load Mnemosyne pipeline overview skill."""
    try:
        from openclaw.agents.ira.src.agents.crm_agent.agent import get_pipeline_overview
        return get_pipeline_overview
    except ImportError as e:
        logger.warning(f"CRM pipeline skill unavailable: {e}")
        return UNAVAILABLE


def _load_crm_drip() -> Any:
    """Lazy-load Mnemosyne drip candidates skill."""
    try:
        from openclaw.agents.ira.src.agents.crm_agent.agent import get_drip_candidates
        return get_drip_candidates
    except ImportError as e:
        logger.warning(f"CRM drip skill unavailable: {e}")
        return UNAVAILABLE


def _load_finance_overview() -> Any:
    """Lazy-load Plutus finance overview skill."""
    try:
        from openclaw.agents.ira.src.agents.finance_agent.agent import finance_overview
        return finance_overview
    except ImportError as e:
        logger.warning(f"Finance overview skill unavailable: {e}")
        return UNAVAILABLE


def _load_order_book_status() -> Any:
    """Lazy-load Plutus order book status skill."""
    try:
        from openclaw.agents.ira.src.agents.finance_agent.agent import order_book_status
        return order_book_status
    except ImportError as e:
        logger.warning(f"Order book status skill unavailable: {e}")
        return UNAVAILABLE


def _load_cashflow_forecast() -> Any:
    """Lazy-load Plutus cashflow forecast skill."""
    try:
        from openclaw.agents.ira.src.agents.finance_agent.agent import cashflow_forecast
        return cashflow_forecast
    except ImportError as e:
        logger.warning(f"Cashflow forecast skill unavailable: {e}")
        return UNAVAILABLE


def _load_revenue_history() -> Any:
    """Lazy-load Plutus revenue history skill."""
    try:
        from openclaw.agents.ira.src.agents.finance_agent.agent import revenue_history
        return revenue_history
    except ImportError as e:
        logger.warning(f"Revenue history skill unavailable: {e}")
        return UNAVAILABLE


def _load_net_cashflow() -> Any:
    """Lazy-load Plutus net cashflow."""
    try:
        from openclaw.agents.ira.src.agents.finance_agent.agent import net_cashflow
        return net_cashflow
    except ImportError as e:
        logger.warning(f"Plutus net_cashflow unavailable: {e}")
        return UNAVAILABLE


def _load_cash_position() -> Any:
    """Lazy-load Plutus cash position."""
    try:
        from openclaw.agents.ira.src.agents.finance_agent.agent import cash_position
        return cash_position
    except ImportError as e:
        logger.warning(f"Plutus cash_position unavailable: {e}")
        return UNAVAILABLE


def _load_payment_plan() -> Any:
    """Lazy-load Plutus payment plan."""
    try:
        from openclaw.agents.ira.src.agents.finance_agent.agent import payment_plan
        return payment_plan
    except ImportError as e:
        logger.warning(f"Plutus payment_plan unavailable: {e}")
        return UNAVAILABLE


def _load_project_summary() -> Any:
    """Lazy-load Atlas project summary skill."""
    try:
        from openclaw.agents.ira.src.agents.atlas.agent import project_summary
        return project_summary
    except ImportError as e:
        logger.warning(f"Atlas project_summary unavailable: {e}")
        return UNAVAILABLE


def _load_all_projects_overview() -> Any:
    """Lazy-load Atlas all projects overview skill."""
    try:
        from openclaw.agents.ira.src.agents.atlas.agent import all_projects_overview
        return all_projects_overview
    except ImportError as e:
        logger.warning(f"Atlas all_projects_overview unavailable: {e}")
        return UNAVAILABLE


def _load_project_documents() -> Any:
    """Lazy-load Atlas project documents skill."""
    try:
        from openclaw.agents.ira.src.agents.atlas.agent import project_documents
        return project_documents
    except ImportError as e:
        logger.warning(f"Atlas project_documents unavailable: {e}")
        return UNAVAILABLE


def _load_project_logbook() -> Any:
    """Lazy-load Atlas project logbook skill."""
    try:
        from openclaw.agents.ira.src.agents.atlas.agent import project_logbook
        return project_logbook
    except ImportError as e:
        logger.warning(f"Atlas project_logbook unavailable: {e}")
        return UNAVAILABLE


def _load_machine_knowledge() -> Any:
    """Lazy-load Atlas machine knowledge skill."""
    try:
        from openclaw.agents.ira.src.agents.atlas.agent import machine_knowledge
        return machine_knowledge
    except ImportError as e:
        logger.warning(f"Atlas machine_knowledge unavailable: {e}")
        return UNAVAILABLE


def _load_risk_register() -> Any:
    """Lazy-load Atlas risk register."""
    try:
        from openclaw.agents.ira.src.agents.atlas.agent import risk_register
        return risk_register
    except ImportError as e:
        logger.warning(f"Atlas risk_register unavailable: {e}")
        return UNAVAILABLE


def _load_payment_alerts() -> Any:
    """Lazy-load Atlas payment alerts."""
    try:
        from openclaw.agents.ira.src.agents.atlas.agent import payment_alerts
        return payment_alerts
    except ImportError as e:
        logger.warning(f"Atlas payment_alerts unavailable: {e}")
        return UNAVAILABLE


def _load_vendor_status() -> Any:
    """Lazy-load Hera vendor status."""
    try:
        from openclaw.agents.ira.src.agents.hera.agent import vendor_status
        return vendor_status
    except ImportError as e:
        logger.warning(f"Hera vendor_status unavailable: {e}")
        return UNAVAILABLE


def _load_vendor_lead_time() -> Any:
    """Lazy-load Hera vendor lead time."""
    try:
        from openclaw.agents.ira.src.agents.hera.agent import component_lead_time
        return component_lead_time
    except ImportError as e:
        logger.warning(f"Hera vendor_lead_time unavailable: {e}")
        return UNAVAILABLE


def _load_vendor_outstanding() -> Any:
    """Lazy-load Hera vendor outstanding."""
    try:
        from openclaw.agents.ira.src.agents.hera.agent import vendor_outstanding
        return vendor_outstanding
    except ImportError as e:
        logger.warning(f"Hera vendor_outstanding unavailable: {e}")
        return UNAVAILABLE


def _load_punch_list() -> Any:
    """Lazy-load Asclepius punch list."""
    try:
        from openclaw.agents.ira.src.agents.asclepius.agent import punch_list
        return punch_list
    except ImportError as e:
        logger.warning(f"Asclepius punch_list unavailable: {e}")
        return UNAVAILABLE


def _load_log_punch_item() -> Any:
    """Lazy-load Asclepius log punch item."""
    try:
        from openclaw.agents.ira.src.agents.asclepius.agent import log_punch_item
        return log_punch_item
    except ImportError as e:
        logger.warning(f"Asclepius log_punch_item unavailable: {e}")
        return UNAVAILABLE


def _load_close_punch_item() -> Any:
    """Lazy-load Asclepius close punch item."""
    try:
        from openclaw.agents.ira.src.agents.asclepius.agent import close_punch_item
        return close_punch_item
    except ImportError as e:
        logger.warning(f"Asclepius close_punch_item unavailable: {e}")
        return UNAVAILABLE


def _load_quality_dashboard() -> Any:
    """Lazy-load Asclepius quality dashboard."""
    try:
        from openclaw.agents.ira.src.agents.asclepius.agent import quality_dashboard
        return quality_dashboard
    except ImportError as e:
        logger.warning(f"Asclepius quality_dashboard unavailable: {e}")
        return UNAVAILABLE


def _load_pipeline_forecast() -> Any:
    """Lazy-load Tyche pipeline forecast skill."""
    try:
        from openclaw.agents.ira.src.agents.tyche.agent import pipeline_forecast
        return pipeline_forecast
    except ImportError as e:
        logger.warning(f"Tyche pipeline_forecast unavailable: {e}")
        return UNAVAILABLE


def _load_win_loss_analysis() -> Any:
    """Lazy-load Tyche win/loss analysis skill."""
    try:
        from openclaw.agents.ira.src.agents.tyche.agent import win_loss_analysis
        return win_loss_analysis
    except ImportError as e:
        logger.warning(f"Tyche win_loss_analysis unavailable: {e}")
        return UNAVAILABLE


def _load_deal_velocity() -> Any:
    """Lazy-load Tyche deal velocity skill."""
    try:
        from openclaw.agents.ira.src.agents.tyche.agent import deal_velocity
        return deal_velocity
    except ImportError as e:
        logger.warning(f"Tyche deal_velocity unavailable: {e}")
        return UNAVAILABLE


def _load_identity() -> Any:
    """Lazy-load identity service."""
    try:
        from openclaw.agents.ira.src.identity.unified_identity import UnifiedIdentityService
        return UnifiedIdentityService()
    except ImportError as e:
        logger.warning(f"Identity service unavailable: {e}")
        return UNAVAILABLE


def _load_discovery_scan() -> Any:
    """Lazy-load Prometheus discovery scan skill."""
    try:
        from openclaw.agents.ira.src.agents.prometheus.agent import discovery_scan
        return discovery_scan
    except ImportError as e:
        logger.warning(f"Discovery scan skill unavailable: {e}")
        return UNAVAILABLE


def _load_hephaestus() -> Any:
    """Lazy-load Hephaestus forge skill (program builder)."""
    try:
        from openclaw.agents.ira.src.agents.hephaestus.agent import forge
        return forge
    except ImportError as e:
        logger.warning(f"Hephaestus forge skill unavailable: {e}")
        return UNAVAILABLE


async def invoke_research(message: str, context: Dict[str, Any]) -> str:
    """
    Invoke research skill. Returns research output string.
    """
    fn = _load_research()
    if fn is UNAVAILABLE:
        return ""
    return await fn(message, context)


async def invoke_write(message: str, context: Dict[str, Any]) -> str:
    """
    Invoke write skill. Returns draft string.
    """
    fn = _load_write()
    if fn is UNAVAILABLE:
        raise RuntimeError("Write skill unavailable")
    return await fn(message, context)


async def invoke_write_streaming(
    message: str, context: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    """
    Invoke write_streaming skill. Yields tokens.
    """
    fn = _load_write_streaming()
    if fn is UNAVAILABLE:
        yield "Error: Write streaming unavailable."
        return
    async for token in fn(message, context):
        yield token


async def invoke_verify(
    draft: str, original_query: str, context: Dict[str, Any]
) -> str:
    """
    Invoke verify skill. Returns verified draft.
    """
    fn = _load_verify()
    if fn is UNAVAILABLE:
        return draft
    return await fn(draft, original_query, context)


async def invoke_iris_enrich(context: Dict[str, Any]) -> Dict[str, str]:
    """
    Invoke iris_enrich skill. Returns email-ready dict.
    """
    fn = _load_iris_enrich()
    if fn is UNAVAILABLE:
        return {}
    return await fn(context)


async def invoke_reflect(interaction_data: Dict[str, Any]) -> None:
    """
    Invoke reflect skill. Fire-and-forget.
    """
    fn = _load_reflect()
    if fn is UNAVAILABLE:
        return
    await fn(interaction_data)


async def invoke_crm_lookup(query: str, context: Dict[str, Any] = None) -> str:
    """Invoke Mnemosyne CRM lookup. Returns contact/lead brief."""
    fn = _load_crm_lookup()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(query, context)


async def invoke_crm_list_customers(context: Dict[str, Any] = None) -> str:
    """Invoke Mnemosyne to list all customers."""
    fn = _load_crm_list_customers()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(context)


async def invoke_crm_pipeline(context: Dict[str, Any] = None) -> str:
    """Invoke Mnemosyne pipeline overview."""
    fn = _load_crm_pipeline()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(context)


async def invoke_crm_drip(context: Dict[str, Any] = None) -> str:
    """Invoke Mnemosyne drip candidates."""
    fn = _load_crm_drip()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(context)


async def invoke_finance_overview(query: str, context: Dict[str, Any] = None) -> str:
    """Invoke Plutus finance overview."""
    fn = _load_finance_overview()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(query, context)


async def invoke_order_book_status(context: Dict[str, Any] = None) -> str:
    """Invoke Plutus order book status."""
    fn = _load_order_book_status()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(context)


async def invoke_cashflow_forecast(context: Dict[str, Any] = None) -> str:
    """Invoke Plutus cashflow forecast."""
    fn = _load_cashflow_forecast()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(context)


async def invoke_revenue_history(query: str, context: Dict[str, Any] = None) -> str:
    """Invoke Plutus revenue history."""
    fn = _load_revenue_history()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(query, context)


async def invoke_net_cashflow(context: Dict[str, Any] = None) -> str:
    """Invoke Plutus net cashflow."""
    fn = _load_net_cashflow()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(context)


async def invoke_cash_position(context: Dict[str, Any] = None) -> str:
    """Invoke Plutus cash position."""
    fn = _load_cash_position()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(context)


async def invoke_payment_plan(context: Dict[str, Any] = None) -> str:
    """Invoke Plutus payment plan."""
    fn = _load_payment_plan()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(context)


async def invoke_project_summary(query: str, context: Dict[str, Any] = None) -> str:
    """Invoke Atlas project summary."""
    fn = _load_project_summary()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(query, context)


async def invoke_all_projects_overview(context: Dict[str, Any] = None) -> str:
    """Invoke Atlas all projects overview."""
    fn = _load_all_projects_overview()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(context)


async def invoke_project_documents(query: str, context: Dict[str, Any] = None) -> str:
    """Invoke Atlas project documents."""
    fn = _load_project_documents()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(query, context)


async def invoke_project_logbook(query: str, context: Dict[str, Any] = None) -> str:
    """Invoke Atlas project logbook."""
    fn = _load_project_logbook()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(query, context)


async def invoke_machine_knowledge(query: str, context: Dict[str, Any] = None) -> str:
    """Invoke Atlas machine knowledge."""
    fn = _load_machine_knowledge()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(query, context)


async def invoke_risk_register(context: Dict[str, Any] = None) -> str:
    """Invoke Atlas risk register."""
    fn = _load_risk_register()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(context)


async def invoke_payment_alerts(context: Dict[str, Any] = None) -> str:
    """Invoke Atlas payment alerts."""
    fn = _load_payment_alerts()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(context)


async def invoke_vendor_status(context: Dict[str, Any] = None) -> str:
    """Invoke Hera vendor status."""
    fn = _load_vendor_status()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(context)


async def invoke_vendor_lead_time(query: str, context: Dict[str, Any] = None) -> str:
    """Invoke Hera vendor lead time."""
    fn = _load_vendor_lead_time()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(query, context)


async def invoke_vendor_outstanding(query: str = "", context: Dict[str, Any] = None) -> str:
    """Invoke Hera vendor outstanding."""
    fn = _load_vendor_outstanding()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(query, context)


async def invoke_punch_list(query: str, context: Dict[str, Any] = None) -> str:
    """Invoke Asclepius punch list."""
    fn = _load_punch_list()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(query, context)


async def invoke_log_punch_item(arguments: Dict[str, Any], context: Dict[str, Any] = None) -> str:
    """Invoke Asclepius log punch item."""
    fn = _load_log_punch_item()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return fn(
        customer=arguments.get("customer", ""),
        description=arguments.get("description", ""),
        category=arguments.get("category", "mechanical"),
        severity=arguments.get("severity", "major"),
        assigned_to=arguments.get("assigned_to", ""),
        phase=arguments.get("phase", ""),
    )


async def invoke_close_punch_item(arguments: Dict[str, Any], context: Dict[str, Any] = None) -> str:
    """Invoke Asclepius close punch item."""
    fn = _load_close_punch_item()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return fn(
        customer=arguments.get("customer", ""),
        item_description=arguments.get("item_description", ""),
        resolution_notes=arguments.get("resolution_notes", ""),
    )


async def invoke_quality_dashboard(context: Dict[str, Any] = None) -> str:
    """Invoke Asclepius quality dashboard."""
    fn = _load_quality_dashboard()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(context)


async def invoke_pipeline_forecast(query: str = "", context: Dict[str, Any] = None) -> str:
    """Invoke Tyche pipeline forecast."""
    fn = _load_pipeline_forecast()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(query, context=context)


async def invoke_win_loss_analysis(
    region: str = "", machine_type: str = "", context: Dict[str, Any] = None
) -> str:
    """Invoke Tyche win/loss analysis."""
    fn = _load_win_loss_analysis()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(region=region, machine_type=machine_type, context=context)


async def invoke_deal_velocity(context: Dict[str, Any] = None) -> str:
    """Invoke Tyche deal velocity."""
    fn = _load_deal_velocity()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(context=context)


async def invoke_discovery_scan(query: str, context: Dict[str, Any] = None) -> str:
    """Invoke Prometheus discovery scan. Returns opportunity report."""
    fn = _load_discovery_scan()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(query, context)


async def invoke_hephaestus(
    task: str = "",
    code: str = "",
    data: str = "",
    context: Dict[str, Any] = None,
) -> str:
    """Invoke Hephaestus to forge and execute a program.

    Can be called with a natural-language task (Hephaestus writes the code)
    or with pre-written code. Data from previous tool calls is passed through.
    """
    fn = _load_hephaestus()
    if fn is UNAVAILABLE:
        return "(Tool unavailable — module not installed)"
    return await fn(task=task, code=code, data=data, context=context)


def invoke_identity_resolve(channel: str, identifier: str) -> Optional[str]:
    """
    Invoke identity service resolve. Sync.
    """
    svc = _load_identity()
    if svc is UNAVAILABLE or not hasattr(svc, "resolve"):
        return "(Tool unavailable — module not installed)"
    return svc.resolve(channel, identifier)


def get_skill_availability() -> Dict[str, str]:
    """
    Report which skills are available. For health checks.
    """
    result: Dict[str, str] = {}
    for name, loader in [
        ("research", _load_research),
        ("write", _load_write),
        ("write_streaming", _load_write_streaming),
        ("verify", _load_verify),
        ("iris_enrich", _load_iris_enrich),
        ("reflect", _load_reflect),
        ("crm_lookup", _load_crm_lookup),
        ("crm_list_customers", _load_crm_list_customers),
        ("crm_pipeline", _load_crm_pipeline),
        ("crm_drip", _load_crm_drip),
        ("finance_overview", _load_finance_overview),
        ("order_book_status", _load_order_book_status),
        ("cashflow_forecast", _load_cashflow_forecast),
        ("revenue_history", _load_revenue_history),
        ("net_cashflow", _load_net_cashflow),
        ("cash_position", _load_cash_position),
        ("payment_plan", _load_payment_plan),
        ("discovery_scan", _load_discovery_scan),
        ("hephaestus", _load_hephaestus),
        ("identity", _load_identity),
        ("project_summary", _load_project_summary),
        ("all_projects_overview", _load_all_projects_overview),
        ("project_documents", _load_project_documents),
        ("project_logbook", _load_project_logbook),
        ("machine_knowledge", _load_machine_knowledge),
        ("risk_register", _load_risk_register),
        ("payment_alerts", _load_payment_alerts),
        ("vendor_status", _load_vendor_status),
        ("vendor_lead_time", _load_vendor_lead_time),
        ("vendor_outstanding", _load_vendor_outstanding),
        ("pipeline_forecast", _load_pipeline_forecast),
        ("win_loss_analysis", _load_win_loss_analysis),
        ("deal_velocity", _load_deal_velocity),
    ]:
        try:
            val = loader()
            result[name] = "available" if val is not UNAVAILABLE else "unavailable"
        except Exception as e:
            result[name] = f"error: {e}"
    return result
