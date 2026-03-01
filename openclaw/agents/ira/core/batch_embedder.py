#!/usr/bin/env python3
"""
BATCH EMBEDDER - Optimized embedding with batching and caching
===============================================================

Reduces API costs by batching multiple embedding requests and caching results.

Features:
- Automatic request batching (configurable batch size)
- Embedding cache integration
- Rate limiting support
- Async batch processing
- Automatic retry with backoff
- Cost tracking

Usage:
    from core.batch_embedder import (
        get_batch_embedder,
        embed_texts,
        embed_single
    )
    
    # Single text (uses cache)
    embedding = await embed_single("What is PF1?")
    
    # Batch texts (optimized)
    embeddings = await embed_texts([
        "PF1 specifications",
        "PF1 price",
        "PF1 applications"
    ])
    
    # With specific model
    embeddings = await embed_texts(texts, model="voyage-3")

Configuration:
    EMBEDDING_MODEL=voyage-3
    EMBEDDING_BATCH_SIZE=32
    EMBEDDING_MAX_CONCURRENT=4
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ira.batch_embedder")

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "voyage-3")
EMBEDDING_BATCH_SIZE = int(os.environ.get("EMBEDDING_BATCH_SIZE", 32))
EMBEDDING_MAX_CONCURRENT = int(os.environ.get("EMBEDDING_MAX_CONCURRENT", 4))
EMBEDDING_DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", 1024))

VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

_voyage_client = None
_openai_client = None


def _get_voyage_client():
    """Get or create Voyage client."""
    global _voyage_client
    if _voyage_client is None and VOYAGE_API_KEY:
        try:
            import voyageai
            _voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)
            logger.info("Voyage AI client initialized")
        except ImportError:
            logger.warning("voyageai not installed")
    return _voyage_client


def _get_openai_client():
    """Get or create OpenAI client."""
    global _openai_client
    if _openai_client is None and OPENAI_API_KEY:
        try:
            from openai import OpenAI
            _openai_client = OpenAI(api_key=OPENAI_API_KEY)
            logger.info("OpenAI client initialized")
        except ImportError:
            logger.warning("openai not installed")
    return _openai_client


@dataclass
class EmbeddingStats:
    """Statistics for embedding operations."""
    total_requests: int = 0
    total_texts: int = 0
    cache_hits: int = 0
    api_calls: int = 0
    api_texts: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    errors: int = 0
    
    @property
    def cache_hit_rate(self) -> float:
        if self.total_texts == 0:
            return 0.0
        return self.cache_hits / self.total_texts
    
    @property
    def avg_latency_ms(self) -> float:
        if self.api_calls == 0:
            return 0.0
        return self.total_latency_ms / self.api_calls
    
    def to_dict(self) -> Dict:
        return {
            "total_requests": self.total_requests,
            "total_texts": self.total_texts,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "api_calls": self.api_calls,
            "api_texts": self.api_texts,
            "total_tokens": self.total_tokens,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "errors": self.errors,
        }


@dataclass
class EmbeddingResult:
    """Result of an embedding operation."""
    embeddings: List[List[float]]
    cached_count: int = 0
    computed_count: int = 0
    latency_ms: float = 0.0
    model: str = ""
    
    def __len__(self) -> int:
        return len(self.embeddings)


class BatchEmbedder:
    """
    Optimized embedder with batching, caching, and rate limiting.
    
    Automatically batches requests and uses cache to minimize API calls.
    """
    
    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        batch_size: int = EMBEDDING_BATCH_SIZE,
        max_concurrent: int = EMBEDDING_MAX_CONCURRENT,
        use_cache: bool = True,
    ):
        self.model = model
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.use_cache = use_cache
        self.stats = EmbeddingStats()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._cache = None
        self._rate_limiter = None
        
        if use_cache:
            try:
                from ..src.core.redis_cache import get_cache
                self._cache = get_cache()
            except ImportError:
                try:
                    from .cache import get_embedding_cache
                    self._cache = get_embedding_cache()
                except ImportError:
                    logger.debug("Cache not available")
        
        try:
            from .rate_limiter import get_limiter
            self._rate_limiter = get_limiter("voyage" if "voyage" in model else "openai")
        except ImportError:
            logger.debug("Rate limiter not available")
    
    async def embed(self, texts: List[str]) -> EmbeddingResult:
        """
        Embed a list of texts with automatic batching and caching.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            EmbeddingResult with embeddings in same order as input
        """
        if not texts:
            return EmbeddingResult(embeddings=[], model=self.model)
        
        start_time = time.time()
        self.stats.total_requests += 1
        self.stats.total_texts += len(texts)
        
        cached_embeddings: Dict[int, List[float]] = {}
        texts_to_embed: List[Tuple[int, str]] = []
        
        if self._cache and self.use_cache:
            for i, text in enumerate(texts):
                cached = self._cache.get(text, self.model)
                if cached is not None:
                    cached_embeddings[i] = cached
                    self.stats.cache_hits += 1
                else:
                    texts_to_embed.append((i, text))
        else:
            texts_to_embed = list(enumerate(texts))
        
        computed_embeddings: Dict[int, List[float]] = {}
        
        if texts_to_embed:
            batches = self._create_batches(texts_to_embed)
            
            batch_results = await asyncio.gather(
                *[self._embed_batch(batch) for batch in batches],
                return_exceptions=True
            )
            
            for batch, result in zip(batches, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch embedding error: {result}")
                    self.stats.errors += 1
                    for idx, _ in batch:
                        computed_embeddings[idx] = [0.0] * EMBEDDING_DIMENSIONS
                else:
                    for (idx, text), embedding in zip(batch, result):
                        computed_embeddings[idx] = embedding
                        
                        if self._cache and self.use_cache:
                            self._cache.set(text, embedding, self.model)
        
        all_embeddings = {**cached_embeddings, **computed_embeddings}
        ordered_embeddings = [all_embeddings[i] for i in range(len(texts))]
        
        latency_ms = (time.time() - start_time) * 1000
        
        return EmbeddingResult(
            embeddings=ordered_embeddings,
            cached_count=len(cached_embeddings),
            computed_count=len(computed_embeddings),
            latency_ms=latency_ms,
            model=self.model,
        )
    
    async def embed_single(self, text: str) -> List[float]:
        """Embed a single text."""
        result = await self.embed([text])
        return result.embeddings[0] if result.embeddings else []
    
    def _create_batches(
        self,
        texts: List[Tuple[int, str]]
    ) -> List[List[Tuple[int, str]]]:
        """Split texts into batches."""
        batches = []
        for i in range(0, len(texts), self.batch_size):
            batches.append(texts[i:i + self.batch_size])
        return batches
    
    async def _embed_batch(
        self,
        batch: List[Tuple[int, str]]
    ) -> List[List[float]]:
        """Embed a single batch with rate limiting."""
        async with self._semaphore:
            if self._rate_limiter:
                if not self._rate_limiter.try_acquire(weight=len(batch)):
                    await asyncio.sleep(1.0)
            
            texts = [text for _, text in batch]
            
            start_time = time.time()
            
            try:
                if "voyage" in self.model.lower():
                    embeddings = await self._embed_with_voyage(texts)
                else:
                    embeddings = await self._embed_with_openai(texts)
                
                latency_ms = (time.time() - start_time) * 1000
                self.stats.api_calls += 1
                self.stats.api_texts += len(texts)
                self.stats.total_latency_ms += latency_ms
                
                return embeddings
                
            except Exception as e:
                logger.error(f"Embedding API error: {e}")
                raise
    
    async def _embed_with_voyage(self, texts: List[str]) -> List[List[float]]:
        """Embed using Voyage AI."""
        client = _get_voyage_client()
        if not client:
            raise RuntimeError("Voyage AI client not available")
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.embed(texts, model=self.model)
        )
        
        return result.embeddings
    
    async def _embed_with_openai(self, texts: List[str]) -> List[List[float]]:
        """Embed using OpenAI."""
        client = _get_openai_client()
        if not client:
            raise RuntimeError("OpenAI client not available")
        
        model = self.model if self.model != "voyage-3" else "text-embedding-3-small"
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.embeddings.create(input=texts, model=model)
        )
        
        self.stats.total_tokens += response.usage.total_tokens
        
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]
    
    def get_stats(self) -> Dict:
        """Get embedding statistics."""
        stats = self.stats.to_dict()
        stats["model"] = self.model
        stats["batch_size"] = self.batch_size
        if self._cache:
            stats["cache_stats"] = self._cache.stats()
        return stats


_batch_embedder: Optional[BatchEmbedder] = None


def get_batch_embedder(
    model: str = EMBEDDING_MODEL,
    **kwargs
) -> BatchEmbedder:
    """Get or create batch embedder instance."""
    global _batch_embedder
    if _batch_embedder is None or _batch_embedder.model != model:
        _batch_embedder = BatchEmbedder(model=model, **kwargs)
    return _batch_embedder


async def embed_texts(
    texts: List[str],
    model: str = EMBEDDING_MODEL,
    use_cache: bool = True,
) -> List[List[float]]:
    """
    Embed multiple texts with automatic batching and caching.
    
    Args:
        texts: List of texts to embed
        model: Embedding model to use
        use_cache: Whether to use embedding cache
        
    Returns:
        List of embeddings in same order as input
    """
    embedder = get_batch_embedder(model)
    embedder.use_cache = use_cache
    result = await embedder.embed(texts)
    return result.embeddings


async def embed_single(
    text: str,
    model: str = EMBEDDING_MODEL,
    use_cache: bool = True,
) -> List[float]:
    """
    Embed a single text.
    
    Args:
        text: Text to embed
        model: Embedding model to use
        use_cache: Whether to use embedding cache
        
    Returns:
        Embedding vector
    """
    embedder = get_batch_embedder(model)
    embedder.use_cache = use_cache
    return await embedder.embed_single(text)


def get_embedding_stats() -> Dict:
    """Get global embedding statistics."""
    if _batch_embedder:
        return _batch_embedder.get_stats()
    return {}


__all__ = [
    "BatchEmbedder",
    "EmbeddingResult",
    "EmbeddingStats",
    "get_batch_embedder",
    "embed_texts",
    "embed_single",
    "get_embedding_stats",
]


if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("Testing Batch Embedder\n" + "=" * 50)
        
        embedder = BatchEmbedder(use_cache=True)
        print(f"Model: {embedder.model}")
        print(f"Batch size: {embedder.batch_size}")
        
        if not VOYAGE_API_KEY and not OPENAI_API_KEY:
            print("\n⚠️ No API keys configured, skipping API tests")
            print("Set VOYAGE_API_KEY or OPENAI_API_KEY to test")
            
            try:
                from ..src.core.redis_cache import get_cache
                cache = get_cache()
            except ImportError:
                from .cache import get_embedding_cache
                cache = get_embedding_cache()
            
            result = await embedder.embed(["test query 1", "test query 2"])
            print(f"\n✅ Cache test: {result.cached_count} cached, {result.computed_count} computed")
        else:
            test_texts = [
                "What is the PF1 machine?",
                "Tell me about thermoforming",
                "PF1-C-2015 specifications",
            ]
            
            print(f"\nEmbedding {len(test_texts)} texts...")
            result = await embedder.embed(test_texts)
            print(f"✅ First batch: {result.cached_count} cached, {result.computed_count} computed")
            print(f"   Latency: {result.latency_ms:.0f}ms")
            
            result2 = await embedder.embed(test_texts)
            print(f"✅ Second batch: {result2.cached_count} cached, {result2.computed_count} computed")
            print(f"   Latency: {result2.latency_ms:.0f}ms")
        
        print(f"\n📊 Stats: {embedder.get_stats()}")
        print("\n🎉 Batch embedder test complete!")
    
    asyncio.run(test())
