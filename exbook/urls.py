from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from core import views as core_views

admin.site.site_header = "Exbooks 後台管理"
admin.site.site_title = "Exbooks 管理者介面"
admin.site.index_title = "歡迎使用 Exbooks 共享書籍後台"

urlpatterns = [
    path("admin/", admin.site.urls),
    # django-allauth URLs (包含 login, logout, signup, email verification, social auth)
    path("accounts/", include("allauth.urls")),
    # Local apps
    path("", core_views.landing_page, name="landing"),
    path("offline/", core_views.OfflineView.as_view(), name="offline"),
    path("accounts/", include("accounts.urls")),
    path("books/", include("books.urls")),
    path("deals/", include("deals.urls")),
    path("ai/", include("ai.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
