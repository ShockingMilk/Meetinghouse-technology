'''Building-wide technology assessment'''
from django.db import models

class AssessmentStatus(models.TextChoices):
    '''Status of a building technology area'''

    WORKING = 'working', 'Working'
    NEEDS_REVIEW = 'needs_review', 'Needs Review'
    UNKNOWN = 'unknown', 'Unknown'
    OFFLINE = 'offline', 'Offline'
    NOT_APPLICABLE = 'not_applicable', 'Not Applicable'

class PrintingType(models.TextChoices):
    '''Building printing arrangement'''

    MULTIFUNCTION = 'multifunction', 'Multifunction'
    SINGLE = 'single', 'Single Function'
    UNKNOWN = 'unknown', 'Unknown'

class VideoSetup(models.TextChoices):
    '''Building video arrangement'''

    PORTABLE = 'portable', 'Portable'
    PERMANENT = 'permanent', 'Permanent'
    NONE = 'none', 'None'
    UNKNOWN = 'unknown', 'Unknown'

class FundingArrangement(models.TextChoices):
    '''General funding arrangement'''

    FMG = 'fmg', 'FMG'
    LOCAL = 'local', 'Local'
    MIXED = 'mixed', 'Mixed'
    UNKNOWN = 'unknown', 'Unknown'

class BuildingAssessment(models.Model):
    '''A dated snapshot of building technology conditions'''

    class BuildingRole(models.TextChoices):
        WARD = 'ward', 'Ward'
        STAKE = 'stake', 'Stake'
        OTHER = 'other', 'Other'

    class RoomAssessmentPriority(models.TextChoices):
        PRIORITY = 'priority', 'Priority'
        NORMAL = 'normal', 'Normal'
        LOW = 'low', 'Low'
        UNKNOWN = 'unknown', 'Unknown'

    building_role = models.CharField(
        max_length=20,
        choices=BuildingRole.choices,
        default=BuildingRole.WARD,
    )

    audio_status = models.CharField(
        max_length=20,
        choices=AssessmentStatus.choices,
        default=AssessmentStatus.UNKNOWN,
    )

    network_status = models.CharField(
        max_length=20,
        choices=AssessmentStatus.choices,
        default=AssessmentStatus.UNKNOWN,
    )

    printing_type = models.CharField(
        max_length=20,
        choices=PrintingType.choices,
        default=PrintingType.UNKNOWN,
    )

    video_setup = models.CharField(
        max_length=20,
        choices=VideoSetup.choices,
        default=VideoSetup.UNKNOWN,
    )

    local_management_status = models.CharField(
        max_length=20,
        choices=AssessmentStatus.choices,
        default=AssessmentStatus.UNKNOWN,
    )

    funding_arrangement = models.CharField(
        max_length=20,
        choices=FundingArrangement.choices,
        default=FundingArrangement.UNKNOWN,
    )

    room_priority = models.CharField(
        max_length=20,
        choices=RoomAssessmentPriority.choices,
        default=RoomAssessmentPriority.NORMAL,
    )

    # Clerk computers are deliberately outside this project's scope
    clerk_computers_in_scope = models.BooleanField(default=False)

    assessment_date = models.DateField(auto_now_add=True)

    assessed_by = models.CharField(
        max_length=150,
        blank=True,
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-assessment_date']

    def __str__(self) -> str:
        '''Describe the assessment'''
        return f'{self.building_role} assessment - {self.assessment_date}'
