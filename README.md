# marketspecialist

**Stop manually researching markets every morning.** Two tools share one core:

1. **Daily email digest** — Top Market Movers (1–5d), Regional Politics &
   Regulations, Sector Trends across **US, APAC, ASEAN, and globally relevant
   macro**. Landing in your Gmail weekdays at 7am ET.
2. **Shared chat website** — ask about any region, sector, or ticker; the agent
   pulls live market + news data and synthesizes. You and your brother share one
   transcript, plus a built-in archive of every past digest.

You do **not** install Python. Everything runs in managed cloud services on
free tiers; only the Anthropic API costs money (≈ **$5/month**).

---

## 🚀 Zero-install setup (≈ 20 minutes, all web UIs)

> Do this once. After, just read your inbox and open the website.

### Step 1 — Anthropic API key  *(2 min)*

1. <https://console.anthropic.com/settings/keys> → **Create Key** → copy the
   `sk-ant-...` string somewhere safe (you'll paste it in step 6).
2. Under **Billing**, add **$10** of credit. That's months of runway.
3. **Do not paste the key into chat.** Only into GitHub and Streamlit
   settings screens (step 6).

### Step 2 — Gmail App Password  *(3 min)*

> ⚠️ If you ever pasted an App Password into chat/email/Slack, revoke it at
> <https://myaccount.google.com/apppasswords> before continuing.

1. Enable **2-Step Verification** on your Google account (if not already).
2. <https://myaccount.google.com/apppasswords> → create, label it
   `marketspecialist` → copy the 16-character string.

### Step 3 — Supabase project (free)  *(5 min)*

Supabase hosts the shared database (digest archive + chat history).

1. <https://supabase.com> → **Start your project** → sign in with GitHub.
2. **New project**, name it `marketspecialist`, pick a strong DB password, pick
   the region closest to you. Wait ~2 min for it to provision.
3. Left sidebar → **SQL Editor** → **New query** → paste the block below → **Run**:

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
   ```

4. Left sidebar → **Project Settings** → **API** → copy two values:
   - **Project URL** (e.g. `https://abcd.supabase.co`)
   - **anon public** key (starts with `eyJ...`)

### Step 4 — Fork / use this repo  *(1 min)*

Either fork this repo to your own GitHub account, or push your copy to a new
private repo. You just need a GitHub repo you own that contains this code.

### Step 5 — Deploy the website on Streamlit Cloud  *(3 min)*

1. <https://streamlit.io/cloud> → **Sign in with GitHub** → authorize.
2. **Create app** → pick your repo + the main branch → main file path:
   `chat/app.py`.
3. **Advanced settings** → **Secrets** → paste (fill in your values):

   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   APP_PASSCODE = "pick-something-you-and-your-brother-share"
   SUPABASE_URL = "https://abcd.supabase.co"
   SUPABASE_KEY = "eyJ..."  # anon public key from step 3
   ```

4. Click **Deploy**. You'll get a URL like
   `https://yourname-marketspecialist.streamlit.app`. **Bookmark it and send
   to your brother.**

### Step 6 — Wire the daily digest cron  *(3 min)*

GitHub → your repo → **Settings** → **Secrets and variables** → **Actions** →
**New repository secret**, one for each row:

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | same key from step 1 |
| `GMAIL_USER` | your Gmail address (sender) |
| `GMAIL_APP_PASSWORD` | the 16-char string from step 2 |
| `GMAIL_TO` | `you@gmail.com,brother@gmail.com` (comma-separated) |
| `SUPABASE_URL` | from step 3 |
| `SUPABASE_KEY` | anon key from step 3 |

Optional (adds more news sources; free tiers):
`NEWSAPI_KEY` (newsapi.org), `FINNHUB_KEY` (finnhub.io), `FRED_KEY` (fred.stlouisfed.org).

### Step 7 — Test it  *(1 min)*

GitHub → **Actions** tab → **Daily Market Digest** → **Run workflow** → leave
`dry_run = false` → **Run workflow**. ~60 seconds later:

- Your Gmail inbox has the digest.
- Your Streamlit site's **Today's Digest** tab shows the same content.
- **Archive** tab lists that date.

That's it. **The cron now runs itself weekdays at 7am ET forever.**

---

## 📄 What the daily email looks like

- **Top Market Movers (1–5d)** — the ~4–6 names that actually moved, with the
  *why* and links to the underlying stories.
- **Regional Politics & Regulations** — central bank statements, tariffs,
  MAS/BNM/BI/BOT/SBV actions, SEC enforcement, Fed speak.
- **Sector Trends** — which sectors are up/down and what's driving it.

Every bullet has source links. Click-through hits the original article (some
paid publications may paywall the full piece; the summary in the digest is
still useful).

## 💬 How the website works

Three tabs:

- **📰 Today's digest** — the latest issue rendered in the browser, same links
  as the email.
- **🗂️ Archive** — pick any past date from a dropdown, re-read that day's digest.
- **💬 Chat** — shared conversation. Type a question, Claude calls the right
  tools (market snapshots, news search, macro indicators, web search) and
  synthesizes. Your brother opens the site later → sees the exchange.

Both of you log in with the same `APP_PASSCODE`. Everything is stored in
Supabase so the site survives restarts and your history persists forever.

## 📡 News sources

All **English-language** RSS feeds + free APIs (no paid subscriptions
required). Covers:

- **US** — Reuters US, WSJ, Bloomberg free RSS, Fed press, SEC EDGAR filings,
  CNBC, FT headlines.
- **APAC** — Nikkei Asia, SCMP Business, Reuters Asia, Bloomberg Asia, CNA.
- **ASEAN** — Business Times SG, The Straits Times, The Edge (MY/SG),
  Jakarta Post, Bangkok Post, VnExpress Business, BusinessWorld PH.
- **Central banks / regulators** — Fed, MAS, BNM, BI, BOT, SBV, BSP.
- **Macro** — FRED (US rates, CPI, jobs), optional World Bank API.

Adding more sources is a YAML edit: `shared/data/regions.yaml`. Local-language
feeds (Nikkei Japan, Caixin, Kompas, etc.) can be added the same way — Claude
handles translation — but are not enabled by default.

## 💰 Cost

| Item | Monthly |
|---|---|
| Anthropic API (1 digest/day + ~20 chat turns) with prompt caching | ~$5 |
| GitHub Actions | $0 (free tier) |
| Streamlit Community Cloud | $0 (free tier) |
| Supabase | $0 (free tier, 500 MB DB) |
| Gmail | $0 |
| **Total** | **~$5/month** |

---

## 🛠️ Local development (only if you want to modify the code)

Skip this section unless you're editing the Python. The workflow above
requires zero local setup.

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in keys
```

```bash
# Digest dry run (prints to stdout, no email sent)
python -m digest.main --dry-run

# Send a real digest to one address
python -m digest.main --send-to you@example.com

# Run the chat app locally
streamlit run chat/app.py

# Tests
pytest
```

## 🧱 Code layout

```
shared/                      single source of truth
  config.py                  env + regions.yaml loader
  claude_client.py           Anthropic SDK wrapper with prompt caching
  digest_store.py            persist digests (Supabase + SQLite fallback)
  data/
    markets.py               yfinance: indices, ETFs, top tickers, movers
    news.py                  RSS aggregator + NewsAPI + Finnhub
    macro.py                 FRED + World Bank
    regions.yaml             region → tickers → RSS feeds (edit this to extend)
  prompts/
    digest_system.md         cached editorial prompt for digest
    chat_system.md           cached agent prompt for chat

digest/                      daily email
  main.py                    fetch → synthesize → persist → send
  synthesize.py              Claude call producing structured JSON
  render.py                  HTML + plain-text templates
  send.py                    Gmail SMTP multipart sender

chat/                        Streamlit website
  app.py                     digest + archive + chat tabs
  agent.py                   Claude agent loop with tool use + caching
  tools.py                   tool defs + dispatch
  storage.py                 chat history (Supabase + SQLite fallback)
  auth.py                    shared-passcode gate

.github/workflows/
  digest.yml                 weekday cron + manual dispatch + failure issue

tests/                       pytest suite
```

## 🔒 Security notes

- Never paste secrets into chat, issues, or commits. Secrets only go into
  **GitHub Actions Secrets** and **Streamlit Cloud Secrets** (both are web
  forms).
- `.env` is gitignored. `.env.example` ships placeholders only.
- The Supabase anon key is safe to expose in a Streamlit secret (it's
  client-facing); pair it with row-level security if you expand beyond
  personal use.
- If a secret ever leaks (pasted somewhere public): revoke and rotate at the
  original provider immediately.

## License

MIT
