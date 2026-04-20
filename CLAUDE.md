# Notes for Claude Code

## Structure
- `shared/` is the single source of truth. Anything the digest and chat tool
  both need lives there. Don't duplicate region/ticker lists — update
  `shared/data/regions.yaml` and both apps see the change.
- `digest/` and `chat/` are intentionally thin. They compose `shared/` modules;
  keep them easy to read.

## Prompt caching
The Anthropic SDK is wrapped in `shared/claude_client.py`. Both the digest and
chat loops put the static system prompt (and, for the chat, conversation
history up to the latest user turn) under `cache_control: {type: "ephemeral"}`.
Do not inline prompts directly via `client.messages.create` — go through the
wrapper so caching stays consistent.

## Running
```bash
# Digest
python -m digest.main --dry-run
python -m digest.main                    # live: sends email

# Chat
streamlit run chat/app.py
```

## Adding a new region/sector
Edit `shared/data/regions.yaml`. Add indices/ETFs/top tickers/RSS feeds. The
digest and chat tool will pick it up automatically — no code changes needed.

## Tests
```bash
pytest
```
Snapshot tests on digest synthesis use a canned bundle (no network, no
Anthropic calls). Market/news tests are smoke tests behind network — they're
marked and skip gracefully offline.

## Do NOT
- Hardcode tickers or feeds outside `regions.yaml`.
- Call `smtplib` or `yfinance` outside `shared/` / `digest/send.py`.
- Remove the `cache_control` breakpoints without measuring cost impact.
- Commit `.env` or `.streamlit/secrets.toml`.
