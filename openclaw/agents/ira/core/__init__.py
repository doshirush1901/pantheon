"""
Ira Core - Shared infrastructure for all Ira components

Provides:
- State management (unified agent state)
- Configuration loading
- Logging utilities
- Health monitoring
- Production resilience (circuit breakers, retries)
"""

from .state import (
    AgentStateManager,
    get_state_manager,
    load_state,
    save_state,
)

# Production resilience
try:
    from .resilience import (
        ProductionCircuitBreaker,
        CircuitBreakerOpenError,
        openai_breaker,
        qdrant_breaker,
        postgres_breaker,
        voyage_breaker,
        mem0_breaker,
        get_service_status,
        get_system_health_summary,
        with_resilience,
        retry_with_exponential_backoff,
    )
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False

# Production logging & observability
try:
    from .observability import (
        configure_logging,
        get_logger,
        bind_trace_context,
        start_trace,
        end_trace,
        get_trace_id,
        PerformanceSpan,
        traced,
        log_event,
        log_error,
    )
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False

# Rate limiting
try:
    from .rate_limiter import (
        ServiceRateLimiter,
        RateLimitConfig,
        RateLimitStrategy,
        RateLimitExceeded,
        get_limiter,
        rate_limit,
        get_rate_limit_status,
        openai_limiter,
        voyage_limiter,
        qdrant_limiter,
    )
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False

# Langfuse LLM observability
try:
    from .langfuse_integration import (
        get_langfuse,
        create_trace,
        trace_llm_call,
        LangfuseTracer,
        OpenAICallbackHandler,
        calculate_cost,
    )
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False

# Caching layer
try:
    from .cache import (
        LRUCache,
        RedisCache,
        EmbeddingCache,
        QueryCache,
        get_cache,
        get_embedding_cache,
        get_query_cache,
        cache_result,
        cache_embedding,
        get_all_cache_stats,
        clear_all_caches,
    )
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

# Batch embedding
try:
    from .batch_embedder import (
        BatchEmbedder,
        get_batch_embedder,
        embed_texts,
        embed_single,
        get_embedding_stats,
    )
    BATCH_EMBEDDER_AVAILABLE = True
except ImportError:
    BATCH_EMBEDDER_AVAILABLE = False

# Health check
try:
    from .health import (
        ComponentStatus,
        ComponentHealth,
        HealthStatus,
        health_check,
        get_health_status,
        create_health_router,
    )
    HEALTH_AVAILABLE = True
except ImportError:
    HEALTH_AVAILABLE = False

__all__ = [
    "AgentStateManager",
    "get_state_manager",
    "load_state",
    "save_state",
    # Resilience (if available)
    "ProductionCircuitBreaker",
    "CircuitBreakerOpenError",
    "openai_breaker",
    "qdrant_breaker",
    "postgres_breaker",
    "voyage_breaker",
    "mem0_breaker",
    "get_service_status",
    "get_system_health_summary",
    "with_resilience",
    "retry_with_exponential_backoff",
    "RESILIENCE_AVAILABLE",
    # Observability (if available)
    "configure_logging",
    "get_logger",
    "bind_trace_context",
    "start_trace",
    "end_trace",
    "get_trace_id",
    "PerformanceSpan",
    "traced",
    "log_event",
    "log_error",
    "OBSERVABILITY_AVAILABLE",
    # Rate limiting (if available)
    "ServiceRateLimiter",
    "RateLimitConfig",
    "RateLimitStrategy",
    "RateLimitExceeded",
    "get_limiter",
    "rate_limit",
    "get_rate_limit_status",
    "openai_limiter",
    "voyage_limiter",
    "qdrant_limiter",
    "RATE_LIMITER_AVAILABLE",
    # Langfuse (if available)
    "get_langfuse",
    "create_trace",
    "trace_llm_call",
    "LangfuseTracer",
    "OpenAICallbackHandler",
    "calculate_cost",
    "LANGFUSE_AVAILABLE",
    # Cache (if available)
    "LRUCache",
    "RedisCache",
    "EmbeddingCache",
    "QueryCache",
    "get_cache",
    "get_embedding_cache",
    "get_query_cache",
    "cache_result",
    "cache_embedding",
    "get_all_cache_stats",
    "clear_all_caches",
    "CACHE_AVAILABLE",
    # Batch embedder (if available)
    "BatchEmbedder",
    "get_batch_embedder",
    "embed_texts",
    "embed_single",
    "get_embedding_stats",
    "BATCH_EMBEDDER_AVAILABLE",
    # Health check (if available)
    "ComponentStatus",
    "ComponentHealth",
    "HealthStatus",
    "health_check",
    "get_health_status",
    "create_health_router",
    "HEALTH_AVAILABLE",
]
