"""
Celery signal handlers for trace context propagation.

Automatically injects trace/span/request IDs into task headers when a task
is published from within a traced HTTP request, and restores them in the
worker process so all logging in the task carries the same trace_id.
"""

from celery.signals import before_task_publish, task_prerun, task_postrun
from core.observability.trace_context import (
    inject_headers,
    extract_headers,
    new_span,
    clear,
)
@before_task_publish.connect
def inject_trace_context_into_task(headers, **kwargs):
    """Inject current trace context into Celery task headers before publishing."""
    # Celery passes headers as a dict, but may be None in older versions
    if headers is None:
        return
    headers.update(inject_headers())
@task_prerun.connect
def restore_trace_context_in_worker(task_id, task, **kwargs):
    """Restore trace context from Celery task headers when worker starts the task."""
    headers = getattr(task.request, "headers", {}) or {}
    extract_headers(headers)
    # Create a new span for this task execution
    new_span()
@task_postrun.connect
def cleanup_trace_context(**kwargs):
    """Clear trace context after task completes to prevent leakage (esp. in eager mode)."""
    clear()