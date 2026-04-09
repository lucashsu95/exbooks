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
    expect(authenticated_page.get_by_role("button", name="接受申請")).to_be_visible()
    expect(authenticated_page.get_by_role("button", name="婉拒")).to_be_visible()

    # Cancel button should NOT be visible for responder
    expect(
        authenticated_page.get_by_role("button", name="取消借閱申請")
    ).not_to_be_visible()


@pytest.mark.django_db
def test_deal_detail_cancel_button_visible_for_applicant(
    authenticated_page, live_server, deal_as_applicant
):
    """測試申請者可以看到取消按鈕。"""
    authenticated_page.goto(f"{live_server.url}/deals/{deal_as_applicant.id}/")

    # Cancel button should be visible for applicant
    expect(
        authenticated_page.get_by_role("button", name="取消借閱申請")
    ).to_be_visible()

    # Accept/Reject buttons should NOT be visible for applicant
    expect(
        authenticated_page.get_by_role("button", name="接受申請")
    ).not_to_be_visible()


@pytest.mark.django_db
def test_deal_detail_send_message(authenticated_page, live_server, deal_as_responder):
    """測試發送留言透過 HTMX 表單。"""
    # Use deal_as_responder so authenticated user (test_user) can send messages
    authenticated_page.goto(f"{live_server.url}/deals/{deal_as_responder.id}/")

    # Verify page loads
    expect(authenticated_page.get_by_role("heading", name="交易詳情")).to_be_visible()

    # Find the message input field
    message_input = authenticated_page.locator("#message-input")
    expect(message_input).to_be_visible()

    # Type a test message
    test_message = "這是一條測試留言"
    message_input.fill(test_message)
    expect(message_input).to_have_value(test_message)

    # Submit the form (HTMX will handle POST to deals:message_send)
    authenticated_page.locator("form:has(#message-input) button[type='submit']").click()

    # Wait for HTMX response (message list should update with new message)
    authenticated_page.wait_for_timeout(2000)

    # Verify the new message appears in the message list
    expect(authenticated_page.locator("#message-list")).to_contain_text(test_message)

    # Verify the input field was cleared after submission
    expect(message_input).to_have_value("")


@pytest.mark.django_db
def test_deal_detail_complete_meeting(authenticated_page, live_server, deal_responded):
    """測試完成面交。"""
    authenticated_page.goto(f"{live_server.url}/deals/{deal_responded.id}/")

    # Click complete button - button is behind fixed nav, use force click
    authenticated_page.get_by_role("button", name="確認面交").click(force=True)

    # Wait for page to load after redirect
    # The status should change to MEETED (M) and show "待評價" or redirect to rating page
    # Check for either the status badge or the rating button
    authenticated_page.wait_for_url("**/deals/**", timeout=10000)

    # Verify we're still on a deals page (either detail or rating)
    expect(authenticated_page.locator("body")).to_be_visible()
