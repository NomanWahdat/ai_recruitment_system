"""Test settings - disables external API calls during testing."""
from .base import *

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
