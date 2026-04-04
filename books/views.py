from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.db.models import Q, Count
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError

from .models import SharedBook, OfficialBook, BookPhoto
from .services.isbn_service import lookup_by_isbn
from .services.book_service import list_book, suspend_book
from .services import process_book_photo
from .forms import BookSearchForm


def overdue_list(request):
    """公開逾期書籍展示頁面。"""
    from deals.services import overdue_service

    # 取得逾期 7 天以上的交易
    overdue_deals = overdue_service.get_overdue_books(days=7)

    # 格式化公開資訊
    overdue_info_list = [
        overdue_service.get_public_overdue_info(deal) for deal in overdue_deals
    ]

    return render(
        request,
        "books/overdue_list.html",
        {
            "overdue_info_list": overdue_info_list,
        },
    )


@login_required
def book_list(request):
    """首頁：探索與最新上架 (支援搜尋與分類)"""
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()

    new_query = (
        SharedBook.objects.select_related("official_book", "keeper__profile")
        .prefetch_related("photos")
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

    if request.headers.get("HX-Request"):
        return render(request, "books/partials/book_list_results.html", context)

    return render(request, "books/book_list.html", context)


@login_required
def book_detail(request, pk):
    """書籍詳情"""
    from books.services.book_timeline_service import BookTimelineService

    book = get_object_or_404(
        SharedBook.objects.select_related(
            "official_book", "keeper__profile", "owner__profile"
        ).prefetch_related("photos"),
        pk=pk,
    )

    # 使用服務層處理時間線邏輯
    timeline_events = BookTimelineService.get_timeline_events(book)
    photos = BookTimelineService.get_book_photos(book)
    in_wishlist = BookTimelineService.check_wishlist_status(
        request.user, book.official_book.id
    )

    from deals.models import Notification

    Notification.objects.filter(
        recipient=request.user,
        shared_book=book,
        is_read=False,
    ).update(is_read=True)

    return render(
        request,
        "books/book_detail.html",
        {
            "book": book,
            "timeline_events": timeline_events,
            "photos": photos,
            "in_wishlist": in_wishlist,
        },
    )


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
            .prefetch_related("photos")
            .filter(owner=request.user)
            .order_by("-updated_at")
        )
    elif tab == "requests":
        active_requests = (
            Deal.objects.select_related(
                "shared_book__official_book", "applicant", "responder"
            )
            .prefetch_related("shared_book__photos")
            .filter(Q(applicant=request.user) | Q(responder=request.user))
            .exclude(status__in=[Deal.Status.DONE, Deal.Status.CANCELLED])
            .order_by("-updated_at")
        )
    else:
        tab = "keeping"
        keeping_books = (
            SharedBook.objects.select_related("official_book", "owner__profile")
            .prefetch_related("photos")
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

    # 基礎查詢：只顯示可移轉 (T)
    all_books = (
        SharedBook.objects.select_related("official_book", "keeper__profile")
        .filter(status=SharedBook.Status.TRANSFERABLE)
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
            "current_transferability": transferability,
            "current_category": category,
            "form": form,
        },
    )


@login_required
def book_add(request):
    from .forms import BookAddForm

    if request.method == "POST":
        form = BookAddForm(request.POST, request.FILES)
        if form.is_valid():
            isbn = form.cleaned_data["isbn"]
            title = form.cleaned_data["title"]
            author = form.cleaned_data["author"]
            publisher = form.cleaned_data["publisher"]
            category = form.cleaned_data["category"]
            cover_url = request.POST.get("cover_url", "").strip()

            try:
                with transaction.atomic():
                    off_book, created = OfficialBook.objects.get_or_create(
                        isbn=isbn,
                        defaults={
                            "title": title,
                            "author": author,
                            "publisher": publisher,
                            "category": category,
                        },
                    )

                    if not created:
                        off_book.title = title
                        off_book.author = author
                        off_book.publisher = publisher
                        off_book.category = category
                        off_book.save(
                            update_fields=[
                                "title",
                                "author",
                                "publisher",
                                "category",
                                "updated_at",
                            ]
                        )

                    uploaded_cover = request.FILES.get("cover_image")
                    if uploaded_cover:
                        off_book.cover_image.save(
                            uploaded_cover.name, uploaded_cover, save=True
                        )
                    elif cover_url and not off_book.cover_image:
                        # Google Books 有封面 URL 且 OfficialBook 尚無封面，自動下載儲存
                        try:
                            import httpx
                            from django.core.files.base import ContentFile
                            import os

                            resp = httpx.get(
                                cover_url, timeout=10, follow_redirects=True
                            )
                            resp.raise_for_status()
                            ext = os.path.splitext(cover_url.split("?")[0])[1] or ".jpg"
                            filename = f"{off_book.pk}{ext}"
                            off_book.cover_image.save(
                                filename, ContentFile(resp.content), save=True
                            )
                        except Exception:
                            # 封面下載失敗不影響上架流程
                            pass

                    shared = form.save(commit=False)
                    shared.official_book = off_book
                    shared.owner = request.user
                    shared.keeper = request.user
                    shared.status = SharedBook.Status.TRANSFERABLE
                    shared.listed_at = timezone.now()
                    shared.save()

                    for image in request.FILES.getlist("photos"):
                        processed = process_book_photo(image)
                        BookPhoto.objects.create(
                            shared_book=shared,
                            uploader=request.user,
                            photo=processed,
                        )
            except ValidationError as e:
                messages.error(request, str(e))
                return render(request, "books/book_add.html", {"form": form})

            messages.success(request, "書籍已成功上架分享！")
            return redirect("books:bookshelf")
        messages.error(request, "書籍資料有誤，請檢查後再送出。")
    else:
        form = BookAddForm()

    return render(request, "books/book_add.html", {"form": form})


@login_required
def book_edit(request, pk):
    from .forms import BookEditForm

    if hasattr(request.user, "profile") and request.user.profile.trust_level == 0:
        messages.error(
            request, "新手等級 (Level 0) 尚無權限編輯書籍資訊，請多參與交易提升等級。"
        )
        return redirect("books:detail", pk=pk)

    book = get_object_or_404(SharedBook, pk=pk, owner=request.user)

    initial = {
        "title": book.official_book.title,
        "author": book.official_book.author,
        "publisher": book.official_book.publisher,
        "category": book.official_book.category,
    }

    if request.method == "POST":
        form = BookEditForm(request.POST, request.FILES, instance=book, initial=initial)
        if form.is_valid():
            try:
                with transaction.atomic():
                    official_book = book.official_book
                    official_book.title = form.cleaned_data["title"]
                    official_book.author = form.cleaned_data["author"]
                    official_book.publisher = form.cleaned_data["publisher"]
                    official_book.category = form.cleaned_data["category"]
                    official_book.save(
                        update_fields=[
                            "title",
                            "author",
                            "publisher",
                            "category",
                            "updated_at",
                        ]
                    )

                    form.save()

                    for image in request.FILES.getlist("photos"):
                        processed = process_book_photo(image)
                        BookPhoto.objects.create(
                            shared_book=book,
                            uploader=request.user,
                            photo=processed,
                        )
            except ValidationError as e:
                messages.error(request, str(e))
                return render(
                    request,
                    "books/book_edit.html",
                    {
                        "form": form,
                        "book": book,
                    },
                )

            messages.success(request, "書籍資料已更新。")
            return redirect("books:detail", pk=book.pk)
        messages.error(request, "更新失敗，請檢查欄位內容。")
    else:
        form = BookEditForm(instance=book, initial=initial)

    return render(
        request,
        "books/book_edit.html",
        {
            "form": form,
            "book": book,
        },
    )


@login_required
@require_POST
def book_delete(request, pk):
    """刪除書籍（僅 owner 可刪除）"""
    book = get_object_or_404(SharedBook, pk=pk, owner=request.user)
    title = book.official_book.title
    book.delete()
    messages.success(request, f"已刪除「{title}」")
    return redirect("books:bookshelf")


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
    if hasattr(request.user, "profile") and request.user.profile.trust_level == 0:
        messages.error(request, "新手等級 (Level 0) 尚無權限切換書籍狀態。")
        return HttpResponse("新手等級尚無權限", status=403)

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

from .services.wishlist_service import add_wish, remove_wish  # noqa: E402
from .models import WishListItem  # noqa: E402


@login_required
def wishlist_list(request):
    """願望書車列表頁"""
    # 使用 annotation 一次性計算可借閱冊數，避免 N+1 查詢
    wishlist_items = (
        WishListItem.objects.filter(user=request.user)
        .select_related("official_book")
        .annotate(
            available_count=Count(
                "official_book__shared_books",
                filter=Q(
                    official_book__shared_books__status=SharedBook.Status.TRANSFERABLE
                ),
            )
        )
        .order_by("-created_at")
    )

    # 建立分頁資料
    items_with_count = [
        {"item": item, "available_count": item.available_count}
        for item in wishlist_items
    ]

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


# ============================================
# 即將到期提醒
# ============================================


@login_required
def due_soon_list(request):
    """即將到期提醒：列出即將到期的借閱書籍"""
    from deals.models import Deal
    from datetime import timedelta

    # 計算提醒門檻（例如 7 天內到期）
    remind_days = int(request.GET.get("days", 7))
    now = timezone.now()
    deadline = now + timedelta(days=remind_days)

    # 查詢使用者作為借閱者且即將到期的交易
    due_soon_deals = (
        Deal.objects.filter(
            applicant=request.user,
            status=Deal.Status.MEETED,
            due_date__lte=deadline,
            due_date__gt=now,
        )
        .select_related("shared_book__official_book", "responder__profile")
        .order_by("due_date")
    )

    # 計算剩餘天數
    deals_with_days_left = []
    for deal in due_soon_deals:
        days_left = (deal.due_date - now).days
        deals_with_days_left.append(
            {
                "deal": deal,
                "days_left": days_left,
                "is_overdue": days_left <= 0,
            }
        )

    context = {
        "deals_with_days_left": deals_with_days_left,
        "remind_days": remind_days,
    }
    return render(request, "books/due_soon_list.html", context)


# ============================================
# 套書管理 Views
# ============================================

from .models import BookSet  # noqa: E402
from .services import (  # noqa: E402
    create_book_set,
    add_book_to_set,
    remove_book_from_set,
    delete_book_set,
    get_user_book_sets,
    get_book_set_detail,
)
from .forms import BookSetCreateForm  # noqa: E402


@login_required
def book_set_list(request):
    """套書列表頁"""
    book_sets = get_user_book_sets(request.user)
    return render(
        request,
        "books/book_set_list.html",
        {"book_sets": book_sets},
    )


@login_required
def book_set_create(request):
    """建立套書"""
    if request.method == "POST":
        form = BookSetCreateForm(request.POST)
        if form.is_valid():
            book_set = create_book_set(
                owner=request.user,
                name=form.cleaned_data["name"],
                description=form.cleaned_data.get("description", ""),
            )
            messages.success(request, "套書已建立")
            return redirect("books:book_set_detail", pk=book_set.pk)
    else:
        form = BookSetCreateForm()

    # 取得用戶可加入的書籍
    available_books = SharedBook.objects.filter(
        owner=request.user,
        book_set=None,
    ).select_related("official_book")

    return render(
        request,
        "books/book_set_create.html",
        {"form": form, "available_books": available_books},
    )


@login_required
def book_set_detail(request, pk):
    """套書詳情"""
    try:
        book_set = get_book_set_detail(pk, request.user)
    except Exception as e:
        messages.error(request, str(e))
        return redirect("books:book_set_list")

    books = book_set.books.select_related("official_book", "keeper").all()

    return render(
        request,
        "books/book_set_detail.html",
        {"book_set": book_set, "books": books},
    )


@login_required
def book_set_edit(request, pk):
    """編輯套書"""
    book_set = get_object_or_404(BookSet, pk=pk, owner=request.user)

    if request.method == "POST":
        form = BookSetCreateForm(request.POST, instance=book_set)
        if form.is_valid():
            form.save()
            messages.success(request, "套書已更新")
            return redirect("books:book_set_detail", pk=pk)
    else:
        form = BookSetCreateForm(instance=book_set)

    # 取得套書中的書籍和可加入的書籍
    books_in_set = book_set.books.select_related("official_book").all()
    available_books = SharedBook.objects.filter(
        owner=request.user,
        book_set=None,
    ).select_related("official_book")

    return render(
        request,
        "books/book_set_edit.html",
        {
            "form": form,
            "book_set": book_set,
            "books_in_set": books_in_set,
            "available_books": available_books,
        },
    )


@login_required
def book_set_delete(request, pk):
    """刪除套書"""
    book_set = get_object_or_404(BookSet, pk=pk, owner=request.user)

    if request.method == "POST":
        try:
            delete_book_set(book_set)
            messages.success(request, "套書已刪除")
        except Exception as e:
            messages.error(request, str(e))
        return redirect("books:book_set_list")

    return render(
        request,
        "books/book_set_delete_confirm.html",
        {"book_set": book_set},
    )


@login_required
@require_POST
def book_set_add_book(request, pk):
    """加入書籍到套書（HTMX）"""
    book_set = get_object_or_404(BookSet, pk=pk, owner=request.user)
    book_id = request.POST.get("book_id")

    if book_id:
        book = get_object_or_404(SharedBook, pk=book_id, owner=request.user)
        try:
            add_book_to_set(book_set, book)
            messages.success(request, f"已加入「{book.official_book.title}」")
        except Exception as e:
            messages.error(request, str(e))

    books = book_set.books.select_related("official_book").all()
    return render(
        request,
        "books/partials/book_set_books.html",
        {"book_set": book_set, "books": books},
    )


@login_required
@require_POST
def book_set_remove_book(request, pk, book_id):
    """從套書移除書籍（HTMX）"""
    book_set = get_object_or_404(BookSet, pk=pk, owner=request.user)
    book = get_object_or_404(SharedBook, pk=book_id, owner=request.user)

    try:
        remove_book_from_set(book_set, book)
        messages.success(request, f"已移除「{book.official_book.title}」")
    except Exception as e:
        messages.error(request, str(e))

    books = book_set.books.select_related("official_book").all()
    return render(
        request,
        "books/partials/book_set_books.html",
        {"book_set": book_set, "books": books},
    )


@login_required
@require_POST
def book_photo_delete(request, pk):
    """刪除書況照片（HTMX）。僅上傳者或書籍擁有者可刪除。"""
    photo = get_object_or_404(BookPhoto.objects.select_related("shared_book"), pk=pk)

    if request.user != photo.uploader and request.user != photo.shared_book.owner:
        return HttpResponse(status=403)

    photo.photo.delete(save=False)
    photo.delete()

    return HttpResponse(status=200)
