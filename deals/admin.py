from django.contrib import admin
from django.utils.html import format_html

from .models import Deal, DealMessage, LoanExtension, Notification, Rating


class DealMessageInline(admin.TabularInline):
    model = DealMessage
    extra = 0
    fields = ("sender", "content", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("sender",)
    classes = ["collapse"]


class RatingInline(admin.TabularInline):
    model = Rating
    extra = 0
    fields = (
        "rater",
        "ratee",
        "friendliness_score",
        "punctuality_score",
        "accuracy_score",
        "comment",
    )
    autocomplete_fields = ("rater", "ratee")
    readonly_fields = ("created_at",)
    classes = ["collapse"]


class LoanExtensionInline(admin.TabularInline):
    model = LoanExtension
    extra = 0
    fields = (
        "requested_by",
        "owner_approved_by",
        "keeper_approved_by",
        "extra_days",
        "status",
        "created_at",
    )
    readonly_fields = ("created_at",)
    autocomplete_fields = ("requested_by", "owner_approved_by", "keeper_approved_by")
    classes = ["collapse"]


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = (
        "deal_type",
        "status_colored",
        "shared_book",
        "applicant",
        "responder",
        "due_date",
        "applicant_rated",
        "responder_rated",
        "created_at",
    )
    list_select_related = (
        "shared_book",
        "shared_book__official_book",
        "applicant",
        "responder",
        "book_set",
    )
    list_filter = ("deal_type", "status")
    search_fields = (
        "shared_book__official_book__title",
        "applicant__username",
        "responder__username",
    )
    autocomplete_fields = ("shared_book", "book_set", "applicant", "responder")
    readonly_fields = ("created_at", "updated_at", "previous_book_status")
    date_hierarchy = "created_at"
    inlines = [DealMessageInline, LoanExtensionInline, RatingInline]
    list_per_page = 20

    fieldsets = (
        (
            "交易基本資訊",
            {"fields": ("deal_type", "status", "shared_book", "book_set")},
        ),
        ("參與用戶", {"fields": ("applicant", "responder")}),
        ("時間與地點", {"fields": ("meeting_location", "meeting_time", "due_date")}),
        ("評價狀態", {"fields": ("applicant_rated", "responder_rated")}),
        (
            "系統資訊",
            {
                "fields": ("created_at", "updated_at", "previous_book_status"),
                "classes": ["collapse"],
            },
        ),
    )

    @admin.display(description="狀態")
    def status_colored(self, obj):
        colors = {
            "Q": "yellow",
            "P": "blue",
            "M": "orange",
            "D": "green",
            "X": "gray",
        }
        color = colors.get(obj.status, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )


@admin.register(DealMessage)
class DealMessageAdmin(admin.ModelAdmin):
    list_display = ("deal", "sender", "content_preview", "created_at")
    list_select_related = (
        "deal",
        "deal__shared_book",
        "deal__shared_book__official_book",
        "sender",
    )
    search_fields = ("content", "sender__username")
    autocomplete_fields = ("deal", "sender")
    readonly_fields = ("created_at",)
    list_per_page = 20

    @admin.display(description="訊息預覽")
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = (
        "deal",
        "rater",
        "ratee",
        "friendliness_score",
        "punctuality_score",
        "accuracy_score",
        "created_at",
    )
    list_select_related = (
        "deal",
        "deal__shared_book",
        "deal__shared_book__official_book",
        "rater",
        "ratee",
    )
    list_filter = ("friendliness_score", "punctuality_score", "accuracy_score")
    search_fields = ("rater__username", "ratee__username", "comment")
    autocomplete_fields = ("deal", "rater", "ratee")
    readonly_fields = ("created_at",)
    list_per_page = 20


@admin.register(LoanExtension)
class LoanExtensionAdmin(admin.ModelAdmin):
    list_display = (
        "deal",
        "requested_by",
        "owner_approved_by",
        "keeper_approved_by",
        "extra_days",
        "status",
        "created_at",
    )
    list_select_related = (
        "deal",
        "deal__shared_book",
        "deal__shared_book__official_book",
        "requested_by",
        "owner_approved_by",
        "keeper_approved_by",
    )
    list_filter = ("status",)
    search_fields = (
        "deal__shared_book__official_book__title",
        "requested_by__username",
    )
    autocomplete_fields = (
        "deal",
        "requested_by",
        "owner_approved_by",
        "keeper_approved_by",
    )
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 20


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "notification_type", "title", "is_read", "created_at")
    list_select_related = ("recipient", "deal", "shared_book")
    list_filter = ("notification_type", "is_read")
    search_fields = ("recipient__username", "title", "message")
    autocomplete_fields = ("recipient", "deal", "shared_book")
    readonly_fields = ("created_at",)
    list_per_page = 20
