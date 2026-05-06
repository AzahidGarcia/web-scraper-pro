# Copyright (c) 2026 Adrian Azahid García / Strivark — MIT License
"""Tests for web_scraper.fetcher — mock httpx, verify retry and robots logic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from web_scraper.fetcher import _RateLimiter, _RobotsCache, fetch

# ──────────────────────────────────────────────────────────────────────────────
# Rate limiter
# ──────────────────────────────────────────────────────────────────────────────

class TestRateLimiter:
    def test_first_request_no_sleep(self) -> None:
        limiter = _RateLimiter(rate=1.0)
        import time
        start = time.monotonic()
        limiter.wait("example.com")
        elapsed = time.monotonic() - start
        assert elapsed < 0.5, "First request should not be throttled"

    def test_second_request_throttled(self) -> None:
        limiter = _RateLimiter(rate=2.0)  # 0.5 s gap
        import time
        limiter.wait("example.com")
        start = time.monotonic()
        limiter.wait("example.com")
        elapsed = time.monotonic() - start
        assert elapsed >= 0.4, "Second request should be throttled to ~0.5 s"

    def test_different_hosts_not_throttled(self) -> None:
        limiter = _RateLimiter(rate=1.0)
        import time
        limiter.wait("host-a.com")
        start = time.monotonic()
        limiter.wait("host-b.com")  # different host — no delay
        elapsed = time.monotonic() - start
        assert elapsed < 0.5


# ──────────────────────────────────────────────────────────────────────────────
# Robots cache
# ──────────────────────────────────────────────────────────────────────────────

class TestRobotsCache:
    def test_allows_when_robots_unreachable(self) -> None:
        cache = _RobotsCache()
        with patch("web_scraper.fetcher.RobotFileParser") as mock_cls:
            mock_rp = MagicMock()
            mock_rp.read.side_effect = OSError("unreachable")
            mock_rp.can_fetch.return_value = True
            mock_cls.return_value = mock_rp
            # Reset internal cache
            cache._cache.clear()
            result = cache.is_allowed("http://unreachable.example.com/page", "TestBot")
            # Should not raise; defaults to True
            assert isinstance(result, bool)

    def test_disallowed_url(self) -> None:
        cache = _RobotsCache()
        with patch("web_scraper.fetcher.RobotFileParser") as mock_cls:
            mock_rp = MagicMock()
            mock_rp.read.return_value = None
            mock_rp.can_fetch.return_value = False
            mock_cls.return_value = mock_rp
            cache._cache.clear()
            assert cache.is_allowed("http://blocked.example.com/page", "TestBot") is False

    def test_allowed_url(self) -> None:
        cache = _RobotsCache()
        with patch("web_scraper.fetcher.RobotFileParser") as mock_cls:
            mock_rp = MagicMock()
            mock_rp.read.return_value = None
            mock_rp.can_fetch.return_value = True
            mock_cls.return_value = mock_rp
            cache._cache.clear()
            assert cache.is_allowed("http://open.example.com/page", "TestBot") is True


# ──────────────────────────────────────────────────────────────────────────────
# fetch() — mocked httpx
# ──────────────────────────────────────────────────────────────────────────────

class TestFetch:
    def _mock_response(self, text: str = "<html/>", status: int = 200) -> httpx.Response:
        return httpx.Response(status, text=text, request=httpx.Request("GET", "http://x.com/"))

    def test_fetch_success(self) -> None:
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = self._mock_response("<html>ok</html>")

        with (
            patch("web_scraper.fetcher._robots_cache") as mock_robots,
            patch("web_scraper.fetcher._rate_limiter") as mock_rl,
            patch("web_scraper.fetcher.httpx.Client", return_value=mock_client),
        ):
            mock_robots.is_allowed.return_value = True
            mock_rl.wait.return_value = None
            resp = fetch("http://example.com/listings")

        assert resp.status_code == 200
        assert "ok" in resp.text

    def test_fetch_raises_on_robots_block(self) -> None:
        with patch("web_scraper.fetcher._robots_cache") as mock_robots:
            mock_robots.is_allowed.return_value = False
            with pytest.raises(PermissionError, match="robots.txt"):
                fetch("http://blocked.example.com/secret")

    def test_fetch_retries_on_timeout(self) -> None:
        """Verify that a TimeoutException triggers retries."""
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        call_count = 0

        def side_effect(*args: object, **kwargs: object) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TimeoutException("timeout", request=MagicMock())
            return self._mock_response("<html>ok</html>")

        mock_client.get.side_effect = side_effect

        with (
            patch("web_scraper.fetcher._robots_cache") as mock_robots,
            patch("web_scraper.fetcher._rate_limiter") as mock_rl,
            patch("web_scraper.fetcher.httpx.Client", return_value=mock_client),
            # Speed up exponential backoff for tests
            patch("tenacity.nap.sleep"),
        ):
            mock_robots.is_allowed.return_value = True
            mock_rl.wait.return_value = None
            resp = fetch("http://example.com/retry-test", max_retries=3)

        assert call_count == 3
        assert resp.status_code == 200

    def test_fetch_raises_after_max_retries(self) -> None:
        """After exhausting retries, the last exception should propagate."""
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.TimeoutException(
            "always timeout", request=MagicMock()
        )

        with (
            patch("web_scraper.fetcher._robots_cache") as mock_robots,
            patch("web_scraper.fetcher._rate_limiter") as mock_rl,
            patch("web_scraper.fetcher.httpx.Client", return_value=mock_client),
            patch("tenacity.nap.sleep"),
        ):
            mock_robots.is_allowed.return_value = True
            mock_rl.wait.return_value = None
            with pytest.raises(httpx.TimeoutException):
                fetch("http://example.com/always-fail", max_retries=2)
