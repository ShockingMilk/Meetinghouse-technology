"""Tests for notification workflow views."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationEvent,
    NotificationEventType,
    NotificationStatus,
)


class NotificationWorkflowViewTests(TestCase):
    """Verify notification workflow actions through their HTTP views."""

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

        self.content_type = ContentType.objects.get_for_model(
            self.user_model,
        )

        self.notification = self.create_notification()

    def create_notification(
        self,
        *,
        title="Workflow test notification",
        status=NotificationStatus.OPEN,
        assigned_to=None,
    ):
        """Create a notification with its required source reference."""
        return Notification.objects.create(
            title=title,
            description="Notification workflow view test.",
            category=NotificationCategory.ASSET_OFFLINE,
            status=status,
            source_content_type=self.content_type,
            source_object_id="1",
            source_summary="Workflow test source",
            deduplication_key=f'workflow-view-{title.lower().replace(" ", "-")}',
            assigned_to=assigned_to,
        )

    def login(self):
        """Authenticate the test actor."""
        self.client.force_login(self.actor)

    def test_anonymous_acknowledgment_redirects_to_login(self):
        """Anonymous users cannot acknowledge notifications."""
        response = self.client.post(
            reverse(
                "notifications:acknowledge",
                args=[self.notification.pk],
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

        self.notification.refresh_from_db()
        self.assertEqual(
            self.notification.status,
            NotificationStatus.OPEN,
        )

    def test_anonymous_assignment_redirects_to_login(self):
        """Anonymous users cannot assign notifications."""
        response = self.client.post(
            reverse(
                "notifications:assign",
                args=[self.notification.pk],
            ),
            {"assignee_id": self.assignee.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

        self.notification.refresh_from_db()
        self.assertIsNone(self.notification.assigned_to)

    def test_acknowledgment_requires_post(self):
        """GET requests cannot trigger acknowledgment."""
        self.login()

        response = self.client.get(
            reverse(
                "notifications:acknowledge",
                args=[self.notification.pk],
            ),
        )

        self.assertEqual(response.status_code, 405)

        self.notification.refresh_from_db()
        self.assertEqual(
            self.notification.status,
            NotificationStatus.OPEN,
        )

    def test_assignment_requires_post(self):
        """GET requests cannot trigger assignment."""
        self.login()

        response = self.client.get(
            reverse(
                "notifications:assign",
                args=[self.notification.pk],
            ),
        )

        self.assertEqual(response.status_code, 405)

        self.notification.refresh_from_db()
        self.assertIsNone(self.notification.assigned_to)

    def test_acknowledgment_updates_notification_and_records_event(self):
        """A valid POST acknowledges the notification."""
        self.login()

        response = self.client.post(
            reverse(
                "notifications:acknowledge",
                args=[self.notification.pk],
            ),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.notification.refresh_from_db()
        self.assertEqual(
            self.notification.status,
            NotificationStatus.ACKNOWLEDGED,
        )
        self.assertIsNotNone(self.notification.acknowledged_at)

        event = NotificationEvent.objects.get(
            notification=self.notification,
            event_type=NotificationEventType.ACKNOWLEDGED,
        )
        self.assertEqual(event.actor, self.actor)

        self.assertContains(response, "Notification acknowledged.")

    def test_resolved_notification_cannot_be_acknowledged(self):
        """A resolved notification remains unchanged after acknowledgment."""
        resolved = self.create_notification(
            title="Resolved notification",
            status=NotificationStatus.RESOLVED,
        )
        self.login()

        response = self.client.post(
            reverse(
                "notifications:acknowledge",
                args=[resolved.pk],
            ),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        resolved.refresh_from_db()
        self.assertEqual(
            resolved.status,
            NotificationStatus.RESOLVED,
        )
        self.assertFalse(
            NotificationEvent.objects.filter(
                notification=resolved,
                event_type=NotificationEventType.ACKNOWLEDGED,
            ).exists()
        )

        self.assertContains(
            response,
            "A resolved notification cannot be acknowledged.",
        )

    def test_assignment_updates_notification_and_records_event(self):
        """A valid active user can be assigned."""
        self.login()

        response = self.client.post(
            reverse(
                "notifications:assign",
                args=[self.notification.pk],
            ),
            {"assignee_id": self.assignee.pk},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.notification.refresh_from_db()
        self.assertEqual(
            self.notification.assigned_to,
            self.assignee,
        )

        event = NotificationEvent.objects.get(
            notification=self.notification,
            event_type=NotificationEventType.ASSIGNED,
        )
        self.assertEqual(event.actor, self.actor)
        self.assertEqual(
            event.metadata["new_assignee_id"],
            self.assignee.pk,
        )

        self.assertContains(
            response,
            f"Notification assigned to {self.assignee.get_username()}.",
        )

    def test_assignment_can_be_removed(self):
        """A blank assignee ID removes the current assignment."""
        assigned = self.create_notification(
            title="Assigned notification",
            assigned_to=self.assignee,
        )
        self.login()

        response = self.client.post(
            reverse(
                "notifications:assign",
                args=[assigned.pk],
            ),
            {"assignee_id": ""},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        assigned.refresh_from_db()
        self.assertIsNone(assigned.assigned_to)

        event = NotificationEvent.objects.get(
            notification=assigned,
            event_type=NotificationEventType.ASSIGNED,
        )
        self.assertEqual(event.actor, self.actor)
        self.assertEqual(
            event.metadata["previous_assignee_id"],
            self.assignee.pk,
        )
        self.assertIsNone(event.metadata["new_assignee_id"])

        self.assertContains(
            response,
            "Notification assignment removed.",
        )

    def test_invalid_assignee_is_rejected(self):
        """A nonexistent user ID cannot change the assignment."""
        self.login()

        response = self.client.post(
            reverse(
                "notifications:assign",
                args=[self.notification.pk],
            ),
            {"assignee_id": "99999999"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.notification.refresh_from_db()
        self.assertIsNone(self.notification.assigned_to)

        self.assertFalse(
            NotificationEvent.objects.filter(
                notification=self.notification,
                event_type=NotificationEventType.ASSIGNED,
            ).exists()
        )

        self.assertContains(
            response,
            "Select a valid active user for this assignment.",
        )

    def test_inactive_assignee_is_rejected(self):
        """Inactive accounts cannot receive notification assignments."""
        inactive_user = self.user_model.objects.create_user(
            username="inactive-assignee",
            password="test-password",
            is_active=False,
        )
        self.login()

        response = self.client.post(
            reverse(
                "notifications:assign",
                args=[self.notification.pk],
            ),
            {"assignee_id": inactive_user.pk},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.notification.refresh_from_db()
        self.assertIsNone(self.notification.assigned_to)

        self.assertFalse(
            NotificationEvent.objects.filter(
                notification=self.notification,
                event_type=NotificationEventType.ASSIGNED,
            ).exists()
        )

    def test_resolved_notification_cannot_be_assigned(self):
        """The workflow service prevents assignment after resolution."""
        resolved = self.create_notification(
            title="Resolved assignment test",
            status=NotificationStatus.RESOLVED,
        )
        self.login()

        response = self.client.post(
            reverse(
                "notifications:assign",
                args=[resolved.pk],
            ),
            {"assignee_id": self.assignee.pk},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        resolved.refresh_from_db()
        self.assertIsNone(resolved.assigned_to)

        self.assertFalse(
            NotificationEvent.objects.filter(
                notification=resolved,
                event_type=NotificationEventType.ASSIGNED,
            ).exists()
        )

        self.assertContains(
            response,
            "A resolved notification cannot be assigned.",
        )

    # ------------------------------------------------------------------
    # Snooze views
    # ------------------------------------------------------------------

    def test_snooze_post_updates_notification_and_records_event(self):
        """A valid local date/time snoozes the notification."""
        self.login()

        until = timezone.localtime(timezone.now() + timedelta(hours=2)).replace(
            second=0, microsecond=0
        )

        response = self.client.post(
            reverse("notifications:snooze", args=[self.notification.pk]),
            {"snoozed_until": until.strftime("%Y-%m-%dT%H:%M")},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.notification.refresh_from_db()
        self.assertIsNotNone(self.notification.snoozed_until)
        self.assertEqual(
            timezone.localtime(self.notification.snoozed_until),
            until,
        )
        self.assertEqual(self.notification.status, NotificationStatus.OPEN)

        event = NotificationEvent.objects.get(
            notification=self.notification,
            event_type=NotificationEventType.SNOOZED,
        )
        self.assertEqual(event.actor, self.actor)
        self.assertContains(response, "Notification snoozed until")

    def test_snooze_invalid_datetime_is_rejected(self):
        """Malformed datetime-local input does not change the notification."""
        self.login()

        response = self.client.post(
            reverse("notifications:snooze", args=[self.notification.pk]),
            {"snoozed_until": "not-a-date"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.notification.refresh_from_db()
        self.assertIsNone(self.notification.snoozed_until)
        self.assertFalse(
            NotificationEvent.objects.filter(
                notification=self.notification,
                event_type=NotificationEventType.SNOOZED,
            ).exists()
        )
        self.assertContains(response, "Enter a valid snooze date and time.")

    def test_unsnooze_post_clears_snooze_and_records_event(self):
        """Unsnoozing clears the timestamp and records the actor."""
        self.notification.snoozed_until = timezone.now() + timedelta(hours=2)
        self.notification.save(update_fields=["snoozed_until"])

        self.login()

        response = self.client.post(
            reverse("notifications:unsnooze", args=[self.notification.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.notification.refresh_from_db()
        self.assertIsNone(self.notification.snoozed_until)

        event = NotificationEvent.objects.get(
            notification=self.notification,
            event_type=NotificationEventType.UNSNOOZED,
        )
        self.assertEqual(event.actor, self.actor)
        self.assertContains(response, "Notification snooze removed.")

    # ------------------------------------------------------------------
    # Manual resolution views
    # ------------------------------------------------------------------

    def test_resolve_post_updates_notification_and_records_note(self):
        """A valid resolution explanation resolves the notification."""
        self.login()
        resolution_note = "Replaced the cable and verified the connection."

        response = self.client.post(
            reverse("notifications:resolve", args=[self.notification.pk]),
            {"resolution_note": resolution_note},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.notification.refresh_from_db()
        self.assertEqual(
            self.notification.status,
            NotificationStatus.RESOLVED,
        )
        self.assertIsNotNone(self.notification.resolved_at)

        event = NotificationEvent.objects.get(
            notification=self.notification,
            event_type=NotificationEventType.RESOLVED_MANUALLY,
        )
        self.assertEqual(event.actor, self.actor)
        self.assertEqual(event.description, resolution_note)
        self.assertContains(response, "Notification manually resolved.")

    def test_resolve_post_rejects_blank_resolution_note(self):
        """A blank resolution explanation cannot resolve a notification."""
        self.login()

        response = self.client.post(
            reverse("notifications:resolve", args=[self.notification.pk]),
            {"resolution_note": "   "},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, NotificationStatus.OPEN)
        self.assertFalse(
            NotificationEvent.objects.filter(
                notification=self.notification,
                event_type=NotificationEventType.RESOLVED_MANUALLY,
            ).exists()
        )
        self.assertContains(response, "A resolution note is required.")

    # ------------------------------------------------------------------
    # Reopen views
    # ------------------------------------------------------------------

    def test_reopen_post_restores_open_status_and_records_reason(self):
        """A valid reason reopens a resolved notification."""
        resolved = self.create_notification(
            title="Resolved reopen view test",
            status=NotificationStatus.RESOLVED,
        )
        resolved.resolved_at = timezone.now()
        resolved.save(update_fields=["resolved_at"])

        self.login()
        reason = "The equipment failed again during the next meeting."

        response = self.client.post(
            reverse("notifications:reopen", args=[resolved.pk]),
            {"reason": reason},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        resolved.refresh_from_db()
        self.assertEqual(resolved.status, NotificationStatus.OPEN)
        self.assertIsNone(resolved.resolved_at)
        self.assertIsNone(resolved.acknowledged_at)

        event = NotificationEvent.objects.get(
            notification=resolved,
            event_type=NotificationEventType.REOPENED,
        )
        self.assertEqual(event.actor, self.actor)
        self.assertEqual(event.description, reason)
        self.assertContains(response, "Notification reopened.")

    def test_reopen_post_rejects_blank_reason(self):
        """A blank reason cannot reopen a resolved notification."""
        resolved = self.create_notification(
            title="Resolved blank reopen test",
            status=NotificationStatus.RESOLVED,
        )
        resolved.resolved_at = timezone.now()
        resolved.save(update_fields=["resolved_at"])

        self.login()

        response = self.client.post(
            reverse("notifications:reopen", args=[resolved.pk]),
            {"reason": "   "},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        resolved.refresh_from_db()
        self.assertEqual(resolved.status, NotificationStatus.RESOLVED)
        self.assertFalse(
            NotificationEvent.objects.filter(
                notification=resolved,
                event_type=NotificationEventType.REOPENED,
            ).exists()
        )
        self.assertContains(response, "A reason is required to reopen a notification.")

    # ------------------------------------------------------------------
    # Request protection
    # ------------------------------------------------------------------

    def test_new_workflow_actions_require_post(self):
        """GET requests cannot trigger snooze, unsnooze, resolve, or reopen."""
        self.login()

        endpoints = (
            "snooze",
            "unsnooze",
            "resolve",
            "reopen",
        )

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(
                    reverse(
                        f"notifications:{endpoint}",
                        args=[self.notification.pk],
                    )
                )
                self.assertEqual(response.status_code, 405)

    def test_new_workflow_actions_require_login(self):
        """Anonymous users cannot invoke the new workflow actions."""
        endpoints = (
            "snooze",
            "unsnooze",
            "resolve",
            "reopen",
        )

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.post(
                    reverse(
                        f"notifications:{endpoint}",
                        args=[self.notification.pk],
                    )
                )
                self.assertEqual(response.status_code, 302)
                self.assertIn("/login/", response.url)
