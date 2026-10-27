from django.utils import timezone
from .candidate_analyzer import CandidateAnalyzer
from .cv_extractor import CVTextExtractor, CVExtractionError


class CandidateProcessor:
    def process_candidate(self, candidate, filename=None):
        candidate.processing_status = "processing"
        candidate.extraction_error = ""
        candidate.analysis_error = ""
        candidate.analysis_completed = False
        candidate.save()
        try:
            text = CVTextExtractor().extract(candidate.cv_file.path)
            candidate.extracted_text = text
            candidate.extraction_success = True
            candidate.extracted_at = timezone.now()
            candidate.save()
            CandidateAnalyzer().analyze(candidate)
            candidate.refresh_from_db()
            lines = text.splitlines()
            evidence = {}
            for field in [
                "full_name",
                "email",
                "phone_number",
                "skills",
                "education",
                "years_of_experience",
            ]:
                value = getattr(candidate, field)
                terms = value if isinstance(value, list) else [str(value)]
                evidence[field] = [
                    {"line": i + 1, "text": line[:500]}
                    for i, line in enumerate(lines)
                    if any(str(term).lower() in line.lower() for term in terms if term)
                ][:10]
            # Date/experience estimates need their source lines even when the exact numeric result isn't written.
            evidence["years_of_experience"] = [
                {"line": i + 1, "text": line[:500]}
                for i, line in enumerate(lines)
                if any(char.isdigit() for char in line)
                and (" - " in line or "experience" in line.lower())
            ][:10]
            candidate.evidence = evidence
            candidate.processing_status = "completed"
            candidate.save()
            return {"candidate_id": candidate.pk, "status": "completed"}
        except Exception as exc:
            candidate.processing_status = "failed"
            candidate.extraction_success = (
                False if isinstance(exc, CVExtractionError) else candidate.extraction_success
            )
            candidate.extraction_error = (
                str(exc)[:500] if isinstance(exc, CVExtractionError) else ""
            )
            candidate.analysis_error = (
                ""
                if isinstance(exc, CVExtractionError)
                else "Profile analysis failed. Retry or review the document."
            )
            candidate.analysis_completed = False
            candidate.save()
            raise
