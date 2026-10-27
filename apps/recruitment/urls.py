from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

app_name = "recruitment"
router = DefaultRouter()
for name, view in [
    ("jobs", views.JobViewSet),
    ("candidates", views.CandidateViewSet),
    ("analyses", views.AnalysisViewSet),
    ("score-runs", views.ScoreRunViewSet),
    ("applications", views.ApplicationViewSet),
    ("tasks", views.TaskViewSet),
    ("events", views.AuditViewSet),
]:
    router.register(name, view, basename=name.rstrip("s"))
urlpatterns = [
    path("health/", views.HealthCheckAPIView.as_view(), name="health-check"),
    path("dashboard/", views.DashboardAPIView.as_view(), name="dashboard"),
    path("evaluation/", views.EvaluationAPIView.as_view(), name="evaluation"),
    path("match/", views.MatchAPIView.as_view(), name="match"),
    path("jobs/<int:job_id>/rankings/", views.JobRankingsAPIView.as_view(), name="job-rankings"),
    path("ai/parse-job/", views.JobParseAPIView.as_view(), name="ai-parse-job"),
    path("ai/status/", views.AIStatusAPIView.as_view(), name="ai-status"),
    path("ai/check/", views.AICheckAPIView.as_view(), name="ai-check"),
    path(
        "ai/match-explanation/",
        views.MatchExplanationAPIView.as_view(),
        name="ai-match-explanation",
    ),
    path(
        "ai/interview-questions/",
        views.InterviewQuestionsAPIView.as_view(),
        name="ai-interview-questions",
    ),
    path(
        "automation/reprocess/",
        views.AutomationReprocessAPIView.as_view(),
        name="automation-reprocess",
    ),
    path(
        "automation/matching/",
        views.AutomationMatchingAPIView.as_view(),
        name="automation-matching",
    ),
] + router.urls
