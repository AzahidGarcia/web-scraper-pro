# Copyright (c) 2026 Adrian Azahid García / Strivark — MIT License
"""web-scraper-pro: responsible, professional web scraping toolkit."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("web-scraper-pro")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = ["__version__"]
