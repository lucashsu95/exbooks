from django.shortcuts import render, redirect
from django.views.generic import TemplateView


def landing_page(request):
    """
    Public marketing landing page for Exbooks.
    Redirects authenticated users to their book list.
    """
    if request.user.is_authenticated:
        return redirect("books:list")
    return render(request, "core/landing.html")


class OfflineView(TemplateView):
    """PWA Offline Fallback View"""

    template_name = "offline.html"
