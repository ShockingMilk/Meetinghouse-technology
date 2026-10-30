'''Software installed on building technology assets'''
from django.db import models

class SoftwareRole(models.TextChoices):
    '''Purpose of an installed software package'''

    VIDEO_CAPTURE = 'video_capture', 'Video Capture'
    VIDEO_PRODUCTION = 'video_production', 'Video Production'
    VIDEO_CONFERENCE = 'video_conference', 'Video Conferencing'
    DRIVER = 'driver', 'Hardware Driver'
    OTHER = 'other', 'Other'

class SoftwareInstallation(models.Model):
    '''A software package installed on a host asset'''

    host_asset = models.ForeignKey(
        'inventory.Asset',
        on_delete=models.PROTECT,
        related_name='software_installations',
    )

    name = models.CharField(max_length=150)
    version = models.CharField(max_length=100, blank=True)

    role = models.CharField(
        max_length=30,
        choices=SoftwareRole.choices,
        default=SoftwareRole.OTHER,
    )

    is_required = models.BooleanField(default=False)
    is_enabled = models.BooleanField(default=True)

    virtual_camera_enabled = models.BooleanField(
        default=False,
    )

    last_verified = models.DateField(
        null=True,
        blank=True,
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['host_asset__inventory_number', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['host_asset', 'name'],
                name='unique_software_per_asset',
            ),
        ]

    def __str__(self) -> str:
        '''Describe the installed software'''
        return f'{self.name} on {self.host_asset.inventory_number}'
