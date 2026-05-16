import re
from urllib.parse import urlparse


def clean_extracted_text(text):
    if not text:
        return ""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n[ \t]+", "\n", normalized)
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def normalize_text(text):
    return clean_extracted_text(text)


def unique_preserve_order(values):
    seen = set()
    results = []

    for value in values:
        normalized = str(value).strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            results.append(normalized)

    return results


def normalize_url(url):
    cleaned = url.strip().rstrip(".,);]")
    if not cleaned:
        return ""

    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"

    parsed = urlparse(cleaned)
    if not parsed.netloc:
        return ""

    return cleaned


def clean_entity(value):
    return re.sub(r"\s+", " ", value).strip(" -:|,\n\t")


def extract_json_from_text(text: str):
    """Extract JSON object from AI response text, handling markdown code blocks.

    Returns (parsed_dict, True) on success or (None, False) on failure.
    """
    import json

    txt = (text or "").strip()
    if not txt:
        return None, False

    # 1. Try direct JSON parse
    try:
        parsed = json.loads(txt)
        if isinstance(parsed, dict):
            return parsed, True
    except Exception:
        pass

    # 2. Strip markdown ```json ... ``` or ``` ... ``` blocks
    md_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", txt, re.DOTALL)
    if md_match:
        try:
            parsed = json.loads(md_match.group(1).strip())
            if isinstance(parsed, dict):
                return parsed, True
        except Exception:
            pass

    # 3. Find first { ... } substring and try to parse
    brace_match = re.search(r"\{.*\}", txt, re.DOTALL)
    if brace_match:
        try:
            parsed = json.loads(brace_match.group(0))
            if isinstance(parsed, dict):
                return parsed, True
        except Exception:
            pass

    return None, False
