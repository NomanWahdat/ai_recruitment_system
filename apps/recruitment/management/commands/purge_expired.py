from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.recruitment.models import Candidate, AuditEvent
from apps.recruitment.services.audit import record


class Command(BaseCommand):
    help = "Preview retention deletion; pass --apply to delete expired profiles and files."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        rows = Candidate.objects.filter(retention_until__lte=timezone.now())
        self.stdout.write(f"Expired candidates: {rows.count()}")
        if options["apply"]:
            for candidate in rows:
                record(candidate.owner, "candidate.retention_deleted", candidate)
                candidate.delete()
            # Keep audit identifiers for one year; no raw profile text is stored.
            AuditEvent.objects.filter(created_at__lt=timezone.now() - timedelta(days=365)).delete()
