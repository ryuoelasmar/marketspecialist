"""News aggregation: RSS (primary) + NewsAPI + Finnhub (supplements)."""

from __future__ import annotations

import datetime as dt
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Iterable

import feedparser
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import all_rss_feeds, classification_keywords, env


@dataclass
class Article:
    title: str
    url: str
    source: str
    published: dt.datetime | None
    summary: str
    region: str
    category: str  # "market", "politics", "sector", "general"

    @property
    def fingerprint(self) -> str:
        return hashlib.md5((self.url or self.title).encode()).hexdigest()


def _parse_date(entry) -> dt.datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            try:
                return dt.datetime(*val[:6])
            except Exception:
                pass
    return None


def _classify(text: str) -> str:
    """Word-boundary keyword matching. Acronyms (all-caps keywords) are matched
    case-sensitively against the original text so 'SEC' doesn't hit 'sector'."""
    import re

    kws = classification_keywords()
    t_lower = text.lower()

    def _hit(keywords: list[str]) -> bool:
        for kw in keywords:
            # Acronym: keep case, look for the uppercase token as a whole word.
            if kw.isupper() and len(kw) <= 5:
                if re.search(rf"\b{re.escape(kw)}\b", text):
                    return True
            else:
                if re.search(rf"\b{re.escape(kw.lower())}\b", t_lower):
                    return True
        return False

    if _hit(kws.get("politics_and_regulation", [])):
        return "politics"
    if _hit(kws.get("sector_trends", [])):
        return "sector"
    if _hit(["market", "index", "rally", "sell-off", "shares", "stocks"]):
        return "market"
    return "general"


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
def _fetch_rss(url: str, region_code: str) -> list[Article]:
    feed = feedparser.parse(url, request_headers={"User-Agent": "marketspecialist/1.0"})
    source = feed.feed.get("title", url)
    articles: list[Article] = []
    for entry in feed.entries:
        title = entry.get("title", "").strip()
        if not title:
            continue
        summary = entry.get("summary", "") or entry.get("description", "")
        articles.append(
            Article(
                title=title,
                url=entry.get("link", ""),
                source=source,
                published=_parse_date(entry),
                summary=_strip_html(summary)[:500],
                region=region_code,
                category=_classify(f"{title} {summary}"),
            )
        )
    return articles


def _strip_html(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", text or "").strip()


def fetch_all_rss(hours: int = 48, max_workers: int = 8) -> list[Article]:
    """Parallel-fetch all configured RSS feeds, keep last `hours`."""
    cutoff = dt.datetime.utcnow() - dt.timedelta(hours=hours)
    feeds = all_rss_feeds()
    out: list[Article] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_fetch_rss, url, code): (url, code) for url, code in feeds}
        for fut in as_completed(futures):
            try:
                articles = fut.result(timeout=20)
            except Exception:
                continue
            for a in articles:
                if a.published is None or a.published >= cutoff:
                    out.append(a)
    return dedupe(out)


def dedupe(articles: Iterable[Article]) -> list[Article]:
    seen: set[str] = set()
    out: list[Article] = []
    for a in articles:
        key = a.fingerprint
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


def search_news_api(query: str, days: int = 7, page_size: int = 20) -> list[Article]:
    """NewsAPI.org search (free tier: 100 req/day, dev use only)."""
    key = env("NEWSAPI_KEY")
    if not key:
        return []
    url = "https://newsapi.org/v2/everything"
    frm = (dt.datetime.utcnow() - dt.timedelta(days=days)).date().isoformat()
    params = {
        "q": query,
        "from": frm,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": page_size,
        "apiKey": key,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
    except Exception:
        return []
    data = r.json()
    out: list[Article] = []
    for item in data.get("articles", []):
        published = None
        if item.get("publishedAt"):
            try:
                published = dt.datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00"))
            except Exception:
                pass
        out.append(
            Article(
                title=item.get("title", ""),
                url=item.get("url", ""),
                source=(item.get("source") or {}).get("name", "NewsAPI"),
                published=published,
                summary=(item.get("description") or "")[:500],
                region="GLOBAL",
                category=_classify(f"{item.get('title','')} {item.get('description','')}"),
            )
        )
    return out


def finnhub_company_news(symbol: str, days: int = 7) -> list[Article]:
    """Finnhub company-news endpoint (free: 60 req/min)."""
    key = env("FINNHUB_KEY")
    if not key:
        return []
    today = dt.date.today()
    frm = today - dt.timedelta(days=days)
    url = "https://finnhub.io/api/v1/company-news"
    params = {"symbol": symbol, "from": frm.isoformat(), "to": today.isoformat(), "token": key}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
    except Exception:
        return []
    out: list[Article] = []
    for item in r.json() or []:
        published = None
        if item.get("datetime"):
            try:
                published = dt.datetime.utcfromtimestamp(int(item["datetime"]))
            except Exception:
                pass
        out.append(
            Article(
                title=item.get("headline", ""),
                url=item.get("url", ""),
                source=item.get("source", "Finnhub"),
                published=published,
                summary=(item.get("summary") or "")[:500],
                region="GLOBAL",
                category="sector",
            )
        )
    return out
