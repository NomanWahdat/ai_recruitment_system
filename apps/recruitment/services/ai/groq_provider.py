import logging
import os
import json
from typing import Any, Dict

import requests
from decouple import config

from .base import AIProvider

logger = logging.getLogger(__name__)


class GroqProvider(AIProvider):
    """Groq provider implementation.

    If `GROQ_API_URL` is set the provider will POST `{"prompt": <prompt>}` to
    that URL and attempt to extract text/JSON from the response. If the URL is
    not set the provider falls back to the original lightweight echo parser to
    preserve backwards compatibility.
    """

    def __init__(self):
        self.api_url = os.getenv("GROQ_API_URL") or config("GROQ_API_URL", default="")
        self.api_key = os.getenv("GROQ_API_KEY") or config("GROQ_API_KEY", default="")
        self.model = os.getenv("GROQ_MODEL") or config("GROQ_MODEL", default="llama-3.3-70b-versatile")

    def _chat_completions_url(self) -> str:
        base_url = (self.api_url or "").rstrip("/")
        if not base_url:
            return ""
        # Groq uses /chat/completions endpoint (OpenAI compatible)
        if base_url.endswith("/v1") or base_url.endswith("/v1/"):
            return f"{base_url}/chat/completions"
        return f"{base_url}/chat/completions"

    def _headers(self) -> Dict[str, str]:
        hdrs: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            hdrs["Authorization"] = f"Bearer {self.api_key}"
            hdrs["x-api-key"] = self.api_key
        return hdrs

    def _extract_text_from_responses_api(self, data: dict) -> str:
        """Extract generated text from the Groq Responses API format.

        The Responses API returns:
        {
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": "..."}]}
            ]
        }
        """
        output = data.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "message":
                    content = item.get("content")
                    if isinstance(content, list):
                        texts = []
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "output_text":
                                texts.append(str(part.get("text", "")))
                        if texts:
                            return "".join(texts).strip()
        # Fallback: check for top-level output_text (some API versions)
        if "output_text" in data and isinstance(data["output_text"], str):
            return data["output_text"]
        return ""

    def generate_text(self, prompt: str, timeout: int = 10) -> str:
        url = self._chat_completions_url()
        if not url:
            return (prompt or "").strip()[:1000]

        try:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=timeout)
            resp.raise_for_status()
            try:
                data = resp.json()
            except Exception:
                return resp.text or ""

            if isinstance(data, dict):
                # OpenAI/Groq Chat Completions API format
                if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
                    first = data["choices"][0]
                    if isinstance(first, dict):
                        # Check for message.content (OpenAI format)
                        message = first.get("message")
                        if isinstance(message, dict):
                            content = message.get("content")
                            if isinstance(content, str):
                                return content
                        # Legacy text field
                        if "text" in first:
                            return first["text"]

                # Fallback: check for output_text
                if "output_text" in data and isinstance(data["output_text"], str):
                    return data["output_text"]

            return resp.text or ""
        except Exception as exc:
            logger.exception("GroqProvider.generate_text failed: %s", exc)
            return ""

    def analyze_json(self, prompt: str, timeout: int = 10) -> Dict[str, Any]:
        url = self._chat_completions_url()
        if not url:
            result: Dict[str, Any] = {}
            for line in (prompt or "").splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    result[k.strip()] = v.strip()
            return result

        try:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=timeout)
            resp.raise_for_status()
            try:
                data = resp.json()
                if isinstance(data, dict):
                    # Extract content from Chat Completions format
                    if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
                        first = data["choices"][0]
                        if isinstance(first, dict):
                            message = first.get("message")
                            if isinstance(message, dict):
                                content = message.get("content", "")
                                if isinstance(content, str) and content.strip():
                                    try:
                                        parsed = json.loads(content)
                                        if isinstance(parsed, dict):
                                            return parsed
                                    except Exception:
                                        pass
                                    # Try to extract JSON from markdown code blocks
                                    import re
                                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                                    if json_match:
                                        try:
                                            parsed = json.loads(json_match.group(1))
                                            if isinstance(parsed, dict):
                                                return parsed
                                        except Exception:
                                            pass
                    # Fallback: check top-level output_text
                    output_text = data.get("output_text")
                    if isinstance(output_text, str) and output_text.strip():
                        try:
                            parsed = json.loads(output_text)
                            if isinstance(parsed, dict):
                                return parsed
                        except Exception:
                            pass
                    return data
                return {"text": str(data)}
            except Exception:
                result: Dict[str, Any] = {}
                text = resp.text or ""
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    pass
                for line in text.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        result[k.strip()] = v.strip()
                return result
        except Exception as exc:
            logger.exception("GroqProvider.analyze_json failed: %s", exc)
            result = {}
            for line in (prompt or "").splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    result[k.strip()] = v.strip()
            return result

    def score_candidate_job(self, job_payload: Dict[str, Any], candidate_payload: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
        """Ask Groq to score a job/candidate pair and return structured JSON.

        Returns empty dict on failure.
        """
        if not self._chat_completions_url():
            return {}

        # Construct a concise prompt asking for strict JSON output
        prompt = (
            "You are a match engine. Given the JOB and CANDIDATE below, return JSON only with keys:"
            " score (number 0-100), matched_skills (array of strings), missing_skills (array of strings), explanation (string)."
            " Use job.required_skills as canonical skills. Respond with JSON only.\n\n"
            f"JOB={job_payload}\n\nCANDIDATE={candidate_payload}\n"
        )

        try:
            resp = self.analyze_json(prompt, timeout=timeout)
            if not isinstance(resp, dict):
                return {}

            out: Dict[str, Any] = {}
            score = resp.get("score") or resp.get("match_score") or resp.get("llm_score")
            try:
                out_score = float(score) if score is not None else None
            except Exception:
                out_score = None
            if out_score is not None:
                out_score = max(0.0, min(100.0, out_score))
                out["score"] = out_score

            matched = resp.get("matched_skills") or resp.get("matched") or []
            if isinstance(matched, str):
                matched = [s.strip() for s in matched.split(",") if s.strip()]
            out["matched_skills"] = matched or []

            missing = resp.get("missing_skills") or resp.get("missing") or []
            if isinstance(missing, str):
                missing = [s.strip() for s in missing.split(",") if s.strip()]
            out["missing_skills"] = missing or []

            explanation = resp.get("explanation") or resp.get("reason") or resp.get("summary") or ""
            out["explanation"] = str(explanation)

            return out
        except Exception as exc:
            logger.exception("GroqProvider.score_candidate_job failed: %s", exc)
            return {}
