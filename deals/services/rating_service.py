from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from deals.models import Deal, Rating
from deals.services.notification_service import notify_rating_pending


def create_rating(
    deal, rater, friendliness_score, punctuality_score, accuracy_score, comment=""
):
    """
    建立交易評價。

    Rules:
    - 僅面交完成後（M 狀態）可評價
    - 每人每筆交易只能評一次（UniqueConstraint 保障）
    - 評價者必須是該筆交易的申請者或回應者
    - BR-9: 雙方均完成評價後，Deal.status 自動變為 D

    Returns:
        Rating: 建立的評價
    """
    if deal.status not in (Deal.Status.MEETED, Deal.Status.DONE):
        raise ValidationError("只有「已面交」或「已完成」狀態的交易可以評價")

    # 確認評價者身份
    if rater == deal.applicant:
        if deal.applicant_rated:
            raise ValidationError("您已經評價過此交易")
        ratee = deal.responder
    elif rater == deal.responder:
        if deal.responder_rated:
            raise ValidationError("您已經評價過此交易")
        ratee = deal.applicant
    else:
        raise ValidationError("只有交易雙方可以評價")

    rating = Rating._default_manager.create(
        deal=deal,
        rater=rater,
        ratee=ratee,
        friendliness_score=friendliness_score,
        punctuality_score=punctuality_score,
        accuracy_score=accuracy_score,
        comment=comment,
    )

    # 更新被評價者的信用積分
    from accounts.services.trust_service import update_trust_score

    update_trust_score(ratee)

    # 更新評價旗標
    if rater == deal.applicant:
        deal.applicant_rated = True
    else:
        deal.responder_rated = True
    deal.save(update_fields=["applicant_rated", "responder_rated", "updated_at"])

    from deals.models import Notification

    Notification._default_manager.filter(
        recipient=rater,
        deal=deal,
        notification_type=Notification.NotificationType.DEAL_MEETED,
        is_read=False,
    ).update(is_read=True)

    # 僅標記已評價，不在此自動觸發交易完成。
    # 交易完成應由「確認歸還」按鈕觸發（閱畢即還）或手動確認。
    return rating


def process_pending_ratings():
    """
    掃描已面交交易的待評價對象，執行提醒與自動代評。

    規則：
    - 基準時間為 deal.updated_at
    - >= 3 天：提醒未評價方（每日最多一次）
    - >= 10 天：系統代評 3 星（固定註解）
    """
    now = timezone.now()
    reminder_cutoff = now - timedelta(days=3)
    auto_rate_cutoff = now - timedelta(days=10)

    deals = Deal._default_manager.filter(status=Deal.Status.MEETED).select_related(
        "shared_book",
        "applicant",
        "responder",
    )

    from deals.models import Notification

    for deal in deals:
        pending_users = []
        if not deal.applicant_rated:
            pending_users.append(deal.applicant)
        if not deal.responder_rated:
            pending_users.append(deal.responder)

        if not pending_users:
            continue

        if deal.updated_at <= auto_rate_cutoff:
            for user in pending_users:
                create_rating(deal, user, 3, 3, 3, "系統代評：逾期 10 天未評")
            continue

        if deal.updated_at <= reminder_cutoff:
            for user in pending_users:
                already_notified_today = Notification._default_manager.filter(
                    recipient=user,
                    deal=deal,
                    notification_type=Notification.NotificationType.DEAL_MEETED,
                    title="評價提醒：仍有交易待評",
                    created_at__date=now.date(),
                ).exists()

                if not already_notified_today:
                    notify_rating_pending(deal=deal, user=user)
