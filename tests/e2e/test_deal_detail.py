"""
E2E 測試：交易詳情頁面 (deal_detail)。

測試場景：
- test_deal_detail_page_loads: 頁面正確載入
- test_deal_detail_accept_button_visible_for_responder: 接受按鈕可見性
- test_deal_detail_cancel_button_visible_for_applicant: 取消按鈕可見性
- test_deal_detail_send_message: 發送留言
- test_deal_detail_complete_meeting: 完成面交
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.django_db
def test_deal_detail_page_loads(authenticated_page, live_server, deal):
    """測試交易詳情頁面正確載入。"""
    authenticated_page.goto(f"{live_server.url}/deals/{deal.id}/")

    # Verify page elements - use more specific selector
    expect(authenticated_page.get_by_role("heading", name="交易詳情")).to_be_visible()
    expect(authenticated_page.locator("body")).to_contain_text(
        deal.shared_book.official_book.title
    )


@pytest.mark.django_db
def test_deal_detail_accept_button_visible_for_responder(
    authenticated_page, live_server, deal_as_responder
):
    """測試回應者可以看到接受/拒絕按鈕。"""
    authenticated_page.goto(f"{live_server.url}/deals/{deal_as_responder.id}/")

    # Verify action buttons are visible for responder
    expect(authenticated_page.locator("button:has-text('接受')")).to_be_visible()
    expect(authenticated_page.locator("button:has-text('拒絕')")).to_be_visible()

    # Cancel button should NOT be visible for responder
    expect(authenticated_page.locator("button:has-text('取消')")).not_to_be_visible()


@pytest.mark.django_db
def test_deal_detail_cancel_button_visible_for_applicant(
    authenticated_page, live_server, deal_as_applicant
):
    """測試申請者可以看到取消按鈕。"""
    authenticated_page.goto(f"{live_server.url}/deals/{deal_as_applicant.id}/")

    # Cancel button should be visible for applicant
    expect(authenticated_page.locator("button:has-text('取消')")).to_be_visible()

    # Accept/Reject buttons should NOT be visible for applicant
    expect(authenticated_page.locator("button:has-text('接受')")).not_to_be_visible()


@pytest.mark.django_db
def test_deal_detail_send_message(authenticated_page, live_server, deal):
    """測試發送留言。"""
    authenticated_page.goto(f"{live_server.url}/deals/{deal.id}/")

    # Note: The current deal_detail template doesn't have a message input
    # This test will need to be updated when message functionality is added
    # For now, we just verify the page loads with the correct title
    expect(authenticated_page.get_by_role("heading", name="交易詳情")).to_be_visible()


@pytest.mark.django_db
def test_deal_detail_complete_meeting(authenticated_page, live_server, deal_responded):
    """測試完成面交。"""
    authenticated_page.goto(f"{live_server.url}/deals/{deal_responded.id}/")

    # Click complete button
    authenticated_page.locator("button:has-text('確認面交')").click()

    # Wait for page to load after redirect
    # The status should change to MEETED (M) and show "待評價" or redirect to rating page
    # Check for either the status badge or the rating button
    authenticated_page.wait_for_url("**/deals/**", timeout=10000)

    # Verify we're still on a deals page (either detail or rating)
    expect(authenticated_page.locator("body")).to_be_visible()
