from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AnalysisViewSet,
    CandidateViewSet,
    HealthCheckAPIView,
    JobViewSet,
    MatchAPIView,
    JobRankingsAPIView,
    JobParseAPIView,
    MatchExplanationAPIView,
    InterviewQuestionsAPIView,
    AutomationReprocessAPIView,
    AutomationMatchingAPIView,
)


app_name = "recruitment"

router = DefaultRouter()
router.register("jobs", JobViewSet, basename="job")
router.register("candidates", CandidateViewSet, basename="candidate")
router.register("analyses", AnalysisViewSet, basename="analysis")

urlpatterns = [
    path("health/", HealthCheckAPIView.as_view(), name="health-check"),
    path("match/", MatchAPIView.as_view(), name="match"),
    path("jobs/<int:job_id>/rankings/", JobRankingsAPIView.as_view(), name="job-rankings"),
    path("ai/parse-job/", JobParseAPIView.as_view(), name="ai-parse-job"),
    path("ai/match-explanation/", MatchExplanationAPIView.as_view(), name="ai-match-explanation"),
    path("ai/interview-questions/", InterviewQuestionsAPIView.as_view(), name="ai-interview-questions"),
    path("automation/reprocess/", AutomationReprocessAPIView.as_view(), name="automation-reprocess"),
    path("automation/matching/", AutomationMatchingAPIView.as_view(), name="automation-matching"),
]

urlpatterns += router.urls
