"""Contextvars-based trace context for distributed tracing across HTTP requests and Celery tasks.

This module provides utilities for generating and propagating trace identifiers
across process boundaries, enabling distributed tracing in a contextvars-aware
environment. It supports HTTP request tracing, Celery task propagation, and
business event logging.

The implementation uses Python's contextvars module to maintain trace context
within the current execution context, allowing for proper isolation between
concurrent requests and tasks.
"""

import contextvars
import uuid

_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_span_id: contextvars.ContextVar[str] = contextvars.ContextVar("span_id", default="")
_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def new_trace() -> str:
    """Initialize a new trace: generate trace_id + span_id, set both contextvars.
    
    Returns:
        The generated trace_id.
    """
    tid = uuid.uuid4().hex[:16]
    sid = uuid.uuid4().hex[:8]
    _trace_id.set(tid)
    _span_id.set(sid)
    return tid


def new_span() -> str:
    """Create a new span_id under the current trace (for child operations like Celery tasks).
    
    Returns:
        The generated span_id.
    """
    sid = uuid.uuid4().hex[:8]
    _span_id.set(sid)
    return sid


def get_trace_id() -> str:
    """Get the current trace ID."""
    return _trace_id.get()


def get_span_id() -> str:
    """Get the current span ID."""
    return _span_id.get()


def get_request_id() -> str:
    """Get the current request ID."""
    return _request_id.get()


def set_request_id(rid: str):
    """Set the request ID."""
    _request_id.set(rid)


def inject_headers() -> dict:
    """Produce headers dict for propagating trace context across process boundaries.
    
    Returns:
        Dictionary containing trace, span, and request IDs as HTTP headers.
    """
    return {
        "X-Trace-ID": get_trace_id(),
        "X-Span-ID": get_span_id(),
        "X-Request-ID": get_request_id(),
    }


def extract_headers(headers: dict):
    """Restore trace context from incoming headers (e.g., Celery message headers).
    
    Args:
        headers: Dictionary containing trace context headers.
    """
    if "X-Trace-ID" in headers:
        _trace_id.set(headers["X-Trace-ID"])
    if "X-Span-ID" in headers:
        _span_id.set(headers["X-Span-ID"])
    if "X-Request-ID" in headers:
        _request_id.set(headers["X-Request-ID"])


def clear():
    """Clear all trace context (useful for eager mode cleanup)."""
    _trace_id.set("")
    _span_id.set("")
    _request_id.set("")