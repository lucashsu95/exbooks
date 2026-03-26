"""
Web Push 發送服務。

封裝 pywebpush 套件，提供發送 Web Push 通知的功能。
"""

import json
import logging
from typing import Optional

from django.conf import settings

from deals.models import PushSubscription, WebPushConfig

logger = logging.getLogger(__name__)

# 嘗試載入 pywebpush
try:
    from pywebpush import webpush, WebPushException

    WEBPUSH_AVAILABLE = True
except ImportError:
    WEBPUSH_AVAILABLE = False
    logger.warning("pywebpush 套件未安裝，Web Push 功能將停用")


def send_push_notification(
    subscription: PushSubscription,
    title: str,
    message: str,
    url: Optional[str] = None,
    deal_id: Optional[str] = None,
    book_id: Optional[str] = None,
    notification_type: Optional[str] = None,
) -> bool:
    """
    發送 Web Push 通知給指定訂閱。

    Args:
        subscription: PushSubscription 物件
        title: 通知標題
        message: 通知內容
        url: 點擊後跳轉的 URL（可選）
        deal_id: 相關交易 ID（可選）
        book_id: 相關書籍 ID（可選）
        notification_type: 通知類型（可選）

    Returns:
        bool: 是否發送成功
    """
    if not WEBPUSH_AVAILABLE:
        logger.warning("pywebpush 未安裝，跳過 Push 發送")
        return False

    if not subscription.is_active:
        logger.debug(f"訂閱 {subscription.id} 已停用，跳過發送")
        return False

    config = WebPushConfig.get_config()
    if not config:
        logger.warning("WebPushConfig 不存在，跳過 Push 發送")
        return False

    # 構建通知資料
    payload = {
        "title": title,
        "message": message,
        "url": url or "/",
    }

    if deal_id:
        payload["deal_id"] = str(deal_id)
    if book_id:
        payload["book_id"] = str(book_id)
    if notification_type:
        payload["notification_type"] = notification_type

    try:
        webpush(
            subscription_info=subscription.subscription_data,
            data=json.dumps(payload),
            vapid_private_key=config.vapid_private_key,
            vapid_claims={
                "sub": config.subject
                or f"mailto:noreply@{settings.SITE_ID}.example.com",
            },
        )
        logger.info(f"Push 發送成功: {subscription.user} - {title}")
        return True

    except WebPushException as e:
        logger.error(f"Push 發送失敗: {e}")

        # 如果是 410 Gone，表示訂閱已失效，停用該訂閱
        if e.response and e.response.status_code == 410:
            subscription.is_active = False
            subscription.save(update_fields=["is_active"])
            logger.info(f"訂閱已失效，已停用: {subscription.id}")

        return False

    except Exception as e:
        logger.error(f"Push 發送發生未知錯誤: {e}")
        return False


def send_push_to_user(
    user,
    title: str,
    message: str,
    url: Optional[str] = None,
    deal_id: Optional[str] = None,
    book_id: Optional[str] = None,
    notification_type: Optional[str] = None,
) -> int:
    """
    發送 Web Push 通知給用戶的所有啟用訂閱。

    Args:
        user: User 物件
        title: 通知標題
        message: 通知內容
        url: 點擊後跳轉的 URL（可選）
        deal_id: 相關交易 ID（可選）
        book_id: 相關書籍 ID（可選）
        notification_type: 通知類型（可選）

    Returns:
        int: 成功發送的訂閱數量
    """
    if not WEBPUSH_AVAILABLE:
        return 0

    subscriptions = PushSubscription.objects.filter(
        user=user,
        is_active=True,
    )

    success_count = 0
    for subscription in subscriptions:
        if send_push_notification(
            subscription=subscription,
            title=title,
            message=message,
            url=url,
            deal_id=deal_id,
            book_id=book_id,
            notification_type=notification_type,
        ):
            success_count += 1

    return success_count


def generate_vapid_keys():
    """
    產生 VAPID 金鑰對。

    Returns:
        dict: {"public_key": str, "private_key": str}
    """
    if not WEBPUSH_AVAILABLE:
        raise RuntimeError("pywebpush 套件未安裝")

    from pywebpush.utils import generate_vapid_keypair

    public_key, private_key = generate_vapid_keypair()

    return {
        "public_key": public_key,
        "private_key": private_key,
    }
