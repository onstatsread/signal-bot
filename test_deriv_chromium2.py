import asyncio
from termux_playwright import async_playwright_termux, launch

DERIV_APP_ID = "34tmw8hqr2IjqrVCumH9L"

JS_CODE = """
() => {
    const ws = new WebSocket("wss://ws.derivws.com/websockets/v3?app_id=%s");
    window._wsResult = null;
    ws.onopen = () => {
        window._wsResult = "opened";
        ws.send(JSON.stringify({
            ticks_history: "R_100", adjust_start_time: 1, count: 5,
            end: "latest", style: "candles", granularity: 300
        }));
    };
    ws.onmessage = (e) => { window._wsResult = e.data; };
    ws.onclose = (e) => { window._wsClose = {code: e.code, reason: e.reason, wasClean: e.wasClean}; };
    ws.onerror = () => { window._wsError = true; };
}
""" % DERIV_APP_ID

async def test():
    async with async_playwright_termux() as p:
        browser = await launch(p, headless=True)
        try:
            page = await browser.new_page()

            def on_ws(ws):
                print(f"[playwright] websocket created: {ws.url}")
                ws.on("close", lambda: print("[playwright] websocket closed"))
                ws.on("socketerror", lambda err: print(f"[playwright] socket error: {err}"))

            page.on("websocket", on_ws)

            await page.goto("https://deriv.com", timeout=30000, wait_until="domcontentloaded")
            await page.evaluate(JS_CODE)

            for _ in range(15):
                await asyncio.sleep(1)
                result = await page.evaluate("window._wsResult")
                close_info = await page.evaluate("window._wsClose")
                if result and result != "opened":
                    print(f"SUCCESS: {result[:300]}")
                    break
                if close_info:
                    print(f"CLOSED: {close_info}")
                    break
            else:
                print("TIMEOUT: no result after 15s")
                print("last state:", await page.evaluate("window._wsResult"))

        except Exception as e:
            print(f"FAILED: {type(e).__name__}: {e}")
        finally:
            await browser.close()

asyncio.run(test())
