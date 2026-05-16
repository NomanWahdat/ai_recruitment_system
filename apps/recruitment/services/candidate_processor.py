from django.db import transaction
from django.utils import timezone

from apps.recruitment.models import Candidate
from apps.recruitment.services.candidate_analyzer import CandidateAnalyzer
from apps.recruitment.services.cv_extractor import CVExtractionError, CVTextExtractor
from apps.recruitment.services.file_handler import CVFileHandler


class CandidateProcessor:
    def __init__(self):
        self.file_handler = CVFileHandler()
        self.extractor = CVTextExtractor()
        self.analyzer = CandidateAnalyzer()

    def create_candidate_from_cv(self, file):
        from apps.recruitment.services.automation.agent_orchestrator import orchestrator

        try:
            original_name, prepared_file = self.file_handler.prepare_upload(file)
        except Exception as exc:
            return {
                "filename": file.name,
                "status": Candidate.ProcessingStatus.FAILED,
                "error": self.file_handler.format_validation_error(exc),
            }

        with transaction.atomic():
            candidate = Candidate.objects.create(
                full_name=self._candidate_name_from_filename(original_name),
                email=self._placeholder_email(original_name),
                cv_file=prepared_file,
                processing_status=Candidate.ProcessingStatus.PENDING,
            )

        # Emit the event so the automation layer can drive the pipeline.
        event_results = orchestrator.emit(
            "candidate_created",
            {
                "candidate_id": candidate.id,
                "filename": original_name,
                "source": "bulk_upload",
            },
        )

        # Fall back to the legacy flow only if no automation handler returned a result.
        if event_results:
            primary_result = next((result for result in event_results if isinstance(result, dict)), None)
            if primary_result:
                return primary_result

        return self.process_candidate(candidate, original_name)

    def process_candidate(self, candidate, filename=None):
        from apps.recruitment.services.automation.agent_orchestrator import orchestrator

        filename = filename or candidate.cv_filename
        candidate.processing_status = Candidate.ProcessingStatus.PROCESSING
        candidate.extraction_success = False
        candidate.extraction_error = ""
        candidate.save(
            update_fields=[
                "processing_status",
                "extraction_success",
                "extraction_error",
                "updated_at",
            ]
        )

        try:
            extracted_text = self.extractor.extract(candidate.cv_file.path)
            if not extracted_text:
                raise CVExtractionError("No readable text found in CV.")
        except Exception as exc:
            # Mark extraction as failed but continue with best-effort analysis using
            # the analyzer fallback (which can use fields provided at upload)
            candidate.processing_status = Candidate.ProcessingStatus.COMPLETED
            candidate.extraction_success = False
            candidate.extraction_error = str(exc)
            candidate.extracted_at = timezone.now()
            candidate.save(
                update_fields=[
                    "processing_status",
                    "extraction_success",
                    "extraction_error",
                    "extracted_at",
                    "updated_at",
                ]
            )

            # Proceed to analysis using whatever candidate data exists (analyzer will
            # fall back if extracted_text is empty).
            analysis_result = self._analyze_candidate(candidate)

            orchestrator.emit(
                "candidate_analyzed",
                {
                    "candidate_id": candidate.id,
                    "filename": filename,
                    "analysis_completed": analysis_result["analysis_completed"],
                    "analysis_error": analysis_result["analysis_error"],
                },
            )

            return {
                "filename": filename,
                "status": Candidate.ProcessingStatus.COMPLETED,
                "candidate_id": candidate.id,
                "analysis_completed": analysis_result["analysis_completed"],
                "analysis_error": analysis_result["analysis_error"],
            }

        candidate.extracted_text = extracted_text
        candidate.processing_status = Candidate.ProcessingStatus.COMPLETED
        candidate.extraction_success = True
        candidate.extraction_error = ""
        candidate.extracted_at = timezone.now()
        candidate.save(
            update_fields=[
                "extracted_text",
                "processing_status",
                "extraction_success",
                "extraction_error",
                "extracted_at",
                "updated_at",
            ]
        )

        analysis_result = self._analyze_candidate(candidate)

        orchestrator.emit(
            "candidate_analyzed",
            {
                "candidate_id": candidate.id,
                "filename": filename,
                "analysis_completed": analysis_result["analysis_completed"],
                "analysis_error": analysis_result["analysis_error"],
            },
        )
        return {
            "filename": filename,
            "status": Candidate.ProcessingStatus.COMPLETED,
            "candidate_id": candidate.id,
            "analysis_completed": analysis_result["analysis_completed"],
            "analysis_error": analysis_result["analysis_error"],
        }

    def bulk_upload(self, files):
        results = [self.create_candidate_from_cv(file) for file in files]
        success_count = sum(
            1
            for result in results
            if result.get("status") == Candidate.ProcessingStatus.COMPLETED
        )
        failed_count = len(results) - success_count
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results,
        }

    def _candidate_name_from_filename(self, filename):
        stem = filename.rsplit(".", 1)[0]
        cleaned = stem.replace("_", " ").replace("-", " ").strip()
        return cleaned.title() or "Unknown Candidate"

    def _placeholder_email(self, filename):
        safe_name = filename.rsplit(".", 1)[0].lower()
        safe_name = "".join(char if char.isalnum() else "." for char in safe_name)
        safe_name = ".".join(part for part in safe_name.split(".") if part)
        safe_name = safe_name or "candidate"
        return f"{safe_name}@placeholder.local"

    def _analyze_candidate(self, candidate):
        try:
            self.analyzer.analyze(candidate)
            return {
                "analysis_completed": True,
                "analysis_error": "",
            }
        except Exception as exc:
            return {
                "analysis_completed": False,
                "analysis_error": str(exc),
            }
