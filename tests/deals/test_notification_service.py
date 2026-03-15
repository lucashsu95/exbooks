import pytest

from deals.models import Notification
from deals.services.notification_service import (
    mark_all_as_read,
    mark_as_read,
    notify,
    notify_book_available,
    notify_book_due_soon,
    notify_book_overdue,
    notify_deal_cancelled,
    notify_deal_meeted,
    notify_deal_requested,
    notify_deal_responded,
    notify_extend_requested,
    notify_extend_result,
)
from tests.factories import (
    DealFactory,
    LoanExtensionFactory,
    NotificationFactory,
    SharedBookFactory,
    UserFactory,
)


pytestmark = pytest.mark.django_db


# ============================================================
# notify (統一入口)
# ============================================================
class TestNotify:
    def test_create_basic(self):
        user = UserFactory()
        notif = notify(
            recipient=user,
            notification_type=Notification.NotificationType.DEAL_REQUESTED,
            title="Test",
            message="Test message",
        )
        assert notif.recipient == user
        assert notif.title == "Test"
        assert notif.message == "Test message"
        assert notif.is_read is False

    def test_with_deal(self):
        deal = DealFactory()
        notif = notify(
            recipient=deal.applicant,
            notification_type=Notification.NotificationType.DEAL_REQUESTED,
            title="Test",
            deal=deal,
        )
        assert notif.deal == deal

    def test_with_shared_book(self):
        book = SharedBookFactory()
        user = UserFactory()
        notif = notify(
            recipient=user,
            notification_type=Notification.NotificationType.BOOK_AVAILABLE,
            title="Test",
            shared_book=book,
        )
        assert notif.shared_book == book


# ============================================================
# 交易通知
# ============================================================
class TestNotifyDealRequested:
    def test_notifies_responder(self):
        deal = DealFactory()
        notify_deal_requested(deal)
        assert (
            Notification.objects.filter(
                recipient=deal.responder,
                notification_type="DEAL_REQUESTED",
            ).count()
            == 1
        )


class TestNotifyDealResponded:
    def test_notifies_applicant(self):
        deal = DealFactory()
        notify_deal_responded(deal)
        assert (
            Notification.objects.filter(
                recipient=deal.applicant,
                notification_type="DEAL_RESPONDED",
            ).count()
            == 1
        )


class TestNotifyDealCancelled:
    def test_by_applicant_notifies_responder(self):
        deal = DealFactory()
        notify_deal_cancelled(deal, deal.applicant)
        assert (
            Notification.objects.filter(
                recipient=deal.responder,
                notification_type="DEAL_CANCELLED",
            ).count()
            == 1
        )

    def test_by_responder_notifies_applicant(self):
        deal = DealFactory()
        notify_deal_cancelled(deal, deal.responder)
        assert (
            Notification.objects.filter(
                recipient=deal.applicant,
                notification_type="DEAL_CANCELLED",
            ).count()
            == 1
        )


class TestNotifyDealMeeted:
    def test_notifies_both_parties(self):
        deal = DealFactory()
        notify_deal_meeted(deal)
        notifs = Notification.objects.filter(
            notification_type="DEAL_MEETED",
        )
        assert notifs.count() == 2
        assert notifs.filter(recipient=deal.applicant).exists()
        assert notifs.filter(recipient=deal.responder).exists()


# ============================================================
# 書籍通知
# ============================================================
class TestNotifyBookDueSoon:
    def test_notifies_keeper(self):
        deal = DealFactory()
        notify_book_due_soon(deal)
        assert (
            Notification.objects.filter(
                recipient=deal.shared_book.keeper,
                notification_type="BOOK_DUE_SOON",
            ).count()
            == 1
        )


class TestNotifyBookOverdue:
    def test_notifies_keeper_and_owner(self):
        owner = UserFactory()
        keeper = UserFactory()
        book = SharedBookFactory(owner=owner, keeper=keeper)
        deal = DealFactory(shared_book=book)
        notify_book_overdue(deal)
        notifs = Notification.objects.filter(
            notification_type="BOOK_OVERDUE",
        )
        assert notifs.count() == 2
        assert notifs.filter(recipient=owner).exists()
        assert notifs.filter(recipient=keeper).exists()

    def test_same_keeper_owner_single_notification(self):
        """keeper == owner 時只發一則"""
        book = SharedBookFactory()  # factory default: keeper=owner
        deal = DealFactory(shared_book=book)
        notify_book_overdue(deal)
        assert (
            Notification.objects.filter(
                notification_type="BOOK_OVERDUE",
            ).count()
            == 1
        )


class TestNotifyBookAvailable:
    def test_notifies_user(self):
        user = UserFactory()
        book = SharedBookFactory()
        notify_book_available(user, book)
        assert (
            Notification.objects.filter(
                recipient=user,
                notification_type="BOOK_AVAILABLE",
            ).count()
            == 1
        )


# ============================================================
# 延長通知
# ============================================================
class TestNotifyExtendRequested:
    def test_notifies_responder(self):
        ext = LoanExtensionFactory()
        notify_extend_requested(ext)
        assert (
            Notification.objects.filter(
                recipient=ext.deal.responder,
                notification_type="EXTEND_REQUESTED",
            ).count()
            == 1
        )


class TestNotifyExtendResult:
    def test_approved(self):
        ext = LoanExtensionFactory(status="APPROVED")
        notify_extend_result(ext)
        assert (
            Notification.objects.filter(
                recipient=ext.requested_by,
                notification_type="EXTEND_APPROVED",
            ).count()
            == 1
        )

    def test_rejected(self):
        ext = LoanExtensionFactory(status="REJECTED")
        notify_extend_result(ext)
        assert (
            Notification.objects.filter(
                recipient=ext.requested_by,
                notification_type="EXTEND_REJECTED",
            ).count()
            == 1
        )


# ============================================================
# 已讀管理
# ============================================================
class TestMarkAsRead:
    def test_mark_single(self):
        notif = NotificationFactory(is_read=False)
        mark_as_read(notif)
        notif.refresh_from_db()
        assert notif.is_read is True


class TestMarkAllAsRead:
    def test_marks_all_unread(self):
        user = UserFactory()
        NotificationFactory(recipient=user, is_read=False)
        NotificationFactory(recipient=user, is_read=False)
        NotificationFactory(recipient=user, is_read=True)
        mark_all_as_read(user)
        assert (
            Notification.objects.filter(
                recipient=user,
                is_read=False,
            ).count()
            == 0
        )
        assert (
            Notification.objects.filter(
                recipient=user,
                is_read=True,
            ).count()
            == 3
        )

    def test_does_not_affect_other_users(self):
        user = UserFactory()
        other = UserFactory()
        NotificationFactory(recipient=user, is_read=False)
        NotificationFactory(recipient=other, is_read=False)
        mark_all_as_read(user)
        assert (
            Notification.objects.filter(
                recipient=other,
                is_read=False,
            ).count()
            == 1
        )
