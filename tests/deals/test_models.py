import uuid

import pytest
from django.db import IntegrityError, transaction

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

    def test_extra_days_help_text_derived_from_constants(self):
        field = LoanExtension._meta.get_field("extra_days")
        text = str(field.help_text)
        assert str(LoanExtension.MIN_EXTRA_DAYS) in text
        assert str(LoanExtension.MAX_EXTRA_DAYS) in text

    def test_db_table(self):
        assert LoanExtension._meta.db_table == "exbook_loan_extension"

    def test_deal_cascade_delete(self):
        ext = LoanExtensionFactory()
        deal = ext.deal
        deal.delete()
        assert not LoanExtension.objects.filter(pk=ext.pk).exists()

    # ------------------------------------------------------------------
    # #21: DB 層防線——(deal, is_pending) unique constraint
    # ------------------------------------------------------------------

    def test_is_pending_generated_value(self):
        """generated column：PENDING 時為 1，離開 PENDING 後為 NULL。"""
        ext = LoanExtensionFactory()
        # generated value 由 DB 端計算，factory 建立後 in-memory 為 None，需刷入
        ext.refresh_from_db()
        assert ext.is_pending == 1
        ext.reject()
        ext.save()
        ext.refresh_from_db()
        assert ext.is_pending is None

    def test_db_rejects_second_pending_for_same_deal(self):
        """第二個寫入者（绕过 service）直接 INSERT 同 deal 的 PENDING 行，
        DB 層拒絕，不再依賴 app-level guard 的隱性 invariant。"""
        deal = DealFactory()
        LoanExtensionFactory(deal=deal)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                LoanExtensionFactory(deal=deal)

    def test_db_rejects_queryset_update_flip_to_pending(self):
        """queryset.update 把非 PENDING 行翻回 PENDING（第二寫入者的另一形態），
        同樣撞 constraint。"""
        deal = DealFactory()
        first = LoanExtensionFactory(deal=deal)
        first.reject()
        first.save()
        LoanExtensionFactory(deal=deal)  # slot 重新佔用
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                LoanExtension.objects.filter(pk=first.pk).update(
                    status=LoanExtension.Status.PENDING
                )

    def test_db_allows_re_request_after_review(self):
        """非 PENDING 行 is_pending=NULL，unique 允許多個 NULL——
        審核完成後同一 deal 可以再申請。"""
        deal = DealFactory()
        first = LoanExtensionFactory(deal=deal)
        first.reject()
        first.save()
        second = LoanExtensionFactory(deal=deal)
        assert second.pk is not None


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
