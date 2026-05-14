from rest_framework import serializers
from accounts.models import UserProfile

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
