from django.apps import AppConfig

class TrainingConfig(AppConfig):
    '''Training application configuration'''

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.training'
    verbose_name = 'Technology Training'
