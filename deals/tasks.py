from celery import shared_task


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
