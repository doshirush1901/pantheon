"""
Ira Configuration - Single Source of Truth

All configuration values should be imported from this module.
This ensures consistency across all Ira components.

Usage:
    from openclaw.agents.ira.config import (
        DATABASE_URL, QDRANT_URL, VOYAGE_API_KEY,
        COLLECTIONS, load_soul
    )
"""

import fcntl
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
import functools
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, TypeVar, Union, Tuple

T = TypeVar('T')

# =============================================================================
# LOGGING SETUP
# =============================================================================

# Standard format for all Ira logs
LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Log level from environment
LOG_LEVEL = os.environ.get("IRA_LOG_LEVEL", "INFO").upper()

# Configure root logger for Ira
_logging_configured = False


def setup_logging(level: str = None, log_file: Optional[Path] = None) -> None:
    """
    Configure logging for all Ira modules.
    
    Call once at startup (e.g., in main entry point).
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to IRA_LOG_LEVEL env var.
        log_file: Optional file path to write logs to.
    """
    global _logging_configured
    
    if _logging_configured:
        return
    
    level = level or LOG_LEVEL
    
    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    
    # Configure root logger for ira namespace
    root_logger = logging.getLogger("ira")
    root_logger.setLevel(getattr(logging, level, logging.INFO))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for an Ira module.
    
    Usage:
        from config import get_logger
        
        logger = get_logger(__name__)
        logger.info("Processing started")
        logger.warning("Something unusual")
        logger.error("Something failed", exc_info=True)
    
    Args:
        name: Module name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    # Ensure logging is configured
    if not _logging_configured:
        setup_logging()
    
    # Create logger under ira namespace
    if name.startswith("openclaw.agents.ira"):
        short_name = name.replace("openclaw.agents.ira.", "ira.")
    elif not name.startswith("ira"):
        short_name = f"ira.{name}"
    else:
        short_name = name
    
    return logging.getLogger(short_name)


_logger = get_logger(__name__)

# =============================================================================
# PATHS
# =============================================================================

CONFIG_DIR = Path(__file__).parent
AGENT_DIR = CONFIG_DIR
SKILLS_DIR = AGENT_DIR / "src"
PROJECT_ROOT = AGENT_DIR.parent.parent.parent
WORKSPACE_DIR = CONFIG_DIR / "workspace"

# OpenClaw workspace (external)
OPENCLAW_WORKSPACE = Path.home() / ".openclaw" / "workspace"

# =============================================================================
# IMPORT PATH SETUP
# =============================================================================

_paths_configured = False

def setup_import_paths() -> None:
    """
    Configure Python path for cross-module imports.
    
    This is a CENTRALIZED alternative to scattered sys.path.insert() calls.
    Call this ONCE at the start of any script that needs cross-skill imports.
    
    Usage:
        # At the top of your module, after standard imports:
        from openclaw.agents.ira.config import setup_import_paths
        setup_import_paths()
        
        # Now you can import from other skills:
        from common.patterns import MACHINE_PATTERNS
        from conversation.entity_extractor import EntityExtractor
    
    Note: For proper package development, consider using:
        pip install -e .
    from the project root with a proper setup.py/pyproject.toml
    """
    global _paths_configured
    
    if _paths_configured:
        return
    
    # Add paths in priority order (first = highest priority)
    paths_to_add = [
        str(AGENT_DIR),                    # For 'from config import ...'
        str(SKILLS_DIR / "common"),        # For 'from patterns import ...'
        str(SKILLS_DIR / "brain"),         # For 'from brain.* import ...'
        str(SKILLS_DIR / "conversation"),  # For 'from conversation.* import ...'
        str(SKILLS_DIR / "memory"),        # For 'from memory.* import ...'
        str(SKILLS_DIR / "identity"),      # For 'from identity.* import ...'
        str(SKILLS_DIR / "market_research"),   # For 'from market_research.* import ...'
        str(PROJECT_ROOT),                 # For 'from openclaw.* import ...'
    ]
    
    for path in reversed(paths_to_add):  # Reverse so first item has highest priority
        if path not in sys.path:
            sys.path.insert(0, path)
    
    _paths_configured = True
    _logger.debug(f"[config] Import paths configured ({len(paths_to_add)} paths)")


# =============================================================================
# ENVIRONMENT LOADING
# =============================================================================

_env_loaded = False


def load_environment(env_file: Path = None) -> bool:
    """
    Load environment variables from .env file.
    
    This is the CANONICAL environment loader for all IRA scripts.
    Replace all custom load_env() functions with this.
    
    Usage:
        from openclaw.agents.ira.config import load_environment
        load_environment()
        
        # Or with custom path:
        load_environment(Path("/custom/path/.env"))
    
    Returns:
        True if .env file was loaded, False if not found
    """
    global _env_loaded
    
    if _env_loaded and env_file is None:
        return True
    
    if env_file is None:
        env_file = PROJECT_ROOT / ".env"
    
    if not env_file.exists():
        _logger.debug(f"[config] .env file not found: {env_file}")
        return False
    
    try:
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            
            os.environ.setdefault(key, value)
        
        _env_loaded = True
        _logger.debug(f"[config] Environment loaded from {env_file}")
        return True
    except Exception as e:
        _logger.warning(f"[config] Failed to load .env: {e}")
        return False


# Backward compatibility alias
load_env = load_environment


def get_skill_path(skill_name: str) -> Path:
    """
    Get the path to a skill directory.
    
    Usage:
        from config import get_skill_path
        brain_path = get_skill_path("brain")
    
    Args:
        skill_name: Name of the skill (e.g., "brain", "conversation")
    
    Returns:
        Path to the skill directory
    """
    return SKILLS_DIR / skill_name


# Auto-configure paths when config is imported
# This allows simple imports from skills without manual setup
setup_import_paths()


# =============================================================================
# LOAD ENVIRONMENT
# =============================================================================

def _load_env():
    """Load environment variables from .env file."""
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)

_load_env()

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# PostgreSQL - Canonical connection string
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://ira:ira_password@localhost:5432/ira_db"
)

# Legacy aliases (for compatibility)
POSTGRES_URL = DATABASE_URL
DB_URL = DATABASE_URL

# =============================================================================
# DATABASE CONNECTION POOL
# =============================================================================

_connection_pool = None
_pool_lock = None

def get_db_pool():
    """Get or create the shared database connection pool.
    
    Uses psycopg2.pool.ThreadedConnectionPool for thread-safe pooling.
    Pool is created lazily on first use.
    
    Usage:
        from config import get_db_pool
        
        pool = get_db_pool()
        conn = pool.getconn()
        try:
            # Use connection
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
        finally:
            pool.putconn(conn)
    
    Or use the context manager:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
    """
    global _connection_pool, _pool_lock
    
    if _pool_lock is None:
        import threading
        _pool_lock = threading.Lock()
    
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                try:
                    from psycopg2.pool import ThreadedConnectionPool
                    _connection_pool = ThreadedConnectionPool(
                        minconn=2,
                        maxconn=10,
                        dsn=DATABASE_URL
                    )
                except ImportError:
                    return None
                except Exception as e:
                    print(f"[config] Connection pool creation failed: {e}")
                    return None
    
    return _connection_pool


class _DBConnection:
    """Context manager for database connections from the pool."""
    
    def __init__(self):
        self.pool = get_db_pool()
        self.conn = None
    
    def __enter__(self):
        if self.pool is None:
            import psycopg2
            self.conn = psycopg2.connect(DATABASE_URL)
            return self.conn
        self.conn = self.pool.getconn()
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is not None:
                self.conn.rollback()
            else:
                self.conn.commit()
            
            if self.pool:
                self.pool.putconn(self.conn)
            else:
                self.conn.close()
        return False


def get_db_connection():
    """Get a database connection with automatic pool management.
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            rows = cursor.fetchall()
    
    Connection is automatically returned to pool (or closed) after use.
    Commits on success, rolls back on exception.
    """
    return _DBConnection()

# =============================================================================
# VECTOR DATABASE (QDRANT)
# =============================================================================

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_TIMEOUT = int(os.environ.get("QDRANT_TIMEOUT", "30"))

# Collection names - SINGLE SOURCE OF TRUTH
# These MUST match actual Qdrant collections!
COLLECTIONS = {
    # Document embeddings (Voyage) - ACTUAL NAMES
    "chunks_voyage": "ira_chunks_v4_voyage",
    "chunks_openai_large": "ira_chunks_v4_openai_large",
    "chunks_openai_small": "ira_chunks_openai_small_v3",  # May not exist
    
    # Email embeddings (Voyage) - ACTUAL NAMES
    "emails_voyage": "ira_emails_voyage_v2",
    "emails_openai_large": "ira_emails_v4_openai_large",
    "emails_openai_small": "ira_emails_openai_small_v3",  # May not exist
    
    # Market research
    "market_research": "ira_market_research_voyage",
    
    # Customer data
    "customers": "ira_customers",
    
    # User/Entity memories (Voyage-3, 1024d for consistency)
    "user_memories": "ira_user_memories_v2",  # Voyage-based
    "entity_memories": "ira_entity_memories_v2",  # Voyage-based
    "memories": "ira_memories",
    
    # Legacy memory collections (OpenAI, 1536d - being migrated)
    "user_memories_legacy": "ira_user_memories",
    "entity_memories_legacy": "ira_entity_memories",
    
    # Dream-learned knowledge (NEW - from nightly learning)
    "dream_knowledge": "ira_dream_knowledge_v1",
    
    # Discovered knowledge (from document scanning/ingestion)
    "discovered_knowledge": "ira_discovered_knowledge",
}

# Legacy collection mappings (for migration) - point old names to new
LEGACY_COLLECTIONS = {
    "ira_chunks_voyage_v3": COLLECTIONS["chunks_voyage"],
    "ira_emails_voyage_v3": COLLECTIONS["emails_voyage"],
}

# =============================================================================
# API KEYS
# =============================================================================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
MEM0_API_KEY = os.environ.get("MEM0_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# =============================================================================
# TELEGRAM
# =============================================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
EXPECTED_CHAT_ID = os.environ.get("EXPECTED_CHAT_ID", "")

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

# Embeddings
EMBEDDING_MODEL_VOYAGE = "voyage-3"
EMBEDDING_MODEL_OPENAI_LARGE = "text-embedding-3-large"
EMBEDDING_MODEL_OPENAI_SMALL = "text-embedding-3-small"

EMBEDDING_DIMENSIONS = {
    "voyage-3": 1024,
    "text-embedding-3-large": 3072,
    "text-embedding-3-small": 1536,
}

# LLM
DEFAULT_LLM_MODEL = os.environ.get("DEFAULT_LLM_MODEL", "gpt-4o")
FAST_LLM_MODEL = os.environ.get("FAST_LLM_MODEL", "gpt-4o-mini")

# =============================================================================
# COMPETITOR DATA (Centralized competitor intelligence)
# =============================================================================

COMPETITOR_DATA = {
    # European Premium (2-4x Machinecraft pricing)
    "ILLIG": {
        "country": "Germany",
        "price_range": "2-3x Machinecraft",
        "strengths": ["precision engineering", "automation options", "European quality standards", "long track record since 1946", "excellent tooling"],
        "weaknesses": ["high price", "long lead times (6-9 months)", "expensive spare parts", "service response in Asia/India"],
        "typical_customers": "Large multinationals, premium automotive OEMs, medical packaging",
        "positioning": "Premium European brand, established since 1946",
        "headquarters": "Heilbronn, Germany",
        "notable_models": ["RDM-K series", "UA series", "HSA series"],
    },
    "Kiefel": {
        "country": "Germany", 
        "price_range": "2.5-4x Machinecraft",
        "strengths": ["cutting-edge technology", "automotive focus", "Brückner group backing", "R&D innovation", "high automation"],
        "weaknesses": ["very high price", "complex machines require specialized training", "overkill for simple applications"],
        "typical_customers": "Tier 1 automotive suppliers, medical packaging, appliance interiors",
        "positioning": "High-end technology leader, premium pricing",
        "headquarters": "Freilassing, Germany (Brückner Group)",
        "notable_models": ["Speedformer KMD", "KIEFEL fiber thermoforming"],
    },
    "GEISS": {
        "country": "Germany",
        "price_range": "2-3x Machinecraft",
        "strengths": ["CNC integration", "twin-sheet thermoforming", "automation solutions", "German precision"],
        "weaknesses": ["high price", "complex systems", "long lead times", "requires skilled operators"],
        "typical_customers": "Automotive interiors, technical parts, twin-sheet applications",
        "positioning": "High-tech German thermoforming with CNC expertise",
        "headquarters": "Sesslach, Germany",
        "notable_models": ["T series", "DU series (twin-sheet)", "CNC trimming centers"],
    },
    "FRIMO": {
        "country": "Germany",
        "price_range": "2-3x Machinecraft",
        "strengths": ["IMG/lamination expertise", "automotive interiors focus", "comprehensive tooling", "slush molding"],
        "weaknesses": ["very specialized", "high price", "complex setup", "limited to automotive focus"],
        "typical_customers": "Automotive interior suppliers, IMG specialists, OEM interior programs",
        "positioning": "Specialist for automotive interior lamination and slush molding",
        "headquarters": "Lotte, Germany",
        "notable_models": ["FLEXpress", "IMG systems"],
    },
    
    # Asian Mid-Range (0.6-1.2x Machinecraft)
    "Ridat": {
        "country": "Taiwan",
        "price_range": "0.8-1.2x Machinecraft",
        "strengths": ["good value", "reliable machines", "global presence", "responsive support"],
        "weaknesses": ["limited automation options", "less innovation", "reputation concerns in premium markets"],
        "typical_customers": "Mid-market manufacturers, packaging companies",
        "positioning": "Value-oriented Asian option with global support",
        "headquarters": "Taiwan",
        "notable_models": ["Various standard models"],
    },
    "ZMD (China)": {
        "country": "China",
        "price_range": "0.4-0.7x Machinecraft",
        "strengths": ["very low price", "quick delivery", "good for simple applications"],
        "weaknesses": ["quality inconsistency", "limited service", "intellectual property concerns", "shorter lifespan"],
        "typical_customers": "Cost-focused buyers, startups, simple packaging",
        "positioning": "Budget option with acceptable quality for simple applications",
        "headquarters": "Various, China",
        "notable_models": ["Generic models"],
    },
    "Gabler": {
        "country": "Switzerland/Germany",
        "price_range": "1.8-2.5x Machinecraft",
        "strengths": ["Swiss precision", "medical/pharma expertise", "clean-room capability"],
        "weaknesses": ["high price", "limited to specific applications", "long lead times"],
        "typical_customers": "Pharmaceutical, medical device, clean-room applications",
        "positioning": "Premium Swiss engineering for specialized medical applications",
        "headquarters": "Switzerland",
        "notable_models": ["Medical forming systems"],
    },
}

COMPETITOR_ALIASES = {
    "illig": "ILLIG", "illing": "ILLIG", "ilg": "ILLIG",
    "kiefel": "Kiefel", "keifel": "Kiefel", "kieffel": "Kiefel", "brueckner": "Kiefel",
    "geiss": "GEISS", "geis": "GEISS",
    "frimo": "FRIMO",
    "ridat": "Ridat",
    "zmd": "ZMD (China)", "chinese": "ZMD (China)",
    "gabler": "Gabler",
}

MACHINECRAFT_POSITIONING = {
    "vs_premium_european": "50-70% lower cost with comparable quality for most applications. Better suited for Indian conditions with local service.",
    "vs_mid_range_asian": "Better quality and features at similar or slightly higher price point. Stronger local support and customization.",
    "vs_chinese": "Higher initial cost but significantly better reliability, longevity, and total cost of ownership. Much better service support.",
}

# =============================================================================
# SOUL / IDENTITY
# =============================================================================

SOUL_FILE = OPENCLAW_WORKSPACE / "SOUL.md"

_soul_content: Optional[str] = None

def load_soul() -> str:
    """Load Ira's soul/identity definition."""
    global _soul_content
    
    if _soul_content is not None:
        return _soul_content
    
    if SOUL_FILE.exists():
        _soul_content = SOUL_FILE.read_text()
        return _soul_content
    
    # Fallback minimal soul
    _soul_content = """# Ira - Intelligent Revenue Assistant

You are Ira, the AI sales assistant for Machinecraft Technologies.

## Core Purpose
Help Machinecraft's sales team with product information, customer context, and communications.

## Communication Style
- Be helpful, professional, and efficient
- Provide accurate information backed by data
- When uncertain, say so and offer to investigate
"""
    return _soul_content


def get_soul_excerpt(max_chars: int = 2000) -> str:
    """Get a truncated version of the soul for prompt injection."""
    soul = load_soul()
    if len(soul) <= max_chars:
        return soul
    return soul[:max_chars] + "\n\n[Soul truncated for brevity]"

# =============================================================================
# FEATURE FLAGS
# =============================================================================

FEATURES = {
    "use_mem0": os.environ.get("USE_MEM0", "true").lower() == "true",
    "use_voyage": os.environ.get("USE_VOYAGE", "true").lower() == "true",
    "use_brain_orchestrator": os.environ.get("USE_BRAIN_ORCHESTRATOR", "true").lower() == "true",
    "enable_proactive": os.environ.get("ENABLE_PROACTIVE", "true").lower() == "true",
    "enable_feedback_learning": os.environ.get("ENABLE_FEEDBACK_LEARNING", "true").lower() == "true",
    
    # Memory Backend Selection
    # USE_POSTGRES=true (default) - Keep using PostgreSQL for existing data
    # USE_POSTGRES=false - Use Mem0 only (after running migration script)
    # HYBRID_MODE=true - Read from both, write to Mem0 (migration period)
    "use_postgres": os.environ.get("USE_POSTGRES", "true").lower() == "true",
    "hybrid_mode": os.environ.get("HYBRID_MODE", "true").lower() == "true",
    "use_unified_identity": os.environ.get("USE_UNIFIED_IDENTITY", "true").lower() == "true",
}

# Storage backend selection
# - "postgres": Full PostgreSQL (existing behavior, default)
# - "hybrid": Read both PostgreSQL + Mem0, write to Mem0 (transition period)
# - "mem0": Mem0 only (after migration complete)
if FEATURES["use_postgres"] and FEATURES["hybrid_mode"]:
    STORAGE_BACKEND = "hybrid"
elif FEATURES["use_postgres"]:
    STORAGE_BACKEND = "postgres"
else:
    STORAGE_BACKEND = "mem0"

# =============================================================================
# OPERATIONAL CONSTANTS
# =============================================================================

# Timeouts (seconds)
TIMEOUTS = {
    "http_default": 30,
    "http_short": 10,
    "http_long": 60,
    "llm_request": 60,
    "embedding_request": 30,
    "qdrant_query": 30,
    "telegram_poll": 10,
    "web_scrape": 20,
}

# Rate Limits
RATE_LIMITS = {
    "telegram_api_seconds": 1.0,
    "openai_requests_per_min": 60,
    "voyage_requests_per_min": 100,
}

# Retry Configuration
RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay_seconds": 1.0,
    "max_delay_seconds": 30.0,
}

# Message Processing
MESSAGE_LIMITS = {
    "telegram_max_length": 4000,
    "telegram_max_age_seconds": 600,
    "email_preview_max_length": 1500,
    "context_max_tokens": 4000,
}

# Memory/Cache
MEMORY_CONFIG = {
    "draft_expiry_seconds": 3600,
    "context_window_messages": 10,
    "embedding_cache_ttl_hours": 24,
}

# Retrieval
RETRIEVAL_CONFIG = {
    "default_top_k": 10,
    "max_top_k": 50,
    "rerank_top_k": 5,
    "min_similarity_score": 0.3,
}

# =============================================================================
# CLIENT FACTORY - Singleton API Clients
# =============================================================================

_qdrant_client = None
_voyage_client = None
_openai_client = None
_client_lock = None


def _get_client_lock():
    """Get or create the client lock for thread-safe access."""
    global _client_lock
    if _client_lock is None:
        import threading
        _client_lock = threading.Lock()
    return _client_lock


def get_qdrant_client():
    """
    Get or create the shared Qdrant client instance.
    
    Thread-safe singleton that reuses the same client across all modules.
    
    Usage:
        from openclaw.agents.ira.config import get_qdrant_client
        
        client = get_qdrant_client()
        results = client.search(collection_name="...", ...)
    
    Returns:
        QdrantClient instance, or None if unavailable
    """
    global _qdrant_client
    
    with _get_client_lock():
        if _qdrant_client is None:
            try:
                from qdrant_client import QdrantClient
                _qdrant_client = QdrantClient(
                    url=QDRANT_URL,
                    timeout=QDRANT_TIMEOUT
                )
                _logger.info(f"[config] Created Qdrant client: {QDRANT_URL}")
            except ImportError:
                _logger.error("[config] qdrant-client package not installed")
                return None
            except Exception as e:
                _logger.error(f"[config] Failed to create Qdrant client: {e}")
                return None
        
        return _qdrant_client


def get_voyage_client():
    """
    Get or create the shared Voyage AI client instance.
    
    Thread-safe singleton for embedding generation.
    
    Usage:
        from openclaw.agents.ira.config import get_voyage_client
        
        client = get_voyage_client()
        embeddings = client.embed(texts, model="voyage-3")
    
    Returns:
        VoyageAI client instance, or None if unavailable/no API key
    """
    global _voyage_client
    
    if not VOYAGE_API_KEY:
        _logger.warning("[config] VOYAGE_API_KEY not set")
        return None
    
    with _get_client_lock():
        if _voyage_client is None:
            try:
                import voyageai
                _voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)
                _logger.info("[config] Created Voyage AI client")
            except ImportError:
                _logger.error("[config] voyageai package not installed")
                return None
            except Exception as e:
                _logger.error(f"[config] Failed to create Voyage client: {e}")
                return None
        
        return _voyage_client


def get_openai_client():
    """
    Get or create the shared OpenAI client instance.
    
    Thread-safe singleton for LLM and embedding calls.
    
    Usage:
        from openclaw.agents.ira.config import get_openai_client
        
        client = get_openai_client()
        response = client.chat.completions.create(...)
    
    Returns:
        OpenAI client instance, or None if unavailable/no API key
    """
    global _openai_client
    
    if not OPENAI_API_KEY:
        _logger.warning("[config] OPENAI_API_KEY not set")
        return None
    
    with _get_client_lock():
        if _openai_client is None:
            try:
                from openai import OpenAI
                _openai_client = OpenAI(api_key=OPENAI_API_KEY)
                _logger.info("[config] Created OpenAI client")
            except ImportError:
                _logger.error("[config] openai package not installed")
                return None
            except Exception as e:
                _logger.error(f"[config] Failed to create OpenAI client: {e}")
                return None
        
        return _openai_client


def get_anthropic_client():
    """
    Get or create the shared Anthropic client instance.
    
    Thread-safe singleton for Claude API calls.
    
    Usage:
        from openclaw.agents.ira.config import get_anthropic_client
        
        client = get_anthropic_client()
        response = client.messages.create(...)
    
    Returns:
        Anthropic client instance, or None if unavailable/no API key
    """
    global _anthropic_client
    
    if not ANTHROPIC_API_KEY:
        return None
    
    with _get_client_lock():
        if "_anthropic_client" not in globals() or globals()["_anthropic_client"] is None:
            try:
                import anthropic
                globals()["_anthropic_client"] = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                _logger.info("[config] Created Anthropic client")
            except ImportError:
                return None
            except Exception as e:
                _logger.error(f"[config] Failed to create Anthropic client: {e}")
                return None
        
        return globals().get("_anthropic_client")


# =============================================================================
# RETRY UTILITIES
# =============================================================================

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential: bool = True,
    retry_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.
    
    Usage:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def call_api():
            return requests.get(url)
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential: Use exponential backoff (2^attempt * base_delay)
        retry_exceptions: Tuple of exceptions to retry on
        on_retry: Optional callback(exception, attempt) called before each retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        _logger.error(f"[retry] {func.__name__} failed after {max_retries} retries: {e}")
                        raise
                    
                    if exponential:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                    else:
                        delay = base_delay
                    
                    _logger.warning(f"[retry] {func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    time.sleep(delay)
            
            raise last_exception
        return wrapper
    return decorator


def make_api_request(
    method: str,
    url: str,
    max_retries: int = 3,
    timeout: int = 30,
    **kwargs
) -> Any:
    """
    Make an HTTP request with automatic retry and error handling.
    
    Usage:
        response = make_api_request("GET", "https://api.example.com/data")
        response = make_api_request("POST", url, json={"key": "value"})
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        max_retries: Number of retries on failure
        timeout: Request timeout in seconds
        **kwargs: Additional arguments passed to requests
    
    Returns:
        Response object on success
        
    Raises:
        RequestException on final failure
    """
    import requests
    from requests.exceptions import RequestException, Timeout, ConnectionError
    
    kwargs.setdefault("timeout", timeout)
    
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.request(method, url, **kwargs)
            
            # Retry on rate limit (429) or server errors (5xx)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                _logger.warning(f"[api] Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            
            if response.status_code >= 500:
                _logger.warning(f"[api] Server error {response.status_code}. Retrying...")
                time.sleep(2 ** attempt)
                continue
            
            return response
            
        except (Timeout, ConnectionError) as e:
            last_exception = e
            if attempt < max_retries:
                delay = 2 ** attempt
                _logger.warning(f"[api] {type(e).__name__}: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                _logger.error(f"[api] Request failed after {max_retries} retries: {e}")
                raise
        except RequestException as e:
            _logger.error(f"[api] Request error: {e}")
            raise
    
    if last_exception:
        raise last_exception


# =============================================================================
# CIRCUIT BREAKER PATTERN
# =============================================================================

class CircuitBreakerState:
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.
    
    When a service fails repeatedly, the circuit "opens" and fails fast
    without calling the service. After a timeout, it enters "half-open"
    state where a single request is allowed through to test recovery.
    
    Usage:
        from config import CircuitBreaker
        
        api_breaker = CircuitBreaker(
            name="external_api",
            failure_threshold=5,
            recovery_timeout=60.0
        )
        
        @api_breaker
        def call_external_api():
            return requests.get("https://api.example.com")
        
        # Or manually:
        with api_breaker:
            result = dangerous_operation()
    
    Attributes:
        name: Identifier for this circuit breaker (for logging)
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before attempting recovery
        success_threshold: Successes needed in half-open to close
    """
    
    _instances: Dict[str, 'CircuitBreaker'] = {}
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()
        
        # Register instance for monitoring
        CircuitBreaker._instances[name] = self
    
    @property
    def state(self) -> str:
        """Get current state, checking for timeout transitions."""
        with self._lock:
            if self._state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitBreakerState.HALF_OPEN
                    self._success_count = 0
            return self._state
    
    def _should_attempt_reset(self) -> bool:
        """Check if recovery timeout has elapsed."""
        if self._last_failure_time is None:
            return True
        return (time.time() - self._last_failure_time) >= self.recovery_timeout
    
    def record_success(self):
        """Record a successful call."""
        with self._lock:
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = CircuitBreakerState.CLOSED
                    self._failure_count = 0
                    _logger.info(f"[circuit:{self.name}] CLOSED - service recovered")
            else:
                self._failure_count = 0
    
    def record_failure(self, error: Exception = None):
        """Record a failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._state = CircuitBreakerState.OPEN
                _logger.warning(f"[circuit:{self.name}] OPEN - recovery failed: {error}")
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitBreakerState.OPEN
                _logger.warning(f"[circuit:{self.name}] OPEN - {self._failure_count} failures: {error}")
    
    def allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        state = self.state  # This may transition from OPEN to HALF_OPEN
        if state == CircuitBreakerState.CLOSED:
            return True
        elif state == CircuitBreakerState.HALF_OPEN:
            return True  # Allow one test request
        else:  # OPEN
            return False
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Use as decorator."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            if not self.allow_request():
                raise CircuitBreakerOpen(
                    f"Circuit breaker '{self.name}' is OPEN. Service unavailable."
                )
            
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure(e)
                raise
        return wrapper
    
    def __enter__(self):
        """Use as context manager."""
        if not self.allow_request():
            raise CircuitBreakerOpen(
                f"Circuit breaker '{self.name}' is OPEN. Service unavailable."
            )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.record_success()
        else:
            self.record_failure(exc_val)
        return False  # Don't suppress exceptions
    
    def reset(self):
        """Manually reset the circuit breaker."""
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            _logger.info(f"[circuit:{self.name}] Manually reset")
    
    @classmethod
    def get_all_status(cls) -> Dict[str, Dict]:
        """Get status of all circuit breakers."""
        return {
            name: {
                "state": cb.state,
                "failure_count": cb._failure_count,
                "last_failure": cb._last_failure_time,
            }
            for name, cb in cls._instances.items()
        }


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """
    Get or create a named circuit breaker.
    
    Usage:
        from config import get_circuit_breaker
        
        breaker = get_circuit_breaker("qdrant", failure_threshold=3)
        
        @breaker
        def query_qdrant():
            ...
    """
    if name in CircuitBreaker._instances:
        return CircuitBreaker._instances[name]
    return CircuitBreaker(name, **kwargs)


# =============================================================================
# RATE LIMITING
# =============================================================================

class RateLimiter:
    """
    Token bucket rate limiter for controlling request rates.
    
    Useful for respecting API rate limits or preventing resource exhaustion.
    
    Usage:
        from config import RateLimiter
        
        # Allow 10 requests per second
        limiter = RateLimiter(rate=10.0, burst=20)
        
        @limiter
        def call_api():
            return requests.get(url)
        
        # Or manually:
        if limiter.acquire():
            make_request()
        else:
            print("Rate limited, try later")
    
    Attributes:
        rate: Tokens added per second (requests per second)
        burst: Maximum tokens (allows bursting)
    """
    
    _instances: Dict[str, 'RateLimiter'] = {}
    
    def __init__(
        self,
        name: str = "default",
        rate: float = 10.0,
        burst: int = 20,
    ):
        self.name = name
        self.rate = rate
        self.burst = burst
        
        self._tokens = float(burst)
        self._last_update = time.time()
        self._lock = threading.Lock()
        
        RateLimiter._instances[name] = self
    
    def _add_tokens(self):
        """Add tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_update = now
    
    def acquire(self, tokens: int = 1, block: bool = True, timeout: float = None) -> bool:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire (default 1)
            block: If True, wait for tokens. If False, return immediately.
            timeout: Maximum time to wait (None = forever)
        
        Returns:
            True if tokens acquired, False if timed out or non-blocking
        """
        start_time = time.time()
        
        while True:
            with self._lock:
                self._add_tokens()
                
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
                
                if not block:
                    return False
                
                # Calculate wait time
                wait_time = (tokens - self._tokens) / self.rate
            
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed + wait_time > timeout:
                    return False
                wait_time = min(wait_time, timeout - elapsed)
            
            time.sleep(min(wait_time, 0.1))  # Check periodically
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Use as decorator."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            self.acquire()
            return func(*args, **kwargs)
        return wrapper
    
    @property
    def available_tokens(self) -> float:
        """Get current token count."""
        with self._lock:
            self._add_tokens()
            return self._tokens
    
    @classmethod
    def get_all_status(cls) -> Dict[str, Dict]:
        """Get status of all rate limiters."""
        return {
            name: {
                "rate": rl.rate,
                "burst": rl.burst,
                "available": rl.available_tokens,
            }
            for name, rl in cls._instances.items()
        }


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded in non-blocking mode."""
    pass


def get_rate_limiter(name: str, **kwargs) -> RateLimiter:
    """
    Get or create a named rate limiter.
    
    Usage:
        from config import get_rate_limiter
        
        # Shared limiter for OpenAI API
        openai_limiter = get_rate_limiter("openai", rate=50.0, burst=100)
        
        @openai_limiter
        def call_openai():
            ...
    """
    if name in RateLimiter._instances:
        return RateLimiter._instances[name]
    return RateLimiter(name, **kwargs)


# Pre-configured rate limiters for common services
_rate_limiters_initialized = False

def _init_rate_limiters():
    """Initialize default rate limiters."""
    global _rate_limiters_initialized
    if _rate_limiters_initialized:
        return
    
    # OpenAI: ~60 RPM on free tier, higher on paid
    RateLimiter("openai", rate=1.0, burst=10)
    
    # Qdrant: Local, can be higher
    RateLimiter("qdrant", rate=100.0, burst=200)
    
    # Telegram: 30 messages/second to same chat
    RateLimiter("telegram", rate=25.0, burst=30)
    
    # Voyage: ~100 RPM typical
    RateLimiter("voyage", rate=1.5, burst=15)
    
    _rate_limiters_initialized = True

# Initialize on import
_init_rate_limiters()


# =============================================================================
# MULTI-STORAGE TRANSACTIONS
# =============================================================================

class StorageTransaction:
    """
    Coordinates writes across multiple storage backends with rollback support.
    
    Provides eventual consistency for operations spanning multiple stores
    (e.g., writing to both JSON files and SQLite databases).
    
    Usage:
        from config import StorageTransaction
        
        with StorageTransaction() as txn:
            # Each operation gets a rollback function
            txn.add_operation(
                lambda: write_to_json(data),
                rollback=lambda: restore_json_backup()
            )
            txn.add_operation(
                lambda: write_to_sqlite(data),
                rollback=lambda: delete_sqlite_record()
            )
            # If any operation fails, all previous are rolled back
    
    Note: This is NOT true ACID transactions. It provides best-effort
    rollback for multi-storage operations.
    """
    
    def __init__(self, name: str = "anonymous"):
        self.name = name
        self._operations: List[Tuple[Callable, Optional[Callable]]] = []
        self._completed: List[int] = []  # Indices of completed operations
        self._lock = threading.Lock()
    
    def add_operation(
        self,
        execute: Callable[[], Any],
        rollback: Optional[Callable[[], None]] = None,
        description: str = None
    ) -> 'StorageTransaction':
        """
        Add an operation to the transaction.
        
        Args:
            execute: The operation to perform
            rollback: Optional function to undo the operation
            description: Optional description for logging
        
        Returns:
            Self for chaining
        """
        self._operations.append((execute, rollback, description or f"op_{len(self._operations)}"))
        return self
    
    def execute_all(self) -> List[Any]:
        """
        Execute all operations in order.
        
        If any operation fails, rollback all completed operations in reverse order.
        
        Returns:
            List of results from each operation
        
        Raises:
            Exception from the failed operation (after rollback)
        """
        results = []
        
        with self._lock:
            for i, (execute, rollback, desc) in enumerate(self._operations):
                try:
                    result = execute()
                    results.append(result)
                    self._completed.append(i)
                    _logger.debug(f"[txn:{self.name}] Completed: {desc}")
                except Exception as e:
                    _logger.error(f"[txn:{self.name}] Failed at {desc}: {e}")
                    self._rollback()
                    raise TransactionRollbackError(
                        f"Transaction '{self.name}' failed at {desc}: {e}"
                    ) from e
            
            _logger.info(f"[txn:{self.name}] Committed {len(self._operations)} operations")
            return results
    
    def _rollback(self):
        """Rollback completed operations in reverse order."""
        _logger.warning(f"[txn:{self.name}] Rolling back {len(self._completed)} operations...")
        
        for i in reversed(self._completed):
            _, rollback, desc = self._operations[i]
            if rollback:
                try:
                    rollback()
                    _logger.info(f"[txn:{self.name}] Rolled back: {desc}")
                except Exception as e:
                    _logger.error(f"[txn:{self.name}] Rollback failed for {desc}: {e}")
        
        self._completed.clear()
    
    def __enter__(self) -> 'StorageTransaction':
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.execute_all()
        return False


class TransactionRollbackError(Exception):
    """Raised when a transaction fails and is rolled back."""
    pass


@contextmanager
def multi_storage_write(
    json_path: Optional[Path] = None,
    sqlite_conn: Optional[sqlite3.Connection] = None,
    backup: bool = True
):
    """
    Context manager for atomic multi-storage writes.
    
    Creates backups before writing and restores them on failure.
    
    Usage:
        from config import multi_storage_write
        
        with multi_storage_write(
            json_path=Path("data/state.json"),
            sqlite_conn=get_sqlite_connection("data/db.sqlite")
        ) as (json_data, cursor):
            # Modify json_data dict
            json_data["new_key"] = "value"
            
            # Execute SQLite operations
            cursor.execute("INSERT INTO ...")
            
        # On exit: JSON is written atomically, SQLite is committed
        # On exception: Backups are restored
    
    Args:
        json_path: Path to JSON file to write
        sqlite_conn: SQLite connection to commit
        backup: Create backups before writing (default True)
    
    Yields:
        Tuple of (json_data dict, sqlite cursor or None)
    """
    json_backup = None
    json_data = {}
    cursor = None
    
    # Load existing JSON data
    if json_path and json_path.exists():
        try:
            json_data = json.loads(json_path.read_text())
            if backup:
                json_backup = json_path.with_suffix('.json.bak')
                import shutil
                shutil.copy2(json_path, json_backup)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Get SQLite cursor
    if sqlite_conn:
        cursor = sqlite_conn.cursor()
    
    try:
        yield (json_data, cursor)
        
        # Commit all changes
        if json_path:
            atomic_write_json(json_path, json_data)
        
        if sqlite_conn:
            sqlite_conn.commit()
        
        # Remove backup on success
        if json_backup and json_backup.exists():
            json_backup.unlink()
            
    except Exception:
        # Restore JSON backup
        if json_backup and json_backup.exists():
            import shutil
            shutil.copy2(json_backup, json_path)
            json_backup.unlink()
            _logger.info(f"Restored JSON backup: {json_path}")
        
        # Rollback SQLite
        if sqlite_conn:
            sqlite_conn.rollback()
            _logger.info("Rolled back SQLite transaction")
        
        raise


# =============================================================================
# FILE I/O UTILITIES - Atomic Writes & Locking
# =============================================================================

def atomic_write_json(path: Union[str, Path], data: Any, indent: int = 2) -> None:
    """
    Write JSON data atomically - prevents corruption on crash.
    
    Uses a temporary file and atomic rename to ensure either
    the old file or new file exists, never a partial write.
    
    Usage:
        from config import atomic_write_json
        
        atomic_write_json("data/config.json", {"key": "value"})
    
    Args:
        path: Path to write to
        data: JSON-serializable data
        indent: JSON indent level (default 2)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=path.parent,
        delete=False,
        suffix='.tmp'
    ) as f:
        json.dump(data, f, indent=indent, default=str, ensure_ascii=False)
        temp_path = Path(f.name)
    
    temp_path.replace(path)


def atomic_write_text(path: Union[str, Path], content: str) -> None:
    """
    Write text atomically - prevents corruption on crash.
    
    Usage:
        from config import atomic_write_text
        
        atomic_write_text("data/output.txt", "content here")
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=path.parent,
        delete=False,
        suffix='.tmp',
        encoding='utf-8'
    ) as f:
        f.write(content)
        temp_path = Path(f.name)
    
    temp_path.replace(path)


def load_json_safe(path: Union[str, Path], default: Any = None) -> Any:
    """
    Load JSON file safely with proper error handling.
    
    Usage:
        from config import load_json_safe
        
        data = load_json_safe("data/config.json", default={})
    
    Args:
        path: Path to JSON file
        default: Default value if file doesn't exist or is invalid
    
    Returns:
        Parsed JSON data, or default value on error
    """
    path = Path(path)
    
    if not path.exists():
        return default
    
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        _logger.warning(f"Invalid JSON in {path}: {e}")
        return default
    except Exception as e:
        _logger.error(f"Error loading {path}: {e}")
        return default


@contextmanager
def locked_file(path: Union[str, Path], mode: str = 'r', timeout: float = 30.0):
    """
    Open file with exclusive lock for safe concurrent access.
    
    Uses fcntl.flock for file locking (POSIX systems).
    
    Usage:
        from config import locked_file
        
        # Reading with lock
        with locked_file("data/state.json", "r") as f:
            data = json.load(f)
        
        # Writing with lock
        with locked_file("data/state.json", "w") as f:
            json.dump(data, f)
    
    Args:
        path: Path to file
        mode: File mode ('r', 'w', 'a', etc.)
        timeout: Lock timeout in seconds (default 30)
    
    Yields:
        File handle with exclusive lock
    """
    path = Path(path)
    
    if 'w' in mode or 'a' in mode:
        path.parent.mkdir(parents=True, exist_ok=True)
    
    f = None
    try:
        f = open(path, mode, encoding='utf-8' if 'b' not in mode else None)
        
        start_time = time.time()
        while True:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Could not acquire lock on {path} within {timeout}s")
                time.sleep(0.1)
        
        yield f
        
    finally:
        if f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            f.close()


def locked_json_update(path: Union[str, Path], update_fn: Callable[[Any], Any], default: Any = None) -> Any:
    """
    Update a JSON file atomically with file locking.
    
    This is the safest way to update JSON files that may be accessed
    by multiple processes concurrently.
    
    Usage:
        from config import locked_json_update
        
        # Add item to list
        def add_item(data):
            data = data or []
            data.append("new_item")
            return data
        
        result = locked_json_update("data/items.json", add_item, default=[])
        
        # Update dict
        def update_config(data):
            data = data or {}
            data["last_run"] = datetime.now().isoformat()
            return data
        
        locked_json_update("data/config.json", update_config, default={})
    
    Args:
        path: Path to JSON file
        update_fn: Function that takes current data and returns updated data
        default: Default value if file doesn't exist
    
    Returns:
        The updated data
    """
    path = Path(path)
    lock_path = path.with_suffix(path.suffix + '.lock')
    
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    
    with locked_file(lock_path, 'w') as _:
        current_data = load_json_safe(path, default=default)
        
        updated_data = update_fn(current_data)
        
        atomic_write_json(path, updated_data)
        
        return updated_data


def append_jsonl(path: Union[str, Path], record: dict) -> None:
    """
    Append a record to a JSONL file with file locking.
    
    Safe for concurrent access from multiple processes.
    
    Usage:
        from config import append_jsonl
        
        append_jsonl("logs/audit.jsonl", {"action": "login", "user": "admin"})
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    line = json.dumps(record, default=str, ensure_ascii=False) + '\n'
    
    with locked_file(path, 'a') as f:
        f.write(line)


# =============================================================================
# SQLITE UTILITIES - WAL Mode & Connection Management
# =============================================================================

_sqlite_connections: Dict[str, sqlite3.Connection] = {}
_sqlite_lock = threading.Lock()


def get_sqlite_connection(
    db_path: Union[str, Path],
    wal_mode: bool = True,
    busy_timeout_ms: int = 30000,
    check_same_thread: bool = False
) -> sqlite3.Connection:
    """
    Get or create a SQLite connection with best practices.
    
    Automatically enables:
    - WAL mode for better concurrency
    - Busy timeout to handle lock contention
    - Row factory for dict-like access
    
    Usage:
        from config import get_sqlite_connection
        
        conn = get_sqlite_connection("data/app.db")
        cursor = conn.execute("SELECT * FROM users")
        for row in cursor:
            print(dict(row))
    
    Args:
        db_path: Path to SQLite database
        wal_mode: Enable WAL mode (default True, recommended)
        busy_timeout_ms: Timeout for busy locks in milliseconds (default 30s)
        check_same_thread: SQLite threading mode (default False for multi-thread)
    
    Returns:
        Configured SQLite connection
    """
    db_path = Path(db_path)
    db_key = str(db_path.resolve())
    
    with _sqlite_lock:
        if db_key in _sqlite_connections:
            conn = _sqlite_connections[db_key]
            try:
                conn.execute("SELECT 1")
                return conn
            except sqlite3.Error:
                del _sqlite_connections[db_key]
        
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(
            str(db_path),
            check_same_thread=check_same_thread,
            timeout=busy_timeout_ms / 1000
        )
        
        conn.row_factory = sqlite3.Row
        
        if wal_mode:
            conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
        conn.execute("PRAGMA foreign_keys=ON")
        
        _sqlite_connections[db_key] = conn
        return conn


@contextmanager
def sqlite_transaction(conn: sqlite3.Connection):
    """
    Context manager for SQLite transactions with automatic rollback.
    
    Usage:
        from config import get_sqlite_connection, sqlite_transaction
        
        conn = get_sqlite_connection("data/app.db")
        
        with sqlite_transaction(conn):
            conn.execute("INSERT INTO users ...")
            conn.execute("INSERT INTO logs ...")
            # Commits on success, rolls back on exception
    """
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# =============================================================================
# SCHEMA VERSIONING UTILITIES
# =============================================================================

# Schema registry - maps db_name to (current_version, migrations)
_schema_registry: Dict[str, Tuple[int, Dict[int, List[str]]]] = {}


def register_schema(
    db_name: str,
    current_version: int,
    migrations: Dict[int, List[str]]
) -> None:
    """
    Register a database schema with its version and migrations.
    
    Usage:
        from config import register_schema
        
        register_schema(
            "unified_identity",
            current_version=2,
            migrations={
                1: [  # Initial schema
                    '''CREATE TABLE IF NOT EXISTS contacts (
                        id TEXT PRIMARY KEY,
                        name TEXT
                    )''',
                ],
                2: [  # Add email column
                    "ALTER TABLE contacts ADD COLUMN email TEXT",
                ],
            }
        )
    
    Args:
        db_name: Unique name for the database
        current_version: Current schema version (integer)
        migrations: Dict mapping version number to list of SQL statements
    """
    _schema_registry[db_name] = (current_version, migrations)


def get_schema_version(conn: sqlite3.Connection) -> int:
    """
    Get the current schema version from a database.
    
    Returns 0 if the version table doesn't exist (new database).
    """
    try:
        cursor = conn.execute(
            "SELECT version FROM _schema_version ORDER BY version DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0


def set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    """Set the schema version in the database."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS _schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute(
        "INSERT OR REPLACE INTO _schema_version (version) VALUES (?)",
        (version,)
    )
    conn.commit()


def migrate_schema(
    conn: sqlite3.Connection,
    db_name: str,
    backup: bool = True
) -> Tuple[int, int]:
    """
    Migrate a database to the latest schema version.
    
    Applies all pending migrations in order. Creates a backup before
    migrating if backup=True.
    
    Usage:
        from config import get_sqlite_connection, migrate_schema, register_schema
        
        # Register schema first
        register_schema("mydb", 2, {1: [...], 2: [...]})
        
        # Then migrate
        conn = get_sqlite_connection("data/mydb.db")
        old_version, new_version = migrate_schema(conn, "mydb")
        print(f"Migrated from v{old_version} to v{new_version}")
    
    Args:
        conn: SQLite connection
        db_name: Name used to look up schema in registry
        backup: Whether to backup before migration (default True)
    
    Returns:
        Tuple of (old_version, new_version)
    
    Raises:
        ValueError: If db_name not in schema registry
        sqlite3.Error: If migration fails
    """
    if db_name not in _schema_registry:
        raise ValueError(f"Schema '{db_name}' not registered. Call register_schema() first.")
    
    target_version, migrations = _schema_registry[db_name]
    current_version = get_schema_version(conn)
    
    if current_version >= target_version:
        _logger.debug(f"Schema '{db_name}' is up to date (v{current_version})")
        return current_version, current_version
    
    # Backup before migration
    if backup and current_version > 0:
        db_path = Path(conn.execute("PRAGMA database_list").fetchone()[2])
        backup_path = backup_sqlite_db(db_path)
        if backup_path:
            _logger.info(f"Backed up {db_name} before migration: {backup_path}")
    
    _logger.info(f"Migrating schema '{db_name}' from v{current_version} to v{target_version}")
    
    # Apply migrations in order
    for version in range(current_version + 1, target_version + 1):
        if version not in migrations:
            raise ValueError(f"Missing migration for version {version} in schema '{db_name}'")
        
        _logger.info(f"Applying migration v{version} for '{db_name}'...")
        
        try:
            for statement in migrations[version]:
                conn.execute(statement)
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            _logger.error(f"Migration v{version} failed for '{db_name}': {e}")
            raise
    
    set_schema_version(conn, target_version)
    _logger.info(f"Schema '{db_name}' migrated to v{target_version}")
    
    return current_version, target_version


def ensure_schema(
    db_path: Union[str, Path],
    db_name: str,
    current_version: int,
    migrations: Dict[int, List[str]],
    backup: bool = True
) -> sqlite3.Connection:
    """
    One-call schema setup: register, connect, and migrate.
    
    This is the simplest way to use schema versioning - combines
    register_schema(), get_sqlite_connection(), and migrate_schema().
    
    Usage:
        from config import ensure_schema
        
        conn = ensure_schema(
            "data/contacts.db",
            "contacts",
            current_version=2,
            migrations={
                1: ["CREATE TABLE contacts (id TEXT PRIMARY KEY, name TEXT)"],
                2: ["ALTER TABLE contacts ADD COLUMN email TEXT"],
            }
        )
        # Database is now at v2, ready to use
    
    Args:
        db_path: Path to SQLite database
        db_name: Name to register the schema under
        current_version: Target schema version
        migrations: Dict of version -> SQL statements
        backup: Whether to backup before migration
    
    Returns:
        Configured and migrated SQLite connection
    """
    register_schema(db_name, current_version, migrations)
    conn = get_sqlite_connection(db_path)
    migrate_schema(conn, db_name, backup=backup)
    return conn


# =============================================================================
# BACKUP UTILITIES
# =============================================================================

BACKUP_DIR = PROJECT_ROOT / "backups"


def backup_file(
    source_path: Union[str, Path],
    backup_dir: Union[str, Path] = None,
    max_backups: int = 5,
    timestamp_format: str = "%Y%m%d_%H%M%S"
) -> Optional[Path]:
    """
    Create a timestamped backup of a file.
    
    Automatically rotates old backups, keeping only the most recent ones.
    
    Usage:
        from config import backup_file
        
        # Backup a JSON file
        backup_path = backup_file("data/knowledge/price_index.json")
        
        # Custom backup location
        backup_file("data/app.db", backup_dir="backups/databases")
    
    Args:
        source_path: Path to file to backup
        backup_dir: Directory for backups (default: PROJECT_ROOT/backups)
        max_backups: Maximum number of backups to keep (default 5)
        timestamp_format: Format for timestamp in backup filename
    
    Returns:
        Path to backup file, or None if source doesn't exist
    """
    import shutil
    from datetime import datetime
    
    source = Path(source_path)
    if not source.exists():
        _logger.warning(f"Cannot backup - file not found: {source}")
        return None
    
    # Determine backup directory
    if backup_dir:
        dest_dir = Path(backup_dir)
    else:
        dest_dir = BACKUP_DIR / source.parent.name
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped backup name
    timestamp = datetime.now().strftime(timestamp_format)
    backup_name = f"{source.stem}_{timestamp}{source.suffix}"
    backup_path = dest_dir / backup_name
    
    # Copy file
    try:
        shutil.copy2(source, backup_path)
        _logger.info(f"Backup created: {backup_path}")
    except Exception as e:
        _logger.error(f"Backup failed for {source}: {e}")
        return None
    
    # Rotate old backups
    _rotate_backups(dest_dir, source.stem, source.suffix, max_backups)
    
    return backup_path


def _rotate_backups(
    backup_dir: Path,
    base_name: str,
    suffix: str,
    max_backups: int
) -> int:
    """Remove old backups, keeping only the most recent ones."""
    import re
    
    # Find all backups matching the pattern
    pattern = re.compile(rf"^{re.escape(base_name)}_\d{{8}}_\d{{6}}{re.escape(suffix)}$")
    backups = sorted([
        f for f in backup_dir.iterdir()
        if f.is_file() and pattern.match(f.name)
    ], key=lambda f: f.stat().st_mtime, reverse=True)
    
    # Remove excess backups
    removed = 0
    for old_backup in backups[max_backups:]:
        try:
            old_backup.unlink()
            removed += 1
        except Exception as e:
            _logger.warning(f"Could not remove old backup {old_backup}: {e}")
    
    return removed


def backup_sqlite_db(
    db_path: Union[str, Path],
    backup_dir: Union[str, Path] = None,
    max_backups: int = 5
) -> Optional[Path]:
    """
    Create a safe backup of a SQLite database using the backup API.
    
    This uses SQLite's built-in backup mechanism which is safe even
    while the database is being written to.
    
    Usage:
        from config import backup_sqlite_db
        
        backup_sqlite_db("data/unified_identity.db")
        backup_sqlite_db("crm/relationships.db", max_backups=10)
    
    Args:
        db_path: Path to SQLite database
        backup_dir: Directory for backups (default: PROJECT_ROOT/backups/sqlite)
        max_backups: Maximum number of backups to keep
    
    Returns:
        Path to backup file, or None on failure
    """
    from datetime import datetime
    
    source = Path(db_path)
    if not source.exists():
        _logger.warning(f"Cannot backup - database not found: {source}")
        return None
    
    # Determine backup directory
    if backup_dir:
        dest_dir = Path(backup_dir)
    else:
        dest_dir = BACKUP_DIR / "sqlite"
    
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped backup name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{source.stem}_{timestamp}.db"
    backup_path = dest_dir / backup_name
    
    try:
        # Use SQLite backup API for safe backup
        source_conn = sqlite3.connect(str(source))
        backup_conn = sqlite3.connect(str(backup_path))
        
        source_conn.backup(backup_conn)
        
        backup_conn.close()
        source_conn.close()
        
        _logger.info(f"SQLite backup created: {backup_path}")
    except Exception as e:
        _logger.error(f"SQLite backup failed for {source}: {e}")
        return None
    
    # Rotate old backups
    _rotate_backups(dest_dir, source.stem, ".db", max_backups)
    
    return backup_path


def backup_all_data(
    include_json: bool = True,
    include_sqlite: bool = True,
    include_jsonl: bool = True
) -> Dict[str, List[Path]]:
    """
    Backup all important data files.
    
    Usage:
        from config import backup_all_data
        
        # Full backup
        result = backup_all_data()
        print(f"Backed up {len(result['json'])} JSON files")
        
        # SQLite only
        backup_all_data(include_json=False, include_jsonl=False)
    
    Returns:
        Dict with lists of backup paths by type
    """
    results = {"json": [], "sqlite": [], "jsonl": []}
    
    # JSON files to backup
    json_files = [
        PROJECT_ROOT / "data" / "knowledge" / "ingested_hashes.json",
        PROJECT_ROOT / "data" / "knowledge" / "knowledge_graph.json",
        PROJECT_ROOT / "data" / "knowledge" / "price_index.json",
        PROJECT_ROOT / "data" / "knowledge" / "price_conflicts.json",
        PROJECT_ROOT / "data" / "knowledge" / "clusters.json",
        PROJECT_ROOT / "data" / "identities.json",
        PROJECT_ROOT / "data" / "qualification_states.json",
    ]
    
    # SQLite databases to backup
    sqlite_files = [
        PROJECT_ROOT / "data" / "unified_identity.db",
        PROJECT_ROOT / "crm" / "relationships.db",
        PROJECT_ROOT / "crm" / "learned_knowledge.db",
        PROJECT_ROOT / "crm" / "memory_analytics.db",
        PROJECT_ROOT / "crm" / "cache" / "embedding_cache.db",
    ]
    
    # JSONL logs to backup
    jsonl_files = [
        PROJECT_ROOT / "data" / "knowledge" / "audit.jsonl",
        PROJECT_ROOT / "data" / "knowledge" / "retrieval_log.jsonl",
        PROJECT_ROOT / "crm" / "logs" / "requests.jsonl",
    ]
    
    if include_json:
        for f in json_files:
            if f.exists():
                backup = backup_file(f, BACKUP_DIR / "json")
                if backup:
                    results["json"].append(backup)
    
    if include_sqlite:
        for f in sqlite_files:
            if f.exists():
                backup = backup_sqlite_db(f)
                if backup:
                    results["sqlite"].append(backup)
    
    if include_jsonl:
        for f in jsonl_files:
            if f.exists():
                backup = backup_file(f, BACKUP_DIR / "jsonl")
                if backup:
                    results["jsonl"].append(backup)
    
    total = sum(len(v) for v in results.values())
    _logger.info(f"Backup complete: {total} files backed up")
    
    return results


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_collection(name: str) -> str:
    """Get canonical collection name."""
    if name in COLLECTIONS:
        return COLLECTIONS[name]
    if name in LEGACY_COLLECTIONS:
        return LEGACY_COLLECTIONS[name]
    return name


def get_embedding_dimension(model: str) -> int:
    """Get embedding dimension for a model."""
    return EMBEDDING_DIMENSIONS.get(model, 1024)


def validate_config() -> Dict[str, bool]:
    """Validate that required configuration is present."""
    return {
        "openai_key": bool(OPENAI_API_KEY),
        "voyage_key": bool(VOYAGE_API_KEY),
        "mem0_key": bool(MEM0_API_KEY),
        "database_url": bool(DATABASE_URL),
        "qdrant_url": bool(QDRANT_URL),
        "telegram_token": bool(TELEGRAM_BOT_TOKEN),
        "soul_file": SOUL_FILE.exists(),
    }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Paths
    "PROJECT_ROOT",
    "AGENT_DIR", 
    "SKILLS_DIR",
    "WORKSPACE_DIR",
    "OPENCLAW_WORKSPACE",
    "setup_import_paths",
    "get_skill_path",
    
    # Database
    "DATABASE_URL",
    "POSTGRES_URL",
    "DB_URL",
    "get_db_pool",
    "get_db_connection",
    
    # Qdrant
    "QDRANT_URL",
    "QDRANT_TIMEOUT",
    "COLLECTIONS",
    "get_collection",
    
    # API Keys
    "OPENAI_API_KEY",
    "VOYAGE_API_KEY",
    "MEM0_API_KEY",
    "ANTHROPIC_API_KEY",
    
    # Telegram
    "TELEGRAM_BOT_TOKEN",
    "EXPECTED_CHAT_ID",
    
    # Models
    "EMBEDDING_MODEL_VOYAGE",
    "EMBEDDING_MODEL_OPENAI_LARGE",
    "EMBEDDING_MODEL_OPENAI_SMALL",
    "EMBEDDING_DIMENSIONS",
    "DEFAULT_LLM_MODEL",
    "FAST_LLM_MODEL",
    "get_embedding_dimension",
    
    # Soul
    "SOUL_FILE",
    "load_soul",
    "get_soul_excerpt",
    
    # Features
    "FEATURES",
    "STORAGE_BACKEND",
    
    # Operational Constants
    "TIMEOUTS",
    "RATE_LIMITS",
    "RETRY_CONFIG",
    "MESSAGE_LIMITS",
    "MEMORY_CONFIG",
    "RETRIEVAL_CONFIG",
    
    # Utilities
    "validate_config",
    "retry_with_backoff",
    "make_api_request",
    
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "CircuitBreakerState",
    "get_circuit_breaker",
    
    # Rate Limiting
    "RateLimiter",
    "RateLimitExceeded",
    "get_rate_limiter",
    
    # Multi-Storage Transactions
    "StorageTransaction",
    "TransactionRollbackError",
    "multi_storage_write",
    
    # File I/O Utilities
    "atomic_write_json",
    "atomic_write_text",
    "load_json_safe",
    "locked_file",
    "locked_json_update",
    "append_jsonl",
    
    # SQLite Utilities
    "get_sqlite_connection",
    "sqlite_transaction",
    
    # Schema Versioning
    "register_schema",
    "get_schema_version",
    "set_schema_version",
    "migrate_schema",
    "ensure_schema",
    
    # Backup Utilities
    "BACKUP_DIR",
    "backup_file",
    "backup_sqlite_db",
    "backup_all_data",
    
    # Client Factory
    "get_qdrant_client",
    "get_voyage_client",
    "get_openai_client",
    "get_anthropic_client",
    
    # Logging
    "get_logger",
    "setup_logging",
    "LOG_LEVEL",
]
