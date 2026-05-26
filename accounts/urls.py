from django.urls import path
from . import views
from .api_views import UserProfileDetailView
from .views import download_user_data, get_export_status

app_name = "accounts"

urlpatterns = [
    # API views (Must come before web views if they share prefix)
    path("api/me/", UserProfileDetailView.as_view(), name="api_me"),
    # Web views
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    # Export routes
    path(
        "export/download/<str:format>/", download_user_data, name="download_user_data"
    ),
    path("export/status/", get_export_status, name="export_status"),
]
