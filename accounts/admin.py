from django.contrib import admin, messages
from django.contrib.auth.models import Group
from django.utils import timezone
from django.utils.html import format_html

from .models import Appeal, TrustLevelConfig, UserProfile, Violation


@admin.register(TrustLevelConfig)
class TrustLevelConfigAdmin(admin.ModelAdmin):
    list_display = ("level", "display_name", "min_score", "max_books", "max_days")
    ordering = ("level",)


# 自定義 GroupAdmin 以控制用戶關聯的唯讀性
admin.site.unregister(Group)


@admin.register(Group)
class CustomGroupAdmin(admin.ModelAdmin):
    filter_horizontal = ("permissions",)
    list_display = ("name",)
    search_fields = ("name",)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.name.startswith("trust_lv"):
            return ("name", "permissions")
        return super().get_readonly_fields(request, obj)


    def has_change_permission(self, request, obj=None):
        # 需求：正向 Group (trust_lv*) 為唯讀
        if obj and obj.name.startswith("trust_lv"):
            return False
        # 負向 Group (restricted, banned) 保持可手動操作
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.name.startswith("trust_lv"):
            return False
        return super().has_delete_permission(request, obj)


class TrustLevelFilter(admin.SimpleListFilter):
    title = "信用等級"
    parameter_name = "trust_level_computed"

    def lookups(self, request, model_admin):
        return (
            ("0", "Lv.0 新手（積分 0-3）"),
            ("1", "Lv.1 一般（積分 4-8）"),
            ("2", "Lv.2 可信（積分 9-15）"),
            ("3", "Lv.3 優良（積分 16+）"),
        )

    def queryset(self, request, queryset):
        v = self.value()
        if v == "0":
            return queryset.filter(trust_score__lt=4)
        if v == "1":
            return queryset.filter(trust_score__gte=4, trust_score__lt=9)
        if v == "2":
            return queryset.filter(trust_score__gte=9, trust_score__lt=16)
        if v == "3":
            return queryset.filter(trust_score__gte=16)
        return queryset


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "nickname",
        "user",
        "avatar_preview",
        "get_trust_level_display",
        "suspension_status",
        "default_transferability",
        "created_at",
    )
    list_select_related = ("user",)
    search_fields = ("nickname", "user__username", "user__email")
    list_filter = ("default_transferability", "is_suspended", TrustLevelFilter)
    autocomplete_fields = ("user",)
    readonly_fields = (
        "avatar_preview",
        "created_at",
        "updated_at",
        "trust_level",
        "suspension_status_display",
    )
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
        (
            "信用與統計",
            {
                "fields": (
                    "trust_score",
                    "trust_level",
                    "successful_returns",
                    "overdue_count",
                )
            },
        ),
        (
            "停權狀態",
            {
                "fields": (
                    "is_suspended",
                    "suspension_end_date",
                    "suspension_reason",
                    "suspension_status_display",
                )
            },
        ),
        ("系統資訊", {"fields": ("created_at", "updated_at"), "classes": ["collapse"]}),
    )

    @admin.display(description="頭像預覽")
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="max-height: 50px;"/>', obj.avatar.url
            )
        return "-"

    @admin.display(description="停權狀態")
    def suspension_status(self, obj):
        if obj.is_currently_suspended:
            if obj.suspension_end_date:
                days_left = (obj.suspension_end_date - timezone.now()).days
                return format_html(
                    '<span style="color: orange; font-weight: bold;">暫停中（剩餘 {} 天）</span>',
                    days_left,
                )
            return format_html(
                '<span style="color: red; font-weight: bold;">永久停權</span>'
            )
        return format_html('<span style="color: green;">正常</span>')

    @admin.display(description="停權狀態詳情")
    def suspension_status_display(self, obj):
        return self.suspension_status(obj)

    @admin.display(description="信用等級", ordering="trust_score")
    def get_trust_level_display(self, obj):
        return f"Lv.{obj.trust_level}"

    actions = [
        "suspend_temporary",
        "suspend_permanent",
        "lift_suspension",
        "reset_suspension",
    ]

    @admin.action(description="暫時停權（7天）")
    def suspend_temporary(self, request, queryset):
        count = 0
        for profile in queryset.filter(is_suspended=False):
            profile.is_suspended = True
            profile.suspension_end_date = timezone.now() + timezone.timedelta(days=7)
            profile.suspension_reason = "管理員執行暫時停權（7天）"
            profile.save(
                update_fields=[
                    "is_suspended",
                    "suspension_end_date",
                    "suspension_reason",
                    "updated_at",
                ]
            )
            count += 1
        self.message_user(request, f"已對 {count} 位用戶執行暫時停權", messages.SUCCESS)

    @admin.action(description="永久停權")
    def suspend_permanent(self, request, queryset):
        count = queryset.filter(is_suspended=False).update(
            is_suspended=True,
            suspension_end_date=None,
            suspension_reason="管理員執行永久停權",
            updated_at=timezone.now(),
        )
        self.message_user(request, f"已對 {count} 位用戶執行永久停權", messages.WARNING)

    @admin.action(description="解除停權")
    def lift_suspension(self, request, queryset):
        count = queryset.filter(is_suspended=True).update(
            is_suspended=False,
            suspension_end_date=None,
            suspension_reason="",
            updated_at=timezone.now(),
        )
        self.message_user(request, f"已解除 {count} 位用戶的停權狀態", messages.SUCCESS)

    @admin.action(description="重置停權狀態（清除所有停權資訊）")
    def reset_suspension(self, request, queryset):
        count = queryset.update(
            is_suspended=False,
            suspension_end_date=None,
            suspension_reason="",
            updated_at=timezone.now(),
        )
        self.message_user(request, f"已重置 {count} 位用戶的停權狀態", messages.SUCCESS)


@admin.register(Violation)
class ViolationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "action_type_colored",
        "severity",
        "violation_type",
        "is_active",
        "created_at",
        "created_by",
    ]
    list_filter = [
        "action_type",
        "severity",
        "violation_type",
        "is_active",
        "created_at",
    ]
    search_fields = ["id", "user__email", "user__username", "description"]
    list_select_related = ["user", "created_by", "lifted_by"]
    readonly_fields = ["id", "created_at", "updated_at", "lifted_at", "lifted_by"]
    autocomplete_fields = ["user", "created_by", "related_appeal"]
    ordering = ["-created_at"]

    fieldsets = (
        (
            "基本資訊",
            {"fields": ("id", "user", "action_type", "severity", "violation_type")},
        ),
        ("處分內容", {"fields": ("description", "suspension_days", "is_active")}),
        ("相關申訴", {"fields": ("related_appeal",)}),
        (
            "處分者資訊",
            {"fields": ("created_by", "created_at")},
        ),
        (
            "解除資訊",
            {"fields": ("lifted_at", "lifted_by"), "classes": ["collapse"]},
        ),
        ("系統", {"fields": ("updated_at",), "classes": ["collapse"]}),
    )

    @admin.display(description="處分類型")
    def action_type_colored(self, obj):
        colors = {
            Violation.ActionType.WARNING: "green",
            Violation.ActionType.TEMPORARY_SUSPENSION: "orange",
            Violation.ActionType.PERMANENT_SUSPENSION: "red",
        }
        color = colors.get(obj.action_type, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_action_type_display(),
        )

    actions = [
        "issue_warning",
        "issue_temporary_suspension",
        "issue_permanent_suspension",
        "lift_violation",
    ]

    @admin.action(description="發出警告")
    def issue_warning(self, request, queryset):
        count = queryset.filter(
            action_type=Violation.ActionType.WARNING, is_active=True
        ).count()
        self.message_user(request, f"{count} 筆警告已發出")

    @admin.action(description="提前解除處分")
    def lift_violation(self, request, queryset):
        count = 0
        for violation in queryset.filter(is_active=True):
            violation.lift(request.user)
            count += 1
        self.message_user(request, f"已解除 {count} 筆處分", messages.SUCCESS)


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
