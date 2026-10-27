import json
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase, APIClient
from apps.recruitment.models import (
    Job,
    Candidate,
    Analysis,
    Application,
    ProcessingTask,
    AuditEvent,
)
from apps.recruitment.services.tasks import enqueue, run_one, claim
from apps.recruitment.services.matching.matcher import match_candidate_to_job
from apps.recruitment.services.matching.scorer import score_components, education_relevant
from apps.recruitment.services.entity_parser import EntityParser
from apps.recruitment.services.experience_extractor import ExperienceExtractor
from apps.recruitment.services.cv_extractor import CVTextExtractor
from apps.recruitment.services.ai.router import AIRouter
from apps.recruitment.services.ai.contracts import validate_score, parse_json
from apps.recruitment.utils.validators import validate_cv_file
from tools.fixtures import docx_bytes, pdf_bytes

TEXT = "Kate Example\nkate@example.com\nSkills\nPython, Django\nExperience\n2010 - 2011\n2020 - 2021\nEducation\nBachelor of Computer Science"


class ExtractionTests(SimpleTestCase):
    def test_blank_english_pipeline_dependency_smoke(self):
        import spacy

        self.assertEqual(spacy.blank("en").lang, "en")

    def test_normal_and_obfuscated_email(self):
        parser = EntityParser()
        for text in [
            "kate@example.com",
            "kate [at] example [dot] com",
            "kate (at) example dot com",
            "kate @ example . com",
        ]:
            self.assertEqual(parser.extract_email(text), "kate@example.com")

    def test_gaps_not_counted(self):
        self.assertEqual(ExperienceExtractor().estimate(TEXT), 2)

    def test_overlaps_counted_once(self):
        self.assertEqual(
            ExperienceExtractor().estimate("Experience\nJan 2020 - Jan 2022\nJan 2021 - Jan 2023"),
            3,
        )

    def test_education_dates_not_experience(self):
        self.assertEqual(ExperienceExtractor().estimate("Education\n2010 - 2020"), 0)

    def test_real_pdf_and_docx_table(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf = Path(folder) / "sample.pdf"
            pdf.write_bytes(pdf_bytes(TEXT))
            doc = Path(folder) / "sample.docx"
            doc.write_bytes(docx_bytes("Kate Example", table_text="Python Django"))
            self.assertIn("kate@example.com", CVTextExtractor().extract(pdf))
            self.assertIn("Python Django", CVTextExtractor().extract(doc))

    def test_spoofed_extension_rejected(self):
        with self.assertRaises(ValidationError):
            validate_cv_file(SimpleUploadedFile("fake.pdf", b"plain text"))

    def test_empty_file_rejected(self):
        with self.assertRaises(ValidationError):
            validate_cv_file(SimpleUploadedFile("empty.pdf", b""))

    def test_unrelated_education_not_full_credit(self):
        self.assertEqual(
            education_relevant("Bachelor of Fine Arts", "Bachelor of Computer Science"), 0
        )

    def test_no_requirements_abstains(self):
        score, components, insufficient = score_components(0, 0, 0, 0, "")
        self.assertEqual(score, 0)
        self.assertTrue(insufficient)

    def test_job_specific_weights(self):
        score, _, _ = score_components(
            2, 1, 2, 2, "", "", {"skills": 1, "experience": 0, "education": 0}
        )
        self.assertEqual(score, 50)

    def test_zero_and_nonfinite_ai_scores(self):
        self.assertEqual(validate_score({"score": 0})["score"], 0)
        for value in [float("nan"), float("inf"), True, -1, 101]:
            with self.assertRaises(ValueError):
                validate_score({"score": value})

    def test_strict_provider_json(self):
        for value in ["", "Return the following prompt", "[]", '{"score": 5} trailing']:
            with self.assertRaises((ValueError, json.JSONDecodeError)):
                parse_json(value)

    def test_empty_primary_falls_back_and_tracks_gemini(self):
        first = Mock(configured=True, name="groq")
        first.analyze_json.return_value = {}
        second = Mock(configured=True)
        second.name = "gemini"
        second.model = "test-model"
        second.analyze_json.return_value = {"score": 0}
        with patch.object(AIRouter, "get_provider", side_effect=[first, second]):
            data, source, model = AIRouter().generate_json("untrusted", "score")
        self.assertEqual(data["score"], 0)
        self.assertEqual(source, "gemini")

    def test_disabled_providers_return_no_simulated_output(self):
        self.assertEqual(AIRouter().generate_json("do something", "score"), (None, "local", ""))

    def test_unicode_dates_and_middle_initial(self):
        self.assertEqual(ExperienceExtractor().estimate("Experience\n2020 \u2013 2022"), 2)
        self.assertEqual(
            EntityParser().extract_name("Riley A. Example\nriley@example.com"), "Riley A. Example"
        )

    def test_dates_not_phone_numbers(self):
        self.assertEqual(EntityParser().extract_phone("Experience\n2020 - 2022"), "")

    def test_provider_http_contracts_and_empty_fallback(self):
        from apps.recruitment.services.ai.groq_provider import GroqProvider
        from apps.recruitment.services.ai.gemini_provider import GeminiProvider

        with override_settings(
            USE_GROQ_AI=True,
            GROQ_API_KEY="synthetic",
            USE_GEMINI_FALLBACK=True,
            GEMINI_API_KEY="synthetic",
            GEMINI_MODEL="test-model",
        ):
            response = Mock()
            response.json.return_value = {"choices": [{"message": {"content": '{"score":0}'}}]}
            with patch("requests.post", return_value=response) as post:
                self.assertEqual(GroqProvider().score_candidate_job({}, {})["score"], 0)
                self.assertNotIn("synthetic", post.call_args.args[0])
            response.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": '{"score":25}'}]}}]
            }
            with patch("requests.post", return_value=response):
                self.assertEqual(GeminiProvider().score_candidate_job({}, {})["score"], 25)


class WorkflowTests(APITestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        override = override_settings(MEDIA_ROOT=self.temp.name)
        override.enable()
        self.addCleanup(override.disable)
        self.nlp = patch(
            "apps.recruitment.services.profile_extractor.ProfileExtractor._load_nlp_model",
            return_value=None,
        )
        self.nlp.start()
        self.addCleanup(self.nlp.stop)
        self.owner = User.objects.create_user("owner", password="ComplexExample!42")
        self.other = User.objects.create_user("other", password="ComplexExample!43")
        self.client.force_authenticate(self.owner)
        self.job = Job.objects.create(
            owner=self.owner,
            title="Backend developer",
            company_name="Synthetic Lab",
            description="Python Django",
            required_skills=["Python", "Django"],
            minimum_experience=2,
        )
        self.candidate = Candidate.objects.create(
            owner=self.owner,
            full_name="Kate Example",
            email="kate@example.com",
            skills=["Python"],
            analysis_completed=True,
            extracted_text=TEXT,
            years_of_experience=2,
        )

    def upload(self, content=None, name="resume.docx"):
        return self.client.post(
            "/api/candidates/",
            {
                "full_name": "Kate Example",
                "email": "kate@example.com",
                "cv_file": SimpleUploadedFile(
                    name, content if content is not None else docx_bytes(TEXT)
                ),
            },
            format="multipart",
        )

    def test_anonymous_sensitive_routes_denied(self):
        self.client.force_authenticate(None)
        for url in [
            "/api/jobs/",
            "/api/candidates/",
            "/api/analyses/",
            "/api/tasks/",
            "/api/applications/",
            "/api/events/",
            "/api/dashboard/",
        ]:
            self.assertEqual(self.client.get(url).status_code, 401, url)
        for url in [
            "/api/match/",
            "/api/automation/reprocess/",
            "/api/automation/matching/",
            "/api/ai/parse-job/",
        ]:
            self.assertEqual(self.client.post(url, {}, format="json").status_code, 401, url)

    def test_two_recruiter_isolation(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/candidates/").data["count"], 0)
        for url in [
            f"/api/candidates/{self.candidate.pk}/",
            f"/api/candidates/{self.candidate.pk}/cv/",
            f"/api/jobs/{self.job.pk}/",
            f"/api/jobs/{self.job.pk}/rankings/",
        ]:
            self.assertEqual(self.client.get(url).status_code, 404)
        for url in [
            "/api/match/",
            "/api/ai/match-explanation/",
            "/api/ai/interview-questions/",
            "/api/applications/",
        ]:
            response = self.client.post(
                url,
                {
                    "candidate_id": self.candidate.pk,
                    "job_id": self.job.pk,
                    "candidate": self.candidate.pk,
                    "job": self.job.pk,
                },
                format="json",
            )
            self.assertIn(response.status_code, [400, 404])

    def test_client_cannot_set_owner(self):
        response = self.client.post(
            "/api/jobs/",
            {"title": "Test", "company_name": "Lab", "description": "Test", "owner": self.other.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Job.objects.get(pk=response.data["id"]).owner, self.owner)

    def test_upload_queues_once_and_worker_processes(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201)
        candidate = Candidate.objects.get(pk=response.data["id"])
        self.assertEqual(candidate.processing_status, "pending")
        self.assertEqual(ProcessingTask.objects.filter(candidate=candidate).count(), 1)
        self.assertTrue(run_one())
        candidate.refresh_from_db()
        self.assertEqual(candidate.processing_status, "completed")
        self.assertEqual(candidate.email, "kate@example.com")
        self.assertEqual(candidate.years_of_experience, 2)
        self.assertEqual(Analysis.objects.filter(candidate=candidate, job=self.job).count(), 1)
        self.assertFalse(run_one())

    def test_duplicate_resume_detected(self):
        content = docx_bytes(TEXT)
        self.assertEqual(self.upload(content).status_code, 201)
        self.assertEqual(self.upload(content).status_code, 400)

    def test_same_resume_allowed_for_another_owner(self):
        content = docx_bytes(TEXT)
        self.upload(content)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.upload(content).status_code, 201)

    def test_private_download_and_no_public_media(self):
        response = self.upload()
        candidate = Candidate.objects.get(pk=response.data["id"])
        download = self.client.get(f"/api/candidates/{candidate.pk}/cv/")
        self.assertEqual(download.status_code, 200)
        self.assertTrue(b"".join(download.streaming_content))
        self.assertEqual(self.client.get("/media/" + candidate.cv_file.name).status_code, 404)
        self.assertTrue(AuditEvent.objects.filter(action="candidate.cv_downloaded").exists())

    def test_delete_removes_file_after_commit(self):
        response = self.upload()
        candidate = Candidate.objects.get(pk=response.data["id"])
        path = Path(candidate.cv_file.path)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.delete(f"/api/candidates/{candidate.pk}/")
        self.assertFalse(path.exists())

    def test_failed_extraction_not_counted_success(self):
        response = self.upload(pdf_bytes(""), "blank.pdf")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(run_one())
        candidate = Candidate.objects.get(pk=response.data["id"])
        self.assertEqual(candidate.processing_status, "failed")
        self.assertFalse(candidate.analysis_completed)
        self.assertEqual(ProcessingTask.objects.get(candidate=candidate).status, "failed")
        self.assertFalse(Analysis.objects.filter(candidate=candidate).exists())

    def test_retry_is_deduplicated(self):
        first = enqueue(self.owner, "match_candidate", candidate=self.candidate)
        self.assertEqual(
            first.pk, enqueue(self.owner, "match_candidate", candidate=self.candidate).pk
        )

    def test_expired_lease_recovered(self):
        task = enqueue(self.owner, "match_candidate", candidate=self.candidate)
        task.status = "running"
        task.attempts = 1
        task.started_at = timezone.now() - timedelta(minutes=11)
        task.save()
        claimed = claim()
        self.assertEqual(claimed.pk, task.pk)
        self.assertEqual(claimed.attempts, 2)

    def test_exhausted_lease_fails(self):
        task = enqueue(self.owner, "match_candidate", candidate=self.candidate)
        task.status = "running"
        task.attempts = 3
        task.started_at = timezone.now() - timedelta(minutes=11)
        task.save()
        self.assertIsNone(claim())
        task.refresh_from_db()
        self.assertEqual(task.status, "failed")

    def test_profile_update_stales_and_refreshes(self):
        match_candidate_to_job(self.candidate, self.job)
        response = self.client.patch(
            f"/api/candidates/{self.candidate.pk}/", {"skills": ["Python", "Django"]}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Analysis.objects.get(candidate=self.candidate).is_stale)
        run_one()
        self.assertFalse(Analysis.objects.get(candidate=self.candidate).is_stale)
        self.assertEqual(
            Analysis.objects.get(candidate=self.candidate).matched_skills, ["Python", "Django"]
        )

    def test_job_update_stales_and_refreshes(self):
        match_candidate_to_job(self.candidate, self.job)
        self.client.patch(
            f"/api/jobs/{self.job.pk}/", {"required_skills": ["React"]}, format="json"
        )
        self.assertTrue(Analysis.objects.get(candidate=self.candidate).is_stale)
        run_one()
        self.assertEqual(Analysis.objects.get(candidate=self.candidate).missing_skills, ["React"])

    def test_superseded_task_cannot_overwrite_corrections(self):
        enqueue(self.owner, "extract", candidate=self.candidate)
        self.client.patch(
            f"/api/candidates/{self.candidate.pk}/", {"full_name": "Reviewed Name"}, format="json"
        )
        run_one()
        self.candidate.refresh_from_db()
        self.assertEqual(self.candidate.full_name, "Reviewed Name")

    def test_matching_idempotent_and_rank_get_is_readonly(self):
        match_candidate_to_job(self.candidate, self.job)
        match_candidate_to_job(self.candidate, self.job)
        self.assertEqual(Analysis.objects.count(), 1)
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(f"/api/jobs/{self.job.pk}/rankings/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            any(
                q["sql"].lstrip().upper().startswith(("UPDATE", "INSERT", "DELETE"))
                for q in captured
            )
        )

    def test_malformed_ids_are_validation_errors(self):
        self.assertEqual(
            self.client.post(
                "/api/match/", {"candidate_id": "bad", "job_id": self.job.pk}, format="json"
            ).status_code,
            400,
        )

    def test_cross_owner_matching_rejected_in_service(self):
        self.job.owner = self.other
        self.job.save()
        with self.assertRaises(ValueError):
            match_candidate_to_job(self.candidate, self.job)

    def test_no_fake_ai_source(self):
        match_candidate_to_job(self.candidate, self.job)
        response = self.client.post(
            "/api/ai/match-explanation/",
            {"candidate_id": self.candidate.pk, "job_id": self.job.pk},
            format="json",
        )
        self.assertEqual(response.data["response_source"], "local")
        self.assertNotIn("Return ONLY", response.data["summary"])

    def test_application_requires_human_review(self):
        response = self.client.post(
            "/api/applications/",
            {"candidate": self.candidate.pk, "job": self.job.pk},
            format="json",
        )
        app_id = response.data["id"]
        self.assertEqual(
            self.client.patch(
                f"/api/applications/{app_id}/",
                {"stage": "hired", "review_note": "Skip review"},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/applications/{app_id}/",
                {"stage": "review", "review_note": "Check evidence"},
                format="json",
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/applications/{app_id}/",
                {"stage": "shortlisted", "review_note": "Looks good"},
                format="json",
            ).status_code,
            400,
        )
        self.client.patch(
            f"/api/candidates/{self.candidate.pk}/", {"skills": ["Python", "Django"]}, format="json"
        )
        run_one()
        self.assertEqual(
            self.client.patch(
                f"/api/applications/{app_id}/",
                {"stage": "shortlisted", "review_note": "Verified skill evidence"},
                format="json",
            ).status_code,
            200,
        )
        app = Application.objects.get(pk=app_id)
        self.assertEqual(app.reviewer, self.owner)
        self.assertTrue(
            AuditEvent.objects.filter(
                action="application.reviewed", details__to_stage="shortlisted"
            ).exists()
        )

    def test_analysis_results_are_not_client_writable(self):
        self.assertEqual(self.client.post("/api/analyses/", {}, format="json").status_code, 405)

    def test_list_does_not_return_raw_resume(self):
        self.assertNotIn("extracted_text", self.client.get("/api/candidates/").data["results"][0])

    def test_pagination_and_search(self):
        self.assertEqual(self.client.get("/api/candidates/?search=missing").data["count"], 0)
        self.assertEqual(self.client.get("/api/candidates/?min_experience=bad").status_code, 400)

    def test_candidate_count_queries_do_not_scale_with_list(self):
        for i in range(5):
            Candidate.objects.create(
                owner=self.owner, full_name=f"Candidate {i}", email=f"c{i}@example.com"
            )
        with CaptureQueriesContext(connection) as captured:
            self.client.get("/api/candidates/")
        self.assertLessEqual(len(captured), 3)

    def test_weak_password_rejected(self):
        self.client.force_authenticate(None)
        response = self.client.post(
            "/api/auth/register/",
            {"username": "new", "email": "new@example.com", "password": "123456"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_expired_token_rejected(self):
        token = Token.objects.create(user=self.owner)
        Token.objects.filter(pk=token.pk).update(created=timezone.now() - timedelta(days=2))
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_session_login_requires_csrf_and_uses_httponly_cookie(self):
        client = APIClient(enforce_csrf_checks=True)
        data = {"username": "owner", "password": "ComplexExample!42"}
        self.assertEqual(client.post("/api/auth/login/", data, format="json").status_code, 403)
        csrf = client.get("/api/auth/csrf/").data["csrfToken"]
        response = client.post("/api/auth/login/", data, format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.cookies["sessionid"]["httponly"])
        self.assertNotIn("token", response.data)
        self.assertEqual(client.get("/api/auth/me/").status_code, 200)

    def test_replacing_document_deletes_old_file_and_clears_review(self):
        response = self.upload()
        candidate = Candidate.objects.get(pk=response.data["id"])
        run_one()
        candidate.refresh_from_db()
        candidate.profile_reviewed_at = timezone.now()
        candidate.save()
        old = Path(candidate.cv_file.path)
        replacement = SimpleUploadedFile(
            "updated.docx", docx_bytes(TEXT + "\nAdditional source evidence")
        )
        with self.captureOnCommitCallbacks(execute=True):
            result = self.client.patch(
                f"/api/candidates/{candidate.pk}/", {"cv_file": replacement}, format="multipart"
            )
        self.assertEqual(result.status_code, 200)
        candidate.refresh_from_db()
        self.assertIsNone(candidate.profile_reviewed_at)
        self.assertFalse(old.exists())
        self.assertTrue(Path(candidate.cv_file.path).exists())

    def test_bulk_upload_reports_duplicates_without_false_success(self):
        content = docx_bytes(TEXT)
        self.upload(content)
        result = self.client.post(
            "/api/candidates/bulk-upload/",
            {
                "files": [
                    SimpleUploadedFile("repeat.docx", content),
                    SimpleUploadedFile("other.docx", docx_bytes(TEXT + "\nAnother version")),
                ]
            },
            format="multipart",
        )
        self.assertEqual(result.status_code, 207)
        self.assertEqual(result.data["queued_count"], 1)
        self.assertEqual(result.data["failed_count"], 1)

    def test_job_scoped_match_does_not_enqueue_other_jobs(self):
        other = Job.objects.create(
            owner=self.owner, title="Other job", company_name="Lab", description="Other"
        )
        response = self.client.post(f"/api/jobs/{self.job.pk}/match/")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(ProcessingTask.objects.filter(job=other).count(), 0)

    def test_failed_task_retry_and_visibility(self):
        response = self.upload(pdf_bytes(""), "blank.pdf")
        run_one()
        task = ProcessingTask.objects.get(candidate_id=response.data["id"])
        retry = self.client.post(f"/api/tasks/{task.pk}/retry/")
        self.assertEqual(retry.status_code, 202)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/tasks/").data["count"], 0)
        self.assertEqual(self.client.post(f"/api/tasks/{task.pk}/retry/").status_code, 404)

    def test_retention_preview_then_delete(self):
        from django.core.management import call_command
        from io import StringIO

        response = self.upload()
        candidate = Candidate.objects.get(pk=response.data["id"])
        candidate.retention_until = timezone.now() - timedelta(days=1)
        candidate.save()
        call_command("purge_expired", stdout=StringIO())
        self.assertTrue(Candidate.objects.filter(pk=candidate.pk).exists())
        with self.captureOnCommitCallbacks(execute=True):
            call_command("purge_expired", apply=True, stdout=StringIO())
        self.assertFalse(Candidate.objects.filter(pk=candidate.pk).exists())

    def test_storage_reconciliation_preserves_referenced_files(self):
        import os
        from io import StringIO
        from django.core.management import call_command

        response = self.upload()
        candidate = Candidate.objects.get(pk=response.data["id"])
        orphan = Path(self.temp.name) / "cvs" / "orphan.pdf"
        orphan.write_bytes(pdf_bytes(""))
        old = (timezone.now() - timedelta(days=2)).timestamp()
        os.utime(orphan, (old, old))
        call_command("reconcile_storage", stdout=StringIO())
        self.assertTrue(orphan.exists())
        call_command("reconcile_storage", apply=True, stdout=StringIO())
        self.assertFalse(orphan.exists())
        self.assertTrue(Path(candidate.cv_file.path).exists())

    def test_legacy_assignment_is_explicit(self):
        from django.core.management import call_command
        from io import StringIO

        legacy = Candidate.objects.create(full_name="Legacy Example", email="legacy@example.com")
        call_command("assign_legacy", owner=self.owner.username, stdout=StringIO())
        legacy.refresh_from_db()
        self.assertIsNone(legacy.owner_id)
        call_command("assign_legacy", owner=self.owner.username, apply=True, stdout=StringIO())
        legacy.refresh_from_db()
        self.assertEqual(legacy.owner, self.owner)
        self.assertIsNotNone(legacy.retention_until)

    def test_local_ai_tools_are_functional(self):
        parsed = self.client.post(
            "/api/ai/parse-job/",
            {"job_description": "React TypeScript frontend developer"},
            format="json",
        )
        self.assertEqual(parsed.status_code, 200)
        self.assertEqual(parsed.data["response_source"], "local")
        match_candidate_to_job(self.candidate, self.job)
        questions = self.client.post(
            "/api/ai/interview-questions/",
            {"candidate_id": self.candidate.pk, "job_id": self.job.pk},
            format="json",
        )
        self.assertEqual(questions.status_code, 200)
        self.assertTrue(questions.data["technical_questions"])

    def test_dashboard_aggregates_and_health(self):
        match_candidate_to_job(self.candidate, self.job)
        data = self.client.get("/api/dashboard/").data
        self.assertEqual(data["scores"]["total"], 1)
        self.assertEqual(data["candidates"], 1)
        self.assertEqual(self.client.get("/api/health/").status_code, 200)

    def test_hybrid_never_sends_identity_or_overrides_skill_evidence(self):
        with override_settings(USE_LLM_FOR_SCORING=True):
            with patch.object(
                AIRouter,
                "generate_json",
                return_value=(
                    {
                        "score": 0,
                        "matched_skills": ["Django"],
                        "missing_skills": ["Python"],
                        "explanation": "Advisory",
                    },
                    "gemini",
                    "test-model",
                ),
            ) as provider:
                result = match_candidate_to_job(self.candidate, self.job)
        self.assertEqual(result["matched_skills"], ["Python"])
        self.assertEqual(result["missing_skills"], ["Django"])
        self.assertNotIn("kate@example.com", provider.call_args.args[0])
        self.assertNotIn("Kate Example", provider.call_args.args[0])
        self.assertEqual(Analysis.objects.get(candidate=self.candidate).provider, "gemini")

    def test_persistence_errors_propagate(self):
        from django.db import DatabaseError

        with patch.object(
            Analysis.objects, "update_or_create", side_effect=DatabaseError("simulated")
        ):
            with self.assertRaises(DatabaseError):
                match_candidate_to_job(self.candidate, self.job)

    def test_score_database_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Analysis.objects.create(job=self.job, candidate=self.candidate, match_score=101)

    def test_missing_job_requirements_cannot_enable_shortlisting(self):
        self.job.required_skills = []
        self.job.minimum_experience = 0
        self.job.education_requirement = ""
        self.job.save()
        result = match_candidate_to_job(self.candidate, self.job)
        self.assertTrue(result["insufficient_requirements"])
        self.assertEqual(
            self.client.get(f"/api/jobs/{self.job.pk}/rankings/").data["top_candidates"], []
        )


from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.test import TransactionTestCase
from django.db import connections


@skipUnless(connection.vendor == "postgresql", "Concurrent queue semantics require PostgreSQL.")
class PostgreSQLQueueTests(TransactionTestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="concurrent-owner", password="ComplexExample!42"
        )
        self.candidate = Candidate.objects.create(
            owner=self.owner, full_name="Concurrent Example", email="concurrent@example.com"
        )

    def test_two_workers_claim_one_task_once(self):
        task = enqueue(self.owner, "match_candidate", candidate=self.candidate)
        barrier = Barrier(2)

        def claimant(_):
            try:
                barrier.wait(timeout=10)
                claimed = claim()
                return claimed.pk if claimed else None
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(claimant, [1, 2]))
        self.assertEqual(results.count(task.pk), 1)
        self.assertEqual(results.count(None), 1)

    def test_concurrent_enqueue_is_deduplicated(self):
        barrier = Barrier(2)

        def schedule(_):
            try:
                barrier.wait(timeout=10)
                return enqueue(self.owner, "match_candidate", candidate=self.candidate).pk
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(schedule, [1, 2]))
        self.assertEqual(results[0], results[1])
        self.assertEqual(ProcessingTask.objects.count(), 1)


class WorkerCommandTests(TransactionTestCase):
    def test_worker_command_drains_queue_and_clears_heartbeat(self):
        from django.core.management import call_command
        from io import StringIO
        from apps.recruitment.models import WorkerHeartbeat

        owner = User.objects.create_user(username="worker-owner", password="ComplexExample!42")
        candidate = Candidate.objects.create(
            owner=owner,
            full_name="Worker Example",
            email="worker@example.com",
            analysis_completed=True,
        )
        task = enqueue(owner, "match_candidate", candidate=candidate)
        call_command("process_tasks", once=True, stdout=StringIO())
        task.refresh_from_db()
        self.assertEqual(task.status, "completed")
        self.assertFalse(WorkerHeartbeat.objects.exists())
