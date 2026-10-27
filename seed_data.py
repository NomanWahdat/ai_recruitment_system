"""Compatibility entry point for the owned, idempotent synthetic demo."""

import os
import django
from django.core.management import call_command


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    django.setup()
    call_command("seed_demo")
