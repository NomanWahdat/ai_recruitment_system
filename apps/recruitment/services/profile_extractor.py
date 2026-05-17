from apps.recruitment.services.education_extractor import EducationExtractor
from apps.recruitment.services.entity_parser import EntityParser
from apps.recruitment.services.experience_extractor import ExperienceExtractor
from apps.recruitment.services.skill_extractor import SkillExtractor
from apps.recruitment.utils.text import normalize_text
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Try to import spacy, but provide fallback if not available
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None
    logger.warning("spaCy not installed. NLP features will use fallback methods.")


class ProfileExtractor:
    def __init__(self):
        self.nlp = self._load_nlp_model()
        self.entity_parser = EntityParser()
        self.skill_extractor = SkillExtractor()
        self.education_extractor = EducationExtractor()
        self.experience_extractor = ExperienceExtractor()

    def extract(self, text):
        normalized_text = normalize_text(text)

        # Prepare defaults
        extracted = {
            "full_name": "",
            "email": "",
            "phone_number": "",
            "skills": [],
            "education": "",
            "years_of_experience": Decimal("0.0"),
            "linkedin_url": "",
            "github_url": "",
            "portfolio_url": "",
        }

        try:
            urls = self.entity_parser.extract_urls(normalized_text)
        except Exception as exc:
            logger.exception("Failed to extract urls: %s", exc)
            urls = {"linkedin_url": "", "github_url": "", "portfolio_url": "", "urls": []}

        try:
            name = self.entity_parser.extract_name(normalized_text, self.nlp)
            extracted["full_name"] = name or extracted["full_name"]
        except Exception as exc:
            logger.exception("Name extraction failed: %s", exc)

        try:
            extracted["email"] = self.entity_parser.extract_email(normalized_text) or extracted["email"]
        except Exception as exc:
            logger.exception("Email extraction failed: %s", exc)

        try:
            extracted["phone_number"] = self.entity_parser.extract_phone(normalized_text) or extracted["phone_number"]
        except Exception as exc:
            logger.exception("Phone extraction failed: %s", exc)

        try:
            skills = self.skill_extractor.extract(normalized_text, self.nlp)
            extracted["skills"] = skills or extracted["skills"]
        except Exception as exc:
            logger.exception("Skill extraction failed: %s", exc)

        try:
            extracted["education"] = self.education_extractor.extract(normalized_text) or extracted["education"]
        except Exception as exc:
            logger.exception("Education extraction failed: %s", exc)

        try:
            years = self.experience_extractor.estimate(normalized_text)
            # ensure Decimal return type to match model expectations
            if isinstance(years, Decimal):
                extracted["years_of_experience"] = years
            else:
                extracted["years_of_experience"] = Decimal(str(float(years)))
        except Exception as exc:
            logger.exception("Experience estimation failed: %s", exc)

        extracted["linkedin_url"] = urls.get("linkedin_url", "")
        extracted["github_url"] = urls.get("github_url", "")
        extracted["portfolio_url"] = urls.get("portfolio_url", "")

        return extracted

    def _load_nlp_model(self):
        if not SPACY_AVAILABLE or spacy is None:
            logger.warning("spaCy not available. Using fallback for NLP model.")
            return None
        try:
            return spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("en_core_web_sm model not found. Using blank English model.")
            return spacy.blank("en")
