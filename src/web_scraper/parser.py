# Copyright (c) 2026 Adrian Azahid García / Strivark — MIT License
"""HTML parser: extract structured fields from pages using CSS selectors."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

# Field spec format: "label:css_selector[@attr]"
# Examples:
#   "title:h2"          → text content of <h2>
#   "url:a@href"        → href attribute of <a>
#   "price:.price"      → text content of .price

_FIELD_RE = re.compile(
    r"^(?P<label>[^:]+):(?P<selector>[^@]+?)(?:@(?P<attr>\w+))?$"
)


def parse_field_spec(spec: str) -> tuple[str, str, str | None]:
    """Parse a single field spec string into *(label, selector, attr)*.

    Parameters
    ----------
    spec:
        A field specification like ``"title:h2"`` or ``"url:a@href"``.

    Returns
    -------
    tuple[str, str, str | None]
        *(label, css_selector, attribute_name_or_None)*

    Raises
    ------
    ValueError
        If the spec string is not parseable.
    """
    m = _FIELD_RE.match(spec.strip())
    if not m:
        raise ValueError(
            f"Cannot parse field spec '{spec}'. "
            "Expected format: 'label:css-selector' or 'label:css-selector@attr'."
        )
    return m.group("label").strip(), m.group("selector").strip(), m.group("attr")


def parse_fields_spec(raw: str) -> list[tuple[str, str, str | None]]:
    """Parse a comma-separated list of field specs.

    Parameters
    ----------
    raw:
        Comma-separated field specs, e.g.
        ``"title:h2, price:.price, url:a@href"``.

    Returns
    -------
    list[tuple[str, str, str | None]]
    """
    return [parse_field_spec(part) for part in raw.split(",")]


def _extract_value(tag: Tag, selector: str, attr: str | None) -> str:
    """Extract a value from *tag* using *selector* and optional *attr*."""
    el = tag.select_one(selector)
    if el is None:
        return ""
    if attr:
        return str(el.get(attr, "")).strip()
    return el.get_text(separator=" ", strip=True)


def parse_listings(
    html: str,
    container_selector: str,
    fields: list[tuple[str, str, str | None]],
) -> list[dict[str, Any]]:
    """Extract a list of structured records from *html*.

    Parameters
    ----------
    html:
        Raw HTML content of the page.
    container_selector:
        CSS selector matching each listing card / row.
    fields:
        List of *(label, selector, attr)* tuples describing which fields to
        extract from each container element.

    Returns
    -------
    list[dict[str, Any]]
        One dict per matched container element.
    """
    soup = BeautifulSoup(html, "lxml")
    records: list[dict[str, Any]] = []
    for container in soup.select(container_selector):
        if not isinstance(container, Tag):
            continue
        record: dict[str, Any] = {}
        for label, selector, attr in fields:
            record[label] = _extract_value(container, selector, attr)
        records.append(record)
    return records
