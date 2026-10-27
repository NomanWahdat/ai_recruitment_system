import logging

import requests
from django.conf import settings

from .groq_provider import GroqProvider
from .gemini_provider import GeminiProvider
from .contracts import prompt as build_prompt, validate_output

logger = logging.getLogger(__name__)

# These messages never include response bodies, document text, URLs or credentials.
STATUS_MESSAGES = {
    "missing_key": "No API key is configured.",
    "disabled": "The provider is disabled in the server configuration.",
    "missing_configuration": "The provider model or endpoint is missing.",
    "insecure_endpoint": "The provider endpoint must use HTTPS.",
    "ready": "Configured; use Test AI connection to verify access.",
    "success": "A validated response was received from the provider.",
    "authentication_failed": "The provider rejected the API key. Check or replace it.",
    "access_denied": "The provider denied access. Check account, region and model permissions.",
    "model_or_endpoint_not_found": "The model or endpoint was not found. Check the configured model.",
    "rate_limited": "The provider rate limit or quota was reached. Check quota/billing or try later.",
    "provider_unavailable": "The provider is temporarily unavailable. Try again later.",
    "request_rejected": "The provider rejected the request. Check model and endpoint compatibility.",
    "timeout": "The provider did not respond within the time limit.",
    "connection_failed": "Cannot connect to the provider. Check internet, DNS, proxy and TLS settings.",
    "invalid_response": "The provider response did not match the required JSON format.",
    "provider_error": "The provider request failed. Check server configuration and try again.",
    "scoring_disabled": "AI-assisted scoring is disabled; this score uses the local rubric.",
    "insufficient_requirements": "Add job requirements before requesting an AI-assisted score.",
}


def failure_code(exc):
    if isinstance(exc, requests.Timeout):
        return "timeout"
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else 0
        return {
            401: "authentication_failed",
            403: "access_denied",
            404: "model_or_endpoint_not_found",
            429: "rate_limited",
        }.get(status, "provider_unavailable" if status >= 500 else "request_rejected")
    if isinstance(exc, requests.ConnectionError):
        return "connection_failed"
    if isinstance(exc, (ValueError, KeyError, IndexError, TypeError)):
        return "invalid_response"
    if isinstance(exc, requests.RequestException):
        return "connection_failed"
    return "provider_error"


class AIRouter:
    def __init__(self):
        self.attempts = []

    def get_provider(self, prefer=None):
        return GeminiProvider() if prefer == "gemini" else GroqProvider()

    def choose_with_fallback(self, prefer=None):
        return self.get_provider(prefer)

    def test_connection(self):
        result, source, model = self.generate_json(
            build_prompt(
                "Return skills (string array), role_type, experience_level and summary (strings).",
                {"job_description": "Synthetic test: Python developer using Django."},
            ),
            "parse",
        )
        return {"ok": result is not None, "model": model, **self.metadata(source)}

    def configuration(self):
        providers = []
        for provider in [self.get_provider(), self.get_provider("gemini")]:
            code = provider.configuration_status
            providers.append(
                {
                    "provider": provider.name,
                    "model": provider.model,
                    "enabled": provider.enabled,
                    "status": code,
                    "message": STATUS_MESSAGES[code],
                }
            )
        return {
            "available": any(p["status"] == "ready" for p in providers),
            "verified": False,
            "providers": providers,
            "scoring_enabled": settings.USE_LLM_FOR_SCORING,
            "message": "Configuration only; a successful connection test verifies provider access.",
        }

    def metadata(self, source):
        failures = [a for a in self.attempts if a["status"] != "success"]
        return {
            "response_source": source,
            "fallback_used": source == "local",
            "fallback_reason": "; ".join(
                a["provider"].capitalize() + ": " + a["message"] for a in failures
            )
            if source == "local"
            else "",
            "provider_attempts": self.attempts,
        }

    def generate_json(self, prompt, kind):
        self.attempts = []
        for provider in [self.get_provider(), self.get_provider("gemini")]:
            if not provider.configured:
                code = provider.configuration_status
                self.attempts.append(
                    {
                        "provider": provider.name,
                        "status": code,
                        "message": STATUS_MESSAGES[code],
                    }
                )
                continue
            try:
                data = validate_output(
                    provider.analyze_json(prompt, timeout=settings.AI_REQUEST_TIMEOUT), kind
                )
                self.attempts.append(
                    {
                        "provider": provider.name,
                        "status": "success",
                        "message": STATUS_MESSAGES["success"],
                    }
                )
                return data, provider.name, provider.model
            except Exception as exc:
                code = failure_code(exc)
                self.attempts.append(
                    {
                        "provider": provider.name,
                        "status": code,
                        "message": STATUS_MESSAGES[code],
                    }
                )
                logger.warning("provider_failed provider=%s category=%s", provider.name, code)
        return None, "local", ""
