from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.conf import settings

from .utils.validators import validate_cv_file


class Job(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="jobs",
    )
    scoring_weights = models.JSONField(default=dict, blank=True)
    revision = models.PositiveIntegerField(default=1)

    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"
        REMOTE = "remote", "Remote"

    title = models.CharField(max_length=255, db_index=True)
    company_name = models.CharField(max_length=255, db_index=True)
    location = models.CharField(max_length=255, blank=True)
    employment_type = models.CharField(
        max_length=30,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
        db_index=True,
    )
    description = models.TextField()
    required_skills = models.JSONField(default=list, blank=True)
    minimum_experience = models.PositiveSmallIntegerField(default=0)
    education_requirement = models.CharField(max_length=255, blank=True)
    salary_range = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Job"
        verbose_name_plural = "Jobs"
        indexes = [
            models.Index(fields=["title", "company_name"]),
            models.Index(fields=["employment_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.title} at {self.company_name}"


class Candidate(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="candidates",
    )
    cv_sha256 = models.CharField(max_length=64, blank=True)
    revision = models.PositiveIntegerField(default=1)
    profile_reviewed_at = models.DateTimeField(null=True, blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    retention_until = models.DateTimeField(null=True, blank=True, db_index=True)

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    full_name = models.CharField(max_length=255, db_index=True)
    email = models.EmailField(db_index=True)
    phone_number = models.CharField(max_length=30, blank=True)
    cv_file = models.FileField(upload_to="cvs/", validators=[validate_cv_file])
    extracted_text = models.TextField(blank=True)
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        db_index=True,
    )
    extraction_success = models.BooleanField(default=False, db_index=True)
    extraction_error = models.TextField(blank=True)
    extracted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    analysis_completed = models.BooleanField(default=False, db_index=True)
    analysis_error = models.TextField(blank=True)
    analyzed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    years_of_experience = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0)],
    )
    skills = models.JSONField(default=list, blank=True)
    education = models.TextField(blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-uploaded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "cv_sha256"],
                condition=~models.Q(cv_sha256=""),
                name="unique_owned_resume_hash",
            )
        ]
        verbose_name = "Candidate"
        verbose_name_plural = "Candidates"
        indexes = [
            models.Index(fields=["full_name", "email"]),
            models.Index(fields=["uploaded_at"]),
            models.Index(fields=["processing_status", "extraction_success"]),
            models.Index(fields=["analysis_completed", "analyzed_at"]),
        ]

    def __str__(self):
        return self.full_name

    @property
    def cv_filename(self):
        return self.cv_file.name.rsplit("/", 1)[-1] if self.cv_file else ""


class Analysis(models.Model):
    scoring_snapshot = models.JSONField(default=dict, blank=True)
    insufficient_requirements = models.BooleanField(default=False)
    generation_provenance = models.JSONField(default=dict, blank=True)
    score_components = models.JSONField(default=dict, blank=True)
    scoring_version = models.CharField(max_length=40, default="rubric-v2")
    provider = models.CharField(max_length=20, default="local")
    provider_model = models.CharField(max_length=100, blank=True)
    prompt_version = models.CharField(max_length=40, default="screening-v2")
    is_stale = models.BooleanField(default=False, db_index=True)
    candidate_revision = models.PositiveIntegerField(default=1)
    job_revision = models.PositiveIntegerField(default=1)

    class RecommendationStatus(models.TextChoices):
        SHORTLISTED = "shortlisted", "Shortlisted"
        CONSIDER = "consider", "Consider"
        REJECTED = "rejected", "Rejected"

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="analyses",
        db_index=True,
    )
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="analyses",
        db_index=True,
    )
    match_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        db_index=True,
    )
    matched_skills = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)
    strengths = models.TextField(blank=True)
    weaknesses = models.TextField(blank=True)
    ai_summary = models.TextField(blank=True)
    recommendation_status = models.CharField(
        max_length=20,
        choices=RecommendationStatus.choices,
        default=RecommendationStatus.CONSIDER,
        db_index=True,
    )
    generated_interview_questions = models.JSONField(default=list, blank=True)
    ranking_position = models.IntegerField(null=True, blank=True, db_index=True)
    analysis_created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-match_score", "-analysis_created_at"]
        verbose_name = "Analysis"
        verbose_name_plural = "Analyses"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(match_score__gte=0, match_score__lte=100),
                name="analysis_score_in_range",
            ),
            models.UniqueConstraint(
                fields=["job", "candidate"],
                name="unique_analysis_per_job_candidate",
            ),
        ]
        indexes = [
            models.Index(fields=["job", "match_score"]),
            models.Index(fields=["candidate", "match_score"]),
            models.Index(fields=["recommendation_status", "match_score"]),
        ]

    def __str__(self):
        return f"{self.candidate.full_name} - {self.job.title} ({self.match_score}%)"


class ScoreRun(models.Model):
    """Append-only application history; deleted with the associated candidate/job."""

    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE, related_name="score_runs")
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def save(self, *args, **kwargs):
        if not self._state.adding or kwargs.get("force_update"):
            from django.core.exceptions import ValidationError

            raise ValidationError("Saved scoring runs cannot be edited. Create a new run.")
        kwargs["force_insert"] = True
        return super().save(*args, **kwargs)


class Application(models.Model):
    class Stage(models.TextChoices):
        APPLIED = "applied", "Applied"
        REVIEW = "review", "Human review"
        SHORTLISTED = "shortlisted", "Shortlisted"
        INTERVIEW = "interview", "Interview"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="applications")
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.APPLIED)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    review_note = models.CharField(max_length=1000, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["job", "candidate"], name="unique_application_pair")
        ]


class AuditEvent(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=60)
    target_type = models.CharField(max_length=30)
    target_id = models.CharField(max_length=30)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class ProcessingTask(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    kind = models.CharField(max_length=30)
    candidate = models.ForeignKey(Candidate, null=True, blank=True, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, null=True, blank=True, on_delete=models.CASCADE)
    dedup_key = models.CharField(max_length=150)
    status = models.CharField(
        max_length=12,
        default="queued",
        choices=[(s, s) for s in ["queued", "running", "completed", "failed"]],
        db_index=True,
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["dedup_key"],
                condition=models.Q(status__in=["queued", "running"]),
                name="unique_active_processing_task",
            )
        ]


class WorkerHeartbeat(models.Model):
    worker_id = models.CharField(max_length=64, unique=True)
    last_seen = models.DateTimeField(auto_now=True)


class ApplicationDecision(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="decisions")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    from_stage = models.CharField(max_length=20)
    to_stage = models.CharField(max_length=20)
    note = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
