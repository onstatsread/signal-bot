"""
Deriv WebSocket client -- fetches historical OHLC candles for a symbol.

Deriv's API is free to use for market data with just an app_id (no login
needed for candles). If DERIV_API_TOKEN is set, we authorize first, which
is only required if you later want to place trades -- not needed for this
signal-only bot, but wired in for when you're ready to combine it with
your execution bot.

Docs: https://developers.deriv.com/docs/websockets
"""
import json
import asyncio
import websockets
from dataclasses import dataclass
from typing import List
from app.config import DERIV_WS_URL, DERIV_API_TOKEN


@dataclass
class Candle:
    epoch: int
    open: float
    high: float
    low: float
    close: float

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low


async def fetch_candles(symbol: str, granularity: int, count: int) -> List[Candle]:
    """
    Fetch `count` most recent candles for `symbol` at `granularity` seconds
    per candle (e.g. 3600 = 1H, 14400 = 4H).
    """
    async with websockets.connect(
        DERIV_WS_URL,
        ping_interval=20,
        extra_headers={"Origin": "https://signal-bot-eqg8.onrender.com"},
    ) as ws:
        if DERIV_API_TOKEN:
            await ws.send(json.dumps({"authorize": DERIV_API_TOKEN}))
            await ws.recv()  # discard authorize response

        request = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": count,
            "end": "latest",
            "style": "candles",
            "granularity": granularity,
        }
        await ws.send(json.dumps(request))
        response = json.loads(await ws.recv())

        if "error" in response:
            raise RuntimeError(f"Deriv API error for {symbol}: {response['error']['message']}")

        raw_candles = response.get("candles", [])
        return [
            Candle(
                epoch=c["epoch"],
                open=float(c["open"]),
                high=float(c["high"]),
                low=float(c["low"]),
                close=float(c["close"]),
            )
            for c in raw_candles
        ]


async def fetch_all(symbols: List[str], granularity: int, count: int) -> dict:
    """Fetch candles for multiple symbols ONE AT A TIME (not concurrently) -- keeps
    memory usage low on Render's free 512MB tier, which was crashing under the
    old concurrent version."""
    out = {}
    for symbol in symbols:
        try:
            out[symbol] = await fetch_candles(symbol, granularity, count)
        except Exception as e:
            print(f"[deriv_client] failed to fetch {symbol}: {e}")
    return out
