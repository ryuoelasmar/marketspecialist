"""Smoke tests for the SQLite fallback path of shared.digest_store.

When SUPABASE_URL/SUPABASE_KEY aren't set, digests should persist to a local
SQLite file. These tests point that file at a tmp_path to stay hermetic.
"""

from __future__ import annotations

import datetime as dt

import pytest

from shared import digest_store


@pytest.fixture(autouse=True)
def _isolate_sqlite(monkeypatch, tmp_path):
    monkeypatch.setattr(digest_store, "SQLITE_PATH", tmp_path / "digests.sqlite")
    # Ensure Supabase path is not taken even if env vars leak in from the host.
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_KEY", "")


def _make_digest(date_iso: str) -> dict:
    return {
        "date": date_iso,
        "headline": "Test headline",
        "top_movers": [],
        "regional_politics": [],
        "sector_trends": [],
    }


def test_roundtrip_and_archive():
    today = dt.date.today().isoformat()
    yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()

    digest_store.save_digest(
        _make_digest(yesterday), subject="s1", html="<p>y</p>", text="y"
    )
    digest_store.save_digest(
        _make_digest(today), subject="s2", html="<p>t</p>", text="t"
    )

    latest = digest_store.latest_digest()
    assert latest is not None
    assert latest["digest_date"] == today
    assert latest["html"] == "<p>t</p>"

    picked = digest_store.digest_for_date(yesterday)
    assert picked is not None
    assert picked["subject"] == "s1"

    dates = digest_store.list_digest_dates()
    assert dates[0] == today
    assert yesterday in dates


def test_upsert_replaces_same_date():
    today = dt.date.today().isoformat()
    digest_store.save_digest(_make_digest(today), subject="first", html="a", text="a")
    digest_store.save_digest(_make_digest(today), subject="second", html="b", text="b")

    latest = digest_store.latest_digest()
    assert latest["subject"] == "second"
    assert digest_store.list_digest_dates().count(today) == 1


def test_missing_date_returns_none():
    assert digest_store.digest_for_date("1900-01-01") is None
    assert digest_store.latest_digest() is None
