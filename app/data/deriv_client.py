"""
Deriv WebSocket client -- fetches historical OHLC candles for a symbol.

Uses curl_cffi with Chrome impersonation instead of the plain `websockets`
library. Deriv/Cloudflare was rejecting every connection (HTTP 520) from
the plain websockets library's non-browser TLS fingerprint -- confirmed
across 4 different networks (Render, Railway, GitHub Actions, and even
mobile data via Termux), ruling out IP-based blocking. curl_cffi presents
a real Chrome TLS/JA3 fingerprint, which should get past that check.

Docs: https://developers.deriv.com/docs/websockets
"""
import json
import asyncio
from dataclasses import dataclass
from typing import List
from curl_cffi import AsyncSession
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
    per candle (e.g. 3600 = 1H, 14400 = 4H). Uses Chrome-impersonated
    WebSocket connection to get past Cloudflare's bot-fingerprint check.
    """
    async with AsyncSession() as s:
        ws = await s.ws_connect(DERIV_WS_URL, impersonate="chrome")

        if DERIV_API_TOKEN:
            await ws.send(json.dumps({"authorize": DERIV_API_TOKEN}).encode())
            await ws.recv()  # discard authorize response

        request = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": count,
            "end": "latest",
            "style": "candles",
            "granularity": granularity,
        }
        await ws.send(json.dumps(request).encode())
        raw = await ws.recv()
        # curl_cffi may return (bytes, flags) tuple or just bytes depending on version
        data = raw[0] if isinstance(raw, tuple) else raw
        response = json.loads(data)

        await ws.close()

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
    """Fetch candles for multiple symbols ONE AT A TIME (not concurrently) --
    keeps memory usage low and avoids hammering the connection."""
    out = {}
    for symbol in symbols:
        try:
            out[symbol] = await fetch_candles(symbol, granularity, count)
        except Exception as e:
            print(f"[deriv_client] failed to fetch {symbol}: {e}")
    return out
