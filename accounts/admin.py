from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('nickname', 'user', 'default_transferability', 'default_location', 'created_at')
    list_select_related = ('user',)
    search_fields = ('nickname', 'user__username', 'user__email')
    list_filter = ('default_transferability',)
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
