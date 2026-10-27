import hashlib
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.recruitment.models import Job, Candidate, Application
from apps.recruitment.services.tasks import enqueue, run_one
from apps.recruitment.services.audit import record
from apps.recruitment.utils.validators import build_safe_filename
from tools.fixtures import docx_bytes, pdf_bytes


class Command(BaseCommand):
    help = "Create idempotent synthetic local demo data, including a real unreadable-PDF failure."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="PortfolioDemo!2026")
        parser.add_argument("--reset-password", action="store_true")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo seeding is restricted to development/test settings.")
        owner, created = User.objects.get_or_create(
            username="portfolio_demo",
            defaults={
                "email": "portfolio-demo@example.com",
                "first_name": "Portfolio",
                "last_name": "Demo",
            },
        )
        if created or options["reset_password"]:
            owner.set_password(options["password"])
            owner.save()
        jobs = []
        for title, skills in [
            ("Backend Engineer", ["Python", "Django", "PostgreSQL"]),
            ("Frontend Engineer", ["React", "TypeScript"]),
        ]:
            job, new = Job.objects.get_or_create(
                owner=owner,
                title=title,
                defaults={
                    "company_name": "Synthetic Research Lab",
                    "description": "Build reliable, well-tested applications. Required skills: "
                    + ", ".join(skills),
                    "required_skills": skills,
                    "minimum_experience": 2,
                    "education_requirement": "Bachelor of Computer Science",
                    "scoring_weights": {"skills": 0.5, "experience": 0.3, "education": 0.2},
                },
            )
            jobs.append(job)
            if new:
                record(owner, "job.created", job)
        samples = [
            (
                "Kate Example",
                "kate@example.com",
                "Kate Example\nkate@example.com\nSkills\nPython, Django, PostgreSQL\nExperience\nJan 2020 - Jan 2022\nJan 2023 - Jan 2025\nEducation\nBachelor of Computer Science",
            ),
            (
                "Alex Example",
                "alex@example.com",
                "Alex Example\nalex [at] example [dot] com\nSummary\n3 years professional experience\nSkills\nReact, TypeScript\nEducation\nBachelor of Computer Science",
            ),
            ("Unreadable Demo", "unreadable@example.com", ""),
        ]
        for name, email, text in samples:
            candidate, new = Candidate.objects.get_or_create(
                owner=owner,
                email=email,
                defaults={
                    "full_name": name,
                    "retention_until": timezone.now() + timedelta(days=settings.CV_RETENTION_DAYS),
                },
            )
            if new:
                content = docx_bytes(text) if text else pdf_bytes("")
                filename = build_safe_filename(name + (".docx" if text else ".pdf"))
                candidate.cv_file.save(filename, ContentFile(content), save=False)
                candidate.cv_sha256 = hashlib.sha256(content).hexdigest()
                candidate.save()
                enqueue(owner, "extract", candidate=candidate)
                record(owner, "candidate.created", candidate)
            Application.objects.get_or_create(job=jobs[0], candidate=candidate)
        while run_one():
            pass
        self.stdout.write("Synthetic demo ready. Username: portfolio_demo")
        self.stdout.write("Existing credentials are preserved unless --reset-password is passed.")
