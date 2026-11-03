from django.conf import settings
from django.db import models


class NotificationEventType(models.TextChoices):
    """Recorded events in a notification's lifecycle."""

    CREATED = 'created', 'Created'
    DETECTED_AGAIN = 'detected_again', 'Detected Again'
    ACKNOWLEDGED = 'acknowledged', 'Acknowledged'
    SNOOZED = 'snoozed', 'Snoozed'
    UNSNOOZED = 'unsnoozed', 'Snooze Expired'
    ASSIGNED = 'assigned', 'Assigned'
    CONDITION_CLEARED = 'condition_cleared', 'Condition Cleared'
    CONDITION_RETURNED = 'condition_returned', 'Condition Returned'
    RESOLVED_AUTOMATICALLY = (
        'resolved_automatically',
        'Resolved Automatically',
    )
    RESOLVED_MANUALLY = (
        'resolved_manually',
        'Resolved Manually',
    )
    REOPENED = 'reopened', 'Reopened'
    DETAILS_UPDATED = 'details_updated', 'Details Updated'
    NOTE_CREATED = 'note_created', 'Note Created'
    NOTE_UPDATED = 'note_updated', 'Note Updated'
    CORRECTION_RECORDED = 'correction_recorded', 'Correction Recorded'


class NotificationEvent(models.Model):
    """
    Historical record of a notification workflow event.

    Events are intended to be append-only through application workflows.
    """

    notification = models.ForeignKey(
        'notifications.Notification',
        on_delete=models.PROTECT,
        related_name='events',
    )

    event_type = models.CharField(
        max_length=30,
        choices=NotificationEventType.choices,
    )
    description = models.TextField(blank=True)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notification_events',
    )

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created_at', 'pk')
        indexes = [
            models.Index(
                fields=('notification', 'created_at'),
                name='notif_event_timeline_idx',
            ),
            models.Index(
                fields=('event_type', 'created_at'),
                name='notif_event_type_date_idx',
            ),
        ]
        verbose_name = 'Notification Event'
        verbose_name_plural = 'Notification Events'

    def __str__(self) -> str:
        """Return a readable event description."""
        return (
            f'{self.notification.title} - '
            f'{self.get_event_type_display()}'
        )
