import uuid

import pytest
from django.db import IntegrityError

from deals.models import Deal, DealMessage, LoanExtension, Notification, Rating
from tests.factories import (
    DealFactory,
    DealMessageFactory,
    LoanExtensionFactory,
    NotificationFactory,
    RatingFactory,
    SharedBookFactory,
)


pytestmark = pytest.mark.django_db


class TestDeal:
    def test_create(self):
        deal = DealFactory()
        assert deal.pk is not None
        assert isinstance(deal.pk, uuid.UUID)
        assert deal.created_at is not None
        assert deal.updated_at is not None

    def test_deal_type_choices(self):
        assert Deal.DealType.LOAN == "LN"
        assert Deal.DealType.RESTORE == "RS"
        assert Deal.DealType.TRANSFER == "TF"
        assert Deal.DealType.REGRESS == "RG"
        assert Deal.DealType.EXCEPT == "EX"

    def test_status_choices(self):
        assert Deal.Status.REQUESTED == "Q"
        assert Deal.Status.RESPONDED == "P"
        assert Deal.Status.MEETED == "M"
        assert Deal.Status.DONE == "D"
        assert Deal.Status.CANCELLED == "X"

    def test_default_status(self):
        deal = DealFactory()
        assert deal.status == Deal.Status.REQUESTED

    def test_str(self):
        deal = DealFactory(deal_type=Deal.DealType.LOAN)
        result = str(deal)
        assert "借用交易" in result

    def test_previous_book_status(self):
        book = SharedBookFactory(status="T")
        deal = DealFactory(shared_book=book, previous_book_status="T")
        assert deal.previous_book_status == "T"

    def test_due_date_nullable(self):
        deal = DealFactory()
        assert deal.due_date is None

    def test_rated_defaults(self):
        deal = DealFactory()
        assert deal.applicant_rated is False
        assert deal.responder_rated is False

    def test_db_table(self):
        assert Deal._meta.db_table == "exbook_deal"

    def test_book_set_nullable(self):
        deal = DealFactory(book_set=None)
        assert deal.book_set is None

    def test_resolve_as_exception_transitions(self):
        """測試 resolve_as_exception 狀態流轉。"""
        # From REQUESTED
        deal = DealFactory(status=Deal.Status.REQUESTED)
        deal.resolve_as_exception()
        assert deal.status == Deal.Status.DONE

        # From RESPONDED
        deal = DealFactory(status=Deal.Status.RESPONDED)
        deal.resolve_as_exception()
        assert deal.status == Deal.Status.DONE

        # From MEETED
        deal = DealFactory(status=Deal.Status.MEETED)
        deal.resolve_as_exception()
        assert deal.status == Deal.Status.DONE

        # From DONE (Should fail)
        deal = DealFactory(status=Deal.Status.DONE)
        with pytest.raises(Exception):
            deal.resolve_as_exception()


class TestDealMessage:
    def test_create(self):
        msg = DealMessageFactory()
        assert msg.pk is not None
        assert msg.content
        assert msg.created_at is not None

    def test_no_updated_at(self):
        """DealMessage uses BaseModel — no updated_at."""
        assert "updated_at" not in [f.name for f in DealMessage._meta.get_fields()]

    def test_ordering(self):
        assert DealMessage._meta.ordering == ["created_at"]

    def test_str(self):
        msg = DealMessageFactory()
        result = str(msg)
        assert "@" in result

    def test_db_table(self):
        assert DealMessage._meta.db_table == "exbook_deal_message"

    def test_deal_cascade_delete(self):
        msg = DealMessageFactory()
        deal = msg.deal
        deal.delete()
        assert not DealMessage.objects.filter(pk=msg.pk).exists()


class TestRating:
    def test_create(self):
        rating = RatingFactory()
        assert rating.pk is not None
        assert 1 <= rating.friendliness_score <= 5
        assert 1 <= rating.punctuality_score <= 5
        assert 1 <= rating.accuracy_score <= 5

    def test_unique_deal_rater(self):
        deal = DealFactory()
        rater = deal.applicant
        ratee = deal.responder
        RatingFactory(deal=deal, rater=rater, ratee=ratee)
        with pytest.raises(IntegrityError):
            RatingFactory(deal=deal, rater=rater, ratee=ratee)

    def test_average_score(self):
        rating = RatingFactory(
            friendliness_score=3,
            punctuality_score=4,
            accuracy_score=5,
        )
        assert rating.average_score == 4.0

    def test_str(self):
        rating = RatingFactory()
        result = str(rating)
        assert "→" in result

    def test_db_table(self):
        assert Rating._meta.db_table == "exbook_rating"


class TestLoanExtension:
    def test_create(self):
        ext = LoanExtensionFactory()
        assert ext.pk is not None
        assert ext.extra_days == 14
        assert ext.status == LoanExtension.Status.PENDING

    def test_status_choices(self):
        assert LoanExtension.Status.PENDING == "PENDING"
        assert LoanExtension.Status.APPROVED == "APPROVED"
        assert LoanExtension.Status.REJECTED == "REJECTED"

    def test_reviewer_fields_nullable(self):
        ext = LoanExtensionFactory()
        assert ext.approved_by is None

    def test_ordering(self):
        assert LoanExtension._meta.ordering == ["-created_at"]

    def test_str(self):
        ext = LoanExtensionFactory(extra_days=14)
        result = str(ext)
        assert "延長 14 天" in result

    def test_db_table(self):
        assert LoanExtension._meta.db_table == "exbook_loan_extension"

    def test_deal_cascade_delete(self):
        ext = LoanExtensionFactory()
        deal = ext.deal
        deal.delete()
        assert not LoanExtension.objects.filter(pk=ext.pk).exists()


class TestNotification:
    def test_create(self):
        notif = NotificationFactory()
        assert notif.pk is not None
        assert notif.is_read is False

    def test_notification_type_choices(self):
        types = Notification.NotificationType
        # 15 choices defined in models/notification.py
        assert len(types.choices) == 15

    def test_default_is_read(self):
        notif = NotificationFactory()
        assert notif.is_read is False

    def test_deal_nullable(self):
        notif = NotificationFactory(deal=None)
        assert notif.deal is None

    def test_shared_book_nullable(self):
        notif = NotificationFactory(shared_book=None)
        assert notif.shared_book is None

    def test_ordering(self):
        assert Notification._meta.ordering == ["-created_at"]

    def test_str(self):
        notif = NotificationFactory()
        result = str(notif)
        assert "-" in result

    def test_db_table(self):
        assert Notification._meta.db_table == "exbook_notification"

    def test_recipient_cascade_delete(self):
        notif = NotificationFactory()
        user = notif.recipient
        user.delete()
        assert not Notification.objects.filter(pk=notif.pk).exists()
