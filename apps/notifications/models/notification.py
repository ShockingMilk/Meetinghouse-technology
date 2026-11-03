from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class NotificationCategory(models.TextChoices):
    """Categories used to identify operational issues."""

    MAINTENANCE_UPCOMING = (
        'maintenance_upcoming',
        'Maintenance Upcoming',
    )
    MAINTENANCE_DUE_SOON = (
        'maintenance_due_soon',
        'Maintenance Due Soon',
    )
    MAINTENANCE_OVERDUE = (
        'maintenance_overdue',
        'Maintenance Overdue',
    )
    MAINTENANCE_FOLLOW_UP = (
        'maintenance_follow_up',
        'Maintenance Follow-up',
    )
    ASSET_OFFLINE = (
        'asset_offline',
        'Asset Offline',
    )
    ASSET_FAILED = (
        'asset_failed',
        'Asset Failed',
    )
    ASSET_UNDER_REPAIR = (
        'asset_under_repair',
        'Asset Under Repair',
    )
    WARRANTY_APPROACHING = (
        'warranty_approaching',
        'Warranty Approaching',
    )
    LIFECYCLE_EXPIRED = (
        'lifecycle_expired',
        'Lifecycle Date Expired',
    )
    LIFECYCLE_INFORMATION_MISSING = (
        'lifecycle_information_missing',
        'Lifecycle Information Missing',
    )
    ROOM_FOLLOW_UP = (
        'room_follow_up',
        'Room Follow-up',
    )
    DEPENDENCY_ISSUE = (
        'dependency_issue',
        'Dependency Issue',
    )
    COMPATIBILITY_ISSUE = (
        'compatibility_issue',
        'Compatibility Issue',
    )
    REPLACEMENT_REVIEW = (
        'replacement_review',
        'Replacement Review',
    )


class NotificationPriority(models.TextChoices):
    """Operational priority levels."""

    CRITICAL = 'critical', 'Critical'
    HIGH = 'high', 'High'
    MEDIUM = 'medium', 'Medium'
    LOW = 'low', 'Low'
    INFORMATIONAL = 'informational', 'Informational'


class NotificationStatus(models.TextChoices):
    """Workflow status of a notification."""

    OPEN = 'open', 'Open'
    ACKNOWLEDGED = 'acknowledged', 'Acknowledged'
    RESOLVED = 'resolved', 'Resolved'


class NotificationResolutionMode(models.TextChoices):
    """Determines whether a notification can resolve automatically."""

    AUTOMATIC = 'automatic', 'Automatic'
    MANUAL = 'manual', 'Manual'


class Notification(models.Model):
    """
    An ongoing operational issue requiring attention.

    Notifications reference source records but do not replace or modify
    the underlying inventory, maintenance, or compatibility records.
    """

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    category = models.CharField(
        max_length=50,
        choices=NotificationCategory.choices,
    )
    priority = models.CharField(
        max_length=20,
        choices=NotificationPriority.choices,
        default=NotificationPriority.MEDIUM,
    )
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.OPEN,
    )
    resolution_mode = models.CharField(
        max_length=20,
        choices=NotificationResolutionMode.choices,
        default=NotificationResolutionMode.MANUAL,
    )

    # Generic reference to the record that generated this notification.
    source_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        related_name='operational_notifications',
    )
    source_object_id = models.CharField(
        max_length=255,
    )
    source = GenericForeignKey(
        'source_content_type',
        'source_object_id',
    )

    # Optional direct asset relationship for filtering and reporting.
    # PROTECT preserves the asset while notification history references it.
    asset = models.ForeignKey(
        'inventory.Asset',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='notifications',
    )

    # Preserve a readable description if the source record later disappears.
    source_summary = models.CharField(
        max_length=255,
        blank=True,
    )

    # Stable identifier used by the generation service to prevent duplicates.
    deduplication_key = models.CharField(
        max_length=255,
        unique=True,
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_notifications',
    )

    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    occurrence_count = models.PositiveIntegerField(default=1)

    condition_active = models.BooleanField(default=True)
    condition_cleared_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    snoozed_until = models.DateTimeField(
        null=True,
        blank=True,
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('status', '-priority', '-last_seen_at')
        indexes = [
            models.Index(
                fields=('status', 'priority'),
                name='notif_status_priority_idx',
            ),
            models.Index(
                fields=('asset', 'status'),
                name='notif_asset_status_idx',
            ),
            models.Index(
                fields=('category', 'status'),
                name='notif_category_status_idx',
            ),
            models.Index(
                fields=('condition_active', 'status'),
                name='notif_condition_status_idx',
            ),
        ]
        verbose_name = 'Operational Notification'
        verbose_name_plural = 'Operational Notifications'

    def __str__(self) -> str:
        """Return a readable notification identifier."""
        return f'{self.get_priority_display()}: {self.title}'

    @property
    def is_snoozed(self) -> bool:
        """Return whether the notification is currently snoozed."""
        return bool(
            self.snoozed_until
            and self.snoozed_until > timezone.now()
        )
