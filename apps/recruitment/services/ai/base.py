import abc
from typing import Any, Dict


class AIProvider(abc.ABC):
    """Abstract AI provider interface."""

    @abc.abstractmethod
    def generate_text(self, prompt: str, timeout: int = 10) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def analyze_json(self, prompt: str, timeout: int = 10) -> Dict[str, Any]:
        raise NotImplementedError
    
    @abc.abstractmethod
    def score_candidate_job(self, job_payload: Dict[str, Any], candidate_payload: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
        """Return a dict with keys: score (0-100), matched_skills, missing_skills, explanation
        Providers should validate and normalize their responses. Implementations MUST NOT raise on provider errors;
        they should return an empty dict to indicate no LLM result available.
        """
        raise NotImplementedError
