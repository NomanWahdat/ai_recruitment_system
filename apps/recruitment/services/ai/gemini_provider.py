import requests
from django.conf import settings
from .base import AIProvider
from .contracts import parse_json, prompt, validate_score


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self):
        self.enabled = settings.USE_GEMINI_FALLBACK
        self.api_key = settings.GEMINI_API_KEY.strip()
        self.model = settings.GEMINI_MODEL.strip()
        self.api_url = (
            settings.GEMINI_API_URL.strip()
            or f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        )

    @property
    def configuration_status(self):
        status = super().configuration_status
        if status == "ready" and not self.api_url.startswith("https://"):
            return "insecure_endpoint"
        return status

    def generate_text(self, prompt, timeout=10):
        if not self.configured:
            raise ValueError("Gemini is not configured")
        response = requests.post(
            self.api_url,
            headers={"x-goog-api-key": self.api_key},
            json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
            },
            timeout=timeout,
            allow_redirects=False,
        )
        response.raise_for_status()
        return "".join(
            p["text"] for p in response.json()["candidates"][0]["content"]["parts"] if "text" in p
        )

    def analyze_json(self, prompt, timeout=10):
        return parse_json(self.generate_text(prompt, timeout))

    def score_candidate_job(self, job_payload, candidate_payload, timeout=10):
        return validate_score(
            self.analyze_json(
                prompt(
                    "Return score (0-100), matched_skills, missing_skills and explanation.",
                    {"job": job_payload, "candidate": candidate_payload},
                ),
                timeout,
            )
        )
