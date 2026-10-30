from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.inventory.models import (
    Asset,
    AssetCategory,
    SoftwareInstallation,
    SoftwareRole,
    VideoWorkflow,
    VideoWorkflowMode,
)

class VideoWorkflowTests(TestCase):
    '''Tests for broadcast workflow validation'''

    def setUp(self):
        self.camera = Asset.objects.create(
            inventory_number='VID-0001',
            name='PTZ Camera',
            category=AssetCategory.VIDEO,
        )

        self.transmitter = Asset.objects.create(
            inventory_number='VID-0002',
            name='J5 Connect TX',
            category=AssetCategory.VIDEO,
        )

        self.receiver = Asset.objects.create(
            inventory_number='VID-0003',
            name='J5 Connect RX',
            category=AssetCategory.VIDEO,
        )

        self.computer = Asset.objects.create(
            inventory_number='COMP-0001',
            name='Broadcast Host',
            category=AssetCategory.COMPUTING,
        )

    def test_direct_workflow_does_not_require_obs(self):
        workflow = VideoWorkflow(
            name='Direct Zoom',
            computer=self.computer,
            camera=self.camera,
            transmitter=self.transmitter,
            receiver=self.receiver,
            mode=VideoWorkflowMode.DIRECT,
        )

        workflow.full_clean()

    def test_obs_workflow_required_obs(self):
        workflow = VideoWorkflow(
            name='OBS to Zoom',
            computer=self.computer,
            camera=self.camera,
            transmitter=self.transmitter,
            receiver=self.receiver,
            mode=VideoWorkflowMode.OBS,
        )

        with self.assertRaises(ValidationError):
            workflow.full_clean()

    def test_obs_must_be_installed_on_broadcast_host(self):
        other_computer = Asset.objects.create(
            inventory_number='COMP-0002',
            name='Other Computer',
            category=AssetCategory.COMPUTING,
        )

        obs = SoftwareInstallation.objects.create(
            host_asset=other_computer,
            name='OBS Studio',
            role=SoftwareRole.VIDEO_PRODUCTION,
        )

        workflow = VideoWorkflow(
            name='Invalid OBS Workflow',
            computer=self.computer,
            camera=self.camera,
            transmitter=self.transmitter,
            receiver=self.receiver,
            mode=VideoWorkflowMode.OBS,
            obs_software=obs,
        )

        with self.assertRaises(ValidationError):
            workflow.full_clean()
