"""
Root conftest — pytest-django auto-discovers this.
"""

import pytest

from tests.factories import (
    BookSetFactory,
    OfficialBookFactory,
    SharedBookFactory,
    UserFactory,
)


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
        status='T',
        transferability='RETURN',
    )
    # keeper defaults to owner in factory
    return book


@pytest.fixture
def transfer_book(db):
    """A SharedBook in TRANSFERABLE status, TRANSFER transferability."""
    return SharedBookFactory(
        status='T',
        transferability='TRANSFER',
    )


@pytest.fixture
def book_set(db):
    return BookSetFactory()
