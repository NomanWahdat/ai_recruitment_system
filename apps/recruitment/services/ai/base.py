import abc
from typing import Any, Dict


class AIProvider(abc.ABC):
    """Abstract AI provider interface."""

    @property
    def configuration_status(self):
        if not self.api_key:
            return "missing_key"
        if not self.enabled:
            return "disabled"
        if not self.model or not self.api_url:
            return "missing_configuration"
        return "ready"

    @property
    def configured(self):
        return self.configuration_status == "ready"

    @abc.abstractmethod
    def generate_text(self, prompt: str, timeout: int = 10) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def analyze_json(self, prompt: str, timeout: int = 10) -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def score_candidate_job(
        self, job_payload: Dict[str, Any], candidate_payload: Dict[str, Any], timeout: int = 10
    ) -> Dict[str, Any]:
        """Return a dict with keys: score (0-100), matched_skills, missing_skills, explanation
        Providers raise on invalid output/HTTP errors. AIRouter owns fallback and diagnostics.
        """
        raise NotImplementedError
