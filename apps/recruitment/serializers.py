from rest_framework import serializers
from .models import (
    Analysis,
    Candidate,
    Job,
    Application,
    ProcessingTask,
    AuditEvent,
    ApplicationDecision,
    ScoreRun,
)
from .utils.validators import validate_cv_file, file_digest, build_safe_filename
from .services.matching.scorer import validate_weights


def skill_list(value):
    if (
        not isinstance(value, list)
        or len(value) > 100
        or any(not isinstance(v, str) or not v.strip() or len(v) > 100 for v in value)
    ):
        raise serializers.ValidationError("Provide at most 100 nonempty skill strings.")
    return list(dict.fromkeys(v.strip() for v in value))


class HealthCheckSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()


class JobSerializer(serializers.ModelSerializer):
    analyses_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Job
        exclude = ["owner"]
        read_only_fields = ["id", "revision", "created_at", "updated_at"]

    def validate_required_skills(self, value):
        return skill_list(value)

    def validate_scoring_weights(self, value):
        try:
            return validate_weights(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))


class CandidateSerializer(serializers.ModelSerializer):
    cv_filename = serializers.CharField(read_only=True)
    analyses_count = serializers.IntegerField(read_only=True, default=0)
    cv_download_url = serializers.SerializerMethodField()

    class Meta:
        model = Candidate
        exclude = ["owner", "cv_sha256"]
        read_only_fields = [
            "id",
            "extracted_text",
            "processing_status",
            "extraction_success",
            "extraction_error",
            "extracted_at",
            "analysis_completed",
            "analysis_error",
            "analyzed_at",
            "uploaded_at",
            "updated_at",
            "evidence",
            "revision",
            "profile_reviewed_at",
            "retention_until",
        ]
        extra_kwargs = {"cv_file": {"write_only": True}}

    def get_cv_download_url(self, obj):
        return (
            self.context["request"].build_absolute_uri(f"/api/candidates/{obj.pk}/cv/")
            if obj.cv_file
            else None
        )

    def validate_skills(self, value):
        return skill_list(value)

    def validate(self, attrs):
        file = attrs.get("cv_file")
        if file:
            validate_cv_file(file)
            digest = file_digest(file)
            query = Candidate.objects.filter(owner=self.context["request"].user, cv_sha256=digest)
            if self.instance:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise serializers.ValidationError(
                    {"cv_file": "This resume is already in your candidate pool."}
                )
            attrs["cv_sha256"] = digest
            file.name = build_safe_filename(file.name)
        return attrs


class CandidateListSerializer(CandidateSerializer):
    class Meta(CandidateSerializer.Meta):
        exclude = CandidateSerializer.Meta.exclude + [
            "extracted_text",
            "evidence",
            "extraction_error",
            "analysis_error",
        ]


class CandidateAnalysisSerializer(serializers.Serializer):
    candidate_id = serializers.IntegerField()
    analysis_completed = serializers.BooleanField()
    extracted_data = serializers.DictField(required=False)
    error = serializers.CharField(required=False)


class BulkCandidateUploadSerializer(serializers.Serializer):
    files = serializers.ListField(child=serializers.FileField(), allow_empty=False, max_length=10)

    def validate_files(self, files):
        for file in files:
            validate_cv_file(file)
        return files


class AnalysisSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    candidate_email = serializers.CharField(source="candidate.email", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)

    class Meta:
        model = Analysis
        fields = "__all__"
        read_only_fields = [field.name for field in Analysis._meta.fields]


class ScoreRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreRun
        fields = "__all__"
        read_only_fields = [field.name for field in ScoreRun._meta.fields]


class DecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationDecision
        exclude = ["application"]


class ApplicationSerializer(serializers.ModelSerializer):
    decisions = DecisionSerializer(many=True, read_only=True)
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)

    class Meta:
        model = Application
        fields = "__all__"
        read_only_fields = ["id", "reviewer", "updated_at"]

    def validate(self, attrs):
        owner = self.context["request"].user
        job = attrs.get("job", getattr(self.instance, "job", None))
        candidate = attrs.get("candidate", getattr(self.instance, "candidate", None))
        if not job or not candidate or job.owner_id != owner.pk or candidate.owner_id != owner.pk:
            raise serializers.ValidationError("Job and candidate must belong to you.")
        if self.instance and ("job" in attrs or "candidate" in attrs):
            raise serializers.ValidationError("Application relationships cannot be changed.")
        stage = attrs.get("stage", getattr(self.instance, "stage", "applied"))
        allowed = {
            "applied": {"review", "rejected"},
            "review": {"shortlisted", "rejected"},
            "shortlisted": {"interview", "rejected"},
            "interview": {"hired", "rejected"},
            "hired": set(),
            "rejected": {"review"},
        }
        if not self.instance and stage != "applied":
            raise serializers.ValidationError("New applications start at applied.")
        if self.instance and stage != self.instance.stage:
            if stage not in allowed[self.instance.stage]:
                raise serializers.ValidationError("Invalid stage transition.")
            if not attrs.get("review_note", "").strip():
                raise serializers.ValidationError("A human review note is required.")
            if stage in {"shortlisted", "interview", "hired"}:
                if not candidate.profile_reviewed_at:
                    raise serializers.ValidationError(
                        "Review and correct the extracted profile first."
                    )
                if not Analysis.objects.filter(
                    job=job, candidate=candidate, is_stale=False, insufficient_requirements=False
                ).exists():
                    raise serializers.ValidationError(
                        "Run matching with the latest profile and job first."
                    )
        return attrs


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingTask
        exclude = ["owner", "dedup_key"]


class AuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        exclude = ["owner"]


class JobParseSerializer(serializers.Serializer):
    job_description = serializers.CharField(max_length=16000)


class PairSerializer(serializers.Serializer):
    candidate_id = serializers.IntegerField(min_value=1)
    job_id = serializers.IntegerField(min_value=1)


AIMatchExplainRequestSerializer = PairSerializer
AIInterviewRequestSerializer = PairSerializer
