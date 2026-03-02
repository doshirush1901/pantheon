#!/usr/bin/env python3
"""
MOUTH (URL): Web Content Ingestion
===================================

Fetches and extracts main content from URLs for Ira's knowledge base.
Used when the user shares a URL via Telegram for ingestion.

Strategy:
1. Jina Reader (r.jina.ai) - returns clean markdown, handles JS-heavy sites
2. Fallback: trafilatura if installed (best for articles)
3. Fallback: requests + basic HTML stripping

Usage:
    from url_fetcher import fetch_url_content

    text, metadata = fetch_url_content("https://example.com/article")
"""

import ipaddress
import logging
import re
import socket
from typing import Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _is_safe_url(url: str) -> bool:
    """Block URLs targeting private/internal networks (SSRF protection)."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if not hostname:
            return False
        if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False
        if hostname.endswith(".local") or hostname.endswith(".internal"):
            return False
        try:
            resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for _, _, _, _, sockaddr in resolved:
                ip = ipaddress.ip_address(sockaddr[0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    logger.warning(f"[SSRF] Blocked URL resolving to private IP: {hostname} -> {ip}")
                    return False
        except (socket.gaierror, ValueError):
            return False
        return True
    except Exception:
        return False

# Match http(s) URLs
URL_RE = re.compile(
    r'https?://'
    r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}'
    r'(?::\d+)?'
    r'(?:/[^\s]*)?',
    re.IGNORECASE,
)


def _safe_fetch(url: str, max_redirects: int = 5, **kwargs) -> Optional["requests.Response"]:
    """Fetch URL with SSRF check on every redirect hop."""
    import requests as _requests
    for _ in range(max_redirects):
        if not _is_safe_url(url):
            logger.warning("[SSRF] Blocked URL after redirect: %s", url)
            return None
        resp = _requests.get(
            url,
            allow_redirects=False,
            timeout=kwargs.get("timeout", 15),
            headers=kwargs.get("headers"),
        )
        if resp.status_code in (301, 302, 303, 307, 308):
            url = resp.headers.get("Location", "")
            if not url:
                return None
            continue
        return resp
    logger.warning("[SSRF] Too many redirects for URL")
    return None


def extract_first_url(text: str) -> Optional[str]:
    """Extract the first URL from text. Returns None if no URL found."""
    if not text or not text.strip():
        return None
    match = URL_RE.search(text.strip())
    return match.group(0) if match else None


def is_bare_url_message(text: str) -> bool:
    """True if the message is essentially just a URL (with optional short caption)."""
    if not text or not text.strip():
        return False
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return False
    first = lines[0]
    # First line must be a URL
    if not URL_RE.fullmatch(first):
        return False
    # If there are more lines, the caption should be short (e.g. < 200 chars total)
    if len(lines) > 1:
        caption = " ".join(lines[1:])
        if len(caption) > 300:  # Long text = probably not a URL caption
            return False
    return True


def fetch_url_content(url: str, timeout: int = 25) -> Tuple[Optional[str], dict]:
    """Fetch and extract main content from a URL.

    Returns:
        (extracted_text, metadata) where metadata has:
        - source: "jina" | "trafilatura" | "requests"
        - url: str
        - title: str (if available)
        - error: str (if failed)
    """
    metadata = {"url": url, "source": None, "title": "", "error": None}

    if not _is_safe_url(url):
        metadata["error"] = "URL blocked: targets private/internal network"
        logger.warning(f"[SSRF] Blocked fetch for: {url}")
        return None, metadata

    # 1. Try Jina Reader (handles JS, returns markdown)
    try:
        jina_url = f"https://r.jina.ai/{url}"
        resp = _safe_fetch(
            jina_url,
            timeout=timeout,
            headers={
                "Accept": "text/markdown",
                "User-Agent": "Ira/1.0 (Knowledge Ingestion)",
            },
        )
        if resp and resp.status_code == 200 and len(resp.text.strip()) > 100:
            metadata["source"] = "jina"
            lines = resp.text.strip().splitlines()
            if lines and not lines[0].startswith("#"):
                metadata["title"] = lines[0][:200]
            return resp.text.strip(), metadata
    except Exception as e:
        metadata["error"] = str(e)[:100]
        logger.debug(f"[URL] Jina fetch failed: {e}")

    # 2. Fallback: fetch raw HTML and clean with centralized text_cleaner
    try:
        resp = _safe_fetch(url, timeout=timeout, headers={"User-Agent": "Ira/1.0"})
        if resp and resp.status_code == 200:
            raw_html = resp.text
            try:
                from .text_cleaner import clean_html_to_text, extract_title
                cleaned = clean_html_to_text(raw_html)
                if cleaned and len(cleaned.strip()) > 100:
                    metadata["source"] = "text_cleaner"
                    metadata["title"] = extract_title(raw_html)
                    return cleaned.strip()[:50000], metadata
            except ImportError:
                pass

            # Last resort: inline regex strip (if text_cleaner unavailable)
            from html import unescape
            text = raw_html
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            text = unescape(text).strip()
            if len(text) > 200:
                metadata["source"] = "requests"
                return text[:50000], metadata
    except Exception as e:
        if not metadata.get("error"):
            metadata["error"] = str(e)[:100]

    return None, metadata
