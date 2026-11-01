from django.contrib.auth.models import AbstractBaseUser
from rest_framework import serializers

from accounts.models import UserProfile
from accounts.services.display_name_service import display_name_for


class DisplayNameField(serializers.ReadOnlyField):
    """
    他人顯示名稱（唯讀）：source 指向 User，輸出暱稱或「會員#<pk>」，絕不輸出 email。

    用法：applicant_nickname = DisplayNameField(source="applicant")
    User 為 None 時 DRF 直接輸出 null。
    """

    def to_representation(self, value: AbstractBaseUser) -> str:
        return display_name_for(value)


class UserProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source="user.email")
    user_username = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "user_email",
            "user_username",
            "nickname",
            "birth_date",
            "default_transferability",
            "default_location",
            "available_schedule",
            "avatar",
            "trust_score",
            "successful_returns",
            "overdue_count",
            "is_suspended",
            "suspension_end_date",
            "suspension_reason",
            "push_enabled",
            "email_notifications_enabled",
        ]
        read_only_fields = [
            "trust_score",
            "successful_returns",
            "overdue_count",
            "is_suspended",
            "suspension_end_date",
            "suspension_reason",
        ]
