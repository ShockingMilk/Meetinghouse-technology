from django.conf import settings
from django.db import models


class NotificationNoteRevision(models.Model):
    """
    Preserve the previous contents when an investigation note is edited.

    Each revision stores the values that existed immediately before an edit.
    """

    note = models.ForeignKey(
        'notifications.NotificationNote',
        on_delete=models.PROTECT,
        related_name='revisions',
    )

    previous_body = models.TextField()
    previous_occurred_at = models.DateTimeField()

    revised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notification_note_revisions',
    )

    revision_reason = models.CharField(
        max_length=255,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-pk')
        verbose_name = 'Notification Note Revision'
        verbose_name_plural = 'Notification Note Revisions'

    def __str__(self) -> str:
        """Return a readable revision identifier."""
        return (
            f'Revision of note #{self.note_id} '
            f'on {self.created_at:%Y-%m-%d %H:%M}'
        )
