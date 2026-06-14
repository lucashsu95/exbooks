import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="deals.process_due_books")
def process_due_books():
    from deals.services.overdue_service import batch_process_due_books

    logger.info("Task started", extra={"task": "deals.process_due_books"})
    try:
        batch_process_due_books()
        logger.info("Task completed", extra={"task": "deals.process_due_books"})
    except Exception:
        logger.exception("Task failed", extra={"task": "deals.process_due_books"})
        raise


@shared_task(name="deals.send_due_reminders")
def send_due_reminders(days: int = 3):
    from deals.services.notification_service import batch_send_due_reminders

    logger.info("Task started", extra={"task": "deals.send_due_reminders", "days": days})
    try:
        batch_send_due_reminders(days)
        logger.info("Task completed", extra={"task": "deals.send_due_reminders"})
    except Exception:
        logger.exception("Task failed", extra={"task": "deals.send_due_reminders", "days": days})
        raise


@shared_task(name="deals.process_pending_ratings")
def process_pending_ratings():
    from deals.services.rating_service import process_pending_ratings as svc

    logger.info("Task started", extra={"task": "deals.process_pending_ratings"})
    try:
        svc()
        logger.info("Task completed", extra={"task": "deals.process_pending_ratings"})
    except Exception:
        logger.exception("Task failed", extra={"task": "deals.process_pending_ratings"})
        raise


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

    logger.info("Task started", extra={
        "task": "deals.send_push_notification",
        "user_id": user_id,
        "title": title,
        "notification_type": notification_type,
    })
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("Push 目標用戶不存在", extra={"user_id": user_id})
        return 0

    try:
        result = send_push_to_user(
            user=user,
            title=title,
            message=message,
            url=url,
            deal_id=deal_id,
            book_id=book_id,
            notification_type=notification_type,
        )
        logger.info("Task completed", extra={
            "task": "deals.send_push_notification",
            "user_id": user_id,
            "result": result,
        })
        return result
    except Exception as exc:
        logger.exception("Push 發送異常", extra={"user_id": user_id})
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
    logger.info("Task started", extra={
        "task": "deals.send_email_notification",
        "user_id": user_id,
        "title": title,
    })
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("Email 目標用戶不存在", extra={"user_id": user_id})
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
        logger.info("Task completed", extra={
            "task": "deals.send_email_notification",
            "user_id": user_id,
        })
    except Exception as exc:
        logger.exception("Email 發送異常", extra={"user_id": user_id})
        raise self.retry(exc=exc)
