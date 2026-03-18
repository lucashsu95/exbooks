from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("profile/<int:user_id>/", views.public_profile, name="public_profile"),
    # 補填 birth_date 流程（現有用戶）
    path("complete-profile/", views.complete_profile, name="complete_profile"),
]
