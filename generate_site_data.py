from __future__ import annotations

import json
from pathlib import Path

from app import DEFAULT_QUERIES, build_margin_board


def sample_items() -> list[dict[str, float | str]]:
    return [
        {"query": "vintage camera", "current_price": 45.0, "sold_avg_price": 99.0, "margin_percent": 120.0, "confidence": 62.0, "source_url": "https://www.ebay.com/sch/i.html?_nkw=vintage+camera"},
        {"query": "guitar pedal", "current_price": 38.5, "sold_avg_price": 70.0, "margin_percent": 81.82, "confidence": 58.0, "source_url": "https://www.ebay.com/sch/i.html?_nkw=guitar+pedal"},
        {"query": "mechanical keyboard", "current_price": 28.0, "sold_avg_price": 49.0, "margin_percent": 75.0, "confidence": 55.0, "source_url": "https://www.ebay.com/sch/i.html?_nkw=mechanical+keyboard"},
    ]


def main() -> None:
    items, errors = build_margin_board(DEFAULT_QUERIES, target_count=40)
    item_payload = [
        {
            "query": i.query,
            "current_price": i.current_price,
            "sold_avg_price": i.sold_avg_price,
            "margin_percent": i.margin_percent,
            "confidence": i.confidence,
            "source_url": i.source_url,
        }
        for i in items
    ]

    if not item_payload:
        item_payload = sample_items()

    payload = {
        "items": item_payload,
        "errors": [] if item_payload else errors,
    }

    out = Path("site/data.json")
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out} with {len(item_payload)} items")


if __name__ == "__main__":
    main()
