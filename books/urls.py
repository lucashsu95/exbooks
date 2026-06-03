from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api_views import OfficialBookViewSet, SharedBookViewSet

router = DefaultRouter()
router.register(r"official", OfficialBookViewSet, basename="official")
router.register(r"shared", SharedBookViewSet, basename="shared")

app_name = "books"

urlpatterns = [
    # DRF API routes
    path("api/", include(router.urls)),
    # Web views (HTMX frontend)
    path("", views.book_list, name="list"),
    path("bookshelf/", views.my_bookshelf, name="bookshelf"),
    path("all/", views.book_all, name="all"),
    path("overdue/", views.overdue_list, name="overdue_list"),
    path("add/", views.book_add, name="add"),
    path("<uuid:pk>/", views.book_detail, name="detail"),
    path("<uuid:pk>/edit/", views.book_edit, name="edit"),
    path("<uuid:pk>/delete/", views.book_delete, name="delete"),
    path("api/isbn-lookup/", views.isbn_lookup, name="isbn_lookup"),
    path("toggle-status/<uuid:pk>/", views.toggle_status, name="toggle_status"),
    # 願望書車
    path("wishlist/", views.wishlist_list, name="wishlist"),
    path("wishlist/toggle/<uuid:pk>/", views.wishlist_toggle, name="wishlist_toggle"),
    path("wishlist/remove/<uuid:pk>/", views.wishlist_remove, name="wishlist_remove"),
    # 即將到期提醒
    path("due-soon/", views.due_soon_list, name="due_soon"),
    # 套書管理
    path("sets/", views.book_set_list, name="book_set_list"),
    path("sets/create/", views.book_set_create, name="book_set_create"),
    path("sets/<uuid:pk>/", views.book_set_detail, name="book_set_detail"),
    path("sets/<uuid:pk>/edit/", views.book_set_edit, name="book_set_edit"),
    path("sets/<uuid:pk>/delete/", views.book_set_delete, name="book_set_delete"),
    path("sets/<uuid:pk>/add-book/", views.book_set_add_book, name="book_set_add_book"),
    path(
        "sets/<uuid:pk>/remove-book/<uuid:book_id>/",
        views.book_set_remove_book,
        name="book_set_remove_book",
    ),
    # 書況照片
    path(
        "photos/<uuid:pk>/serve/",
        views.serve_protected_photo,
        name="serve_protected_photo",
    ),
    path("photos/<uuid:pk>/delete/", views.book_photo_delete, name="photo_delete"),
]
