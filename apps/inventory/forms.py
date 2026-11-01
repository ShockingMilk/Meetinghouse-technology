'''Forms for guided building technology inventory entry.'''

from django import forms

from .models import (
    Asset,
    AssetCategory,
    AssetCondition,
    AssetOwnership,
    AssetStatus,
    Room,
    RoomPriority,
)


class RoomSelectionForm(forms.Form):
    '''Choose the room or area where the equipment is located.'''

    room = forms.ModelChoiceField(
        queryset=Room.objects.order_by('name'),
        required=False,
        empty_label='Not assigned yet',
    )


class RoomQuickAddForm(forms.ModelForm):
    '''Add a room without leaving the equipment wizard.'''

    class Meta:
        model = Room
        fields = ('name', 'room_number', 'priority', 'description')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }


class AssetCategoryForm(forms.Form):
    '''Choose a category for this equipment record.'''

    category = forms.ChoiceField(
        choices=AssetCategory.choices,
        widget=forms.RadioSelect,
    )


class AssetGeneralForm(forms.Form):
    '''Collect the equipment's identity and physical location.'''

    inventory_number = forms.CharField(max_length=30, label='Inventory number')
    name = forms.CharField(max_length=150, label='Equipment name')
    manufacturer = forms.CharField(max_length=100, required=False)
    model_number = forms.CharField(max_length=100, required=False, label='Model')
    serial_number = forms.CharField(max_length=150, required=False)
    physical_location = forms.CharField(
        max_length=200,
        required=False,
        help_text='Optional detail such as a cabinet, rack, or shelf.',
    )

    def __init__(self, *args, asset_pk=None, **kwargs):
        self.asset_pk = asset_pk
        super().__init__(*args, **kwargs)

    def clean_inventory_number(self):
        inventory_number = self.cleaned_data['inventory_number'].strip()
        matches = Asset.objects.filter(inventory_number__iexact=inventory_number)
        if self.asset_pk:
            matches = matches.exclude(pk=self.asset_pk)
        if matches.exists():
            raise forms.ValidationError('This inventory number is already in use.')
        return inventory_number


class AssetTechnicalForm(forms.Form):
    '''Collect lifecycle dates, references, and technical notes.'''

    installation_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    warranty_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    end_of_life_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    security_support_end_date = forms.DateField(
        required=False,
        label='Security support end date',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    last_tested = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    documentation_url = forms.URLField(required=False, label='Documentation link')
    funding_route = forms.CharField(max_length=100, required=False)
    approval_status = forms.CharField(max_length=100, required=False)
    replacement_estimate = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=0,
        label='Estimated replacement cost',
    )
    recommended_action = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    specification = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    dependencies = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Other equipment or services this item depends on.',
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )


class AssetResponsibilityForm(forms.Form):
    '''Record ownership, condition, lifecycle status, and responsibility.'''

    ownership = forms.ChoiceField(
        choices=AssetOwnership.choices,
        initial=AssetOwnership.UNKNOWN,
    )
    condition = forms.ChoiceField(
        choices=AssetCondition.choices,
        initial=AssetCondition.UNKNOWN,
    )
    status = forms.ChoiceField(
        choices=AssetStatus.choices,
        initial=AssetStatus.UNKNOWN,
    )
    responsible_party = forms.CharField(max_length=150, required=False)


WIZARD_FORMS = {
    1: RoomSelectionForm,
    2: AssetCategoryForm,
    3: AssetGeneralForm,
    4: AssetTechnicalForm,
    5: AssetResponsibilityForm,
}

WIZARD_STEPS = {
    1: 'Room',
    2: 'Category',
    3: 'Equipment details',
    4: 'Technical details',
    5: 'Responsibility',
    6: 'Review and save',
}
