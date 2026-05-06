# Copyright (c) 2026 Adrian Azahid García / Strivark — MIT License
"""CLI entry-point for web-scraper-pro."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import click
import httpx

from web_scraper import __version__
from web_scraper.config import settings
from web_scraper.exporter import export
from web_scraper.fetcher import fetch, fetch_all_pages
from web_scraper.parser import parse_fields_spec, parse_listings
from web_scraper.scheduler import watch as run_watch

# ──────────────────────────────────────────────────────────────────────────────
# Logging setup
# ──────────────────────────────────────────────────────────────────────────────

def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=level,
        stream=sys.stderr,
    )


# ──────────────────────────────────────────────────────────────────────────────
# CLI root
# ──────────────────────────────────────────────────────────────────────────────

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-V", "--version")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Enable debug logging.")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """web-scraper-pro — responsible web scraping with Excel/CSV output.

    \b
    Examples:
      web-scraper scrape --url https://example.com \\
          --selector "div.listing-card" \\
          --fields "title:h2, price:.price, url:a@href" \\
          --output listings.xlsx

      web-scraper watch --url https://example.com \\
          --selector "div.listing-card" \\
          --fields "title:h2" \\
          --output listings.xlsx \\
          --interval 1h
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    _configure_logging(verbose)


# ──────────────────────────────────────────────────────────────────────────────
# scrape command
# ──────────────────────────────────────────────────────────────────────────────

@main.command()
@click.option("--url", "-u", required=True, help="Starting URL to scrape.")
@click.option(
    "--selector", "-s", required=True,
    help="CSS selector for listing container elements.",
)
@click.option(
    "--fields", "-f", required=True,
    help=(
        "Comma-separated field specs, e.g. "
        "'title:h2, price:.price, url:a@href'."
    ),
)
@click.option(
    "--output", "-o", required=True,
    help="Output file path (.xlsx or .csv).",
)
@click.option(
    "--paginate", "-p", default=None,
    help="CSS selector for the 'next page' link.",
)
@click.option(
    "--max-pages", default=50, show_default=True,
    help="Maximum number of pages to fetch.",
)
@click.option(
    "--no-robots", is_flag=True, default=False,
    help="Skip robots.txt check (use responsibly).",
)
@click.pass_context
def scrape(
    ctx: click.Context,
    url: str,
    selector: str,
    fields: str,
    output: str,
    paginate: str | None,
    max_pages: int,
    no_robots: bool,
) -> None:
    """Scrape a URL and export listings to Excel or CSV."""
    _configure_logging(ctx.obj.get("verbose", False))
    respect_robots = not no_robots

    try:
        field_specs = parse_fields_spec(fields)
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="--fields") from exc

    all_records: list[dict[str, Any]] = []

    try:
        if paginate:
            click.echo(f"Fetching paginated pages from {url} …", err=True)
            pages = fetch_all_pages(
                url,
                paginate,
                max_pages=max_pages,
                respect_robots=respect_robots,
            )
            for page_html in pages:
                all_records.extend(parse_listings(page_html, selector, field_specs))
        else:
            click.echo(f"Fetching {url} …", err=True)
            resp = fetch(url, respect_robots=respect_robots)
            all_records = parse_listings(resp.text, selector, field_specs)

    except PermissionError as exc:
        click.echo(f"🚫 {exc}", err=True)
        sys.exit(1)
    except httpx.HTTPStatusError as exc:
        click.echo(f"HTTP error {exc.response.status_code} fetching {exc.request.url}", err=True)
        sys.exit(1)
    except httpx.RequestError as exc:
        click.echo(f"Request error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Extracted {len(all_records)} records.", err=True)

    if not all_records:
        click.echo("⚠  No records found — check your selectors.", err=True)
        sys.exit(0)

    try:
        out_path = export(all_records, output)
        click.echo(f"✅  Saved to {out_path}")
    except ValueError as exc:
        click.echo(f"Export error: {exc}", err=True)
        sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# watch command
# ──────────────────────────────────────────────────────────────────────────────

@main.command()
@click.option("--url", "-u", required=True, help="URL to watch.")
@click.option(
    "--selector", "-s", required=True,
    help="CSS selector for listing container elements.",
)
@click.option(
    "--fields", "-f", required=True,
    help="Comma-separated field specs.",
)
@click.option(
    "--output", "-o", required=True,
    help="Output file path (.xlsx or .csv). Overwritten on each run.",
)
@click.option(
    "--interval", "-i", default=None,
    help=(
        "Polling interval (e.g. '1h', '30m', '60s'). "
        f"Defaults to SCRAPER_WATCH_INTERVAL env var (currently '{settings.watch_interval}')."
    ),
)
@click.option(
    "--notify-changes", is_flag=True, default=False,
    help="Log new records detected since the previous run.",
)
@click.option(
    "--no-robots", is_flag=True, default=False,
    help="Skip robots.txt check (use responsibly).",
)
@click.pass_context
def watch(
    ctx: click.Context,
    url: str,
    selector: str,
    fields: str,
    output: str,
    interval: str | None,
    notify_changes: bool,
    no_robots: bool,
) -> None:
    """Scrape a URL on a recurring interval (watch mode)."""
    _configure_logging(ctx.obj.get("verbose", False))
    respect_robots = not no_robots
    effective_interval = interval or settings.watch_interval

    try:
        field_specs = parse_fields_spec(fields)
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="--fields") from exc

    out_path = Path(output)

    def _job() -> list[dict[str, Any]]:
        resp = fetch(url, respect_robots=respect_robots)
        records = parse_listings(resp.text, selector, field_specs)
        export(records, out_path)
        return records

    click.echo(
        f"👁  Watch mode active. Interval={effective_interval}. Output={out_path}. "
        "Press Ctrl-C to stop.",
        err=True,
    )
    run_watch(_job, effective_interval, notify_changes=notify_changes)
