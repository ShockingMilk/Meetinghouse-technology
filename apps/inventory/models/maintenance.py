"""Maintenance history and recurring inspection schedules."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class MaintenanceActivityType(models.TextChoices):
    INSPECTION = 'inspection', 'Inspection'
    PREVENTIVE = 'preventive', 'Preventive maintenance'
    CLEANING = 'cleaning', 'Cleaning'
    TROUBLESHOOTING = 'troubleshooting', 'Troubleshooting'
    REPAIR = 'repair', 'Repair'
    REPLACEMENT = 'replacement', 'Replacement'
    INSTALLATION = 'installation', 'Installation'
    OTHER = 'other', 'Other'


class MaintenanceResult(models.TextChoices):
    WORKING = 'working', 'Working normally'
    ATTENTION = 'attention', 'Needs attention'
    OFFLINE = 'offline', 'Offline'
    REPAIR_COMPLETED = 'repair_completed', 'Repair completed'
    UNABLE_TO_VERIFY = 'unable_to_verify', 'Unable to verify'
    NOT_APPLICABLE = 'not_applicable', 'Not applicable'

class MaintenanceRecord(models.Model):
    '''A maintenance, test, or repair record for an asset'''

    asset = models.ForeignKey(
        'inventory.Asset',
        on_delete=models.PROTECT,
        related_name='maintenance_records'
    )

    performed_at = models.DateTimeField()

    performed_by = models.CharField(
        max_length=150,
    )

    maintenance_type = models.CharField(
        max_length=100,
        choices=MaintenanceActivityType.choices,
    )

    description = models.TextField()

    result = models.CharField(
        max_length=200,
        choices=MaintenanceResult.choices,
        default=MaintenanceResult.UNABLE_TO_VERIFY,
    )

    action_taken = models.TextField(default='')
    materials_used = models.TextField(blank=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])

    follow_up_required = models.BooleanField(default=False)

    follow_up_notes = models.TextField(blank=True, verbose_name='Follow-up description')
    follow_up_date = models.DateField(null=True, blank=True)
    resolved_at = models.DateField(null=True, blank=True, verbose_name='Resolution date')
    resolution_notes = models.TextField(blank=True)
    schedule = models.ForeignKey(
        'inventory.MaintenanceSchedule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_records',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-performed_at', '-created_at']

    def __str__(self) -> str:
        '''Describe the maintenance record'''
        return f'{self.asset.inventory_number} - {self.maintenance_type}'

    @property
    def is_resolved(self):
        return bool(self.follow_up_required and self.resolved_at)


class MaintenanceSchedule(models.Model):
    """User-managed recurring inspection or maintenance plan."""

    asset = models.ForeignKey(
        'inventory.Asset',
        on_delete=models.PROTECT,
        related_name='maintenance_schedules',
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    activity_type = models.CharField(max_length=30, choices=MaintenanceActivityType.choices, default=MaintenanceActivityType.INSPECTION)
    interval_months = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(60)])
    starts_on = models.DateField(default=timezone.localdate, help_text='First due date; later dates follow the previous completed inspection.')
    enabled = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('asset__inventory_number', 'name')

    def __str__(self):
        return f'{self.asset.inventory_number} — {self.name}'
