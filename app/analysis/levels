"""
Key levels: support/resistance from swing points, moving averages (8/21),
and Fibonacci retracement (50%/61.8%) -- the book's "Level" and confluence
tools. Runs on HTF candles; checked against the current LTF price.
"""
from dataclasses import dataclass
from typing import List, Optional
from app.data.deriv_client import Candle
from app.analysis.trend import find_swing_points
from app.config import MA_FAST, MA_SLOW, FIB_LEVELS, FIB_TOLERANCE, LEVEL_TOLERANCE


@dataclass
class LevelHit:
    kind: str            # "support" | "resistance" | "ma_fast" | "ma_slow" | "fib_50" | "fib_618"
    price: float
    label: str            # human-readable, goes straight into the Telegram message


def sma(candles: List[Candle], period: int) -> Optional[float]:
    if len(candles) < period:
        return None
    closes = [c.close for c in candles[-period:]]
    return sum(closes) / period


def nearest_support_resistance(candles: List[Candle], current_price: float) -> List[LevelHit]:
    """Return the nearest support (below price) and resistance (above price) from swing points."""
    swings = find_swing_points(candles)
    supports = sorted([s.price for s in swings if s.kind == "low" and s.price < current_price], reverse=True)
    resistances = sorted([s.price for s in swings if s.kind == "high" and s.price > current_price])

    hits = []
    if supports:
        hits.append(LevelHit(kind="support", price=supports[0], label=f"Support {supports[0]:.5f}"))
    if resistances:
        hits.append(LevelHit(kind="resistance", price=resistances[0], label=f"Resistance {resistances[0]:.5f}"))
    return hits


def moving_average_levels(candles: List[Candle]) -> List[LevelHit]:
    hits = []
    fast = sma(candles, MA_FAST)
    slow = sma(candles, MA_SLOW)
    if fast:
        hits.append(LevelHit(kind="ma_fast", price=fast, label=f"{MA_FAST} MA {fast:.5f}"))
    if slow:
        hits.append(LevelHit(kind="ma_slow", price=slow, label=f"{MA_SLOW} MA {slow:.5f}"))
    return hits


def fibonacci_levels(candles: List[Candle]) -> List[LevelHit]:
    """
    Fib retracement of the most recent significant swing (last swing high to
    last swing low, or vice versa -- whichever is more recent defines the leg).
    """
    swings = find_swing_points(candles)
    if len(swings) < 2:
        return []

    last_two = swings[-2:]
    p0, p1 = last_two[0].price, last_two[1].price
    diff = p1 - p0

    hits = []
    for level in FIB_LEVELS:
        price = p1 - diff * level
        label = f"Fib {int(level * 100)}% {price:.5f}"
        kind = "fib_50" if level == 0.5 else "fib_618"
        hits.append(LevelHit(kind=kind, price=price, label=label))
    return hits


def price_near_level(price: float, level: LevelHit, tolerance: Optional[float] = None) -> bool:
    tol = tolerance if tolerance is not None else (
        FIB_TOLERANCE if level.kind.startswith("fib") else LEVEL_TOLERANCE
    )
    return abs(price - level.price) / level.price <= tol


def all_levels(candles: List[Candle], current_price: float) -> List[LevelHit]:
    """Everything the book uses as a 'level': S/R, 8/21 MA, Fib 50/61.8%."""
    return (
        nearest_support_resistance(candles, current_price)
        + moving_average_levels(candles)
        + fibonacci_levels(candles)
    )
