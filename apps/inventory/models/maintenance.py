'''Maintenance and service history'''
from django.db import models

class MaintenanceRecord(models.Model):
    '''A maintenance, test, or repair record for an asset'''

    asset = models.ForeignKey(
        'inventory.Asset',
        on_delete=models.PROTECT,
        related_name='maintenance_records'
    )

    performed_at = models.DateTimeField()

    performed_by = models.CharField(
        max_length=150,
        blank=True,
    )

    maintenance_type = models.CharField(
        max_length=100,
    )

    description = models.TextField()

    result = models.CharField(
        max_length=200,
        blank=True,
    )

    follow_up_required = models.BooleanField(default=False)

    follow_up_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['performed_at']

    def __str__(self) -> str:
        '''Describe the maintenance record'''
        return f'{self.asset.inventory_number} - {self.maintenance_type}'
