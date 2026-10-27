import signal
import time
import uuid

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.recruitment.models import WorkerHeartbeat
from apps.recruitment.services.tasks import run_one


class Command(BaseCommand):
    help = "Process persistent recruitment tasks separately from the web server."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Drain available tasks, then exit.")

    def handle(self, *args, **options):
        self.stopping = False
        heartbeat = WorkerHeartbeat.objects.create(worker_id=uuid.uuid4().hex)
        previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}

        def stop(*_):
            self.stopping = True

        for sig in previous:
            signal.signal(sig, stop)
        self.stdout.write("Recruitment worker ready")
        try:
            while not self.stopping:
                close_old_connections()
                heartbeat.save()
                if not run_one():
                    if options["once"]:
                        break
                    time.sleep(1)
        finally:
            WorkerHeartbeat.objects.filter(pk=heartbeat.pk).delete()
            for sig, handler in previous.items():
                signal.signal(sig, handler)
