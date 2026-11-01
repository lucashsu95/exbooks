from rest_framework import serializers

from accounts.serializers import DisplayNameField
from deals.models.deal import Deal
from deals.models.loan_extension import LoanExtension
from deals.models.deal_message import DealMessage
from deals.models.notification import Notification


class LoanExtensionSerializer(serializers.ModelSerializer):
    requested_by_nickname = DisplayNameField(source="requested_by")
    approved_by_nickname = DisplayNameField(source="approved_by")

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
        read_only_fields = ["status", "approved_by", "requested_by"]


class DealSerializer(serializers.ModelSerializer):
    shared_book_title = serializers.ReadOnlyField(
        source="shared_book.official_book.title"
    )
    applicant_nickname = DisplayNameField(source="applicant")
    responder_nickname = DisplayNameField(source="responder")

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
        # applicant 恆為 request.user、responder 由 service 判定；
        # book_set 由 service 依 shared_book 推導（不接受 client 指定）；
        # due_date 與評價旗標只能經 service 寫入。
        read_only_fields = [
            "book_set",
            "status",
            "previous_book_status",
            "applicant",
            "responder",
            "due_date",
            "applicant_rated",
            "responder_rated",
        ]


class DealMessageSerializer(serializers.ModelSerializer):
    sender_nickname = DisplayNameField(source="sender")

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



