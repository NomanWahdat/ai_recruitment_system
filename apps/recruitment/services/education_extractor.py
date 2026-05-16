import re

from apps.recruitment.utils.text import clean_entity, unique_preserve_order


class EducationExtractor:
    education_keywords = [
        "bachelor",
        "master",
        "phd",
        "doctorate",
        "bs",
        "bsc",
        "ms",
        "msc",
        "mba",
        "computer science",
        "software engineering",
        "information technology",
        "university",
        "college",
        "institute",
    ]

    def extract(self, text):
        if not text:
            return ""

        lines = [clean_entity(line) for line in text.splitlines()]
        matches = []

        for index, line in enumerate(lines):
            lowered = line.lower()
            if any(keyword in lowered for keyword in self.education_keywords):
                context = [line]
                if index + 1 < len(lines):
                    next_line = clean_entity(lines[index + 1])
                    if next_line and len(next_line) < 120:
                        context.append(next_line)
                matches.append(" - ".join(context))

        if not matches:
            degree_match = re.search(
                r"\b(?:BS|BSc|BA|MS|MSc|MBA|B\.Sc|M\.Sc|Bachelor(?:'s)?|Master(?:'s)?|PhD|Doctorate)\b[^\n,.]*",
                text,
                re.IGNORECASE,
            )
            if degree_match:
                matches.append(clean_entity(degree_match.group(0)))

        # Standardize and return up to 5 unique education snippets
        cleaned = unique_preserve_order(matches[:5])
        return "; ".join(cleaned)
