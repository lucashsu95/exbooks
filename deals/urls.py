"""
交易相關 URL 路由。
"""

from django.urls import path
from . import views

app_name = "deals"

urlpatterns = [
    path("", views.deal_list, name="list"),
    path("create/<uuid:book_id>/<str:deal_type>/", views.deal_create, name="create"),
    path("<uuid:pk>/", views.deal_detail, name="detail"),
    path("<uuid:pk>/accept/", views.deal_accept, name="accept"),
    path("<uuid:pk>/reject/", views.deal_reject, name="reject"),
    path("<uuid:pk>/cancel/", views.deal_cancel, name="cancel"),
    path("<uuid:pk>/complete/", views.deal_complete_meeting, name="complete"),
    path("<uuid:pk>/message/", views.deal_message_send, name="message_send"),
    path("<uuid:pk>/rate/", views.rating_create, name="rating_create"),
    # Web Push
    path(
        "push/vapid-public-key/",
        views.push_vapid_public_key,
        name="push_vapid_public_key",
    ),
    path("push/subscribe/", views.push_subscribe, name="push_subscribe"),
    path("push/unsubscribe/", views.push_unsubscribe, name="push_unsubscribe"),
]
