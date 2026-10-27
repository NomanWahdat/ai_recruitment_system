from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from apps.recruitment.models import Job, Candidate, Analysis, AuditEvent
from apps.recruitment.services.tasks import enqueue


class Command(BaseCommand):
    help = "Explicit administrator migration of unowned records. Preview by default."

    def add_arguments(self, parser):
        parser.add_argument("--owner", required=True)
        parser.add_argument("--apply", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            owner = User.objects.get(username=options["owner"])
        except User.DoesNotExist:
            raise CommandError("Unknown recruiter")
        jobs = Job.objects.filter(owner=None)
        candidates = Candidate.objects.filter(owner=None)
        self.stdout.write(f"Unowned jobs: {jobs.count()}, candidates: {candidates.count()}")
        if options["apply"]:
            jobs.update(owner=owner)
            candidates.update(
                owner=owner,
                retention_until=timezone.now() + timedelta(days=settings.CV_RETENTION_DAYS),
            )
            Analysis.objects.filter(job__owner=owner, candidate__owner=owner).update(
                is_stale=True, ranking_position=None
            )
            for job in Job.objects.filter(owner=owner):
                enqueue(owner, "match_job", job=job)
            AuditEvent.objects.create(
                owner=owner, action="legacy.assigned", target_type="migration", target_id="legacy"
            )
