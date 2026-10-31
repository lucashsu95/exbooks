"""
Web Push 發送服務。

封裝 pywebpush 套件，提供發送 Web Push 通知的功能。
"""

import json
import logging
from typing import Optional
from urllib.parse import urlsplit

from django.conf import settings

from deals.models import PushSubscription, WebPushConfig

logger = logging.getLogger(__name__)

# 瀏覽器 Push 服務的主機白名單（防 SSRF：端點由用戶端提供，伺服器會對它發 POST）。
# 完全相符的主機
PUSH_ENDPOINT_EXACT_HOSTS = frozenset(
    {
        "fcm.googleapis.com",
        "updates.push.services.mozilla.com",
    }
)
# 僅允許其「正當子網域」（*.push.apple.com 不含 push.apple.com 本身）
PUSH_ENDPOINT_WILDCARD_SUFFIXES = (
    ".push.apple.com",
    ".notify.windows.com",
)


def is_allowed_push_endpoint(endpoint: object) -> bool:
    """
    檢查 Web Push 訂閱端點是否為可信任的瀏覽器 Push 服務。

    條件：https、無 userinfo、使用預設埠（不可指定埠），
    主機須完全相符白名單，或為萬用字元網域的正當子網域（非子字串比對）。
    """
    if not isinstance(endpoint, str) or not endpoint:
        return False
    try:
        parts = urlsplit(endpoint)
        port = parts.port
    except ValueError:
        return False
    if parts.scheme != "https":
        return False
    if parts.username is not None or parts.password is not None or "@" in parts.netloc:
        return False
    if port is not None or parts.netloc.endswith(":"):
        return False
    host = (parts.hostname or "").lower()
    if not host or host.endswith("."):
        return False
    if host in PUSH_ENDPOINT_EXACT_HOSTS:
        return True
    return any(
        host.endswith(suffix) and len(host) > len(suffix)
        for suffix in PUSH_ENDPOINT_WILDCARD_SUFFIXES
    )

# 嘗試載入 pywebpush
try:
    from pywebpush import webpush, WebPushException

    WEBPUSH_AVAILABLE = True
except ImportError:
    WEBPUSH_AVAILABLE = False
    logger.warning("pywebpush 套件未安裝，Web Push 功能將停用")


def subscribe(
    user, endpoint: str, p256dh: str, auth: str, user_agent: str = ""
) -> tuple[PushSubscription, bool]:
    """
    建立或更新使用者的 Push 訂閱（同一 endpoint 不重複）。

    endpoint 不在白名單時拋 ValueError，由呼叫端轉成 400。
    回傳 (訂閱, 是否新建)。
    """
    if not is_allowed_push_endpoint(endpoint):
        raise ValueError("不支援的推播端點")
    return PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": user,
            "p256dh": p256dh,
            "auth": auth,
            "user_agent": user_agent[:500],
            "is_active": True,
        },
    )


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
    logger.debug(
        "send_push_notification",
        extra={
            "subscription_id": subscription.id,
            "user_id": subscription.user_id,
            "title": title,
            "notification_type": notification_type,
        },
    )
    if not WEBPUSH_AVAILABLE:
        logger.warning("pywebpush 未安裝，跳過 Push 發送")
        return False

    if not subscription.is_active:
        logger.debug(f"訂閱 {subscription.id} 已停用，跳過發送")
        return False

    # 既有資料可能早於端點驗證寫入；發送前再檢查一次，不合法就停用
    if not is_allowed_push_endpoint(subscription.endpoint):
        logger.warning(
            "push endpoint not allowed, subscription deactivated",
            extra={
                "subscription_id": subscription.id,
                "user_id": subscription.user_id,
            },
        )
        subscription.is_active = False
        subscription.save(update_fields=["is_active"])
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
        logger.info(
            "Push sent successfully",
            extra={
                "subscription_id": subscription.id,
                "user_id": subscription.user_id,
                "title": title,
            },
        )
        return True

    except WebPushException as e:
        logger.exception(
            "Push send failed",
            extra={
                "subscription_id": subscription.id,
                "user_id": subscription.user_id,
                "title": title,
            },
        )

        # 如果是 410 Gone，表示訂閱已失效，停用該訂閱
        if e.response and e.response.status_code == 410:
            subscription.is_active = False
            subscription.save(update_fields=["is_active"])
            logger.info(
                "subscription deactivated (410)",
                extra={"subscription_id": subscription.id},
            )

        return False

    except Exception:
        logger.exception(
            "Push send unexpected error",
            extra={
                "subscription_id": subscription.id,
                "user_id": subscription.user_id,
            },
        )
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

    logger.debug(
        "send_push_to_user",
        extra={
            "user_id": user.id,
            "subscriptions": subscriptions.count(),
            "title": title,
        },
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

    logger.debug(
        "send_push_to_user done",
        extra={"user_id": user.id, "success_count": success_count},
    )
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
