# Candlestick Signal Bot

Telegram signal generator built from *The Candlestick Trading Bible* (Bella Ealie).
No website — Telegram is the interface. This is a background service.

## How it maps to the plan

| Plan piece | File |
|---|---|
| Data Pipeline | `app/data/deriv_client.py` |
| Trend + Level detection | `app/analysis/trend.py`, `app/analysis/levels.py` |
| Pattern detection (4 strategies) | `app/analysis/patterns.py` |
| Confluence Scorer (strict Trend+Level+Signal) | `app/analysis/confluence.py` |
| Scanner + best-of ranking | `app/scanner.py` |
| Signal Lifecycle Manager (close-confirmation SL/TP) | `app/lifecycle.py` |
| Telegram Delivery + summaries | `app/telegram_bot.py` |
| FastAPI entry / cron-triggered routes | `app/main.py` |

## Setup

1. Copy `.env.example` to `.env` and fill in:
   - `TELEGRAM_BOT_TOKEN` — from @BotFather
   - `TELEGRAM_CHAT_ID` — your chat/channel id (message @userinfobot or use `/getUpdates` after messaging your bot once)
   - `DERIV_API_TOKEN` — optional for signal-only use; get one at app.deriv.com > API token (read-only scope is enough)

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run locally to test:
   ```
   uvicorn app.main:app --reload
   ```

4. Trigger a scan manually to test end-to-end:
   ```
   curl -X POST http://localhost:8000/scan
   ```

## Deploying on Render

1. Push this to a new GitHub repo.
2. Create a new Web Service on Render, connect the repo.
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Attach a free Postgres instance — Render sets `DATABASE_URL` automatically.
4. Set the other env vars (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `DERIV_API_TOKEN`) in the Render dashboard.
5. Add **Render Cron Jobs** (or an external free scheduler like cron-job.org hitting your Render URL) to call:
   - `POST /scan` — every hour (matches the 1H trading timeframe)
   - `POST /check-signals` — every hour, right after `/scan`
   - `POST /summary/daily` — once a day
   - `POST /summary/weekly` — once a week

## Notes / what to tune once it's running

- `WATCHLIST` in `app/config.py` — add/remove forex pairs or synthetic indices freely.
- `MIN_RR`, `FIB_TOLERANCE`, `LEVEL_TOLERANCE` in `app/config.py` — loosen/tighten if signals are too rare or too noisy.
- The confluence scorer currently weights "number of matched levels" over raw R:R for best-of ranking — adjust the formula in `confluence.py` (`evaluate_symbol`) once you have real data on what actually wins.
- `detect_inside_bar` treats every inside-bar breakout as tradeable in the trend's direction — the book also says to only trade ones at genuine key levels, which the confluence layer already enforces, so this is intentional, not a gap.
