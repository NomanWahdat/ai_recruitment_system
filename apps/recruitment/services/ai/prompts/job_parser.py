import re
from apps.recruitment.services.skill_extractor import SkillExtractor


def parse_job_from_text(description):
    lowered = description.lower()
    skills = SkillExtractor().extract(description)
    role = (
        "fullstack"
        if "fullstack" in lowered or "full-stack" in lowered
        else "frontend"
        if re.search(r"\b(frontend|react|vue|angular)\b", lowered)
        else "devops"
        if "devops" in lowered
        else "ai"
        if re.search(r"\b(machine learning|ml|tensorflow|pytorch)\b", lowered)
        else "backend"
    )
    level = (
        "senior"
        if re.search(r"\b(senior|lead)\b", lowered)
        else "junior"
        if re.search(r"\b(junior|entry)\b", lowered)
        else "mid"
    )
    return {
        "skills": skills,
        "role_type": role,
        "experience_level": level,
        "summary": description.strip()[:500],
    }
