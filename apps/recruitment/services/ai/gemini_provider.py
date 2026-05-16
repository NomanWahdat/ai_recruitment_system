import logging
import os
import json
import re
from typing import Any, Dict

import requests
from decouple import config

from .base import AIProvider

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    """Gemini provider implementation.

    If `GEMINI_API_URL` is configured, POST prompts to that URL using `GEMINI_API_KEY`.
    Otherwise, fall back to the previous local echo behavior.
    """

    def __init__(self):
        self.api_url = os.getenv("GEMINI_API_URL") or config("GEMINI_API_URL", default="")
        self.api_key = os.getenv("GEMINI_API_KEY") or config("GEMINI_API_KEY", default="")
        self.model = os.getenv("GEMINI_MODEL") or config("GEMINI_MODEL", default="gemini-2.0-flash")

    def _content_url(self) -> str:
        base_url = (self.api_url or "").rstrip("/")
        if not base_url:
            return ""
        # If URL already contains :generateContent with the correct model, use as-is
        if "generateContent" in base_url and self.model in base_url:
            return base_url
        # If URL contains :generateContent but with a different model, replace the model
        if "generateContent" in base_url and "/models/" in base_url:
            return re.sub(r'/models/[^:]+:', f'/models/{self.model}:', base_url)
        if ":generate" in base_url and "/models/" in base_url:
            fixed = re.sub(r'/models/[^:]+:', f'/models/{self.model}:', base_url)
            return fixed.replace(":generate", ":generateContent")
        if "/models/" in base_url:
            fixed = re.sub(r'/models/[^/:]+$', f'/models/{self.model}', base_url)
            return f"{fixed}:generateContent"
        return f"{base_url}/models/{self.model}:generateContent"

    def _headers(self) -> Dict[str, str]:
        # Gemini REST API authenticates via ?key= query param (added by _url_with_key),
        # not via Authorization: Bearer header.
        hdrs = {"Content-Type": "application/json"}
        return hdrs

    def _url_with_key(self, url: str) -> str:
        # Gemini REST commonly accepts API key via query parameter.
        if not self.api_key:
            return url
        if "generativelanguage.googleapis.com" not in url:
            return url
        if "key=" in url:
            return url
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}key={self.api_key}"

    def generate_text(self, prompt: str, timeout: int = 10) -> str:
        url = self._content_url()
        if not url:
            return "[Gemini simulated response]\n" + (prompt or "").strip()[:1500]

        try:
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}],
                    }
                ],
                "generationConfig": {"temperature": 0},
            }
            resp = requests.post(self._url_with_key(url), json=payload, headers=self._headers(), timeout=timeout)
            resp.raise_for_status()
            try:
                data = resp.json()
            except Exception:
                return resp.text or ""

            # Try common fields
            if isinstance(data, dict):
                if "text" in data and isinstance(data["text"], str):
                    return data["text"]
                if "output" in data and isinstance(data["output"], str):
                    return data["output"]
                candidates = data.get("candidates") or []
                if candidates and isinstance(candidates, list):
                    first = candidates[0] or {}
                    content = first.get("content") or {}
                    parts = content.get("parts") or []
                    if parts and isinstance(parts, list):
                        text_parts = [str(part.get("text", "")) for part in parts if isinstance(part, dict)]
                        joined = "".join(text_parts).strip()
                        if joined:
                            return joined
                if "candidates" in data and isinstance(data["candidates"], list) and data["candidates"]:
                    cand = data["candidates"][0]
                    if isinstance(cand, dict) and "output" in cand:
                        return cand["output"]
                if "candidates" in data and isinstance(data["candidates"], list):
                    # fallback to first candidate text
                    try:
                        return str(data["candidates"][0])
                    except Exception:
                        pass

            return resp.text or ""
        except Exception as exc:
            logger.exception("GeminiProvider.generate_text failed: %s", exc)
            return ""

    def analyze_json(self, prompt: str, timeout: int = 10) -> Dict[str, Any]:
        url = self._content_url()
        if not url:
            parts = (prompt or "").split("\n\n")
            out = {f"part_{i}": p.strip() for i, p in enumerate(parts[:10]) if p.strip()}
            return out

        try:
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}],
                    }
                ],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
            }
            resp = requests.post(self._url_with_key(url), json=payload, headers=self._headers(), timeout=timeout)
            resp.raise_for_status()
            try:
                data = resp.json()
                if isinstance(data, dict):
                    # Gemini usually returns text under candidates[].content.parts[].text
                    candidates = data.get("candidates") or []
                    if candidates and isinstance(candidates, list):
                        first = candidates[0] or {}
                        content = first.get("content") or {}
                        parts = content.get("parts") or []
                        if parts and isinstance(parts, list):
                            text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict)).strip()
                            if text:
                                try:
                                    parsed = json.loads(text)
                                    if isinstance(parsed, dict):
                                        return parsed
                                except Exception:
                                    pass
                    return data
                return {"text": str(data)}
            except Exception:
                text = resp.text or ""
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    pass
                parts = text.split("\n\n")
                out = {f"part_{i}": p.strip() for i, p in enumerate(parts[:10]) if p.strip()}
                return out
        except Exception as exc:
            logger.exception("GeminiProvider.analyze_json failed: %s", exc)
            parts = (prompt or "").split("\n\n")
            out = {f"part_{i}": p.strip() for i, p in enumerate(parts[:10]) if p.strip()}
            return out

    def score_candidate_job(self, job_payload: Dict[str, Any], candidate_payload: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
        """Ask Gemini to score a job/candidate pair and return structured JSON.

        Returns empty dict on failure.
        """
        if not self._content_url():
            return {}

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
            logger.exception("GeminiProvider.score_candidate_job failed: %s", exc)
            return {}
