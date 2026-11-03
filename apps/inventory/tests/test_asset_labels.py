"""Tests for physical inventory label preparation pages."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.inventory.models import Asset, AssetCategory, Room, RoomPriority


@override_settings(ASSET_LABEL_SITE_HEADING='MEETINGHOUSE TECH')
class AssetLabelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='label-admin', password='test-password-42')
        self.client.force_login(self.user)
        self.room = Room.objects.create(name='Cultural Hall', room_number='101', priority=RoomPriority.NORMAL)
        self.asset = Asset.objects.create(
            inventory_number='AUDIO-0042',
            name='Audio Mixer',
            category=AssetCategory.AUDIO,
            serial_number='SECRET-SERIAL-DO-NOT-PRINT',
            room=self.room,
        )

    def test_individual_label_uses_room_heading_and_identifier_only(self):
        response = self.client.get(reverse('inventory:asset_label', args=(self.asset.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cultural Hall')
        self.assertContains(response, 'AUDIO-0042')
        self.assertContains(response, 'Audio Mixer')
        self.assertNotContains(response, 'SECRET-SERIAL-DO-NOT-PRINT')
        detail = self.client.get(reverse('inventory:asset_detail', args=(self.asset.pk,)))
        self.assertContains(detail, reverse('inventory:asset_label', args=(self.asset.pk,)))

    def test_unassigned_asset_uses_configured_site_heading(self):
        self.asset.room = None
        self.asset.save(update_fields=('room',))
        response = self.client.get(reverse('inventory:asset_label', args=(self.asset.pk,)))
        self.assertContains(response, 'MEETINGHOUSE TECH')
        self.assertContains(response, 'AUDIO-0042')

    def test_batch_label_page_contains_selected_assets_only(self):
        other = Asset.objects.create(inventory_number='VID-0002', name='PTZ Camera')
        response = self.client.post(
            reverse('inventory:asset_labels'),
            {'asset_ids': [str(self.asset.pk), str(other.pk)]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AUDIO-0042')
        self.assertContains(response, 'VID-0002')
        self.assertNotContains(response, 'SECRET-SERIAL-DO-NOT-PRINT')

    def test_empty_batch_selection_shows_helpful_state(self):
        response = self.client.post(reverse('inventory:asset_labels'), {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select equipment first')

    def test_long_asset_name_is_shortened_but_full_name_remains_as_reference(self):
        self.asset.name = 'Extremely Long Audio Mixer Name Used For Testing Label Length'
        self.asset.save(update_fields=('name',))
        response = self.client.get(reverse('inventory:asset_label', args=(self.asset.pk,)))
        self.assertContains(response, 'Extremely Long Audio Mixer')
        self.assertContains(response, 'Full asset name:')
        self.assertContains(response, 'AUDIO-0042')

    def test_printing_does_not_change_asset_record(self):
        before = (self.asset.name, self.asset.inventory_number, self.asset.updated_at)
        self.client.get(reverse('inventory:asset_label', args=(self.asset.pk,)))
        self.asset.refresh_from_db()
        self.assertEqual((self.asset.name, self.asset.inventory_number, self.asset.updated_at), before)

    def test_label_pages_require_authentication(self):
        self.client.logout()
        response = self.client.get(reverse('inventory:asset_label', args=(self.asset.pk,)))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    @override_settings(ROOT_URLCONF='config.training_urls', TRAINING_ONLY=True)
    def test_training_only_profile_does_not_expose_label_routes(self):
        self.client.logout()
        self.assertEqual(self.client.get('/inventory/labels/print/').status_code, 404)
