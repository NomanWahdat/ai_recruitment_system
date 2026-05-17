from typing import Dict, Any, List
from django.db import transaction
from apps.recruitment.models import Job, Candidate, Analysis
from .skill_matcher import compare_skills
from .scorer import compute_score
import logging
import os
from decouple import config
from apps.recruitment.services.ai.router import AIRouter

logger = logging.getLogger(__name__)


def _is_enabled(name: str, default: str = "false") -> bool:
    value = os.getenv(name)
    if value is None:
        value = config(name, default=default)
    return str(value).lower() in ("1", "true", "yes", "on")


def _get_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        value = config(name, default=default)
    return str(value)


def _merge_skill_lists(base: List[str], extra: List[str]) -> List[str]:
    merged: List[str] = []
    seen = set()
    for item in (base or []) + (extra or []):
        normalized = str(item or "").strip()
        lowered = normalized.lower()
        if normalized and lowered not in seen:
            seen.add(lowered)
            merged.append(normalized)
    return merged


def _build_job_payload(job: Job) -> Dict[str, Any]:
    return {
        "title": job.title,
        "required_skills": job.required_skills or [],
        "description": job.description or "",
        "minimum_experience": getattr(job, "minimum_experience", 0) or 0,
        "education_requirement": getattr(job, "education_requirement", "") or "",
    }


def _build_candidate_payload(candidate: Candidate) -> Dict[str, Any]:
    return {
        "full_name": candidate.full_name,
        "skills": candidate.skills or [],
        "years_of_experience": float(candidate.years_of_experience or 0),
        "education": candidate.education or "",
        "text_snippet": (candidate.extracted_text or "")[:2000],
    }


def _compute_deterministic_match(candidate: Candidate, job: Job) -> Dict[str, Any]:
    job_skills = job.required_skills or []
    candidate_skills = candidate.skills or []

    matched_skills, missing_skills = compare_skills(job_skills, candidate_skills)
    total_required = len(job_skills) if job_skills else 0
    matched_count = len(matched_skills)

    years_required = getattr(job, "minimum_experience", 0) or 0
    candidate_years = float(candidate.years_of_experience or 0)
    job_text = f"{job.title} {job.description or ''}"

    score = compute_score(
        total_required=total_required,
        matched_count=matched_count,
        years_required=years_required,
        candidate_years=candidate_years,
        education=candidate.education or "",
        job_text=job_text,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
    )

    experience_match = candidate_years >= years_required
    education_match = bool(candidate.education and candidate.education.strip())

    return {
        "score": float(score),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "experience_match": experience_match,
        "education_match": education_match,
    }


def _compute_llm_match(candidate: Candidate, job: Job) -> Dict[str, Any]:
    # Enable LLM scoring if USE_LLM_FOR_SCORING is explicitly set, or if USE_GROQ_AI is enabled
    if not (_is_enabled("USE_LLM_FOR_SCORING") or _is_enabled("USE_GROQ_AI")):
        return {}

    router = AIRouter()
    job_payload = _build_job_payload(job)
    candidate_payload = _build_candidate_payload(candidate)

    timeout = int(_get_env("LLM_REQUEST_TIMEOUT", "10"))
    providers = []
    default_provider = router.get_provider()
    providers.append(default_provider)
    try:
        fallback_provider = router.get_provider(prefer="gemini")
        if fallback_provider.__class__ is not default_provider.__class__:
            providers.append(fallback_provider)
    except Exception:
        pass

    for provider in providers:
        try:
            llm_result = provider.score_candidate_job(job_payload, candidate_payload, timeout=timeout) or {}
            if llm_result:
                return llm_result
        except Exception:
            logger.exception("LLM scoring failed for job=%s candidate=%s", getattr(job, "id", "?"), getattr(candidate, "id", "?"))
            continue
    return {}


def _merge_scores(deterministic: Dict[str, Any], llm_result: Dict[str, Any]) -> Dict[str, Any]:
    score = float(deterministic.get("score", 0.0))
    matched_skills = list(deterministic.get("matched_skills") or [])
    missing_skills = list(deterministic.get("missing_skills") or [])

    if not llm_result:
        return {
            **deterministic,
            "score": score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "llm_score": None,
            "llm_explanation": "",
        }

    llm_score = llm_result.get("score")
    try:
        llm_score = float(llm_score) if llm_score is not None else None
    except Exception:
        llm_score = None

    if llm_score is not None:
        try:
            weight = float(_get_env("LLM_SCORE_WEIGHT", "0.25"))
        except Exception:
            weight = 0.25
        final_score = round(score * (1.0 - weight) + llm_score * weight, 2)
    else:
        final_score = score

    return {
        **deterministic,
        "score": final_score,
        "llm_score": llm_score,
        "matched_skills": _merge_skill_lists(matched_skills, llm_result.get("matched_skills") or []),
        "missing_skills": _merge_skill_lists(missing_skills, llm_result.get("missing_skills") or []),
        "llm_explanation": str(llm_result.get("explanation") or ""),
    }


def compute_hybrid_match(candidate: Candidate, job: Job) -> Dict[str, Any]:
    deterministic = _compute_deterministic_match(candidate, job)
    llm_result = _compute_llm_match(candidate, job)
    return _merge_scores(deterministic, llm_result)


def match_candidate_to_job(candidate: Candidate, job: Job) -> Dict[str, Any]:
    """Compute match between a candidate and job and persist Analysis record."""
    hybrid_result = compute_hybrid_match(candidate, job)
    score = hybrid_result["score"]
    matched_skills = hybrid_result["matched_skills"]
    missing_skills = hybrid_result["missing_skills"]
    experience_match = hybrid_result["experience_match"]
    education_match = hybrid_result["education_match"]

    # Persist Analysis (create or update)
    try:
        with transaction.atomic():
            analysis, created = Analysis.objects.get_or_create(job=job, candidate=candidate, defaults={
                "match_score": score,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "strengths": "",
                "weaknesses": "",
                "ai_summary": hybrid_result.get("llm_explanation", ""),
            })
            if not created:
                analysis.match_score = score
                analysis.matched_skills = matched_skills
                analysis.missing_skills = missing_skills
                if hybrid_result.get("llm_explanation"):
                    analysis.ai_summary = hybrid_result.get("llm_explanation", "")
                analysis.save(update_fields=["match_score", "matched_skills", "missing_skills", "ai_summary", "updated_at"])
    except Exception as exc:
        logger.exception("Failed to persist analysis for job=%s candidate=%s: %s", job.id, candidate.id, exc)

    result = {
        "job_id": job.id,
        "candidate_id": candidate.id,
        "match_score": score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "experience_match": experience_match,
        "education_match": education_match,
        "llm_score": hybrid_result.get("llm_score"),
        "llm_explanation": hybrid_result.get("llm_explanation", ""),
    }

    return result
