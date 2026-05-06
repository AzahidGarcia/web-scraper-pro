# Copyright (c) 2026 Adrian Azahid García / Strivark — MIT License
"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def sample_html() -> str:
    """Return the content of the sample HTML fixture."""
    return (FIXTURES_DIR / "sample_html.html").read_text(encoding="utf-8")
