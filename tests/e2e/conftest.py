def _playwright_available():
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


if not _playwright_available():

    def pytest_collect_file(file_path, parent):
        if file_path.suffix == ".py" and file_path.name.startswith("test_"):
            parent.config.issue_config_time_warning(
                f"Skipping {file_path.name}: Playwright unavailable", "e2e"
            )
            return None

    collect_ignore = [
        "test_book_add.py",
        "test_deal_create.py",
        "test_deal_detail.py",
        "test_deal_list.py",
        "test_rating_create.py",
    ]
