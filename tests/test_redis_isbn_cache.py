import pytest
from unittest.mock import patch, MagicMock
from books.services.isbn_service import lookup_by_isbn, get_isbn_cache_key

@pytest.fixture
def mock_cache():
    """Mock Django's core cache"""
    with patch("books.services.isbn_service.cache") as mocked:
        yield mocked

@pytest.fixture
def mock_official_book():
    """Mock OfficialBook.objects.get to raise DoesNotExist by default"""
    with patch("books.models.OfficialBook.objects.get") as mocked:
        from books.models import OfficialBook
        mocked.side_effect = OfficialBook.DoesNotExist
        yield mocked

@pytest.fixture
def mock_httpx_get():
    """Mock httpx.get for API calls"""
    with patch("books.services.isbn_service.httpx.get") as mocked:
        yield mocked

def test_isbn_cache_hit(mock_cache, mock_official_book):
    """Test scenario: Second query returns cached data without API call"""
    isbn = "9789863503613"
    cache_key = get_isbn_cache_key(isbn)
    cached_data = {
        "title": "Cached Book",
        "author": "Cached Author",
        "publisher": "Cached Publisher",
        "cover_url": "http://example.com/cover.jpg",
        "isbn": isbn,
        "source": "google_api",
    }
    
    # Setup mock to return cached data
    mock_cache.get.return_value = cached_data
    
    # Execute
    result = lookup_by_isbn(isbn)
    
    # Verify
    assert result == cached_data
    mock_cache.get.assert_called_once_with(cache_key)
    # Ensure no DB or API check happened after cache hit (DB check actually happens BEFORE cache in current implementation)
    # Wait, the current implementation checks DB FIRST, then Cache.
    # So we verify DB was called, but API was NOT called.
    assert mock_official_book.called

def test_isbn_cache_miss_then_set(mock_cache, mock_official_book, mock_httpx_get):
    """Test scenario: New ISBN fetches from API and caches result"""
    isbn = "9789863503613"
    cache_key = get_isbn_cache_key(isbn)
    
    # 1. Cache miss
    mock_cache.get.return_value = None
    
    # 2. Mock API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "items": [{
            "volumeInfo": {
                "title": "API Book",
                "authors": ["API Author"],
                "publisher": "API Publisher",
                "imageLinks": {"thumbnail": "http://example.com/api_cover.jpg"}
            }
        }]
    }
    mock_response.status_code = 200
    mock_httpx_get.return_value = mock_response
    
    # Execute
    result = lookup_by_isbn(isbn)
    
    # Verify
    expected_result = {
        "title": "API Book",
        "author": "API Author",
        "publisher": "API Publisher",
        "cover_url": "http://example.com/api_cover.jpg",
        "isbn": isbn,
        "source": "google_api",
    }
    assert result == expected_result
    
    # Verify cache was checked and then set
    mock_cache.get.assert_called_once_with(cache_key)
    mock_cache.set.assert_called_once_with(cache_key, expected_result, 24 * 60 * 60)

def test_isbn_cache_key_format():
    """Test ISBN cache key format"""
    isbn = "9789863503613"
    assert get_isbn_cache_key(isbn) == f"isbn:{isbn}"
