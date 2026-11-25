"""
Development settings for EduExam SaaS.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Allow all CORS origins in dev
CORS_ALLOW_ALL_ORIGINS = True

# Simpler password hashing in dev for speed
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
