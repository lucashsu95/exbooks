import logging

from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)


def landing_page(request):
    """
    Public marketing landing page for Exbooks.
    Redirects authenticated users to their book list.
    """
    logger.info("landing_page", extra={"user_id": request.user.pk, "authenticated": request.user.is_authenticated})
    if request.user.is_authenticated:
        return redirect("books:list")
    return render(request, "core/landing.html")


class OfflineView(TemplateView):
    """PWA Offline Fallback View"""

    template_name = "offline.html"


@require_GET
def robots_txt(request):
    """搜尋引擎：允許公開頁與 browse，禁止後台與需登入區域。"""
    logger.debug("robots_txt served")
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


@require_GET
def health_check(request):
    """Return app and database health status for deploy probes."""
    from django.db import connection

    try:
        connection.ensure_connection()
        db_status = "ok" if connection.is_usable() else "unhealthy"
        status_code = 200 if db_status == "ok" else 503
        logger.info("health_check", extra={"db_status": db_status, "status_code": status_code})
    except Exception:
        db_status = "unhealthy"
        status_code = 503
        logger.exception("health_check failed", extra={"db_status": db_status, "status_code": status_code})

    payload = {
        "status": "ok" if db_status == "ok" else "unhealthy",
        "database": db_status,
    }
    return JsonResponse(payload, status=status_code)
