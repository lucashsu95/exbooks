import asyncio
from playwright.async_api import async_playwright

async def take_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        print("Taking login page screenshot...")
        await page.goto("http://127.0.0.1:8001/accounts/login/")
        await page.wait_for_selector("input")
        await page.screenshot(path="evidence_login_captcha.png", full_page=True)
        print("Saved evidence_login_captcha.png")

        print("Logging in...")
        await page.goto("http://127.0.0.1:8001/admin/login/")
        await page.fill('input[name="username"]', 'admin')
        await page.fill('input[name="password"]', 'admin123')
        await page.click('input[type="submit"]')
        await page.wait_for_url("**/admin/")

        print("Taking sidebar screenshot...")
        await page.goto("http://127.0.0.1:8001/")
        await page.evaluate("toggleSidebar()")
        await asyncio.sleep(1)
        
        sidebar = await page.query_selector("#sidebar")
        if sidebar:
            await sidebar.screenshot(path="evidence_sidebar_logout.png")
            print("Saved evidence_sidebar_logout.png")
        else:
            print("Sidebar not found!")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(take_screenshots())
