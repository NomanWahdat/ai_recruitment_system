"""Saved-score arithmetic can be replayed without a provider or current profile/settings."""

import hashlib
import hmac
import json
import math
from copy import deepcopy
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .scorer import SCORING_VERSION, clamp_score

SNAPSHOT_VERSION = "score-audit-v1"
IMPLEMENTATION_SHA256 = hashlib.sha256(
    b"".join(
        (Path(__file__).parent / name).read_bytes()
        for name in ["scorer.py", "skill_matcher.py", "matcher.py", "audit.py"]
    )
).hexdigest()


def canonical_numbers(value):
    # PostgreSQL JSONB can normalize -0.0 and integer-valued floats on round-trip.
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [canonical_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: canonical_numbers(item) for key, item in value.items()}
    return value


def fingerprint(snapshot):
    payload = canonical_numbers({key: value for key, value in snapshot.items() if key != "sha256"})
    return hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def build_snapshot(candidate, job, result, requested_weight, applied_weight):
    base_weights = job.scoring_weights or {
        "skills": settings.SKILL_WEIGHT,
        "experience": settings.EXPERIENCE_WEIGHT,
        "education": settings.EDUCATION_WEIGHT,
    }
    snapshot = {
        "schema_version": SNAPSHOT_VERSION,
        "implementation_sha256": IMPLEMENTATION_SHA256,
        "calculated_at": timezone.now().isoformat(),
        "inputs": {
            "candidate": {
                "skills": list(candidate.skills),
                "years": float(candidate.years_of_experience),
                "education": candidate.education,
                "revision": getattr(candidate, "revision", None),
            },
            "job": {
                "required_skills": list(job.required_skills),
                "minimum_experience": job.minimum_experience,
                "education_requirement": job.education_requirement,
                "scoring_weights": dict(base_weights),
                "revision": getattr(job, "revision", None),
            },
        },
        "rubric": {
            "version": SCORING_VERSION,
            "score": result["deterministic_score"],
            "components": deepcopy(result["score_components"]),
            "matched_skills": list(result["matched_skills"]),
            "missing_skills": list(result["missing_skills"]),
        },
        "ai": {
            "enabled": settings.USE_LLM_FOR_SCORING,
            "provider": result["provider"],
            "model": result["provider_model"],
            "prompt_version": result["prompt_version"],
            "score": result["llm_score"],
            "requested_weight": requested_weight,
            "applied_weight": applied_weight,
            "explanation": result["llm_explanation"],
            "fallback_reason": result["fallback_reason"],
            "provider_attempts": deepcopy(result["provider_attempts"]),
        },
        "insufficient_requirements": result["insufficient_requirements"],
        "final_score": result["score"],
        "formula": "round(local_score * (1 - applied_ai_weight) + ai_score * applied_ai_weight, 2)",
    }
    snapshot["sha256"] = fingerprint(snapshot)
    return snapshot


def bounded_number(value, low, high):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not low <= value <= high
    ):
        raise ValueError("Invalid snapshot number")
    return value


def reproduce(snapshot, saved_score=None):
    if not snapshot:
        return {
            "available": False,
            "verified": False,
            "reason": "This legacy analysis has no saved scoring snapshot. Run matching again.",
        }
    try:
        if snapshot.get("schema_version") != SNAPSHOT_VERSION:
            raise ValueError("Unsupported snapshot version")
        digest_ok = hmac.compare_digest(str(snapshot.get("sha256", "")), fingerprint(snapshot))
        components = snapshot["rubric"]["components"]
        if set(components) != {"skills", "experience", "education"}:
            raise ValueError("Invalid rubric components")
        total = 0
        for part in components.values():
            ratio = 0 if part["ratio"] is None else bounded_number(part["ratio"], 0, 1)
            total += ratio * bounded_number(part["weight"], 0, 1) * 100
        local = clamp_score(total)
        weight = bounded_number(snapshot["ai"]["applied_weight"], 0, 1)
        ai = snapshot["ai"]["score"]
        if ai is None:
            if weight != 0:
                raise ValueError("Missing AI score with a nonzero blend weight")
            ai = 0
        else:
            ai = bounded_number(ai, 0, 100)
        final = round(local * (1 - weight) + ai * weight, 2)
        expected = bounded_number(snapshot["final_score"], 0, 100)
        local_ok = local == snapshot["rubric"]["score"]
        score_ok = final == expected and (saved_score is None or final == saved_score)
        return {
            "available": True,
            "verified": digest_ok and local_ok and score_ok,
            "hash_matches": digest_ok,
            "rubric_matches": local_ok,
            "score_matches": score_ok,
            "local_score": local,
            "ai_score": snapshot["ai"]["score"],
            "applied_ai_weight": weight,
            "reproduced_score": final,
            "saved_score": expected,
            "external_requests": 0,
            "reason": "Replayed saved arithmetic; the AI model was not called again.",
        }
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
        return {
            "available": True,
            "verified": False,
            "reason": "The saved snapshot is invalid or its schema is unsupported.",
            "external_requests": 0,
        }
