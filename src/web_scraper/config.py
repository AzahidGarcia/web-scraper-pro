# Copyright (c) 2026 Adrian Azahid García / Strivark — MIT License
"""Configuration loaded from environment / .env file."""

from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (silently skip if absent)
load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)


DEFAULT_USER_AGENT = (
    "web-scraper-pro/1.0 (responsible bot; "
    "https://github.com/AzahidGarcia/web-scraper-pro)"
)

_INTERVAL_RE = re.compile(r"^(?P<value>\d+(?:\.\d+)?)(?P<unit>[smh])$")


def parse_interval(raw: str) -> float:
    """Convert a human interval string (``"1h"``, ``"30m"``, ``"60s"``) to seconds."""
    m = _INTERVAL_RE.match(raw.strip().lower())
    if not m:
        raise ValueError(
            f"Invalid interval '{raw}'. Use format: <number><s|m|h>  e.g. '1h', '30m'."
        )
    value = float(m.group("value"))
    unit = m.group("unit")
    multipliers = {"s": 1, "m": 60, "h": 3600}
    return value * multipliers[unit]


class Settings:
    """Central settings object populated from env vars."""

    rate_limit: float
    timeout: int
    user_agent: str
    max_retries: int
    use_playwright: bool
    watch_interval: str

    def __init__(self) -> None:
        self.rate_limit = float(os.environ.get("SCRAPER_RATE_LIMIT", "1.0"))
        self.timeout = int(os.environ.get("SCRAPER_TIMEOUT", "30"))
        self.user_agent = (
            os.environ.get("SCRAPER_USER_AGENT", "").strip() or DEFAULT_USER_AGENT
        )
        self.max_retries = int(os.environ.get("SCRAPER_MAX_RETRIES", "3"))
        self.use_playwright = os.environ.get("SCRAPER_USE_PLAYWRIGHT", "0") == "1"
        self.watch_interval = os.environ.get("SCRAPER_WATCH_INTERVAL", "1h")


settings = Settings()
