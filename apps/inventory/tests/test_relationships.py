"""Coverage for building connections, dependencies, compatibility, and impact."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import Resolver404, reverse, resolve

from apps.inventory.models import (
    Asset, AssetCategory, AssetConnection, AssetDependency, AssetSpecification,
    CompatibilityVerification, ReplacementCompatibilityReview, Room,
    SoftwareInstallation,
)
from apps.inventory.services.relationships import relationship_impact, replacement_impact, validate_dependency


class RelationshipWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='relationship-admin', password='test-password')
        self.client.force_login(self.user)
        self.room = Room.objects.create(name='Cultural Hall')
        self.camera = Asset.objects.create(inventory_number='VID-001', name='PTZ camera', category=AssetCategory.VIDEO, room=self.room)
        self.transmitter = Asset.objects.create(inventory_number='VID-002', name='J5 transmitter', category=AssetCategory.VIDEO)
        self.receiver = Asset.objects.create(inventory_number='VID-003', name='J5 receiver', category=AssetCategory.VIDEO)
        self.host = Asset.objects.create(inventory_number='COMP-001', name='Broadcast host', category=AssetCategory.COMPUTING)

    def test_connection_create_edit_unknown_status_and_duplicate_validation(self):
        add_url = reverse('inventory:relationship_create')
        payload = {'source': self.camera.pk, 'destination': self.transmitter.pk, 'connection_type': 'video', 'connection_medium': 'other', 'interface': '', 'signal_description': '', 'compatibility': 'unknown', 'is_required': True, 'last_verified': '', 'verification_notes': '', 'notes': ''}
        response = self.client.post(add_url, payload)
        connection = AssetConnection.objects.get(source=self.camera, destination=self.transmitter)
        self.assertEqual(connection.compatibility, 'unknown')
        self.assertEqual(response.status_code, 302)
        response = self.client.post(reverse('inventory:relationship_edit', args=('connection', connection.pk)), {**payload, 'source': self.camera.pk, 'destination': self.transmitter.pk, 'compatibility': 'unverified'})
        connection.refresh_from_db()
        self.assertEqual(connection.compatibility, 'unverified')
        duplicate = self.client.post(add_url, payload)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(AssetConnection.objects.count(), 1)

    def test_connection_rejects_self_relationship(self):
        connection = AssetConnection(source=self.camera, destination=self.camera)
        with self.assertRaises(ValidationError):
            connection.full_clean()

    def test_required_optional_and_external_service_dependencies(self):
        required = AssetDependency.objects.create(dependent_asset=self.host, required_asset=self.receiver, description='Camera signal receiver', is_required=True)
        optional = AssetDependency.objects.create(dependent_asset=self.host, external_service_name='OBS Studio workflow', dependency_type='service', description='Optional production workflow', is_required=False)
        self.assertTrue(required.is_required)
        self.assertFalse(optional.is_required)
        self.assertIsNone(optional.required_asset)
        self.assertEqual(optional.external_service_name, 'OBS Studio workflow')

    def test_dependency_can_reuse_installed_software_as_requirement(self):
        obs = SoftwareInstallation.objects.create(host_asset=self.host, name='OBS Studio', role='video_production', is_required=False)
        dependency = AssetDependency.objects.create(dependent_asset=self.host, required_software=obs, dependency_type='software', description='Optional virtual camera workflow', is_required=False)
        self.assertEqual(dependency.required_software, obs)
        self.assertEqual(relationship_impact(self.host)['requirements'], [dependency])

    def test_dependency_form_blocks_self_and_circular_path(self):
        AssetDependency.objects.create(dependent_asset=self.host, required_asset=self.receiver, description='Receiver input')
        AssetDependency.objects.create(dependent_asset=self.receiver, required_asset=self.transmitter, description='Wireless receiver')
        with self.assertRaises(ValidationError):
            validate_dependency(self.transmitter.pk, self.host.pk)
        payload = {'dependent_asset': self.transmitter.pk, 'required_asset': self.host.pk, 'external_service_name': '', 'dependency_type': 'equipment', 'is_required': True, 'description': 'Would close cycle', 'failure_impact': '', 'verification_status': 'unknown', 'last_verified': '', 'notes': ''}
        response = self.client.post(reverse('inventory:relationship_create', args=('dependency',)), payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AssetDependency.objects.count(), 2)

    def test_existing_legacy_cycles_are_reported_without_deleting_records(self):
        first = AssetDependency.objects.create(dependent_asset=self.host, required_asset=self.receiver, description='Receiver')
        second = AssetDependency.objects.create(dependent_asset=self.receiver, required_asset=self.host, description='Host')
        from apps.inventory.services.relationships import existing_dependency_cycles
        self.assertTrue(existing_dependency_cycles())
        self.assertTrue(AssetDependency.objects.filter(pk__in=(first.pk, second.pk)).exists())

    def test_structured_spec_unknown_and_verification_evidence_history(self):
        spec = AssetSpecification.objects.create(asset=self.camera, category='video', name='Supported resolution', value='', verification_status='unknown')
        self.assertEqual(spec.value, '')
        verification = CompatibilityVerification.objects.create(asset=self.camera, related_asset=self.transmitter, requirement='Camera output to transmitter input', outcome='unknown', method='other')
        self.assertEqual(verification.outcome, 'unknown')
        self.assertEqual(CompatibilityVerification.objects.filter(asset=self.camera).count(), 1)

    def test_dependency_impact_traverses_reverse_and_multiple_levels_without_duplication(self):
        AssetDependency.objects.create(dependent_asset=self.host, required_asset=self.receiver, description='Receiver USB connection')
        AssetDependency.objects.create(dependent_asset=self.receiver, required_asset=self.transmitter, description='Wireless link')
        AssetDependency.objects.create(dependent_asset=self.transmitter, required_asset=self.camera, description='Camera feed')
        summary = relationship_impact(self.camera)
        self.assertEqual(len(summary['transitive_impact']), 3)
        impact = replacement_impact(self.receiver)
        self.assertEqual([item.dependent_asset for item in impact['transitive_impact']], [self.host])

    def test_replacement_review_is_not_an_inventory_asset_and_shows_impact(self):
        AssetConnection.objects.create(source=self.camera, destination=self.transmitter, connection_type='video', connection_medium='other', interface='HDMI', compatibility='unknown')
        AssetDependency.objects.create(dependent_asset=self.host, required_asset=self.receiver, description='Broadcast input')
        response = self.client.post(reverse('inventory:replacement_review_edit', args=(self.receiver.pk,)), {'proposed_name': 'Candidate receiver', 'proposed_manufacturer': 'Example', 'proposed_model': 'Candidate-1', 'requirements': 'USB interface required', 'status': 'testing', 'limitations': '', 'notes': ''})
        review = ReplacementCompatibilityReview.objects.get(asset=self.receiver)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(review.status, 'testing')
        self.assertFalse(Asset.objects.filter(name='Candidate receiver').exists())
        impact_response = self.client.get(reverse('inventory:replacement_review', args=(self.receiver.pk,)))
        self.assertContains(impact_response, 'Broadcast host')

    def test_asset_detail_and_room_include_cross_room_relationships(self):
        AssetConnection.objects.create(source=self.camera, destination=self.transmitter, connection_type='video', connection_medium='other')
        AssetDependency.objects.create(dependent_asset=self.host, required_asset=self.camera, description='Video workflow')
        detail = self.client.get(reverse('inventory:asset_detail', args=(self.camera.pk,)))
        self.assertContains(detail, 'Connections &amp; compatibility')
        room_detail = self.client.get(reverse('inventory:room_detail', args=(self.room.pk,)))
        self.assertContains(room_detail, 'Broadcast host')
        self.assertContains(room_detail, 'Unassigned')

    def test_index_filters_connections_by_room_and_lists_missing_specs(self):
        AssetConnection.objects.create(source=self.camera, destination=self.transmitter, connection_type='video', connection_medium='other')
        response = self.client.get(reverse('inventory:relationship_index'), {'room': self.room.pk})
        self.assertContains(response, 'PTZ camera')
        self.assertContains(response, 'J5 transmitter')
        self.assertContains(response, 'Broadcast host')

    def test_authentication_and_training_only_route_isolation(self):
        self.client.logout()
        response = self.client.get(reverse('inventory:relationship_index'))
        self.assertEqual(response.status_code, 302)
        with override_settings(ROOT_URLCONF='config.training_urls'):
            with self.assertRaises(Resolver404):
                resolve('/inventory/relationships/', urlconf='config.training_urls')

