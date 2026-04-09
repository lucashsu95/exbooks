from django.shortcuts import render, redirect


def landing_page(request):
    """
    Public marketing landing page for Exbooks.
    Redirects authenticated users to their book list.
    """
    if request.user.is_authenticated:
        return redirect("books:list")
    return render(request, "core/landing.html")
