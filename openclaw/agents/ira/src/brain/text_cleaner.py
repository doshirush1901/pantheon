#!/usr/bin/env python3
"""
Centralized Text Cleaning Utility
==================================

Single source of truth for converting raw HTML into clean, readable text.
Used by url_fetcher.py and any other module that handles web content.

Strategy:
1. trafilatura (best quality for articles, handles boilerplate removal)
2. Fallback: regex-based HTML stripping (no external deps beyond stdlib)

Usage:
    from text_cleaner import clean_html_to_text

    text = clean_html_to_text(raw_html)
"""

import re
import logging
from html import unescape
from typing import Optional

logger = logging.getLogger(__name__)


def clean_html_to_text(html: str, include_tables: bool = True) -> str:
    """Convert raw HTML to clean text.

    Tries trafilatura first (high-quality article extraction with boilerplate
    removal), then falls back to regex-based stripping.

    Args:
        html: Raw HTML string
        include_tables: Whether to preserve table content (trafilatura only)

    Returns:
        Cleaned text string
    """
    if not html or not html.strip():
        return ""

    # 1. Try trafilatura (handles nav, footer, ads, cookie banners, etc.)
    text = _clean_with_trafilatura(html, include_tables)
    if text and len(text.strip()) > 100:
        return _normalize_whitespace(text)

    # 2. Fallback: regex stripping
    return _clean_with_regex(html)


def extract_title(html: str) -> str:
    """Extract the page title from HTML."""
    try:
        import trafilatura
        meta = trafilatura.extract_metadata(html)
        if meta and meta.title:
            return meta.title
    except (ImportError, Exception):
        pass

    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        return unescape(match.group(1).strip())[:300]
    return ""


def _clean_with_trafilatura(html: str, include_tables: bool) -> Optional[str]:
    """Use trafilatura for high-quality extraction."""
    try:
        import trafilatura
        result = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=include_tables,
            no_fallback=False,
            favor_precision=True,
        )
        return result
    except ImportError:
        return None
    except Exception as e:
        logger.debug(f"[TEXT_CLEANER] trafilatura failed: {e}")
        return None


def _clean_with_regex(html: str) -> str:
    """Fallback HTML-to-text using regex. No external dependencies."""
    text = html

    # Remove script and style blocks entirely
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<noscript[^>]*>.*?</noscript>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Convert common block elements to newlines
    text = re.sub(r"<(?:br|hr|p|div|li|tr|h[1-6])[^>]*>", "\n", text, flags=re.IGNORECASE)

    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Decode HTML entities
    text = unescape(text)

    return _normalize_whitespace(text)


def _normalize_whitespace(text: str) -> str:
    """Collapse excessive whitespace while preserving paragraph breaks."""
    # Collapse runs of blank lines to max 2 newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse horizontal whitespace (tabs, multiple spaces)
    text = re.sub(r"[^\S\n]+", " ", text)
    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines).strip()
