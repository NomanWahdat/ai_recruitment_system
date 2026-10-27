import re
from decimal import Decimal
from datetime import date


class ExperienceExtractor:
    def __init__(self, as_of=None):
        self.as_of = as_of

    explicit_pattern = re.compile(
        r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+)?experience", re.I
    )
    months = {
        name: i
        for i, name in enumerate(
            ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1
        )
    }
    date_range = re.compile(
        r"(?:(Jan\w*|Feb\w*|Mar\w*|Apr\w*|May|Jun\w*|Jul\w*|Aug\w*|Sep\w*|Oct\w*|Nov\w*|Dec\w*)\s+)?((?:19|20)\d{2})\s*[-\u2013\u2014]\s*(?:(present|current)|(?:(Jan\w*|Feb\w*|Mar\w*|Apr\w*|May|Jun\w*|Jul\w*|Aug\w*|Sep\w*|Oct\w*|Nov\w*|Dec\w*)\s+)?((?:19|20)\d{2}))",
        re.I,
    )

    def _extract_experience_section(self, text):
        match = re.search(
            r"^(?:professional\s+|work\s+)?(?:experience|employment|work history)\s*:?\s*$",
            text,
            re.I | re.M,
        )
        if not match:
            return ""
        section = text[match.end() :]
        return re.split(
            r"^(?:education|skills|projects|certifications|references|interests)\s*:?\s*$",
            section,
            flags=re.I | re.M,
        )[0]

    def estimate(self, text):
        if not text:
            return Decimal("0.0")
        spans = []
        now = self.as_of or date.today()
        for m in self.date_range.finditer(self._extract_experience_section(text)):
            start = int(m[2]) * 12 + self.months.get((m[1] or "jan")[:3].lower(), 1)
            end = (
                now.year * 12 + now.month
                if m[3]
                else int(m[5]) * 12 + self.months.get((m[4] or "jan")[:3].lower(), 1)
            )
            if end >= start:
                spans.append((start, min(end, now.year * 12 + now.month)))
        merged = []
        for start, end in sorted(spans):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        years = sum(max(0, end - start) for start, end in merged) / 12
        if not spans:
            years = max([float(m[1]) for m in self.explicit_pattern.finditer(text)] or [0])
        return Decimal(str(round(min(years, 60), 1)))
