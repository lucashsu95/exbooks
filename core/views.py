from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET
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


@require_GET
def robots_txt(request):
    """搜尋引擎：允許公開頁與 browse，禁止後台與需登入區域。"""
    sitemap_url = request.build_absolute_uri("/sitemap.xml")
    body = "\n".join(
        [
            "User-agent: *",
            "Disallow: /admin/",
            "Disallow: /accounts/",
            "Disallow: /deals/",
            "Disallow: /ai/",
            "Disallow: /books/",
            "Allow: /books/browse/",
            f"Sitemap: {sitemap_url}",
            "",
        ]
    )
    return HttpResponse(body, content_type="text/plain; charset=utf-8")
