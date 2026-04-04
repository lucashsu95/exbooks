from django.core.exceptions import ValidationError
from django.db import transaction
from django_fsm import can_proceed

from deals.models import Deal, Rating


@transaction.atomic
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

    rating = Rating.objects.create(
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

    Notification.objects.filter(
        recipient=rater,
        deal=deal,
        notification_type=Notification.NotificationType.DEAL_MEETED,
        is_read=False,
    ).update(is_read=True)

    if deal.applicant_rated and deal.responder_rated:
        # 區分完成條件：
        # - 閱畢即還 (LOAN)：除了互評，還必須書籍已歸還（狀態變為 T）
        # - 其他 (TRANSFER, RESTORE, etc.)：互評完即完成
        should_complete = True
        if (
            deal.deal_type == Deal.DealType.LOAN
            and deal.shared_book.status != SharedBook.Status.TRANSFERABLE
        ):
            should_complete = False

        if should_complete and can_proceed(deal.complete):
            deal.complete()
            deal.save()

            # 交易完成，更新雙方信用積分（完成交易 +10 分）
            update_trust_score(deal.applicant)
            update_trust_score(deal.responder)

    return rating
