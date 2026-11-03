from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationNote(models.Model):
    """
    An editable investigation note attached to a notification.

    occurred_at records when the real-world event happened.
    created_at records when the note was entered into the application.
    updated_at records the most recent edit.
    """

    notification = models.ForeignKey(
        'notifications.Notification',
        on_delete=models.PROTECT,
        related_name='notes',
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notification_notes',
    )

    body = models.TextField()

    occurred_at = models.DateTimeField(
        default=timezone.now,
        help_text=(
            'When the event or contact actually happened. '
            'This may be earlier than the date the note is entered.'
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('occurred_at', 'created_at')
        indexes = [
            models.Index(
                fields=('notification', 'occurred_at'),
                name='notification_note_timeline_idx',
            ),
        ]
        verbose_name = 'Notification Note'
        verbose_name_plural = 'Notification Notes'

    def __str__(self) -> str:
        """Return a short description of the note."""
        return (
            f'Note for {self.notification.title} '
            f'({self.occurred_at:%Y-%m-%d})'
        )
