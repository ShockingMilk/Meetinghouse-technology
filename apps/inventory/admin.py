"""Django admin configuration for inventory"""

from django.contrib import admin

from .models import (
    Asset,
    AssetConnection,
    BuildingAssessment,
    CameraPreset,
    MaintenanceRecord,
    Room,
    RoomAssessment,
    SoftwareInstallation,
    VideoWorkflow,
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
    )

    list_filter = (
        "connection_type",
        "connection_medium",
        "compatibility",
    )

    search_fields = (
        "source__inventory_number",
        "destination__inventory_number",
        "interface",
    )


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
