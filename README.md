# web-scraper-pro

> Responsible, portfolio-grade web scraping — Excel/CSV output, pagination,
> watch mode, and robots.txt compliance out of the box.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Quick Start](#quick-start)
4. [Installation](#installation)
5. [CLI Reference](#cli-reference)
6. [Configuration](#configuration)
7. [Output Formats](#output-formats)
8. [Watch Mode & Scheduling](#watch-mode--scheduling)
9. [JS-Heavy Sites (Playwright)](#js-heavy-sites-playwright)
10. [Project Structure](#project-structure)
11. [Development](#development)
12. [Testing](#testing)
13. [Responsible Scraping Policy](#responsible-scraping-policy)
14. [License](#license)

---

## Overview

`web-scraper-pro` is a command-line tool that turns any publicly accessible
website into a clean spreadsheet.  It was built with the philosophy that
**scraping responsibly is non-negotiable**: every request honours `robots.txt`,
carries an identifiable `User-Agent`, and respects a configurable rate limit.

---

## Features

| Feature | Details |
|---|---|
| **Responsible by default** | Checks `robots.txt` before every domain; refuses with a clear message if disallowed |
| **Rate limiting** | 1 req/s per host (configurable); prevents hammering servers |
| **Pagination** | Follow any CSS-selector-based "next page" link automatically |
| **Retries** | Exponential back-off via `tenacity` (3 attempts by default) |
| **Excel output** | Professional formatting — bold headers, auto-width columns, currency number format |
| **CSV output** | UTF-8, `DictWriter`-based, human-readable |
| **Watch mode** | Re-scrape on a cron-like interval; detects and logs new records |
| **GitHub Actions** | Drop-in scheduled workflow (`scheduled_scrape.yml`) |
| **Playwright support** | Optional JS-heavy scraping (install the `playwright` extra) |
| **Fully typed** | `mypy --strict` clean |

---

## Quick Start

```bash
# 1. Install
pip install web-scraper-pro

# 2. Scrape a page and export to Excel
web-scraper scrape \
    --url "https://books.toscrape.com/" \
    --selector "article.product_pod" \
    --fields "title:h3 a@title, price:.price_color" \
    --output books.xlsx

# 3. Paginated scrape (follow "Next" links, up to 5 pages)
web-scraper scrape \
    --url "https://books.toscrape.com/" \
    --selector "article.product_pod" \
    --fields "title:h3 a@title, price:.price_color" \
    --paginate "li.next a" \
    --max-pages 5 \
    --output books_all.xlsx

# 4. Watch mode — re-scrape every hour, log new items
web-scraper watch \
    --url "https://books.toscrape.com/" \
    --selector "article.product_pod" \
    --fields "title:h3 a@title, price:.price_color" \
    --output books_watch.xlsx \
    --interval 1h \
    --notify-changes
```

---

## Installation

### From PyPI *(coming soon)*

```bash
pip install web-scraper-pro
```

### From source

```bash
git clone https://github.com/AzahidGarcia/web-scraper-pro.git
cd web-scraper-pro
pip install -e ".[dev]"
```

### Optional: Playwright (JS-heavy sites)

```bash
pip install "web-scraper-pro[playwright]"
playwright install chromium
```

Then set `SCRAPER_USE_PLAYWRIGHT=1` in your `.env` or shell environment.

---

## CLI Reference

### `web-scraper scrape`

```
Usage: web-scraper scrape [OPTIONS]

  Scrape a URL and export listings to Excel or CSV.

Options:
  -u, --url TEXT          Starting URL to scrape.  [required]
  -s, --selector TEXT     CSS selector for listing container elements.  [required]
  -f, --fields TEXT       Comma-separated field specs, e.g.
                          'title:h2, price:.price, url:a@href'.  [required]
  -o, --output TEXT       Output file path (.xlsx or .csv).  [required]
  -p, --paginate TEXT     CSS selector for the 'next page' link.
      --max-pages INT     Maximum number of pages to fetch.  [default: 50]
      --no-robots         Skip robots.txt check (use responsibly).
  -v, --verbose           Enable debug logging.
  -h, --help              Show this message and exit.
```

#### Field spec syntax

```
label:css-selector
label:css-selector@attribute
```

Examples:

| Spec | Extracts |
|---|---|
| `title:h2` | Text content of the first `<h2>` inside the container |
| `url:a@href` | `href` attribute of the first `<a>` |
| `price:.listing-price` | Text content of `.listing-price` |
| `img:img@src` | `src` attribute of the first `<img>` |

### `web-scraper watch`

```
Usage: web-scraper watch [OPTIONS]

  Scrape a URL on a recurring interval (watch mode).

Options:
  -u, --url TEXT          URL to watch.  [required]
  -s, --selector TEXT     CSS selector for listing container elements.  [required]
  -f, --fields TEXT       Comma-separated field specs.  [required]
  -o, --output TEXT       Output file path (.xlsx or .csv). Overwritten each run.  [required]
  -i, --interval TEXT     Polling interval (e.g. '1h', '30m', '60s').
      --notify-changes    Log new records detected since the previous run.
      --no-robots         Skip robots.txt check.
  -h, --help              Show this message and exit.
```

---

## Configuration

Copy `.env.example` to `.env` and edit as needed:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `SCRAPER_RATE_LIMIT` | `1.0` | Requests per second per host |
| `SCRAPER_TIMEOUT` | `30` | HTTP request timeout (seconds) |
| `SCRAPER_USER_AGENT` | *(built-in)* | Custom User-Agent header |
| `SCRAPER_MAX_RETRIES` | `3` | Retry attempts on transient errors |
| `SCRAPER_USE_PLAYWRIGHT` | `0` | Set `1` to enable Playwright |
| `SCRAPER_WATCH_INTERVAL` | `1h` | Default watch interval |

---

## Output Formats

### Excel (`.xlsx`)

- Bold, dark-blue header row with white text
- Frozen top row for easy scrolling
- Auto-fitted column widths
- Numeric format (`#,##0.00`) applied to price/cost/amount columns

### CSV (`.csv`)

- UTF-8 encoding
- Standard RFC 4180 format
- Compatible with Excel, Google Sheets, pandas

---

## Watch Mode & Scheduling

### CLI watch mode

```bash
web-scraper watch \
    --url "https://example.com/listings" \
    --selector "div.listing-card" \
    --fields "title:h2, price:.price" \
    --output listings.xlsx \
    --interval 30m \
    --notify-changes
```

The output file is overwritten on each successful run.
Press `Ctrl-C` to stop.

### GitHub Actions cron

The repository ships with `.github/workflows/scheduled_scrape.yml`.
It runs daily at 08:00 UTC and uploads the Excel file as a workflow artifact.

To customise the schedule, edit the `cron` expression:

```yaml
on:
  schedule:
    - cron: "0 8 * * *"   # daily at 08:00 UTC
```

---

## JS-Heavy Sites (Playwright)

Some pages render content via JavaScript. Install the optional extra:

```bash
pip install "web-scraper-pro[playwright]"
playwright install chromium
```

Enable in your environment:

```bash
export SCRAPER_USE_PLAYWRIGHT=1
```

Then use the same CLI commands — the fetcher will delegate to Playwright
automatically when this flag is set.

> **Note:** Playwright is an *optional* dependency. The core package works
> without it for standard HTML pages.

---

## Project Structure

```
web-scraper-pro/
├── pyproject.toml
├── README.md
├── LICENSE                         MIT — Adrian Azahid García / Strivark
├── .gitignore
├── .env.example
├── src/
│   └── web_scraper/
│       ├── __init__.py
│       ├── cli.py                  click CLI: scrape + watch commands
│       ├── fetcher.py              httpx + robots.txt + tenacity retries
│       ├── parser.py               BeautifulSoup CSS-selector extractor
│       ├── exporter.py             Excel / CSV writers
│       ├── scheduler.py            Watch-mode loop
│       └── config.py               Settings from env vars
├── tests/
│   ├── conftest.py
│   ├── test_fetcher.py
│   ├── test_parser.py
│   ├── test_exporter.py
│   └── fixtures/
│       └── sample_html.html
├── examples/
│   ├── scrape_listings.sh
│   └── README.md
└── .github/
    └── workflows/
        └── scheduled_scrape.yml
```

---

## Development

```bash
# Clone and install in editable mode with dev extras
git clone https://github.com/AzahidGarcia/web-scraper-pro.git
cd web-scraper-pro
pip install -e ".[dev]"

# Lint
ruff check .

# Type-check
mypy src/

# Run all tests
pytest
```

---

## Testing

Tests live in `tests/` and are split by module:

| File | Covers |
|---|---|
| `test_fetcher.py` | Rate limiter, robots.txt cache, HTTP retry logic (mocked httpx) |
| `test_parser.py` | CSS-selector extraction using `tests/fixtures/sample_html.html` |
| `test_exporter.py` | Excel/CSV generation, header formatting, currency detection |

```bash
pytest -v
```

---

## Responsible Scraping Policy

`web-scraper-pro` is built around three principles:

1. **Respect `robots.txt`** — checked automatically before every new domain.
   A `PermissionError` is raised with a clear human-readable message if the
   site disallows the configured User-Agent.

2. **Rate limiting** — defaults to 1 request per second per host.
   Override with `SCRAPER_RATE_LIMIT` — but please be considerate.

3. **Identifiable User-Agent** — every request sends a User-Agent string that
   identifies the bot and links to this repository, so site operators can
   contact the scraper operator.

Never use `--no-robots` to bypass `robots.txt` without the site owner's
explicit permission.

---

## License

MIT © 2026 Adrian Azahid García / Strivark.
See [LICENSE](LICENSE) for the full text.

---

*Part of Strivark's portfolio of automation tools.*
