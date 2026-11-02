"""Reusable maintenance schedule and follow-up calculations."""

import calendar
from datetime import date, timedelta

from django.conf import settings
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from apps.inventory.models import MaintenanceRecord


def add_months(anchor: date, months: int) -> date:
    """Add calendar months without relying on a third-party date library."""
    month_index = anchor.month - 1 + months
    year = anchor.year + month_index // 12
    month = month_index % 12 + 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def last_completed_date(schedule):
    """Return the most recent associated completion date, if any."""
    if hasattr(schedule, '_latest_completion_at'):
        completed_at = schedule._latest_completion_at
        return timezone.localtime(completed_at).date() if completed_at else None
    records = schedule.completed_records.all()
    performed_dates = [timezone.localtime(record.performed_at).date() for record in records]
    return max(performed_dates) if performed_dates else None


def with_latest_completion(queryset):
    """Annotate each schedule with only its latest recorded completion time."""
    latest = MaintenanceRecord.objects.filter(schedule_id=OuterRef('pk')).order_by('-performed_at', '-created_at')
    return queryset.annotate(_latest_completion_at=Subquery(latest.values('performed_at')[:1]))


def next_due_date(schedule):
    """Calculate a schedule's next due date from its baseline or completion."""
    completed = last_completed_date(schedule)
    if completed is None:
        return schedule.starts_on
    if completed < schedule.starts_on:
        return schedule.starts_on
    return add_months(completed, schedule.interval_months)


def schedule_state(schedule, *, as_of=None):
    """Return enabled/upcoming/due-soon/overdue state with its due date."""
    as_of = as_of or timezone.localdate()
    if not schedule.enabled:
        return {'state': 'disabled', 'due_date': None}
    due = next_due_date(schedule)
    if due < as_of:
        state = 'overdue'
    elif due <= as_of + timedelta(days=settings.MAINTENANCE_DUE_SOON_DAYS):
        state = 'due_soon'
    else:
        state = 'upcoming'
    return {'state': state, 'due_date': due}


def default_interval_months(asset):
    """Suggest a local planning interval without creating a schedule."""
    if asset.status == 'stored':
        return settings.MAINTENANCE_CATEGORY_INTERVALS_MONTHS['portable_or_stored']
    return settings.MAINTENANCE_CATEGORY_INTERVALS_MONTHS.get(asset.category, 6)


def default_schedule_suggestion(asset):
    """Return editable form suggestions; this does not create a schedule."""
    if asset.status == 'stored':
        return {
            'name': 'Portable or stored equipment check',
            'description': 'Local planning suggestion: check before use and at the selected recurring interval.',
        }
    suggestions = {
        'audio': ('Audio equipment inspection', 'Local planning suggestion; review every six months.'),
        'assistive_listening': ('Assistive listening check', 'Local planning suggestion; review every three months.'),
        'video': ('Video equipment inspection', 'Local planning suggestion; review every three months and before important broadcasts where appropriate.'),
        'printer': ('Printer maintenance check', 'Local planning suggestion; review every three to six months.'),
        'network': ('Network equipment review', 'Schedule only within the equipment owner’s authorized scope.'),
    }
    name, description = suggestions.get(asset.category, ('Equipment inspection', 'Local planning suggestion; adjust to the needs and authorization for this equipment.'))
    return {'name': name, 'description': description}


def follow_up_state(record, *, as_of=None):
    """Classify an unresolved follow-up; past due dates never resolve it."""
    as_of = as_of or timezone.localdate()
    if not record.follow_up_required:
        return 'not_required'
    if record.resolved_at:
        return 'resolved'
    if record.follow_up_date and record.follow_up_date < as_of:
        return 'overdue'
    if record.follow_up_date and record.follow_up_date <= as_of + timedelta(days=settings.MAINTENANCE_DUE_SOON_DAYS):
        return 'due_soon'
    return 'open'
