from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from books.models.official_book import OfficialBook
from books.models.shared_book import SharedBook
from books.serializers import OfficialBookSerializer, SharedBookSerializer
from books.services import book_service


class OfficialBookViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows OfficialBooks to be viewed and searched.
    """

    queryset = OfficialBook.objects.all().order_by("id")
    serializer_class = OfficialBookSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["title", "author", "isbn"]


class SharedBookViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing SharedBooks.
    """

    queryset = (
        SharedBook.objects.select_related(
            "official_book", "owner__profile", "keeper__profile"
        )
        .all()
        .order_by("-listed_at")
    )
    serializer_class = SharedBookSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = [
        "official_book__title",
        "official_book__author",
        "condition_description",
    ]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_update(self, serializer):
        # Ensure only the owner can update the book
        if serializer.instance.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only the owner can update this book.")
        serializer.save()

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def list_for_transfer(self, request, pk=None):
        """
        Mark the book as transferable (T).
        """
        book = self.get_object()
        if book.owner != request.user:
            return Response(
                {"error": "Only the owner can perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            book_service.list_book(book)
            # The service might handle the transition.
            # According to models.py, we should use the FSM transition method.
            # If book_service.list_book already calls book.list_for_transfer(), it's fine.
            return Response(
                {"status": "Book listed for transfer successfully."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def suspend(self, request, pk=None):
        """
        Suspend the book (S).
        """
        book = self.get_object()
        if book.owner != request.user:
            return Response(
                {"error": "Only the owner can perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            book_service.suspend_book(book)
            return Response(
                {"status": "Book suspended successfully."}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
