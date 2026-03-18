import pytest
from playwright.sync_api import Page


@pytest.mark.django_db
def test_playwright_setup(page: Page):
    """
    Simple test to verify playwright is working.
    """
    assert page is not None
    page.goto("about:blank")
    assert page.url == "about:blank"


@pytest.mark.django_db
def test_authenticated_page_fixture(authenticated_page: Page):
    """
    Verify the authenticated_page fixture.
    """
    assert authenticated_page is not None
    # Check if sessionid cookie is set
    cookies = authenticated_page.context.cookies()
    # The cookie name is from settings.SESSION_COOKIE_NAME, which defaults to 'sessionid'
    session_cookie = next((c for c in cookies if c["name"] == "sessionid"), None)
    assert session_cookie is not None
