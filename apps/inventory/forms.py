"""Forms for guided building technology inventory entry."""

from django import forms

from .models import (
    Asset,
    AssetCategory,
    AssetCondition,
    AssetOwnership,
    AssetStatus,
    ReplacementRecommendation,
    AssetConnection,
    ConnectionType,
    ConnectionMedium,
    CompatibilityStatus,
    Room,
    RoomAssessment,
    RoomPriority,
)


class RoomSelectionForm(forms.Form):
    """Choose the room or area where the equipment is located."""

    room = forms.ModelChoiceField(
        queryset=Room.objects.order_by("name"),
        required=False,
        empty_label="Not assigned yet",
    )


class RoomForm(forms.ModelForm):
    """Create or update a building room."""

    class Meta:
        model = Room
        fields = [
            "name",
            "room_number",
            "priority",
            "description",
            "notes",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }


class RoomQuickAddForm(RoomForm):
    """Add a room without leaving the equipment wizard."""


class AssetCategoryForm(forms.Form):
    """Choose a category for this equipment record."""

    category = forms.ChoiceField(
        choices=AssetCategory.choices,
        widget=forms.RadioSelect,
    )


class AssetGeneralForm(forms.Form):
    """Collect the equipment's identity and physical location."""

    inventory_number = forms.CharField(max_length=30, label="Inventory number")
    name = forms.CharField(max_length=150, label="Equipment name")
    manufacturer = forms.CharField(max_length=100, required=False)
    model_number = forms.CharField(max_length=100, required=False, label="Model")
    serial_number = forms.CharField(max_length=150, required=False)
    physical_location = forms.CharField(
        max_length=200,
        required=False,
        help_text="Optional detail such as a cabinet, rack, or shelf.",
    )

    def __init__(self, *args, asset_pk=None, **kwargs):
        self.asset_pk = asset_pk
        super().__init__(*args, **kwargs)

    def clean_inventory_number(self):
        inventory_number = self.cleaned_data["inventory_number"].strip()
        matches = Asset.objects.filter(inventory_number__iexact=inventory_number)
        if self.asset_pk:
            matches = matches.exclude(pk=self.asset_pk)
        if matches.exists():
            raise forms.ValidationError("This inventory number is already in use.")
        return inventory_number


class AssetTechnicalForm(forms.Form):
    """Collect lifecycle dates, references, and technical notes."""

    installation_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    warranty_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_of_life_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    security_support_end_date = forms.DateField(
        required=False,
        label="Security support end date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    last_tested = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    documentation_url = forms.URLField(required=False, label="Documentation link")
    funding_route = forms.CharField(max_length=100, required=False)
    approval_status = forms.CharField(max_length=100, required=False)
    replacement_estimate = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=0,
        label="Estimated replacement cost",
    )
    recommended_action = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    replacement_recommendation = forms.ChoiceField(
        choices=(
            ("", "No recommendation recorded"),
            *ReplacementRecommendation.choices,
        ),
        required=False,
        help_text="A planning recommendation only. It does not approve a purchase or change the equipment status.",
    )
    specification = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    dependencies = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Other equipment or services this item depends on.",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class AssetResponsibilityForm(forms.Form):
    """Record ownership, condition, lifecycle status, and responsibility."""

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


class AssetDetailsForm(AssetGeneralForm):
    """Collect common identity, lifecycle, ownership, and notes in one step."""

    CATEGORY_DETAIL_HELP = {
        AssetCategory.VIDEO: "For example: camera type, video connection, power, mounting, or control method.",
        AssetCategory.AUDIO: "For example: speaker or microphone type, signal connection, power, or mounting.",
        AssetCategory.PRINTER: "For example: printer type, supported media, or connection method.",
        AssetCategory.NETWORK: "For example: equipment role, port count, or uplink type. Do not record credentials or passwords.",
        AssetCategory.COMPUTING: "For example: device role, operating system, or installed function. Do not record passwords.",
    }

    def __init__(self, *args, asset_pk=None, category=None, **kwargs):
        super().__init__(*args, asset_pk=asset_pk, **kwargs)
        self.fields.update(AssetTechnicalForm.base_fields)
        self.fields.update(AssetResponsibilityForm.base_fields)
        self.fields["specification"].label = "Category-specific details"
        self.fields["specification"].help_text = self.CATEGORY_DETAIL_HELP.get(
            category,
            "Add relevant details for this equipment category. Do not include passwords, network credentials, or confidential building information.",
        )


class AssetConnectionsForm(forms.Form):
    """Optionally connect the new equipment to existing inventory records."""

    connected_assets = forms.ModelMultipleChoiceField(
        queryset=Asset.objects.order_by("inventory_number"),
        required=False,
        label="Related equipment",
        help_text="Select existing equipment. Connections do not create duplicate records.",
        widget=forms.CheckboxSelectMultiple,
    )
    connection_direction = forms.ChoiceField(
        choices=(
            ("outgoing", "Equipment sends to selected items"),
            ("incoming", "Selected items send to this equipment"),
        ),
        required=False,
        initial="outgoing",
        label="Direction",
    )
    connection_type = forms.ChoiceField(
        choices=ConnectionType.choices, required=False, initial=ConnectionType.OTHER
    )
    connection_medium = forms.ChoiceField(
        choices=ConnectionMedium.choices, required=False, initial=ConnectionMedium.OTHER
    )
    interface = forms.CharField(max_length=100, required=False)
    compatibility = forms.ChoiceField(
        choices=CompatibilityStatus.choices,
        required=False,
        initial=CompatibilityStatus.UNKNOWN,
    )
    connection_notes = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2})
    )

    def __init__(self, *args, asset_pk=None, **kwargs):
        super().__init__(*args, **kwargs)
        if asset_pk:
            self.fields["connected_assets"].queryset = Asset.objects.exclude(
                pk=asset_pk
            ).order_by("inventory_number")


class RoomAssessmentForm(forms.ModelForm):
    """Create a historical assessment for one room."""

    class Meta:
        model = RoomAssessment
        fields = (
            "assessment_date",
            "assessed_by",
            "overall_status",
            "audio_status",
            "audio_notes",
            "video_status",
            "video_notes",
            "network_status",
            "network_notes",
            "printing_status",
            "printing_notes",
            "assistive_listening_status",
            "assistive_listening_notes",
            "power_status",
            "power_notes",
            "notes",
            "follow_up_required",
            "follow_up_notes",
        )
        widgets = {
            "assessment_date": forms.DateInput(attrs={"type": "date"}),
            "audio_notes": forms.Textarea(attrs={"rows": 3}),
            "video_notes": forms.Textarea(attrs={"rows": 3}),
            "network_notes": forms.Textarea(attrs={"rows": 3}),
            "printing_notes": forms.Textarea(attrs={"rows": 3}),
            "assistive_listening_notes": forms.Textarea(attrs={"rows": 3}),
            "power_notes": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 4}),
            "follow_up_notes": forms.Textarea(attrs={"rows": 3}),
        }


WIZARD_FORMS = {
    1: RoomSelectionForm,
    2: AssetCategoryForm,
    3: AssetDetailsForm,
    4: AssetConnectionsForm,
}

WIZARD_STEPS = {
    1: "Room",
    2: "Category",
    3: "Equipment details",
    4: "Connections",
    5: "Review and save",
}
