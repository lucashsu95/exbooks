from django.contrib import admin
from django.utils.html import format_html

from .models import UserProfile


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
