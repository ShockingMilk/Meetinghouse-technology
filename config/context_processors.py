'''Context shared by templates across deployment profiles.'''

from django.conf import settings


def application_mode(request):
    '''Expose the deployment profile so training can hide management links.'''
    return {'training_only': getattr(settings, 'TRAINING_ONLY', False)}
