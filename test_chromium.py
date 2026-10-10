import asyncio
from termux_playwright import async_playwright_termux, launch

async def test():
    async with async_playwright_termux() as p:
        browser = await launch(p, headless=True)
        try:
            page = await browser.new_page()
            resp = await page.goto("https://example.com", timeout=30000)
            print(f"SUCCESS: status {resp.status}, title: {await page.title()}")
        finally:
            await browser.close()

asyncio.run(test())
