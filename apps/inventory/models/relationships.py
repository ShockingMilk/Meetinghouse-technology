"""Structured specifications, operational dependencies, and compatibility reviews."""

from django.core.exceptions import ValidationError
from django.db import models


class DependencyType(models.TextChoices):
    EQUIPMENT = 'equipment', 'Equipment'
    SERVICE = 'service', 'External service or capability'
    SOFTWARE = 'software', 'Software or workflow'
    OTHER = 'other', 'Other'


class DependencyVerification(models.TextChoices):
    UNKNOWN = 'unknown', 'Unknown / not verified'
    VERIFIED = 'verified', 'Verified'
    NEEDS_REVIEW = 'needs_review', 'Needs review'
    INCOMPATIBLE = 'incompatible', 'Known issue'


class SpecificationCategory(models.TextChoices):
    PHYSICAL = 'physical', 'Physical interface'
    SIGNAL = 'signal', 'Signal and media'
    VIDEO = 'video', 'Video'
    AUDIO = 'audio', 'Audio'
    POWER = 'power', 'Power'
    SOFTWARE = 'software', 'Software'
    NETWORK = 'network', 'Network'
    OTHER = 'other', 'Other'


class SpecificationVerification(models.TextChoices):
    UNKNOWN = 'unknown', 'Unknown / not verified'
    VERIFIED = 'verified', 'Verified'
    NEEDS_REVIEW = 'needs_review', 'Needs review'


class VerificationOutcome(models.TextChoices):
    VERIFIED = 'verified', 'Compatible — verified'
    LIMITED = 'limited', 'Compatible with limitations'
    INCOMPATIBLE = 'incompatible', 'Incompatible'
    UNKNOWN = 'unknown', 'Unknown / not verified'


class VerificationMethod(models.TextChoices):
    TEST = 'test', 'Physical testing'
    MANUFACTURER = 'manufacturer', 'Manufacturer documentation'
    SPEC_REVIEW = 'spec_review', 'Technical specification review'
    VENDOR = 'vendor', 'Vendor confirmation'
    OTHER = 'other', 'Other'


class ReplacementReviewStatus(models.TextChoices):
    NOT_REVIEWED = 'not_reviewed', 'Not reviewed'
    RESEARCH = 'research', 'Research required'
    TESTING = 'testing', 'Testing required'
    COMPATIBLE = 'compatible', 'Compatible'
    LIMITED = 'limited', 'Compatible with limitations'
    INCOMPATIBLE = 'incompatible', 'Incompatible'


class AssetDependency(models.Model):
    """An operational requirement from one asset to equipment or an external service."""

    dependent_asset = models.ForeignKey('inventory.Asset', on_delete=models.PROTECT, related_name='dependencies_out')
    required_asset = models.ForeignKey('inventory.Asset', on_delete=models.PROTECT, null=True, blank=True, related_name='dependencies_in')
    required_software = models.ForeignKey('inventory.SoftwareInstallation', on_delete=models.PROTECT, null=True, blank=True, related_name='operational_dependencies')
    external_service_name = models.CharField(max_length=150, blank=True, help_text='Use for an external service or capability; do not create a fake inventory item.')
    dependency_type = models.CharField(max_length=20, choices=DependencyType.choices, default=DependencyType.EQUIPMENT)
    is_required = models.BooleanField(default=True)
    description = models.CharField(max_length=240)
    failure_impact = models.TextField(blank=True)
    verification_status = models.CharField(max_length=20, choices=DependencyVerification.choices, default=DependencyVerification.UNKNOWN)
    last_verified = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('dependent_asset__inventory_number', 'description')
        constraints = [
            models.CheckConstraint(condition=(
                models.Q(required_asset__isnull=False, required_software__isnull=True, external_service_name='')
                | models.Q(required_asset__isnull=True, required_software__isnull=False, external_service_name='')
                | models.Q(required_asset__isnull=True, required_software__isnull=True) & ~models.Q(external_service_name='')
            ), name='dependency_exactly_one_target'),
            models.CheckConstraint(condition=models.Q(required_asset__isnull=True) | ~models.Q(required_asset=models.F('dependent_asset')), name='dependency_not_self'),
            models.UniqueConstraint(fields=('dependent_asset', 'required_asset', 'description'), condition=models.Q(required_asset__isnull=False), name='unique_asset_dependency'),
            models.UniqueConstraint(fields=('dependent_asset', 'external_service_name', 'description'), condition=models.Q(required_asset__isnull=True, required_software__isnull=True), name='unique_service_dependency'),
            models.UniqueConstraint(fields=('dependent_asset', 'required_software', 'description'), condition=models.Q(required_software__isnull=False), name='unique_software_dependency'),
        ]
        indexes = [models.Index(fields=('verification_status', 'is_required'))]

    def clean(self):
        super().clean()
        errors = {}
        targets = sum((bool(self.required_asset_id), bool(self.required_software_id), bool(self.external_service_name.strip())))
        if targets != 1:
            errors['required_asset'] = 'Choose exactly one inventory asset, installed software record, or external service.'
        if self.dependent_asset_id and self.required_asset_id == self.dependent_asset_id:
            errors['required_asset'] = 'An asset cannot depend on itself.'
        if self.required_software_id and self.dependency_type != DependencyType.SOFTWARE:
            errors['dependency_type'] = 'Select Software or workflow when linking an installed software record.'
        dependency_target_id = self.required_asset_id or (self.required_software.host_asset_id if self.required_software_id else None)
        if self.dependent_asset_id and dependency_target_id and dependency_target_id != self.dependent_asset_id:
            from apps.inventory.services.relationships import validate_dependency
            try:
                validate_dependency(self.dependent_asset_id, dependency_target_id, exclude_pk=self.pk)
            except ValidationError as error:
                errors.update(error.message_dict)
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        target = self.required_asset or self.required_software or self.external_service_name
        return f'{self.dependent_asset.inventory_number} depends on {target}'


class AssetSpecification(models.Model):
    """One category-relevant technical fact, with explicit verification state."""

    asset = models.ForeignKey('inventory.Asset', on_delete=models.CASCADE, related_name='specifications')
    category = models.CharField(max_length=20, choices=SpecificationCategory.choices, default=SpecificationCategory.OTHER)
    name = models.CharField(max_length=100, help_text='For example: connector, supported resolution, voltage, protocol, or operating system.')
    value = models.CharField(max_length=240, blank=True, help_text='Leave blank when unknown; do not infer values from connector names.')
    verification_status = models.CharField(max_length=20, choices=SpecificationVerification.choices, default=SpecificationVerification.UNKNOWN)
    evidence_reference = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('category', 'name')
        constraints = [models.UniqueConstraint(fields=('asset', 'category', 'name'), name='unique_asset_specification')]
        indexes = [models.Index(fields=('category', 'verification_status'))]

    def __str__(self):
        return f'{self.asset.inventory_number}: {self.name}'


class ReplacementCompatibilityReview(models.Model):
    """Planning record for a proposed replacement, separate from active inventory."""

    asset = models.OneToOneField('inventory.Asset', on_delete=models.CASCADE, related_name='compatibility_review')
    proposed_name = models.CharField(max_length=150, blank=True)
    proposed_manufacturer = models.CharField(max_length=100, blank=True)
    proposed_model = models.CharField(max_length=100, blank=True)
    requirements = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=ReplacementReviewStatus.choices, default=ReplacementReviewStatus.NOT_REVIEWED)
    limitations = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Replacement review for {self.asset.inventory_number}'


class CompatibilityVerification(models.Model):
    """Appendable evidence about a connection or proposed replacement check."""

    asset = models.ForeignKey('inventory.Asset', on_delete=models.CASCADE, related_name='compatibility_verifications')
    related_asset = models.ForeignKey('inventory.Asset', on_delete=models.PROTECT, null=True, blank=True, related_name='related_compatibility_verifications')
    connection = models.ForeignKey('inventory.AssetConnection', on_delete=models.SET_NULL, null=True, blank=True, related_name='verifications')
    proposed_replacement = models.CharField(max_length=200, blank=True)
    requirement = models.CharField(max_length=240)
    outcome = models.CharField(max_length=20, choices=VerificationOutcome.choices, default=VerificationOutcome.UNKNOWN)
    method = models.CharField(max_length=20, choices=VerificationMethod.choices, default=VerificationMethod.OTHER)
    evidence_reference = models.URLField(blank=True)
    verified_by = models.CharField(max_length=150, blank=True)
    verified_on = models.DateField(null=True, blank=True)
    limitations = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-verified_on', '-created_at')
        indexes = [models.Index(fields=('outcome', 'verified_on'))]

    def clean(self):
        super().clean()
        if self.related_asset_id == self.asset_id:
            raise ValidationError({'related_asset': 'Choose a different related asset.'})
        if self.connection_id and self.asset_id and self.connection and self.asset_id not in (self.connection.source_id, self.connection.destination_id):
            raise ValidationError({'connection': 'The selected connection must involve the reviewed asset.'})

    def __str__(self):
        return f'{self.asset.inventory_number}: {self.requirement} ({self.get_outcome_display()})'
