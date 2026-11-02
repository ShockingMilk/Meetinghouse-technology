'''Shared Django settings'''

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get(
    key='DJANGO_SECRET_KEY',
    default='development-only-key-change-before-deployment',
)

BRAND_LOGO_URL = os.environ.get('BRAND_LOGO_URL') or '/static/branding/site-logo.png'
ASSET_LABEL_SITE_HEADING = os.environ.get('ASSET_LABEL_SITE_HEADING', 'MEETINGHOUSE TECH').strip()
LIFECYCLE_WARNING_DAYS = int(os.environ.get('LIFECYCLE_WARNING_DAYS', '180'))
MAINTENANCE_DUE_SOON_DAYS = int(os.environ.get('MAINTENANCE_DUE_SOON_DAYS', '30'))
MAINTENANCE_CATEGORY_INTERVALS_MONTHS = {
    'audio': int(os.environ.get('MAINTENANCE_INTERVAL_AUDIO_MONTHS', '6')),
    'assistive_listening': int(os.environ.get('MAINTENANCE_INTERVAL_ASSISTIVE_MONTHS', '3')),
    'video': int(os.environ.get('MAINTENANCE_INTERVAL_VIDEO_MONTHS', '3')),
    'printer': int(os.environ.get('MAINTENANCE_INTERVAL_PRINTER_MONTHS', '3')),
    'network': int(os.environ.get('MAINTENANCE_INTERVAL_NETWORK_MONTHS', '6')),
    'portable_or_stored': int(os.environ.get('MAINTENANCE_INTERVAL_STORED_MONTHS', '6')),
}
SHOW_MANAGEMENT_LINK = os.environ.get('SHOW_MANAGEMENT_LINK', '0') == '1'
MANAGEMENT_LOGIN_URL = os.environ.get('MANAGEMENT_LOGIN_URL', '')

DEBUG = False

ALLOWED_HOSTS = os.environ.get(
    key='DJANGO_ALLOWED_HOSTS',
    default='localhost,127.0.0.1',
).split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'apps.management',
    'apps.inventory',
    'apps.training',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'config.context_processors.application_mode',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get(
            key='DJANGO_DB_PATH',
            default=str(BASE_DIR / 'data' / 'db.sqlite3'),
        ),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'UserAttributeSimilarityValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'MinimumLengthValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'CommonPasswordValidator'
        ),
    },
]

LANGUAGE_CODE = os.environ.get(
    key='DJANGO_LANGUAGE_CODE',
    default='en-us',
)

TIME_ZONE = os.environ.get(
    key='DJANGO_TIME_ZONE',
    default='America/Los_Angeles',
)

USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'management:dashboard'
LOGOUT_REDIRECT_URL = 'login'

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
