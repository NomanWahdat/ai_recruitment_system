from datetime import timedelta
import logging
from django.db import connection, transaction
from django.utils import timezone
from apps.recruitment.models import Candidate, Job, ProcessingTask
from .audit import record

logger = logging.getLogger(__name__)


def enqueue(owner, kind, candidate=None, job=None):
    if (
        not owner
        or (candidate and candidate.owner_id != owner.pk)
        or (job and job.owner_id != owner.pk)
    ):
        raise ValueError("Task ownership mismatch")
    obj = candidate or job
    key = f"{kind}:{obj.pk}:{obj.revision}"
    with transaction.atomic():
        # Resource lock serializes concurrent enqueue calls on PostgreSQL.
        type(obj).objects.select_for_update().get(pk=obj.pk)
        active = ProcessingTask.objects.filter(
            dedup_key=key, status__in=["queued", "running"]
        ).first()
        if active:
            return active
        return ProcessingTask.objects.create(
            owner=owner,
            kind=kind,
            candidate=candidate,
            job=job,
            dedup_key=key,
            available_at=timezone.now(),
        )


def claim():
    now = timezone.now()
    with transaction.atomic():
        expired = ProcessingTask.objects.filter(
            status="running", started_at__lt=now - timedelta(minutes=10)
        )
        exhausted = list(expired.filter(attempts__gte=3).values_list("candidate_id", flat=True))
        expired.filter(attempts__gte=3).update(
            status="failed", error="Worker lease expired after three attempts.", finished_at=now
        )
        Candidate.objects.filter(pk__in=exhausted).update(
            processing_status="failed",
            analysis_completed=False,
            analysis_error="Worker lease expired. Retry processing.",
        )
        expired.filter(attempts__lt=3).update(
            status="queued", available_at=now, error="Recovered expired worker lease."
        )
        qs = ProcessingTask.objects.filter(status="queued", available_at__lte=now).order_by(
            "created_at", "id"
        )
        task = (
            qs.select_for_update(skip_locked=True).first()
            if connection.vendor == "postgresql"
            else qs.select_for_update().first()
        )
        if task:
            task.status = "running"
            task.started_at = now
            task.attempts += 1
            task.save()
        return task


def run_one():
    task = claim()
    if not task:
        return False
    try:
        from .candidate_processor import CandidateProcessor
        from .matching.matcher import match_candidate_to_job

        task.refresh_from_db()
        if task.candidate_id:
            with transaction.atomic():
                candidate = Candidate.objects.select_for_update().get(
                    pk=task.candidate_id, owner=task.owner
                )
                if task.dedup_key.rsplit(":", 1)[-1] != str(candidate.revision):
                    task.status = "completed"
                    task.error = "Superseded by a newer profile revision."
                    task.finished_at = timezone.now()
                    task.save()
                    return True
                if task.kind == "extract":
                    CandidateProcessor().process_candidate(candidate)
                    candidate.refresh_from_db()
                if not candidate.analysis_completed and not candidate.profile_reviewed_at:
                    raise ValueError("Candidate has no reviewed or extracted profile")
                for job in Job.objects.filter(owner=task.owner).order_by("id"):
                    match_candidate_to_job(candidate, job)
        elif task.job_id:
            job = Job.objects.get(pk=task.job_id, owner=task.owner)
            for candidate in Candidate.objects.filter(
                owner=task.owner, analysis_completed=True
            ).order_by("id"):
                match_candidate_to_job(candidate, job)
        task.status = "completed"
        task.error = ""
        task.finished_at = timezone.now()
        task.save()
        record(task.owner, "task.completed", task, kind=task.kind, attempts=task.attempts)
    except Exception as exc:
        logger.error("task_failed id=%s category=%s", task.pk, type(exc).__name__)
        task.status = "failed"
        task.error = (
            "Document extraction failed."
            if task.kind == "extract"
            else "Processing failed; retry after checking the inputs."
        )
        task.finished_at = timezone.now()
        task.save()
        if task.candidate_id:
            from .cv_extractor import CVExtractionError

            Candidate.objects.filter(pk=task.candidate_id).update(
                processing_status="failed" if task.kind == "extract" else "completed",
                extraction_error=str(exc)[:500] if isinstance(exc, CVExtractionError) else "",
                analysis_error="Document processing failed. Inspect the source file and retry.",
                analysis_completed=False if task.kind == "extract" else True,
            )
        record(task.owner, "task.failed", task, kind=task.kind, category=type(exc).__name__)
    return True
