from django.urls import path

from . import guided_views, views

app_name = 'inventory'

urlpatterns = [
    path('', views.asset_list, name='asset_list'),
    path('new/', guided_views.start_asset_creation, name='asset_wizard_start'),
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
