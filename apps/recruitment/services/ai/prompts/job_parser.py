from typing import Dict, Any


JOB_SKILL_KEYWORDS = [
    "python",
    "django",
    "flask",
    "fastapi",
    "react",
    "node",
    "postgres",
    "postgresql",
    "aws",
    "docker",
    "kubernetes",
    "ml",
    "machine learning",
]


def build_job_parse_prompt(job_description: str) -> str:
    prompt = (
        "Parse the following job description and return ONLY valid JSON (no markdown, no explanation) "
        "with these exact keys:\n"
        '  "skills": [list of required skill strings],\n'
        '  "role_type": "backend" | "frontend" | "fullstack" | "devops" | "ai" | other,\n'
        '  "experience_level": "junior" | "mid" | "senior",\n'
        '  "summary": "one-sentence summary"\n\n'
        f"Job description:\n{job_description}\n"
    )
    return prompt


def parse_job_from_text(job_description: str) -> Dict[str, Any]:
    text = (job_description or "").lower()
    skills = [k for k in JOB_SKILL_KEYWORDS if k in text]

    # role_type heuristics
    if any(k in text for k in ["frontend", "react", "vue", "angular"]):
        role_type = "frontend"
    elif any(k in text for k in ["ml", "machine learning", "tensorflow", "pytorch"]):
        role_type = "ai"
    else:
        role_type = "backend"

    # experience heuristics
    if "senior" in text or "5+" in text or "5 years" in text:
        experience = "senior"
    elif "junior" in text or "entry" in text or "0-" in text:
        experience = "junior"
    else:
        experience = "mid"

    summary = (job_description or "").strip()[:500]

    return {
        "skills": skills,
        "role_type": role_type,
        "experience_level": experience,
        "summary": summary,
    }
