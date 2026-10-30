'''Video broadcast workflow configuration'''

from django.core.exceptions import ValidationError
from django.db import models

from .software import SoftwareRole

class VideoWorkflowMode(models.TextChoices):
    '''Available video paths into the meeting'''

    DIRECT = 'direct', 'Receiver Directly to Zoom'
    OBS = 'obs', 'Receiver Through OBS Virtual Camera'

class VideoWorkflow(models.Model):
    '''A documented video broadcast configuration'''

    name = models.CharField(max_length=150)

    computer = models.ForeignKey(
        'inventory.Asset',
        on_delete=models.PROTECT,
        related_name='video_workflows',
    )

    camera = models.ForeignKey(
        'inventory.Asset',
        on_delete=models.PROTECT,
        related_name='camera_workflows',
    )

    transmitter = models.ForeignKey(
        'inventory.Asset',
        on_delete=models.PROTECT,
        related_name='transmitter_workflows',
    )

    receiver = models.ForeignKey(
        'inventory.Asset',
        on_delete=models.PROTECT,
        related_name='receiver_workflows',
    )

    mode = models.CharField(
        max_length=20,
        choices=VideoWorkflowMode.choices,
        default=VideoWorkflowMode.DIRECT,
    )

    obs_software = models.ForeignKey(
        'inventory.SoftwareInstallation',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='video_workflows',
    )

    is_active = models.BooleanField(default=False)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def clean(self) -> None:
        '''Validate that the workflow\'s assets and software agree'''
        super().clean()

        errors = {}

        if self.mode == VideoWorkflowMode.OBS:
            if not self.obs_software_id:
                errors['obs_software'] = "OBS software must be selected for OBS mode."
            elif self.computer_id:
                if self.obs_software.host_asset_id != self.computer_id:
                    errors['obs_software'] = 'The OBS installation must belong to the selected broadcast computer.'
                if self.obs_software.role != SoftwareRole.VIDEO_PRODUCTION:
                    errors['obs_software'] = 'The selected software must have the Video Production role.'
        elif self.mode == VideoWorkflowMode.DIRECT:
            if self.obs_software_id:
                errors['obs_software'] = 'OBS software should not be selected for a direct-to-Zoom workflow.'

        asset_ids = [
            self.computer_id,
            self.camera_id,
            self.transmitter_id,
            self.receiver_id,
        ]

        if None not in asset_ids and len(set(asset_ids)) != 4:
            errors['camera'] = 'The computer, camera, transmitter, and receiver must be four distinct assets.'

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        '''Return the workflow name'''
        return self.name
