from .base import *
import dj_database_url
from django.core.exceptions import ImproperlyConfigured

DEBUG = False
SECRET_KEY = config("SECRET_KEY")
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith(
    ("unsafe-", "your-", "replace-", "django-insecure-")
):
    raise ImproperlyConfigured(
        "Production requires a generated SECRET_KEY of at least 50 characters."
    )
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())
DATABASES = {"default": dj_database_url.parse(config("DATABASE_URL"), conn_max_age=600)}
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
