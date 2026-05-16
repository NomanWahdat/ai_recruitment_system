from typing import List

from decimal import Decimal

# Weights
SKILL_WEIGHT = 0.7
EXPERIENCE_WEIGHT = 0.2
EDUCATION_WEIGHT = 0.1


def clamp_score(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 100:
        return 100.0
    return round(value, 2)


def education_relevant(education: str, job_text: str) -> float:
    """Return relevance score: 1.0 for highly relevant, 0.5 for any education, 0.0 for none."""
    if not education:
        return 0.0
    lowered = education.lower()
    # Strong relevance keywords (STEM/tech)
    strong_keywords = ["computer", "software", "engineering", "information", "technology", "ai", "data"]
    if any(kw in lowered for kw in strong_keywords):
        return 1.0
    # Check if job text mentions any of these
    if job_text and any(kw in job_text.lower() for kw in strong_keywords):
        return 1.0
    # Any education is worth partial credit
    return 0.5


def compute_score(
    total_required: int,
    matched_count: int,
    years_required: float,
    candidate_years: float,
    education: str,
    job_text: str,
    matched_skills: List[str],
    missing_skills: List[str],
) -> float:
    """Return final score 0-100 using weights and bonus/penalty rules."""
    # Skill ratio
    skill_ratio = (matched_count / total_required) if total_required > 0 else 1.0

    skill_score = skill_ratio * 100 * SKILL_WEIGHT

    # Experience scoring — graduated bonus for exceeding minimum
    exp_score = 0.0
    experience_match = False
    try:
        if candidate_years >= years_required:
            exp_score = 100 * EXPERIENCE_WEIGHT
            experience_match = True
            # Graduated bonus: +1 per extra year above minimum, capped at +5
            if years_required > 0:
                extra_years = candidate_years - years_required
                exp_score += min(extra_years * 1.0, 5.0)
        else:
            # partial score proportional to candidate_years / years_required
            if years_required > 0:
                exp_score = (candidate_years / years_required) * 100 * EXPERIENCE_WEIGHT
            else:
                exp_score = 100 * EXPERIENCE_WEIGHT
    except Exception:
        exp_score = 0.0

    # Education scoring — partial credit for any education
    edu_score = 0.0
    edu_relevance = education_relevant(education, job_text)
    if edu_relevance > 0:
        edu_score = edu_relevance * 100 * EDUCATION_WEIGHT

    base = skill_score + exp_score + edu_score

    # Bonuses
    bonus = 0
    normalized = [s.lower() for s in matched_skills]
    if any("python" == s for s in normalized):
        bonus += 10
    if any(s in {"django", "flask", "fastapi"} for s in normalized):
        bonus += 5
    if any(s in {"docker", "kubernetes"} for s in normalized):
        bonus += 5

    # Penalty for missing skills — scaled proportionally to missing ratio
    penalty = 0
    total_skills = len(matched_skills) + len(missing_skills)
    if missing_skills and total_skills > 0:
        missing_ratio = len(missing_skills) / total_skills
        # Scale: up to -15 when all skills are missing, 0 when none are
        penalty = -round(missing_ratio * 15, 2)

    final = float(base + bonus + penalty)
    return clamp_score(final)
