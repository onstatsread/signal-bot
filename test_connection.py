import asyncio
from app.data.deriv_client import fetch_candles

async def test():
    candles = await fetch_candles('R_100', 300, 5)
    print(f'SUCCESS: got {len(candles)} candles')
    print(candles[-1])

asyncio.run(test())
