from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def book_list(request):
    """書籍列表（暫時佔位）。"""
    return render(request, 'books/book_list.html')
