import math
import re
from django.conf import settings

SCORING_VERSION = "rubric-v2"


def clamp_score(value):
    return round(max(0, min(100, float(value))), 2)


def education_relevant(education, requirement):
    if not education or not requirement:
        return 0.0
    education = education.lower()
    requirement = requirement.lower()
    degree_levels = [
        ("phd", 4),
        ("doctor", 4),
        ("master", 3),
        ("msc", 3),
        ("bachelor", 2),
        ("bsc", 2),
        ("associate", 1),
    ]
    required = max([level for label, level in degree_levels if label in requirement] or [0])
    actual = max([level for label, level in degree_levels if label in education] or [0])
    excluded = {
        "bachelor",
        "bachelors",
        "master",
        "masters",
        "phd",
        "degree",
        "in",
        "of",
        "or",
        "and",
        "a",
        "s",
        "related",
        "field",
        "required",
        "preferred",
        "equivalent",
    }
    subjects = set(re.findall(r"[a-z]+", requirement)) - excluded
    subject_match = not subjects or bool(subjects & set(re.findall(r"[a-z]+", education)))
    return float(actual >= required and subject_match)


def validate_weights(weights):
    if not isinstance(weights, dict) or set(weights) - {"skills", "experience", "education"}:
        raise ValueError("Weights must contain only skills, experience and education.")
    if any(
        isinstance(v, bool)
        or not isinstance(v, (int, float))
        or not math.isfinite(v)
        or not 0 <= v <= 1
        for v in weights.values()
    ):
        raise ValueError("Weights must be finite numbers between zero and one.")
    if weights and (
        set(weights) != {"skills", "experience", "education"}
        or abs(sum(weights.values()) - 1) > 0.000001
    ):
        raise ValueError("Provide all three weights with a total of one.")
    return weights


def score_components(
    total_required,
    matched_count,
    years_required,
    candidate_years,
    education,
    requirement="",
    weights=None,
):
    weights = validate_weights(weights or {}) or {
        "skills": settings.SKILL_WEIGHT,
        "experience": settings.EXPERIENCE_WEIGHT,
        "education": settings.EDUCATION_WEIGHT,
    }
    validate_weights(weights)
    ratios = {
        "skills": min(1, matched_count / total_required) if total_required else None,
        "experience": min(1, max(0, candidate_years) / years_required) if years_required else None,
        "education": education_relevant(education, requirement) if requirement.strip() else None,
    }
    denominator = sum(weights[k] for k, v in ratios.items() if v is not None)
    components = {
        k: {
            "ratio": v,
            "weight": round(weights[k] / denominator, 6) if v is not None and denominator else 0,
        }
        for k, v in ratios.items()
    }
    score = clamp_score(sum((v["ratio"] or 0) * v["weight"] * 100 for v in components.values()))
    return score, components, not bool(denominator)


def compute_score(
    total_required,
    matched_count,
    years_required,
    candidate_years,
    education,
    job_text="",
    matched_skills=None,
    missing_skills=None,
    weights=None,
):
    return score_components(
        total_required, matched_count, years_required, candidate_years, education, job_text, weights
    )[0]
