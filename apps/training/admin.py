"""Read-only administration for immutable published training records."""

from django.contrib import admin

from .models import TrainingCategory, TrainingGuide, TrainingGuideRevision


@admin.register(TrainingCategory)
class TrainingCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')


@admin.register(TrainingGuide)
class TrainingGuideAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'published_at', 'updated_at')
    list_filter = ('status', 'category')
    search_fields = ('title', 'summary', 'tags', 'slug')
    readonly_fields = tuple(field.name for field in TrainingGuide._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TrainingGuideRevision)
class TrainingGuideRevisionAdmin(admin.ModelAdmin):
    list_display = ('guide', 'revision_number', 'published_at', 'editor')
    list_select_related = ('guide', 'editor')
    readonly_fields = tuple(field.name for field in TrainingGuideRevision._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
