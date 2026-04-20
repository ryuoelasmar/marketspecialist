"""Config + region/sector loading."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
REGIONS_PATH = Path(__file__).resolve().parent / "data" / "regions.yaml"


def env(key: str, default: str | None = None, required: bool = False) -> str | None:
    val = os.getenv(key, default)
    if required and not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


@lru_cache(maxsize=1)
def load_regions() -> dict:
    with REGIONS_PATH.open() as f:
        return yaml.safe_load(f)


def region_codes() -> list[str]:
    return list(load_regions()["regions"].keys())


def region(code: str) -> dict:
    return load_regions()["regions"][code]


def all_tracked_symbols() -> list[tuple[str, str, str]]:
    """Every (symbol, label, region) we track across all regions."""
    out: list[tuple[str, str, str]] = []
    for code, r in load_regions()["regions"].items():
        for idx in r.get("indices", []):
            out.append((idx["symbol"], idx["name"], code))
        for etf in r.get("sector_etfs", []):
            out.append((etf["symbol"], f'{etf["sector"]} ({code})', code))
        for tkr in r.get("top_tickers", []):
            out.append((tkr, tkr, code))
    return out


def all_rss_feeds() -> list[tuple[str, str]]:
    """Every (url, region_code) RSS feed we track."""
    out: list[tuple[str, str]] = []
    for code, r in load_regions()["regions"].items():
        for url in r.get("rss", []):
            out.append((url, code))
    return out


def classification_keywords() -> dict[str, list[str]]:
    return load_regions()["classification"]
