# CSFD fork: thin celery wrappers around the audit management commands so
# the existing celery beat infra in plane/celery.py can schedule them.
# Importing inside the task body keeps Django app loading lazy.

from celery import shared_task


@shared_task(name="plane.app.audit.tasks.weekly_summary")
def weekly_summary():
    from django.core.management import call_command

    call_command("audit_weekly_summary")


@shared_task(name="plane.app.audit.tasks.prune")
def prune():
    from django.core.management import call_command

    call_command("audit_prune")
