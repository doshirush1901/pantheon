"""
NewsData.io API client for Ira.

Provides latest news search for ice-breakers in sales emails,
lead intelligence enrichment, and industry trend monitoring.

API docs: https://newsdata.io/documentation
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("ira.tools.newsdata")

_BASE_URL = "https://newsdata.io/api/1/latest"

_CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "cache" / "newsdata"
_CACHE_TTL = 6 * 3600  # 6 hours — news doesn't change every minute

_BUSINESS_CATEGORIES = "business,technology,science,world"


def _cache_key(query: str, country: str, category: str) -> str:
    raw = f"{query}|{country}|{category}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()


def _read_cache(key: str) -> Optional[List[Dict[str, Any]]]:
    path = _CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data.get("ts", 0) < _CACHE_TTL:
            return data.get("articles", [])
    except Exception:
        pass
    return None


def _write_cache(key: str, articles: List[Dict[str, Any]]):
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {"ts": time.time(), "articles": articles}
        (_CACHE_DIR / f"{key}.json").write_text(json.dumps(payload, default=str))
    except Exception as e:
        logger.debug("NewsData cache write failed: %s", e)


def _format_article(a: Dict[str, Any]) -> str:
    title = a.get("title", "").strip()
    desc = (a.get("description") or "").strip()
    source = a.get("source_name") or a.get("source_id") or "unknown"
    pub = (a.get("pubDate") or "")[:10]
    link = a.get("link", "")

    parts = [f"• {title}"]
    if desc:
        parts.append(f"  {desc[:300]}")
    parts.append(f"  — {source}, {pub}")
    if link:
        parts.append(f"  {link}")
    return "\n".join(parts)


async def search_news(
    query: str,
    country: str = "",
    category: str = "",
    language: str = "en",
    max_results: int = 5,
) -> str:
    """
    Search NewsData.io for latest news articles.

    Returns a formatted string of top articles ready for LLM consumption.
    Falls back gracefully if API key is missing or request fails.
    """
    api_key = os.environ.get("NEWSDATA_API_KEY", "")
    if not api_key:
        return "(NewsData.io API key not configured — set NEWSDATA_API_KEY in .env)"

    cat = category or _BUSINESS_CATEGORIES
    ck = _cache_key(query, country, cat)
    cached = _read_cache(ck)
    if cached:
        logger.debug("NewsData cache hit for %r", query)
        formatted = [_format_article(a) for a in cached[:max_results]]
        return f"[Latest News for '{query}']\n\n" + "\n\n".join(formatted)

    params: Dict[str, Any] = {
        "apikey": api_key,
        "q": query,
        "language": language,
        "category": cat,
    }
    if country:
        params["country"] = country

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(_BASE_URL, params=params)

        if resp.status_code == 403:
            return "(NewsData.io: invalid API key or quota exceeded)"
        if resp.status_code == 429:
            return "(NewsData.io: rate limit hit — try again later)"
        if resp.status_code != 200:
            logger.warning("NewsData.io returned %d: %s", resp.status_code, resp.text[:200])
            return f"(NewsData.io error: HTTP {resp.status_code})"

        data = resp.json()
        if data.get("status") != "success":
            msg = data.get("results", {}).get("message", "unknown error")
            return f"(NewsData.io API error: {msg})"

        articles = data.get("results") or []
        if not articles:
            return f"(No recent news found for '{query}')"

        clean = []
        for a in articles[:max_results]:
            clean.append({
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "source_name": a.get("source_name", ""),
                "pubDate": a.get("pubDate", ""),
                "link": a.get("link", ""),
                "country": a.get("country", []),
                "category": a.get("category", []),
            })

        _write_cache(ck, clean)

        formatted = [_format_article(a) for a in clean]
        return f"[Latest News for '{query}']\n\n" + "\n\n".join(formatted)

    except httpx.TimeoutException:
        return "(NewsData.io request timed out)"
    except Exception as e:
        logger.warning("NewsData.io search failed: %s", e)
        return f"(NewsData.io error: {e})"
