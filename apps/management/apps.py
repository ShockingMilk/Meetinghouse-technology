from django.apps import AppConfig

class ManagementConfig(AppConfig):
    '''Management application configuration'''

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.management'
    verbose_name = 'Technology Management'
