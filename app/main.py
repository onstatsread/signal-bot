"""
FastAPI entry point.

Since this is a background bot, not a website, the routes here exist to
be triggered by a scheduler -- e.g. Render's Cron Jobs (or GitHub Actions,
or a free uptime-pinger) calling these URLs on a schedule:

  POST /scan            -- every hour, on each new candle close: scan + alert best-of
  POST /check-signals    -- every hour, right after /scan: check open signals for SL/TP
  POST /summary/daily    -- once a day
  POST /summary/weekly    -- once a week

No UI. No pages. Just endpoints a cron job hits.
"""
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.db.session import init_db, get_session
from app.scanner import run_scan_cycle
from app.lifecycle import check_open_signals
from app.telegram_bot import send_daily_summary, send_weekly_summary

app = FastAPI(title="Candlestick Signal Bot")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/scan")
async def scan(db: Session = Depends(get_session)):
    signal = await run_scan_cycle(db)
    return {"signal_sent": signal is not None, "symbol": signal.symbol if signal else None}
@app.get("/debug/last-scan")
def debug_last_scan(db: Session = Depends(get_session)):
    from app.db.models import ScanLog
    logs = db.query(ScanLog).order_by(ScanLog.scanned_at.desc()).limit(20).all()
    return [
        {
            "symbol": l.symbol,
            "trend": l.trend,
            "pattern_found": l.pattern_found,
            "qualified": l.qualified,
            "reason_skipped": l.reason_skipped,
            "scanned_at": l.scanned_at.isoformat() if l.scanned_at else None,
        }
        for l in logs
    ]

@app.post("/check-signals")
async def check_signals(db: Session = Depends(get_session)):
    await check_open_signals(db)
    return {"status": "checked"}


@app.post("/summary/daily")
async def daily_summary(db: Session = Depends(get_session)):
    await send_daily_summary(db)
    return {"status": "sent"}


@app.post("/summary/weekly")
async def weekly_summary(db: Session = Depends(get_session)):
    await send_weekly_summary(db)
    return {"status": "sent"}
