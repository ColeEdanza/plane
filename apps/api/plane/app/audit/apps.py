# CSFD fork: HIPAA-aligned audit log app. Routes its model to the 'audit' DB alias
# via plane.app.audit.db_router.AuditRouter; see DECISIONS.md (2026-05-25 audit log
# operational decisions) for fail-open + same-instance separate-DB rationale.

from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = "plane.app.audit"
    label = "audit"
    verbose_name = "Audit Log"

    def ready(self):
        # Register signal handlers (login / logout / login_failed)
        from plane.app.audit import signals  # noqa: F401
