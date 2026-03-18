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
]
