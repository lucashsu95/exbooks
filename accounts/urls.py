from django.urls import path
from . import views
from .api_views import UserProfileDetailView

app_name = "accounts"

urlpatterns = [
    # API views (Must come before web views if they share prefix)
    path("api/me/", UserProfileDetailView.as_view(), name="api_me"),
    
    # Web views
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
]

