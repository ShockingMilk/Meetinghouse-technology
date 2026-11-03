"""Django admin configuration for inventory"""

from django.contrib import admin

from .models import (
    Asset,
    AssetConnection,
    AssetDependency,
    AssetSpecification,
    CompatibilityVerification,
    BuildingAssessment,
    CameraPreset,
    MaintenanceRecord,
    MaintenanceSchedule,
    Room,
    RoomAssessment,
    SoftwareInstallation,
    VideoWorkflow,
    ReplacementCompatibilityReview,
)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    """Admin configuration for rooms"""

    list_display = ("name", "room_number", "priority")
    list_filter = ("priority",)
    search_fields = ("name", "room_number")


@admin.register(BuildingAssessment)
class BuildingAssessmentAdmin(admin.ModelAdmin):
    """Admin configuration for building assessments"""

    list_display = (
        "building_role",
        "assessment_date",
        "audio_status",
        "network_status",
        "printing_type",
        "video_setup",
        "local_management_status",
        "room_priority",
        "funding_arrangement",
    )

    list_filter = (
        "building_role",
        "audio_status",
        "network_status",
        "local_management_status",
        "funding_arrangement",
        "room_priority",
    )

    readonly_fields = ("assessment_date",)


@admin.register(RoomAssessment)
class RoomAssessmentAdmin(admin.ModelAdmin):
    """Admin configuration for historical room assessments."""

    list_display = (
        "room",
        "assessment_date",
        "overall_status",
        "follow_up_required",
        "assessed_by",
    )
    list_filter = (
        "overall_status",
        "follow_up_required",
        "assessment_date",
    )
    search_fields = (
        "room__name",
        "room__room_number",
        "assessed_by",
        "notes",
        "follow_up_notes",
    )
    readonly_fields = ("created_at",)

    def get_readonly_fields(self, request, obj=None):
        """Keep saved assessments historical while allowing new entries."""
        if obj is None:
            return self.readonly_fields
        return tuple(field.name for field in self.model._meta.fields)

    def has_delete_permission(self, request, obj=None):
        """Preserve assessment history from accidental deletion."""
        return False


class AssetConnectionInline(admin.TabularInline):
    """Show outgoing connections on an asset"""

    model = AssetConnection
    fk_name = "source"
    extra = 0


class CameraPresetInline(admin.TabularInline):
    """Show camera presets on the camera asset"""

    model = CameraPreset
    extra = 0
    ordering = ("preset_number",)


class SoftwareInstallationInline(admin.TabularInline):
    """Show installed software on a host asset"""

    model = SoftwareInstallation
    extra = 0


class AssetDependencyInline(admin.TabularInline):
    model = AssetDependency
    fk_name = 'dependent_asset'
    extra = 0


class AssetSpecificationInline(admin.TabularInline):
    model = AssetSpecification
    extra = 0


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    """Admin configuration for technology assets"""

    list_display = (
        "inventory_number",
        "name",
        "category",
        "ownership",
        "condition",
        "status",
        "room",
    )

    list_filter = (
        "category",
        "ownership",
        "condition",
        "status",
    )

    search_fields = (
        "inventory_number",
        "name",
        "manufacturer",
        "model_number",
        "serial_number",
    )

    readonly_fields = (
        "asset_id",
        "created_at",
        "updated_at",
    )

    inlines = [
        AssetConnectionInline,
        CameraPresetInline,
        SoftwareInstallationInline,
        AssetDependencyInline,
        AssetSpecificationInline,
    ]


@admin.register(AssetConnection)
class AssetConnectionAdmin(admin.ModelAdmin):
    """Admin configuration for asset connections"""

    list_display = (
        "source",
        "destination",
        "connection_type",
        "connection_medium",
        "compatibility",
        "last_verified",
    )

    list_filter = (
        "connection_type",
        "connection_medium",
        "compatibility",
        "is_required",
    )

    search_fields = (
        "source__inventory_number",
        "destination__inventory_number",
        "interface",
        "signal_description",
    )


@admin.register(AssetDependency)
class AssetDependencyAdmin(admin.ModelAdmin):
    list_display = ('dependent_asset', 'required_asset', 'external_service_name', 'dependency_type', 'is_required', 'verification_status', 'last_verified')
    list_filter = ('dependency_type', 'is_required', 'verification_status', 'dependent_asset__ownership')
    search_fields = ('dependent_asset__inventory_number', 'dependent_asset__name', 'required_asset__inventory_number', 'required_asset__name', 'external_service_name', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AssetSpecification)
class AssetSpecificationAdmin(admin.ModelAdmin):
    list_display = ('asset', 'category', 'name', 'value', 'verification_status', 'updated_at')
    list_filter = ('category', 'verification_status', 'asset__ownership')
    search_fields = ('asset__inventory_number', 'asset__name', 'name', 'value', 'notes')


@admin.register(CompatibilityVerification)
class CompatibilityVerificationAdmin(admin.ModelAdmin):
    list_display = ('asset', 'related_asset', 'requirement', 'outcome', 'method', 'verified_by', 'verified_on')
    list_filter = ('outcome', 'method', 'verified_on', 'asset__ownership')
    search_fields = ('asset__inventory_number', 'asset__name', 'related_asset__inventory_number', 'requirement', 'proposed_replacement', 'verified_by')
    readonly_fields = ('created_at',)


@admin.register(ReplacementCompatibilityReview)
class ReplacementCompatibilityReviewAdmin(admin.ModelAdmin):
    list_display = ('asset', 'proposed_name', 'proposed_model', 'status', 'updated_at')
    list_filter = ('status', 'asset__ownership')
    search_fields = ('asset__inventory_number', 'asset__name', 'proposed_name', 'proposed_manufacturer', 'proposed_model')
    readonly_fields = ('updated_at',)


@admin.register(CameraPreset)
class CameraPresetAdmin(admin.ModelAdmin):
    """Admin configuration for PTZ presets"""

    list_display = (
        "camera",
        "preset_number",
        "name",
        "status",
        "last_verified",
    )

    list_filter = ("status",)
    ordering = ("camera", "preset_number")


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    """Admin configuration for maintenance records"""

    list_display = (
        "asset",
        "maintenance_type",
        "performed_at",
        "performed_by",
        "follow_up_required",
        "resolved_at",
    )

    list_filter = (
        "maintenance_type",
        "follow_up_required",
    )

    search_fields = (
        "asset__inventory_number",
        "description",
        "performed_by",
    )


@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = ('asset', 'name', 'activity_type', 'interval_months', 'starts_on', 'enabled')
    list_filter = ('enabled', 'activity_type', 'interval_months', 'asset__category')
    search_fields = ('asset__inventory_number', 'asset__name', 'name', 'description')
    autocomplete_fields = ('asset',)

    def has_delete_permission(self, request, obj=None):
        """Keep schedules visible as disabled history instead of deleting them."""
        return False


@admin.register(SoftwareInstallation)
class SoftwareInstallationAdmin(admin.ModelAdmin):
    """Admin configuration for installed software"""

    list_display = (
        "name",
        "host_asset",
        "version",
        "role",
        "is_enabled",
    )

    list_filter = ("role", "is_enabled")
    search_fields = ("name", "host_asset__inventory_number")


@admin.register(VideoWorkflow)
class VideoWorkflowAdmin(admin.ModelAdmin):
    """Admin configuration for video workflows"""

    list_display = (
        "name",
        "computer",
        "mode",
        "is_active",
    )

    list_filter = ("mode", "is_active")
    search_fields = ("name", "computer__inventory_number")
