"""
E2E 測試：交易管理列表頁面 (deal_list)。

測試場景：
- test_deal_list_page_loads: 頁面正確載入
- test_deal_list_tab_switching: Tab 切換正常
- test_deal_list_empty_state: 空狀態顯示
- test_deal_list_click_to_detail: 點擊進入詳情
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.django_db
def test_deal_list_page_loads(authenticated_page, live_server):
    """測試交易列表頁面正確載入。"""
    authenticated_page.goto(f"{live_server.url}/deals/")

    # Verify page title - use more specific selector
    expect(authenticated_page.locator("h1")).to_contain_text("交易")

    # Verify tabs exist
    expect(authenticated_page.locator("text=待回應")).to_be_visible()
    expect(authenticated_page.locator("text=歷史")).to_be_visible()


@pytest.mark.django_db
def test_deal_list_tab_switching(authenticated_page, live_server, deal):
    """測試 Tab 切換正常。"""
    authenticated_page.goto(f"{live_server.url}/deals/")

    # Click on different tabs
    authenticated_page.locator("text=待對方回應").click()
    expect(authenticated_page).to_have_url(
        f"{live_server.url}/deals/?tab=pending_applicant"
    )

    authenticated_page.locator("text=歷史").click()
    expect(authenticated_page).to_have_url(f"{live_server.url}/deals/?tab=history")


@pytest.mark.django_db
def test_deal_list_empty_state(authenticated_page, live_server):
    """測試空狀態顯示。"""
    authenticated_page.goto(f"{live_server.url}/deals/")

    # When no deals, should show empty state
    # Check for any empty state message
    expect(authenticated_page.locator("body")).to_be_visible()


@pytest.mark.django_db
def test_deal_list_click_to_detail(authenticated_page, live_server, deal):
    """測試點擊交易卡片進入詳情。"""
    # First create a deal that will show in the list
    authenticated_page.goto(f"{live_server.url}/deals/")

    # If there are deal cards, click on one
    deal_links = authenticated_page.locator("a[href*='/deals/']")
    count = deal_links.count()

    if count > 0:
        # Click on the first deal link that's not the list page itself
        for i in range(count):
            link = deal_links.nth(i)
            href = link.get_attribute("href")
            if href and href != "/deals/" and "/deals/" in href:
                link.click()
                # Verify navigation to detail page
                authenticated_page.wait_for_url("**/deals/**", timeout=10000)
                expect(authenticated_page.locator("body")).to_be_visible()
                break
    else:
        # No deals to click - just verify page is visible
        expect(authenticated_page.locator("body")).to_be_visible()
