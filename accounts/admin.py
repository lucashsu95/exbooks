from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import Appeal, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "nickname",
        "user",
        "avatar_preview",
        "default_transferability",
        "default_location",
        "created_at",
    )
    list_select_related = ("user",)
    search_fields = ("nickname", "user__username", "user__email")
    list_filter = ("default_transferability",)
    autocomplete_fields = ("user",)
    readonly_fields = ("avatar_preview", "created_at", "updated_at")
    list_per_page = 20

    fieldsets = (
        ("關聯帳號", {"fields": ("user", "nickname")}),
        (
            "偏好設定",
            {
                "fields": (
                    "default_transferability",
                    "default_location",
                    "available_schedule",
                )
            },
        ),
        ("頭像", {"fields": ("avatar", "avatar_preview")}),
        ("系統資訊", {"fields": ("created_at", "updated_at"), "classes": ["collapse"]}),
    )

    @admin.display(description="頭像預覽")
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="max-height: 50px;"/>', obj.avatar.url
            )
        return "-"


@admin.register(Appeal)
class AppealAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "appeal_type",
        "title",
        "status",
        "created_at",
        "resolved_by",
    ]
    list_filter = ["status", "appeal_type", "created_at"]
    search_fields = ["id", "user__email", "title", "description"]
    list_select_related = ["user", "resolved_by"]
    readonly_fields = ["id", "created_at", "updated_at", "resolved_at"]
    ordering = ["-created_at"]

    fieldsets = (
        ("基本資訊", {"fields": ("id", "user", "appeal_type", "status")}),
        ("內容", {"fields": ("title", "description", "evidence")}),
        ("審核", {"fields": ("resolution_notes", "resolved_by", "resolved_at")}),
        ("系統", {"fields": ("created_at", "updated_at"), "classes": ["collapse"]}),
    )

    actions = ["mark_under_review", "mark_approved", "mark_rejected"]

    @admin.action(description="標記為審核中")
    def mark_under_review(self, request, queryset):
        count = queryset.filter(status=Appeal.Status.SUBMITTED).update(
            status=Appeal.Status.UNDER_REVIEW
        )
        self.message_user(request, f"{count} 件申訴已標記為審核中")

    @admin.action(description="審核通過")
    def mark_approved(self, request, queryset):
        count = queryset.filter(status=Appeal.Status.UNDER_REVIEW).update(
            status=Appeal.Status.APPROVED,
            resolved_by=request.user,
            resolved_at=timezone.now(),
        )
        self.message_user(request, f"{count} 件申訴已審核通過")

    @admin.action(description="審核駁回")
    def mark_rejected(self, request, queryset):
        count = queryset.filter(status=Appeal.Status.UNDER_REVIEW).update(
            status=Appeal.Status.REJECTED,
            resolved_by=request.user,
            resolved_at=timezone.now(),
        )
        self.message_user(request, f"{count} 件申訴已審核駁回")
