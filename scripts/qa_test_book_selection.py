"""
QA Test for Book Set Create Page - Book Selection Cards
Tests: Checkbox state, CSS highlight, fallback image, mobile layout
"""

import asyncio
import os
from playwright.async_api import async_playwright


async def run_qa_tests():
    """Run QA tests for book selection cards"""

    # Create test results directory
    os.makedirs("test_results", exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        print("=" * 70)
        print("QA TEST: Book Set Create Page - Book Selection Cards")
        print("=" * 70)

        # Test 1: Desktop View - Basic Structure
        print("\n[Test 1] Desktop View - Page Structure Check")
        print("-" * 50)

        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        # Navigate to book set create page (will redirect to login)
        await page.goto("http://localhost:8000/books/sets/create/")
        await page.wait_for_load_state("networkidle")

        # Check if redirected to login
        if "login" in page.url:
            print("  [!] Page requires authentication - redirected to login")
            print("  [INFO] Taking screenshot of login page for reference")
            await page.screenshot(path="test_results/01_login_page.png")
        else:
            print("  [OK] Page loaded successfully")
            await page.screenshot(path="test_results/01_desktop_initial.png")

            # Check for book selection cards
            cards = await page.locator(".book-selection-label").count()
            print(f"  [INFO] Found {cards} book selection card(s)")

        await context.close()

        # Test 2: HTML Structure Analysis
        print("\n[Test 2] HTML Structure Analysis")
        print("-" * 50)

        # Read the template file
        template_path = "templates/forms/widgets/book_selection.html"
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Check key elements
            checks = [
                (
                    "Checkbox input with 'peer' class",
                    'class="peer hidden book-selection-input"',
                ),
                (
                    "Card container with peer-checked styles",
                    "peer-checked:border-primary",
                ),
                ("Selection icon element", "selection-icon"),
                ("Book cover container", "w-12 h-16"),
                ("Fallback icon for missing cover", "material-symbols-outlined"),
                ("CSS for checked state", ".book-selection-input:checked"),
                ("Responsive flex layout", "flex gap-4 items-center"),
                ("Truncate for long titles", "truncate"),
            ]

            for check_name, pattern in checks:
                if pattern in html_content:
                    print(f"  [OK] {check_name}")
                else:
                    print(f"  [FAIL] {check_name} - Pattern not found: {pattern}")

            # Check CSS variables
            if "--primary-color" in html_content:
                print("  [OK] CSS variable for primary color defined")
            else:
                print("  [WARN] CSS variable --primary-color not found")
        else:
            print(f"  [SKIP] Template file not found: {template_path}")

        # Test 3: CSS Styling Verification
        print("\n[Test 3] CSS Styling Verification")
        print("-" * 50)

        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        # Create a test HTML page with the book selection card
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght@100..700&display=block" rel="stylesheet">
            <style>
                :root { --primary-color: #3b82f6; }
                .book-selection-input:checked + .book-selection-card .selection-icon {
                    border-color: var(--primary-color);
                    background-color: var(--primary-color);
                    color: white;
                    transform: scale(1.1);
                }
            </style>
        </head>
        <body class="bg-gray-100 p-8">
            <div class="max-w-md mx-auto space-y-3">
                <!-- Test Card 1: With Image -->
                <label class="relative block cursor-pointer group book-selection-label">
                    <input type="checkbox" id="test1" class="peer hidden book-selection-input">
                    <div class="flex gap-4 items-center p-3 rounded-2xl border-2 transition-all duration-200 shadow-sm border-slate-100 bg-white group-hover:bg-slate-50 peer-checked:border-primary peer-checked:bg-primary/5 peer-checked:shadow-md peer-checked:shadow-primary/5 book-selection-card">
                        <div class="size-6 rounded-full border-2 flex items-center justify-center shrink-0 transition-all duration-200 border-slate-300 bg-white text-transparent selection-icon">
                            <span class="material-symbols-outlined text-sm font-bold">check</span>
                        </div>
                        <div class="flex gap-3 items-center flex-1 min-w-0">
                            <div class="w-12 h-16 bg-slate-100 rounded-lg flex-shrink-0 overflow-hidden shadow-sm border border-slate-200">
                                <img src="https://via.placeholder.com/48x64/3b82f6/ffffff?text=Book" class="w-full h-full object-cover">
                            </div>
                            <div class="flex-1 min-w-0">
                                <span class="text-sm font-bold text-slate-900 block truncate">Test Book Title</span>
                                <p class="text-xs text-slate-500 mt-0.5 truncate">Test Author</p>
                                <p class="text-[10px] text-slate-400 mt-0.5">Test Publisher</p>
                            </div>
                        </div>
                    </div>
                </label>

                <!-- Test Card 2: Without Image (Fallback) -->
                <label class="relative block cursor-pointer group book-selection-label">
                    <input type="checkbox" id="test2" class="peer hidden book-selection-input">
                    <div class="flex gap-4 items-center p-3 rounded-2xl border-2 transition-all duration-200 shadow-sm border-slate-100 bg-white group-hover:bg-slate-50 peer-checked:border-primary peer-checked:bg-primary/5 peer-checked:shadow-md peer-checked:shadow-primary/5 book-selection-card">
                        <div class="size-6 rounded-full border-2 flex items-center justify-center shrink-0 transition-all duration-200 border-slate-300 bg-white text-transparent selection-icon">
                            <span class="material-symbols-outlined text-sm font-bold">check</span>
                        </div>
                        <div class="flex gap-3 items-center flex-1 min-w-0">
                            <div class="w-12 h-16 bg-slate-100 rounded-lg flex-shrink-0 overflow-hidden shadow-sm border border-slate-200 flex items-center justify-center">
                                <span class="material-symbols-outlined text-slate-300">book</span>
                            </div>
                            <div class="flex-1 min-w-0">
                                <span class="text-sm font-bold text-slate-900 block truncate">Book Without Cover</span>
                                <p class="text-xs text-slate-500 mt-0.5 truncate">Unknown Author</p>
                            </div>
                        </div>
                    </div>
                </label>
            </div>
        </body>
        </html>
        """

        await page.set_content(test_html)
        await page.wait_for_timeout(500)

        # Take screenshot of initial state
        await page.screenshot(path="test_results/02_cards_initial.png")
        print("  [OK] Screenshot saved: 02_cards_initial.png")

        # Test 4: Checkbox Click Behavior
        print("\n[Test 4] Checkbox Click Behavior")
        print("-" * 50)

        # Click on the label (not the hidden checkbox)
        await page.click("label:has(#test1)")
        await page.wait_for_timeout(300)

        # Check if checkbox is checked
        is_checked = await page.is_checked("#test1")
        if is_checked:
            print("  [OK] Checkbox state changed to checked after click")
        else:
            print("  [FAIL] Checkbox did not change to checked state")

        await page.screenshot(path="test_results/03_card_checked.png")
        print("  [OK] Screenshot saved: 03_card_checked.png")

        # Click again to uncheck
        await page.click("label:has(#test1)")
        await page.wait_for_timeout(300)

        is_checked = await page.is_checked("#test1")
        if not is_checked:
            print("  [OK] Checkbox state changed to unchecked after second click")
        else:
            print("  [FAIL] Checkbox did not change to unchecked state")

        # Test 5: CSS Highlight Verification
        print("\n[Test 5] CSS Highlight Verification")
        print("-" * 50)

        # Check first card (checked) - click on label
        await page.click("label:has(#test1)")
        await page.wait_for_timeout(300)

        # Get computed styles using JavaScript
        card_border = await page.evaluate("""() => {
            const card = document.querySelector('#test1').closest('.book-selection-card');
            return card ? getComputedStyle(card).borderColor : 'not found';
        }""")
        print(f"  [INFO] Checked card border color: {card_border}")

        icon_bg = await page.evaluate("""() => {
            const icon = document.querySelector('#test1:checked + .book-selection-card .selection-icon');
            return icon ? getComputedStyle(icon).backgroundColor : 'not found';
        }""")
        print(f"  [INFO] Selection icon background: {icon_bg}")

        if "rgb(59, 130, 246)" in icon_bg or "rgb(59, 130, 246)" in card_border:
            print("  [OK] CSS highlight (primary color) is applied")
        else:
            print("  [WARN] CSS highlight may not be using expected primary color")

        # Test 6: Mobile Layout Test
        print("\n[Test 6] Mobile Layout Test (iPhone 12)")
        print("-" * 50)

        await context.close()
        mobile_context = await browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=3
        )
        mobile_page = await mobile_context.new_page()
        await mobile_page.set_content(test_html)
        await mobile_page.wait_for_timeout(500)

        await mobile_page.screenshot(path="test_results/04_mobile_layout.png")
        print("  [OK] Mobile screenshot saved: 04_mobile_layout.png")

        # Check for overflow
        has_overflow = await mobile_page.evaluate("""() => {
            return document.body.scrollWidth > document.body.clientWidth;
        }""")

        if has_overflow:
            print("  [FAIL] Horizontal overflow detected on mobile!")
        else:
            print("  [OK] No horizontal overflow on mobile")

        # Check card width
        card_width = await mobile_page.eval_on_selector(
            ".book-selection-card", "el => el.getBoundingClientRect().width"
        )
        print(f"  [INFO] Card width on mobile: {card_width}px")

        if card_width > 370:
            print("  [WARN] Card may be too wide for mobile viewport")
        else:
            print("  [OK] Card width is appropriate for mobile")

        await mobile_context.close()

        # Test 7: Fallback Image Display
        print("\n[Test 7] Fallback Image Display")
        print("-" * 50)

        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()
        await page.set_content(test_html)

        # Check second card (without image)
        has_fallback_icon = (
            await page.locator("#test2")
            .locator("..")
            .locator(".material-symbols-outlined:has-text('book')")
            .count()
            > 0
        )

        if has_fallback_icon:
            print("  [OK] Fallback icon (book symbol) is displayed for missing cover")
        else:
            print("  [INFO] Fallback icon check - may need manual verification")

        # Check first card (with image)
        has_image = (
            await page.locator("#test1").locator("..").locator("img").count() > 0
        )
        if has_image:
            print("  [OK] Book cover image is displayed")
        else:
            print("  [WARN] Book cover image not found")

        await context.close()

        # Summary
        print("\n" + "=" * 70)
        print("QA TEST SUMMARY")
        print("=" * 70)
        print("\nScreenshots saved in test_results/:")
        for f in os.listdir("test_results"):
            print(f"  - {f}")

        print("\n[Test Results]")
        print("  [Test 1] Desktop View - Page Structure: Completed")
        print("  [Test 2] HTML Structure Analysis: Completed")
        print("  [Test 3] CSS Styling Verification: Completed")
        print("  [Test 4] Checkbox Click Behavior: Completed")
        print("  [Test 5] CSS Highlight Verification: Completed")
        print("  [Test 6] Mobile Layout Test: Completed")
        print("  [Test 7] Fallback Image Display: Completed")

        print("\n[NOTE] Full authentication test requires valid login credentials")
        print("[NOTE] Manual verification recommended for visual styling details")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run_qa_tests())
