from django.urls import path

from . import guided_views, maintenance_views, relationship_views, views

app_name = 'inventory'

urlpatterns = [
    path('', views.asset_list, name='asset_list'),
    path('rooms/', views.room_list, name='room_list'),
    path(
        'rooms/<int:pk>/',
        views.room_detail,
        name='room_detail',
    ),
    path(
        'rooms/<int:pk>/assessments/new/',
        views.room_assessment_create,
        name='room_assessment_create',
    ),
    path('new/', guided_views.start_asset_creation, name='asset_wizard_start'),
    path('labels/print/', views.asset_labels, name='asset_labels'),
    path('<int:pk>/label/', views.asset_label, name='asset_label'),
    path('maintenance/', maintenance_views.dashboard, name='maintenance_dashboard'),
    path('maintenance/follow-ups/', maintenance_views.dashboard, name='maintenance_followups'),
    path('maintenance/reports/', maintenance_views.reports, name='maintenance_reports'),
    path('maintenance/schedules/new/', maintenance_views.schedule_create, name='maintenance_schedule_create'),
    path('maintenance/schedules/new/<int:asset_pk>/', maintenance_views.schedule_create, name='maintenance_schedule_create_for_asset'),
    path('maintenance/schedules/<int:pk>/edit/', maintenance_views.schedule_edit, name='maintenance_schedule_edit'),
    path('maintenance/records/new/', maintenance_views.maintenance_record_create, name='maintenance_record_create'),
    path('<int:asset_pk>/maintenance/new/', maintenance_views.maintenance_record_create, name='maintenance_record_create_for_asset'),
    path('maintenance/records/<int:pk>/edit/', maintenance_views.maintenance_record_edit, name='maintenance_record_edit'),
    path('maintenance/records/<int:pk>/', maintenance_views.maintenance_record_detail, name='maintenance_record_detail'),
    path('relationships/', relationship_views.relationship_index, name='relationship_index'),
    path('relationships/new/', relationship_views.relationship_form, {'kind': 'connection'}, name='relationship_create'),
    path('relationships/<str:kind>/new/', relationship_views.relationship_form, name='relationship_create'),
    path('relationships/<str:kind>/new/asset/<int:asset_pk>/', relationship_views.relationship_form, name='relationship_create_for_asset'),
    path('relationships/<str:kind>/<int:pk>/edit/', relationship_views.relationship_form, name='relationship_edit'),
    path('assets/<int:asset_pk>/replacement-review/', relationship_views.replacement_review, name='replacement_review'),
    path('assets/<int:asset_pk>/replacement-review/edit/', relationship_views.relationship_form, {'kind': 'review'}, name='replacement_review_edit'),
    path(
        'drafts/<uuid:wizard_id>/step/<int:step>/',
        guided_views.asset_wizard_step,
        name='asset_wizard_step',
    ),
    path(
        'drafts/<uuid:wizard_id>/review/',
        guided_views.asset_wizard_review,
        name='asset_wizard_review',
    ),
    path(
        'drafts/<uuid:wizard_id>/room/',
        guided_views.room_quick_add,
        name='room_quick_add',
    ),
    path(
        'drafts/<uuid:wizard_id>/cancel/',
        guided_views.cancel_asset_draft,
        name='asset_wizard_cancel',
    ),
    path('<int:pk>/edit/', guided_views.start_asset_edit, name='asset_wizard_edit'),
    path('<int:pk>/', views.asset_detail, name='asset_detail'),
]
