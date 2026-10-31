from rest_framework import mixins, viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models

from deals.models.deal import Deal
from deals.models.loan_extension import LoanExtension
from deals.models.deal_message import DealMessage
from deals.models.notification import Notification
from deals.serializers import (
    DealSerializer,
    LoanExtensionSerializer,
    DealMessageSerializer,
    NotificationSerializer,
)
from core.error_messages import service_error_message
from deals.rules import deal_party_q
from deals.services import deal_service, extension_service, notification_service


class DealViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    API endpoint for managing Deals.

    只開放 list / retrieve / create 與自訂 action（accept/decline/cancel/
    complete_meeting）。狀態與當事人只能經 deal_service 變更；不提供
    update / destroy，避免 PATCH 改 due_date / 當事人 / 評價旗標或直接刪除。
    """

    queryset = (
        Deal.objects.select_related(
            "shared_book__official_book", "applicant__profile", "responder__profile"
        )
        .all()
        .order_by("-created_at")
    )
    serializer_class = DealSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = [
        "shared_book__official_book__title",
        "shared_book__official_book__author",
    ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            deal = deal_service.create_deal(
                applicant=request.user,
                shared_book=serializer.validated_data["shared_book"],
                deal_type=serializer.validated_data["deal_type"],
                meeting_location=serializer.validated_data.get("meeting_location", ""),
                meeting_time=serializer.validated_data.get("meeting_time"),
            )
            return Response(
                self.get_serializer(deal).data, status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response({"error": service_error_message(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        # 可見範圍 = 交易當事人（applicant / responder / owner / keeper），
        # 與 Web 交易詳情同一規則（deals.rules.is_deal_party）
        return self.queryset.filter(deal_party_q(self.request.user))

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        deal = self.get_object()
        if not request.user.has_perm("deals.can_accept_deal", deal):
            return Response(
                {"error": "Only the responder can accept the deal."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            deal_service.accept_deal(deal)
            return Response(
                {"status": "Deal accepted successfully."}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": service_error_message(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        deal = self.get_object()
        if not request.user.has_perm("deals.can_decline_deal", deal):
            return Response(
                {"error": "Only the responder can decline the deal."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            deal_service.decline_deal(deal)
            return Response(
                {"status": "Deal declined successfully."}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": service_error_message(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        deal = self.get_object()
        if not request.user.has_perm("deals.can_cancel_deal", deal):
            return Response(
                {"error": "Only the applicant can cancel the deal."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            deal_service.cancel_deal(deal)
            return Response(
                {"status": "Deal cancelled successfully."}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": service_error_message(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def complete_meeting(self, request, pk=None):
        deal = self.get_object()
        if not request.user.has_perm("deals.can_complete_meeting", deal):
            return Response(
                {"error": "You are not a party to this deal."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            deal_service.complete_meeting(deal)
            return Response(
                {"status": "Meeting marked as complete."}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": service_error_message(e)}, status=status.HTTP_400_BAD_REQUEST)


class LoanExtensionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Loan Extensions.
    """

    queryset = (
        LoanExtension.objects.select_related(
            "deal", "requested_by__profile", "approved_by__profile"
        )
        .all()
        .order_by("-created_at")
    )
    serializer_class = LoanExtensionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(
            models.Q(requested_by=self.request.user)
            | models.Q(deal__responder=self.request.user)
        )

    def perform_create(self, serializer):
        deal = serializer.validated_data["deal"]
        extra_days = serializer.validated_data["extra_days"]

        try:
            extension = extension_service.request_extension(
                deal=deal, applicant=self.request.user, extra_days=extra_days
            )
            return extension
        except Exception as e:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(service_error_message(e))

    def _method_not_allowed(self):
        # 合法寫入只走 create（request_extension）與 approve/reject/cancel service；
        # 預設 ModelViewSet 的 update/destroy 會繞過 service 直接改列
        # （如 PATCH 搬移 deal），故一律 405。
        return Response(
            {"error": "此操作不被允許；延長申請的核准/拒絕請用 approve/reject。"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        return self._method_not_allowed()

    def partial_update(self, request, *args, **kwargs):
        return self._method_not_allowed()

    def destroy(self, request, *args, **kwargs):
        return self._method_not_allowed()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        extension = self.get_object()
        try:
            extension_service.approve_extension(extension, request.user)
            return Response(
                {"status": "Extension approved."}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": service_error_message(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        extension = self.get_object()
        try:
            extension_service.reject_extension(extension, request.user)
            return Response(
                {"status": "Extension rejected successfully."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": service_error_message(e)}, status=status.HTTP_400_BAD_REQUEST)


class DealMessageViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    API endpoint for managing Deal Messages.

    留言建立後不可修改、刪除或搬移到其他交易；只開放 list / retrieve /
    create（create 走 deal_service.send_deal_message 並檢查當事人權限）。
    """

    queryset = (
        DealMessage.objects.select_related("deal", "sender__profile")
        .all()
        .order_by("created_at")
    )
    serializer_class = DealMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(
            models.Q(sender=self.request.user)
            | deal_party_q(self.request.user, prefix="deal__")
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        deal = serializer.validated_data["deal"]
        if not request.user.has_perm("deals.can_send_message", deal):
            return Response(
                {"error": "Only a party to the deal can send messages."},
                status=status.HTTP_403_FORBIDDEN,
            )

        content = serializer.validated_data["content"].strip()
        if not content:
            return Response(
                {"error": "留言內容不能為空白。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            message = deal_service.send_deal_message(
                deal=deal,
                sender=request.user,
                content=content,
            )
            return Response(
                self.get_serializer(message).data,
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response(
                {"error": service_error_message(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for managing Notifications.

    通知由系統產生，API 端唯讀；唯一的寫入是 mark_as_read action。
    """

    queryset = (
        Notification.objects.select_related("deal", "shared_book")
        .all()
        .order_by("-created_at")
    )
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(recipient=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        notification_service.mark_as_read(self.get_object())
        return Response(
            {"status": "Notification marked as read."}, status=status.HTTP_200_OK
        )
