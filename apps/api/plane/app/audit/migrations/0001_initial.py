import uuid

import django.db.models
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("request", "HTTP request"),
                            ("login", "Login success"),
                            ("logout", "Logout"),
                            ("login_failed", "Login failed"),
                            ("webhook", "Webhook-observed model change"),
                        ],
                        db_index=True,
                        max_length=32,
                    ),
                ),
                ("user_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("user_email", models.CharField(blank=True, default="", max_length=255)),
                ("remote_addr", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True, default="")),
                ("session_key", models.CharField(blank=True, default="", max_length=64)),
                ("path", models.TextField(blank=True, default="")),
                ("method", models.CharField(blank=True, default="", max_length=10)),
                ("status_code", models.IntegerField(blank=True, null=True)),
                ("duration_ms", models.IntegerField(blank=True, null=True)),
                (
                    "model_name",
                    models.CharField(blank=True, db_index=True, default="", max_length=64),
                ),
                (
                    "object_id",
                    models.CharField(blank=True, db_index=True, default="", max_length=64),
                ),
                ("action", models.CharField(blank=True, default="", max_length=32)),
                ("payload", models.JSONField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_by_email", models.CharField(blank=True, default="", max_length=255)),
            ],
            options={
                "db_table": "audit_events",
            },
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["timestamp", "event_type"], name="audit_event_timesta_idx"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["user_id", "timestamp"], name="audit_event_user_id_idx"),
        ),
    ]
