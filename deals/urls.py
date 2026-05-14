from django.urls import path, include
from . import views
from .api_views import DealViewSet, LoanExtensionViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"deals", DealViewSet, basename="deal")
router.register(r"extensions", LoanExtensionViewSet, basename="extension")

app_name = "deals"

urlpatterns = [
    path("api/", include(router.urls)),
]

