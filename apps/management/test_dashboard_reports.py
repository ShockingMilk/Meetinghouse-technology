"""Regression tests for the calculated dashboard and filtered reporting."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import Resolver404, reverse, resolve
from django.utils import timezone

from apps.inventory.models import (
    Asset, AssetCondition, AssetConnection, AssetDependency, AssetOwnership,
    AssetStatus, CompatibilityVerification, MaintenanceActivityType,
    MaintenanceRecord, MaintenanceResult, MaintenanceSchedule, Room,
    RoomAssessment, RoomPriority,
    ReplacementCompatibilityReview,
)
from apps.management.reporting import csv_safe
from apps.management.services import building_dashboard
from apps.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationPriority,
    NotificationStatus,
)


class BuildingDashboardTests(TestCase):
    def setUp(self):
        self.room = Room.objects.create(name='Chapel', room_number='101', priority=RoomPriority.NORMAL)
        self.asset = Asset.objects.create(
            inventory_number='A-001', name='Sound system', room=self.room,
            category='audio', ownership=AssetOwnership.LOCAL,
            status=AssetStatus.ACTIVE, condition=AssetCondition.FAILED,
        )

    def test_counts_exclude_retired_but_include_unassigned_active_inventory(self):
        Asset.objects.create(inventory_number='A-002', name='Stored mic', status=AssetStatus.STORED)
        Asset.objects.create(inventory_number='A-003', name='Retired amp', status=AssetStatus.RETIRED)
        summary = building_dashboard()
        self.assertEqual(summary['active_asset_count'], 1)
        self.assertEqual(summary['asset_count'], 2)
        self.assertEqual(summary['stored_count'], 1)
        self.assertEqual(summary['unassigned_count'], 1)
        self.assertEqual(summary['under_repair_count'], 0)
        self.assertIn('Equipment reported failed or offline', [item['label'] for item in summary['attention_items']])

    def test_room_coverage_distinguishes_unassessed_unknown_and_needs_review(self):
        unknown = Room.objects.create(name='Cultural hall', priority=RoomPriority.NORMAL)
        Room.objects.create(name='Classroom', priority=RoomPriority.NORMAL)
        RoomAssessment.objects.create(room=self.room, overall_status='needs_review')
        RoomAssessment.objects.create(room=unknown, overall_status='unknown')
        summary = building_dashboard()
        self.assertEqual(summary['room_count'], 3)
        self.assertEqual(summary['assessed_room_count'], 1)
        self.assertEqual(summary['unassessed_room_count'], 1)
        self.assertEqual(summary['unknown_room_count'], 1)
        self.assertEqual(summary['coverage_percent'], 33)
        by_name = {room.name: room.assessment_state for room in summary['rooms']}
        self.assertEqual(by_name['Chapel'], 'needs_review')
        self.assertEqual(by_name['Cultural hall'], 'unknown')
        self.assertEqual(by_name['Classroom'], 'not_assessed')

    def test_empty_building_has_zero_coverage_and_empty_states(self):
        Asset.objects.all().delete()
        Room.objects.all().delete()
        summary = building_dashboard()
        self.assertEqual(summary['asset_count'], 0)
        self.assertEqual(summary['coverage_percent'], 0)
        self.assertEqual(summary['attention_items'], [])

    def test_overdue_inspection_and_unresolved_followup_are_counted(self):
        yesterday = timezone.localdate() - timedelta(days=2)
        MaintenanceSchedule.objects.create(asset=self.asset, name='Quarterly test', interval_months=3, starts_on=yesterday)
        MaintenanceRecord.objects.create(
            asset=self.asset, performed_at=timezone.now(), performed_by='Specialist',
            maintenance_type=MaintenanceActivityType.TROUBLESHOOTING,
            description='Input issue', result=MaintenanceResult.ATTENTION,
            follow_up_required=True, follow_up_notes='Replace cable', follow_up_date=yesterday,
        )
        summary = building_dashboard()
        self.assertEqual(summary['overdue_inspection_count'], 1)
        self.assertEqual(summary['open_followup_count'], 1)
        self.assertEqual(summary['overdue_followup_count'], 1)

    @override_settings(LIFECYCLE_WARNING_DAYS=90)
    def test_lifecycle_warning_is_calculated_without_marking_equipment_failed(self):
        self.asset.condition = AssetCondition.GOOD
        self.asset.warranty_end_date = timezone.localdate() + timedelta(days=45)
        self.asset.save(update_fields=('condition', 'warranty_end_date'))
        summary = building_dashboard()
        warning = next(item for item in summary['attention_items'] if item['label'] == 'Warranty expiration approaching')
        self.assertEqual(warning['priority'], 'medium')
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.condition, AssetCondition.GOOD)

    def test_incompatible_records_and_pending_replacement_are_prioritized(self):
        other = Asset.objects.create(inventory_number='A-004', name='Display')
        AssetConnection.objects.create(source=self.asset, destination=other, compatibility='incompatible', is_required=False)
        AssetDependency.objects.create(
            dependent_asset=self.asset, external_service_name='Streaming service',
            dependency_type='service', is_required=False, description='Live-stream service',
            verification_status='incompatible',
        )
        CompatibilityVerification.objects.create(asset=self.asset, requirement='Audio routing', outcome='incompatible')
        ReplacementCompatibilityReview.objects.create(asset=self.asset, status='research')
        summary = building_dashboard()
        self.assertEqual(summary['incompatible_count'], 3)
        self.assertIn('Replacement review awaiting a decision', [item['label'] for item in summary['attention_items']])
        connection_alert = next(item for item in summary['attention_items'] if item['label'] == 'Incompatible equipment connection')
        self.assertEqual(connection_alert['priority'], 'medium')

class NotificationDashboardViewTests(TestCase):
    """Verify operational notifications on the authenticated dashboard."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='notification-user',
            password='safe-password',
        )
        self.content_type = ContentType.objects.get_for_model(
            get_user_model(),
        )

    def create_notification(
        self,
        title,
        *,
        priority=NotificationPriority.MEDIUM,
        status=NotificationStatus.OPEN,
        snoozed_until=None,
    ):
        """Create a notification for dashboard integration tests."""
        return Notification.objects.create(
            title=title,
            description=f'Test notification: {title}',
            category=NotificationCategory.ASSET_OFFLINE,
            priority=priority,
            status=status,
            source_content_type=self.content_type,
            source_object_id='1',
            source_summary='Dashboard test source',
            deduplication_key=f'dashboard-test-{title.lower().replace(" ", "-")}',
            snoozed_until=snoozed_until,
        )

    def test_dashboard_requires_authentication(self):
        """Unauthenticated visitors cannot access the management dashboard."""
        response = self.client.get(reverse('management:dashboard'))

        self.assertEqual(response.status_code, 302)

    def test_dashboard_displays_active_snoozed_and_excludes_resolved(self):
        """The dashboard separates snoozed notifications from active ones."""

        self.create_notification(
            'Active offline equipment',
            priority=NotificationPriority.HIGH,
        )
        self.create_notification(
            'Acknowledged equipment issue',
            status=NotificationStatus.ACKNOWLEDGED,
        )
        self.create_notification(
            'Snoozed equipment issue',
            snoozed_until=timezone.now() + timedelta(hours=2),
        )
        self.create_notification(
            'Resolved equipment issue',
            status=NotificationStatus.RESOLVED,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('management:dashboard'))

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'Operational notifications')
        self.assertContains(response, 'Active offline equipment')
        self.assertContains(response, 'Acknowledged equipment issue')
        self.assertContains(response, 'Snoozed notifications (1)')
        self.assertContains(response, 'Snoozed equipment issue')

        self.assertNotContains(response, 'Resolved equipment issue')

    def test_dashboard_notification_counts_match_display_limits(self):
        """Dashboard counts cover all records even when lists are limited."""
        for number in range(9):
            self.create_notification(f'Active issue {number:02d}')

        from datetime import timedelta

        from django.utils import timezone

        self.create_notification(
            'Snoozed issue',
            snoozed_until=timezone.now() + timedelta(hours=2),
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('management:dashboard'))

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'Showing 8 of 9')
        self.assertContains(response, 'actionable notifications.')
        self.assertContains(response, 'Snoozed notifications (1)')

        self.assertContains(response, 'Active issue 08')
        self.assertContains(response, 'Active issue 01')
        self.assertNotContains(response, 'Active issue 00')

        self.assertContains(response, 'Snoozed issue')


class BuildingReportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='report-user', password='safe-password')
        self.room = Room.objects.create(name='Chapel', room_number='101', priority=RoomPriority.NORMAL)
        self.asset = Asset.objects.create(inventory_number='A-101', name='=Formula', room=self.room, category='audio', ownership=AssetOwnership.LOCAL)

    def test_reports_require_authentication(self):
        response = self.client.get(reverse('management:reports'))
        self.assertEqual(response.status_code, 302)

    def test_filtered_inventory_report_prints_and_exports_same_subset(self):
        Asset.objects.create(inventory_number='A-102', name='Other', category='video')
        self.client.force_login(self.user)
        url = reverse('management:reports')
        params = {'report': 'inventory', 'room': str(self.room.pk), 'category': 'audio'}
        page = self.client.get(url, params)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'A-101')
        self.assertNotContains(page, 'A-102')
        self.assertContains(page, 'Applied filters')
        self.assertContains(page, 'Download CSV')
        exported = self.client.get(url, {**params, 'csv': '1'})
        self.assertEqual(exported.status_code, 200)
        self.assertIn("'=Formula", exported.content.decode('utf-8'))
        self.assertNotIn('A-102', exported.content.decode('utf-8'))

    def test_report_input_validation_and_pagination(self):
        for number in range(60):
            Asset.objects.create(inventory_number=f'X-{number:03}', name='Additional')
        self.client.force_login(self.user)
        response = self.client.get(reverse('management:reports'), {'report': 'inventory', 'room': 'invalid'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select a valid choice')
        first_page = self.client.get(reverse('management:reports'), {'report': 'inventory'})
        self.assertContains(first_page, 'Page 1 of 2')
        second_page = self.client.get(reverse('management:reports'), {'report': 'inventory', 'page': '2'})
        self.assertContains(second_page, 'Page 2 of 2')

    def test_compatibility_status_reports_include_connections_and_dependencies(self):
        other = Asset.objects.create(inventory_number='A-102', name='Display', room=self.room)
        AssetConnection.objects.create(source=self.asset, destination=other, compatibility='unknown')
        AssetDependency.objects.create(
            dependent_asset=self.asset, external_service_name='Streaming service',
            dependency_type='service', description='Stream', verification_status='needs_review',
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('management:reports'), {'report': 'unverified'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Connection')
        self.assertContains(response, 'Dependency')

    def test_training_only_urlconf_does_not_resolve_management_reports(self):
        with override_settings(ROOT_URLCONF='config.training_urls'):
            with self.assertRaises(Resolver404):
                resolve('/reports/')

    def test_csv_formula_prefixes_are_neutralized(self):
        self.assertEqual(csv_safe('=1+1'), "'=1+1")
        self.assertEqual(csv_safe('Normal text'), 'Normal text')
