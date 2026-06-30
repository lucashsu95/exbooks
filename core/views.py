import logging
from urllib import parse as urlparse

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import activate, check_for_language
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
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
    from core.observability.business_events import emit_business_event
    from core.observability.business_events import emit_audit_event

    try:
        connection.ensure_connection()
        db_status = "ok" if connection.is_usable() else "unhealthy"
        status_code = 200 if db_status == "ok" else 503
        logger.info("health_check", extra={"db_status": db_status, "status_code": status_code})
        
        # --- TEMPORARY FOR OBSERVABILITY VERIFICATION ---
        emit_business_event("obs.verify_health", {"status": "triggered"})
        emit_audit_event("obs.verify_health", {"action": "verification_access"})
        # -----------------------------------------------
        
    except Exception:
        db_status = "unhealthy"
        status_code = 503
        logger.exception("health_check failed", extra={"db_status": db_status, "status_code": status_code})

    except Exception:
        db_status = "unhealthy"
        status_code = 503
        logger.exception("health_check failed", extra={"db_status": db_status, "status_code": status_code})

    payload = {
        "status": "ok" if db_status == "ok" else "unhealthy",
        "database": db_status,
    }
    response = JsonResponse(payload, status=status_code)
    if request.GET.get("meow") == "1":
        response["X-Exbooks-Cat"] = "🐱 喵！系統很健康，貓咪也很開心～"
    return response


SUPPORTED_LANGS = {code for code, _ in settings.LANGUAGES}


def _strip_lang_prefix(path: str) -> str:
    has_trailing_slash = path != "/" and path.endswith("/")
    parts = path.strip("/").split("/")
    if parts and parts[0] in SUPPORTED_LANGS:
        stripped = "/" + "/".join(parts[1:]) if len(parts) > 1 else "/"
        if has_trailing_slash and not stripped.endswith("/"):
            stripped += "/"
        return stripped
    return path


def _add_lang_prefix(path: str, lang_code: str) -> str:
    if lang_code == settings.LANGUAGE_CODE:
        return path
    if path == "/":
        return f"/{lang_code}/"
    return f"/{lang_code}{path}"


@csrf_protect
@never_cache
def set_language(request):
    """
    Custom language switcher that correctly handles i18n_patterns with
    ``prefix_default_language=False``.

    Django's built-in ``translate_url`` only works from the default
    (unprefixed) URL — it returns the original URL unchanged when called
    on a prefixed URL like ``/en/books/``.  This means the redirect always
    goes back to the old-language URL and ``LocaleMiddleware`` re-activates
    that language via the prefix, making it impossible to switch away from
    a non-default locale.

    This view strips the old prefix from *next* and applies the new one.
    """
    next_url = request.POST.get("next", request.GET.get("next"))
    if (
        next_url or request.accepts("text/html")
    ) and not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = request.META.get("HTTP_REFERER")
        if not url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = "/"

    response = HttpResponseRedirect(next_url) if next_url else HttpResponse(status=204)

    lang_code = request.POST.get("language")
    if request.method == "POST" and lang_code and check_for_language(lang_code):
        parsed = urlparse.urlparse(next_url)
        clean_path = _strip_lang_prefix(parsed.path)
        new_path = _add_lang_prefix(clean_path, lang_code)
        if parsed.scheme:
            corrected = f"{parsed.scheme}://{parsed.netloc}{new_path}"
        else:
            corrected = new_path
        if parsed.fragment:
            corrected += f"#{parsed.fragment}"
        response = HttpResponseRedirect(request.build_absolute_uri(corrected))
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            lang_code,
            max_age=settings.LANGUAGE_COOKIE_AGE,
            path=settings.LANGUAGE_COOKIE_PATH,
            domain=settings.LANGUAGE_COOKIE_DOMAIN,
            secure=settings.LANGUAGE_COOKIE_SECURE,
            httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
            samesite=settings.LANGUAGE_COOKIE_SAMESITE,
        )

    return response
