from django.contrib import admin
from django.utils.html import format_html

from .models import Analysis, Candidate, Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "company_name",
        "location",
        "employment_type",
        "minimum_experience",
        "created_at",
    ]
    list_filter = ["employment_type", "created_at", "updated_at"]
    search_fields = ["title", "company_name", "location", "description"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at", "formatted_required_skills"]

    fieldsets = [
        (
            "Job Details",
            {
                "fields": [
                    "title",
                    "company_name",
                    "location",
                    "employment_type",
                    "description",
                ]
            },
        ),
        (
            "Requirements",
            {
                "fields": [
                    "required_skills",
                    "formatted_required_skills",
                    "minimum_experience",
                    "education_requirement",
                ]
            },
        ),
        ("Compensation", {"fields": ["salary_range"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]

    def formatted_required_skills(self, obj):
        return format_html("<pre>{}</pre>", obj.required_skills)

    formatted_required_skills.short_description = "Required skills preview"


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    
    class AnalyzedFilter(admin.SimpleListFilter):
        title = "Analyzed"
        parameter_name = "analyzed"

        def lookups(self, request, model_admin):
            return (("yes", "Analyzed"), ("no", "Not analyzed"))

        def queryset(self, request, queryset):
            if self.value() == "yes":
                return queryset.filter(analysis_completed=True)
            if self.value() == "no":
                return queryset.filter(analysis_completed=False)
            return queryset

    list_display = [
        "full_name",
        "email",
        "phone_number",
        "years_of_experience",
        "processing_status",
        "extraction_success",
        "analysis_completed",
        "cv_filename",
        "extracted_at",
        "analyzed_at",
        "uploaded_at",
    ]
    list_filter = [
        "processing_status",
        "extraction_success",
        AnalyzedFilter,
        "extracted_at",
        "analyzed_at",
        "uploaded_at",
        "updated_at",
        "years_of_experience",
    ]
    search_fields = ["full_name", "email", "phone_number", "skills", "education"]
    ordering = ["-uploaded_at"]
    readonly_fields = [
        "uploaded_at",
        "updated_at",
        "cv_filename",
        "extracted_at",
        "analyzed_at",
        "formatted_skills",
    ]

    fieldsets = [
        (
            "Candidate Details",
            {
                "fields": [
                    "full_name",
                    "email",
                    "phone_number",
                    "years_of_experience",
                    "education",
                ]
            },
        ),
        (
            "CV Processing",
            {
                "fields": [
                    "cv_file",
                    "cv_filename",
                    "processing_status",
                    "extraction_success",
                    "extraction_error",
                    "extracted_at",
                    "extracted_text",
                ]
            },
        ),
        ("Skills", {"fields": ["skills", "formatted_skills"]}),
        (
            "Profile Analysis",
            {
                "fields": [
                    "analysis_completed",
                    "analysis_error",
                    "analyzed_at",
                ]
            },
        ),
        (
            "Links",
            {"fields": ["linkedin_url", "github_url", "portfolio_url"]},
        ),
        ("Timestamps", {"fields": ["uploaded_at", "updated_at"]}),
    ]

    def formatted_skills(self, obj):
        return format_html("<pre>{}</pre>", obj.skills)

    formatted_skills.short_description = "Skills preview"


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = [
        "candidate",
        "job",
        "match_score",
        "ranking_position",
        "recommendation_status",
        "analysis_created_at",
    ]
    list_filter = [
        "recommendation_status",
        "job",
        "candidate",
        "analysis_created_at",
        "updated_at",
    ]
    search_fields = [
        "job__title",
        "job__company_name",
        "candidate__full_name",
        "candidate__email",
        "ai_summary",
    ]
    ordering = ["-match_score", "-analysis_created_at"]
    readonly_fields = ["analysis_created_at", "updated_at", "formatted_ai_data"]
    autocomplete_fields = ["job", "candidate"]

    fieldsets = [
        ("Relationship", {"fields": ["job", "candidate"]}),
        (
            "Score and Recommendation",
            {"fields": ["match_score", "recommendation_status"]},
        ),
        (
            "AI Analysis",
            {
                "fields": [
                    "matched_skills",
                    "missing_skills",
                    "strengths",
                    "weaknesses",
                    "ai_summary",
                    "generated_interview_questions",
                    "formatted_ai_data",
                ]
            },
        ),
        ("Timestamps", {"fields": ["analysis_created_at", "updated_at"]}),
    ]

    def formatted_ai_data(self, obj):
        return format_html(
            "<pre>Matched: {}\nMissing: {}\nQuestions: {}</pre>",
            obj.matched_skills,
            obj.missing_skills,
            obj.generated_interview_questions,
        )

    formatted_ai_data.short_description = "AI data preview"


class MatchLevelFilter(admin.SimpleListFilter):
    title = "Match Level"
    parameter_name = "match_level"

    def lookups(self, request, model_admin):
        return (("high", "High (>80)"), ("medium", "Medium (50-80)"), ("low", "Low (<50)"))

    def queryset(self, request, queryset):
        if self.value() == "high":
            return queryset.filter(match_score__gt=80)
        if self.value() == "medium":
            return queryset.filter(match_score__gte=50, match_score__lte=80)
        if self.value() == "low":
            return queryset.filter(match_score__lt=50)
        return queryset
