# CSFD fork: HIPAA-aligned audit event row. One row per HTTP request,
# auth event, or webhook-consumed model change. Lives in the plane_audit
# database (separate logical DB on the same Postgres instance) — see
# db_router.py for routing and sql/bootstrap.sql for DB/role provisioning.
#
# Append-only at the DB role level in production (Plane connects as
# plane_writer which has INSERT-only on this table). The model intentionally
# does NOT inherit from plane.db.models.base.BaseModel because BaseModel
# expects a "created_by"/"updated_by" FK back to the User table which lives
# in the default DB — cross-DB FKs are not enforced and add noise.

import uuid

from django.db import models


class AuditEvent(models.Model):
    EVENT_REQUEST = "request"
    EVENT_LOGIN = "login"
    EVENT_LOGOUT = "logout"
    EVENT_LOGIN_FAILED = "login_failed"
    EVENT_WEBHOOK = "webhook"

    EVENT_CHOICES = [
        (EVENT_REQUEST, "HTTP request"),
        (EVENT_LOGIN, "Login success"),
        (EVENT_LOGOUT, "Logout"),
        (EVENT_LOGIN_FAILED, "Login failed"),
        (EVENT_WEBHOOK, "Webhook-observed model change"),
    ]

    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    event_type = models.CharField(max_length=32, choices=EVENT_CHOICES, db_index=True)

    # Actor — user_id may be null for unauthenticated / failed-login events.
    # We store the email too so the audit row is still useful if the User row
    # is later deleted in the primary DB.
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    user_email = models.CharField(max_length=255, blank=True, default="")

    # Request metadata
    remote_addr = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    session_key = models.CharField(max_length=64, blank=True, default="")
    path = models.TextField(blank=True, default="")
    method = models.CharField(max_length=10, blank=True, default="")
    status_code = models.IntegerField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)

    # Webhook-sourced events: identifies which model/object was touched.
    model_name = models.CharField(max_length=64, blank=True, default="", db_index=True)
    object_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    action = models.CharField(max_length=32, blank=True, default="")  # create / update / delete

    # Free-form structured detail — webhook payload digest, error info, etc.
    # Never store full PHI bodies here; the webhook consumer is responsible
    # for stripping payloads to identifiers + changed fields only.
    payload = models.JSONField(null=True, blank=True)

    # Review tracking (HIPAA periodic-review requirement). Flipped manually
    # from a small god-mode view (Tier 2 follow-up).
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by_email = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        app_label = "audit"
        db_table = "audit_events"
        indexes = [
            models.Index(fields=["timestamp", "event_type"]),
            models.Index(fields=["user_id", "timestamp"]),
        ]
        # No ordering by default — high-volume table, callers must paginate
        # and filter by timestamp range explicitly.

    def __str__(self):
        ts = self.timestamp.isoformat() if self.timestamp else "?"
        email = self.user_email or "-"
        return f"{self.event_type} {ts} {email}"
