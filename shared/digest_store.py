"""Persist digest runs so the website can render today's issue + an archive.

- If SUPABASE_URL + SUPABASE_KEY are set, use Supabase Postgres.
- Otherwise fall back to a local SQLite file (dev only; not shared across users).

Expected Supabase table:
    create table digests (
      id bigint generated always as identity primary key,
      created_at timestamptz default now(),
      digest_date date not null unique,
      subject text not null,
      data jsonb not null,
      html text not null,
      text text not null
    );
    create index on digests (digest_date desc);
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path

from shared.config import env


SQLITE_PATH = Path.home() / ".marketspecialist_digests.sqlite"


def _supabase():
    url = env("SUPABASE_URL")
    key = env("SUPABASE_KEY")
    if not url or not key:
        return None
    from supabase import create_client

    return create_client(url, key)


def _init_sqlite() -> sqlite3.Connection:
    conn = sqlite3.connect(SQLITE_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS digests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            digest_date TEXT NOT NULL UNIQUE,
            subject TEXT NOT NULL,
            data TEXT NOT NULL,
            html TEXT NOT NULL,
            text TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_digest_date ON digests (digest_date DESC)")
    conn.commit()
    return conn


def save_digest(digest: dict, *, subject: str, html: str, text: str) -> None:
    """Insert (or replace) today's digest row. Safe to call multiple times per day."""
    digest_date = digest.get("date") or dt.date.today().isoformat()
    row = {
        "digest_date": digest_date,
        "subject": subject,
        "data": digest,
        "html": html,
        "text": text,
    }
    sb = _supabase()
    if sb is not None:
        sb.table("digests").upsert(row, on_conflict="digest_date").execute()
        return
    conn = _init_sqlite()
    conn.execute(
        "INSERT OR REPLACE INTO digests (created_at, digest_date, subject, data, html, text) "
        "VALUES (?,?,?,?,?,?)",
        (
            dt.datetime.utcnow().isoformat(),
            digest_date,
            subject,
            json.dumps(digest),
            html,
            text,
        ),
    )
    conn.commit()
    conn.close()


def latest_digest() -> dict | None:
    sb = _supabase()
    if sb is not None:
        resp = (
            sb.table("digests")
            .select("*")
            .order("digest_date", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None
    conn = _init_sqlite()
    cur = conn.execute(
        "SELECT digest_date, subject, data, html, text, created_at FROM digests "
        "ORDER BY digest_date DESC LIMIT 1"
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "digest_date": row[0],
        "subject": row[1],
        "data": json.loads(row[2]),
        "html": row[3],
        "text": row[4],
        "created_at": row[5],
    }


def digest_for_date(date_iso: str) -> dict | None:
    sb = _supabase()
    if sb is not None:
        resp = sb.table("digests").select("*").eq("digest_date", date_iso).limit(1).execute()
        rows = resp.data or []
        return rows[0] if rows else None
    conn = _init_sqlite()
    cur = conn.execute(
        "SELECT digest_date, subject, data, html, text, created_at FROM digests "
        "WHERE digest_date = ? LIMIT 1",
        (date_iso,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "digest_date": row[0],
        "subject": row[1],
        "data": json.loads(row[2]),
        "html": row[3],
        "text": row[4],
        "created_at": row[5],
    }


def list_digest_dates(limit: int = 180) -> list[str]:
    sb = _supabase()
    if sb is not None:
        resp = (
            sb.table("digests")
            .select("digest_date")
            .order("digest_date", desc=True)
            .limit(limit)
            .execute()
        )
        return [r["digest_date"] for r in (resp.data or [])]
    conn = _init_sqlite()
    cur = conn.execute(
        "SELECT digest_date FROM digests ORDER BY digest_date DESC LIMIT ?", (limit,)
    )
    out = [r[0] for r in cur.fetchall()]
    conn.close()
    return out
