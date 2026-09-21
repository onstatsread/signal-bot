"""
Market structure: trend detection (HH/HL, LH/LL), ranging detection,
and choppy-market filtering -- straight from the book's "Market Structure"
chapter. Runs on the HIGHER timeframe candles (4H).
"""
from dataclasses import dataclass
from typing import List, Literal
from app.data.deriv_client import Candle
from app.config import SWING_LOOKBACK, MIN_TOUCHES_FOR_RANGE

TrendType = Literal["up", "down", "range", "choppy"]


@dataclass
class SwingPoint:
    index: int
    price: float
    kind: Literal["high", "low"]


def find_swing_points(candles: List[Candle], lookback: int = SWING_LOOKBACK) -> List[SwingPoint]:
    """A swing high/low is a bar whose high/low is the most extreme within `lookback` bars either side."""
    swings = []
    for i in range(lookback, len(candles) - lookback):
        window = candles[i - lookback: i + lookback + 1]
        c = candles[i]
        if c.high == max(x.high for x in window):
            swings.append(SwingPoint(index=i, price=c.high, kind="high"))
        elif c.low == min(x.low for x in window):
            swings.append(SwingPoint(index=i, price=c.low, kind="low"))
    return swings


def classify_trend(candles: List[Candle]) -> TrendType:
    """
    Uptrend: sequence of higher highs AND higher lows.
    Downtrend: sequence of lower highs AND lower lows.
    Range: swing highs/lows cluster around two horizontal levels (2+ touches each).
    Choppy: none of the above -- no clean structure. Caller should skip the symbol.
    """
    swings = find_swing_points(candles)
    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]

    if len(highs) < 2 or len(lows) < 2:
        return "choppy"

    recent_highs = highs[-3:]
    recent_lows = lows[-3:]

    highs_rising = all(recent_highs[i].price < recent_highs[i + 1].price for i in range(len(recent_highs) - 1))
    lows_rising = all(recent_lows[i].price < recent_lows[i + 1].price for i in range(len(recent_lows) - 1))
    highs_falling = all(recent_highs[i].price > recent_highs[i + 1].price for i in range(len(recent_highs) - 1))
    lows_falling = all(recent_lows[i].price > recent_lows[i + 1].price for i in range(len(recent_lows) - 1))

    if highs_rising and lows_rising:
        return "up"
    if highs_falling and lows_falling:
        return "down"

    # Check for a range: do highs cluster near one level, lows near another, with 2+ touches each?
    if _has_min_touches(recent_highs, MIN_TOUCHES_FOR_RANGE) and _has_min_touches(recent_lows, MIN_TOUCHES_FOR_RANGE):
        return "range"

    return "choppy"


def _has_min_touches(points: List[SwingPoint], min_touches: int, tolerance: float = 0.0015) -> bool:
    if len(points) < min_touches:
        return False
    avg = sum(p.price for p in points) / len(points)
    touches = sum(1 for p in points if abs(p.price - avg) / avg <= tolerance)
    return touches >= min_touches
