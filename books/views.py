from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Prefetch, Q
from django.contrib import messages
from django.utils import timezone

from .models import SharedBook, OfficialBook


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
    """查看全部"""
    all_books = (
        SharedBook.objects.select_related("official_book", "keeper__profile")
        .filter(status=SharedBook.Status.TRANSFERABLE)
        .exclude(keeper=request.user)
        .order_by("-updated_at")
    )

    return render(request, "books/book_all.html", {"all_books": all_books})


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
