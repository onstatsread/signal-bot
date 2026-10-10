import asyncio
import json
from termux_playwright import async_playwright_termux, launch

DERIV_APP_ID = "34tmw8hqr2IjqrVCumH9L"

JS_CODE = """
async () => {
    return new Promise((resolve, reject) => {
        const ws = new WebSocket("wss://ws.derivws.com/websockets/v3?app_id=%s");
        const timeout = setTimeout(() => reject("TIMEOUT after 15s"), 15000);

        ws.onopen = () => {
            ws.send(JSON.stringify({
                ticks_history: "R_100",
                adjust_start_time: 1,
                count: 5,
                end: "latest",
                style: "candles",
                granularity: 300
            }));
        };

        ws.onmessage = (event) => {
            clearTimeout(timeout);
            ws.close();
            resolve(event.data);
        };

        ws.onerror = (err) => {
            clearTimeout(timeout);
            reject("WebSocket error");
        };
    });
}
""" % DERIV_APP_ID

async def test():
    async with async_playwright_termux() as p:
        browser = await launch(p, headless=True)
        try:
            page = await browser.new_page()
            await page.goto("https://deriv.com", timeout=30000, wait_until="domcontentloaded")

            result = await page.evaluate(JS_CODE)
            data = json.loads(result)

            if "error" in data:
                print(f"CONNECTED but API error: {data['error']}")
            else:
                candles = data.get("candles", [])
                print(f"SUCCESS: got {len(candles)} candles")
                print(candles[-2:] if len(candles) >= 2 else candles)

        except Exception as e:
            print(f"FAILED: {type(e).__name__}: {e}")
        finally:
            await browser.close()

asyncio.run(test())
