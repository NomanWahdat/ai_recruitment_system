import logging
from typing import Dict, Any

from django.utils import timezone

from apps.recruitment.models import Analysis, Candidate, Job
from apps.recruitment.services.candidate_processor import CandidateProcessor
from apps.recruitment.services.ai.router import AIRouter
from apps.recruitment.services.ai.prompts.match_explainer import build_match_explain_prompt, parse_explanation_from_text
from apps.recruitment.services.matching.matcher import match_candidate_to_job

logger = logging.getLogger(__name__)


class CandidateAgent:
    def handle_candidate_created(self, payload: Dict[str, Any]):
        candidate_id = payload.get("candidate_id")
        if not candidate_id:
            return {"candidate_id": None, "processed": False}

        candidate = Candidate.objects.filter(id=candidate_id).first()
        if not candidate:
            return {"candidate_id": candidate_id, "processed": False, "error": "candidate not found"}

        logger.info("Handling candidate_created for candidate_id=%s", candidate_id)

        if not candidate.extracted_text and candidate.cv_file:
            try:
                processor = CandidateProcessor()
                return processor.process_candidate(candidate, candidate.cv_filename)
            except Exception as exc:
                logger.exception("Candidate NLP analysis failed for %s: %s", candidate_id, exc)
                return {"candidate_id": candidate.id, "processed": False, "error": str(exc)}

        if candidate.extracted_text:
            # Re-run analyzer on reprocess or when skills/profile are missing.
            source = payload.get("source", "")
            if not candidate.skills or source == "reprocess":
                try:
                    processor = CandidateProcessor()
                    processor._analyze_candidate(candidate)
                except Exception as exc:
                    logger.exception("Candidate profile refresh failed for %s: %s", candidate_id, exc)
            analyzed_result = self.handle_candidate_analyzed({"candidate_id": candidate_id})
            return {"candidate_id": candidate.id, "processed": True, "analysis": analyzed_result}

        return {"candidate_id": candidate.id, "processed": False, "reason": "no_cv_text"}

    def handle_candidate_analyzed(self, payload: Dict[str, Any]):
        candidate_id = payload.get("candidate_id")
        if not candidate_id:
            return {"candidate_id": None, "matched_jobs": 0, "ranked_jobs": 0}

        candidate = Candidate.objects.filter(id=candidate_id).first()
        if not candidate:
            return {"candidate_id": candidate_id, "matched_jobs": 0, "ranked_jobs": 0, "error": "candidate not found"}

        jobs = Job.objects.all().only("id", "title", "description", "required_skills", "minimum_experience", "education_requirement")
        matched_jobs = 0
        ranked_jobs = 0
        match_sources = []
        explanation_sources = []
        from apps.recruitment.services.automation.agent_orchestrator import orchestrator

        matched_job_ids = []
        for job in jobs:
            try:
                result = match_candidate_to_job(candidate, job)
                # Track matching source
                if result.get("llm_score") is not None:
                    match_sources.append("groq_ai")
                else:
                    match_sources.append("local")
                matched_jobs += 1
                matched_job_ids.append(job.id)
                expl_source = self._generate_ai_explanation(candidate, job)
                explanation_sources.append(expl_source)
            except Exception as exc:
                logger.exception("Candidate matching failed for candidate=%s job=%s: %s", candidate.id, job.id, exc)

        # Emit ranking_requested once per job after all matches are done
        # to avoid redundant recalculations during the matching loop
        for jid in matched_job_ids:
            orchestrator.emit("ranking_requested", {"job_id": jid, "candidate_id": candidate.id})
            ranked_jobs += 1

        candidate.analysis_completed = True
        candidate.analyzed_at = timezone.now()
        candidate.save(update_fields=["analysis_completed", "analyzed_at", "updated_at"])

        matching_source = "groq_ai" if any(s == "groq_ai" for s in match_sources) else "local"
        explanation_source = "groq_ai" if any(s == "groq_ai" for s in explanation_sources) else "local"

        return {
            "candidate_id": candidate.id,
            "matched_jobs": matched_jobs,
            "ranked_jobs": ranked_jobs,
            "matching_response_source": matching_source,
            "explanation_response_source": explanation_source,
        }

    def _generate_ai_explanation(self, candidate: Candidate, job: Job):
        """Generate AI explanation and return response source ('groq_ai' or 'local')."""
        analysis = Analysis.objects.filter(candidate=candidate, job=job).first()
        if not analysis:
            return "local"

        candidate_profile = {
            "full_name": candidate.full_name,
            "skills": candidate.skills or [],
            "years_of_experience": float(candidate.years_of_experience or 0),
            "education": candidate.education or "",
        }
        job_payload = {
            "title": job.title,
            "required_skills": job.required_skills or [],
            "minimum_experience": job.minimum_experience or 0,
            "description": job.description or "",
        }
        analysis_payload = {
            "match_score": analysis.match_score,
            "matched_skills": analysis.matched_skills or [],
            "missing_skills": analysis.missing_skills or [],
            "ranking_position": analysis.ranking_position,
        }
        prompt = build_match_explain_prompt(candidate_profile, job_payload, analysis_payload)

        router = AIRouter()
        provider = router.get_provider()
        text = ""
        response_source = "local"
        try:
            text = provider.generate_text(prompt, timeout=10)
        except Exception:
            try:
                provider = router.get_provider(prefer="gemini")
                text = provider.generate_text(prompt, timeout=10)
            except Exception:
                text = ""

        # Only parse actual AI text, not the prompt itself
        if text:
            parsed = parse_explanation_from_text(text)
            response_source = "groq_ai"
        else:
            parsed = {
                "summary": "AI explanation unavailable.",
                "strengths": [],
                "weaknesses": [],
                "recommendation": "",
            }
            response_source = "local"

        try:
            analysis.ai_summary = parsed.get("summary", "")
            analysis.strengths = "\n".join(parsed.get("strengths", []))
            analysis.weaknesses = "\n".join(parsed.get("weaknesses", []))
            analysis.save(update_fields=["ai_summary", "strengths", "weaknesses", "updated_at"])
        except Exception:
            logger.exception("Failed to persist AI explanation for candidate=%s job=%s", candidate.id, job.id)

        return response_source


candidate_agent = CandidateAgent()
