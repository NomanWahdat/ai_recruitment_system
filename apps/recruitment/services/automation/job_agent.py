import logging
from typing import Dict, Any

from apps.recruitment.models import Candidate, Job
from apps.recruitment.services.ai.router import AIRouter
from apps.recruitment.services.ai.prompts.job_parser import build_job_parse_prompt, parse_job_from_text
from apps.recruitment.services.matching.matcher import match_candidate_to_job
from apps.recruitment.utils.text import extract_json_from_text

logger = logging.getLogger(__name__)


class JobAgent:
    def handle_job_created(self, payload: Dict[str, Any]):
        job_id = payload.get("job_id")
        if not job_id:
            return {"job_id": None, "matched_candidates": 0, "ranked": 0}

        job = Job.objects.filter(id=job_id).first()
        if not job:
            return {"job_id": job_id, "matched_candidates": 0, "ranked": 0, "error": "job not found"}

        logger.info("Handling job_created for job_id=%s", job_id)

        # Try Groq AI for job parsing first, fall back to local heuristic
        parsed = None
        parse_source = "local"
        description = job.description or ""

        if description:
            router = AIRouter()
            provider = router.get_provider()
            prompt = build_job_parse_prompt(description)
            ai_text = ""
            try:
                ai_text = provider.generate_text(prompt, timeout=10)
            except Exception:
                try:
                    provider = router.get_provider(prefer="gemini")
                    ai_text = provider.generate_text(prompt, timeout=10)
                except Exception:
                    ai_text = ""

            if ai_text:
                extracted, ok = extract_json_from_text(ai_text)
                if ok and extracted:
                    parsed = {
                        "skills": extracted.get("skills", []),
                        "role_type": extracted.get("role_type", ""),
                        "experience_level": extracted.get("experience_level", ""),
                        "summary": extracted.get("summary", ""),
                    }
                    parse_source = "groq_ai"

        if not parsed:
            parsed = parse_job_from_text(description)
            parse_source = "local"

        parsed["response_source"] = parse_source

        # Merge inferred skills into job.required_skills while preserving existing skills
        existing = [str(skill).strip() for skill in (job.required_skills or []) if str(skill).strip()]
        inferred = [str(skill).strip() for skill in (parsed.get("skills") or []) if str(skill).strip()]
        merged = []
        seen = set()
        for skill in existing + inferred:
            lowered = skill.lower()
            if lowered not in seen:
                seen.add(lowered)
                merged.append(skill)

        if merged and merged != existing:
            job.required_skills = merged
            job.save(update_fields=["required_skills", "updated_at"])

        matched = 0
        ranked = 0
        match_sources = []
        candidates = Candidate.objects.all().only("id", "skills", "years_of_experience", "education", "full_name")
        from apps.recruitment.services.automation.agent_orchestrator import orchestrator
        for candidate in candidates:
            try:
                match_result = match_candidate_to_job(candidate, job)
                # Track response source from matching
                if match_result.get("llm_score") is not None:
                    match_sources.append("groq_ai")
                else:
                    match_sources.append("local")
                orchestrator.emit(
                    "match_completed",
                    {"job_id": job.id, "candidate_id": candidate.id, "match_result": match_result},
                )
                orchestrator.emit("ranking_requested", {"job_id": job.id, "candidate_id": candidate.id})
                matched += 1
                ranked += 1
            except Exception as exc:
                logger.exception("Job matching failed for job=%s candidate=%s: %s", job.id, candidate.id, exc)

        # Determine overall matching source
        matching_source = "groq_ai" if any(s == "groq_ai" for s in match_sources) else "local"

        return {
            "job_id": job.id,
            "parsed": parsed,
            "matched_candidates": matched,
            "ranked": ranked,
            "matching_response_source": matching_source,
        }


job_agent = JobAgent()
