from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.recruitment.models import Candidate


class Command(BaseCommand):
    help = "Preview unreferenced local CV files older than 24 hours. --apply deletes them."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        storage = Path(settings.MEDIA_ROOT).resolve()
        root = (storage / "cvs").resolve()
        if not root.is_relative_to(storage):
            raise CommandError("CV directory is outside configured media storage.")
        references = set(Candidate.objects.exclude(cv_file="").values_list("cv_file", flat=True))
        cutoff = (timezone.now() - timedelta(hours=24)).timestamp()
        candidates = []
        if root.exists():
            for item in root.rglob("*"):
                resolved = item.resolve()
                if resolved.is_relative_to(root) and item.is_file() and not item.is_symlink():
                    relative = item.relative_to(storage).as_posix()
                    if relative not in references and item.stat().st_mtime < cutoff:
                        candidates.append(item)
        self.stdout.write(f"Unreferenced CV files older than 24h: {len(candidates)}")
        for item in candidates:
            self.stdout.write(item.relative_to(storage).as_posix())
            if options["apply"]:
                item.unlink()
