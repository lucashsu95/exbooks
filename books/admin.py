from django.contrib import admin
from django.db.models import Prefetch
from django.utils.html import format_html

from .models import (
    Author,
    BookPhoto,
    BookSet,
    OfficialBook,
    OfficialBookAuthor,
    Publisher,
    SharedBook,
    WishListItem,
)


class BookPhotoInline(admin.TabularInline):
    model = BookPhoto
    extra = 0
    fields = ("photo", "caption", "uploader", "deal", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("uploader",)


class SharedBookInline(admin.TabularInline):
    model = SharedBook
    extra = 0
    fields = ("owner", "keeper", "status", "transferability", "loan_duration_days")
    autocomplete_fields = ("owner", "keeper")
    show_change_link = True


class OfficialBookAuthorInline(admin.TabularInline):
    model = OfficialBookAuthor
    extra = 0
    autocomplete_fields = ("author",)
    fields = ("author", "role", "sort_order")


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("display_name", "sort_key", "created_at")
    search_fields = ("display_name", "sort_key")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("sort_key", "display_name")


@admin.register(OfficialBook)
class OfficialBookAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "isbn",
        "author_columns",
        "publisher_display",
        "cover_image_preview",
        "created_at",
    )
    search_fields = (
        "title",
        "isbn",
        "author",
        "publisher",
        "publisher_ref__name",
        "author_links__author__display_name",
    )
    list_filter = ("category", "publisher_ref")
    readonly_fields = ("cover_image_preview", "created_at", "updated_at")
    list_per_page = 20
    inlines = [OfficialBookAuthorInline, SharedBookInline]

    fieldsets = (
        (
            "基本資訊",
            {
                "fields": (
                    "title",
                    "isbn",
                    "category",
                    "author",
                    "publisher",
                    "publisher_ref",
                )
            },
        ),
        ("詳細資訊", {"fields": ("cover_image", "cover_image_preview", "description")}),
        (
            "系統資訊",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("publisher_ref").prefetch_related(
            Prefetch(
                "author_links",
                queryset=OfficialBookAuthor.objects.select_related("author").order_by(
                    "sort_order", "created_at"
                ),
            )
        )

    @admin.display(description="作者（優先正規化）")
    def author_columns(self, obj):
        links = list(obj.author_links.all())
        if links:
            parts = []
            for link in links:
                suffix = (
                    f"（{link.get_role_display()}）"
                    if link.role != OfficialBookAuthor.Role.AUTHOR
                    else ""
                )
                parts.append(f"{link.author.display_name}{suffix}")
            return "、".join(parts)
        return obj.author or "—"

    @admin.display(description="出版社（優先正規化）", ordering="publisher_ref__name")
    def publisher_display(self, obj):
        if obj.publisher_ref_id:
            return obj.publisher_ref.name
        return obj.publisher or "—"

    @admin.display(description="封面預覽")
    def cover_image_preview(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="max-height: 50px;" />', obj.cover_image.url
            )
        return "無圖片"


@admin.register(BookSet)
class BookSetAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    list_select_related = ("owner",)
    search_fields = ("name", "owner__username")
    autocomplete_fields = ("owner",)
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 20


@admin.register(SharedBook)
class SharedBookAdmin(admin.ModelAdmin):
    list_display = (
        "official_book",
        "owner",
        "keeper",
        "status_colored",
        "transferability",
        "loan_duration_days",
        "listed_at",
    )
    list_select_related = ("official_book", "owner", "keeper", "book_set")
    list_filter = ("status", "transferability")
    search_fields = (
        "official_book__title",
        "official_book__isbn",
        "owner__username",
        "keeper__username",
    )
    autocomplete_fields = ("official_book", "owner", "keeper", "book_set")
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 20
    inlines = [BookPhotoInline]

    fieldsets = (
        ("書籍關聯", {"fields": ("official_book", "book_set")}),
        ("持有人資訊", {"fields": ("owner", "keeper")}),
        (
            "借閱設定",
            {
                "fields": (
                    "status",
                    "transferability",
                    "loan_duration_days",
                    "extend_duration_days",
                    "listed_at",
                )
            },
        ),
        (
            "系統資訊",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="狀態", ordering="status")
    def status_colored(self, obj):
        colors = {
            "T": "green",
            "O": "orange",
            "R": "red",
            "V": "blue",
            "S": "gray",
        }
        color = colors.get(obj.status, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )


@admin.register(BookPhoto)
class BookPhotoAdmin(admin.ModelAdmin):
    list_display = (
        "shared_book",
        "uploader",
        "photo_preview",
        "caption",
        "deal",
        "created_at",
    )
    list_select_related = (
        "shared_book",
        "shared_book__official_book",
        "uploader",
        "deal",
    )
    list_filter = ("created_at",)
    search_fields = ("shared_book__official_book__title", "caption")
    autocomplete_fields = ("shared_book", "uploader", "deal")
    readonly_fields = ("photo_preview", "created_at")
    list_per_page = 20

    @admin.display(description="照片預覽")
    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-height: 50px;" />', obj.photo.url
            )
        return "無圖片"


@admin.register(WishListItem)
class WishListItemAdmin(admin.ModelAdmin):
    list_display = ("user", "official_book", "created_at")
    list_select_related = ("user", "official_book")
    search_fields = ("user__username", "official_book__title", "official_book__isbn")
    autocomplete_fields = ("user", "official_book")
    readonly_fields = ("created_at",)
