"""
Database models.

signals        -- every alerted setup, tracked from OPEN through WON/LOST
scan_log       -- every symbol we evaluated each cycle, even if it didn't qualify
                  (lets you audit "why didn't X fire" later)
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text
)
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)          # "BUY" or "SELL"
    strategy = Column(String, nullable=False)            # "pin_bar" | "engulfing" | "inside_bar" | "false_breakout"

    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    risk_reward = Column(Float, nullable=False)

    trend_aligned = Column(Boolean, default=False)
    level_aligned = Column(Boolean, default=False)
    signal_aligned = Column(Boolean, default=False)
    confluence_notes = Column(Text, default="")           # human-readable: "Support 0.8420 + 21MA"
    confluence_score = Column(Float, default=0.0)          # used for best-of ranking

    status = Column(String, default="OPEN")                # OPEN | WON | LOST
    result_price = Column(Float, nullable=True)
    result_pips = Column(Float, nullable=True)

    opened_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime, nullable=True)


class ScanLog(Base):
    """One row per symbol per scan cycle -- lightweight audit trail."""
    __tablename__ = "scan_log"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    trend = Column(String, nullable=True)                  # "up" | "down" | "range" | "choppy"
    pattern_found = Column(String, nullable=True)
    qualified = Column(Boolean, default=False)
    reason_skipped = Column(String, nullable=True)
    scanned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
