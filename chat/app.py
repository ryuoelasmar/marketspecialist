"""Streamlit chat UI.

Run locally:
    streamlit run chat/app.py

Deploy:
    Push to GitHub, connect repo in Streamlit Community Cloud, set secrets:
    ANTHROPIC_API_KEY, APP_PASSCODE, SUPABASE_URL, SUPABASE_KEY, optional NEWSAPI_KEY/FINNHUB_KEY/FRED_KEY/TAVILY_API_KEY.
"""

from __future__ import annotations

import streamlit as st

from chat.agent import run_agent
from chat.auth import require_passcode
from chat.storage import history_for_agent, save_message

SESSION_ID = "main"  # single shared conversation for you + your brother

st.set_page_config(page_title="Market Specialist", page_icon="📈", layout="wide")

user_label = require_passcode()
st.caption(f"Logged in as **{user_label}** · shared session")

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
                text_parts.append(f"_[tool result]_")
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
