import pytest
from playwright.sync_api import Page


def _playwright_browser_available():
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


if not _playwright_browser_available():
    pytest.skip("Playwright browser not available", allow_module_level=True)


@pytest.mark.django_db
def test_playwright_setup(page: Page):
    assert page is not None
    page.goto("about:blank")
    assert page.url == "about:blank"


@pytest.mark.django_db
def test_authenticated_page_fixture(authenticated_page: Page):
    assert authenticated_page is not None
    cookies = authenticated_page.context.cookies()
    session_cookie = next((c for c in cookies if c["name"] == "sessionid"), None)
    assert session_cookie is not None
