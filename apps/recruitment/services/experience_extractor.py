import re
from decimal import Decimal
from datetime import datetime


class ExperienceExtractor:
    explicit_pattern = re.compile(
        r"(?P<years>\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+)?experience",
        re.IGNORECASE,
    )
    simple_year_pattern = re.compile(r"(?P<years>\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)", re.IGNORECASE)
    range_pattern = re.compile(r"\b(?:19|20)\d{2}\s*[-–—]\s*(?:present|current|(?:19|20)\d{2})\b", re.IGNORECASE)
    # Extended pattern: "Month YYYY - Month YYYY" or "Month YYYY - present"
    month_range_pattern = re.compile(
        r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
        r"\s+((?:19|20)\d{2})\s*[-–—]\s*"
        r"(?:(present|current)|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
        r"\s+((?:19|20)\d{2}))",
        re.IGNORECASE,
    )

    # Section headers that indicate professional experience
    _experience_headers = re.compile(
        r"^(?:professional\s+)?(?:experience|work\s+(?:history|experience)|employment|career)\b",
        re.IGNORECASE | re.MULTILINE,
    )
    # Section headers that indicate non-work sections (education, volunteer, etc.)
    _non_work_headers = re.compile(
        r"^(?:education|academic|school|university|certif|volunteer|extracurricular|additional|skills|interests|hobbies|references|projects)\b",
        re.IGNORECASE | re.MULTILINE,
    )

    def estimate(self, text):
        if not text:
            return Decimal("0.0")

        explicit_years = self._extract_explicit_years(text)
        duration_years = self._estimate_from_date_ranges(text)
        # Prefer explicit numeric callouts if larger, otherwise use estimated duration
        estimate = max(explicit_years, duration_years)
        return Decimal(str(round(min(estimate, 60), 1)))

    def _extract_explicit_years(self, text):
        matches = [float(match.group("years")) for match in self.explicit_pattern.finditer(text)]
        if not matches:
            matches = [float(match.group("years")) for match in self.simple_year_pattern.finditer(text)]
        return max(matches) if matches else 0.0

    def _extract_experience_section(self, text):
        """Extract only the professional experience section from CV text."""
        lines = text.split("\n")
        in_experience = False
        experience_lines = []

        for line in lines:
            stripped = line.strip()
            if self._experience_headers.search(stripped):
                in_experience = True
                continue
            elif self._non_work_headers.search(stripped):
                if in_experience:
                    break  # End of experience section
                continue
            if in_experience:
                experience_lines.append(line)

        return "\n".join(experience_lines) if experience_lines else ""

    def _estimate_from_date_ranges(self, text):
        # Try to extract only from experience section first
        experience_text = self._extract_experience_section(text)
        target_text = experience_text if experience_text else text

        current_year = datetime.utcnow().year
        # Collect all (start_year, end_year) tuples
        spans = []

        # Pattern 1: "YYYY - YYYY" or "YYYY - present"
        for match in self.range_pattern.findall(target_text):
            years = [int(year) for year in re.findall(r"(?:19|20)\d{2}", match)]
            if len(years) == 1 and re.search(r"present|current", match, re.IGNORECASE):
                spans.append((years[0], current_year))
            elif len(years) >= 2:
                spans.append((years[0], years[-1]))

        # Pattern 2: "Month YYYY - Month YYYY" or "Month YYYY - present"
        for match in self.month_range_pattern.finditer(target_text):
            start_year = int(match.group(1))
            if match.group(2):  # present/current
                spans.append((start_year, current_year))
            elif match.group(3):
                end_year = int(match.group(3))
                spans.append((start_year, end_year))

        if not spans:
            return 0.0

        # Compute career span: earliest start to latest end (not sum of all ranges)
        earliest_start = min(s[0] for s in spans)
        latest_end = max(s[1] for s in spans)
        return float(max(0, latest_end - earliest_start))
