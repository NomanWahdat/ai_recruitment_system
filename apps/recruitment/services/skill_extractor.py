import re
from collections import Counter

from apps.recruitment.utils.text import unique_preserve_order


SKILL_DICTIONARY = {
    "Backend": ["Python", "Django", "Flask", "FastAPI", "Node.js", "Express"],
    "Frontend": ["React", "Vue", "Angular", "JavaScript", "TypeScript"],
    "AI/ML": [
        "OpenAI",
        "TensorFlow",
        "PyTorch",
        "NLP",
        "Machine Learning",
        "LangChain",
    ],
    "Database": ["PostgreSQL", "MySQL", "MongoDB", "Redis"],
    "Cloud/DevOps": ["AWS", "Docker", "Kubernetes", "GCP", "Azure"],
    "Automation": ["n8n", "Zapier", "Make", "Selenium"],
    "Interpretation": [
        "Pashto",
        "Dari",
        "Farsi",
        "English",
        "Interpretation",
        "Translation",
        "Medical Interpretation",
        "Legal Interpretation",
        "Customer Support",
        "Communication Skills",
        "Cultural Mediation",
        "OPI",
        "VRI",
        "HIPAA",
    ],
}


class SkillExtractor:
    def __init__(self):
        self.skill_lookup = {
            skill.lower(): skill
            for skills in SKILL_DICTIONARY.values()
            for skill in skills
        }

    def extract(self, text, nlp=None):
        if not text:
            return []

        counter = Counter()
        lowered_text = text.lower()

        # direct dictionary matches
        for key, label in self.skill_lookup.items():
            pattern = self._skill_pattern(key)
            matches = re.findall(pattern, lowered_text, flags=re.IGNORECASE)
            if matches:
                counter[label] += len(matches)

        # Extract explicit "skills" section lines for broader CV support.
        section_hits = self._extract_skills_section(text)
        for item in section_hits:
            # Normalize to canonical casing when available.
            key = item.lower()
            counter[self.skill_lookup.get(key, item)] += 1

        # NLP based extraction: noun chunks and named entities (if model supports)
        if nlp:
            try:
                doc = nlp(text[:100000])
                # noun chunks (phrase-level matches)
                if "parser" in nlp.pipe_names:
                    noun_chunks = [chunk.text.strip().lower() for chunk in doc.noun_chunks]
                    for chunk in noun_chunks:
                        if chunk in self.skill_lookup:
                            counter[self.skill_lookup[chunk]] += 1

                # entities and tokens (handle lemmatized tokens)
                for ent in doc.ents:
                    ent_text = ent.text.strip().lower()
                    if ent_text in self.skill_lookup:
                        counter[self.skill_lookup[ent_text]] += 1

                # token-level checks: join adjacent tokens to capture names like 'machine learning'
                tokens = [t.lemma_.lower() for t in doc if not t.is_stop and not t.is_punct]
                joined = " ".join(tokens)
                for key, label in self.skill_lookup.items():
                    if key in joined:
                        counter[label] += 1
            except Exception:
                # Fail gracefully and rely on dictionary matches
                pass

        ranked = [skill for skill, _ in counter.most_common()]
        return unique_preserve_order(ranked)

    def _extract_skills_section(self, text):
        lines = [line.strip(" -\t") for line in (text or "").splitlines()]
        extracted = []
        in_skills = False

        for line in lines:
            if not line:
                continue
            lowered = line.lower().strip()

            if lowered in {"skills", "technical skills", "key skills"}:
                in_skills = True
                continue

            if in_skills and (re.match(r"^[a-z ]{2,30}:$", lowered) or lowered in {
                "education", "experience", "professional experience", "work experience",
                "additional", "extracurricular", "certifications", "references",
                "volunteer", "interests", "hobbies", "projects",
            }):
                # New section header encountered.
                break

            if in_skills:
                # Split comma-separated and conjunction-separated skills.
                parts = re.split(r",|\band\b|\u2022|;", line, flags=re.IGNORECASE)
                for part in parts:
                    cleaned = re.sub(r"\s+", " ", part).strip(" -:\t\u2013\u2014")
                    # Filter: skill names should be short, not start with descriptions
                    if not cleaned or len(cleaned) > 35:
                        continue
                    # Skip entries that look like descriptions/sentences
                    if any(cleaned.lower().startswith(w) for w in [
                        "native", "in-depth", "expertise in", "strong",
                        "effective", "with ", "knowledge of", "experience in",
                        "ability to", "proficient in",
                    ]):
                        continue
                    extracted.append(cleaned)

        return extracted

    def _skill_pattern(self, skill):
        escaped = re.escape(skill)
        if skill in {"c", "c++"}:
            return escaped
        return rf"(?<![A-Za-z0-9+#.]){escaped}(?![A-Za-z0-9+#.])"
