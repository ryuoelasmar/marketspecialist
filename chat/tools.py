"""Tool definitions + dispatcher for the chat agent.

Schemas follow Anthropic's tool-use format. The dispatcher maps tool names to
Python callables. All tool results are returned as plain strings (pretty JSON)
so Claude can consume them directly as tool_result content blocks.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, is_dataclass
from typing import Any

from shared.config import env, region_codes
from shared.data import macro, markets, news


TOOLS: list[dict] = [
    {
        "name": "get_market_snapshot",
        "description": (
            "Get a snapshot of indices, sector ETFs, and top tickers for a region "
            "with 1d/5d/YTD percent changes. Use this for any broad market/region "
            "performance question."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "enum": ["US", "APAC", "ASEAN", "GLOBAL"],
                    "description": "Region code to snapshot.",
                }
            },
            "required": ["region"],
        },
    },
    {
        "name": "get_ticker_detail",
        "description": (
            "Price, market cap, PE, 52w range, sector, and industry for a specific "
            "ticker. Yahoo Finance symbols (e.g. AAPL, 7203.T, D05.SI)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Yahoo Finance symbol."}
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "search_news",
        "description": (
            "Search recent news articles by keyword. Pulls from RSS feeds, "
            "NewsAPI, and Finnhub depending on what keys are configured. "
            "Returns titles, sources, URLs, and publish dates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "days": {"type": "integer", "default": 7, "minimum": 1, "maximum": 30},
                "region": {
                    "type": "string",
                    "enum": ["US", "APAC", "ASEAN", "GLOBAL", "ANY"],
                    "default": "ANY",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_macro_indicators",
        "description": (
            "Macro indicators for a country (GDP growth, inflation, unemployment, "
            "lending rate). For the US also returns FRED daily series."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "description": "ISO-2 country code (US, JP, CN, IN, SG, MY, TH, ID, PH, VN, etc.)",
                }
            },
            "required": ["country"],
        },
    },
    {
        "name": "web_search",
        "description": (
            "Fallback free-form web search. Only use when no other tool can "
            "answer the question. Returns title + snippet + URL."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]


def _json(obj: Any) -> str:
    def default(o):
        if is_dataclass(o):
            return asdict(o)
        if isinstance(o, dt.datetime):
            return o.isoformat()
        if isinstance(o, dt.date):
            return o.isoformat()
        return str(o)

    return json.dumps(obj, default=default, ensure_ascii=False, indent=2)


def _tool_market_snapshot(region: str) -> str:
    if region not in region_codes():
        return _json({"error": f"Unknown region '{region}'. Valid: {region_codes()}"})
    snap = markets.region_snapshot(region)
    return _json(snap)


def _tool_ticker_detail(symbol: str) -> str:
    return _json(markets.ticker_detail(symbol))


def _tool_search_news(query: str, days: int = 7, region: str = "ANY") -> str:
    results: list = []
    # Broad RSS already cached locally by fetch_all_rss; filter by query.
    try:
        rss = news.fetch_all_rss(hours=days * 24)
        q = query.lower()
        for a in rss:
            if q in a.title.lower() or q in a.summary.lower():
                if region == "ANY" or a.region == region:
                    results.append(a)
        results = results[:15]
    except Exception as e:
        results.append({"error": f"RSS fetch failed: {e}"})

    # Supplement with NewsAPI if still thin
    if len([r for r in results if not isinstance(r, dict)]) < 5:
        results.extend(news.search_news_api(query, days=days, page_size=15))

    return _json({"count": len(results), "articles": results[:20]})


def _tool_macro(country: str) -> str:
    out: dict[str, Any] = {"country": country.upper(), "world_bank": macro.country_macro(country)}
    if country.upper() == "US":
        out["fred"] = macro.fred_snapshot()
    return _json(out)


def _tool_web_search(query: str) -> str:
    key = env("TAVILY_API_KEY")
    if not key:
        return _json({"error": "TAVILY_API_KEY not configured; web_search unavailable."})
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=key)
        resp = client.search(query=query, max_results=5)
        return _json(resp)
    except Exception as e:
        return _json({"error": f"Tavily search failed: {e}"})


DISPATCH = {
    "get_market_snapshot": lambda i: _tool_market_snapshot(i["region"]),
    "get_ticker_detail": lambda i: _tool_ticker_detail(i["symbol"]),
    "search_news": lambda i: _tool_search_news(
        i["query"], i.get("days", 7), i.get("region", "ANY")
    ),
    "get_macro_indicators": lambda i: _tool_macro(i["country"]),
    "web_search": lambda i: _tool_web_search(i["query"]),
}


def run_tool(name: str, tool_input: dict) -> str:
    fn = DISPATCH.get(name)
    if not fn:
        return _json({"error": f"Unknown tool: {name}"})
    try:
        return fn(tool_input)
    except Exception as e:
        return _json({"error": f"{name} failed: {e}"})
