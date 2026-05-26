# CSFD fork: HIPAA-aligned per-request audit middleware. Records one
# AuditEvent row per API request after the response is produced. Fail-open:
# if the audit DB is unreachable, the user-facing request still succeeds
# and the failure is logged via plane logger (see DECISIONS.md — "Failure
# mode: fail-open"). Strict (fail-closed) mode is intentionally not
# implemented in v1; add a settings flag here if compliance review requires.
#
# Placement: in MIDDLEWARE this must sit AFTER AuthenticationMiddleware so
# request.user is populated, and AFTER plane.middleware.logger.RequestLogger
# so we record the same status_code the in-memory logger does. We intentionally
# do NOT replace RequestLoggerMiddleware — that one emits structured logs
# for ops observability; this one emits durable rows for compliance.

import logging
import time

from django.db import DatabaseError

from plane.utils.ip_address import get_client_ip


logger = logging.getLogger("plane.audit")


SKIP_PATHS = frozenset(
    [
        "/",  # health check
        "/health",
        "/healthz",
        "/ready",
        "/metrics",
        "/static",
    ]
)


def _should_audit(request) -> bool:
    path = request.path or ""
    if path in SKIP_PATHS:
        return False
    # Skip static asset serving even when not at /static exactly
    if path.startswith("/static/"):
        return False
    return True


class AuditMiddleware:
    """Persist one AuditEvent row per HTTP request to the audit DB.

    Fail-open: any exception writing to the audit DB is logged and swallowed.
    A persistent failure is detectable via the "plane.audit" logger which
    can be alerted on (Loki/Sentry/email — wired by ops, not this code).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration_ms = int((time.time() - start) * 1000)

        if not _should_audit(request):
            return response

        try:
            self._record(request, response, duration_ms)
        except DatabaseError:
            logger.warning(
                "audit DB unreachable; request not recorded",
                extra={
                    "path": request.path,
                    "method": request.method,
                    "status_code": getattr(response, "status_code", None),
                },
                exc_info=True,
            )
        except Exception:  # noqa: BLE001 — intentional fail-open
            logger.warning(
                "audit middleware error; request not recorded",
                extra={"path": request.path},
                exc_info=True,
            )

        return response

    def _record(self, request, response, duration_ms):
        # Local import so Django app-loading order during settings init is
        # not perturbed by importing the model at module load time.
        from plane.app.audit.models import AuditEvent

        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            user_id = user.id
            user_email = (user.email or "")[:255]
        else:
            user_id = None
            user_email = ""

        session = getattr(request, "session", None)
        session_key = (session.session_key or "")[:64] if session is not None else ""

        AuditEvent.objects.using("audit" if "audit" in _aliases() else "default").create(
            event_type=AuditEvent.EVENT_REQUEST,
            user_id=user_id,
            user_email=user_email,
            remote_addr=_safe_ip(request),
            user_agent=(request.META.get("HTTP_USER_AGENT", "") or "")[:8000],
            session_key=session_key,
            path=(request.path or "")[:2000],
            method=(request.method or "")[:10],
            status_code=getattr(response, "status_code", None),
            duration_ms=duration_ms,
        )


def _aliases():
    # Local import to avoid circular import during Django startup.
    from django.conf import settings

    return settings.DATABASES


def _safe_ip(request):
    ip = get_client_ip(request)
    if not ip:
        return None
    # GenericIPAddressField rejects empty / invalid — keep it None on parse fail.
    import ipaddress

    try:
        ipaddress.ip_address(ip.strip())
    except ValueError:
        return None
    return ip.strip()
