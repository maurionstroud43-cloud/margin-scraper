# Flip Margin Scraper

Lightweight Python web app that scrapes eBay listing and sold data, then surfaces up to 40 high-margin products that look easy to flip.

## Run locally

```bash
python app.py
```

Then open:

- http://localhost:8000
- http://127.0.0.1:8000

## Test it

### 1) Run unit tests

```bash
python -m unittest discover -s tests -v
```

### 2) Quick server health check

Start the server in one terminal:

```bash
python app.py
```

In another terminal, verify the page loads:

```bash
curl -i http://127.0.0.1:8000/ | head -n 20
```

### 3) Python syntax check

```bash
python -m py_compile app.py
```

## GitHub Pages deployment (no API key required)

This repo now includes `.github/workflows/deploy-pages.yml`.

- On push to `work`, GitHub Actions runs `python generate_site_data.py`.
- It publishes the `site/` folder as GitHub Pages.
- The hosted page is a **static demo** (latest generated results), while live scraping remains local via `python app.py`.

## How it ranks opportunities

- Pulls current buy-now prices and sold listing prices for each keyword.
- Estimates buy price from lower current prices.
- Estimates resale price from upper sold prices.
- Computes margin and confidence score.
- Keeps candidates with margin > 15%, sorts descending, and returns up to target count.
