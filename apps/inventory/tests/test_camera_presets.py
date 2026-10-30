from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.inventory.models import (
    Asset,
    AssetCategory,
    CameraPreset,
    CameraPresetStatus,
)

class CameraPresetTests(TestCase):
    '''Tests for camera preset records'''

    def setUp(self):
        self.camera = Asset.objects.create(
            inventory_number='VID-0001',
            name='PTZ Camera',
            category=AssetCategory.VIDEO,
        )

    def test_preset_number_zero_is_valid(self):
        preset = CameraPreset.objects.create(
            camera=self.camera,
            preset_number=0,
            name='Default',
            status=CameraPresetStatus.PLANNED,
        )

        self.assertEqual(preset.preset_number, 0)

    def test_preset_number_ten_is_invalid(self):
        preset = CameraPreset(
            camera=self.camera,
            preset_number=10,
            name='Invalid',
        )

        with self.assertRaises(ValidationError):
            preset.full_clean()
