"""L-6：ISBN 查詢端點（會呼叫外部 Google Books）需登入才能使用。"""

from unittest.mock import patch

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_isbn_lookup_rejects_anonymous(client):
    with patch("books.views.lookup_by_isbn") as mock_lookup:
        resp = client.get(reverse("books:isbn_lookup"), {"isbn": "9789861234567"})
    assert resp.status_code == 302
    assert "/accounts/login/" in resp["Location"]
    mock_lookup.assert_not_called()


@pytest.mark.django_db
def test_isbn_lookup_works_for_logged_in_user(authenticated_client):
    with patch("books.views.lookup_by_isbn", return_value=None) as mock_lookup:
        resp = authenticated_client.get(
            reverse("books:isbn_lookup"), {"isbn": "9789861234567"}
        )
    assert resp.status_code == 200
    mock_lookup.assert_called_once_with("9789861234567")
