"""
REST API 的 JWT 簽發（/api/token/）。

SimpleJWT 預設只驗帳密，會繞過 allauth 的 ACCOUNT_EMAIL_VERIFICATION =
"mandatory"；這裡加上「主要 Email 已驗證」檢查，並套用獨立的 scoped
throttle（rate 見 settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]）。
"""

from allauth.account.models import EmailAddress
from rest_framework import exceptions
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class VerifiedEmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        **TokenObtainPairSerializer.default_error_messages,
        "email_not_verified": "Email 尚未完成驗證，請先至信箱完成驗證。",
    }

    def validate(self, attrs):
        data = super().validate(attrs)
        if not EmailAddress.objects.filter(
            user=self.user, verified=True, primary=True
        ).exists():
            raise exceptions.AuthenticationFailed(
                self.error_messages["email_not_verified"], "email_not_verified"
            )
        return data


class VerifiedEmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = VerifiedEmailTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token_obtain"
