from django.contrib import admin

from .models import BookPhoto, BookSet, OfficialBook, SharedBook, WishListItem


class BookPhotoInline(admin.TabularInline):
    model = BookPhoto
    extra = 0
    fields = ('photo', 'caption', 'uploader', 'deal', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('uploader',)


class SharedBookInline(admin.TabularInline):
    model = SharedBook
    extra = 0
    fields = ('owner', 'keeper', 'status', 'transferability', 'loan_duration_days')
    autocomplete_fields = ('owner', 'keeper')
    show_change_link = True


@admin.register(OfficialBook)
class OfficialBookAdmin(admin.ModelAdmin):
    list_display = ('title', 'isbn', 'author', 'publisher', 'created_at')
    search_fields = ('title', 'isbn', 'author', 'publisher')
    list_filter = ('publisher',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [SharedBookInline]


@admin.register(BookSet)
class BookSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at')
    list_select_related = ('owner',)
    search_fields = ('name', 'owner__username')
    autocomplete_fields = ('owner',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SharedBook)
class SharedBookAdmin(admin.ModelAdmin):
    list_display = (
        'official_book', 'owner', 'keeper', 'status',
        'transferability', 'loan_duration_days', 'listed_at',
    )
    list_select_related = ('official_book', 'owner', 'keeper', 'book_set')
    list_filter = ('status', 'transferability')
    search_fields = (
        'official_book__title', 'official_book__isbn',
        'owner__username', 'keeper__username',
    )
    autocomplete_fields = ('official_book', 'owner', 'keeper', 'book_set')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [BookPhotoInline]


@admin.register(BookPhoto)
class BookPhotoAdmin(admin.ModelAdmin):
    list_display = ('shared_book', 'uploader', 'caption', 'deal', 'created_at')
    list_select_related = ('shared_book', 'shared_book__official_book', 'uploader', 'deal')
    list_filter = ('created_at',)
    search_fields = ('shared_book__official_book__title', 'caption')
    autocomplete_fields = ('shared_book', 'uploader', 'deal')
    readonly_fields = ('created_at',)


@admin.register(WishListItem)
class WishListItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'official_book', 'created_at')
    list_select_related = ('user', 'official_book')
    search_fields = ('user__username', 'official_book__title', 'official_book__isbn')
    autocomplete_fields = ('user', 'official_book')
    readonly_fields = ('created_at',)
