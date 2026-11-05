"""Tests for notification dashboard services."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from apps.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationEvent,
    NotificationEventType,
    NotificationNote,
    NotificationPriority,
    NotificationStatus,
)
from apps.notifications.services import notification_dashboard


class NotificationDashboardTests(TestCase):
    """Verify notification dashboard filtering, counts, and ordering."""

    def setUp(self):
        self.user_model = get_user_model()
        self.content_type = ContentType.objects.get_for_model(
            self.user_model,
        )

    def create_notification(
        self,
        title,
        *,
        priority=NotificationPriority.MEDIUM,
        status=NotificationStatus.OPEN,
        snoozed_until=None,
    ):
        """Create a notification with the required source reference."""
        return Notification.objects.create(
            title=title,
            description=f"Test notification: {title}",
            category=NotificationCategory.ASSET_OFFLINE,
            priority=priority,
            status=status,
            source_content_type=self.content_type,
            source_object_id="1",
            source_summary="Test source",
            deduplication_key=f'test-{title.lower().replace(" ", "-")}',
            snoozed_until=snoozed_until,
        )

    def test_dashboard_counts_active_snoozed_and_resolved(self):
        """Resolved notifications are excluded from unresolved counts."""
        self.create_notification("Open notification")

        self.create_notification(
            "Acknowledged notification",
            status=NotificationStatus.ACKNOWLEDGED,
        )

        self.create_notification(
            "Snoozed notification",
            snoozed_until=timezone.now() + timedelta(hours=2),
        )

        self.create_notification(
            "Resolved notification",
            status=NotificationStatus.RESOLVED,
        )

        result = notification_dashboard()

        self.assertEqual(result["unresolved_count"], 3)
        self.assertEqual(result["actionable_count"], 2)
        self.assertEqual(result["snoozed_count"], 1)

        self.assertEqual(
            {item.title for item in result["active_notifications"]},
            {
                "Open notification",
                "Acknowledged notification",
            },
        )

        self.assertEqual(
            [item.title for item in result["snoozed_notifications"]],
            ["Snoozed notification"],
        )

    def test_expired_snooze_is_actionable(self):
        """A notification whose snooze has expired appears in active items."""
        notification = self.create_notification(
            "Expired snooze",
            snoozed_until=timezone.now() - timedelta(minutes=5),
        )

        result = notification_dashboard()

        self.assertEqual(result["actionable_count"], 1)
        self.assertEqual(result["snoozed_count"], 0)
        self.assertEqual(
            result["active_notifications"][0].pk,
            notification.pk,
        )

    def test_active_notifications_are_sorted_by_priority(self):
        """Priority uses severity order rather than alphabetical order."""
        self.create_notification(
            "Low priority",
            priority=NotificationPriority.LOW,
        )
        self.create_notification(
            "Critical priority",
            priority=NotificationPriority.CRITICAL,
        )
        self.create_notification(
            "High priority",
            priority=NotificationPriority.HIGH,
        )
        self.create_notification(
            "Informational priority",
            priority=NotificationPriority.INFORMATIONAL,
        )
        self.create_notification(
            "Medium priority",
            priority=NotificationPriority.MEDIUM,
        )

        result = notification_dashboard()

        self.assertEqual(
            [item.priority for item in result["active_notifications"]],
            [
                NotificationPriority.CRITICAL,
                NotificationPriority.HIGH,
                NotificationPriority.MEDIUM,
                NotificationPriority.LOW,
                NotificationPriority.INFORMATIONAL,
            ],
        )

    def test_notification_lists_respect_limit(self):
        """The returned lists are limited without changing total counts."""
        for number in range(10):
            self.create_notification(f"Active {number:02d}")

        for number in range(10):
            self.create_notification(
                f"Snoozed {number:02d}",
                snoozed_until=timezone.now() + timedelta(hours=1),
            )

        result = notification_dashboard(limit=3)

        self.assertEqual(result["unresolved_count"], 20)
        self.assertEqual(result["actionable_count"], 10)
        self.assertEqual(result["snoozed_count"], 10)

        self.assertEqual(len(result["active_notifications"]), 3)
        self.assertEqual(len(result["snoozed_notifications"]), 3)

    def test_dashboard_does_not_modify_notifications(self):
        """Reading dashboard data must not alter notification workflow state."""
        notification = self.create_notification("Unchanged notification")

        original_status = notification.status
        original_occurrence_count = notification.occurrence_count
        original_last_seen = notification.last_seen_at

        notification_dashboard()

        notification.refresh_from_db()

        self.assertEqual(notification.status, original_status)
        self.assertEqual(
            notification.occurrence_count,
            original_occurrence_count,
        )
        self.assertEqual(notification.last_seen_at, original_last_seen)

    def test_empty_dashboard_returns_zero_counts_and_empty_lists(self):
        """An installation without notifications has a clean empty state."""
        result = notification_dashboard()

        self.assertEqual(result["unresolved_count"], 0)
        self.assertEqual(result["actionable_count"], 0)
        self.assertEqual(result["snoozed_count"], 0)
        self.assertEqual(list(result["active_notifications"]), [])
        self.assertEqual(list(result["snoozed_notifications"]), [])


class NotificationPageTests(TestCase):
    """Verify access and read-only notification pages."""

    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            username="notification-reviewer",
            password="test-password",
        )
        self.content_type = ContentType.objects.get_for_model(
            self.user_model,
        )

    def create_notification(self, title, **kwargs):
        """Create a notification using the required source reference."""
        defaults = {
            "description": f"Description for {title}",
            "category": NotificationCategory.ASSET_OFFLINE,
            "priority": NotificationPriority.MEDIUM,
            "status": NotificationStatus.OPEN,
            "source_content_type": self.content_type,
            "source_object_id": "1",
            "source_summary": "Test source record",
            "deduplication_key": (f'page-test-{title.lower().replace(" ", "-")}'),
        }
        defaults.update(kwargs)
        return Notification.objects.create(
            title=title,
            **defaults,
        )

    def test_notification_list_requires_login(self):
        response = self.client.get(
            reverse("notifications:list"),
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_notification_detail_requires_login(self):
        notification = self.create_notification("Private notification")

        response = self.client.get(
            reverse(
                "notifications:detail",
                args=[notification.pk],
            ),
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_notification_list_displays_unresolved_by_default(self):
        self.client.force_login(self.user)

        self.create_notification("Open issue")
        self.create_notification(
            "Acknowledged issue",
            status=NotificationStatus.ACKNOWLEDGED,
        )
        self.create_notification(
            "Resolved issue",
            status=NotificationStatus.RESOLVED,
        )

        response = self.client.get(
            reverse("notifications:list"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open issue")
        self.assertContains(response, "Acknowledged issue")
        self.assertNotContains(response, "Resolved issue")

    def test_notification_list_can_filter_by_status(self):
        self.client.force_login(self.user)

        self.create_notification("Open issue")
        self.create_notification(
            "Resolved issue",
            status=NotificationStatus.RESOLVED,
        )

        response = self.client.get(
            reverse("notifications:list"),
            {"status": NotificationStatus.RESOLVED},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resolved issue")
        self.assertNotContains(response, "Open issue")

    def test_notification_list_can_search_notification_text(self):
        self.client.force_login(self.user)

        self.create_notification(
            "Projector connection issue",
            description="The projector is offline.",
        )
        self.create_notification("Printer maintenance reminder")

        response = self.client.get(
            reverse("notifications:list"),
            {"q": "projector"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Projector connection issue")
        self.assertNotContains(response, "Printer maintenance reminder")

    def test_notification_detail_displays_notification_information(self):
        self.client.force_login(self.user)

        notification = self.create_notification(
            "Projector offline",
            description="The projector is not responding.",
        )

        response = self.client.get(
            reverse(
                "notifications:detail",
                args=[notification.pk],
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Projector offline")
        self.assertContains(
            response,
            "The projector is not responding.",
        )
        self.assertContains(response, "Test source record")

    def test_notification_detail_displays_events_and_notes(self):
        self.client.force_login(self.user)

        notification = self.create_notification("Audio issue")

        NotificationEvent.objects.create(
            notification=notification,
            event_type=NotificationEventType.CREATED,
            description="Notification created for testing.",
            actor=self.user,
        )

        NotificationNote.objects.create(
            notification=notification,
            author=self.user,
            body="Checked the audio rack.",
        )

        response = self.client.get(
            reverse(
                "notifications:detail",
                args=[notification.pk],
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Notification created for testing.")
        self.assertContains(response, "Checked the audio rack.")

    def test_read_only_pages_do_not_modify_notification(self):
        self.client.force_login(self.user)

        notification = self.create_notification("Unchanged issue")
        original_status = notification.status
        original_occurrence_count = notification.occurrence_count
        original_last_seen = notification.last_seen_at

        self.client.get(reverse("notifications:list"))
        self.client.get(
            reverse(
                "notifications:detail",
                args=[notification.pk],
            ),
        )

        notification.refresh_from_db()

        self.assertEqual(notification.status, original_status)
        self.assertEqual(
            notification.occurrence_count,
            original_occurrence_count,
        )
        self.assertEqual(notification.last_seen_at, original_last_seen)

    def test_notification_list_can_filter_active_snoozes(self):
        """Only notifications with future snooze timestamps are returned."""
        self.client.force_login(self.user)

        self.create_notification(
            "Currently snoozed",
            snoozed_until=timezone.now() + timedelta(hours=2),
        )
        self.create_notification(
            "Expired snooze",
            snoozed_until=timezone.now() - timedelta(minutes=5),
        )
        self.create_notification("Never snoozed")

        response = self.client.get(
            reverse("notifications:list"),
            {"snooze": "snoozed"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Currently snoozed")
        self.assertNotContains(response, "Expired snooze")
        self.assertNotContains(response, "Never snoozed")

    def test_notification_list_can_filter_notifications_not_snoozed(self):
        """Expired and never-snoozed notifications are actionable."""
        self.client.force_login(self.user)

        self.create_notification(
            "Currently snoozed",
            snoozed_until=timezone.now() + timedelta(hours=2),
        )
        self.create_notification(
            "Expired snooze",
            snoozed_until=timezone.now() - timedelta(minutes=5),
        )
        self.create_notification("Never snoozed")

        response = self.client.get(
            reverse("notifications:list"),
            {"snooze": "not_snoozed"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Currently snoozed")
        self.assertContains(response, "Expired snooze")
        self.assertContains(response, "Never snoozed")

    def test_notification_list_displays_snooze_expiration(self):
        """An active snooze displays its expiration date and time."""
        self.client.force_login(self.user)

        until = timezone.now() + timedelta(hours=2)

        notification = self.create_notification(
            "Snoozed projector",
            snoozed_until=until,
        )

        response = self.client.get(
            reverse("notifications:list"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Snoozed until")
        self.assertContains(
            response,
            timezone.localtime(until).strftime("%b"),
        )

    def test_notification_list_identifies_expired_snoozes(self):
        """An expired snooze is identified as expired, not active."""
        self.client.force_login(self.user)

        self.create_notification(
            "Expired projector snooze",
            snoozed_until=timezone.now() - timedelta(minutes=5),
        )

        response = self.client.get(
            reverse("notifications:list"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Snooze expired")
        self.assertNotContains(response, "Snoozed until")

    def test_notification_list_pagination_preserves_snooze_filter(self):
        """Moving between pages retains the selected snooze filter."""
        self.client.force_login(self.user)

        for number in range(30):
            self.create_notification(
                f"Snoozed notification {number:02d}",
                snoozed_until=timezone.now() + timedelta(hours=2),
            )

        response = self.client.get(
            reverse("notifications:list"),
            {"snooze": "snoozed"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "snooze=snoozed")
        self.assertContains(response, "Next")

    def test_invalid_snooze_filter_defaults_to_all(self):
        """Invalid snooze filter values do not exclude notifications."""
        self.client.force_login(self.user)

        self.create_notification("Available notification")

        response = self.client.get(
            reverse("notifications:list"),
            {"snooze": "invalid-value"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Available notification")
        self.assertEqual(
            response.context["selected_snooze"],
            "all",
        )
