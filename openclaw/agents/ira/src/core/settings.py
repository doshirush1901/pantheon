"""
Centralized Settings — Single Source of Truth for All Configuration
===================================================================

Type-safe, validated configuration using pydantic-settings.
Loads from environment variables and .env files.

Usage:
    from openclaw.agents.ira.src.core.settings import get_settings

    settings = get_settings()
    api_key = settings.openai_api_key
    model = settings.default_llm_model
"""

import os
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ira.settings")

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field, SecretStr
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

_PROJECT_ROOT = Path(__file__).resolve().parents[6]
_ENV_FILE = _PROJECT_ROOT / ".env"


if PYDANTIC_AVAILABLE:

    class Settings(BaseSettings):
        """All Ira configuration in one validated, type-safe object."""

        # ── API Keys ──────────────────────────────────────────────────
        openai_api_key: SecretStr = Field(default=SecretStr(""), description="OpenAI API key for GPT-4o")
        voyage_api_key: SecretStr = Field(default=SecretStr(""), description="Voyage AI embedding key")
        mem0_api_key: SecretStr = Field(default=SecretStr(""), description="Mem0 memory service key")
        anthropic_api_key: SecretStr = Field(default=SecretStr(""), description="Anthropic Claude key")
        jina_api_key: SecretStr = Field(default=SecretStr(""), description="Jina AI web research key")

        # ── Telegram ──────────────────────────────────────────────────
        telegram_bot_token: SecretStr = Field(default=SecretStr(""), description="Telegram bot token")
        expected_chat_id: str = Field(default="", description="Authorized Telegram chat ID")
        rushabh_telegram_id: str = Field(default="", description="Admin Telegram ID for notifications")

        # ── Infrastructure ────────────────────────────────────────────
        database_url: str = Field(default="", description="PostgreSQL connection URL")
        qdrant_url: str = Field(default="http://localhost:6333", description="Qdrant vector DB URL")
        qdrant_timeout: int = Field(default=30, description="Qdrant request timeout in seconds")
        neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j graph DB URI")
        neo4j_user: str = Field(default="neo4j", description="Neo4j username")
        neo4j_password: SecretStr = Field(default=SecretStr(""), description="Neo4j password")
        redis_url: str = Field(default="redis://localhost:6379/0", description="Redis cache URL")

        # ── LLM Models ───────────────────────────────────────────────
        default_llm_model: str = Field(default="gpt-4.1", description="Primary LLM model")
        fast_llm_model: str = Field(default="gpt-4.1-mini", description="Fast/cheap LLM for lightweight tasks")

        # ── Logging ───────────────────────────────────────────────────
        ira_log_level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")
        ira_log_format: str = Field(default="json", description="Log format: json or text")
        ira_environment: str = Field(default="production", description="Environment: production, staging, test")

        # ── Feature Flags ─────────────────────────────────────────────
        use_mem0: bool = Field(default=True, description="Enable Mem0 memory layer")
        use_voyage: bool = Field(default=True, description="Enable Voyage AI embeddings")
        use_postgres: bool = Field(default=True, description="Enable PostgreSQL backend")
        hybrid_mode: bool = Field(default=True, description="Enable hybrid search (BM25 + semantic)")
        use_unified_identity: bool = Field(default=True, description="Enable unified identity resolution")
        enable_proactive: bool = Field(default=True, description="Enable proactive outreach")
        enable_feedback_learning: bool = Field(default=True, description="Enable feedback learning loop")

        # ── Email Channel ─────────────────────────────────────────────
        email_imap_host: str = Field(default="imap.gmail.com", description="IMAP server host")
        email_imap_user: str = Field(default="", description="IMAP username/email")
        email_imap_password: SecretStr = Field(default=SecretStr(""), description="IMAP app password")
        ira_email: str = Field(default="ira@machinecraft.org", description="Ira's email address")
        email_poll_interval: int = Field(default=60, description="Email polling interval in seconds")

        # ── Embedding ─────────────────────────────────────────────────
        embedding_model: str = Field(default="voyage-3", description="Embedding model name")
        embedding_batch_size: int = Field(default=32, description="Embedding batch size")
        embedding_max_concurrent: int = Field(default=4, description="Max concurrent embedding requests")
        embedding_dimensions: int = Field(default=1024, description="Embedding vector dimensions")

        # ── Caching ───────────────────────────────────────────────────
        cache_default_ttl: int = Field(default=3600, description="Default cache TTL in seconds")
        embedding_cache_size: int = Field(default=10000, description="Max cached embeddings")
        query_cache_size: int = Field(default=1000, description="Max cached queries")

        # ── Rate Limiting ─────────────────────────────────────────────
        openai_rate_limit: int = Field(default=60, description="OpenAI requests per minute")
        voyage_rate_limit: int = Field(default=100, description="Voyage requests per minute")
        qdrant_rate_limit: int = Field(default=200, description="Qdrant requests per minute")
        mem0_rate_limit: int = Field(default=60, description="Mem0 requests per minute")

        # ── Observability ─────────────────────────────────────────────
        langfuse_public_key: str = Field(default="", description="Langfuse public key")
        langfuse_secret_key: SecretStr = Field(default=SecretStr(""), description="Langfuse secret key")
        langfuse_host: str = Field(default="https://cloud.langfuse.com", description="Langfuse host URL")

        # ── Reranker ──────────────────────────────────────────────────
        reranker_type: str = Field(default="flashrank", description="Reranker: flashrank or colbert")

        # ── Dashboard ─────────────────────────────────────────────────
        ira_dashboard_url: str = Field(default="", description="Dashboard URL for Telegram Web App")
        dashboard_host: str = Field(default="0.0.0.0", description="Dashboard server host")
        dashboard_port: int = Field(default=8080, description="Dashboard server port")

        # ── Google ────────────────────────────────────────────────────
        google_service_account_path: str = Field(default="service_account.json", description="Google Cloud SA JSON path")

        class Config:
            env_file = str(_ENV_FILE) if _ENV_FILE.exists() else None
            env_file_encoding = "utf-8"
            case_sensitive = False
            extra = "ignore"

        def get_openai_key(self) -> str:
            """Convenience: return the raw OpenAI key string."""
            return self.openai_api_key.get_secret_value()

        def get_voyage_key(self) -> str:
            return self.voyage_api_key.get_secret_value()

        def get_mem0_key(self) -> str:
            return self.mem0_api_key.get_secret_value()

else:
    class Settings:
        """Fallback settings when pydantic-settings is not installed."""

        def __init__(self):
            self.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
            self.voyage_api_key = os.environ.get("VOYAGE_API_KEY", "")
            self.mem0_api_key = os.environ.get("MEM0_API_KEY", "")
            self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            self.jina_api_key = os.environ.get("JINA_API_KEY", "")
            self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            self.expected_chat_id = os.environ.get("EXPECTED_CHAT_ID", "")
            self.rushabh_telegram_id = os.environ.get("RUSHABH_TELEGRAM_ID", "") or self.expected_chat_id
            self.database_url = os.environ.get("DATABASE_URL", "")
            self.qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
            self.qdrant_timeout = int(os.environ.get("QDRANT_TIMEOUT", "30"))
            self.neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
            self.neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
            self.neo4j_password = os.environ.get("NEO4J_PASSWORD", "")
            self.redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            self.default_llm_model = os.environ.get("DEFAULT_LLM_MODEL", "gpt-4.1")
            self.fast_llm_model = os.environ.get("FAST_LLM_MODEL", "gpt-4.1-mini")
            self.ira_log_level = os.environ.get("IRA_LOG_LEVEL", "INFO").upper()
            self.ira_environment = os.environ.get("IRA_ENVIRONMENT", "production")
            self.embedding_model = os.environ.get("EMBEDDING_MODEL", "voyage-3")
            self.embedding_dimensions = int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))
            self.reranker_type = os.environ.get("RERANKER_TYPE", "flashrank")

        def get_openai_key(self) -> str:
            return self.openai_api_key

        def get_voyage_key(self) -> str:
            return self.voyage_api_key

        def get_mem0_key(self) -> str:
            return self.mem0_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton factory for the Settings object. Cached after first call."""
    settings = Settings()
    logger.info("[Settings] Loaded configuration (env=%s, model=%s)",
                getattr(settings, 'ira_environment', 'unknown'),
                getattr(settings, 'default_llm_model', 'unknown'))
    return settings
