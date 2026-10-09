"""
Minimal standalone test: can GitHub Actions' servers reach Deriv's
WebSocket API? No app dependencies, no database -- just the raw
connection test, isolated from everything else.
"""
import asyncio
import json
import websockets

DERIV_WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"

async def test():
    try:
        async with websockets.connect(DERIV_WS_URL, ping_interval=20) as ws:
            request = {
                "ticks_history": "R_100",
                "adjust_start_time": 1,
                "count": 5,
                "end": "latest",
                "style": "candles",
                "granularity": 300,
            }
            await ws.send(json.dumps(request))
            response = json.loads(await ws.recv())
            if "error" in response:
                print(f"CONNECTED but API error: {response['error']}")
            else:
                print(f"SUCCESS: got {len(response.get('candles', []))} candles")
                print(response.get('candles', [])[:2])
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

asyncio.run(test())
