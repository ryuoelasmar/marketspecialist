"""Digest entry point: fetch -> synthesize -> render -> send.

Usage:
    python -m digest.main                    # fetch, synthesize, send via Gmail
    python -m digest.main --dry-run          # print HTML to stdout, don't send
    python -m digest.main --send-to me@x.com # override recipients
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import asdict, is_dataclass
from typing import Any

from digest.render import render_html, render_text
from digest.send import send_email
from digest.synthesize import synthesize
from shared.data.macro import fred_snapshot
from shared.data.markets import all_quotes, top_movers
from shared.data.news import fetch_all_rss


def _to_dict(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, list):
        return [_to_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


def build_bundle(hours: int = 48) -> dict:
    quotes = all_quotes()
    movers_1d = top_movers(quotes, n=12, window="1d")
    movers_5d = top_movers(quotes, n=8, window="5d")
    news = fetch_all_rss(hours=hours)
    # Keep only articles Claude can act on; cap news to stay within token budget.
    news_by_cat: dict[str, list] = {"market": [], "politics": [], "sector": [], "general": []}
    for a in news:
        news_by_cat.setdefault(a.category, []).append(a)
    for cat in news_by_cat:
        news_by_cat[cat] = news_by_cat[cat][:40]
    macro = fred_snapshot()
    return {
        "date": dt.date.today().isoformat(),
        "markets": {
            "top_movers_1d": _to_dict(movers_1d),
            "top_movers_5d": _to_dict(movers_5d),
            "all_quotes": _to_dict(quotes),
        },
        "news": {
            "politics": _to_dict(news_by_cat["politics"]),
            "sector": _to_dict(news_by_cat["sector"]),
            "market": _to_dict(news_by_cat["market"]),
        },
        "macro": macro,
    }


def run(dry_run: bool = False, send_to: str | None = None, hours: int = 48) -> int:
    bundle = build_bundle(hours=hours)
    digest = synthesize(bundle)
    html = render_html(digest)
    text = render_text(digest)
    subject = f"Market Specialist — {digest.get('date', dt.date.today().isoformat())}"

    if dry_run:
        sys.stdout.write("=== SUBJECT ===\n" + subject + "\n\n")
        sys.stdout.write("=== JSON ===\n" + json.dumps(digest, indent=2) + "\n\n")
        sys.stdout.write("=== TEXT ===\n" + text + "\n\n")
        sys.stdout.write("=== HTML ===\n" + html + "\n")
        return 0

    send_email(subject=subject, html=html, text=text, to=send_to)
    print(f"Sent digest to {send_to or 'configured recipients'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="print, don't email")
    parser.add_argument("--send-to", default=None, help="override recipients (comma-separated)")
    parser.add_argument("--hours", type=int, default=48, help="news lookback window")
    args = parser.parse_args()
    return run(dry_run=args.dry_run, send_to=args.send_to, hours=args.hours)


if __name__ == "__main__":
    raise SystemExit(main())
