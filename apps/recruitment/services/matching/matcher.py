from django.conf import settings
from django.db import transaction
import math
from apps.recruitment.models import Job, Candidate, Analysis, ScoreRun
from apps.recruitment.services.ai.router import AIRouter, STATUS_MESSAGES
from apps.recruitment.services.ai.contracts import prompt, PROMPT_VERSION
from .skill_matcher import compare_skills
from .scorer import score_components, SCORING_VERSION
from .audit import build_snapshot


def compute_hybrid_match(candidate, job):
    matched, missing = compare_skills(job.required_skills, candidate.skills)
    score, components, insufficient = score_components(
        len(matched) + len(missing),
        len(matched),
        job.minimum_experience,
        float(candidate.years_of_experience),
        candidate.education,
        job.education_requirement,
        job.scoring_weights,
    )
    data = None
    source = "local"
    model = ""
    router = AIRouter()
    if settings.USE_LLM_FOR_SCORING and not insufficient:
        # Do not transmit names, contact details or raw resumes.
        data, source, model = router.generate_json(
            prompt(
                "Return score (number 0-100), matched_skills (strings), missing_skills (strings), explanation (string).",
                {
                    "job": {
                        "skills": job.required_skills,
                        "years": job.minimum_experience,
                        "education": job.education_requirement,
                    },
                    "candidate": {
                        "skills": candidate.skills,
                        "years": float(candidate.years_of_experience),
                        "education": candidate.education,
                    },
                },
            ),
            "score",
        )
    metadata = router.metadata(source)
    if insufficient or not settings.USE_LLM_FOR_SCORING:
        metadata["fallback_reason"] = STATUS_MESSAGES[
            "insufficient_requirements" if insufficient else "scoring_disabled"
        ]
    requested_weight = settings.LLM_SCORE_WEIGHT
    if not math.isfinite(requested_weight):
        raise ValueError("LLM_SCORE_WEIGHT must be finite.")
    weight = max(0, min(1, requested_weight)) if data else 0
    final = round(score * (1 - weight) + (data["score"] if data else 0) * weight, 2)
    # Canonical skill evidence stays deterministic. AI cannot silently add/remove requirements.
    result = {
        **metadata,
        "score": final,
        "deterministic_score": score,
        "llm_score": data["score"] if data else None,
        "matched_skills": matched,
        "missing_skills": missing,
        "score_components": components,
        "insufficient_requirements": insufficient,
        "provider": source,
        "provider_model": model,
        "llm_explanation": data.get("explanation", "") if data else "",
        "prompt_version": PROMPT_VERSION,
        "experience_match": float(candidate.years_of_experience) >= job.minimum_experience,
        "education_match": components["education"]["ratio"] == 1,
    }
    result["scoring_snapshot"] = build_snapshot(candidate, job, result, requested_weight, weight)
    return result


def refresh_positions(job_id):
    analyses = list(
        Analysis.objects.filter(
            job_id=job_id, is_stale=False, insufficient_requirements=False
        ).order_by("-match_score", "candidate_id", "id")
    )
    for position, analysis in enumerate(analyses, 1):
        analysis.ranking_position = position
    if analyses:
        Analysis.objects.bulk_update(analyses, ["ranking_position"])


@transaction.atomic
def match_candidate_to_job(candidate, job):
    if candidate.owner_id is None or candidate.owner_id != job.owner_id:
        raise ValueError("Candidate and job must belong to the same recruiter.")
    # Lock in candidate -> job order, including concurrent profile/job edits.
    candidate = Candidate.objects.select_for_update().get(pk=candidate.pk)
    job = Job.objects.select_for_update().get(pk=job.pk)
    result = compute_hybrid_match(candidate, job)
    analysis, _ = Analysis.objects.update_or_create(
        job=job,
        candidate=candidate,
        defaults={
            "match_score": result["score"],
            "scoring_snapshot": result["scoring_snapshot"],
            "matched_skills": result["matched_skills"],
            "missing_skills": result["missing_skills"],
            "insufficient_requirements": result["insufficient_requirements"],
            "score_components": result["score_components"],
            "scoring_version": SCORING_VERSION,
            "provider": result["provider"],
            "provider_model": result["provider_model"],
            "prompt_version": PROMPT_VERSION,
            "candidate_revision": candidate.revision,
            "job_revision": job.revision,
            "is_stale": False,
            "ai_summary": result["llm_explanation"],
            "strengths": "",
            "weaknesses": "",
            "generated_interview_questions": [],
            "generation_provenance": {
                "scoring": {
                    "fallback_reason": result["fallback_reason"],
                    "provider_attempts": result["provider_attempts"],
                }
            },
        },
    )
    score_run = ScoreRun.objects.create(analysis=analysis, snapshot=result["scoring_snapshot"])
    refresh_positions(job.pk)
    return {
        **result,
        "match_score": analysis.match_score,
        "analysis_id": analysis.pk,
        "score_run_id": score_run.pk,
        "candidate_id": candidate.pk,
        "job_id": job.pk,
        "response_source": result["provider"],
    }


def _merge_scores(deterministic, llm_result):
    # Backwards-compatible helper: keep skill evidence disjoint.
    return {**deterministic, "llm_score": llm_result.get("score") if llm_result else None}
