"""API 測試共用：JWT 只發給已驗證 Email 的帳號（見 accounts.api_auth）。"""

from allauth.account.models import EmailAddress


def mark_email_verified(user):
    EmailAddress.objects.update_or_create(
        user=user,
        email=user.email,
        defaults={"verified": True, "primary": True},
    )
    return user
