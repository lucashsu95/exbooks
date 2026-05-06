"""
Tests for async notification dispatch (Celery tasks) and preference controls.
"""

import pytest
from unittest.mock import patch

from deals.models import Notification
from deals.services.notification_service import notify
from tests.factories import DealFactory, UserFactory


pytestmark = pytest.mark.django_db


class TestNotifyDispatchesCeleryTasks:
    """notify() should dispatch push/email via Celery .delay() instead of blocking."""

    @patch("deals.tasks.send_email_notification_task.delay")
    @patch("deals.tasks.send_push_notification_task.delay")
    def test_dispatches_push_task(self, mock_push_delay, mock_email_delay):
        user = UserFactory()
        notify(
            recipient=user,
            notification_type=Notification.NotificationType.DEAL_REQUESTED,
            title="借閱申請",
            message="測試",
        )
        mock_push_delay.assert_called_once()
        kwargs = mock_push_delay.call_args.kwargs
        assert kwargs["user_id"] == user.pk
        assert kwargs["title"] == "借閱申請"

    @patch("deals.tasks.send_email_notification_task.delay")
    @patch("deals.tasks.send_push_notification_task.delay")
    def test_dispatches_email_task(self, mock_push_delay, mock_email_delay):
        user = UserFactory()
        notify(
            recipient=user,
            notification_type=Notification.NotificationType.DEAL_REQUESTED,
            title="借閱申請",
            message="測試",
        )
        mock_email_delay.assert_called_once()
        kwargs = mock_email_delay.call_args.kwargs
        assert kwargs["user_id"] == user.pk
        assert kwargs["title"] == "借閱申請"

    @patch("deals.tasks.send_email_notification_task.delay")
    @patch("deals.tasks.send_push_notification_task.delay")
    def test_skip_push_when_flag_false(self, mock_push_delay, mock_email_delay):
        user = UserFactory()
        notify(
            recipient=user,
            notification_type=Notification.NotificationType.DEAL_REQUESTED,
            title="Test",
            send_push=False,
        )
        mock_push_delay.assert_not_called()

    @patch("deals.tasks.send_email_notification_task.delay")
    @patch("deals.tasks.send_push_notification_task.delay")
    def test_skip_email_when_flag_false(self, mock_push_delay, mock_email_delay):
        user = UserFactory()
        notify(
            recipient=user,
            notification_type=Notification.NotificationType.DEAL_REQUESTED,
            title="Test",
            send_email=False,
        )
        mock_email_delay.assert_not_called()

    @patch("deals.tasks.send_email_notification_task.delay")
    @patch("deals.tasks.send_push_notification_task.delay")
    def test_includes_deal_url_in_push(self, mock_push_delay, mock_email_delay):
        deal = DealFactory()
        notify(
            recipient=deal.applicant,
            notification_type=Notification.NotificationType.DEAL_REQUESTED,
            title="Test",
            deal=deal,
        )
        kwargs = mock_push_delay.call_args.kwargs
        assert str(deal.id) in kwargs["url"]
        assert kwargs["deal_id"] == str(deal.id)


class TestNotificationPreferences:
    """notify() respects UserProfile push_enabled / email_notifications_enabled."""

    @patch("deals.tasks.send_email_notification_task.delay")
    @patch("deals.tasks.send_push_notification_task.delay")
    def test_push_disabled_skips_push_task(self, mock_push_delay, mock_email_delay):
        user = UserFactory()
        user.profile.push_enabled = False
        user.profile.save(update_fields=["push_enabled"])

        notify(
            recipient=user,
            notification_type=Notification.NotificationType.DEAL_REQUESTED,
            title="Test",
        )
        mock_push_delay.assert_not_called()
        mock_email_delay.assert_called_once()

    @patch("deals.tasks.send_email_notification_task.delay")
    @patch("deals.tasks.send_push_notification_task.delay")
    def test_email_disabled_skips_email_task(self, mock_push_delay, mock_email_delay):
        user = UserFactory()
        user.profile.email_notifications_enabled = False
        user.profile.save(update_fields=["email_notifications_enabled"])

        notify(
            recipient=user,
            notification_type=Notification.NotificationType.DEAL_REQUESTED,
            title="Test",
        )
        mock_push_delay.assert_called_once()
        mock_email_delay.assert_not_called()

    @patch("deals.tasks.send_email_notification_task.delay")
    @patch("deals.tasks.send_push_notification_task.delay")
    def test_both_disabled_only_creates_db_notification(
        self, mock_push_delay, mock_email_delay
    ):
        user = UserFactory()
        user.profile.push_enabled = False
        user.profile.email_notifications_enabled = False
        user.profile.save(update_fields=["push_enabled", "email_notifications_enabled"])

        notif = notify(
            recipient=user,
            notification_type=Notification.NotificationType.DEAL_REQUESTED,
            title="Test",
        )
        assert notif.pk is not None
        mock_push_delay.assert_not_called()
        mock_email_delay.assert_not_called()


class TestNotificationBadgeView:
    """notification_count view returns correct badge HTML."""

    def test_returns_badge_for_authenticated_user(self, client):
        user = UserFactory()
        client.force_login(user)

        Notification.objects.create(
            recipient=user,
            notification_type=Notification.NotificationType.DEAL_REQUESTED,
            title="Test",
            is_read=False,
        )
        Notification.objects.create(
            recipient=user,
            notification_type=Notification.NotificationType.DEAL_RESPONDED,
            title="Test 2",
            is_read=False,
        )

        response = client.get("/deals/notifications/count/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "2" in content

    def test_no_badge_when_all_read(self, client):
        user = UserFactory()
        client.force_login(user)

        Notification.objects.create(
            recipient=user,
            notification_type=Notification.NotificationType.DEAL_REQUESTED,
            title="Test",
            is_read=True,
        )

        response = client.get("/deals/notifications/count/")
        content = response.content.decode()
        assert "bg-rose-500" not in content


class TestCeleryPushTask:
    """send_push_notification_task correctly calls push_service."""

    @patch("deals.services.push_service.send_push_to_user", return_value=1)
    def test_calls_push_service(self, mock_send):
        from deals.tasks import send_push_notification_task

        user = UserFactory()
        result = send_push_notification_task(
            user_id=user.pk,
            title="Test",
            message="Hello",
            url="/",
        )
        mock_send.assert_called_once()
        assert result == 1

    def test_handles_missing_user(self):
        from deals.tasks import send_push_notification_task

        result = send_push_notification_task(
            user_id=99999,
            title="Test",
            message="Hello",
        )
        assert result == 0


class TestCeleryEmailTask:
    """send_email_notification_task correctly calls send_mail."""

    @patch("django.core.mail.send_mail")
    def test_calls_send_mail(self, mock_mail):
        from deals.tasks import send_email_notification_task

        user = UserFactory(email="test@example.com")
        send_email_notification_task(
            user_id=user.pk,
            title="Test",
            message="Hello",
        )
        mock_mail.assert_called_once()
        args, kwargs = mock_mail.call_args
        assert "[Exbooks] Test" in args or kwargs.get("subject") == "[Exbooks] Test"

    def test_handles_missing_user(self):
        from deals.tasks import send_email_notification_task

        send_email_notification_task(
            user_id=99999,
            title="Test",
            message="Hello",
        )

    @patch("django.core.mail.send_mail")
    def test_skips_when_no_email(self, mock_mail):
        from deals.tasks import send_email_notification_task

        user = UserFactory(email="")
        send_email_notification_task(
            user_id=user.pk,
            title="Test",
            message="Hello",
        )
        mock_mail.assert_not_called()
