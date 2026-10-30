'''PTZ Camera presets stored by the camera itself'''
from django.core.validators  import MaxValueValidator, MinValueValidator
from django.db import models

class CameraPresetStatus(models.TextChoices):
    '''Configuration state of a camera preset'''

    UNASSIGNED = 'unassigned', 'Unassigned'
    PLANNED = 'planned', 'Planned'
    CONFIGURED = 'configured', 'Configured'
    VERIFIED = 'verified', 'Verified'
    NEEDS_REVIEW = 'needs_review', 'Needs Review'

class CameraPreset(models.Model):
    '''A preset position saved in a PTZ camera'''

    camera = models.ForeignKey(
        'inventory.Asset',
        on_delete=models.PROTECT,
        related_name='camera_presets',
    )

    preset_number = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(9),
        ],
    )

    name = models.CharField(
        max_length=100,
    )

    purpose = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=CameraPresetStatus.choices,
        default=CameraPresetStatus.UNASSIGNED,
    )

    framing_notes = models.TextField(blank=True)

    last_verified = models.DateField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['camera', 'preset_number']
        constraints = [
            models.UniqueConstraint(
                fields=['camera', 'preset_number'],
                name='unique_camera_preset_number',
            ),
        ]

    def __str__(self) -> str:
        '''Describe the preset'''
        return f'{self.camera.inventory_number} - Preset {self.preset_number}: {self.name}'
