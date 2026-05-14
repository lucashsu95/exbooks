from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models

from deals.models.deal import Deal
from deals.models.loan_extension import LoanExtension
from deals.models.deal_message import DealMessage
from deals.models.notification import Notification
from deals.models.rating import Rating
from deals.serializers import (
    DealSerializer, 
    LoanExtensionSerializer, 
    DealMessageSerializer, 
    NotificationSerializer, 
    RatingSerializer
)
from deals.services import deal_service, extension_service

class DealViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Deals.
    """
    queryset = Deal.objects.select_related("shared_book__official_book", "applicant__profile", "responder__profile").all().order_by("-created_at")
    serializer_class = DealSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["shared_book__official_book__title", "shared_book__official_book__author"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            deal = deal_service.create_deal(
                applicant=request.user,
                shared_book_id=serializer.validated_data["shared_book"].id,
                deal_type=serializer.validated_data["deal_type"],
                book_set_id=serializer.validated_data.get("book_set").id if serializer.validated_data.get("book_set") else None,
                loan_duration_days=serializer.validated_data.get("loan_duration_days"),
                meeting_location=serializer.validated_data.get("meeting_location", ""),
                meeting_time=serializer.validated_data.get("meeting_time"),
                note=serializer.validated_data.get("note"),
            )
            return Response(self.get_serializer(deal).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        return self.queryset.filter(
            models.Q(applicant=self.request.user) | models.Q(responder=self.request.user)
        )

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        deal = self.get_object()
        if deal.responder != request.user:
            return Response({"error": "Only the responder can accept the deal."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            deal_service.accept_deal(deal)
            return Response({"status": "Deal accepted successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        deal = self.get_object()
        if deal.responder != request.user:
            return Response({"error": "Only the responder can decline the deal."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            deal_service.decline_deal(deal)
            return Response({"status": "Deal declined successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        deal = self.get_object()
        if deal.applicant != request.user and deal.responder != request.user:
            return Response({"error": "You are not a party to this deal."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            deal_service.cancel_deal(deal)
            return Response({"status": "Deal cancelled successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def complete_meeting(self, request, pk=None):
        deal = self.get_object()
        try:
            deal_service.complete_meeting(deal)
            return Response({"status": "Meeting marked as complete."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LoanExtensionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Loan Extensions.
    """
    queryset = LoanExtension.objects.select_related("deal", "requested_by__profile", "approved_by__profile").all().order_by("-created_at")
    serializer_class = LoanExtensionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(
            models.Q(requested_by=self.request.user) | models.Q(deal__responder=self.request.user)
        )

    def perform_create(self, serializer):
        deal = serializer.validated_data["deal"]
        extra_days = serializer.validated_data["extra_days"]
        
        try:
            extension = extension_service.request_extension(
                deal=deal,
                applicant=self.request.user,
                extra_days=extra_days
            )
            return extension
        except Exception as e:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(str(e))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        extension = self.get_object()
        try:
            extension_service.approve_extension(extension, request.user)
            return Response({"status": "Extension approved."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        extension = self.get_object()
        try:
            extension_service.reject_extension(extension, request.user)
            return Response({"status": "Extension rejected successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class DealMessageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Deal Messages.
    """
    queryset = DealMessage.objects.select_related("deal", "sender__profile").all().order_by("created_at")
    serializer_class = DealMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(
            models.Q(sender=self.request.user) | models.Q(deal__applicant=self.request.user) | models.Q(deal__responder=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

class NotificationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Notifications.
    """
    queryset = Notification.objects.select_related("deal", "shared_book").all().order_by("-created_at")
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(recipient=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response({"status": "Notification marked as read."}, status=status.HTTP_200_OK)

class RatingViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Ratings.
    """
    queryset = Rating.objects.select_related("deal", "rater__profile", "ratee__profile").all().order_by("-created_at")
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(
            models.Q(rater=self.request.user) | models.Q(ratee=self.request.user)
        )

    def perform_create(self, serializer):
        # Ensure rater is part of the deal
        deal = serializer.validated_data["deal"]
        if self.request.user not in [deal.applicant, deal.responder]:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only a party to the deal can provide a rating.")
        
        # Ensure rater can only rate once per deal
        # The unique constraint on (deal, rater) handles this, but we'll provide a clean error.
        serializer.save(rater=self.request.user)

    def get_queryset(self):
        # Users should only see deals they are part of
        return self.queryset.filter(
            models.Q(applicant=self.request.user) | models.Q(responder=self.request.user)
        )

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        deal = self.get_object()
        if deal.responder != request.user:
            return Response({"error": "Only the responder can accept the deal."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            deal_service.accept_deal(deal)
            return Response({"status": "Deal accepted successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        deal = self.get_object()
        if deal.responder != request.user:
            return Response({"error": "Only the responder can decline the deal."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            deal_service.decline_deal(deal)
            return Response({"status": "Deal declined successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        deal = self.get_object()
        if deal.applicant != request.user and deal.responder != request.user:
            return Response({"error": "You are not a party to this deal."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            deal_service.cancel_deal(deal)
            return Response({"status": "Deal cancelled successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def complete_meeting(self, request, pk=None):
        deal = self.get_object()
        try:
            deal_service.complete_meeting(deal)
            return Response({"status": "Meeting marked as complete."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LoanExtensionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Loan Extensions.
    """
    queryset = LoanExtension.objects.select_related("deal", "requested_by__profile", "approved_by__profile").all().order_by("-created_at")
    serializer_class = LoanExtensionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(
            models.Q(requested_by=self.request.user) | models.Q(deal__responder=self.request.user)
        )

    def perform_create(self, serializer):
        # Use extension_service to handle request_extension logic
        deal = serializer.validated_data["deal"]
        extra_days = serializer.validated_data["extra_days"]
        
        try:
            extension = extension_service.request_extension(
                deal=deal,
                applicant=self.request.user,
                extra_days=extra_days
            )
            return extension
        except Exception as e:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(str(e))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        extension = self.get_object()
        try:
            extension_service.approve_extension(extension, request.user)
            return Response({"status": "Extension approved."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        extension = self.get_object()
        try:
            extension_service.reject_extension(extension, request.user)
            return Response({"status": "Extension rejected successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
