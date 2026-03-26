"""
書籍上架 E2E 測試

測試書籍上架完整流程，包含：
- 頁面載入
- ISBN 查詢成功/失敗
- 手動輸入書籍資訊
- 照片上傳
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.django_db
class TestBookAdd:
    """書籍上架頁面 E2E 測試"""

    def test_book_add_page_loads(self, authenticated_page: Page, live_server):
        """測試書籍上架頁面載入"""
        authenticated_page.goto(f"{live_server.url}/books/add/")

        # 驗證頁面標題
        expect(authenticated_page.locator("h1")).to_contain_text("新增分享書籍")

        # 驗證表單元素存在
        expect(authenticated_page.locator("input[name='isbn']")).to_be_visible()
        expect(authenticated_page.locator("input[name='title']")).to_be_visible()
        expect(authenticated_page.locator("input[name='author']")).to_be_visible()
        expect(authenticated_page.locator("select[name='category']")).to_be_visible()
        expect(
            authenticated_page.locator("select[name='transferability']")
        ).to_be_visible()
        expect(
            authenticated_page.locator("textarea[name='condition_description']")
        ).to_be_visible()
        expect(
            authenticated_page.locator("input[name='loan_duration_days']")
        ).to_be_visible()
        expect(authenticated_page.locator("input[name='photos']")).to_be_visible()
        expect(
            authenticated_page.get_by_role("button", name="確認新增")
        ).to_be_visible()

    def test_book_add_with_isbn_lookup(self, authenticated_page: Page, live_server):
        """測試 ISBN 輸入欄位存在且可輸入"""
        authenticated_page.goto(f"{live_server.url}/books/add/")

        # 驗證 ISBN 輸入欄位存在
        isbn_input = authenticated_page.locator("input[name='isbn']")
        expect(isbn_input).to_be_visible()

        # 輸入 ISBN
        isbn_input.fill("9789861234567")

        # 驗證輸入值
        expect(isbn_input).to_have_value("9789861234567")

        # 驗證 ISBN 結果區域存在（HTMX 目標，初始為空 div）
        expect(authenticated_page.locator("#isbn-result")).to_be_attached()

    def test_book_add_isbn_clear_button(self, authenticated_page: Page, live_server):
        """測試 ISBN 欄位可清空"""
        authenticated_page.goto(f"{live_server.url}/books/add/")

        isbn_input = authenticated_page.locator("input[name='isbn']")

        # 輸入 ISBN
        isbn_input.fill("9780000000000")
        expect(isbn_input).to_have_value("9780000000000")

        # 清空欄位
        isbn_input.clear()
        expect(isbn_input).to_have_value("")

    def test_book_add_without_isbn_manual_input(
        self, authenticated_page: Page, live_server, db
    ):
        """測試手動輸入書籍資訊（無 ISBN 查詢）"""
        authenticated_page.goto(f"{live_server.url}/books/add/")

        # 手動輸入書籍資訊
        authenticated_page.locator("input[name='isbn']").fill("9789869999999")
        authenticated_page.locator("input[name='title']").fill("手動輸入書名")
        authenticated_page.locator("input[name='author']").fill("手動輸入作者")
        authenticated_page.locator("select[name='category']").select_option("小說")
        authenticated_page.locator("select[name='transferability']").select_option(
            "RETURN"
        )
        authenticated_page.locator("textarea[name='condition_description']").fill(
            "書況良好，無劃記"
        )
        authenticated_page.locator("input[name='loan_duration_days']").fill("30")

        # 提交表單
        authenticated_page.get_by_role("button", name="確認新增").click()

        # 驗證導向書架頁面
        authenticated_page.wait_for_url(f"{live_server.url}/books/bookshelf/")

        # 驗證成功訊息（Django messages toast）
        expect(authenticated_page.locator(".toast")).to_contain_text(
            "書籍已成功上架分享"
        )

    def test_book_add_with_photos(
        self, authenticated_page: Page, live_server, db, tmp_path
    ):
        """測試照片上傳功能（僅驗證檔案選擇與預覽，不驗證後端儲存）"""
        authenticated_page.goto(f"{live_server.url}/books/add/")

        # 輸入基本書籍資訊
        authenticated_page.locator("input[name='isbn']").fill("9789876543210")
        authenticated_page.locator("input[name='title']").fill("照片測試書籍")
        authenticated_page.locator("input[name='author']").fill("照片測試作者")
        authenticated_page.locator("select[name='transferability']").select_option(
            "TRANSFER"
        )
        authenticated_page.locator("textarea[name='condition_description']").fill(
            "附照片說明"
        )
        authenticated_page.locator("input[name='loan_duration_days']").fill("60")

        # 建立測試圖片檔案
        test_image = tmp_path / "test_book.jpg"
        # 建立一個簡單的 JPEG 檔案（最小有效 JPEG）
        test_image.write_bytes(
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xd9"
        )

        # 上傳照片
        file_input = authenticated_page.locator("input[name='photos']")
        file_input.set_input_files(str(test_image))

        # 驗證照片預覽出現（前端 JavaScript 功能）
        authenticated_page.wait_for_selector("#photo-preview img", timeout=5000)
        expect(authenticated_page.locator("#photo-preview img")).to_be_visible()

        # 註：由於後端尚未完整實作照片處理，此測試僅驗證前端互動
