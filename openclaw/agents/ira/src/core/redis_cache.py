"""
Redis Cache - Unified caching solution for IRA.

This is the canonical cache implementation for all IRA components.
Provides async Redis-based caching with automatic in-memory fallback.

Usage:
    from src.core.redis_cache import RedisCache, get_cache
    
    cache = get_cache()
    await cache.connect()
    await cache.set("embedding", query, result)
    cached = await cache.get("embedding", query)
"""

import hashlib
import json
import logging
import os
import time
from typing import Any, Optional


logger = logging.getLogger("ira.cache")


class RedisCache:
    """
    Redis-based cache for external lookups.
    
    Caches results from:
    - Qdrant vector searches
    - Mem0 memory searches
    - Machine database lookups
    - Voyage AI embeddings
    - LLM responses
    
    Features:
    - Async Redis operations
    - In-memory fallback when Redis is unavailable
    - Type-specific TTLs
    - Cache statistics
    """
    
    DEFAULT_TTL = 3600  # 1 hour default
    
    TTL_BY_TYPE = {
        "embedding": 86400,      # 24 hours for embeddings
        "qdrant": 1800,          # 30 minutes for vector search
        "mem0": 900,             # 15 minutes for memory (more dynamic)
        "machine_db": 86400,     # 24 hours for machine specs (stable)
        "document": 3600,        # 1 hour for document chunks
        "competitor": 43200,     # 12 hours for competitor intel
        "llm_response": 1800,    # 30 minutes for LLM responses
        "fact_check": 3600,      # 1 hour for fact check results
    }
    
    def __init__(self, redis_url: Optional[str] = None, prefix: str = "ira"):
        """
        Initialize the cache.
        
        Args:
            redis_url: Redis connection URL. Defaults to REDIS_URL env var.
            prefix: Key prefix for namespacing. Defaults to "ira".
        """
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379")
        self.prefix = prefix
        self._client = None
        self._connected = False
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "errors": 0}
        
    async def connect(self) -> bool:
        """
        Connect to Redis.
        
        Returns:
            True if connected to Redis, False if using fallback.
        """
        if self._connected:
            return True
        
        try:
            import redis.asyncio as redis
            self._client = redis.from_url(self.redis_url, decode_responses=True)
            await self._client.ping()
            self._connected = True
            logger.info(f"Redis cache connected: {self.redis_url}")
            return True
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
            self._client = {}
            self._connected = False
            return False
    
    def _make_key(self, cache_type: str, query: str, **kwargs) -> str:
        """Generate cache key from query and parameters."""
        key_data = f"{cache_type}:{query}:{json.dumps(kwargs, sort_keys=True)}"
        hash_value = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"{self.prefix}:{cache_type}:{hash_value}"
    
    async def get(self, cache_type: str, query: str, **kwargs) -> Optional[Any]:
        """
        Get cached value.
        
        Args:
            cache_type: Type of cached data (e.g., "embedding", "qdrant")
            query: The query or key to look up
            **kwargs: Additional parameters that affect the cache key
        
        Returns:
            Cached value or None if not found/expired
        """
        key = self._make_key(cache_type, query, **kwargs)
        
        try:
            if self._connected and self._client and not isinstance(self._client, dict):
                value = await self._client.get(key)
                if value:
                    self._stats["hits"] += 1
                    return json.loads(value)
            elif isinstance(self._client, dict):
                cached = self._client.get(key)
                if cached and cached["expires"] > time.time():
                    self._stats["hits"] += 1
                    return cached["value"]
        except Exception as e:
            self._stats["errors"] += 1
            logger.debug(f"Cache get error: {e}")
        
        self._stats["misses"] += 1
        return None
    
    async def set(
        self,
        cache_type: str,
        query: str,
        value: Any,
        ttl: Optional[int] = None,
        **kwargs
    ) -> bool:
        """
        Set cached value.
        
        Args:
            cache_type: Type of cached data
            query: The query or key
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live in seconds. Defaults to type-specific TTL.
            **kwargs: Additional parameters that affect the cache key
        
        Returns:
            True if successfully cached
        """
        key = self._make_key(cache_type, query, **kwargs)
        ttl = ttl or self.TTL_BY_TYPE.get(cache_type, self.DEFAULT_TTL)
        
        try:
            serialized = json.dumps(value, default=str)
            
            if self._connected and self._client and not isinstance(self._client, dict):
                await self._client.setex(key, ttl, serialized)
                self._stats["sets"] += 1
                return True
            elif isinstance(self._client, dict):
                self._client[key] = {
                    "value": value,
                    "expires": time.time() + ttl
                }
                self._stats["sets"] += 1
                return True
        except Exception as e:
            self._stats["errors"] += 1
            logger.debug(f"Cache set error: {e}")
        
        return False
    
    async def delete(self, cache_type: str, query: str, **kwargs) -> bool:
        """Delete a cached value."""
        key = self._make_key(cache_type, query, **kwargs)
        
        try:
            if self._connected and self._client and not isinstance(self._client, dict):
                await self._client.delete(key)
                return True
            elif isinstance(self._client, dict):
                self._client.pop(key, None)
                return True
        except Exception as e:
            logger.debug(f"Cache delete error: {e}")
        
        return False
    
    async def clear_type(self, cache_type: str) -> int:
        """Clear all cached values of a specific type."""
        pattern = f"{self.prefix}:{cache_type}:*"
        deleted = 0
        
        try:
            if self._connected and self._client and not isinstance(self._client, dict):
                keys = await self._client.keys(pattern)
                if keys:
                    deleted = await self._client.delete(*keys)
            elif isinstance(self._client, dict):
                to_delete = [k for k in self._client.keys() if k.startswith(f"{self.prefix}:{cache_type}:")]
                for k in to_delete:
                    del self._client[k]
                    deleted += 1
        except Exception as e:
            logger.debug(f"Cache clear error: {e}")
        
        return deleted
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0
        return {
            **self._stats, 
            "hit_rate": hit_rate,
            "connected": self._connected,
            "using_redis": self._connected and not isinstance(self._client, dict)
        }


# Singleton instance
_cache_instance: Optional[RedisCache] = None


def get_cache(redis_url: Optional[str] = None) -> RedisCache:
    """
    Get singleton cache instance.
    
    Args:
        redis_url: Optional Redis URL (only used on first call)
    
    Returns:
        RedisCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache(redis_url)
    return _cache_instance


async def get_connected_cache(redis_url: Optional[str] = None) -> RedisCache:
    """
    Get cache instance and ensure it's connected.
    
    Args:
        redis_url: Optional Redis URL
    
    Returns:
        Connected RedisCache instance
    """
    cache = get_cache(redis_url)
    await cache.connect()
    return cache
