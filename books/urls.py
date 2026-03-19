from django.urls import path

from . import views

app_name = "books"

urlpatterns = [
    path("", views.book_list, name="list"),
    path("bookshelf/", views.my_bookshelf, name="bookshelf"),
    path("all/", views.book_all, name="all"),
    path("add/", views.book_add, name="add"),
    path("<uuid:pk>/", views.book_detail, name="detail"),
    path("api/isbn-lookup/", views.isbn_lookup, name="isbn_lookup"),
    path("toggle-status/<uuid:pk>/", views.toggle_status, name="toggle_status"),
    # 願望書車
    path("wishlist/", views.wishlist_list, name="wishlist"),
    path("wishlist/toggle/<uuid:pk>/", views.wishlist_toggle, name="wishlist_toggle"),
    path("wishlist/remove/<uuid:pk>/", views.wishlist_remove, name="wishlist_remove"),
]
