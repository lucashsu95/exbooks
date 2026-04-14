"""
QA Test for Book Set Create Page
Tests: Checkbox state, CSS highlight, fallback image, mobile layout
"""

import asyncio
from playwright.async_api import async_playwright


async def test_book_set_create():
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        try:
            print("=" * 60)
            print("QA Test: Book Set Create Page")
            print("=" * 60)

            # Navigate to login page first
            print("\n[Step 1] Navigating to login page...")
            await page.goto("http://localhost:8000/accounts/login/")
            await page.wait_for_load_state("networkidle")

            # Check if already logged in
            if "login" not in page.url:
                print("Already logged in, proceeding...")
            else:
                print("Attempting auto-login with test credentials...")
                # Try to fill in login form if it exists
                try:
                    await page.fill('input[name="login"]', "test@example.com")
                    await page.fill('input[name="password"]', "testpass123")
                    await page.click('button[type="submit"]')
                    await page.wait_for_load_state("networkidle")
                    print("Login submitted")
                except Exception as e:
                    print(f"Could not auto-login: {e}")
                    print("Checking if already authenticated...")

            # Navigate to book set create page
            print("\n[Step 2] Navigating to /books/sets/create/...")
            await page.goto("http://localhost:8000/books/sets/create/")
            await page.wait_for_load_state("networkidle")

            # Take initial screenshot
            await page.screenshot(path="test_results/01_initial_page.png")
            print("[OK] Screenshot saved: 01_initial_page.png")

            # Test 1: Check if book selection cards exist
            print("\n[Step 3] Checking for book selection cards...")
            cards = await page.locator(".book-selection-label").all()
            print(f"Found {len(cards)} book selection card(s)")

            if len(cards) == 0:
                print("[!] No books available - checking for empty state...")
                empty_state = await page.locator("text=沒有").is_visible()
                if empty_state:
                    print("[OK] Empty state message displayed")
                await page.screenshot(path="test_results/02_no_books.png")
                print("\n[!] Cannot continue tests - no books available")
                return

            # Test 2: Click on first card and verify checkbox state
            print("\n[Step 4] Testing checkbox click on first card...")
            first_card = cards[0]
            checkbox = first_card.locator('input[type="checkbox"]')

            # Get initial state
            is_checked_before = await checkbox.is_checked()
            print(f"  Before click: checked = {is_checked_before}")

            # Click the card
            await first_card.click()
            await asyncio.sleep(0.5)  # Wait for animation

            # Get state after click
            is_checked_after = await checkbox.is_checked()
            print(f"  After click: checked = {is_checked_after}")

            if is_checked_after != is_checked_before:
                print("[OK] Checkbox state changed correctly")
            else:
                print("[FAIL] Checkbox state did NOT change")

            await page.screenshot(path="test_results/03_card_clicked.png")
            print("[OK] Screenshot saved: 03_card_clicked.png")

            # Test 3: Verify CSS highlight (checked state)
            print("\n[Step 5] Checking CSS highlight for checked state...")
            card_div = first_card.locator(".book-selection-card")

            # Check for checked state classes
            border_color = await card_div.evaluate(
                "el => getComputedStyle(el).borderColor"
            )
            print(f"  Card border color: {border_color}")

            # Check selection icon
            icon = first_card.locator(".selection-icon")
            icon_style = await icon.evaluate(
                "el => getComputedStyle(el).backgroundColor"
            )
            print(f"  Selection icon background: {icon_style}")

            if "rgb(59, 130, 246)" in icon_style or "rgb(59, 130, 246)" in border_color:
                print("[OK] CSS highlight working")
            else:
                print("[WARN] CSS highlight may need verification")

            # Test 4: Check for fallback image
            print("\n[Step 6] Checking fallback image display...")
            cover_divs = await page.locator(".book-selection-card .w-12").all()
            for i, cover in enumerate(cover_divs[:3]):  # Check first 3
                # Check if image exists
                img = cover.locator("img")
                has_img = await img.count() > 0

                if has_img:
                    src = await img.get_attribute("src")
                    print(f"  Book {i + 1}: Has image (src: {src[:50]}...)")
                else:
                    # Check for fallback icon
                    fallback = cover.locator(".material-symbols-outlined")
                    has_fallback = await fallback.count() > 0
                    if has_fallback:
                        icon_text = await fallback.text_content()
                        print(f"  Book {i + 1}: Using fallback icon '{icon_text}'")
                    else:
                        print(f"  Book {i + 1}: No image or fallback found")

            # Test 5: Mobile viewport test
            print("\n[Step 7] Testing mobile layout (iPhone 12 Pro)...")
            await context.close()
            mobile_context = await browser.new_context(
                viewport={"width": 390, "height": 844},
                device_scale_factor=3,
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
            )
            mobile_page = await mobile_context.new_page()

            await mobile_page.goto("http://localhost:8000/books/sets/create/")
            await mobile_page.wait_for_load_state("networkidle")

            await mobile_page.screenshot(path="test_results/04_mobile_layout.png")
            print("[OK] Mobile screenshot saved: 04_mobile_layout.png")

            # Check for layout issues
            cards_mobile = await mobile_page.locator(".book-selection-label").all()
            print(f"  Mobile: Found {len(cards_mobile)} card(s)")

            # Check if cards are properly sized
            first_card_mobile = mobile_page.locator(".book-selection-label").first
            box = await first_card_mobile.bounding_box()
            if box:
                print(f"  First card size: {box['width']}x{box['height']}px")
                if box["width"] > 350:  # Should be less than viewport width
                    print("[WARN] Card may be too wide for mobile viewport")
                else:
                    print("[OK] Card width looks good for mobile")

            # Check for horizontal overflow
            overflow = await mobile_page.evaluate("""() => {
                const body = document.body;
                return body.scrollWidth > body.clientWidth;
            }""")
            if overflow:
                print("[FAIL] Horizontal overflow detected!")
            else:
                print("[OK] No horizontal overflow")

            await mobile_context.close()

            print("\n" + "=" * 60)
            print("QA Test Complete!")
            print("=" * 60)
            print("\nScreenshots saved in test_results/")

        except Exception as e:
            print(f"\n[FAIL] Error during test: {e}")
            await page.screenshot(path="test_results/error_screenshot.png")
            raise
        finally:
            await browser.close()


if __name__ == "__main__":
    import os

    os.makedirs("test_results", exist_ok=True)
    asyncio.run(test_book_set_create())
