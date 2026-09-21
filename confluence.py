"""
Ties together Trend + Level + Signal (the book's core 3-part check) into a
single qualification decision, per the locked rule: STRICT -- all three
must align or the setup is dropped entirely, before best-of ranking even
sees it.
"""
from dataclasses import dataclass
from typing import List, Optional
from app.data.deriv_client import Candle
from app.analysis.trend import classify_trend, TrendType
from app.analysis.levels import all_levels, price_near_level, LevelHit, nearest_support_resistance
from app.analysis.patterns import PatternMatch, detect_all_patterns
from app.config import MIN_RR


@dataclass
class QualifiedSetup:
    symbol: str
    direction: str
    strategy: str
    trend: TrendType
    matched_levels: List[LevelHit]
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    confluence_score: float
    notes: str


def _trend_agrees(trend: TrendType, direction: str) -> bool:
    if trend == "up":
        return direction == "BUY"
    if trend == "down":
        return direction == "SELL"
    if trend == "range":
        return True  # range trades work both boundaries -- level check does the real filtering
    return False  # choppy -- never agrees


def _compute_target(htf_candles: List[Candle], entry: float, direction: str) -> Optional[float]:
    """Target = next opposing S/R level, per every strategy chapter in the book."""
    levels = nearest_support_resistance(htf_candles, entry)
    if direction == "BUY":
        resistances = [l.price for l in levels if l.kind == "resistance"]
        return min(resistances) if resistances else None
    else:
        supports = [l.price for l in levels if l.kind == "support"]
        return max(supports) if supports else None


def evaluate_symbol(symbol: str, htf_candles: List[Candle], ltf_candles: List[Candle]) -> Optional[QualifiedSetup]:
    """
    Full pipeline for one symbol:
    1. Trend on HTF
    2. Patterns on LTF
    3. Level check against HTF-derived levels
    4. Strict confluence gate
    5. Target + R:R calc, reject if below MIN_RR
    """
    trend = classify_trend(htf_candles)
    if trend == "choppy":
        return None  # never trade choppy markets -- book rule

    patterns = detect_all_patterns(ltf_candles)
    if not patterns:
        return None

    current_price = ltf_candles[-1].close
    levels = all_levels(htf_candles, current_price)

    best_setup: Optional[QualifiedSetup] = None

    for pattern in patterns:
        trend_ok = _trend_agrees(trend, pattern.direction)
        if not trend_ok:
            continue  # strict mode: trend must agree

        matched = [lv for lv in levels if price_near_level(pattern.entry_price, lv)]
        if not matched:
            continue  # strict mode: must be AT a level

        target = _compute_target(htf_candles, pattern.entry_price, pattern.direction)
        if target is None:
            continue

        risk = abs(pattern.entry_price - pattern.stop_loss)
        reward = abs(target - pattern.entry_price)
        if risk == 0:
            continue
        rr = reward / risk
        if rr < MIN_RR:
            continue

        score = len(matched) * 2 + rr  # confluence count weighted highest, R:R as tiebreaker

        setup = QualifiedSetup(
            symbol=symbol,
            direction=pattern.direction,
            strategy=pattern.strategy,
            trend=trend,
            matched_levels=matched,
            entry_price=pattern.entry_price,
            stop_loss=pattern.stop_loss,
            take_profit=target,
            risk_reward=round(rr, 2),
            confluence_score=round(score, 2),
            notes=" + ".join(lv.label for lv in matched),
        )

        if best_setup is None or setup.confluence_score > best_setup.confluence_score:
            best_setup = setup

    return best_setup
