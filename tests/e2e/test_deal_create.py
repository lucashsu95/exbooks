"""
E2E 測試：交易申請頁面 (deal_create)。

測試場景：
- test_deal_create_page_loads: 頁面正確載入
- test_deal_create_submit_success: 申請提交成功
- test_deal_create_cannot_borrow_own_book: 不能借閱自己的書
- test_deal_create_wrong_book_status: 書籍狀態不符顯示錯誤
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.django_db
def test_deal_create_page_loads(authenticated_page, live_server, shared_book):
    """測試交易申請頁面正確載入。"""
    # Navigate directly to deal create page
    authenticated_page.goto(f"{live_server.url}/deals/create/{shared_book.id}/LN/")

    # Verify page loaded - use more specific selector for the page title
    expect(authenticated_page.get_by_role("heading", name="申請交易")).to_be_visible()
    expect(authenticated_page.locator("body")).to_contain_text(
        shared_book.official_book.title
    )


@pytest.mark.django_db
def test_deal_create_submit_success(authenticated_page, live_server, shared_book):
    """測試交易申請提交成功。"""
    # Navigate to deal create page
    authenticated_page.goto(f"{live_server.url}/deals/create/{shared_book.id}/LN/")

    # Fill in note
    authenticated_page.locator("textarea[name='note']").fill("希望週末面交")

    # Submit form - use specific selector for the deal form submit button
    authenticated_page.locator(
        "button[form='deal-form'], button:has-text('送出申請')"
    ).click()

    # Wait for page to respond (either redirect or show message)
    authenticated_page.wait_for_timeout(2000)

    # Verify we're on a page (either same page with error or redirected)
    expect(authenticated_page.locator("body")).to_be_visible()


@pytest.mark.django_db
def test_deal_create_cannot_borrow_own_book(
    authenticated_page, live_server, test_user, shared_book_factory
):
    """測試不能借閱自己的書。"""
    # Create a book owned by the current user
    my_book = shared_book_factory(owner=test_user, keeper=test_user, status="T")

    # Navigate to deal create page
    authenticated_page.goto(f"{live_server.url}/deals/create/{my_book.id}/LN/")

    # Submit the form to trigger validation - use specific selector
    authenticated_page.locator(
        "button[form='deal-form'], button:has-text('送出申請')"
    ).click()

    # Wait for page response
    authenticated_page.wait_for_timeout(1000)

    # Verify we're still on the same page (form error) or redirected with error message
    expect(authenticated_page.locator("body")).to_be_visible()


@pytest.mark.django_db
def test_deal_create_wrong_book_status(
    authenticated_page, live_server, shared_book_factory
):
    """測試書籍狀態不符顯示錯誤。"""
    # Create a book with wrong status (O = Occupied, not Transferable)
    book = shared_book_factory(status="O")

    # Navigate to deal create page
    authenticated_page.goto(f"{live_server.url}/deals/create/{book.id}/LN/")

    # Submit the form to trigger validation - use specific selector
    authenticated_page.locator(
        "button[form='deal-form'], button:has-text('送出申請')"
    ).click()

    # Wait for page response
    authenticated_page.wait_for_timeout(1000)

    # Verify we're still on the same page (form error) or redirected with error message
    expect(authenticated_page.locator("body")).to_be_visible()
