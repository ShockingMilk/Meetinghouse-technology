"""Forms for maintenance history, schedules, and reports."""

from django import forms
from django.utils import timezone

from .models import (
    Asset,
    AssetCategory,
    AssetStatus,
    MaintenanceRecord,
    MaintenanceResult,
    MaintenanceSchedule,
    Room,
)
from .services.maintenance import default_interval_months


class MaintenanceRecordForm(forms.ModelForm):
    """Short routine entry with optional costs and follow-up details."""

    authorization_acknowledged = forms.BooleanField(
        required=False,
        label='I will follow the equipment owner’s authorization requirements.',
    )

    class Meta:
        model = MaintenanceRecord
        fields = (
            'asset', 'schedule', 'performed_at', 'performed_by', 'maintenance_type',
            'result', 'description', 'action_taken', 'materials_used',
            'estimated_cost', 'actual_cost', 'follow_up_required', 'follow_up_notes',
            'follow_up_date',
        )
        widgets = {
            'performed_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'description': forms.Textarea(attrs={'rows': 3}),
            'action_taken': forms.Textarea(attrs={'rows': 3}),
            'materials_used': forms.Textarea(attrs={'rows': 2}),
            'follow_up_notes': forms.Textarea(attrs={'rows': 2}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
        }
        help_texts = {
            'description': 'Describe what was inspected or observed. Do not include passwords or network credentials.',
            'action_taken': 'Required. Record what was actually done, even if the action was only to inspect or report.',
            'follow_up_notes': 'Describe the issue or next step; do not include passwords or confidential network details.',
            'schedule': 'Choose the completed schedule so the next due date advances from this activity.',
        }

    def __init__(self, *args, asset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['performed_at'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S%z']
        self.fields['performed_at'].initial = self.initial.get('performed_at') or timezone.localtime()
        self.fields['result'].initial = self.initial.get('result') or MaintenanceResult.UNABLE_TO_VERIFY
        self.fields['action_taken'].required = True
        self.fields['asset'].queryset = Asset.objects.select_related('room').order_by('inventory_number')
        self.fields['schedule'].queryset = MaintenanceSchedule.objects.select_related('asset').filter(enabled=True).order_by('asset__inventory_number', 'name')
        selected_asset = asset
        raw_asset_id = self.data.get('asset') if self.is_bound else self.initial.get('asset')
        if raw_asset_id:
            try:
                selected_asset = Asset.objects.filter(pk=raw_asset_id).first()
            except (ValueError, TypeError):
                selected_asset = None
        if selected_asset:
            self.fields['asset'].initial = selected_asset.pk
            self.fields['schedule'].queryset = self.fields['schedule'].queryset.filter(asset=selected_asset)
            if selected_asset.ownership == 'FMG':
                self.fields['authorization_acknowledged'].help_text = 'For FMG-owned equipment, record observations or review only unless the required authorization is in place.'
        if self.instance.pk:
            self.fields['schedule'].queryset = MaintenanceSchedule.objects.filter(asset=self.instance.asset).order_by('name')

    def clean(self):
        cleaned = super().clean()
        schedule = cleaned.get('schedule')
        asset = cleaned.get('asset')
        if schedule and asset and schedule.asset_id != asset.pk:
            self.add_error('schedule', 'Choose a schedule belonging to this equipment.')
        if schedule and cleaned.get('maintenance_type') and schedule.activity_type != cleaned['maintenance_type']:
            self.add_error('schedule', 'Choose a schedule with the same activity type as this completed work.')
        if asset and asset.ownership == 'FMG' and not cleaned.get('authorization_acknowledged'):
            self.add_error('authorization_acknowledged', 'Confirm the authorization boundary before recording work for FMG-owned equipment.')
        if cleaned.get('follow_up_required') and not cleaned.get('follow_up_notes'):
            self.add_error('follow_up_notes', 'Describe the issue or next action when follow-up is required.')
        return cleaned


class MaintenanceResolutionForm(forms.Form):
    """Mark a follow-up resolved with a date and a brief outcome."""

    resolved_at = forms.DateField(initial=timezone.localdate, widget=forms.DateInput(attrs={'type': 'date'}), label='Resolution date')
    resolution_notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label='Resolution notes')


class MaintenanceScheduleForm(forms.ModelForm):
    """Create or adjust an explicit schedule; never auto-assign one."""

    authorization_acknowledged = forms.BooleanField(
        required=False,
        label='I will follow the equipment owner’s authorization requirements.',
    )

    class Meta:
        model = MaintenanceSchedule
        fields = ('asset', 'name', 'description', 'activity_type', 'interval_months', 'starts_on', 'enabled', 'notes')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'starts_on': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, asset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['asset'].queryset = Asset.objects.select_related('room').order_by('inventory_number')
        if asset:
            self.fields['asset'].initial = asset.pk
            self.fields['interval_months'].initial = default_interval_months(asset)
            if asset.ownership == 'FMG':
                self.fields['authorization_acknowledged'].help_text = 'For FMG-owned equipment, record observations or review dates only unless the required authorization is in place.'
        if self.instance.pk:
            self.fields['asset'].disabled = True
        self.fields['interval_months'].help_text = 'Choose a recurring calendar-month interval. Suggested defaults are planning aids, not policy.'
        self.fields['interval_months'].widget.attrs.update({'min': 1, 'max': 60, 'step': 1})

    def clean(self):
        cleaned = super().clean()
        asset = cleaned.get('asset')
        if asset and asset.ownership == 'FMG' and not cleaned.get('authorization_acknowledged'):
            self.add_error('authorization_acknowledged', 'Confirm the authorization boundary before scheduling work for FMG-owned equipment.')
        return cleaned


class MaintenanceReportFilterForm(forms.Form):
    REPORT_CHOICES = (
        ('history', 'Maintenance history'),
        ('followups', 'Open follow-ups'),
        ('overdue', 'Overdue inspections'),
        ('lifecycle', 'Lifecycle review'),
        ('replacement', 'Replacement planning'),
    )
    report = forms.ChoiceField(choices=REPORT_CHOICES, required=False, initial='history')
    asset = forms.ModelChoiceField(queryset=Asset.objects.order_by('inventory_number'), required=False)
    room = forms.ModelChoiceField(queryset=Room.objects.order_by('name'), required=False)
    category = forms.ChoiceField(choices=(('', 'All categories'), *AssetCategory.choices), required=False)
    status = forms.ChoiceField(choices=(('', 'All equipment status'), *AssetStatus.choices), required=False)
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('date_from'), cleaned.get('date_to')
        if start and end and end < start:
            self.add_error('date_to', 'End date must be on or after the start date.')
        return cleaned
