from typing import List, Set, Tuple
import re


# Synonym groups: each inner set contains equivalent skill names (lowercased).
# When comparing, if a candidate skill matches any alias in the same group as
# a job skill, they are considered a match.
SKILL_ALIASES = [
    {"javascript", "js"},
    {"typescript", "ts"},
    {"postgresql", "postgres"},
    {"node.js", "node", "nodejs"},
    {"react", "reactjs", "react.js"},
    {"vue", "vuejs", "vue.js"},
    {"angular", "angularjs", "angular.js"},
    {"python3", "python"},
    {"c++", "cpp"},
    {"c#", "csharp"},
    {"machine learning", "ml"},
    {"artificial intelligence", "ai"},
    {"amazon web services", "aws"},
    {"google cloud platform", "gcp", "google cloud"},
    {"microsoft azure", "azure"},
    {"mongodb", "mongo"},
    {"docker", "containerization"},
    {"kubernetes", "k8s"},
    {"ci/cd", "cicd", "ci cd", "continuous integration"},
    {"rest api", "restful", "rest"},
    {"graphql", "gql"},
]


def _build_alias_map() -> dict:
    """Build a mapping: normalized_skill -> canonical (first in group)."""
    alias_map = {}
    for group in SKILL_ALIASES:
        canonical = sorted(group)[0]
        for alias in group:
            alias_map[alias] = canonical
    return alias_map


_ALIAS_MAP = _build_alias_map()


def _canonicalize(skill: str) -> str:
    """Return the canonical form of a skill using alias mapping."""
    return _ALIAS_MAP.get(skill, skill)


def normalize_skills(skills: List[str]) -> List[str]:
    seen = set()
    results = []
    for s in skills or []:
        normalized = re.sub(r"\s+", " ", str(s or "").strip()).lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            results.append(normalized)
    return results


def compare_skills(job_skills: List[str], candidate_skills: List[str]) -> Tuple[List[str], List[str]]:
    """Return (matched_skills, missing_skills) with original-cased job_skills preserved when possible."""
    job_norm = normalize_skills(job_skills)
    cand_norm = normalize_skills(candidate_skills)

    # Build a set of canonical candidate skills for matching
    cand_canonical: Set[str] = {_canonicalize(s) for s in cand_norm}

    matched = []
    missing = []

    # Build mapping from normalized -> original job skill
    orig_map = {re.sub(r"\s+", " ", str(s).strip()).lower(): s for s in (job_skills or [])}

    for j_norm in job_norm:
        j_canonical = _canonicalize(j_norm)
        if j_norm in cand_norm or j_canonical in cand_canonical:
            matched.append(orig_map.get(j_norm, j_norm))
        else:
            missing.append(orig_map.get(j_norm, j_norm))

    return matched, missing
