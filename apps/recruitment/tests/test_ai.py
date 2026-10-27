import io
import json
from unittest.mock import Mock, patch

import requests
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APITestCase

from apps.recruitment.services.ai.groq_provider import GroqProvider
from apps.recruitment.services.ai.gemini_provider import GeminiProvider
from apps.recruitment.services.ai.router import AIRouter


PARSE = {
    "skills": ["Python", "Django"],
    "role_type": "Backend developer",
    "experience_level": "unspecified",
    "summary": "Synthetic developer role.",
}


@override_settings(
    GROQ_API_KEY="synthetic-secret",
    USE_GROQ_AI=True,
    USE_GEMINI_FALLBACK=False,
    GEMINI_API_KEY="",
)
class ProviderDiagnosticsTests(SimpleTestCase):
    def test_configuration_never_calls_provider_or_exposes_key(self):
        with patch("requests.post") as post:
            status = AIRouter().configuration()
        post.assert_not_called()
        self.assertTrue(status["available"])
        self.assertFalse(status["verified"])
        self.assertNotIn("synthetic-secret", json.dumps(status))

    def test_missing_key_disabled_blank_model_and_insecure_endpoint(self):
        for settings, expected in [
            ({"GROQ_API_KEY": "  "}, "missing_key"),
            ({"USE_GROQ_AI": False}, "disabled"),
            ({"GROQ_MODEL": ""}, "missing_configuration"),
            ({"GROQ_API_URL": "http://example.com"}, "insecure_endpoint"),
        ]:
            with self.subTest(expected=expected), override_settings(**settings):
                with patch("requests.post") as post:
                    router = AIRouter()
                    self.assertEqual(router.generate_json("JSON", "parse")[1], "local")
                    self.assertEqual(router.attempts[0]["status"], expected)
                post.assert_not_called()

    def test_http_failures_are_actionable_and_redacted(self):
        for status, expected in [
            (401, "authentication_failed"),
            (403, "access_denied"),
            (404, "model_or_endpoint_not_found"),
            (429, "rate_limited"),
            (503, "provider_unavailable"),
            (400, "request_rejected"),
        ]:
            with self.subTest(status=status):
                response = requests.Response()
                response.status_code = status
                error = requests.HTTPError("secret-and-candidate-text", response=response)
                router = AIRouter()
                with patch("requests.post", side_effect=error):
                    self.assertEqual(router.generate_json("JSON", "parse")[1], "local")
                metadata = router.metadata("local")
                self.assertEqual(router.attempts[0]["status"], expected)
                self.assertTrue(metadata["fallback_used"])
                self.assertNotIn("secret-and-candidate-text", json.dumps(metadata))
                self.assertNotIn("synthetic-secret", json.dumps(metadata))

    def test_transport_and_invalid_output_failures(self):
        for error, expected in [
            (requests.Timeout("sensitive"), "timeout"),
            (requests.ConnectionError("sensitive"), "connection_failed"),
            (ValueError("sensitive"), "invalid_response"),
        ]:
            with (
                self.subTest(expected=expected),
                patch.object(GroqProvider, "analyze_json", side_effect=error),
            ):
                router = AIRouter()
                router.generate_json("JSON", "parse")
                self.assertEqual(router.attempts[0]["status"], expected)

    @override_settings(USE_GEMINI_FALLBACK=True, GEMINI_API_KEY="synthetic-gemini")
    def test_primary_failure_falls_back_to_real_secondary_result(self):
        with (
            patch.object(GroqProvider, "analyze_json", side_effect=requests.Timeout),
            patch.object(GeminiProvider, "analyze_json", return_value=PARSE),
        ):
            router = AIRouter()
            result, source, _ = router.generate_json("JSON", "parse")
        self.assertEqual(result, PARSE)
        self.assertEqual(source, "gemini")
        self.assertEqual([a["status"] for a in router.attempts], ["timeout", "success"])
        self.assertFalse(router.metadata(source)["fallback_used"])

    def test_groq_json_mode_and_bounded_timeout(self):
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": json.dumps(PARSE)}}]}
        with (
            override_settings(AI_REQUEST_TIMEOUT=30),
            patch("requests.post", return_value=response) as post,
        ):
            result = AIRouter().test_connection()
        self.assertTrue(result["ok"])
        self.assertEqual(result["response_source"], "groq")
        self.assertEqual(post.call_args.kwargs["json"]["response_format"], {"type": "json_object"})
        self.assertEqual(post.call_args.kwargs["timeout"], 30)
        self.assertFalse(post.call_args.kwargs["allow_redirects"])
        self.assertIn("Synthetic test", post.call_args.kwargs["json"]["messages"][1]["content"])

    def test_configuration_command_does_not_make_live_requests(self):
        output = io.StringIO()
        with patch("requests.post") as post:
            call_command("check_ai", stdout=output)
        post.assert_not_called()
        self.assertNotIn("synthetic-secret", output.getvalue())


class AIDiagnosticsAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("ai-recruiter")

    def test_diagnostics_require_authentication(self):
        self.assertEqual(self.client.get("/api/ai/status/").status_code, 401)
        self.assertEqual(self.client.post("/api/ai/check/", {}).status_code, 401)

    def test_missing_configuration_is_visible_on_results(self):
        self.client.force_authenticate(self.user)
        with override_settings(GROQ_API_KEY="", GEMINI_API_KEY=""), patch("requests.post") as post:
            status = self.client.get("/api/ai/status/")
            result = self.client.post(
                "/api/ai/parse-job/", {"job_description": "Python developer using Django"}
            )
            check = self.client.post("/api/ai/check/", {})
        post.assert_not_called()
        self.assertFalse(status.data["available"])
        self.assertEqual(result.data["response_source"], "local")
        self.assertIn("No API key", result.data["fallback_reason"])
        self.assertFalse(check.data["ok"])

    def test_verified_provider_response_reaches_api(self):
        self.client.force_authenticate(self.user)
        with (
            override_settings(USE_GROQ_AI=True, GROQ_API_KEY="synthetic"),
            patch.object(GroqProvider, "analyze_json", return_value=PARSE),
        ):
            response = self.client.post(
                "/api/ai/parse-job/", {"job_description": "Python developer using Django"}
            )
            check = self.client.post("/api/ai/check/", {})
        self.assertEqual(response.data["response_source"], "groq")
        self.assertFalse(response.data["fallback_used"])
        self.assertEqual(response.data["skills"], PARSE["skills"])
        self.assertTrue(check.data["ok"])
