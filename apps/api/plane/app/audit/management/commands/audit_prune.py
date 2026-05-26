# CSFD fork: retention pruning for the audit table. Default 73 months
# (6 years + safety margin) per DECISIONS.md. Runs as a separate role
# (audit_pruner) in production — the role HAS DELETE on audit_events but
# nothing else has DELETE. See sql/bootstrap.sql.

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


DEFAULT_RETENTION_MONTHS = 73


class Command(BaseCommand):
    help = "Delete audit_events rows older than the retention window (default 73 months)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--months",
            type=int,
            default=DEFAULT_RETENTION_MONTHS,
            help=f"Retention window in months (default {DEFAULT_RETENTION_MONTHS}).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report the row count that would be deleted, but do not delete.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=10000,
            help="Delete in batches of this size to keep transactions small.",
        )

    def handle(self, *args, **options):
        from plane.app.audit.models import AuditEvent

        months = options["months"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        cutoff = timezone.now() - timedelta(days=int(months * 30.44))

        qs = AuditEvent.objects.filter(timestamp__lt=cutoff)
        count = qs.count()

        if dry_run or count == 0:
            self.stdout.write(
                f"audit_prune: cutoff={cutoff.isoformat()} would delete {count} rows"
                + (" (dry-run)" if dry_run else "")
            )
            return

        deleted_total = 0
        while True:
            ids = list(
                AuditEvent.objects.filter(timestamp__lt=cutoff)
                .values_list("id", flat=True)[:batch_size]
            )
            if not ids:
                break
            n, _ = AuditEvent.objects.filter(id__in=ids).delete()
            deleted_total += n
            self.stdout.write(f"audit_prune: deleted batch of {n} (cumulative {deleted_total})")

        self.stdout.write(
            self.style.SUCCESS(
                f"audit_prune: deleted {deleted_total} rows older than {cutoff.isoformat()}"
            )
        )
