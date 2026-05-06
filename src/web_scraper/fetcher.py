# Copyright (c) 2026 Adrian Azahid García / Strivark — MIT License
"""HTTP fetcher with robots.txt compliance, rate-limiting, and tenacity retries."""

from __future__ import annotations

import logging
import threading
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from web_scraper.config import settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Rate limiter (per-host token bucket — simple last-request timestamp approach)
# ──────────────────────────────────────────────────────────────────────────────

class _RateLimiter:
    """Ensures at most *rate* requests per second per host."""

    def __init__(self, rate: float = 1.0) -> None:
        self._rate = rate  # req/s
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, host: str) -> None:
        with self._lock:
            now = time.monotonic()
            last = self._last.get(host, 0.0)
            gap = 1.0 / self._rate
            sleep_for = gap - (now - last)
            if sleep_for > 0:
                time.sleep(sleep_for)
            self._last[host] = time.monotonic()


_rate_limiter = _RateLimiter(rate=settings.rate_limit)


# ──────────────────────────────────────────────────────────────────────────────
# robots.txt cache
# ──────────────────────────────────────────────────────────────────────────────

class _RobotsCache:
    def __init__(self) -> None:
        self._cache: dict[str, RobotFileParser] = {}

    def is_allowed(self, url: str, user_agent: str) -> bool:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base not in self._cache:
            rp = RobotFileParser()
            rp.set_url(f"{base}/robots.txt")
            try:
                rp.read()
            except Exception:
                # If robots.txt can't be fetched, assume allowed
                rp.allow_all = True  # type: ignore[attr-defined]
            self._cache[base] = rp
        return self._cache[base].can_fetch(user_agent, url)


_robots_cache = _RobotsCache()


# ──────────────────────────────────────────────────────────────────────────────
# Retryable fetch
# ──────────────────────────────────────────────────────────────────────────────

_RETRYABLE = (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)


def _fetch_with_retry(
    c: httpx.Client,
    url: str,
    headers: dict[str, str],
    max_retries: int,
) -> httpx.Response:
    """Inner fetch with tenacity retry applied at call time."""

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _inner() -> httpx.Response:
        resp = c.get(url, headers=headers, timeout=settings.timeout, follow_redirects=True)
        resp.raise_for_status()
        return resp

    return _inner()


def fetch(
    url: str,
    *,
    client: httpx.Client | None = None,
    max_retries: int | None = None,
    respect_robots: bool = True,
) -> httpx.Response:
    """Fetch *url* synchronously with rate-limiting, robots.txt check, and retries.

    Parameters
    ----------
    url:
        The URL to fetch.
    client:
        Optional existing ``httpx.Client``.  A temporary one is created when absent.
    max_retries:
        Override ``settings.max_retries``.
    respect_robots:
        When ``True`` (default) raise ``PermissionError`` if disallowed.

    Raises
    ------
    PermissionError
        If robots.txt disallows the URL.
    httpx.HTTPStatusError
        On non-2xx responses after all retries.
    """
    retries = max_retries if max_retries is not None else settings.max_retries

    if respect_robots and not _robots_cache.is_allowed(url, settings.user_agent):
        raise PermissionError(
            f"robots.txt disallows scraping '{url}' with agent '{settings.user_agent}'.\n"
            "Respecting the site's crawling policy."
        )

    host = urlparse(url).netloc
    _rate_limiter.wait(host)

    headers = {"User-Agent": settings.user_agent}

    if client is not None:
        return _fetch_with_retry(client, url, headers, retries)

    with httpx.Client() as tmp_client:
        return _fetch_with_retry(tmp_client, url, headers, retries)


def fetch_all_pages(
    start_url: str,
    next_selector: str,
    *,
    max_pages: int = 50,
    client: httpx.Client | None = None,
    respect_robots: bool = True,
) -> list[str]:
    """Fetch all paginated pages starting from *start_url*.

    Parameters
    ----------
    start_url:
        URL of the first page.
    next_selector:
        CSS selector that resolves to the ``<a>`` tag for the "next page" link.
    max_pages:
        Safety ceiling to prevent infinite crawling (default 50).
    client:
        Reusable ``httpx.Client``.
    respect_robots:
        Passed through to :func:`fetch`.

    Returns
    -------
    list[str]
        HTML content for every page collected.
    """
    from bs4 import BeautifulSoup

    pages: list[str] = []
    url: str | None = start_url
    base_parsed = urlparse(start_url)
    base_url = f"{base_parsed.scheme}://{base_parsed.netloc}"

    def _resolve(href: str) -> str:
        if href.startswith("http"):
            return href
        return base_url + (href if href.startswith("/") else f"/{href}")

    visited: set[str] = set()

    with (client or httpx.Client()) as c:
        while url and len(pages) < max_pages:
            if url in visited:
                break
            visited.add(url)
            resp = fetch(url, client=c, respect_robots=respect_robots)
            pages.append(resp.text)
            soup = BeautifulSoup(resp.text, "lxml")
            next_tag = soup.select_one(next_selector)
            if next_tag and next_tag.get("href"):
                url = _resolve(str(next_tag["href"]))
            else:
                break

    return pages
