"""Macro indicators: FRED (US) + World Bank (global, no key)."""

from __future__ import annotations

import datetime as dt

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import env


FRED_DEFAULT_SERIES = {
    "DGS10": "US 10Y Treasury Yield",
    "DFF": "Fed Funds Effective Rate",
    "UNRATE": "US Unemployment Rate",
    "CPIAUCSL": "US CPI (All Urban)",
    "T10Y2Y": "US 10Y-2Y Spread",
}

# World Bank indicator codes
WB_INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (%)",
    "SL.UEM.TOTL.ZS": "Unemployment rate (%)",
    "FR.INR.LEND": "Lending interest rate (%)",
}

# ISO2 country codes keyed by region/country label
COUNTRY_CODES = {
    "US": "US",
    "JP": "JP",
    "CN": "CN",
    "HK": "HK",
    "IN": "IN",
    "KR": "KR",
    "TW": "TW",
    "SG": "SG",
    "MY": "MY",
    "TH": "TH",
    "ID": "ID",
    "PH": "PH",
    "VN": "VN",
    "AU": "AU",
    "GB": "GB",
    "EU": "EUU",
}


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
def fred_latest(series_id: str) -> dict | None:
    key = env("FRED_KEY")
    if not key:
        return None
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1,
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    obs = r.json().get("observations", [])
    if not obs:
        return None
    o = obs[0]
    try:
        value = float(o["value"])
    except (TypeError, ValueError):
        return None
    return {"series": series_id, "date": o["date"], "value": value}


def fred_snapshot() -> list[dict]:
    out: list[dict] = []
    for sid, label in FRED_DEFAULT_SERIES.items():
        row = fred_latest(sid)
        if row:
            row["label"] = label
            out.append(row)
    return out


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
def worldbank_latest(country: str, indicator: str) -> dict | None:
    iso = COUNTRY_CODES.get(country.upper(), country)
    url = f"https://api.worldbank.org/v2/country/{iso}/indicator/{indicator}"
    params = {"format": "json", "per_page": 5, "date": f"{dt.date.today().year - 3}:{dt.date.today().year}"}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
    except Exception:
        return None
    data = r.json()
    if not isinstance(data, list) or len(data) < 2:
        return None
    for row in data[1]:
        if row.get("value") is not None:
            return {
                "country": iso,
                "indicator": indicator,
                "year": row.get("date"),
                "value": row["value"],
            }
    return None


def country_macro(country: str) -> list[dict]:
    out: list[dict] = []
    for code, label in WB_INDICATORS.items():
        row = worldbank_latest(country, code)
        if row:
            row["label"] = label
            out.append(row)
    return out
