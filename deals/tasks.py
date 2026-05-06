import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="deals.process_due_books")
def process_due_books():
    from deals.services.overdue_service import batch_process_due_books

    batch_process_due_books()


@shared_task(name="deals.send_due_reminders")
def send_due_reminders(days: int = 3):
    from deals.services.notification_service import batch_send_due_reminders

    batch_send_due_reminders(days)


@shared_task(name="deals.process_pending_ratings")
def process_pending_ratings():
    from deals.services.rating_service import process_pending_ratings as svc

    svc()


@shared_task(
    name="deals.send_push_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def send_push_notification_task(
    self,
    user_id,
    title,
    message,
    url="/",
    deal_id=None,
    book_id=None,
    notification_type=None,
):
    """非同步發送 Web Push 通知給指定用戶的所有訂閱端點。"""
    from django.contrib.auth import get_user_model

    from deals.services.push_service import send_push_to_user

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("Push 目標用戶不存在: %s", user_id)
        return 0

    try:
        return send_push_to_user(
            user=user,
            title=title,
            message=message,
            url=url,
            deal_id=deal_id,
            book_id=book_id,
            notification_type=notification_type,
        )
    except Exception as exc:
        logger.error("Push 發送異常: %s", exc)
        raise self.retry(exc=exc)


@shared_task(
    name="deals.send_email_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def send_email_notification_task(self, user_id, title, message):
    """非同步發送 Email 通知。"""
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.core.mail import send_mail

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("Email 目標用戶不存在: %s", user_id)
        return

    if not user.email:
        return

    try:
        send_mail(
            subject=f"[Exbooks] {title}",
            message=message or title,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("Email 發送異常: %s", exc)
        raise self.retry(exc=exc)
