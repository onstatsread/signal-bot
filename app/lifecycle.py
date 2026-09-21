"""
Watches every OPEN signal and closes it (WON/LOST) once a candle CLOSES
beyond its SL or TP -- per the locked rule: close-confirmation only, no
wick-touch triggers. Should run every time fresh LTF candles come in,
right after (or as part of) the scan cycle.
"""
from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Session

from app.config import LTF_GRANULARITY, CANDLES_TO_FETCH
from app.data.deriv_client import fetch_candles, Candle
from app.db.models import Signal
from app.telegram_bot import send_signal_closed


def _check_close(signal: Signal, candles: List[Candle]):
    """Return 'WON', 'LOST', or None based on the most recently CLOSED candle."""
    if not candles:
        return None
    c = candles[-2] if len(candles) > 1 else candles[-1]  # last fully closed candle

    if signal.direction == "BUY":
        if c.close >= signal.take_profit:
            return "WON"
        if c.close <= signal.stop_loss:
            return "LOST"
    else:  # SELL
        if c.close <= signal.take_profit:
            return "WON"
        if c.close >= signal.stop_loss:
            return "LOST"
    return None


async def check_open_signals(db: Session):
    open_signals = db.query(Signal).filter(Signal.status == "OPEN").all()
    if not open_signals:
        return

    # Group by symbol so we only fetch each symbol's candles once
    symbols = {s.symbol for s in open_signals}
    candle_cache = {}
    for symbol in symbols:
        candle_cache[symbol] = await fetch_candles(symbol, LTF_GRANULARITY, CANDLES_TO_FETCH)

    for signal in open_signals:
        candles = candle_cache.get(signal.symbol, [])
        outcome = _check_close(signal, candles)
        if outcome is None:
            continue

        last_close = candles[-2].close if len(candles) > 1 else candles[-1].close
        pip_multiplier = 10000 if "frx" in signal.symbol else 1  # rough forex-pip vs synthetic-point distinction
        result_pips = (last_close - signal.entry_price) * pip_multiplier
        if signal.direction == "SELL":
            result_pips = -result_pips

        signal.status = outcome
        signal.result_price = last_close
        signal.result_pips = round(result_pips, 1)
        signal.closed_at = datetime.now(timezone.utc)
        db.add(signal)
        db.commit()

        await send_signal_closed(signal)
