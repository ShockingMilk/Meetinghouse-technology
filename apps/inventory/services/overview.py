"""Read-only summaries used by the maintenance and lifecycle workspace."""

from django.utils import timezone

from apps.inventory.models import Asset, MaintenanceRecord, MaintenanceSchedule

from .lifecycle import lifecycle_warnings, replacement_review_needed
from .maintenance import follow_up_state, schedule_state, with_latest_completion


def maintenance_summary():
    """Build dashboard indicators from current records without cached flags."""
    today = timezone.localdate()
    schedules = with_latest_completion(MaintenanceSchedule.objects.select_related('asset', 'asset__room'))
    schedule_items = []
    for schedule in schedules:
        state = schedule_state(schedule, as_of=today)
        if state['state'] in ('overdue', 'due_soon'):
            schedule_items.append({'schedule': schedule, **state})

    followups = list(
        MaintenanceRecord.objects.filter(follow_up_required=True, resolved_at__isnull=True)
        .select_related('asset', 'asset__room', 'schedule')
        .order_by('follow_up_date', '-performed_at')
    )
    for record in followups:
        record.follow_up_state = follow_up_state(record, as_of=today)

    assets = Asset.objects.select_related('room').all()
    lifecycle_items = []
    missing_lifecycle = []
    replacements = []
    count_data = {'warranty_approaching': 0, 'warranty_expired': 0,
                  'security_approaching': 0, 'security_expired': 0,
                  'end_of_life_approaching': 0, 'end_of_life_passed': 0}
    for asset in assets:
        lifecycle = lifecycle_warnings(asset, as_of=today)
        if lifecycle['needs_review']:
            lifecycle_items.append({'asset': asset, **lifecycle})
        if lifecycle['missing_fields']:
            missing_lifecycle.append(asset)
        if replacement_review_needed(asset):
            replacements.append(asset)
        for item in lifecycle['warnings']:
            count_key = {
                ('Warranty', 'approaching'): 'warranty_approaching',
                ('Warranty', 'expired'): 'warranty_expired',
                ('Security support', 'approaching'): 'security_approaching',
                ('Security support', 'expired'): 'security_expired',
                ('End of life', 'approaching'): 'end_of_life_approaching',
                ('End of life', 'expired'): 'end_of_life_passed',
            }.get((item['key'], item['state']))
            if count_key:
                count_data[count_key] += 1

    return {
        'today': today,
        'schedule_items': schedule_items,
        'due_soon_schedules': [item for item in schedule_items if item['state'] == 'due_soon'],
        'overdue_schedules': [item for item in schedule_items if item['state'] == 'overdue'],
        'open_followups': followups,
        'overdue_followups': [item for item in followups if item.follow_up_state == 'overdue'],
        'lifecycle_items': lifecycle_items,
        'missing_lifecycle_assets': missing_lifecycle,
        'replacement_assets': replacements,
        'lifecycle_counts': count_data,
        'asset_count': assets.count(),
    }
