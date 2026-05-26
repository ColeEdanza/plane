# CSFD fork: route the audit app to a separate logical database (alias "audit"),
# even though that DB lives on the same Postgres instance as Plane in prod.
# See DECISIONS.md (2026-05-25 audit log operational decisions).
#
# Behaviour: if the "audit" alias is NOT configured (e.g. local-dev convenience
# without a second DB set up yet), the router falls back to "default" so the
# app remains runnable. Production deployments MUST configure the alias.

from django.conf import settings


AUDIT_APP_LABEL = "audit"


def _audit_alias():
    return "audit" if "audit" in settings.DATABASES else "default"


class AuditRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == AUDIT_APP_LABEL:
            return _audit_alias()
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == AUDIT_APP_LABEL:
            return _audit_alias()
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # We intentionally do NOT relate audit rows to primary-DB rows via FK
        # — cross-DB relations are flaky and audit rows must outlive the rows
        # they reference. The user_id field is a bare UUID, not a ForeignKey.
        if obj1._meta.app_label == AUDIT_APP_LABEL and obj2._meta.app_label == AUDIT_APP_LABEL:
            return True
        if obj1._meta.app_label == AUDIT_APP_LABEL or obj2._meta.app_label == AUDIT_APP_LABEL:
            return False
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        alias = _audit_alias()
        if app_label == AUDIT_APP_LABEL:
            return db == alias
        # When audit DB is its own alias, keep other app migrations off it.
        if db == "audit":
            return False
        return None
