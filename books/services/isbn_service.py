import re
import logging
from typing import Optional, Dict, Any

import httpx
from django.core.cache import cache

# 設定 logger
logger = logging.getLogger(__name__)

# Google Books API 基本設定
GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"
CACHE_TIMEOUT = 24 * 60 * 60  # 24 hours in seconds


def normalize_isbn(isbn: str) -> Optional[str]:
    """
    正規化 ISBN 格式，支援 ISBN-10 和 ISBN-13
    移除所有非數字和 X 的字元，並驗證基本格式

    Args:
        isbn: 原始 ISBN 字串

    Returns:
        正規化後的 ISBN，若格式無效則返回 None
    """
    # 移除所有空白和連字符
    cleaned = re.sub(r"[^\dX]", "", isbn.upper())

    # 驗證長度
    if len(cleaned) == 10:
        # ISBN-10: 檢查最後一位是否為數字或 X
        if not re.match(r"^\d{9}[\dX]$", cleaned):
            return None
        return cleaned
    elif len(cleaned) == 13:
        # ISBN-13: 檢查是否全為數字
        if not cleaned.isdigit():
            return None
        return cleaned
    else:
        return None


def lookup_by_isbn(isbn: str) -> Optional[Dict[str, Any]]:
    """
    透過 Google Books API 查詢 ISBN 對應的書籍資訊

    Args:
        isbn: ISBN-10 或 ISBN-13 字串

    Returns:
        包含書籍資訊的字典，若查詢失敗或無結果則返回 None
        格式: {
            'title': str,
            'author': str,
            'publisher': str,
            'cover_url': str,
            'isbn': str
        }
    """
    # 正規化 ISBN
    normalized_isbn = normalize_isbn(isbn)
    if not normalized_isbn:
        logger.warning(f"Invalid ISBN format: {isbn}")
        return None

    # 檢查快取
    cache_key = f"isbn_lookup_{normalized_isbn}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    # 準備 API 請求
    params = {
        "q": f"isbn:{normalized_isbn}",
    }

    try:
        # 發送請求到 Google Books API
        response = httpx.get(GOOGLE_BOOKS_API_URL, params=params, timeout=10)
        response.raise_for_status()

        # 解析回應
        data = response.json()

        # 檢查是否有結果
        if not data.get("items"):
            logger.info(f"No book found for ISBN: {normalized_isbn}")
            cache.set(cache_key, None, CACHE_TIMEOUT)
            return None

        # 提取第一筆結果的書籍資訊
        book_info = data["items"][0]["volumeInfo"]

        # 準備回傳資料
        result = {
            "title": book_info.get("title", ""),
            "author": ", ".join(book_info.get("authors", [])),
            "publisher": book_info.get("publisher", ""),
            "cover_url": book_info.get("imageLinks", {}).get("thumbnail", ""),
            "isbn": normalized_isbn,
        }

        # 快取結果
        cache.set(cache_key, result, CACHE_TIMEOUT)
        return result

    except httpx.TimeoutException:
        logger.error(
            f"Timeout when querying Google Books API for ISBN: {normalized_isbn}"
        )
        return None
    except httpx.RequestError as e:
        logger.error(
            f"Network error when querying Google Books API for ISBN {normalized_isbn}: {e}"
        )
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error when querying Google Books API for ISBN {normalized_isbn}: {e}"
        )
        return None
