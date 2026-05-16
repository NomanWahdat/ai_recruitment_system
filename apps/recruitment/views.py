import logging

from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView

from .models import Analysis, Candidate, Job
from .serializers import (
    AnalysisSerializer,
    BulkCandidateUploadSerializer,
    CandidateAnalysisSerializer,
    CandidateSerializer,
    HealthCheckSerializer,
    JobSerializer,
)
from .services.candidate_analyzer import CandidateAnalyzer
from .services.candidate_processor import CandidateProcessor
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from apps.recruitment.services.matching.matcher import match_candidate_to_job
from apps.recruitment.services.ai.router import AIRouter
from apps.recruitment.utils.text import extract_json_from_text
from apps.recruitment.services.ai.prompts.job_parser import build_job_parse_prompt, parse_job_from_text
from apps.recruitment.services.ai.prompts.match_explainer import build_match_explain_prompt, parse_explanation_from_text
from apps.recruitment.services.ai.prompts.interview_generator import build_interview_prompt, generate_questions_from_text
from .serializers import (
    AnalysisSerializer,
    BulkCandidateUploadSerializer,
    CandidateAnalysisSerializer,
    CandidateSerializer,
    HealthCheckSerializer,
    JobSerializer,
    JobParseSerializer,
    JobParseResponseSerializer,
    AIMatchExplainRequestSerializer,
    AIMatchExplainResponseSerializer,
    AIInterviewRequestSerializer,
    AIInterviewResponseSerializer,
)

from apps.recruitment.services.matching.ranking_engine import top_candidates_for_job
from apps.recruitment.services.automation.agent_orchestrator import orchestrator
from apps.recruitment.services.automation.workflow_engine import workflow_engine


class HealthCheckAPIView(APIView):
    serializer_class = HealthCheckSerializer

    def get(self, request):
        data = {
            "status": "ok",
            "message": "AI Recruitment System API Running",
        }
        serializer = self.serializer_class(data)
        return Response(serializer.data)


class JobViewSet(ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer

    def perform_create(self, serializer):
        job = serializer.save()
        orchestrator.emit(
            "job_created",
            {
                "job_id": job.id,
                "source": "job_api",
            },
        )


class CandidateViewSet(ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer

    def perform_create(self, serializer):
        candidate = serializer.save()
        orchestrator.emit(
            "candidate_created",
            {
                "candidate_id": candidate.id,
                "source": "candidate_api",
            },
        )

        # Ensure CV extraction and analysis run even if automation handlers are not
        # wired or returned no actionable result. Run processing in a background
        # thread to avoid blocking the API response.
        try:
            from apps.recruitment.services.candidate_processor import CandidateProcessor
            import threading

            def _background_process(cand_id):
                try:
                    cp = CandidateProcessor()
                    cand = Candidate.objects.filter(id=cand_id).first()
                    if cand:
                        cp.process_candidate(cand, cand.cv_filename)
                except Exception:
                    # background errors should not affect API response
                    logger = logging.getLogger(__name__)
                    logger.exception("Background candidate processing failed for %s", cand_id)

            thread = threading.Thread(target=_background_process, args=(candidate.id,), daemon=True)
            thread.start()
        except Exception:
            # Do not block or raise on any background scheduling issues
            pass

    @action(
        detail=False,
        methods=["post"],
        url_path="bulk-upload",
        parser_classes=[MultiPartParser, FormParser],
    )
    def bulk_upload(self, request):
        files = request.FILES.getlist("files")
        serializer = BulkCandidateUploadSerializer(data={"files": files})
        serializer.is_valid(raise_exception=True)

        processor = CandidateProcessor()
        response_data = processor.bulk_upload(serializer.validated_data["files"])
        response_status = (
            status.HTTP_207_MULTI_STATUS
            if response_data["failed_count"]
            else status.HTTP_201_CREATED
        )
        return Response(response_data, status=response_status)

    @action(detail=True, methods=["post"], url_path="analyze")
    def analyze(self, request, pk=None):
        candidate = self.get_object()
        analyzer = CandidateAnalyzer()

        try:
            response_data = analyzer.analyze(candidate)
            serializer = CandidateAnalysisSerializer(response_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as exc:
            response_data = {
                "candidate_id": candidate.id,
                "analysis_completed": False,
                "error": str(exc),
            }
            serializer = CandidateAnalysisSerializer(response_data)
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)


class AnalysisViewSet(ModelViewSet):
    queryset = Analysis.objects.select_related("job", "candidate")
    serializer_class = AnalysisSerializer


class MatchAPIView(APIView):
    parser_classes = [JSONParser]
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request):
        data = request.data or {}
        candidate_id = data.get("candidate_id")
        job_id = data.get("job_id")

        if not candidate_id or not job_id:
            return Response({"detail": "candidate_id and job_id required"}, status=status.HTTP_400_BAD_REQUEST)

        candidate = Candidate.objects.filter(id=candidate_id).first()
        job = Job.objects.filter(id=job_id).first()
        if not candidate or not job:
            return Response({"detail": "candidate or job not found"}, status=status.HTTP_404_NOT_FOUND)

        result = match_candidate_to_job(candidate, job)
        # Indicate if the score includes LLM component
        if result.get("llm_score") is not None:
            result["response_source"] = "hybrid (deterministic + groq_ai)"
        else:
            result["response_source"] = "local (deterministic only)"
        return Response(result, status=status.HTTP_200_OK)


class JobRankingsAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, job_id: int):
        resp = top_candidates_for_job(job_id, top_n=10)
        return Response(resp, status=status.HTTP_200_OK)


class JobParseAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request):
        serializer = JobParseSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        job_description = serializer.validated_data["job_description"]

        router = AIRouter()
        provider = router.get_provider()

        prompt = build_job_parse_prompt(job_description)
        ai_text = ""
        try:
            ai_text = provider.generate_text(prompt, timeout=10)
        except Exception:
            # fallback to gemini
            try:
                provider = router.get_provider(prefer="gemini")
                ai_text = provider.generate_text(prompt, timeout=10)
            except Exception:
                ai_text = ""

        # Try to parse AI response as JSON first; fall back to deterministic parser
        result = None
        response_source = "local"
        if ai_text:
            parsed, ok = extract_json_from_text(ai_text)
            if ok and parsed:
                result = {
                    "skills": parsed.get("skills", []),
                    "role_type": parsed.get("role_type", ""),
                    "experience_level": parsed.get("experience_level", ""),
                    "summary": parsed.get("summary", ""),
                }
                response_source = "groq_ai"

        if not result:
            result = parse_job_from_text(job_description)
            response_source = "local"

        out_serializer = JobParseResponseSerializer(result)
        data = out_serializer.data
        data["response_source"] = response_source
        return Response(data, status=status.HTTP_200_OK)


class MatchExplanationAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request):
        serializer = AIMatchExplainRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        candidate_id = serializer.validated_data["candidate_id"]
        job_id = serializer.validated_data["job_id"]

        candidate = Candidate.objects.filter(id=candidate_id).first()
        job = Job.objects.filter(id=job_id).first()
        if not candidate or not job:
            return Response({"detail": "candidate or job not found"}, status=status.HTTP_404_NOT_FOUND)

        analysis = Analysis.objects.filter(candidate=candidate, job=job).first()
        if not analysis:
            return Response({"detail": "Analysis not found for this job and candidate. Run matching first."}, status=status.HTTP_404_NOT_FOUND)

        # Build structured safe payload
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
        try:
            text = provider.generate_text(prompt, timeout=12)
        except Exception:
            try:
                provider = router.get_provider(prefer="gemini")
                text = provider.generate_text(prompt, timeout=12)
            except Exception as exc:
                # log and fallback empty
                text = ""

        # Only parse actual AI text, not the prompt itself
        response_source = "local"
        if text:
            parsed = parse_explanation_from_text(text)
            response_source = "groq_ai"
        else:
            parsed = {
                "summary": "AI explanation unavailable. Match is based on deterministic skill and experience scoring.",
                "strengths": [],
                "weaknesses": [],
                "recommendation": "",
            }
            response_source = "local"

        # Persist brief AI explanation to analysis
        try:
            analysis.ai_summary = parsed.get("summary", "")
            analysis.strengths = "\n".join(parsed.get("strengths", []))
            analysis.weaknesses = "\n".join(parsed.get("weaknesses", []))
            analysis.save(update_fields=["ai_summary", "strengths", "weaknesses", "updated_at"])
        except Exception:
            pass

        out_serializer = AIMatchExplainResponseSerializer(parsed)
        data = out_serializer.data
        data["response_source"] = response_source
        return Response(data, status=status.HTTP_200_OK)


class InterviewQuestionsAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request):
        serializer = AIInterviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        candidate_id = serializer.validated_data["candidate_id"]
        job_id = serializer.validated_data["job_id"]

        candidate = Candidate.objects.filter(id=candidate_id).first()
        job = Job.objects.filter(id=job_id).first()
        if not candidate or not job:
            return Response({"detail": "candidate or job not found"}, status=status.HTTP_404_NOT_FOUND)

        analysis = Analysis.objects.filter(candidate=candidate, job=job).first()
        if not analysis:
            return Response({"detail": "Analysis not found for this job and candidate. Run matching first."}, status=status.HTTP_404_NOT_FOUND)

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
        }

        prompt = build_interview_prompt(candidate_profile, job_payload, analysis_payload)

        router = AIRouter()
        provider = router.get_provider()
        text = ""
        try:
            text = provider.generate_text(prompt, timeout=12)
        except Exception:
            try:
                provider = router.get_provider(prefer="gemini")
                text = provider.generate_text(prompt, timeout=12)
            except Exception:
                text = ""

        response_source = "local"
        if text:
            questions = generate_questions_from_text(text)
            # Check if we got AI-parsed questions (not just fallback)
            parsed_check, ok = extract_json_from_text(text)
            if ok:
                response_source = "groq_ai"
        else:
            questions = generate_questions_from_text("")
            response_source = "local"

        # Persist generated questions into analysis.generated_interview_questions
        try:
            analysis.generated_interview_questions = (
                questions.get("technical_questions", [])
                + questions.get("behavioral_questions", [])
                + questions.get("skill_based_questions", [])
            )
            analysis.save(update_fields=["generated_interview_questions", "updated_at"])
        except Exception:
            pass

        out_serializer = AIInterviewResponseSerializer(questions)
        data = out_serializer.data
        data["response_source"] = response_source
        return Response(data, status=status.HTTP_200_OK)


class AutomationReprocessAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request):
        result = workflow_engine.reprocess_all()
        return Response(result, status=status.HTTP_200_OK)


class AutomationMatchingAPIView(APIView):
    """Re-run only the matching engine for all candidate-job pairs (no re-extraction)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request):
        from apps.recruitment.models import Candidate, Job
        from apps.recruitment.services.matching.matcher import match_candidate_to_job
        from apps.recruitment.services.matching.ranking_engine import top_candidates_for_job

        candidates = Candidate.objects.all()
        jobs = Job.objects.all()
        results = []
        overall_sources = []

        for job in jobs:
            job_matches = []
            for candidate in candidates:
                try:
                    match_result = match_candidate_to_job(candidate, job)
                    source = "groq_ai" if match_result.get("llm_score") is not None else "local"
                    overall_sources.append(source)
                    job_matches.append({
                        "candidate_id": candidate.id,
                        "candidate_name": candidate.full_name,
                        "match_score": match_result.get("match_score"),
                        "llm_score": match_result.get("llm_score"),
                        "matched_skills": match_result.get("matched_skills", []),
                        "missing_skills": match_result.get("missing_skills", []),
                        "response_source": source,
                    })
                except Exception as exc:
                    job_matches.append({
                        "candidate_id": candidate.id,
                        "error": str(exc),
                    })

            # Re-rank after matching
            try:
                ranking = top_candidates_for_job(job.id, top_n=50)
            except Exception:
                ranking = {}

            results.append({
                "job_id": job.id,
                "job_title": job.title,
                "matches": job_matches,
                "ranking": ranking.get("top_candidates", []),
            })

        matching_source = "groq_ai" if any(s == "groq_ai" for s in overall_sources) else "local"

        return Response({
            "jobs_processed": len(jobs),
            "candidates_processed": len(candidates),
            "response_source": matching_source,
            "results": results,
        }, status=status.HTTP_200_OK)
