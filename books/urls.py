from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, views_public
from .api_views import OfficialBookViewSet

router = DefaultRouter()
router.register(r"official", OfficialBookViewSet, basename="official")

app_name = "books"

urlpatterns = [
    # API views
    path("api/", include(router.urls)),
    
    # Web views
    path("", views.book_list, name="list"),
    path("detail/<uuid:pk>/", views.book_detail, name="detail"),
]


