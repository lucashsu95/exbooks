import logging
import time
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """Logs request/response information including timing and user identity.

    Adds a unique request_id to each request for tracing log entries.
    Sensitive headers (Authorization, Cookie) are excluded from logs.
    """

    SENSITIVE_HEADERS = {"cookie", "authorization", "proxy-authorization"}

    def process_request(self, request):
        request.request_id = str(uuid.uuid4())[:8]
        request._request_start_time = time.perf_counter()

    def process_response(self, request, response):
        duration = None
        start_time = getattr(request, "_request_start_time", None)
        if start_time:
            duration = time.perf_counter() - start_time

        user_info = "anonymous"
        if hasattr(request, "user") and request.user.is_authenticated:
            user_info = f"user:{request.user.pk}"

        log_extra = {
            "request_id": getattr(request, "request_id", "-"),
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "user": user_info,
        }
        if duration is not None:
            log_extra["duration_ms"] = round(duration * 1000, 2)

        if response.status_code >= 500:
            logger.error(
                "%s %s → %s (%s)",
                request.method,
                request.path,
                response.status_code,
                user_info,
                extra=log_extra,
            )
        elif response.status_code >= 400:
            logger.warning(
                "%s %s → %s (%s)",
                request.method,
                request.path,
                response.status_code,
                user_info,
                extra=log_extra,
            )
        else:
            logger.info(
                "%s %s → %s (%s)",
                request.method,
                request.path,
                response.status_code,
                user_info,
                extra=log_extra,
            )

        return response
