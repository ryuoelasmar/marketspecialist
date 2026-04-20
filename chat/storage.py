"""Shared chat history storage.

- If SUPABASE_URL + SUPABASE_KEY are set, use Supabase Postgres.
- Otherwise fall back to a local SQLite file (dev only; not shared across users).

Expected Supabase table:
    create table messages (
      id bigint generated always as identity primary key,
      created_at timestamptz default now(),
      session_id text not null,
      role text not null,           -- 'user' | 'assistant' | 'tool'
      user_label text,              -- who typed it (for user turns)
      content jsonb not null        -- full content array per Anthropic schema
    );
    create index on messages (session_id, created_at);
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any

from shared.config import env


SQLITE_PATH = Path.home() / ".marketspecialist_chat.sqlite"


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
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            user_label TEXT,
            content TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON messages (session_id, created_at)")
    conn.commit()
    return conn


def save_message(session_id: str, role: str, content: Any, user_label: str | None = None) -> None:
    sb = _supabase()
    row = {
        "session_id": session_id,
        "role": role,
        "user_label": user_label,
        "content": content if not isinstance(content, str) else [{"type": "text", "text": content}],
    }
    if sb is not None:
        sb.table("messages").insert(row).execute()
        return
    conn = _init_sqlite()
    conn.execute(
        "INSERT INTO messages (created_at, session_id, role, user_label, content) VALUES (?,?,?,?,?)",
        (
            dt.datetime.utcnow().isoformat(),
            session_id,
            role,
            user_label,
            json.dumps(row["content"]),
        ),
    )
    conn.commit()
    conn.close()


def load_messages(session_id: str, limit: int = 200) -> list[dict]:
    sb = _supabase()
    if sb is not None:
        resp = (
            sb.table("messages")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at")
            .limit(limit)
            .execute()
        )
        return resp.data or []
    conn = _init_sqlite()
    cur = conn.execute(
        "SELECT created_at, session_id, role, user_label, content FROM messages "
        "WHERE session_id = ? ORDER BY created_at LIMIT ?",
        (session_id, limit),
    )
    rows = []
    for created_at, sid, role, user_label, content_json in cur.fetchall():
        rows.append(
            {
                "created_at": created_at,
                "session_id": sid,
                "role": role,
                "user_label": user_label,
                "content": json.loads(content_json),
            }
        )
    conn.close()
    return rows


def history_for_agent(session_id: str) -> list[dict]:
    """Return messages in the shape the Claude API expects (role + content)."""
    out = []
    for row in load_messages(session_id):
        out.append({"role": row["role"], "content": row["content"]})
    return out
