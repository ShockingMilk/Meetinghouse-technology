from django.apps import AppConfig

class InventoryConfig(AppConfig):
    '''Inventory application configuration'''

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inventory'
    verbose_name = 'Building Technology Inventory'
