from typing import Dict, Any, List


def build_interview_prompt(candidate: Dict[str, Any], job: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    return (
        "Generate interview questions for this candidate-job pair. "
        "Return ONLY valid JSON (no markdown) with these exact keys:\n"
        '  "technical_questions": ["list of technical questions"],\n'
        '  "behavioral_questions": ["list of behavioral questions"],\n'
        '  "skill_based_questions": ["list of skill-based questions"]\n\n'
        "Candidate skills: "
        + ", ".join(candidate.get("skills", []))
        + "\nJob required skills: "
        + ", ".join(job.get("required_skills", []))
        + f"\nMatch score: {analysis.get('match_score', '')}"
        + f"\nMatched skills: {', '.join(analysis.get('matched_skills', []))}"
        + f"\nMissing skills: {', '.join(analysis.get('missing_skills', []))}"
    )


def generate_questions_from_text(text: str) -> Dict[str, Any]:
    # Try to parse JSON from AI response first (handles markdown code blocks)
    from apps.recruitment.utils.text import extract_json_from_text
    txt = (text or "").strip()
    if txt:
        parsed, ok = extract_json_from_text(txt)
        if ok and parsed:
            return {
                "technical_questions": parsed.get("technical_questions", []) or [],
                "behavioral_questions": parsed.get("behavioral_questions", []) or [],
                "skill_based_questions": parsed.get("skill_based_questions", []) or [],
            }

    # Fallback: heuristics based on keywords
    tech = []
    beh = [
        "Tell me about a time you faced a technical challenge and how you resolved it.",
        "Describe a project where you worked in a team and your role.",
    ]
    skill_based = []

    lowered = txt.lower()
    if "python" in lowered:
        tech.append("Explain how you manage Python package dependencies and virtual environments.")
        skill_based.append("Describe a complex Python project you worked on.")
    if "django" in lowered:
        tech.append("Explain Django request/response lifecycle and middlewares.")
        skill_based.append("How do you optimize Django ORM queries?")
    if "docker" in lowered:
        tech.append("How do you containerize a Django application for production?")
        skill_based.append("Explain how you handle multi-container deployments.")
    if "react" in lowered:
        tech.append("How do you manage state in a complex React application?")
        skill_based.append("Explain the React component lifecycle and hooks you use most.")
    if "aws" in lowered:
        tech.append("Describe your experience with AWS services for deployment and scaling.")
        skill_based.append("How do you handle infrastructure-as-code on AWS?")
    if "kubernetes" in lowered:
        tech.append("How do you orchestrate and monitor services in a Kubernetes cluster?")
        skill_based.append("Explain your approach to Kubernetes resource management and scaling.")
    if "node" in lowered or "express" in lowered:
        tech.append("How do you handle async patterns and error handling in Node.js?")
        skill_based.append("Describe a REST API you built with Node.js/Express.")
    if "postgres" in lowered or "postgresql" in lowered:
        tech.append("How do you approach database schema design and query optimization in PostgreSQL?")
    if "machine learning" in lowered or "ml" in lowered or "tensorflow" in lowered or "pytorch" in lowered:
        tech.append("Walk through your approach to training and deploying a machine learning model.")
        skill_based.append("How do you evaluate model performance and handle overfitting?")

    return {
        "technical_questions": tech,
        "behavioral_questions": beh,
        "skill_based_questions": skill_based,
    }
