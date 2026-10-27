import json

from django.core.management.base import BaseCommand, CommandError

from apps.recruitment.services.ai.router import AIRouter


class Command(BaseCommand):
    help = "Show redacted AI configuration. --live sends a fixed synthetic connection test."

    def add_arguments(self, parser):
        parser.add_argument("--live", action="store_true")

    def handle(self, *args, **options):
        router = AIRouter()
        self.stdout.write(json.dumps(router.configuration(), indent=2))
        if options["live"]:
            result = router.test_connection()
            self.stdout.write(json.dumps(result, indent=2))
            if not result["ok"]:
                raise CommandError(
                    "No AI provider returned a valid response. See diagnostics above."
                )
