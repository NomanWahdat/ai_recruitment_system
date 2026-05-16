from rest_framework import serializers

from .models import Analysis, Candidate, Job
from .utils.validators import validate_cv_file


class HealthCheckSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()


class JobSerializer(serializers.ModelSerializer):
    analyses_count = serializers.IntegerField(
        source="analyses.count",
        read_only=True,
    )

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "company_name",
            "location",
            "employment_type",
            "description",
            "required_skills",
            "minimum_experience",
            "education_requirement",
            "salary_range",
            "created_at",
            "updated_at",
            "analyses_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "analyses_count"]

    def validate_required_skills(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Required skills must be a list.")
        return value


class CandidateSerializer(serializers.ModelSerializer):
    cv_filename = serializers.CharField(read_only=True)
    analyses_count = serializers.IntegerField(
        source="analyses.count",
        read_only=True,
    )

    class Meta:
        model = Candidate
        fields = [
            "id",
            "full_name",
            "email",
            "phone_number",
            "cv_file",
            "cv_filename",
            "extracted_text",
            "processing_status",
            "extraction_success",
            "extraction_error",
            "extracted_at",
            "analysis_completed",
            "analysis_error",
            "analyzed_at",
            "years_of_experience",
            "skills",
            "education",
            "linkedin_url",
            "github_url",
            "portfolio_url",
            "uploaded_at",
            "updated_at",
            "analyses_count",
        ]
        read_only_fields = [
            "id",
            "cv_filename",
            "processing_status",
            "extraction_success",
            "extraction_error",
            "extracted_at",
            "analysis_completed",
            "analysis_error",
            "analyzed_at",
            "uploaded_at",
            "updated_at",
            "analyses_count",
        ]

    def validate_cv_file(self, value):
        validate_cv_file(value)
        return value

    def validate_skills(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Skills must be a list.")
        return value


class CandidateAnalysisSerializer(serializers.Serializer):
    candidate_id = serializers.IntegerField()
    analysis_completed = serializers.BooleanField()
    extracted_data = serializers.DictField(required=False)
    error = serializers.CharField(required=False)


class BulkCandidateUploadSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False,
        write_only=True,
    )

    def validate_files(self, value):
        for file in value:
            validate_cv_file(file)
        return value


class AnalysisSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)
    candidate_name = serializers.CharField(
        source="candidate.full_name",
        read_only=True,
    )
    candidate_email = serializers.EmailField(source="candidate.email", read_only=True)

    class Meta:
        model = Analysis
        fields = [
            "id",
            "job",
            "job_title",
            "candidate",
            "candidate_name",
            "candidate_email",
            "match_score",
            "matched_skills",
            "missing_skills",
            "strengths",
            "weaknesses",
            "ai_summary",
            "recommendation_status",
            "generated_interview_questions",
            "ranking_position",
            "analysis_created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "job_title",
            "candidate_name",
            "candidate_email",
            "analysis_created_at",
            "updated_at",
        ]

    def validate_matched_skills(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Matched skills must be a list.")
        return value

    def validate_missing_skills(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Missing skills must be a list.")
        return value

    def validate_generated_interview_questions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError(
                "Generated interview questions must be a list."
            )
        return value

    def validate(self, attrs):
        job = attrs.get("job", getattr(self.instance, "job", None))
        candidate = attrs.get("candidate", getattr(self.instance, "candidate", None))

        if job and candidate:
            queryset = Analysis.objects.filter(job=job, candidate=candidate)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError(
                    "Analysis already exists for this job and candidate."
                )

        return attrs


# AI layer serializers
class JobParseSerializer(serializers.Serializer):
    job_description = serializers.CharField()


class JobParseResponseSerializer(serializers.Serializer):
    skills = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    role_type = serializers.CharField()
    experience_level = serializers.CharField()
    summary = serializers.CharField()


class AIMatchExplainRequestSerializer(serializers.Serializer):
    candidate_id = serializers.IntegerField()
    job_id = serializers.IntegerField()


class AIMatchExplainResponseSerializer(serializers.Serializer):
    summary = serializers.CharField()
    strengths = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    weaknesses = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    recommendation = serializers.CharField(allow_blank=True)


class AIInterviewRequestSerializer(serializers.Serializer):
    candidate_id = serializers.IntegerField()
    job_id = serializers.IntegerField()


class AIInterviewResponseSerializer(serializers.Serializer):
    technical_questions = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    behavioral_questions = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    skill_based_questions = serializers.ListField(child=serializers.CharField(), allow_empty=True)
