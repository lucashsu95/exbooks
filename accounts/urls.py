from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("profile/<int:user_id>/", views.public_profile, name="public_profile"),
    path("profile/<int:user_id>/ratings/", views.user_ratings, name="user_ratings"),
    # 補填 birth_date 流程（現有用戶）
    path("complete-profile/", views.complete_profile, name="complete_profile"),
    # 申訴相關路由
    path("appeals/", views.appeal_list, name="appeal_list"),
    path("appeals/new/", views.appeal_create, name="appeal_create"),
    path("appeals/<uuid:appeal_id>/", views.appeal_detail, name="appeal_detail"),
    path("appeals/<uuid:appeal_id>/cancel/", views.appeal_cancel, name="appeal_cancel"),
]
