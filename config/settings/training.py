'''Production settings for the public training-only deployment.'''

import os

from .production import *

ROOT_URLCONF = 'config.training_urls'
TRAINING_ONLY = True

# Training pages do not require authentication or use a database. Keep the
# deployment's database path separate in case future training features change.
DATABASES['default']['NAME'] = os.environ.get(
    'DJANGO_DB_PATH',
    '/tmp/meetinghouse-training.sqlite3',
)
