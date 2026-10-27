import re
from apps.recruitment.utils.text import clean_entity, unique_preserve_order


class EducationExtractor:
    pattern = re.compile(
        r"\b(?:bachelor|master|phd|doctorate|bsc|msc|mba|bs|ms|university|college|institute|computer science|software engineering)\b",
        re.I,
    )

    def extract(self, text):
        lines = [clean_entity(line) for line in (text or "").splitlines()]
        return "; ".join(
            unique_preserve_order([line for line in lines if self.pattern.search(line)])[:5]
        )
