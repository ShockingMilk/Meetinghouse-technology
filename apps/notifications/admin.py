from django.contrib import admin

from .models import (
    Notification,
    NotificationEvent,
    NotificationNote,
    NotificationNoteRevision,
)


class ReadOnlyHistoryAdmin(admin.ModelAdmin):
    """Prevent direct editing of historical records in Django admin."""

    def get_readonly_fields(self, request, obj=None):
        """Make every concrete model field read-only."""
        return [
            field.name
            for field in self.model._meta.concrete_fields
        ]

    def has_add_permission(self, request):
        """Historical records must be created by application workflows."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of historical records."""
        return False


@admin.register(Notification)
class NotificationAdmin(ReadOnlyHistoryAdmin):
    """Read-only inspection of operational notifications."""

    list_display = (
        'title',
        'category',
        'priority',
        'status',
        'assigned_to',
        'condition_active',
        'last_seen_at',
    )
    list_filter = (
        'status',
        'priority',
        'category',
        'resolution_mode',
        'condition_active',
    )
    search_fields = (
        'title',
        'description',
        'source_summary',
        'deduplication_key',
        'asset__inventory_number',
        'asset__name',
    )
    list_select_related = (
        'asset',
        'assigned_to',
        'source_content_type',
    )


@admin.register(NotificationEvent)
class NotificationEventAdmin(ReadOnlyHistoryAdmin):
    """Read-only inspection of notification event history."""

    list_display = (
        'notification',
        'event_type',
        'actor',
        'created_at',
    )
    list_filter = ('event_type', 'created_at')
    search_fields = (
        'notification__title',
        'description',
    )
    list_select_related = ('notification', 'actor')


@admin.register(NotificationNote)
class NotificationNoteAdmin(ReadOnlyHistoryAdmin):
    """Read-only inspection of notification investigation notes."""

    list_display = (
        'notification',
        'author',
        'occurred_at',
        'created_at',
        'updated_at',
    )
    search_fields = (
        'notification__title',
        'body',
    )
    list_select_related = ('notification', 'author')


@admin.register(NotificationNoteRevision)
class NotificationNoteRevisionAdmin(ReadOnlyHistoryAdmin):
    """Read-only inspection of previous note versions."""

    list_display = (
        'note',
        'revised_by',
        'revision_reason',
        'created_at',
    )
    search_fields = (
        'note__notification__title',
        'previous_body',
        'revision_reason',
    )
    list_select_related = (
        'note',
        'revised_by',
    )
