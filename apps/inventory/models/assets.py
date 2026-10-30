'''Building technology asset models'''
import uuid
from django.db import models

class AssetCategory(models.TextChoices):
    '''Broad equipment categories'''

    AUDIO = 'audio', 'Audio'
    ASSISTIVE_LISTENING = 'assistive_listening', 'Assistive Listening'
    CABLING = 'cabling', 'Cabling'
    COMPUTING = 'computing', 'Computing'
    NETWORK = 'network', 'Network'
    POWER = 'power', 'Power'
    PRINTER = 'printer', 'PRINTER'
    VIDEO = 'video', 'Video'
    OTHER = 'other', 'Other'

class AssetOwnership(models.TextChoices):
    '''Equipment ownership classification'''

    FMG = 'FMG', 'FMG Owned'
    LOCAL = 'local', 'Locally Managed'
    UNKNOWN = 'unknown', 'Unknown - Verify Ownership'

class AssetCondition(models.TextChoices):
    '''Physical and operation condition'''

    NEW = 'new', 'New'
    GOOD = 'good', 'Good'
    FAIR = 'fair', 'Fair'
    POOR = 'poor', 'POOR'
    FAILED = 'failed', 'Failed'
    UNKNOWN = 'unknown', 'Unknown'

class AssetStatus(models.TextChoices):
    '''Lifecycle status'''

    ACTIVE = 'active', 'Active'
    STORED = 'stored', 'Stored'
    UNDER_REPAIR = 'under_repair', 'Under Repair'
    RETIRED = 'retired', 'Retired'
    PLANNED = 'planned', 'Planned'
    UNKNOWN = 'unknown', 'Unknown'

class Asset(models.Model):
    '''A physical or logical technology asset in the building'''

    asset_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    inventory_number = models.CharField(
        max_length=30,
        unique=True,
    )

    name = models.CharField(max_length=150)

    category = models.CharField(
        max_length=30,
        choices=AssetCategory.choices,
        default=AssetCategory.OTHER,
    )

    manufacturer = models.CharField(
        max_length=100,
        blank=True,
    )

    model_number = models.CharField(
        max_length=100,
        blank=True,
    )

    serial_number = models.CharField(
        max_length=150,
        blank=True,
    )

    ownership = models.CharField(
        max_length=20,
        choices=AssetOwnership.choices,
        default=AssetOwnership.UNKNOWN,
    )

    condition = models.CharField(
        max_length=20,
        choices=AssetCondition.choices,
        default=AssetCondition.UNKNOWN,
    )

    status = models.CharField(
        max_length=20,
        choices=AssetStatus.choices,
        default=AssetStatus.UNKNOWN,
    )

    room = models.ForeignKey(
        'inventory.Room',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assets',
    )

    physical_location = models.CharField(
        max_length=200,
        blank=True,
    )

    responsible_party = models.CharField(
        max_length=150,
        blank=True,
    )

    installation_date = models.DateField(
        null=True,
        blank=True,
    )

    warranty_end_date = models.DateField(
        null=True,
        blank=True,
    )

    end_of_life_date = models.DateField(
        null=True,
        blank=True,
    )

    security_support_end_date = models.DateField(
        null=True,
        blank=True,
    )

    last_tested = models.DateField(
        null=True,
        blank=True,
    )

    documentation_url = models.URLField(
        blank=True,
    )

    funding_route = models.CharField(
        max_length=100,
        blank=True,
    )

    approval_status = models.CharField(
        max_length=100,
        blank=True,
    )

    replacement_estimate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    recommended_action = models.TextField(blank=True)
    specification = models.TextField(blank=True)
    dependencies = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['inventory_number']
        verbose_name = 'Technology Asset'
        verbose_name_plural = 'Technologyi Assets'

    def __str__(self) -> str:
        '''Return a readable inventory identifier'''
        return f'{self.inventory_number} - {self.name}'
