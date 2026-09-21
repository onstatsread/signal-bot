"""
The 4 strategies (v1 scope, locked decision): Pin Bar, Engulfing Bar,
Inside Bar (continuation), Inside Bar False Breakout.

Each detector is a pure function: candles in, PatternMatch or None out.
No trend/level awareness here -- that's layered on in confluence.py.
Stop-loss rules follow the book exactly (see extraction doc section 4).
"""
from dataclasses import dataclass
from typing import List, Optional, Literal
from app.data.deriv_client import Candle

Direction = Literal["BUY", "SELL"]


@dataclass
class PatternMatch:
    strategy: str          # "pin_bar" | "engulfing" | "inside_bar" | "false_breakout"
    direction: Direction
    signal_candle: Candle
    stop_loss: float        # computed per the book's rule for this pattern
    entry_price: float      # aggressive entry = signal candle close


def detect_pin_bar(candles: List[Candle]) -> Optional[PatternMatch]:
    """
    Hammer (bullish) / Shooting Star (bearish): small body, tail >= 2x body,
    on the correct side. Checked on the most recently CLOSED candle.
    """
    if len(candles) < 2:
        return None
    c = candles[-2]  # last fully closed candle (candles[-1] may still be forming)
    if c.body == 0:
        return None

    if c.lower_wick >= 2 * c.body and c.upper_wick < c.body:
        return PatternMatch(
            strategy="pin_bar",
            direction="BUY",
            signal_candle=c,
            stop_loss=c.low,
            entry_price=c.close,
        )
    if c.upper_wick >= 2 * c.body and c.lower_wick < c.body:
        return PatternMatch(
            strategy="pin_bar",
            direction="SELL",
            signal_candle=c,
            stop_loss=c.high,
            entry_price=c.close,
        )
    return None


def detect_engulfing(candles: List[Candle]) -> Optional[PatternMatch]:
    """Second body fully engulfs the first, opposite color."""
    if len(candles) < 3:
        return None
    prev, cur = candles[-3], candles[-2]

    bullish_engulf = (
        prev.is_bearish and cur.is_bullish
        and cur.close >= prev.open and cur.open <= prev.close
    )
    bearish_engulf = (
        prev.is_bullish and cur.is_bearish
        and cur.open >= prev.close and cur.close <= prev.open
    )

    if bullish_engulf:
        return PatternMatch(
            strategy="engulfing", direction="BUY", signal_candle=cur,
            stop_loss=min(cur.low, prev.low), entry_price=cur.close,
        )
    if bearish_engulf:
        return PatternMatch(
            strategy="engulfing", direction="SELL", signal_candle=cur,
            stop_loss=max(cur.high, prev.high), entry_price=cur.close,
        )
    return None


def detect_inside_bar(candles: List[Candle]) -> Optional[PatternMatch]:
    """
    Mother candle + inside baby candle, traded as a CONTINUATION breakout
    in the direction of the prevailing short-term move (the 2 bars before
    the mother candle). Signal fires only once the breakout candle closes
    beyond the mother candle's range.
    """
    if len(candles) < 4:
        return None
    pre, mother, baby, breakout = candles[-4], candles[-3], candles[-2], candles[-1]

    is_inside = baby.high <= mother.high and baby.low >= mother.low
    if not is_inside:
        return None

    # Only evaluate once we have a confirmed breakout candle
    if breakout.close > mother.high:
        return PatternMatch(
            strategy="inside_bar", direction="BUY", signal_candle=breakout,
            stop_loss=mother.low, entry_price=breakout.close,
        )
    if breakout.close < mother.low:
        return PatternMatch(
            strategy="inside_bar", direction="SELL", signal_candle=breakout,
            stop_loss=mother.high, entry_price=breakout.close,
        )
    return None


def detect_false_breakout(candles: List[Candle]) -> Optional[PatternMatch]:
    """
    Price breaks out of the mother candle's range then closes back INSIDE
    it -- the stop-hunt trap pattern. Needs mother + baby (inside bar) +
    a breakout attempt that fails and closes back within the mother's range.
    """
    if len(candles) < 4:
        return None
    _, mother, baby, reversal = candles[-4], candles[-3], candles[-2], candles[-1]

    is_inside = baby.high <= mother.high and baby.low >= mother.low
    if not is_inside:
        return None

    broke_up_but_closed_back = reversal.high > mother.high and reversal.close < mother.high
    broke_down_but_closed_back = reversal.low < mother.low and reversal.close > mother.low

    if broke_up_but_closed_back:
        return PatternMatch(
            strategy="false_breakout", direction="SELL", signal_candle=reversal,
            stop_loss=reversal.high, entry_price=reversal.close,
        )
    if broke_down_but_closed_back:
        return PatternMatch(
            strategy="false_breakout", direction="BUY", signal_candle=reversal,
            stop_loss=reversal.low, entry_price=reversal.close,
        )
    return None


ALL_DETECTORS = [detect_pin_bar, detect_engulfing, detect_inside_bar, detect_false_breakout]


def detect_all_patterns(candles: List[Candle]) -> List[PatternMatch]:
    matches = []
    for detector in ALL_DETECTORS:
        match = detector(candles)
        if match:
            matches.append(match)
    return matches
