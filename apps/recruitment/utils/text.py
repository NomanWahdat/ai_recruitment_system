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
