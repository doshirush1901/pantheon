"""
Company Configuration — the single customization point for Pantheon agents.

Users provide an agent.yaml file describing their company, persona, products,
competitors, and memory namespaces. Every module reads from this config instead
of hardcoding company-specific strings.

Usage:
    from openclaw.agents.ira.src.core.company_config import get_config, CompanyConfig
    cfg = get_config()
    print(cfg.company.name)           # "Machinecraft Technologies"
    print(cfg.memory.ns("customers")) # "machinecraft_customers"
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("pantheon.config")

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent


# ============================================================================
# CONFIG DATA CLASSES
# ============================================================================

@dataclass
class CompanyInfo:
    name: str = "My Company"
    domain: str = "example.com"
    agent_name: str = "Agent"
    agent_email: str = "agent@example.com"
    admin_email: str = "admin@example.com"
    admin_telegram_id: str = ""
    tagline: str = ""

    @property
    def agent_signature(self) -> str:
        return f"{self.agent_name}\n{self.name}\n{self.agent_email}"


@dataclass
class PersonaConfig:
    role: str = "AI Sales Assistant"
    tone: str = "Professional, warm, data-driven"
    style: str = "Clear and confident"
    avoid: str = "Jargon, vague claims, excessive exclamation marks"


@dataclass
class MemoryNamespaces:
    customers: str = "customers"
    knowledge: str = "knowledge"
    pricing: str = "pricing"
    processes: str = "processes"
    general: str = "general"
    corrections: str = "corrections"

    def ns(self, key: str) -> str:
        """Get a namespace by key, with company prefix."""
        return getattr(self, key, key)

    def all_search_ids(self) -> List[str]:
        return [self.knowledge, self.customers, self.pricing, self.processes, self.general]


@dataclass
class ProductConfig:
    specs_file: str = "data/brain/product_specs.json"
    rules_file: str = "data/brain/rules.txt"
    critical_rules: List[str] = field(default_factory=list)

    def specs_path(self, project_root: Path) -> Path:
        return project_root / self.specs_file

    def rules_path(self, project_root: Path) -> Path:
        return project_root / self.rules_file


@dataclass
class CompetitorEntry:
    name: str = ""
    country: str = ""
    positioning: str = ""


@dataclass
class CompetitorConfig:
    entries: List[CompetitorEntry] = field(default_factory=list)
    our_positioning: str = ""

    @property
    def names(self) -> List[str]:
        return [e.name for e in self.entries]


@dataclass
class CompanyConfig:
    """Top-level config — everything a Pantheon agent needs to know about its company."""
    company: CompanyInfo = field(default_factory=CompanyInfo)
    persona: PersonaConfig = field(default_factory=PersonaConfig)
    memory: MemoryNamespaces = field(default_factory=MemoryNamespaces)
    products: ProductConfig = field(default_factory=ProductConfig)
    competitors: CompetitorConfig = field(default_factory=CompetitorConfig)
    extra: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# YAML LOADER
# ============================================================================

def _load_yaml(path: Path) -> dict:
    """Load YAML with env var interpolation (${VAR} syntax)."""
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not installed — using empty config. pip install pyyaml")
        return {}

    if not path.exists():
        return {}

    text = path.read_text()

    # Interpolate ${ENV_VAR} references
    import re
    def _replace_env(match):
        var = match.group(1)
        return os.environ.get(var, match.group(0))
    text = re.sub(r'\$\{(\w+)\}', _replace_env, text)

    return yaml.safe_load(text) or {}


def load_config(config_path: Optional[str] = None) -> CompanyConfig:
    """Load company config from agent.yaml.
    
    Search order:
    1. Explicit path (if provided)
    2. PANTHEON_CONFIG env var
    3. agent.yaml in project root
    4. Built-in defaults
    """
    if config_path:
        path = Path(config_path)
    elif os.environ.get("PANTHEON_CONFIG"):
        path = Path(os.environ["PANTHEON_CONFIG"])
    else:
        path = _PROJECT_ROOT / "agent.yaml"

    raw = _load_yaml(path)
    if not raw:
        logger.info("No agent.yaml found at %s — using defaults", path)
        return _build_default_config()

    logger.info("Loaded company config from %s", path)
    return _parse_config(raw)


def _parse_config(raw: dict) -> CompanyConfig:
    co = raw.get("company", {})
    pe = raw.get("persona", {})
    me = raw.get("memory", {}).get("namespaces", {})
    pr = raw.get("products", {})
    comp = raw.get("competitors", {})

    company = CompanyInfo(
        name=co.get("name", "My Company"),
        domain=co.get("domain", "example.com"),
        agent_name=co.get("agent_name", "Agent"),
        agent_email=co.get("agent_email", "agent@example.com"),
        admin_email=co.get("admin_email", "admin@example.com"),
        admin_telegram_id=co.get("admin_telegram_id", os.environ.get("ADMIN_TELEGRAM_ID", "")),
        tagline=co.get("tagline", ""),
    )

    persona = PersonaConfig(
        role=pe.get("role", "AI Sales Assistant"),
        tone=pe.get("tone", "Professional, warm, data-driven"),
        style=pe.get("style", "Clear and confident"),
        avoid=pe.get("avoid", "Jargon, vague claims"),
    )

    prefix = company.name.lower().replace(" ", "_").split("_")[0]
    memory = MemoryNamespaces(
        customers=me.get("customers", f"{prefix}_customers"),
        knowledge=me.get("knowledge", f"{prefix}_knowledge"),
        pricing=me.get("pricing", f"{prefix}_pricing"),
        processes=me.get("processes", f"{prefix}_processes"),
        general=me.get("general", f"{prefix}_general"),
        corrections=me.get("corrections", f"system_{prefix}_corrections"),
    )

    products = ProductConfig(
        specs_file=pr.get("specs_file", "data/brain/product_specs.json"),
        rules_file=pr.get("rules_file", "data/brain/rules.txt"),
        critical_rules=pr.get("critical_rules", []),
    )

    competitor_entries = []
    for entry in comp.get("entries", []):
        competitor_entries.append(CompetitorEntry(
            name=entry.get("name", ""),
            country=entry.get("country", ""),
            positioning=entry.get("positioning", ""),
        ))

    competitors = CompetitorConfig(
        entries=competitor_entries,
        our_positioning=comp.get("our_positioning", ""),
    )

    return CompanyConfig(
        company=company,
        persona=persona,
        memory=memory,
        products=products,
        competitors=competitors,
        extra=raw.get("extra", {}),
    )


def _build_default_config() -> CompanyConfig:
    """Build config from env vars when no agent.yaml exists (backward compat)."""
    admin_id = os.environ.get("RUSHABH_TELEGRAM_ID", os.environ.get("ADMIN_TELEGRAM_ID", ""))
    agent_email = os.environ.get("IRA_EMAIL", "agent@example.com")

    domain = agent_email.split("@")[1] if "@" in agent_email else "example.com"

    return CompanyConfig(
        company=CompanyInfo(
            name=os.environ.get("COMPANY_NAME", "My Company"),
            domain=domain,
            agent_name=os.environ.get("AGENT_NAME", "Agent"),
            agent_email=agent_email,
            admin_email=os.environ.get("ADMIN_EMAIL", ""),
            admin_telegram_id=admin_id,
        ),
        memory=MemoryNamespaces(
            customers=os.environ.get("MEM0_NS_CUSTOMERS", "customers"),
            knowledge=os.environ.get("MEM0_NS_KNOWLEDGE", "knowledge"),
            pricing=os.environ.get("MEM0_NS_PRICING", "pricing"),
            processes=os.environ.get("MEM0_NS_PROCESSES", "processes"),
            general=os.environ.get("MEM0_NS_GENERAL", "general"),
        ),
    )


# ============================================================================
# SINGLETON
# ============================================================================

_config: Optional[CompanyConfig] = None


def get_config() -> CompanyConfig:
    """Get the global company config (lazy-loaded singleton)."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(config: CompanyConfig) -> None:
    """Override the global config (for testing or programmatic setup)."""
    global _config
    _config = config


def reset_config() -> None:
    """Force reload on next get_config() call."""
    global _config
    _config = None
