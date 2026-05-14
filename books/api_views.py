from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from books.models.official_book import OfficialBook
from books.serializers import OfficialBookSerializer

class OfficialBookViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows OfficialBooks to be viewed and searched.
    """
    queryset = OfficialBook.objects.all().order_by("id")
    serializer_class = OfficialBookSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["title", "author", "isbn"]
