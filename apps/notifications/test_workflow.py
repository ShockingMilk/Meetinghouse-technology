"""Tests for notification acknowledgment and assignment services."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationEvent,
    NotificationEventType,
    NotificationStatus,
    NotificationResolutionMode,
)
from apps.notifications.services import (
    acknowledge_notification,
    assign_notification,
    reopen_notification,
    resolve_notification_manually,
    snooze_notification,
    unsnooze_notification,
)


class NotificationWorkflowTests(TestCase):
    """Verify notification state changes and audit events."""

    def setUp(self):
        self.user_model = get_user_model()
        self.actor = self.user_model.objects.create_user(
            username="workflow-actor",
            password="test-password",
        )
        self.assignee = self.user_model.objects.create_user(
            username="workflow-assignee",
            password="test-password",
        )
        self.second_assignee = self.user_model.objects.create_user(
            username="workflow-assignee-two",
            password="test-password",
        )

        self.content_type = ContentType.objects.get_for_model(
            self.user_model,
        )

        self.notification = Notification.objects.create(
            title="Test operational notification",
            description="Workflow service test.",
            category=NotificationCategory.ASSET_OFFLINE,
            status=NotificationStatus.OPEN,
            source_content_type=self.content_type,
            source_object_id=str(self.actor.pk),
            source_summary="Workflow test source",
            deduplication_key="workflow-service-test",
        )

    def test_acknowledge_changes_status_and_records_event(self):
        """Acknowledgment updates the notification and creates an event."""
        notification = acknowledge_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
        )

        notification.refresh_from_db()

        self.assertEqual(
            notification.status,
            NotificationStatus.ACKNOWLEDGED,
        )
        self.assertIsNotNone(notification.acknowledged_at)

        event = NotificationEvent.objects.get(
            notification=notification,
            event_type=NotificationEventType.ACKNOWLEDGED,
        )

        self.assertEqual(event.actor, self.actor)
        self.assertEqual(
            event.metadata["previous_status"],
            NotificationStatus.OPEN,
        )
        self.assertEqual(
            event.metadata["new_status"],
            NotificationStatus.ACKNOWLEDGED,
        )

    def test_repeated_acknowledgment_does_not_create_duplicate_event(self):
        """Acknowledging an already acknowledged item is idempotent."""
        acknowledge_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
        )

        original_event_count = NotificationEvent.objects.filter(
            notification=self.notification,
            event_type=NotificationEventType.ACKNOWLEDGED,
        ).count()

        acknowledge_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
        )

        self.assertEqual(
            NotificationEvent.objects.filter(
                notification=self.notification,
                event_type=NotificationEventType.ACKNOWLEDGED,
            ).count(),
            original_event_count,
        )

    def test_resolved_notification_cannot_be_acknowledged(self):
        """A resolved notification cannot transition back through acknowledgment."""
        self.notification.status = NotificationStatus.RESOLVED
        self.notification.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            acknowledge_notification(
                notification_id=self.notification.pk,
                actor=self.actor,
            )

        self.assertFalse(
            NotificationEvent.objects.filter(
                notification=self.notification,
                event_type=NotificationEventType.ACKNOWLEDGED,
            ).exists()
        )

    def test_assignment_records_assignee_and_event(self):
        """Assigning a notification updates its assignee and audit history."""
        notification = assign_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
            assignee=self.assignee,
        )

        notification.refresh_from_db()

        self.assertEqual(notification.assigned_to, self.assignee)

        event = NotificationEvent.objects.get(
            notification=notification,
            event_type=NotificationEventType.ASSIGNED,
        )

        self.assertEqual(event.actor, self.actor)
        self.assertIsNone(event.metadata["previous_assignee_id"])
        self.assertEqual(
            event.metadata["new_assignee_id"],
            self.assignee.pk,
        )
        self.assertEqual(
            event.metadata["new_assignee"],
            self.assignee.get_username(),
        )

    def test_reassignment_preserves_each_assignment_event(self):
        """Reassignment creates a new event instead of replacing history."""
        assign_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
            assignee=self.assignee,
        )

        assign_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
            assignee=self.second_assignee,
        )

        self.notification.refresh_from_db()

        self.assertEqual(
            self.notification.assigned_to,
            self.second_assignee,
        )

        events = NotificationEvent.objects.filter(
            notification=self.notification,
            event_type=NotificationEventType.ASSIGNED,
        ).order_by("created_at", "pk")

        self.assertEqual(events.count(), 2)

        second_event = events.last()
        self.assertEqual(
            second_event.metadata["previous_assignee_id"],
            self.assignee.pk,
        )
        self.assertEqual(
            second_event.metadata["new_assignee_id"],
            self.second_assignee.pk,
        )

    def test_unassignment_records_event(self):
        """Removing an assignment is also preserved in the event history."""
        assign_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
            assignee=self.assignee,
        )

        assign_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
            assignee=None,
        )

        self.notification.refresh_from_db()

        self.assertIsNone(self.notification.assigned_to)

        events = NotificationEvent.objects.filter(
            notification=self.notification,
            event_type=NotificationEventType.ASSIGNED,
        ).order_by("created_at", "pk")

        self.assertEqual(events.count(), 2)
        self.assertEqual(
            events.last().metadata["previous_assignee_id"],
            self.assignee.pk,
        )
        self.assertIsNone(
            events.last().metadata["new_assignee_id"],
        )

    def test_same_assignee_does_not_create_duplicate_event(self):
        """Assigning the current assignee again is a no-op."""
        assign_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
            assignee=self.assignee,
        )

        assign_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
            assignee=self.assignee,
        )

        self.assertEqual(
            NotificationEvent.objects.filter(
                notification=self.notification,
                event_type=NotificationEventType.ASSIGNED,
            ).count(),
            1,
        )

    def test_resolved_notification_cannot_be_assigned(self):
        """Resolved notifications cannot receive new assignments."""
        self.notification.status = NotificationStatus.RESOLVED
        self.notification.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            assign_notification(
                notification_id=self.notification.pk,
                actor=self.actor,
                assignee=self.assignee,
            )

        self.assertIsNone(self.notification.assigned_to)
        self.assertFalse(
            NotificationEvent.objects.filter(
                notification=self.notification,
                event_type=NotificationEventType.ASSIGNED,
            ).exists()
        )

    # ------------------------------------------------------------------
    # Snooze workflow
    # ------------------------------------------------------------------

    def test_snooze_sets_expiration_and_records_event(self):
        """Snoozing stores the expiration without changing status."""
        until = timezone.now() + timedelta(hours=2)

        notification = snooze_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
            until=until,
        )

        notification.refresh_from_db()

        self.assertEqual(notification.status, NotificationStatus.OPEN)
        self.assertEqual(notification.snoozed_until, until)

        event = NotificationEvent.objects.get(
            notification=notification,
            event_type=NotificationEventType.SNOOZED,
        )

        self.assertEqual(event.actor, self.actor)
        self.assertEqual(
            event.metadata["snoozed_until"],
            until.isoformat(),
        )

    def test_snooze_rejects_past_datetime(self):
        """A snooze expiration must be in the future."""
        with self.assertRaises(ValidationError):
            snooze_notification(
                notification_id=self.notification.pk,
                actor=self.actor,
                until=timezone.now() - timedelta(minutes=1),
            )

        self.notification.refresh_from_db()
        self.assertIsNone(self.notification.snoozed_until)

    def test_snooze_rejects_naive_datetime(self):
        """A snooze expiration must include timezone information."""
        from datetime import datetime

        with self.assertRaises(ValidationError):
            snooze_notification(
                notification_id=self.notification.pk,
                actor=self.actor,
                until=datetime(2030, 1, 1, 12, 0),
            )

    def test_repeating_same_snooze_does_not_create_duplicate_event(self):
        """Repeating the same snooze expiration is idempotent."""
        until = timezone.now() + timedelta(hours=2)

        snooze_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
            until=until,
        )
        snooze_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
            until=until,
        )

        self.assertEqual(
            NotificationEvent.objects.filter(
                notification=self.notification,
                event_type=NotificationEventType.SNOOZED,
            ).count(),
            1,
        )

    def test_unsnooze_clears_expiration_and_records_event(self):
        """Unsnoozing clears the timestamp and preserves the prior value."""
        until = timezone.now() + timedelta(hours=2)

        snooze_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
            until=until,
        )

        notification = unsnooze_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
        )

        notification.refresh_from_db()
        self.assertIsNone(notification.snoozed_until)

        event = NotificationEvent.objects.get(
            notification=notification,
            event_type=NotificationEventType.UNSNOOZED,
        )

        self.assertEqual(event.actor, self.actor)
        self.assertEqual(
            event.metadata["previous_snoozed_until"],
            until.isoformat(),
        )

    def test_unsnooze_without_active_snooze_is_idempotent(self):
        """Unsnoozing a notification that is not snoozed creates no event."""
        unsnooze_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
        )

        self.assertFalse(
            NotificationEvent.objects.filter(
                notification=self.notification,
                event_type=NotificationEventType.UNSNOOZED,
            ).exists()
        )

    # ------------------------------------------------------------------
    # Manual resolution workflow
    # ------------------------------------------------------------------

    def test_manual_resolution_requires_note(self):
        """A blank resolution note cannot resolve a notification."""
        with self.assertRaises(ValidationError):
            resolve_notification_manually(
                notification_id=self.notification.pk,
                actor=self.actor,
                resolution_note="   ",
            )

        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, NotificationStatus.OPEN)

    def test_manual_resolution_updates_state_and_records_note(self):
        """Manual resolution stores the note in the audit event."""
        note = "Replaced the faulty network cable and verified connectivity."

        notification = resolve_notification_manually(
            notification_id=self.notification.pk,
            actor=self.actor,
            resolution_note=note,
        )

        notification.refresh_from_db()

        self.assertEqual(notification.status, NotificationStatus.RESOLVED)
        self.assertEqual(
            notification.resolution_mode,
            NotificationResolutionMode.MANUAL,
        )
        self.assertIsNotNone(notification.resolved_at)

        event = NotificationEvent.objects.get(
            notification=notification,
            event_type=NotificationEventType.RESOLVED_MANUALLY,
        )

        self.assertEqual(event.actor, self.actor)
        self.assertEqual(event.description, note)
        self.assertEqual(event.metadata["resolution_note"], note)
        self.assertEqual(
            event.metadata["previous_status"],
            NotificationStatus.OPEN,
        )

    def test_manual_resolution_clears_snooze(self):
        """Resolving a snoozed notification removes its snooze."""
        snooze_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
            until=timezone.now() + timedelta(hours=2),
        )

        resolve_notification_manually(
            notification_id=self.notification.pk,
            actor=self.actor,
            resolution_note="Issue corrected.",
        )

        self.notification.refresh_from_db()
        self.assertIsNone(self.notification.snoozed_until)

    def test_resolved_notification_cannot_be_manually_resolved_again(self):
        """A second manual resolution attempt is rejected."""
        resolve_notification_manually(
            notification_id=self.notification.pk,
            actor=self.actor,
            resolution_note="Issue corrected.",
        )

        with self.assertRaises(ValidationError):
            resolve_notification_manually(
                notification_id=self.notification.pk,
                actor=self.actor,
                resolution_note="Trying to resolve again.",
            )

        self.assertEqual(
            NotificationEvent.objects.filter(
                notification=self.notification,
                event_type=NotificationEventType.RESOLVED_MANUALLY,
            ).count(),
            1,
        )

    # ------------------------------------------------------------------
    # Reopen workflow
    # ------------------------------------------------------------------

    def test_reopen_requires_reason(self):
        """A blank reason cannot reopen a resolved notification."""
        self.notification.status = NotificationStatus.RESOLVED
        self.notification.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            reopen_notification(
                notification_id=self.notification.pk,
                actor=self.actor,
                reason="  ",
            )

        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, NotificationStatus.RESOLVED)

    def test_reopen_restores_open_state_and_records_reason(self):
        """Reopening resets active workflow timestamps and records why."""
        resolve_notification_manually(
            notification_id=self.notification.pk,
            actor=self.actor,
            resolution_note="Issue corrected.",
        )

        reason = "The equipment failed again during the next meeting."

        notification = reopen_notification(
            notification_id=self.notification.pk,
            actor=self.actor,
            reason=reason,
        )

        notification.refresh_from_db()

        self.assertEqual(notification.status, NotificationStatus.OPEN)
        self.assertIsNone(notification.acknowledged_at)
        self.assertIsNone(notification.resolved_at)
        self.assertIsNone(notification.snoozed_until)

        event = NotificationEvent.objects.get(
            notification=notification,
            event_type=NotificationEventType.REOPENED,
        )

        self.assertEqual(event.actor, self.actor)
        self.assertEqual(event.description, reason)
        self.assertEqual(event.metadata["reopen_reason"], reason)
        self.assertEqual(
            event.metadata["previous_status"],
            NotificationStatus.RESOLVED,
        )
        self.assertEqual(
            event.metadata["new_status"],
            NotificationStatus.OPEN,
        )

    def test_cannot_reopen_unresolved_notification(self):
        """Only a resolved notification can be reopened."""
        with self.assertRaises(ValidationError):
            reopen_notification(
                notification_id=self.notification.pk,
                actor=self.actor,
                reason="Testing an invalid transition.",
            )

        self.assertFalse(
            NotificationEvent.objects.filter(
                notification=self.notification,
                event_type=NotificationEventType.REOPENED,
            ).exists()
        )
