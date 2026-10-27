from datetime import timedelta
import hashlib
import json
from django.conf import settings
from django.db import transaction, connection
from django.db.models import Count, Avg, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from .models import (
    Job,
    Candidate,
    Analysis,
    Application,
    ProcessingTask,
    AuditEvent,
    WorkerHeartbeat,
    ApplicationDecision,
    ScoreRun,
)
from .serializers import (
    JobSerializer,
    CandidateSerializer,
    CandidateListSerializer,
    AnalysisSerializer,
    ScoreRunSerializer,
    ApplicationSerializer,
    TaskSerializer,
    AuditSerializer,
    BulkCandidateUploadSerializer,
    PairSerializer,
    JobParseSerializer,
)
from .services.audit import record
from .services.tasks import enqueue
from .services.matching.matcher import match_candidate_to_job
from .services.matching.audit import reproduce
from .services.matching.ranking_engine import top_candidates_for_job
from .services.ai.router import AIRouter
from .services.ai.contracts import prompt
from .services.ai.prompts.job_parser import parse_job_from_text


class HealthCheckAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return Response({"status": "ok", "message": "API and database ready"})
        except Exception:
            return Response({"status": "unavailable"}, status=503)


class CostlyActionsMixin:
    def get_throttles(self):
        if not getattr(settings, "API_THROTTLING_ENABLED", True):
            return []
        throttles = super().get_throttles()
        if self.action in {
            "create",
            "update",
            "partial_update",
            "bulk_upload",
            "analyze",
            "match",
            "retry",
        }:
            self.throttle_scope = "expensive"
            throttles.append(ScopedRateThrottle())
        return throttles


class JobViewSet(CostlyActionsMixin, ModelViewSet):
    serializer_class = JobSerializer
    search_fields = ["title", "company_name", "description"]
    ordering_fields = ["created_at", "title"]

    def get_queryset(self):
        return (
            Job.objects.filter(owner=self.request.user)
            .annotate(analyses_count=Count("analyses"))
            .order_by("-created_at", "-id")
        )

    @transaction.atomic
    def perform_create(self, serializer):
        job = serializer.save(owner=self.request.user)
        enqueue(self.request.user, "match_job", job=job)
        record(self.request.user, "job.created", job)

    @transaction.atomic
    def perform_update(self, serializer):
        serializer.instance = Job.objects.select_for_update().get(pk=serializer.instance.pk)
        job = serializer.save(revision=serializer.instance.revision + 1)
        job.analyses.update(is_stale=True, ranking_position=None)
        enqueue(self.request.user, "match_job", job=job)
        record(self.request.user, "job.updated", job, fields=list(serializer.validated_data))

    @transaction.atomic
    def perform_destroy(self, instance):
        record(self.request.user, "job.deleted", instance)
        instance.delete()

    @action(detail=True, methods=["post"])
    def match(self, request, pk=None):
        task = enqueue(request.user, "match_job", job=self.get_object())
        return Response(TaskSerializer(task).data, status=202)


class CandidateViewSet(CostlyActionsMixin, ModelViewSet):
    serializer_class = CandidateSerializer
    search_fields = ["full_name", "email", "skills"]
    ordering_fields = ["uploaded_at", "full_name", "years_of_experience"]

    def get_queryset(self):
        qs = (
            Candidate.objects.filter(owner=self.request.user)
            .annotate(analyses_count=Count("analyses"))
            .order_by("-uploaded_at", "-id")
        )
        value = self.request.query_params.get("processing_status")
        if value:
            qs = qs.filter(processing_status=value)
        for key, lookup in [
            ("min_experience", "years_of_experience__gte"),
            ("max_experience", "years_of_experience__lte"),
        ]:
            if key in self.request.query_params:
                try:
                    value = float(self.request.query_params[key])
                    if not 0 <= value <= 100:
                        raise ValueError()
                except ValueError:
                    raise ValidationError({key: "Expected a number between 0 and 100."})
                qs = qs.filter(**{lookup: value})
        return qs

    def get_serializer_class(self):
        return CandidateListSerializer if self.action == "list" else CandidateSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        candidate = serializer.save(
            owner=self.request.user,
            retention_until=timezone.now() + timedelta(days=settings.CV_RETENTION_DAYS),
        )
        enqueue(self.request.user, "extract", candidate=candidate)
        record(self.request.user, "candidate.created", candidate)

    @transaction.atomic
    def perform_update(self, serializer):
        serializer.instance = Candidate.objects.select_for_update().get(pk=serializer.instance.pk)
        changes = {"revision": serializer.instance.revision + 1}
        new_file = "cv_file" in serializer.validated_data
        if new_file:
            changes.update(
                processing_status="pending",
                extracted_text="",
                extraction_success=False,
                analysis_completed=False,
                evidence={},
                profile_reviewed_at=None,
            )
        else:
            changes["profile_reviewed_at"] = timezone.now()
        candidate = serializer.save(**changes)
        candidate.analyses.update(is_stale=True, ranking_position=None)
        enqueue(
            self.request.user, "extract" if new_file else "match_candidate", candidate=candidate
        )
        record(
            self.request.user,
            "candidate.document_replaced" if new_file else "candidate.profile_reviewed",
            candidate,
            fields=[key for key in serializer.validated_data if key != "cv_sha256"],
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        record(self.request.user, "candidate.deleted", instance)
        instance.delete()

    @action(detail=True, methods=["get"])
    def cv(self, request, pk=None):
        candidate = self.get_object()
        if not candidate.cv_file:
            return Response({"detail": "No resume file exists."}, status=404)
        try:
            response = FileResponse(
                candidate.cv_file.open("rb"), as_attachment=True, filename=candidate.cv_filename
            )
        except FileNotFoundError:
            return Response({"detail": "Resume file is unavailable."}, status=404)
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        record(request.user, "candidate.cv_downloaded", candidate)
        return response

    @action(detail=True, methods=["post"])
    def analyze(self, request, pk=None):
        candidate = self.get_object()
        kind = (
            "extract"
            if candidate.processing_status == "failed" or not candidate.extracted_text
            else "match_candidate"
        )
        task = enqueue(request.user, kind, candidate=candidate)
        return Response(TaskSerializer(task).data, status=202)

    @action(
        detail=False,
        methods=["post"],
        url_path="bulk-upload",
        parser_classes=[MultiPartParser, FormParser],
    )
    def bulk_upload(self, request):
        upload = BulkCandidateUploadSerializer(data={"files": request.FILES.getlist("files")})
        upload.is_valid(raise_exception=True)
        results = []
        for file in upload.validated_data["files"]:
            filename = file.name
            serializer = CandidateSerializer(
                data={
                    "full_name": filename.rsplit(".", 1)[0][:255],
                    "email": "unknown@example.invalid",
                    "cv_file": file,
                },
                context={"request": request},
            )
            if serializer.is_valid():
                try:
                    self.perform_create(serializer)
                    results.append(
                        {
                            "filename": filename,
                            "status": "queued",
                            "candidate_id": serializer.instance.pk,
                        }
                    )
                except Exception:
                    results.append(
                        {
                            "filename": filename,
                            "status": "failed",
                            "error": "Unable to save document.",
                        }
                    )
            else:
                results.append(
                    {"filename": filename, "status": "failed", "error": serializer.errors}
                )
        queued = sum(r["status"] == "queued" for r in results)
        return Response(
            {"queued_count": queued, "failed_count": len(results) - queued, "results": results},
            status=202 if queued == len(results) else 207,
        )


class AnalysisViewSet(ReadOnlyModelViewSet):
    serializer_class = AnalysisSerializer
    ordering_fields = ["match_score", "analysis_created_at"]

    def get_queryset(self):
        qs = Analysis.objects.filter(
            job__owner=self.request.user, candidate__owner=self.request.user
        ).select_related("job", "candidate")
        for key in ["job", "candidate"]:
            if key in self.request.query_params:
                try:
                    qs = qs.filter(**{key + "_id": int(self.request.query_params[key])})
                except ValueError:
                    raise ValidationError("Invalid resource ID.")
        return qs

    @action(detail=True, methods=["get"])
    def reproduce(self, request, pk=None):
        analysis = self.get_object()
        return Response(
            {
                **reproduce(analysis.scoring_snapshot, analysis.match_score),
                "is_stale": analysis.is_stale,
            }
        )


class ScoreRunViewSet(ReadOnlyModelViewSet):
    serializer_class = ScoreRunSerializer

    def get_queryset(self):
        qs = ScoreRun.objects.filter(
            analysis__job__owner=self.request.user,
            analysis__candidate__owner=self.request.user,
        )
        if "analysis" in self.request.query_params:
            try:
                qs = qs.filter(analysis_id=int(self.request.query_params["analysis"]))
            except ValueError:
                raise ValidationError("Invalid analysis ID.")
        return qs

    @action(detail=True, methods=["get"])
    def reproduce(self, request, pk=None):
        return Response(reproduce(self.get_object().snapshot))


class EvaluationAPIView(APIView):
    def get(self, request):
        # Only serve the bundled synthetic benchmark. Private custom evaluations stay local.
        try:
            path = settings.BASE_DIR / "evaluation" / "dataset.json"
            report = json.loads(
                (settings.BASE_DIR / "docs" / "evaluation-results.json").read_text(encoding="utf-8")
            )
            if report["dataset_sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
                return Response(
                    {"detail": "The bundled evaluation report is stale. Regenerate it."}, status=503
                )
            return Response(report)
        except (OSError, ValueError, KeyError):
            return Response({"detail": "The bundled evaluation report is unavailable."}, status=503)


class ApplicationViewSet(ModelViewSet):
    serializer_class = ApplicationSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = (
            Application.objects.filter(
                job__owner=self.request.user, candidate__owner=self.request.user
            )
            .select_related("job", "candidate", "reviewer")
            .prefetch_related("decisions")
        )
        if "candidate" in self.request.query_params:
            try:
                qs = qs.filter(candidate_id=int(self.request.query_params["candidate"]))
            except ValueError:
                raise ValidationError("Invalid candidate ID.")
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        application = serializer.save()
        record(self.request.user, "application.created", application, stage=application.stage)

    @transaction.atomic
    def perform_update(self, serializer):
        locked = Application.objects.select_for_update().get(pk=serializer.instance.pk)
        serializer.instance = locked
        # Revalidate stage against the locked current state.
        serializer.validate(serializer.validated_data)
        previous = locked.stage
        application = serializer.save(reviewer=self.request.user)
        if previous != application.stage:
            ApplicationDecision.objects.create(
                application=application,
                reviewer=self.request.user,
                from_stage=previous,
                to_stage=application.stage,
                note=application.review_note,
            )
        record(
            self.request.user,
            "application.reviewed",
            application,
            from_stage=previous,
            to_stage=application.stage,
        )


class TaskViewSet(CostlyActionsMixin, ReadOnlyModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        return ProcessingTask.objects.filter(owner=self.request.user).order_by("-created_at", "-id")

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def retry(self, request, pk=None):
        old = self.get_object()
        if old.status not in {"failed", "completed"}:
            raise ValidationError("This task is already active.")
        resource = old.candidate or old.job
        if old.candidate and old.kind == "extract":
            if resource.profile_reviewed_at:
                raise ValidationError(
                    "Replace the document explicitly to re-extract a reviewed profile."
                )
            resource.processing_status = "pending"
            resource.save(update_fields=["processing_status"])
        task = enqueue(request.user, old.kind, candidate=old.candidate, job=old.job)
        record(request.user, "task.retried", task)
        return Response(TaskSerializer(task).data, status=202)


class AuditViewSet(ReadOnlyModelViewSet):
    serializer_class = AuditSerializer

    def get_queryset(self):
        return AuditEvent.objects.filter(owner=self.request.user)


class ExpensiveAPIView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "expensive"


def pair(request):
    serializer = PairSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    values = serializer.validated_data
    return (
        get_object_or_404(Candidate, pk=values["candidate_id"], owner=request.user),
        get_object_or_404(Job, pk=values["job_id"], owner=request.user),
    )


class MatchAPIView(ExpensiveAPIView):
    def post(self, request):
        candidate, job = pair(request)
        if not candidate.analysis_completed and not candidate.profile_reviewed_at:
            raise ValidationError("Process or review the candidate profile before matching.")
        result = match_candidate_to_job(candidate, job)
        record(request.user, "analysis.matched", job, candidate_id=candidate.pk)
        return Response(result)


class JobRankingsAPIView(APIView):
    def get(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id, owner=request.user)
        return Response(top_candidates_for_job(job.pk))


class AIStatusAPIView(APIView):
    def get(self, request):
        return Response(AIRouter().configuration())


class AICheckAPIView(ExpensiveAPIView):
    def post(self, request):
        # Fixed synthetic input: testing a connection never sends candidate information.
        return Response(AIRouter().test_connection())


class JobParseAPIView(ExpensiveAPIView):
    def post(self, request):
        serializer = JobParseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        description = serializer.validated_data["job_description"]
        router = AIRouter()
        result, source, model = router.generate_json(
            prompt(
                "Return skills (string array), role_type, experience_level and summary (strings).",
                {"job_description": description},
            ),
            "parse",
        )
        return Response(
            {
                **(result or parse_job_from_text(description)),
                **router.metadata(source),
                "model": model,
                "prompt_version": "screening-v2",
            }
        )


class MatchExplanationAPIView(ExpensiveAPIView):
    def post(self, request):
        candidate, job = pair(request)
        analysis = get_object_or_404(Analysis, candidate=candidate, job=job, is_stale=False)
        payload = {
            "skills": candidate.skills,
            "required_skills": job.required_skills,
            "matched": analysis.matched_skills,
            "missing": analysis.missing_skills,
            "score_components": analysis.score_components,
        }
        router = AIRouter()
        result, source, model = router.generate_json(
            prompt(
                "Return summary (string), strengths and weaknesses (string arrays), recommendation (string). Ground every statement in the supplied fields.",
                payload,
            ),
            "explain",
        )
        result = result or {
            "summary": "Local rubric comparison. Human review is required.",
            "strengths": [f"Matched skill: {s}" for s in analysis.matched_skills],
            "weaknesses": [f"Missing skill evidence: {s}" for s in analysis.missing_skills],
            "recommendation": "Review the resume evidence before deciding.",
        }
        analysis.ai_summary = result["summary"]
        analysis.strengths = "\n".join(result["strengths"])
        analysis.weaknesses = "\n".join(result["weaknesses"])
        analysis.save(update_fields=["ai_summary", "strengths", "weaknesses", "updated_at"])
        analysis.generation_provenance["explanation"] = {
            **router.metadata(source),
            "provider": source,
            "model": model,
            "prompt_version": "screening-v2",
        }
        analysis.save(update_fields=["generation_provenance"])
        record(request.user, "analysis.explained", analysis, provider=source)
        return Response({**result, **router.metadata(source), "model": model})


class InterviewQuestionsAPIView(ExpensiveAPIView):
    def post(self, request):
        candidate, job = pair(request)
        analysis = get_object_or_404(Analysis, candidate=candidate, job=job, is_stale=False)
        router = AIRouter()
        result, source, model = router.generate_json(
            prompt(
                "Return technical_questions, behavioral_questions, skill_based_questions (string arrays).",
                {
                    "skills": candidate.skills,
                    "required_skills": job.required_skills,
                    "missing": analysis.missing_skills,
                },
            ),
            "interview",
        )
        result = result or {
            "technical_questions": [
                f"Describe a project where you used {skill}."
                for skill in analysis.matched_skills[:4]
            ],
            "behavioral_questions": ["Describe a difficult team decision and your role."],
            "skill_based_questions": [
                f"How would you approach learning {skill}?" for skill in analysis.missing_skills[:4]
            ],
        }
        analysis.generated_interview_questions = sum(
            [
                result[k]
                for k in ["technical_questions", "behavioral_questions", "skill_based_questions"]
            ],
            [],
        )
        analysis.save(update_fields=["generated_interview_questions", "updated_at"])
        analysis.generation_provenance["interview"] = {
            **router.metadata(source),
            "provider": source,
            "model": model,
            "prompt_version": "screening-v2",
        }
        analysis.save(update_fields=["generation_provenance"])
        record(request.user, "analysis.questions_generated", analysis, provider=source)
        return Response({**result, **router.metadata(source), "model": model})


class AutomationReprocessAPIView(ExpensiveAPIView):
    def post(self, request):
        tasks = [
            enqueue(
                request.user, "match_candidate" if c.extracted_text else "extract", candidate=c
            ).pk
            for c in Candidate.objects.filter(owner=request.user)
        ]
        return Response({"queued": len(tasks), "task_ids": tasks}, status=202)


class AutomationMatchingAPIView(ExpensiveAPIView):
    def post(self, request):
        tasks = [
            enqueue(request.user, "match_job", job=j).pk
            for j in Job.objects.filter(owner=request.user)
        ]
        return Response({"queued": len(tasks), "task_ids": tasks}, status=202)


class DashboardAPIView(APIView):
    def get(self, request):
        owner = request.user
        analyses = Analysis.objects.filter(
            job__owner=owner,
            candidate__owner=owner,
            is_stale=False,
            insufficient_requirements=False,
        )
        scores = analyses.aggregate(
            total=Count("id"),
            average=Avg("match_score"),
            high=Count("id", filter=Q(match_score__gt=80)),
            medium=Count("id", filter=Q(match_score__gte=50, match_score__lte=80)),
            low=Count("id", filter=Q(match_score__lt=50)),
        )
        tasks = ProcessingTask.objects.filter(owner=owner)
        return Response(
            {
                "candidates": Candidate.objects.filter(owner=owner).count(),
                "jobs": Job.objects.filter(owner=owner).count(),
                "scores": scores,
                "queued": tasks.filter(status="queued").count(),
                "failed": tasks.filter(status="failed").count(),
                "worker_online": WorkerHeartbeat.objects.filter(
                    last_seen__gte=timezone.now() - timedelta(seconds=30)
                ).exists(),
                "events": AuditSerializer(
                    AuditEvent.objects.filter(owner=owner)[:10], many=True
                ).data,
            }
        )
