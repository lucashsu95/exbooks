from rest_framework import serializers
from deals.models.deal import Deal
from deals.models.loan_extension import LoanExtension
from deals.models.deal_message import DealMessage
from deals.models.notification import Notification


class LoanExtensionSerializer(serializers.ModelSerializer):
    requested_by_nickname = serializers.ReadOnlyField(
        source="requested_by.profile.nickname"
    )
    approved_by_nickname = serializers.ReadOnlyField(
        source="approved_by.profile.nickname"
    )

    class Meta:
        model = LoanExtension
        fields = [
            "id",
            "deal",
            "requested_by",
            "requested_by_nickname",
            "approved_by",
            "approved_by_nickname",
            "extra_days",
            "status",
        ]
        read_only_fields = ["status", "approved_by"]


class DealSerializer(serializers.ModelSerializer):
    shared_book_title = serializers.ReadOnlyField(
        source="shared_book.official_book.title"
    )
    applicant_nickname = serializers.ReadOnlyField(source="applicant.profile.nickname")
    responder_nickname = serializers.ReadOnlyField(source="responder.profile.nickname")

    class Meta:
        model = Deal
        fields = [
            "id",
            "shared_book",
            "shared_book_title",
            "book_set",
            "deal_type",
            "status",
            "previous_book_status",
            "applicant",
            "applicant_nickname",
            "responder",
            "responder_nickname",
            "meeting_location",
            "meeting_time",
            "due_date",
            "applicant_rated",
            "responder_rated",
        ]
        read_only_fields = ["status", "previous_book_status"]


class DealMessageSerializer(serializers.ModelSerializer):
    sender_nickname = serializers.ReadOnlyField(source="sender.profile.nickname")

    class Meta:
        model = DealMessage
        fields = ["id", "deal", "sender", "sender_nickname", "content", "created_at"]
        read_only_fields = ["sender"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "deal",
            "shared_book",
            "notification_type",
            "title",
            "message",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]



