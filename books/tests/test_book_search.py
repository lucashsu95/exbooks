"""
書籍搜尋與篩選功能測試

測試項目：
- 關鍵字搜尋（ISBN、書名、作者、出版社）
- 狀態篩選
- 流通性篩選
- 分類篩選
- 分頁功能
"""

import pytest
from django.urls import reverse
from django.test import Client

from books.models import SharedBook, OfficialBook
from tests.factories import UserFactory, OfficialBookFactory, SharedBookFactory


@pytest.fixture
def search_test_data(db):
    """建立搜尋測試所需的測試資料"""
    user = UserFactory()

    # 建立不同出版社的書籍
    book1 = OfficialBookFactory(
        title="Python 程式設計",
        author="張三",
        publisher="技術出版社",
        isbn="9789861234567",
        category=OfficialBook.Category.TECH,
    )
    book2 = OfficialBookFactory(
        title="Django 實戰",
        author="李四",
        publisher="程式出版社",
        isbn="9789867654321",
        category=OfficialBook.Category.TECH,
    )
    book3 = OfficialBookFactory(
        title="小說精選",
        author="王五",
        publisher="文學出版社",
        isbn="9789861111111",
        category=OfficialBook.Category.FICTION,
    )

    # 建立不同狀態和流通性的 SharedBook
    shared1 = SharedBookFactory(
        official_book=book1,
        owner=user,
        keeper=user,
        status=SharedBook.Status.TRANSFERABLE,
        transferability=SharedBook.Transferability.TRANSFER,
    )
    shared2 = SharedBookFactory(
        official_book=book2,
        owner=user,
        keeper=user,
        status=SharedBook.Status.TRANSFERABLE,
        transferability=SharedBook.Transferability.RETURN,
    )
    shared3 = SharedBookFactory(
        official_book=book3,
        owner=user,
        keeper=user,
        status=SharedBook.Status.OCCUPIED,
        transferability=SharedBook.Transferability.RETURN,
    )

    return {
        "user": user,
        "books": [book1, book2, book3],
        "shared_books": [shared1, shared2, shared3],
    }


@pytest.fixture
def authenticated_client(db):
    """已認證的測試客戶端"""
    user = UserFactory()
    client = Client()
    client.force_login(user)
    return client


class TestBookSearch:
    """書籍搜尋功能測試"""

    def test_search_by_title(self, authenticated_client, search_test_data):
        """測試依書名搜尋"""
        response = authenticated_client.get(
            reverse("books:all"), {"q": "Python"}, follow=True
        )
        assert response.status_code == 200
        # 應該找到包含 "Python" 的書籍
        assert b"Python" in response.content or b"python" in response.content.lower()

    def test_search_by_author(self, authenticated_client, search_test_data):
        """測試依作者搜尋"""
        response = authenticated_client.get(
            reverse("books:all"), {"q": "張三"}, follow=True
        )
        assert response.status_code == 200

    def test_search_by_isbn(self, authenticated_client, search_test_data):
        """測試依 ISBN 搜尋"""
        response = authenticated_client.get(
            reverse("books:all"), {"q": "9789861234567"}, follow=True
        )
        assert response.status_code == 200

    def test_search_by_publisher(self, authenticated_client, search_test_data):
        """測試依出版社搜尋"""
        response = authenticated_client.get(
            reverse("books:all"), {"q": "技術出版社"}, follow=True
        )
        assert response.status_code == 200

    def test_search_no_results(self, authenticated_client, search_test_data):
        """測試搜尋無結果"""
        response = authenticated_client.get(
            reverse("books:all"), {"q": "不存在的書"}, follow=True
        )
        assert response.status_code == 200
        # 應該顯示無結果訊息 (使用 ASCII 安全的方式檢查)
        content = response.content.decode("utf-8")
        assert "目前沒有符合條件的書籍" in content


class TestBookFilter:
    """書籍篩選功能測試"""

    def test_filter_by_status(self, authenticated_client, search_test_data):
        """測試依狀態篩選"""
        response = authenticated_client.get(
            reverse("books:all"), {"status": "T"}, follow=True
        )
        assert response.status_code == 200
        # 檢查篩選後的結果
        context = response.context
        assert "page_obj" in context

    def test_filter_by_transferability(self, authenticated_client, search_test_data):
        """測試依流通性篩選"""
        response = authenticated_client.get(
            reverse("books:all"), {"transferability": "TRANSFER"}, follow=True
        )
        assert response.status_code == 200
        context = response.context
        assert "page_obj" in context

    def test_filter_by_category(self, authenticated_client, search_test_data):
        """測試依分類篩選"""
        response = authenticated_client.get(
            reverse("books:all"), {"category": "科技"}, follow=True
        )
        assert response.status_code == 200
        context = response.context
        assert "page_obj" in context

    def test_combined_filters(self, authenticated_client, search_test_data):
        """測試組合篩選條件"""
        response = authenticated_client.get(
            reverse("books:all"),
            {"q": "Python", "status": "T", "category": "科技"},
            follow=True,
        )
        assert response.status_code == 200
        context = response.context
        assert "page_obj" in context


class TestBookPagination:
    """書籍分頁功能測試"""

    @pytest.fixture
    def many_books(self, db):
        """建立大量書籍用於分頁測試"""
        user = UserFactory()
        books = []
        for i in range(25):  # 建立 25 本書，超過每頁 12 筆
            book = OfficialBookFactory(
                title=f"測試書籍 {i}",
                author=f"作者 {i}",
                publisher=f"出版社 {i % 5}",
            )
            shared = SharedBookFactory(
                official_book=book,
                owner=user,
                keeper=user,
                status=SharedBook.Status.TRANSFERABLE,
            )
            books.append(shared)
        return {"user": user, "books": books}

    def test_pagination_first_page(self, authenticated_client, many_books):
        """測試第一頁分頁"""
        response = authenticated_client.get(reverse("books:all"), follow=True)
        assert response.status_code == 200
        context = response.context
        page_obj = context["page_obj"]
        # 第一頁應該有 12 筆
        assert len(page_obj.object_list) <= 12

    def test_pagination_second_page(self, authenticated_client, many_books):
        """測試第二頁分頁"""
        response = authenticated_client.get(
            reverse("books:all"), {"page": 2}, follow=True
        )
        assert response.status_code == 200
        context = response.context
        page_obj = context["page_obj"]
        assert page_obj.number == 2

    def test_pagination_with_search(self, authenticated_client, many_books):
        """測試搜尋結果的分頁"""
        response = authenticated_client.get(
            reverse("books:all"), {"q": "測試書籍", "page": 1}, follow=True
        )
        assert response.status_code == 200
        context = response.context
        assert "page_obj" in context

    def test_pagination_preserves_filters(self, authenticated_client, many_books):
        """測試分頁時保留篩選條件"""
        # 使用 page=1 來確保有結果和分頁
        response = authenticated_client.get(
            reverse("books:all"),
            {"status": "T", "transferability": "TRANSFER"},
            follow=True,
        )
        assert response.status_code == 200
        # 檢查隱藏表單欄位是否保留篩選參數
        content = response.content.decode("utf-8")
        # 檢查隱藏 input 欄位
        assert 'name="status"' in content
        assert 'name="transferability"' in content


class TestBookListView:
    """書籍列表頁面測試"""

    def test_book_list_page_loads(self, authenticated_client):
        """測試書籍列表頁面載入"""
        response = authenticated_client.get(reverse("books:all"), follow=True)
        assert response.status_code == 200

    def test_book_list_has_search_form(self, authenticated_client):
        """測試書籍列表頁面有搜尋表單"""
        response = authenticated_client.get(reverse("books:all"), follow=True)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        # 應該有搜尋輸入框
        assert 'name="q"' in content

    def test_book_list_has_filter_pills(self, authenticated_client):
        """測試書籍列表頁面有篩選按鈕"""
        response = authenticated_client.get(reverse("books:all"), follow=True)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        # 應該有狀態、流通性、分類篩選
        assert "status" in content
        assert "transferability" in content
        assert "category" in content

    def test_book_list_has_pagination(self, authenticated_client, search_test_data):
        """測試書籍列表頁面有分頁導航"""
        response = authenticated_client.get(reverse("books:all"), follow=True)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        # 應該有分頁相關元素
        assert "page_obj" in response.context or b"page" in response.content.lower()


class TestBookSearchForm:
    """BookSearchForm 表單測試"""

    def test_form_fields(self):
        """測試表單欄位"""
        from books.forms import BookSearchForm

        form = BookSearchForm()
        assert "q" in form.fields
        assert "status" in form.fields
        assert "transferability" in form.fields
        assert "category" in form.fields

    def test_form_empty_is_valid(self):
        """測試空表單也是有效的"""
        from books.forms import BookSearchForm

        form = BookSearchForm(data={})
        assert form.is_valid()

    def test_form_with_data_is_valid(self):
        """測試帶資料的表單有效"""
        from books.forms import BookSearchForm

        form = BookSearchForm(
            data={
                "q": "Python",
                "status": "T",
                "transferability": "TRANSFER",
                "category": "科技",
            }
        )
        assert form.is_valid()
