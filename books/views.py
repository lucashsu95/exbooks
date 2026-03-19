from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.core.paginator import Paginator

from .models import SharedBook, OfficialBook
from .services.isbn_service import lookup_by_isbn
from .services.book_service import list_book, suspend_book
from .forms import BookSearchForm


@login_required
def book_list(request):
    """首頁：探索與最新上架 (支援搜尋與分類)"""
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()

    new_query = (
        SharedBook.objects.select_related("official_book", "keeper__profile")
        .filter(status=SharedBook.Status.TRANSFERABLE)
        .exclude(keeper=request.user)
    )

    nearby_query = new_query

    if q:
        new_query = new_query.filter(
            Q(official_book__title__icontains=q)
            | Q(official_book__author__icontains=q)
            | Q(official_book__isbn__icontains=q)
        )
        nearby_query = nearby_query.filter(
            Q(official_book__title__icontains=q)
            | Q(official_book__author__icontains=q)
            | Q(official_book__isbn__icontains=q)
        )

    if category and category != "全部":
        new_query = new_query.filter(official_book__category=category)
        nearby_query = nearby_query.filter(official_book__category=category)

    new_arrivals = new_query.order_by("-updated_at")[:10]

    user_location = ""
    if hasattr(request.user, "profile"):
        user_location = request.user.profile.default_location

    if user_location:
        nearby_books = nearby_query.filter(
            keeper__profile__default_location__icontains=user_location
        )[:10]
        if not nearby_books:
            nearby_books = nearby_query.order_by("?")[:10]
    else:
        nearby_books = nearby_query.order_by("?")[:10]

    context = {
        "new_arrivals": new_arrivals,
        "nearby_books": nearby_books,
        "search_query": q,
        "current_category": category or "全部",
    }
    return render(request, "books/book_list.html", context)


@login_required
def book_detail(request, pk):
    """書籍詳情"""
    book = get_object_or_404(
        SharedBook.objects.select_related(
            "official_book", "keeper__profile", "owner__profile"
        ),
        pk=pk,
    )
    return render(request, "books/book_detail.html", {"book": book})


@login_required
def my_bookshelf(request):
    """我的書架：目前持有的書籍、我的貢獻、進行中的請求"""
    tab = request.GET.get("tab", "keeping")
    from deals.models import Deal

    keeping_books = []
    contributions_books = []
    active_requests = []

    if tab == "contributions":
        contributions_books = (
            SharedBook.objects.select_related("official_book", "keeper__profile")
            .filter(owner=request.user)
            .order_by("-updated_at")
        )
    elif tab == "requests":
        active_requests = (
            Deal.objects.select_related(
                "shared_book__official_book", "applicant", "responder"
            )
            .filter(Q(applicant=request.user) | Q(responder=request.user))
            .exclude(status__in=[Deal.Status.DONE, Deal.Status.CANCELLED])
            .order_by("-updated_at")
        )
    else:
        tab = "keeping"
        keeping_books = (
            SharedBook.objects.select_related("official_book", "owner__profile")
            .filter(keeper=request.user)
            .order_by("-updated_at")
        )

    context = {
        "current_tab": tab,
        "keeping_books": keeping_books,
        "contributions_books": contributions_books,
        "active_requests": active_requests,
    }
    return render(request, "books/my_bookshelf.html", context)


@login_required
def book_all(request):
    """查看全部（支援搜尋、篩選、分頁）"""
    # 使用 BookSearchForm 處理 GET 參數
    form = BookSearchForm(request.GET)

    # 基礎查詢
    all_books = (
        SharedBook.objects.select_related("official_book", "keeper__profile")
        .exclude(keeper=request.user)
        .order_by("-updated_at")
    )

    # 搜尋
    q = request.GET.get("q", "").strip()
    if q:
        all_books = all_books.filter(
            Q(official_book__title__icontains=q)
            | Q(official_book__author__icontains=q)
            | Q(official_book__isbn__icontains=q)
            | Q(official_book__publisher__icontains=q)
        )

    # 狀態篩選
    status = request.GET.get("status", "").strip()
    if status:
        all_books = all_books.filter(status=status)

    # 流通性篩選
    transferability = request.GET.get("transferability", "").strip()
    if transferability:
        all_books = all_books.filter(transferability=transferability)

    # 分類篩選
    category = request.GET.get("category", "").strip()
    if category:
        all_books = all_books.filter(official_book__category=category)

    # 分頁（每頁 12 筆）
    paginator = Paginator(all_books, 12)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "books/book_all.html",
        {
            "page_obj": page_obj,
            "search_query": q,
            "current_status": status,
            "current_transferability": transferability,
            "current_category": category,
            "form": form,
        },
    )


@login_required
def book_add(request):
    from .forms import BookAddForm

    if request.method == "POST":
        form = BookAddForm(request.POST)
        if form.is_valid():
            isbn = form.cleaned_data["isbn"]
            title = form.cleaned_data["title"]
            author = form.cleaned_data["author"]

            off_book, created = OfficialBook.objects.get_or_create(
                isbn=isbn, defaults={"title": title, "author": author}
            )

            shared = form.save(commit=False)
            shared.official_book = off_book
            shared.owner = request.user
            shared.keeper = request.user
            shared.status = SharedBook.Status.TRANSFERABLE
            shared.listed_at = timezone.now()
            shared.save()

            messages.success(request, "書籍已成功上架分享！")
            return redirect("books:bookshelf")
    else:
        form = BookAddForm()

    return render(request, "books/book_add.html", {"form": form})


@require_GET
def isbn_lookup(request):
    """HTMX endpoint: ISBN 查詢"""
    isbn = request.GET.get("isbn", "")
    result = lookup_by_isbn(isbn) if isbn else None
    return render(
        request,
        "books/partials/isbn_result.html",
        {"result": result, "isbn": isbn},
    )


@login_required
@require_POST
def toggle_status(request, pk):
    """切換書籍狀態 S ↔ T"""
    book = get_object_or_404(SharedBook, pk=pk, owner=request.user)
    if book.status == SharedBook.Status.SUSPENDED:
        list_book(book)
        messages.success(request, "書籍已開放借閱")
    elif book.status == SharedBook.Status.TRANSFERABLE:
        suspend_book(book)
        messages.success(request, "書籍已暫停借閱")
    else:
        messages.error(request, "書籍狀態無法切換")
        return HttpResponse("書籍狀態無法切換", status=400)
    return render(request, "books/partials/status_toggle.html", {"book": book})


# ============================================
# 願望書車相關 Views
# ============================================

from .services.wishlist_service import add_wish, remove_wish
from .models import WishListItem


@login_required
def wishlist_list(request):
    """願望書車列表頁"""
    wishlist_items = (
        WishListItem.objects.filter(user=request.user)
        .select_related("official_book")
        .order_by("-created_at")
    )

    # 計算每本書的可借閱冊數
    items_with_count = []
    for item in wishlist_items:
        available_count = SharedBook.objects.filter(
            official_book=item.official_book,
            status=SharedBook.Status.TRANSFERABLE,
        ).count()
        items_with_count.append(
            {
                "item": item,
                "available_count": available_count,
            }
        )

    # 分頁
    paginator = Paginator(items_with_count, 12)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "books/wishlist.html",
        {"page_obj": page_obj, "wishlist_items": wishlist_items},
    )


@login_required
@require_POST
def wishlist_toggle(request, pk):
    """切換願望書車狀態（加入/移除）"""
    from django.core.exceptions import ValidationError

    official_book = get_object_or_404(OfficialBook, pk=pk)

    # 檢查是否已在願望書車中
    existing = WishListItem.objects.filter(
        user=request.user,
        official_book=official_book,
    ).first()

    if existing:
        # 移除
        remove_wish(request.user, official_book)
        messages.success(request, "已從願望書車移除")
        in_wishlist = False
    else:
        # 加入
        try:
            add_wish(request.user, official_book)
            messages.success(request, "已加入願望書車")
            in_wishlist = True
        except ValidationError as e:
            messages.error(request, str(e))
            in_wishlist = False

    return render(
        request,
        "books/partials/wishlist_button.html",
        {"official_book": official_book, "in_wishlist": in_wishlist},
    )


@login_required
@require_POST
def wishlist_remove(request, pk):
    """從願望書車移除"""
    from django.core.exceptions import ValidationError

    official_book = get_object_or_404(OfficialBook, pk=pk)

    try:
        remove_wish(request.user, official_book)
        messages.success(request, "已從願望書車移除")
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect("books:wishlist")
