"""Simple shared-passcode gate for the Streamlit app."""

from __future__ import annotations

import streamlit as st

from shared.config import env


def require_passcode() -> str:
    """Block the app until the user enters the shared passcode.

    Returns the user's display label once authenticated.
    """
    passcode = env("APP_PASSCODE") or st.secrets.get("APP_PASSCODE", None)
    if not passcode:
        st.warning("APP_PASSCODE not configured. Running in open-dev mode.")
        if "user_label" not in st.session_state:
            st.session_state.user_label = "dev"
        return st.session_state.user_label

    if st.session_state.get("authed"):
        return st.session_state.user_label

    st.title("Market Specialist")
    with st.form("login"):
        label = st.text_input("Your name (for chat labels)", value="")
        code = st.text_input("Passcode", type="password")
        ok = st.form_submit_button("Enter")
    if ok:
        if code == passcode and label.strip():
            st.session_state.authed = True
            st.session_state.user_label = label.strip()
            st.rerun()
        else:
            st.error("Invalid passcode or missing name.")
    st.stop()
