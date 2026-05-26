# CSFD fork: weekly audit summary mailer. Sent to AUDIT_REVIEW_EMAIL
# (default dr@cs.dental — see DECISIONS.md "Privacy-officer email").
# Covers the trailing 7 days; intentionally a digest, not the raw log.
# Per-row review remains a human task in the (future) god-mode review UI.

from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone


class Command(BaseCommand):
    help = "Email a weekly audit-log summary to the privacy officer."

    def handle(self, *args, **options):
        from plane.app.audit.models import AuditEvent

        recipient = getattr(settings, "AUDIT_REVIEW_EMAIL", "dr@cs.dental")
        sender = getattr(
            settings,
            "AUDIT_REVIEW_FROM_EMAIL",
            getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@cs.dental"),
        )

        since = timezone.now() - timedelta(days=7)
        qs = AuditEvent.objects.filter(timestamp__gte=since)

        total = qs.count()
        by_type = list(qs.values("event_type").annotate(n=Count("id")).order_by("-n"))
        failed_logins = qs.filter(event_type=AuditEvent.EVENT_LOGIN_FAILED).count()
        unique_users = qs.exclude(user_id__isnull=True).values("user_id").distinct().count()
        unique_ips = qs.exclude(remote_addr__isnull=True).values("remote_addr").distinct().count()
        unreviewed = qs.filter(reviewed_at__isnull=True).count()
        top_paths = list(
            qs.exclude(path="")
            .values("path")
            .annotate(n=Count("id"))
            .order_by("-n")[:10]
        )

        lines = [
            "Plane audit summary - trailing 7 days",
            f"Window: {since.isoformat()} -> {timezone.now().isoformat()}",
            "",
            f"Total events:    {total}",
            f"Failed logins:   {failed_logins}",
            f"Unique users:    {unique_users}",
            f"Unique IPs:      {unique_ips}",
            f"Unreviewed rows: {unreviewed}",
            "",
            "By event type:",
        ]
        for row in by_type:
            et = row["event_type"]
            n = row["n"]
            lines.append(f"  {et:<15} {n}")
        lines.append("")
        lines.append("Top 10 paths by hit count:")
        for row in top_paths:
            n = row["n"]
            path = row["path"]
            lines.append(f"  {n:>6}  {path}")
        lines.append("")
        lines.append(
            "Review action: open the audit DB and mark rows reviewed_at via the "
            "god-mode review UI (or psql) once human review is complete."
        )

        body = "\n".join(lines)
        subject = f"[Plane audit] Weekly summary - {total} events, {failed_logins} failed logins"

        send_mail(
            subject=subject,
            message=body,
            from_email=sender,
            recipient_list=[recipient],
            fail_silently=False,
        )

        self.stdout.write(self.style.SUCCESS(f"Sent audit summary to {recipient} ({total} events)"))
