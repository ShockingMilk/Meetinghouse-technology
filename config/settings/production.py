'''Deployment settings for the private management environment'''
import os
from .base import *

DEBUG = False

INSTALLED_APPS += [
    'apps.notifications',
]

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        'DJANGO_ALLOWED_HOSTS',
        '',
    ).split(',')
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'DJANGO_CSRF_TRUSTED_ORIGINS',
        '',
    ).split(',')
    if origin.strip()
]

SECURE_SSL_REDIRECT = os.environ.get(
    key='DJANGO_SECURE_SSL_REDIRECT',
    default='0',
) == '1'

SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT
CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT

SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
