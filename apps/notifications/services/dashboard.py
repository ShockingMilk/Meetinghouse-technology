"""Read-only notification data for operational dashboards."""

from django.db.models import Case, IntegerField, Q, Value, When
from django.utils import timezone

from apps.notifications.models import (
    Notification,
    NotificationPriority,
    NotificationStatus,
)


PRIORITY_ORDER = {
    NotificationPriority.CRITICAL: 0,
    NotificationPriority.HIGH: 1,
    NotificationPriority.MEDIUM: 2,
    NotificationPriority.LOW: 3,
    NotificationPriority.INFORMATIONAL: 4,
}


def _ordered_notifications(queryset):
    """Apply explicit severity ordering, then most recently seen."""
    priority_order = Case(
        *[
            When(priority=priority, then=Value(order))
            for priority, order in PRIORITY_ORDER.items()
        ],
        default=Value(len(PRIORITY_ORDER)),
        output_field=IntegerField(),
    )

    return queryset.annotate(
        priority_order=priority_order,
    ).order_by(
        'priority_order',
        '-last_seen_at',
        '-created_at',
    )


def _dashboard_queryset():
    """Return unresolved notifications with related display data loaded."""
    return Notification.objects.filter(
        status__in=(
            NotificationStatus.OPEN,
            NotificationStatus.ACKNOWLEDGED,
        ),
    ).select_related(
        'asset',
        'asset__room',
        'assigned_to',
        'source_content_type',
    )


def notification_dashboard(limit=8):
    """
    Return notification counts and separate active/snoozed lists.

    This function is intentionally read-only. It does not create,
    resolve, acknowledge, snooze, or otherwise modify notifications.
    """
    now = timezone.now()
    unresolved = _dashboard_queryset()

    snoozed = unresolved.filter(snoozed_until__gt=now)
    active = unresolved.filter(
        Q(snoozed_until__isnull=True)
        | Q(snoozed_until__lte=now)
    )

    return {
        'unresolved_count': unresolved.count(),
        'actionable_count': active.count(),
        'snoozed_count': snoozed.count(),
        'active_notifications': _ordered_notifications(active)[:limit],
        'snoozed_notifications': _ordered_notifications(snoozed)[:limit],
    }
