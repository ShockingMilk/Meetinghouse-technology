'''Production settings for the public training-only deployment.'''

import os

from .production import *

ROOT_URLCONF = 'config.training_urls'
TRAINING_ONLY = True

# Training pages do not require authentication. The imported public catalog is
# stored in this deployment's own database and never shares management data.
DATABASES['default']['NAME'] = os.environ.get(
    'DJANGO_DB_PATH',
    '/app/data/meetinghouse-training.sqlite3',
)

# The training profile has its own database. Only the public guide catalog is
# copied into it; it never points at the management database.
TRAINING_CATALOG_PATH = os.environ.get('TRAINING_CATALOG_PATH', '/app/data/training-catalog.json')
