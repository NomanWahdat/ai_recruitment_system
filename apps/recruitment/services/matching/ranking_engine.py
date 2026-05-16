from typing import Dict, Any
import os
from apps.recruitment.models import Job, Candidate, Analysis
from django.db.models import Prefetch
from apps.recruitment.services.matching.matcher import match_candidate_to_job


def _is_enabled(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes", "on")


def refresh_rankings_for_job(job: Job) -> None:
    """Recompute stored analyses for a job when hybrid scoring is enabled.

    This keeps the rankings endpoint aligned with the same scoring path used by
    job/candidate matching while preserving the existing API shape.
    """
    if not _is_enabled("USE_LLM_FOR_SCORING"):
        return

    analyses = Analysis.objects.select_related("candidate").filter(job=job)
    for analysis in analyses:
        candidate = analysis.candidate
        try:
            match_candidate_to_job(candidate, job)
        except Exception:
            # Keep ranking resilient; fall back to the latest stored score.
            continue


def top_candidates_for_job(job_id: int, top_n: int = 10, refresh: bool = False) -> Dict[str, Any]:
    job = Job.objects.filter(id=job_id).first()
    if not job:
        return {"job_id": job_id, "top_candidates": []}

    # Only refresh rankings when explicitly requested (e.g. reprocess).
    # Avoids N LLM API calls on every rankings page view.
    if refresh:
        refresh_rankings_for_job(job)

    # Query analyses for this job ordered by match_score desc
    analyses = (
        Analysis.objects.select_related("candidate")
        .filter(job=job)
        .order_by("-match_score")[:top_n]
    )

    top = []
    position = 1
    for a in analyses:
        # update ranking_position if different
        if a.ranking_position != position:
            a.ranking_position = position
            a.save(update_fields=["ranking_position"])
        top.append({
            "candidate_id": a.candidate.id,
            "match_score": a.match_score,
            "ranking_position": a.ranking_position,
        })
        position += 1

    return {"job_id": job.id, "top_candidates": top}
