from django.utils import timezone

from apps.recruitment.services.profile_extractor import ProfileExtractor
from apps.recruitment.utils.text import clean_extracted_text
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class CandidateAnalysisError(Exception):
    pass


class CandidateAnalyzer:
    def __init__(self):
        self.profile_extractor = ProfileExtractor()

    def analyze(self, candidate):
        if not candidate.extracted_text:
            # Fallback: if no extracted CV text is available (PDF read failed, etc.),
            # attempt a best-effort analysis using existing candidate fields provided
            # at upload time (skills, years_of_experience, education). This allows
            # the pipeline to continue even when OCR/PDF extraction fails.
            extracted_data = {
                "full_name": candidate.full_name,
                "email": candidate.email,
                "phone_number": candidate.phone_number,
                "skills": candidate.skills or [],
                "education": candidate.education or "",
                "years_of_experience": candidate.years_of_experience or 0,
                "linkedin_url": candidate.linkedin_url or "",
                "github_url": candidate.github_url or "",
                "portfolio_url": candidate.portfolio_url or "",
            }
            # Persist these values as the 'extracted' results and mark analysis completed.
            try:
                self._update_candidate(candidate, extracted_data)
            except Exception as exc:
                logger.exception("Fallback candidate analysis update failed for id=%s", getattr(candidate, "id", "?"))
                raise CandidateAnalysisError(str(exc)) from exc

            return {
                "candidate_id": candidate.id,
                "analysis_completed": True,
                "extracted_data": extracted_data,
            }

        try:
            # Ensure text is cleaned before extraction
            text = clean_extracted_text(candidate.extracted_text)
            extracted_data = self.profile_extractor.extract(text)
            # Update candidate with as much data as we extracted (partial updates allowed)
            self._update_candidate(candidate, extracted_data)
        except Exception as exc:
            logger.exception("Candidate analysis failed for id=%s", getattr(candidate, "id", "?"))
            # Mark candidate with analysis error but do not raise internal exceptions to callers
            self._mark_failed(candidate, str(exc))
            raise CandidateAnalysisError(str(exc)) from exc

        # Convert Decimal values to float for JSON serialization (years_of_experience)
        serialized = {}
        for k, v in extracted_data.items():
            if isinstance(v, Decimal):
                serialized[k] = float(v)
            else:
                serialized[k] = v

        return {
            "candidate_id": candidate.id,
            "analysis_completed": True,
            "extracted_data": serialized,
        }

    def _update_candidate(self, candidate, data):
        update_fields = ["analysis_completed", "analysis_error", "analyzed_at", "updated_at"]

        for field in [
            "full_name",
            "email",
            "phone_number",
            "skills",
            "education",
            "years_of_experience",
            "linkedin_url",
            "github_url",
            "portfolio_url",
        ]:
            value = data.get(field)
            if value not in [None, "", []]:
                setattr(candidate, field, value)
                update_fields.append(field)

        candidate.analysis_completed = True
        candidate.analysis_error = ""
        candidate.analyzed_at = timezone.now()
        candidate.save(update_fields=sorted(set(update_fields)))

    def _mark_failed(self, candidate, error):
        candidate.analysis_completed = False
        candidate.analysis_error = error
        candidate.analyzed_at = timezone.now()
        candidate.save(
            update_fields=[
                "analysis_completed",
                "analysis_error",
                "analyzed_at",
                "updated_at",
            ]
        )
