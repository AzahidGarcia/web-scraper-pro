#!/usr/bin/env bash
# Copyright (c) 2026 Adrian Azahid García / Strivark — MIT License
# ─────────────────────────────────────────────────────────────────────────────
# Example: scrape a listing page and export to Excel
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# Basic scrape — single page
web-scraper scrape \
    --url "https://books.toscrape.com/" \
    --selector "article.product_pod" \
    --fields "title:h3 a@title, price:.price_color, rating:.star-rating@class" \
    --output /tmp/books.xlsx

echo "Saved to /tmp/books.xlsx"

# ─────────────────────────────────────────────────────────────────────────────
# Paginated scrape — follow "next" button
# ─────────────────────────────────────────────────────────────────────────────
web-scraper scrape \
    --url "https://books.toscrape.com/" \
    --selector "article.product_pod" \
    --fields "title:h3 a@title, price:.price_color" \
    --paginate "li.next a" \
    --max-pages 3 \
    --output /tmp/books_paginated.xlsx

echo "Paginated scrape saved to /tmp/books_paginated.xlsx"

# ─────────────────────────────────────────────────────────────────────────────
# Watch mode — re-scrape every 30 minutes, log new listings
# ─────────────────────────────────────────────────────────────────────────────
# web-scraper watch \
#     --url "https://books.toscrape.com/" \
#     --selector "article.product_pod" \
#     --fields "title:h3 a@title, price:.price_color" \
#     --output /tmp/books_watch.xlsx \
#     --interval 30m \
#     --notify-changes
