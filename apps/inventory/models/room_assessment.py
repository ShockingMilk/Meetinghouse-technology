"""Historical room technology assessments."""

from django.db import models
from django.utils import timezone

from .assessment import AssessmentStatus
from .room import Room


class RoomAssessmentType(models.TextChoices):
    """Scope of a room technology assessment."""

    FULL = "full", "Full assessment"
    FOCUSED = "focused", "Focused assessment"


class RoomAssessmentArea(models.TextChoices):
    """Technology areas that can be assessed in a room."""

    AUDIO = "audio", "Audio"
    VIDEO = "video", "Video"
    NETWORK = "network", "Network"
    PRINTING = "printing", "Printing"
    ASSISTIVE_LISTENING = "assistive_listening", "Assistive listening"
    POWER = "power", "Power"


class RoomAssessment(models.Model):
    """A dated, append-only assessment of technology in an individual room."""

    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name="assessments",
    )
    assessment_date = models.DateField(default=timezone.localdate)
    assessed_by = models.CharField(max_length=150, blank=True)

    assessment_type = models.CharField(
        max_length=20,
        choices=RoomAssessmentType.choices,
        default=RoomAssessmentType.FULL,
    )
    assessed_areas = models.JSONField(
        default=list,
        blank=True,
        help_text="Technology areas explicitly included in this assessment.",
    )

    overall_status = models.CharField(
        max_length=20,
        choices=AssessmentStatus.choices,
        default=AssessmentStatus.UNKNOWN,
    )

    audio_status = models.CharField(
        max_length=20,
        choices=AssessmentStatus.choices,
        default=AssessmentStatus.UNKNOWN,
    )
    audio_notes = models.TextField(blank=True)

    video_status = models.CharField(
        max_length=20,
        choices=AssessmentStatus.choices,
        default=AssessmentStatus.UNKNOWN,
    )
    video_notes = models.TextField(blank=True)

    network_status = models.CharField(
        max_length=20,
        choices=AssessmentStatus.choices,
        default=AssessmentStatus.UNKNOWN,
    )
    network_notes = models.TextField(blank=True)

    printing_status = models.CharField(
        max_length=20,
        choices=AssessmentStatus.choices,
        default=AssessmentStatus.UNKNOWN,
    )
    printing_notes = models.TextField(blank=True)

    assistive_listening_status = models.CharField(
        max_length=20,
        choices=AssessmentStatus.choices,
        default=AssessmentStatus.UNKNOWN,
    )
    assistive_listening_notes = models.TextField(blank=True)

    power_status = models.CharField(
        max_length=20,
        choices=AssessmentStatus.choices,
        default=AssessmentStatus.UNKNOWN,
    )
    power_notes = models.TextField(blank=True)

    notes = models.TextField(blank=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    AREA_FIELDS = {
        RoomAssessmentArea.AUDIO: ("audio_status", "audio_notes"),
        RoomAssessmentArea.VIDEO: ("video_status", "video_notes"),
        RoomAssessmentArea.NETWORK: ("network_status", "network_notes"),
        RoomAssessmentArea.PRINTING: ("printing_status", "printing_notes"),
        RoomAssessmentArea.ASSISTIVE_LISTENING: (
            "assistive_listening_status",
            "assistive_listening_notes",
        ),
        RoomAssessmentArea.POWER: ("power_status", "power_notes"),
    }

    @property
    def unassessed_areas(self):
        """Return areas excluded from this assessment's recorded scope."""
        assessed = set(self.assessed_areas or [])
        return [
            (value, label)
            for value, label in RoomAssessmentArea.choices
            if value not in assessed
        ]

    @property
    def assessed_area_details(self):
        """Return status and notes only for areas included in this assessment."""
        details = []
        for area, label in RoomAssessmentArea.choices:
            if area not in (self.assessed_areas or []):
                continue

            status_field, notes_field = self.AREA_FIELDS[area]
            details.append(
                {
                    "key": area,
                    "label": label,
                    "status": getattr(self, status_field),
                    "status_display": getattr(self, f"get_{status_field}_display")(),
                    "notes": getattr(self, notes_field),
                }
            )
        return details

    class Meta:
        ordering = ["-assessment_date", "-created_at"]
        verbose_name = "Room Assessment"
        verbose_name_plural = "Room Assessments"

    def __str__(self) -> str:
        """Return a readable assessment description."""
        return f"{self.room.name} assessment ({self.assessment_date})"
