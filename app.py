from __future__ import annotations

from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser
from statistics import mean
from typing import Iterable
from urllib.parse import parse_qs, quote_plus
from urllib.request import Request, urlopen
import socketserver
import http.server

HOST = "0.0.0.0"
PORT = 8000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}
DEFAULT_QUERIES = [
    "vintage camera",
    "lego set",
    "gameboy",
    "cast iron pan",
    "sony walkman",
    "vinyl record lot",
    "pokemon cards lot",
    "guitar pedal",
    "mechanical keyboard",
    "power tools",
]


@dataclass
class MarginItem:
    query: str
    current_price: float
    sold_avg_price: float
    margin_percent: float
    confidence: float
    source_url: str


class EbayPriceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.capture = False
        self.prices: list[float] = []

    def handle_starttag(self, tag, attrs):
        if tag != "span":
            return
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "")
        if "s-item__price" in classes:
            self.capture = True

    def handle_endtag(self, tag):
        if tag == "span":
            self.capture = False

    def handle_data(self, data):
        if not self.capture:
            return
        value = parse_price(data)
        if value is not None and value > 1:
            self.prices.append(value)


def parse_price(text: str) -> float | None:
    digits = "".join(ch for ch in text if ch.isdigit() or ch in ".,")
    if not digits:
        return None
    digits = digits.replace(",", "")
    try:
        return float(digits)
    except ValueError:
        return None


def fetch_ebay_prices(query: str, sold: bool = False, limit: int = 30) -> list[float]:
    url = f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}&LH_BIN=1"
    if sold:
        url += "&LH_Sold=1&LH_Complete=1"

    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=12) as response:
        html = response.read().decode("utf-8", errors="ignore")

    parser = EbayPriceParser()
    parser.feed(html)
    return parser.prices[:limit]


def score_item(current_prices: Iterable[float], sold_prices: Iterable[float], query: str) -> MarginItem | None:
    current_prices = list(current_prices)
    sold_prices = list(sold_prices)
    if len(current_prices) < 3 or len(sold_prices) < 3:
        return None

    buy_price = mean(sorted(current_prices)[:5])
    resale_price = mean(sorted(sold_prices)[-5:])
    if buy_price <= 0:
        return None

    margin = ((resale_price - buy_price) / buy_price) * 100
    confidence = min(1.0, (len(current_prices) + len(sold_prices)) / 60)
    return MarginItem(
        query=query,
        current_price=round(buy_price, 2),
        sold_avg_price=round(resale_price, 2),
        margin_percent=round(margin, 2),
        confidence=round(confidence * 100, 1),
        source_url=f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}",
    )


def build_margin_board(queries: list[str], target_count: int = 40) -> tuple[list[MarginItem], list[str]]:
    items: list[MarginItem] = []
    errors: list[str] = []
    expanded_queries = list(queries)

    for seed in queries:
        expanded_queries.extend([f"{seed} used", f"{seed} lot", f"{seed} tested"])

    for query in expanded_queries:
        if len(items) >= target_count:
            break
        try:
            current = fetch_ebay_prices(query, sold=False)
            sold = fetch_ebay_prices(query, sold=True)
            scored = score_item(current, sold, query)
            if scored and scored.margin_percent > 15:
                items.append(scored)
        except Exception as exc:
            errors.append(f"{query}: {exc}")

    ranked = sorted(items, key=lambda i: (i.margin_percent, i.confidence), reverse=True)
    return ranked[:target_count], errors[:8]


def render_page(items: list[MarginItem], errors: list[str], raw_queries: str, target_count: int) -> str:
    rows = "\n".join(
        f"<tr><td>{escape(i.query)}</td><td>{i.current_price}</td><td>{i.sold_avg_price}</td>"
        f"<td class='strong'>{i.margin_percent}</td><td>{i.confidence}</td>"
        f"<td><a href='{escape(i.source_url)}' target='_blank' rel='noreferrer'>View</a></td></tr>"
        for i in items
    )
    if not rows:
        rows = "<tr><td colspan='6'>No items yet. Click scrape.</td></tr>"

    warning_html = ""
    if errors:
        lis = "".join(f"<li>{escape(err)}</li>" for err in errors)
        warning_html = f"<section class='panel warning'><h2>Scrape warnings</h2><ul>{lis}</ul></section>"

    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'/>
<meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>Flip Margin Scraper</title>
<link rel='stylesheet' href='/static/style.css'/>
</head>
<body>
<main class='container'>
<header>
<h1>Flip Margin Scraper</h1>
<p>Scrapes eBay current + sold listings and ranks up to {target_count} easy-to-flip opportunities.</p>
</header>
<form method='post' class='panel'>
<label for='limit'>Target item count (max 60)</label>
<input id='limit' name='limit' type='number' min='5' max='60' value='{target_count}' />
<label for='queries'>Search seeds (one per line)</label>
<textarea id='queries' name='queries' rows='8'>{escape(raw_queries)}</textarea>
<button type='submit'>Scrape margin items</button>
</form>
{warning_html}
<section class='panel'>
<h2>Top opportunities</h2>
<table>
<thead><tr><th>Keyword</th><th>Buy Avg ($)</th><th>Sold Avg ($)</th><th>Margin %</th><th>Confidence %</th><th>Link</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</section>
</main>
</body>
</html>"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/static/"):
            return super().do_GET()

        raw_queries = "\n".join(DEFAULT_QUERIES)
        page = render_page([], [], raw_queries, 40)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(content_len).decode("utf-8", errors="ignore")
        data = parse_qs(payload)

        raw_queries = data.get("queries", [""])[0]
        queries = [q.strip() for q in raw_queries.splitlines() if q.strip()] or DEFAULT_QUERIES
        try:
            target_count = max(5, min(60, int(data.get("limit", ["40"])[0])))
        except ValueError:
            target_count = 40

        items, errors = build_margin_board(queries, target_count=target_count)
        page = render_page(items, errors, "\n".join(queries), target_count)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))


def run_server() -> None:
    with socketserver.ThreadingTCPServer((HOST, PORT), Handler) as httpd:
        print(f"Serving on http://{HOST}:{PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()
