# Copyright (c) 2026 Adrian Azahid García / Strivark — MIT License
"""Tests for web_scraper.parser — BeautifulSoup selectors with HTML fixture."""

from __future__ import annotations

import pytest

from web_scraper.parser import parse_field_spec, parse_fields_spec, parse_listings


class TestParseFieldSpec:
    def test_text_field(self) -> None:
        label, selector, attr = parse_field_spec("title:h2")
        assert label == "title"
        assert selector == "h2"
        assert attr is None

    def test_attr_field(self) -> None:
        label, selector, attr = parse_field_spec("url:a@href")
        assert label == "url"
        assert selector == "a"
        assert attr == "href"

    def test_complex_selector(self) -> None:
        label, selector, attr = parse_field_spec("price:.listing-card .price")
        assert label == "price"
        assert selector == ".listing-card .price"
        assert attr is None

    def test_invalid_spec_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse field spec"):
            parse_field_spec("no-colon-here")

    def test_whitespace_tolerance(self) -> None:
        label, selector, attr = parse_field_spec("  title : h2 ")
        assert label == "title"
        assert selector == "h2"


class TestParseFieldsSpec:
    def test_multiple_fields(self) -> None:
        specs = parse_fields_spec("title:h2, price:.price, url:a@href")
        assert len(specs) == 3
        assert specs[0] == ("title", "h2", None)
        assert specs[1] == ("price", ".price", None)
        assert specs[2] == ("url", "a", "href")


class TestParseListings:
    def test_extracts_three_listings(self, sample_html: str) -> None:
        fields = parse_fields_spec("title:h2, price:.price, url:a@href")
        records = parse_listings(sample_html, "div.listing-card", fields)
        assert len(records) == 3

    def test_listing_fields_correct(self, sample_html: str) -> None:
        fields = parse_fields_spec("title:h2, price:.price, url:a@href")
        records = parse_listings(sample_html, "div.listing-card", fields)
        first = records[0]
        assert first["title"] == "Cozy Studio Downtown"
        assert first["price"] == "$1,200/mo"
        assert first["url"] == "/listing/1"

    def test_missing_selector_returns_empty_string(self, sample_html: str) -> None:
        fields = parse_fields_spec("nonexistent:.does-not-exist")
        records = parse_listings(sample_html, "div.listing-card", fields)
        assert all(r["nonexistent"] == "" for r in records)

    def test_no_containers_returns_empty_list(self, sample_html: str) -> None:
        fields = parse_fields_spec("title:h2")
        records = parse_listings(sample_html, "div.no-such-class", fields)
        assert records == []

    def test_all_listings_have_expected_keys(self, sample_html: str) -> None:
        fields = parse_fields_spec("title:h2, price:.price")
        records = parse_listings(sample_html, "div.listing-card", fields)
        for rec in records:
            assert "title" in rec
            assert "price" in rec
