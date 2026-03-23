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
    # 延長借閱
    path(
        "<uuid:deal_pk>/extension/request/",
        views.extension_request,
        name="extension_request",
    ),
    path(
        "extension/<uuid:extension_pk>/approve/",
        views.extension_approve,
        name="extension_approve",
    ),
    path(
        "extension/<uuid:extension_pk>/reject/",
        views.extension_reject,
        name="extension_reject",
    ),
    path(
        "extension/<uuid:extension_pk>/cancel/",
        views.extension_cancel,
        name="extension_cancel",
    ),
    # 通知
    path("notifications/", views.notification_list, name="notification_list"),
    path("notifications/count/", views.notification_count, name="notification_count"),
    path(
        "notifications/<uuid:pk>/read/",
        views.notification_mark_read,
        name="notification_mark_read",
    ),
    path(
        "notifications/read-all/",
        views.notification_mark_all_read,
        name="notification_mark_all_read",
    ),
    # 書籍歸還確認
    path("<uuid:pk>/confirm-return/", views.deal_confirm_return, name="confirm_return"),
    # 例外處理
    path(
        "exception/create/<uuid:book_id>/",
        views.exception_create,
        name="exception_create",
    ),
    path(
        "exception/<uuid:pk>/resolve/",
        views.exception_resolve,
        name="exception_resolve",
    ),
]
