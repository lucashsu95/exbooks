from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from books.sitemaps import PublicSharedBookSitemap, StaticViewSitemap
from core import views as core_views

SITEMAPS = {
    "static": StaticViewSitemap,
    "shared_books": PublicSharedBookSitemap,
}

admin.site.site_header = "Exbooks 後台管理"
admin.site.site_title = "Exbooks 管理者介面"
admin.site.index_title = "歡迎使用 Exbooks 共享書籍後台"

urlpatterns = [
    path("captcha/", include("captcha.urls")),
    path("robots.txt", core_views.robots_txt),
    path("health/", core_views.health_check, name="health_check"),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": SITEMAPS},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("admin/", admin.site.urls),
    path("set-language/", core_views.set_language, name="set_language"),
    # JWT Auth
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

# Language-prefixed URLs (e.g., /en/books/, /zh-hant/deals/)
urlpatterns += i18n_patterns(
    # django-allauth URLs (login, logout, signup, email verification, social auth)
    path("accounts/", include("allauth.urls")),
    # Local apps
    path("", core_views.landing_page, name="landing"),
    path("offline/", core_views.OfflineView.as_view(), name="offline"),
    path("accounts/", include("accounts.urls")),
    path("books/", include("books.urls")),
    path("deals/", include("deals.urls")),
    path("ai/", include("ai.urls")),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
