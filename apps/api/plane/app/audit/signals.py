# CSFD fork: capture Django auth signals (login / logout / login_failed)
# as AuditEvent rows. These fire whenever auth views call django.contrib.auth.login
# / logout / authenticate. Plane uses django.contrib.auth, so these signals
# DO fire for the email + magic-link + OAuth flows. (If a future auth backend
# bypasses django.contrib.auth.login, audit coverage falls back to the per-
# request middleware capture of the auth POST endpoint, which is sufficient.)

import logging

from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db import DatabaseError
from django.dispatch import receiver

from plane.utils.ip_address import get_client_ip


logger = logging.getLogger("plane.audit")


def _safe_record(event_type, *, user=None, request=None, credentials=None):
    """Best-effort record. Same fail-open posture as the middleware."""
    try:
        from plane.app.audit.models import AuditEvent
        from django.conf import settings

        alias = "audit" if "audit" in settings.DATABASES else "default"

        if user is not None and getattr(user, "is_authenticated", False):
            user_id = user.id
            user_email = (user.email or "")[:255]
        elif user is not None and getattr(user, "email", None):
            # AnonymousUser with email — unusual but defensive
            user_id = None
            user_email = (user.email or "")[:255]
        else:
            user_id = None
            user_email = ""

        # For login_failed we don't get a User object — credentials dict has
        # the attempted username/email. We capture the email-shaped value
        # but never the password (credentials may contain "password" key).
        if not user_email and credentials:
            for key in ("email", "username"):
                val = credentials.get(key)
                if val:
                    user_email = str(val)[:255]
                    break

        remote_addr = None
        user_agent = ""
        session_key = ""
        path = ""
        method = ""
        if request is not None:
            ip = get_client_ip(request)
            if ip:
                import ipaddress

                try:
                    ipaddress.ip_address(ip.strip())
                    remote_addr = ip.strip()
                except ValueError:
                    remote_addr = None
            user_agent = (request.META.get("HTTP_USER_AGENT", "") or "")[:8000]
            session = getattr(request, "session", None)
            session_key = (session.session_key or "")[:64] if session is not None else ""
            path = (request.path or "")[:2000]
            method = (request.method or "")[:10]

        AuditEvent.objects.using(alias).create(
            event_type=event_type,
            user_id=user_id,
            user_email=user_email,
            remote_addr=remote_addr,
            user_agent=user_agent,
            session_key=session_key,
            path=path,
            method=method,
        )
    except DatabaseError:
        logger.warning("audit DB unreachable; %s not recorded", event_type, exc_info=True)
    except Exception:  # noqa: BLE001
        logger.warning("audit signal handler error for %s", event_type, exc_info=True)


@receiver(user_logged_in)
def _on_login(sender, request, user, **kwargs):
    _safe_record("login", user=user, request=request)


@receiver(user_logged_out)
def _on_logout(sender, request, user, **kwargs):
    _safe_record("logout", user=user, request=request)


@receiver(user_login_failed)
def _on_login_failed(sender, credentials, request=None, **kwargs):
    # NOTE: credentials may contain a "password" key — _safe_record only
    # extracts email/username and never persists the credentials dict.
    _safe_record("login_failed", request=request, credentials=credentials)
