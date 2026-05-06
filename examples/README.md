# Examples

## `scrape_listings.sh`

Demonstrates the three main usage patterns:

| Command | Description |
|---|---|
| Basic scrape | Fetch a single page and export to Excel |
| Paginated scrape | Follow pagination links up to `--max-pages` |
| Watch mode | Poll a URL on a recurring interval; log new records |

### Running

```bash
# Install the package first
pip install -e ".[dev]"

# Run the examples (targets books.toscrape.com — a scraping sandbox)
bash examples/scrape_listings.sh
```

> **Note:** `books.toscrape.com` is a dedicated scraping practice site.
> Always verify `robots.txt` before targeting any other URL.
> `web-scraper-pro` does this automatically by default.
