"""
Sends the exact message formats agreed on: open-signal (with strategy +
confluence breakdown), close-signal (WON/LOST), and daily/weekly summaries.
"""
import httpx
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from app.db.models import Signal

STRATEGY_LABELS = {
    "pin_bar": "Pin Bar",
    "engulfing": "Engulfing Bar",
    "inside_bar": "Inside Bar",
    "false_breakout": "Inside Bar False Breakout",
}


async def _send(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[telegram_bot] not configured, message not sent:\n", text)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
        })


async def send_signal_opened(signal: Signal):
    emoji = "🟢" if signal.direction == "BUY" else "🔴"
    strategy_label = STRATEGY_LABELS.get(signal.strategy, signal.strategy)

    text = (
        f"⭐ <b>BEST SETUP — {signal.direction}</b> {emoji}\n"
        f"{signal.symbol}\n\n"
        f"Strategy: {strategy_label}\n"
        f"Confluence: Trend ✅ | Level ✅ | Signal ✅\n"
        f"Level: {signal.confluence_notes}\n\n"
        f"Entry: {signal.entry_price:.5f}\n"
        f"Stop Loss: {signal.stop_loss:.5f}\n"
        f"Take Profit: {signal.take_profit:.5f}\n"
        f"R:R — 1 : {signal.risk_reward}\n\n"
        f"Opened: {signal.opened_at.strftime('%d %b, %H:%M UTC')}"
    )
    await _send(text)


async def send_signal_closed(signal: Signal):
    won = signal.status == "WON"
    emoji = "✅" if won else "❌"
    label = "TP HIT" if won else "SL HIT"
    duration = signal.closed_at - signal.opened_at
    hours, remainder = divmod(int(duration.total_seconds()), 3600)
    minutes = remainder // 60

    text = (
        f"{emoji} <b>{label} — {signal.symbol} {signal.direction}</b>\n"
        f"Entry {signal.entry_price:.5f} → Closed {signal.result_price:.5f}\n"
        f"{'+' if signal.result_pips >= 0 else ''}{signal.result_pips} pips\n\n"
        f"Duration: {hours}h {minutes}m"
    )
    await _send(text)


async def send_daily_summary(db: Session):
    since = datetime.now(timezone.utc) - timedelta(days=1)
    closed = db.query(Signal).filter(Signal.closed_at >= since, Signal.status != "OPEN").all()
    await _send(_build_summary_text(closed, "DAILY SUMMARY"))


async def send_weekly_summary(db: Session):
    since = datetime.now(timezone.utc) - timedelta(days=7)
    closed = db.query(Signal).filter(Signal.closed_at >= since, Signal.status != "OPEN").all()
    text = _build_summary_text(closed, "WEEKLY SUMMARY", by_strategy=True)
    await _send(text)


def _build_summary_text(closed, title: str, by_strategy: bool = False) -> str:
    total = len(closed)
    wins = [s for s in closed if s.status == "WON"]
    losses = [s for s in closed if s.status == "LOST"]
    win_rate = (len(wins) / total * 100) if total else 0.0

    # Net R: winners count as +risk_reward R, losers as -1R
    net_r = sum(s.risk_reward for s in wins) - len(losses)

    date_label = datetime.now(timezone.utc).strftime("%d %b %Y")
    lines = [
        f"📊 <b>{title} — {date_label}</b>\n",
        f"Signals sent: {total}",
        f"✅ Wins: {len(wins)}",
        f"❌ Losses: {len(losses)}",
        f"Win rate: {win_rate:.1f}%",
        f"Net R: {'+' if net_r >= 0 else ''}{net_r:.1f}R",
    ]

    if by_strategy and closed:
        lines.append("\nBy strategy:")
        seen = {}
        for s in closed:
            seen.setdefault(s.strategy, {"W": 0, "L": 0})
            seen[s.strategy]["W" if s.status == "WON" else "L"] += 1
        for strat, rec in seen.items():
            label = STRATEGY_LABELS.get(strat, strat)
            lines.append(f"{label}: {rec['W']}W-{rec['L']}L")

    return "\n".join(lines)
