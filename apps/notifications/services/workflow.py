"""Transactional services for notification workflow actions."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import (
    Notification,
    NotificationEvent,
    NotificationEventType,
    NotificationResolutionMode,
    NotificationStatus,
)


@transaction.atomic
def acknowledge_notification(*, notification_id, actor):
    """
    Acknowledge an open notification and record the action.

    Repeated acknowledgment is idempotent: it returns the existing
    notification without creating another event.
    """
    notification = Notification.objects.select_for_update().get(pk=notification_id)

    if notification.status == NotificationStatus.ACKNOWLEDGED:
        return notification

    if notification.status == NotificationStatus.RESOLVED:
        raise ValidationError("A resolved notification cannot be acknowledged.")

    if notification.status != NotificationStatus.OPEN:
        raise ValidationError(
            "This notification cannot be acknowledged from its current state."
        )

    acknowledged_at = timezone.now()

    notification.status = NotificationStatus.ACKNOWLEDGED
    notification.acknowledged_at = acknowledged_at
    notification.save(
        update_fields=[
            "status",
            "acknowledged_at",
            "updated_at",
        ]
    )

    NotificationEvent.objects.create(
        notification=notification,
        event_type=NotificationEventType.ACKNOWLEDGED,
        actor=actor,
        description="Notification acknowledged.",
        metadata={
            "previous_status": NotificationStatus.OPEN,
            "new_status": NotificationStatus.ACKNOWLEDGED,
        },
    )

    return notification


@transaction.atomic
def assign_notification(*, notification_id, actor, assignee):
    """
    Assign, reassign, or unassign an unresolved notification.

    Pass assignee=None to remove the current assignment. Every actual
    assignment change is recorded as an append-only event.
    """
    notification = (
        Notification.objects.select_for_update()
        .select_related("assigned_to")
        .get(pk=notification_id)
    )

    if notification.status == NotificationStatus.RESOLVED:
        raise ValidationError("A resolved notification cannot be assigned.")

    previous_assignee = notification.assigned_to

    previous_id = previous_assignee.pk if previous_assignee else None
    new_id = assignee.pk if assignee else None

    if previous_id == new_id:
        return notification

    notification.assigned_to = assignee
    notification.save(
        update_fields=[
            "assigned_to",
            "updated_at",
        ]
    )

    previous_name = previous_assignee.get_username() if previous_assignee else None
    new_name = assignee.get_username() if assignee else None

    if new_name is None:
        description = f"Assignment removed from {previous_name}."
    elif previous_name is None:
        description = f"Notification assigned to {new_name}."
    else:
        description = f"Notification reassigned from {previous_name} to {new_name}."

    NotificationEvent.objects.create(
        notification=notification,
        event_type=NotificationEventType.ASSIGNED,
        actor=actor,
        description=description,
        metadata={
            "previous_assignee_id": previous_id,
            "previous_assignee": previous_name,
            "new_assignee_id": new_id,
            "new_assignee": new_name,
        },
    )

    return notification


@transaction.atomic
def snooze_notification(*, notification_id, actor, until):
    """
    Snooze an unresolved notification until a future aware datetime.

    Snoozing does not alter the notification's open/acknowledged status.
    Repeating the same snooze is idempotent.
    """
    notification = Notification.objects.select_for_update().get(pk=notification_id)

    if notification.status == NotificationStatus.RESOLVED:
        raise ValidationError("A resolved notification cannot be snoozed.")

    if not isinstance(until, type(timezone.now())):
        raise ValidationError("The snooze expiration must be a datetime.")

    if timezone.is_naive(until):
        raise ValidationError("The snooze expiration must include a timezone.")

    now = timezone.now()

    if until <= now:
        raise ValidationError("The snooze expiration must be in the future.")

    if notification.snoozed_until == until:
        return notification

    previous_until = notification.snoozed_until

    notification.snoozed_until = until
    notification.save(
        update_fields=[
            "snoozed_until",
            "updated_at",
        ]
    )

    NotificationEvent.objects.create(
        notification=notification,
        event_type=NotificationEventType.SNOOZED,
        actor=actor,
        description="Notification snoozed.",
        metadata={
            "previous_snoozed_until": (
                previous_until.isoformat() if previous_until else None
            ),
            "snoozed_until": until.isoformat(),
        },
    )

    return notification


@transaction.atomic
def unsnooze_notification(*, notification_id, actor):
    """
    Remove a notification's snooze and record the action.

    Calling this when the notification is not snoozed is an idempotent no-op.
    """
    notification = Notification.objects.select_for_update().get(pk=notification_id)

    if notification.status == NotificationStatus.RESOLVED:
        raise ValidationError("A resolved notification cannot be unsnoozed.")

    previous_until = notification.snoozed_until

    if previous_until is None:
        return notification

    notification.snoozed_until = None
    notification.save(
        update_fields=[
            "snoozed_until",
            "updated_at",
        ]
    )

    NotificationEvent.objects.create(
        notification=notification,
        event_type=NotificationEventType.UNSNOOZED,
        actor=actor,
        description="Notification snooze removed.",
        metadata={
            "previous_snoozed_until": previous_until.isoformat(),
        },
    )

    return notification


@transaction.atomic
def resolve_notification_manually(
    *,
    notification_id,
    actor,
    resolution_note,
):
    """
    Manually resolve a notification and preserve the required explanation.

    The resolution note is stored in the event description and metadata.
    """
    note = (resolution_note or "").strip()

    if not note:
        raise ValidationError("A resolution note is required.")

    notification = Notification.objects.select_for_update().get(pk=notification_id)

    if notification.status == NotificationStatus.RESOLVED:
        raise ValidationError("This notification is already resolved.")

    previous_status = notification.status
    resolved_at = timezone.now()

    notification.status = NotificationStatus.RESOLVED
    notification.resolution_mode = NotificationResolutionMode.MANUAL
    notification.resolved_at = resolved_at
    notification.snoozed_until = None
    notification.save(
        update_fields=[
            "status",
            "resolution_mode",
            "resolved_at",
            "snoozed_until",
            "updated_at",
        ]
    )

    NotificationEvent.objects.create(
        notification=notification,
        event_type=NotificationEventType.RESOLVED_MANUALLY,
        actor=actor,
        description=note,
        metadata={
            "previous_status": previous_status,
            "new_status": NotificationStatus.RESOLVED,
            "resolution_mode": NotificationResolutionMode.MANUAL,
            "resolution_note": note,
        },
    )

    return notification


@transaction.atomic
def reopen_notification(*, notification_id, actor, reason):
    """
    Reopen a resolved notification and preserve the reason in its event.

    Reopened notifications return to OPEN so the acknowledgment workflow
    can begin again.
    """
    reopen_reason = (reason or "").strip()

    if not reopen_reason:
        raise ValidationError("A reason is required to reopen a notification.")

    notification = Notification.objects.select_for_update().get(pk=notification_id)

    if notification.status != NotificationStatus.RESOLVED:
        raise ValidationError("Only resolved notifications can be reopened.")

    previous_resolution_mode = notification.resolution_mode
    previous_resolved_at = notification.resolved_at

    notification.status = NotificationStatus.OPEN
    notification.acknowledged_at = None
    notification.resolved_at = None
    notification.snoozed_until = None
    notification.save(
        update_fields=[
            "status",
            "acknowledged_at",
            "resolved_at",
            "snoozed_until",
            "updated_at",
        ]
    )

    NotificationEvent.objects.create(
        notification=notification,
        event_type=NotificationEventType.REOPENED,
        actor=actor,
        description=reopen_reason,
        metadata={
            "previous_status": NotificationStatus.RESOLVED,
            "new_status": NotificationStatus.OPEN,
            "previous_resolution_mode": previous_resolution_mode,
            "previous_resolved_at": (
                previous_resolved_at.isoformat() if previous_resolved_at else None
            ),
            "reopen_reason": reopen_reason,
        },
    )

    return notification
