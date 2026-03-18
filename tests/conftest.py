"""
Tests conftest — pytest-django auto-discovers this.
"""

import os
import pytest
from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.contrib.sessions.backends.db import SessionStore

# Allow async unsafe operations for playwright compatibility
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

from tests.factories import (
    BookSetFactory,
    DealFactory,
    OfficialBookFactory,
    SharedBookFactory,
    UserFactory,
)


@pytest.fixture
def test_user(db):
    """Generic test user."""
    return UserFactory()


@pytest.fixture
def owner_user(db):
    """User who owns books."""
    return UserFactory(username="owner")


@pytest.fixture
def keeper_user(db):
    """User who currently keeps books."""
    return UserFactory(username="keeper")


@pytest.fixture
def reader_user(db):
    """User who reads/borrows books."""
    return UserFactory(username="reader")


@pytest.fixture
def authenticated_client(client, test_user):
    """Django test client with an authenticated user."""
    client.force_login(test_user)
    return client


@pytest.fixture
def authenticated_page(page, test_user, db):
    """Playwright page with an authenticated user session."""
    # Create a session for the user
    session = SessionStore()
    session[SESSION_KEY] = test_user.pk
    session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
    session[HASH_SESSION_KEY] = test_user.get_session_auth_hash()
    session.save()

    # Set the cookie in Playwright
    cookie = {
        "name": settings.SESSION_COOKIE_NAME,
        "value": session.session_key,
        "domain": "localhost",
        "path": "/",
    }
    page.context.add_cookies([cookie])
    return page


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def other_user(db):
    return UserFactory()


@pytest.fixture
def official_book(db):
    return OfficialBookFactory()


@pytest.fixture
def shared_book(db):
    """A SharedBook in TRANSFERABLE status, RETURN transferability, keeper=owner."""
    book = SharedBookFactory(
        status="T",
        transferability="RETURN",
    )
    # keeper defaults to owner in factory
    return book


@pytest.fixture
def transfer_book(db):
    """A SharedBook in TRANSFERABLE status, TRANSFER transferability."""
    return SharedBookFactory(
        status="T",
        transferability="TRANSFER",
    )


@pytest.fixture
def book_set(db):
    return BookSetFactory()


@pytest.fixture
def deal(db):
    """A Deal in REQUESTED status for testing."""
    return DealFactory(status="Q")


@pytest.fixture
def shared_book_factory(db):
    """Factory fixture for creating SharedBook instances."""
    return SharedBookFactory


@pytest.fixture
def deal_as_responder(db, test_user):
    """A Deal where test_user is the responder (can accept/reject)."""
    # Create a book owned by someone else
    book_owner = UserFactory()
    book = SharedBookFactory(owner=book_owner, keeper=book_owner, status="T")
    # Create deal where test_user is responder (book owner)
    return DealFactory(
        shared_book=book,
        responder=test_user,
        applicant=UserFactory(),
        status="Q",
    )


@pytest.fixture
def deal_as_applicant(db, test_user):
    """A Deal where test_user is the applicant (can cancel)."""
    book_owner = UserFactory()
    book = SharedBookFactory(owner=book_owner, keeper=book_owner, status="T")
    return DealFactory(
        shared_book=book,
        applicant=test_user,
        responder=book_owner,
        status="Q",
    )


@pytest.fixture
def deal_responded(db, test_user):
    """A Deal in RESPONDED status (ready for meeting)."""
    book_owner = UserFactory()
    book = SharedBookFactory(owner=book_owner, keeper=book_owner, status="T")
    return DealFactory(
        shared_book=book,
        applicant=test_user,
        responder=book_owner,
        status="P",  # RESPONDED - meeting pending
    )


@pytest.fixture
def deal_meeted(db, test_user):
    """A Deal in MEETED status (ready for rating)."""
    book_owner = UserFactory()
    book = SharedBookFactory(owner=book_owner, keeper=book_owner, status="T")
    return DealFactory(
        shared_book=book,
        applicant=test_user,
        responder=book_owner,
        status="M",  # MEETED - ready for rating
    )


@pytest.fixture
def deal_already_rated(db, test_user):
    """A Deal where test_user has already rated."""
    from tests.factories import RatingFactory

    book_owner = UserFactory()
    book = SharedBookFactory(owner=book_owner, keeper=book_owner, status="T")
    deal = DealFactory(
        shared_book=book,
        applicant=test_user,
        responder=book_owner,
        status="M",
        applicant_rated=True,
    )
    # Create the rating
    RatingFactory(deal=deal, rater=test_user, ratee=book_owner)
    return deal
