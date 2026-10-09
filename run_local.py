"""
Runs the signal bot directly on-device (Termux), no web server needed.

Loops forever: scan -> check open signals -> sleep -> repeat.
Also fires daily/weekly summaries at the right times.
Uses local SQLite (signal_bot.db, right here in this folder) instead
of Postgres -- simpler, no separate database service needed on-device.

Usage:
    python run_local.py
Stop with CTRL+C. For it to keep running after you close Termux,
see the README section on termux-wake-lock + running in background.
"""
import asyncio
from datetime import datetime, timezone

from app.db.session import init_db, SessionLocal
from app.scanner import run_scan_cycle
from app.lifecycle import check_open_signals
from app.telegram_bot import send_daily_summary, send_weekly_summary
from app.config import LTF_GRANULARITY

# How often to run a scan cycle -- matches the candle timeframe.
# LTF_GRANULARITY is in seconds (e.g. 300 = 5min, 900 = 15min).
SCAN_INTERVAL_SECONDS = LTF_GRANULARITY

# Track the last day/week a summary was sent, so we only send once.
_last_daily_summary_date = None
_last_weekly_summary_week = None


async def maybe_send_summaries(db):
    global _last_daily_summary_date, _last_weekly_summary_week
    now = datetime.now(timezone.utc)

    # Daily summary once per day, around 22:00 UTC
    if now.hour == 22 and _last_daily_summary_date != now.date():
        await send_daily_summary(db)
        _last_daily_summary_date = now.date()
        print(f"[run_local] sent daily summary at {now.isoformat()}")

    # Weekly summary once per week, Sunday around 22:00 UTC
    iso_year, iso_week, iso_weekday = now.isocalendar()
    if iso_weekday == 7 and now.hour == 22 and _last_weekly_summary_week != (iso_year, iso_week):
        await send_weekly_summary(db)
        _last_weekly_summary_week = (iso_year, iso_week)
        print(f"[run_local] sent weekly summary at {now.isoformat()}")


async def run_forever():
    init_db()
    print(f"[run_local] started. Scanning every {SCAN_INTERVAL_SECONDS} seconds.")
    print("[run_local] press CTRL+C to stop.")

    while True:
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            print(f"\n[run_local] --- cycle at {now.isoformat()} ---")

            signal = await run_scan_cycle(db)
            if signal:
                print(f"[run_local] SIGNAL SENT: {signal.symbol} {signal.direction}")
            else:
                print("[run_local] no qualifying setup this cycle.")

            await check_open_signals(db)
            await maybe_send_summaries(db)

        except Exception as e:
            print(f"[run_local] ERROR during cycle: {type(e).__name__}: {e}")
        finally:
            db.close()

        await asyncio.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        asyncio.run(run_forever())
    except KeyboardInterrupt:
        print("\n[run_local] stopped.")
