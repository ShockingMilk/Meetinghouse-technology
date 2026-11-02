"""Historical room technology assessments."""

from django.db import models
from django.utils import timezone

from .assessment import AssessmentStatus
from .room import Room


class RoomAssessment(models.Model):
    """A dated assessment of technology in an individual room."""

    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name="assessments",
    )
    assessment_date = models.DateField(default=timezone.localdate)
    assessed_by = models.CharField(max_length=150, blank=True)

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

    class Meta:
        ordering = ["-assessment_date", "-created_at"]
        verbose_name = "Room Assessment"
        verbose_name_plural = "Room Assessments"

    def __str__(self) -> str:
        """Return a readable assessment description."""
        return f"{self.room.name} assessment ({self.assessment_date})"
