'''Tests for the session-based equipment entry wizard.'''

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.inventory.models import (
    Asset,
    AssetCategory,
    AssetCondition,
    AssetOwnership,
    AssetStatus,
    Room,
    RoomPriority,
)


class AssetWizardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='tech-admin',
            password='test-password-42',
        )
        self.client.force_login(self.user)
        self.room = Room.objects.create(
            name='Broadcast Booth',
            room_number='101',
            priority=RoomPriority.PRIORITY,
        )

    def begin_draft(self):
        response = self.client.get(reverse('inventory:asset_wizard_start'))
        self.assertEqual(response.status_code, 302)
        drafts = self.client.session['inventory_wizard_drafts']
        wizard_id = next(iter(drafts))
        return wizard_id

    def complete_first_five_steps(self, wizard_id, *, name='PTZ Camera', number='VID-0001'):
        steps = [
            (1, {'room': str(self.room.pk)}),
            (2, {'category': AssetCategory.VIDEO}),
            (3, {
                'inventory_number': number,
                'name': name,
                'manufacturer': 'Example Manufacturer',
                'model_number': 'PTZ-1',
                'serial_number': 'SERIAL-1',
                'physical_location': 'Camera shelf',
            }),
            (4, {
                'installation_date': '',
                'warranty_end_date': '',
                'end_of_life_date': '',
                'security_support_end_date': '',
                'last_tested': '',
                'documentation_url': '',
                'funding_route': '',
                'approval_status': '',
                'replacement_estimate': '',
                'recommended_action': '',
                'specification': '',
                'dependencies': '',
                'notes': '',
            }),
            (5, {
                'ownership': AssetOwnership.UNKNOWN,
                'condition': AssetCondition.GOOD,
                'status': AssetStatus.ACTIVE,
                'responsible_party': 'Technology specialist',
            }),
        ]
        for step, fields in steps:
            fields['action'] = 'next'
            response = self.client.post(
                reverse('inventory:asset_wizard_step', args=(wizard_id, step)),
                fields,
            )
            self.assertEqual(response.status_code, 302)
        return reverse('inventory:asset_wizard_review', args=(wizard_id,))

    def test_new_equipment_is_saved_only_after_final_confirmation(self):
        wizard_id = self.begin_draft()
        review_url = self.complete_first_five_steps(wizard_id)

        self.assertFalse(Asset.objects.exists())
        self.assertEqual(self.client.get(review_url).status_code, 200)

        response = self.client.post(review_url, {'action': 'save'})

        asset = Asset.objects.get(inventory_number='VID-0001')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(asset.name, 'PTZ Camera')
        self.assertEqual(asset.room, self.room)
        self.assertEqual(asset.category, AssetCategory.VIDEO)
        self.assertNotIn(wizard_id, self.client.session['inventory_wizard_drafts'])

    def test_incomplete_step_can_be_saved_and_resumed(self):
        wizard_id = self.begin_draft()
        self.client.post(
            reverse('inventory:asset_wizard_step', args=(wizard_id, 1)),
            {'room': str(self.room.pk), 'action': 'next'},
        )
        self.client.post(
            reverse('inventory:asset_wizard_step', args=(wizard_id, 2)),
            {'category': AssetCategory.VIDEO, 'action': 'next'},
        )

        # Return to step three and save an incomplete change without validation.
        response = self.client.post(
            reverse('inventory:asset_wizard_step', args=(wizard_id, 3)),
            {
                'inventory_number': 'VID-DRAFT-2',
                'name': '',
                'action': 'save_draft',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Asset.objects.exists())

        response = self.client.get(reverse('inventory:asset_wizard_step', args=(wizard_id, 3)))
        self.assertContains(response, 'VID-DRAFT-2')

    def test_room_quick_add_saves_room_and_selects_it_for_draft(self):
        wizard_id = self.begin_draft()
        response = self.client.post(
            reverse('inventory:room_quick_add', args=(wizard_id,)),
            {
                'name': 'Audio Rack',
                'room_number': '102',
                'priority': RoomPriority.NORMAL,
                'description': 'Rack equipment area',
            },
        )

        new_room = Room.objects.get(name='Audio Rack')
        draft = self.client.session['inventory_wizard_drafts'][wizard_id]
        self.assertEqual(response.status_code, 302)
        self.assertEqual(draft['room'], str(new_room.pk))
        self.assertFalse(Asset.objects.exists())

    def test_edit_does_not_change_asset_before_final_confirmation(self):
        asset = Asset.objects.create(
            inventory_number='VID-0004',
            name='Old Camera Name',
            category=AssetCategory.VIDEO,
            room=self.room,
        )
        response = self.client.get(reverse('inventory:asset_wizard_edit', args=(asset.pk,)))
        self.assertEqual(response.status_code, 302)
        wizard_id = next(iter(self.client.session['inventory_wizard_drafts']))

        self.client.post(
            reverse('inventory:asset_wizard_step', args=(wizard_id, 1)),
            {'room': str(self.room.pk), 'action': 'next'},
        )
        self.client.post(
            reverse('inventory:asset_wizard_step', args=(wizard_id, 2)),
            {'category': AssetCategory.VIDEO, 'action': 'next'},
        )
        self.client.post(
            reverse('inventory:asset_wizard_step', args=(wizard_id, 3)),
            {
                'inventory_number': 'VID-0004',
                'name': 'Updated Camera Name',
                'manufacturer': '',
                'model_number': '',
                'serial_number': '',
                'physical_location': '',
                'action': 'next',
            },
        )
        self.client.post(
            reverse('inventory:asset_wizard_step', args=(wizard_id, 4)),
            {'action': 'next'},
        )
        self.client.post(
            reverse('inventory:asset_wizard_step', args=(wizard_id, 5)),
            {
                'ownership': AssetOwnership.UNKNOWN,
                'condition': AssetCondition.UNKNOWN,
                'status': AssetStatus.UNKNOWN,
                'responsible_party': '',
                'action': 'next',
            },
        )
        review_url = reverse('inventory:asset_wizard_review', args=(wizard_id,))
        asset.refresh_from_db()
        self.assertEqual(asset.name, 'Old Camera Name')

        self.client.post(review_url, {'action': 'save'})
        asset.refresh_from_db()
        self.assertEqual(asset.name, 'Updated Camera Name')

    def test_wizard_requires_sign_in(self):
        self.client.logout()
        response = self.client.get(reverse('inventory:asset_wizard_start'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    @override_settings(ROOT_URLCONF='config.training_urls', TRAINING_ONLY=True)
    def test_training_only_profile_is_open_and_hides_management_routes(self):
        self.client.logout()

        response = self.client.get('/training/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No sign-in needed.')
        self.assertNotContains(response, 'Admin sign in')
        self.assertNotContains(response, 'Technology management')
        self.assertEqual(self.client.get('/inventory/').status_code, 404)
        self.assertEqual(self.client.get('/login/').status_code, 404)
        self.assertEqual(self.client.get('/admin/').status_code, 404)
