"""Forms for documenting connections, dependencies, specifications, and reviews."""

from django import forms
from django.core.exceptions import ValidationError

from .models import (
    Asset, AssetConnection, AssetDependency, AssetSpecification,
    CompatibilityVerification, DependencyType, ReplacementCompatibilityReview,
    SoftwareInstallation,
)
from .services.relationships import validate_connection, validate_dependency, validate_compatibility_verification


class AssetConnectionForm(forms.ModelForm):
    class Meta:
        model = AssetConnection
        fields = ('source', 'destination', 'connection_type', 'connection_medium', 'interface', 'signal_description', 'compatibility', 'is_required', 'last_verified', 'verification_notes', 'notes')
        widgets = {'last_verified': forms.DateInput(attrs={'type': 'date'}), 'verification_notes': forms.Textarea(attrs={'rows': 2}), 'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['source'].queryset = Asset.objects.select_related('room').order_by('inventory_number')
        self.fields['destination'].queryset = Asset.objects.select_related('room').order_by('inventory_number')

    def clean(self):
        data = super().clean()
        try:
            validate_connection(data.get('source').pk if data.get('source') else None, data.get('destination').pk if data.get('destination') else None)
        except ValidationError as error:
            self.add_error('destination', error)
        return data


class AssetDependencyForm(forms.ModelForm):
    class Meta:
        model = AssetDependency
        fields = ('dependent_asset', 'required_asset', 'required_software', 'external_service_name', 'dependency_type', 'is_required', 'description', 'failure_impact', 'verification_status', 'last_verified', 'notes')
        widgets = {'last_verified': forms.DateInput(attrs={'type': 'date'}), 'failure_impact': forms.Textarea(attrs={'rows': 2}), 'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        self.instance_pk = kwargs.get('instance').pk if kwargs.get('instance') else None
        super().__init__(*args, **kwargs)
        self.fields['dependent_asset'].queryset = Asset.objects.select_related('room').order_by('inventory_number')
        self.fields['required_asset'].queryset = Asset.objects.select_related('room').order_by('inventory_number')
        self.fields['required_software'].queryset = SoftwareInstallation.objects.select_related('host_asset').order_by('host_asset__inventory_number', 'name')
        self.fields['external_service_name'].help_text = 'Only fill this for an external service or capability; do not create a fake inventory asset.'

    def clean(self):
        data = super().clean()
        dependent, required = data.get('dependent_asset'), data.get('required_asset')
        external = (data.get('external_service_name') or '').strip()
        software = data.get('required_software')
        if sum((bool(required), bool(software), bool(external))) != 1:
            self.add_error('required_asset', 'Choose exactly one inventory asset, installed software record, or external service.')
        if software and data.get('dependency_type') != 'software':
            self.add_error('dependency_type', 'Select Software or workflow when linking an installed software record.')
        if dependent and required:
            try:
                validate_dependency(dependent.pk, required.pk, exclude_pk=self.instance_pk)
            except ValidationError as error:
                if hasattr(error, 'error_dict'):
                    for field, field_errors in error.error_dict.items():
                        for field_error in field_errors:
                            self.add_error(field if field in self.fields else None, field_error)
                else:
                    self.add_error('required_asset', error)
        return data


class AssetSpecificationForm(forms.ModelForm):
    class Meta:
        model = AssetSpecification
        fields = ('asset', 'category', 'name', 'value', 'verification_status', 'evidence_reference', 'notes')
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, asset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.locked_asset = asset
        self.fields['asset'].queryset = Asset.objects.order_by('inventory_number')
        if asset:
            self.fields.pop('asset')

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.locked_asset:
            instance.asset = self.locked_asset
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class CompatibilityVerificationForm(forms.ModelForm):
    class Meta:
        model = CompatibilityVerification
        fields = ('asset', 'related_asset', 'connection', 'proposed_replacement', 'requirement', 'outcome', 'method', 'evidence_reference', 'verified_by', 'verified_on', 'limitations', 'notes')
        widgets = {'verified_on': forms.DateInput(attrs={'type': 'date'}), 'limitations': forms.Textarea(attrs={'rows': 2}), 'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, asset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.locked_asset = asset
        self.fields['asset'].queryset = Asset.objects.order_by('inventory_number')
        self.fields['related_asset'].queryset = Asset.objects.order_by('inventory_number')
        if asset:
            self.fields.pop('asset')
            self.fields['related_asset'].queryset = Asset.objects.exclude(pk=asset.pk).order_by('inventory_number')

    def clean(self):
        data = super().clean()
        instance = self.instance
        if self.locked_asset:
            instance.asset = self.locked_asset
        for field in ('asset', 'related_asset', 'connection'):
            if field in data:
                setattr(instance, f'{field}_id' if field != 'connection' else 'connection_id', getattr(data[field], 'pk', None) if data[field] else None)
                if field == 'connection':
                    instance.connection = data[field]
        try:
            validate_compatibility_verification(instance)
        except ValidationError as error:
            for field, messages in error.error_dict.items():
                for message in messages:
                    self.add_error(field, message)
        return data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.locked_asset:
            instance.asset = self.locked_asset
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ReplacementReviewForm(forms.ModelForm):
    class Meta:
        model = ReplacementCompatibilityReview
        fields = ('proposed_name', 'proposed_manufacturer', 'proposed_model', 'requirements', 'status', 'limitations', 'notes')
        widgets = {'requirements': forms.Textarea(attrs={'rows': 3}), 'limitations': forms.Textarea(attrs={'rows': 3}), 'notes': forms.Textarea(attrs={'rows': 3})}

