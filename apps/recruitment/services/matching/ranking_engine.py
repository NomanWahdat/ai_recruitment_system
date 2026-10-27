from apps.recruitment.models import Analysis


def top_candidates_for_job(job_id, top_n=10, refresh=False):
    # Pure read: ranking writes occur only inside matching transactions.
    rows = (
        Analysis.objects.filter(job_id=job_id, is_stale=False, insufficient_requirements=False)
        .select_related("candidate")
        .order_by("-match_score", "candidate_id", "id")[:top_n]
    )
    return {
        "job_id": job_id,
        "top_candidates": [
            {
                "candidate_id": a.candidate_id,
                "match_score": a.match_score,
                "ranking_position": index,
                "analysis_id": a.pk,
                "provider": a.provider,
                "candidate_name": a.candidate.full_name,
                "matched_skills": a.matched_skills,
            }
            for index, a in enumerate(rows, 1)
        ],
    }
