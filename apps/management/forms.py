"""Validated, report-specific filters for building management reports."""

from django import forms

from apps.inventory.models import (
    AssetCategory, AssetCondition, AssetOwnership, AssetStatus,
    CompatibilityStatus, MaintenanceActivityType, MaintenanceResult, ReplacementRecommendation, Room,
)
from .reporting import REPORTS


REPORT_FILTERS = {
    'inventory': ('room', 'category', 'ownership', 'status', 'condition'),
    'inventory-room': ('room', 'category', 'ownership', 'status', 'condition'),
    'inventory-category': ('room', 'ownership', 'status', 'condition'),
    'inventory-condition': ('room', 'category', 'ownership'),
    'stored': ('room', 'category', 'ownership'),
    'room-inventory': ('room', 'category', 'ownership', 'status', 'condition'),
    'assessment-history': ('room', 'date_from', 'date_to'),
    'assessment-coverage': ('room',), 'rooms-review': ('room',), 'rooms-unassessed': ('room',),
    'maintenance-history': ('room', 'category', 'ownership', 'activity', 'result', 'date_from', 'date_to'),
    'completed-inspections': ('room', 'category', 'ownership', 'result', 'date_from', 'date_to'),
    'open-followups': ('room', 'category', 'ownership', 'date_from', 'date_to'),
    'overdue-followups': ('room', 'category', 'ownership', 'date_from', 'date_to'),
    'inspection-schedules': ('room', 'category', 'ownership'),
    'overdue-inspections': ('room', 'category', 'ownership'),
    'warranty': ('room', 'category', 'ownership', 'date_from', 'date_to'),
    'security-support': ('room', 'category', 'ownership', 'date_from', 'date_to'),
    'end-of-life': ('room', 'category', 'ownership', 'date_from', 'date_to'),
    'replacements': ('room', 'category', 'ownership', 'replacement_priority'),
    'missing-lifecycle': ('room', 'category', 'ownership'),
    'connections': ('room', 'category', 'ownership', 'compatibility'),
    'incompatible': ('room', 'category', 'ownership'), 'unverified': ('room', 'category', 'ownership'),
    'dependencies': ('room', 'category', 'ownership', 'compatibility'),
    'verification-history': ('room', 'category', 'ownership', 'compatibility', 'date_from', 'date_to'),
    'replacement-reviews': ('room', 'category', 'ownership'),
    'ownership-fmg': ('room', 'category', 'status', 'condition'),
    'ownership-local': ('room', 'category', 'status', 'condition'),
    'ownership-unknown': ('room', 'category', 'status', 'condition'),
}


class BuildingReportFilterForm(forms.Form):
    report = forms.ChoiceField(choices=[(key, value[0]) for key, value in REPORTS.items()], widget=forms.Select(attrs={'onchange': 'this.form.requestSubmit()'}))
    room = forms.ModelChoiceField(queryset=Room.objects.order_by('name'), required=False)
    category = forms.ChoiceField(choices=[('', 'All categories'), *AssetCategory.choices], required=False)
    ownership = forms.ChoiceField(choices=[('', 'All ownership'), *AssetOwnership.choices], required=False)
    status = forms.ChoiceField(choices=[('', 'All statuses'), *AssetStatus.choices], required=False)
    condition = forms.ChoiceField(choices=[('', 'All conditions'), *AssetCondition.choices], required=False)
    activity = forms.ChoiceField(choices=[('', 'All activities'), *MaintenanceActivityType.choices], required=False)
    result = forms.ChoiceField(choices=[('', 'All results'), *MaintenanceResult.choices], required=False)
    compatibility = forms.ChoiceField(choices=[('', 'All compatibility states'), *CompatibilityStatus.choices, ('needs_review', 'Needs review')], required=False)
    replacement_priority = forms.ChoiceField(choices=[('', 'All recommendations'), *ReplacementRecommendation.choices], required=False)
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, report=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['report'].initial = report or 'inventory'
        selected_report = (self.data.get('report') if self.is_bound else report) or 'inventory'
        if selected_report not in REPORT_FILTERS:
            selected_report = 'inventory'
        allowed = set(REPORT_FILTERS[selected_report]) | {'report'}
        for name in list(self.fields):
            if name not in allowed:
                del self.fields[name]

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('date_from'), cleaned.get('date_to')
        if start and end and start > end:
            self.add_error('date_to', 'End date must be on or after start date.')
        return cleaned
