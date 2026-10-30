'''Deployment settings for the private management environment'''
import os
from .base import *

DEBUG = False

ALLOWED_HOSTS = os.environ.get(
    key='DJANGO_ALLOWED_HOSTS',
    default='',
).split(',')

CSRF_TRUSTED_ORIGINS = os.environ.get(
    key='DJANGO_CSRF_TRUSTED_ORIGINS',
    default='',
).split(',')

SECURE_SSL_REDIRECT = os.environ.get(
    key='DJANGO_SECURE_SSL_REDIRECT',
    default='0',
) == '1'

SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT
CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT

SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
