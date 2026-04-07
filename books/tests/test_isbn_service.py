"""
ISBN 服務測試 — 驗證 Google Books API 查詢功能。
"""

from unittest.mock import patch, MagicMock

from books.services.isbn_service import (
    normalize_isbn,
    lookup_by_isbn,
)


class TestNormalizeISBN:
    """測試 ISBN 正規化功能。"""

    def test_normalize_isbn_13(self):
        """測試 ISBN-13 正規化。"""
        assert normalize_isbn("978-986-123-456-7") == "9789861234567"
        assert normalize_isbn("9789861234567") == "9789861234567"

    def test_normalize_isbn_10(self):
        """測試 ISBN-10 正規化。"""
        assert normalize_isbn("986-123-456-X") == "986123456X"
        assert normalize_isbn("9861234567") == "9861234567"

    def test_normalize_isbn_with_spaces(self):
        """測試包含空格的 ISBN。"""
        assert normalize_isbn("978 986 123 456 7") == "9789861234567"

    def test_normalize_invalid_isbn(self):
        """測試無效的 ISBN 格式。"""
        assert normalize_isbn("123") is None
        assert normalize_isbn("") is None
        assert normalize_isbn("abcdefghijklm") is None


class TestLookupByISBN:
    """測試 ISBN 查詢功能。"""

    @patch("books.services.isbn_service.OfficialBook.objects.get")
    @patch("books.services.isbn_service.cache")
    @patch("books.services.isbn_service.httpx.get")
    def test_lookup_success(self, mock_get, mock_cache, mock_db_get):
        """測試成功查詢書籍（資料庫無資料，從 API 查詢）。"""
        # 設定 mock：資料庫查無此書
        from django.core.exceptions import ObjectDoesNotExist

        mock_db_get.side_effect = ObjectDoesNotExist("ISBN not found")

        # 設定 mock cache
        mock_cache.get.return_value = None
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "volumeInfo": {
                        "title": "測試書籍",
                        "authors": ["作者A", "作者B"],
                        "publisher": "測試出版社",
                        "imageLinks": {"thumbnail": "http://example.com/cover.jpg"},
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # 執行查詢
        result = lookup_by_isbn("9789861234567")

        # 驗證結果
        assert result is not None
        assert result["title"] == "測試書籍"
        assert result["author"] == "作者A, 作者B"
        assert result["publisher"] == "測試出版社"
        assert result["cover_url"] == "http://example.com/cover.jpg"
        assert result["isbn"] == "9789861234567"
        assert result["source"] == "google_api"

    @patch("books.services.isbn_service.OfficialBook.objects.get")
    def test_lookup_from_database(self, mock_db_get):
        """測試從資料庫查詢書籍。"""
        # 設定 mock：資料庫有此書
        mock_book = MagicMock()
        mock_book.title = "資料庫書籍"
        mock_book.author = "資料庫作者"
        mock_book.publisher = "資料庫出版社"
        mock_book.cover_image.url = "http://example.com/db_cover.jpg"
        mock_db_get.return_value = mock_book

        # 執行查詢
        result = lookup_by_isbn("9789861234567")

        # 驗證結果
        assert result is not None
        assert result["title"] == "資料庫書籍"
        assert result["author"] == "資料庫作者"
        assert result["publisher"] == "資料庫出版社"
        assert result["cover_url"] == "http://example.com/db_cover.jpg"
        assert result["isbn"] == "9789861234567"
        assert result["source"] == "database"

    @patch("books.services.isbn_service.OfficialBook.objects.get")
    @patch("books.services.isbn_service.cache")
    @patch("books.services.isbn_service.httpx.get")
    def test_lookup_no_results(self, mock_get, mock_cache, mock_db_get):
        """測試查無書籍。"""
        from django.core.exceptions import ObjectDoesNotExist

        mock_db_get.side_effect = ObjectDoesNotExist("ISBN not found")
        mock_cache.get.return_value = None
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = lookup_by_isbn("9999999999999")
        assert result is None

    @patch("books.services.isbn_service.OfficialBook.objects.get")
    @patch("books.services.isbn_service.cache")
    def test_lookup_cached_result(self, mock_cache, mock_db_get):
        """測試快取命中。"""
        from django.core.exceptions import ObjectDoesNotExist

        mock_db_get.side_effect = ObjectDoesNotExist("ISBN not found")

        cached_data = {
            "title": "快取書籍",
            "author": "快取作者",
            "publisher": "快取出版社",
            "cover_url": "http://example.com/cached.jpg",
            "isbn": "9789861234567",
        }
        mock_cache.get.return_value = cached_data

        result = lookup_by_isbn("9789861234567")
        assert result == cached_data

    @patch("books.services.isbn_service.OfficialBook.objects.get")
    @patch("books.services.isbn_service.cache")
    @patch("books.services.isbn_service.httpx.get")
    def test_lookup_timeout(self, mock_get, mock_cache, mock_db_get):
        """測試 API 超時。"""
        from django.core.exceptions import ObjectDoesNotExist
        from httpx import TimeoutException

        mock_db_get.side_effect = ObjectDoesNotExist("ISBN not found")
        mock_cache.get.return_value = None
        mock_get.side_effect = TimeoutException("Timeout")

        result = lookup_by_isbn("9789861234567")
        assert result == {"error": "timeout"}

    @patch("books.services.isbn_service.OfficialBook.objects.get")
    @patch("books.services.isbn_service.cache")
    @patch("books.services.isbn_service.httpx.get")
    def test_lookup_request_error(self, mock_get, mock_cache, mock_db_get):
        """測試網路請求錯誤。"""
        from django.core.exceptions import ObjectDoesNotExist
        from httpx import RequestError

        mock_db_get.side_effect = ObjectDoesNotExist("ISBN not found")
        mock_cache.get.return_value = None
        mock_get.side_effect = RequestError("Network error")

        result = lookup_by_isbn("9789861234567")
        assert result == {"error": "network_error"}

    @patch("books.services.isbn_service.OfficialBook.objects.get")
    @patch("books.services.isbn_service.cache")
    @patch("books.services.isbn_service.httpx.get")
    def test_lookup_unexpected_error(self, mock_get, mock_cache, mock_db_get):
        """測試未預期的錯誤。"""
        from django.core.exceptions import ObjectDoesNotExist

        mock_db_get.side_effect = ObjectDoesNotExist("ISBN not found")
        mock_cache.get.return_value = None
        mock_get.side_effect = Exception("Unexpected error")

        result = lookup_by_isbn("9789861234567")
        assert result == {"error": "unknown"}

    def test_lookup_invalid_isbn(self):
        """測試無效 ISBN。"""
        result = lookup_by_isbn("invalid")
        assert result is None

    @patch("books.services.isbn_service.OfficialBook.objects.get")
    @patch("books.services.isbn_service.cache")
    @patch("books.services.isbn_service.httpx.get")
    def test_lookup_missing_fields(self, mock_get, mock_cache, mock_db_get):
        """測試缺少某些欄位的回應。"""
        from django.core.exceptions import ObjectDoesNotExist

        mock_db_get.side_effect = ObjectDoesNotExist("ISBN not found")
        mock_cache.get.return_value = None
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "volumeInfo": {
                        "title": "缺欄位書籍",
                        # 缺少 authors, publisher, imageLinks
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = lookup_by_isbn("9789861234567")

        assert result is not None
        assert result["title"] == "缺欄位書籍"
        assert result["author"] == ""
        assert result["publisher"] == ""
        assert result["cover_url"] == ""
        assert result["isbn"] == "9789861234567"
