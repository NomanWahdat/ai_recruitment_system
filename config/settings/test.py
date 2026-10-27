"""Test settings - disables external API calls during testing."""

from .base import *
from .base import DATABASES as POSTGRES_DATABASES

DEBUG = True

# Use SQLite for faster tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable AI providers during tests to avoid API calls
USE_GROQ_AI = False
USE_GEMINI_FALLBACK = False

# Disable automation orchestrator events
# This prevents AI calls during job/candidate creation
AUTOMATION_ENABLED = False
API_THROTTLING_ENABLED = False
USE_LLM_FOR_SCORING = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": []}
if config("TEST_POSTGRES", default=False, cast=bool):
    DATABASES = POSTGRES_DATABASES

# Use console email backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Disable logging noise during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "WARNING",
    },
}
