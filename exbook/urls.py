from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

admin.site.site_header = "Exbooks 後台管理"
admin.site.site_title = "Exbooks 管理者介面"
admin.site.index_title = "歡迎使用 Exbooks 共享書籍後台"

urlpatterns = [
    path("admin/", admin.site.urls),
    # Auth (Django built-in)
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # Apps
    path("", include("accounts.urls")),
    path("books/", include("books.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
