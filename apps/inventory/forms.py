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
    RoomAssessmentType,
    RoomAssessmentArea,
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
    """Create a full or focused historical assessment for one room."""

    assessment_type = forms.ChoiceField(
        choices=RoomAssessmentType.choices,
        initial=RoomAssessmentType.FULL,
        widget=forms.RadioSelect,
    )

    assessed_areas = forms.MultipleChoiceField(
        choices=RoomAssessmentArea.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Areas included in this assessment",
    )

    AREA_FIELDS = {
        RoomAssessmentArea.AUDIO: ("audio_status", "audio_notes"),
        RoomAssessmentArea.VIDEO: ("video_status", "video_notes"),
        RoomAssessmentArea.NETWORK: ("network_status", "network_notes"),
        RoomAssessmentArea.PRINTING: ("printing_status", "printing_notes"),
        RoomAssessmentArea.ASSISTIVE_LISTENING: (
            "assistive_listening_status",
            "assistive_listening_notes",
        ),
        RoomAssessmentArea.POWER: ("power_status", "power_notes"),
    }

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        all_areas = list(RoomAssessmentArea.values)

        if self.instance and self.instance.pk:
            self.fields["assessment_type"].initial = self.instance.assessment_type
            self.fields["assessed_areas"].initial = self.instance.assessed_areas or []
        else:
            self.fields["assessed_areas"].initial = all_areas

        selected_areas = (
            (
                self.data.getlist("assessed_areas")
                if hasattr(self.data, "getlist")
                else self.data.get("assessed_areas", [])
            )
            if self.is_bound
            else self.fields["assessed_areas"].initial
        )

        # Status fields are required only when their area is included.
        for area, (status_field, notes_field) in self.AREA_FIELDS.items():
            included = area in selected_areas
            self.fields[status_field].required = included
            self.fields[notes_field].required = False

    def clean(self):
        cleaned_data = super().clean()

        assessment_type = cleaned_data.get("assessment_type")
        assessed_areas = cleaned_data.get("assessed_areas") or []

        if assessment_type == RoomAssessmentType.FULL:
            cleaned_data["assessed_areas"] = list(RoomAssessmentArea.values)

        elif assessment_type == RoomAssessmentType.FOCUSED:
            if not assessed_areas:
                self.add_error(
                    "assessed_areas",
                    "Select at least one area for a focused assessment.",
                )

        if (
            cleaned_data.get("follow_up_required")
            and not (cleaned_data.get("follow_up_notes") or "").strip()
        ):
            self.add_error(
                "follow_up_notes",
                "Enter the action needed when follow-up is required.",
            )

        for area, (status_field, notes_field) in self.AREA_FIELDS.items():
            if area not in (cleaned_data.get("assessed_areas") or []):
                continue

            if not cleaned_data.get(status_field):
                self.add_error(
                    status_field,
                    "Select a status for each area included in the assessment.",
                )

        return cleaned_data

    def save(self, commit=True):
        assessment = super().save(commit=False)
        assessment.assessment_type = self.cleaned_data["assessment_type"]
        assessment.assessed_areas = self.cleaned_data["assessed_areas"]

        if commit:
            assessment.save()
            self.save_m2m()

        return assessment

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        all_areas = list(RoomAssessmentArea.values)

        if self.instance and self.instance.pk:
            self.fields["assessment_type"].initial = self.instance.assessment_type
            self.fields["assessed_areas"].initial = self.instance.assessed_areas or []
        else:
            self.fields["assessed_areas"].initial = all_areas

        selected_areas = (
            (
                self.data.getlist("assessed_areas")
                if hasattr(self.data, "getlist")
                else self.data.get("assessed_areas", [])
            )
            if self.is_bound
            else self.fields["assessed_areas"].initial
        )

        # Status fields are required only when their area is included.
        for area, (status_field, notes_field) in self.AREA_FIELDS.items():
            included = area in selected_areas
            self.fields[status_field].required = included
            self.fields[notes_field].required = False

    def clean(self):
        cleaned_data = super().clean()

        assessment_type = cleaned_data.get("assessment_type")
        assessed_areas = cleaned_data.get("assessed_areas") or []

        if assessment_type == RoomAssessmentType.FULL:
            cleaned_data["assessed_areas"] = list(RoomAssessmentArea.values)

        elif assessment_type == RoomAssessmentType.FOCUSED:
            if not assessed_areas:
                self.add_error(
                    "assessed_areas",
                    "Select at least one area for a focused assessment.",
                )

        if (
            cleaned_data.get("follow_up_required")
            and not (cleaned_data.get("follow_up_notes") or "").strip()
        ):
            self.add_error(
                "follow_up_notes",
                "Enter the action needed when follow-up is required.",
            )

        for area, (status_field, notes_field) in self.AREA_FIELDS.items():
            if area not in (cleaned_data.get("assessed_areas") or []):
                continue

            if not cleaned_data.get(status_field):
                self.add_error(
                    status_field,
                    "Select a status for each area included in the assessment.",
                )

        return cleaned_data

    def save(self, commit=True):
        assessment = super().save(commit=False)
        assessment.assessment_type = self.cleaned_data["assessment_type"]
        assessment.assessed_areas = self.cleaned_data["assessed_areas"]

        if commit:
            assessment.save()
            self.save_m2m()

        return assessment


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
