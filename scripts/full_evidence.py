import asyncio
import subprocess
import os
import time
from playwright.async_api import async_playwright

async def take_screenshots():
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "exbook.dev_settings"
    server_proc = subprocess.Popen(
        ["python", "manage.py", "runserver", "0.0.0.0:8001"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={'width': 1280, 'height': 800})
            page = await context.new_page()

            for i in range(10):
                try:
                    await page.goto("http://127.0.0.1:8001/accounts/login/")
                    break
                except:
                    await asyncio.sleep(1)
            
            await page.screenshot(path="evidence_login_captcha.png", full_page=True)
            print("Saved evidence_login_captcha.png")

            await page.goto("http://127.0.0.1:8001/admin/login/")
            await page.fill('input[name="username"]', 'admin')
            await page.fill('input[name="password"]', 'admin123')
            await page.click('input[type="submit"]')
            await page.wait_for_url("**/admin/")

            await page.goto("http://127.0.0.1:8001/")
            await page.evaluate("toggleSidebar()")
            await asyncio.sleep(1)
            
            sidebar = await page.query_selector("#sidebar")
            if sidebar:
                await sidebar.screenshot(path="evidence_sidebar_logout.png")
                print("Saved evidence_sidebar_logout.png")
            
            await browser.close()
    finally:
        server_proc.terminate()

if __name__ == "__main__":
    asyncio.run(take_screenshots())
