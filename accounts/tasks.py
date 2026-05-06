from celery import shared_task


@shared_task(name="accounts.recalculate_trust_scores")
def recalculate_trust_scores():
    from accounts.services.trust_service import recalculate_all_trust_scores

    recalculate_all_trust_scores()
