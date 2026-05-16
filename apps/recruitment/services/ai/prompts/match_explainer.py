from typing import Dict, Any, List


def build_match_explain_prompt(candidate: Dict[str, Any], job: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    parts = [
        "Explain why the candidate matches the job. Return ONLY valid JSON (no markdown) with these keys:",
        '  "summary": "brief overall assessment",',
        '  "strengths": ["list of strength statements"],',
        '  "weaknesses": ["list of weakness statements"],',
        '  "recommendation": "hire recommendation statement"',
        "",
        "Candidate profile:",
        f"  Name: {candidate.get('full_name', '')}",
        f"  Skills: {', '.join(candidate.get('skills', []))}",
        f"  Years: {candidate.get('years_of_experience', '')}",
        f"  Education: {candidate.get('education', '')}",
        "Job details:",
        f"  Title: {job.get('title', '')}",
        f"  Required skills: {', '.join(job.get('required_skills', []))}",
        f"  Minimum experience: {job.get('minimum_experience', '')}",
        "Match analysis:",
        f"  Match score: {analysis.get('match_score', '')}",
        f"  Matched skills: {', '.join(analysis.get('matched_skills', []))}",
        f"  Missing skills: {', '.join(analysis.get('missing_skills', []))}",
    ]
    return "\n".join(parts)


def parse_explanation_from_text(text: str) -> Dict[str, Any]:
    # Try to parse JSON first (providers may return structured JSON or markdown-wrapped JSON)
    from apps.recruitment.utils.text import extract_json_from_text

    txt = text or ""
    parsed, ok = extract_json_from_text(txt)
    if ok and parsed:
        return {
            "summary": parsed.get("summary", ""),
            "strengths": parsed.get("strengths", []) or [],
            "weaknesses": parsed.get("weaknesses", []) or [],
            "recommendation": parsed.get("recommendation", "") or "",
        }

    # Fallback to improved heuristics: look for labeled sections
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    strengths = []
    weaknesses = []
    recommendation = ""
    summary = lines[0] if lines else ""

    for l in lines[1:]:
        lowered = l.lower()
        if lowered.startswith("strength") or "strength" in lowered:
            strengths.append(l)
        elif lowered.startswith("weak") or any(w in lowered for w in ["missing", "lack", "limited"]):
            weaknesses.append(l)
        elif lowered.startswith("recommend") or any(w in lowered for w in ["suggest", "improve", "consider"]):
            recommendation += l + " "
        else:
            # try to classify lines that look positive/negative
            if any(w in lowered for w in ["excellent", "strong", "good", "well", "experienced"]):
                strengths.append(l)
            elif any(w in lowered for w in ["weak", "missing", "lack", "limited", "needs"]):
                weaknesses.append(l)

    return {
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendation": recommendation.strip(),
    }
