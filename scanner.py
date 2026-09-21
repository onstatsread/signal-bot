"""
Orchestrates one full scan cycle:
1. Fetch HTF + LTF candles for every symbol in the watchlist
2. Run the confluence pipeline on each
3. Log every symbol's outcome (ScanLog) for auditability
4. Rank all qualifying setups, take the single best (BEST_OF_ONLY, locked)
5. Persist it as an open Signal and hand it to the Telegram sender
"""
import asyncio
from typing import Optional
from sqlalchemy.orm import Session

from app.config import WATCHLIST, HTF_GRANULARITY, LTF_GRANULARITY, CANDLES_TO_FETCH
from app.data.deriv_client import fetch_all
from app.analysis.confluence import evaluate_symbol, QualifiedSetup
from app.db.models import Signal, ScanLog
from app.telegram_bot import send_signal_opened


async def run_scan_cycle(db: Session) -> Optional[Signal]:
    htf_data = await fetch_all(WATCHLIST, HTF_GRANULARITY, CANDLES_TO_FETCH)
    ltf_data = await fetch_all(WATCHLIST, LTF_GRANULARITY, CANDLES_TO_FETCH)

    candidates = []

    for symbol in WATCHLIST:
        htf = htf_data.get(symbol)
        ltf = ltf_data.get(symbol)
        if not htf or not ltf:
            db.add(ScanLog(symbol=symbol, qualified=False, reason_skipped="no_data"))
            continue

        setup = evaluate_symbol(symbol, htf, ltf)
        if setup:
            candidates.append(setup)
            db.add(ScanLog(symbol=symbol, trend=setup.trend, pattern_found=setup.strategy, qualified=True))
        else:
            db.add(ScanLog(symbol=symbol, qualified=False, reason_skipped="no_confluence"))

    db.commit()

    if not candidates:
        return None

    # Best-of-only: rank by confluence_score, take the single winner
    best: QualifiedSetup = max(candidates, key=lambda s: s.confluence_score)

    signal = Signal(
        symbol=best.symbol,
        direction=best.direction,
        strategy=best.strategy,
        entry_price=best.entry_price,
        stop_loss=best.stop_loss,
        take_profit=best.take_profit,
        risk_reward=best.risk_reward,
        trend_aligned=True,
        level_aligned=True,
        signal_aligned=True,
        confluence_notes=best.notes,
        confluence_score=best.confluence_score,
        status="OPEN",
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)

    await send_signal_opened(signal)
    return signal
