"""Local workstation development settings."""

from .base import *


DEBUG = True

INSTALLED_APPS += [
    'apps.notifications',
]

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'web',
]

# Development-only convenience. Production must configure trusted origins.
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
