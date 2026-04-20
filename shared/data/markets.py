"""Market data via yfinance. All free, unofficial Yahoo Finance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import all_tracked_symbols, region


@dataclass
class Quote:
    symbol: str
    label: str
    region: str
    last: float | None
    change_1d_pct: float | None
    change_5d_pct: float | None
    change_ytd_pct: float | None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _download(symbols: list[str], period: str = "1mo") -> dict:
    if not symbols:
        return {}
    data = yf.download(
        tickers=" ".join(symbols),
        period=period,
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        progress=False,
        threads=True,
    )
    return data


def _pct(closes, offset: int) -> float | None:
    """Percent change from `offset` trading days ago to the latest close."""
    if closes is None or len(closes) <= offset:
        return None
    latest = closes.iloc[-1]
    prior = closes.iloc[-1 - offset]
    if prior == 0 or prior is None:
        return None
    return float((latest - prior) / prior * 100)


def fetch_quotes(symbols: list[tuple[str, str, str]]) -> list[Quote]:
    """Fetch 1d/5d/YTD % changes for (symbol, label, region) triples."""
    if not symbols:
        return []
    tickers = [s[0] for s in symbols]
    data = _download(tickers, period="1y")
    year_start = datetime(datetime.utcnow().year, 1, 1)

    out: list[Quote] = []
    for symbol, label, region_code in symbols:
        try:
            df = data[symbol] if len(tickers) > 1 else data
            closes = df["Close"].dropna()
            if closes.empty:
                out.append(Quote(symbol, label, region_code, None, None, None, None))
                continue
            last = float(closes.iloc[-1])
            ytd_pct = None
            ytd_slice = closes[closes.index >= year_start]
            if not ytd_slice.empty and ytd_slice.iloc[0] != 0:
                ytd_pct = float((ytd_slice.iloc[-1] - ytd_slice.iloc[0]) / ytd_slice.iloc[0] * 100)
            out.append(
                Quote(
                    symbol=symbol,
                    label=label,
                    region=region_code,
                    last=last,
                    change_1d_pct=_pct(closes, 1),
                    change_5d_pct=_pct(closes, 5),
                    change_ytd_pct=ytd_pct,
                )
            )
        except Exception:
            out.append(Quote(symbol, label, region_code, None, None, None, None))
    return out


def all_quotes() -> list[Quote]:
    return fetch_quotes(all_tracked_symbols())


def top_movers(quotes: list[Quote], n: int = 6, window: str = "1d") -> list[Quote]:
    """Return the n largest absolute movers over `window` (1d, 5d, ytd)."""
    key_map = {
        "1d": lambda q: q.change_1d_pct,
        "5d": lambda q: q.change_5d_pct,
        "ytd": lambda q: q.change_ytd_pct,
    }
    key = key_map[window]
    with_data = [q for q in quotes if key(q) is not None]
    with_data.sort(key=lambda q: abs(key(q)), reverse=True)
    return with_data[:n]


def region_snapshot(region_code: str) -> dict:
    """Compact snapshot for a single region: indices + sector ETFs + top tickers."""
    r = region(region_code)
    triples: list[tuple[str, str, str]] = []
    for idx in r.get("indices", []):
        triples.append((idx["symbol"], idx["name"], region_code))
    for etf in r.get("sector_etfs", []):
        triples.append((etf["symbol"], f'{etf["sector"]} ({region_code})', region_code))
    for tkr in r.get("top_tickers", []):
        triples.append((tkr, tkr, region_code))
    quotes = fetch_quotes(triples)
    return {
        "region": region_code,
        "as_of": datetime.utcnow().isoformat() + "Z",
        "indices": [q for q in quotes if q.label in {idx["name"] for idx in r.get("indices", [])}],
        "sectors": [q for q in quotes if any(q.label.endswith(f"({region_code})") and etf["sector"] in q.label for etf in r.get("sector_etfs", []))],
        "tickers": [q for q in quotes if q.symbol in r.get("top_tickers", [])],
    }


def ticker_detail(symbol: str) -> dict:
    """Price + fundamentals for a single symbol."""
    t = yf.Ticker(symbol)
    info = {}
    try:
        info = t.info or {}
    except Exception:
        info = {}
    hist = t.history(period="1y")
    last = float(hist["Close"].iloc[-1]) if not hist.empty else None
    high_52w = float(hist["High"].max()) if not hist.empty else None
    low_52w = float(hist["Low"].min()) if not hist.empty else None
    return {
        "symbol": symbol,
        "name": info.get("longName") or info.get("shortName") or symbol,
        "price": last,
        "currency": info.get("currency"),
        "market_cap": info.get("marketCap"),
        "pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "dividend_yield": info.get("dividendYield"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "high_52w": high_52w,
        "low_52w": low_52w,
    }
