"""公開書籍瀏覽（免登入，供 SEO／社群預覽）。不包含持有者個資。"""

import json

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import SharedBook
from .views import PILL_CATEGORIES


def _public_book_queryset():
    return (
        SharedBook.objects.select_related("official_book")
        .prefetch_related("photos")
        .filter(status=SharedBook.Status.TRANSFERABLE)
    )


@require_GET
def public_book_list(request):
    """可索引的書籍列表（僅顯示可移轉中的分享冊）。"""
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()

    base = _public_book_queryset()
    filtered = base

    if q:
        filtered = filtered.filter(
            Q(official_book__title__icontains=q)
            | Q(official_book__author__icontains=q)
            | Q(official_book__isbn__icontains=q)
        )

    if category and category != "全部":
        filtered = filtered.filter(official_book__category=category)

    filtered = filtered.order_by("-listed_at", "-updated_at")

    paginator = Paginator(filtered, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    featured_books = list(base.order_by("-listed_at", "-updated_at")[:3])

    canonical = request.build_absolute_uri(request.path)
    if request.GET:
        canonical = request.build_absolute_uri("/books/browse/")

    context = {
        "page_obj": page_obj,
        "featured_books": featured_books,
        "search_query": q,
        "current_category": category or "全部",
        "categories": PILL_CATEGORIES,
        "canonical_url": canonical,
        "page_title": "探索可借閱書籍",
        "meta_description": "Exbooks 公開書單：目前在社群中開放借閱／傳遞的書籍（不需登入即可瀏覽書目）。",
    }
    return render(request, "books/public/browse_list.html", context)


@require_GET
def public_book_detail(request, pk):
    """公開書籍詳情（不含持有者聯絡與地點）。"""
    book = get_object_or_404(
        _public_book_queryset()
        .select_related("official_book", "official_book__publisher_ref")
        .prefetch_related("official_book__author_links__author"),
        pk=pk,
    )
    ob = book.official_book
    title = ob.title
    desc = (ob.description or "")[:300]

    canonical_url = request.build_absolute_uri(request.path)
    og_image_url = ""
    if ob.cover_image:
        og_image_url = request.build_absolute_uri(ob.cover_image.url)

    context = {
        "book": book,
        "canonical_url": canonical_url,
        "page_title": title,
        "meta_description": desc or f"{title} — Exbooks 共享書籍",
        "og_title": f"{title} | Exbooks",
        "og_description": desc or title,
        "og_image_url": og_image_url,
        "book_json_ld": json.dumps(
            _build_book_json_ld(request, book), ensure_ascii=False
        ),
    }
    return render(request, "books/public/browse_detail.html", context)


def _build_book_json_ld(request, book):
    """Schema.org Book（公開詳情頁）。"""
    ob = book.official_book
    url = request.build_absolute_uri(request.path)
    data = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": ob.title,
        "isbn": ob.isbn,
        "url": url,
    }
    links = sorted(
        ob.author_links.all(),
        key=lambda x: (x.sort_order, x.created_at),
    )
    if links:
        data["author"] = [
            {"@type": "Person", "name": link.author.display_name} for link in links
        ]
    elif ob.author:
        data["author"] = {"@type": "Person", "name": ob.author}
    if ob.publisher_ref_id:
        data["publisher"] = {
            "@type": "Organization",
            "name": ob.publisher_ref.name,
        }
    elif ob.publisher:
        data["publisher"] = {"@type": "Organization", "name": ob.publisher}
    if ob.description:
        data["description"] = ob.description[:5000]
    if ob.cover_image:
        data["image"] = request.build_absolute_uri(ob.cover_image.url)
    return data
