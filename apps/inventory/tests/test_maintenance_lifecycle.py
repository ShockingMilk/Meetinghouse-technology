"""Integrated tests for maintenance records, schedules, and lifecycle views."""

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.inventory.models import (
    Asset,
    AssetCategory,
    AssetCondition,
    AssetOwnership,
    AssetStatus,
    MaintenanceActivityType,
    MaintenanceRecord,
    MaintenanceResult,
    MaintenanceSchedule,
    Room,
    RoomPriority,
    ReplacementRecommendation,
    RoomAssessment,
)
from apps.inventory.services.lifecycle import lifecycle_warnings
from apps.inventory.services.maintenance import (
    add_months,
    default_interval_months,
    follow_up_state,
    next_due_date,
    schedule_state,
)


def make_record(asset, **values):
    return MaintenanceRecord.objects.create(
        asset=asset,
        performed_at=values.pop('performed_at', timezone.now()),
        performed_by=values.pop('performed_by', 'Technology specialist'),
        maintenance_type=values.pop('maintenance_type', MaintenanceActivityType.INSPECTION),
        result=values.pop('result', MaintenanceResult.WORKING),
        description=values.pop('description', 'Routine equipment check.'),
        action_taken=values.pop('action_taken', 'Tested equipment.'),
        **values,
    )


class MaintenanceServiceTests(TestCase):
    def setUp(self):
        self.asset = Asset.objects.create(inventory_number='VID-001', name='PTZ camera', category=AssetCategory.VIDEO)

    def test_add_months_clamps_end_of_month_and_year(self):
        self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))
        self.assertEqual(add_months(date(2026, 12, 31), 3), date(2027, 3, 31))

    def test_due_date_uses_baseline_then_latest_linked_completion(self):
        schedule = MaintenanceSchedule.objects.create(asset=self.asset, name='Quarterly inspection', interval_months=3, starts_on=date(2026, 1, 31))
        self.assertEqual(next_due_date(schedule), date(2026, 1, 31))
        make_record(self.asset, schedule=schedule, performed_at=timezone.make_aware(datetime(2026, 2, 28, 12, 0)))
        self.assertEqual(next_due_date(schedule), date(2026, 5, 28))

    def test_maintenance_history_is_newest_first(self):
        older = make_record(self.asset, performed_at=timezone.make_aware(datetime(2026, 1, 1, 12, 0)))
        newer = make_record(self.asset, performed_at=timezone.make_aware(datetime(2026, 2, 1, 12, 0)))
        self.assertEqual(list(self.asset.maintenance_records.all()), [newer, older])

    @override_settings(MAINTENANCE_DUE_SOON_DAYS=30)
    def test_due_states_include_overdue_due_soon_upcoming_and_disabled(self):
        today = date(2026, 11, 2)
        overdue = MaintenanceSchedule.objects.create(asset=self.asset, name='Late', interval_months=3, starts_on=today - timedelta(days=1))
        soon = MaintenanceSchedule.objects.create(asset=self.asset, name='Soon', interval_months=3, starts_on=today + timedelta(days=10))
        later = MaintenanceSchedule.objects.create(asset=self.asset, name='Later', interval_months=3, starts_on=today + timedelta(days=60))
        disabled = MaintenanceSchedule.objects.create(asset=self.asset, name='Disabled', interval_months=3, starts_on=today, enabled=False)
        self.assertEqual(schedule_state(overdue, as_of=today)['state'], 'overdue')
        self.assertEqual(schedule_state(soon, as_of=today)['state'], 'due_soon')
        self.assertEqual(schedule_state(later, as_of=today)['state'], 'upcoming')
        self.assertEqual(schedule_state(disabled, as_of=today)['state'], 'disabled')

    @override_settings(MAINTENANCE_CATEGORY_INTERVALS_MONTHS={'video': 3, 'portable_or_stored': 6})
    def test_category_interval_is_only_a_suggestion_and_stored_uses_six_months(self):
        self.assertEqual(default_interval_months(self.asset), 3)
        self.asset.status = AssetStatus.STORED
        self.assertEqual(default_interval_months(self.asset), 6)

    def test_follow_up_stays_open_after_due_date_until_resolved(self):
        record = make_record(self.asset, follow_up_required=True, follow_up_notes='Replace the loose cable.', follow_up_date=date(2026, 10, 1))
        self.assertEqual(follow_up_state(record, as_of=date(2026, 11, 2)), 'overdue')
        record.resolved_at = date(2026, 11, 1)
        self.assertEqual(follow_up_state(record, as_of=date(2026, 11, 2)), 'resolved')

    @override_settings(LIFECYCLE_WARNING_DAYS=180)
    def test_missing_lifecycle_dates_are_unknown_and_dates_are_classified(self):
        today = date(2026, 11, 2)
        self.asset.warranty_end_date = today + timedelta(days=100)
        self.asset.security_support_end_date = today - timedelta(days=1)
        summary = lifecycle_warnings(self.asset, as_of=today)
        states = {item['field']: item['state'] for item in summary['warnings']}
        self.assertEqual(states['warranty_end_date'], 'approaching')
        self.assertEqual(states['security_support_end_date'], 'expired')
        self.assertEqual(states['end_of_life_date'], 'unknown')
        self.assertIn('installation_date', summary['missing_fields'])


class MaintenanceWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='maintenance-admin', password='secret-password')
        self.client.force_login(self.user)
        self.room = Room.objects.create(name='Chapel', room_number='101', priority=RoomPriority.NORMAL)
        self.asset = Asset.objects.create(
            inventory_number='AUDIO-100',
            name='Chapel sound system',
            category=AssetCategory.AUDIO,
            room=self.room,
            ownership=AssetOwnership.LOCAL,
            condition=AssetCondition.GOOD,
            status=AssetStatus.ACTIVE,
        )

    def record_payload(self, **overrides):
        payload = {
            'asset': str(self.asset.pk),
            'schedule': '',
            'performed_at': '2026-11-02T10:00',
            'performed_by': 'Technology specialist',
            'maintenance_type': MaintenanceActivityType.INSPECTION,
            'result': MaintenanceResult.WORKING,
            'description': 'Checked the room sound system.',
            'action_taken': 'Played a test signal.',
            'materials_used': '',
            'estimated_cost': '',
            'actual_cost': '',
            'follow_up_required': '',
            'follow_up_notes': '',
            'follow_up_date': '',
        }
        payload.update(overrides)
        return payload

    def test_record_workflow_does_not_change_asset_status_or_condition(self):
        response = self.client.post(reverse('inventory:maintenance_record_create_for_asset', args=(self.asset.pk,)), self.record_payload(result=MaintenanceResult.ATTENTION))
        record = MaintenanceRecord.objects.get()
        self.assertRedirects(response, reverse('inventory:maintenance_record_detail', args=(record.pk,)))
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, AssetStatus.ACTIVE)
        self.assertEqual(self.asset.condition, AssetCondition.GOOD)
        self.assertEqual(record.result, MaintenanceResult.ATTENTION)

    def test_follow_up_is_open_until_resolution_is_explicit(self):
        today = timezone.localdate()
        record = make_record(self.asset, follow_up_required=True, follow_up_notes='Verify the amplifier input.', follow_up_date=today - timedelta(days=1))
        detail_url = reverse('inventory:maintenance_record_detail', args=(record.pk,))
        self.assertContains(self.client.get(detail_url), 'Overdue')
        response = self.client.post(detail_url, {'action': 'resolve', 'resolved_at': today.isoformat(), 'resolution_notes': 'Retested and verified.'})
        self.assertRedirects(response, detail_url)
        record.refresh_from_db()
        self.assertEqual(record.resolved_at, today)
        self.assertEqual(record.resolution_notes, 'Retested and verified.')

    def test_schedule_creation_does_not_create_maintenance_records(self):
        response = self.client.post(reverse('inventory:maintenance_schedule_create_for_asset', args=(self.asset.pk,)), {
            'asset': str(self.asset.pk), 'name': 'Semiannual sound check', 'description': '',
            'activity_type': MaintenanceActivityType.INSPECTION, 'interval_months': '6',
            'starts_on': '2026-11-02', 'enabled': 'on', 'notes': '',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MaintenanceSchedule.objects.count(), 1)
        self.assertFalse(MaintenanceRecord.objects.exists())

    def test_record_edit_updates_history_without_changing_asset(self):
        record = make_record(self.asset)
        response = self.client.post(reverse('inventory:maintenance_record_edit', args=(record.pk,)), self.record_payload(description='Updated inspection note.'))
        self.assertRedirects(response, reverse('inventory:maintenance_record_detail', args=(record.pk,)))
        record.refresh_from_db()
        self.asset.refresh_from_db()
        self.assertEqual(record.description, 'Updated inspection note.')
        self.assertEqual(self.asset.status, AssetStatus.ACTIVE)

    def test_fmg_schedule_requires_authorization_acknowledgement(self):
        self.asset.ownership = AssetOwnership.FMG
        self.asset.save(update_fields=('ownership',))
        payload = {
            'asset': str(self.asset.pk), 'name': 'Observation review', 'description': '',
            'activity_type': MaintenanceActivityType.INSPECTION, 'interval_months': '6',
            'starts_on': '2026-11-02', 'enabled': 'on', 'notes': '',
        }
        response = self.client.post(reverse('inventory:maintenance_schedule_create_for_asset', args=(self.asset.pk,)), payload)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MaintenanceSchedule.objects.exists())
        payload['authorization_acknowledged'] = 'on'
        response = self.client.post(reverse('inventory:maintenance_schedule_create_for_asset', args=(self.asset.pk,)), payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MaintenanceSchedule.objects.count(), 1)

    def test_asset_detail_and_room_detail_include_maintenance_lifecycle_without_losing_assessments(self):
        make_record(self.asset)
        schedule = MaintenanceSchedule.objects.create(asset=self.asset, name='Audio check', interval_months=6, starts_on=timezone.localdate())
        RoomAssessment.objects.create(room=self.room)
        detail = self.client.get(reverse('inventory:asset_detail', args=(self.asset.pk,)))
        self.assertContains(detail, 'Support and replacement review')
        self.assertContains(detail, 'Audio check')
        room_detail = self.client.get(reverse('inventory:room_detail', args=(self.room.pk,)))
        self.assertContains(room_detail, 'Assessment history')
        self.assertContains(room_detail, 'Maintenance and lifecycle by asset')
        self.assertContains(room_detail, 'Audio check')

    def test_maintenance_dashboard_handles_empty_inventory(self):
        Asset.objects.all().delete()
        response = self.client.get(reverse('inventory:maintenance_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '0')
        self.assertContains(response, 'No unresolved maintenance follow-ups')

    def test_reports_filter_by_room_and_export_csv_safely(self):
        record = make_record(self.asset, performed_by='=1+1', description='Routine check')
        response = self.client.get(reverse('inventory:maintenance_reports'), {'report': 'history', 'room': str(self.room.pk), 'csv': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertContains(response, "'=1+1")
        self.assertContains(response, 'AUDIO-100')

    def test_replacement_planning_uses_recommendation_without_changing_status(self):
        self.asset.replacement_recommendation = ReplacementRecommendation.PRIORITY
        self.asset.replacement_estimate = Decimal('1200.00')
        self.asset.save(update_fields=('replacement_recommendation', 'replacement_estimate'))
        response = self.client.get(reverse('inventory:maintenance_reports'), {'report': 'replacement'})
        self.assertContains(response, 'Replace as priority')
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, AssetStatus.ACTIVE)

    def test_maintenance_pages_require_sign_in(self):
        self.client.logout()
        for route in (
            reverse('inventory:maintenance_dashboard'),
            reverse('inventory:maintenance_reports'),
            reverse('inventory:maintenance_record_create'),
        ):
            response = self.client.get(route)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login/', response.url)

    @override_settings(ROOT_URLCONF='config.training_urls', TRAINING_ONLY=True)
    def test_training_only_deployment_does_not_expose_maintenance(self):
        self.client.logout()
        self.assertEqual(self.client.get('/inventory/maintenance/').status_code, 404)
