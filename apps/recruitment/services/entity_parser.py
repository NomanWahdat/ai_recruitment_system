import re

import phonenumbers

from apps.recruitment.utils.text import clean_entity, normalize_url, unique_preserve_order


class EntityParser:
    email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    url_pattern = re.compile(
        r"(?:(?:https?://)?(?:www\.)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s]*)?)"
    )

    def extract_email(self, text):
        if not text:
            return ""

        cleaned = text
        # common obfuscations: 'name [at] domain.com', 'name (at) domain dot com'
        cleaned = re.sub(r"\s*\[?\(?at\)?\]?\s*", "@", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*\[?\(?dot\)?\]?\s*", ".", cleaned, flags=re.IGNORECASE)
        # remove spaces in common email fragments like 'name @ domain . com'
        cleaned = re.sub(r"\s*@\s*", "@", cleaned)
        cleaned = re.sub(r"\s*\.\s*", ".", cleaned)

        matches = self.email_pattern.findall(cleaned)
        return matches[0].lower() if matches else ""

    def extract_phone(self, text):
        if not text:
            return ""

        for region in [None, "US", "PK", "GB", "IN"]:
            try:
                for match in phonenumbers.PhoneNumberMatcher(text, region):
                    number = match.number
                    if phonenumbers.is_possible_number(number):
                        return phonenumbers.format_number(
                            number,
                            phonenumbers.PhoneNumberFormat.INTERNATIONAL,
                        )
            except Exception:
                continue

        fallback = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", text)
        return clean_entity(fallback.group(0)) if fallback else ""

    def extract_urls(self, text):
        urls = [normalize_url(url) for url in self.url_pattern.findall(text or "")]
        urls = [url for url in urls if url and "@" not in url]
        urls = unique_preserve_order(urls)

        linkedin_url = ""
        github_url = ""
        portfolio_url = ""

        for url in urls:
            lowered = url.lower()
            if "linkedin.com" in lowered and not linkedin_url:
                linkedin_url = url
            elif "github.com" in lowered and not github_url:
                github_url = url
            elif not portfolio_url and not any(
                domain in lowered
                for domain in ["linkedin.com", "github.com", "facebook.com", "twitter.com"]
            ):
                portfolio_url = url

        return {
            "linkedin_url": linkedin_url,
            "github_url": github_url,
            "portfolio_url": portfolio_url,
            "urls": urls,
        }

    def extract_name(self, text, nlp=None):
        header_name = self._extract_name_from_header(text)
        if header_name:
            return header_name

        if nlp:
            doc = nlp((text or "")[:2000])
            for entity in doc.ents:
                if entity.label_ == "PERSON":
                    name = clean_entity(entity.text)
                    if self._looks_like_name(name):
                        return name

        return ""

    def _extract_name_from_header(self, text):
        lines = [clean_entity(line) for line in (text or "").splitlines()[:8]]
        ignored = {"resume", "cv", "curriculum vitae"}

        for line in lines:
            lowered = line.lower()
            if not line or lowered in ignored or "@" in line or "http" in lowered:
                continue
            if self._looks_like_name(line):
                return line

        return ""

    def _looks_like_name(self, value):
        parts = value.split()
        if not 2 <= len(parts) <= 4:
            return False
        return all(part.replace("-", "").isalpha() for part in parts)
