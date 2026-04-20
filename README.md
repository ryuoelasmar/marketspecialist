# marketspecialist

Two tools sharing one Python core:

1. **Daily Gmail digest** covering Top Market Movers (1–5d), Regional Politics
   & Regulations, and Sector Trends across **US, APAC, ASEAN, and global**
   markets. Sent each weekday morning via GitHub Actions.
2. **Dynamic chat tool** (Streamlit web app) that answers region/sector/ticker
   questions using live market + news data. Shared history so you and your
   brother see the same transcript.

## Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in keys
```

### 1. Run the digest locally

```bash
# Dry run: print to stdout, no email sent
python -m digest.main --dry-run

# Send to one address for testing
python -m digest.main --send-to you@example.com
```

### 2. Run the chat app locally

```bash
streamlit run chat/app.py
```

---

## Setup: Gmail App Password (digest delivery)

1. Turn on 2-Step Verification on your Google account.
2. Go to <https://myaccount.google.com/apppasswords>.
3. Create a password labeled `marketspecialist`. Copy the 16-char value.
4. Put it in `.env` as `GMAIL_APP_PASSWORD`.
5. Set `GMAIL_USER` (the sender address) and `GMAIL_TO` (comma-separated
   recipients — you + your brother).

## Setup: GitHub Actions (daily cron)

In your repo settings → Secrets and variables → Actions → New repository secret:

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Claude API key |
| `GMAIL_USER` | sender Gmail address |
| `GMAIL_APP_PASSWORD` | the 16-char App Password |
| `GMAIL_TO` | `you@gmail.com,brother@gmail.com` |
| `NEWSAPI_KEY` | optional, free at newsapi.org |
| `FINNHUB_KEY` | optional, free at finnhub.io |
| `FRED_KEY` | optional, free at fred.stlouisfed.org |

The workflow runs weekdays at 07:00 America/New_York. Trigger manually via
Actions tab → **Daily Market Digest** → **Run workflow** to test.

## Setup: Chat app on Streamlit Community Cloud

1. Push this repo to GitHub.
2. Go to <https://share.streamlit.io>, connect the repo, point it at `chat/app.py`.
3. Under **Secrets**, paste:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   APP_PASSCODE = "pick-a-shared-passcode"
   SUPABASE_URL = "https://xxx.supabase.co"
   SUPABASE_KEY = "eyJ..."  # anon key is fine for personal use
   NEWSAPI_KEY = ""
   FINNHUB_KEY = ""
   FRED_KEY = ""
   TAVILY_API_KEY = ""
   ```
4. Create the Supabase table (free tier, <https://supabase.com>):
   ```sql
   create table messages (
     id bigint generated always as identity primary key,
     created_at timestamptz default now(),
     session_id text not null,
     role text not null,
     user_label text,
     content jsonb not null
   );
   create index on messages (session_id, created_at);
   ```
5. Share the Streamlit URL + passcode with your brother. Done.

## How it works

```
shared/            core library
  config.py        env + regions.yaml loader
  claude_client.py Anthropic SDK wrapper with prompt caching helpers
  data/
    markets.py     yfinance: indices, ETFs, % movers, ticker details
    news.py        RSS aggregator + NewsAPI + Finnhub
    macro.py       FRED + World Bank
    regions.yaml   single source of truth for region→tickers→feeds
  prompts/
    digest_system.md  cached system prompt for digest synthesis
    chat_system.md    cached system prompt for chat agent

digest/            daily email
  main.py          fetch → synthesize → render → send
  synthesize.py    Claude call producing structured JSON
  render.py        HTML + plain-text templates
  send.py          Gmail SMTP

chat/              Streamlit app
  app.py           UI + transcript rendering
  agent.py         Claude agent loop with tool use + caching
  tools.py         tool defs + dispatch (market, news, macro, web search)
  storage.py       Supabase (or SQLite fallback) for shared history
  auth.py          shared-passcode gate

.github/workflows/
  digest.yml       weekday cron + manual dispatch
```

## Cost (estimated)

- Digest: ~1 Claude Sonnet call/day ≈ **$1–2/month**.
- Chat: 20 turns/day with prompt caching ≈ **$3–5/month**.
- Infra: **$0** (GitHub Actions free, Streamlit Community Cloud free,
  Supabase free tier).

## Tests

```bash
pytest
```

## License

MIT
