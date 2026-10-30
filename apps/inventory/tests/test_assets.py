from django.test import TestCase

from apps.inventory.models import Asset, AssetCategory, AssetOwnership

class AssetModelTests(TestCase):
    '''Tests for the asset model'''

    def test_asset_string_representation(self):
        asset = Asset.objects.create(
            inventory_number='VID-0001',
            name='PTZ Camera',
            category=AssetCategory.VIDEO,
            ownership=AssetOwnership.UNKNOWN,
        )

        self.assertEqual(
            str(asset),
            'VID-0001 - PTZ Camera',
        )
