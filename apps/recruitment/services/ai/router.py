import os
import logging
from typing import Optional
from .base import AIProvider
from .groq_provider import GroqProvider
from .gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class AIRouter:
    def __init__(self):
        self.default = os.getenv("DEFAULT_AI_PROVIDER", "groq").lower()

    def get_provider(self, prefer: Optional[str] = None) -> AIProvider:
        prefer = (prefer or self.default).lower()

        # Prefer Groq for speed; fallback to Gemini
        if prefer == "groq":
            return GroqProvider()
        if prefer == "gemini":
            return GeminiProvider()

        # unknown -> prefer groq
        return GroqProvider()

    def choose_with_fallback(self, prefer: Optional[str] = None) -> AIProvider:
        # Attempt preferred, but design calling code to retry on failure and call Gemini if Groq fails.
        return self.get_provider(prefer=prefer)
