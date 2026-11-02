'''Context shared by templates across deployment profiles.'''

from django.conf import settings


def application_mode(request):
    '''Expose deployment branding and access mode to shared templates.'''
    return {
        'training_only': getattr(settings, 'TRAINING_ONLY', False),
        'brand_logo_url': settings.BRAND_LOGO_URL,
        'show_management_link': getattr(settings, 'SHOW_MANAGEMENT_LINK', False),
        'management_login_url': getattr(settings, 'MANAGEMENT_LOGIN_URL', ''),
    }
