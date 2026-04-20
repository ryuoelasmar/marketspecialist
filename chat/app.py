"""Streamlit UI: today's digest + archive + shared chat.

Run locally:
    streamlit run chat/app.py

Deploy:
    Push to GitHub, connect repo in Streamlit Community Cloud, set secrets:
    ANTHROPIC_API_KEY, APP_PASSCODE, SUPABASE_URL, SUPABASE_KEY,
    optional NEWSAPI_KEY/FINNHUB_KEY/FRED_KEY/TAVILY_API_KEY.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit Cloud runs `chat/app.py` with sys.path[0] == the chat/ directory,
# which shadows the repo root and breaks `from chat.*` / `from shared.*` imports.
# Ensure the repo root is importable regardless of how the app is launched.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

from chat.agent import run_agent
from chat.auth import require_passcode
from chat.storage import history_for_agent, save_message
from shared.digest_store import digest_for_date, latest_digest, list_digest_dates

SESSION_ID = "main"  # single shared conversation for you + your brother

st.set_page_config(page_title="Market Specialist", page_icon="📈", layout="wide")

user_label = require_passcode()
st.caption(f"Logged in as **{user_label}** · shared session")

digest_tab, archive_tab, chat_tab = st.tabs(
    ["📰 Today's digest", "🗂️ Archive", "💬 Chat"]
)


def _render_digest_payload(payload: dict | None, *, label: str) -> None:
    if not payload:
        st.info(
            "No digest stored yet. The first one will appear after the scheduled run "
            "(weekdays, 07:00 America/New_York), or trigger **Daily Market Digest** "
            "manually from the GitHub Actions tab."
        )
        return
    st.markdown(f"### {payload.get('subject', label)}")
    html = payload.get("html") or ""
    if html:
        st.components.v1.html(html, height=1400, scrolling=True)
    else:
        st.markdown("```\n" + (payload.get("text") or "") + "\n```")


with digest_tab:
    _render_digest_payload(latest_digest(), label="Latest digest")


with archive_tab:
    dates = list_digest_dates(limit=365)
    if not dates:
        st.info("Archive is empty until the first digest runs.")
    else:
        pick = st.selectbox("Select a past digest", dates, index=0)
        if pick:
            _render_digest_payload(digest_for_date(pick), label=f"Digest · {pick}")


with chat_tab:
    # Render full transcript from storage (so both users see each other's turns).
    for row in history_for_agent(SESSION_ID):
        role = row["role"]
        content = row["content"]
        if role == "user":
            text_parts = []
            for block in content if isinstance(content, list) else [{"type": "text", "text": content}]:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    text_parts.append("_[tool result]_")
            if text_parts:
                with st.chat_message("user"):
                    st.markdown("\n".join(text_parts))
        elif role == "assistant":
            text_parts = []
            for block in content if isinstance(content, list) else [{"type": "text", "text": content}]:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    text_parts.append(f"_🔧 called `{block.get('name')}`_")
            if text_parts:
                with st.chat_message("assistant"):
                    st.markdown("\n\n".join(text_parts))

    prompt = st.chat_input("Ask about a region, sector, or ticker…")
    if prompt:
        labeled_prompt = f"[{user_label}] {prompt}"
        save_message(SESSION_ID, "user", labeled_prompt, user_label=user_label)
        with st.chat_message("user"):
            st.markdown(labeled_prompt)

        history = history_for_agent(SESSION_ID)
        starting_len = len(history)
        assistant_box = st.chat_message("assistant")
        status = assistant_box.empty()
        answer_box = assistant_box.empty()

        for event in run_agent(history):
            if event["type"] == "tool_use":
                status.markdown(f"🔧 calling `{event['name']}` …")
            elif event["type"] == "tool_result":
                status.markdown(f"✅ `{event['name']}` returned {len(event['output'])} chars")
            elif event["type"] == "assistant_text":
                answer_box.markdown(event["text"])
            elif event["type"] == "final":
                status.empty()
                if event["text"]:
                    answer_box.markdown(event["text"])

        # Persist only the new messages run_agent appended beyond the starting snapshot.
        for m in history[starting_len:]:
            save_message(SESSION_ID, m["role"], m["content"])
