"""Tests for creating and editing room records."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.inventory.models import Room, RoomPriority


class RoomEditTests(TestCase):
    """Verify room editing through the inventory interface."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="room-editor",
            password="test-password",
        )

        self.room = Room.objects.create(
            name="Cultural Hall",
            room_number="101",
            priority=RoomPriority.NORMAL,
            description="Original description",
            notes="Original notes",
        )

    def login(self):
        self.client.force_login(self.user)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(
            reverse("inventory:room_edit", args=[self.room.pk]),
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_edit_page_displays_existing_room_information(self):
        self.login()

        response = self.client.get(
            reverse("inventory:room_edit", args=[self.room.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Cultural Hall")
        self.assertContains(response, "Original description")
        self.assertContains(response, "Original notes")

    def test_valid_post_updates_existing_room(self):
        self.login()

        response = self.client.post(
            reverse("inventory:room_edit", args=[self.room.pk]),
            {
                "name": "Updated Cultural Hall",
                "room_number": "102",
                "priority": RoomPriority.PRIORITY,
                "description": "Updated description",
                "notes": "Updated notes",
            },
        )

        self.assertRedirects(
            response,
            reverse("inventory:room_detail", args=[self.room.pk]),
        )

        self.room.refresh_from_db()

        self.assertEqual(self.room.name, "Updated Cultural Hall")
        self.assertEqual(self.room.room_number, "102")
        self.assertEqual(self.room.priority, RoomPriority.PRIORITY)
        self.assertEqual(self.room.description, "Updated description")
        self.assertEqual(self.room.notes, "Updated notes")

        self.assertEqual(Room.objects.count(), 1)

    def test_invalid_post_does_not_update_room(self):
        self.login()

        response = self.client.post(
            reverse("inventory:room_edit", args=[self.room.pk]),
            {
                "name": "",
                "room_number": "102",
                "priority": RoomPriority.PRIORITY,
                "description": "Updated description",
                "notes": "Updated notes",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.room.refresh_from_db()

        self.assertEqual(self.room.name, "Cultural Hall")
        self.assertEqual(self.room.notes, "Original notes")

    def test_editing_room_does_not_create_a_second_room(self):
        self.login()

        self.client.post(
            reverse("inventory:room_edit", args=[self.room.pk]),
            {
                "name": "Cultural Hall",
                "room_number": "101",
                "priority": RoomPriority.NORMAL,
                "description": "Changed description",
                "notes": "Changed notes",
            },
        )

        self.assertEqual(Room.objects.count(), 1)
