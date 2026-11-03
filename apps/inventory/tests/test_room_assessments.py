from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.inventory.forms import RoomAssessmentForm
from apps.inventory.models import (
    Asset,
    AssetCategory,
    AssessmentStatus,
    Room,
    RoomAssessment,
)


class RoomAssessmentModelTests(TestCase):
    def test_assessment_uses_room_and_keeps_history_ordered(self):
        room = Room.objects.create(name="Chapel")
        older = RoomAssessment.objects.create(
            room=room,
            assessment_date="2026-10-01",
            overall_status=AssessmentStatus.WORKING,
        )
        newer = RoomAssessment.objects.create(
            room=room,
            assessment_date="2026-11-02",
            overall_status=AssessmentStatus.NEEDS_REVIEW,
        )

        self.assertEqual(list(room.assessments.all()), [newer, older])
        self.assertEqual(str(newer), "Chapel assessment (2026-11-02)")

    def test_assessment_form_does_not_allow_changing_room(self):
        self.assertNotIn("room", RoomAssessmentForm().fields)


class RoomAssessmentViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="tech-admin",
            password="test-password",
        )
        self.room = Room.objects.create(name="Chapel", room_number="101")

    def test_room_pages_require_sign_in(self):
        response = self.client.get(reverse("inventory:room_list"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_room_list_shows_counts_latest_status_and_follow_up(self):
        Asset.objects.create(
            inventory_number="AUDIO-001",
            name="Chapel sound system",
            category=AssetCategory.AUDIO,
            room=self.room,
        )
        RoomAssessment.objects.create(
            room=self.room,
            overall_status=AssessmentStatus.NEEDS_REVIEW,
            follow_up_required=True,
            follow_up_notes="Check the wireless microphone.",
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("inventory:room_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chapel")
        self.assertContains(response, "Needs Review")
        self.assertContains(response, "Required")

    def test_room_detail_lists_assigned_assets_and_assessment_history(self):
        Asset.objects.create(
            inventory_number="AUDIO-001",
            name="Chapel sound system",
            category=AssetCategory.AUDIO,
            room=self.room,
        )
        RoomAssessment.objects.create(
            room=self.room,
            overall_status=AssessmentStatus.WORKING,
            notes="System checked before Sunday services.",
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("inventory:room_detail", args=[self.room.pk]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chapel sound system")
        self.assertContains(response, "System checked before Sunday services.")

    def test_assessment_create_appends_history_to_room_from_url(self):
        self.client.force_login(self.user)
        payload = {
            "assessment_date": "2026-11-02",
            "assessed_by": "Technology specialist",
            "overall_status": AssessmentStatus.NEEDS_REVIEW,
            "audio_status": AssessmentStatus.WORKING,
            "video_status": AssessmentStatus.UNKNOWN,
            "network_status": AssessmentStatus.UNKNOWN,
            "printing_status": AssessmentStatus.NOT_APPLICABLE,
            "assistive_listening_status": AssessmentStatus.UNKNOWN,
            "power_status": AssessmentStatus.WORKING,
            "follow_up_required": "on",
            "follow_up_notes": "Verify microphone battery.",
        }

        response = self.client.post(
            reverse("inventory:room_assessment_create", args=[self.room.pk]),
            payload,
        )

        self.assertRedirects(
            response,
            reverse("inventory:room_detail", args=[self.room.pk]),
        )
        assessment = RoomAssessment.objects.get()
        self.assertEqual(assessment.room, self.room)
        self.assertTrue(assessment.follow_up_required)

    def test_room_context_prefills_new_asset_draft(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("inventory:asset_wizard_start"),
            {"room": self.room.pk},
        )

        self.assertEqual(response.status_code, 302)
        from apps.inventory.models import AssetDraft
        draft = AssetDraft.objects.get(created_by=self.user).draft_data
        self.assertEqual(draft["room"], str(self.room.pk))

    def test_unassigned_inventory_filter_only_shows_unassigned_assets(self):
        Asset.objects.create(
            inventory_number="AUDIO-001",
            name="In chapel",
            category=AssetCategory.AUDIO,
            room=self.room,
        )
        Asset.objects.create(
            inventory_number="AUDIO-002",
            name="Unassigned system",
            category=AssetCategory.AUDIO,
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("inventory:asset_list"),
            {"room": "unassigned"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unassigned system")
        self.assertNotContains(response, "In chapel")
